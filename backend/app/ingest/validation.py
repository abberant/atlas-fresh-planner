"""Validate the workbook. Every problem is reported, nothing is repaired.

All errors of one run are collected in a single pass so the user can fix the file
once instead of discovering problems one by one. If there is at least one error,
no plan is produced.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, BinaryIO, Sequence

from app.domain.models import (
    Client,
    Farm,
    ReferencePrice,
    SourceData,
    Station,
    ValidationIssue,
)
from app.domain.segments import AcceptanceMode, Segment
from app.ingest.workbook_reader import (
    RawRow,
    RawTable,
    WorkbookReadError,
    find_table,
    read_sheets,
)

FARM_SHEET = "Farms"
CLIENT_SHEET = "Clients"
STATION_SHEET = "Station"

MIX_SUM_TOLERANCE = Decimal("0.000001")
STEP_T = Decimal(5)

# acceptance_mode and requested_segment are written exactly like this or rejected.
MODE_VALUES: tuple[str, ...] = tuple(mode.value for mode in AcceptanceMode)
SEGMENT_VALUES: tuple[str, ...] = tuple(segment.value for segment in Segment)
MODE_ALLOWED = " or ".join(MODE_VALUES)
SEGMENT_ALLOWED = ", ".join(SEGMENT_VALUES[:-1]) + " or " + SEGMENT_VALUES[-1]

FARM_HEADERS: tuple[str, ...] = (
    "farm_id",
    "farm_name",
    "expected_daily_capacity_t",
    "expected_a_pct",
    "expected_b_pct",
    "expected_c_pct",
    "expected_d_pct",
    "actual_a_t",
    "actual_b_t",
    "actual_c_t",
    "actual_d_t",
)
CLIENT_HEADERS: tuple[str, ...] = (
    "client_id",
    "client_name",
    "acceptance_mode",
    "requested_segment",
    "demand_t",
    "export_price_per_t_eur",
)
STATION_HEADERS: tuple[str, ...] = (
    "station_id",
    "export_conditioning_capacity_t",
    "local_market_ratio",
)
PRICE_HEADERS: tuple[str, ...] = ("segment", "reference_export_price_per_t_eur")

MIX_HEADER: dict[Segment, str] = {segment: f"expected_{segment.value.lower()}_pct" for segment in Segment}
ACTUAL_HEADER: dict[Segment, str] = {segment: f"actual_{segment.value.lower()}_t" for segment in Segment}


class _Issues:
    """Small collector so every check reads the same way."""

    def __init__(self) -> None:
        self.items: list[ValidationIssue] = []

    def add(
        self,
        code: str,
        sheet: str,
        message: str,
        row: int | None = None,
        entity_id: str | None = None,
        field: str | None = None,
    ) -> None:
        self.items.append(
            ValidationIssue(
                code=code,
                sheet=sheet,
                row=row,
                entity_id=entity_id,
                field=field,
                message=message,
            )
        )

    def __len__(self) -> int:
        return len(self.items)


def _where(sheet: str, row: int | None, label: str | None, entity_id: str | None) -> str:
    parts = [sheet]
    if row is not None:
        parts.append(f"row {row}")
    if entity_id and label:
        parts.append(f"{label} {entity_id}")
    return ", ".join(parts)


def _fmt(value: Decimal, min_decimals: int = 0) -> str:
    """Readable number for error messages, without scientific notation."""
    try:
        shown = value.quantize(Decimal("0.000001")).normalize()
    except InvalidOperation:  # very large numbers cannot be quantized
        shown = value
    text = format(shown, "f")
    if "." in text:
        whole, fraction = text.split(".")
    else:
        whole, fraction = text, ""
    if len(fraction) < min_decimals:
        fraction = fraction.ljust(min_decimals, "0")
    return f"{whole}.{fraction}" if fraction else whole


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _found(value: Any) -> str:
    """How a rejected cell value is shown back to the user."""
    if value is None or (isinstance(value, str) and value == ""):
        return "empty"
    return repr(value)


def _exact_choice(value: Any, allowed: tuple[str, ...]) -> str | None:
    """Strict match. Spaces and letter case are never corrected, only rejected."""
    return value if isinstance(value, str) and value in allowed else None


def _to_decimal(value: Any) -> Decimal | None:
    """Numbers only. Text, blanks and booleans are rejected, never converted."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    return None


