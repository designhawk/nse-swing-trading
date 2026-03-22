"""
NSE Swing Trading — Daily Signal Generator

Reads Friday's (or last available) close prices and tells you:
  - What to BUY at Monday's market open
  - What to EXIT at open (stop hit or RSI overbought)
  - Stop-loss prices for stocks you currently hold

Usage:
    python signals.py              # Today's signals (uses cached data)
    python signals.py --refresh    # Re-download latest prices first (do this every morning)
    python signals.py --held RELIANCE HCLTECH   # Track specific stocks you own
"""

import os
import sys
import time
import argparse
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from prepare import (
    SYMBOLS, DATA_DIR, LOOKBACK_BARS,
    BarData, PortfolioState, Signal,
    INITIAL_CAPITAL,
)


# ---------------------------------------------------------------------------
# Data refresh
# ---------------------------------------------------------------------------

def refresh_data():
    """Re-download latest prices for all symbols from Groww API."""
    from dotenv import load_dotenv
    load_dotenv()
    from prepare import _get_groww_client, _download_groww_data, TRAIN_START, TEST_END

    print("Refreshing data from Groww...")
    groww = _get_groww_client()
    ok = 0
    for symbol in SYMBOLS:
        filepath = os.path.join(DATA_DIR, f"{symbol.replace('&', '_')}_1d.parquet")
        try:
            df = _download_groww_data(groww, symbol, TRAIN_START, TEST_END)
            if df.empty:
                continue
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            os.makedirs(DATA_DIR, exist_ok=True)
            df.to_parquet(filepath, index=False)
            ok += 1
        except Exception as e:
            print(f"  Warning: {symbol}: {e}")
    print(f"Updated {ok}/{len(SYMBOLS)} symbols.\n")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all_data():
    """Load all available historical data (not split-filtered)."""
    result = {}
    for symbol in SYMBOLS:
        filepath = os.path.join(DATA_DIR, f"{symbol.replace('&', '_')}_1d.parquet")
        if not os.path.exists(filepath):
            continue
        try:
            df = pd.read_parquet(filepath)
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            if len(df) > 0:
                result[symbol] = df
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Strategy replay
# ---------------------------------------------------------------------------

def replay_strategy(strategy, data):
    """
    Replay strategy on all available data to warm up indicators.
    Returns the pending signals (to execute tomorrow) and last bar data.
    Also returns the strategy's current state (peak prices, etc.)
    """
    all_timestamps = set()
    for df in data.values():
        all_timestamps.update(df['timestamp'].tolist())
    timestamps = sorted(all_timestamps)

    indexed = {sym: df.set_index('timestamp') for sym, df in data.items()}
    history_buffers = {sym: [] for sym in data}

    portfolio = PortfolioState(
        cash=INITIAL_CAPITAL,
        positions={},
        entry_prices={},
        equity=INITIAL_CAPITAL,
        timestamp=0,
    )

    pending_signals = []
    last_bar_data = {}

    for ts in timestamps:
        bar_data = {}
        for symbol in data:
            if symbol not in indexed or ts not in indexed[symbol].index:
                continue
            row = indexed[symbol].loc[ts]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            bar_dict = {
                'timestamp': ts, 'open': float(row['open']),
                'high': float(row['high']), 'low': float(row['low']),
                'close': float(row['close']), 'volume': float(row['volume']),
                'funding_rate': 0.0,
            }
            history_buffers[symbol].append(bar_dict)
            if len(history_buffers[symbol]) > LOOKBACK_BARS:
                history_buffers[symbol] = history_buffers[symbol][-LOOKBACK_BARS:]
            hist_df = pd.DataFrame(history_buffers[symbol])
            bar_data[symbol] = BarData(
                symbol=symbol, timestamp=ts,
                open=float(row['open']), high=float(row['high']),
                low=float(row['low']), close=float(row['close']),
                volume=float(row['volume']), funding_rate=0.0,
                history=hist_df,
            )
        if not bar_data:
            continue

        # Execute previous bar's pending signals at today's open
        for sig in pending_signals:
            if sig.symbol not in bar_data:
                continue
            exec_price = bar_data[sig.symbol].open
            current_pos = portfolio.positions.get(sig.symbol, 0.0)
            delta = sig.target_position - current_pos
            if abs(delta) < 10.0:
                continue
            if sig.target_position == 0:
                if sig.symbol in portfolio.entry_prices:
                    entry = portfolio.entry_prices[sig.symbol]
                    if entry > 0:
                        pnl = current_pos * (exec_price - entry) / entry
                        portfolio.cash += abs(current_pos) + pnl
                    del portfolio.entry_prices[sig.symbol]
                portfolio.positions.pop(sig.symbol, None)
            elif current_pos == 0:
                portfolio.cash -= abs(sig.target_position)
                portfolio.positions[sig.symbol] = sig.target_position
                portfolio.entry_prices[sig.symbol] = exec_price
            else:
                portfolio.positions[sig.symbol] = sig.target_position

        pending_signals = []

        # Mark-to-market
        unrealized = sum(
            pos * (bar_data[sym].close - portfolio.entry_prices.get(sym, bar_data[sym].close))
            / portfolio.entry_prices.get(sym, bar_data[sym].close)
            for sym, pos in portfolio.positions.items() if sym in bar_data
        )
        portfolio.equity = portfolio.cash + sum(abs(v) for v in portfolio.positions.values()) + unrealized

        try:
            pending_signals = strategy.on_bar(bar_data, portfolio) or []
        except Exception:
            pending_signals = []

        last_bar_data = bar_data

    return pending_signals, portfolio, last_bar_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def calc_atr(history, lookback=14):
    if len(history) < lookback + 1:
        return None
    highs = history['high'].values[-lookback:]
    lows = history['low'].values[-lookback:]
    closes = history['close'].values[-(lookback+1):-1]
    tr = np.maximum(highs - lows,
                    np.maximum(np.abs(highs - closes), np.abs(lows - closes)))
    return np.mean(tr)


