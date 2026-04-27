# Real Data Mode - User Guide

## Overview
The IoT Cloud Framework now supports testing with **real-world datasets** from official sources, in addition to the synthetic data mode.

## Quick Start

### Switch Between Modes

Edit `data_generation/config.yaml`:

```yaml
experiment:
  data_mode: "real"  # or "synthetic"
  real_dataset: "intel_lab"  # which real dataset to use
```

Then run your experiments normally:
```bash
python main.py
python comprehensive_combination_tests.py
python single_strategy_tests.py
```

## Available Datasets

### 1. Intel Berkeley Research Lab (intel_lab)
- **Source**: http://db.csail.mit.edu/labdata/labdata.html
- **Type**: Real IoT sensor data from UC Berkeley lab
- **Sensors**: 54 Mica2Dot sensors deployed in lab
- **Metrics**: Temperature, Humidity, Light, Voltage
- **Records**: 2.3M+ readings over 1 month (Feb-Apr 2004)
- **Usage**: Set `real_dataset: "intel_lab"` in config
- **Default Metric**: Temperature (Celsius)

**Data Characteristics**:
- Real-world noise and sensor drift
- Missing values and sensor dropouts
- Temporal patterns (day/night cycles)
- Spatial correlation between nearby sensors

### 2. Synthetic Realistic Data (sample)
- **Source**: Algorithmically generated
- **Type**: Realistic synthetic data with noise patterns
- **Usage**: Set `real_dataset: "sample"` in config
- **Good For**: Quick testing without downloads

### 3. Smart Building Data (smart_building) - Coming Soon
- **Type**: Building automation system data
- **Status**: Planned addition

## Configuration Options

### Full Config Example

```yaml
experiment:
  # === DATA MODE CONFIGURATION ===
  data_mode: "real"           # "synthetic" or "real"
  real_dataset: "intel_lab"   # Which real dataset to use
  
  # Standard configuration (same for both modes)
  runs: 10
  sensors: 5
  timesteps: 100
  
  # Reduction strategies to test
  reducers:
    - "AdaptiveSampling"
    - "AdaptiveThreshold"
    - "Aggregation"
    - "Filtering"
```

### Data Mode Options

| Mode | Description | Data Source |
|------|-------------|-------------|
| `synthetic` | Generated data with configurable patterns | `data_generation/synthetic_sensors.py` |
| `real` | Real-world IoT datasets | Official repositories (downloads automatically) |

### Real Dataset Options

| Dataset | Key | Source Organization | Best For |
|---------|-----|---------------------|----------|
| Intel Lab | `intel_lab` | UC Berkeley / MIT CSAIL | Temperature monitoring, indoor environments |
| Sample | `sample` | N/A | Quick testing, offline development |

## How It Works

### Data Loading Process

1. **Configuration Check**: Framework reads `data_mode` from config.yaml
2. **Mode Selection**:
   - **Synthetic**: Generates data using `generate_dataset()` with noise patterns
   - **Real**: Downloads and processes real dataset using `get_real_dataset()`
3. **Data Preparation**: Real data is formatted to match framework expectations:
   - Shape: `(n_sensors, timesteps)` numpy array
   - Values: Floating point sensor readings
   - Metadata: Source information, units, date ranges
4. **Experiment Execution**: All reduction strategies work identically on both modes

### Intel Lab Dataset Processing

```python
from data_generation.real_data_loader import get_real_dataset

# Load Intel Lab temperature data
real_data, metadata = get_real_dataset(
    dataset_name="intel_lab",
    n_sensors=5,
    timesteps=100
)

# real_data.shape = (5, 100)
# metadata = {
#     'source': 'Intel Berkeley Research Lab',
#     'sensor_type': 'Temperature',
#     'units': 'Celsius',
#     'total_records': 2300000+,
#     'total_sensors': 54,
#     'url': 'http://db.csail.mit.edu/labdata/labdata.html'
# }
```

### Automatic Features

- **Auto-download**: Dataset downloaded automatically on first use
- **Caching**: Downloaded data stored in `data_generation/real_datasets/`
- **Preprocessing**: 
  - Removes invalid readings (NaN, out-of-range)
  - Handles missing values
  - Selects most active sensors
  - Extracts contiguous time windows
- **Error Handling**: Falls back gracefully if download fails

