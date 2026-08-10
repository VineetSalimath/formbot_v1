from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import FieldMapping, MappingConfig, MatrixMapping


SUPPORTED_FIELD_TYPES = {"radio", "checkbox", "text"}


def _require_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def load_mapping(path: str | Path) -> MappingConfig:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    if not isinstance(raw, dict):
        raise ValueError("Mapping file must contain a YAML object")

    fields_raw = raw.get("fields", []) or []
    matrices_raw = raw.get("matrices", []) or []

    if not isinstance(fields_raw, list):
        raise ValueError("fields must be a YAML list")
    if not isinstance(matrices_raw, list):
        raise ValueError("matrices must be a YAML list")

    fields: list[FieldMapping] = []
    matrices: list[MatrixMapping] = []

    for index, item in enumerate(fields_raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"fields[{index}] must be an object")

        column = _require_string(item, "column", f"fields[{index}]")
        question = _require_string(item, "question", f"fields[{index}]")
        field_type = _require_string(item, "type", f"fields[{index}]").lower()

        if field_type not in SUPPORTED_FIELD_TYPES:
            raise ValueError(
                f"fields[{index}].type must be one of "
                f"{sorted(SUPPORTED_FIELD_TYPES)}"
            )

        separator = str(item.get("separator", ";"))
        fields.append(
            FieldMapping(
                column=column,
                question=question,
                type=field_type,
                separator=separator,
            )
        )

    for index, item in enumerate(matrices_raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"matrices[{index}] must be an object")

        name = str(item.get("name") or f"matrix_{index}")
        question = _require_string(item, "question", f"matrices[{index}]")

        columns = item.get("columns")
        options = item.get("options")

        if not isinstance(columns, list) or not columns or not all(
            isinstance(value, str) and value.strip() for value in columns
        ):
            raise ValueError(
                f"matrices[{index}].columns must be a non-empty list of strings"
            )

        if not isinstance(options, list) or not options or not all(
            isinstance(value, str) and value.strip() for value in options
        ):
            raise ValueError(
                f"matrices[{index}].options must be a non-empty list of strings"
            )

        matrices.append(
            MatrixMapping(
                name=name,
                question=question,
                columns=tuple(value.strip() for value in columns),
                options=tuple(value.strip() for value in options),
            )
        )

    config = MappingConfig(fields=tuple(fields), matrices=tuple(matrices))

    if not config.fields and not config.matrices:
        raise ValueError("Mapping file has no fields or matrices")

    return config
