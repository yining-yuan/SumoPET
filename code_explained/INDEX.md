# Complete Codebase Documentation Index

## 📚 Documentation Files (START HERE!)

### 1. **FILE_SUMMARY.md** ⭐ Start here for quick overview
   - High-level description of what each file does
   - Typical experiment workflow
   - 3-layer architecture diagram
   - Output files explanation
   - Perfect for understanding the big picture

### 2. **FUNCTION_REFERENCE.md** ⭐ Detailed reference guide
   - Complete explanation of every function in the codebase
   - "What it does" + "Why it exists" + "How it works"
   - For each function: parameters, returns, examples
   - 100+ functions fully documented
   - Use this when you need to understand a specific function

### 3. **This file (INDEX.md)**
   - Navigation guide for all documentation and code files

---

## 📁 Commented Python Files

All Python files have been annotated with detailed comments explaining what each function does and why. The original code structure is unchanged - comments were only added, not removed.

### Layer 1: Data Collection
- **iot_agent.py** 
  - 1 main class: `IoTAgentModule`
  - 1 main method: `collect_vehicles()`
  - Connects to SUMO simulator
  - Collects vehicle data

### Layer 2: Data Caching  
- **context_broker.py**
  - 1 main class: `ContextBroker`
  - 4 methods: `__init__`, `update_entities`, `query_all_vehicles`, `get_counts`
  - Acts as middleware/cache
  - Provides query interface

### Layer 3: Privacy Engine
- **adaptive_pet_engine.py**
  - 1 main class: `AdaptivePETEngine`
  - 11 methods total
  - Selects privacy mechanism
  - Applies Laplace, Gaussian, k-anonymity, or no privacy
  - Largest and most complex file

### Data Structures
- **data_structures.py**
  - 2 enums: `PrivacyMechanism`, `StakeholderType`
  - 4 dataclasses: `VehicleEntity`, `QueryResult`, `MetricsEvaluation`
  - Defines all data types
  - Provides common language across layers

### Metrics & Evaluation
- **metrics_calculator.py**
  - 1 main class: `MetricsCalculator`
  - 10 methods total
  - Calculates 5 different evaluation metrics
  - Checks actionability and SLA compliance
  - Measures decision quality degradation

### Orchestration
- **experiment_controller.py**
  - 1 main class: `ExperimentController`
  - 6 methods total
  - Coordinates all 3 layers
  - Runs experiment simulation
  - Exports results to CSV

### Execution
- **run_experiment.py**
  - Entry point for running experiments
  - 2 functions: `run_experiment()`, `main()`
  - Starts SUMO simulator
  - Command-line argument handling

### Analysis
- **analyze_results.py**
  - Post-experiment analysis tool
  - 10+ functions
  - Generates Table 1 comparisons
  - Creates visualizations
  - Produces LaTeX for papers

### Testing
- **test_k_anon.py**
  - Standalone debugging script
  - Tests k-anonymity mechanism
  - Not part of main pipeline

---

## 🎯 How to Use This Documentation

### If you want to understand... → Read this:

| Question | Document | Section |
|----------|----------|---------|
| What does this codebase do? | FILE_SUMMARY.md | Top section |
| How do the layers work together? | FILE_SUMMARY.md | Architecture section |
| What's the typical workflow? | FILE_SUMMARY.md | Workflow section |
| What does a specific file do? | FILE_SUMMARY.md | File-by-file |
| How does a specific function work? | FUNCTION_REFERENCE.md | Look up function name |
| What's the data flow? | FILE_SUMMARY.md | 3-Layer System diagram |
| What output files are created? | FILE_SUMMARY.md | Output Files section |
| How to run an experiment? | run_experiment.py | Comments in file |
| How to analyze results? | analyze_results.py | Comments in file |

---

## 🔍 Function Counts by File

| File | Functions | Purpose |
|------|-----------|---------|
| data_structures.py | 4 dataclasses + 2 enums | Define all data types |
| iot_agent.py | 2 | Collect vehicle data |
| context_broker.py | 4 | Cache and query data |
| adaptive_pet_engine.py | 11 | Apply privacy mechanisms |
| metrics_calculator.py | 10 | Calculate evaluation metrics |
| experiment_controller.py | 6 | Orchestrate experiment |
| run_experiment.py | 2 | Execute experiments |
| analyze_results.py | 10+ | Analyze results |
| test_k_anon.py | 0 (test script) | Debug k-anonymity |
| **TOTAL** | **59+ functions** | **Complete privacy experiment system** |

---

## 🏗️ System Architecture

