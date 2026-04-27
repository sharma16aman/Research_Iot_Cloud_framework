# cloud/analyzer.py
"""
Database analysis module for querying and analyzing stored IoT sensor data.
Provides statistical summaries, data quality metrics, and export capabilities.
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
import os


class DataAnalyzer:
    """
    Analyzer for querying and analyzing data stored in SQLite database.
    """
    
    def __init__(self, db_path: str = "results/cloud_data.db"):
        """
        Initialize analyzer with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
        self.conn = sqlite3.connect(db_path)
    
    def get_total_records(self) -> int:
        """Get total number of records in database."""
        cursor = self.conn.execute("SELECT COUNT(*) FROM readings")
        return cursor.fetchone()[0]
    
    def get_sensor_count(self) -> int:
        """Get number of unique sensors."""
        cursor = self.conn.execute("SELECT COUNT(DISTINCT sensor_id) FROM readings")
        return cursor.fetchone()[0]
    
    def get_time_range(self) -> Tuple[str, str]:
        """Get first and last timestamp in database."""
        cursor = self.conn.execute("SELECT MIN(ts), MAX(ts) FROM readings")
        return cursor.fetchone()
    
    def get_sensor_stats(self) -> pd.DataFrame:
        """
        Get statistics per sensor.
        
        Returns:
            DataFrame with columns: sensor_id, record_count, avg_temp, std_temp,
                                   avg_humidity, avg_pressure, null_count
        """
        query = """
        SELECT 
            sensor_id,
            COUNT(*) as record_count,
            AVG(temperature) as avg_temp,
            AVG(humidity) as avg_humidity,
            AVG(pressure) as avg_pressure,
            STDEV(temperature) as std_temp,
            SUM(CASE WHEN temperature IS NULL THEN 1 ELSE 0 END) as null_count
        FROM readings
        GROUP BY sensor_id
        ORDER BY sensor_id
        """
        try:
            df = pd.read_sql_query(query, self.conn)
        except Exception:
            # SQLite doesn't have STDEV, use pandas instead
            df = pd.read_sql_query(
                "SELECT sensor_id, temperature, humidity, pressure FROM readings",
                self.conn
            )
            stats = df.groupby('sensor_id').agg({
                'temperature': ['count', 'mean', 'std'],
                'humidity': 'mean',
                'pressure': 'mean'
            })
            stats.columns = ['record_count', 'avg_temp', 'std_temp', 'avg_humidity', 'avg_pressure']
            null_counts = df.groupby('sensor_id')['temperature'].apply(lambda x: x.isnull().sum())
            stats['null_count'] = null_counts
            df = stats.reset_index()
        
        return df
    
    def get_sensor_data(self, sensor_id: int) -> pd.DataFrame:
        """
        Get all data for a specific sensor.
        
        Args:
            sensor_id: ID of sensor to query
            
        Returns:
            DataFrame with timestamp and sensor readings
        """
        query = """
        SELECT ts, temperature, humidity, pressure
        FROM readings
        WHERE sensor_id = ?
        ORDER BY ts
        """
        df = pd.read_sql_query(query, self.conn, params=(sensor_id,))
        return df
    
    def get_time_series(self, sensor_id: int, variable: str = 'temperature') -> Tuple[List, List]:
        """
        Get time series for a specific sensor and variable.
        
        Args:
            sensor_id: ID of sensor
            variable: 'temperature', 'humidity', or 'pressure'
            
        Returns:
            Tuple of (timestamps, values)
        """
        query = f"""
        SELECT ts, {variable}
        FROM readings
        WHERE sensor_id = ?
        ORDER BY ts
        """
        cursor = self.conn.execute(query, (sensor_id,))
        results = cursor.fetchall()
        timestamps = [r[0] for r in results]
        values = [r[1] for r in results]
        return timestamps, values
    
    def get_data_quality_report(self) -> Dict:
        """
        Generate comprehensive data quality report.
        
        Returns:
            Dictionary containing various data quality metrics
        """
        report = {
            'total_records': self.get_total_records(),
            'unique_sensors': self.get_sensor_count(),
            'time_range': self.get_time_range(),
        }
        
        # Get null/missing data counts
        cursor = self.conn.execute("""
            SELECT 
                SUM(CASE WHEN temperature IS NULL THEN 1 ELSE 0 END) as null_temp,
                SUM(CASE WHEN humidity IS NULL THEN 1 ELSE 0 END) as null_hum,
                SUM(CASE WHEN pressure IS NULL THEN 1 ELSE 0 END) as null_pres
            FROM readings
        """)
        null_counts = cursor.fetchone()
        report['null_temperature'] = null_counts[0]
        report['null_humidity'] = null_counts[1]
        report['null_pressure'] = null_counts[2]
        
        # Get value ranges
        cursor = self.conn.execute("""
            SELECT 
                MIN(temperature), MAX(temperature),
                MIN(humidity), MAX(humidity),
                MIN(pressure), MAX(pressure)
            FROM readings
        """)
        ranges = cursor.fetchone()
        report['temp_range'] = (ranges[0], ranges[1])
        report['humidity_range'] = (ranges[2], ranges[3])
        report['pressure_range'] = (ranges[4], ranges[5])
        
        return report
    
    def export_to_csv(self, output_path: str, sensor_id: Optional[int] = None):
        """
        Export data to CSV file.
        
        Args:
            output_path: Path to output CSV file
            sensor_id: Optional sensor ID to filter by (None = all sensors)
        """
        if sensor_id is None:
            query = "SELECT * FROM readings ORDER BY sensor_id, ts"
            df = pd.read_sql_query(query, self.conn)
        else:
            query = "SELECT * FROM readings WHERE sensor_id = ? ORDER BY ts"
            df = pd.read_sql_query(query, self.conn, params=(sensor_id,))
        
        df.to_csv(output_path, index=False)
        print(f"Exported {len(df)} records to {output_path}")
    
    def get_summary_statistics(self) -> pd.DataFrame:
        """
        Get summary statistics across all sensors.
        
        Returns:
            DataFrame with descriptive statistics
        """
        query = "SELECT temperature, humidity, pressure FROM readings"
        df = pd.read_sql_query(query, self.conn)
        return df.describe()
    
    def get_hourly_aggregates(self, sensor_id: int) -> pd.DataFrame:
        """
        Get hourly aggregated data for a sensor.
        
        Args:
            sensor_id: ID of sensor
            
        Returns:
            DataFrame with hourly averages
        """
        df = self.get_sensor_data(sensor_id)
        df['ts'] = pd.to_datetime(df['ts'])
        df.set_index('ts', inplace=True)
        
        # Resample to hourly and compute mean
        hourly = df.resample('H').mean()
        return hourly.reset_index()
    
    def compare_sensors(self, metric: str = 'temperature') -> pd.DataFrame:
        """
        Compare a specific metric across all sensors.
        
        Args:
            metric: 'temperature', 'humidity', or 'pressure'
            
        Returns:
            DataFrame with sensor comparison
        """
        query = f"""
        SELECT sensor_id, {metric}
        FROM readings
        ORDER BY sensor_id, ts
        """
        df = pd.read_sql_query(query, self.conn)
        
        # Pivot to have sensors as columns
        df['idx'] = df.groupby('sensor_id').cumcount()
        pivot = df.pivot(index='idx', columns='sensor_id', values=metric)
        return pivot
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def generate_report(db_path: str = "results/cloud_data.db", 
                   output_path: str = "results/analysis_report.txt"):
    """
    Generate a comprehensive text report of database contents.
    
    Args:
        db_path: Path to database file
        output_path: Path to output report file
    """
    with DataAnalyzer(db_path) as analyzer:
        report = analyzer.get_data_quality_report()
        sensor_stats = analyzer.get_sensor_stats()
        summary_stats = analyzer.get_summary_statistics()
        
        with open(output_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("IoT SENSOR DATA ANALYSIS REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("OVERVIEW\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total Records: {report['total_records']}\n")
            f.write(f"Unique Sensors: {report['unique_sensors']}\n")
            f.write(f"Time Range: {report['time_range'][0]} to {report['time_range'][1]}\n\n")
            
            f.write("DATA QUALITY\n")
            f.write("-" * 60 + "\n")
            f.write(f"Missing Temperature: {report['null_temperature']} records\n")
            f.write(f"Missing Humidity: {report['null_humidity']} records\n")
            f.write(f"Missing Pressure: {report['null_pressure']} records\n\n")
            
            f.write("VALUE RANGES\n")
            f.write("-" * 60 + "\n")
            f.write(f"Temperature: {report['temp_range'][0]:.2f} to {report['temp_range'][1]:.2f} °C\n")
            f.write(f"Humidity: {report['humidity_range'][0]:.2f} to {report['humidity_range'][1]:.2f} %\n")
            f.write(f"Pressure: {report['pressure_range'][0]:.2f} to {report['pressure_range'][1]:.2f} hPa\n\n")
            
            f.write("SUMMARY STATISTICS\n")
            f.write("-" * 60 + "\n")
            f.write(summary_stats.to_string())
            f.write("\n\n")
            
            f.write("PER-SENSOR STATISTICS\n")
            f.write("-" * 60 + "\n")
            f.write(sensor_stats.to_string())
            f.write("\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("End of Report\n")
        
        print(f"Report generated: {output_path}")


if __name__ == "__main__":
    # Example usage
    try:
        generate_report()
        
        print("\nAdditional analysis available:")
        print("  analyzer = DataAnalyzer('results/cloud_data.db')")
        print("  analyzer.get_sensor_stats()")
        print("  analyzer.export_to_csv('output.csv')")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("No database found. Run main.py in streaming mode with receive_to_db=true first.")
