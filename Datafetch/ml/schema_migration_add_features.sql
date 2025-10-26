-- Schema Migration: Add 27 New Features to ml_features Table
-- Removes reliance on odds features (data leakage)
-- Adds fundamental features: speed, BTN, quality, weather, weight

-- Speed Features (6 columns)
ALTER TABLE ml_features ADD COLUMN horse_avg_speed_furlongs_per_sec REAL;
ALTER TABLE ml_features ADD COLUMN horse_best_speed_career REAL;
ALTER TABLE ml_features ADD COLUMN horse_speed_last_3_avg REAL;
ALTER TABLE ml_features ADD COLUMN horse_speed_improving_new REAL;
ALTER TABLE ml_features ADD COLUMN horse_speed_vs_track_record REAL;
ALTER TABLE ml_features ADD COLUMN horse_speed_consistency REAL;

-- BTN (Beaten By) Features (12 columns)
ALTER TABLE ml_features ADD COLUMN horse_avg_btn_last_5 REAL;
ALTER TABLE ml_features ADD COLUMN horse_median_btn_last_5 REAL;
ALTER TABLE ml_features ADD COLUMN horse_btn_improving REAL;
ALTER TABLE ml_features ADD COLUMN horse_pct_within_3_lengths REAL;
ALTER TABLE ml_features ADD COLUMN horse_btn_vs_field_avg REAL;
ALTER TABLE ml_features ADD COLUMN horse_btn_vs_winner_percentile REAL;
ALTER TABLE ml_features ADD COLUMN horse_best_btn_career REAL;
ALTER TABLE ml_features ADD COLUMN horse_btn_consistency REAL;
ALTER TABLE ml_features ADD COLUMN horse_avg_ovr_btn_last_5 REAL;
ALTER TABLE ml_features ADD COLUMN horse_ovr_btn_improving REAL;
ALTER TABLE ml_features ADD COLUMN horse_ovr_btn_vs_field REAL;
ALTER TABLE ml_features ADD COLUMN horse_pct_top_half_finishes REAL;

-- Quality Features (3 columns)
ALTER TABLE ml_features ADD COLUMN field_quality_rating REAL;
ALTER TABLE ml_features ADD COLUMN race_competitiveness REAL;
ALTER TABLE ml_features ADD COLUMN horse_beaten_by_quality REAL;

-- Weather/Going Features (4 columns)
ALTER TABLE ml_features ADD COLUMN horse_soft_going_speed_ratio REAL;
ALTER TABLE ml_features ADD COLUMN horse_weather_performance REAL;
ALTER TABLE ml_features ADD COLUMN rail_position_advantage REAL;
ALTER TABLE ml_features ADD COLUMN going_change_adaptation REAL;

-- Weight-Adjusted Features (2 columns)
ALTER TABLE ml_features ADD COLUMN horse_weight_adjusted_rating REAL;
ALTER TABLE ml_features ADD COLUMN horse_weight_performance_trend REAL;

-- Verify migration
SELECT 
    COUNT(*) as total_columns,
    SUM(CASE WHEN name LIKE 'horse_avg_speed%' THEN 1 ELSE 0 END) as speed_cols,
    SUM(CASE WHEN name LIKE '%btn%' THEN 1 ELSE 0 END) as btn_cols,
    SUM(CASE WHEN name LIKE '%quality%' OR name LIKE '%competitive%' OR name LIKE '%beaten_by%' THEN 1 ELSE 0 END) as quality_cols,
    SUM(CASE WHEN name LIKE '%going%' OR name LIKE '%weather%' OR name LIKE '%rail%' THEN 1 ELSE 0 END) as weather_cols,
    SUM(CASE WHEN name LIKE '%weight_adjusted%' OR name LIKE '%weight_performance%' THEN 1 ELSE 0 END) as weight_cols
FROM pragma_table_info('ml_features');

