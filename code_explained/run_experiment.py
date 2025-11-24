#!/usr/bin/env python3
"""
OPTION A: Complete implementation with all 5 metrics from paper
Matches experimental setup from Section 4 of the paper
"""

import argparse
import csv
import math
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
import logging
import numpy as np

from experiment_controller import ExperimentController

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if "SUMO_HOME" in os.environ:
    sys.path.append(os.path.join(os.environ["SUMO_HOME"], "bin"))

# sys.path.append("/c/Program Files (x86)/Eclipse/Sumo/tools")

import traci


# ==================== MAIN EXECUTION ====================

#!/usr/bin/env python3
"""
OPTION A: Complete implementation with all 5 metrics from paper
Matches experimental setup from Section 4 of the paper
"""

import argparse
import csv
import math
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
import logging
import numpy as np

from experiment_controller import ExperimentController

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if "SUMO_HOME" in os.environ:
    sys.path.append(os.path.join(os.environ["SUMO_HOME"], "bin"))

# sys.path.append("/c/Program Files (x86)/Eclipse/Sumo/tools")

import traci


# ==================== MAIN EXECUTION ====================

def run_experiment(mode: str, cfg: str, output_dir: str, max_steps: int = 7200, seed: int = 42):
    # WHAT: Main experiment runner - starts SUMO simulation and runs privacy experiment
    # WHY: Orchestrates the complete experimental pipeline for one privacy mode
    # FLOW:
    #   1. Set random seeds for reproducibility
    #   2. Create output directory for results
    #   3. Build SUMO launch command with config and output options
    #   4. Start SUMO traffic simulation
    #   5. Create ExperimentController to manage queries
    #   6. Run simulation loop: collect vehicle data and process queries each step
    #   7. Export results when finished (CSV files with metrics)
    # PARAMETERS:
    #   - mode: baseline, static-laplace, static-kanon, or adaptive
    #   - cfg: Path to SUMO config file (.sumocfg)
    #   - output_dir: Where to save CSV results
    #   - max_steps: How many simulation steps to run (7200 = full experiment)
    #   - seed: Random seed for reproducibility (default 42)
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    
    # Build SUMO command
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "/home/opp_env/.venv/bin/sumo", "-c", str(cfg),
        "--no-step-log", "--duration-log.disable",
        "--seed", str(seed),
        "--tripinfo-output", str(out / f"tripinfo_{mode}.xml"),
        "--emission-output", str(out / f"emission_{mode}.xml")
    ]
    
    logger.info(f"Starting SUMO for {mode} mode...")
    traci.start(cmd)
    
    # Create controller
    controller = ExperimentController(mode=mode, export_dir=str(out))
    
    try:
        step = 0
        while step < max_steps and traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            controller.step(step)
            step += 1
        
        # Export results
        controller.export_results()
        logger.info(f"Completed {mode} mode after {step} steps")
        
    finally:
        traci.close()

def main():
    # WHAT: Argument parser and entry point for running privacy experiments
    # WHY: Allows users to specify mode, config file, and options from command line
    # USAGE: python run_experiment.py baseline --cfg path/to/config.sumocfg
    # OPTIONS:
    #   - mode (required): One of [baseline, static-laplace, static-kanon, adaptive]
    #   - --cfg (required): Path to SUMO configuration file
    #   - --output-dir: Where to save results (default: ./outputs)
    #   - --max-steps: How many simulation steps (default: 7200)
    #   - --seed: Random seed (default: 42)
        description="Option A: Privacy affects query results only (Paper Section 4)"
    
    
        parser.add_argument("mode", 
                        choices=["baseline", "static-laplace", "static-kanon", "adaptive"],
                        help="Experimental condition from paper")
        parser.add_argument("--cfg", required=True, 
                        help="SUMO config file")
        parser.add_argument("--output-dir", default="./outputs",
                        help="Output directory for results")
        parser.add_argument("--max-steps", type=int, default=7200,
                        help="Max simulation steps (paper uses 7200)")
        parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
        
        args = parser.parse_args()
        run_experiment(args.mode, args.cfg, args.output_dir, args.max_steps, args.seed)

if __name__ == "__main__":
        main()