def _decimal_places(value: Decimal) -> int:
    exponent = value.normalize().as_tuple().exponent
    return max(0, -int(exponent)) if isinstance(exponent, int) else 0


def _is_5t_step(value: Decimal) -> bool:
    return value == value.to_integral_value() and value % STEP_T == 0


def _number(
    issues: _Issues,
    raw: Any,
    *,
    sheet: str,
    row: int | None,
    field: str,
    entity_label: str | None,
    entity_id: str | None,
    what: str,
) -> Decimal | None:
    value = _to_decimal(raw)
    if value is None:
        issues.add(
            "VALUE_NOT_NUMBER",
            sheet,
            f"{_where(sheet, row, entity_label, entity_id)}: {what} must be a number. "
            f"Found {'an empty cell' if raw is None or str(raw).strip() == '' else repr(raw)}.",
            row=row,
            entity_id=entity_id,
            field=field,
        )
    return value


# --------------------------------------------------------------------------- farms


def _validate_farms(table: RawTable, issues: _Issues) -> list[Farm]:
    farms: list[Farm] = []
    seen: dict[str, int] = {}

    for raw_row in table.rows:
        row = raw_row.number
        farm_id = _text(raw_row.get("farm_id"))
        ok = True

        if farm_id is None:
            issues.add(
                "ID_MISSING",
                FARM_SHEET,
                f"{FARM_SHEET}, row {row}: farm_id is empty. Every farm needs an identifier.",
                row=row,
                field="farm_id",
            )
            ok = False
        elif farm_id in seen:
            issues.add(
                "ID_DUPLICATE",
                FARM_SHEET,
                f"{FARM_SHEET}, row {row}, farm {farm_id}: this farm_id is already used on "
                f"row {seen[farm_id]}. Farm identifiers must be unique.",
                row=row,
                entity_id=farm_id,
                field="farm_id",
            )
            ok = False
        else:
            seen[farm_id] = row

        farm_name = _text(raw_row.get("farm_name"))
        if farm_name is None:
            issues.add(
                "NAME_MISSING",
                FARM_SHEET,
                f"{_where(FARM_SHEET, row, 'farm', farm_id)}: farm_name is empty. Give the farm a name.",
                row=row,
                entity_id=farm_id,
                field="farm_name",
            )
            ok = False

        capacity = _number(
            issues,
            raw_row.get("expected_daily_capacity_t"),
            sheet=FARM_SHEET,
            row=row,
            field="expected_daily_capacity_t",
            entity_label="farm",
            entity_id=farm_id,
            what="expected daily capacity",
        )
        if capacity is None:
            ok = False
        else:
            if capacity < 0:
                issues.add(
                    "QUANTITY_NEGATIVE",
                    FARM_SHEET,
                    f"{_where(FARM_SHEET, row, 'farm', farm_id)}: expected daily capacity is "
                    f"{_fmt(capacity)} t. It cannot be negative.",
                    row=row,
                    entity_id=farm_id,
                    field="expected_daily_capacity_t",
                )
                ok = False
            if _decimal_places(capacity) > 1:
                issues.add(
                    "CAPACITY_DECIMALS",
                    FARM_SHEET,
                    f"{_where(FARM_SHEET, row, 'farm', farm_id)}: expected daily capacity is "
                    f"{_fmt(capacity)} t. Use at most one decimal.",
                    row=row,
                    entity_id=farm_id,
                    field="expected_daily_capacity_t",
                )
                ok = False

        mix: dict[Segment, Decimal] = {}
        mix_in_range = True
        for segment in Segment:
            header = MIX_HEADER[segment]
            value = _number(
                issues,
                raw_row.get(header),
                sheet=FARM_SHEET,
                row=row,
                field=header,
                entity_label="farm",
                entity_id=farm_id,
                what=f"expected {segment.value} share",
            )
            if value is None:
                ok = False
                mix_in_range = False
                continue
            if value < 0 or value > 1:
                issues.add(
                    "MIX_OUT_OF_RANGE",
                    FARM_SHEET,
                    f"{_where(FARM_SHEET, row, 'farm', farm_id)}: expected {segment.value} share is "
                    f"{_fmt(value)}. Each share must be between 0 and 1.",
                    row=row,
                    entity_id=farm_id,
                    field=header,
                )
                ok = False
                mix_in_range = False
            mix[segment] = value

        if len(mix) == len(Segment) and mix_in_range:
            total = sum(mix.values(), Decimal(0))
            if abs(total - 1) > MIX_SUM_TOLERANCE:
                issues.add(
                    "MIX_SUM_INVALID",
                    FARM_SHEET,
                    f"{_where(FARM_SHEET, row, 'farm', farm_id)}: expected mix adds up to "
                    f"{_fmt(total, min_decimals=2)}. It must add up to 1.0.",
                    row=row,
                    entity_id=farm_id,
                    field="expected_*_pct",
                )
                ok = False

        actual: dict[Segment, int] = {}
        for segment in Segment:
            header = ACTUAL_HEADER[segment]
            value = _number(
                issues,
                raw_row.get(header),
                sheet=FARM_SHEET,
                row=row,
                field=header,
                entity_label="farm",
                entity_id=farm_id,
                what=f"actual Segment {segment.value} tonnes",
            )
            if value is None:
                ok = False
                continue
            if value < 0:
                issues.add(
                    "QUANTITY_NEGATIVE",
                    FARM_SHEET,
                    f"{_where(FARM_SHEET, row, 'farm', farm_id)}: actual Segment {segment.value} is "
                    f"{_fmt(value)} t. Tonnes cannot be negative.",
                    row=row,
                    entity_id=farm_id,
                    field=header,
                )
                ok = False
                continue
            if not _is_5t_step(value):
                issues.add(
                    "QUANTITY_NOT_5T_STEP",
                    FARM_SHEET,
                    f"{_where(FARM_SHEET, row, 'farm', farm_id)}: actual Segment {segment.value} is "
                    f"{_fmt(value)} t. Tonnes must be a whole multiple of 5.",
                    row=row,
                    entity_id=farm_id,
                    field=header,
                )
                ok = False
                continue
            actual[segment] = int(value)

        if ok and farm_id is not None and farm_name is not None and capacity is not None:
            farms.append(
                Farm(
                    farm_id=farm_id,
                    farm_name=farm_name,
                    row=row,
                    expected_daily_capacity_t=capacity,
                    expected_mix=mix,
                    actual_t=actual,
                )
            )

    if not table.rows and table.header_row is not None:
        issues.add(
            "NO_DATA_ROWS",
            FARM_SHEET,
            f"{FARM_SHEET}: no farm rows found below the header row. At least one farm is required.",
            row=table.header_row,
        )
    return farms


