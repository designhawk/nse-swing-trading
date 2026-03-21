"""
Baseline momentum strategy for Indian NSE stocks.
This is the ONLY file you should edit when running experiments.

Strategy: Multi-signal ensemble for large-cap Indian stocks
- 10 NSE symbols (large-cap leaders)
- Daily timeframe
- Signals: momentum, EMA crossover, RSI, MACD, Bollinger Bands
"""

import numpy as np
from prepare import Signal, PortfolioState, BarData

# 10 Large-cap NSE stocks
ACTIVE_SYMBOLS = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
    "HINDUNILVR.NS",
    "ITC.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "KOTAKBANK.NS"
]

# Equal weight allocation (10% per stock)
SYMBOL_WEIGHTS = {sym: 0.10 for sym in ACTIVE_SYMBOLS}

# Lookback periods (adjusted for daily timeframe)
SHORT_WINDOW = 5      # 1 week
MED_WINDOW = 15       # 2 weeks
MED2_WINDOW = 20      # 4 weeks
LONG_WINDOW = 30      # 1.5 months
EMA_FAST = 7
EMA_SLOW = 26
RSI_PERIOD = 8
RSI_BULL = 50
RSI_BEAR = 55
RSI_OVERBOUGHT = 69
RSI_OVERSOLD = 31

MACD_FAST = 16
MACD_SLOW = 21
MACD_SIGNAL = 9

BB_PERIOD = 7

# Risk management
BASE_POSITION_PCT = 0.10       # 10% per stock (max 100% invested)
VOL_LOOKBACK = 20              # 1 month volatility
TARGET_VOL = 0.015             # 1.5% daily vol target
ATR_LOOKBACK = 14              # ATR lookback
ATR_STOP_MULT = 5.5            # Trailing stop multiplier
TAKE_PROFIT_PCT = 99.0         # Take profit (disabled with 99%)
BASE_THRESHOLD = 0.012         # Momentum threshold (1.2%)

# Position management
COOLDOWN_BARS = 1              # Bars to wait after exit
MIN_VOTES = 4                  # Minimum votes for signal (out of 6)


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
        # Calculate rolling BB width
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
        # Percentile of current width
        pctile = 100 * np.sum(np.array(widths) <= current_width) / len(widths)
        return pctile

    def on_bar(self, bar_data, portfolio):
        """
        Main strategy logic called once per bar.
        
        Args:
            bar_data: dict of symbol -> BarData
            portfolio: PortfolioState
            
        Returns:
            List of Signal objects
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
            ret_med = (closes[-1] - closes[-MED2_WINDOW]) / closes[-MED2_WINDOW]
            ret_long = (closes[-1] - closes[-LONG_WINDOW]) / closes[-LONG_WINDOW]

            # Signal 1: Momentum
            mom_bull = ret_short > dyn_threshold
            mom_bear = ret_short < -dyn_threshold

            # Signal 2: Very-short momentum
            vshort_bull = ret_vshort > dyn_threshold * 0.7
            vshort_bear = ret_vshort < -dyn_threshold * 0.7

            # Signal 3: EMA crossover
            ema_fast_arr = ema(closes[-(EMA_SLOW+10):], EMA_FAST)
            ema_slow_arr = ema(closes[-(EMA_SLOW+10):], EMA_SLOW)
            ema_bull = ema_fast_arr[-1] > ema_slow_arr[-1]
            ema_bear = ema_fast_arr[-1] < ema_slow_arr[-1]

            # Signal 4: RSI
            rsi = calc_rsi(closes, RSI_PERIOD)
            rsi_bull = rsi > RSI_BULL
            rsi_bear = rsi < RSI_BEAR

            # Signal 5: MACD
            macd_hist = self._calc_macd(closes)
            macd_bull = macd_hist > 0
            macd_bear = macd_hist < 0

            # Signal 6: Bollinger Band compression
            bb_pctile = self._calc_bb_width_pctile(closes, BB_PERIOD)
            bb_compressed = bb_pctile < 85

            # Count votes
            bull_votes = sum([mom_bull, vshort_bull, ema_bull, rsi_bull, macd_bull, bb_compressed])
            bear_votes = sum([mom_bear, vshort_bear, ema_bear, rsi_bear, macd_bear, bb_compressed])

            # Determine signal
            bullish = bull_votes >= MIN_VOTES
            bearish = bear_votes >= MIN_VOTES

            # Check cooldown
            in_cooldown = (self.bar_count - self.exit_bar.get(symbol, -999)) < COOLDOWN_BARS

            # Calculate position size
            weight = SYMBOL_WEIGHTS.get(symbol, 0.10)
            size = equity * BASE_POSITION_PCT * weight

            # Current position
            current_pos = portfolio.positions.get(symbol, 0.0)
            target = current_pos

            # Entry logic (no position)
            if current_pos == 0:
                if not in_cooldown:
                    if bullish:
                        target = size
                    elif bearish:
                        target = -size

            # Exit/Modification logic (have position)
            else:
                # Calculate ATR for trailing stop
                atr = self._calc_atr(bd.history, ATR_LOOKBACK)
                if atr is None:
                    atr = self.atr_at_entry.get(symbol, mid * 0.02)

                # Initialize peak prices for trailing stop
                if symbol not in self.peak_prices:
                    self.peak_prices[symbol] = mid

                # Trailing stop
                if current_pos > 0:
                    self.peak_prices[symbol] = max(self.peak_prices[symbol], mid)
                    stop = self.peak_prices[symbol] - ATR_STOP_MULT * atr
                    if mid < stop:
                        target = 0.0
                else:
                    self.peak_prices[symbol] = min(self.peak_prices[symbol], mid)
                    stop = self.peak_prices[symbol] + ATR_STOP_MULT * atr
                    if mid > stop:
                        target = 0.0

                # RSI mean reversion exit
                if current_pos > 0 and rsi > RSI_OVERBOUGHT:
                    target = 0.0
                elif current_pos < 0 and rsi < RSI_OVERSOLD:
                    target = 0.0

                # Signal flip (reverse position)
                if current_pos > 0 and bearish and not in_cooldown:
                    target = -size
                elif current_pos < 0 and bullish and not in_cooldown:
                    target = size

            # Generate signal if position changed
            if abs(target - current_pos) > 10.0:  # ₹10 minimum change
                signals.append(Signal(symbol=symbol, target_position=target))
                
                # Track entry/exit for state management
                if target != 0 and current_pos == 0:
                    # Opening new position
                    self.entry_prices[symbol] = mid
                    self.peak_prices[symbol] = mid
                    self.atr_at_entry[symbol] = self._calc_atr(bd.history, ATR_LOOKBACK) or mid * 0.02
                elif target == 0:
                    # Closing position
                    self.entry_prices.pop(symbol, None)
                    self.peak_prices.pop(symbol, None)
                    self.atr_at_entry.pop(symbol, None)
                    self.exit_bar[symbol] = self.bar_count
                elif (target > 0 and current_pos < 0) or (target < 0 and current_pos > 0):
                    # Flipping position
                    self.entry_prices[symbol] = mid
                    self.peak_prices[symbol] = mid
                    self.atr_at_entry[symbol] = self._calc_atr(bd.history, ATR_LOOKBACK) or mid * 0.02

        return signals
