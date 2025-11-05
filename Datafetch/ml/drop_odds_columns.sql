-- Drop Odds Columns Migration
-- Removes all 12 odds-related columns from ml_features table
-- This eliminates data leakage by removing market-dependent features

-- SQLite doesn't support DROP COLUMN directly on multiple columns
-- We need to recreate the table without odds columns

BEGIN TRANSACTION;

-- Step 1: Create new table with only the columns we want (110 features + 2 auto)
CREATE TABLE ml_features_new (
    feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id TEXT NOT NULL,
    runner_id INTEGER NOT NULL,
    horse_id TEXT NOT NULL,
    -- Horse features (17)
    horse_age INTEGER,
    horse_career_runs INTEGER,
    horse_career_wins INTEGER,
    horse_win_rate REAL,
    horse_place_rate REAL,
    horse_avg_position REAL,
    horse_course_wins INTEGER,
    horse_distance_win_rate REAL,
    horse_going_win_rate REAL,
    horse_days_since_last INTEGER,
    horse_form_last_5_avg REAL,
    horse_form_improving INTEGER,
    horse_consistency REAL,
    horse_best_rating REAL,
    horse_best_tsr REAL,
    horse_avg_tsr_last_5 REAL,
    speed_improving INTEGER,
    typical_running_style INTEGER,
    -- Trainer features (8)
    trainer_win_rate_14d REAL,
    trainer_win_rate_90d REAL,
    trainer_strike_rate REAL,
    trainer_course_win_rate REAL,
    trainer_distance_win_rate REAL,
    trainer_roi REAL,
    trainer_form_with_horse REAL,
    trainer_rating REAL,
    -- Jockey features (7)
    jockey_win_rate_14d REAL,
    jockey_win_rate_90d REAL,
    jockey_strike_rate REAL,
    jockey_course_win_rate REAL,
    jockey_distance_win_rate REAL,
    jockey_roi REAL,
    jockey_rating REAL,
    -- Combo features (3)
    combo_win_rate REAL,
    combo_strike_rate REAL,
    combo_runs INTEGER,
    -- Race context (7)
    field_size INTEGER,
    race_class TEXT,
    race_class_encoded INTEGER,
    distance_f REAL,
    going_encoded INTEGER,
    surface_encoded INTEGER,
    prize_money REAL,
    -- Runner specific (7)
    runner_number INTEGER,
    draw INTEGER,
    weight_lbs REAL,
    ofr REAL,
    rpr REAL,
    ts REAL,
    headgear_encoded INTEGER,
    -- Relative features (15)
    rating_vs_avg REAL,
    weight_vs_avg REAL,
    age_vs_avg REAL,
    weight_lbs_rank INTEGER,
    age_rank INTEGER,
    field_best_rpr REAL,
    field_worst_rpr REAL,
    field_avg_rpr REAL,
    horse_rpr_rank INTEGER,
    horse_rpr_vs_best REAL,
    horse_rpr_vs_worst REAL,
    field_rpr_spread REAL,
    top_3_rpr_avg REAL,
    horse_in_top_quartile INTEGER,
    tsr_vs_field_avg REAL,
    pace_pressure_likely INTEGER,
    -- Draw features (4)
    course_distance_draw_bias REAL,
    draw_position_normalized REAL,
    low_draw_advantage INTEGER,
    high_draw_advantage INTEGER,
    -- Pedigree (3)
    sire_distance_win_rate REAL,
    sire_surface_win_rate REAL,
    dam_produce_win_rate REAL,
    -- Demographic (3)
    horse_sex_encoded INTEGER,
    horse_is_filly_mare INTEGER,
    horse_is_gelding INTEGER,
    -- Trainer recent (4)
    trainer_14d_runs INTEGER,
    trainer_14d_wins INTEGER,
    trainer_14d_win_pct REAL,
    trainer_is_hot INTEGER,
    -- Speed features (6) - NEW
    horse_avg_speed_furlongs_per_sec REAL,
    horse_best_speed_career REAL,
    horse_speed_last_3_avg REAL,
    horse_speed_improving_new REAL,
    horse_speed_vs_track_record REAL,
    horse_speed_consistency REAL,
    -- BTN features (12) - NEW
    horse_avg_btn_last_5 REAL,
    horse_median_btn_last_5 REAL,
    horse_btn_improving REAL,
    horse_pct_within_3_lengths REAL,
    horse_btn_vs_field_avg REAL,
    horse_btn_vs_winner_percentile REAL,
    horse_best_btn_career REAL,
    horse_btn_consistency REAL,
    horse_avg_ovr_btn_last_5 REAL,
    horse_ovr_btn_improving REAL,
    horse_ovr_btn_vs_field REAL,
    horse_pct_top_half_finishes REAL,
    -- Quality features (3) - NEW
    field_quality_rating REAL,
    race_competitiveness REAL,
    horse_beaten_by_quality REAL,
    -- Weather features (4) - NEW
    horse_soft_going_speed_ratio REAL,
    horse_weather_performance REAL,
    rail_position_advantage REAL,
    going_change_adaptation REAL,
    -- Weight features (2) - NEW
    horse_weight_adjusted_rating REAL,
    horse_weight_performance_trend REAL,
    -- Auto timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (race_id) REFERENCES races(race_id),
    FOREIGN KEY (runner_id) REFERENCES results(runner_id),
    FOREIGN KEY (horse_id) REFERENCES results(horse_id)
);

