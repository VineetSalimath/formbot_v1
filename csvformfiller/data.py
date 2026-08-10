from __future__ import annotations

import csv
from pathlib import Path

from .mapping import load_mapping
from .models import MappingConfig


def load_csv_rows(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row")
        rows = [
            {key: (value or "") for key, value in row.items()}
            for row in reader
        ]
        return list(reader.fieldnames), rows


def validate_columns(headers: list[str], mapping: MappingConfig) -> None:
    missing = sorted(mapping.required_columns - set(headers))
    if missing:
        raise ValueError(
            "CSV is missing mapped column(s): " + ", ".join(missing)
        )


def load_and_validate(
    csv_path: str | Path,
    mapping_path: str | Path,
) -> tuple[MappingConfig, list[dict[str, str]]]:
    mapping = load_mapping(mapping_path)
    headers, rows = load_csv_rows(csv_path)
    validate_columns(headers, mapping)
    return mapping, rows
