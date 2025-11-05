# Model Diagnostics & Calibration Tools

This directory contains comprehensive diagnostic tools for analyzing model performance, detecting data leakage, and calibrating probability predictions.

## 🎯 Overview

The diagnostic suite consists of 5 tools:

1. **Feature Importance Analysis** - Identify important features and detect data leakage
2. **Training Data Validation** - Verify data sufficiency and quality
3. **Calibration Diagnostics** - Assess probability calibration quality
4. **Calibration Training** - Learn temperature scaling parameters
5. **Master Diagnostic Runner** - Execute all tools and generate comprehensive report

## 🚀 Quick Start

### Run All Diagnostics

The easiest way to run all diagnostics:

```bash
cd Datafetch/ml
python run_diagnostics.py --race-type Flat
```

This will:
- Analyze feature importance
- Validate training data
- Generate calibration curves
- Train temperature scaling
- Create HTML report at `models/diagnostic_report.html`

### Run Individual Tools

#### 1. Feature Importance Analysis

Identifies which features are most important and flags suspicious features that could indicate data leakage:

```bash
python analyze_features.py --race-type Flat
```

**Outputs:**
- `models/feature_importance_analysis.png` - Visualization
- `models/feature_analysis_report.csv` - Detailed feature rankings

**What to look for:**
- 🚨 HIGH RISK: Odds-based features in top 5 (suggests leakage)
- ⚠️ MEDIUM RISK: Odds features in top 10 (may be problematic)
- ✓ Good: Race-context features dominate (field strength, form, ratings)

#### 2. Training Data Validation

Checks if you have enough data and validates temporal split integrity:

```bash
python validate_training_data.py --race-type Flat
```

**Outputs:**
- Console report with data statistics
- Sample size assessment
- Temporal split validation

**What to look for:**
- ✓✓ EXCELLENT: 50,000+ samples
- ✓ GOOD: 10,000+ samples
- ⚠️ ADEQUATE: 5,000+ samples
- ❌ INSUFFICIENT: <5,000 samples

#### 3. Calibration Diagnostics

Analyzes how well predicted probabilities match actual outcomes:

```bash
python calibration_diagnostics.py --race-type Flat
```

**Outputs:**
- `models/calibration_curve.png` - Shows predicted vs actual win rates
- `models/reliability_diagram.png` - Win rates by predicted rank
- `models/calibration_report.txt` - Metric summary

**Key Metrics:**
- **Brier Score**: Lower is better (perfect = 0.0)
- **Expected Calibration Error (ECE)**: 
  - <0.01 = Excellent
  - <0.05 = Good
  - <0.10 = Moderate (calibration recommended)
  - ≥0.10 = Poor (calibration essential)

#### 4. Calibration Training

Learns optimal temperature parameter to improve calibration:

```bash
python train_calibration.py --race-type Flat
```

**Outputs:**
- `models/calibration_params_flat.json` - Temperature parameter

**Temperature Interpretation:**
- **T > 1.5**: Model is overconfident → reduces prediction confidence
- **T < 0.7**: Model is underconfident → increases prediction confidence
- **0.7 ≤ T ≤ 1.5**: Reasonable calibration

**Effect on Predictions:**
- Overconfident model (T=2.0): A 30% prediction becomes ~20% (less confident)
- Underconfident model (T=0.5): A 20% prediction becomes ~30% (more confident)

## 📊 Understanding Calibration

### What is Calibration?

A calibrated model's predicted probabilities match reality:
- If model predicts 30% for 100 horses, ~30 should win
- If predictions are 60%, ~60 should win

### Why Does It Matter?

For betting:
- **Overconfident model**: Predicts 40% but reality is 25% → you overbet
- **Calibrated model**: Predicts 25% matching reality → correct stakes

### Temperature Scaling

Simple but effective calibration method:
```python
calibrated_prob = softmax(raw_score / temperature)
```

- Only requires 1 parameter (temperature)
- Preserves ranking order
- Improves probability estimates

## 🔍 What's Happening Under the Hood

### 1. Feature Importance
- Loads trained XGBoost model
- Extracts `gain` importance (contribution to loss reduction)
- Flags features matching leakage patterns (odds, SP, etc.)
- Visualizes top 30 features

### 2. Data Validation
- Queries `racing_pro.db` for race/runner counts
- Validates temporal split (80/20 by date)
- Checks ML features and targets completeness
- Assesses sample size sufficiency

### 3. Calibration Diagnostics
- Loads test set (same temporal split as training)
- Generates predictions using trained model
- Computes calibration curve (10 bins)
- Calculates Brier score, log loss, ECE

### 4. Calibration Training
- Uses validation set (last 10% of test set)
- Optimizes temperature to minimize negative log likelihood
- Evaluates improvement over uncalibrated model
- Saves temperature parameter

### 5. Predictor Integration
- Loads `calibration_params_flat.json` automatically
- Applies temperature scaling in `_scores_to_probabilities`
- Falls back to uncalibrated if no params found

## 📈 Interpreting Results

### Good Signs ✓
- Top features are race-context metrics (field strength, form)
- ECE < 0.05
- Brier score < 0.15
- Temperature between 0.7 and 1.5
- 10,000+ training samples
- Calibration curve hugs diagonal line

### Warning Signs ⚠️
- Odds features in top 10
- ECE > 0.05
- Temperature > 1.5 (overconfidence)
- <10,000 training samples
- Calibration curve diverges from diagonal

### Red Flags 🚨
- Odds features dominate top 5 (data leakage!)
- ECE > 0.10 (poor calibration)
- <5,000 training samples
- Calibration curve wildly off diagonal

## 🔧 Troubleshooting

### "Model not found"
Train a model first:
```bash
python train_baseline.py --race-type Flat
```

### "Database not found"
Ensure you're running from `Datafetch/ml/`:
```bash
cd Datafetch/ml
python run_diagnostics.py
```

### "No calibration improvement"
- Check if model is already well-calibrated (ECE < 0.05)
- Verify test set is large enough (>1000 samples)
- Review feature importance for leakage

### Calibration not being applied
- Ensure `calibration_params_flat.json` exists in `models/`
- Check predictor initialization logs for "✓ Loaded calibration parameters"
- Verify race type matches (Flat vs Hurdle vs Chase)

## 📚 Further Reading

- **Calibration**: [On Calibration of Modern Neural Networks (Guo et al., 2017)](https://arxiv.org/abs/1706.04599)
- **Temperature Scaling**: Simple post-hoc method requiring only validation set
- **Platt Scaling**: Alternative using logistic regression (2 parameters vs 1)
- **Brier Score**: Proper scoring rule for probabilistic predictions

## 🎯 Workflow Recommendation

1. **After initial training**:
   ```bash
   python run_diagnostics.py --race-type Flat
   ```

2. **Check HTML report**:
   - Review feature importance
   - Examine calibration curves
   - Note temperature parameter

3. **Test on upcoming races**:
   - Make predictions with calibrated model
   - Monitor if stakes feel appropriate

4. **Re-run periodically**:
   - After adding significant new data
   - If betting performance degrades
   - Every few months as market conditions change

## 💡 Pro Tips

- **Compare before/after**: Make a few test predictions before and after calibration to see the difference
- **Track real performance**: The ultimate test is real betting ROI
- **Market efficiency**: Even perfect calibration can't beat an efficient market
- **Sample size matters**: More data = better calibration
- **Temporal split is critical**: Never test on past data when training on future!

