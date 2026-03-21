"""
Experiment runner for manual strategy development.
Logs experiments and tracks results.

Usage:
    python experiment_runner.py --exp exp1 --desc "Increased RSI period to 14"
    python experiment_runner.py --list              # Show all experiments
    python experiment_runner.py --best              # Show best experiment
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from prepare import load_data, run_backtest, compute_score, INITIAL_CAPITAL
from strategy import Strategy

EXPERIMENTS_FILE = os.path.join(ROOT, "research", "experiments.json")


def load_experiments():
    """Load experiment history from file."""
    if os.path.exists(EXPERIMENTS_FILE):
        with open(EXPERIMENTS_FILE, 'r') as f:
            return json.load(f)
    return []


def save_experiments(experiments):
    """Save experiment history to file."""
    with open(EXPERIMENTS_FILE, 'w') as f:
        json.dump(experiments, f, indent=2)


def run_experiment(exp_name: str, description: str):
    """Run a backtest and log the result."""
    print(f"\n{'='*60}")
    print(f"Running Experiment: {exp_name}")
    print(f"Description: {description}")
    print(f"{'='*60}\n")
    
    # Load data
    data = load_data("val")
    if not data:
        print("Error: No data loaded. Run 'python prepare.py' first.")
        return
    
    # Run backtest
    t_start = time.time()
    strategy = Strategy()
    result = run_backtest(strategy, data)
    t_end = time.time()
    
    score = compute_score(result)
    
    # Display results
    print(f"\n{'-'*60}")
    print("RESULTS:")
    print(f"{'-'*60}")
    print(f"Score:              {score:.6f}")
    print(f"Sharpe:             {result.sharpe:.6f}")
    print(f"Total Return:       {result.total_return_pct:.2f}%")
    print(f"Max Drawdown:       {result.max_drawdown_pct:.2f}%")
    print(f"Number of Trades:   {result.num_trades}")
    print(f"Win Rate:           {result.win_rate_pct:.2f}%")
    print(f"Profit Factor:      {result.profit_factor:.2f}")
    print(f"Annual Turnover:    {result.annual_turnover:.2f}")
    print(f"Backtest Time:      {result.backtest_seconds:.1f}s")
    print(f"{'-'*60}\n")
    
    # Load existing experiments
    experiments = load_experiments()
    
    # Check if experiment name already exists
    existing = next((e for e in experiments if e['name'] == exp_name), None)
    if existing:
        print(f"Warning: Experiment '{exp_name}' already exists. Overwriting...")
        experiments.remove(existing)
    
    # Create experiment record
    experiment = {
        'name': exp_name,
        'description': description,
        'timestamp': datetime.now().isoformat(),
        'score': score,
        'sharpe': result.sharpe,
        'total_return_pct': result.total_return_pct,
        'max_drawdown_pct': result.max_drawdown_pct,
        'num_trades': result.num_trades,
        'win_rate_pct': result.win_rate_pct,
        'profit_factor': result.profit_factor,
        'annual_turnover': result.annual_turnover,
        'backtest_seconds': result.backtest_seconds
    }
    
    experiments.append(experiment)
    save_experiments(experiments)
    
    print(f"[OK] Experiment '{exp_name}' saved to {EXPERIMENTS_FILE}")
    
    # Find best experiment
    best = max(experiments, key=lambda x: x['score'])
    print(f"\nBest Experiment: {best['name']} (Score: {best['score']:.6f})")
    
    return experiment


def list_experiments():
    """Display all experiments sorted by score."""
    experiments = load_experiments()
    
    if not experiments:
        print("No experiments found. Run an experiment first.")
        return
    
    # Sort by score descending
    experiments.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n{'='*100}")
    print(f"{'Rank':<6}{'Name':<20}{'Score':<12}{'Sharpe':<10}{'Return':<10}{'Drawdown':<10}{'Trades':<8}{'Description':<20}")
    print(f"{'='*100}")
    
    for i, exp in enumerate(experiments, 1):
        print(f"{i:<6}{exp['name']:<20}{exp['score']:<12.6f}{exp['sharpe']:<10.6f}"
              f"{exp['total_return_pct']:<10.2f}{exp['max_drawdown_pct']:<10.2f}"
              f"{exp['num_trades']:<8}{exp['description'][:20]:<20}")
    
    print(f"{'='*100}\n")
    print(f"Total experiments: {len(experiments)}")
    
    # Show best
    best = experiments[0]
    print(f"\nBest: {best['name']} | Score: {best['score']:.6f} | Sharpe: {best['sharpe']:.6f}")


def show_best():
    """Show the best experiment details."""
    experiments = load_experiments()
    
    if not experiments:
        print("No experiments found.")
        return
    
    best = max(experiments, key=lambda x: x['score'])
    
    print(f"\n{'='*60}")
    print(f"BEST EXPERIMENT: {best['name']}")
    print(f"{'='*60}")
    print(f"Description:        {best['description']}")
    print(f"Timestamp:          {best['timestamp']}")
    print(f"Score:              {best['score']:.6f}")
    print(f"Sharpe:             {best['sharpe']:.6f}")
    print(f"Total Return:       {best['total_return_pct']:.2f}%")
    print(f"Max Drawdown:       {best['max_drawdown_pct']:.2f}%")
    print(f"Number of Trades:   {best['num_trades']}")
    print(f"Win Rate:           {best['win_rate_pct']:.2f}%")
    print(f"Profit Factor:      {best['profit_factor']:.2f}")
    print(f"Annual Turnover:    {best['annual_turnover']:.2f}")
    print(f"{'='*60}\n")


def clear_experiments():
    """Clear all experiment history."""
    if os.path.exists(EXPERIMENTS_FILE):
        os.remove(EXPERIMENTS_FILE)
        print("Experiment history cleared.")
    else:
        print("No experiment history to clear.")


def main():
    parser = argparse.ArgumentParser(description="Experiment runner for Indian NSE trading strategies")
    parser.add_argument("--exp", type=str, help="Experiment name (e.g., exp1)")
    parser.add_argument("--desc", type=str, default="", help="Experiment description")
    parser.add_argument("--list", action="store_true", help="List all experiments")
    parser.add_argument("--best", action="store_true", help="Show best experiment")
    parser.add_argument("--clear", action="store_true", help="Clear experiment history")
    
    args = parser.parse_args()
    
    if args.clear:
        clear_experiments()
    elif args.list:
        list_experiments()
    elif args.best:
        show_best()
    elif args.exp:
        run_experiment(args.exp, args.desc)
    else:
        # Run default experiment
        exp_name = f"exp{len(load_experiments()) + 1}"
        run_experiment(exp_name, args.desc or "Baseline strategy")


if __name__ == "__main__":
    main()
