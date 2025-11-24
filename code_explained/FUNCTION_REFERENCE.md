# Function Reference - Complete Codebase Explanation

This document explains every function in each Python file, what it does, and why it exists.

---

## 1. data_structures.py
**Purpose**: Defines all data types and enums used throughout the system

### Enums (not functions, but important types):

#### `PrivacyMechanism` (Enum)
- **What**: Represents the 4 privacy technologies that can be applied
- **Why**: Used to track which privacy mechanism was applied to each query
- **Values**: 
  - `LAPLACE` - Differential privacy via Laplace noise
  - `GAUSSIAN` - Differential privacy via Gaussian noise  
  - `K_ANONYMITY` - Privacy via generalization/anonymization
  - `NONE` - No privacy (baseline)

#### `StakeholderType` (Enum)
- **What**: Represents the 3 types of data stakeholders in the system
- **Why**: Different stakeholders have different privacy/latency needs, so engine adapts accordingly
- **Values**:
  - `OPERATOR` - Ride-sharing dispatcher (needs fast location queries)
  - `PLANNER` - City traffic planner (analyzes aggregate trends)
  - `REGULATOR` - Government auditor/regulator (enforces compliance)

### Dataclasses (record structures):

#### `VehicleEntity` (Dataclass)
- **What**: Represents a single vehicle's state at one point in time
- **Why**: Encapsulates all vehicle data needed by the privacy system
- **Fields**:
  - `id` - Unique vehicle identifier
  - `type` - Vehicle type (taxi, bike, bus, car)
  - `location` - (x, y) coordinates on the map
  - `edge` - Road/street the vehicle is on
  - `speed` - Current speed in m/s
  - `timestamp` - When this data was collected

#### `QueryResult` (Dataclass)
- **What**: Records the results of a single privacy-enhanced query
- **Why**: Tracks all evaluation metrics for measuring privacy-utility tradeoffs
- **Fields**:
  - `step` - Simulation step when query occurred
  - `stakeholder` - Who made the query (operator/planner/regulator)
  - `query_type` - "location" or "count"
  - `true_value` - Ground truth before privacy
  - `reported_value` - Privacy-degraded data returned
  - `mechanism` - Which privacy mechanism was applied
  - `epsilon` - Privacy budget (lower = more privacy, less utility)
  - `latency_ms` - Response time in milliseconds
  - `completeness` - % of data retained (1.0 = all data kept)
  - `error_meters` - Location error in meters (location queries only)
  - `count_error` - Count difference (aggregate queries only)

#### `MetricsEvaluation` (Dataclass)
- **What**: Summary of all 5 evaluation metrics from the paper
- **Why**: Final metrics computed at end of experiment to evaluate tradeoffs
- **Fields** (all 0.0-1.0 scale):
  - `response_accuracy` - Section 3.1: How accurate are results?
  - `actionable_rate` - Section 3.2: % of queries good enough to act on?
  - `sla_compliance` - Section 3.3: % meeting latency/completeness SLAs?
  - `temporal_consistency` - Section 3.4: Do results stay consistent over time?
  - `decision_quality` - Section 3.5: Do privacy-degraded decisions still work?

---

## 2. adaptive_pet_engine.py
**Purpose**: Core privacy engine that selects and applies privacy mechanisms

### `AdaptivePETEngine.__init__(mode: str)`
- **What**: Initializes the privacy engine for the experiment
- **Why**: Sets up the privacy mechanisms and thresholds to be used
- **Sets up**:
  - Different epsilon values for DP mechanisms (low=0.5, medium=1.0, high=2.0)
  - Different k values for k-anonymity (3/5/10)
  - Location bounds for clipping noise
  - Empty lists to track queries and dispatch decisions

### `AdaptivePETEngine._detect_bounds(entities: List[VehicleEntity]) → Tuple`
- **What**: Automatically detects geographic boundaries from vehicle data
- **Why**: Laplace mechanism needs valid bounds to clip noisy coordinates within realistic area
- **Algorithm**: Finds min/max x,y coordinates from vehicles, adds 10% padding
- **Returns**: (x_min, x_max, y_min, y_max) bounds with padding
- **Example**: Vehicles at x=100-1200 → returns x=80-1220

