import json
import os

def load_config():
    # Determine the absolute path to the config file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "config.json")
    
    # Load and return the JSON configuration
    with open(config_path, "r") as f:
        return json.load(f)

# Load the configuration once at module import
CONFIG = load_config()