import logging
import os
from datetime import datetime

def setup_logger(log_dir: str = "logs") -> logging.Logger:
    """Configure and return the application logger."""
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(
        log_dir,
        f"platform_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"   
    )

    logger = logging.getLogger("Scriptlatform")
    logger.setLevel(logging.DEBUG)

    # File Handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger