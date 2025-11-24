# ==================== LAYER 3: PETs ENGINE ====================

from typing import Dict, List, Optional, Tuple
from data_structures import VehicleEntity, StakeholderType, PrivacyMechanism
import math
from collections import defaultdict

from diffprivlib.mechanisms import LaplaceBoundedDomain, Laplace, GaussianAnalytic

import anonypy
import pandas as pd

import logging
logger = logging.getLogger(__name__)

class AdaptivePETEngine:
    """Implements adaptive PET selection with all mechanisms from paper"""
    
    def __init__(self, mode: str):
        self.mode = mode
        
        # Higher epsilon values for reasonable noise levels
        self.epsilon_values = {'low': 0.5, 'medium': 1.0, 'high': 2.0}
        self.k_values = {3: 'low', 5: 'medium', 10: 'high'}
        self.delta = 1e-5
        
        # Bounds and sensitivity - will be auto-detected
        self.location_bounds = None
        
        self.query_results = []
        self.dispatch_decisions = []
        
        logger.info(f"[PETs Engine] Mode: {mode}")
    
    def _detect_bounds(self, entities: List[VehicleEntity]) -> Tuple[float, float, float, float]:
        """Auto-detect coordinate bounds from actual data"""
        if not entities:
            return (0, 1000, 0, 1000)
        
        x_coords = [e.location[0] for e in entities]
        y_coords = [e.location[1] for e in entities]
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # Add 10% padding
        x_range = max(100, x_max - x_min)  # Minimum 100m range
        y_range = max(100, y_max - y_min)
        
        x_min -= x_range * 0.1
        x_max += x_range * 0.1
        y_min -= y_range * 0.1
        y_max += y_range * 0.1
        
        logger.info(f"Auto-detected bounds: X=[{x_min:.1f}, {x_max:.1f}], Y=[{y_min:.1f}, {y_max:.1f}]")
        return (x_min, x_max, y_min, y_max)
    
    def select_mechanism(self, stakeholder: StakeholderType, query_type: str) -> Tuple[PrivacyMechanism, float]:
        """Adaptive selection based on stakeholder and query type"""
        if self.mode == "baseline":
            return PrivacyMechanism.NONE, float('inf')
        
        elif self.mode == "static-laplace":
            return PrivacyMechanism.LAPLACE, self.epsilon_values['medium']
        
        elif self.mode == "static-kanon":
            return PrivacyMechanism.K_ANONYMITY, 5
        
        elif self.mode == "adaptive":
            # Stakeholder-specific selection from paper
            if stakeholder == StakeholderType.OPERATOR:
                # Low latency required -> Laplace
                return PrivacyMechanism.LAPLACE, self.epsilon_values['medium']
            elif stakeholder == StakeholderType.PLANNER:
                # Use k-anonymity for planner
                return PrivacyMechanism.K_ANONYMITY, 5
            else:  # REGULATOR
                return PrivacyMechanism.GAUSSIAN, self.epsilon_values['medium']
        
        return PrivacyMechanism.LAPLACE, self.epsilon_values['medium']

    def apply_privacy(self, data: any, mechanism: PrivacyMechanism, 
                     epsilon: float, query_type: str) -> Tuple[any, float]:
        """Apply selected PET and return (degraded_data, completeness)"""
        
        if mechanism == PrivacyMechanism.NONE:
            # Return same format as other mechanisms
            if query_type == "location":
                return [(e.id, e.location) for e in data], 1.0
            else:
                return data, 1.0
        
        elif mechanism == PrivacyMechanism.LAPLACE:
            if query_type == "location":
                return self._apply_laplace_locations(data, epsilon)
            else:
                return self._apply_laplace_counts(data, epsilon), 1.0
        
        elif mechanism == PrivacyMechanism.GAUSSIAN:
            if query_type == "location":
                return self._apply_gaussian_locations(data, epsilon)
            else:
                return self._apply_gaussian_counts(data, epsilon), 1.0
        
        elif mechanism == PrivacyMechanism.K_ANONYMITY:
            # K-anonymity only works on entities (location data)
            return self._apply_k_anonymity(data, int(epsilon))
        
        return data, 1.0
    
    def _apply_laplace_locations(self, entities: List[VehicleEntity], 
                                 epsilon: float) -> Tuple[List, float]:
        """Apply Laplace noise to locations"""
        print(f"Applying Laplace noise to locations with epsilon {epsilon}")
        if math.isinf(epsilon):
            return [(e.id, e.location) for e in entities], 1.0
        
        # Auto-detect bounds on first call
        # if self.location_bounds is None:
        #     x_min, x_max, y_min, y_max = self._detect_bounds(entities)
        #     self.location_bounds = (x_min, x_max, y_min, y_max)
        
        # x_min, x_max, y_min, y_max = self.location_bounds

        x_min = 100
        x_max = 1300
        y_min = 100
        y_max = 1300
        
        # Trikala map is roughly 1200m x 1200m
        x_sensitivity = x_max - x_min   
        y_sensitivity = y_max - y_min
        
        logger.debug(f"Laplace sensitivities: X={x_sensitivity:.1f}m, Y={y_sensitivity:.1f}m")

        mech_x = LaplaceBoundedDomain(
            epsilon=epsilon/2, 
            delta=0.0, 
            sensitivity=x_sensitivity,
            lower=x_min, 
            upper=x_max
        )
        mech_y = LaplaceBoundedDomain(
            epsilon=epsilon/2,
            delta=0.0,
            sensitivity=y_sensitivity,
            lower=y_min,
            upper=y_max
        )
        
        noisy_locations = []
        for e in entities:
            noisy_x = mech_x.randomise(e.location[0])
            noisy_y = mech_y.randomise(e.location[1])
            noisy_locations.append((e.id, (noisy_x, noisy_y)))
        
        return noisy_locations, 1.0  # 100% completeness
    
    def _apply_gaussian_locations(self, entities: List[VehicleEntity],
                                  epsilon: float) -> Tuple[List, float]:
        """Apply Gaussian noise to locations"""
        if math.isinf(epsilon):
            return [(e.id, e.location) for e in entities], 1.0
        
        # Auto-detect bounds on first call
        if self.location_bounds is None:
            x_min, x_max, y_min, y_max = self._detect_bounds(entities)
            self.location_bounds = (x_min, x_max, y_min, y_max)
        
        x_min, x_max, y_min, y_max = self.location_bounds
        
        # Trikala map is roughly 1200m x 1200m
        x_sensitivity = 1200
        y_sensitivity = 1200
        
        logger.debug(f"Gaussian sensitivities: X={x_sensitivity:.1f}m, Y={y_sensitivity:.1f}m")

        mech_x = GaussianAnalytic(
            epsilon=epsilon/2, 
            delta=self.delta/2,
            sensitivity=x_sensitivity
        )
        mech_y = GaussianAnalytic(
            epsilon=epsilon/2, 
            delta=self.delta/2,
            sensitivity=y_sensitivity
        )
        
        noisy_locations = []
        for e in entities:
            noisy_x = max(x_min, min(x_max, mech_x.randomise(e.location[0])))
            noisy_y = max(y_min, min(y_max, mech_y.randomise(e.location[1])))
            noisy_locations.append((e.id, (noisy_x, noisy_y)))
        
        return noisy_locations, 1.0
    
    def _apply_laplace_counts(self, counts: Dict[str, int], epsilon: float) -> Dict:
        """Apply Laplace noise to counts"""
        print(f"Applying Laplace noise to counts with epsilon {epsilon}")
        if math.isinf(epsilon):
            return counts

        sensitivity = 1 # Adding/removing one user to dataset will change count by +/- 1
        
        mech = LaplaceBoundedDomain(
            epsilon=epsilon, delta=0.0,
            sensitivity=sensitivity,
            lower=0,
            upper=1000
        )
        
        noisy_counts = {}
        for key, value in counts.items():
            noisy_counts[key] = max(0, int(mech.randomise(float(value))))
        return noisy_counts
    
    def _apply_gaussian_counts(self, counts: Dict[str, int], epsilon: float) -> Dict:
        """Apply Gaussian noise to counts"""
        if math.isinf(epsilon):
            return counts
        
        mech = GaussianAnalytic(
            epsilon=epsilon, delta=self.delta,
            sensitivity=self.count_sensitivity
        )
        
        noisy_counts = {}
        for key, value in counts.items():
            noisy_value = mech.randomise(float(value))
            noisy_counts[key] = max(0, int(noisy_value))
        return noisy_counts
    
    def _apply_k_anonymity(self, entities: List[VehicleEntity], 
                           k: int) -> Tuple[List, float]:
        """Apply k-anonymity with Mondrian partitioning"""
        
        # Convert to dataframe for anonypy
        df = pd.DataFrame(entities) # TODO: is this slow?

        # Columns: id, type, edge, speed, location

        # Split location tuple into separate columns
        df[["location_x", "location_y"]] = df["location"].apply(pd.Series)

        # Ensure categorical columns are treated as categorical
        categorical = ["type", "edge"]
        for name in categorical:
            df[name] = df[name].astype("category")

        quasi_identifiers = ["type", "speed", "location_x", "location_y"] # Quasi-identifiers
        sensitive_column = "id" # Actually, sensitive column makes no difference, but library requires something to be passed in

        p = anonypy.Preserver(df, quasi_identifiers, sensitive_column)
        rows = p.anonymize_k_anonymity(k=k)

        dfn = pd.DataFrame(rows)

        # After anonymization, each location_x field has format e.g. ["289.342280009367-386.77633339845875"] (list with one str element)
        # Convert each range in location_x and location_y to the average of that range (bucket)
        def range_to_average(val):
            val = val[0]
            parts = val.split('-')
            low = float(parts[0])
            high = float(parts[1])
            return (low + high) / 2.0

        dfn["location_x"] = dfn["location_x"].apply(range_to_average)
        dfn["location_y"] = dfn["location_y"].apply(range_to_average)

        # Recombine location_x and location_y into one tuple field
        dfn["location"] = list(zip(dfn["location_x"], dfn["location_y"]))

        completeness = 1.0 # We haven't removed any rows so completeness is 1.0

        # Suppress id
        return [(e["id"], e["location"]) for e in dfn.to_dict(orient="records")], completeness
    
    def find_nearest_vehicle(self, request_location: Tuple[float, float],
                            vehicle_locations: List[Tuple[str, Tuple[float, float]]]) -> Optional[str]:
        """Decision task: identify nearest vehicle"""
        if not vehicle_locations:
            return None
        
        nearest = None
        min_dist = float('inf')
        
        for veh_id, location in vehicle_locations:
            dist = math.sqrt((location[0] - request_location[0])**2 + 
                           (location[1] - request_location[1])**2)
            if dist < min_dist:
                min_dist = dist
                nearest = veh_id
        
        return nearest