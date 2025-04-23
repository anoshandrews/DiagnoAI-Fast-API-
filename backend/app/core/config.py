import json
import os

working_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(working_dir, "../../config.json")

with open(config_path) as f:
    config = json.load(f)

GROQ_API_KEY = config["GROQ_API_KEY"]