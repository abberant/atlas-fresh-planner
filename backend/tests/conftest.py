"""Shared test fixtures.

Invalid workbooks are built by copying the seed file to a temporary folder and
editing one cell, so no extra binary fixtures are committed.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable

import pytest
from openpyxl import load_workbook

from app.domain.models import SourceData
from app.ingest.validation import validate_workbook

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_WORKBOOK = REPO_ROOT / "data" / "Atlas_Fresh_Production_Commercial_Data.xlsx"


@pytest.fixture(scope="session")
def seed_path() -> Path:
    assert SEED_WORKBOOK.exists(), f"seed workbook not found at {SEED_WORKBOOK}"
    return SEED_WORKBOOK


@pytest.fixture(scope="session")
def seed_source(seed_path: Path) -> SourceData:
    source, issues = validate_workbook(seed_path)
    assert issues == [], f"the seed workbook must be valid, got {issues}"
    assert source is not None
    return source


EditFn = Callable[..., Path]


@pytest.fixture
def edited_workbook(seed_path: Path, tmp_path: Path) -> EditFn:
    """Copy the seed workbook and apply cell edits. Returns the new file path.

    Usage: edited_workbook(("Farms", "A6", "F01")) sets Farms!A6 to F01.
    """

    counter = {"n": 0}

    def _edit(*edits: tuple[str, str, Any], delete_sheet: str | None = None) -> Path:
        counter["n"] += 1
        target = tmp_path / f"edited_{counter['n']}.xlsx"
        shutil.copyfile(seed_path, target)
        workbook = load_workbook(target)
        if delete_sheet is not None:
            del workbook[delete_sheet]
        for sheet_name, cell, value in edits:
            workbook[sheet_name][cell] = value
        workbook.save(target)
        workbook.close()
        return target

    return _edit
