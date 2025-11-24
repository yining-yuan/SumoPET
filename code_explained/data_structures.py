# ==================== DATA STRUCTURES ====================

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ENUM: PrivacyMechanism
# WHAT: Represents the different privacy technologies that can be applied
# WHY: Used to select and track which privacy method was applied to data
class PrivacyMechanism(Enum):
    LAPLACE = "laplace"           # Differential privacy via Laplace noise
    GAUSSIAN = "gaussian"         # Differential privacy via Gaussian noise
    K_ANONYMITY = "k_anonymity"   # Anonymization via k-anonymity generalization
    NONE = "none"                 # No privacy applied (baseline)

# ENUM: StakeholderType
# WHAT: Represents the three types of data stakeholders in the system
# WHY: Different stakeholders have different privacy needs and adaptive engine selects mechanisms accordingly
class StakeholderType(Enum):
    OPERATOR = "operator"       # Ride-sharing dispatch operator (needs fast location queries)
    PLANNER = "planner"         # City traffic planner (analyzes aggregate trends)
    REGULATOR = "regulator"     # Government regulator (ensures compliance/auditing)

# DATACLASS: VehicleEntity
# WHAT: Represents a single vehicle's state at a point in time
# WHY: Encapsulates all vehicle data needed by the system
@dataclass
class VehicleEntity:
    id: str                     # Unique vehicle identifier
    type: str                   # Vehicle type (taxi, bike, bus, car)
    location: Tuple[float, float] # (x, y) coordinates on the map
    edge: str                   # Which road/edge vehicle is on (SUMO concept)
    speed: float                # Current speed in m/s
    timestamp: float            # When this data was collected

# DATACLASS: QueryResult
# WHAT: Records the results of a single privacy-enhanced query
# WHY: Tracks all the evaluation metrics needed to measure privacy-utility tradeoff
@dataclass
class QueryResult:
    step: int                   # Simulation step when query occurred
    stakeholder: StakeholderType # Who made the query
    query_type: str             # Type of query: "location" or "count"
    true_value: any             # Ground truth data before privacy
    reported_value: any         # Privacy-degraded data returned to user
    mechanism: PrivacyMechanism # Which privacy mechanism was applied
    epsilon: float              # Privacy budget (lower = more privacy, less utility)
    latency_ms: float           # Query response time in milliseconds
    completeness: float         # % of data retained (1.0 = all data, 0.8 = 20% suppressed)
    error_meters: float         # Location error in meters (for location queries only)
    count_error: float          # Count difference (for aggregate queries only)

# DATACLASS: MetricsEvaluation
# WHAT: Summary of all 5 evaluation metrics from the paper
# WHY: Final metrics computed at end of experiment to evaluate privacy-utility-latency tradeoffs
@dataclass
class MetricsEvaluation:
    """All 5 metrics from Section 3 of the paper"""
    response_accuracy: float     # Section 3.1 - How accurate are query results?
    actionable_rate: float       # Section 3.2 - What % of queries are good enough to act on?
    sla_compliance: float        # Section 3.3 - What % of queries meet latency/completeness SLAs?
    temporal_consistency: float  # Section 3.4 - Do results stay consistent over time?
    decision_quality: float      # Section 3.5 - Do privacy-degraded decisions still work well?