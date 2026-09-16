"""Plan endpoints. Source data and computed results are kept separate in the response."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.api.errors import DataUnavailable, WorkbookInvalid
from app.api.plan_store import StoredPlan, plan_store
from app.config import get_settings
from app.domain.models import (
    Client,
    Farm,
    PlanResult,
    ReferencePrice,
    SourceData,
    Station,
)
from app.ingest.validation import validate_workbook
from app.planning.engine import plan as build_plan

router = APIRouter(prefix="/api", tags=["plan"])


class SourcePayload(BaseModel):
    """The parsed input, unchanged. Kept apart from anything the engine computed."""

    farms: list[Farm]
    clients: list[Client]
    station: Station
    reference_prices: list[ReferencePrice]

    @classmethod
    def of(cls, source: SourceData) -> "SourcePayload":
        return cls(
            farms=source.farms,
            clients=source.clients,
            station=source.station,
            reference_prices=source.reference_prices,
        )


class PlanResponse(BaseModel):
    plan_id: str
    source: SourcePayload
    plan: PlanResult


def _plan_from_file(path: Path) -> StoredPlan:
    if not path.exists():
        raise DataUnavailable(
            f"The input workbook was not found at {path}. Check DATA_PATH in your environment."
        )

    source, issues = validate_workbook(path)
    if issues or source is None:
        raise WorkbookInvalid(issues)

    stored = StoredPlan(plan_id=source.fingerprint(), source=source, plan=build_plan(source))
    plan_store.put(stored)
    return stored


@router.post("/plan/seed", response_model=PlanResponse)
def plan_seed(response: Response) -> PlanResponse:
    """Load today's workbook from DATA_PATH, validate it and build the plan."""
    started = time.perf_counter()
    stored = _plan_from_file(get_settings().resolved_data_path)
    # Timing lives in a header, never inside the plan, so the plan stays deterministic.
    response.headers["X-Compute-Ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    return PlanResponse(
        plan_id=stored.plan_id,
        source=SourcePayload.of(stored.source),
        plan=stored.plan,
    )
