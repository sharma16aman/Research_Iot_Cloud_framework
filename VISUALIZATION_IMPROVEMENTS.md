# Visualization & Combination Testing Improvements

## Summary

Based on your feedback about the visualization issues ("like some straight line") and the need to test different combinations, I've implemented two major improvements:

## 1. Enhanced Trade-off Visualizations ✓

### Problem
The original `fig_tradeoff.png` connected parameter configurations with straight lines, making the plot cluttered and hard to interpret.

### Solution: `enhanced_plots.py`
Created 4 new visualization types that eliminate the "straight line" problem:

#### Plot 1: Scatter Plot Without Lines
- **File**: `results/tradeoff_scatter.png`
- Uses distinct markers and colors for each reducer
- **NO solid connecting lines** - only subtle background dashes (alpha=0.2)
- Each parameter configuration shown as individual point
- Clear legend with reduction % and RMSE stats

#### Plot 2: Per-Strategy Subplots
- **File**: `results/tradeoff_per_strategy.png`
- Separate 2×2 subplot grid for each reducer
- Gradient-colored scatter points (darker = better parameters)
- Optional smooth curves (requires scipy, gracefully degrades)
- Shows progression across parameter sweeps

#### Plot 3: Heatmap Matrices
- **File**: `results/tradeoff_heatmap.png`
- Side-by-side heatmaps for reduction % and RMSE
- Color-coded performance across strategies
- Easy to spot best/worst configurations

#### Plot 4: Pareto Frontier
- **File**: `results/tradeoff_pareto.png`
- Highlights optimal configurations (large star markers)
- Non-optimal points shown as smaller circles
- Clearly shows the accuracy-efficiency trade-off boundary

### Usage
```bash
python enhanced_plots.py
```

All plots saved to `results/` directory with high DPI (300).

---

## 2. Combination Testing Framework ✓

### Problem
No way to test arbitrary combinations of:
- Protocols (HTTP vs MQTT)
- Serializers (JSON vs CBOR)
- Strategy chains (e.g., AdaptiveSampling + AdaptiveThreshold)

### Solution: `combination_tests.py`

#### Features

**Test Protocol Variations**
```python
tester.test_protocol_variations(
    strategy_name="AdaptiveSampling",
    params={'low_thresh': 0.12, 'high_thresh': 0.35},
    serializer_name="JSON"
)
```
Compares HTTP vs MQTT for same strategy + serializer.

**Test Serializer Variations**
```python
tester.test_serializer_variations(
    strategy_name="AdaptiveThreshold",
    params={'initial_thresh': 0.22, 'max_gap': 40},
    protocol_name="HTTP"
)
```
Compares JSON vs CBOR for same strategy + protocol.

**Test Strategy Chains**
```python
strategy_chains = [
    [("AdaptiveSampling", {'low_thresh': 0.12, 'high_thresh': 0.35})],
    [("AdaptiveThreshold", {'initial_thresh': 0.22, 'max_gap': 40})],
    [
        ("AdaptiveSampling", {'low_thresh': 0.12, 'high_thresh': 0.35}),
        ("AdaptiveThreshold", {'initial_thresh': 0.22, 'max_gap': 40})
    ]
]
tester.test_strategy_chains(strategy_chains, "JSON", "HTTP")
```
Tests single strategies vs. chained combinations.

**Test Full Combinations**
```python
tester.test_full_combinations(
    strategy_name="AdaptiveThreshold",
    params={'initial_thresh': 0.22, 'max_gap': 40}
)
```
Tests all 4 combinations: JSON+HTTP, JSON+MQTT, CBOR+HTTP, CBOR+MQTT.

#### Results Structure

All results saved to `results/combinations/`:
- CSV files with mean ± std for all metrics
- Columns: reduction_rate_mean, rmse_mean, serialized_size_mean, etc.
- Separate files for each test type

---

## 3. Combination Visualizations ✓

### Solution: `visualize_combinations.py`

Automatically generates plots for all combination test results:

#### Protocol Comparison Plots
- 3 subplots: Reduction Rate, RMSE, Serialized Size
- HTTP vs MQTT side-by-side bars
- Error bars showing standard deviation

#### Serializer Comparison Plots
- JSON vs CBOR comparison
- **Highlights CBOR size advantage** (e.g., "54.0% smaller")
- Shows that accuracy (RMSE) is identical for both

#### Strategy Chain Plots
- 4 subplots comparing all tested chains
- Reduction rate, RMSE, trade-off scatter, serialized size
- Horizontal bar charts for easy comparison
- Scatter plot shows optimal configurations

