"""
Comprehensive Visualization for All 24 Combinations
Creates detailed comparison plots
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['font.size'] = 9

def plot_comprehensive_comparison():
    """Create comprehensive visualization of all 24 combinations"""
    
    # Load results
    df = pd.read_csv("results/comprehensive/all_24_combinations.csv")
    output_dir = Path("results/comprehensive")
    
    # Filter out NaN RMSE for some plots
    df_valid_rmse = df[~df['rmse_mean'].isna()].copy()
    
    print(f"Loaded {len(df)} combinations")
    print(f"Valid RMSE data: {len(df_valid_rmse)} combinations")
    
    # ========== PLOT 1: Overview - All 24 Combinations ==========
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Create combination labels
    df['combo_label'] = df.apply(
        lambda row: f"{row['strategy_chain'][:15]}...\n{row['serializer']}+{row['protocol']}", 
        axis=1
    )
    
    # Color by strategy chain
    strategy_chains = df['strategy_chain'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(strategy_chains)))
    color_map = {chain: colors[i] for i, chain in enumerate(strategy_chains)}
    df['color'] = df['strategy_chain'].map(color_map)
    
    # 1.1 Reduction Rate
    ax = axes[0, 0]
    x = np.arange(len(df))
    bars = ax.bar(x, df['reduction_rate_mean'], 
                  yerr=df['reduction_rate_std'],
                  color=[df.loc[i, 'color'] for i in df.index],
                  alpha=0.7, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"#{i+1}" for i in range(len(df))], fontsize=7)
    ax.set_ylabel('Reduction Rate (%)', fontweight='bold')
    ax.set_title('Data Reduction Rate (All 24 Combinations)', fontweight='bold')
    ax.set_ylim([0, 105])
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=90, color='red', linestyle='--', alpha=0.3, label='90% threshold')
    ax.legend(fontsize=8)
    
    # 1.2 RMSE (only valid values)
    ax = axes[0, 1]
    valid_indices = df_valid_rmse.index
    x_valid = np.arange(len(df_valid_rmse))
    ax.bar(x_valid, df_valid_rmse['rmse_mean'],
           yerr=df_valid_rmse['rmse_std'],
           color=[df.loc[i, 'color'] for i in valid_indices],
           alpha=0.7, capsize=2)
    ax.set_xticks(x_valid)
    ax.set_xticklabels([f"#{i+1}" for i in valid_indices], fontsize=7)
    ax.set_ylabel('RMSE', fontweight='bold')
    ax.set_title('Reconstruction Error (Valid RMSE Only)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0.1, color='orange', linestyle='--', alpha=0.3, label='0.1 threshold')
    ax.legend(fontsize=8)
    
    # 1.3 Serialized Size
    ax = axes[1, 0]
    ax.bar(x, df['serialized_size_mean'],
           yerr=df['serialized_size_std'],
           color=[df.loc[i, 'color'] for i in df.index],
           alpha=0.7, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"#{i+1}" for i in range(len(df))], fontsize=7)
    ax.set_ylabel('Serialized Size (bytes)', fontweight='bold')
    ax.set_title('Data Transmission Size (All 24 Combinations)', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.set_yscale('log')
    
    # 1.4 Trade-off Scatter (valid RMSE only)
    ax = axes[1, 1]
    for strategy_chain in strategy_chains:
        df_chain = df_valid_rmse[df_valid_rmse['strategy_chain'] == strategy_chain]
        if len(df_chain) > 0:
            ax.scatter(df_chain['rmse_mean'], df_chain['reduction_rate_mean'],
                      s=150, alpha=0.7, color=color_map[strategy_chain],
                      label=strategy_chain, edgecolors='black', linewidth=1)
    ax.set_xlabel('RMSE (lower is better)', fontweight='bold')
    ax.set_ylabel('Reduction Rate % (higher is better)', fontweight='bold')
    ax.set_title('Accuracy vs Efficiency Trade-off', fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc='lower right')
    ax.set_ylim([70, 105])
    
    plt.tight_layout()
    output_file = output_dir / "overview_all_24_combinations.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()
    
    # ========== PLOT 2: Strategy Chain Comparison ==========
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    for idx, strategy_chain in enumerate(strategy_chains):
        ax = axes[idx]
        df_chain = df[df['strategy_chain'] == strategy_chain]
        
        # Create combination labels for this chain
        df_chain['ser_proto'] = df_chain['serializer'] + '+' + df_chain['protocol']
        
        # Plot grouped bars
        x = np.arange(len(df_chain))
        width = 0.35
        
        # Reduction rate on left y-axis
        ax_twin = ax.twinx()
        bars1 = ax.bar(x - width/2, df_chain['reduction_rate_mean'], width,
                       label='Reduction %', color='skyblue', alpha=0.7)
        
        # Serialized size on right y-axis
        bars2 = ax_twin.bar(x + width/2, df_chain['serialized_size_mean'], width,
                           label='Size (bytes)', color='salmon', alpha=0.7)
        
        ax.set_xlabel('Serializer + Protocol')
        ax.set_ylabel('Reduction Rate (%)', color='skyblue', fontweight='bold')
        ax_twin.set_ylabel('Size (bytes)', color='salmon', fontweight='bold')
        ax.set_title(f"{strategy_chain}", fontweight='bold', fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(df_chain['ser_proto'], rotation=45, ha='right', fontsize=8)
        ax.tick_params(axis='y', labelcolor='skyblue')
        ax_twin.tick_params(axis='y', labelcolor='salmon')
        ax.set_ylim([0, 105])
        ax.grid(axis='y', alpha=0.3)
        
        # Add RMSE text if available
        if strategy_chain in df_valid_rmse['strategy_chain'].values:
            rmse_val = df_valid_rmse[df_valid_rmse['strategy_chain'] == strategy_chain]['rmse_mean'].iloc[0]
            ax.text(0.5, 0.95, f'RMSE: {rmse_val:.4f}',
                   transform=ax.transAxes, ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3),
                   fontsize=8)
    
    plt.tight_layout()
    output_file = output_dir / "strategy_chain_comparison.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()
    
    # ========== PLOT 3: Serializer Comparison (JSON vs CBOR) ==========
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    for idx, strategy_chain in enumerate(strategy_chains):
        row = idx // 3
        col = idx % 3
        ax = axes[row, col]
        
        df_chain = df[df['strategy_chain'] == strategy_chain]
        
        # Group by serializer
        json_data = df_chain[df_chain['serializer'] == 'JSON']
        cbor_data = df_chain[df_chain['serializer'] == 'CBOR']
        
        json_size = json_data['serialized_size_mean'].mean()
        cbor_size = cbor_data['serialized_size_mean'].mean()
        
        # Plot comparison
        x = [0, 1]
        sizes = [json_size, cbor_size]
        colors_ser = ['#3498db', '#9b59b6']
        
        bars = ax.bar(x, sizes, color=colors_ser, alpha=0.7, width=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(['JSON', 'CBOR'])
        ax.set_ylabel('Avg Size (bytes)', fontweight='bold')
        ax.set_title(f"{strategy_chain[:25]}", fontweight='bold', fontsize=9)
        ax.grid(axis='y', alpha=0.3)
        
        # Add percentage savings
        if json_size > 0:
            savings = 100 * (1 - cbor_size / json_size)
            ax.text(0.5, max(sizes) * 0.8, f'{savings:.1f}% smaller',
                   ha='center', fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
        
        # Add value labels
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=8)
    
    plt.suptitle('Serializer Comparison: JSON vs CBOR (Average Size)', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    output_file = output_dir / "serializer_comparison_json_vs_cbor.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()
    
    # ========== PLOT 4: Protocol Comparison (HTTP vs MQTT) ==========
    print("\nNote: Protocol (HTTP vs MQTT) shows identical performance for same strategy+serializer")
    print("      This is expected as protocol choice doesn't affect data reduction or accuracy.")
    
    # ========== PLOT 5: Best Configurations Ranking ==========
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    # Rank by reduction rate
    ax = axes[0]
    df_sorted = df.sort_values('reduction_rate_mean', ascending=True).tail(15)
    y = np.arange(len(df_sorted))
    
    bars = ax.barh(y, df_sorted['reduction_rate_mean'],
                   xerr=df_sorted['reduction_rate_std'],
                   color=[color_map[chain] for chain in df_sorted['strategy_chain']],
                   alpha=0.7, capsize=3)
    ax.set_yticks(y)
    labels = [f"#{int(df_sorted.iloc[i].name)+1}: {df_sorted.iloc[i]['strategy_chain'][:20]}\n{df_sorted.iloc[i]['serializer']}+{df_sorted.iloc[i]['protocol']}" 
              for i in range(len(df_sorted))]
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Reduction Rate (%)', fontweight='bold')
    ax.set_title('Top 15 by Data Reduction Rate', fontweight='bold', fontsize=12)
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        ax.text(row['reduction_rate_mean'] + 1, i, f"{row['reduction_rate_mean']:.2f}%",
               va='center', fontsize=7)
    
    # Rank by smallest size (best efficiency)
    ax = axes[1]
    df_sorted_size = df.sort_values('serialized_size_mean', ascending=True).head(15)
    y = np.arange(len(df_sorted_size))
    
    bars = ax.barh(y, df_sorted_size['serialized_size_mean'],
                   xerr=df_sorted_size['serialized_size_std'],
                   color=[color_map[chain] for chain in df_sorted_size['strategy_chain']],
                   alpha=0.7, capsize=3)
    ax.set_yticks(y)
    labels = [f"#{int(df_sorted_size.iloc[i].name)+1}: {df_sorted_size.iloc[i]['strategy_chain'][:20]}\n{df_sorted_size.iloc[i]['serializer']}+{df_sorted_size.iloc[i]['protocol']}" 
              for i in range(len(df_sorted_size))]
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Serialized Size (bytes)', fontweight='bold')
    ax.set_title('Top 15 by Smallest Transmission Size', fontweight='bold', fontsize=12)
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (idx, row) in enumerate(df_sorted_size.iterrows()):
        ax.text(row['serialized_size_mean'] + 50, i, f"{int(row['serialized_size_mean'])}",
               va='center', fontsize=7)
    
    plt.tight_layout()
    output_file = output_dir / "best_configurations_ranking.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()
    
    # ========== PLOT 6: Summary Heatmap ==========
    fig, axes = plt.subplots(1, 2, figsize=(18, 10))
    
    # Create pivot tables for heatmap
    df_pivot_red = df.pivot_table(
        values='reduction_rate_mean',
        index='strategy_chain',
        columns=['serializer', 'protocol']
    )
    
    df_pivot_size = df.pivot_table(
        values='serialized_size_mean',
        index='strategy_chain',
        columns=['serializer', 'protocol']
    )
    
    # Reduction rate heatmap
    ax = axes[0]
    sns.heatmap(df_pivot_red, annot=True, fmt='.1f', cmap='RdYlGn',
                ax=ax, cbar_kws={'label': 'Reduction %'},
                vmin=70, vmax=100)
    ax.set_title('Reduction Rate (%) Heatmap', fontweight='bold', fontsize=12)
    ax.set_xlabel('Serializer + Protocol', fontweight='bold')
    ax.set_ylabel('Strategy Chain', fontweight='bold')
    
    # Size heatmap (reversed colormap - lower is better)
    ax = axes[1]
    sns.heatmap(df_pivot_size, annot=True, fmt='.0f', cmap='RdYlGn_r',
                ax=ax, cbar_kws={'label': 'Size (bytes)'},
                norm=plt.matplotlib.colors.LogNorm())
    ax.set_title('Serialized Size (bytes) Heatmap', fontweight='bold', fontsize=12)
    ax.set_xlabel('Serializer + Protocol', fontweight='bold')
    ax.set_ylabel('Strategy Chain', fontweight='bold')
    
    plt.tight_layout()
    output_file = output_dir / "summary_heatmap.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()


def main():
    """Generate all comprehensive visualizations"""
    print("\n" + "="*70)
    print("COMPREHENSIVE VISUALIZATION - 24 Combinations")
    print("="*70 + "\n")
    
    plot_comprehensive_comparison()
    
    print("\n" + "="*70)
    print("✓ All visualizations generated successfully!")
    print("Results saved to: results/comprehensive/")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
