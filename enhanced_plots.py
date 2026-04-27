# enhanced_plots.py
"""
Generate enhanced visualization plots with better clarity and multiple views.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import patches
import json

# Set style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
sns.set_palette("husl")

def ci95(arr):
    """Calculate 95% confidence interval."""
    arr = np.asarray(arr, dtype=float)
    m = float(np.mean(arr))
    s = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    half = 1.96 * s / max(1, np.sqrt(len(arr)))
    return m, half

def create_enhanced_tradeoff_plot(df, output_dir="results"):
    """Create multiple enhanced trade-off visualizations."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Filter JSON data for clarity
    df_json = df[df["serializer"] == "JSON"].copy()
    
    # Aggregate by reducer and param_set
    grouped = df_json.groupby(["reducer", "param_set"], as_index=False).agg({
        'reduction_pct': ['mean', lambda x: ci95(x)[1]],
        'rmse_mean': ['mean', lambda x: ci95(x)[1]]
    })
    grouped.columns = ['reducer', 'param_set', 'reduction_mean', 'reduction_ci', 
                       'rmse_mean', 'rmse_ci']
    
    # ===== Plot 1: Scatter with distinct markers (NO LINES) =====
    fig, ax = plt.subplots(figsize=(14, 8))
    
    markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
    colors = plt.cm.Set2(np.linspace(0, 1, 10))
    
    for idx, (reducer_name, sub) in enumerate(grouped.groupby("reducer")):
        sub = sub.sort_values("reduction_mean")
        x = sub["reduction_mean"].to_numpy()
        y = sub["rmse_mean"].to_numpy()
        xerr = sub["reduction_ci"].to_numpy()
        yerr = sub["rmse_ci"].to_numpy()
        
        # Plot points with error bars (NO LINE CONNECTION)
        ax.errorbar(x, y, xerr=xerr, yerr=yerr, 
                   fmt=markers[idx % len(markers)], 
                   color=colors[idx % len(colors)],
                   markersize=10, capsize=5, linewidth=0, elinewidth=2,
                   label=reducer_name, alpha=0.8)
        
        # Add subtle connecting line in background
        ax.plot(x, y, '--', color=colors[idx % len(colors)], 
               alpha=0.2, linewidth=1, zorder=0)
    
    ax.set_xlabel("Data Reduction (%)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Reconstruction Error (RMSE)", fontsize=14, fontweight='bold')
    ax.set_title("Accuracy-Efficiency Trade-off Analysis\n(Each point = different parameter configuration)", 
                fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='upper right', framealpha=0.95)
    
    # Add pareto frontier guidance
    ax.axvline(x=90, color='green', linestyle=':', alpha=0.3, linewidth=2)
    ax.text(90, ax.get_ylim()[0] + 0.01, '90% reduction', 
           rotation=90, va='bottom', ha='right', fontsize=9, alpha=0.5)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "tradeoff_scatter.png"), dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {os.path.join(output_dir, 'tradeoff_scatter.png')}")
    plt.close()
    
    # ===== Plot 2: Separate subplots per reducer =====
    reducers = grouped['reducer'].unique()
    n_reducers = len(reducers)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    for idx, reducer_name in enumerate(reducers):
        if idx >= len(axes):
            break
            
        sub = grouped[grouped['reducer'] == reducer_name].sort_values('reduction_mean')
        
        ax = axes[idx]
        x = sub["reduction_mean"].to_numpy()
        y = sub["rmse_mean"].to_numpy()
        xerr = sub["reduction_ci"].to_numpy()
        yerr = sub["rmse_ci"].to_numpy()
        
        # Create gradient for points
        scatter = ax.scatter(x, y, c=np.arange(len(x)), cmap='viridis', 
                           s=200, alpha=0.7, edgecolors='black', linewidth=2)
        
        # Add error bars
        ax.errorbar(x, y, xerr=xerr, yerr=yerr, fmt='none', 
                   ecolor='gray', capsize=5, alpha=0.5, elinewidth=2)
        
        # Connect with curve
        try:
            from scipy.interpolate import make_interp_spline
            if len(x) > 3:
                x_smooth = np.linspace(x.min(), x.max(), 100)
                spl = make_interp_spline(x, y, k=min(3, len(x)-1))
                y_smooth = spl(x_smooth)
                ax.plot(x_smooth, y_smooth, '--', color='gray', alpha=0.3, linewidth=2)
            else:
                ax.plot(x, y, '--', color='gray', alpha=0.3, linewidth=2)
        except ImportError:
            # scipy not available, use simple line
            ax.plot(x, y, '--', color='gray', alpha=0.3, linewidth=2)
        
        # Annotate best point
        best_idx = np.argmax(x)  # Highest reduction
        ax.annotate('Best', xy=(x[best_idx], y[best_idx]), 
                   xytext=(10, -10), textcoords='offset points',
                   fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        ax.set_xlabel("Reduction (%)", fontsize=12, fontweight='bold')
        ax.set_ylabel("RMSE", fontsize=12, fontweight='bold')
        ax.set_title(f"{reducer_name}", fontsize=14, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.3)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Config Index', fontsize=10)
    
    # Hide extra subplots
    for idx in range(n_reducers, len(axes)):
        axes[idx].axis('off')
    
    plt.suptitle("Strategy-Specific Trade-off Analysis", fontsize=18, fontweight='bold', y=0.995)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "tradeoff_per_strategy.png"), dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {os.path.join(output_dir, 'tradeoff_per_strategy.png')}")
    plt.close()
    
    # ===== Plot 3: Heatmap view =====
    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    
    # Reduction heatmap
    pivot_red = grouped.pivot_table(values='reduction_mean', 
                                    index='reducer', 
                                    columns='param_set',
                                    aggfunc='first')
    sns.heatmap(pivot_red, annot=True, fmt='.1f', cmap='RdYlGn', 
               ax=axes[0], cbar_kws={'label': 'Reduction %'},
               linewidths=1, linecolor='gray')
    axes[0].set_title("Data Reduction Comparison", fontsize=14, fontweight='bold')
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Strategy", fontsize=12, fontweight='bold')
    
    # RMSE heatmap
    pivot_rmse = grouped.pivot_table(values='rmse_mean', 
                                     index='reducer', 
                                     columns='param_set',
                                     aggfunc='first')
    sns.heatmap(pivot_rmse, annot=True, fmt='.4f', cmap='RdYlGn_r', 
               ax=axes[1], cbar_kws={'label': 'RMSE'},
               linewidths=1, linecolor='gray')
    axes[1].set_title("Reconstruction Error Comparison", fontsize=14, fontweight='bold')
    axes[1].set_xlabel("")
    axes[1].set_ylabel("")
    
    plt.suptitle("Heatmap Analysis: Reduction vs Accuracy", fontsize=16, fontweight='bold')
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "tradeoff_heatmap.png"), dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {os.path.join(output_dir, 'tradeoff_heatmap.png')}")
    plt.close()
    
    # ===== Plot 4: Pareto frontier =====
    fig, ax = plt.subplots(figsize=(14, 8))
    
    for idx, (reducer_name, sub) in enumerate(grouped.groupby("reducer")):
        sub = sub.sort_values("reduction_mean")
        x = sub["reduction_mean"].to_numpy()
        y = sub["rmse_mean"].to_numpy()
        
        # Find pareto optimal points (max reduction for each RMSE level)
        pareto_points = []
        for i in range(len(x)):
            is_pareto = True
            for j in range(len(x)):
                if x[j] > x[i] and y[j] <= y[i]:
                    is_pareto = False
                    break
            if is_pareto:
                pareto_points.append(i)
        
        # Plot all points
        ax.scatter(x, y, s=100, alpha=0.3, color=colors[idx % len(colors)], 
                  marker=markers[idx % len(markers)])
        
        # Highlight pareto points
        if pareto_points:
            ax.scatter(x[pareto_points], y[pareto_points], 
                      s=250, alpha=0.9, color=colors[idx % len(colors)],
                      marker=markers[idx % len(markers)], 
                      edgecolors='black', linewidths=2,
                      label=f"{reducer_name} (Pareto)")
    
    ax.set_xlabel("Data Reduction (%)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Reconstruction Error (RMSE)", fontsize=14, fontweight='bold')
    ax.set_title("Pareto Frontier Analysis\n(Large points = Pareto optimal configurations)", 
                fontsize=16, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='upper right', framealpha=0.95)
    
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "tradeoff_pareto.png"), dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {os.path.join(output_dir, 'tradeoff_pareto.png')}")
    plt.close()
    
    print("\n✓ All enhanced plots generated successfully!")

if __name__ == "__main__":
    # Load results
    results_file = "results/results_vectorized.csv"
    if os.path.exists(results_file):
        df = pd.read_csv(results_file)
        print(f"Loaded {len(df)} results from {results_file}")
        create_enhanced_tradeoff_plot(df)
    else:
        print(f"Error: {results_file} not found. Run main.py first.")
