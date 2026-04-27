"""
Comprehensive Combination Testing
Tests all 24 specified combinations:
- 6 strategy chains × 4 (serializer × protocol) combinations
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
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


class ComprehensiveTester:
    """Test all 24 strategy chain × serializer × protocol combinations"""
    
    def __init__(self, results_dir: str = "results/comprehensive"):
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
    
    def chain_strategies(self, signal: np.ndarray, strategies: List[tuple]):
        """
        Chain multiple reduction strategies together
        strategies: List of (strategy_name, params) tuples
        Returns: (indices, values) of kept samples
        """
        current_indices = np.arange(len(signal))
        current_values = self.ffill_nan(signal)
        
        for strategy_name, params in strategies:
            reducer = self.build_reducer(strategy_name, params)
            kept_idx, kept_vals = reducer.run(current_values)
            
            # Update for next stage
            current_indices = current_indices[kept_idx]
            current_values = kept_vals
        
        return current_indices, current_values
    
    def get_serializer(self, name: str):
        """Get serializer module"""
        if name.upper() == "JSON":
            return json_handler
        elif name.upper() == "CBOR":
            return cbor_handler
        else:
            raise ValueError(f"Unknown serializer: {name}")
    
    def test_combination(self, 
                        strategies: List[tuple],
                        serializer: str,
                        protocol: str,
                        num_samples: int = 1000,
                        num_runs: int = 10) -> Dict[str, Any]:
        """
        Test a single combination
        
        Args:
            strategies: List of (strategy_name, params) tuples
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
            
            # Apply chained strategies
            kept_indices, kept_values = self.chain_strategies(signal, strategies)
            
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
        strategy_names = '+'.join([s[0] for s in strategies])
        
        return {
            'strategy_chain': strategy_names,
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
    """Run all 24 comprehensive combination tests"""
    tester = ComprehensiveTester()
    
    print("\n" + "="*70)
    print("COMPREHENSIVE COMBINATION TESTING")
    print("Testing 6 strategy chains × 4 (serializer × protocol) = 24 combinations")
    print("="*70 + "\n")
    
    # Define the 6 strategy chains
    strategy_chains = [
        {
            'name': 'AdaptiveSampling+AdaptiveThreshold',
            'strategies': [
                ('AdaptiveSampling', {'low_thresh': 0.12, 'high_thresh': 0.35}),
                ('AdaptiveThreshold', {'initial_thresh': 0.22, 'max_gap': 40})
            ]
        },
        {
            'name': 'Aggregation+Filtering',
            'strategies': [
                ('Aggregation', {'window': 5, 'method': 'mean'}),
                ('Filtering', {'window': 5})
            ]
        },
        {
            'name': 'Aggregation+AdaptiveSampling',
            'strategies': [
                ('Aggregation', {'window': 5, 'method': 'mean'}),
                ('AdaptiveSampling', {'low_thresh': 0.12, 'high_thresh': 0.35})
            ]
        },
        {
            'name': 'Aggregation+AdaptiveThreshold',
            'strategies': [
                ('Aggregation', {'window': 5, 'method': 'mean'}),
                ('AdaptiveThreshold', {'initial_thresh': 0.22, 'max_gap': 40})
            ]
        },
        {
            'name': 'Filtering+AdaptiveThreshold',
            'strategies': [
                ('Filtering', {'window': 5}),
                ('AdaptiveThreshold', {'initial_thresh': 0.22, 'max_gap': 40})
            ]
        },
        {
            'name': 'Filtering+AdaptiveSampling',
            'strategies': [
                ('Filtering', {'window': 5}),
                ('AdaptiveSampling', {'low_thresh': 0.12, 'high_thresh': 0.35})
            ]
        }
    ]
    
    # Define serializer × protocol combinations
    serializers = ['JSON', 'CBOR']
    protocols = ['HTTP', 'MQTT']
    
    all_results = []
    test_num = 1
    
    # Test each strategy chain with all serializer×protocol combinations
    for chain in strategy_chains:
        logger.info(f"\n{'='*70}")
        logger.info(f"Strategy Chain: {chain['name']}")
        logger.info(f"{'='*70}")
        
        for serializer in serializers:
            for protocol in protocols:
                logger.info(f"\n  Test #{test_num}: {serializer} + {protocol}")
                
                result = tester.test_combination(
                    strategies=chain['strategies'],
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
    output_file = tester.results_dir / "all_24_combinations.csv"
    df.to_csv(output_file, index=False)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"✓ All 24 combination tests completed!")
    logger.info(f"✓ Results saved to: {output_file}")
    logger.info(f"{'='*70}\n")
    
    # Print summary table
    print("\n" + "="*70)
    print("SUMMARY TABLE")
    print("="*70 + "\n")
    
    print(f"{'#':<4} {'Strategy Chain':<35} {'Ser':<5} {'Proto':<6} {'Red%':<8} {'RMSE':<8} {'Size':<8}")
    print("-" * 70)
    
    for idx, row in df.iterrows():
        print(f"{idx+1:<4} {row['strategy_chain']:<35} {row['serializer']:<5} {row['protocol']:<6} "
              f"{row['reduction_rate_mean']:>6.2f}% {row['rmse_mean']:>7.4f} {row['serialized_size_mean']:>7.0f}")
    
    print("\n")


if __name__ == "__main__":
    main()
