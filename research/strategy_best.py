"""
Long-only swing trading strategy for Indian NSE stocks (Nifty 50).
This is the ONLY file you should edit when running experiments.

Strategy: Multi-signal ensemble, long-only, Nifty 50 universe
- 50 NSE symbols (full Nifty 50)
- Daily timeframe
- Signals: momentum, EMA crossover, RSI, MACD, Bollinger Bands
- Long-only: no short positions (legal for NSE cash equity)
"""

import numpy as np
from prepare import Signal, PortfolioState, BarData

# Nifty 50 large-cap NSE stocks (Groww symbols — no .NS suffix)
ACTIVE_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT",
    "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE",
    "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB",
    "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "INDUSINDBK", "JSWSTEEL",
    "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND",
    "NTPC", "ONGC", "POWERGRID", "SBILIFE", "SHRIRAMFIN",
    "SUNPHARMA", "TATACONSUM", "TATASTEEL",
    "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
]

# Equal weight: 2% per stock (50 stocks * 2% = 100% max deployed)
SYMBOL_WEIGHTS = {sym: 0.02 for sym in ACTIVE_SYMBOLS}

# Lookback periods (tuned for daily swing trading)
SHORT_WINDOW = 4      # 1 week
MED_WINDOW = 15        # ~2 weeks
MED2_WINDOW = 20      # 4 weeks
LONG_WINDOW = 40      # 1.5 months
EMA_FAST = 5
EMA_SLOW = 26
RSI_PERIOD = 14
RSI_BULL = 45
RSI_OVERBOUGHT = 75   # Exit long above this

MACD_FAST = 16
MACD_SLOW = 23
MACD_SIGNAL = 12

BB_PERIOD = 7

# Risk management
VOL_LOOKBACK = 30              # Volatility lookback
TARGET_VOL = 0.015             # 1.5% daily vol target
ATR_LOOKBACK = 14              # ATR lookback
ATR_STOP_MULT = 7.0            # Trailing stop multiplier
BASE_THRESHOLD = 0.012          # Momentum threshold (1%)

# Position management
COOLDOWN_BARS = 3              # Bars to wait after exit
MIN_VOTES = 4                  # Minimum bull votes needed (out of 5 signals)


def ema(values, span):
    """Calculate exponential moving average."""
    alpha = 2.0 / (span + 1)
    result = np.empty_like(values, dtype=float)
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    return result