## Results Comparison

### Test Results: Synthetic vs Real Data

```
Synthetic Data (AdaptiveThreshold):
  Reduction: 93.11%
  RMSE: 0.074

Real Data - Intel Lab (AdaptiveThreshold):
  Reduction: 52.64%
  RMSE: 0.089
```

**Key Insights**:
- Real data shows lower reduction rates (more variability)
- Real data has slightly higher RMSE (less predictable patterns)
- Both modes validate strategy effectiveness
- Real data provides production-realistic expectations

### Why Different Performance?

| Aspect | Synthetic | Real |
|--------|-----------|------|
| Noise | Gaussian white noise | Sensor drift, electromagnetic interference |
| Patterns | Regular sine/cosine waves | Irregular day/night cycles, occupancy effects |
| Missing Data | None | ~5-10% dropout rate |
| Outliers | Rare | Common (sensor malfunctions) |
| Predictability | High | Low |

## Usage Examples

### Example 1: Compare Strategy Performance on Real Data

```bash
# Edit config.yaml
data_mode: "real"
real_dataset: "intel_lab"

# Run single-strategy tests
python single_strategy_tests.py

# Results in: results/single_strategies/
# - performance_overview.png
# - serializer_comparison.png
# - summary_table.png
```

### Example 2: Test All 24 Combinations on Real Data

```bash
# Edit config.yaml
data_mode: "real"
real_dataset: "intel_lab"

# Run comprehensive tests
python comprehensive_combination_tests.py

# Results in: results/comprehensive/
# - overview_comparison.png
# - strategy_comparison.png
# - serializer_protocol_comparison.png
```

### Example 3: A/B Test Synthetic vs Real

```python
import yaml
from main import run_vectorized

# Load config
with open("data_generation/config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

# Test synthetic
cfg["experiment"]["data_mode"] = "synthetic"
df_synth = run_vectorized(cfg)

# Test real
cfg["experiment"]["data_mode"] = "real"
cfg["experiment"]["real_dataset"] = "intel_lab"
df_real = run_vectorized(cfg)

# Compare
print(f"Synthetic reduction: {df_synth['reduction_pct'].mean():.2f}%")
print(f"Real reduction: {df_real['reduction_pct'].mean():.2f}%")
```

### Example 4: Quick Test Script

Use the provided test script:
```bash
python test_real_data.py
```

Output:
```
======================================================================
TEST 1: SYNTHETIC DATA MODE (baseline)
======================================================================
[OK] Synthetic mode: 36 results

======================================================================
TEST 2: REAL DATA MODE (Intel Lab)
======================================================================
[OK] Real mode: 36 results

======================================================================
COMPARISON
======================================================================
Synthetic Data:
  Reduction: 93.11%
  RMSE (where applicable): 0.0745

Real Data (Intel Lab):
  Reduction: 52.64%
  RMSE (where applicable): 0.0892

[OK] Both modes working successfully!
```

## Advanced Usage

### Custom Real Dataset Integration

To add your own real-world dataset:

1. **Add Dataset Loader** to `data_generation/real_data_loader.py`:

```python
def load_my_dataset(self, n_sensors=5, timesteps=100):
    """Load custom dataset"""
    # Download data
    url = "https://example.com/data.csv"
    filepath = self.download_file(url, "my_data.csv")
    
    # Parse data
    df = pd.read_csv(filepath)
    # ... preprocessing ...
    
    # Prepare for framework
    sensor_data, metadata = self.prepare_for_framework(
        df, 
        sensor_col='sensor_id',
        value_col='measurement',
        time_col='timestamp',
        n_sensors=n_sensors,
        timesteps=timesteps
    )
    
    metadata.update({
        'source': 'My Organization',
        'sensor_type': 'My Metric',
        'units': 'My Units'
    })
    
    return sensor_data, metadata
```

2. **Register Dataset** in `get_real_dataset()`:

```python
def get_real_dataset(dataset_name="intel_lab", n_sensors=5, timesteps=100):
    loader = RealDataLoader()
    
    if dataset_name == "my_dataset":
        return loader.load_my_dataset(n_sensors, timesteps)
    # ... existing datasets ...
```

3. **Use in Config**:

```yaml
experiment:
  data_mode: "real"
  real_dataset: "my_dataset"
```

## Troubleshooting

### Issue: Download Fails

**Symptom**: "Failed to download dataset" error

**Solutions**:
1. Check internet connection
2. Verify dataset URL is accessible
3. Check firewall/proxy settings
4. Use `real_dataset: "sample"` for offline testing

### Issue: Not Enough Data

**Symptom**: "Could not find enough sensors/timesteps"

**Solutions**:
1. Reduce `sensors` or `timesteps` in config
2. Use dataset with more data (Intel Lab has 54 sensors)
3. Check data quality in downloaded file

### Issue: Memory Error

**Symptom**: OutOfMemoryError during loading

**Solutions**:
1. Reduce number of sensors/timesteps
2. Enable data sampling in loader
3. Process dataset in chunks

### Issue: Wrong Data Format

**Symptom**: Shape mismatch or type errors

**Solutions**:
1. Check `prepare_for_framework()` output shape
2. Verify data is numeric (not strings)
3. Ensure no NaN values in final array

## Performance Considerations

### Dataset Size vs Performance

| Dataset | Records | Download Time | Load Time | Memory |
|---------|---------|---------------|-----------|--------|
| Intel Lab | 2.3M | ~5-10 sec | ~2-3 sec | ~50 MB |
| Sample | Generated | 0 sec | <1 sec | Negligible |

### Optimization Tips

1. **Cache Downloads**: Real datasets cached after first download
2. **Sensor Selection**: Use fewer sensors for faster experiments
3. **Timestep Limits**: 100-200 timesteps sufficient for most tests
4. **Parallel Testing**: Run multiple experiments in parallel

## Best Practices

### Research & Development

1. **Start with Synthetic**: Debug your strategies on synthetic data first
2. **Validate with Real**: Confirm performance on real-world data
3. **Compare Both Modes**: Report results for both synthetic and real
4. **Document Differences**: Explain why performance differs between modes

### Production Deployment

1. **Train on Real**: Use real data for parameter tuning
2. **Test Edge Cases**: Real data exposes more failure modes
3. **Monitor Continuously**: Real-world patterns change over time
4. **Validate Regularly**: Re-test strategies on fresh real data

### Academic Publications

1. **Cite Data Source**: Always cite original dataset source
2. **Report Both Modes**: Include synthetic baseline + real validation
3. **Describe Preprocessing**: Document how real data was prepared
4. **Share Results**: Make your configs and results reproducible

## FAQ

**Q: Why use real data if synthetic works?**  
A: Real data validates that strategies work in production environments with real-world noise, drift, and anomalies.

**Q: Can I use my own sensor data?**  
A: Yes! Follow the "Custom Real Dataset Integration" section above.

**Q: Which dataset should I use?**  
A: Intel Lab for indoor temperature/environmental monitoring. Add custom datasets for other sensor types.

**Q: Does real data change my results?**  
A: Yes, typically lower reduction rates but more realistic performance expectations.

**Q: Do I need to download data every time?**  
A: No, data is cached after first download in `data_generation/real_datasets/`.

**Q: Can I test strategies side-by-side?**  
A: Yes! Use `test_real_data.py` or write custom comparison scripts.

**Q: What if the dataset URL breaks?**  
A: Use cached version or switch to `real_dataset: "sample"` for testing.

## Citation

If you use the Intel Lab dataset in your research, please cite:

```
@inproceedings{madden2004intel,
  title={Intel Lab Data},
  author={Madden, Samuel},
  booktitle={UC Berkeley / Intel Research Lab},
  year={2004},
  url={http://db.csail.mit.edu/labdata/labdata.html}
}
```

## See Also

- [COMPREHENSIVE_RESULTS.md](COMPREHENSIVE_RESULTS.md) - Results with 24 strategy combinations
- [SINGLE_STRATEGY_RESULTS.md](SINGLE_STRATEGY_RESULTS.md) - Individual strategy analysis
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference
- [README.md](README.md) - Main project documentation

## Support

For issues or questions:
1. Check this guide first
2. Review error messages carefully
3. Try `real_dataset: "sample"` to isolate data loading issues
4. Check data file integrity in `data_generation/real_datasets/`

---

**Last Updated**: Based on real data integration with Intel Berkeley Research Lab dataset  
**Framework Version**: v2.0 (Dual-mode support)
