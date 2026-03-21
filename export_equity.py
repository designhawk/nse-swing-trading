"""Export equity curve to CSV for analysis and visualization."""
import csv
from datetime import datetime
from prepare import load_data, run_backtest
from strategy import Strategy

print("Running backtest to export equity curve...")

data = load_data("val")
if not data:
    print("Error: No data loaded. Run 'python prepare.py' first.")
    exit(1)

strategy = Strategy()
result = run_backtest(strategy, data)

# Export to CSV
output_file = "equity_curve.csv"
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'equity', 'timestamp_ms'])
    
    # Get timestamps from data
    all_timestamps = []
    for symbol, df in data.items():
        all_timestamps.extend(df["timestamp"].tolist())
    timestamps = sorted(set(all_timestamps))
    
    # Pad equity curve if needed (it has len(timestamps)+1 entries starting with initial capital)
    equity_curve = result.equity_curve
    
    for i, equity in enumerate(equity_curve):
        # Use index to approximate timestamp if needed
        if i < len(timestamps):
            ts_ms = timestamps[i]
            ts = datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
        else:
            ts = f"bar_{i}"
            ts_ms = i
        writer.writerow([ts, equity, ts_ms])

print(f"✅ Equity curve exported to {output_file}")
print(f"   {len(equity_curve)} data points")
print(f"   Starting: ₹{equity_curve[0]:,.2f}")
print(f"   Final: ₹{equity_curve[-1]:,.2f}")
print(f"   Return: {((equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100):.2f}%")
