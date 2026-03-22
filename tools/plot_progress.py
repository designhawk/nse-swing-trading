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
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9))

    # Separate data for legend
    x_kept = [i for i, k in zip(x, kept) if k]
    x_reverted = [i for i, k in zip(x, kept) if not k]
    scores_kept = [s for s, k in zip(scores, kept) if k]
    scores_reverted = [s for s, k in zip(scores, kept) if not k]
    sharpes_kept = [s for s, k in zip(sharpes, kept) if k]
    sharpes_reverted = [s for s, k in zip(sharpes, kept) if not k]

    # Plot 1: Score over time
    ax1.scatter(x_kept, scores_kept, c='green', alpha=0.6, s=50, label='Kept (improved)')
    ax1.scatter(x_reverted, scores_reverted, c='red', alpha=0.6, s=50, label='Reverted (worse)')
    ax1.plot(x, scores, 'b-', alpha=0.3, linewidth=1)
    ax1.axhline(y=max(scores), color='green', linestyle='--', alpha=0.5, linewidth=2, label=f'Best: {max(scores):.3f}')
    ax1.axhline(y=min(scores), color='red', linestyle=':', alpha=0.3, linewidth=1, label=f'Worst: {min(scores):.3f}')
    ax1.set_xlabel('Experiment #', fontsize=11)
    ax1.set_ylabel('Score (composite metric)', fontsize=11)
    ax1.set_title('Experiment Progress — Score Over Time', fontsize=13, fontweight='bold')
    ax1.legend(loc='best', framealpha=0.9)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Sharpe over time
    ax2.scatter(x_kept, sharpes_kept, c='green', alpha=0.6, s=50, label='Kept (improved)')
    ax2.scatter(x_reverted, sharpes_reverted, c='red', alpha=0.6, s=50, label='Reverted (worse)')
    ax2.plot(x, sharpes, 'b-', alpha=0.3, linewidth=1)
    ax2.axhline(y=max(sharpes), color='green', linestyle='--', alpha=0.5, linewidth=2, label=f'Best: {max(sharpes):.3f}')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.2, linewidth=1)
    ax2.set_xlabel('Experiment #', fontsize=11)
    ax2.set_ylabel('Sharpe Ratio (risk-adjusted return)', fontsize=11)
    ax2.set_title('Sharpe Ratio Over Time', fontsize=13, fontweight='bold')
    ax2.legend(loc='best', framealpha=0.9)
    ax2.grid(True, alpha=0.3)

    # Add summary text
    total = len(experiments)
    kept_count = sum(kept)
    improvement_rate = (kept_count / total * 100) if total > 0 else 0
    fig.text(0.5, 0.01, f'Total: {total} experiments | Kept: {kept_count} ({improvement_rate:.1f}%) | Reverted: {total - kept_count}',
             ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout(rect=[0, 0.03, 1, 1])
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
