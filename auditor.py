import json
import sys
import threading
from datetime import datetime, timezone

from models import AuditWriteError, ConfigurationError

SCHEMA_VERSION = "0.4"


class Auditor:
    def __init__(self, path: str) -> None:
        try:
            self._file = open(path, "a", encoding="utf-8")
        except OSError as e:
            raise ConfigurationError(f"Cannot open audit log at {path!r}: {e}") from e
        self._lock = threading.Lock()
        self._closed = False

    def log(self, event: str, data: dict) -> None:
        if not event:
            raise ValueError("event must be non-empty")
        if not isinstance(data, dict):
            raise ValueError("data must be a dict")
        if self._closed:
            return
        record = {
            "event": event,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "schema_version": SCHEMA_VERSION,
            **data,
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with self._lock:
            try:
                self._file.write(line)
                self._file.flush()
            except OSError as e:
                raise AuditWriteError(f"Failed to write audit record: {e}") from e

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._file.flush()
            self._file.close()
        except OSError:
            pass

    def __enter__(self) -> "Auditor":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Auditor(closed={self._closed})"
