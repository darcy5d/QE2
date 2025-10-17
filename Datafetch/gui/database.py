"""
Database Helper for Racecard GUI
Provides query methods for all data access needs
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any


class DatabaseHelper:
    """Helper class for database queries"""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        if db_path is None:
            # Default to racing_pro.db in Datafetch directory
            db_path = Path(__file__).parent.parent / "racing_pro.db"
        
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Access columns by name
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ========================================================================
    # NAVIGATION QUERIES
    # ========================================================================
    
    def get_regions(self) -> List[str]:
        """Get list of unique regions"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT region 
            FROM races 
            WHERE region IS NOT NULL AND region != ''
            ORDER BY region
        """)
        return [row[0] for row in cursor.fetchall()]
    
    def get_courses(self, region: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Get list of courses, optionally filtered by region
        Returns: List of (course_name, course_id) tuples
        """
        cursor = self.conn.cursor()
        
        if region and region != "All":
            cursor.execute("""
                SELECT DISTINCT course, course_id
                FROM races
                WHERE region = ?
                ORDER BY course
            """, (region,))
        else:
            cursor.execute("""
                SELECT DISTINCT course, course_id
                FROM races
                ORDER BY course
            """)
        
        return [(row[0], row[1]) for row in cursor.fetchall()]
    
    def get_filtered_options(
        self,
        option_type: str,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
        region: Optional[str] = None,
        course: Optional[str] = None
    ) -> List[str]:
        """
        Get available options for a specific filter type based on other active filters
        
        Args:
            option_type: 'year', 'month', 'day', 'region', or 'course'
            Other params: Currently active filter values (excluding the one being queried)
            
        Returns:
            List of available values for the requested option type
        """
        cursor = self.conn.cursor()
        
        # Build WHERE clause based on active filters (excluding the one we're querying)
        where_clauses = []
        params = []
        
        if option_type != 'year' and year and year != "All":
            where_clauses.append("substr(date, 1, 4) = ?")
            params.append(year)
        
        if option_type != 'month' and month and month != "All":
            # Convert month name to number if needed
            if month.isdigit():
                month_num = month
            else:
                month_map = {
                    "January": "01", "February": "02", "March": "03",
                    "April": "04", "May": "05", "June": "06",
                    "July": "07", "August": "08", "September": "09",
                    "October": "10", "November": "11", "December": "12"
                }
                month_num = month_map.get(month, month)
            where_clauses.append("substr(date, 6, 2) = ?")
            params.append(month_num.zfill(2))
        
        if option_type != 'day' and day and day != "All":
            where_clauses.append("substr(date, 9, 2) = ?")
            params.append(day.zfill(2))
        
        if option_type != 'region' and region and region != "All":
            where_clauses.append("region = ?")
            params.append(region)
        
        if option_type != 'course' and course and course != "All":
            where_clauses.append("course = ?")
            params.append(course)
        
        # Build query based on option type
        if option_type == 'year':
            query = "SELECT DISTINCT substr(date, 1, 4) as year FROM races"
            order_by = " ORDER BY year"
        elif option_type == 'month':
            query = "SELECT DISTINCT substr(date, 6, 2) as month FROM races"
            order_by = " ORDER BY month"
        elif option_type == 'day':
            query = "SELECT DISTINCT substr(date, 9, 2) as day FROM races"
            order_by = " ORDER BY day"
        elif option_type == 'region':
            query = "SELECT DISTINCT region FROM races"
            # Add region validity check to where_clauses
            where_clauses.insert(0, "region IS NOT NULL AND region != ''")
            order_by = " ORDER BY region"
        elif option_type == 'course':
            query = "SELECT DISTINCT course FROM races"
            order_by = " ORDER BY course"
        else:
            return []
        
        # Add WHERE clause if there are active filters
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += order_by
        
        cursor.execute(query, params)
        return [row[0] for row in cursor.fetchall()]
    
    def get_available_dates(self, course: Optional[str] = None) -> List[str]:
        """
        Get list of dates with races, optionally filtered by course
        Returns: List of dates in YYYY-MM-DD format
        """
        cursor = self.conn.cursor()
        
        if course:
            cursor.execute("""
                SELECT DISTINCT date
                FROM races
                WHERE course = ?
                ORDER BY date
            """, (course,))
        else:
            cursor.execute("""
                SELECT DISTINCT date
                FROM races
                ORDER BY date
            """)
        
        return [row[0] for row in cursor.fetchall()]
    
    def get_years(self) -> List[str]:
        """Get list of unique years in dataset"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT substr(date, 1, 4) as year
            FROM races
            ORDER BY year
        """)
        return [row[0] for row in cursor.fetchall()]
    
    def get_months(self, year: str) -> List[str]:
        """Get list of months with races for a given year"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT substr(date, 6, 2) as month
            FROM races
            WHERE substr(date, 1, 4) = ?
            ORDER BY month
        """, (year,))
        return [row[0] for row in cursor.fetchall()]
    
    def get_days(self, year: str, month: str) -> List[str]:
        """Get list of days with races for a given year and month"""
        cursor = self.conn.cursor()
        year_month = f"{year}-{month}"
        cursor.execute("""
            SELECT DISTINCT substr(date, 9, 2) as day
            FROM races
            WHERE substr(date, 1, 7) = ?
            ORDER BY day
        """, (year_month,))
        return [row[0] for row in cursor.fetchall()]
    
    def get_races_for_date(self, course: str, date: str) -> List[Dict[str, Any]]:
        """
        Get list of races for a specific course and date
        Returns: List of race dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                race_id,
                course,
                date,
                off_time,
                race_name,
                race_class,
                field_size
            FROM races
            WHERE course = ? AND date = ?
            ORDER BY off_time
        """, (course, date))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_races_for_date_all_courses(self, date: str) -> List[Dict[str, Any]]:
        """Get all races for a specific date across all courses"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                race_id,
                course,
                date,
                off_time,
                race_name,
                race_class,
                field_size
            FROM races
            WHERE date = ?
            ORDER BY off_time, course
        """, (date,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_races_filtered(
        self,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
        region: Optional[str] = None,
        course: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get races with independent filter combination
        All filters are optional and work independently
        
        Args:
            year: Filter by year (e.g., "2023")
            month: Filter by month (e.g., "01" or "January")
            day: Filter by day (e.g., "15")
            region: Filter by region (e.g., "GB")
            course: Filter by course name (e.g., "Musselburgh")
            
        Returns:
            List of race dictionaries matching all specified filters
        """
        cursor = self.conn.cursor()
        
        # Build WHERE clause dynamically
        where_clauses = []
        params = []
        
        if year and year != "All":
            where_clauses.append("substr(date, 1, 4) = ?")
            params.append(year)
        
        if month and month != "All":
            # Handle month as number (01-12) or name
            if month.isdigit():
                month_num = month
            else:
                # Convert month name to number
                month_map = {
                    "January": "01", "February": "02", "March": "03",
                    "April": "04", "May": "05", "June": "06",
                    "July": "07", "August": "08", "September": "09",
                    "October": "10", "November": "11", "December": "12"
                }
                month_num = month_map.get(month, month)
            where_clauses.append("substr(date, 6, 2) = ?")
            params.append(month_num.zfill(2))
        
        if day and day != "All":
            where_clauses.append("substr(date, 9, 2) = ?")
            params.append(day.zfill(2))
        
        if region and region != "All":
            where_clauses.append("region = ?")
            params.append(region)
        
        if course and course != "All":
            where_clauses.append("course = ?")
            params.append(course)
        
        # Build final query
        query = """
            SELECT 
                race_id,
                course,
                date,
                off_time,
                race_name,
                race_class,
                field_size,
                region
            FROM races
        """
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY date, off_time, course"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # RACE DETAILS
    # ========================================================================
    
    def get_race_details(self, race_id: str) -> Optional[Dict[str, Any]]:
        """Get complete race details with all runners"""
        cursor = self.conn.cursor()
        
        # Get race info
        cursor.execute("""
            SELECT *
            FROM races
            WHERE race_id = ?
        """, (race_id,))
        
        race = cursor.fetchone()
        if not race:
            return None
        
        race_dict = dict(race)
        
        # Get runners with related entities
        cursor.execute("""
            SELECT 
                ru.runner_id,
                ru.number,
                ru.draw,
                ru.lbs,
                ru.ofr,
                ru.rpr,
                ru.ts,
                ru.form,
                ru.last_run,
                ru.comment,
                ru.spotlight,
                h.horse_id,
                h.name as horse_name,
                h.age,
                h.sex,
                t.trainer_id,
                t.name as trainer_name,
                t.location as trainer_location,
                j.jockey_id,
                j.name as jockey_name,
                o.owner_id,
                o.name as owner_name
            FROM runners ru
            LEFT JOIN horses h ON ru.horse_id = h.horse_id
            LEFT JOIN trainers t ON ru.trainer_id = t.trainer_id
            LEFT JOIN jockeys j ON ru.jockey_id = j.jockey_id
            LEFT JOIN owners o ON ru.owner_id = o.owner_id
            WHERE ru.race_id = ?
            ORDER BY CAST(ru.number AS INTEGER)
        """, (race_id,))
        
        race_dict['runners'] = [dict(row) for row in cursor.fetchall()]
        
        return race_dict
    
    # ========================================================================
    # ENTITY PROFILES
    # ========================================================================
    
    def get_horse_profile(self, horse_id: str) -> Optional[Dict[str, Any]]:
        """Get complete horse profile with pedigree and runs"""
        cursor = self.conn.cursor()
        
        # Get horse details with pedigree
        cursor.execute("""
            SELECT 
                h.*,
                d.name as dam_name,
                s.name as sire_name,
                ds.name as damsire_name
            FROM horses h
            LEFT JOIN dams d ON h.dam_id = d.dam_id
            LEFT JOIN sires s ON h.sire_id = s.sire_id
            LEFT JOIN damsires ds ON h.damsire_id = ds.damsire_id
            WHERE h.horse_id = ?
        """, (horse_id,))
        
        horse = cursor.fetchone()
        if not horse:
            return None
        
        horse_dict = dict(horse)
        
        # Get recent runs
        cursor.execute("""
            SELECT 
                r.date,
                r.course,
                r.race_name,
                r.distance,
                r.going,
                ru.number,
                ru.draw,
                t.name as trainer_name,
                j.name as jockey_name
            FROM runners ru
            JOIN races r ON ru.race_id = r.race_id
            LEFT JOIN trainers t ON ru.trainer_id = t.trainer_id
            LEFT JOIN jockeys j ON ru.jockey_id = j.jockey_id
            WHERE ru.horse_id = ?
            ORDER BY r.date DESC
            LIMIT 20
        """, (horse_id,))
        
        horse_dict['runs'] = [dict(row) for row in cursor.fetchall()]
        
        return horse_dict
    
    def get_trainer_profile(self, trainer_id: str) -> Optional[Dict[str, Any]]:
        """Get trainer profile with statistics and recent runners"""
        cursor = self.conn.cursor()
        
        # Get trainer details
        cursor.execute("""
            SELECT *
            FROM trainers
            WHERE trainer_id = ?
        """, (trainer_id,))
        
        trainer = cursor.fetchone()
        if not trainer:
            return None
        
        trainer_dict = dict(trainer)
        
        # Get runner count
        cursor.execute("""
            SELECT COUNT(*) as runner_count
            FROM runners
            WHERE trainer_id = ?
        """, (trainer_id,))
        
        trainer_dict['runner_count'] = cursor.fetchone()[0]
        
        # Get recent runners
        cursor.execute("""
            SELECT 
                r.date,
                r.course,
                r.race_name,
                h.name as horse_name,
                h.horse_id,
                j.name as jockey_name,
                ru.number
            FROM runners ru
            JOIN races r ON ru.race_id = r.race_id
            JOIN horses h ON ru.horse_id = h.horse_id
            LEFT JOIN jockeys j ON ru.jockey_id = j.jockey_id
            WHERE ru.trainer_id = ?
            ORDER BY r.date DESC
            LIMIT 30
        """, (trainer_id,))
        
        trainer_dict['recent_runners'] = [dict(row) for row in cursor.fetchall()]
        
        # Get 14-day stats if available
        cursor.execute("""
            SELECT stat_key, stat_value
            FROM trainer_14_days
            WHERE trainer_id = ?
        """, (trainer_id,))
        
        trainer_dict['stats_14_days'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        return trainer_dict
    
    def get_jockey_profile(self, jockey_id: str) -> Optional[Dict[str, Any]]:
        """Get jockey profile with statistics and recent rides"""
        cursor = self.conn.cursor()
        
        # Get jockey details
        cursor.execute("""
            SELECT *
            FROM jockeys
            WHERE jockey_id = ?
        """, (jockey_id,))
        
        jockey = cursor.fetchone()
        if not jockey:
            return None
        
        jockey_dict = dict(jockey)
        
        # Get ride count
        cursor.execute("""
            SELECT COUNT(*) as ride_count
            FROM runners
            WHERE jockey_id = ?
        """, (jockey_id,))
        
        jockey_dict['ride_count'] = cursor.fetchone()[0]
        
        # Get recent rides
        cursor.execute("""
            SELECT 
                r.date,
                r.course,
                r.race_name,
                h.name as horse_name,
                h.horse_id,
                t.name as trainer_name,
                ru.number,
                ru.draw
            FROM runners ru
            JOIN races r ON ru.race_id = r.race_id
            JOIN horses h ON ru.horse_id = h.horse_id
            LEFT JOIN trainers t ON ru.trainer_id = t.trainer_id
            WHERE ru.jockey_id = ?
            ORDER BY r.date DESC
            LIMIT 30
        """, (jockey_id,))
        
        jockey_dict['recent_rides'] = [dict(row) for row in cursor.fetchall()]
        
        return jockey_dict
    
    def get_owner_profile(self, owner_id: str) -> Optional[Dict[str, Any]]:
        """Get owner profile with horses and statistics"""
        cursor = self.conn.cursor()
        
        # Get owner details
        cursor.execute("""
            SELECT *
            FROM owners
            WHERE owner_id = ?
        """, (owner_id,))
        
        owner = cursor.fetchone()
        if not owner:
            return None
        
        owner_dict = dict(owner)
        
        # Get horse count
        cursor.execute("""
            SELECT COUNT(DISTINCT horse_id) as horse_count
            FROM runners
            WHERE owner_id = ?
        """, (owner_id,))
        
        owner_dict['horse_count'] = cursor.fetchone()[0]
        
        # Get recent runners
        cursor.execute("""
            SELECT 
                r.date,
                r.course,
                r.race_name,
                h.name as horse_name,
                h.horse_id,
                t.name as trainer_name,
                j.name as jockey_name,
                ru.number
            FROM runners ru
            JOIN races r ON ru.race_id = r.race_id
            JOIN horses h ON ru.horse_id = h.horse_id
            LEFT JOIN trainers t ON ru.trainer_id = t.trainer_id
            LEFT JOIN jockeys j ON ru.jockey_id = j.jockey_id
            WHERE ru.owner_id = ?
            ORDER BY r.date DESC
            LIMIT 30
        """, (owner_id,))
        
        owner_dict['recent_runners'] = [dict(row) for row in cursor.fetchall()]
        
        return owner_dict

