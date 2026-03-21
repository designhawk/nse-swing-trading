"""
Run backtest for Indian NSE stocks. Usage: python backtest.py
Imports strategy from strategy.py, runs on validation data, prints metrics.
This file is fixed — do not modify.
"""

import time
import signal as sig

from prepare import load_data, run_backtest, compute_score, TIME_BUDGET

# Timeout guard
def timeout_handler(signum, frame):
    print("TIMEOUT: backtest exceeded time budget")
    exit(1)

# Note: signal.SIGALRM is not available on Windows, so we use a different approach
try:
    sig.signal(sig.SIGALRM, timeout_handler)
    sig.alarm(TIME_BUDGET + 30)  # 30s grace for startup
except AttributeError:
    # Windows doesn't have SIGALRM, we'll use a simpler timeout mechanism
    pass

t_start = time.time()

from strategy import Strategy

strategy = Strategy()
data = load_data("val")

if not data:
    print("\nError: No data loaded!")
    print("Please run 'python prepare.py' first to download historical data.")
    exit(1)

print(f"Loaded {sum(len(df) for df in data.values())} bars across {len(data)} symbols")
print(f"Symbols: {list(data.keys())}")
print()

result = run_backtest(strategy, data)
score = compute_score(result)

t_end = time.time()

print("---")
print(f"score:              {score:.6f}")
print(f"sharpe:             {result.sharpe:.6f}")
print(f"total_return_pct:   {result.total_return_pct:.6f}")
print(f"max_drawdown_pct:   {result.max_drawdown_pct:.6f}")
print(f"num_trades:         {result.num_trades}")
print(f"win_rate_pct:       {result.win_rate_pct:.6f}")
print(f"profit_factor:      {result.profit_factor:.6f}")
print(f"annual_turnover:    {result.annual_turnover:.2f}")
print(f"backtest_seconds:   {result.backtest_seconds:.1f}")
print(f"total_seconds:      {t_end - t_start:.1f}")
