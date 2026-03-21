# Auto-Research Trading - India Edition

Autonomous trading strategy research framework adapted for Indian NSE stocks (large-cap leaders).

## Features

- **10 Large-cap NSE Stocks**: RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, SBIN, BHARTIARTL, KOTAKBANK
- **Daily Timeframe**: Optimized for swing/positional trading
- **5 Years Historical Data**: 2019-2024 for robust backtesting
- **₹10 Lakhs Starting Capital**: Realistic for Indian retail traders
- **Multi-signal Ensemble Strategy**: Momentum, EMA, RSI, MACD, Bollinger Bands
- **Built-in Experiment Tracker**: Log and compare strategy variations

## Quick Start

### 1. Install Dependencies

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | bash  # macOS/Linux
# Or download from https://github.com/astral-sh/uv/releases for Windows

# Install dependencies
uv pip install -e .
```

Or with pip:
```bash
pip install -e .
```

### 2. Download Historical Data

```bash
python prepare.py
```

This downloads 5 years of daily OHLCV data from Yahoo Finance for all 10 stocks.

### 3. Run Backtest

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
...
```

### 4. Run Experiments

```bash
# Run with auto-generated experiment name
python experiment_runner.py

# Run with specific name and description
python experiment_runner.py --exp exp1 --desc "Increased RSI period to 14"

# View all experiments
python experiment_runner.py --list

# View best experiment
python experiment_runner.py --best
```

## Strategy Development

### Rules

1. **Only edit `strategy.py`** - This is the single mutable file
2. **Do not modify** `prepare.py`, `backtest.py`, or other core files
3. **No new dependencies** - Only use: numpy, pandas, scipy, yfinance, pytz
4. **Time budget** - 120 seconds per backtest

### Manual Experiment Loop

```bash
# 1. Create a git branch for your experiment
git checkout -b experiment/my-idea

# 2. Edit strategy.py with your idea
#    - Change parameters, add signals, modify entry/exit logic

# 3. Run the backtest
python backtest.py

# 4. Log the experiment
python experiment_runner.py --exp exp1 --desc "Your changes here"

# 5. If score improved -> commit
#    If score got worse -> revert
```

### Using Autoresearch (No /autoresearch skill needed)

We provide **two options** for autonomous research:

#### Option 1: Python Script (Cross-platform, Recommended)

```bash
# Run indefinitely (press Ctrl+C to stop)
python auto_research.py

# Run max 50 experiments
python auto_research.py --max 50

# Run for 1 hour
python auto_research.py --budget 3600

# Restore best strategy later
python auto_research.py --restore
```

**What it does:**
1. ✅ Automatically modifies `strategy.py` parameters
2. ✅ Runs backtest
3. ✅ Keeps if score improves
4. ✅ Reverts if worse
5. ✅ Saves best to `strategy_best.py`
6. ✅ Logs to `experiments.json`

#### Option 2: Bash Script (Unix/Linux/macOS/Git Bash)

```bash
# Make executable and run
chmod +x autoresearch.sh
./autoresearch.sh
```

**Requirements:** Git Bash (Windows), bc command

#### Option 3: Interactive with Claude Code

If you prefer using Claude Code interactively:

```bash
# Start Claude Code
claude
```

Then inside Claude Code:
```
Read strategy.py
Read results.tsv

# Ask Claude to suggest and implement a modification
"Please analyze the current strategy and suggest one specific parameter change to improve the Sharpe ratio. Implement it and run a backtest."

# After Claude edits and runs backtest, check results
python experiment_runner.py --exp exp1 --desc "Modification suggested by Claude"
```

## Strategy Architecture

### Current Baseline Strategy

**Multi-signal ensemble with majority voting:**

| Signal | Bull Condition | Bear Condition |
|--------|----------------|----------------|
| Momentum | 10-day return > threshold | 10-day return < -threshold |
| Very-short momentum | 5-day return > threshold×0.7 | 5-day return < -threshold×0.7 |
| EMA crossover | EMA(7) > EMA(26) | EMA(7) < EMA(26) |
| RSI(8) | RSI > 50 | RSI < 50 |
| MACD(14,23,9) | MACD histogram > 0 | MACD histogram < 0 |
| BB compression | BB width < 85th percentile | BB width < 85th percentile |

**Entry:** 4 out of 6 signals must agree

**Exit conditions (priority order):**
1. **ATR trailing stop** - 5.5x ATR from peak/trough
2. **RSI mean-reversion** - Exit longs at RSI > 69, exit shorts at RSI < 31
3. **Signal flip** - Reverse when opposing ensemble fires

