"""EMA crossover benchmark - classic trend following."""
import numpy as np
from prepare import Signal, PortfolioState, BarData

def ema(values, span):
    alpha = 2.0 / (span + 1)
    result = np.empty_like(values, dtype=float)
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    return result

class Strategy:
    def __init__(self):
        self.fast_period = 12
        self.slow_period = 26
        
    def on_bar(self, bar_data, portfolio):
        signals = []
        equity = portfolio.equity if portfolio.equity > 0 else portfolio.cash
        
        for symbol, bd in bar_data.items():
            if len(bd.history) < self.slow_period + 5:
                continue
                
            closes = bd.history["close"].values
            fast_ema = ema(closes, self.fast_period)
            slow_ema = ema(closes, self.slow_period)
            
            current_pos = portfolio.positions.get(symbol, 0.0)
            target = 0.0
            
            if fast_ema[-1] > slow_ema[-1]:
                target = equity * 0.1
            elif fast_ema[-1] < slow_ema[-1]:
                target = -equity * 0.1
            
            if abs(target - current_pos) > 10:
                signals.append(Signal(symbol=symbol, target_position=target))
                
        return signals
