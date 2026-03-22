"""
Autotrader backtesting engine for Indian NSE stocks. Fixed evaluation harness — DO NOT MODIFY.
Downloads historical data from Groww Trade API, runs backtests, computes scores.

Usage:
    python prepare.py                  # download data
    python prepare.py --symbols RELIANCE    # download specific symbols
"""

import os
import sys
import time
import math
import signal
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import pyarrow.parquet as pq
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

TIME_BUDGET = 120              # backtest time budget in seconds (2 minutes)
INITIAL_CAPITAL = 1_000_000.0  # ₹10 Lakhs starting capital
BROKERAGE_PER_TRADE = 20.0     # Zerodha flat Rs 20/order (buy and sell)
EXCHANGE_CHARGE_BPS = 3.5      # NSE transaction charges ~3.5 bps
STT_SELL_BPS = 10.0            # STT 0.1% on sell side only (delivery equity)
SLIPPAGE_BPS = 5.0             # Realistic daily bar slippage
MAX_LEVERAGE = 1               # No leverage for cash market (1x)
LOOKBACK_BARS = 500            # history buffer provided to strategy
BAR_INTERVAL = "1d"            # Daily bars

# Nifty 50 large-cap NSE stocks (Groww symbols — no .NS suffix)
SYMBOLS = [
    # Original 10
    "RELIANCE",   # Reliance Industries
    "TCS",        # Tata Consultancy Services
    "HDFCBANK",   # HDFC Bank
    "INFY",       # Infosys
    "ICICIBANK",  # ICICI Bank
    "HINDUNILVR", # Hindustan Unilever
    "ITC",        # ITC Limited
    "SBIN",       # State Bank of India
    "BHARTIARTL", # Bharti Airtel
    "KOTAKBANK",  # Kotak Mahindra Bank
    # Nifty 50 additions
    "ADANIENT",   # Adani Enterprises
    "ADANIPORTS", # Adani Ports
    "APOLLOHOSP", # Apollo Hospitals
    "ASIANPAINT", # Asian Paints
    "AXISBANK",   # Axis Bank
    "BAJAJ-AUTO", # Bajaj Auto
    "BAJAJFINSV", # Bajaj Finserv
    "BAJFINANCE", # Bajaj Finance
    "BPCL",       # BPCL
    "BRITANNIA",  # Britannia Industries
    "CIPLA",      # Cipla
    "COALINDIA",  # Coal India
    "DIVISLAB",   # Divi's Laboratories
    "DRREDDY",    # Dr. Reddy's
    "EICHERMOT",  # Eicher Motors
    "GRASIM",     # Grasim Industries
    "HCLTECH",    # HCL Technologies
    "HDFCLIFE",   # HDFC Life
    "HEROMOTOCO", # Hero MotoCorp
    "HINDALCO",   # Hindalco Industries
    "INDUSINDBK", # IndusInd Bank
    "JSWSTEEL",   # JSW Steel
    "LT",         # Larsen & Toubro
    "LTIM",       # LTIMindtree
    "M&M",        # Mahindra & Mahindra
    "MARUTI",     # Maruti Suzuki
    "NESTLEIND",  # Nestle India
    "NTPC",       # NTPC
    "ONGC",       # ONGC
    "POWERGRID",  # Power Grid Corp
    "SBILIFE",    # SBI Life Insurance
    "SHRIRAMFIN", # Shriram Finance
    "SUNPHARMA",  # Sun Pharma
    "TATACONSUM", # Tata Consumer Products
    "TATAMOTORS", # Tata Motors
    "TATASTEEL",  # Tata Steel
    "TECHM",      # Tech Mahindra
    "TITAN",      # Titan Company
    "TRENT",      # Trent
    "ULTRACEMCO", # UltraTech Cement
    "WIPRO",      # Wipro
]

# Date splits (2020-2026)
TRAIN_START = "2020-01-01"
TRAIN_END = "2024-01-01"
VAL_START = "2024-01-01"
VAL_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-12-31"

