# QUICKSTART GUIDE

Get started with the IoT Edge-Cloud Data Reduction Framework in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation

1. **Create and activate virtual environment:**

```bash
python -m venv projectenv
projectenv\Scripts\activate  # Windows
# or
source projectenv/bin/activate  # Linux/Mac
```

2. **Install dependencies:**

```bash
pip install -r requirement.txt
```

## Running Your First Experiment

### Option 1: Default Configuration (Recommended)

Just run the main script:

```bash
python main.py
```

This will:
- Generate synthetic sensor data
- Apply multiple reduction strategies
- Compare JSON and CBOR serialization
- Generate plots and tables in the `results/` folder

Expected output:
```
results/
├── results_vectorized.csv      # Raw experiment data
├── summary_table.csv           # Statistical summary
├── summary_table.tex           # LaTeX table
├── fig_tradeoff.png           # Trade-off visualization
└── experiment.log             # Execution log
```

### Option 2: Interactive Tutorial

Open the Jupyter notebook for step-by-step guidance:

```bash
jupyter notebook tutorial.ipynb
```

## Understanding the Results

After running experiments, check:

1. **Trade-off Plot** (`results/fig_tradeoff.png`):
   - X-axis: Data reduction percentage (higher = more bandwidth saved)
   - Y-axis: Reconstruction error (lower = better accuracy)
   - Each point represents a parameter configuration

2. **Summary Table** (`results/summary_table.csv`):
   - Compare strategies on reduction, accuracy, and energy
   - Mean ± 95% confidence intervals provided

3. **Raw Results** (`results/results_vectorized.csv`):
   - Complete data for custom analysis
   - Import into Excel, pandas, or your favorite tool

## Customizing Experiments

Edit `data_generation/config.yaml`:

```yaml
experiment:
  mode: "vectorized"           # or "streaming"
  runs: 12                     # number of repetitions
  sensors: 8                   # number of sensors
  timesteps: 600               # samples per sensor
  reducers:                    # strategies to test
    - "AdaptiveSampling"
    - "AdaptiveThreshold"
    - "Aggregation"
    - "Filtering"
  serializers: ["JSON", "CBOR"]  # formats to compare
```

After editing, validate your configuration:

```bash
python data_generation/config_validator.py
```

## Quick Tips

### Faster Experiments
Reduce `runs`, `sensors`, or `timesteps` in config.yaml:
```yaml
runs: 3        # instead of 12
sensors: 4     # instead of 8
timesteps: 300 # instead of 600
```

### More Detailed Analysis
```bash
python evaluation/visualizer.py  # Generate all plots
python cloud/analyzer.py         # Analyze database (if streaming mode)
```

### Debug Issues
Check the log file:
```bash
cat results/experiment.log  # Linux/Mac
type results\experiment.log  # Windows
```

## Common Issues

### "cbor2 not installed"
```bash
pip install cbor2
```
Or remove "CBOR" from `serializers` in config.yaml.

### "Configuration validation failed"
Run the validator to see specific errors:
```bash
python data_generation/config_validator.py
```

### Memory errors with large experiments
Reduce scale:
- Decrease `runs`, `sensors`, or `timesteps`
- Test one reducer at a time
- Use streaming mode instead of vectorized

## Next Steps

1. **Explore the tutorial**: `tutorial.ipynb` for interactive learning
2. **Read the full README**: Detailed documentation in `README.md`
3. **Customize strategies**: Modify parameters in `config.yaml`
4. **Add new strategies**: See `README.md` section on extending

## Example Results

Typical output from default configuration:

| Method | Reduction (%) | RMSE | Energy Proxy |
|--------|--------------|------|--------------|
| AdaptiveSampling | 78.8 ± 2.1 | 0.102 | 221,500 |
| AdaptiveThreshold | 95.3 ± 1.5 | 0.074 | 52,500 |
| Aggregation | 80.0 ± 1.8 | - | 190,000 |

This shows AdaptiveThreshold achieves the highest reduction with good accuracy!

## Getting Help

- Check `README.md` for complete documentation
- Review `tutorial.ipynb` for examples
- Open an issue on GitHub for bugs
- Check `results/experiment.log` for error details

## Quick Command Reference

```bash
# Run experiment
python main.py

# Validate configuration
python data_generation/config_validator.py

# Generate visualizations
python evaluation/visualizer.py

# Analyze database
python cloud/analyzer.py

# Open tutorial
jupyter notebook tutorial.ipynb
```

---

**Ready to start?** Run `python main.py` and explore the results!
