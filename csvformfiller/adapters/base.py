from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import MappingConfig


class FormAdapter(ABC):
    @abstractmethod
    def inspect_visible_page(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fill_visible_page(
        self,
        row: dict[str, str],
        mapping: MappingConfig,
        completed_keys: set[str],
    ) -> set[str]:
        raise NotImplementedError

    @abstractmethod
    def has_next(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def click_next(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def has_submit(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def click_submit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def wait_for_submission_confirmation(self, timeout: int = 45) -> None:
        raise NotImplementedError
