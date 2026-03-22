# NSE Swing Trading Research Tool

Autonomous strategy research + daily signal generator for Indian NSE stocks.

**What this does:**
- Runs backtests on 7 years of Nifty 50 data with realistic Indian costs (STT, brokerage, slippage)
- Auto-experiments with strategy parameters overnight to find improvements
- Generates a daily "what to buy/sell tomorrow" signal report

**What this is NOT:**
- Not a live trading system — it does not connect to any broker
- Not financial advice — all signals require your own judgement before acting

---

## Quick Start (First Time)

```bash
# 1. Install dependencies
pip install -e .

# 2. Download Nifty 50 historical data (2019–today, ~2 minutes)
python prepare.py

# 3. Verify everything works
python backtest.py

# 4. See today's signals
python signals.py
```

---

## Daily Workflow (Every Trading Day)

**Each morning before market open (9:15 AM IST):**

```bash
python signals.py --refresh
```

The `--refresh` flag downloads last night's closing prices. Output:

```
==============================================================
  NSE SWING SIGNALS
  Based on: 2026-03-21 close prices
  Execute:  Next trading day at market open (~9:15 AM IST)
==============================================================

  BUY at market open  (2 stocks)
  ---------------------------------------------------------------
  Stock               Last Close    Suggested Size*
  ---------------------------------------------------------------
  HCLTECH          Rs  1,603.58  Rs 20,000 (~12 shares)
  NTPC             Rs    380.95  Rs 20,000 (~52 shares)

  EXIT: No exits signaled today.

  TIP: To see stop prices for stocks you own, run:
  python signals.py --held RELIANCE TCS
```

**If you own stocks, track your stops:**

```bash
python signals.py --held RELIANCE HCLTECH NTPC
```

This shows exactly what price each stock needs to fall below before you exit.

**Sizing your positions:**
- Default model assumes Rs 10 Lakhs capital, 2% per stock = Rs 20,000 per position
- If your capital is different, scale proportionally:
  - Rs 5L capital → Rs 10,000 per stock
  - Rs 20L capital → Rs 40,000 per stock
  - Rs 1L capital → Rs 2,000 per stock (but costs will bite harder at small sizes)

---

## How the Strategy Works

Long-only swing trading on Nifty 50 stocks, daily timeframe.

**Entry:** A stock gets a buy signal when 4 out of 5 indicators agree:
1. Medium-term momentum (8-day return above threshold)
2. Short-term momentum (5-day return above threshold)
3. EMA crossover (EMA-7 above EMA-30)
4. RSI(14) above 60 (stock has momentum, not overbought)
5. MACD histogram positive

**Exit (whichever comes first):**
- Trailing stop: price falls more than 5.5× ATR below the peak
- RSI overbought: RSI(14) exceeds 70

**Why long-only?**
Short selling requires holding overnight positions in NSE cash equity, which is illegal. This strategy only buys.

**Execution:**
Signals fire at the day's close → you execute at the NEXT day's market open. No same-day magic.

**Costs modelled:**
- Rs 20 flat brokerage per trade (Zerodha model)
- 3.5 bps NSE exchange charges
- **0.1% STT on every sell** (this is real, mandatory, and significant)
- 5 bps slippage

---

## Files — What to Use When

| File | When to use |
|------|-------------|
| `signals.py` | **Every trading day** — get buy/sell/stop signals |
| `backtest.py` | After editing `strategy.py` — check if change improved score |
| `auto_research.py` | Overnight — let it automatically find better parameters |
| `strategy.py` | Edit this to try new ideas |
| `tools/run_benchmarks.py` | Compare strategy vs buy-and-hold, momentum, mean-reversion |
| `prepare.py` | One-time data download; run again to add new symbols |
| `tools/export_equity.py` | Export equity curve to CSV for Excel/analysis |

**Files you should never edit:**
- `prepare.py` — backtest engine and cost model (changing it invalidates all experiment history)
- `backtest.py` — entry point (fixed interface)
- `benchmarks/` — reference strategies to compare against

---

## Improving the Strategy

The current strategy has **Sharpe ~2.1** on the 2023–2024 validation period with honest costs. To try to improve it:

### Option A — Overnight auto-search (recommended)

