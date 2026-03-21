"""
Auto-research script - automated strategy optimization loop.
This simulates the /autoresearch Claude Code skill functionality.

Usage:
    python auto_research.py                    # Run indefinitely until Ctrl+C
    python auto_research.py --max 50          # Run max 50 experiments
    python auto_research.py --budget 3600     # Run for 1 hour (3600 seconds)
"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime
from pathlib import Path
import shutil

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from prepare import load_data, run_backtest, compute_score, INITIAL_CAPITAL
from strategy import Strategy

RESEARCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research")
EXPERIMENTS_FILE = os.path.join(RESEARCH_DIR, "experiments.json")
BEST_STRATEGY_FILE = os.path.join(RESEARCH_DIR, "strategy_best.py")
BACKUP_DIR = os.path.join(RESEARCH_DIR, "strategy_backups")

# Strategy modification ideas
PARAMETER_MODIFICATIONS = [
    # RSI variations
    ("RSI_PERIOD", [6, 10, 12, 14]),
    ("RSI_BULL", [45, 55, 60]),
    ("RSI_BEAR", [40, 45, 55]),
    ("RSI_OVERBOUGHT", [65, 70, 75]),
    ("RSI_OVERSOLD", [25, 30, 35]),
    
    # Lookback periods
    ("SHORT_WINDOW", [3, 4, 5, 6, 7]),
    ("MED_WINDOW", [8, 10, 12, 15]),
    ("MED2_WINDOW", [15, 20, 25]),
    ("LONG_WINDOW", [25, 30, 40, 50]),
    
    # EMA periods
    ("EMA_FAST", [5, 7, 9, 12]),
    ("EMA_SLOW", [20, 26, 30]),
    
    # MACD
    ("MACD_FAST", [12, 14, 16]),
    ("MACD_SLOW", [21, 23, 26]),
    ("MACD_SIGNAL", [7, 9, 12]),
    
    # Position sizing
    ("BASE_POSITION_PCT", [0.08, 0.10, 0.12, 0.15]),
    ("ATR_STOP_MULT", [4.0, 5.0, 5.5, 6.0, 7.0]),
    ("COOLDOWN_BARS", [1, 2, 3, 5]),
    ("MIN_VOTES", [3, 4, 5]),
    
    # Momentum
    ("BASE_THRESHOLD", [0.008, 0.010, 0.012, 0.015, 0.018]),
    ("VOL_LOOKBACK", [15, 20, 30]),
    ("TARGET_VOL", [0.012, 0.015, 0.018, 0.020]),
]

def load_experiments():
    """Load experiment history."""
    if os.path.exists(EXPERIMENTS_FILE):
        with open(EXPERIMENTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_experiments(experiments):
    """Save experiment history."""
    with open(EXPERIMENTS_FILE, 'w') as f:
        json.dump(experiments, f, indent=2)

def get_best_score():
    """Get the best score so far."""
    experiments = load_experiments()
    if not experiments:
        return -float('inf')
    return max(e['score'] for e in experiments)

def backup_strategy(exp_num):
    """Backup current strategy."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_file = os.path.join(BACKUP_DIR, f"strategy_exp{exp_num}.py")
    shutil.copy("strategy.py", backup_file)
    return backup_file

def modify_strategy():
    """
    Automatically modify strategy.py with a random change.
    Returns the modification made.
    """
    # Read current strategy
    with open("strategy.py", 'r') as f:
        content = f.read()
    
    # Pick a random modification
    param_name, values = random.choice(PARAMETER_MODIFICATIONS)
    new_value = random.choice(values)
    
    # Find and replace the parameter
    import re
    
    # Pattern to match parameter definition (e.g., RSI_PERIOD = 8)
    pattern = rf"({param_name}\s*=\s*)(\d+\.?\d*)"
    
    match = re.search(pattern, content)
    if match:
        old_value = match.group(2)
        old_line = match.group(0)
        new_line = f"{match.group(1)}{new_value}"
        
        content = content.replace(old_line, new_line, 1)
        
        # Write back
        with open("strategy.py", 'w') as f:
            f.write(content)
        
        return f"Changed {param_name} from {old_value} to {new_value}"
    else:
        return f"Could not find {param_name} to modify"

