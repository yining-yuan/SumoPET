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
        # WHAT: Initializes the PETs (Privacy Enhancing Technologies) engine
        # WHY: Need to configure the privacy mechanisms that will be applied based on experimental mode
        # SETS UP: Different epsilon values for DP mechanisms, k values for k-anonymity, and tracking lists
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
        # WHAT: Automatically detects the geographic boundaries (min/max x,y coordinates) from vehicle data
        # WHY: Need to know the valid range for Laplace mechanism to clip noisy locations within realistic bounds
        # RETURNS: Tuple of (x_min, x_max, y_min, y_max) with 10% padding added for safety
        # EXAMPLE: If vehicles are at (100, 200), returns adjusted bounds like (80, 220)
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
        # WHAT: Chooses which privacy mechanism to apply based on stakeholder type and query type
        # WHY: Different stakeholders (operator, planner, regulator) have different privacy/utility tradeoffs
        # LOGIC:
        #   - baseline: No privacy applied (PrivacyMechanism.NONE)
        #   - static-laplace: Always use Laplace mechanism with medium epsilon
        #   - static-kanon: Always use k-anonymity with k=5
        #   - adaptive: Selects mechanism based on stakeholder needs (operator→Laplace, planner→k-anonymity, regulator→Gaussian)
        # RETURNS: Tuple of (mechanism type, epsilon/k value to use)
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
        # WHAT: Main dispatcher that applies the selected privacy mechanism to data
        # WHY: Centralized method to handle all privacy transformations (noise, anonymization)
        # RETURNS: Tuple of (privacy-degraded data, completeness ratio - how much data is retained after privacy)
        # LOGIC: Routes to appropriate privacy function based on mechanism type (Laplace/Gaussian/k-anonymity/None)
        # EXAMPLE: Input 100 vehicles → apply Laplace → returns noisy locations + 1.0 completeness (all kept)
        
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
        # WHAT: Applies Laplace differential privacy noise to vehicle location coordinates
        # WHY: Protects individual vehicle locations while allowing aggregate analysis; lower epsilon = more privacy
        # MECHANISM: Adds Laplace-distributed random noise to X and Y coordinates independently
        # SENSITIVITY: Set to map size (1200m) because worst-case change is moving one vehicle across entire map
        # RETURNS: List of (vehicle_id, noisy_location_tuple) pairs + 1.0 completeness (all vehicles retained)
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
        # WHAT: Applies Gaussian differential privacy noise to vehicle locations
        # WHY: Alternative to Laplace; Gaussian typically adds less extreme outliers, better for regulators
        # MECHANISM: Adds Gaussian-distributed noise to X and Y with epsilon and delta parameters
        # DELTA: Set to 1e-5 (small but non-zero) for approximate differential privacy (eps-delta)
        # CLIPPING: Noisy coordinates are clipped to bounds to keep them realistic
        # RETURNS: List of (vehicle_id, noisy_location) + 1.0 completeness
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
        # WHAT: Applies Laplace noise to aggregate count queries (total vehicles, taxis, bikes, etc.)
        # WHY: When asked "how many vehicles are on the road?" need to add noise to hide individual contributions
        # SENSITIVITY: 1 because adding/removing one vehicle changes total count by exactly 1
        # BOUNDS: Clipped to [0, 1000] to ensure counts stay realistic
        # RETURNS: Dictionary with noisy counts (e.g., {'total': 45, 'taxis': 12, ...})
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
        # WHAT: Applies Gaussian noise to aggregate vehicle counts
        # WHY: Alternative to Laplace for adding privacy to count queries; produces smoother noise distribution
        # NOTE: count_sensitivity attribute not defined (likely a bug - should be set to 1 or epsilon)
        # RETURNS: Dictionary with Gaussian-noisy counts, clamped to [0, ∞)
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
        # WHAT: Applies k-anonymity to vehicle locations by suppressing granular location details
        # WHY: Ensures each vehicle location falls into a group with at least k other similar vehicles (privacy via generalization)
        # ALGORITHM: Uses Mondrian algorithm via anonypy library to partition location/type/speed space
        # QUASI-IDENTIFIERS: type, speed, location_x, location_y (features that could re-identify)
        # PROCESS:
        #   1. Convert vehicle list to dataframe with separate location_x, location_y columns
        #   2. Apply Mondrian partitioning with k parameter
        #   3. Generalize locations to bucket ranges (average the range)
        #   4. Return anonymized locations + completeness metric
        # RETURNS: List of (vehicle_id, generalized_location) + 1.0 completeness (no data suppressed)
        
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
        # WHAT: Finds the closest vehicle to a request location using Euclidean distance
        # WHY: Simulates dispatcher's decision task (who to send to service a request) - used to measure decision quality degradation
        # ALGORITHM: Iterates through vehicles, calculates distance to request point, returns vehicle with min distance
        # USAGE: Called twice per location query - once with true data, once with privacy-degraded data
        #        If privacy causes different vehicle selection, decision quality metric decreases
        # RETURNS: Vehicle ID of nearest vehicle, or None if no vehicles available
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