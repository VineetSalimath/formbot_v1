from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PacingConfig:
    page_delay_min: float = 0.5
    page_delay_max: float = 1.5
    row_delay_min: float = 1.0
    row_delay_max: float = 3.0

    def validate(self) -> None:
        pairs = (
            ("page", self.page_delay_min, self.page_delay_max),
            ("row", self.row_delay_min, self.row_delay_max),
        )
        for label, minimum, maximum in pairs:
            if minimum < 0:
                raise ValueError(f"{label} delay minimum cannot be negative")
            if maximum < minimum:
                raise ValueError(
                    f"{label} delay maximum must be >= {label} delay minimum"
                )


@dataclass(frozen=True)
class FieldMapping:
    column: str
    question: str
    type: str
    separator: str = ";"


@dataclass(frozen=True)
class MatrixMapping:
    name: str
    question: str
    columns: tuple[str, ...]
    options: tuple[str, ...]


@dataclass(frozen=True)
class MappingConfig:
    fields: tuple[FieldMapping, ...] = field(default_factory=tuple)
    matrices: tuple[MatrixMapping, ...] = field(default_factory=tuple)

    @property
    def required_columns(self) -> set[str]:
        columns = {item.column for item in self.fields}
        for matrix in self.matrices:
            columns.update(matrix.columns)
        return columns


@dataclass
class FillResult:
    row_id: str
    status: str
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
