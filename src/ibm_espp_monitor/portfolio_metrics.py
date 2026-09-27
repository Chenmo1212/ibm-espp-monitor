from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from ibm_espp_monitor.portfolio import EsppLot, total_quantity, weighted_average_cost_basis


@dataclass(frozen=True)
class LotMetric:
    lot: EsppLot
    market_value_usd: Decimal
    gain_percent: float
    profitable: bool


@dataclass(frozen=True)
class PortfolioMetrics:
    total_quantity: Decimal
    weighted_average_cost_usd: Decimal
    market_value_usd: Decimal
    cost_value_usd: Decimal
    unrealised_gain_percent: float
    profitable_lot_count: int
    high_gain_lot_count: int


def calculate_lot_metrics(
    lots: Sequence[EsppLot], market_price_usd: Decimal
) -> list[LotMetric]:
    metrics: list[LotMetric] = []
    for lot in lots:
        market_val = lot.quantity * market_price_usd
        gain = float((market_price_usd - lot.cost_basis_usd) / lot.cost_basis_usd)
        metrics.append(
            LotMetric(
                lot=lot,
                market_value_usd=market_val,
                gain_percent=gain,
                profitable=gain > 0,
            )
        )
    return metrics


def calculate_portfolio_metrics(
    lot_metrics: Sequence[LotMetric], min_high_gain: float = 0.10
) -> PortfolioMetrics:
    if not lot_metrics:
        raise ValueError("Cannot calculate portfolio metrics for empty lot list")

    lots = [m.lot for m in lot_metrics]
    tot_qty = total_quantity(lots)
    avg_cost = weighted_average_cost_basis(lots)

    cost_val = sum((lot.cost_value_usd for lot in lots), Decimal("0"))
    market_val = sum((m.market_value_usd for m in lot_metrics), Decimal("0"))

    if cost_val <= Decimal("0"):
        unrealised_gain = 0.0
    else:
        unrealised_gain = float((market_val - cost_val) / cost_val)

    profitable_count = sum(1 for m in lot_metrics if m.profitable)
    high_gain_count = sum(1 for m in lot_metrics if m.gain_percent >= min_high_gain)

    return PortfolioMetrics(
        total_quantity=tot_qty,
        weighted_average_cost_usd=avg_cost,
        market_value_usd=market_val,
        cost_value_usd=cost_val,
        unrealised_gain_percent=unrealised_gain,
        profitable_lot_count=profitable_count,
        high_gain_lot_count=high_gain_count,
    )
