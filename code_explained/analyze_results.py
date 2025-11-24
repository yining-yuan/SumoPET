#!/usr/bin/env python3
"""
CORRECTED Analysis Script - Generate Table 1 and Visualizations
================================================================
Analyzes results from all experimental conditions
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse
import sys

# Set style for professional plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

def load_metrics(base_dir: str, modes: list) -> pd.DataFrame:
    # WHAT: Loads the final metrics CSV files from all experimental conditions
    # WHY: Gathers results across baseline, static-laplace, static-kanon, and adaptive modes for comparison
    # PROCESS: For each mode, searches multiple possible file locations, loads metrics_{mode}.csv
    # RETURNS: DataFrame with one row per mode, columns for each of the 5 metrics
    # USED FOR: Comparing metrics across all conditions in Table 1
    
    results = []
    base_path = Path(base_dir)
    
    for mode in modes:
        # Try multiple possible paths
        possible_paths = [
            base_path / f"outputs_{mode}" / f"metrics_{mode}.csv",
            base_path / "outputs" / f"metrics_{mode}.csv",
            base_path / f"metrics_{mode}.csv"
        ]
        
        metrics_file = None
        for path in possible_paths:
            if path.exists():
                metrics_file = path
                break
        
        if metrics_file and metrics_file.exists():
            print(f"Loading {metrics_file}")
            df = pd.read_csv(metrics_file)
            metrics_dict = dict(zip(df['metric'], df['value']))
            metrics_dict['condition'] = mode
            results.append(metrics_dict)
        else:
            print(f"Warning: Metrics file not found for {mode}")
            print(f"  Tried: {[str(p) for p in possible_paths]}")
    
    if not results:
        print("ERROR: No metrics files found!")
        sys.exit(1)
    
    return pd.DataFrame(results)

def load_queries(base_dir: str, modes: list) -> dict:
    # WHAT: Loads detailed per-query result files from all conditions
    # WHY: Enables detailed analysis by stakeholder (operator vs planner) and query type (location vs count)
    # PROCESS: For each mode, loads queries_{mode}.csv containing all query results
    # RETURNS: Dictionary mapping mode → DataFrame of all queries for that mode
    # COLUMNS: step, stakeholder, query_type, mechanism, epsilon, error_meters, count_error, completeness, latency_ms
    # USED FOR: Stakeholder analysis, error distribution plots
    
    query_data = {}
    base_path = Path(base_dir)
    
    for mode in modes:
        possible_paths = [
            base_path / f"outputs_{mode}" / f"queries_{mode}.csv",
            base_path / "outputs" / f"queries_{mode}.csv",
            base_path / f"queries_{mode}.csv"
        ]
        
        queries_file = None
        for path in possible_paths:
            if path.exists():
                queries_file = path
                break
        
        if queries_file and queries_file.exists():
            print(f"Loading {queries_file}")
            query_data[mode] = pd.read_csv(queries_file)
        else:
            print(f"Warning: Queries file not found for {mode}")
    
    return query_data

def generate_table1(metrics_df: pd.DataFrame, output_file: str = "table1_results.csv"):
    # WHAT: Creates Table 1 from paper - summary of all 5 metrics across conditions
    # WHY: Paper's main results table showing how each privacy mode affects the 5 metrics
    # PROCESS:
    #   1. Formats metric values as percentages (e.g., 0.95 → 95.0%)
    #   2. Prints human-readable table to console
    #   3. Saves to CSV file for inclusion in paper/report
    # COLUMNS: Condition, Accuracy (%), Actionable (%), SLA (%), Temporal (%), Decision (%)
    # USED FOR: Quick comparison of privacy modes
    
    print("\n" + "="*80)
    print("TABLE 1: Comparative Evaluation Results (Paper Section 5)")
    print("="*80)
    
    # Format for paper table
    table_data = []
    
    condition_names = {
        'baseline': 'Baseline',
        'static-laplace': 'Static-Lap',
        'static-kanon': 'Static-Kan',
        'adaptive': 'Adaptive'
    }
    
    for _, row in metrics_df.iterrows():
        condition = row['condition']
        display_name = condition_names.get(condition, condition)
        
        table_row = {
            'Condition': display_name,
            'Accuracy (%)': f"{float(row.get('response_accuracy', 0)) * 100:.1f}",
            'Actionable (%)': f"{float(row.get('actionable_rate', 0)) * 100:.1f}",
            'SLA (%)': f"{float(row.get('sla_compliance', 0)) * 100:.1f}",
            'Temporal (%)': f"{float(row.get('temporal_consistency', 0)) * 100:.1f}",
            'Decision (%)': f"{float(row.get('decision_quality', 0)) * 100:.1f}"
        }
        table_data.append(table_row)
    
    df_table = pd.DataFrame(table_data)
    
    # Print to console
    print("\n")
    print(df_table.to_string(index=False))
    print("\n" + "="*80)
    
    # Save to CSV
    df_table.to_csv(output_file, index=False)
    print(f"\nSaved Table 1 to {output_file}")
    
    return df_table

def analyze_by_stakeholder(query_data: dict):
    # WHAT: Breaks down detailed query statistics by stakeholder type (operator vs planner)
    # WHY: Different stakeholders are affected differently by privacy (operators care about latency, planners about accuracy)
    # ANALYSIS:
    #   - Operator: Location error stats, completeness, latency metrics
    #   - Planner: Count error stats, completeness, latency metrics
    # PRINTED: Summary table showing mean/std/max errors for each stakeholder in each condition
    # USED FOR: Understanding which stakeholder is most impacted by each privacy mechanism
    
    print("\n" + "="*80)
    print("STAKEHOLDER-SPECIFIC ANALYSIS")
    print("="*80)
    
    for mode, df in query_data.items():
        if df.empty:
            continue
        
        print(f"\n{mode.upper()}")
        print("-"*50)
        
        # Operator queries (location)
        operator_df = df[df['stakeholder'] == 'operator']
        if not operator_df.empty:
            print(f"\nOperator Queries (n={len(operator_df)}):")
            print(f"  Avg Location Error:  {operator_df['error_meters'].mean():7.1f}m")
            print(f"  Std Location Error:  {operator_df['error_meters'].std():7.1f}m")
            print(f"  Max Location Error:  {operator_df['error_meters'].max():7.1f}m")
            print(f"  Avg Completeness:    {operator_df['completeness'].mean():7.1%}")
            print(f"  Avg Latency:         {operator_df['latency_ms'].mean():7.1f}ms")
        
        # Planner queries (count)
        planner_df = df[df['stakeholder'] == 'planner']
        if not planner_df.empty:
            print(f"\nPlanner Queries (n={len(planner_df)}):")
            print(f"  Avg Count Error:     {planner_df['count_error'].mean():7.1f}")
            print(f"  Std Count Error:     {planner_df['count_error'].std():7.1f}")
            print(f"  Max Count Error:     {planner_df['count_error'].max():7.1f}")
            print(f"  Avg Completeness:    {planner_df['completeness'].mean():7.1%}")
            print(f"  Avg Latency:         {planner_df['latency_ms'].mean():7.1f}ms")

def plot_metrics_comparison(metrics_df: pd.DataFrame, 
                           output_file: str = "metrics_comparison.png"):
    # WHAT: Creates bar chart visualization comparing all 5 metrics across the 4 conditions
    # WHY: Visual comparison makes it easy to see which privacy mode is best overall
    # LAYOUT: 2x3 grid of subplots - one per metric (the 6th subplot is empty)
    # COLORS: Baseline=green, Laplace=blue, k-anonymity=purple, Adaptive=red
    # SCALE: 0-110% on y-axis with value labels on top of bars
    # OUTPUT: PNG file suitable for papers/presentations
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Five Metrics Comparison Across Experimental Conditions', 
                 fontsize=16, fontweight='bold')
    
    metrics = ['response_accuracy', 'actionable_rate', 'sla_compliance', 
               'temporal_consistency', 'decision_quality']
    titles = ['Response Accuracy', 'Actionable Rate', 'SLA Compliance',
              'Temporal Consistency', 'Decision Quality']
    
    colors = {
        'baseline': '#2ecc71',      # Green
        'static-laplace': '#3498db', # Blue
        'static-kanon': '#9b59b6',   # Purple
        'adaptive': '#e74c3c'        # Red
    }
    
    condition_names = {
        'baseline': 'Baseline',
        'static-laplace': 'Static-Lap',
        'static-kanon': 'Static-Kan',
        'adaptive': 'Adaptive'
    }
    
    for idx, (metric, title) in enumerate(zip(metrics, titles)):
        row = idx // 3
        col = idx % 3
        ax = axes[row, col]
        
        conditions = []
        values = []
        bar_colors = []
        
        for _, row_data in metrics_df.iterrows():
            condition = row_data['condition']
            conditions.append(condition_names.get(condition, condition))
            values.append(float(row_data.get(metric, 0)) * 100)
            bar_colors.append(colors.get(condition, 'gray'))
        
        bars = ax.bar(conditions, values, color=bar_colors, alpha=0.8, edgecolor='black')
        ax.set_title(title, fontweight='bold')
        ax.set_ylabel('Percentage (%)')
        ax.set_ylim(0, 110)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + 2,
                   f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Rotate x labels
        ax.set_xticklabels(conditions, rotation=45, ha='right')
    
    # Remove empty subplot
    fig.delaxes(axes[1, 2])
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nSaved metrics comparison to {output_file}")
    plt.close()

def plot_error_distributions(query_data: dict, 
                             output_file: str = "error_distributions.png"):
    """Plot location error distributions"""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Error Distributions by Mechanism', fontsize=14, fontweight='bold')
    
    # Location errors
    ax1 = axes[0]
    location_data = []
    labels = []
    
    for mode, df in query_data.items():
        operator_df = df[df['stakeholder'] == 'operator']
        if not operator_df.empty:
            location_data.append(operator_df['error_meters'])
            labels.append(mode.replace('-', '\n'))
    
    if location_data:
        bp1 = ax1.boxplot(location_data, labels=labels, patch_artist=True)
        ax1.set_title('Location Error Distribution (Operator Queries)')
        ax1.set_ylabel('Error (meters)')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Color boxes
        colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
        for patch, color in zip(bp1['boxes'], colors[:len(bp1['boxes'])]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
    
    # Count errors
    ax2 = axes[1]
    count_data = []
    labels2 = []
    
    for mode, df in query_data.items():
        planner_df = df[df['stakeholder'] == 'planner']
        if not planner_df.empty:
            count_data.append(planner_df['count_error'])
            labels2.append(mode.replace('-', '\n'))
    
    if count_data:
        bp2 = ax2.boxplot(count_data, labels=labels2, patch_artist=True)
        ax2.set_title('Count Error Distribution (Planner Queries)')
        ax2.set_ylabel('Absolute Count Error')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Color boxes
        for patch, color in zip(bp2['boxes'], colors[:len(bp2['boxes'])]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved error distributions to {output_file}")
    plt.close()

def calculate_improvements(metrics_df: pd.DataFrame):
    """Calculate percentage improvements from adaptive approach"""
    
    print("\n" + "="*80)
    print("ADAPTIVE IMPROVEMENTS (Paper Section 5 Key Findings)")
    print("="*80)
    
    # Get adaptive results
    adaptive_row = metrics_df[metrics_df['condition'] == 'adaptive']
    if adaptive_row.empty:
        print("Warning: No adaptive results found")
        return
    
    adaptive = adaptive_row.iloc[0]
    
    # Get static approaches
    static_lap_row = metrics_df[metrics_df['condition'] == 'static-laplace']
    static_kan_row = metrics_df[metrics_df['condition'] == 'static-kanon']
    
    if static_lap_row.empty or static_kan_row.empty:
        print("Warning: Missing static results for comparison")
        return
    
    static_lap = static_lap_row.iloc[0]
    static_kan = static_kan_row.iloc[0]
    
    print("\nKey Metrics Comparison:")
    print("-"*80)
    
    metrics_to_compare = [
        ('response_accuracy', 'Response Accuracy'),
        ('actionable_rate', 'Actionable Rate'),
        ('sla_compliance', 'SLA Compliance'),
        ('decision_quality', 'Decision Quality')
    ]
    
    for metric, name in metrics_to_compare:
        adaptive_val = float(adaptive.get(metric, 0))
        lap_val = float(static_lap.get(metric, 0))
        kan_val = float(static_kan.get(metric, 0))
        
        best_static = max(lap_val, kan_val)
        best_static_name = 'Static-Laplace' if lap_val > kan_val else 'Static-Kanon'
        
        print(f"\n{name}:")
        print(f"  Adaptive:              {adaptive_val:7.1%}")
        print(f"  Static-Laplace:        {lap_val:7.1%}")
        print(f"  Static-Kanon:          {kan_val:7.1%}")
        print(f"  Best Static:           {best_static:7.1%} ({best_static_name})")
        
        if best_static > 0:
            improvement = ((adaptive_val - best_static) / best_static) * 100
            print(f"  Improvement:           {improvement:+6.1f}%")
        else:
            print(f"  Improvement:           N/A (baseline is 0)")

def generate_latex_table(metrics_df: pd.DataFrame, output_file: str = "table1_latex.tex"):
    """Generate LaTeX table for paper"""
    
    condition_names = {
        'baseline': 'Baseline',
        'static-laplace': 'Static-Laplace',
        'static-kanon': 'Static-$k$-Anon',
        'adaptive': 'Adaptive'
    }
    
    with open(output_file, 'w') as f:
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write("\\caption{Comparative Evaluation Results}\n")
        f.write("\\label{tab:results}\n")
        f.write("\\begin{tabular}{lccccc}\n")
        f.write("\\toprule\n")
        f.write("Condition & Accuracy & Actionable & SLA & Temporal & Decision \\\\\n")
        f.write("          & (\\%)     & (\\%)       & (\\%) & (\\%)     & (\\%) \\\\\n")
        f.write("\\midrule\n")
        
        for _, row in metrics_df.iterrows():
            condition = row['condition']
            name = condition_names.get(condition, condition)
            
            acc = float(row.get('response_accuracy', 0)) * 100
            act = float(row.get('actionable_rate', 0)) * 100
            sla = float(row.get('sla_compliance', 0)) * 100
            temp = float(row.get('temporal_consistency', 0)) * 100
            dec = float(row.get('decision_quality', 0)) * 100
            
            f.write(f"{name:20s} & {acc:5.1f} & {act:5.1f} & {sla:5.1f} & {temp:5.1f} & {dec:5.1f} \\\\\n")
        
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
    
    print(f"\nSaved LaTeX table to {output_file}")

def plot_decision_quality_details(query_data: dict, 
                                  output_file: str = "decision_quality_details.png"):
    """Detailed analysis of decision quality"""
    
    # Try to load decision logs
    decision_data = {}
    
    for mode in query_data.keys():
        possible_paths = [
            Path('.') / f"outputs_{mode}" / f"decisions_{mode}.csv",
            Path('.') / "outputs" / f"decisions_{mode}.csv",
            Path('.') / f"decisions_{mode}.csv"
        ]
        
        for path in possible_paths:
            if path.exists():
                decision_data[mode] = pd.read_csv(path)
                break
    
    if not decision_data:
        print("Warning: No decision log files found, skipping decision quality plot")
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x_pos = np.arange(len(decision_data))
    match_rates = []
    labels = []
    
    for mode, df in decision_data.items():
        if 'match' in df.columns:
            match_rate = df['match'].sum() / len(df) * 100
            match_rates.append(match_rate)
            labels.append(mode.replace('-', '\n'))
    
    colors_list = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
    bars = ax.bar(x_pos, match_rates, color=colors_list[:len(match_rates)], 
                  alpha=0.8, edgecolor='black')
    
    ax.set_xlabel('Experimental Condition', fontweight='bold')
    ax.set_ylabel('Decision Quality (%)', fontweight='bold')
    ax.set_title('Decision Support Quality: Correct Nearest-Vehicle Selection', 
                 fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 110)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar, val in zip(bars, match_rates):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 2,
               f'{val:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Saved decision quality details to {output_file}")
    plt.close()

def create_summary_report(metrics_df: pd.DataFrame, query_data: dict, 
                         output_file: str = "analysis_summary.txt"):
    """Create comprehensive text summary"""
    
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("COMPREHENSIVE ANALYSIS SUMMARY\n")
        f.write("="*80 + "\n\n")
        
        f.write("EXPERIMENTAL CONDITIONS:\n")
        f.write("-" * 80 + "\n")
        for condition in metrics_df['condition']:
            f.write(f"  - {condition}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("FIVE METRICS SUMMARY\n")
        f.write("="*80 + "\n\n")
        
        for _, row in metrics_df.iterrows():
            condition = row['condition']
            f.write(f"\n{condition.upper()}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Response Accuracy:      {float(row.get('response_accuracy', 0)):7.1%}\n")
            f.write(f"Actionable Rate:        {float(row.get('actionable_rate', 0)):7.1%}\n")
            f.write(f"SLA Compliance:         {float(row.get('sla_compliance', 0)):7.1%}\n")
            f.write(f"Temporal Consistency:   {float(row.get('temporal_consistency', 0)):7.1%}\n")
            f.write(f"Decision Quality:       {float(row.get('decision_quality', 0)):7.1%}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("QUERY STATISTICS\n")
        f.write("="*80 + "\n\n")
        
        for mode, df in query_data.items():
            f.write(f"\n{mode.upper()}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Queries: {len(df)}\n")
            
            operator_df = df[df['stakeholder'] == 'operator']
            planner_df = df[df['stakeholder'] == 'planner']
            
            f.write(f"  Operator: {len(operator_df)}\n")
            f.write(f"  Planner:  {len(planner_df)}\n")
            
            if not operator_df.empty:
                f.write(f"\nOperator (Location) Statistics:\n")
                f.write(f"  Avg Error:        {operator_df['error_meters'].mean():7.1f}m\n")
                f.write(f"  Std Error:        {operator_df['error_meters'].std():7.1f}m\n")
                f.write(f"  Min Error:        {operator_df['error_meters'].min():7.1f}m\n")
                f.write(f"  Max Error:        {operator_df['error_meters'].max():7.1f}m\n")
                f.write(f"  Avg Completeness: {operator_df['completeness'].mean():7.1%}\n")
                f.write(f"  Avg Latency:      {operator_df['latency_ms'].mean():7.1f}ms\n")
            
            if not planner_df.empty:
                f.write(f"\nPlanner (Count) Statistics:\n")
                f.write(f"  Avg Error:        {planner_df['count_error'].mean():7.1f}\n")
                f.write(f"  Std Error:        {planner_df['count_error'].std():7.1f}\n")
                f.write(f"  Min Error:        {planner_df['count_error'].min():7.1f}\n")
                f.write(f"  Max Error:        {planner_df['count_error'].max():7.1f}\n")
                f.write(f"  Avg Completeness: {planner_df['completeness'].mean():7.1%}\n")
                f.write(f"  Avg Latency:      {planner_df['latency_ms'].mean():7.1f}ms\n")
    
    print(f"\nSaved comprehensive summary to {output_file}")

def main():
    # WHAT: Entry point for experiment results analysis script
    # WHY: Orchestrates loading, analyzing, and visualizing experimental results
    # PROCESS:
    #   1. Parse command-line arguments (base directory, modes, output prefix)
    #   2. Load metrics and query data from CSV files
    #   3. Generate Table 1 (main results)
    #   4. Analyze results by stakeholder
    #   5. Calculate improvement comparisons
    #   6. Generate visualizations (bar charts, error distributions, decision quality)
    #   7. Create LaTeX version of Table 1 for papers
    #   8. Generate comprehensive text summary report
    # OUTPUT: Multiple files (CSVs, PNGs, LaTeX, TXT) with all analyses
    # USAGE: python analyze_results.py --base-dir ./outputs --modes baseline static-laplace static-kanon adaptive
        # description="Analyze experiment results and generate Table 1 from paper",
        # formatter_class=argparse.RawDescriptionHelpFormatter
    # )
    
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Base directory containing outputs (default: current directory)"
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["baseline", "static-laplace", "static-kanon", "adaptive"],
        help="Experimental modes to compare"
    )
    parser.add_argument(
        "--output-prefix",
        default="",
        help="Prefix for output files"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("EXPERIMENT RESULTS ANALYSIS")
    print("="*80)
    print(f"Base directory: {args.base_dir}")
    print(f"Modes: {', '.join(args.modes)}")
    print()
    
    # Load data
    print("Loading metrics and query data...")
    metrics_df = load_metrics(args.base_dir, args.modes)
    query_data = load_queries(args.base_dir, args.modes)
    
    if metrics_df.empty:
        print("ERROR: No metrics data found. Run experiments first.")
        sys.exit(1)
    
    # Generate all analyses
    print("\nGenerating analyses...")
    
    # 1. Main results table
    table1 = generate_table1(metrics_df, f"{args.output_prefix}table1_results.csv")
    
    # 2. Stakeholder-specific analysis
    if query_data:
        analyze_by_stakeholder(query_data)
    
    # 3. Calculate improvements
    calculate_improvements(metrics_df)
    
    # 4. Generate visualizations
    print("\nGenerating visualizations...")
    plot_metrics_comparison(metrics_df, f"{args.output_prefix}metrics_comparison.png")
    
    if query_data:
        plot_error_distributions(query_data, f"{args.output_prefix}error_distributions.png")
        plot_decision_quality_details(query_data, f"{args.output_prefix}decision_quality_details.png")
    
    # 5. LaTeX table
    generate_latex_table(metrics_df, f"{args.output_prefix}table1_latex.tex")
    
    # 6. Summary report
    create_summary_report(metrics_df, query_data, f"{args.output_prefix}analysis_summary.txt")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nGenerated files:")
    print(f"  - {args.output_prefix}table1_results.csv")
    print(f"  - {args.output_prefix}table1_latex.tex")
    print(f"  - {args.output_prefix}metrics_comparison.png")
    print(f"  - {args.output_prefix}error_distributions.png")
    print(f"  - {args.output_prefix}decision_quality_details.png")
    print(f"  - {args.output_prefix}analysis_summary.txt")
    print()

if __name__ == "__main__":
    main()