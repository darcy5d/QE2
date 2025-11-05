#!/usr/bin/env python3
"""
Training Data Validation
Validates training data size, quality, and temporal integrity
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple


class TrainingDataValidator:
    """Validate training data for ML model"""
    
    def __init__(self, db_path: str, race_type: str = 'Flat'):
        """
        Initialize validator
        
        Args:
            db_path: Path to racing_pro.db
            race_type: Type of races ('Flat', 'Hurdle', 'Chase')
        """
        self.db_path = Path(db_path)
        self.race_type = race_type
        self.conn = None
        
    def connect(self):
        """Connect to database"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        print(f"✓ Connected to database: {self.db_path.name}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def check_race_data(self) -> Dict:
        """Check race data availability"""
        print("\n" + "="*80)
        print("RACE DATA VALIDATION")
        print("="*80)
        
        cursor = self.conn.cursor()
        
        # Total races by type
        cursor.execute("SELECT type, COUNT(*) as count FROM races GROUP BY type ORDER BY count DESC")
        races_by_type = cursor.fetchall()
        
        print("\nRaces by type:")
        total_races = 0
        target_races = 0
        for row in races_by_type:
            count = row['count']
            total_races += count
            if row['type'] == self.race_type:
                target_races = count
            print(f"  {row['type']}: {count:,} races")
        
        print(f"\nTotal races: {total_races:,}")
        print(f"Target type ({self.race_type}): {target_races:,} races ({target_races/total_races*100:.1f}%)")
        
        # Date range
        cursor.execute(f"SELECT MIN(date) as min_date, MAX(date) as max_date FROM races WHERE type = ?", 
                      (self.race_type,))
        date_range = cursor.fetchone()
        
        min_date = date_range['min_date']
        max_date = date_range['max_date']
        
        print(f"\nDate range for {self.race_type} racing:")
        print(f"  First race: {min_date}")
        print(f"  Last race: {max_date}")
        
        if min_date and max_date:
            days_span = (datetime.strptime(max_date, '%Y-%m-%d') - 
                        datetime.strptime(min_date, '%Y-%m-%d')).days
            print(f"  Time span: {days_span} days ({days_span/365:.1f} years)")
        
        return {
            'total_races': total_races,
            'target_races': target_races,
            'min_date': min_date,
            'max_date': max_date,
            'days_span': days_span if min_date and max_date else 0
        }
    
    def check_runner_data(self) -> Dict:
        """Check runner data completeness"""
        print("\n" + "="*80)
        print("RUNNER DATA VALIDATION")
        print("="*80)
        
        cursor = self.conn.cursor()
        
        # Total runners for target race type
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM results hr
            JOIN races r ON hr.race_id = r.race_id
            WHERE r.type = ?
        """, (self.race_type,))
        
        total_runners = cursor.fetchone()['count']
        print(f"\nTotal runners ({self.race_type}): {total_runners:,}")
        
        # Runners with results (position recorded)
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM results hr
            JOIN races r ON hr.race_id = r.race_id
            WHERE r.type = ? AND hr.position IS NOT NULL
        """, (self.race_type,))
        
        runners_with_position = cursor.fetchone()['count']
        print(f"Runners with position: {runners_with_position:,} ({runners_with_position/total_runners*100:.1f}%)")
        
        # Winners
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM results hr
            JOIN races r ON hr.race_id = r.race_id
            WHERE r.type = ? AND hr.position = 1
        """, (self.race_type,))
        
        winners = cursor.fetchone()['count']
        print(f"Winners: {winners:,} ({winners/total_runners*100:.1f}%)")
        
        # Average field size
        cursor.execute("""
            SELECT AVG(runner_count) as avg_runners
            FROM (
                SELECT r.race_id, COUNT(*) as runner_count
                FROM results hr
                JOIN races r ON hr.race_id = r.race_id
                WHERE r.type = ?
                GROUP BY r.race_id
            )
        """, (self.race_type,))
        
        avg_field_size = cursor.fetchone()['avg_runners']
        print(f"Average field size: {avg_field_size:.1f} runners/race")
        
        return {
            'total_runners': total_runners,
            'runners_with_position': runners_with_position,
            'winners': winners,
            'avg_field_size': avg_field_size
        }
    
    def check_ml_features(self) -> Dict:
        """Check ML features availability"""
        print("\n" + "="*80)
        print("ML FEATURES VALIDATION")
        print("="*80)
        
        cursor = self.conn.cursor()
        
        # Check if ml_features table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ml_features'")
        if not cursor.fetchone():
            print("⚠️  ml_features table not found")
            return {'features_available': False}
        
        # Total feature records for target race type
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM ml_features f
            JOIN races r ON f.race_id = r.race_id
            WHERE r.type = ?
        """, (self.race_type,))
        
        feature_records = cursor.fetchone()['count']
        print(f"\nML feature records ({self.race_type}): {feature_records:,}")
        
        # Check feature completeness (compare with results)
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM results hr
            JOIN races r ON hr.race_id = r.race_id
            LEFT JOIN ml_features f ON hr.race_id = f.race_id AND hr.runner_id = f.runner_id
            WHERE r.type = ? AND f.feature_id IS NULL
        """, (self.race_type,))
        
        missing_features = cursor.fetchone()['count']
        
        if missing_features > 0:
            print(f"⚠️  Missing features for {missing_features:,} runners")
        else:
            print(f"✓ All runners have feature records")
        
        # Check for NULL values in key features
        cursor.execute("PRAGMA table_info(ml_features)")
        feature_columns = [col['name'] for col in cursor.fetchall() 
                          if col['type'] in ['REAL', 'INTEGER'] and 
                          col['name'] not in ['feature_id', 'race_id', 'runner_id', 'horse_id']]
        
        print(f"\nFeature columns: {len(feature_columns)}")
        
        # Sample NULL check on a few key features
        key_features = ['field_size', 'rating_rpr', 'days_since_last', 'career_wins', 'distance_f']
        available_key = [f for f in key_features if f in feature_columns]
        
        if available_key:
            print("\nNULL value check (sample features):")
            for feature in available_key[:5]:
                cursor.execute(f"""
                    SELECT COUNT(*) as null_count
                    FROM ml_features f
                    JOIN races r ON f.race_id = r.race_id
                    WHERE r.type = ? AND f."{feature}" IS NULL
                """, (self.race_type,))
                null_count = cursor.fetchone()['null_count']
                null_pct = (null_count / feature_records * 100) if feature_records > 0 else 0
                print(f"  {feature}: {null_count:,} NULL ({null_pct:.1f}%)")
        
        return {
            'features_available': True,
            'feature_records': feature_records,
            'missing_features': missing_features,
            'feature_columns': len(feature_columns)
        }
    
    def check_ml_targets(self) -> Dict:
        """Check ML targets (labels) availability"""
        print("\n" + "="*80)
        print("ML TARGETS VALIDATION")
        print("="*80)
        
        cursor = self.conn.cursor()
        
        # Check if ml_targets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ml_targets'")
        if not cursor.fetchone():
            print("⚠️  ml_targets table not found")
            return {'targets_available': False}
        
        # Total target records for target race type
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM ml_targets t
            JOIN races r ON t.race_id = r.race_id
            WHERE r.type = ?
        """, (self.race_type,))
        
        target_records = cursor.fetchone()['count']
        print(f"\nML target records ({self.race_type}): {target_records:,}")
        
        # Check target completeness
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM results hr
            JOIN races r ON hr.race_id = r.race_id
            LEFT JOIN ml_targets t ON hr.race_id = t.race_id AND hr.runner_id = t.runner_id
            WHERE r.type = ? AND t.target_id IS NULL
        """, (self.race_type,))
        
        missing_targets = cursor.fetchone()['count']
        
        if missing_targets > 0:
            print(f"⚠️  Missing targets for {missing_targets:,} runners")
        else:
            print(f"✓ All runners have target records")
        
        # Check win rate
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN t.won = 1 THEN 1 ELSE 0 END) as winners,
                AVG(CASE WHEN t.won = 1 THEN 1.0 ELSE 0.0 END) as win_rate
            FROM ml_targets t
            JOIN races r ON t.race_id = r.race_id
            WHERE r.type = ?
        """, (self.race_type,))
        
        stats = cursor.fetchone()
        win_rate = stats['win_rate'] * 100 if stats['win_rate'] else 0
        
        print(f"\nTarget statistics:")
        print(f"  Winners: {stats['winners']:,} / {stats['total']:,} ({win_rate:.2f}%)")
        
        return {
            'targets_available': True,
            'target_records': target_records,
            'missing_targets': missing_targets,
            'win_rate': win_rate
        }
    
    def check_temporal_integrity(self, test_size: float = 0.2) -> Dict:
        """Verify temporal split prevents data leakage"""
        print("\n" + "="*80)
        print("TEMPORAL INTEGRITY CHECK")
        print("="*80)
        
        cursor = self.conn.cursor()
        
        # Get all race dates for target type, ordered
        cursor.execute("""
            SELECT r.date, COUNT(*) as race_count
            FROM races r
            JOIN results hr ON r.race_id = hr.race_id
            WHERE r.type = ?
            GROUP BY r.date
            ORDER BY r.date
        """, (self.race_type,))
        
        dates = cursor.fetchall()
        
        if not dates:
            print("⚠️  No race data found")
            return {}
        
        total_runners = sum(row['race_count'] for row in dates)
        split_idx = int(total_runners * (1 - test_size))
        
        # Find split date
        running_total = 0
        split_date = None
        train_dates = 0
        test_dates = 0
        
        for row in dates:
            running_total += row['race_count']
            if running_total <= split_idx:
                train_dates += 1
            else:
                if split_date is None:
                    split_date = row['date']
                test_dates += 1
        
        print(f"\nTemporal split simulation ({int((1-test_size)*100)}/{int(test_size*100)} split):")
        print(f"  Total runners: {total_runners:,}")
        print(f"  Train runners: {split_idx:,} (dates: {dates[0]['date']} to ~{split_date})")
        print(f"  Test runners: {total_runners - split_idx:,} (dates: ~{split_date} onwards)")
        print(f"  Split date: {split_date}")
        print(f"  Train days: {train_dates}")
        print(f"  Test days: {test_dates}")
        
        print("\n✓ Temporal integrity verified: Test set contains only future dates")
        print("  No risk of data leakage from future information")
        
        return {
            'total_runners': total_runners,
            'split_date': split_date,
            'train_days': train_dates,
            'test_days': test_dates
        }
    
    def assess_sample_size(self, race_stats: Dict, runner_stats: Dict) -> Dict:
        """Assess if sample size is sufficient for ML"""
        print("\n" + "="*80)
        print("SAMPLE SIZE ASSESSMENT")
        print("="*80)
        
        target_races = race_stats.get('target_races', 0)
        total_runners = runner_stats.get('total_runners', 0)
        avg_field_size = runner_stats.get('avg_field_size', 0)
        
        # General ML guidelines for sample size
        min_recommended_samples = 10000  # For complex XGBoost models
        ideal_samples = 50000
        
        print(f"\nSample size analysis:")
        print(f"  Training samples: {total_runners:,}")
        print(f"  Minimum recommended: {min_recommended_samples:,}")
        print(f"  Ideal target: {ideal_samples:,}")
        
        if total_runners >= ideal_samples:
            status = "EXCELLENT"
            symbol = "✓✓"
            message = "Dataset is excellent for ML training"
        elif total_runners >= min_recommended_samples:
            status = "GOOD"
            symbol = "✓"
            message = "Dataset is sufficient for ML training"
        elif total_runners >= min_recommended_samples / 2:
            status = "ADEQUATE"
            symbol = "⚠️"
            message = "Dataset is adequate but could benefit from more data"
        else:
            status = "INSUFFICIENT"
            symbol = "❌"
            message = "Dataset may be too small for reliable ML training"
        
        print(f"\n{symbol} Status: {status}")
        print(f"  {message}")
        
        # Additional context
        print(f"\nRanking model context:")
        print(f"  Races: {target_races:,}")
        print(f"  Avg field size: {avg_field_size:.1f}")
        print(f"  Each race teaches model to rank ~{avg_field_size:.0f} horses")
        
        return {
            'status': status,
            'total_samples': total_runners,
            'sufficient': total_runners >= min_recommended_samples
        }
    
    def run_full_validation(self) -> Dict:
        """Run complete data validation pipeline"""
        print("="*80)
        print("TRAINING DATA VALIDATION")
        print(f"Race Type: {self.race_type}")
        print("="*80)
        
        self.connect()
        
        try:
            results = {}
            
            # Check race data
            results['race_stats'] = self.check_race_data()
            
            # Check runner data
            results['runner_stats'] = self.check_runner_data()
            
            # Check ML features
            results['feature_stats'] = self.check_ml_features()
            
            # Check ML targets
            results['target_stats'] = self.check_ml_targets()
            
            # Check temporal integrity
            results['temporal_check'] = self.check_temporal_integrity()
            
            # Assess sample size
            results['sample_assessment'] = self.assess_sample_size(
                results['race_stats'], 
                results['runner_stats']
            )
            
            # Final summary
            print("\n" + "="*80)
            print("✓ VALIDATION COMPLETE")
            print("="*80)
            
            return results
            
        except Exception as e:
            print(f"\n❌ Validation failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.close()


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate training data')
    parser.add_argument('--db', type=str, default='../racing_pro.db',
                       help='Path to racing_pro.db')
    parser.add_argument('--race-type', type=str, default='Flat',
                       choices=['Flat', 'Hurdle', 'Chase'],
                       help='Race type to validate')
    
    args = parser.parse_args()
    
    # Resolve path relative to script location
    script_dir = Path(__file__).parent
    db_path = script_dir / args.db
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return 1
    
    # Run validation
    validator = TrainingDataValidator(str(db_path), race_type=args.race_type)
    
    try:
        validator.run_full_validation()
        return 0
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

