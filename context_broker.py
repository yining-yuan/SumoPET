# ==================== LAYER 2: CONTEXT BROKER ====================

from data_structures import VehicleEntity
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ContextBroker:
    def __init__(self):
        self.entities: Dict[str, VehicleEntity] = {}
        logger.info("[Context Broker] Initialized")
    
    def update_entities(self, entities: List[VehicleEntity]):
        for entity in entities:
            self.entities[entity.id] = entity
    
    def query_all_vehicles(self) -> List[VehicleEntity]:
        return list(self.entities.values())

    def get_counts(self) -> Dict[str, int]:
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