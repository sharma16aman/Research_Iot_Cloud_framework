# Quick Reference: Testing & Commands

## Testing Scripts Overview

### Core Testing

| Script | Purpose | Output | Time |
|--------|---------|--------|------|
| `test_real_data.py` | Compare synthetic vs real data | Console comparison | ~1 min |
| `main.py` | Run configured experiment | CSV + plots | 2-5 min |
| `comprehensive_combination_tests.py` | Test 24 combinations (chained) | CSV + 6 plots | 15-20 min |
| `single_strategy_tests.py` | Test 16 single strategies | CSV + 4 plots | 10-15 min |

### Visualization

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `enhanced_plots.py` | Generate 4 plot types | results_vectorized.csv | 4 PNG files |
| `visualize_comprehensive.py` | Plot 24 combinations | all_24_combinations.csv | 6 PNG files |
| `visualize_single_strategies.py` | Plot single strategies | single_strategy_results.csv | 4 PNG files |

---

## Fast Commands

### Quick Start: Test Both Data Modes
```bash
python test_real_data.py
```
Output: Synthetic (93% reduction) vs Real (52% reduction)

### Generate All Enhanced Plots
```bash
python enhanced_plots.py
```
Output: `tradeoff_scatter.png`, `tradeoff_per_strategy.png`, `tradeoff_heatmap.png`, `tradeoff_pareto.png`

### Run All 24 Combination Tests (Chained Strategies)
```bash
python comprehensive_combination_tests.py
```
Output: `results/comprehensive/all_24_combinations.csv` + 6 plots

### Run All 16 Single-Strategy Tests
```bash
python single_strategy_tests.py
```
Output: `results/single_strategies/single_strategy_results.csv` + 4 plots

### Visualize Combination Results
```bash
python visualize_comprehensive.py
```

### Visualize Single-Strategy Results
```bash
python visualize_single_strategies.py
```

---

## Data Mode Selection

### Synthetic Data (Default)
```yaml
# config.yaml
experiment:
  data_mode: "synthetic"
  sensors: 8
  timesteps: 600
```

### Real Data (Intel Lab)
```yaml
# config.yaml
experiment:
  data_mode: "real"
  real_dataset: "intel_lab"
  sensors: 5
  timesteps: 100
```

See [REAL_DATA_GUIDE.md](REAL_DATA_GUIDE.md) for complete guide.

---

## Custom Testing Examples

### Example 1: Compare Protocols
Test HTTP vs MQTT for a specific strategy:

```python
from combination_tests import CombinationTester

tester = CombinationTester()

# AdaptiveSampling with JSON
tester.test_protocol_variations(
    strategy_name="AdaptiveSampling",
    params={'low_thresh': 0.12, 'high_thresh': 0.35},
    serializer_name="JSON"
)

# Results saved to: results/combinations/AdaptiveSampling_JSON_protocol_comparison.csv
```

### Example 2: Compare Serializers
Test JSON vs CBOR for a specific strategy:

```python
# AdaptiveThreshold with HTTP
tester.test_serializer_variations(
    strategy_name="AdaptiveThreshold",
    params={'initial_thresh': 0.22, 'max_gap': 40},
    protocol_name="HTTP"
)

# Results saved to: results/combinations/AdaptiveThreshold_HTTP_serializer_comparison.csv
```

### Example 3: Test Strategy Chains
Chain multiple reduction strategies:

```python
# Define chains to test
chains = [
    # Single AdaptiveSampling
    [("AdaptiveSampling", {'low_thresh': 0.12, 'high_thresh': 0.35})],
    
    # Single AdaptiveThreshold
    [("AdaptiveThreshold", {'initial_thresh': 0.22, 'max_gap': 40})],
    
    # Chained: Sampling → Threshold
    [
        ("AdaptiveSampling", {'low_thresh': 0.12, 'high_thresh': 0.35}),
        ("AdaptiveThreshold", {'initial_thresh': 0.22, 'max_gap': 40})
    ],
    
    # Chained: Aggregation → Filtering
    [
        ("Aggregation", {'window': 5, 'method': 'mean'}),
        ("Filtering", {'window': 5})
    ],
    
    # Chained: Filtering → Sampling
    [
        ("Filtering", {'window': 3}),
        ("AdaptiveSampling", {'low_thresh': 0.12, 'high_thresh': 0.35})
    ]
]

tester.test_strategy_chains(
    strategy_chains=chains,
    serializer_name="JSON",
    protocol_name="HTTP"
)

# Results saved to: results/combinations/strategy_chains_JSON_HTTP.csv
```

### Example 4: Full Combination Matrix
Test all serializer × protocol combinations:

```python
# AdaptiveThreshold with all 4 combinations
tester.test_full_combinations(
    strategy_name="AdaptiveThreshold",
    params={'initial_thresh': 0.22, 'max_gap': 40}
)

# Tests: JSON+HTTP, JSON+MQTT, CBOR+HTTP, CBOR+MQTT
# Results saved to: results/combinations/AdaptiveThreshold_full_combinations.csv
```

---

## Available Strategies

### AdaptiveSampling
```python
params = {
    'low_thresh': 0.12,    # Stable region threshold
    'high_thresh': 0.35    # Unstable region threshold
}
```

### AdaptiveThreshold
```python
params = {
    'initial_thresh': 0.22,  # Starting threshold
    'max_gap': 40            # Max samples between transmissions
}
```

### Aggregation
```python
params = {
    'window': 5,          # Aggregation window size
    'method': 'mean'      # 'mean' or 'median'
}
```

### Filtering
```python
params = {
    'window': 5  # Moving average window size
}
```

