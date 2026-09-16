"""Clients are served by price, highest first, ties broken by client_id."""

from __future__ import annotations

from app.planning.engine import client_processing_order, plan
from builders import make_client, make_farm, make_source, rows_as_tuples


def test_higher_price_is_served_first() -> None:
    source = make_source(
        farms=[make_farm("F01", {"A": 30})],
        clients=[
            make_client("C01", "EXACT", "A", 30, 900),
            make_client("C02", "EXACT", "A", 30, 1200),
        ],
    )
    result = plan(source)

    assert [client.client_id for client in result.clients] == ["C02", "C01"]
    assert rows_as_tuples(result.allocations) == [("F01", "A", "C02", 30)]
    by_id = {client.client_id: client for client in result.clients}
    assert by_id["C02"].status.value == "COMPLETE"
    assert by_id["C01"].status.value == "UNSERVED"


def test_equal_price_tie_is_broken_by_client_id() -> None:
    """Scarce supply goes to the smaller client_id when prices are equal."""
    source = make_source(
        farms=[make_farm("F01", {"B": 20})],
        clients=[
            make_client("C07", "EXACT", "B", 20, 1000),
            make_client("C03", "EXACT", "B", 20, 1000),
        ],
    )
    result = plan(source)

    assert [client.client_id for client in result.clients] == ["C03", "C07"]
    assert rows_as_tuples(result.allocations) == [("F01", "B", "C03", 20)]


def test_processing_order_does_not_depend_on_input_order() -> None:
    clients = [
        make_client("C05", "EXACT", "A", 10, 800),
        make_client("C01", "EXACT", "A", 10, 1500),
        make_client("C09", "EXACT", "A", 10, 800),
        make_client("C02", "EXACT", "A", 10, 1200),
    ]
    forward = [client.client_id for client in client_processing_order(clients)]
    backward = [client.client_id for client in client_processing_order(list(reversed(clients)))]

    assert forward == ["C01", "C02", "C05", "C09"]
    assert forward == backward


def test_reference_prices_do_not_change_client_order() -> None:
    """Reference prices value the local market only. They never reorder clients."""
    from decimal import Decimal

    from app.domain.segments import Segment

    farms = [make_farm("F01", {"A": 10, "D": 10})]
    clients = [
        make_client("C01", "EXACT", "D", 10, 2000),
        make_client("C02", "EXACT", "A", 10, 1000),
    ]
    normal = plan(make_source(farms, clients))
    flipped = plan(
        make_source(
            farms,
            clients,
            reference_prices={
                Segment.A: Decimal(10),
                Segment.B: Decimal(20),
                Segment.C: Decimal(30),
                Segment.D: Decimal(9000),
            },
        )
    )

    assert [client.client_id for client in normal.clients] == ["C01", "C02"]
    assert [client.client_id for client in flipped.clients] == ["C01", "C02"]
    assert normal.kpis.export_revenue_eur == flipped.kpis.export_revenue_eur
