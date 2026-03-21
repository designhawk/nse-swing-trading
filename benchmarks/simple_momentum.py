"""Simple momentum benchmark - buy when price goes up, sell when down."""
import numpy as np
from prepare import Signal, PortfolioState, BarData

class Strategy:
    def __init__(self):
        self.lookback = 10
        self.threshold = 0.02
        
    def on_bar(self, bar_data, portfolio):
        signals = []
        equity = portfolio.equity if portfolio.equity > 0 else portfolio.cash
        
        for symbol, bd in bar_data.items():
            if len(bd.history) < self.lookback + 1:
                continue
                
            closes = bd.history["close"].values
            ret = (closes[-1] - closes[-self.lookback]) / closes[-self.lookback]
            
            current_pos = portfolio.positions.get(symbol, 0.0)
            target = 0.0
            
            if ret > self.threshold:
                target = equity * 0.1  # 10% position
            elif ret < -self.threshold:
                target = -equity * 0.1
            
            if abs(target - current_pos) > 10:
                signals.append(Signal(symbol=symbol, target_position=target))
                
        return signals