-- Step 2: Copy data from old table (excluding odds columns)
INSERT INTO ml_features_new SELECT 
    feature_id, race_id, runner_id, horse_id,
    horse_age, horse_career_runs, horse_career_wins,
    horse_win_rate, horse_place_rate, horse_avg_position,
    horse_course_wins, horse_distance_win_rate, horse_going_win_rate,
    horse_days_since_last, horse_form_last_5_avg, horse_form_improving,
    horse_consistency, horse_best_rating,
    horse_best_tsr, horse_avg_tsr_last_5, speed_improving, typical_running_style,
    trainer_win_rate_14d, trainer_win_rate_90d, trainer_strike_rate,
    trainer_course_win_rate, trainer_distance_win_rate, trainer_roi,
    trainer_form_with_horse, trainer_rating,
    jockey_win_rate_14d, jockey_win_rate_90d, jockey_strike_rate,
    jockey_course_win_rate, jockey_distance_win_rate, jockey_roi, jockey_rating,
    combo_win_rate, combo_strike_rate, combo_runs,
    field_size, race_class, race_class_encoded, distance_f, going_encoded,
    surface_encoded, prize_money,
    runner_number, draw, weight_lbs, ofr, rpr, ts, headgear_encoded,
    rating_vs_avg, weight_vs_avg, age_vs_avg, weight_lbs_rank, age_rank,
    field_best_rpr, field_worst_rpr, field_avg_rpr, horse_rpr_rank,
    horse_rpr_vs_best, horse_rpr_vs_worst, field_rpr_spread, top_3_rpr_avg,
    horse_in_top_quartile, tsr_vs_field_avg, pace_pressure_likely,
    course_distance_draw_bias, draw_position_normalized, low_draw_advantage, high_draw_advantage,
    sire_distance_win_rate, sire_surface_win_rate, dam_produce_win_rate,
    horse_sex_encoded, horse_is_filly_mare, horse_is_gelding,
    trainer_14d_runs, trainer_14d_wins, trainer_14d_win_pct, trainer_is_hot,
    horse_avg_speed_furlongs_per_sec, horse_best_speed_career,
    horse_speed_last_3_avg, horse_speed_improving_new,
    horse_speed_vs_track_record, horse_speed_consistency,
    horse_avg_btn_last_5, horse_median_btn_last_5,
    horse_btn_improving, horse_pct_within_3_lengths,
    horse_btn_vs_field_avg, horse_btn_vs_winner_percentile,
    horse_best_btn_career, horse_btn_consistency,
    horse_avg_ovr_btn_last_5, horse_ovr_btn_improving,
    horse_ovr_btn_vs_field, horse_pct_top_half_finishes,
    field_quality_rating, race_competitiveness,
    horse_beaten_by_quality,
    horse_soft_going_speed_ratio, horse_weather_performance,
    rail_position_advantage, going_change_adaptation,
    horse_weight_adjusted_rating, horse_weight_performance_trend,
    created_at
FROM ml_features;

-- Step 3: Drop old table
DROP TABLE ml_features;

-- Step 4: Rename new table
ALTER TABLE ml_features_new RENAME TO ml_features;

-- Step 5: Recreate indexes for performance
CREATE INDEX idx_ml_features_race ON ml_features(race_id);
CREATE INDEX idx_ml_features_runner ON ml_features(runner_id);
CREATE INDEX idx_ml_features_horse ON ml_features(horse_id);

COMMIT;

-- Verify the migration
SELECT 
    COUNT(*) as total_columns,
    SUM(CASE WHEN name LIKE '%odds%' OR name LIKE '%market%' THEN 1 ELSE 0 END) as odds_columns
FROM pragma_table_info('ml_features');

