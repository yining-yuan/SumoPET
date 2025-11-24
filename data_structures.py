# ==================== DATA STRUCTURES ====================

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

class PrivacyMechanism(Enum):
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    K_ANONYMITY = "k_anonymity"
    NONE = "none"

class StakeholderType(Enum):
    OPERATOR = "operator"
    PLANNER = "planner"
    REGULATOR = "regulator"

@dataclass
class VehicleEntity:
    id: str
    type: str
    location: Tuple[float, float]
    edge: str
    speed: float
    timestamp: float

@dataclass
class QueryResult:
    step: int
    stakeholder: StakeholderType
    query_type: str
    true_value: any
    reported_value: any
    mechanism: PrivacyMechanism
    epsilon: float
    latency_ms: float
    completeness: float  # % of data retained
    error_meters: float  # For location queries
    count_error: float   # For aggregate queries

@dataclass
class MetricsEvaluation:
    """All 5 metrics from Section 3 of the paper"""
    response_accuracy: float  # Section 3.1
    actionable_rate: float    # Section 3.2
    sla_compliance: float     # Section 3.3
    temporal_consistency: float # Section 3.4
    decision_quality: float   # Section 3.5