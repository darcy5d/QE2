"""
ML Database Helper
Centralized database queries for ML features and models
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class MLDatabaseHelper:
    """Helper class for ML-specific database queries"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_feature_statistics(self) -> pd.DataFrame:
        """Calculate statistics for all features"""
        conn = self.get_connection()
        
        # Get all numeric columns from ml_features table
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(ml_features)")
        columns = cursor.fetchall()
        
        feature_cols = []
        for col in columns:
            col_name = col['name']
            col_type = col['type']
            print(f"Column: {col_name}, Type: {col_type}")  # Debug
            # Skip ID columns and created_at
            if col_name not in ['feature_id', 'race_id', 'runner_id', 'horse_id', 
                                'created_at', 'race_class'] and col_type in ['REAL', 'INTEGER']:
                feature_cols.append(col_name)
        
        print(f"Feature columns to process: {feature_cols}")  # Debug
        
        # Calculate statistics for each feature
        stats_data = []
        for col in feature_cols:
            # Skip if column is None or empty
            if not col or col is None:
                continue
            
            try:
                # First query: basic statistics
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT("{col}") as non_null_count,
                        AVG("{col}") as mean_val,
                        MIN("{col}") as min_val,
                        MAX("{col}") as max_val
                    FROM ml_features
                """)
                row = cursor.fetchone()
                
                total = row['total_count']
                non_null = row['non_null_count']
                missing_pct = ((total - non_null) / total * 100) if total > 0 else 0
                
                # Calculate std dev only if we have a valid mean
                std_val = 0
                mean_val = row['mean_val']
                if mean_val is not None and non_null > 1:
                    cursor.execute(f"""
                        SELECT 
                            AVG(("{col}" - ?) * ("{col}" - ?)) as variance
                        FROM ml_features
                        WHERE "{col}" IS NOT NULL
                    """, (mean_val, mean_val))
                    var_row = cursor.fetchone()
                    if var_row and var_row['variance']:
                        std_val = var_row['variance'] ** 0.5
            except Exception as e:
                print(f"Error processing column '{col}': {e}")
                continue
            
            # Helper to safely format numeric values
            def format_num(val):
                if val is None:
                    return 'N/A'
                try:
                    return f"{float(val):.3f}"
                except (ValueError, TypeError):
                    return 'N/A'
            
            stats_data.append({
                'Feature': col,
                'Count': non_null,
                'Missing %': f"{missing_pct:.1f}",
                'Mean': format_num(row['mean_val']),
                'Std': format_num(std_val),
                'Min': format_num(row['min_val']),
                'Max': format_num(row['max_val'])
            })
        
        conn.close()
        return pd.DataFrame(stats_data)
    
    def get_sample_features(self, offset: int = 0, limit: int = 50, 
                           search_term: str = None) -> List[Dict]:
        """Get sample feature data with pagination"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build query
        where_clause = ""
        params = []
        
        if search_term:
            where_clause = """
                WHERE f.race_id LIKE ? 
                OR h.name LIKE ?
                OR f.runner_id IN (
                    SELECT runner_id FROM runners r 
                    WHERE r.horse_id IN (
                        SELECT horse_id FROM horses WHERE name LIKE ?
                    )
                )
            """
            search_pattern = f"%{search_term}%"
            params = [search_pattern, search_pattern, search_pattern]
        
        query = f"""
            SELECT 
                f.race_id,
                f.runner_id,
                h.name as horse_name,
                rac.date,
                f.horse_age,
                f.horse_win_rate,
                f.trainer_win_rate_90d,
                f.jockey_win_rate_90d,
                f.ofr,
                f.field_size,
                f.distance_f,
                f.weight_lbs,
                t.won as result
            FROM ml_features f
            LEFT JOIN horses h ON f.horse_id = h.horse_id
            LEFT JOIN races rac ON f.race_id = rac.race_id
            LEFT JOIN ml_targets t ON f.race_id = t.race_id AND f.runner_id = t.runner_id
            {where_clause}
            ORDER BY rac.date DESC
            LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append(dict(row))
        
        conn.close()
        return results
    
    def get_feature_count(self) -> int:
        """Get total number of feature vectors"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM ml_features")
        count = cursor.fetchone()['count']
        conn.close()
        return count
    
    def get_target_count(self) -> int:
        """Get total number of targets (race results)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM ml_targets")
        count = cursor.fetchone()['count']
        conn.close()
        return count
    
    def get_feature_completeness(self) -> Dict[str, float]:
        """Calculate feature completeness by category"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM ml_features")
        total = cursor.fetchone()['total']
        
        if total == 0:
            return {}
        
        categories = {
            'Horse Features': ['horse_age', 'horse_career_runs', 'horse_win_rate', 
                              'horse_form_last_5_avg'],
            'Trainer Features': ['trainer_win_rate_14d', 'trainer_win_rate_90d', 
                                'trainer_strike_rate'],
            'Jockey Features': ['jockey_win_rate_14d', 'jockey_win_rate_90d', 
                               'jockey_strike_rate'],
            'Race Context': ['distance_f', 'going_encoded', 'field_size', 'prize_money'],
            'Runner Specific': ['ofr', 'rpr', 'weight_lbs', 'draw']
        }
        
        completeness = {}
        for category, cols in categories.items():
            # Calculate average completeness for columns in category
            non_null_counts = []
            for col in cols:
                try:
                    cursor.execute(f"SELECT COUNT({col}) as count FROM ml_features WHERE {col} IS NOT NULL")
                    count = cursor.fetchone()['count']
                    non_null_counts.append(count / total * 100)
                except:
                    pass
            
            if non_null_counts:
                completeness[category] = sum(non_null_counts) / len(non_null_counts)
        
        conn.close()
        return completeness
    
    def get_date_range(self) -> Tuple[Optional[str], Optional[str]]:
        """Get date range of feature data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MIN(r.date) as min_date, MAX(r.date) as max_date
            FROM ml_features f
            JOIN races r ON f.race_id = r.race_id
        """)
        row = cursor.fetchone()
        conn.close()
        
        return (row['min_date'], row['max_date'])
    
    def get_trained_models(self) -> List[Dict]:
        """Get list of trained models from filesystem"""
        models_dir = Path(self.db_path).parent / 'ml' / 'models'
        
        if not models_dir.exists():
            return []
        
        models = []
        for model_file in models_dir.glob('*.json'):
            # Get file stats
            stat = model_file.stat()
            models.append({
                'name': model_file.stem,
                'path': str(model_file),
                'size': stat.st_size,
                'modified': stat.st_mtime
            })
        
        return sorted(models, key=lambda x: x['modified'], reverse=True)
    
    def get_full_features_for_runner(self, runner_id: int) -> Dict:
        """Get all features for a specific runner"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM ml_features WHERE runner_id = ?", (runner_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {}