### `AdaptivePETEngine.select_mechanism(stakeholder: StakeholderType, query_type: str) → Tuple`
- **What**: Chooses which privacy mechanism to apply based on stakeholder type
- **Why**: Different stakeholders have different privacy/utility/latency needs
- **Logic by mode**:
  - `baseline`: No privacy (PrivacyMechanism.NONE)
  - `static-laplace`: Always Laplace with medium epsilon
  - `static-kanon`: Always k-anonymity with k=5
  - `adaptive`: 
    - Operator → Laplace (low latency needed)
    - Planner → k-anonymity (aggregate data)
    - Regulator → Gaussian (highest accuracy)
- **Returns**: (mechanism_type, epsilon_or_k_value)

### `AdaptivePETEngine.apply_privacy(data, mechanism, epsilon, query_type) → Tuple`
- **What**: Main dispatcher that applies selected privacy mechanism to data
- **Why**: Centralized place to handle all privacy transformations
- **Routes to appropriate function** based on mechanism type
- **Returns**: (privacy-degraded data, completeness ratio)
- **Handles**: Location queries (add noise to coordinates) and count queries (add noise to numbers)

### `AdaptivePETEngine._apply_laplace_locations(entities, epsilon) → Tuple`
- **What**: Adds Laplace differential privacy noise to vehicle location coordinates
- **Why**: Protects individual locations while allowing aggregate analysis
- **Algorithm**: 
  - Adds Laplace noise to X and Y independently
  - Splits epsilon equally between dimensions (epsilon/2 each)
  - Clips results to valid bounds (1200x1200m map)
- **Sensitivity**: 1200m (worst-case: move vehicle across entire map)
- **Returns**: [(vehicle_id, noisy_location), ...], completeness=1.0

### `AdaptivePETEngine._apply_gaussian_locations(entities, epsilon) → Tuple`
- **What**: Adds Gaussian differential privacy noise to vehicle locations
- **Why**: Alternative to Laplace; produces smoother noise distribution, preferred by regulators
- **Algorithm**: Gaussian noise with epsilon/delta parameters
- **Delta**: 1e-5 for approximate differential privacy (ε-δ)
- **Clipping**: Results clipped to bounds to keep coordinates realistic
- **Returns**: [(vehicle_id, noisy_location), ...], completeness=1.0

### `AdaptivePETEngine._apply_laplace_counts(counts: Dict, epsilon) → Dict`
- **What**: Adds Laplace noise to aggregate vehicle counts
- **Why**: When asked "how many vehicles?", must hide individual contributions
- **Sensitivity**: 1 (adding/removing one vehicle changes total by exactly 1)
- **Bounds**: Clipped to [0, 1000] for realistic counts
- **Example**: true_counts={'total': 50} → noisy_counts={'total': 47} (with noise)
- **Returns**: Dictionary with noisy counts

### `AdaptivePETEngine._apply_gaussian_counts(counts: Dict, epsilon) → Dict`
- **What**: Adds Gaussian noise to aggregate counts
- **Why**: Alternative to Laplace with smoother noise
- **Note**: Uses `self.count_sensitivity` which isn't defined (potential bug)
- **Returns**: Dictionary with Gaussian-noisy counts, clamped to ≥0

### `AdaptivePETEngine._apply_k_anonymity(entities: List, k: int) → Tuple`
- **What**: Applies k-anonymity via Mondrian partitioning to vehicle locations
- **Why**: Ensures each vehicle location is indistinguishable from k-1 others (generalization not noise)
- **Algorithm**:
  1. Convert vehicles to DataFrame with separate location_x, location_y columns
  2. Apply Mondrian algorithm (via anonypy library) with quasi-identifiers: type, speed, location_x, location_y
  3. Generalize location ranges to bucket averages
  4. Return anonymized locations
- **Returns**: [(vehicle_id, generalized_location), ...], completeness=1.0
- **Privacy level**: Higher k = more privacy; k-anonymity means each group has ≥k members