---

## Result Metrics

Each test returns:

| Metric | Description |
|--------|-------------|
| `reduction_rate_mean` | % of data points eliminated (higher is better) |
| `reduction_rate_std` | Standard deviation across runs |
| `rmse_mean` | Reconstruction error (lower is better) |
| `rmse_std` | Standard deviation of RMSE |
| `serialized_size_mean` | Bytes after serialization (lower is better) |
| `serialized_size_std` | Standard deviation of size |
| `baseline_size_mean` | Original data size (no reduction) |
| `size_reduction_%` | Serialization compression % |
| `strategies` | Strategy chain used |
| `serializer` | JSON or CBOR |
| `protocol` | HTTP or MQTT |
| `num_runs` | Number of test repetitions |

---

## Interpreting Results

### High Reduction, Low RMSE = Excellent
- Example: AdaptiveThreshold achieves 95.74% reduction, RMSE 0.0726
- Removes most data while maintaining accuracy

### Very High Reduction, Higher RMSE = Aggressive
- Example: AdaptiveSampling+AdaptiveThreshold achieves 99.04%, RMSE 0.1058
- Extremely bandwidth-efficient, some accuracy loss

### Moderate Reduction, Low RMSE = Conservative
- Example: Filtering+AdaptiveSampling achieves 79.42%, RMSE 0.0838
- Safer option when accuracy is critical

### CBOR vs JSON
- CBOR typically 50-60% smaller than JSON
- No difference in RMSE (serialization doesn't affect accuracy)
- Use CBOR when bandwidth/storage matters

### HTTP vs MQTT
- Performance is identical (same strategy, same data)
- Choose based on infrastructure:
  - MQTT: Pub/sub, low overhead, IoT-friendly
  - HTTP: RESTful, easier debugging, web-friendly

---

## Complete Custom Example

```python
from combination_tests import CombinationTester

# Initialize tester
tester = CombinationTester(results_dir="results/my_experiments")

# Test a specific scenario
result = tester.test_single_combination(
    strategies=[
        ("Aggregation", {'window': 3, 'method': 'median'}),
        ("AdaptiveSampling", {'low_thresh': 0.08, 'high_thresh': 0.25})
    ],
    serializer_name="CBOR",
    protocol_name="MQTT",
    num_samples=2000,  # More data points
    num_runs=10        # More test runs for statistical confidence
)

# Print results
print(f"Reduction: {result['reduction_rate_mean']:.2f}% ± {result['reduction_rate_std']:.2f}")
print(f"RMSE: {result['rmse_mean']:.4f} ± {result['rmse_std']:.4f}")
print(f"Size: {result['serialized_size_mean']:.0f} bytes")
print(f"vs Baseline: {result['baseline_size_mean']:.0f} bytes")
print(f"Compression: {result['size_reduction_%']:.1f}%")
```

---

## Visualization Options

After running combination tests:

```bash
# Automatic: visualizes all CSV files in results/combinations/
python visualize_combinations.py
```

Or manually for specific CSV:

```python
from visualize_combinations import (
    plot_protocol_comparison,
    plot_serializer_comparison,
    plot_strategy_chains,
    plot_full_combinations
)
from pathlib import Path

# Protocol comparison
csv_file = Path("results/combinations/AdaptiveSampling_JSON_protocol_comparison.csv")
plot_protocol_comparison(csv_file)

# Serializer comparison
csv_file = Path("results/combinations/AdaptiveThreshold_HTTP_serializer_comparison.csv")
plot_serializer_comparison(csv_file)

# Strategy chains
csv_file = Path("results/combinations/strategy_chains_JSON_HTTP.csv")
plot_strategy_chains(csv_file)

# Full combinations
csv_file = Path("results/combinations/AdaptiveThreshold_full_combinations.csv")
plot_full_combinations(csv_file)
```

---

## Tips

1. **Start with example tests**: Run `python combination_tests.py` first to see the framework in action

2. **Compare apples to apples**: When testing protocols, keep strategy and serializer constant

3. **Use multiple runs**: Default is 5 runs, increase to 10-20 for publication-quality results

4. **Chain thoughtfully**: Order matters! Aggregation before sampling != sampling before aggregation

5. **Check for NaN**: Some combinations may produce NaN RMSE if data is completely filtered out

6. **Visualize everything**: Always run `python visualize_combinations.py` after testing to see results

7. **Save results**: CSV files are small, keep everything for later analysis

---

## Troubleshooting

**Import errors**: Make sure you're in the project root directory
```bash
cd C:\Users\sharmaam\iot-cloud-framework\iot-cloud-framework
```

**Module not found**: Check Python environment is activated
```bash
C:/Users/sharmaam/iot-cloud-framework/projectenv/Scripts/Activate.ps1
```

**NaN RMSE**: Strategy filtered out all data, try less aggressive parameters

**Plots look wrong**: Check CSV has valid data (not all NaN or zeros)

---

## Example Research Questions

Use this framework to answer:

1. **"Which serializer saves more bandwidth?"**
   → Use `test_serializer_variations()`

2. **"Does protocol choice affect performance?"**
   → Use `test_protocol_variations()`

3. **"What's the best 2-stage reduction pipeline?"**
   → Use `test_strategy_chains()` with all pairs

4. **"What configuration minimizes cost while keeping RMSE < 0.1?"**
   → Run full tests, filter results where `rmse_mean < 0.1`, sort by `reduction_rate_mean`

5. **"Can we achieve 98% reduction with RMSE < 0.08?"**
   → Test chain: AdaptiveSampling + AdaptiveThreshold with tuned parameters
