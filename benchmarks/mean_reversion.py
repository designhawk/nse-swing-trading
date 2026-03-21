"""Mean reversion benchmark - buy oversold, sell overbought."""
import numpy as np
from prepare import Signal, PortfolioState, BarData

def calc_rsi(closes, period=14):
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
        self.rsi_period = 14
        self.oversold = 30
        self.overbought = 70
        
    def on_bar(self, bar_data, portfolio):
        signals = []
        equity = portfolio.equity if portfolio.equity > 0 else portfolio.cash
        
        for symbol, bd in bar_data.items():
            if len(bd.history) < self.rsi_period + 1:
                continue
                
            closes = bd.history["close"].values
            rsi = calc_rsi(closes, self.rsi_period)
            
            current_pos = portfolio.positions.get(symbol, 0.0)
            target = current_pos
            
            if rsi < self.oversold and current_pos <= 0:
                target = equity * 0.1
            elif rsi > self.overbought and current_pos >= 0:
                target = -equity * 0.1
            elif self.oversold <= rsi <= self.overbought:
                target = 0.0
            
            if abs(target - current_pos) > 10:
                signals.append(Signal(symbol=symbol, target_position=target))
                
        return signals
