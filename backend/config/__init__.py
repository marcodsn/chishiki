import os
import json

default_config = {
    "redis": {
        "host": "postgres",
        "port": 5432,
    },
    "backend": {
        "host": "0.0.0.0",
        "port": 7710,
        "debug": False,
    },
    "windows": [128, 256, 512],
    "extensions": [".pdf", ".txt"],
    "ml_services": {
        "use_bge": True,
        "bge_unload_interval": 300,
        "use_nougat": True,
        "nougat_unload_interval": 300,
    }
}

class Config:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                return json.load(file)
        else:
            with open(self.config_file, 'w') as file:
                json.dump(default_config, file, indent=4)
            return default_config

# Initialize the global configuration
config_file = os.path.join(os.path.dirname(__file__), 'config.json')
config = Config(config_file)
