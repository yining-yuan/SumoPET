# ==================== LAYER 1: IoT AGENT ====================

import time
from typing import Dict, List, Optional, Tuple
from data_structures import VehicleEntity

import logging
logger = logging.getLogger(__name__)

# ==================== LAYER 1: IoT AGENT ====================

import time
from typing import Dict, List, Optional, Tuple
from data_structures import VehicleEntity

import logging
logger = logging.getLogger(__name__)

class IoTAgentModule:
    # WHAT: Connects to SUMO simulator and collects real-time vehicle data
    # WHY: Provides ground truth data that flows through the privacy system
    # Acts as the sensor layer that gathers vehicle positions, speeds, and types
    
    def __init__(self, traci_instance):
        # WHAT: Initializes IoT agent with connection to SUMO simulator
        # WHY: Needs reference to traci (Traffic Control Interface) to query simulation
        # STORES: Reference to traci instance used in collect_vehicles()
        self.traci = traci_instance
        logger.info("[IoT Agent] Initialized")
    
    def collect_vehicles(self) -> List[VehicleEntity]:
        # WHAT: Gathers all currently active vehicles from SUMO simulator and packages them as VehicleEntity objects
        # WHY: Called every step to get ground truth data for privacy processing
        # PROCESS:
        #   1. Query SUMO for list of all vehicle IDs
        #   2. For each vehicle, fetch: type, position (x,y), current road, speed
        #   3. Create VehicleEntity object with all this data
        #   4. Return list of entities
        # ERROR HANDLING: Gracefully skips vehicles with missing data; logs warnings if SUMO query fails
        # RETURNS: List of VehicleEntity objects representing all vehicles at current simulation time
        entities = []
        try:
            vehicle_ids = self.traci.vehicle.getIDList()
            for veh_id in vehicle_ids:
                try:
                    vtype = self.traci.vehicle.getTypeID(veh_id)
                    x, y = self.traci.vehicle.getPosition(veh_id)
                    edge = self.traci.vehicle.getRoadID(veh_id)
                    speed = self.traci.vehicle.getSpeed(veh_id)
                    entities.append(VehicleEntity(veh_id, vtype, (x, y), edge, speed, time.time()))
                except:
                    continue
        except Exception as e:
            logger.warning(f"Error collecting vehicles: {e}")
        return entities