import logging
import logging.handlers
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"
MAX_BYTES = 5 * 1024 * 1024   # 5 MB per log file
BACKUP_COUNT = 3               # Keep 3 rotated files


def get_logger(name: str = "trading_bot") -> logging.Logger:
    """
    Returns a configured logger instance.

    Idempotent: calling this multiple times with the same name returns
    the same logger without adding duplicate handlers.
    """
    logger = logging.getLogger(name)

    # Guard: do not add handlers if they already exist
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # --- File handler: DEBUG and above, structured format ---
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # --- Console handler: WARNING and above, concise format ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
