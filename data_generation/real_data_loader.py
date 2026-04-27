"""
Real-World IoT Dataset Loader
Fetches and processes real sensor data from official sources
"""

import pandas as pd
import numpy as np
import requests
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class RealDataLoader:
    """Load and process real-world IoT sensor datasets"""
    
    def __init__(self, cache_dir: str = "data/real_datasets"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def download_file(self, url: str, filename: str) -> Path:
        """Download file if not cached"""
        filepath = self.cache_dir / filename
        
        if filepath.exists():
            logger.info(f"Using cached file: {filepath}")
            return filepath
        
        logger.info(f"Downloading {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Downloaded to {filepath}")
        return filepath
    
    def load_intel_lab_data(self) -> pd.DataFrame:
        """
        Intel Berkeley Research Lab Dataset
        54 sensors deployed in lab, collecting temperature, humidity, light, voltage
        Source: http://db.csail.mit.edu/labdata/labdata.html
        """
        url = "http://db.csail.mit.edu/labdata/data.txt"
        filepath = self.cache_dir / "intel_lab_data.txt"
        
        try:
            if not filepath.exists():
                logger.info("Downloading Intel Lab dataset...")
                filepath = self.download_file(url, "intel_lab_data.txt")
            
            # Load data: date time epoch moteid temperature humidity light voltage
            df = pd.read_csv(filepath, sep=r'\s+', 
                            names=['date', 'time', 'epoch', 'moteid', 
                                   'temperature', 'humidity', 'light', 'voltage'],
                            on_bad_lines='skip')
            
            # Use epoch column as ordering index (avoids fragile date string parsing)
            # epoch is a reliable integer counter in the Intel Lab dataset
            df['epoch'] = pd.to_numeric(df['epoch'], errors='coerce')
            df = df.dropna(subset=['epoch'])
            df['timestamp'] = df['epoch']   # use epoch as surrogate timestamp
            
            logger.info(f"Loaded Intel Lab data: {len(df)} records, {df['moteid'].nunique()} sensors")
            return df
            
        except Exception as e:
            logger.warning(f"Failed to load Intel Lab data: {e}")
            return None
    
    def load_climate_data_online(self) -> pd.DataFrame:
        """
        NOAA Climate Data Online
        Real temperature data from weather stations
        """
        # This is a sample - in practice you'd use NOAA API with authentication
        logger.info("For NOAA data, you need API token from https://www.ncdc.noaa.gov/cdo-web/token")
        logger.info("Using simulated climate-like data instead...")
        return None
    
    def create_sample_real_data(self) -> pd.DataFrame:
        """
        Create sample data that mimics real sensor behavior
        Based on patterns from actual IoT deployments
        """
        logger.info("Creating sample real-world-like dataset...")
        
        # Simulate 24 hours of data at 1-minute intervals
        timestamps = pd.date_range('2025-01-01', periods=1440, freq='1min')
        
        # Temperature with realistic patterns
        hour = timestamps.hour + timestamps.minute / 60
        
        # Realistic office temperature pattern
        base_temp = 20.0
        diurnal = 3 * np.sin(2 * np.pi * (hour - 6) / 24)  # Peak at 6 PM
        hvac_cycles = 0.5 * np.sin(2 * np.pi * hour * 4)  # HVAC cycling
        noise = np.random.normal(0, 0.15, len(timestamps))
        
        # Add occasional events (door opening, people arriving)
        events = np.zeros(len(timestamps))
        event_times = np.random.choice(len(timestamps), 10, replace=False)
        for t in event_times:
            events[t:min(t+30, len(events))] = np.linspace(1.5, 0, min(30, len(events)-t))
        
        temperature = base_temp + diurnal + hvac_cycles + noise + events
        
        # Convert to numpy array for indexing
        temperature = temperature.values if hasattr(temperature, 'values') else np.array(temperature)
        
        # Add realistic sensor artifacts
        dropout_indices = np.random.choice(len(temperature), 5, replace=False)
        temperature[dropout_indices] = np.nan  # Dropouts
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'sensor_id': 'TEMP_001',
            'temperature': temperature,
            'value': temperature
        })
        
        logger.info(f"Created sample dataset: {len(df)} records")
        return df
    
    def prepare_for_framework(self, df: pd.DataFrame, 
                            sensor_id_col: str = 'moteid',
                            value_col: str = 'temperature',
                            n_sensors: int = 8,
                            timesteps: int = 600) -> np.ndarray:
        """
        Convert real dataset to framework format (N_sensors × T timesteps)
        
        Args:
            df: DataFrame with sensor data
            sensor_id_col: Column name for sensor IDs
            value_col: Column name for values
            n_sensors: Number of sensors to extract
            timesteps: Number of time steps per sensor
            
        Returns:
            Array of shape (n_sensors, timesteps)
        """
        if df is None or len(df) == 0:
            raise ValueError("Empty dataset")
        
        # Get unique sensors
        sensor_ids = df[sensor_id_col].unique()[:n_sensors]
        
        signals = []
        for sensor_id in sensor_ids:
            sensor_data = df[df[sensor_id_col] == sensor_id].sort_values('timestamp')
            
            # Get values
            values = sensor_data[value_col].values
            
            # Resample to desired length
            if len(values) > timesteps:
                # Downsample
                indices = np.linspace(0, len(values)-1, timesteps).astype(int)
                values = values[indices]
            elif len(values) < timesteps:
                # Pad with last value
                pad_length = timesteps - len(values)
                values = np.concatenate([values, np.repeat(values[-1], pad_length)])
            
            # Handle NaN
            values = self._ffill_nan(values)
            
            signals.append(values)
        
        result = np.array(signals)
        logger.info(f"Prepared {n_sensors} sensors × {timesteps} timesteps")
        return result
    
    def _ffill_nan(self, arr: np.ndarray) -> np.ndarray:
        """Forward-fill NaN values"""
        arr = arr.copy()
        if np.isnan(arr[0]):
            arr[0] = 0.0
        for i in range(1, len(arr)):
            if np.isnan(arr[i]):
                arr[i] = arr[i-1]
        return arr


