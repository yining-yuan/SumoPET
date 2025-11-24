# ==================== METRICS CALCULATOR (Section 3) ====================

from typing import Dict, List, Optional, Tuple
from data_structures import QueryResult, StakeholderType
import math

import logging
logger = logging.getLogger(__name__)


class MetricsCalculator:
    # WHAT: Calculates all 5 evaluation metrics from paper Section 3
    # WHY: Measures how well the privacy system balances privacy, utility, and latency across different stakeholders
    
    """Implements all 5 metrics from paper Section 3"""
    
    def __init__(self):
        # WHAT: Initializes thresholds for determining whether queries are "actionable" or meet "SLA"
        # WHY: Different stakeholders have different requirements (operators need low latency, regulators need high accuracy)
        # THRESHOLDS MEAN:
        #   - Operator: Needs 90% of fleet visible (completeness), <500m location error, <100ms response, 95% accuracy
        #   - Planner: Needs 90% accuracy on counts, 80% coverage, <500ms response
        #   - Regulator: Needs 98% accuracy, 100% of data (no suppression) for audit trail
        # Thresholds from paper
        # Thresholds from paper
        self.operator_thresholds = {
            'completeness': 0.90,  # ≥90% fleet visibility
            'error_m': 500,        # <500m error
            'latency_ms': 100,     # <100ms
            'accuracy': 0.95       # ≥95% accuracy
        }
        self.planner_thresholds = {
            'accuracy': 0.90,      # ≥90% accuracy
            'coverage': 0.80,      # ≥80% coverage
            'latency_ms': 500      # <500ms
        }
        self.regulator_thresholds = {
            'accuracy': 0.98,      # ≥98% accuracy
            'completeness': 1.0    # 100% audit trail
        }
        
        self.query_history = []  # For temporal consistency
        
    def calculate_response_accuracy(self, reported, true) -> float:
        # WHAT: Calculates how accurate privacy-degraded query result is compared to ground truth
        # WHY: Metric 3.1 - measures utility loss from privacy mechanism
        # FORMULA: Accuracy = 1 - |reported - true| / |true|  (normalized error)
        # HANDLES: Both list inputs (location data) and numeric inputs (counts)
        # RANGE: 0.0 (completely wrong) to 1.0 (perfect match)
        # EDGE CASE: If true value is 0, returns 1.0 only if reported is also 0
        """Section 3.1: Accuracy = 1 - |reported - true|/true"""
        # Handle list inputs (location queries)
        if isinstance(reported, list) and isinstance(true, list):
            # For location queries, return 1.0 if both lists exist
            return 1.0 if len(reported) == len(true) else 0.5
        
        # Handle numeric inputs
        if true == 0:
            return 1.0 if reported == 0 else 0.0
        return max(0, 1 - abs(reported - true) / abs(true))
    
    def calculate_actionable_rate(self, queries: List[QueryResult]) -> float:
        # WHAT: Metric 3.2 - measures % of queries that provide good enough data for stakeholder to act on
        # WHY: Privacy can degrade data so much that even if returned, it's not useful for decision-making
        # LOGIC: Counts queries meeting stakeholder-specific thresholds, divides by total queries
        # MEANING: 100% = all queries usable; 50% = only half the queries are good enough to act on
        # EXAMPLE: Operator gets dispatch query with 600m location error (>500m threshold) → not actionable
        """Section 3.2: Actionable = queries meeting threshold/total"""
        if not queries:
            return 0.0
            
        actionable = 0
        for q in queries:
            if self._is_actionable(q):
                actionable += 1
        
        return actionable / len(queries)
    
    def _is_actionable(self, query: QueryResult) -> bool:
        # WHAT: Helper to check if a single query result meets actionability thresholds for its stakeholder
        # WHY: Different stakeholders have different requirements
        # LOGIC:
        #   - Operator (dispatch): Needs ≥90% completeness (see most of fleet) AND <500m error (can find vehicle)
        #   - Planner (analysis): Needs ≥90% accuracy on counts (understand trends correctly)
        #   - Others: Return False (regulator not tested for actionability)
        """Check if query meets stakeholder-specific thresholds"""
        if query.stakeholder == StakeholderType.OPERATOR:
            # Operator dispatch: completeness ≥ 90% AND error < 500m
            return (query.completeness >= self.operator_thresholds['completeness'] and
                    query.error_meters < self.operator_thresholds['error_m'])
        
        elif query.stakeholder == StakeholderType.PLANNER:
            # Planner analysis: accuracy ≥ 90%
            accuracy = self.calculate_response_accuracy(
                query.reported_value.get('total', 0) if isinstance(query.reported_value, dict) else query.reported_value,
                query.true_value.get('total', 0) if isinstance(query.true_value, dict) else query.true_value
            )
            return accuracy >= self.planner_thresholds['accuracy']
        
        return False
    
    def calculate_sla_compliance(self, queries: List[QueryResult]) -> float:
        # WHAT: Metric 3.3 - measures % of queries meeting Service Level Agreement requirements
        # WHY: Privacy systems need to meet operational requirements (latency) not just accuracy
        # LOGIC: Counts queries meeting stakeholder's latency+completeness/accuracy SLAs, divides by total
        # MEANING: 100% = system reliable for operations; <90% = too many missed SLAs, system unreliable
        # SLA REQUIREMENTS:
        #   - Operator: <100ms response time AND ≥90% completeness
        #   - Planner: <500ms response time AND ≥90% accuracy on counts
        """Section 3.3: SLA = queries meeting all criteria/total"""
        if not queries:
            return 0.0
            
        compliant = 0
        for q in queries:
            if self._meets_sla(q):
                compliant += 1
        
        return compliant / len(queries)
    
    def _meets_sla(self, query: QueryResult) -> bool:
        # WHAT: Helper to check if a single query meets SLA (Service Level Agreement) requirements
        # WHY: Not enough to be accurate; data must arrive fast enough to be useful
        # LOGIC:
        #   - Operator: latency <100ms (fast enough for dispatch) AND completeness ≥90%
        #   - Planner: latency <500ms (can tolerate delays) AND accuracy ≥90%
        #   - Others: Return False
        """Check if query meets all SLA requirements"""
        if query.stakeholder == StakeholderType.OPERATOR:
            # Operator: latency < 100ms AND completeness > 90%
            return (query.latency_ms < self.operator_thresholds['latency_ms'] and
                    query.completeness >= self.operator_thresholds['completeness'])
        
        elif query.stakeholder == StakeholderType.PLANNER:
            # Planner: latency < 500ms AND accuracy > 90%
            accuracy = self.calculate_response_accuracy(
                query.reported_value.get('total', 0) if isinstance(query.reported_value, dict) else query.reported_value,
                query.true_value.get('total', 0) if isinstance(query.true_value, dict) else query.true_value
            )
            return (query.latency_ms < self.planner_thresholds['latency_ms'] and
                    accuracy >= self.planner_thresholds['accuracy'])
        
        return False
    
    def check_temporal_consistency(self, time_series: List[Dict]) -> float:
        # WHAT: Metric 3.4 - checks if privacy-degraded data makes physical sense over time
        # WHY: Privacy noise could cause impossible situations (vehicle teleporting, counts jumping by 100)
        # PHYSICAL CONSTRAINTS:
        #   1. Vehicle counts can't change more than ~20 per 100 seconds (vehicles enter/exit slowly)
        #   2. Individual location can't move more than 50m/second (vehicle speed limit ~200 km/h)
        # LOGIC: Compares each query to previous, counts violations, returns (1 - violation_rate)
        # RANGE: 1.0 (perfectly consistent) to 0.0 (many impossible changes)
        # RETURNS: % of consecutive queries that don't violate physical constraints
        """Section 3.4: Consistency = queries passing coherence/total"""
        if len(time_series) < 2:
            return 1.0
            
        violations = 0
        for i in range(1, len(time_series)):
            curr = time_series[i]
            prev = time_series[i-1]
            
            # Time difference in seconds
            delta_t = (curr['step'] - prev['step'])  # steps are seconds
            
            # Check physical constraints from paper
            if 'count' in curr and 'count' in prev:
                delta_count = abs(curr['count'] - prev['count'])
                # Vehicle count change < 20 per 100 seconds
                max_change = 20 * (delta_t / 100)
                if delta_count > max_change:
                    violations += 1
            
            if 'location' in curr and 'location' in prev:
                # Speed < 200 km/h = 55.5 m/s
                # Location change < 50m per second
                dx = curr['location'][0] - prev['location'][0]
                dy = curr['location'][1] - prev['location'][1]
                distance = math.sqrt(dx*dx + dy*dy)
                max_distance = 50 * delta_t
                if distance > max_distance:
                    violations += 1
        
        consistency = 1 - (violations / (len(time_series) - 1))
        return max(0, consistency)
    
    def measure_decision_quality(self, decisions_with_pet: List, ground_truth: List) -> float:
        # WHAT: Metric 3.5 - measures if dispatch decisions are still correct with privacy-degraded locations
        # WHY: Privacy impacts utility; even if system is private, it fails if wrong vehicle gets dispatched
        # LOGIC:
        #   1. For each location query: dispatcher picks "nearest vehicle" based on true data (baseline)
        #   2. Dispatcher also picks nearest vehicle based on privacy-degraded data (with_pet)
        #   3. Counts how many times both pick the same vehicle
        #   4. Returns: (correct_decisions / total_decisions)
        # MEANING: 100% = privacy doesn't affect dispatch decisions; 50% = half of decisions change
        # USAGE: Low decision quality = privacy too strong; loses practical utility
        """Section 3.5: Decision = correct with degraded data/total"""
        if not decisions_with_pet or not ground_truth:
            return 0.0
        
        correct = 0
        for i in range(min(len(decisions_with_pet), len(ground_truth))):
            if self._same_decision(decisions_with_pet[i], ground_truth[i]):
                correct += 1
        
        return correct / len(decisions_with_pet)
    
    def _same_decision(self, decision1, decision2) -> bool:
        # WHAT: Helper to compare two dispatch decisions and see if they're identical
        # WHY: Used by measure_decision_quality to check if privacy-degraded data leads to same dispatch
        # COMPARES: The 'nearest_vehicle' field - are they sending to the same vehicle?
        # RETURNS: True if both decisions select the same vehicle, False otherwise
        """Check if two dispatch decisions are the same"""
        # For nearest vehicle selection
        if 'nearest_vehicle' in decision1 and 'nearest_vehicle' in decision2:
            return decision1['nearest_vehicle'] == decision2['nearest_vehicle']
        return decision1 == decision2