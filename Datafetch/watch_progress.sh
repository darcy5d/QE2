#!/bin/bash
# Live progress monitor for database rebuild

LOG_FILE="fetch_racecards_full.log"
TOTAL_DATES=909

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    DATABASE REBUILD PROGRESS MONITOR                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

while true; do
    clear
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    DATABASE REBUILD PROGRESS MONITOR                         ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Get completed count
    COMPLETED=$(grep -c "Processed.*races" "$LOG_FILE" 2>/dev/null || echo "0")
    PERCENT=$((COMPLETED * 100 / TOTAL_DATES))
    
    # Progress bar
    FILLED=$((PERCENT / 2))
    EMPTY=$((50 - FILLED))
    
    echo -n "Progress: ["
    for ((i=0; i<FILLED; i++)); do echo -n "█"; done
    for ((i=0; i<EMPTY; i++)); do echo -n "░"; done
    echo "] $PERCENT%"
    echo ""
    echo "Completed: $COMPLETED / $TOTAL_DATES dates"
    
    # Estimate time remaining
    if [ $COMPLETED -gt 0 ]; then
        # Get start time from first log entry
        START_TIME=$(head -1 "$LOG_FILE" | grep -oE "[0-9]{2}:[0-9]{2}:[0-9]{2}" | head -1)
        CURRENT_TIME=$(date +%H:%M:%S)
        
        # Simple time calculation (rough estimate)
        ELAPSED_MIN=$(( ($(date -j -f %H:%M:%S $CURRENT_TIME +%s) - $(date -j -f %H:%M:%S $START_TIME +%s)) / 60 ))
        if [ $ELAPSED_MIN -gt 0 ]; then
            RATE=$(echo "scale=2; $COMPLETED / $ELAPSED_MIN" | bc)
            REMAINING=$(echo "scale=0; ($TOTAL_DATES - $COMPLETED) / $RATE" | bc 2>/dev/null || echo "calculating...")
            echo "Elapsed: ${ELAPSED_MIN} minutes | Est. remaining: ${REMAINING} minutes"
        fi
    fi
    
    echo ""
    echo "────────────────────────────────────────────────────────────────────────────────"
    echo "LATEST ACTIVITY:"
    echo "────────────────────────────────────────────────────────────────────────────────"
    tail -8 "$LOG_FILE" 2>/dev/null | grep -E "Progress|Processed"
    echo ""
    echo "────────────────────────────────────────────────────────────────────────────────"
    echo "Press Ctrl+C to exit monitoring (fetch continues in background)"
    echo ""
    
    sleep 5
done

