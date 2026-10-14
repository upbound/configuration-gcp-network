"""Make the generated models importable during tests.

`up project build` generates them into .up/python, a `crossplane-models` distribution exposing
the top-level `models` package, and installs it into the function's environment at build time.
Tests run outside that environment, so the generated tree goes on sys.path directly.
"""

import sys
from pathlib import Path

import pytest

_MODELS = Path(__file__).resolve().parents[3] / ".up" / "python"

if not _MODELS.is_dir():
    # Raised at conftest import, before collection fails with a far less useful
    # ModuleNotFoundError.
    raise pytest.UsageError(
        f"generated models not found at {_MODELS}\n"
        "The unit tests build real provider model objects, so generate them first with:\n\n"
        "    up project build\n"
    )

sys.path.insert(0, str(_MODELS))
