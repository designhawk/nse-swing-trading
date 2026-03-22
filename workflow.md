# NSE Swing Trading — Workflow

---

## What this tool does

Scans all 49 Nifty 50 stocks every morning and tells you:
- Which stocks to **buy** at market open, with exact stop-loss and target prices
- Which stocks to **exit** if you hold them
- Your **current stop prices** so you know when to get out intraday

It does NOT place orders. You act manually on Zerodha / Upstox / etc.

---

## First-time setup

```bash
pip install -e .
python prepare.py        # downloads 7 years of Nifty 50 data (~2 min)
python backtest.py       # verify it works — expect Sharpe ~2.1
python signals.py        # see today's signals
```

---

## Weekly timetable

### Monday — start of week

| Time | Action |
|------|--------|
| 8:45 AM | Check if US markets / SGX Nifty had a big move over the weekend. If Nifty is expected to gap down 1%+, be extra cautious with new buys today. |
| 9:00 AM | `python signals.py --refresh --held STOCK1 STOCK2` — get fresh signals and updated stop prices |
| 9:10 AM | Glance at the Market Overview in the output. If breadth is bearish (< 40% bullish), skip new buys for today. |
| 9:15 AM | Market opens. If buy signal exists AND Monday's open is **above** the stop price shown — enter. If open is at or below stop, skip the trade. |
| 3:30 PM | Market closes. Note down closing prices of your holdings mentally. |
| Night (optional) | `python auto_research.py --max 50` — let it search for better parameters overnight |

### Tuesday to Thursday — mid week

| Time | Action |
|------|--------|
| 9:00 AM | `python signals.py --refresh --held STOCK1 STOCK2` — check for new signals and updated stops |
| 9:15 AM | Act on any buy or exit signals |
| During the day | If any holding falls to its stop price intraday — exit immediately, don't wait for next morning |
| Night (optional) | Run `auto_research.py` if you want more experiments |

### Friday — end of week

| Time | Action |
|------|--------|
| 9:00 AM | `python signals.py --refresh --held STOCK1 STOCK2` |
| 9:15 AM | Act on signals as usual |
| After market | Review the week — did signals play out? Note any gaps between signal price and actual fill |
| Evening | `python backtest.py` — weekly health check, confirm score is still ~2.1 |
| Evening | `python tools/run_benchmarks.py` — confirm strategy still beats baselines |
| Night | Good time to run `auto_research.py` — full weekend to search for improvements |

### Saturday / Sunday — no market

| Time | Action |
|------|--------|
| Morning | Check if `auto_research.py` found improvements: `python auto_research.py --restore` then `python backtest.py` |
| Anytime | Check weekend news — RBI announcements, global events, earnings — anything that could cause Monday gap |
| Anytime | Review `research/experiments.json` to see what parameter changes helped or didn't |

---

### The one rule for Monday gaps

Before entering any Monday buy signal, mentally check:

```
Is Monday's open price ABOVE the stop price shown in the signal?
  Yes → enter the trade
  No  → skip it, the setup is invalidated by the gap
```

---

## Every trading morning (before 9:15 AM IST)

```bash
python signals.py --refresh
```

The `--refresh` downloads last night's closing prices. You'll see:

```
  BUY tomorrow at market open  (2 stocks)
  ---------------------------------------------------------------
  Stock              Buy ~Rs    Stop Rs   Target Rs   Risk %
  ---------------------------------------------------------------
  HCLTECH        1,603.00   1,490.00   1,829.00    7.1%
  NTPC             380.95     340.00     422.85    10.7%

  No exits signaled today.

  MARKET OVERVIEW
  Stocks above 20-day SMA:  32/49 (65%)
  Bias: BULLISH — momentum strategies tend to work well
```

### Reading the signal

| Column | Meaning |
|--------|---------|
| **Buy ~Rs** | Yesterday's close — your actual fill will be close to this at 9:15 AM open |
| **Stop Rs** | If the stock trades **at or below** this price at any point during the day, exit immediately |
| **Target Rs** | A rough 2:1 guide. The strategy has no fixed target — it trails the stop upward as price rises, so you can hold longer |
| **Risk %** | How far the stop is from entry. Smaller = tighter stop |

### What to do

- **BUY signal** → place a market order at 9:15 AM open
- **EXIT signal** → only matters if you actually hold the stock. Exit at open.
- **No signals** → stay in cash. Common in bearish markets — that's correct behaviour.
- **Market bearish** (< 40% stocks above 20-day SMA) → be cautious, even if you get a buy signal

---

## If you own stocks — track stops every morning

```bash
python signals.py --refresh --held HCLTECH NTPC
```

