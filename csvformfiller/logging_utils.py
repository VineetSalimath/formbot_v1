from __future__ import annotations

import csv
import time
from pathlib import Path


LOG_FIELDS = ("id", "status", "message", "timestamp")


def successful_ids(path: str | Path) -> set[str]:
    path = Path(path)
    if not path.exists():
        return set()

    found: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("status") == "SUCCESS":
                found.add(row.get("id", ""))
    return found


def append_log(
    path: str | Path,
    row_id: str,
    status: str,
    message: str = "",
) -> None:
    path = Path(path)
    exists = path.exists()

    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "id": row_id,
                "status": status,
                "message": message,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