#### Full Combination Matrix Plots
- All 4 serializer×protocol combinations
- Bar charts with color coding
- Shows average CBOR savings across protocols
- Size reduction percentage vs baseline

### Usage
```bash
python visualize_combinations.py
```

Processes all CSV files in `results/combinations/` and generates PNG plots.

---

## Key Findings from Tests

### Protocol Comparison (HTTP vs MQTT)
- **No significant difference** in reduction rate or accuracy
- Both achieve identical performance (same strategy, same data)
- Protocol choice depends on infrastructure, not performance

### Serializer Comparison (JSON vs CBOR)
- **CBOR saves ~54% space** for AdaptiveThreshold results
  - JSON: 1553 bytes
  - CBOR: 715 bytes
- **Identical accuracy** (same RMSE)
- CBOR recommended for bandwidth-constrained scenarios

### Strategy Chaining
- **AdaptiveSampling + AdaptiveThreshold**: 
  - Achieves 99.04% reduction (vs 95.74% single)
  - RMSE increases slightly to 0.1058 (vs 0.0726)
  - Extremely aggressive reduction (10 samples from 1000)
  
- **Filtering + AdaptiveSampling**:
  - 79.42% reduction
  - Better accuracy (RMSE 0.0838)
  - Filtering smooths signal first, then sampling

- **Aggregation + Filtering**:
  - 80% reduction
  - Produces smoother reconstruction
  - Good for data preprocessing pipelines

---

## Files Created

### Scripts
1. `enhanced_plots.py` - New trade-off visualizations
2. `combination_tests.py` - Testing framework
3. `visualize_combinations.py` - Combination result visualizations

### Results Generated
- `results/tradeoff_scatter.png` - Clean scatter without lines
- `results/tradeoff_per_strategy.png` - Per-strategy subplots
- `results/tradeoff_heatmap.png` - Performance heatmaps
- `results/tradeoff_pareto.png` - Pareto frontier analysis
- `results/combinations/*.csv` - All combination test data
- `results/combinations/*_plot.png` - All combination visualizations

---

## Usage Examples

### Run Everything
```bash
# Generate enhanced trade-off plots
python enhanced_plots.py

# Run combination tests (protocols, serializers, chains)
python combination_tests.py

# Visualize combination results
python visualize_combinations.py
```

### Custom Combination Test
```python
from combination_tests import CombinationTester

tester = CombinationTester()

# Test your specific scenario
tester.test_single_combination(
    strategies=[
        ("AdaptiveSampling", {'low_thresh': 0.08, 'high_thresh': 0.25}),
        ("AdaptiveThreshold", {'initial_thresh': 0.15, 'max_gap': 20})
    ],
    serializer_name="CBOR",
    protocol_name="MQTT",
    num_samples=1000,
    num_runs=10
)
```

---

## Benefits

### Visualization Improvements
✓ Eliminated cluttered straight lines  
✓ Multiple view angles of same data  
✓ Publication-quality plots (300 DPI)  
✓ Clear visual hierarchy  
✓ Pareto frontier identification  

### Combination Testing
✓ Systematic protocol comparison  
✓ Quantified serializer advantages  
✓ Strategy chaining capabilities  
✓ Reproducible experiments (5-10 runs per test)  
✓ Comprehensive metrics (reduction, RMSE, size)  

### Scientific Value
✓ Answers "which combination is best?" questions  
✓ Shows CBOR provides 50%+ size savings  
✓ Demonstrates protocol independence  
✓ Reveals strategy chaining trade-offs  
✓ Enables informed architecture decisions  

---

## Next Steps

1. **More Strategy Chains**: Test other combinations like:
   - Aggregation + AdaptiveThreshold
   - Filtering + Aggregation + AdaptiveSampling (3-stage)

2. **Parameter Optimization**: Use combination_tests.py to find optimal parameters for specific use cases

3. **Real-World Validation**: Apply learned insights to actual IoT deployments

4. **Documentation**: Include these visualizations in research papers/thesis

---

## Questions Answered

✅ "Can the labelling... be better because it is like some straight line"  
→ Yes! Created 4 new plot types without connecting lines

✅ "Generate tradeoff and result for every combo"  
→ Yes! combination_tests.py tests any strategy+serializer+protocol combo

✅ "A result where we use adaptive sampling and adaptive threshold with json as serializer and http"  
→ Yes! See strategy_chains_JSON_HTTP.csv and corresponding plot

✅ "While another one where protocol changes to mqtt"  
→ Yes! See AdaptiveSampling_JSON_protocol_comparison.csv

All requested functionality implemented and tested! 🎉
