"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.shared import UPSTREAM_DOCKERFILE_TEXT, load_filetypes, load_mapping


@pytest.fixture
def upstream_flags() -> set[str]:
    return set(load_mapping()["linters"])


@pytest.fixture
def filetypes() -> dict[str, Any]:
    return load_filetypes()


@pytest.fixture
def upstream_dockerfile(tmp_path: Path) -> Path:
    path = tmp_path / "Dockerfile.upstream"
    path.write_text(UPSTREAM_DOCKERFILE_TEXT)
    return path