# ------------------------------------------------------------------------- clients


def _validate_clients(table: RawTable, issues: _Issues) -> list[Client]:
    clients: list[Client] = []
    seen: dict[str, int] = {}

    for raw_row in table.rows:
        row = raw_row.number
        client_id = _text(raw_row.get("client_id"))
        ok = True

        if client_id is None:
            issues.add(
                "ID_MISSING",
                CLIENT_SHEET,
                f"{CLIENT_SHEET}, row {row}: client_id is empty. Every client needs an identifier.",
                row=row,
                field="client_id",
            )
            ok = False
        elif client_id in seen:
            issues.add(
                "ID_DUPLICATE",
                CLIENT_SHEET,
                f"{CLIENT_SHEET}, row {row}, client {client_id}: this client_id is already used on "
                f"row {seen[client_id]}. Client identifiers must be unique.",
                row=row,
                entity_id=client_id,
                field="client_id",
            )
            ok = False
        else:
            seen[client_id] = row

        client_name = _text(raw_row.get("client_name"))
        if client_name is None:
            issues.add(
                "NAME_MISSING",
                CLIENT_SHEET,
                f"{_where(CLIENT_SHEET, row, 'client', client_id)}: client_name is empty. "
                "Give the client a name.",
                row=row,
                entity_id=client_id,
                field="client_name",
            )
            ok = False

        raw_mode = raw_row.get("acceptance_mode")
        mode: AcceptanceMode | None = None
        if _exact_choice(raw_mode, MODE_VALUES) is not None:
            mode = AcceptanceMode(raw_mode)
        else:
            issues.add(
                "MODE_INVALID",
                CLIENT_SHEET,
                f"{_where(CLIENT_SHEET, row, 'client', client_id)}: acceptance_mode is "
                f"{_found(raw_mode)}. Allowed values are {MODE_ALLOWED}, written exactly like "
                "that, in capital letters and with no extra spaces.",
                row=row,
                entity_id=client_id,
                field="acceptance_mode",
            )
            ok = False

        raw_segment = raw_row.get("requested_segment")
        segment: Segment | None = None
        if _exact_choice(raw_segment, SEGMENT_VALUES) is not None:
            segment = Segment(raw_segment)
        else:
            issues.add(
                "SEGMENT_INVALID",
                CLIENT_SHEET,
                f"{_where(CLIENT_SHEET, row, 'client', client_id)}: requested_segment is "
                f"{_found(raw_segment)}. Allowed values are {SEGMENT_ALLOWED}, written exactly "
                "like that, in capital letters and with no extra spaces.",
                row=row,
                entity_id=client_id,
                field="requested_segment",
            )
            ok = False

        demand = _number(
            issues,
            raw_row.get("demand_t"),
            sheet=CLIENT_SHEET,
            row=row,
            field="demand_t",
            entity_label="client",
            entity_id=client_id,
            what="demand",
        )
        if demand is None:
            ok = False
        elif demand < 0:
            issues.add(
                "QUANTITY_NEGATIVE",
                CLIENT_SHEET,
                f"{_where(CLIENT_SHEET, row, 'client', client_id)}: demand is {_fmt(demand)} t. "
                "It cannot be negative.",
                row=row,
                entity_id=client_id,
                field="demand_t",
            )
            ok = False
        elif not _is_5t_step(demand):
            issues.add(
                "QUANTITY_NOT_5T_STEP",
                CLIENT_SHEET,
                f"{_where(CLIENT_SHEET, row, 'client', client_id)}: demand is {_fmt(demand)} t. "
                "Demand must be a whole multiple of 5.",
                row=row,
                entity_id=client_id,
                field="demand_t",
            )
            ok = False

        price = _to_decimal(raw_row.get("export_price_per_t_eur"))
        if price is None:
            issues.add(
                "PRICE_INVALID",
                CLIENT_SHEET,
                f"{_where(CLIENT_SHEET, row, 'client', client_id)}: export price is missing or is "
                "not a number. The price must be greater than 0.",
                row=row,
                entity_id=client_id,
                field="export_price_per_t_eur",
            )
            ok = False
        elif price <= 0:
            issues.add(
                "PRICE_INVALID",
                CLIENT_SHEET,
                f"{_where(CLIENT_SHEET, row, 'client', client_id)}: export price is "
                f"{_fmt(price)} EUR per t. The price must be greater than 0.",
                row=row,
                entity_id=client_id,
                field="export_price_per_t_eur",
            )
            ok = False

        if ok and client_id and client_name and mode and segment and demand is not None and price is not None:
            clients.append(
                Client(
                    client_id=client_id,
                    client_name=client_name,
                    row=row,
                    acceptance_mode=mode,
                    requested_segment=segment,
                    demand_t=int(demand),
                    export_price_per_t_eur=price,
                )
            )

    if not table.rows and table.header_row is not None:
        issues.add(
            "NO_DATA_ROWS",
            CLIENT_SHEET,
            f"{CLIENT_SHEET}: no client rows found below the header row. At least one client is required.",
            row=table.header_row,
        )
    return clients


# ------------------------------------------------------------------------- station


def _validate_station(table: RawTable, issues: _Issues) -> Station | None:
    if not table.rows:
        issues.add(
            "CAPACITY_INVALID",
            STATION_SHEET,
            f"{STATION_SHEET}: no station row found. One row with station_id, "
            "export_conditioning_capacity_t and local_market_ratio is required.",
            row=table.header_row,
            field="export_conditioning_capacity_t",
        )
        return None

    if len(table.rows) > 1:
        issues.add(
            "STATION_ROW_COUNT_INVALID",
            STATION_SHEET,
            f"{STATION_SHEET}: {len(table.rows)} station rows found. This product plans one "
            "station, so exactly one row is expected.",
            row=table.rows[1].number,
        )
        return None

    raw_row: RawRow = table.rows[0]
    row = raw_row.number
    station_id = _text(raw_row.get("station_id"))
    ok = True

    if station_id is None:
        issues.add(
            "ID_MISSING",
            STATION_SHEET,
            f"{STATION_SHEET}, row {row}: station_id is empty. The station needs an identifier.",
            row=row,
            field="station_id",
        )
        ok = False

    capacity = _to_decimal(raw_row.get("export_conditioning_capacity_t"))
    if capacity is None:
        issues.add(
            "CAPACITY_INVALID",
            STATION_SHEET,
            f"{_where(STATION_SHEET, row, 'station', station_id)}: export conditioning capacity "
            "is missing or is not a number. It must be a positive multiple of 5.",
            row=row,
            entity_id=station_id,
            field="export_conditioning_capacity_t",
        )
        ok = False
    elif capacity <= 0:
        issues.add(
            "CAPACITY_INVALID",
            STATION_SHEET,
            f"{_where(STATION_SHEET, row, 'station', station_id)}: export conditioning capacity is "
            f"{_fmt(capacity)} t. It must be greater than 0.",
            row=row,
            entity_id=station_id,
            field="export_conditioning_capacity_t",
        )
        ok = False
    elif not _is_5t_step(capacity):
        issues.add(
            "QUANTITY_NOT_5T_STEP",
            STATION_SHEET,
            f"{_where(STATION_SHEET, row, 'station', station_id)}: export conditioning capacity is "
            f"{_fmt(capacity)} t. It must be a whole multiple of 5.",
            row=row,
            entity_id=station_id,
            field="export_conditioning_capacity_t",
        )
        ok = False

    ratio = _to_decimal(raw_row.get("local_market_ratio"))
    if ratio is None:
        issues.add(
            "RATIO_INVALID",
            STATION_SHEET,
            f"{_where(STATION_SHEET, row, 'station', station_id)}: local_market_ratio is missing or "
            "is not a number. It must be between 0 and 1.",
            row=row,
            entity_id=station_id,
            field="local_market_ratio",
        )
        ok = False
    elif ratio < 0 or ratio > 1:
        issues.add(
            "RATIO_INVALID",
            STATION_SHEET,
            f"{_where(STATION_SHEET, row, 'station', station_id)}: local_market_ratio is "
            f"{_fmt(ratio)}. It must be between 0 and 1.",
            row=row,
            entity_id=station_id,
            field="local_market_ratio",
        )
        ok = False

    if ok and station_id and capacity is not None and ratio is not None:
        return Station(
            station_id=station_id,
            export_conditioning_capacity_t=int(capacity),
            local_market_ratio=ratio,
        )
    return None