def ts_to_date(ts_ms):
    return datetime.utcfromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d')


def divider(char='-', width=62):
    print(char * width)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="NSE swing trading signal generator")
    parser.add_argument('--refresh', action='store_true',
                        help='Re-download latest prices first (recommended each morning)')
    parser.add_argument('--held', nargs='*', metavar='SYMBOL',
                        help='Stocks you actually own (e.g. --held RELIANCE HCLTECH)')
    args = parser.parse_args()

    if args.refresh:
        refresh_data()

    from strategy import Strategy, ATR_STOP_MULT
    strategy = Strategy()

    print("Loading data...")
    data = load_all_data()
    if not data:
        print("No data found. Run: python prepare.py")
        return

    pending_signals, paper_portfolio, last_bar_data = replay_strategy(strategy, data)

    latest_ts = max(bd.timestamp for bd in last_bar_data.values()) if last_bar_data else 0
    data_date = ts_to_date(latest_ts) if latest_ts else "unknown"

    print()
    divider('=')
    print(f"  NSE SWING SIGNALS")
    print(f"  Based on: {data_date} close prices")
    print(f"  Execute:  Next trading day at market open (~9:15 AM IST)")
    divider('=')

    # ----------------------------------------------------------------
    # Section 1: New BUY signals
    # ----------------------------------------------------------------
    buy_signals = [s for s in pending_signals if s.target_position > 0]
    sell_signals = [s for s in pending_signals if s.target_position == 0]

    print()
    if buy_signals:
        print(f"  BUY tomorrow at market open  ({len(buy_signals)} stocks)")
        divider()
        print(f"  {'Stock':<18}  {'Buy ~Rs':>9}  {'Stop Rs':>9}  {'Target Rs':>10}  {'Risk %':>7}")
        divider()
        for sig in sorted(buy_signals, key=lambda x: x.symbol):
            if sig.symbol not in last_bar_data:
                continue
            bd = last_bar_data[sig.symbol]
            close = bd.close
            atr = calc_atr(bd.history, 14)
            if atr:
                stop = close - ATR_STOP_MULT * atr
                risk = close - stop
                target = close + 2 * risk          # 2:1 reward-to-risk
                risk_pct = risk / close * 100
                print(f"  {sig.symbol:<18}  {close:>9,.2f}  {stop:>9,.2f}  {target:>10,.2f}  {risk_pct:>6.1f}%")
            else:
                print(f"  {sig.symbol:<18}  {close:>9,.2f}  (not enough data for stop)")
        print()
        print("  Buy:    place order at market open (~9:15 AM)")
        print("  Stop:   exit immediately if price falls to this level intraday")
        print("  Target: no fixed target — strategy trails the stop as price rises")
        print("          the 2:1 target shown is a rough guide only")
    else:
        print("  No new buy signals today — stay in cash.")

    # ----------------------------------------------------------------
    # Section 2: EXIT signals (only relevant if you hold the stock)
    # ----------------------------------------------------------------
    print()
    if sell_signals:
        print(f"  EXIT at market open  ({len(sell_signals)} stocks)")
        divider()
        print("  Only relevant if you actually hold these stocks.")
        divider()
        for sig in sorted(sell_signals, key=lambda x: x.symbol):
            paper_entry = paper_portfolio.entry_prices.get(sig.symbol, 0)
            if sig.symbol in last_bar_data:
                close = last_bar_data[sig.symbol].close
                if paper_entry > 0:
                    pnl_pct = (close - paper_entry) / paper_entry * 100
                    print(f"  SELL  {sig.symbol:<18}  last close Rs {close:,.2f}  ({pnl_pct:+.1f}% from entry)")
                else:
                    print(f"  SELL  {sig.symbol:<18}  last close Rs {close:,.2f}")
    else:
        print("  No exits signaled today.")

    # ----------------------------------------------------------------
    # Section 3: Stop prices for stocks you hold
    # ----------------------------------------------------------------
    held_symbols = args.held or []

    if held_symbols:
        print()
        print(f"  YOUR HOLDINGS — current stop prices")
        divider()
        print("  Exit immediately if price falls BELOW the stop, any time during the day.")
        divider()
        print(f"  {'Stock':<20}  {'Last Close':>10}  {'Stop Rs':>9}  {'Gap %':>7}")
        divider()
        found_any = False
        for symbol in sorted(held_symbols):
            if symbol not in last_bar_data:
                print(f"  {symbol:<20}  no data")
                continue
            bd = last_bar_data[symbol]
            atr = calc_atr(bd.history, 14)
            peak = strategy.peak_prices.get(symbol, bd.close)
            if atr:
                stop = peak - ATR_STOP_MULT * atr
                gap_pct = (bd.close - stop) / bd.close * 100
                print(f"  {symbol:<20}  {bd.close:>10,.2f}  {stop:>9,.2f}  {gap_pct:>6.1f}%")
            else:
                print(f"  {symbol:<20}  {bd.close:>10,.2f}  (insufficient history)")
            found_any = True
        if not found_any:
            print("  None of your symbols were found.")
        print()
        print("  Run each morning:  python signals.py --refresh --held RELIANCE HCLTECH")

    else:
        print()
        print("  Holding stocks? Add them to see stop prices:")
        print("  python signals.py --refresh --held RELIANCE HCLTECH")

    # ----------------------------------------------------------------
    # Section 4: Market overview
    # ----------------------------------------------------------------
    print()
    divider('=')
    print("  MARKET OVERVIEW (based on strategy indicators)")
    divider('=')

    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for sym, bd in last_bar_data.items():
        closes = bd.history['close'].values if len(bd.history) > 30 else None
        if closes is None or len(closes) < 30:
            continue
        # Simple trend check: price vs 20-day SMA
        sma20 = closes[-20:].mean()
        if bd.close > sma20 * 1.01:
            bullish_count += 1
        elif bd.close < sma20 * 0.99:
            bearish_count += 1
        else:
            neutral_count += 1

    total = bullish_count + bearish_count + neutral_count
    if total > 0:
        bull_pct = bullish_count / total * 100
        bear_pct = bearish_count / total * 100
        print()
        print(f"  Stocks above 20-day SMA:  {bullish_count}/{total} ({bull_pct:.0f}%)  — market breadth")
        print(f"  Stocks below 20-day SMA:  {bearish_count}/{total} ({bear_pct:.0f}%)")
        if bull_pct >= 60:
            print("  Bias: BULLISH — momentum strategies tend to work well")
        elif bear_pct >= 60:
            print("  Bias: BEARISH — expect fewer buy signals, more stops")
        else:
            print("  Bias: MIXED — choppy conditions, be selective")

    print()
    divider('=')
    print("  DISCLAIMER: Research tool only. Not financial advice.")
    print("  Verify all signals. Use your own judgement before trading.")
    divider('=')
    print()


if __name__ == "__main__":
    main()
