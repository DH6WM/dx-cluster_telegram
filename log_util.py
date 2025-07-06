# log_util.py
import csv
import os
from datetime import datetime

LOG_DIR = "log"
os.makedirs(LOG_DIR, exist_ok=True)

DX_HEADERS = [
    "timestamp", 
    "frequency_khz", 
    "band", 
    "mode", 
    "de_call", 
    "dx_call", 
    "comment"
]

MESSAGE_HEADERS = ["timestamp", "level", "message"]
ERROR_HEADERS = ["timestamp", "exception_type", "exception_msg", "details"]

def get_timestamp():
    return datetime.utcnow().isoformat(timespec="seconds")

def get_date_str():
    return datetime.utcnow().strftime("%Y-%m-%d")

def get_dx_logfile_path():
    """Pfad zur tagesbezogenen DX-Logdatei."""
    return os.path.join(LOG_DIR, f"dx_log_{get_date_str()}.csv")

def get_message_logfile_path():
    """Pfad zur tagesbezogenen messages-Logdatei."""
    return os.path.join(LOG_DIR, f"messages_{get_date_str()}.csv")

def get_error_logfile_path():
    """Pfad zur zentralen Fehlerdatei."""
    return os.path.join(LOG_DIR, "error_log.csv")

def init_file_if_missing(filepath, headers):
    """Legt Datei mit Header an, falls sie noch nicht existiert."""
    if not os.path.exists(filepath):
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

def log_dx_spot(frequency_khz, band, mode, de_call, dx_call, comment):
    """Schreibt einen DX-Spot in die Tagesdatei."""
    path = get_dx_logfile_path()
    init_file_if_missing(path, DX_HEADERS)
    with open(path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            get_timestamp(),
            frequency_khz,
            band,
            mode,
            de_call,
            dx_call,
            comment
        ])

def log_message(message: str, level: str = "INFO"):
    """Schreibt eine Nachricht in die tagesbezogene messages-Logdatei."""
    path = get_message_logfile_path()
    init_file_if_missing(path, MESSAGE_HEADERS)
    with open(path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            get_timestamp(),
            level.upper(),
            message
        ])
    # print(f"[{level.upper()}] {message}")

def log_error(exc_or_msg, context: str = ""):
    """
    Protokolliert einen Fehler in error_log.csv.
    Unterstützt entweder ein Exception-Objekt oder einen reinen Fehlertext.
    """
    path = get_error_logfile_path()
    init_file_if_missing(path, ERROR_HEADERS)

    if isinstance(exc_or_msg, Exception):
        exc_type = type(exc_or_msg).__name__
        exc_msg = str(exc_or_msg)
    else:
        exc_type = "ManualError"
        exc_msg = str(exc_or_msg)

    with open(path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            get_timestamp(),
            exc_type,
            exc_msg,
            context
        ])
    # print(f"[ERROR] {exc_type}: {exc_msg}")
