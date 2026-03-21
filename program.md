# autotrader-india

Autonomous trading strategy research on Indian NSE stocks.

## Context

This project adapts the auto-researchtrading pattern for Indian stock market strategy discovery.
**Your goal: discover novel daily-timeframe strategies that outperform the baseline.**

## Current Leaderboard

Run `python run_benchmarks.py` to see current standings.

Baseline momentum strategy from benchmarks scores ~2-3. **Your goal is to beat this.**

## Benchmark Strategies

These are reference implementations to compare against:

1. **simple_momentum** - Buy when price goes up, sell when down
2. **mean_reversion** - Buy oversold (RSI < 30), sell overbought (RSI > 70)
3. **ema_crossover** - Classic trend following with EMA(12/26)
4. **buy_hold** - Passive equal-weight buy and hold

## Setup

To set up a new experiment session:

1. **Ensure data is downloaded**: `python prepare.py`
2. **Check baseline**: `python run_benchmarks.py`
3. **Read the strategy**: `Read strategy.py`
4. **Verify git is initialized**: `git status`

## Experimentation

Each experiment runs a backtest on historical NSE data (10 large-cap stocks, daily bars, 2023-2024).

**What you CAN do:**
- Modify `strategy.py` — this is the only file you edit

**What you CANNOT do:**
- Modify `prepare.py`, `backtest.py`, or anything in `benchmarks/`
- Install new packages. Only numpy, pandas, scipy, yfinance, pytz, and standard library
- Look at test set data

**The goal: get the highest `score`.** Higher is better.

## Output format

```
python backtest.py
```

Shows:
- score: Risk-adjusted composite score
- sharpe: Annualized Sharpe ratio
- total_return_pct: Total percentage return
- max_drawdown_pct: Maximum peak-to-trough loss
- num_trades: Number of round-trip trades
- win_rate_pct: Percentage of winning trades
- profit_factor: Gross profit / gross loss

## Results TSV

The `results.tsv` file tracks experiments:

```
commit	score	sharpe	max_dd	return	trades	status	description
```

## The experiment loop

### Automated (Recommended - No /autoresearch skill needed!)

**IMPORTANT:** The `/autoresearch` skill from the original crypto repo requires special Claude Code setup and is NOT available here. 

Instead, use our Python script which provides the SAME functionality:

```bash
# Run 50 experiments automatically (no human intervention)
python auto_research.py --max 50

# Or run indefinitely until Ctrl+C
python auto_research.py

# Or run for a specific time
python auto_research.py --budget 3600  # 1 hour
```

**What it does:**
1. Reads current strategy and scores
2. Proposes and implements a modification to strategy.py
3. Runs `python backtest.py` and parses the score
4. Keeps the change if score improved, reverts if not
5. Repeats indefinitely until interrupted
6. Saves best strategy to `strategy_best.py`

This is EXACTLY what `/autoresearch` does, but as a standalone Python script!

### Manual with git

```bash
LOOP FOREVER:

1. Read strategy.py and results.tsv
2. Modify strategy.py with an experimental idea
3. git commit -m "expN: description"
4. python backtest.py
5. Parse score from output
6. Record in results.tsv
7. If score IMPROVED (higher than best so far): keep
8. If score equal or worse: git reset --hard HEAD~1
```

### Interactive with Claude Code

```bash
claude
```

Inside Claude:
```
Read strategy.py
Read results.tsv
Read STRATEGIES.md

"Analyze the current strategy and suggest one specific parameter change 
to improve the Sharpe ratio. Implement it and run a backtest."
```

## Strategy Research Directions

### Tier 1 — Most Likely to Improve Score
- **Adjust RSI period** — Try 6, 10, 14 instead of 8
- **Modify momentum lookback** — Try 5, 15, 20 days instead of 10
- **Change MIN_VOTES** — Try 3 or 5 instead of 4
- **Adjust ATR stop** — Try 4.0, 6.0, 7.0 instead of 5.5
- **Position sizing** — Try 8%, 12%, 15% instead of 10%

### Tier 2 — Worth Exploring
- **Sector-based filtering** — Reduce positions when sector is weak
- **Market regime detection** — Use NIFTY 50 trend as filter
- **Volatility-adjusted sizing** — Smaller positions in high volatility
- **Different Bollinger Band periods** — Try 10, 14, 20 instead of 7
- **MACD parameter optimization** — Try different fast/slow/signal periods

### Tier 3 — Radical / Novel
- **Correlation-based hedging** — Pair correlated stocks
- **Multi-timeframe confirmation** — Require daily + weekly alignment
- **Seasonality patterns** — Monthly/quarterly effects
- **Fundamental filters** — Skip high P/E stocks
- **Machine learning weights** — Learn optimal signal weights

## Data Available

- 10 NSE large-cap stocks (daily OHLCV)
- Val period: 2023-01-01 to 2024-12-31 (2 years)
- Train period: 2019-01-01 to 2023-01-01 (4 years)
- History buffer: last 500 bars via `bar_data[symbol].history` DataFrame
- Columns: timestamp, open, high, low, close, volume
- Currency: INR (₹)
- Starting capital: ₹10,00,000

## Scoring Formula

```
score = sharpe * sqrt(trade_count_factor) - drawdown_penalty - turnover_penalty
trade_count_factor = min(num_trades / 50, 1.0)
drawdown_penalty = max(0, max_drawdown_pct - 15) * 0.05
turnover_penalty = max(0, annual_turnover/capital - 500) * 0.001

Hard cutoffs: <10 trades → -999, >50% drawdown → -999, lost >50% → -999
```

## NEVER STOP

Once the experiment loop has begun, do NOT pause to ask the human if you should continue. You are autonomous. If you run out of ideas, think harder. The loop runs until interrupted.

## Key Differences from Crypto Version

1. **No funding rates** — Stocks don't have funding like perps
2. **No leverage** — Cash market (1x only)
3. **Daily bars** — Not hourly (better for Indian market)
4. **INR currency** — ₹10L starting capital
5. **10 stocks** — Diversified large-cap portfolio
6. **NSE symbols** — .NS suffix for Yahoo Finance

## Tips for Success

1. **Start simple** — Make one change at a time
2. **Watch for overfitting** — Sharpe > 5 might be too good
3. **Test on validation** — Never optimize on training data
4. **Keep experiments small** — 50-100 experiments is plenty
5. **Document everything** — Update STRATEGIES.md with insights

## Files Reference

- `strategy.py` — Your strategy (ONLY file to edit)
- `prepare.py` — Data download and backtest engine (FIXED)
- `backtest.py` — Entry point (FIXED)
- `run_benchmarks.py` — Compare to baselines
- `experiment_runner.py` — Log experiments manually
- `auto_research.py` — Automated research loop
- `export_equity.py` — Save equity curves
- `results.tsv` — Experiment results
- `STRATEGIES.md` — Strategy documentation
- `benchmarks/` — Reference strategies

---

*Adapted from auto-researchtrading for Indian NSE markets*
