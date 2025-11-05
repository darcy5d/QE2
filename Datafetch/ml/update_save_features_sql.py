#!/usr/bin/env python3
"""
Helper script to generate the updated save_features SQL
Removes 12 odds columns, adds 27 new feature columns
"""

# Current columns (91 features)
OLD_COLUMNS = [
    # IDs
    'race_id', 'runner_id', 'horse_id',
    # Horse features (17)
    'horse_age', 'horse_career_runs', 'horse_career_wins',
    'horse_win_rate', 'horse_place_rate', 'horse_avg_position',
    'horse_course_wins', 'horse_distance_win_rate', 'horse_going_win_rate',
    'horse_days_since_last', 'horse_form_last_5_avg', 'horse_form_improving',
    'horse_consistency', 'horse_best_rating',
    'horse_best_tsr', 'horse_avg_tsr_last_5', 'speed_improving', 'typical_running_style',
    # Trainer features (8)
    'trainer_win_rate_14d', 'trainer_win_rate_90d', 'trainer_strike_rate',
    'trainer_course_win_rate', 'trainer_distance_win_rate', 'trainer_roi',
    'trainer_form_with_horse', 'trainer_rating',
    # Jockey features (7)
    'jockey_win_rate_14d', 'jockey_win_rate_90d', 'jockey_strike_rate',
    'jockey_course_win_rate', 'jockey_distance_win_rate', 'jockey_roi', 'jockey_rating',
    # Combo features (3)
    'combo_win_rate', 'combo_strike_rate', 'combo_runs',
    # Race context (7)
    'field_size', 'race_class', 'race_class_encoded', 'distance_f', 'going_encoded',
    'surface_encoded', 'prize_money',
    # Runner specific (7)
    'runner_number', 'draw', 'weight_lbs', 'ofr', 'rpr', 'ts', 'headgear_encoded',
    # Relative features (7)
    'rating_vs_avg', 'weight_vs_avg', 'age_vs_avg', 'weight_lbs_rank', 'age_rank',
    'field_best_rpr', 'field_worst_rpr', 'field_avg_rpr', 'horse_rpr_rank',
    'horse_rpr_vs_best', 'horse_rpr_vs_worst', 'field_rpr_spread', 'top_3_rpr_avg',
    'horse_in_top_quartile', 'tsr_vs_field_avg', 'pace_pressure_likely',
    # Draw features (4)
    'course_distance_draw_bias', 'draw_position_normalized', 'low_draw_advantage', 'high_draw_advantage',
    # ODDS FEATURES TO REMOVE (12)
    'odds_rank', 'opening_odds', 'final_odds', 'odds_movement', 'market_rank',
    'odds_implied_prob', 'odds_is_favorite', 'odds_favorite_rank', 'odds_decimal',
    'odds_bookmaker_count', 'odds_spread', 'odds_market_stability',
    # Pedigree (3)
    'sire_distance_win_rate', 'sire_surface_win_rate', 'dam_produce_win_rate',
    # Demographic (3)
    'horse_sex_encoded', 'horse_is_filly_mare', 'horse_is_gelding',
    # Trainer recent form (4)
    'trainer_14d_runs', 'trainer_14d_wins', 'trainer_14d_win_pct', 'trainer_is_hot'
]

# Odds columns to remove
ODDS_COLUMNS = [
    'odds_rank', 'opening_odds', 'final_odds', 'odds_movement', 'market_rank',
    'odds_implied_prob', 'odds_is_favorite', 'odds_favorite_rank', 'odds_decimal',
    'odds_bookmaker_count', 'odds_spread', 'odds_market_stability'
]

# New columns to add (27 features)
NEW_COLUMNS = [
    # Speed features (6)
    'horse_avg_speed_furlongs_per_sec', 'horse_best_speed_career',
    'horse_speed_last_3_avg', 'horse_speed_improving_new',  # Renamed to avoid conflict
    'horse_speed_vs_track_record', 'horse_speed_consistency',
    # BTN features (12)
    'horse_avg_btn_last_5', 'horse_median_btn_last_5',
    'horse_btn_improving', 'horse_pct_within_3_lengths',
    'horse_btn_vs_field_avg', 'horse_btn_vs_winner_percentile',
    'horse_best_btn_career', 'horse_btn_consistency',
    'horse_avg_ovr_btn_last_5', 'horse_ovr_btn_improving',
    'horse_ovr_btn_vs_field', 'horse_pct_top_half_finishes',
    # Quality features (3)
    'field_quality_rating', 'race_competitiveness',
    'horse_beaten_by_quality',
    # Weather features (4)
    'horse_soft_going_speed_ratio', 'horse_weather_performance',
    'rail_position_advantage', 'going_change_adaptation',
    # Weight features (2)
    'horse_weight_adjusted_rating', 'horse_weight_performance_trend'
]

# Generate new column list
columns_without_odds = [c for c in OLD_COLUMNS if c not in ODDS_COLUMNS]
new_columns_list = columns_without_odds + NEW_COLUMNS

print("="*80)
print("UPDATED COLUMN LIST (106 features)")
print("="*80)
print(f"Old count: {len(OLD_COLUMNS)} - Removed: {len(ODDS_COLUMNS)} + Added: {len(NEW_COLUMNS)} = New count: {len(new_columns_list)}")
print()

# Generate SQL column names
sql_columns = ",\n                    ".join(new_columns_list)
print("SQL Column Names:")
print("=" *80)
print(f"                    {sql_columns}")
print()

# Generate placeholders
placeholders = ", ".join(["?"] * len(new_columns_list))
print("SQL Placeholders:")
print("="*80)
print(f"                    {placeholders}")
print()

# Generate feature accessor list for Python
print("Python Feature Accessors:")
print("="*80)
for col in new_columns_list:
    if col in ['race_id', 'runner_id', 'horse_id']:
        print(f"                features['{col}'],")
    else:
        # Use .get() with defaults for optional features
        print(f"                features.get('{col}'),")

print()
print("="*80)
print(f"TOTAL: {len(new_columns_list)} columns (was {len(OLD_COLUMNS)})")
print("="*80)

