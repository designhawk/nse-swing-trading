# Strategy Evolution Log

This document tracks the evolution of trading strategies through autoresearch experiments.

## Current Best: Baseline

**Experiment:** baseline  
**Date:** 2025-01-20  
**Score:** 6.521471  
**Description:** Initial 6-signal ensemble strategy

### Performance Metrics
- **Sharpe Ratio:** 6.521471
- **Total Return:** 8.68%
- **Max Drawdown:** 0.20%
- **Number of Trades:** 1,672
- **Win Rate:** 74.56%
- **Profit Factor:** 9.71
- **Annual Turnover:** ₹10,612,128.64

### Strategy Architecture

**Symbols:** 10 NSE Large-cap stocks
- RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS, ICICIBANK.NS
- HINDUNILVR.NS, ITC.NS, SBIN.NS, BHARTIARTL.NS, KOTAKBANK.NS

**Timeframe:** Daily bars

**Capital:** ₹10,00,000

### Signals (6-signal ensemble)

1. **Momentum (10-day)** - Price return > dynamic threshold
2. **Very-short Momentum (5-day)** - Return > 0.7 × threshold
3. **EMA Crossover** - EMA(7) > EMA(26)
4. **RSI(8)** - RSI > 50 (bull) / < 50 (bear)
5. **MACD(14,23,9)** - Histogram > 0
6. **Bollinger Band Compression** - Width < 85th percentile

**Entry:** 4 out of 6 signals must agree

### Exit Conditions

1. **ATR Trailing Stop** - 5.5x ATR from peak/trough (priority)
2. **RSI Mean-Reversion** - Exit longs at RSI > 69, shorts at RSI < 31
3. **Signal Flip** - Reverse position when opposing ensemble fires

### Key Parameters

```python
BASE_POSITION_PCT = 0.10    # 10% per stock
COOLDOWN_BARS = 2           # 2-day wait after exit
RSI_PERIOD = 8              # Fast RSI
ATR_STOP_MULT = 5.5         # Wide trailing stop
MIN_VOTES = 4               # 4 of 6 signals needed
BASE_THRESHOLD = 0.012      # 1.2% momentum threshold
```

---

## Experiment History

### Phase 1: Baseline

| Exp | Score | Sharpe | Return | Max DD | Change | Status |
|-----|-------|--------|--------|--------|--------|--------|
| baseline | 6.52 | 6.52 | 8.68% | 0.20% | Initial strategy | ✅ Kept |

---

## Research Directions

### Tier 1 — High Probability
- [ ] Adjust RSI period (try 6, 10, 14)
- [ ] Modify momentum lookback periods
- [ ] Test different MIN_VOTES thresholds (3, 5)
- [ ] Adjust ATR stop multiplier
- [ ] Experiment with position sizing

### Tier 2 — Worth Exploring
- [ ] Add sector-based filtering
- [ ] Market regime detection (NIFTY 50 trend)
- [ ] Volatility-based position sizing
- [ ] Different Bollinger Band periods
- [ ] MACD parameter optimization

### Tier 3 — Novel Ideas
- [ ] Correlation-based hedging
- [ ] Multi-timeframe confirmation
- [ ] Seasonality patterns (monthly/quarterly effects)
- [ ] News/sentiment integration
- [ ] Machine learning signal weights

---

## Key Insights

### What Works
- Multi-signal ensemble reduces false signals
- Fast RSI (period 8) captures momentum quickly
- Wide ATR stops (5.5x) let winners run
- Low drawdown (0.20%) indicates good risk control
- High win rate (74.6%) shows signal quality

### What to Avoid
- Over-optimization on historical data
- Adding too many signals (complexity penalty)
- Tight stops that get hit by noise
- Ignoring sector/market context

---

## Comparison to Benchmarks

Run `python run_benchmarks.py` to see current comparisons.

---

## Notes

- Validation period: 2023-01-01 to 2024-12-31 (2 years)
- Training period: 2019-01-01 to 2023-01-01 (4 years)
- All results are out-of-sample on validation data
- Strategy must beat benchmarks to be considered successful

---

*Last updated: 2025-01-20*
