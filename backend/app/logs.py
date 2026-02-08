import json
import os
from datetime import datetime

LOG_FILE = "app/output/logs.json"
os.makedirs("app/output", exist_ok=True)

def save_prevention(photo_path, counts):
    log = {
        "type": "prevention",
        "photo": photo_path,
        "counts": counts,
        "timestamp": datetime.now().isoformat()
    }
    _save_log(log)

def save_incident(photo_path, description):
    log = {
        "type": "incident",
        "photo": photo_path,
        "description": description,
        "timestamp": datetime.now().isoformat()
    }
    _save_log(log)

def _save_log(log):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    else:
        logs = []
    logs.append(log)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)
