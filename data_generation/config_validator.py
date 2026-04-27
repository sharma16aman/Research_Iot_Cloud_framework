# data_generation/config_validator.py
"""
Configuration validator for experiment YAML files.
Validates parameter ranges, consistency, and required fields.
"""

import yaml
from typing import Dict, List, Any, Optional, Tuple
import os


class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""
    pass


class ConfigValidator:
    """
    Validates experiment configuration files.
    """
    
    VALID_MODES = ["vectorized", "streaming"]
    VALID_SERIALIZERS = ["JSON", "CBOR"]
    VALID_REDUCERS = ["AdaptiveSampling", "AdaptiveThreshold", "Aggregation", "Filtering",
                     "aggregation-mean", "filtering-ma"]
    VALID_PROTOCOLS = ["MQTT", "HTTP"]
    
    def __init__(self, config_path: str = "data_generation/config.yaml"):
        """
        Initialize validator with config file path.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.config = None
        self.errors = []
        self.warnings = []
    
    def load_config(self) -> Dict:
        """Load YAML configuration file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            try:
                self.config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ConfigValidationError(f"Invalid YAML syntax: {e}")
        
        return self.config
    
    def validate(self, raise_on_error: bool = True) -> Tuple[bool, List[str], List[str]]:
        """
        Validate the entire configuration.
        
        Args:
            raise_on_error: Whether to raise exception on validation failure
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        if self.config is None:
            self.load_config()
        
        self.errors = []
        self.warnings = []
        
        # Validate required top-level sections
        self._validate_required_sections()
        
        # Validate experiment section
        self._validate_experiment()
        
        # Validate strategy-specific configurations
        self._validate_strategy_configs()
        
        # Validate sweep configurations
        self._validate_sweep()
        
        # Validate streaming configuration if in streaming mode
        if self.config.get('experiment', {}).get('mode') == 'streaming':
            self._validate_streaming()
        
        is_valid = len(self.errors) == 0
        
        if not is_valid and raise_on_error:
            error_msg = "\n".join([f"  - {err}" for err in self.errors])
            raise ConfigValidationError(f"Configuration validation failed:\n{error_msg}")
        
        return is_valid, self.errors, self.warnings
    
    def _validate_required_sections(self):
        """Validate presence of required configuration sections."""
        if 'experiment' not in self.config:
            self.errors.append("Missing required section: 'experiment'")
    
    def _validate_experiment(self):
        """Validate experiment configuration section."""
        exp = self.config.get('experiment', {})
        
        # Validate mode
        mode = exp.get('mode')
        if not mode:
            self.errors.append("experiment.mode is required")
        elif mode not in self.VALID_MODES:
            self.errors.append(f"Invalid mode: '{mode}'. Must be one of {self.VALID_MODES}")
        
        # Validate runs (vectorized mode)
        if mode == 'vectorized':
            runs = exp.get('runs')
            if not runs:
                self.warnings.append("experiment.runs not specified, using default")
            elif not isinstance(runs, int) or runs <= 0:
                self.errors.append("experiment.runs must be a positive integer")
            elif runs < 3:
                self.warnings.append(f"experiment.runs={runs} is very low, consider at least 10 for statistics")
        
        # Validate sensors
        sensors = exp.get('sensors')
        if not sensors:
            self.errors.append("experiment.sensors is required")
        elif not isinstance(sensors, int) or sensors <= 0:
            self.errors.append("experiment.sensors must be a positive integer")
        elif sensors > 1000:
            self.warnings.append(f"experiment.sensors={sensors} is very high, may be slow")
        
        # Validate timesteps
        timesteps = exp.get('timesteps')
        if not timesteps:
            self.errors.append("experiment.timesteps is required")
        elif not isinstance(timesteps, int) or timesteps <= 0:
            self.errors.append("experiment.timesteps must be a positive integer")
        elif timesteps < 10:
            self.warnings.append(f"experiment.timesteps={timesteps} is very low")
        
        # Validate noise
        noise = exp.get('noise')
        if noise is not None:
            if not isinstance(noise, (int, float)) or noise < 0:
                self.errors.append("experiment.noise must be non-negative number")
            elif noise > 1.0:
                self.warnings.append(f"experiment.noise={noise} is very high")
        
        # Validate drift
        drift = exp.get('drift')
        if drift is not None:
            if not isinstance(drift, (int, float)) or drift < 0:
                self.errors.append("experiment.drift must be non-negative number")
        
        # Validate reducers
        reducers = exp.get('reducers')
        if not reducers:
            self.errors.append("experiment.reducers is required and must not be empty")
        elif not isinstance(reducers, list):
            self.errors.append("experiment.reducers must be a list")
        else:
            for reducer in reducers:
                if reducer not in self.VALID_REDUCERS:
                    self.errors.append(f"Invalid reducer: '{reducer}'. Must be one of {self.VALID_REDUCERS}")
        
        # Validate serializers
        serializers = exp.get('serializers')
        if not serializers:
            self.errors.append("experiment.serializers is required and must not be empty")
        elif not isinstance(serializers, list):
            self.errors.append("experiment.serializers must be a list")
        else:
            for ser in serializers:
                if ser not in self.VALID_SERIALIZERS:
                    self.errors.append(f"Invalid serializer: '{ser}'. Must be one of {self.VALID_SERIALIZERS}")
            if "CBOR" in serializers:
                self.warnings.append("CBOR serializer requires cbor2 package (pip install cbor2)")
        
        # Validate protocol settings (streaming mode)
        if exp.get('use_protocols'):
            protocol = exp.get('protocol')
            if not protocol:
                self.errors.append("experiment.protocol required when use_protocols=true")
            elif protocol not in self.VALID_PROTOCOLS:
                self.errors.append(f"Invalid protocol: '{protocol}'. Must be one of {self.VALID_PROTOCOLS}")
            
            if protocol == "MQTT":
                self.warnings.append("MQTT protocol requires paho-mqtt package")
            elif protocol == "HTTP":
                self.warnings.append("HTTP protocol requires requests package")
    
    def _validate_strategy_configs(self):
        """Validate strategy-specific configuration sections."""
        # Adaptive Sampling
        if 'adaptive_sampling' in self.config:
            self._validate_adaptive_sampling(self.config['adaptive_sampling'])
        
        # Adaptive Threshold
        if 'adaptive_threshold' in self.config:
            self._validate_adaptive_threshold(self.config['adaptive_threshold'])
        
        # Aggregation
        if 'aggregation' in self.config:
            self._validate_aggregation(self.config['aggregation'])
        
        # Filtering
        if 'filtering' in self.config:
            self._validate_filtering(self.config['filtering'])
    
    def _validate_adaptive_sampling(self, config: Dict):
        """Validate adaptive sampling parameters."""
        base_interval = config.get('base_interval')
        if base_interval is not None and (not isinstance(base_interval, (int, float)) or base_interval <= 0):
            self.errors.append("adaptive_sampling.base_interval must be positive number")
        
        low_thresh = config.get('low_thresh')
        high_thresh = config.get('high_thresh')
        
        if low_thresh is not None:
            if not isinstance(low_thresh, (int, float)) or low_thresh < 0:
                self.errors.append("adaptive_sampling.low_thresh must be non-negative")
        
        if high_thresh is not None:
            if not isinstance(high_thresh, (int, float)) or high_thresh < 0:
                self.errors.append("adaptive_sampling.high_thresh must be non-negative")
        
        if low_thresh is not None and high_thresh is not None and low_thresh >= high_thresh:
            self.errors.append("adaptive_sampling.low_thresh must be less than high_thresh")
    
    def _validate_adaptive_threshold(self, config: Dict):
        """Validate adaptive threshold parameters."""
        initial_thresh = config.get('initial_thresh')
        min_thresh = config.get('min_thresh')
        max_thresh = config.get('max_thresh')
        
        if initial_thresh is not None and (not isinstance(initial_thresh, (int, float)) or initial_thresh < 0):
            self.errors.append("adaptive_threshold.initial_thresh must be non-negative")
        
        if min_thresh is not None and (not isinstance(min_thresh, (int, float)) or min_thresh < 0):
            self.errors.append("adaptive_threshold.min_thresh must be non-negative")
        
        if max_thresh is not None and (not isinstance(max_thresh, (int, float)) or max_thresh < 0):
            self.errors.append("adaptive_threshold.max_thresh must be non-negative")
        
        if min_thresh is not None and max_thresh is not None and min_thresh >= max_thresh:
            self.errors.append("adaptive_threshold.min_thresh must be less than max_thresh")
        
        max_gap = config.get('max_gap')
        if max_gap is not None and (not isinstance(max_gap, int) or max_gap <= 0):
            self.errors.append("adaptive_threshold.max_gap must be positive integer")
    
    def _validate_aggregation(self, config: Dict):
        """Validate aggregation parameters."""
        window = config.get('window')
        if window is not None and (not isinstance(window, int) or window <= 0):
            self.errors.append("aggregation.window must be positive integer")
        elif window is not None and window > 100:
            self.warnings.append(f"aggregation.window={window} is very large")
        
        method = config.get('method')
        if method is not None and method not in ['mean', 'median', 'min', 'max']:
            self.errors.append("aggregation.method must be one of: mean, median, min, max")
    
    def _validate_filtering(self, config: Dict):
        """Validate filtering parameters."""
        window = config.get('window')
        if window is not None and (not isinstance(window, int) or window <= 0):
            self.errors.append("filtering.window must be positive integer")
        elif window is not None and window > 50:
            self.warnings.append(f"filtering.window={window} is very large")
        
        filter_type = config.get('filter_type')
        if filter_type is not None and filter_type not in ['ma', 'ema']:
            self.errors.append("filtering.filter_type must be 'ma' or 'ema'")
    
    def _validate_sweep(self):
        """Validate parameter sweep configurations."""
        if 'sweep' not in self.config:
            return  # Sweep is optional
        
        sweep = self.config['sweep']
        
        for strategy_name, params in sweep.items():
            if not isinstance(params, dict):
                self.errors.append(f"sweep.{strategy_name} must be a dictionary")
                continue
            
            for param_name, values in params.items():
                if not isinstance(values, list):
                    self.errors.append(f"sweep.{strategy_name}.{param_name} must be a list")
                elif len(values) == 0:
                    self.warnings.append(f"sweep.{strategy_name}.{param_name} is empty")
                elif len(values) > 10:
                    self.warnings.append(f"sweep.{strategy_name}.{param_name} has {len(values)} values (may be slow)")
    
    def _validate_streaming(self):
        """Validate streaming mode configuration."""
        if 'streaming' not in self.config:
            self.warnings.append("Streaming mode enabled but 'streaming' section missing")
            return
        
        stream = self.config['streaming']
        
        sensors = stream.get('sensors')
        if sensors is not None and (not isinstance(sensors, int) or sensors <= 0):
            self.errors.append("streaming.sensors must be positive integer")
        
        steps_per_sensor = stream.get('steps_per_sensor')
        if steps_per_sensor is not None and (not isinstance(steps_per_sensor, int) or steps_per_sensor <= 0):
            self.errors.append("streaming.steps_per_sensor must be positive integer")
        
        sampling_hz = stream.get('sampling_hz')
        if sampling_hz is not None and (not isinstance(sampling_hz, (int, float)) or sampling_hz <= 0):
            self.errors.append("streaming.sampling_hz must be positive number")
    
    def print_report(self):
        """Print validation report to console."""
        print("=" * 60)
        print("CONFIGURATION VALIDATION REPORT")
        print("=" * 60)
        print(f"Config file: {self.config_path}\n")
        
        if len(self.errors) == 0 and len(self.warnings) == 0:
            print("✓ Configuration is valid with no warnings")
        else:
            if self.errors:
                print(f"✗ {len(self.errors)} ERROR(S):")
                for i, err in enumerate(self.errors, 1):
                    print(f"  {i}. {err}")
                print()
            
            if self.warnings:
                print(f"⚠ {len(self.warnings)} WARNING(S):")
                for i, warn in enumerate(self.warnings, 1):
                    print(f"  {i}. {warn}")
                print()
        
        print("=" * 60)


def validate_config(config_path: str = "data_generation/config.yaml", 
                   raise_on_error: bool = True,
                   print_report: bool = True) -> bool:
    """
    Convenience function to validate a config file.
    
    Args:
        config_path: Path to configuration file
        raise_on_error: Whether to raise exception on validation failure
        print_report: Whether to print validation report
        
    Returns:
        True if valid, False otherwise
    """
    validator = ConfigValidator(config_path)
    is_valid, errors, warnings = validator.validate(raise_on_error=raise_on_error)
    
    if print_report:
        validator.print_report()
    
    return is_valid


if __name__ == "__main__":
    # Example usage
    try:
        is_valid = validate_config()
        if is_valid:
            print("\n✓ Configuration ready for experiments")
        else:
            print("\n✗ Please fix configuration errors before running experiments")
    except ConfigValidationError as e:
        print(f"\nValidation Error: {e}")
    except FileNotFoundError as e:
        print(f"\nFile Error: {e}")
