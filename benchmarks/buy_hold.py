"""Buy and hold benchmark - passive investment."""
from prepare import Signal, PortfolioState, BarData

class Strategy:
    def __init__(self):
        self.initialized = False
        
    def on_bar(self, bar_data, portfolio):
        if self.initialized:
            return []
            
        signals = []
        equity = portfolio.equity if portfolio.equity > 0 else portfolio.cash
        
        # Buy equal weight in all available symbols
        n_symbols = len(bar_data)
        if n_symbols == 0:
            return []
            
        position_size = equity / n_symbols
        
        for symbol in bar_data.keys():
            signals.append(Signal(symbol=symbol, target_position=position_size))
        
        self.initialized = True
        return signals
