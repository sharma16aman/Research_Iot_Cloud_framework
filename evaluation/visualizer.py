# evaluation/visualizer.py
"""
Enhanced visualization module for IoT edge data reduction experiments.
Generates publication-quality plots for analysis and comparison.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, List, Tuple, Dict


# Set style for publication-quality plots
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
sns.set_palette("husl")


class ExperimentVisualizer:
    """
    Generate various plots for experiment results analysis.
    """
    
    def __init__(self, results_df: pd.DataFrame, output_dir: str = "results"):
        """
        Initialize visualizer with results DataFrame.
        
        Args:
            results_df: DataFrame with experiment results
            output_dir: Directory to save plots
        """
        self.df = results_df
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def plot_tradeoff(self, 
                     serializer: str = "JSON",
                     save_name: str = "tradeoff_plot.png",
                     figsize: Tuple[int, int] = (10, 6),
                     show: bool = False):
        """
        Plot accuracy-efficiency trade-off with error bars.
        
        Args:
            serializer: Which serializer to plot ("JSON" or "CBOR")
            save_name: Output filename
            figsize: Figure size (width, height)
            show: Whether to display plot interactively
        """
        df_filtered = self.df[self.df["serializer"] == serializer]
        
        # Group by reducer and param_set
        grouped = df_filtered.groupby(["reducer", "param_set"], as_index=False).agg({
            'reduction_pct': ['mean', lambda x: self._ci95(x)[1]],
            'rmse_mean': ['mean', lambda x: self._ci95(x)[1]]
        })
        grouped.columns = ['reducer', 'param_set', 'reduction_mean', 'reduction_ci', 
                          'rmse_mean', 'rmse_ci']
        
        plt.figure(figsize=figsize)
        
        for reducer_name, sub in grouped.groupby("reducer"):
            sub = sub.sort_values("reduction_mean")
            x = sub["reduction_mean"].to_numpy()
            y = sub["rmse_mean"].to_numpy()
            xerr = sub["reduction_ci"].to_numpy()
            yerr = sub["rmse_ci"].to_numpy()
            
            plt.errorbar(x, y, xerr=xerr, yerr=yerr, 
                        fmt='o-', capsize=4, linewidth=2, 
                        markersize=8, label=reducer_name, alpha=0.8)
        
        plt.xlabel("Data Reduction (%)", fontsize=12, fontweight='bold')
        plt.ylabel("Reconstruction Error (RMSE)", fontsize=12, fontweight='bold')
        plt.title(f"Accuracy-Efficiency Trade-off ({serializer} Serialization)", 
                 fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.legend(fontsize=10, loc='best')
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, save_name)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_comparison_bars(self,
                            metric: str = "reduction_pct",
                            serializer: str = "JSON",
                            save_name: str = "comparison_bars.png",
                            figsize: Tuple[int, int] = (12, 6),
                            show: bool = False):
        """
        Bar chart comparing reducers on a specific metric.
        
        Args:
            metric: Metric to compare (e.g., 'reduction_pct', 'rmse_mean', 'energy_proxy')
            serializer: Which serializer to plot
            save_name: Output filename
            figsize: Figure size
            show: Whether to display plot
        """
        df_filtered = self.df[self.df["serializer"] == serializer]
        
        grouped = df_filtered.groupby("reducer", as_index=False).agg({
            metric: ['mean', lambda x: self._ci95(x)[1]]
        })
        grouped.columns = ['reducer', 'mean', 'ci']
        grouped = grouped.sort_values('mean', ascending=False)
        
        plt.figure(figsize=figsize)
        x_pos = np.arange(len(grouped))
        
        bars = plt.bar(x_pos, grouped['mean'], yerr=grouped['ci'], 
                      capsize=8, alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Color bars by performance
        colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(bars)))
        for bar, color in zip(bars, colors):
            bar.set_color(color)
        
        plt.xlabel("Reduction Strategy", fontsize=12, fontweight='bold')
        plt.ylabel(metric.replace('_', ' ').title(), fontsize=12, fontweight='bold')
        plt.title(f"Performance Comparison: {metric.replace('_', ' ').title()}", 
                 fontsize=14, fontweight='bold')
        plt.xticks(x_pos, grouped['reducer'], rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, save_name)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_serializer_comparison(self,
                                  save_name: str = "serializer_comparison.png",
                                  figsize: Tuple[int, int] = (12, 5),
                                  show: bool = False):
        """
        Compare JSON vs CBOR serialization efficiency.
        
        Args:
            save_name: Output filename
            figsize: Figure size
            show: Whether to display plot
        """
        if "CBOR" not in self.df["serializer"].unique():
            print("Warning: CBOR data not found in results")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        # Plot 1: Bytes transmitted
        grouped = self.df.groupby(["reducer", "serializer"], as_index=False)['bytes'].mean()
        pivot = grouped.pivot(index='reducer', columns='serializer', values='bytes')
        
        pivot.plot(kind='bar', ax=ax1, alpha=0.7, edgecolor='black', linewidth=1.5)
        ax1.set_ylabel("Average Bytes Transmitted", fontweight='bold')
        ax1.set_xlabel("Reduction Strategy", fontweight='bold')
        ax1.set_title("Serialization: Bytes Transmitted", fontweight='bold')
        ax1.legend(title="Serializer")
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        ax1.tick_params(axis='x', rotation=45)
        
        # Plot 2: Reduction percentage
        grouped = self.df.groupby(["reducer", "serializer"], as_index=False)['reduction_pct'].mean()
        pivot = grouped.pivot(index='reducer', columns='serializer', values='reduction_pct')
        
        pivot.plot(kind='bar', ax=ax2, alpha=0.7, edgecolor='black', linewidth=1.5)
        ax2.set_ylabel("Average Reduction (%)", fontweight='bold')
        ax2.set_xlabel("Reduction Strategy", fontweight='bold')
        ax2.set_title("Serialization: Reduction Percentage", fontweight='bold')
        ax2.legend(title="Serializer")
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, save_name)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_parameter_sensitivity(self,
                                  reducer: str,
                                  param_name: str,
                                  metric: str = "reduction_pct",
                                  serializer: str = "JSON",
                                  save_name: Optional[str] = None,
                                  figsize: Tuple[int, int] = (10, 6),
                                  show: bool = False):
        """
        Plot how a metric varies with a specific parameter.
        
        Args:
            reducer: Name of reducer to analyze
            param_name: Parameter to vary
            metric: Metric to plot on y-axis
            serializer: Which serializer to use
            save_name: Output filename (auto-generated if None)
            figsize: Figure size
            show: Whether to display plot
        """
        if save_name is None:
            save_name = f"sensitivity_{reducer}_{param_name}.png"
        
        df_filtered = self.df[
            (self.df["reducer"] == reducer) & 
            (self.df["serializer"] == serializer)
        ]
        
        # Extract parameter values from param_set JSON
        import json
        param_values = []
        for ps in df_filtered["param_set"]:
            try:
                params = json.loads(ps) if isinstance(ps, str) else (ps or {})
                param_values.append(params.get(param_name, None))
            except:
                param_values.append(None)
        
        df_filtered = df_filtered.copy()
        df_filtered['param_value'] = param_values
        df_filtered = df_filtered[df_filtered['param_value'].notna()]
        
        if len(df_filtered) == 0:
            print(f"No data found for parameter: {param_name}")
            return
        
        grouped = df_filtered.groupby('param_value', as_index=False).agg({
            metric: ['mean', lambda x: self._ci95(x)[1]]
        })
        grouped.columns = ['param_value', 'mean', 'ci']
        grouped = grouped.sort_values('param_value')
        
        plt.figure(figsize=figsize)
        plt.errorbar(grouped['param_value'], grouped['mean'], 
                    yerr=grouped['ci'], fmt='o-', capsize=5, 
                    linewidth=2, markersize=10, alpha=0.8)
        
        plt.xlabel(param_name.replace('_', ' ').title(), fontsize=12, fontweight='bold')
        plt.ylabel(metric.replace('_', ' ').title(), fontsize=12, fontweight='bold')
        plt.title(f"Parameter Sensitivity: {reducer} - {param_name}", 
                 fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, save_name)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_energy_comparison(self,
                              save_name: str = "energy_comparison.png",
                              figsize: Tuple[int, int] = (10, 6),
                              show: bool = False):
        """
        Compare energy proxy across reducers.
        
        Args:
            save_name: Output filename
            figsize: Figure size
            show: Whether to display plot
        """
        grouped = self.df[self.df["serializer"] == "JSON"].groupby("reducer", as_index=False).agg({
            'energy_proxy': ['mean', lambda x: self._ci95(x)[1]]
        })
        grouped.columns = ['reducer', 'mean', 'ci']
        grouped = grouped.sort_values('mean')
        
        plt.figure(figsize=figsize)
        x_pos = np.arange(len(grouped))
        
        colors = ['green' if val < grouped['mean'].median() else 'orange' 
                 for val in grouped['mean']]
        
        plt.barh(x_pos, grouped['mean'], xerr=grouped['ci'], 
                capsize=5, alpha=0.7, edgecolor='black', 
                linewidth=1.5, color=colors)
        
        plt.yticks(x_pos, grouped['reducer'])
        plt.xlabel("Energy Proxy (bytes + 50×messages)", fontsize=12, fontweight='bold')
        plt.title("Energy Consumption Comparison", fontsize=14, fontweight='bold')
        plt.grid(axis='x', alpha=0.3, linestyle='--')
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, save_name)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def plot_heatmap_matrix(self,
                           metric: str = "reduction_pct",
                           serializer: str = "JSON",
                           save_name: str = "heatmap.png",
                           figsize: Tuple[int, int] = (10, 8),
                           show: bool = False):
        """
        Heatmap showing metric values for different reducer/parameter combinations.
        
        Args:
            metric: Metric to display
            serializer: Which serializer to use
            save_name: Output filename
            figsize: Figure size
            show: Whether to display plot
        """
        df_filtered = self.df[self.df["serializer"] == serializer]
        
        # Create pivot table
        pivot = df_filtered.pivot_table(
            index='reducer',
            columns='param_set',
            values=metric,
            aggfunc='mean'
        )
        
        plt.figure(figsize=figsize)
        sns.heatmap(pivot, annot=True, fmt='.2f', cmap='YlGnBu', 
                   cbar_kws={'label': metric.replace('_', ' ').title()},
                   linewidths=0.5, linecolor='gray')
        
        plt.title(f"Heatmap: {metric.replace('_', ' ').title()}", 
                 fontsize=14, fontweight='bold')
        plt.xlabel("Parameter Set", fontweight='bold')
        plt.ylabel("Reducer", fontweight='bold')
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, save_name)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {output_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def generate_all_plots(self, show: bool = False):
        """
        Generate all standard plots.
        
        Args:
            show: Whether to display plots interactively
        """
        print("Generating all visualizations...")
        
        self.plot_tradeoff(serializer="JSON", save_name="fig_tradeoff_json.png", show=show)
        
        if "CBOR" in self.df["serializer"].unique():
            self.plot_tradeoff(serializer="CBOR", save_name="fig_tradeoff_cbor.png", show=show)
            self.plot_serializer_comparison(show=show)
        
        self.plot_comparison_bars(metric="reduction_pct", save_name="fig_reduction_bars.png", show=show)
        self.plot_comparison_bars(metric="rmse_mean", save_name="fig_rmse_bars.png", show=show)
        self.plot_energy_comparison(show=show)
        
        print("All plots generated successfully!")
    
    @staticmethod
    def _ci95(arr):
        """Calculate 95% confidence interval half-width."""
        arr = np.asarray(arr, dtype=float)
        m = float(np.mean(arr))
        s = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
        half = 1.96 * s / max(1, np.sqrt(len(arr)))
        return m, half


# Convenience function for quick visualization
def visualize_results(results_csv: str = "results/results_vectorized.csv",
                     output_dir: str = "results",
                     show: bool = False):
    """
    Quick function to generate all plots from a results CSV.
    
    Args:
        results_csv: Path to results CSV file
        output_dir: Directory to save plots
        show: Whether to display plots interactively
    """
    if not os.path.exists(results_csv):
        print(f"Error: Results file not found: {results_csv}")
        return
    
    df = pd.read_csv(results_csv)
    visualizer = ExperimentVisualizer(df, output_dir)
    visualizer.generate_all_plots(show=show)


if __name__ == "__main__":
    # Example usage
    visualize_results()
