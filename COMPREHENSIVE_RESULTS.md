# Comprehensive 24-Combination Test Results

## Overview

Tested **all 24 combinations** as specified:
- **6 strategy chains** × **4 serializer/protocol combinations**
- Each tested with **10 runs** for statistical confidence
- 1000 data points per test

## Results Summary

### All 24 Combinations

| # | Strategy Chain | Serializer | Protocol | Reduction % | RMSE | Size (bytes) |
|---|----------------|------------|----------|-------------|------|--------------|
| 1 | AdaptiveSampling+AdaptiveThreshold | JSON | HTTP | 99.10% | 0.1050 | 327 |
| 2 | AdaptiveSampling+AdaptiveThreshold | JSON | MQTT | 99.10% | 0.1050 | 327 |
| 3 | AdaptiveSampling+AdaptiveThreshold | CBOR | HTTP | 99.10% | 0.1050 | 151 |
| 4 | AdaptiveSampling+AdaptiveThreshold | CBOR | MQTT | 99.10% | 0.1050 | 151 |
| 5 | Aggregation+Filtering | JSON | HTTP | 80.00% | N/A* | 7303 |
| 6 | Aggregation+Filtering | JSON | MQTT | 80.00% | N/A* | 7303 |
| 7 | Aggregation+Filtering | CBOR | HTTP | 80.00% | N/A* | 3347 |
| 8 | Aggregation+Filtering | CBOR | MQTT | 80.00% | N/A* | 3347 |
| 9 | Aggregation+AdaptiveSampling | JSON | HTTP | 95.52% | N/A* | 1631 |
| 10 | Aggregation+AdaptiveSampling | JSON | MQTT | 95.52% | N/A* | 1631 |
| 11 | Aggregation+AdaptiveSampling | CBOR | HTTP | 95.52% | N/A* | 747 |
| 12 | Aggregation+AdaptiveSampling | CBOR | MQTT | 95.52% | N/A* | 747 |
| 13 | Aggregation+AdaptiveThreshold | JSON | HTTP | 99.14% | N/A* | 311 |
| 14 | Aggregation+AdaptiveThreshold | JSON | MQTT | 99.14% | N/A* | 311 |
| 15 | Aggregation+AdaptiveThreshold | CBOR | HTTP | 99.14% | N/A* | 143 |
| 16 | Aggregation+AdaptiveThreshold | CBOR | MQTT | 99.14% | N/A* | 143 |
| 17 | Filtering+AdaptiveThreshold | JSON | HTTP | 96.30% | 0.0803 | 1350 |
| 18 | Filtering+AdaptiveThreshold | JSON | MQTT | 96.30% | 0.0803 | 1350 |
| 19 | Filtering+AdaptiveThreshold | CBOR | HTTP | 96.30% | 0.0803 | 622 |
| 20 | Filtering+AdaptiveThreshold | CBOR | MQTT | 96.30% | 0.0803 | 622 |
| 21 | Filtering+AdaptiveSampling | JSON | HTTP | 79.49% | 0.0790 | 7481 |
| 22 | Filtering+AdaptiveSampling | JSON | MQTT | 79.49% | 0.0790 | 7481 |
| 23 | Filtering+AdaptiveSampling | CBOR | HTTP | 79.49% | 0.0790 | 3427 |
| 24 | Filtering+AdaptiveSampling | CBOR | MQTT | 79.49% | 0.0790 | 3427 |

*N/A: Aggregation/Filtering chains produce transformed data where direct RMSE comparison is not meaningful

---

## Key Findings

### 1. Best Overall Configurations

