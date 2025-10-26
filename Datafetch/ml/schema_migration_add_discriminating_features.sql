-- Schema Migration: Add Discriminating Features
-- Adds 18 new columns to ml_features table
-- Total features: 110 → 128

BEGIN TRANSACTION;

-- Market Position Feature (1 column)
ALTER TABLE ml_features ADD COLUMN market_position_tier INTEGER;

-- Class Movement Features (4 columns)
ALTER TABLE ml_features ADD COLUMN class_last_3_avg REAL;
ALTER TABLE ml_features ADD COLUMN class_change REAL;
ALTER TABLE ml_features ADD COLUMN dropping_in_class INTEGER;
ALTER TABLE ml_features ADD COLUMN rising_in_class INTEGER;

-- Course Specialist Features (5 columns)
ALTER TABLE ml_features ADD COLUMN course_runs INTEGER;
ALTER TABLE ml_features ADD COLUMN course_wins INTEGER;
ALTER TABLE ml_features ADD COLUMN course_win_rate REAL;
ALTER TABLE ml_features ADD COLUMN course_place_rate REAL;
ALTER TABLE ml_features ADD COLUMN course_specialist INTEGER;

-- Distance Optimization Features (4 columns)
ALTER TABLE ml_features ADD COLUMN best_distance_f REAL;
ALTER TABLE ml_features ADD COLUMN distance_from_optimal REAL;
ALTER TABLE ml_features ADD COLUMN runs_at_distance INTEGER;
ALTER TABLE ml_features ADD COLUMN win_rate_at_distance REAL;

-- Trainer Hot Streak Features (4 columns)
ALTER TABLE ml_features ADD COLUMN trainer_wins_last_14d INTEGER;
ALTER TABLE ml_features ADD COLUMN trainer_runs_last_14d INTEGER;
ALTER TABLE ml_features ADD COLUMN trainer_win_rate_recent REAL;
ALTER TABLE ml_features ADD COLUMN trainer_is_hot INTEGER;

COMMIT;

-- Verify migration
SELECT 
    'Migration Complete' as status,
    COUNT(*) as total_columns
FROM pragma_table_info('ml_features');

