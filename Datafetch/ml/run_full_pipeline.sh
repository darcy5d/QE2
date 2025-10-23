#!/bin/bash
# Automated ML Pipeline Runner
# Waits for fetch to complete, then runs stats → features → training

set -e  # Exit on error

echo "============================================================"
echo "ML PIPELINE AUTOMATION"
echo "============================================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Function to check if fetch is running
is_fetch_running() {
    ps aux | grep -q "[f]etch_historical_results.py"
}

# Function to get result count
get_result_count() {
    sqlite3 racing_pro.db "SELECT COUNT(*) FROM results" 2>/dev/null || echo "0"
}

# Wait for fetch to complete
if is_fetch_running; then
    echo "⏳ Fetch process is still running. Waiting for completion..."
    echo "   Checking every 30 seconds..."
    echo ""
    
    while is_fetch_running; do
        CURRENT_COUNT=$(get_result_count)
        if [ "$CURRENT_COUNT" != "0" ]; then
            echo "   Current progress: $CURRENT_COUNT results fetched"
        fi
        sleep 30
    done
    
    echo ""
    echo "✓ Fetch completed!"
    echo ""
    sleep 2  # Give DB time to close
else
    echo "✓ No fetch process running"
    echo ""
fi

# Check we have results
RESULT_COUNT=$(get_result_count)
if [ "$RESULT_COUNT" == "0" ]; then
    echo "❌ No results found in database!"
    echo "   Please run fetch_historical_results.py first"
    exit 1
fi

echo "📊 Found $RESULT_COUNT results in database"
echo ""

# Step 1: Compute Statistics
echo "============================================================"
echo "STEP 1: Computing Statistics"
echo "============================================================"
echo ""

python ml/compute_stats.py
if [ $? -ne 0 ]; then
    echo "❌ Stats computation failed!"
    exit 1
fi

echo ""
echo "✓ Statistics computed successfully"
echo ""
sleep 2

# Step 2: Generate Features
echo "============================================================"
echo "STEP 2: Generating Features"
echo "============================================================"
echo ""

python ml/feature_engineer.py
if [ $? -ne 0 ]; then
    echo "❌ Feature generation failed!"
    exit 1
fi

echo ""
echo "✓ Features generated successfully"
echo ""
sleep 2

# Step 3: Check status
echo "============================================================"
echo "PIPELINE STATUS"
echo "============================================================"
echo ""

python ml/monitor_progress.py

echo ""
echo "============================================================"
echo "✓ ML PIPELINE COMPLETE!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Train baseline model: python ml/train_baseline.py"
echo "  2. View data in GUI: python racecard_gui.py"
echo "  3. Start making predictions!"
echo ""


