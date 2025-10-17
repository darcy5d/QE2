"""
Statistics Calculator - Comprehensive statistical analysis for database exploration
"""

import sqlite3
from typing import Dict, List, Any, Tuple
import json


class StatsCalculator:
    """Calculate comprehensive statistics for database tables and columns"""
    
    def __init__(self, db_helper):
        """Initialize with database helper"""
        self.db = db_helper
        self.conn = db_helper.conn
    
    def get_table_list(self) -> List[Tuple[str, int]]:
        """Get list of all tables with row counts"""
        cursor = self.conn.cursor()
        
        # Get all table names
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        # Get row count for each table
        table_info = []
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            table_info.append((table_name, row_count))
        
        return table_info
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get comprehensive information about a table"""
        cursor = self.conn.cursor()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        # Get schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Check if table has a date column
        date_range = None
        for col in columns:
            col_name = col[1]
            if col_name in ['date', 'dob', 'last_run']:
                try:
                    cursor.execute(f"SELECT MIN({col_name}), MAX({col_name}) FROM {table_name} WHERE {col_name} IS NOT NULL")
                    min_date, max_date = cursor.fetchone()
                    if min_date and max_date:
                        date_range = (col_name, min_date, max_date)
                        break
                except:
                    pass
        
        return {
            'table_name': table_name,
            'row_count': row_count,
            'column_count': len(columns),
            'columns': [(col[1], col[2]) for col in columns],  # (name, type)
            'date_range': date_range
        }
    
    def analyze_column(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """Perform comprehensive analysis of a column"""
        cursor = self.conn.cursor()
        
        # Get column type
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_type = None
        for col in columns:
            if col[1] == column_name:
                column_type = col[2]
                break
        
        if column_type is None:
            return {'error': f'Column {column_name} not found'}
        
        # Basic stats
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT({column_name}) FROM {table_name} WHERE {column_name} IS NOT NULL")
        non_null_count = cursor.fetchone()[0]
        
        null_count = total_count - non_null_count
        null_percentage = (null_count / total_count * 100) if total_count > 0 else 0
        
        # Get unique count
        cursor.execute(f"SELECT COUNT(DISTINCT {column_name}) FROM {table_name} WHERE {column_name} IS NOT NULL")
        unique_count = cursor.fetchone()[0]
        
        stats = {
            'column_name': column_name,
            'data_type': column_type,
            'total_count': total_count,
            'non_null_count': non_null_count,
            'null_count': null_count,
            'null_percentage': round(null_percentage, 2),
            'unique_count': unique_count
        }
        
        # Determine analysis type
        if self._is_numeric_column(table_name, column_name):
            stats.update(self.get_numeric_stats(table_name, column_name))
        elif self._is_date_column(column_name):
            stats.update(self.get_date_stats(table_name, column_name))
        else:
            stats.update(self.get_text_stats(table_name, column_name))
        
        return stats
    
    def _is_numeric_column(self, table_name: str, column_name: str) -> bool:
        """Check if column contains numeric data"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(f"SELECT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL LIMIT 1")
            sample = cursor.fetchone()
            if sample:
                value = sample[0]
                # Try to convert to float
                try:
                    float(str(value))
                    return True
                except:
                    return False
        except:
            pass
        return False
    
    def _is_date_column(self, column_name: str) -> bool:
        """Check if column is a date column by name"""
        date_keywords = ['date', 'dob', 'time', 'last_run']
        return any(keyword in column_name.lower() for keyword in date_keywords)
    
    def get_numeric_stats(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """Calculate statistics for numeric columns"""
        cursor = self.conn.cursor()
        
        # Get all non-null values
        cursor.execute(f"""
            SELECT CAST({column_name} AS REAL) 
            FROM {table_name} 
            WHERE {column_name} IS NOT NULL AND {column_name} != ''
            ORDER BY CAST({column_name} AS REAL)
        """)
        values = [row[0] for row in cursor.fetchall()]
        
        if not values:
            return {'analysis_type': 'numeric', 'note': 'No numeric values found'}
        
        n = len(values)
        
        # Basic stats
        mean = sum(values) / n
        minimum = min(values)
        maximum = max(values)
        
        # Median
        if n % 2 == 0:
            median = (values[n//2 - 1] + values[n//2]) / 2
        else:
            median = values[n//2]
        
        # Quartiles
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = values[q1_idx]
        q3 = values[q3_idx]
        
        # Standard deviation
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = variance ** 0.5
        
        # Skewness (Pearson's second coefficient)
        skewness = 3 * (mean - median) / std_dev if std_dev != 0 else 0
        
        # Mode (most common value)
        from collections import Counter
        value_counts = Counter(values)
        mode = value_counts.most_common(1)[0][0] if value_counts else None
        
        return {
            'analysis_type': 'numeric',
            'mean': round(mean, 4),
            'median': round(median, 4),
            'mode': round(mode, 4) if mode is not None else None,
            'std_dev': round(std_dev, 4),
            'min': round(minimum, 4),
            'max': round(maximum, 4),
            'q1': round(q1, 4),
            'q3': round(q3, 4),
            'skewness': round(skewness, 4),
            'range': round(maximum - minimum, 4)
        }
    
    def get_text_stats(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """Calculate statistics for text columns"""
        cursor = self.conn.cursor()
        
        # Most common values
        cursor.execute(f"""
            SELECT {column_name}, COUNT(*) as freq
            FROM {table_name}
            WHERE {column_name} IS NOT NULL AND {column_name} != ''
            GROUP BY {column_name}
            ORDER BY freq DESC
            LIMIT 15
        """)
        most_common = cursor.fetchall()
        
        # Character length stats
        cursor.execute(f"""
            SELECT 
                AVG(LENGTH({column_name})) as avg_len,
                MIN(LENGTH({column_name})) as min_len,
                MAX(LENGTH({column_name})) as max_len
            FROM {table_name}
            WHERE {column_name} IS NOT NULL AND {column_name} != ''
        """)
        len_stats = cursor.fetchone()
        
        return {
            'analysis_type': 'text',
            'most_common': [(str(val), freq) for val, freq in most_common],
            'avg_length': round(len_stats[0], 2) if len_stats[0] else 0,
            'min_length': len_stats[1] if len_stats[1] else 0,
            'max_length': len_stats[2] if len_stats[2] else 0
        }
    
    def get_date_stats(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """Calculate statistics for date columns"""
        cursor = self.conn.cursor()
        
        # Date range
        cursor.execute(f"""
            SELECT MIN({column_name}), MAX({column_name})
            FROM {table_name}
            WHERE {column_name} IS NOT NULL AND {column_name} != ''
        """)
        min_date, max_date = cursor.fetchone()
        
        # Distribution by month (if enough data)
        try:
            cursor.execute(f"""
                SELECT substr({column_name}, 1, 7) as month, COUNT(*) as count
                FROM {table_name}
                WHERE {column_name} IS NOT NULL AND {column_name} != ''
                GROUP BY month
                ORDER BY month
                LIMIT 12
            """)
            monthly_dist = cursor.fetchall()
        except:
            monthly_dist = []
        
        return {
            'analysis_type': 'date',
            'min_date': min_date,
            'max_date': max_date,
            'monthly_distribution': [(month, count) for month, count in monthly_dist]
        }
    
    def export_table_stats_csv(self, table_name: str, filepath: str):
        """Export table statistics to CSV"""
        import csv
        
        table_info = self.get_table_info(table_name)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Table Statistics', table_name])
            writer.writerow(['Total Rows', table_info['row_count']])
            writer.writerow(['Total Columns', table_info['column_count']])
            writer.writerow([])
            
            if table_info['date_range']:
                col_name, min_d, max_d = table_info['date_range']
                writer.writerow(['Date Range', f'{min_d} to {max_d}'])
                writer.writerow([])
            
            writer.writerow(['Column Name', 'Data Type'])
            for col_name, col_type in table_info['columns']:
                writer.writerow([col_name, col_type])
    
    def export_column_stats_json(self, table_name: str, column_name: str, filepath: str):
        """Export column statistics to JSON"""
        stats = self.analyze_column(table_name, column_name)
        
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)

