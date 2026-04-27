# IoT Edge-Cloud Data Reduction Framework

A modular benchmarking framework for evaluating and comparing edge-based IoT data reduction strategies under controlled, reproducible conditions.

## 📋 Overview

This framework implements a three-layer IoT architecture (Sensing → Edge → Cloud) to systematically evaluate data reduction techniques that minimize bandwidth consumption while preserving data fidelity. It enables fair comparison of multiple reduction strategies under identical experimental conditions.

### Key Features

- **Dual Data Mode**: Test with synthetic OR real-world datasets
  - **Synthetic**: Reproducible multi-sensor time-series with configurable noise, spikes, drift
  - **Real**: Official datasets (Intel Berkeley Research Lab temperature/humidity data)
- **Multiple Reduction Strategies**:
  - Adaptive Sampling (dynamic sampling rate based on signal variability)
  - Adaptive Threshold/Event-Driven (Kalman filter + Page-Hinkley drift detection)
  - Aggregation (window-based statistical summarization)
  - Filtering (moving average and exponential smoothing)
- **Flexible Serialization**: JSON and CBOR support
- **Protocol Handlers**: MQTT and HTTP transmission simulation
- **Cloud Storage**: SQLite database for received data
- **Comprehensive Metrics**:
  - Efficiency: Data reduction ratio, bytes transmitted, energy proxy
  - Accuracy: RMSE, MAE, signal reconstruction error
- **Automated Experimentation**: Parameter sweeps, statistical analysis, visualization

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IoT Sensing Layer                        │
│  (Synthetic sensors generating time-series data)            │
└────────────────────┬────────────────────────────────────────┘
                     │ Raw sensor data
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Edge Processing Layer                      │
│  • Adaptive Sampling      • Aggregation                     │
│  • Event-Driven Trigger   • Filtering                       │
│  • Local computation and data reduction                     │
└────────────────────┬────────────────────────────────────────┘
                     │ Reduced data stream
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Layer                            │
│  • Data reception (MQTT/HTTP)                               │
│  • Signal reconstruction                                    │
│  • Storage (SQLite)                                         │
│  • Metric computation and evaluation                        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/iot-cloud-framework.git
cd iot-cloud-framework
```

2. Create a virtual environment (recommended):
```bash
python -m venv projectenv
# On Windows:
projectenv\Scripts\activate
# On Linux/Mac:
source projectenv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirement.txt
```

### Basic Usage

1. **Configure your experiment** by editing `data_generation/config.yaml`:
```yaml
experiment:
  mode: "vectorized"          # or "streaming"
  data_mode: "synthetic"      # or "real" for real-world datasets
  real_dataset: "intel_lab"   # if data_mode is "real"
  runs: 12                    # number of repetitions
  sensors: 8                  # number of sensors
  timesteps: 600              # samples per sensor
  reducers: ["AdaptiveSampling", "AdaptiveThreshold"]
  serializers: ["JSON", "CBOR"]
```

2. **Run the experiment**:
```bash
python main.py
```

3. **View results**:
   - CSV data: `results/results_vectorized.csv`
   - Summary table: `results/summary_table.csv` (and `.tex` for LaTeX)
   - Trade-off plot: `results/fig_tradeoff.png`

### Quick Start: Synthetic vs Real Data

```bash
# Test with synthetic data (default)
python test_real_data.py

# Or manually edit config.yaml:
# data_mode: "synthetic"  # Generated data
# data_mode: "real"       # Intel Lab temperature data
```

See [REAL_DATA_GUIDE.md](REAL_DATA_GUIDE.md) for complete real data usage guide.

## 📊 Experimental Modes

### Vectorized Mode (Recommended for Research)
- Fast batch processing for parameter sweeps
- Multiple runs with different random seeds
- Automatic statistical analysis (mean ± 95% CI)
- Best for generating publication-quality results

```yaml
experiment:
  mode: "vectorized"
  runs: 12
  sensors: 8
  timesteps: 600
```

### Streaming Mode (For Real-time Simulation)
- Simulates real-time sensor data streams
- Optional MQTT/HTTP transmission
- Database storage of received data
- Useful for testing protocol implementations

```yaml
experiment:
  mode: "streaming"
  use_protocols: true
  protocol: "MQTT"  # or "HTTP"
  receive_to_db: true
```

## 🔧 Configuration

### Data Reduction Strategies

Each strategy can be configured with specific parameters:

```yaml
adaptive_sampling:
  base_interval: 1.0
  low_thresh: 0.12      # Low variability threshold
  high_thresh: 0.35     # High variability threshold

adaptive_threshold:
  initial_thresh: 0.22  # Initial change threshold
  max_gap: 40           # Heartbeat interval (samples)
  kf_process_var: 0.006 # Kalman filter process noise
  kf_meas_var: 0.01     # Kalman filter measurement noise
```

### Parameter Sweeps

Test multiple parameter combinations automatically:

```yaml
sweep:
  adaptivesampling:
    low_thresh:  [0.08, 0.12, 0.18]
    high_thresh: [0.25, 0.35, 0.5]
  adaptivethreshold:
    initial_thresh: [0.15, 0.22, 0.30]
    max_gap: [20, 40, 60]
