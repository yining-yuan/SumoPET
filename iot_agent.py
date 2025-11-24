# ==================== LAYER 1: IoT AGENT ====================

import time
from typing import Dict, List, Optional, Tuple
from data_structures import VehicleEntity

import logging
logger = logging.getLogger(__name__)

class IoTAgentModule:
    def __init__(self, traci_instance):
        self.traci = traci_instance
        logger.info("[IoT Agent] Initialized")
    
    def collect_vehicles(self) -> List[VehicleEntity]:
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