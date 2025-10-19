#!/bin/bash
# Rebuild ML Features and Train Ranking Model
# Run this after implementing ranking model changes

echo "=========================================="
echo "REBUILD FEATURES & TRAIN RANKING MODEL"
echo "=========================================="
echo ""

# Change to project directory
cd "$(dirname "$0")/Datafetch/ml"

# Step 1: Regenerate features with new columns
echo "Step 1: Regenerating ML features..."
echo "This will populate all 23 new feature columns"
echo ""
python build_ml_dataset.py

if [ $? -ne 0 ]; then
    echo "❌ Feature generation failed!"
    exit 1
fi

echo ""
echo "✓ Feature generation complete"
echo ""

# Step 2: Train ranking model
echo "Step 2: Training ranking model..."
echo "This uses rank:pairwise objective with race grouping"
echo ""
python train_baseline.py --output-dir models

if [ $? -ne 0 ]; then
    echo "❌ Model training failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ COMPLETE!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart your GUI to load the new ranking model"
echo "2. Generate predictions for upcoming races"
echo "3. Verify probabilities sum to ~100% per race"
echo "4. Check that field strength features are working"
echo ""
echo "Expected improvements:"
echo "  - Top Pick Win Rate: >30% (was ~25%)"
echo "  - Top 3 Hit Rate: >70% (was ~65%)"
echo "  - Realistic probability distributions"
echo "  - Field-aware predictions"
echo ""

