#!/usr/bin/env python3
"""Generate progress chart from experiments.json"""
import json
import matplotlib.pyplot as plt
from datetime import datetime
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERIMENTS_FILE = os.path.join(ROOT, "research", "experiments.json")
OUTPUT_FILE = os.path.join(ROOT, "research", "progress.png")


def load_experiments():
    if not os.path.exists(EXPERIMENTS_FILE):
        print(f"No {EXPERIMENTS_FILE} found")
        return []
    with open(EXPERIMENTS_FILE) as f:
        return json.load(f)


def plot_progress(experiments):
    if not experiments:
        print("No experiments to plot")
        return

    # Extract data
    x = list(range(1, len(experiments) + 1))
    scores = [e['score'] for e in experiments]
    sharpes = [e['sharpe'] for e in experiments]
    kept = [e.get('kept', False) for e in experiments]

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # Plot 1: Score over time
    colors = ['green' if k else 'red' for k in kept]
    ax1.scatter(x, scores, c=colors, alpha=0.6, s=50)
    ax1.plot(x, scores, 'b-', alpha=0.3, linewidth=1)
    ax1.axhline(y=max(scores), color='g', linestyle='--', alpha=0.5, label=f'Best: {max(scores):.3f}')
    ax1.set_xlabel('Experiment #')
    ax1.set_ylabel('Score')
    ax1.set_title('Experiment Progress — Score Over Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Sharpe over time
    ax2.scatter(x, sharpes, c=colors, alpha=0.6, s=50)
    ax2.plot(x, sharpes, 'b-', alpha=0.3, linewidth=1)
    ax2.axhline(y=max(sharpes), color='g', linestyle='--', alpha=0.5, label=f'Best: {max(sharpes):.3f}')
    ax2.set_xlabel('Experiment #')
    ax2.set_ylabel('Sharpe Ratio')
    ax2.set_title('Sharpe Ratio Over Time')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Add summary text
    total = len(experiments)
    kept_count = sum(kept)
    fig.text(0.5, 0.02, f'Total: {total} | Kept: {kept_count} | Reverted: {total - kept_count}',
             ha='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight')
    print(f"Saved progress chart to {OUTPUT_FILE}")

    # Print summary
    print(f"\nSummary:")
    print(f"  Total experiments: {total}")
    print(f"  Improvements kept: {kept_count}")
    print(f"  Best score: {max(scores):.3f}")
    print(f"  Best Sharpe: {max(sharpes):.3f}")


if __name__ == "__main__":
    experiments = load_experiments()
    plot_progress(experiments)
