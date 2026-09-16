"""A small in memory store of the last computed plans, keyed by plan_id.

The product is stateless: this is only a short lived cache so the assistant can
explain a plan the user is looking at without recomputing or re-uploading it.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from app.domain.models import PlanResult, SourceData

MAX_ENTRIES = 8


@dataclass(frozen=True)
class StoredPlan:
    plan_id: str
    source: SourceData
    plan: PlanResult


class PlanStore:
    def __init__(self, max_entries: int = MAX_ENTRIES) -> None:
        self._max_entries = max_entries
        self._items: OrderedDict[str, StoredPlan] = OrderedDict()

    def put(self, stored: StoredPlan) -> None:
        self._items[stored.plan_id] = stored
        self._items.move_to_end(stored.plan_id)
        while len(self._items) > self._max_entries:
            self._items.popitem(last=False)

    def get(self, plan_id: str) -> StoredPlan | None:
        stored = self._items.get(plan_id)
        if stored is not None:
            self._items.move_to_end(plan_id)
        return stored

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


plan_store = PlanStore()
