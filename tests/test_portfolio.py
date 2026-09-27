from datetime import date
from decimal import Decimal
import pytest
from ibm_espp_monitor.portfolio import (
    EsppLot,
    load_lots,
    lot_gain,
    total_quantity,
    weighted_average_cost_basis,
)


def test_load_lots_preserves_purchase_and_dividend_shares():
    lots = load_lots("data/espp_lots.csv")

    assert len(lots) == 20
    assert lots[0].allocation_date == date(2025, 7, 23)
    assert lots[0].cost_basis_usd == Decimal("242.0500")
    assert lots[0].quantity == Decimal("2.93769")
    assert any(
        l.contribution_type == "Purchase" and l.instrument == "Dividend Shares"
        for l in lots
    )


def test_total_quantity_matches_imported_records():
    lots = load_lots("data/espp_lots.csv")

    assert total_quantity(lots) == Decimal("52.52768")


def test_weighted_average_cost_basis_is_quantity_weighted():
    lots = load_lots("data/espp_lots.csv")

    assert weighted_average_cost_basis(lots).quantize(Decimal("0.01")) == Decimal(
        "216.14"
    )


def test_lot_gain_uses_market_price_against_cost_basis():
    lot = EsppLot(
        allocation_date=date(2026, 7, 23),
        instrument="Purchase Shares",
        contribution_type="Purchase",
        cost_basis_usd=Decimal("172.8700"),
        quantity=Decimal("4.40712"),
        available_from=date(2026, 7, 23),
    )

    assert lot_gain(lot, Decimal("225.51")).quantize(Decimal("0.0001")) == Decimal(
        "0.3045"
    )


def test_empty_lots_raise_value_error_for_average_cost():
    with pytest.raises(ValueError, match="Cannot calculate average cost"):
        weighted_average_cost_basis([])


def test_lot_gain_raises_for_invalid_cost_basis():
    lot = EsppLot(
        allocation_date=date(2026, 7, 23),
        instrument="Purchase Shares",
        contribution_type="Purchase",
        cost_basis_usd=Decimal("0"),
        quantity=Decimal("4.40712"),
        available_from=date(2026, 7, 23),
    )
    with pytest.raises(ValueError, match="Cost basis must be positive"):
        lot_gain(lot, Decimal("225.51"))