# Pre-configured dataset loaders
def load_intel_lab_temperature(n_sensors: int = 8, timesteps: int = 600) -> Tuple[np.ndarray, dict]:
    """
    Load Intel Lab temperature data in framework format
    
    Returns:
        signals: (n_sensors, timesteps) array
        metadata: dict with dataset info
    """
    loader = RealDataLoader()
    
    try:
        df = loader.load_intel_lab_data()
        
        if df is not None and len(df) > 0:
            # Filter valid temperature readings
            df = df[df['temperature'] > -100]  # Remove invalid readings
            df = df[df['temperature'] < 100]
            
            signals = loader.prepare_for_framework(
                df, 
                sensor_id_col='moteid',
                value_col='temperature',
                n_sensors=n_sensors,
                timesteps=timesteps
            )
            
            metadata = {
                'source': 'Intel Berkeley Research Lab',
                'sensor_type': 'Temperature',
                'units': 'Celsius',
                'total_records': len(df),
                'total_sensors': df['moteid'].nunique(),
                'date_range': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
                'url': 'http://db.csail.mit.edu/labdata/labdata.html'
            }
            
            return signals, metadata
    except Exception as e:
        logger.warning(f"Failed to load Intel Lab data: {e}")
    
    # Fallback to sample data
    logger.info("Using sample realistic data instead...")
    df = loader.create_sample_real_data()
    
    # Convert to multi-sensor format
    signals = []
    for i in range(n_sensors):
        sensor_data = df['value'].values
        # Add slight variation per sensor
        sensor_data = sensor_data + np.random.normal(0, 0.1, len(sensor_data))
        
        # Resample to timesteps
        if len(sensor_data) > timesteps:
            indices = np.linspace(0, len(sensor_data)-1, timesteps).astype(int)
            sensor_data = sensor_data[indices]
        
        signals.append(sensor_data)
    
    metadata = {
        'source': 'Sample Realistic Data',
        'sensor_type': 'Temperature',
        'units': 'Celsius',
        'note': 'Mimics real office environment sensor patterns'
    }
    
    return np.array(signals), metadata


def load_smart_building_data(n_sensors: int = 8, timesteps: int = 600) -> Tuple[np.ndarray, dict]:
    """
    Load smart building sensor data
    Falls back to realistic sample if unavailable
    """
    loader = RealDataLoader()
    
    # Try Intel Lab data first
    try:
        df = loader.load_intel_lab_data()
        if df is not None and len(df) > 1000:
            # Use humidity data for variety
            df = df[df['humidity'] > 0]
            df = df[df['humidity'] < 100]
            
            signals = loader.prepare_for_framework(
                df,
                sensor_id_col='moteid', 
                value_col='humidity',
                n_sensors=n_sensors,
                timesteps=timesteps
            )
            
            metadata = {
                'source': 'Intel Lab - Humidity',
                'sensor_type': 'Humidity',
                'units': 'Percent',
                'url': 'http://db.csail.mit.edu/labdata/labdata.html'
            }
            
            return signals, metadata
    except:
        pass
    
    # Fallback
    return load_intel_lab_temperature(n_sensors, timesteps)


# Easy interface for main.py
def get_real_dataset(dataset_name: str = 'intel_lab', 
                     n_sensors: int = 8, 
                     timesteps: int = 600) -> Tuple[np.ndarray, dict]:
    """
    Get real-world dataset by name
    
    Args:
        dataset_name: 'intel_lab', 'smart_building', or 'sample'
        n_sensors: Number of sensors
        timesteps: Number of time steps
        
    Returns:
        signals: (n_sensors, timesteps) array
        metadata: dict with dataset info
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Loading real-world dataset: {dataset_name}")
    logger.info(f"Configuration: {n_sensors} sensors × {timesteps} timesteps")
    logger.info(f"{'='*60}\n")
    
    if dataset_name == 'intel_lab':
        return load_intel_lab_temperature(n_sensors, timesteps)
    elif dataset_name == 'smart_building':
        return load_smart_building_data(n_sensors, timesteps)
    elif dataset_name == 'sample':
        loader = RealDataLoader()
        df = loader.create_sample_real_data()
        
        signals = []
        for i in range(n_sensors):
            sensor_data = df['value'].values
            sensor_data = sensor_data + np.random.normal(0, 0.1 * i, len(sensor_data))
            
            if len(sensor_data) > timesteps:
                indices = np.linspace(0, len(sensor_data)-1, timesteps).astype(int)
                sensor_data = sensor_data[indices]
            
            signals.append(sensor_data)
        
        metadata = {'source': 'Sample', 'sensor_type': 'Temperature'}
        return np.array(signals), metadata
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")


if __name__ == "__main__":
    # Test the loader
    logging.basicConfig(level=logging.INFO)
    
    print("\nTesting Real Data Loader...")
    print("="*60)
    
    # Test Intel Lab data
    signals, metadata = get_real_dataset('intel_lab', n_sensors=4, timesteps=100)
    
    print(f"\nDataset: {metadata['source']}")
    print(f"Shape: {signals.shape}")
    print(f"Value range: [{signals.min():.2f}, {signals.max():.2f}]")
    print(f"Mean: {signals.mean():.2f}")
    print(f"Std: {signals.std():.2f}")
    
    if 'url' in metadata:
        print(f"Source: {metadata['url']}")
    
    print("\n✓ Real data loader working!")