def _validate_reference_prices(table: RawTable, issues: _Issues) -> list[ReferencePrice]:
    found: dict[Segment, ReferencePrice] = {}
    first_row: dict[Segment, int] = {}

    for raw_row in table.rows:
        row = raw_row.number
        raw_segment = raw_row.get("segment")
        if _exact_choice(raw_segment, SEGMENT_VALUES) is None:
            issues.add(
                "SEGMENT_INVALID",
                STATION_SHEET,
                f"{STATION_SHEET}, row {row}: reference price segment is {_found(raw_segment)}. "
                f"Allowed values are {SEGMENT_ALLOWED}, written exactly like that, in capital "
                "letters and with no extra spaces.",
                row=row,
                entity_id=_text(raw_segment),
                field="segment",
            )
            continue
        segment = Segment(raw_segment)

        if segment in found or segment in first_row:
            issues.add(
                "REFERENCE_PRICE_DUPLICATE",
                STATION_SHEET,
                f"{STATION_SHEET}, row {row}: Segment {segment.value} already has a reference price "
                f"on row {first_row[segment]}. Each segment must appear once.",
                row=row,
                entity_id=segment.value,
                field="segment",
            )
            continue
        first_row[segment] = row

        price = _to_decimal(raw_row.get("reference_export_price_per_t_eur"))
        if price is None:
            issues.add(
                "PRICE_INVALID",
                STATION_SHEET,
                f"{STATION_SHEET}, row {row}, Segment {segment.value}: reference export price is "
                "missing or is not a number. It must be greater than 0.",
                row=row,
                entity_id=segment.value,
                field="reference_export_price_per_t_eur",
            )
            continue
        if price <= 0:
            issues.add(
                "PRICE_INVALID",
                STATION_SHEET,
                f"{STATION_SHEET}, row {row}, Segment {segment.value}: reference export price is "
                f"{_fmt(price)} EUR per t. It must be greater than 0.",
                row=row,
                entity_id=segment.value,
                field="reference_export_price_per_t_eur",
            )
            continue

        found[segment] = ReferencePrice(segment=segment, reference_export_price_per_t_eur=price)

    for segment in Segment:
        if segment not in first_row:
            issues.add(
                "REFERENCE_PRICE_MISSING",
                STATION_SHEET,
                f"{STATION_SHEET}: no reference export price for Segment {segment.value}. "
                "Segments A, B, C and D are all required.",
                row=table.header_row,
                entity_id=segment.value,
                field="segment",
            )

    return [found[segment] for segment in Segment if segment in found]


