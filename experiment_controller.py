# ==================== EXPERIMENT CONTROLLER ====================

from typing import Dict, List, Optional, Tuple
from data_structures import VehicleEntity, QueryResult, MetricsEvaluation, StakeholderType, PrivacyMechanism
from iot_agent import IoTAgentModule
from context_broker import ContextBroker
from adaptive_pet_engine import AdaptivePETEngine
from metrics_calculator import MetricsCalculator

from pathlib import Path
import time
import csv
import math

import traci

import pickle

import logging
logger = logging.getLogger(__name__)

class ExperimentController:
    def __init__(self, mode: str, export_dir: str):
        self.mode = mode
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize layers
        self.iot_agent = IoTAgentModule(traci)
        self.context_broker = ContextBroker()
        self.pets_engine = AdaptivePETEngine(mode)
        self.metrics_calc = MetricsCalculator()
        
        # Track all queries and results
        self.all_queries = []
        self.time_series = []
        
        # For decision quality metric
        self.baseline_decisions = []
        self.degraded_decisions = []
        
        # Ground Truth Storage for Encrypted Input Mode
        self.ground_truth_store = {}
        self.ground_truth_file = self.export_dir / "baseline_ground_truth.pkl"
        
        if self.mode == "encrypted-input":
            if self.ground_truth_file.exists():
                logger.info(f"Loading baseline ground truth from {self.ground_truth_file}")
                with open(self.ground_truth_file, 'rb') as f:
                    self.ground_truth_store = pickle.load(f)
            else:
                logger.warning(f"Ground truth file not found at {self.ground_truth_file}. Metrics will be invalid (self-comparison).")
        
        logger.info(f"=== EXPERIMENT MODE: {mode} ===")
    
    def process_query(self, step: int, stakeholder: StakeholderType, 
                     query_type: str) -> QueryResult:
        """Process a single query with privacy"""
        start_time = time.time()
        
        # Get ground truth from current simulation state
        current_entities = self.context_broker.query_all_vehicles()
        current_counts = self.context_broker.get_counts()
        
        # Determine "True Value" based on mode
        if self.mode == "baseline":
            # In baseline, current state IS the ground truth
            if query_type == "location":
                true_value = [(e.id, e.location) for e in current_entities]
            else:
                true_value = current_counts
            
            # Save for later use by encrypted mode
            if step not in self.ground_truth_store:
                self.ground_truth_store[step] = {}
            self.ground_truth_store[step][query_type] = true_value
            
        elif self.mode == "encrypted-input":
            # In encrypted mode, try to load ground truth from baseline run
            if step in self.ground_truth_store and query_type in self.ground_truth_store[step]:
                true_value = self.ground_truth_store[step][query_type]
            else:
                # Fallback if missing (e.g. different step intervals)
                if query_type == "location":
                    true_value = [(e.id, e.location) for e in current_entities]
                else:
                    true_value = current_counts
        else:
            # Standard modes (static-laplace, adaptive)
            if query_type == "location":
                true_value = [(e.id, e.location) for e in current_entities]
            else:
                true_value = current_counts
        
        # Select and apply PET
        mechanism, epsilon = self.pets_engine.select_mechanism(stakeholder, query_type)
        
        if query_type == "location":
            # For encrypted-input, reported value is the current simulation state (which is perturbed)
            # For others, it's the result of applying privacy to current state
            reported_value, completeness = self.pets_engine.apply_privacy(
                current_entities, mechanism, epsilon, query_type
            )

            # Calculate error
            # Note: For encrypted-input, location error might be high/undefined due to ID mismatch
            error_meters = self._calculate_location_error(true_value, reported_value)
            count_error = 0
            
        else:  # count query
            # For encrypted-input, reported value is current simulation counts
            if mechanism == PrivacyMechanism.K_ANONYMITY:
                 reported_value = current_counts
                 completeness = 1.0
            else:
                reported_value, completeness = self.pets_engine.apply_privacy(
                    current_counts, mechanism, epsilon, query_type
                )
            
            # Calculate error
            error_meters = 0
            count_error = abs(reported_value.get('total', 0) - true_value.get('total', 0))
        
        latency_ms = (time.time() - start_time) * 1000
        
        result = QueryResult(
            step=step,
            stakeholder=stakeholder,
            query_type=query_type,
            true_value=true_value,
            reported_value=reported_value,
            mechanism=mechanism,
            epsilon=epsilon,
            latency_ms=latency_ms,
            completeness=completeness,
            error_meters=error_meters,
            count_error=count_error
        )
        
        self.all_queries.append(result)
        
        # Track time series for temporal consistency
        if query_type == "count":
            self.time_series.append({
                'step': step,
                'count': reported_value.get('total', 0)
            })

            # print(result)
        
        # Simulate dispatch decision for decision quality metric
        if query_type == "location" and stakeholder == StakeholderType.OPERATOR:
            # Use center of network bounds if available
            if self.pets_engine.location_bounds:
                x_min, x_max, y_min, y_max = self.pets_engine.location_bounds
                request_loc = ((x_min + x_max) / 2, (y_min + y_max) / 2)
            else:
                request_loc = (400, 400)  # Fallback
            
            # Baseline decision (with true data)
            baseline_nearest = self.pets_engine.find_nearest_vehicle(
                request_loc, true_value
            )
            self.baseline_decisions.append({'nearest_vehicle': baseline_nearest})
            
            # Degraded decision (with privacy)
            degraded_nearest = self.pets_engine.find_nearest_vehicle(
                request_loc, reported_value
            )
            self.degraded_decisions.append({'nearest_vehicle': degraded_nearest})

        return result
    
    def _calculate_location_error(self, true_locs: List[Tuple], 
                                 reported_locs: List[Tuple]) -> float:
        """Calculate average location error in meters"""
        if not reported_locs:
            return 0.0
        
        errors = []
        reported_dict = dict(reported_locs)
        
        for veh_id, true_loc in true_locs:
            if veh_id in reported_dict:
                rep_loc = reported_dict[veh_id]

                # print(f"True loc: {true_loc}, Reported loc: {rep_loc}")

                error = math.sqrt((true_loc[0] - rep_loc[0])**2 + 
                                (true_loc[1] - rep_loc[1])**2)
                errors.append(error)
        
        return sum(errors) / len(errors) if errors else 0.0
    
    def step(self, sim_step: int):
        """Single simulation step with queries from paper"""
        # Collect and update data
        entities = self.iot_agent.collect_vehicles()
        self.context_broker.update_entities(entities)
        
        # Operator queries every 100 steps (72 total over 7200 steps)
        if sim_step > 0 and sim_step % 100 == 0:
            # Operator asks for both location and count
            result = self.process_query(sim_step, StakeholderType.OPERATOR, "location")
            logger.info(
                f"[Step {sim_step}] Operator: {result.mechanism.value}, "
                f"error={result.error_meters:.1f}m, "
                f"completeness={result.completeness:.1%}, "
                f"latency={result.latency_ms:.1f}ms"
            )

            result = self.process_query(sim_step, StakeholderType.OPERATOR, "count")
            logger.info(
                f"[Step {sim_step}] Operator: {result.mechanism.value}, "
                f"count_error={result.count_error}, "
                f"completeness={result.completeness:.1%}"
            )

        # Planner queries every 300 steps (24 total)
        if sim_step > 0 and sim_step % 300 == 0:
            # Planner asks for both location and count
            result = self.process_query(sim_step, StakeholderType.PLANNER, "location")
            logger.info(
                f"[Step {sim_step}] Planner: {result.mechanism.value}, "
                f"error={result.error_meters:.1f}m, "
                f"completeness={result.completeness:.1%}, "
                f"latency={result.latency_ms:.1f}ms"
            )

            result = self.process_query(sim_step, StakeholderType.PLANNER, "count")
            logger.info(
                f"[Step {sim_step}] Planner: {result.mechanism.value}, "
                f"count_error={result.count_error}, "
                f"completeness={result.completeness:.1%}"
            )
    
    def calculate_final_metrics(self) -> MetricsEvaluation:
        """Calculate all 5 metrics from paper"""
        
        # 1. Response Accuracy (Section 3.1)
        accuracies = []
        for q in self.all_queries:
            if q.query_type == "count":
                acc = self.metrics_calc.calculate_response_accuracy(
                    q.reported_value.get('total', 0),
                    q.true_value.get('total', 0)
                )
                accuracies.append(acc)
        response_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
        
        # 2. Actionable Information Rate (Section 3.2)
        actionable_rate = self.metrics_calc.calculate_actionable_rate(self.all_queries)
        
        # 3. SLA Compliance Rate (Section 3.3)
        sla_compliance = self.metrics_calc.calculate_sla_compliance(self.all_queries)
        
        # 4. Temporal Consistency (Section 3.4)
        temporal_consistency = self.metrics_calc.check_temporal_consistency(self.time_series)
        
        # 5. Decision Support Quality (Section 3.5)
        decision_quality = self.metrics_calc.measure_decision_quality(
            self.degraded_decisions, self.baseline_decisions
        )
        
        return MetricsEvaluation(
            response_accuracy=response_accuracy,
            actionable_rate=actionable_rate,
            sla_compliance=sla_compliance,
            temporal_consistency=temporal_consistency,
            decision_quality=decision_quality
        )
    
    def export_results(self):
        """Export detailed results and final metrics"""
        
        # Save ground truth if in baseline mode
        if self.mode == "baseline":
            logger.info(f"Saving baseline ground truth to {self.ground_truth_file}")
            with open(self.ground_truth_file, 'wb') as f:
                pickle.dump(self.ground_truth_store, f)

        # Export query-level results
        with open(self.export_dir / f"queries_{self.mode}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['step', 'stakeholder', 'query_type', 'mechanism', 
                           'epsilon', 'error_meters', 'count_error', 'completeness',
                           'latency_ms'])
            
            for q in self.all_queries:
                writer.writerow([
                    q.step, q.stakeholder.value, q.query_type,
                    q.mechanism.value, q.epsilon, q.error_meters,
                    q.count_error, q.completeness, q.latency_ms
                ])
        
        # Calculate and export final metrics
        metrics = self.calculate_final_metrics()
        
        with open(self.export_dir / f"metrics_{self.mode}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['metric', 'value'])
            writer.writerow(['response_accuracy', f"{metrics.response_accuracy:.3f}"])
            writer.writerow(['actionable_rate', f"{metrics.actionable_rate:.3f}"])
            writer.writerow(['sla_compliance', f"{metrics.sla_compliance:.3f}"])
            writer.writerow(['temporal_consistency', f"{metrics.temporal_consistency:.3f}"])
            writer.writerow(['decision_quality', f"{metrics.decision_quality:.3f}"])
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"FINAL METRICS - {self.mode.upper()}")
        print(f"{'='*60}")
        print(f"Response Accuracy:      {metrics.response_accuracy:.1%}")
        print(f"Actionable Rate:        {metrics.actionable_rate:.1%}")
        print(f"SLA Compliance:         {metrics.sla_compliance:.1%}")
        print(f"Temporal Consistency:   {metrics.temporal_consistency:.1%}")
        print(f"Decision Quality:       {metrics.decision_quality:.1%}")
        print(f"{'='*60}\n")