### `AdaptivePETEngine.find_nearest_vehicle(request_location, vehicle_locations) → Optional[str]`
- **What**: Finds closest vehicle to a request location using Euclidean distance
- **Why**: Simulates dispatcher's decision task (which vehicle to send to service request)
- **Used for**: Measuring decision quality degradation - if privacy causes wrong vehicle selection, metric decreases
- **Algorithm**: Iterate through vehicles, calculate distance, return vehicle with minimum distance
- **Returns**: Vehicle ID of nearest vehicle, or None if no vehicles
- **Example**: Request at (400, 400), vehicles at [(v1, (410, 410)), (v2, (600, 600))] → returns v1

---

## 3. context_broker.py
**Purpose**: Middleware layer that stores and provides access to vehicle data

### `ContextBroker.__init__()`
- **What**: Initializes the empty entity store
- **Why**: Sets up in-memory database for caching vehicle information
- **Creates**: Empty dictionary `self.entities` to store vehicles by ID

### `ContextBroker.update_entities(entities: List[VehicleEntity])`
- **What**: Updates stored vehicle data with new/current information
- **Why**: Called every simulation step to refresh broker with latest positions and speeds
- **Algorithm**: Iterates through entities and overwrites them in the dictionary
- **Effect**: Broker always has current snapshot of all vehicles

### `ContextBroker.query_all_vehicles() → List[VehicleEntity]`
- **What**: Returns all currently stored vehicles as a list
- **Why**: Used by privacy engine to get ground truth data before applying privacy
- **Used for**: Location queries and decision quality evaluation
- **Returns**: List of all VehicleEntity objects stored

### `ContextBroker.get_counts() → Dict[str, int]`
- **What**: Computes aggregate statistics (vehicle type counts) from stored entities
- **Why**: Used for count queries - stakeholders ask "how many taxis are operating?"
- **Algorithm**: Iterate through vehicles, bin by type using string matching
- **Classification**: Uses keywords in vehicle type string (e.g., "taxi" in vtype)
- **Returns**: {'taxis': 12, 'bikes': 5, 'cars': 28, 'buses': 3, 'total': 48}

---

## 4. iot_agent.py
**Purpose**: Connects to SUMO simulator and collects real-time vehicle data

### `IoTAgentModule.__init__(traci_instance)`
- **What**: Initializes IoT agent with connection to SUMO simulator
- **Why**: Needs reference to SUMO's Traffic Control Interface (traci)
- **Stores**: Reference to traci instance for use in collect_vehicles()

### `IoTAgentModule.collect_vehicles() → List[VehicleEntity]`
- **What**: Gathers all active vehicles from SUMO simulator as VehicleEntity objects
- **Why**: Called every step to get ground truth data for privacy processing
- **Algorithm**:
  1. Query SUMO for list of all vehicle IDs
  2. For each vehicle, fetch: type, position (x,y), current road, speed
  3. Create VehicleEntity with all data
- **Error handling**: Gracefully skips vehicles with missing data, logs warnings
- **Returns**: List of VehicleEntity objects representing all vehicles at current time
- **Example**: 50 vehicles active in simulation → returns list of 50 VehicleEntity objects

---

## 5. metrics_calculator.py
**Purpose**: Calculates all 5 evaluation metrics from paper Section 3

### `MetricsCalculator.__init__()`
- **What**: Initializes thresholds for determining if queries are "actionable" or meet SLAs
- **Why**: Different stakeholders have different requirements
- **Thresholds set**:
  - **Operator**: 90% completeness, <500m error, <100ms response, 95% accuracy
  - **Planner**: 90% accuracy, 80% coverage, <500ms response
  - **Regulator**: 98% accuracy, 100% completeness

### `MetricsCalculator.calculate_response_accuracy(reported, true) → float`
- **Metric**: Section 3.1 - Accuracy = 1 - |reported - true| / |true|
- **What**: Measures how close privacy-degraded result is to ground truth
- **Why**: Quantifies utility loss from privacy mechanism
- **Handles**: Both list inputs (location data) and numeric inputs (counts)
- **Range**: 0.0 (completely wrong) to 1.0 (perfect match)
- **Edge case**: If true=0, returns 1.0 only if reported=0

### `MetricsCalculator.calculate_actionable_rate(queries: List[QueryResult]) → float`
- **Metric**: Section 3.2 - Actionable = queries meeting threshold / total
- **What**: % of queries that provide data good enough for stakeholder to act on
- **Why**: Privacy can degrade data so much that even if returned, it's not useful
- **Example**: Operator query with 600m error (>500m threshold) → not actionable
- **Returns**: 0.0-1.0 (0% to 100% of queries actionable)