```
EXPERIMENT EXECUTION FLOW:

┌─────────────────────────────────────────────────────┐
│ User runs: python run_experiment.py adaptive ...    │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────↓──────────┐
        │ SUMO Simulator      │ (Traffic simulation)
        └──────────┬──────────┘
                   │
    ┌──────────────┴──────────────┐
    │ Every simulation step:      │
    │                             │
    │ 1. IoT Agent                │ Layer 1: Collect data
    │    collect_vehicles()       │
    │         ↓                   │
    │ 2. Context Broker           │ Layer 2: Cache data
    │    update_entities()        │
    │         ↓                   │
    │ 3. Scheduled queries:       │
    │    - Every 100 steps:       │
    │      Operator query         │
    │    - Every 300 steps:       │
    │      Planner query          │
    │         ↓                   │
    │ 4. PETs Engine              │ Layer 3: Apply privacy
    │    select_mechanism()       │
    │    apply_privacy()          │
    │         ↓                   │
    │ 5. Metrics Calculator       │ Evaluate
    │    calculate_*_accuracy()   │
    │    check_sla()              │
    │         ↓                   │
    │ 6. Experiment Controller    │ Record results
    │    all_queries.append()     │
    │                             │
    └─────────────┬───────────────┘
                  │
        ┌─────────↓─────────┐
        │ After 7200 steps: │
        │                   │
        │ 1. Calculate      │
        │    final metrics  │
        │         ↓         │
        │ 2. Export to      │
        │    CSV files      │
        └─────────┬─────────┘
                  │
        ┌─────────↓────────────────┐
        │ User runs analysis:      │
        │ python analyze_results.py│
        │         ↓                │
        │ Load results from all    │
        │ experimental modes       │
        │         ↓                │
        │ Generate:                │
        │ - Table 1 (comparison)   │
        │ - Charts (visualizations)│
        │ - Summary report         │
        └──────────────────────────┘
```

---

## 📊 5 Evaluation Metrics

The system calculates these 5 metrics for each privacy mode:

| # | Metric | Measures | Section |
|---|--------|----------|---------|
| 1 | Response Accuracy | How close noisy results are to ground truth | 3.1 |
| 2 | Actionable Rate | % of queries good enough to act on | 3.2 |
| 3 | SLA Compliance | % meeting latency and completeness requirements | 3.3 |
| 4 | Temporal Consistency | Do results make physical sense over time? | 3.4 |
| 5 | Decision Quality | Do dispatch decisions still work with privacy? | 3.5 |

---

## 🔐 Privacy Mechanisms

The system can apply 4 different privacy mechanisms:

| Mechanism | Type | How It Works | When Used |
|-----------|------|-------------|-----------|
| **NONE** | Baseline | No privacy applied | Control condition |
| **LAPLACE** | Differential Privacy | Adds Laplace noise to coordinates/counts | Operators (need low latency) |
| **GAUSSIAN** | Differential Privacy | Adds Gaussian noise to coordinates/counts | Regulators (need high accuracy) |
| **K_ANONYMITY** | Anonymization | Groups vehicles, generalizes locations | Planners (need aggregate data) |

---

## 🎓 How to Learn the Codebase

### Quick Learning Path (2 hours):
1. Read FILE_SUMMARY.md (15 min)
2. Read architecture section (15 min)
3. Read 5 metrics explanation (15 min)
4. Look up 2-3 specific functions in FUNCTION_REFERENCE.md (15 min)
5. Skim actual code comments in 1-2 Python files (45 min)

### Deep Learning Path (6 hours):
1. Complete Quick Learning Path above
2. Read FUNCTION_REFERENCE.md completely (1 hour)
3. Read through all Python files, noting comments (3 hours)
4. Trace through a single experiment: what calls what? (1 hour)
5. Try modifying: add a new privacy mechanism or metric (1 hour)

---

## 💡 Key Concepts

### Privacy Budget (epsilon)
- **Lower epsilon** = More privacy, more noise/generalization, less utility
- **Higher epsilon** = Less privacy, less noise, more utility
- **Default values**: low=0.5, medium=1.0, high=2.0

### k-anonymity (k)
- **Lower k** = Less anonymity, more detailed data
- **Higher k** = More privacy, more generalized data
- **Default value**: k=5 (each group has ≥5 similar vehicles)

### Stakeholder Thresholds
- **Operator**: 90% completeness, <500m error, <100ms latency
- **Planner**: 90% accuracy on counts, <500ms latency
- **Regulator**: 98% accuracy, 100% completeness

### Query Frequency
- **Operator**: Queries every 100 steps (frequent, needs low latency)
- **Planner**: Queries every 300 steps (less frequent, can tolerate latency)

---

## 🚨 Important Notes

1. **Code structure unchanged**: Only comments were added; original code left intact
2. **Comments explain WHAT/WHY**: Each function has "What it does" + "Why it exists"
3. **Examples provided**: Many functions have usage examples in comments
4. **Layer architecture**: System is designed in 3 clean layers with clear interfaces
5. **Experimental modes**: Can run 4 different modes to compare privacy approaches

---

## 📞 Quick Reference: Finding What You Need

```python
# Want to understand the flow? 
# → Read: experiment_controller.py step() method

# Want to know how Laplace works?
# → Read: adaptive_pet_engine.py _apply_laplace_locations() method

# Want to know the 5 metrics?
# → Read: metrics_calculator.py (all methods)

# Want to understand k-anonymity?
# → Read: adaptive_pet_engine.py _apply_k_anonymity() method

# Want to know what VehicleEntity contains?
# → Read: data_structures.py VehicleEntity class

# Want to know how results are analyzed?
# → Read: analyze_results.py main() method
```

---

## ✅ What You Now Have

1. ✅ All 9 Python files with detailed inline comments
2. ✅ Complete function reference document (59+ functions documented)
3. ✅ High-level file summary with architecture diagrams
4. ✅ This index/guide for navigation
5. ✅ Original code unchanged (comments only added)

**You're ready to understand, modify, and extend this codebase!**