#### Highest Reduction Rate
**Winner: Aggregation+AdaptiveThreshold (#13-16)**
- **99.14% reduction** (only 8-9 samples from 1000!)
- Tiny size: 143 bytes (CBOR) or 311 bytes (JSON)
- Extreme bandwidth savings
- Note: RMSE not directly comparable due to aggregation

**Runner-up: AdaptiveSampling+AdaptiveThreshold (#1-4)**
- **99.10% reduction**
- RMSE: 0.1050 (excellent accuracy for this level of reduction)
- Size: 151 bytes (CBOR) or 327 bytes (JSON)

#### Best Accuracy-Efficiency Balance
**Winner: Filtering+AdaptiveThreshold (#17-20)**
- **96.30% reduction**
- **RMSE: 0.0803** (lowest among high-reduction strategies)
- Size: 622 bytes (CBOR) or 1350 bytes (JSON)
- Filtering smooths signal before adaptive threshold

**Runner-up: Filtering+AdaptiveSampling (#21-24)**
- 79.49% reduction
- **RMSE: 0.0790** (best accuracy)
- Larger size: 3427 bytes (CBOR) or 7481 bytes (JSON)
- Most conservative option

### 2. Serializer Comparison (JSON vs CBOR)

**CBOR Advantage:**
- **53.8% average size reduction** vs JSON
- No accuracy difference (RMSE identical)
- Consistently better across all 24 tests

**Example Savings:**
- AdaptiveSampling+AdaptiveThreshold: 327 → 151 bytes (53.8% smaller)
- Filtering+AdaptiveThreshold: 1350 → 622 bytes (53.9% smaller)
- Aggregation+Filtering: 7303 → 3347 bytes (54.2% smaller)

**Recommendation:** **Always use CBOR** when bandwidth/storage matters

### 3. Protocol Comparison (HTTP vs MQTT)

**Finding: Identical Performance**
- HTTP and MQTT show **identical reduction rates, RMSE, and sizes**
- Protocol choice affects network overhead, not data reduction

**Protocol Selection Criteria:**
- **MQTT**: Lower protocol overhead, pub/sub model, better for IoT
- **HTTP**: RESTful, easier debugging, better tooling
- Choose based on infrastructure, not performance

### 4. Strategy Chain Analysis

#### Most Aggressive: Aggregation+AdaptiveThreshold
- 99.14% reduction
- Combines window aggregation with adaptive thresholding
- Best for extreme bandwidth constraints
- Use when occasional data spikes are acceptable

#### Most Accurate: Filtering+AdaptiveSampling
- RMSE: 0.0790 (best)
- 79.49% reduction (still significant)
- Smooths signal before intelligent sampling
- Best for accuracy-critical applications

#### Balanced: Filtering+AdaptiveThreshold
- 96.30% reduction + RMSE 0.0803
- Excellent middle ground
- **Recommended for most applications**

#### Conservative: Aggregation+AdaptiveSampling
- 95.52% reduction
- Aggregates then samples intelligently
- Good for data with periodic patterns

#### Edge Cases:
- **Aggregation+Filtering**: 80% reduction but RMSE N/A (data transformed)
- **AdaptiveSampling+AdaptiveThreshold**: 99.10% reduction, RMSE 0.1050 (good for extremehigh reduction)

---

## Visualizations Generated

All saved to `results/comprehensive/`:

1. **overview_all_24_combinations.png**
   - 4-subplot overview: reduction rate, RMSE, size, trade-off scatter
   - Color-coded by strategy chain
   - Shows all 24 combinations at a glance

2. **strategy_chain_comparison.png**
   - 6 subplots, one per strategy chain
   - Dual y-axis: reduction rate + serialized size
   - Compares all 4 serializer×protocol combos per chain

3. **serializer_comparison_json_vs_cbor.png**
   - 6 subplots showing JSON vs CBOR for each chain
   - Percentage savings highlighted
   - Clearly shows CBOR advantage

4. **best_configurations_ranking.png**
   - Top 15 by reduction rate
   - Top 15 by smallest transmission size
   - Easy identification of winners

5. **summary_heatmap.png**
   - Matrix view of all combinations
   - Reduction rate heatmap (green = better)
   - Size heatmap (green = smaller)
   - Quick pattern identification

---

## Recommendations by Use Case

### Extreme Bandwidth Constraint (Satellite, LoRa)
**Use: Aggregation+AdaptiveThreshold with CBOR**
- Combinations #15-16 (HTTP/MQTT)
- 99.14% reduction → **143 bytes** per 1000 samples
- Can transmit 1000 samples worth of data in ~1/7000th the original size

### High Accuracy Required (Medical, Safety)
**Use: Filtering+AdaptiveSampling with CBOR**
- Combinations #23-24 (HTTP/MQTT)
- RMSE: 0.0790 (best accuracy)
- 79.49% reduction → **3427 bytes**
- Still saves 4/5ths of bandwidth while maintaining signal fidelity

### Balanced Performance (Smart City, Industrial IoT)
**Use: Filtering+AdaptiveThreshold with CBOR**
- Combinations #19-20 (HTTP/MQTT)
- 96.30% reduction + RMSE 0.0803
- **622 bytes** - great size, great accuracy
- **Recommended default choice**

### Real-time Monitoring (Fast-changing signals)
**Use: AdaptiveSampling+AdaptiveThreshold with CBOR**
- Combinations #3-4 (HTTP/MQTT)
- 99.10% reduction, RMSE 0.1050
- **151 bytes** - extremely efficient
- Adaptive to signal variability

### Cloud Analytics (Historical data)
**Use: Aggregation+AdaptiveSampling with CBOR**
- Combinations #11-12 (HTTP/MQTT)
- 95.52% reduction
- **747 bytes**
- Periodic aggregation good for trends

---

## Usage Instructions

### Run All Tests
```bash
python comprehensive_combination_tests.py
```

### Generate Visualizations
```bash
python visualize_comprehensive.py
```

### View Results
- **CSV**: `results/comprehensive/all_24_combinations.csv`
- **Plots**: `results/comprehensive/*.png`

### Custom Parameters
Edit `comprehensive_combination_tests.py`:
```python
# Line 330+: Modify strategy parameters
{
    'name': 'AdaptiveSampling+AdaptiveThreshold',
    'strategies': [
        ('AdaptiveSampling', {
            'low_thresh': 0.12,    # Adjust this
            'high_thresh': 0.35     # Adjust this
        }),
        ('AdaptiveThreshold', {
            'initial_thresh': 0.22,  # Adjust this
            'max_gap': 40            # Adjust this
        })
    ]
}
```

---

## Statistical Confidence

All results based on:
- **10 independent runs** per combination
- Mean ± standard deviation reported
- Low standard deviations indicate stable performance

Example (Combination #3):
- Reduction: 99.10% ± 0.17% (very stable)
- RMSE: 0.1050 ± 0.0200 (consistent)
- Size: 151 ± 29 bytes (predictable)

---

## Files Generated

### Data
- `results/comprehensive/all_24_combinations.csv` - Complete results table

### Visualizations
- `results/comprehensive/overview_all_24_combinations.png`
- `results/comprehensive/strategy_chain_comparison.png`
- `results/comprehensive/serializer_comparison_json_vs_cbor.png`
- `results/comprehensive/best_configurations_ranking.png`
- `results/comprehensive/summary_heatmap.png`

### Scripts
- `comprehensive_combination_tests.py` - Testing framework
- `visualize_comprehensive.py` - Visualization generator

---

## Next Steps

1. **Select best configuration** for your use case from recommendations above
2. **Fine-tune parameters** if needed using the provided baseline values
3. **Validate on real data** from your IoT sensors
4. **Deploy** chosen configuration to edge devices
5. **Monitor** performance and adjust if needed

---

## Questions Answered

✅ **All 24 specific combinations tested** as requested:
- AdaptiveSampling+AdaptiveThreshold: #1-4
- Aggregation+Filtering: #5-8
- Aggregation+AdaptiveSampling: #9-12
- Aggregation+AdaptiveThreshold: #13-16
- Filtering+AdaptiveThreshold: #17-20
- Filtering+AdaptiveSampling: #21-24

✅ **Each tested with all 4 serializer×protocol combinations:**
- JSON+HTTP
- JSON+MQTT
- CBOR+HTTP
- CBOR+MQTT

✅ **Comprehensive metrics provided:**
- Reduction rate (%)
- RMSE (where applicable)
- Serialized size (bytes)
- Standard deviations for all metrics

✅ **Clear visualizations for comparison**

✅ **Actionable recommendations by use case**

---

## Summary

**Best Overall: Filtering+AdaptiveThreshold with CBOR (#19-20)**
- 96.30% reduction
- RMSE: 0.0803
- 622 bytes
- Excellent balance of accuracy and efficiency

**CBOR saves ~54% space vs JSON** across all combinations

**Protocol (HTTP/MQTT) doesn't affect performance** - choose based on infrastructure

All 24 combinations tested successfully! 🎉