### `MetricsCalculator._is_actionable(query: QueryResult) → bool`
- **What**: Helper to check if single query meets actionability thresholds
- **Why**: Different stakeholders have different requirements
- **Logic**:
  - **Operator**: ≥90% completeness AND <500m error
  - **Planner**: ≥90% accuracy on counts
  - **Others**: False (regulator not tested)
- **Returns**: True if query meets thresholds, False otherwise

### `MetricsCalculator.calculate_sla_compliance(queries: List[QueryResult]) → float`
- **Metric**: Section 3.3 - SLA = queries meeting all criteria / total
- **What**: % of queries meeting Service Level Agreement requirements
- **Why**: Need to meet operational requirements (latency) not just accuracy
- **SLAs**:
  - **Operator**: <100ms response AND ≥90% completeness
  - **Planner**: <500ms response AND ≥90% accuracy
- **Returns**: 0.0-1.0 (100% = all SLAs met, reliable system)

### `MetricsCalculator._meets_sla(query: QueryResult) → bool`
- **What**: Helper to check if single query meets SLA requirements
- **Why**: Not enough to be accurate; data must arrive fast enough to be useful
- **Returns**: True if latency and completeness/accuracy meet SLA

### `MetricsCalculator.check_temporal_consistency(time_series: List[Dict]) → float`
- **Metric**: Section 3.4 - Consistency = queries without violations / total
- **What**: Checks if privacy-degraded data makes physical sense over time
- **Why**: Privacy noise could cause impossible situations (teleporting, impossible count jumps)
- **Physical constraints**:
  - Vehicle counts change <20 per 100 seconds (vehicles enter/exit slowly)
  - Individual location moves <50 m/second (vehicle speed limit ~200 km/h)
- **Algorithm**: Compares each query to previous, counts violations, returns (1 - violation_rate)
- **Returns**: 0.0-1.0 (1.0 = perfectly consistent, 0.0 = many violations)

### `MetricsCalculator.measure_decision_quality(decisions_with_pet, ground_truth) → float`
- **Metric**: Section 3.5 - Decision = correct decisions with privacy / total
- **What**: Measures if dispatch decisions are still correct with privacy-degraded data
- **Why**: Privacy impacts utility; wrong vehicle dispatch = system failure
- **Algorithm**:
  1. For each location query: dispatcher picks nearest vehicle (true data)
  2. Also picks nearest vehicle (privacy-degraded data)
  3. Counts when both pick same vehicle
- **Returns**: 0.0-1.0 (1.0 = all decisions correct, 0.0 = no decisions correct)
- **Example**: 100% means privacy doesn't affect dispatch; 50% means half of decisions change

### `MetricsCalculator._same_decision(decision1, decision2) → bool`
- **What**: Helper to compare two dispatch decisions
- **Why**: Used by measure_decision_quality to check if vehicles match
- **Compares**: The `nearest_vehicle` field
- **Returns**: True if both select same vehicle, False otherwise

---

## 6. experiment_controller.py
**Purpose**: Main orchestrator that manages the 3-layer architecture and runs the experiment

### `ExperimentController.__init__(mode: str, export_dir: str)`
- **What**: Initializes experiment controller with all 3 layers and tracking structures
- **Why**: Sets up complete system for running privacy experiment
- **Modes**: baseline, static-laplace, static-kanon, adaptive
- **Initializes**:
  - IoT Agent: Collects vehicle data from SUMO
  - Context Broker: Stores and queries vehicle data
  - PETs Engine: Applies privacy mechanisms
  - Metrics Calculator: Evaluates tradeoffs
- **Tracks**: Lists for queries, time series, baseline vs privacy-degraded decisions

### `ExperimentController.process_query(step, stakeholder, query_type) → QueryResult`
- **What**: Processes single data query from stakeholder, applies privacy, records results
- **Why**: Core method that exercises privacy system; each query generates evaluation data
- **Flow**:
  1. Get ground truth from broker
  2. Select privacy mechanism based on stakeholder/query type
  3. Apply privacy to degrade data
  4. Calculate accuracy/error/completeness metrics
  5. Track decisions for decision quality metric
