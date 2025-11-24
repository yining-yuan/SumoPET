# Codebase Summary - What Each File Does

## Quick Overview

This is a **Privacy-Enhancing Technologies (PETs) experimental framework** that measures how different privacy mechanisms impact data utility and operational quality in a ride-sharing system. It uses SUMO traffic simulation to generate realistic vehicle location data, applies privacy mechanisms, and evaluates the privacy-utility tradeoff.

---

## File-by-File Summary

### 📊 **data_structures.py**
**What it does**: Defines all the data types and enums used throughout the system
- **Enums**: PrivacyMechanism (4 types), StakeholderType (3 types)
- **Classes**: VehicleEntity (vehicle state), QueryResult (query outcomes), MetricsEvaluation (final metrics)
- **Why**: Provides common data contracts so all layers speak the same language
- **Example**: A VehicleEntity represents one vehicle at one point in time with position, speed, type

### 🔒 **adaptive_pet_engine.py** (LAYER 3: Privacy Engine)
**What it does**: The core privacy mechanism - selects and applies privacy techniques
- **Main features**:
  - Selects privacy mechanism based on stakeholder type (adaptive mode)
  - Applies 4 different privacy techniques: Laplace noise, Gaussian noise, k-anonymity, or none
  - Manages privacy budgets (epsilon values)
  - Simulates dispatcher decisions for decision quality measurement
- **Key methods**:
  - `select_mechanism()` - Choose privacy method based on stakeholder
  - `apply_privacy()` - Apply chosen privacy method to data
  - `_apply_laplace_locations()` - Add Laplace noise to coordinates
  - `_apply_gaussian_locations()` - Add Gaussian noise to coordinates
  - `_apply_k_anonymity()` - Generalize locations into k-anonymous groups
  - `find_nearest_vehicle()` - Simulate dispatch decision (for evaluation)

### 🗄️ **context_broker.py** (LAYER 2: Data Cache)
**What it does**: Middleware that stores and retrieves vehicle data
- **Acts as**: Database layer between IoT sensors and privacy engine
- **Provides**:
  - `update_entities()` - Store new vehicle data each step
  - `query_all_vehicles()` - Get all vehicles for privacy processing
  - `get_counts()` - Get aggregate statistics (how many taxis, buses, etc.)
- **Why**: Decouples vehicle collection from privacy processing

### 📡 **iot_agent.py** (LAYER 1: Data Collection)
**What it does**: Connects to SUMO traffic simulator and collects vehicle data
- **Main method**: `collect_vehicles()`
  - Queries SUMO for all active vehicles
  - Extracts: ID, type, position, road, speed
  - Returns list of VehicleEntity objects
- **Why**: This is the source of "ground truth" data that privacy mechanisms then degrade

### 📈 **metrics_calculator.py**
**What it does**: Evaluates the privacy system's performance with all 5 metrics from the paper
- **5 Metrics calculated**:
  1. **Response Accuracy** - How accurate are noisy query results vs ground truth?
  2. **Actionable Rate** - What % of queries are good enough to act on?
  3. **SLA Compliance** - What % meet latency and completeness Service Level Agreements?
  4. **Temporal Consistency** - Do results make physical sense over time (no impossible jumps)?
  5. **Decision Quality** - Do dispatch decisions still work with privacy-degraded data?
- **Why**: Quantifies the privacy-utility-latency tradeoff
- **Stakeholder thresholds**:
  - Operator: Needs low latency (<100ms), high completeness (>90%)
  - Planner: Needs high accuracy (>90%), can handle higher latency (<500ms)
  - Regulator: Needs highest accuracy (>98%), complete audit trail

### 🎮 **experiment_controller.py**
**What it does**: Orchestrates the entire experiment - coordinates all 3 layers
- **Manages**:
  - IoT Agent (collects vehicles)
  - Context Broker (stores data)
  - PETs Engine (applies privacy)
  - Metrics Calculator (evaluates results)
- **Main flow** (`step()` method):
  1. Collect vehicle data from SUMO
  2. Process operator queries every 100 steps (location + count)
  3. Process planner queries every 300 steps (location + count)
  4. Track baseline vs privacy-degraded decisions
  5. Record all results
- **Final step** (`calculate_final_metrics()`):
  - Compute all 5 metrics from collected queries
  - Save detailed results and metrics to CSV files

### 🚀 **run_experiment.py**
**What it does**: Command-line entry point that runs one complete experiment
- **Usage**: `python run_experiment.py baseline --cfg trikala.sumocfg`
- **What happens**:
  1. Starts SUMO simulator with specified config
  2. Creates ExperimentController for specified mode
  3. Runs simulation for 7200 steps (full day)
  4. Exports results to CSV files
- **Modes supported**:
  - `baseline` - No privacy (ground truth)
  - `static-laplace` - Always use Laplace noise
  - `static-kanon` - Always use k-anonymity
  - `adaptive` - Choose mechanism based on stakeholder