def calc_rsi(closes, period):
    """Calculate RSI for given closes."""
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes[-(period+1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    rs = avg_gain / max(avg_loss, 1e-10)
    return 100 - 100 / (1 + rs)


class Strategy:
    def __init__(self):
        self.entry_prices = {}
        self.peak_prices = {}
        self.atr_at_entry = {}
        self.bar_count = 0
        self.exit_bar = {}
        self.peak_equity = 1_000_000.0

    def _calc_atr(self, history, lookback):
        """Calculate Average True Range."""
        if len(history) < lookback + 1:
            return None
        highs = history["high"].values[-lookback:]
        lows = history["low"].values[-lookback:]
        closes = history["close"].values[-(lookback+1):-1]
        tr = np.maximum(highs - lows,
                        np.maximum(np.abs(highs - closes), np.abs(lows - closes)))
        return np.mean(tr)

    def _calc_vol(self, closes, lookback):
        """Calculate realized volatility."""
        if len(closes) < lookback:
            return TARGET_VOL
        log_rets = np.diff(np.log(closes[-lookback:]))
        return max(np.std(log_rets), 1e-6)

    def _calc_macd(self, closes):
        """Calculate MACD histogram."""
        if len(closes) < MACD_SLOW + MACD_SIGNAL + 5:
            return 0.0
        fast_ema = ema(closes[-(MACD_SLOW + MACD_SIGNAL + 5):], MACD_FAST)
        slow_ema = ema(closes[-(MACD_SLOW + MACD_SIGNAL + 5):], MACD_SLOW)
        macd_line = fast_ema - slow_ema
        signal_line = ema(macd_line, MACD_SIGNAL)
        return macd_line[-1] - signal_line[-1]

    def _calc_bb_width_pctile(self, closes, period):
        """Calculate Bollinger Band width percentile."""
        if len(closes) < period * 3:
            return 50.0
        widths = []
        for i in range(period * 2, len(closes)):
            window = closes[i-period:i]
            sma = np.mean(window)
            std = np.std(window)
            width = (2 * std) / sma if sma > 0 else 0
            widths.append(width)
        if len(widths) < 2:
            return 50.0
        current_width = widths[-1]
        pctile = 100 * np.sum(np.array(widths) <= current_width) / len(widths)
        return pctile

    def on_bar(self, bar_data, portfolio):
        """
        Main strategy logic called once per bar.
        Long-only: only generates positive (buy) target positions.

        Args:
            bar_data: dict of symbol -> BarData
            portfolio: PortfolioState

        Returns:
            List of Signal objects (executed at next bar's open)
        """
        signals = []
        equity = portfolio.equity if portfolio.equity > 0 else portfolio.cash
        self.bar_count += 1

        self.peak_equity = max(self.peak_equity, equity)

        for symbol in ACTIVE_SYMBOLS:
            if symbol not in bar_data:
                continue

            bd = bar_data[symbol]

            # Ensure enough history
            min_history = max(LONG_WINDOW, EMA_SLOW, MACD_SLOW + MACD_SIGNAL + 5, BB_PERIOD * 3) + 1
            if len(bd.history) < min_history:
                continue

            closes = bd.history["close"].values
            mid = bd.close

            # Calculate volatility and dynamic threshold
            realized_vol = self._calc_vol(closes, VOL_LOOKBACK)
            vol_ratio = realized_vol / TARGET_VOL
            dyn_threshold = BASE_THRESHOLD * (0.3 + vol_ratio * 0.7)
            dyn_threshold = max(0.005, min(0.020, dyn_threshold))

            # Calculate returns
            ret_vshort = (closes[-1] - closes[-SHORT_WINDOW]) / closes[-SHORT_WINDOW]
            ret_short = (closes[-1] - closes[-MED_WINDOW]) / closes[-MED_WINDOW]

            # Signal 1: Medium-term momentum
            mom_bull = ret_short > dyn_threshold

            # Signal 2: Very-short momentum
            vshort_bull = ret_vshort > dyn_threshold * 0.7

            # Signal 3: EMA crossover
            ema_fast_arr = ema(closes[-(EMA_SLOW+10):], EMA_FAST)
            ema_slow_arr = ema(closes[-(EMA_SLOW+10):], EMA_SLOW)
            ema_bull = ema_fast_arr[-1] > ema_slow_arr[-1]

            # Signal 4: RSI momentum
            rsi = calc_rsi(closes, RSI_PERIOD)
            rsi_bull = rsi > RSI_BULL

            # Signal 5: MACD
            macd_hist = self._calc_macd(closes)
            macd_bull = macd_hist > 0

            # Count bull votes (5 signals, long-only)
            bull_votes = sum([mom_bull, vshort_bull, ema_bull, rsi_bull, macd_bull])
            bullish = bull_votes >= MIN_VOTES

            # Check cooldown
            in_cooldown = (self.bar_count - self.exit_bar.get(symbol, -999)) < COOLDOWN_BARS

            # Position size: 2% of equity per stock
            weight = SYMBOL_WEIGHTS.get(symbol, 0.02)
            size = equity * weight

            # Current position
            current_pos = portfolio.positions.get(symbol, 0.0)
            target = current_pos

            # Entry logic (no position, long-only)
            if current_pos == 0:
                if bullish and not in_cooldown:
                    target = size

            # Exit logic (have long position)
            elif current_pos > 0:
                # Calculate ATR for trailing stop
                atr = self._calc_atr(bd.history, ATR_LOOKBACK)
                if atr is None:
                    atr = self.atr_at_entry.get(symbol, mid * 0.02)

                # Initialize peak price for trailing stop
                if symbol not in self.peak_prices:
                    self.peak_prices[symbol] = mid

                # Trailing stop (long only)
                self.peak_prices[symbol] = max(self.peak_prices[symbol], mid)
                stop = self.peak_prices[symbol] - ATR_STOP_MULT * atr
                if mid < stop:
                    target = 0.0

                # RSI overbought exit
                if rsi > RSI_OVERBOUGHT:
                    target = 0.0

            # Generate signal if position changed
            if abs(target - current_pos) > 10.0:  # Rs 10 minimum change
                signals.append(Signal(symbol=symbol, target_position=target))

                # Track entry/exit for state management
                if target > 0 and current_pos == 0:
                    self.entry_prices[symbol] = mid
                    self.peak_prices[symbol] = mid
                    self.atr_at_entry[symbol] = self._calc_atr(bd.history, ATR_LOOKBACK) or mid * 0.02
                elif target == 0:
                    self.entry_prices.pop(symbol, None)
                    self.peak_prices.pop(symbol, None)
                    self.atr_at_entry.pop(symbol, None)
                    self.exit_bar[symbol] = self.bar_count

        return signals
