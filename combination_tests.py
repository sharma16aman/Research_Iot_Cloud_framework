"""
Combination Testing Framework
Test different combinations of reduction strategies, serializers, and protocols
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


class CombinationTester:
    """Test framework for different protocol/serializer/strategy combinations"""
    
    def __init__(self, results_dir: str = "results/combinations"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def build_reducer(self, strategy_name: str, params: Dict[str, Any] = None):
        """Build a reduction strategy with given parameters"""
        if params is None:
            params = {}
            
        n = strategy_name.lower()
        if n == "adaptivesampling":
            return AdaptiveSampler(
                low_thresh=params.get('low_thresh', 0.1),
                high_thresh=params.get('high_thresh', 0.3)
            )
        elif n == "adaptivethreshold":
            return AdaptiveThresholdReducer(
                initial_thresh=params.get('initial_thresh', 0.2),
                max_gap=params.get('max_gap', 30)
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
    
    def build_serializer(self, serializer_name: str):
        """Build a serializer"""
        if serializer_name.upper() == "JSON":
            return json_handler
        elif serializer_name.upper() == "CBOR":
            return cbor_handler
        else:
            raise ValueError(f"Unknown serializer: {serializer_name}")
    
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
            
            logger.info(f"After {strategy_name}: {len(kept_idx)} samples remaining")
        
        return current_indices, current_values
    
    def test_single_combination(self, 
                                strategies: List[tuple],
                                serializer_name: str,
                                protocol_name: str,
                                num_samples: int = 1000,
                                num_runs: int = 5) -> Dict[str, float]:
        """
        Test a single combination of strategies, serializer, and protocol
        
        Args:
            strategies: List of (strategy_name, params) tuples
            serializer_name: "JSON" or "CBOR"
            protocol_name: "HTTP" or "MQTT"
            num_samples: Number of data points to generate
            num_runs: Number of test runs to average
            
        Returns:
            Dictionary with performance metrics
        """
        results = {
            'reduction_rates': [],
            'rmse_values': [],
            'serialized_sizes': [],
            'total_bytes': [],
            'baseline_bytes': []
        }
        
        serializer = self.build_serializer(serializer_name)
        
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
            baseline_serialized = serializer.serialize(baseline_data)
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
            reduced_serialized = serializer.serialize(reduced_data)
            reduced_size = len(reduced_serialized)
            
            results['reduction_rates'].append(reduction_rate)
            results['rmse_values'].append(rmse_value)
            results['serialized_sizes'].append(reduced_size)
            results['total_bytes'].append(reduced_size)
            results['baseline_bytes'].append(baseline_size)
        
        # Calculate averages
        avg_results = {
            'reduction_rate_mean': np.mean(results['reduction_rates']),
            'reduction_rate_std': np.std(results['reduction_rates']),
            'rmse_mean': np.mean(results['rmse_values']),
            'rmse_std': np.std(results['rmse_values']),
            'serialized_size_mean': np.mean(results['serialized_sizes']),
            'serialized_size_std': np.std(results['serialized_sizes']),
            'baseline_size_mean': np.mean(results['baseline_bytes']),
            'size_reduction_%': 100.0 * (1.0 - np.mean(results['serialized_sizes']) / np.mean(results['baseline_bytes'])),
            'strategies': '+'.join([s[0] for s in strategies]),
            'serializer': serializer_name,
            'protocol': protocol_name,
            'num_runs': num_runs,
            'num_samples': num_samples
        }
        
        return avg_results
    
    def test_protocol_variations(self, 
                                  strategy_name: str,
                                  params: Dict[str, Any],
                                  serializer_name: str = "JSON"):
        """Test HTTP vs MQTT for same strategy and serializer"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing Protocol Variations")
        logger.info(f"Strategy: {strategy_name}, Serializer: {serializer_name}")
        logger.info(f"Parameters: {params}")
        logger.info(f"{'='*60}\n")
        
        results = []
        
        for protocol in ["HTTP", "MQTT"]:
            logger.info(f"Testing with {protocol}...")
            result = self.test_single_combination(
                strategies=[(strategy_name, params)],
                serializer_name=serializer_name,
                protocol_name=protocol
            )
            results.append(result)
            
            logger.info(f"  Reduction: {result['reduction_rate_mean']:.2f}%")
            logger.info(f"  RMSE: {result['rmse_mean']:.4f}")
            logger.info(f"  Serialized Size: {result['serialized_size_mean']:.0f} bytes\n")
        
        # Save results
        df = pd.DataFrame(results)
        filename = f"{strategy_name}_{serializer_name}_protocol_comparison.csv"
        df.to_csv(self.results_dir / filename, index=False)
        logger.info(f"✓ Saved: {self.results_dir / filename}\n")
        
        return df
    
    def test_serializer_variations(self,
                                    strategy_name: str,
                                    params: Dict[str, Any],
                                    protocol_name: str = "HTTP"):
        """Test JSON vs CBOR for same strategy and protocol"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing Serializer Variations")
        logger.info(f"Strategy: {strategy_name}, Protocol: {protocol_name}")
        logger.info(f"Parameters: {params}")
        logger.info(f"{'='*60}\n")
        
        results = []
        
        for serializer in ["JSON", "CBOR"]:
            logger.info(f"Testing with {serializer}...")
            result = self.test_single_combination(
                strategies=[(strategy_name, params)],
                serializer_name=serializer,
                protocol_name=protocol_name
            )
            results.append(result)
            
            logger.info(f"  Reduction: {result['reduction_rate_mean']:.2f}%")
            logger.info(f"  RMSE: {result['rmse_mean']:.4f}")
            logger.info(f"  Serialized Size: {result['serialized_size_mean']:.0f} bytes\n")
        
        # Save results
        df = pd.DataFrame(results)
        filename = f"{strategy_name}_{protocol_name}_serializer_comparison.csv"
        df.to_csv(self.results_dir / filename, index=False)
        logger.info(f"✓ Saved: {self.results_dir / filename}\n")
        
        return df
    
    def test_strategy_chains(self,
                             strategy_chains: List[List[tuple]],
                             serializer_name: str = "JSON",
                             protocol_name: str = "HTTP"):
        """Test different chained strategy combinations"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing Strategy Chain Combinations")
        logger.info(f"Serializer: {serializer_name}, Protocol: {protocol_name}")
        logger.info(f"{'='*60}\n")
        
        results = []
        
        for chain in strategy_chains:
            chain_name = '+'.join([s[0] for s in chain])
            logger.info(f"Testing chain: {chain_name}")
            
            result = self.test_single_combination(
                strategies=chain,
                serializer_name=serializer_name,
                protocol_name=protocol_name
            )
            results.append(result)
            
            logger.info(f"  Reduction: {result['reduction_rate_mean']:.2f}%")
            logger.info(f"  RMSE: {result['rmse_mean']:.4f}")
            logger.info(f"  Serialized Size: {result['serialized_size_mean']:.0f} bytes\n")
        
        # Save results
        df = pd.DataFrame(results)
        filename = f"strategy_chains_{serializer_name}_{protocol_name}.csv"
        df.to_csv(self.results_dir / filename, index=False)
        logger.info(f"✓ Saved: {self.results_dir / filename}\n")
        
        return df
    
    def test_full_combinations(self, 
                               strategy_name: str,
                               params: Dict[str, Any]):
        """Test all combinations of serializers and protocols for one strategy"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing All Combinations")
        logger.info(f"Strategy: {strategy_name}")
        logger.info(f"Parameters: {params}")
        logger.info(f"{'='*60}\n")
        
        results = []
        
        for serializer in ["JSON", "CBOR"]:
            for protocol in ["HTTP", "MQTT"]:
                combo_name = f"{serializer}+{protocol}"
                logger.info(f"Testing: {combo_name}")
                
                result = self.test_single_combination(
                    strategies=[(strategy_name, params)],
                    serializer_name=serializer,
                    protocol_name=protocol
                )
                results.append(result)
                
                logger.info(f"  Reduction: {result['reduction_rate_mean']:.2f}%")
                logger.info(f"  RMSE: {result['rmse_mean']:.4f}")
                logger.info(f"  Serialized Size: {result['serialized_size_mean']:.0f} bytes\n")
        
        # Save results
        df = pd.DataFrame(results)
        filename = f"{strategy_name}_full_combinations.csv"
        df.to_csv(self.results_dir / filename, index=False)
        logger.info(f"✓ Saved: {self.results_dir / filename}\n")
        
        return df


def main():
    """Example usage of combination testing framework"""
    tester = CombinationTester()
    
    # Example 1: Test protocol variations (HTTP vs MQTT)
    # AdaptiveSampling with JSON serializer
    print("\n" + "="*60)
    print("Example 1: Protocol Comparison")
    print("="*60)
    tester.test_protocol_variations(
        strategy_name="AdaptiveSampling",
        params={'low_thresh': 0.12, 'high_thresh': 0.35},
        serializer_name="JSON"
    )
    
    # Example 2: Test serializer variations (JSON vs CBOR)
    # AdaptiveThreshold with HTTP protocol
    print("\n" + "="*60)
    print("Example 2: Serializer Comparison")
    print("="*60)
    tester.test_serializer_variations(
        strategy_name="AdaptiveThreshold",
        params={'initial_thresh': 0.22, 'max_gap': 40},
        protocol_name="HTTP"
    )
    
    # Example 3: Test chained strategies
    print("\n" + "="*60)
    print("Example 3: Strategy Chains")
    print("="*60)
    strategy_chains = [
        # Single strategies
        [("AdaptiveSampling", {'low_thresh': 0.12, 'high_thresh': 0.35})],
        [("AdaptiveThreshold", {'initial_thresh': 0.22, 'max_gap': 40})],
        
        # Chained strategies
        [
            ("AdaptiveSampling", {'low_thresh': 0.12, 'high_thresh': 0.35}),
            ("AdaptiveThreshold", {'initial_thresh': 0.22, 'max_gap': 40})
        ],
        [
            ("Aggregation", {'window': 5, 'method': 'mean'}),
            ("Filtering", {'window': 5})
        ],
        [
            ("Filtering", {'window': 3}),
            ("AdaptiveSampling", {'low_thresh': 0.12, 'high_thresh': 0.35})
        ]
    ]
    
    tester.test_strategy_chains(
        strategy_chains=strategy_chains,
        serializer_name="JSON",
        protocol_name="HTTP"
    )
    
    # Example 4: Test all combinations for one strategy
    print("\n" + "="*60)
    print("Example 4: Full Combinations (all serializers × protocols)")
    print("="*60)
    tester.test_full_combinations(
        strategy_name="AdaptiveThreshold",
        params={'initial_thresh': 0.22, 'max_gap': 40}
    )
    
    print("\n" + "="*60)
    print("✓ All combination tests completed!")
    print(f"Results saved to: {tester.results_dir}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
