"""
Single Strategy Testing (No Chaining)
Compare individual strategies with all serializer×protocol combinations
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
from pathlib import Path

# Import framework components
from data_generation.synthetic_sensors import generate_dataset
from edge_reduction.adaptive_sampling import AdaptiveSampler
from edge_reduction.event_driven import AdaptiveThresholdReducer
from edge_reduction.aggregation import aggregate_array
from edge_reduction.filtering import moving_average
from serialization import json_handler, cbor_handler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SingleStrategyTester:
    """Test individual strategies (no chaining) with all serializer×protocol combinations"""
    
    def __init__(self, results_dir: str = "results/single_strategies"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def ffill_nan(self, arr: np.ndarray) -> np.ndarray:
        """Forward-fill NaN values"""
        out = arr.copy()
        mask = np.isnan(out)
        idx = np.where(~mask, np.arange(len(mask)), 0)
        np.maximum.accumulate(idx, axis=0, out=idx)
        out[mask] = out[idx[mask]]
        return out
    
    def rmse(self, original: np.ndarray, reconstructed: np.ndarray) -> float:
        """Calculate RMSE between original and reconstructed signals"""
        return np.sqrt(np.mean((original - reconstructed)**2))
    
    def reconstruct_from_samples(self, T: int, indices: np.ndarray, values: np.ndarray) -> np.ndarray:
        """Reconstruct full signal using forward-fill from sampled points"""
        recon = np.empty(T)
        recon[:] = np.nan
        recon[indices] = values
        return self.ffill_nan(recon)
    
    def build_reducer(self, strategy_name: str, params: Dict[str, Any] = None):
        """Build a reduction strategy with given parameters"""
        if params is None:
            params = {}
            
        n = strategy_name.lower()
        if n == "adaptivesampling":
            return AdaptiveSampler(
                low_thresh=params.get('low_thresh', 0.12),
                high_thresh=params.get('high_thresh', 0.35)
            )
        elif n == "adaptivethreshold":
            return AdaptiveThresholdReducer(
                initial_thresh=params.get('initial_thresh', 0.22),
                max_gap=params.get('max_gap', 40)
            )
        elif n == "aggregation":
            # Create wrapper class that has run() method
            class _Agg:
                def __init__(self, window=5, method="mean"):
                    self.window = window
                    self.method = method
                def run(self, series):
                    out = aggregate_array(series, window=self.window, method=self.method)
                    idx = np.arange(self.window-1, len(series), self.window)
                    if len(out) > len(idx): idx = np.concatenate([idx, [len(series)-1]])
                    if len(idx) > len(out): idx = idx[:len(out)]
                    return idx, out
            return _Agg(
                window=params.get('window', 5),
                method=params.get('method', 'mean')
            )
        elif n == "filtering":
            # Create wrapper class that has run() method
            class _Filt:
                def __init__(self, window=5):
                    self.window = window
                def run(self, series):
                    filt = moving_average(series, window=self.window)
                    idx = np.arange(len(series))
                    return idx, filt
            return _Filt(window=params.get('window', 5))
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
    
    def get_serializer(self, name: str):
        """Get serializer module"""
        if name.upper() == "JSON":
            return json_handler
        elif name.upper() == "CBOR":
            return cbor_handler
        else:
            raise ValueError(f"Unknown serializer: {name}")
    
    def test_single_strategy(self, 
                            strategy_name: str,
                            params: Dict[str, Any],
                            serializer: str,
                            protocol: str,
                            num_samples: int = 1000,
                            num_runs: int = 10) -> Dict[str, Any]:
        """
        Test a single strategy with specific serializer and protocol
        
        Args:
            strategy_name: Name of the strategy
            params: Strategy parameters
            serializer: "JSON" or "CBOR"
            protocol: "HTTP" or "MQTT"
            num_samples: Number of data points to generate
            num_runs: Number of test runs to average
            
        Returns:
            Dictionary with performance metrics
        """
        results = {
            'reduction_rates': [],
            'rmse_values': [],
            'serialized_sizes': [],
            'baseline_bytes': []
        }
        
        ser = self.get_serializer(serializer)
        
        for run in range(num_runs):
            # Generate synthetic data (1 sensor)
            data = generate_dataset(
                n_sensors=1,
                T=num_samples,
                noise=0.05,
                spikes=True,
                drift=0.0,
                seed=42 + run
            )
            signal = self.ffill_nan(data[0])
            
            # Calculate baseline (send all)
            baseline_data = [
                {"t": i, "v": float(signal[i])} 
                for i in range(len(signal))
            ]
            baseline_serialized = ser.serialize(baseline_data)
            baseline_size = len(baseline_serialized)
            
            # Apply single strategy
            reducer = self.build_reducer(strategy_name, params)
            kept_indices, kept_values = reducer.run(signal)
            
            # Calculate metrics
            reduction_rate = 100.0 * (1.0 - len(kept_indices) / len(signal))
            
            reconstructed = self.reconstruct_from_samples(len(signal), kept_indices, kept_values)
            rmse_value = self.rmse(signal, reconstructed)
            
            # Serialize reduced data
            reduced_data = [
                {"t": int(kept_indices[i]), "v": float(kept_values[i])} 
                for i in range(len(kept_indices))
            ]
            reduced_serialized = ser.serialize(reduced_data)
            reduced_size = len(reduced_serialized)
            
            results['reduction_rates'].append(reduction_rate)
            results['rmse_values'].append(rmse_value)
            results['serialized_sizes'].append(reduced_size)
            results['baseline_bytes'].append(baseline_size)
        
        # Calculate statistics
        return {
            'strategy': strategy_name,
            'serializer': serializer,
            'protocol': protocol,
            'reduction_rate_mean': np.mean(results['reduction_rates']),
            'reduction_rate_std': np.std(results['reduction_rates']),
            'rmse_mean': np.mean(results['rmse_values']),
            'rmse_std': np.std(results['rmse_values']),
            'serialized_size_mean': np.mean(results['serialized_sizes']),
            'serialized_size_std': np.std(results['serialized_sizes']),
            'baseline_size_mean': np.mean(results['baseline_bytes']),
            'size_reduction_%': 100.0 * (1.0 - np.mean(results['serialized_sizes']) / np.mean(results['baseline_bytes'])),
            'num_runs': num_runs,
            'num_samples': num_samples
        }


def main():
    """Run all single-strategy tests"""
    tester = SingleStrategyTester()
    
    print("\n" + "="*70)
    print("SINGLE STRATEGY TESTING (NO CHAINING)")
    print("Testing 4 strategies × 4 (serializer × protocol) = 16 combinations")
    print("="*70 + "\n")
    
    # Define the 4 individual strategies with optimal parameters
    strategies = [
        {
            'name': 'AdaptiveSampling',
            'params': {'low_thresh': 0.12, 'high_thresh': 0.35}
        },
        {
            'name': 'AdaptiveThreshold',
            'params': {'initial_thresh': 0.22, 'max_gap': 40}
        },
        {
            'name': 'Aggregation',
            'params': {'window': 5, 'method': 'mean'}
        },
        {
            'name': 'Filtering',
            'params': {'window': 5}
        }
    ]
    
    # Define serializer × protocol combinations
    serializers = ['JSON', 'CBOR']
    protocols = ['HTTP', 'MQTT']
    
    all_results = []
    test_num = 1
    
    # Test each strategy with all serializer×protocol combinations
    for strategy in strategies:
        logger.info(f"\n{'='*70}")
        logger.info(f"Strategy: {strategy['name']}")
        logger.info(f"Parameters: {strategy['params']}")
        logger.info(f"{'='*70}")
        
        for serializer in serializers:
            for protocol in protocols:
                logger.info(f"\n  Test #{test_num}: {serializer} + {protocol}")
                
                result = tester.test_single_strategy(
                    strategy_name=strategy['name'],
                    params=strategy['params'],
                    serializer=serializer,
                    protocol=protocol,
                    num_samples=1000,
                    num_runs=10
                )
                
                all_results.append(result)
                
                logger.info(f"    Reduction: {result['reduction_rate_mean']:.2f}% ± {result['reduction_rate_std']:.2f}")
                logger.info(f"    RMSE: {result['rmse_mean']:.4f} ± {result['rmse_std']:.4f}")
                logger.info(f"    Size: {result['serialized_size_mean']:.0f} ± {result['serialized_size_std']:.0f} bytes")
                logger.info(f"    Size Reduction: {result['size_reduction_%']:.1f}%")
                
                test_num += 1
    
    # Save all results to CSV
    df = pd.DataFrame(all_results)
    output_file = tester.results_dir / "all_16_single_strategies.csv"
    df.to_csv(output_file, index=False)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"✓ All 16 single-strategy tests completed!")
    logger.info(f"✓ Results saved to: {output_file}")
    logger.info(f"{'='*70}\n")
    
    # Print summary table
    print("\n" + "="*70)
    print("SUMMARY TABLE - Single Strategy Comparison")
    print("="*70 + "\n")
    
    print(f"{'#':<4} {'Strategy':<22} {'Ser':<5} {'Proto':<6} {'Red%':<8} {'RMSE':<8} {'Size':<8}")
    print("-" * 70)
    
    for idx, row in df.iterrows():
        print(f"{idx+1:<4} {row['strategy']:<22} {row['serializer']:<5} {row['protocol']:<6} "
              f"{row['reduction_rate_mean']:>6.2f}% {row['rmse_mean']:>7.4f} {row['serialized_size_mean']:>7.0f}")
    
    print("\n" + "="*70)
    print("STRATEGY COMPARISON (Average across all serializer/protocol combos)")
    print("="*70 + "\n")
    
    # Group by strategy and calculate averages
    strategy_summary = df.groupby('strategy').agg({
        'reduction_rate_mean': 'mean',
        'rmse_mean': 'mean',
        'serialized_size_mean': 'mean'
    }).round(2)
    
    print(strategy_summary.to_string())
    print("\n")


if __name__ == "__main__":
    main()
