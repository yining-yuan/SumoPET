# ==================== METRICS CALCULATOR (Section 3) ====================

from typing import Dict, List, Optional, Tuple
from data_structures import QueryResult, StakeholderType
import math

import logging
logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Implements all 5 metrics from paper Section 3"""
    
    def __init__(self):
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
        
    def calculate_response_accuracy(self, reported, true):
        """Section 3.1: Accuracy = 1 - |reported - true|/true"""
        if true == 0:
            return 1.0 if reported == 0 else 0.0
        return max(0, 1 - abs(reported - true) / abs(true))
    
    def calculate_actionable_rate(self, queries: List[QueryResult]) -> float:
        """Section 3.2: Actionable = queries meeting threshold/total"""
        if not queries:
            return 0.0
            
        actionable = 0
        for q in queries:
            if self._is_actionable(q):
                actionable += 1
        
        return actionable / len(queries)
    
    def _is_actionable(self, query: QueryResult) -> bool:
        """Check if query meets stakeholder-specific thresholds"""
        if query.stakeholder == StakeholderType.OPERATOR:
            # Operator dispatch: completeness ≥ 90% AND error < 500m
            return (query.completeness >= self.operator_thresholds['completeness'] and
                    query.error_meters < self.operator_thresholds['error_m'])
        
        elif query.stakeholder == StakeholderType.PLANNER:
            # Planner analysis: accuracy ≥ 90%
            # New 1125: Add query to fix bugs
            if query.query_type == "location":
                # For location queries, use coverage/completeness as proxy for actionable
                return query.completeness >= self.planner_thresholds.get('coverage', 0.80)

            accuracy = self.calculate_response_accuracy(
                query.reported_value.get('total', 0) if isinstance(query.reported_value, dict) else query.reported_value,
                query.true_value.get('total', 0) if isinstance(query.true_value, dict) else query.true_value
            )
            return accuracy >= self.planner_thresholds['accuracy']
        
        return False
    
    def calculate_sla_compliance(self, queries: List[QueryResult]) -> float:
        """Section 3.3: SLA = queries meeting all criteria/total"""
        if not queries:
            return 0.0
            
        compliant = 0
        for q in queries:
            if self._meets_sla(q):
                compliant += 1
        
        return compliant / len(queries)
    
    def _meets_sla(self, query: QueryResult) -> bool:
        """Check if query meets all SLA requirements"""
        if query.stakeholder == StakeholderType.OPERATOR:
            # Operator: latency < 100ms AND completeness > 90%
            return (query.latency_ms < self.operator_thresholds['latency_ms'] and
                    query.completeness >= self.operator_thresholds['completeness'])
        
        elif query.stakeholder == StakeholderType.PLANNER:
            # Planner: latency < 500ms AND accuracy > 90%
            # New 1125: Add query to fix bugs
            if query.query_type == "location":
                return (query.latency_ms < self.planner_thresholds['latency_ms'] and
                        query.completeness >= self.planner_thresholds.get('coverage', 0.80))

            accuracy = self.calculate_response_accuracy(
                query.reported_value.get('total', 0) if isinstance(query.reported_value, dict) else query.reported_value,
                query.true_value.get('total', 0) if isinstance(query.true_value, dict) else query.true_value
            )
            return (query.latency_ms < self.planner_thresholds['latency_ms'] and
                    accuracy >= self.planner_thresholds['accuracy'])
        
        return False
    
    def check_temporal_consistency(self, time_series: List[Dict]) -> float:
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
        """Section 3.5: Decision = correct with degraded data/total"""
        if not decisions_with_pet or not ground_truth:
            return 0.0
        
        correct = 0
        for i in range(min(len(decisions_with_pet), len(ground_truth))):
            if self._same_decision(decisions_with_pet[i], ground_truth[i]):
                correct += 1
        
        return correct / len(decisions_with_pet)
    
    def _same_decision(self, decision1, decision2) -> bool:
        """Check if two dispatch decisions are the same"""
        # For nearest vehicle selection
        if 'nearest_vehicle' in decision1 and 'nearest_vehicle' in decision2:
            return decision1['nearest_vehicle'] == decision2['nearest_vehicle']
        return decision1 == decision2