DAYS_PER_YEAR = 252            # NSE trading days per year

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "autotrader-india")
DATA_DIR = os.path.join(CACHE_DIR, "data")

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class BarData:
    symbol: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    funding_rate: float  # Always 0 for stocks, kept for compatibility
    history: pd.DataFrame  # last LOOKBACK_BARS bars

@dataclass
class Signal:
    symbol: str
    target_position: float   # target INR notional (signed: +long, -short)
    order_type: str = "market"

@dataclass
class PortfolioState:
    cash: float
    positions: dict          # symbol -> signed INR notional
    entry_prices: dict       # symbol -> avg entry price
    equity: float = 0.0
    timestamp: int = 0

@dataclass
class BacktestResult:
    sharpe: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    num_trades: int = 0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    annual_turnover: float = 0.0
    backtest_seconds: float = 0.0
    equity_curve: list = field(default_factory=list)
    trade_log: list = field(default_factory=list)

# ---------------------------------------------------------------------------
# Data download
# ---------------------------------------------------------------------------

def _get_groww_client():
    """Authenticate with Groww API using credentials from .env.
    Supports both TOTP flow (GROWW_TOTP_SECRET set) and API key+secret flow.
    """
    from growwapi import GrowwAPI
    api_key = os.environ.get("GROWW_API_KEY")
    api_secret = os.environ.get("GROWW_API_SECRET")
    totp_secret = os.environ.get("GROWW_TOTP_SECRET")

    if not api_key:
        raise ValueError("GROWW_API_KEY must be set in .env")

    if totp_secret:
        # TOTP flow (no daily expiry)
        import pyotp
        totp = pyotp.TOTP(totp_secret).now()
        access_token = GrowwAPI.get_access_token(api_key=api_key, totp=totp)
    else:
        # API key + secret flow
        if not api_secret:
            raise ValueError("GROWW_API_SECRET must be set in .env")
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)

    return GrowwAPI(access_token)


def _download_groww_data(groww, symbol: str, start: str, end: str) -> pd.DataFrame:
    """Download daily OHLCV via Groww get_historical_candle_data (deprecated but functional).
    Supports up to 1080 days per request for daily (1440 min) interval per official docs."""
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = min(datetime.strptime(end, "%Y-%m-%d"), datetime.now())

        all_candles = []
        chunk_start = start_dt
        while chunk_start < end_dt:
            chunk_end = min(chunk_start + timedelta(days=1079), end_dt)  # 1080-day limit for daily
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                resp = groww.get_historical_candle_data(
                    trading_symbol=symbol,
                    exchange=groww.EXCHANGE_NSE,
                    segment=groww.SEGMENT_CASH,
                    start_time=chunk_start.strftime("%Y-%m-%d 00:00:00"),
                    end_time=chunk_end.strftime("%Y-%m-%d 23:59:59"),
                    interval_in_minutes=1440,  # daily
                )
            candles = resp.get("candles", []) if isinstance(resp, dict) else []
            all_candles.extend(candles)
            chunk_start = chunk_end + timedelta(days=1)
            time.sleep(0.3)

        if not all_candles:
            print(f"  {symbol}: No data returned from Groww")
            return pd.DataFrame()

        # Each candle: [epoch_seconds, open, high, low, close, volume]
        # Groww timestamps are IST midnight (UTC-5:30h). Add 19800s to align to UTC midnight
        # so load_data date comparisons work correctly.
        df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = df["timestamp"].astype(int) * 1000 + 19800000  # IST → UTC ms
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close"])
        df["funding_rate"] = 0.0
        return df[["timestamp", "open", "high", "low", "close", "volume", "funding_rate"]]

    except Exception as e:
        print(f"  {symbol}: Error downloading data - {e}")
        return pd.DataFrame()


