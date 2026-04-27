"""
Test Main.py with Real Data
Quick test to verify real data mode works
"""

import yaml
import sys
import logging

logging.basicConfig(level=logging.INFO)

# Load config
with open("data_generation/config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

# Test with synthetic data first
print("\n" + "="*70)
print("TEST 1: SYNTHETIC DATA MODE (baseline)")
print("="*70)
cfg["experiment"]["data_mode"] = "synthetic"
cfg["experiment"]["runs"] = 2  # Quick test
cfg["experiment"]["sensors"] = 3
cfg["experiment"]["timesteps"] = 100
cfg["experiment"]["reducers"] = ["AdaptiveThreshold"]

from main import run_vectorized
df_synthetic = run_vectorized(cfg)
print(f"\n[OK] Synthetic mode: {len(df_synthetic)} results")

# Test with real data
print("\n" + "="*70)
print("TEST 2: REAL DATA MODE (Intel Lab)")
print("="*70)
cfg["experiment"]["data_mode"] = "real"
cfg["experiment"]["real_dataset"] = "intel_lab"

df_real = run_vectorized(cfg)
print(f"\n[OK] Real mode: {len(df_real)} results")

# Compare
print("\n" + "="*70)
print("COMPARISON")
print("="*70)
print(f"\nSynthetic Data:")
print(f"  Reduction: {df_synthetic['reduction_pct'].mean():.2f}%")
if 'rmse' in df_synthetic.columns:
    rmse_data = df_synthetic[df_synthetic['rmse'].notna()]
    if len(rmse_data) > 0:
        print(f"  RMSE (where applicable): {rmse_data['rmse'].mean():.4f}")

print(f"\nReal Data (Intel Lab):")
print(f"  Reduction: {df_real['reduction_pct'].mean():.2f}%")
if 'rmse' in df_real.columns:
    rmse_data = df_real[df_real['rmse'].notna()]
    if len(rmse_data) > 0:
        print(f"  RMSE (where applicable): {rmse_data['rmse'].mean():.4f}")

print("\n[OK] Both modes working successfully!")