### Key Parameters

```python
BASE_POSITION_PCT = 0.10    # 10% per stock (max 100% invested)
COOLDOWN_BARS = 2           # Wait 2 days after exit
RSI_PERIOD = 8              # Fast RSI for daily data
ATR_STOP_MULT = 5.5         # Wide stop to let winners run
MIN_VOTES = 4               # 4 of 6 signals needed
```

## Data

### Symbols
- **RELIANCE.NS** - Reliance Industries (Energy, Telecom, Retail)
- **TCS.NS** - Tata Consultancy Services (IT)
- **HDFCBANK.NS** - HDFC Bank (Banking)
- **INFY.NS** - Infosys (IT)
- **ICICIBANK.NS** - ICICI Bank (Banking)
- **HINDUNILVR.NS** - Hindustan Unilever (FMCG)
- **ITC.NS** - ITC Limited (FMCG, Hotels, Paper)
- **SBIN.NS** - State Bank of India (Banking)
- **BHARTIARTL.NS** - Bharti Airtel (Telecom)
- **KOTAKBANK.NS** - Kotak Mahindra Bank (Banking)

### Date Ranges
- **Training**: 2019-01-01 to 2023-01-01 (4 years)
- **Validation**: 2023-01-01 to 2024-12-31 (2 years)
- **Test**: 2025-01-01 onwards (out-of-sample)

### Data Source
Yahoo Finance (via yfinance library) - Free, reliable daily data for NSE stocks.

## Scoring

```
score = sharpe × √(min(trades/50, 1.0)) − drawdown_penalty − turnover_penalty

Where:
- sharpe: Annualized Sharpe ratio (252 trading days)
- drawdown_penalty: max(0, max_drawdown_pct − 15%) × 0.05
- turnover_penalty: max(0, annual_turnover/capital − 500) × 0.001

Hard cutoffs (→ score = -999):
- Fewer than 10 trades
- Max drawdown > 50%
- Lost > 50% of capital
```

## Project Structure

```
auto-researchtrading-india/
├── prepare.py              # Data download & backtest engine (FIXED)
├── backtest.py             # Entry point for backtesting (FIXED)
├── strategy.py             # YOUR STRATEGY - edit this file
├── experiment_runner.py    # Experiment tracking & logging
├── auto_research.py        # Autonomous research loop (Python)
├── autoresearch.sh         # Autonomous research loop (Bash)
├── results.tsv             # Experiment results log
├── pyproject.toml          # Dependencies
├── README.md               # This file
├── SETUP.md                # Setup instructions
├── experiments.json        # Auto-generated experiment log
├── strategy_best.py        # Best strategy (auto-saved)
└── .cache/
    └── autotrader-india/   # Downloaded data cache
        └── data/
            ├── RELIANCE_NS_1d.parquet
            ├── TCS_NS_1d.parquet
            └── ...
```

## Tips for Strategy Development

### 1. Start Simple
The baseline strategy is already decent. Make small, incremental changes.

### 2. Test One Change at a Time
Don't change multiple parameters simultaneously - you won't know what worked.

### 3. Watch for Overfitting
If Sharpe is very high (>3) on validation, you may be overfitting.

### 4. Consider Market Regimes
Indian markets behave differently in:
- Bull markets (strong momentum)
- Bear markets (mean reversion)
- Sideways markets (range-bound)

### 5. Sector Rotation
Different sectors lead at different times. Consider sector-based filters.

## Common Modifications to Try

1. **Adjust RSI period**: Try 6, 10, 14 instead of 8
2. **Change momentum lookback**: Try 5, 15, 20 days instead of 10
3. **Modify position sizing**: Equal weight vs volatility-adjusted
4. **Add sector filters**: Reduce positions when sector is weak
5. **Market regime detection**: Use NIFTY 50 trend as filter
6. **Add fundamental filters**: Skip stocks with high P/E

## Troubleshooting

### "No data loaded" error
Run `python prepare.py` first to download historical data.

### Import errors
Install dependencies: `pip install -e .` or `uv pip install -e .`

### Slow backtests
- Reduce LOOKBACK_BARS in prepare.py (default: 500)
- Use fewer symbols for testing

### Yahoo Finance rate limits
The downloader has built-in delays (0.5s between requests). If still rate-limited, wait a few minutes and retry.

## License

MIT License - See original crypto project at https://github.com/Nunchi-trade/auto-researchtrading

## Disclaimer

This is a research framework for educational purposes. Past performance does not guarantee future results. Always test strategies thoroughly before deploying real capital.
