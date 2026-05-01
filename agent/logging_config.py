import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")

class JSONLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class ColourFormatter(logging.Formatter):
    """Coloured console output — no third-party libs required."""

    RESET = "\x1b[0m"
    COLOURS = {
        logging.DEBUG: "\x1b[38;5;240m",     # grey
        logging.INFO: "\x1b[38;5;75m",        # sky blue
        logging.WARNING: "\x1b[38;5;214m",    # amber
        logging.ERROR: "\x1b[38;5;196m",      # red
        logging.CRITICAL: "\x1b[1;38;5;196m", # bold red
    }
    LEVEL_LABELS = {
        logging.DEBUG: "DBG",
        logging.INFO: "INF",
        logging.WARNING: "WRN",
        logging.ERROR: "ERR",
        logging.CRITICAL: "CRT",
    }

    def format(self, record: logging.LogRecord) -> str:
        colour = self.COLOURS.get(record.levelno, "")
        label = self.LEVEL_LABELS.get(record.levelno, record.levelname)
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        return f"{colour}{ts} [{label}] {record.getMessage()}{self.RESET}"


def setup_logging(log_file: str = "trading_bot.log", verbose: bool = False) -> None:
    """
    Call once at startup. Configures:
      - File handler  - logs/<log_file>  (DEBUG, JSON-lines)
      - Console handler - stderr  (INFO if verbose else WARNING, coloured)
    """
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / log_file

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(JSONLineFormatter())

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.DEBUG if verbose else logging.WARNING)
    ch.setFormatter(ColourFormatter())

    root.addHandler(fh)
    root.addHandler(ch)

    logging.getLogger("httpx").setLevel(logging.WARNING)  # suppress httpx noise
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.getLogger("trading_bot").info(
        "Logging initialised | file=%s verbose=%s", log_path, verbose
    )