```bash
# Run 50 experiments automatically, keep improvements
python auto_research.py --max 50

# Or run indefinitely
python auto_research.py

# Check results next morning
python auto_research.py --restore   # apply best found strategy
```

The script randomly modifies one parameter at a time, runs a backtest, keeps the change if it improved the score, reverts if not. Results are saved to `research/experiments.json`.

### Option B — Manual experiment

```bash
# 1. Edit strategy.py — change one parameter
# 2. Run backtest
python backtest.py

# 3. If score improved, keep. If not, restore:
git checkout strategy.py
```

### Parameters worth tuning (in strategy.py)

```python
MIN_VOTES = 4           # Raise to 5 for fewer, higher-conviction trades
ATR_STOP_MULT = 5.5     # Lower = tighter stops = less drawdown but more exits
RSI_BULL = 60           # Raise = stricter entry, fewer trades
COOLDOWN_BARS = 3       # Days to wait before re-entering a stock after exit
EMA_SLOW = 30           # Longer = smoother trend filter
```

**Rule:** change one thing at a time. If two things change, you won't know which one helped.

### Check out-of-sample performance

Once you've tuned on the validation set, run on the test set (2025 data) to see real out-of-sample performance:

```bash
python backtest.py --split test
```

**Important:** only check the test set occasionally. If you run it repeatedly and tune towards it, it stops being out-of-sample.

---

## Understanding the Backtest Score

```
score = sharpe × √(min(trades/50, 1.0)) − drawdown_penalty − turnover_penalty
```

- **Higher is better**
- Score roughly equals Sharpe when you have 50+ trades and low drawdown
- Honest Sharpe of **1.5–2.5** is good for a real daily strategy (the old inflated 8.0 was fake)
- If score suddenly jumps above 4, check for bugs — likely overfitting

```bash
# Current honest baseline on validation (2023–2024):
# score: ~2.1  sharpe: ~2.1  return: ~37%  max_dd: ~7%  trades: ~2172
```

---

## Data

- **Source:** Groww (free, adjusted for splits/dividends)
- **Universe:** 49 Nifty 50 stocks (TATAMOTORS excluded — Groww issues)
- **History:** 2019–present (auto-updated when you run `--refresh`)
- **Splits:**
  - Train: 2019–2022 (strategy development)
  - Validation: 2023–2024 (used by auto_research to find parameters)
  - Test: 2025–present (out-of-sample, use sparingly)

---

## Project Structure

```
auto-researchtrading-india/
│
├── signals.py              ← START HERE every morning
├── strategy.py             ← EDIT THIS to change strategy logic
│
├── backtest.py             ← Test a strategy change
├── auto_research.py        ← Overnight parameter search
├── prepare.py              ← Data engine (do not edit)
├── README.md               ← This file
│
├── tools/
│   ├── run_benchmarks.py   ← Compare strategy vs baselines
│   ├── export_equity.py    ← Export equity curve to CSV
│   └── experiment_runner.py← Manual experiment logging
│
├── research/
│   ├── experiments.json    ← Auto-research experiment log
│   ├── strategy_best.py    ← Best strategy found by auto_research
│   └── strategy_backups/   ← Per-experiment backups (gitignored)
│
├── benchmarks/             ← Reference strategies (do not edit)
│
└── docs/
    ├── SETUP.md            ← Installation instructions
    └── STRATEGIES.md       ← Notes on what has/hasn't worked
```

---

## Known Limitations

1. **Survivorship bias** — Nifty 50 stocks are today's winners. Historical returns are slightly inflated because we know these companies survived.

2. **No broker integration** — signals.py tells you what to do, but you place orders manually on Zerodha/Upstox/etc.

3. **Daily bars only** — the strategy can't time intraday entries. You execute at the open, which may gap from the previous close.

4. **Groww data** — generally reliable but occasionally has errors or gaps. Always sanity-check before acting on a signal.

5. **Parameter optimization on val set** — the current strategy parameters were found by running 80+ experiments on 2023–2024 data. The true forward-looking performance is unknown until tested live.

---

## Disclaimer

This is a research and educational tool. It is not registered investment advice. Past backtest performance does not guarantee future results. Always verify signals independently and use your own judgement. Never risk money you cannot afford to lose.
