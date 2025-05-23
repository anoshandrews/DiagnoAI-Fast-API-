"""should you do logging and error handling on the logging file, well I don't know,
let this be here for now"""

import logging
import os
from pathlib import Path

# Absolute path to the logs directory relative to this file's location
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

# Create a logger instance with a clear, unique name
logger = logging.getLogger("diagnoai")
logger.setLevel(logging.DEBUG)  # DEBUG for dev, INFO or WARNING for prod

# File handler writing logs to the absolute log file path
file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

# Console handler (optional, useful for development)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formatter applies to both handlers
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s", 
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers only if they aren’t already added (avoid duplicates)
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Prevent logs from propagating to the root logger (avoids double logging)
logger.propagate = False