- **Query types**: "location" (dispatcher needs nearby vehicle) or "count" (planner needs fleet stats)
- **Returns**: QueryResult with all metrics

### `ExperimentController._calculate_location_error(true_locs, reported_locs) → float`
- **What**: Computes average Euclidean distance between true and privacy-degraded locations
- **Why**: Measures utility loss from privacy mechanism - how much does noise distort data?
- **Algorithm**: For each vehicle, calculate distance, average all
- **Metric**: Error in meters
- **Returns**: Mean error (0=perfect, higher=more distortion)
- **Used for**: Actionable rate threshold checking

### `ExperimentController.step(sim_step: int)`
- **What**: Executes one simulation step, collecting data and processing scheduled queries
- **Why**: Called every step; manages when queries are issued
- **Schedule**:
  - **Operator queries**: Every 100 steps (72 total over 7200 steps)
    - Needs both location AND count queries
    - High frequency = frequent, low-latency dispatch decisions
  - **Planner queries**: Every 300 steps (24 total)
    - Also needs location AND count queries
    - Lower frequency = less urgent, can handle higher latency
- **Rationale**: Operators need frequent updates (1 per second), planners can wait (1 per 3 seconds)

### `ExperimentController.calculate_final_metrics() → MetricsEvaluation`
- **What**: Computes all 5 final evaluation metrics from paper (Section 3)
- **Why**: Provides comprehensive evaluation of privacy mechanism's impact on utility/operations
- **Metrics calculated**:
  1. **Response Accuracy**: How close are noisy results to truth?
  2. **Actionable Rate**: % of queries good enough for stakeholder to act on?
  3. **SLA Compliance**: % of queries meeting latency and completeness SLAs?
  4. **Temporal Consistency**: Do query results make physical sense over time?
  5. **Decision Quality**: Do dispatch decisions still work with privacy-degraded locations?
- **Returns**: MetricsEvaluation object with all 5 scores (0.0-1.0 each)

### `ExperimentController.export_results()`
- **What**: Saves all query results and final metrics to CSV files
- **Why**: Enables offline analysis and comparison across privacy modes
- **Creates**:
  1. `queries_{mode}.csv`: Detailed per-query metrics
     - Columns: step, stakeholder, query_type, mechanism, epsilon, error_meters, count_error, completeness, latency_ms
  2. `metrics_{mode}.csv`: Final 5 metrics summary
- **Also prints**: Summary table to stdout showing final metric values
- **Files saved**: In specified export directory

---

## 7. run_experiment.py
**Purpose**: Command-line entry point for running privacy experiments

### `run_experiment(mode, cfg, output_dir, max_steps, seed)`
- **What**: Main experiment runner - starts SUMO simulation and runs privacy experiment
- **Why**: Orchestrates complete experimental pipeline for one privacy mode
- **Flow**:
  1. Set random seeds for reproducibility
  2. Create output directory
  3. Build SUMO launch command with config and output options
  4. Start SUMO traffic simulation
  5. Create ExperimentController to manage queries
  6. Run simulation loop: collect data and process queries each step
  7. Export results (CSV files)
- **Parameters**:
  - `mode`: baseline, static-laplace, static-kanon, or adaptive
  - `cfg`: Path to SUMO config file (.sumocfg)
  - `output_dir`: Where to save CSV results
  - `max_steps`: How many simulation steps (7200 = full experiment)
  - `seed`: Random seed for reproducibility

### `main()`
- **What**: Argument parser and entry point
- **Why**: Allows command-line specification of mode, config, and options
- **Usage**: `python run_experiment.py baseline --cfg path/to/config.sumocfg`
- **Arguments**:
  - `mode` (required): One of [baseline, static-laplace, static-kanon, adaptive]
  - `--cfg` (required): Path to SUMO configuration file
  - `--output-dir`: Where to save results (default: ./outputs)
  - `--max-steps`: Simulation steps (default: 7200)
  - `--seed`: Random seed (default: 42)

---

## 8. test_k_anon.py
**Purpose**: Standalone test script to debug k-anonymity implementation