```

## 📈 Evaluation Metrics

### Efficiency Metrics
- **Data Reduction Ratio**: `η = 1 - (D_edge / D_raw)`
- **Bytes Transmitted**: Total serialized data size
- **Energy Proxy**: `bytes_sent + 50 × messages` (transmission cost model)

### Accuracy Metrics
- **RMSE**: Root Mean Square Error between original and reconstructed signals
- **MAE**: Mean Absolute Error
- **Reconstruction method**: Zero-order hold (forward-fill)

## 📁 Project Structure

```
iot-cloud-framework/
├── main.py                          # Main entry point
├── requirement.txt                  # Dependencies
├── README.md                        # This file
├── REAL_DATA_GUIDE.md               # Real data mode guide
├── SYNTHETIC_VS_REAL.md             # Performance comparison
├── test_real_data.py                # Quick comparison test
├── data_generation/
│   ├── config.yaml                  # Experiment configuration
│   ├── synthetic_sensors.py         # Synthetic data generator
│   ├── real_data_loader.py          # Real dataset loader (NEW)
│   └── real_datasets/               # Downloaded real data cache
├── edge_reduction/
│   ├── adaptive_sampling.py         # Adaptive sampling strategy
│   ├── event_driven.py              # Kalman + Page-Hinkley strategy
│   ├── aggregation.py               # Window-based aggregation
│   └── filtering.py                 # Moving average filters
├── serialization/
│   ├── json_handler.py              # JSON serializer
│   └── cbor_handler.py              # CBOR serializer
├── protocols/
│   ├── mqtt_handler.py              # MQTT publisher
│   └── http_handler.py              # HTTP poster
├── cloud/
│   ├── receiver.py                  # Data receiver
│   └── database.py                  # SQLite storage
├── evaluation/
│   ├── accuracy_metrics.py          # RMSE, MAE, reconstruction
│   └── efficiency_metrics.py        # Bytes, reduction ratio, energy
└── results/                         # Generated outputs
    ├── results_vectorized.csv
    ├── summary_table.csv
    ├── summary_table.tex
    └── fig_tradeoff.png
```

## 🔬 Research Applications

This framework is designed for:

1. **Benchmarking Studies**: Compare reduction strategies objectively on both synthetic and real data
2. **Parameter Optimization**: Find optimal configurations for specific scenarios
3. **Trade-off Analysis**: Quantify accuracy-efficiency relationships
4. **Algorithm Development**: Test new reduction strategies against baselines
5. **Production Validation**: Test strategies on real-world IoT sensor data
6. **Publication-Quality Results**: Automated generation of tables and figures

### Available Datasets

- **Synthetic**: Generated time-series with configurable noise patterns
- **Intel Lab**: Real temperature/humidity data from UC Berkeley research lab (54 sensors, 2.3M+ readings)
- See [REAL_DATA_GUIDE.md](REAL_DATA_GUIDE.md) for adding custom datasets

## 📝 Example Results

The framework automatically generates:

1. **Trade-off Plot**: Shows reduction ratio vs. RMSE with error bars
2. **Summary Table**: Mean ± 95% CI for all metrics
3. **Raw Results CSV**: Complete data for custom analysis

Sample output:
```
Method                   Reduction (%)  RMSE      Energy
AdaptiveSampling        78.8 ± 2.1     0.102     221,500
AdaptiveThreshold       95.3 ± 1.5     0.074     52,500
```

## 🛠️ Extending the Framework

### Adding a New Reduction Strategy

1. Create a new file in `edge_reduction/`:
```python
# edge_reduction/my_strategy.py
class MyStrategy:
    def __init__(self, param1=1.0):
        self.param1 = param1
    
    def run(self, data):
        # Process data array
        # Return: (indices, values)
        return sampled_indices, sampled_values
```

2. Import and register in `main.py`:
```python
from edge_reduction.my_strategy import MyStrategy

def build_reducer(name, cfg):
    if name.lower() == "mystrategy":
        return name, MyStrategy(param1=cfg.get("my_param", 1.0))
    # ... existing strategies
```

3. Add configuration in `config.yaml`:
```yaml
experiment:
  reducers: ["MyStrategy"]
  
mystrategy:
  param1: 2.5
```

## 🐛 Troubleshooting

### CBOR Import Error
If you see "CBOR requested but cbor2 not installed":
```bash
pip install cbor2
```

### MQTT/HTTP Not Working
The framework uses simulation mode if `paho-mqtt` or `requests` are not installed:
```bash
pip install paho-mqtt requests
```

### Empty Results
- Check `config.yaml` syntax (valid YAML)
- Ensure `sensors > 0` and `timesteps > 0`
- Verify reducer names match exactly (case-sensitive)

## 📚 Citation

If you use this framework in your research, please cite:

```bibtex
@misc{iot-edge-framework,
  author = {Aman Sharma},
  title = {IoT Edge-Cloud Data Reduction Framework},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/yourusername/iot-cloud-framework}
}
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📧 Contact

For questions or issues:
- Open an issue on GitHub
- Email: Sharma.aman1605@gmail.com

## 🙏 Acknowledgments

This framework was developed as part of IoT edge computing research. Key references:

1. Lou et al., "A Data-Driven Adaptive Sampling Method Based on Edge Computing" (Sensors, 2020)
2. Kalman Filter and Page-Hinkley drift detection implementations
3. Edge computing and IoT data reduction literature

---

**Status**: Active Development | **Version**: 1.0.0 | **Last Updated**: January 2025
