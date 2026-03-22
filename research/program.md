# NSE Swing Trading — Agent Instructions

## Goal
Maximize the backtest score on the validation set (2024–2025) by tuning strategy parameters.

## Files You Can Edit
- `strategy.py` — ONLY this file. Contains parameters and signal logic.

## Files You Must NOT Edit
- `prepare.py`, `backtest.py`, `auto_research.py`, `signals.py` — infrastructure
- `benchmarks/` — reference strategies

## Before Starting
1. Read current `strategy.py` to understand parameters
2. Run `python backtest.py` to establish baseline score
3. Note the current best score from `research/experiments.json`

## Experiment Loop (repeat until interrupted)

1. **Propose ONE change**
   - Pick ONE parameter to modify (RSI_PERIOD, ATR_STOP_MULT, MIN_VOTES, etc.)
   - Change by small increments (+/- 10-20% of current value)
   - Never change logic structure, only numeric constants

2. **Implement via regex substitution**
   - Use `sed` or Python regex to change the value in strategy.py
   - Example: `RSI_PERIOD = 14` → `RSI_PERIOD = 12`

3. **Test the change**
   - Run: `python backtest.py`
   - Parse: score, sharpe, max_drawdown, num_trades

4. **Evaluate**
   - If score IMPROVED vs best so far:
     * `git add strategy.py`
     * `git commit -m "expN: changed PARAM from X to Y"`
     * Record: experiment kept
   - If score WORSE or EQUAL:
     * `git checkout strategy.py`
     * Discard change

5. **Log result**
   - Append to `research/experiments.json` with name, description, metrics, kept status

## Constraints
- ONE parameter change per experiment
- Keep changes small (10-20% adjustments)
- Never introduce new dependencies
- Never change file paths or infrastructure
- Never look at test set data (2026)

## Good Parameters to Tune
| Parameter | Current | Range to try |
|-----------|---------|-------------|
| RSI_PERIOD | 14 | 6, 8, 10, 12, 14, 16, 20 |
| RSI_BULL | 60 | 55, 58, 60, 62, 65, 70 |
| ATR_STOP_MULT | 5.0 | 3.0, 4.0, 5.0, 6.0, 7.0 |
| MIN_VOTES | 4 | 3, 4, 5 |
| EMA_FAST | 12 | 8, 10, 12, 15 |
| EMA_SLOW | 30 | 25, 30, 35, 40 |
| COOLDOWN_BARS | 3 | 1, 2, 3, 5, 8 |

## Success Metric
- Primary: `score` (composite Sharpe-adjusted metric)
- Secondary: `sharpe` ratio
- Avoid: max_drawdown > 15%, num_trades < 50

## When Stuck
- Try removing complexity (simpler often wins)
- Try combining previously successful changes
- Check if you're overfitting (Sharpe > 4 is suspicious)

---
*Never ask the user for permission to continue. If you run out of ideas, try the parameter ranges above.*