### Script purpose (no functions, but important):
- **What**: Test script to debug k-anonymity implementation
- **Why**: Isolates k-anonymity testing from main experiment for easier debugging
- **Process**:
  1. Starts SUMO simulator with Trikala city traffic scenario
  2. Runs simulation for 50 steps to collect vehicles
  3. Calls k-anonymity with k=2 on collected vehicles
  4. Prints results to verify anonymization works
- **Used for**: Verifying k-anonymity mechanism works before running full experiment
- **Not part of**: Main experimental pipeline

---

## 9. analyze_results.py
**Purpose**: Analyzes experiment results and generates Table 1 and visualizations

### `load_metrics(base_dir, modes) → pd.DataFrame`
- **What**: Loads final metrics CSV files from all experimental conditions
- **Why**: Gathers results across baseline, static-laplace, static-kanon, and adaptive modes
- **Process**: For each mode, searches multiple possible paths, loads metrics_{mode}.csv
- **Returns**: DataFrame with one row per mode, columns for each 5 metrics
- **Used for**: Comparing metrics in Table 1

### `load_queries(base_dir, modes) → dict`
- **What**: Loads detailed per-query result files from all conditions
- **Why**: Enables detailed analysis by stakeholder and query type
- **Process**: Loads queries_{mode}.csv for each mode
- **Returns**: Dictionary mapping mode → DataFrame of all queries
- **Columns**: step, stakeholder, query_type, mechanism, epsilon, error_meters, count_error, completeness, latency_ms
- **Used for**: Stakeholder analysis, error distribution plots

### `generate_table1(metrics_df, output_file) → pd.DataFrame`
- **What**: Creates Table 1 from paper - summary of all 5 metrics
- **Why**: Paper's main results table comparing privacy modes
- **Process**:
  1. Format metric values as percentages
  2. Print human-readable table to console
  3. Save to CSV
- **Columns**: Condition, Accuracy (%), Actionable (%), SLA (%), Temporal (%), Decision (%)
- **Used for**: Quick comparison of privacy modes

### `analyze_by_stakeholder(query_data)`
- **What**: Breaks down detailed statistics by stakeholder type
- **Why**: Different stakeholders affected differently by privacy
- **Analysis**:
  - **Operator**: Location error stats, completeness, latency
  - **Planner**: Count error stats, completeness, latency
- **Output**: Summary tables printed to console
- **Used for**: Understanding which stakeholder most impacted

### `plot_metrics_comparison(metrics_df, output_file)`
- **What**: Creates bar chart comparing all 5 metrics across 4 conditions
- **Why**: Visual comparison shows which privacy mode best overall
- **Layout**: 2x3 grid, one subplot per metric
- **Colors**: Baseline=green, Laplace=blue, k-anonymity=purple, Adaptive=red
- **Scale**: 0-110% with value labels
- **Output**: PNG file for papers/presentations

### `main()`
- **What**: Entry point for results analysis script
- **Why**: Orchestrates loading, analyzing, and visualizing results
- **Process**:
  1. Parse command-line arguments
  2. Load metrics and query data
  3. Generate Table 1
  4. Analyze by stakeholder
  5. Calculate improvements
  6. Generate visualizations (bar charts, error distributions, decision quality)
  7. Create LaTeX version of Table 1
  8. Generate comprehensive text summary
- **Output**: Multiple files (CSVs, PNGs, LaTeX, TXT)
- **Usage**: `python analyze_results.py --base-dir ./outputs`

---

## Summary of Architecture

The system uses a **3-layer architecture**:

### Layer 1: IoT Agent (`iot_agent.py`)
- Collects vehicle data from SUMO simulator
- Returns list of VehicleEntity objects

### Layer 2: Context Broker (`context_broker.py`)
- Middleware that caches vehicle data
- Provides query methods to access data
- Decouples IoT from privacy layer

### Layer 3: PETs Engine (`adaptive_pet_engine.py`)
- Applies privacy mechanisms to data
- Selects mechanism based on stakeholder
- Returns privacy-degraded data with completeness metric

### Orchestration: Experiment Controller (`experiment_controller.py`)
- Manages all layers
- Processes queries on schedule
- Calculates metrics
- Exports results

### Analysis: Results Analyzer (`analyze_results.py`)
- Loads experiment results
- Generates comparisons and visualizations
- Creates paper-ready tables

