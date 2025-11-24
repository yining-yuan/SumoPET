import time
from adaptive_pet_engine import AdaptivePETEngine
from iot_agent import IoTAgentModule
from context_broker import ContextBroker

import os
import traci
from pathlib import Path

import anonypy

import pandas as pd

import logging
logger = logging.getLogger(__name__)

# WHAT: Test script to debug k-anonymity implementation
# WHY: Isolates k-anonymity testing from main experiment for easier debugging
# PROCESS:
#   1. Starts SUMO simulator with Trikala city traffic scenario
#   2. Runs simulation for 50 steps to collect vehicles
#   3. Calls k-anonymity with k=2 on collected vehicles
#   4. Prints results to verify anonymization works correctly
# NOTE: This is a standalone test - not part of the main experimental pipeline
# USED FOR: Verifying that k-anonymity mechanism works before running full experiment
mode = "test_k_anon"
out = Path(f"outputs_{mode}")
out.mkdir(parents=True, exist_ok=True)

cmd = [
    "/home/opp_env/.venv/bin/sumo", "-c", str("trikala_maas_project/config/trikala_merged.sumocfg"),
    "--no-step-log", "--duration-log.disable",
    "--seed", str(seed),
    "--tripinfo-output", str(out / f"tripinfo_{mode}.xml"),
    "--emission-output", str(out / f"emission_{mode}.xml")
]

logger.info(f"Starting SUMO for {mode} mode...")
traci.start(cmd)

iot_agent = IoTAgentModule(traci)
context_broker = ContextBroker()

for i in range(50):
    traci.simulationStep()
    time.sleep(0.1)
    
    real_entities = iot_agent.collect_vehicles()
    context_broker.update_entities(real_entities)
    
    entities = context_broker.query_all_vehicles()

traci.close()

# print(query_result)

engine = AdaptivePETEngine("static-kanon")

print(engine._apply_k_anonymity(entities, 2))

# df = pd.DataFrame(entities)

# df[["location_x", "location_y"]] = df["location"].apply(pd.Series)

# with pd.option_context('display.max_columns', None):
#     print(df)

# categorical = ["type", "edge"]
# for name in categorical:
#     df[name] = df[name].astype("category")

# print(df["location"].dtype)

# # suppressed: "type", "speed", "edge"
# quasi_identifiers = ["location_x", "location_y"] # Quasi-identifiers
# sensitive_column = "id"
# # Anything not in quasi_identifiers or sensitive_column will get suppressed (removed)
# # e.g. "edge" is suppressed

# p = anonypy.Preserver(df, quasi_identifiers, sensitive_column)
# rows = p.anonymize_k_anonymity(k=2)

# print(rows)

# dfn = pd.DataFrame(rows)

# print("Anonymized:")
# with pd.option_context('display.max_columns', None):
#     print(dfn)

# # After anonymization, each location_x field has format e.g. ["289.342280009367-386.77633339845875"] (list with one str element)
# # Convert each range in location_x and location_y to the average of that range (bucket)
# def range_to_average(val):
#     val = val[0]
#     parts = val.split('-')
#     low = float(parts[0])
#     high = float(parts[1])
#     return (low + high) / 2.0

# dfn["location_x"] = dfn["location_x"].apply(range_to_average)
# dfn["location_y"] = dfn["location_y"].apply(range_to_average)

# # Regroup location_x and location_y into one tuple field
# dfn["location"] = list(zip(dfn["location_x"], dfn["location_y"]))

# print("Bucketed:")
# with pd.option_context('display.max_columns', None):
#     print(dfn)
