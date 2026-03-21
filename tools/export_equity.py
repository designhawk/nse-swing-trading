"""Export equity curve to CSV for analysis and visualization."""
import os
import sys
import csv
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from prepare import load_data, run_backtest
from strategy import Strategy

print("Running backtest to export equity curve...")

data = load_data("val")
if not data:
    print("Error: No data loaded. Run 'python prepare.py' first.")
    exit(1)

strategy = Strategy()
result = run_backtest(strategy, data)

# Export to CSV in project root
output_file = os.path.join(ROOT, "equity_curve.csv")
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'equity', 'timestamp_ms'])

    # Get timestamps from data
    all_timestamps = []
    for symbol, df in data.items():
        all_timestamps.extend(df["timestamp"].tolist())
    timestamps = sorted(set(all_timestamps))

    equity_curve = result.equity_curve

    for i, equity in enumerate(equity_curve):
        if i < len(timestamps):
            ts_ms = timestamps[i]
            ts = datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
        else:
            ts = f"bar_{i}"
            ts_ms = i
        writer.writerow([ts, equity, ts_ms])

print(f"[OK] Equity curve exported to {output_file}")
print(f"   {len(equity_curve)} data points")
print(f"   Starting: Rs{equity_curve[0]:,.2f}")
print(f"   Final: Rs{equity_curve[-1]:,.2f}")
print(f"   Return: {((equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100):.2f}%")
