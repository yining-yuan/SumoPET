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
import shutil
import numpy as np

from experiment_controller import ExperimentController
try:
    from build_encrypted_scenario import encrypt_routes
except ImportError:
    encrypt_routes = None

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if "SUMO_HOME" in os.environ:
    # Add SUMO tools to path so sumolib/traci can be found if not pip-installed
    tools_path = os.path.join(os.environ["SUMO_HOME"], "tools")
    if os.path.isdir(tools_path):
        sys.path.append(tools_path)

# sys.path.append("/c/Program Files (x86)/Eclipse/Sumo/tools")

import traci

try:
    from sumolib import checkBinary as _sumo_check_binary
except Exception:
    _sumo_check_binary = None


def _resolve_sumo_binary(gui: bool = False, override: str | None = None) -> str:
    """Find the SUMO binary path in a robust, cross-platform way.

    Order of resolution:
    1) sumolib.checkBinary if available
    2) $SUMO_HOME/bin/{sumo|sumo-gui}
    3) $CONDA_PREFIX/bin/{sumo|sumo-gui}
    4) shutil.which on PATH
    Raises FileNotFoundError with guidance if not found.
    """
    binary_name = "sumo-gui" if gui else "sumo"

    # 0) explicit override
    if override:
        candidate = os.path.expanduser(override)
        if os.path.isfile(candidate):
            return candidate
        raise FileNotFoundError(f"Provided SUMO binary not found: {candidate}")

    # 1) sumolib helper, but validate existence
    if _sumo_check_binary is not None:
        try:
            candidate = _sumo_check_binary(binary_name)
            # If sumolib returns just the name, ensure it's on PATH
            if os.path.isabs(candidate) and os.path.isfile(candidate):
                return candidate
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        except Exception:
            pass

    # 2) SUMO_HOME
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        candidate = os.path.join(sumo_home, "bin", binary_name)
        if os.path.isfile(candidate):
            return candidate

    # 3) CONDA_PREFIX/bin
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidate = os.path.join(conda_prefix, "bin", binary_name)
        if os.path.isfile(candidate):
            return candidate

    # 4) PATH
    on_path = shutil.which(binary_name)
    if on_path:
        return on_path

    raise FileNotFoundError(
        f"Could not find '{binary_name}'. Install SUMO and either set $SUMO_HOME or add '{binary_name}' to PATH."
    )


# ==================== MAIN EXECUTION ====================

def run_experiment(mode: str, cfg: str, output_dir: str, max_steps: int = 7200, seed: int = 42, sumo_bin_override: str | None = None):
    """Run complete experiment with SUMO"""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    
    # Build SUMO command
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    sumo_bin = _resolve_sumo_binary(gui=False, override=sumo_bin_override)
    cmd = [
        sumo_bin, "-c", str(cfg),
        "--no-step-log", "--duration-log.disable",
        "--seed", str(seed),
        "--tripinfo-output", str(out / f"tripinfo_{mode}.xml"),
        "--emission-output", str(out / f"emission_{mode}.xml")
    ]
    # New 1125: Add a new mode for encrypted-input
    if mode == "encrypted-input":
        if encrypt_routes is None:
            logger.error("Cannot run encrypted-input mode: build_encrypted_scenario.py not found or failed to import.")
            return
        
        base_path = Path(cfg).parent.parent # trikala_maas_project/
        routes_dir = base_path / "routes"
        original_routes = routes_dir / "persons_merged.rou.xml"
        encrypted_routes = routes_dir / "persons_encrypted.rou.xml"
        public_transport = routes_dir / "public_transport.rou.xml"

        if not original_routes.exists():
             # Fallback if running from different CWD
             original_routes = Path("trikala_maas_project/routes/persons_merged.rou.xml")
             encrypted_routes = Path("trikala_maas_project/routes/persons_encrypted.rou.xml")
             public_transport = Path("trikala_maas_project/routes/public_transport.rou.xml")

        if original_routes.exists():
            success = encrypt_routes(str(original_routes), str(encrypted_routes))
            if success:
                logger.info(f"Using encrypted routes: {encrypted_routes}")
                # Override route files in SUMO command
                # Note: public transport usually needs to be included too
                route_files_arg = f"{public_transport},{encrypted_routes}"
                cmd.extend(["--route-files", route_files_arg])
            else:
                logger.error("Encryption failed, aborting.")
                return
        else:
            logger.error(f"Original route file not found at {original_routes}")
            return
    
    logger.info(f"Starting SUMO for {mode} mode using: {sumo_bin}")
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
    parser = argparse.ArgumentParser(
        description="Option A: Privacy affects query results only (Paper Section 4)"
    )
    
    parser.add_argument("mode", 
                       choices=["baseline", "static-laplace", "static-kanon", "adaptive", "encrypted-input"],
                       help="Experimental condition from paper")
    parser.add_argument("--cfg", required=True, 
                       help="SUMO config file")
    parser.add_argument("--output-dir", default="./outputs",
                       help="Output directory for results")
    parser.add_argument("--max-steps", type=int, default=7200,
                       help="Max simulation steps (paper uses 7200)")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed for reproducibility")
    parser.add_argument("--sumo-bin", default=None,
                       help="Override path to SUMO binary (sumo or sumo-gui)")
    
    args = parser.parse_args()
    run_experiment(args.mode, args.cfg, args.output_dir, args.max_steps, args.seed, args.sumo_bin)

if __name__ == "__main__":
    main()