### 🧪 **test_k_anon.py**
**What it does**: Standalone test script for debugging k-anonymity
- **Purpose**: Verify k-anonymity mechanism works before full experiment
- **Process**:
  1. Starts SUMO simulator
  2. Collects vehicles for 50 steps
  3. Calls k-anonymity with k=2
  4. Prints results
- **Not used** in production experiments

### 📊 **analyze_results.py**
**What it does**: Post-experiment analysis - compares results across all modes
- **Generates**:
  - Table 1 (main results table)
  - Visualizations (bar charts, error distributions)
  - LaTeX version for papers
  - Comprehensive summary report
- **Main functions**:
  - `load_metrics()` - Load final metrics from all modes
  - `load_queries()` - Load detailed query results
  - `generate_table1()` - Create comparison table
  - `analyze_by_stakeholder()` - Break down by operator/planner
  - `plot_metrics_comparison()` - Create bar charts
  - `main()` - Orchestrate all analysis

---

## Typical Experiment Workflow

```
1. USER RUNS EXPERIMENT:
   python run_experiment.py adaptive --cfg trikala.sumocfg
   
2. SYSTEM FLOW:
   SUMO Simulator
        ↓ (every step)
   IoT Agent [collect_vehicles]
        ↓
   Context Broker [update_entities]
        ↓
   Experiment Controller [step]
        ├─ Every 100 steps → Operator Query
        │  ├─ Get ground truth from broker
        │  ├─ Select privacy mechanism (adaptive)
        │  ├─ Apply privacy via PETs Engine
        │  ├─ Calculate error/completeness
        │  └─ Record QueryResult
        │
        └─ Every 300 steps → Planner Query
           (same process)

3. AFTER SIMULATION COMPLETES:
   Export Results [export_results]
        ↓
   queries_adaptive.csv (all query results)
   metrics_adaptive.csv (final 5 metrics)

4. REPEAT FOR ALL MODES:
   python run_experiment.py baseline --cfg ...
   python run_experiment.py static-laplace --cfg ...
   python run_experiment.py static-kanon --cfg ...

5. ANALYZE ALL RESULTS:
   python analyze_results.py --base-dir ./outputs
        ↓
   Table 1 (comparison)
   metrics_comparison.png (bar chart)
   analysis_summary.txt (detailed report)
```

---

## Key Architecture: 3-Layer System

```
┌─────────────────────────────────────────────┐
│ LAYER 1: IoT Agent (iot_agent.py)           │
│ → Collects real vehicle data from SUMO      │
│ → Returns: List[VehicleEntity]              │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│ LAYER 2: Context Broker (context_broker.py) │
│ → Caches vehicle data                       │
│ → Provides query interface                  │
│ → Decouples IoT from Privacy                │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│ LAYER 3: PETs Engine (adaptive_pet_engine.py)
│ → Selects privacy mechanism                 │
│ → Applies privacy (noise/anonymity)         │
│ → Returns: (degraded_data, completeness)    │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│ Evaluation: Metrics Calculator              │
│ (metrics_calculator.py)                     │
│ → Calculates all 5 metrics                  │
│ → Measures privacy-utility tradeoff         │
└─────────────────────────────────────────────┘
```

---

## Output Files Generated

After running experiment for each mode, system creates:

```
outputs/
├── queries_baseline.csv          # All queries for baseline mode
├── metrics_baseline.csv          # Final 5 metrics for baseline
├── queries_static-laplace.csv    # All queries for Laplace mode
├── metrics_static-laplace.csv    # Final metrics for Laplace
├── queries_static-kanon.csv      # All queries for k-anon mode
├── metrics_static-kanon.csv      # Final metrics for k-anon
├── queries_adaptive.csv          # All queries for adaptive mode
├── metrics_adaptive.csv          # Final metrics for adaptive
│
# After running analysis:
├── table1_results.csv            # Table 1 comparison (CSV)
├── table1_latex.tex              # Table 1 for papers (LaTeX)
├── metrics_comparison.png        # Bar chart visualization
├── error_distributions.png       # Error box plots
├── decision_quality_details.png  # Decision quality comparison
└── analysis_summary.txt          # Detailed text report
```

---

## What Each File DOESN'T Do

- **data_structures.py** - Doesn't process anything; just defines types
- **iot_agent.py** - Doesn't store data; just collects and returns it
- **context_broker.py** - Doesn't apply privacy; just caches data
- **adaptive_pet_engine.py** - Doesn't evaluate results; just applies privacy
- **metrics_calculator.py** - Doesn't run experiments; just evaluates results
- **run_experiment.py** - Doesn't analyze results; just runs them
- **analyze_results.py** - Doesn't run experiments; just analyzes them

Each file has a single, focused responsibility!