def run_single_experiment(exp_num):
    """Run a single experiment."""
    print(f"\n{'='*70}")
    print(f"EXPERIMENT {exp_num}")
    print(f"{'='*70}")
    
    # Backup current strategy
    backup_file = backup_strategy(exp_num)
    
    # Modify strategy
    modification = modify_strategy()
    print(f"Modification: {modification}")
    print()
    
    # Load data
    data = load_data("val")
    if not data:
        print("ERROR: No data loaded. Run 'python prepare.py' first.")
        return None
    
    # Run backtest
    t_start = time.time()
    
    try:
        # Force reimport of strategy module
        if 'strategy' in sys.modules:
            del sys.modules['strategy']
        
        # Import fresh strategy
        spec = __import__('importlib.util').util.spec_from_file_location("strategy", "strategy.py")
        strategy_module = __import__('importlib.util').util.module_from_spec(spec)
        spec.loader.exec_module(strategy_module)
        Strategy = strategy_module.Strategy
        
        strategy = Strategy()
        result = run_backtest(strategy, data)
        score = compute_score(result)
        
    except Exception as e:
        print(f"ERROR running backtest: {e}")
        # Restore backup
        shutil.copy(backup_file, "strategy.py")
        return None
    
    t_end = time.time()
    
    # Display results
    print(f"Results:")
    print(f"  Score:            {score:.6f}")
    print(f"  Sharpe:           {result.sharpe:.6f}")
    print(f"  Total Return:     {result.total_return_pct:.2f}%")
    print(f"  Max Drawdown:     {result.max_drawdown_pct:.2f}%")
    print(f"  Trades:           {result.num_trades}")
    print(f"  Win Rate:         {result.win_rate_pct:.2f}%")
    print(f"  Time:             {t_end - t_start:.1f}s")
    
    # Check if improvement
    best_score = get_best_score()
    
    if score > best_score:
        print(f"\n[IMPROVEMENT] {score:.6f} > {best_score:.6f}")
        
        # Save as best strategy
        shutil.copy("strategy.py", BEST_STRATEGY_FILE)
        
        # Log experiment
        experiment = {
            'name': f'exp{exp_num}',
            'description': modification,
            'timestamp': datetime.now().isoformat(),
            'score': score,
            'sharpe': result.sharpe,
            'total_return_pct': result.total_return_pct,
            'max_drawdown_pct': result.max_drawdown_pct,
            'num_trades': result.num_trades,
            'win_rate_pct': result.win_rate_pct,
            'profit_factor': result.profit_factor,
            'annual_turnover': result.annual_turnover,
            'kept': True
        }
        
        experiments = load_experiments()
        experiments.append(experiment)
        save_experiments(experiments)
        
        return score
        
    else:
        print(f"\n[NO IMPROVEMENT] {score:.6f} <= {best_score:.6f}")
        print("Reverting changes...")
        
        # Restore backup
        shutil.copy(backup_file, "strategy.py")
        
        # Log experiment
        experiment = {
            'name': f'exp{exp_num}',
            'description': modification,
            'timestamp': datetime.now().isoformat(),
            'score': score,
            'sharpe': result.sharpe,
            'total_return_pct': result.total_return_pct,
            'max_drawdown_pct': result.max_drawdown_pct,
            'num_trades': result.num_trades,
            'win_rate_pct': result.win_rate_pct,
            'profit_factor': result.profit_factor,
            'annual_turnover': result.annual_turnover,
            'kept': False
        }
        
        experiments = load_experiments()
        experiments.append(experiment)
        save_experiments(experiments)
        
        return None

def run_autoresearch(max_experiments=None, time_budget=None):
    """
    Run automated research loop.
    
    Args:
        max_experiments: Maximum number of experiments to run
        time_budget: Maximum time in seconds to run
    """
    print("\n" + "="*70)
    print("AUTO-RESEARCH FOR INDIAN NSE STOCKS")
    print("="*70)
    print("\nThis will automatically:")
    print("1. Modify strategy parameters")
    print("2. Run backtest")
    print("3. Keep improvements, revert failures")
    print("4. Repeat until stopped")
    print("\nPress Ctrl+C to stop at any time")
    print("="*70 + "\n")
    
    # Get starting point
    experiments = load_experiments()
    start_exp = len(experiments) + 1
    start_time = time.time()
    
    if experiments:
        best = max(experiments, key=lambda x: x['score'])
        print(f"Starting from {len(experiments)} previous experiments")
        print(f"Best so far: {best['name']} (Score: {best['score']:.6f})\n")
    else:
        print("No previous experiments found")
        print("Make sure to run 'python backtest.py' first to establish baseline\n")
    
    exp_num = start_exp
    improvements = 0
    
    try:
        while True:
            # Check max experiments
            if max_experiments and (exp_num - start_exp) >= max_experiments:
                print(f"\nReached max experiments ({max_experiments})")
                break
            
            # Check time budget
            if time_budget and (time.time() - start_time) >= time_budget:
                print(f"\nReached time budget ({time_budget}s)")
                break
            
            # Run experiment
            result = run_single_experiment(exp_num)
            if result:
                improvements += 1
            
            exp_num += 1
            
            # Small delay between experiments
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    
    # Summary
    print("\n" + "="*70)
    print("AUTO-RESEARCH COMPLETE")
    print("="*70)
    print(f"Experiments run: {exp_num - start_exp}")
    print(f"Improvements: {improvements}")
    
    if os.path.exists(BEST_STRATEGY_FILE):
        print(f"\nBest strategy saved to: {BEST_STRATEGY_FILE}")
        print("To use it: cp strategy_best.py strategy.py")
    
    experiments = load_experiments()
    if experiments:
        best = max(experiments, key=lambda x: x['score'])
        print(f"\nOverall best: {best['name']}")
        print(f"  Score: {best['score']:.6f}")
        print(f"  Sharpe: {best['sharpe']:.6f}")
        print(f"  Return: {best['total_return_pct']:.2f}%")
        print(f"  Drawdown: {best['max_drawdown_pct']:.2f}%")

def main():
    parser = argparse.ArgumentParser(description="Auto-research for Indian NSE trading strategies")
    parser.add_argument("--max", type=int, help="Maximum number of experiments to run")
    parser.add_argument("--budget", type=int, help="Time budget in seconds")
    parser.add_argument("--restore", action="store_true", help="Restore best strategy")
    
    args = parser.parse_args()
    
    if args.restore:
        if os.path.exists(BEST_STRATEGY_FILE):
            shutil.copy(BEST_STRATEGY_FILE, "strategy.py")
            print("Restored best strategy from strategy_best.py")
        else:
            print("No best strategy found. Run auto_research.py first.")
        return
    
    run_autoresearch(max_experiments=args.max, time_budget=args.budget)

if __name__ == "__main__":
    main()
