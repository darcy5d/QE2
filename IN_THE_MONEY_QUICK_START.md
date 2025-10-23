# 💰 In The Money - Quick Start Guide

## What is it?

The **In The Money** tab analyzes your ML model's predictions against market odds to find value betting opportunities. It automatically calculates optimal stake sizes using the Kelly Criterion.

## 5-Minute Setup

### 1. Prerequisites ✅
- [ ] Upcoming races fetched ("Upcoming Races" tab)
- [ ] ML model trained ("Model Training" tab)
- [ ] Predictions generated ("Predictions" tab)

### 2. Configure Settings ⚙️

**Navigate to: 💰 In The Money tab**

#### Essential Settings:
```
Bankroll: $1000          (Your total betting budget)
Kelly Fraction: 1/2 Kelly (Recommended for beginners)
Min Edge: 5%             (Only show bets with >5% advantage)
```

#### Bet Type Filters:
- ☑ Win - Standard win bets
- ☑ Place - Top 3 finish bets (safer)
- ☑ Exacta - 1st and 2nd in correct order
- ☐ Trifecta - 1st, 2nd, 3rd in order (uncheck if conservative)
- ☐ First Four - 1st through 4th in order (uncheck if conservative)

### 3. Generate Recommendations 🚀

Click: **"🚀 Find Value Bets"**

The system will:
1. Load all predictions
2. Compare model odds vs market odds
3. Calculate expected value for each bet
4. Apply Kelly Criterion for stake sizing
5. Display only positive EV opportunities

### 4. Review Results 📊

Results are organized hierarchically:

```
📅 Friday 18 October
  └─ 🏇 Ascot (5 bets)
      └─ 14:00 - 1m2f - Class 2
          ├─ WIN: Thunder Bay (#3) → Stake $25 @ 4.50 (EV: +12.5%)
          ├─ PLACE: Silver Star (#7) → Stake $18 @ 2.10 (EV: +8.3%)
```

**What the numbers mean:**
- **Stake $25**: Recommended bet amount (based on Kelly Criterion)
- **@ 4.50**: Market odds available
- **EV: +12.5%**: Expected 12.5% return on this bet

### 5. Place Your Bets 🎯

**For each recommendation:**
1. Check the horse and bet type
2. Note the recommended stake
3. Verify odds are still available
4. Place bet with your bookmaker

**Export for Records:**
- Click "📊 Export Bets"
- Save CSV for tracking
- Track actual results vs predictions

## Understanding Kelly Fractions

| Kelly | Risk Level | Typical Stake | When to Use |
|-------|------------|---------------|-------------|
| 1/8 Kelly | Very Low | 1-3% | Just starting, very cautious |
| 1/4 Kelly | Low | 3-6% | Building confidence |
| **1/2 Kelly** | **Medium** | **7-12%** | **RECOMMENDED DEFAULT** |
| 2/3 Kelly | High | 10-18% | Experienced, proven model |
| Full Kelly | Very High | 15-25% | Expert only, high variance |

## Reading the Predictions Tab

The **Predictions** tab now shows extended information:

| Column | Meaning |
|--------|---------|
| Assessment | Quick label: "Top Pick", "Strong Chance", "Good Chance", "Outsider" |
| Our Win Odds | What your model thinks fair odds are |
| Mkt Win Odds | What bookmakers are offering |
| Our Place Odds | Your model's fair place odds |
| Mkt Place Odds | Bookmakers' place odds |

**🟢 Green highlighting** = Value bet! Market odds are better than model odds.

## Example Workflow

### Scenario: Saturday Racing

1. **Morning (9:00 AM)**
   - Fetch today's races (Upcoming Races tab)
   - Generate predictions (Predictions tab)
   - Takes 5-10 minutes

2. **Analysis (9:15 AM)**
   - Open In The Money tab
   - Set bankroll: $500
   - Set Kelly: 1/4 Kelly (conservative)
   - Min edge: 10%
   - Find Value Bets

3. **Results**
   ```
   Total Bets: 12
   Total Stake: $147.50
   Expected Profit: $23.40 (15.9% ROI)
   ```