Shows your current stop price for each holding:

```
  YOUR HOLDINGS — current stop prices
  Stock               Last Close    Stop Rs   Gap %
  HCLTECH          1,650.00     1,510.00   8.5%
  NTPC               395.00       342.00   13.4%

  Exit immediately if price falls BELOW the stop, any time during the day.
```

The stop trails upward as the stock rises — it will never move down. Check it each morning.

---

## Position sizing

Default model: Rs 10 Lakhs capital, Rs 20,000 (2%) per stock.

| Your capital | Size per stock |
|-------------|---------------|
| Rs 1 Lakh   | Rs 2,000      |
| Rs 2 Lakhs  | Rs 4,000      |
| Rs 5 Lakhs  | Rs 10,000     |
| Rs 10 Lakhs | Rs 20,000     |
| Rs 20 Lakhs | Rs 40,000     |

Below Rs 5,000 per trade, the flat Rs 20 brokerage starts eating returns. Factor this in at small capital.

---

## Weekly — health check

```bash
python backtest.py                  # should show Sharpe ~2.1 on 2023-2024 data
python tools/run_benchmarks.py      # should beat buy-and-hold and simple momentum
```

---

## Overnight — let it find better parameters automatically

Run before you sleep:

```bash
python auto_research.py --max 50    # runs ~50 experiments, keeps improvements
```

Next morning:

```bash
python auto_research.py --restore   # apply the best strategy found
python backtest.py                  # confirm score improved
```

Each experiment tweaks one parameter (RSI period, stop multiplier, etc.), backtests it, keeps it if better. Results saved to `research/experiments.json`.

### View progress chart

After running experiments, generate a visual chart:

```bash
python tools/plot_progress.py
```

This creates `research/progress.png` showing:
- Score over time (green dots = kept improvements, red = reverted)
- Sharpe ratio progression
- Summary stats: total experiments, best score, improvements kept

Open the PNG to see your research progress at a glance.

---

## Try your own ideas

```bash
# 1. Edit one parameter in strategy.py — change one thing only
# 2. Test it
python backtest.py
# 3a. Score improved? Keep it.
# 3b. Score dropped? Revert.
git checkout strategy.py
```

Key parameters to experiment with:

| Parameter | Default | What it does |
|-----------|---------|-------------|
| `MIN_VOTES` | 4 | Signals needed to enter (out of 5). Raise to 5 = fewer, stronger trades |
| `ATR_STOP_MULT` | 5.0 | Stop distance in ATR units. Lower = tighter stop, less drawdown |
| `RSI_BULL` | 60 | RSI must be above this to enter. Raise = stricter filter |
| `COOLDOWN_BARS` | 3 | Days before re-entering a stock after exit |
| `EMA_SLOW` | 30 | Slow EMA period for trend filter |

---

## Out-of-sample check (use rarely)

Once you've done many experiments, check on data the strategy has never seen:

```bash
python backtest.py --split test     # tests on 2025-2026 data
```

Only run this occasionally — if you keep tweaking towards it, it stops being a real test.

---

## File reference

| File | Run when |
|------|---------|
| `signals.py --refresh` | Every trading morning |
| `signals.py --refresh --held ...` | Every morning if you own stocks |
| `backtest.py` | After editing strategy.py |
| `auto_research.py --max 50` | Overnight |
| `auto_research.py --restore` | Morning after overnight run |
| `tools/run_benchmarks.py` | Weekly |
| `tools/export_equity.py` | When you want to chart the equity curve |

**Never edit:** `prepare.py`, `backtest.py`, `benchmarks/`

---

## How the strategy decides to buy

A stock gets a BUY signal when 4 out of 5 indicators agree:

1. Medium-term momentum up (8-day return above threshold)
2. Short-term momentum up (5-day return above threshold)
3. EMA(12) above EMA(30) — trending up
4. RSI(14) above 60 — has momentum, not yet overbought
5. MACD histogram positive

Exit when the trailing stop is hit (ATR-based) or RSI exceeds 70.

---

## Understanding the backtest score

```
score = Sharpe x sqrt(min(trades/50, 1.0)) - drawdown penalty - turnover penalty
```

- Higher is better. Score roughly equals Sharpe when you have 50+ trades.
- Realistic range: **1.5 – 2.5** with honest Indian costs
- Score > 4 is suspicious — likely overfitting

Current baseline: score ~2.1, Sharpe ~2.1, return ~37%, max drawdown ~7% (2023–2024 val set)

---

## Disclaimer

Research tool only. Not financial advice. Backtest results do not guarantee future returns. Always verify signals before acting. Never risk money you cannot afford to lose.
