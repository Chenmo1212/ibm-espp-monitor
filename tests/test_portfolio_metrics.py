from datetime import date
from decimal import Decimal
import pytest
from ibm_espp_monitor.portfolio import EsppLot, load_lots
from ibm_espp_monitor.portfolio_metrics import (
    calculate_lot_metrics,
    calculate_portfolio_metrics,
)


def make_lot(
    allocation_date: date = date(2026, 7, 23),
    instrument: str = "Purchase Shares",
    contribution_type: str = "Purchase",
    cost_basis_usd: Decimal = Decimal("172.8700"),
    quantity: Decimal = Decimal("4.40712"),
    available_from: date = date(2026, 7, 23),
) -> EsppLot:
    return EsppLot(
        allocation_date=allocation_date,
        instrument=instrument,
        contribution_type=contribution_type,
        cost_basis_usd=cost_basis_usd,
        quantity=quantity,
        available_from=available_from,
    )


def test_july_2026_lot_has_about_30_percent_gain_at_225_51():
    lot = make_lot(
        allocation_date=date(2026, 7, 23),
        cost_basis_usd=Decimal("172.8700"),
        quantity=Decimal("4.40712"),
    )

    metric = calculate_lot_metrics([lot], Decimal("225.51"))[0]

    assert metric.gain_percent == pytest.approx(0.3045, abs=0.0001)
    assert metric.profitable is True


def test_portfolio_metrics_use_all_lots():
    lots = load_lots("data/espp_lots.csv")
    metrics = calculate_portfolio_metrics(
        calculate_lot_metrics(lots, Decimal("225.51"))
    )

    assert metrics.total_quantity == Decimal("52.52768")
    assert metrics.weighted_average_cost_usd.quantize(Decimal("0.01")) == Decimal("216.14")
    assert metrics.profitable_lot_count > 0
