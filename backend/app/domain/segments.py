"""Quality segments, ordering, compatibility and quality upgrades.

Quality order is A > B > C > D. Rank 0 is the best quality.
"""

from __future__ import annotations

from enum import Enum


class Segment(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class AcceptanceMode(str, Enum):
    EXACT = "EXACT"
    MINIMUM = "MINIMUM"


# Best first. The index in this tuple is the quality rank.
SEGMENT_ORDER: tuple[Segment, ...] = (Segment.A, Segment.B, Segment.C, Segment.D)

SEGMENT_RANK: dict[Segment, int] = {segment: rank for rank, segment in enumerate(SEGMENT_ORDER)}


def rank(segment: Segment) -> int:
    """Quality rank. A is 0 (best), D is 3 (worst)."""
    return SEGMENT_RANK[segment]


def accepted_segments(mode: AcceptanceMode, requested: Segment) -> tuple[Segment, ...]:
    """Segments a client accepts, best quality first.

    EXACT X accepts X only. MINIMUM X accepts X or any better segment.
    """
    if mode is AcceptanceMode.EXACT:
        return (requested,)
    return tuple(segment for segment in SEGMENT_ORDER if rank(segment) <= rank(requested))


def accepts(mode: AcceptanceMode, requested: Segment, supplied: Segment) -> bool:
    """True when a supply segment may be sent to a client with this rule."""
    if mode is AcceptanceMode.EXACT:
        return supplied is requested
    return rank(supplied) <= rank(requested)


def quality_upgrade(requested: Segment, supplied: Segment) -> int:
    """How many quality levels better than requested the supply is. 0 means no upgrade."""
    return rank(requested) - rank(supplied)
