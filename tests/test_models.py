import pytest

from csvformfiller.models import PacingConfig


def test_pacing_validation_accepts_valid_range():
    PacingConfig(0, 1, 2, 3).validate()


def test_pacing_validation_rejects_reversed_range():
    with pytest.raises(ValueError):
        PacingConfig(2, 1, 2, 3).validate()
