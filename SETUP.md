# Setup Instructions

## Installation

### 1. Navigate to project directory
```bash
cd auto-researchtrading-india
```

### 2. Create virtual environment (recommended)
```bash
# Using uv (fast)
uv venv

# Or using python
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
```

### 3. Install dependencies
```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

### 4. Verify installation
```bash
python -c "import numpy, pandas, yfinance; print('All dependencies installed!')"
```

## First Run

### 1. Download historical data
```bash
python prepare.py
```
This downloads 5 years of daily data for all 10 NSE stocks (~2-3 minutes).

### 2. Run baseline backtest
```bash
python backtest.py
```

Expected output:
```
Loaded ~1500 bars across 10 symbols
Symbols: ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', ...]

---
score:              X.XXXXXX
sharpe:             X.XXXXXX
total_return_pct:   XX.XXXXXX
max_drawdown_pct:   X.XXXXXX
num_trades:         XXX
win_rate_pct:       XX.XXXXXX
profit_factor:      X.XXXXXX
annual_turnover:    XXXX.XX
backtest_seconds:   X.X
total_seconds:      X.X
```

### 3. Log your first experiment
```bash
python experiment_runner.py --exp baseline --desc "Initial momentum strategy"
```

## Using with Claude Code

### Setup Claude Code with Kimi API
```powershell
# Set environment variables (Windows PowerShell)
$env:ENABLE_TOOL_SEARCH="false"
$env:ANTHROPIC_BASE_URL="https://api.kimi.com/coding/"
$env:ANTHROPIC_API_KEY="sk-kimi-YOUR_API_KEY_HERE"

# Start Claude Code
claude
```

### Inside Claude Code
```
# Check status
/status

# Run autonomous research
/autoresearch

# Or manually
# Read the current strategy
Read strategy.py

# Make changes
Edit strategy.py ...

# Run backtest
python backtest.py
```

## Manual Experiment Workflow

```bash
# 1. Make changes to strategy.py
# 2. Run backtest
python backtest.py

# 3. Log experiment
python experiment_runner.py --exp exp1 --desc "Increased RSI to 14"

# 4. Check results
python experiment_runner.py --list

# 5. Keep or revert changes based on score
# Good score -> git commit
# Bad score -> git checkout strategy.py
```

## Tips

- Each experiment should test ONE change
- Wait for data download to complete before running backtests
- Use experiment_runner.py to track all changes
- Check experiments.json for full history
- Best score is automatically tracked

## Troubleshooting

### Import errors
```bash
pip install numpy pandas scipy yfinance pytz pyarrow requests
```

### No data error
```bash
# Clear cache and re-download
rm -rf ~/.cache/autotrader-india
python prepare.py
```

### Slow performance
- Reduce LOOKBACK_BARS in prepare.py (default: 500)
- Test with fewer symbols first
