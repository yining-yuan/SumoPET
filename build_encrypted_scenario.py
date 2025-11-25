import os
import sys
import hashlib
import random
import math
import logging
from pathlib import Path
import xml.etree.ElementTree as ET

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import sumolib, but fallback to standard XML parsing if needed
try:
    if "SUMO_HOME" in os.environ:
        tools_path = os.path.join(os.environ["SUMO_HOME"], "tools")
        if tools_path not in sys.path:
            sys.path.append(tools_path)
    import sumolib
    HAS_SUMOLIB = True
except ImportError:
    HAS_SUMOLIB = False
    logger.warning("sumolib not found. Using standard xml.etree.ElementTree for route encryption.")

SECRET_SALT = "trikala-experiment-salt-2025"

def pseudo_encrypt_vid(vid: str) -> str:
    """Hash vehicle ID for pseudonymization"""
    if vid.startswith("bus"): # Don't encrypt public transport IDs usually, or do it consistently
        return vid
    h = hashlib.sha256(f"{SECRET_SALT}:{vid}".encode("utf-8")).hexdigest()
    return f"anon_{h[:8]}"

def laplace_noise(scale: float) -> float:
    """Generate Laplace noise"""
    u = random.random() - 0.5
    return -scale * (1 if u < 0 else -1) * math.log(1 - 2 * abs(u))

def encrypt_routes(input_file: str, output_file: str, noise_scale: float = 10.0):
    """
    Reads input_file, applies privacy transformations, writes to output_file.
    """
    logger.info(f"Encrypting routes from {input_file} to {output_file}")
    
    # Using ElementTree for robustness if sumolib is missing or for simple XML manipulation
    # (sumolib.xml.parse is great but sometimes overkill for simple attribute editing)
    try:
        tree = ET.parse(input_file)
        root = tree.getroot()
        
        count = 0
        for person in root.findall('person'):
            # 1. Pseudonymize ID
            original_id = person.get('id')
            person.set('id', pseudo_encrypt_vid(original_id))
            
            # 2. Add noise to depart time
            try:
                depart = float(person.get('depart'))
                # Add noise but ensure time doesn't go negative or violate logic too much
                # For persons, depart is when they appear.
                noisy_depart = max(0.0, depart + laplace_noise(noise_scale))
                person.set('depart', f"{noisy_depart:.2f}")
            except (ValueError, TypeError):
                pass
            
            count += 1
            
        # Also handle vehicles if any (though file is persons_merged.rou.xml)
        for vehicle in root.findall('vehicle'):
            original_id = vehicle.get('id')
            vehicle.set('id', pseudo_encrypt_vid(original_id))
            
            try:
                depart = float(vehicle.get('depart'))
                noisy_depart = max(0.0, depart + laplace_noise(noise_scale))
                vehicle.set('depart', f"{noisy_depart:.2f}")
            except (ValueError, TypeError):
                pass
            count += 1

        tree.write(output_file, encoding='UTF-8', xml_declaration=True)
        logger.info(f"Successfully encrypted {count} entities.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to encrypt routes: {e}")
        return False

if __name__ == "__main__":
    # Test run
    base_dir = Path("trikala_maas_project/routes")
    in_f = base_dir / "persons_merged.rou.xml"
    out_f = base_dir / "persons_encrypted.rou.xml"
    if in_f.exists():
        encrypt_routes(str(in_f), str(out_f))
