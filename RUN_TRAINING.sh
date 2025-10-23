#!/bin/bash
# Flat Racing Model Training Script
# Run this to train the Flat-only model

set -e  # Exit on error

echo "======================================"
echo "🏇 Flat Racing Model Training"
echo "======================================"
echo ""

# Navigate to ML directory
cd "$(dirname "$0")/Datafetch/ml"

echo "📍 Current directory: $(pwd)"
echo ""

# Check if racing_pro.db exists
if [ ! -f "../racing_pro.db" ]; then
    echo "❌ ERROR: racing_pro.db not found!"
    echo "   Expected location: $(pwd)/../racing_pro.db"
    exit 1
fi

echo "✅ Database found: racing_pro.db"
echo ""

# Run training
echo "🚀 Starting Flat model training..."
echo "   This may take 10-30 minutes depending on your CPU"
echo ""

python train_baseline.py \
    --race-type Flat \
    --test-size 0.2 \
    --output-dir models

# Check if model was created
if [ -f "models/xgboost_flat.json" ]; then
    echo ""
    echo "======================================"
    echo "✅ SUCCESS! Flat model trained"
    echo "======================================"
    echo ""
    echo "Created files:"
    ls -lh models/*flat* | awk '{print "  ", $9, "(" $5 ")"}'
    echo ""
    echo "Next steps:"
    echo "1. Test predictions: python -c 'from predictor import ModelPredictor; p=ModelPredictor(race_type=\"Flat\"); print(\"Model loaded!\")'"
    echo "2. Start GUI: cd ../.. && python Datafetch/racecard_gui.py"
    echo "3. Go to 'In The Money' tab and click 'Find Value Bets'"
    echo ""
else
    echo ""
    echo "❌ ERROR: Model file not created!"
    echo "   Check the output above for errors"
    exit 1
fi