def download_data(symbols=None):
    """Download historical OHLCV data for all symbols from Groww Trade API."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if symbols is None:
        symbols = SYMBOLS

    groww = _get_groww_client()
    start_date = TRAIN_START
    end_date = TEST_END

    for symbol in symbols:
        filepath = os.path.join(DATA_DIR, f"{symbol.replace('&', '_')}_1d.parquet")
        if os.path.exists(filepath):
            try:
                existing = pd.read_parquet(filepath)
                print(f"  {symbol}: already have {len(existing)} bars")
                continue
            except:
                pass

        print(f"  {symbol}: downloading from Groww...")

        df = _download_groww_data(groww, symbol, start_date, end_date)

        if df.empty or len(df) < 100:
            print(f"  {symbol}: Insufficient data ({len(df)} bars), skipping")
            continue

        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        df.to_parquet(filepath, index=False)
        print(f"  {symbol}: saved {len(df)} bars to {filepath}")


def load_data(split: str = "val") -> dict:
    """Load OHLCV data for the given split. Returns {symbol: DataFrame}."""
    splits = {
        "train": (TRAIN_START, TRAIN_END),
        "val": (VAL_START, VAL_END),
        "test": (TEST_START, TEST_END),
    }
    assert split in splits, f"split must be one of {list(splits.keys())}"
    start_str, end_str = splits[split]
    
    # Convert to timestamps for comparison
    start_dt = pd.Timestamp(start_str, tz="UTC")
    end_dt = pd.Timestamp(end_str, tz="UTC")
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    result = {}
    for symbol in SYMBOLS:
        filepath = os.path.join(DATA_DIR, f"{symbol.replace('&', '_')}_1d.parquet")
        if not os.path.exists(filepath):
            print(f"  Warning: {symbol} data file not found")
            continue
        try:
            df = pd.read_parquet(filepath)
            # Convert timestamp to numeric if needed
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            mask = (df["timestamp"] >= start_ms) & (df["timestamp"] < end_ms)
            split_df = df[mask].reset_index(drop=True)
            if len(split_df) > 0:
                result[symbol] = split_df
                print(f"  {symbol}: loaded {len(split_df)} bars for {split} split")
            else:
                print(f"  {symbol}: no data in {split} split date range")
        except Exception as e:
            print(f"  Error loading {symbol}: {e}")
    
    if not result:
        print(f"\nWarning: No data loaded for {split} split!")
        print("Run 'python prepare.py' first to download data.")
    
    return result

# ---------------------------------------------------------------------------
# Backtesting engine (DO NOT CHANGE)
# ---------------------------------------------------------------------------

def run_backtest(strategy, data: dict) -> BacktestResult:
    """
    Run strategy over data. Returns BacktestResult with full metrics.
    Enforces TIME_BUDGET.
    """
    t_start = time.time()

    # Build unified timeline
    all_timestamps = set()
    for symbol, df in data.items():
        all_timestamps.update(df["timestamp"].tolist())
    timestamps = sorted(all_timestamps)

    if not timestamps:
        return BacktestResult()

    # Index data by (symbol, timestamp) for fast lookup
    indexed = {}
    for symbol, df in data.items():
        indexed[symbol] = df.set_index("timestamp")

    # Portfolio state
    portfolio = PortfolioState(
        cash=INITIAL_CAPITAL,
        positions={},
        entry_prices={},
        equity=INITIAL_CAPITAL,
        timestamp=0,
    )

    equity_curve = [INITIAL_CAPITAL]
    daily_returns = []
    trade_log = []
    total_volume = 0.0
    prev_equity = INITIAL_CAPITAL
    pending_signals = []  # signals from previous bar, executed at this bar's open

    # History buffers
    history_buffers = {symbol: [] for symbol in data}

    for ts in timestamps:
        elapsed = time.time() - t_start
        if elapsed > TIME_BUDGET:
            break

        portfolio.timestamp = ts

        # Build bar data
        bar_data = {}
        for symbol in data:
            if symbol not in indexed or ts not in indexed[symbol].index:
                continue
            row = indexed[symbol].loc[ts]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]

            # Update history buffer
            bar_dict = {
                "timestamp": ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "funding_rate": float(row.get("funding_rate", 0.0)),
            }
            history_buffers[symbol].append(bar_dict)
            if len(history_buffers[symbol]) > LOOKBACK_BARS:
                history_buffers[symbol] = history_buffers[symbol][-LOOKBACK_BARS:]

            hist_df = pd.DataFrame(history_buffers[symbol])

            bar_data[symbol] = BarData(
                symbol=symbol,
                timestamp=ts,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                funding_rate=float(row.get("funding_rate", 0.0)),
                history=hist_df,
            )

        if not bar_data:
            continue

        # === STEP 1: Execute PREVIOUS bar's signals at today's OPEN price ===
        for sig in pending_signals:
            if sig.symbol not in bar_data:
                continue

            open_price = bar_data[sig.symbol].open  # next-bar open execution
            current_pos = portfolio.positions.get(sig.symbol, 0.0)
            delta = sig.target_position - current_pos

            if abs(delta) < 10.0:  # < Rs 10 change, skip
                continue

            # Check leverage constraint (1x for cash market)
            new_positions = dict(portfolio.positions)
            new_positions[sig.symbol] = sig.target_position
            total_exposure = sum(abs(v) for v in new_positions.values())
            if total_exposure > portfolio.equity * MAX_LEVERAGE:
                continue

            # Apply slippage (at open price)
            slippage = open_price * SLIPPAGE_BPS / 10000
            if delta > 0:  # buying
                exec_price = open_price + slippage
            else:  # selling
                exec_price = open_price - slippage

            # Indian NSE costs: flat brokerage + exchange charges + STT on sells
            trade_notional = abs(delta)
            fee = BROKERAGE_PER_TRADE + trade_notional * EXCHANGE_CHARGE_BPS / 10000
            if delta < 0:  # sell side: Securities Transaction Tax
                fee += trade_notional * STT_SELL_BPS / 10000
            portfolio.cash -= fee
            total_volume += trade_notional

            # Update position
            pnl = 0.0
            if sig.target_position == 0:
                # Closing position — realize PnL
                if sig.symbol in portfolio.entry_prices:
                    entry = portfolio.entry_prices[sig.symbol]
                    if entry > 0:
                        pnl = current_pos * (exec_price - entry) / entry
                        portfolio.cash += abs(current_pos) + pnl
                    del portfolio.entry_prices[sig.symbol]
                if sig.symbol in portfolio.positions:
                    del portfolio.positions[sig.symbol]
                trade_log.append(("close", sig.symbol, delta, exec_price, pnl))
            else:
                if current_pos == 0:
                    # Opening new position
                    portfolio.cash -= abs(sig.target_position)
                    portfolio.positions[sig.symbol] = sig.target_position
                    portfolio.entry_prices[sig.symbol] = exec_price
                    trade_log.append(("open", sig.symbol, delta, exec_price, 0))
                else:
                    # Modifying position
                    old_notional = abs(current_pos)
                    old_entry = portfolio.entry_prices.get(sig.symbol, exec_price)
                    if abs(sig.target_position) < abs(current_pos):
                        reduced = abs(current_pos) - abs(sig.target_position)
                        if old_entry > 0:
                            pnl = (current_pos / abs(current_pos)) * reduced * (exec_price - old_entry) / old_entry
                        else:
                            pnl = 0.0
                        portfolio.cash += reduced + pnl
                    elif abs(sig.target_position) > abs(current_pos):
                        added = abs(sig.target_position) - abs(current_pos)
                        portfolio.cash -= added
                        if old_notional + added > 0:
                            new_entry = (old_entry * old_notional + exec_price * added) / (old_notional + added)
                            portfolio.entry_prices[sig.symbol] = new_entry
                    portfolio.positions[sig.symbol] = sig.target_position
                    trade_log.append(("modify", sig.symbol, delta, exec_price, 0))

        pending_signals = []

        # === STEP 2: Mark-to-market at CLOSE, record equity ===
        unrealized_pnl = 0.0
        for sym, pos_notional in portfolio.positions.items():
            if sym in bar_data:
                close_price = bar_data[sym].close
                entry_price = portfolio.entry_prices.get(sym, close_price)
                if entry_price > 0:
                    price_change = (close_price - entry_price) / entry_price
                    unrealized_pnl += pos_notional * price_change

        current_equity = portfolio.cash + sum(abs(v) for v in portfolio.positions.values()) + unrealized_pnl
        portfolio.equity = current_equity
        equity_curve.append(current_equity)

        # Daily return
        if prev_equity > 0:
            daily_returns.append((current_equity - prev_equity) / prev_equity)
        prev_equity = current_equity

        # === STEP 3: Generate signals for NEXT bar (buffered, not executed yet) ===
        try:
            pending_signals = strategy.on_bar(bar_data, portfolio) or []
        except Exception:
            pending_signals = []

        # Liquidation check
        if current_equity < INITIAL_CAPITAL * 0.01:
            break

    t_end = time.time()

    # Compute metrics
    returns = np.array(daily_returns) if daily_returns else np.array([0.0])
    eq = np.array(equity_curve)

    # Sharpe ratio (annualized from daily)
    if returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(DAYS_PER_YEAR)
    else:
        sharpe = 0.0

    # Total return
    final_equity = eq[-1] if len(eq) > 0 else INITIAL_CAPITAL
    total_return_pct = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    # Max drawdown
    peak = np.maximum.accumulate(eq)
    drawdown = (peak - eq) / np.where(peak > 0, peak, 1)
    max_drawdown_pct = drawdown.max() * 100

    # Win rate and profit factor
    trade_pnls = [t[4] for t in trade_log if t[0] == "close"]
    num_trades = len(trade_log)
    if trade_pnls:
        wins = [p for p in trade_pnls if p > 0]
        losses = [p for p in trade_pnls if p < 0]
        win_rate_pct = len(wins) / len(trade_pnls) * 100 if trade_pnls else 0
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1e-10
        profit_factor = gross_profit / gross_loss
    else:
        win_rate_pct = 0.0
        profit_factor = 0.0

    # Annual turnover
    data_days = len(timestamps)
    if data_days > 0:
        annual_turnover = total_volume * (DAYS_PER_YEAR / data_days)
    else:
        annual_turnover = 0.0

    return BacktestResult(
        sharpe=sharpe,
        total_return_pct=total_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        num_trades=num_trades,
        win_rate_pct=win_rate_pct,
        profit_factor=profit_factor,
        annual_turnover=annual_turnover,
        backtest_seconds=t_end - t_start,
        equity_curve=equity_curve,
        trade_log=trade_log,
    )

# ---------------------------------------------------------------------------
# Evaluation metric (DO NOT CHANGE — this is the fixed metric)
# ---------------------------------------------------------------------------

def compute_score(result: BacktestResult) -> float:
    """
    Composite risk-adjusted score (HIGHER is better).

    score = sharpe * sqrt(trade_count_factor) - drawdown_penalty - turnover_penalty

    Hard cutoffs for degenerate strategies.
    """
    # Hard cutoffs
    if result.num_trades < 10:
        return -999.0
    if result.max_drawdown_pct > 50.0:
        return -999.0
    final_equity = result.equity_curve[-1] if result.equity_curve else INITIAL_CAPITAL
    if final_equity < INITIAL_CAPITAL * 0.5:
        return -999.0

    # Trade count factor: full credit at 50+ trades
    trade_count_factor = min(result.num_trades / 50.0, 1.0)

    # Drawdown penalty: no penalty below 15%, then 5x per additional percent
    drawdown_penalty = max(0, result.max_drawdown_pct - 15.0) * 0.05

    # Turnover penalty: penalize excessive churning (>500x annual)
    turnover_ratio = result.annual_turnover / INITIAL_CAPITAL if INITIAL_CAPITAL > 0 else 0
    turnover_penalty = max(0, turnover_ratio - 500) * 0.001

    score = result.sharpe * math.sqrt(trade_count_factor) - drawdown_penalty - turnover_penalty
    return score

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare data for autotrader India")
    parser.add_argument("--symbols", nargs="+", default=None, help="Symbols to download (default: all)")
    args = parser.parse_args()

    print(f"Cache directory: {CACHE_DIR}")
    print()

    print("Downloading data from Groww...")
    print("This may take a few minutes...")
    print()
    download_data(args.symbols)
    print()
    print("Done! Ready to backtest.")
    print()
    print("Next steps:")
    print("  python backtest.py              # Run backtest on validation data")
    print("  python experiment_runner.py     # Run experiments with logging")