# ------------------------------------------------------------------------ pipeline


def _resolve_sheet(sheets: dict[str, list[list[Any]]], wanted: str) -> list[list[Any]] | None:
    for name, rows in sheets.items():
        if name.strip().lower() == wanted.lower():
            return rows
    return None


def _report_missing_columns(table: RawTable, issues: _Issues, table_label: str) -> None:
    for header in table.missing_headers:
        where = f"{table.sheet}"
        if table.header_row is not None:
            where += f", header row {table.header_row}"
        issues.add(
            "COLUMN_MISSING",
            table.sheet,
            f"{where}: the {table_label} table has no column named {header!r}. Add it.",
            row=table.header_row,
            field=header,
        )


def validate_sheets(sheets: dict[str, list[list[Any]]]) -> tuple[SourceData | None, list[ValidationIssue]]:
    """Validate already loaded sheets. Returns (source, []) or (None, issues)."""
    issues = _Issues()

    farm_rows = _resolve_sheet(sheets, FARM_SHEET)
    client_rows = _resolve_sheet(sheets, CLIENT_SHEET)
    station_rows = _resolve_sheet(sheets, STATION_SHEET)

    for name, rows in ((FARM_SHEET, farm_rows), (CLIENT_SHEET, client_rows), (STATION_SHEET, station_rows)):
        if rows is None:
            issues.add(
                "SHEET_MISSING",
                name,
                f"The workbook has no sheet named {name!r}. Sheets Farms, Clients and Station are required.",
            )

    farms: list[Farm] = []
    clients: list[Client] = []
    station: Station | None = None
    prices: list[ReferencePrice] = []

    if farm_rows is not None:
        table = find_table(FARM_SHEET, farm_rows, FARM_HEADERS)
        _report_missing_columns(table, issues, "farms")
        if not table.missing_headers:
            farms = _validate_farms(table, issues)

    if client_rows is not None:
        table = find_table(CLIENT_SHEET, client_rows, CLIENT_HEADERS)
        _report_missing_columns(table, issues, "clients")
        if not table.missing_headers:
            clients = _validate_clients(table, issues)

    if station_rows is not None:
        station_table = find_table(STATION_SHEET, station_rows, STATION_HEADERS)
        _report_missing_columns(station_table, issues, "station")
        if not station_table.missing_headers:
            station = _validate_station(station_table, issues)

        price_table = find_table(STATION_SHEET, station_rows, PRICE_HEADERS)
        _report_missing_columns(price_table, issues, "reference price")
        if not price_table.missing_headers:
            prices = _validate_reference_prices(price_table, issues)

    if len(issues) or station is None or len(prices) != len(Segment):
        if not len(issues):  # defensive, should not happen
            issues.add(
                "SERVER_ERROR",
                STATION_SHEET,
                "The workbook could not be validated. Please check the Station sheet.",
            )
        return None, issues.items

    return (
        SourceData(farms=farms, clients=clients, station=station, reference_prices=prices),
        [],
    )


def validate_workbook(source: str | Path | BinaryIO) -> tuple[SourceData | None, list[ValidationIssue]]:
    """Read and validate a workbook file. Returns (source, []) or (None, issues)."""
    try:
        sheets = read_sheets(source)
    except WorkbookReadError as exc:
        return None, [
            ValidationIssue(
                code="FILE_UNREADABLE",
                sheet="(file)",
                message=f"The file could not be opened as an Excel .xlsx workbook. Details: {exc}",
            )
        ]
    return validate_sheets(sheets)


def issues_as_dicts(issues: Sequence[ValidationIssue]) -> list[dict[str, Any]]:
    return [issue.model_dump() for issue in issues]
