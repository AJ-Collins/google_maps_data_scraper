# ─────────────────────────────────────────────
#  utils/logger.py  –  Logging setup
# ─────────────────────────────────────────────

import logging
import sys
from config import LOG_PATH


def get_logger(name: str = "leadgen") -> logging.Logger:
    """Return a configured logger that writes to both console and file."""
    logger = logging.getLogger(name)

    if logger.handlers:          # avoid duplicate handlers on re-import
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s  [%(levelname)-8s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger