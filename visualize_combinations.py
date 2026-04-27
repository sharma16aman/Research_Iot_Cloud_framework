"""
Visualization for Combination Test Results
Compare protocols, serializers, and strategy chains
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

def plot_protocol_comparison(csv_file, output_dir="results/combinations"):
    """Plot HTTP vs MQTT comparison"""
    df = pd.read_csv(csv_file)
    output_dir = Path(output_dir)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Reduction rate
    axes[0].bar(df['protocol'], df['reduction_rate_mean'], 
                yerr=df['reduction_rate_std'], capsize=5,
                color=['#2ecc71', '#e74c3c'], alpha=0.7)
    axes[0].set_ylabel('Reduction Rate (%)')
    axes[0].set_title('Data Reduction Rate')
    axes[0].set_ylim([0, 100])
    axes[0].grid(axis='y', alpha=0.3)
    
    # RMSE
    axes[1].bar(df['protocol'], df['rmse_mean'], 
                yerr=df['rmse_std'], capsize=5,
                color=['#2ecc71', '#e74c3c'], alpha=0.7)
    axes[1].set_ylabel('RMSE')
    axes[1].set_title('Reconstruction Error')
    axes[1].grid(axis='y', alpha=0.3)
    
    # Serialized size
    axes[2].bar(df['protocol'], df['serialized_size_mean'], 
                yerr=df['serialized_size_std'], capsize=5,
                color=['#2ecc71', '#e74c3c'], alpha=0.7)
    axes[2].set_ylabel('Size (bytes)')
    axes[2].set_title('Serialized Data Size')
    axes[2].grid(axis='y', alpha=0.3)
    
    strategy = df['strategies'].iloc[0]
    serializer = df['serializer'].iloc[0]
    fig.suptitle(f'Protocol Comparison: {strategy} + {serializer}', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_file = output_dir / f"{csv_file.stem}_plot.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

def plot_serializer_comparison(csv_file, output_dir="results/combinations"):
    """Plot JSON vs CBOR comparison"""
    df = pd.read_csv(csv_file)
    output_dir = Path(output_dir)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    colors = ['#3498db', '#9b59b6']
    
    # Reduction rate
    axes[0].bar(df['serializer'], df['reduction_rate_mean'], 
                yerr=df['reduction_rate_std'], capsize=5,
                color=colors, alpha=0.7)
    axes[0].set_ylabel('Reduction Rate (%)')
    axes[0].set_title('Data Reduction Rate')
    axes[0].set_ylim([0, 100])
    axes[0].grid(axis='y', alpha=0.3)
    
    # RMSE
    axes[1].bar(df['serializer'], df['rmse_mean'], 
                yerr=df['rmse_std'], capsize=5,
                color=colors, alpha=0.7)
    axes[1].set_ylabel('RMSE')
    axes[1].set_title('Reconstruction Error')
    axes[1].grid(axis='y', alpha=0.3)
    
    # Serialized size - this is where CBOR shines!
    axes[2].bar(df['serializer'], df['serialized_size_mean'], 
                yerr=df['serialized_size_std'], capsize=5,
                color=colors, alpha=0.7)
    axes[2].set_ylabel('Size (bytes)')
    axes[2].set_title('Serialized Data Size')
    axes[2].grid(axis='y', alpha=0.3)
    
    # Add percentage labels for size difference
    json_size = df[df['serializer'] == 'JSON']['serialized_size_mean'].values[0]
    cbor_size = df[df['serializer'] == 'CBOR']['serialized_size_mean'].values[0]
    size_reduction = 100 * (1 - cbor_size / json_size)
    axes[2].text(0.5, max(json_size, cbor_size) * 0.9, 
                 f'{size_reduction:.1f}% smaller', 
                 ha='center', fontsize=11, fontweight='bold',
                 bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
    
    strategy = df['strategies'].iloc[0]
    protocol = df['protocol'].iloc[0]
    fig.suptitle(f'Serializer Comparison: {strategy} + {protocol}', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_file = output_dir / f"{csv_file.stem}_plot.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

def plot_strategy_chains(csv_file, output_dir="results/combinations"):
    """Plot comparison of different strategy chains"""
    df = pd.read_csv(csv_file)
    output_dir = Path(output_dir)
    
    # Filter out NaN RMSE values
    df_valid = df[~df['rmse_mean'].isna()].copy()
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Color map
    colors = plt.cm.Set3(np.linspace(0, 1, len(df_valid)))
    
    # 1. Reduction rate comparison
    ax = axes[0, 0]
    bars = ax.barh(df_valid['strategies'], df_valid['reduction_rate_mean'],
                   xerr=df_valid['reduction_rate_std'], capsize=5,
                   color=colors, alpha=0.7)
    ax.set_xlabel('Reduction Rate (%)')
    ax.set_title('Data Reduction Rate')
    ax.set_xlim([0, 100])
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (idx, row) in enumerate(df_valid.iterrows()):
        ax.text(row['reduction_rate_mean'] + 2, i, 
                f"{row['reduction_rate_mean']:.1f}%",
                va='center', fontsize=9)
    
    # 2. RMSE comparison
    ax = axes[0, 1]
    ax.barh(df_valid['strategies'], df_valid['rmse_mean'],
            xerr=df_valid['rmse_std'], capsize=5,
            color=colors, alpha=0.7)
    ax.set_xlabel('RMSE')
    ax.set_title('Reconstruction Error')
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (idx, row) in enumerate(df_valid.iterrows()):
        ax.text(row['rmse_mean'] + 0.005, i, 
                f"{row['rmse_mean']:.4f}",
                va='center', fontsize=9)
    
    # 3. Trade-off scatter
    ax = axes[1, 0]
    for i, (idx, row) in enumerate(df_valid.iterrows()):
        ax.scatter(row['rmse_mean'], row['reduction_rate_mean'],
                  s=200, alpha=0.7, color=colors[i], 
                  label=row['strategies'], edgecolors='black', linewidth=1.5)
        ax.annotate(row['strategies'], 
                   (row['rmse_mean'], row['reduction_rate_mean']),
                   xytext=(10, 5), textcoords='offset points',
                   fontsize=8, alpha=0.8)
    ax.set_xlabel('RMSE (lower is better)')
    ax.set_ylabel('Reduction Rate % (higher is better)')
    ax.set_title('Accuracy vs. Efficiency Trade-off')
    ax.grid(alpha=0.3)
    ax.set_xlim(left=0)
    ax.set_ylim([0, 105])
    
    # 4. Serialized size comparison
    ax = axes[1, 1]
    ax.barh(df_valid['strategies'], df_valid['serialized_size_mean'],
            xerr=df_valid['serialized_size_std'], capsize=5,
            color=colors, alpha=0.7)
    ax.set_xlabel('Serialized Size (bytes)')
    ax.set_title('Data Transmission Size')
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (idx, row) in enumerate(df_valid.iterrows()):
        ax.text(row['serialized_size_mean'] + 200, i, 
                f"{row['serialized_size_mean']:.0f}",
                va='center', fontsize=9)
    
    serializer = df['serializer'].iloc[0]
    protocol = df['protocol'].iloc[0]
    fig.suptitle(f'Strategy Chain Comparison: {serializer} + {protocol}', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_file = output_dir / f"{csv_file.stem}_plot.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

def plot_full_combinations(csv_file, output_dir="results/combinations"):
    """Plot all serializer × protocol combinations"""
    df = pd.read_csv(csv_file)
    output_dir = Path(output_dir)
    
    # Create combination labels
    df['combo'] = df['serializer'] + '+' + df['protocol']
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
    
    # 1. Reduction rate
    ax = axes[0, 0]
    x = np.arange(len(df))
    ax.bar(x, df['reduction_rate_mean'], yerr=df['reduction_rate_std'],
           capsize=5, color=colors, alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(df['combo'], rotation=45, ha='right')
    ax.set_ylabel('Reduction Rate (%)')
    ax.set_title('Data Reduction Rate')
    ax.set_ylim([0, 100])
    ax.grid(axis='y', alpha=0.3)
    
    # 2. RMSE
    ax = axes[0, 1]
    ax.bar(x, df['rmse_mean'], yerr=df['rmse_std'],
           capsize=5, color=colors, alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(df['combo'], rotation=45, ha='right')
    ax.set_ylabel('RMSE')
    ax.set_title('Reconstruction Error')
    ax.grid(axis='y', alpha=0.3)
    
    # 3. Serialized size
    ax = axes[1, 0]
    ax.bar(x, df['serialized_size_mean'], yerr=df['serialized_size_std'],
           capsize=5, color=colors, alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(df['combo'], rotation=45, ha='right')
    ax.set_ylabel('Size (bytes)')
    ax.set_title('Serialized Data Size')
    ax.grid(axis='y', alpha=0.3)
    
    # Highlight CBOR advantage
    json_avg = df[df['serializer'] == 'JSON']['serialized_size_mean'].mean()
    cbor_avg = df[df['serializer'] == 'CBOR']['serialized_size_mean'].mean()
    size_reduction = 100 * (1 - cbor_avg / json_avg)
    ax.text(0.5, 0.95, f'CBOR saves {size_reduction:.1f}% on average',
            transform=ax.transAxes, ha='center', va='top',
            fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
    
    # 4. Size reduction percentage
    ax = axes[1, 1]
    ax.bar(x, df['size_reduction_%'], color=colors, alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(df['combo'], rotation=45, ha='right')
    ax.set_ylabel('Size Reduction (%)')
    ax.set_title('Serialization Compression vs Baseline')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim([0, 100])
    
    strategy = df['strategies'].iloc[0]
    fig.suptitle(f'Full Combination Analysis: {strategy}', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    output_file = output_dir / f"{csv_file.stem}_plot.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

def main():
    """Generate all combination visualizations"""
    combinations_dir = Path("results/combinations")
    
    print("\n" + "="*60)
    print("Generating Combination Test Visualizations")
    print("="*60 + "\n")
    
    # Find all CSV files
    csv_files = list(combinations_dir.glob("*.csv"))
    
    for csv_file in csv_files:
        print(f"\nProcessing: {csv_file.name}")
        
        if "protocol_comparison" in csv_file.name:
            plot_protocol_comparison(csv_file)
        elif "serializer_comparison" in csv_file.name:
            plot_serializer_comparison(csv_file)
        elif "strategy_chains" in csv_file.name:
            plot_strategy_chains(csv_file)
        elif "full_combinations" in csv_file.name:
            plot_full_combinations(csv_file)
    
    print("\n" + "="*60)
    print("✓ All visualizations generated successfully!")
    print(f"Results saved to: {combinations_dir}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
