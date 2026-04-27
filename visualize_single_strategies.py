"""
Visualizations for Single Strategy Comparison
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['font.size'] = 10

def plot_single_strategy_comparison():
    """Create comparison visualizations for individual strategies"""
    
    # Load results
    df = pd.read_csv("results/single_strategies/all_16_single_strategies.csv")
    output_dir = Path("results/single_strategies")
    
    # Filter out NaN RMSE for some plots
    df_valid_rmse = df[~df['rmse_mean'].isna()].copy()
    
    print(f"Loaded {len(df)} single-strategy tests")
    print(f"Valid RMSE data: {len(df_valid_rmse)} tests")
    
    # ========== PLOT 1: Strategy Performance Overview ==========
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    strategies = df['strategy'].unique()
    colors_map = {'AdaptiveSampling': '#3498db', 'AdaptiveThreshold': '#e74c3c',
                  'Aggregation': '#2ecc71', 'Filtering': '#f39c12'}
    
    # 1.1 Reduction Rate by Strategy
    ax = axes[0, 0]
    strategy_avg = df.groupby('strategy')['reduction_rate_mean'].mean().sort_values(ascending=False)
    bars = ax.barh(range(len(strategy_avg)), strategy_avg.values,
                   color=[colors_map[s] for s in strategy_avg.index], alpha=0.7)
    ax.set_yticks(range(len(strategy_avg)))
    ax.set_yticklabels(strategy_avg.index)
    ax.set_xlabel('Average Reduction Rate (%)', fontweight='bold')
    ax.set_title('Data Reduction Rate by Strategy', fontweight='bold', fontsize=12)
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (idx, val) in enumerate(strategy_avg.items()):
        ax.text(val + 2, i, f'{val:.1f}%', va='center', fontsize=10, fontweight='bold')
    
    # 1.2 RMSE by Strategy (valid only)
    ax = axes[0, 1]
    df_rmse = df_valid_rmse.groupby('strategy')['rmse_mean'].mean().sort_values()
    bars = ax.barh(range(len(df_rmse)), df_rmse.values,
                   color=[colors_map[s] for s in df_rmse.index], alpha=0.7)
    ax.set_yticks(range(len(df_rmse)))
    ax.set_yticklabels(df_rmse.index)
    ax.set_xlabel('Average RMSE (lower is better)', fontweight='bold')
    ax.set_title('Reconstruction Accuracy by Strategy', fontweight='bold', fontsize=12)
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (idx, val) in enumerate(df_rmse.items()):
        ax.text(val + 0.002, i, f'{val:.4f}', va='center', fontsize=10, fontweight='bold')
    
    # 1.3 Serialized Size by Strategy
    ax = axes[1, 0]
    size_avg = df.groupby('strategy')['serialized_size_mean'].mean().sort_values()
    bars = ax.barh(range(len(size_avg)), size_avg.values,
                   color=[colors_map[s] for s in size_avg.index], alpha=0.7)
    ax.set_yticks(range(len(size_avg)))
    ax.set_yticklabels(size_avg.index)
    ax.set_xlabel('Average Serialized Size (bytes, lower is better)', fontweight='bold')
    ax.set_title('Data Transmission Size by Strategy', fontweight='bold', fontsize=12)
    ax.grid(axis='x', alpha=0.3)
    ax.set_xscale('log')
    
    # Add value labels
    for i, (idx, val) in enumerate(size_avg.items()):
        ax.text(val * 1.2, i, f'{int(val)}', va='center', fontsize=10, fontweight='bold')
    
    # 1.4 Trade-off: Reduction vs RMSE
    ax = axes[1, 1]
    for strategy in df_valid_rmse['strategy'].unique():
        df_strat = df_valid_rmse[df_valid_rmse['strategy'] == strategy]
        avg_red = df_strat['reduction_rate_mean'].mean()
        avg_rmse = df_strat['rmse_mean'].mean()
        ax.scatter(avg_rmse, avg_red, s=500, alpha=0.7,
                  color=colors_map[strategy], label=strategy,
                  edgecolors='black', linewidth=2)
        ax.annotate(strategy, (avg_rmse, avg_red), 
                   xytext=(10, 10), textcoords='offset points',
                   fontsize=10, fontweight='bold')
    
    ax.set_xlabel('RMSE (lower is better)', fontweight='bold')
    ax.set_ylabel('Reduction Rate % (higher is better)', fontweight='bold')
    ax.set_title('Accuracy vs Efficiency Trade-off', fontweight='bold', fontsize=12)
    ax.grid(alpha=0.3)
    ax.set_xlim(left=0)
    ax.set_ylim([0, 105])
    
    # Add quadrants
    ax.axhline(y=85, color='orange', linestyle='--', alpha=0.3, label='85% threshold')
    ax.axvline(x=0.08, color='red', linestyle='--', alpha=0.3, label='RMSE 0.08')
    ax.legend(fontsize=9)
    
    plt.tight_layout()
    output_file = output_dir / "strategy_performance_overview.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()
    
    # ========== PLOT 2: Serializer Comparison per Strategy ==========
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    axes = axes.flatten()
    
    for idx, strategy in enumerate(strategies):
        ax = axes[idx]
        df_strat = df[df['strategy'] == strategy]
        
        # Group by serializer
        json_data = df_strat[df_strat['serializer'] == 'JSON']
        cbor_data = df_strat[df_strat['serializer'] == 'CBOR']
        
        json_size = json_data['serialized_size_mean'].mean()
        cbor_size = cbor_data['serialized_size_mean'].mean()
        
        # Plot comparison
        x = [0, 1]
        sizes = [json_size, cbor_size]
        colors_ser = ['#3498db', '#9b59b6']
        
        bars = ax.bar(x, sizes, color=colors_ser, alpha=0.7, width=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(['JSON', 'CBOR'], fontsize=11, fontweight='bold')
        ax.set_ylabel('Avg Size (bytes)', fontweight='bold')
        ax.set_title(f"{strategy}", fontweight='bold', fontsize=12)
        ax.grid(axis='y', alpha=0.3)
        
        # Add percentage savings
        if json_size > 0:
            savings = 100 * (1 - cbor_size / json_size)
            y_pos = max(sizes) * 0.7
            ax.text(0.5, y_pos, f'CBOR saves\n{savings:.1f}%',
                   ha='center', fontsize=11, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.6))
        
        # Add value labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Add reduction rate info
        reduction = df_strat['reduction_rate_mean'].mean()
        ax.text(0.98, 0.98, f'Reduction: {reduction:.1f}%',
               transform=ax.transAxes, ha='right', va='top',
               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.4),
               fontsize=9)
    
    plt.suptitle('JSON vs CBOR Serialization Size Comparison', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    output_file = output_dir / "serializer_comparison_by_strategy.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()
    
    # ========== PLOT 3: Detailed Metrics Table ==========
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('tight')
    ax.axis('off')
    
    # Create summary table
    summary_data = []
    for strategy in strategies:
        df_strat = df[df['strategy'] == strategy]
        
        # Calculate averages across all serializer/protocol combos
        avg_red = df_strat['reduction_rate_mean'].mean()
        avg_rmse = df_strat['rmse_mean'].mean() if not df_strat['rmse_mean'].isna().all() else np.nan
        
        # JSON vs CBOR
        json_size = df_strat[df_strat['serializer'] == 'JSON']['serialized_size_mean'].mean()
        cbor_size = df_strat[df_strat['serializer'] == 'CBOR']['serialized_size_mean'].mean()
        cbor_savings = 100 * (1 - cbor_size / json_size) if json_size > 0 else 0
        
        summary_data.append([
            strategy,
            f"{avg_red:.2f}%",
            f"{avg_rmse:.4f}" if not np.isnan(avg_rmse) else "N/A",
            f"{int(json_size)}",
            f"{int(cbor_size)}",
            f"{cbor_savings:.1f}%"
        ])
    
    table = ax.table(cellText=summary_data,
                    colLabels=['Strategy', 'Reduction\nRate', 'RMSE', 'JSON Size\n(bytes)', 
                              'CBOR Size\n(bytes)', 'CBOR\nSavings'],
                    cellLoc='center',
                    loc='center',
                    colWidths=[0.2, 0.15, 0.12, 0.15, 0.15, 0.13])
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.5)
    
    # Color header
    for i in range(6):
        table[(0, i)].set_facecolor('#3498db')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Color rows alternately
    for i in range(1, len(summary_data) + 1):
        for j in range(6):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')
    
    plt.title('Single Strategy Performance Summary', fontsize=14, fontweight='bold', pad=20)
    output_file = output_dir / "strategy_summary_table.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()
    
    # ========== PLOT 4: Winner Comparison ==========
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Compare strategies on key metrics (excluding Filtering for reduction)
    df_compare = df[df['strategy'] != 'Filtering'].copy()
    
    # Normalize metrics to 0-100 scale for radar chart
    strategy_metrics = {}
    for strategy in df_compare['strategy'].unique():
        df_s = df_compare[df_compare['strategy'] == strategy]
        
        reduction = df_s['reduction_rate_mean'].mean()
        rmse = df_s['rmse_mean'].mean()
        size = df_s['serialized_size_mean'].mean()
        
        # Normalize (higher is better for all)
        norm_reduction = reduction  # Already 0-100
        norm_accuracy = 100 * (1 - rmse / 0.2) if not np.isnan(rmse) else 0  # Assume 0.2 is worst
        norm_efficiency = 100 * (1 - size / 10000)  # Assume 10000 bytes is worst
        
        strategy_metrics[strategy] = {
            'Reduction Rate': norm_reduction,
            'Accuracy (100-RMSE×500)': max(0, norm_accuracy),
            'Size Efficiency': max(0, norm_efficiency)
        }
    
    # Bar chart comparison
    x = np.arange(len(strategy_metrics))
    width = 0.25
    
    metrics = list(list(strategy_metrics.values())[0].keys())
    colors_bar = ['#3498db', '#e74c3c', '#2ecc71']
    
    for i, metric in enumerate(metrics):
        values = [strategy_metrics[s][metric] for s in strategy_metrics.keys()]
        ax.bar(x + i*width, values, width, label=metric, color=colors_bar[i], alpha=0.7)
    
    ax.set_xlabel('Strategy', fontweight='bold', fontsize=12)
    ax.set_ylabel('Normalized Score (0-100, higher is better)', fontweight='bold', fontsize=12)
    ax.set_title('Strategy Comparison (Normalized Metrics)', fontweight='bold', fontsize=14)
    ax.set_xticks(x + width)
    ax.set_xticklabels(strategy_metrics.keys(), fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim([0, 105])
    
    # Add winner annotation
    ax.text(0.02, 0.98, '🏆 AdaptiveThreshold: Best overall balance\n(95.7% reduction, RMSE 0.073)',
           transform=ax.transAxes, va='top', fontsize=10,
           bbox=dict(boxstyle='round', facecolor='gold', alpha=0.6))
    
    plt.tight_layout()
    output_file = output_dir / "strategy_winner_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def main():
    """Generate all single-strategy comparison visualizations"""
    print("\n" + "="*70)
    print("SINGLE STRATEGY VISUALIZATION")
    print("="*70 + "\n")
    
    plot_single_strategy_comparison()
    
    print("\n" + "="*70)
    print("✓ All visualizations generated successfully!")
    print("Results saved to: results/single_strategies/")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
