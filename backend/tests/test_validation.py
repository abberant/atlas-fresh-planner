"""Validation rejects bad input, names the problem and never plans."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingest.validation import validate_workbook

# Each case: label, cell edits, expected code, expected sheet, expected entity id.
CASES = [
    ("duplicate farm id", [("Farms", "A6", "F01")], "ID_DUPLICATE", "Farms", "F01"),
    ("missing farm id", [("Farms", "A9", None)], "ID_MISSING", "Farms", None),
    ("missing client id", [("Clients", "A7", None)], "ID_MISSING", "Clients", None),
    ("invalid acceptance mode", [("Clients", "C6", "MAYBE")], "MODE_INVALID", "Clients", "C02"),
    ("invalid requested segment", [("Clients", "D8", "E")], "SEGMENT_INVALID", "Clients", "C04"),
    (
        "mix sum 0.9",
        [("Farms", "D11", 0.0)],  # F07 expected_A_pct 0.1 -> 0.0, mix sums to 0.9
        "MIX_SUM_INVALID",
        "Farms",
        "F07",
    ),
    ("mix fraction 1.2", [("Farms", "D5", 1.2)], "MIX_OUT_OF_RANGE", "Farms", "F01"),
    ("negative actual tonnes", [("Farms", "H5", -25)], "QUANTITY_NEGATIVE", "Farms", "F01"),
    ("actual not a 5 t step", [("Farms", "H5", 12)], "QUANTITY_NOT_5T_STEP", "Farms", "F01"),
    ("demand not a 5 t step", [("Clients", "E5", 52)], "QUANTITY_NOT_5T_STEP", "Clients", "C01"),
    ("client price zero", [("Clients", "F5", 0)], "PRICE_INVALID", "Clients", "C01"),
    ("client price text", [("Clients", "F5", "free")], "PRICE_INVALID", "Clients", "C01"),
    ("actual tonnes text", [("Farms", "H5", "twenty")], "VALUE_NOT_NUMBER", "Farms", "F01"),
    ("capacity zero", [("Station", "B5", 0)], "CAPACITY_INVALID", "Station", "STATION-01"),
    ("capacity negative", [("Station", "B5", -500)], "CAPACITY_INVALID", "Station", "STATION-01"),
    ("ratio above one", [("Station", "C5", 1.5)], "RATIO_INVALID", "Station", "STATION-01"),
    ("reference price for C missing", [("Station", "A19", None)], "REFERENCE_PRICE_MISSING", "Station", "C"),
    ("reference price duplicated", [("Station", "A19", "B")], "REFERENCE_PRICE_DUPLICATE", "Station", "B"),
    ("reference price zero", [("Station", "B20", 0)], "PRICE_INVALID", "Station", "D"),
    ("farm capacity with two decimals", [("Farms", "C5", 35.25)], "CAPACITY_DECIMALS", "Farms", "F01"),
    ("farm capacity negative", [("Farms", "C5", -35)], "QUANTITY_NEGATIVE", "Farms", "F01"),
    ("missing farm column", [("Farms", "H4", "actual_alpha_t")], "COLUMN_MISSING", "Farms", None),
    ("empty client name", [("Clients", "B5", None)], "NAME_MISSING", "Clients", "C01"),
]


@pytest.mark.parametrize(
    "label,edits,code,sheet,entity_id",
    CASES,
    ids=[case[0] for case in CASES],
)
def test_invalid_input_is_rejected(
    edited_workbook, label: str, edits, code: str, sheet: str, entity_id: str | None
) -> None:
    path = edited_workbook(*edits)
    source, issues = validate_workbook(path)

    assert source is None, f"{label}: planning must not run on invalid input"
    matching = [issue for issue in issues if issue.code == code]
    assert matching, f"{label}: expected code {code}, got {[i.code for i in issues]}"

    issue = matching[0]
    assert issue.sheet == sheet
    if entity_id is not None:
        assert entity_id in {i.entity_id for i in matching}, f"{label}: entity id {entity_id} not reported"
    assert issue.message.strip(), f"{label}: the message must not be empty"
    assert sheet in issue.message, f"{label}: the message must name the sheet"


def test_seed_workbook_is_valid(seed_path: Path) -> None:
    source, issues = validate_workbook(seed_path)
    assert issues == []
    assert source is not None
    assert len(source.farms) == 20
    assert len(source.clients) == 10
    assert len(source.reference_prices) == 4


def test_missing_sheet_is_reported(edited_workbook) -> None:
    path = edited_workbook(delete_sheet="Clients")
    source, issues = validate_workbook(path)
    assert source is None
    codes = {issue.code for issue in issues}
    assert "SHEET_MISSING" in codes
    assert any(issue.sheet == "Clients" for issue in issues)


def test_all_problems_are_reported_in_one_pass(edited_workbook) -> None:
    """Three unrelated problems in one file come back together, not one by one."""
    path = edited_workbook(
        ("Farms", "A6", "F01"),  # duplicate farm id
        ("Clients", "C6", "MAYBE"),  # invalid mode
        ("Station", "B5", 0),  # invalid capacity
    )
    source, issues = validate_workbook(path)
    assert source is None
    codes = {issue.code for issue in issues}
    assert {"ID_DUPLICATE", "MODE_INVALID", "CAPACITY_INVALID"} <= codes


def test_unreadable_file_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "not-a-workbook.xlsx"
    path.write_bytes(b"this is not an excel file")
    source, issues = validate_workbook(path)
    assert source is None
    assert [issue.code for issue in issues] == ["FILE_UNREADABLE"]
