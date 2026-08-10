from pathlib import Path

import pytest

from csvformfiller.data import load_csv_rows, validate_columns
from csvformfiller.mapping import load_mapping


ROOT = Path(__file__).resolve().parents[1]


def test_example_mapping_loads():
    mapping = load_mapping(ROOT / "examples" / "mapping.example.yaml")
    assert len(mapping.fields) == 5
    assert len(mapping.matrices) == 1
    assert "country" in mapping.required_columns
    assert "habit_4" in mapping.required_columns


def test_example_csv_matches_mapping():
    mapping = load_mapping(ROOT / "examples" / "mapping.example.yaml")
    headers, rows = load_csv_rows(ROOT / "examples" / "responses.csv")
    validate_columns(headers, mapping)
    assert len(rows) == 2


def test_missing_column_is_rejected(tmp_path):
    mapping = load_mapping(ROOT / "examples" / "mapping.example.yaml")
    with pytest.raises(ValueError, match="missing mapped column"):
        validate_columns(["age"], mapping)
