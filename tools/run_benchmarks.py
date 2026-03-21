"""Run all benchmark strategies and compare to current strategy.py.

Usage:
    python tools/run_benchmarks.py
"""
import sys
import os
import importlib
import time

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from prepare import load_data, run_backtest, compute_score

BENCHMARKS = [
    "benchmarks.simple_momentum",
    "benchmarks.mean_reversion",
    "benchmarks.ema_crossover",
    "benchmarks.buy_hold",
]

data = load_data("val")
if not data:
    print("Error: No data loaded. Run 'python prepare.py' first.")
    sys.exit(1)

print(f"Loaded {sum(len(df) for df in data.values())} bars across {len(data)} symbols\n")
print("=" * 100)
print("BENCHMARK LEADERBOARD (sorted by score, higher is better)")
print("=" * 100)
print(f"{'Rank':<6}{'Strategy':<25}{'Score':<12}{'Sharpe':<10}{'Return':<10}{'Max DD':<10}{'Trades':<8}{'Win Rate':<10}{'Time':<8}")
print("-" * 100)

results = []
for i, name in enumerate(BENCHMARKS, 1):
    short = name.split(".")[-1]
    try:
        mod = importlib.import_module(name)
        strategy = mod.Strategy()
        t0 = time.time()
        result = run_backtest(strategy, data)
        score = compute_score(result)
        dt = time.time() - t0
        results.append((short, score, result.sharpe, result.total_return_pct,
                        result.max_drawdown_pct, result.num_trades, result.win_rate_pct, dt))
        print(f"{i:<6}{short:<25}{score:<12.4f}{result.sharpe:<10.3f}"
              f"{result.total_return_pct:<10.2f}{result.max_drawdown_pct:<10.2f}"
              f"{result.num_trades:<8}{result.win_rate_pct:<10.1f}{dt:<8.1f}s")
    except Exception as e:
        print(f"{i:<6}{short:<25}CRASHED: {e}")
        results.append((short, -999, 0, 0, 0, 0, 0, 0))

print("=" * 100)
print("\n" + "=" * 100)
print("CURRENT STRATEGY (strategy.py)")
print("=" * 100)

try:
    from strategy import Strategy as CurrentStrategy
    strategy = CurrentStrategy()
    t0 = time.time()
    result = run_backtest(strategy, data)
    score = compute_score(result)
    dt = time.time() - t0
    print(f"{'Current':<25}{score:<12.4f}{result.sharpe:<10.3f}"
          f"{result.total_return_pct:<10.2f}{result.max_drawdown_pct:<10.2f}"
          f"{result.num_trades:<8}{result.win_rate_pct:<10.1f}{dt:<8.1f}s")
    best_bench = max(results, key=lambda x: x[1])
    if score > best_bench[1]:
        print(f"\n[OK] Current strategy beats best benchmark by {score - best_bench[1]:.4f}")
    else:
        print(f"\n[WARN] Current strategy is {best_bench[1] - score:.4f} below best benchmark ({best_bench[0]})")
except Exception as e:
    print(f"CRASHED: {e}")

print("=" * 100)
