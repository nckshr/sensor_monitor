import json
import os
import logging

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "port": 8432,
    "monitor_frequency_minutes": 5,
    "ntfy_topic": "ntfy.sh/default_sensing_alerts",
    "debug_mode": False
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        logging.warning(f"Configuration file {CONFIG_FILE} not found. Creating default.")
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
        
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Merge with defaults for missing keys
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception as e:
        logging.error(f"Error loading {CONFIG_FILE}: {e}")
        return DEFAULT_CONFIG

config_data = load_config()

PORT = config_data.get("port", 8432)
MONITOR_FREQUENCY_MINUTES = config_data.get("monitor_frequency_minutes", 5)
NTFY_TOPIC = config_data.get("ntfy_topic", "ntfy.sh/default_sensing_alerts")
DEBUG_MODE = config_data.get("debug_mode", False)

def update_config(key: str, value):
    global PORT, MONITOR_FREQUENCY_MINUTES, NTFY_TOPIC, DEBUG_MODE
    config = load_config()
    config[key] = value
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
        
    if key == "port": PORT = value
    elif key == "monitor_frequency_minutes": MONITOR_FREQUENCY_MINUTES = value
    elif key == "ntfy_topic": NTFY_TOPIC = value
    elif key == "debug_mode": DEBUG_MODE = value

