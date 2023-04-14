"""Logger configuration."""
import logging.config
from pathlib import Path

import yaml

from app.constants import LOGGING_CONFIG, LOGGING_LEVEL


def _read_config_file() -> dict:
    path = Path(LOGGING_CONFIG)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _configure() -> logging.Logger:
    """Configure logging."""
    logging_config_dict = _read_config_file()
    logging.config.dictConfig(logging_config_dict)
    logger = logging.getLogger(__name__).parent
    assert logger is not None
    if LOGGING_LEVEL:
        logger.setLevel(LOGGING_LEVEL)
    return logger


L = _configure()
