# ==================== LAYER 2: CONTEXT BROKER ====================

from data_structures import VehicleEntity
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ContextBroker:
    # WHAT: Middleware layer that stores and provides access to vehicle data
    # WHY: Decouples IoT data collection layer from privacy enhancement layer; acts as a data repository
    
    def __init__(self):
        # WHAT: Initializes the empty entity store
        # WHY: Sets up the in-memory database for caching vehicle information
        # STORES: Dictionary mapping vehicle_id (string) → VehicleEntity objects
        self.entities: Dict[str, VehicleEntity] = {}
        logger.info("[Context Broker] Initialized")
    
    def update_entities(self, entities: List[VehicleEntity]):
        # WHAT: Updates the stored vehicle data with new/current vehicle information
        # WHY: Called every simulation step to refresh the broker with latest vehicle positions, speeds, etc.
        # PROCESS: Iterates through provided entities and adds/overwrites them in the internal dictionary
        # EFFECT: Replaces old vehicle data with new, so
        #broker always has current snapshot
        for entity in entities:
            self.entities[entity.id] = entity
    
    def query_all_vehicles(self) -> List[VehicleEntity]:
        # WHAT: Returns all currently stored vehicles as a list
        # WHY: Used by privacy engine to get ground truth data before applying privacy mechanisms
        # USED FOR: Location queries (dispatcher queries) and decision quality evaluation
        # RETURNS: List of all VehicleEntity objects stored in the broker
        return list(self.entities.values())

    def get_counts(self) -> Dict[str, int]:
        # WHAT: Computes aggregate statistics (vehicle type counts) from stored entities (from wehere exactly?)
        # WHY: Used for count queries - planners/regulators often ask "how many taxis are operating?"
        # PROCESS: Iterates through all vehicles and bins them by type (taxi/bike/bus/car)
        # CLASSIFIES: Uses string matching (e.g., "taxi" in vehicle_type) to categorize vehicles
        # RETURNS: Dictionary like {'taxis': 12, 'bikes': 5, 'cars': 28, 'buses': 3, 'total': 48}
        counts = {'taxis': 0, 'bikes': 0, 'cars': 0, 'buses': 0, 'total': 0}
        for entity in self.entities.values():
            vtype = entity.type.lower()
            if 'taxi' in vtype:
                counts['taxis'] += 1
            elif 'bike' in vtype or 'bicycle' in vtype:
                counts['bikes'] += 1
            elif 'bus' in vtype:
                counts['buses'] += 1
            else:
                counts['cars'] += 1
            counts['total'] += 1
        return counts