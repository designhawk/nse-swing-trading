#!/bin/bash
# autoresearch.sh - Automated strategy research loop for Indian NSE stocks
# Usage: ./autoresearch.sh
# Press Ctrl+C to stop

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Initialize results tracking
if [ ! -f results.tsv ]; then
    echo -e "commit\tscore\tsharpe\tmax_dd\treturn\ttrades\tstatus\tdescription" > results.tsv
fi

# Function to get best score so far
get_best_score() {
    if [ -f results.tsv ]; then
        # Skip header, get max score column
        tail -n +2 results.tsv | cut -f2 | sort -n | tail -1
    else
        echo "-999"
    fi
}

# Function to log result
log_result() {
    local commit=$1
    local score=$2
    local sharpe=$3
    local max_dd=$4
    local return=$5
    local trades=$6
    local status=$7
    local desc=$8
    
    echo -e "${commit}\t${score}\t${sharpe}\t${max_dd}\t${return}\t${trades}\t${status}\t${desc}" >> results.tsv
}

# Main loop
echo "========================================"
echo "AUTO-RESEARCH FOR INDIAN NSE STOCKS"
echo "========================================"
echo ""
echo "This will autonomously:"
echo "1. Modify strategy.py parameters"
echo "2. Run backtest"
echo "3. Keep if improved, revert if not"
echo "4. Repeat until stopped"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================"
echo ""

# Initial commit of baseline
git add .
git commit -m "baseline: Initial strategy" || true

EXP_NUM=1
BEST_SCORE=$(get_best_score)

while true; do
    echo ""
    echo "========================================"
    echo "EXPERIMENT $EXP_NUM"
    echo "========================================"
    
    # Generate a random modification
    # This simulates what Claude would do - modify one parameter
    MODIFICATION=$(python3 << 'EOF'
import random

modifications = [
    ("RSI_PERIOD", [6, 10, 12, 14]),
    ("RSI_BULL", [45, 55, 60]),
    ("RSI_BEAR", [40, 45, 55]),
    ("SHORT_WINDOW", [3, 4, 6, 7]),
    ("MED_WINDOW", [8, 12, 15]),
    ("LONG_WINDOW", [25, 40, 50]),
    ("BASE_POSITION_PCT", [0.08, 0.12, 0.15]),
    ("ATR_STOP_MULT", [4.0, 6.0, 7.0]),
    ("COOLDOWN_BARS", [1, 3, 5]),
    ("MIN_VOTES", [3, 5]),
    ("BASE_THRESHOLD", [0.008, 0.015, 0.018]),
]

param, values = random.choice(modifications)
new_val = random.choice(values)
print(f"{param}:{new_val}")
EOF
)
    
    PARAM=$(echo $MODIFICATION | cut -d: -f1)
    NEW_VAL=$(echo $MODIFICATION | cut -d: -f2)
    
    echo "Modification: $PARAM = $NEW_VAL"
    echo ""
    
    # Apply modification using sed
    if [[ "$NEW_VAL" =~ ^[0-9]+$ ]]; then
        # Integer
        sed -i "s/^$PARAM = [0-9]\+$/$PARAM = $NEW_VAL/" strategy.py
    else
        # Float
        sed -i "s/^$PARAM = [0-9.]\+$/$PARAM = $NEW_VAL/" strategy.py
    fi
    
    # Git commit
    git add strategy.py
    git commit -m "exp$EXP_NUM: $PARAM = $NEW_VAL" || continue
    
    # Run backtest
    echo "Running backtest..."
    python backtest.py > run.log 2>&1 || true
    
    # Parse results
    SCORE=$(grep "^score:" run.log | awk '{print $2}' || echo "-999")
    SHARPE=$(grep "^sharpe:" run.log | awk '{print $2}' || echo "0")
    MAX_DD=$(grep "^max_drawdown_pct:" run.log | awk '{print $2}' || echo "100")
    RETURN=$(grep "^total_return_pct:" run.log | awk '{print $2}' || echo "0")
    TRADES=$(grep "^num_trades:" run.log | awk '{print $2}' || echo "0")
    
    COMMIT=$(git rev-parse --short HEAD)
    
    echo ""
    echo "Results:"
    echo "  Score: $SCORE"
    echo "  Sharpe: $SHARPE"
    echo "  Max DD: $MAX_DD%"
    echo "  Return: $RETURN%"
    echo "  Trades: $TRADES"
    
    # Compare with best
    if (( $(echo "$SCORE > $BEST_SCORE" | bc -l) )); then
        echo -e "${GREEN}✅ IMPROVEMENT! $SCORE > $BEST_SCORE${NC}"
        log_result "$COMMIT" "$SCORE" "$SHARPE" "$MAX_DD" "$RETURN" "$TRADES" "keep" "$PARAM=$NEW_VAL"
        BEST_SCORE=$SCORE
        
        # Save best strategy
        cp strategy.py strategy_best.py
    else
        echo -e "${RED}❌ No improvement. $SCORE <= $BEST_SCORE${NC}"
        echo "Reverting..."
        log_result "$COMMIT" "$SCORE" "$SHARPE" "$MAX_DD" "$RETURN" "$TRADES" "discard" "$PARAM=$NEW_VAL"
        git reset --hard HEAD~1
    fi
    
    EXP_NUM=$((EXP_NUM + 1))
    
    # Small delay
    sleep 1
done