4. **Betting (9:30 AM - 12:00 PM)**
   - Place recommended bets
   - Check odds still available
   - Export to CSV for records

5. **Evening (After Racing)**
   - Check results
   - Track actual P&L
   - Compare with predictions

## Pro Tips 💡

### Start Conservative
- Begin with 1/4 Kelly
- Only bet Win and Place
- Require 10%+ edge
- Track 50 bets before increasing stakes

### When to Increase Stakes
✅ After 50+ bets showing profit
✅ Model predictions are well-calibrated
✅ You understand the system fully
✅ You can afford higher variance

### Red Flags 🚨
⚠️ Model consistently wrong on favorites
⚠️ Losing money after 50+ bets
⚠️ Odds moving significantly between analysis and betting
⚠️ Betting more than 10% bankroll on single race

### Best Practices
1. **Set aside dedicated bankroll** - Don't use money you can't afford to lose
2. **Track everything** - Export CSV after every session
3. **Review weekly** - Are predictions accurate? Is edge real?
4. **Adjust as needed** - If losing, reduce stakes or stop
5. **Never chase losses** - Stick to Kelly recommendations

## Common Questions

### Q: Why are there no recommendations?
**A:** Could be:
- No races have sufficient edge (increase min edge filter)
- Market odds not available in database
- Model predictions too close to market odds

### Q: Stakes seem too large!
**A:** Switch to more conservative Kelly fraction:
- Try 1/4 Kelly instead of 1/2 Kelly
- Or reduce bankroll setting

### Q: Can I bet on everything shown?
**A:** Yes, but:
- Check odds are still available
- Ensure total stake doesn't exceed bankroll
- Consider focusing on highest EV bets first

### Q: How accurate is the model?
**A:** Check the Predictions tab:
- Look for "Strong Chance" and "Top Pick" horses
- Review their actual finishing positions
- Calculate hit rate over time

### Q: What if odds change after analysis?
**A:** 
- Better odds = Even better value, bet more if Kelly allows
- Worse odds = Recalculate EV, may no longer be value
- Significantly worse = Skip the bet

## Risk Management Rules

### Rule #1: Never Exceed Total Bankroll
Sum of all stakes must be ≤ bankroll

### Rule #2: Never Exceed 10% on Single Bet
System automatically caps at 10% maximum

### Rule #3: Stop if Down 30%
If bankroll drops 30%, stop and reassess model

### Rule #4: Track Everything
Export and save every betting session

### Rule #5: Review and Adjust
Weekly review of P&L and model performance

## Support and Troubleshooting

### No races showing up?
1. Check "Upcoming Races" tab - are races fetched?
2. Check "Predictions" tab - are predictions generated?
3. Try lowering min edge requirement

### Error generating recommendations?
1. Ensure ML model is trained
2. Check racing_pro.db exists and has historical data
3. Verify upcoming_races.db is populated

### Stakes seem wrong?
1. Verify bankroll is set correctly
2. Check Kelly fraction setting
3. Ensure min edge isn't too high

## Success Metrics

Track these over time:

**After 50 bets:**
- Win rate should be >35% for win bets
- Win rate should be >60% for place bets
- Actual ROI should be positive

**After 100 bets:**
- Model should be profitable
- Can consider increasing to 1/2 Kelly
- May add exotic bets if confident

**After 200 bets:**
- Clear evidence of edge
- Can optimize bet selection
- Consider increasing bankroll

---

## Quick Reference Card

```
📋 DAILY WORKFLOW
1. Fetch races (Upcoming Races tab)
2. Generate predictions (Predictions tab)
3. Configure settings (In The Money tab)
4. Find value bets
5. Place recommended bets
6. Export for records
7. Track results

💰 RECOMMENDED STARTING SETTINGS
Bankroll: $500-$1000
Kelly: 1/4 or 1/2
Min Edge: 10%
Bets: Win + Place only

🎯 SUCCESS CRITERIA
Track 50+ bets
Win rate >35% (win bets)
ROI positive
Odds available when betting
```

---

**Remember: Discipline beats luck. Stick to the system!** 🍀

