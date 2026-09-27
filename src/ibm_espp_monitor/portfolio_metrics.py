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
    gain_usd: Decimal = Decimal("0")
    gain_eur: Decimal = Decimal("0")
    post_tax_gain_eur: Decimal = Decimal("0")


@dataclass(frozen=True)
class PortfolioMetrics:
    total_quantity: Decimal
    weighted_average_cost_usd: Decimal
    market_value_usd: Decimal
    cost_value_usd: Decimal
    unrealised_gain_percent: float
    profitable_lot_count: int
    high_gain_lot_count: int
    market_value_eur: Decimal = Decimal("0")
    total_gain_usd: Decimal = Decimal("0")
    total_gain_eur: Decimal = Decimal("0")
    total_post_tax_gain_eur: Decimal = Decimal("0")


def calculate_lot_metrics(
    lots: Sequence[EsppLot],
    market_price_usd: Decimal,
    fx_eur_usd: float = 1.08,
    cgt_rate: float = 0.33,
) -> list[LotMetric]:
    fx_rate = Decimal(str(fx_eur_usd))
    tax_multiplier = Decimal(str(1.0 - cgt_rate))
    metrics: list[LotMetric] = []
    for lot in lots:
        market_val = lot.quantity * market_price_usd
        cost_val = lot.cost_value_usd
        gain_usd = market_val - cost_val
        gain_eur = gain_usd / fx_rate
        # For positive gains, tax applies; if gain <= 0, post_tax is gain
        if gain_eur > Decimal("0"):
            post_tax_gain_eur = gain_eur * tax_multiplier
        else:
            post_tax_gain_eur = gain_eur

        gain = float((market_price_usd - lot.cost_basis_usd) / lot.cost_basis_usd)
        metrics.append(
            LotMetric(
                lot=lot,
                market_value_usd=market_val,
                gain_usd=gain_usd,
                gain_eur=gain_eur,
                post_tax_gain_eur=post_tax_gain_eur,
                gain_percent=gain,
                profitable=gain > 0,
            )
        )
    return metrics


def calculate_portfolio_metrics(
    lot_metrics: Sequence[LotMetric],
    min_high_gain: float = 0.10,
    fx_eur_usd: float = 1.08,
    cgt_rate: float = 0.33,
    remaining_cgt_allowance_eur: float = 0.0,
) -> PortfolioMetrics:
    if not lot_metrics:
        raise ValueError("Cannot calculate portfolio metrics for empty lot list")

    lots = [m.lot for m in lot_metrics]
    tot_qty = total_quantity(lots)
    avg_cost = weighted_average_cost_basis(lots)

    cost_val = sum((lot.cost_value_usd for lot in lots), Decimal("0"))
    market_val = sum((m.market_value_usd for m in lot_metrics), Decimal("0"))
    fx_rate = Decimal(str(fx_eur_usd))
    market_val_eur = market_val / fx_rate

    total_gain_usd = market_val - cost_val
    total_gain_eur = total_gain_usd / fx_rate

    allowance_dec = Decimal(str(max(0.0, remaining_cgt_allowance_eur)))
    tax_multiplier = Decimal(str(1.0 - cgt_rate))
    if total_gain_eur > Decimal("0"):
        tax_free_portion = min(total_gain_eur, allowance_dec)
        taxable_gain = max(Decimal("0"), total_gain_eur - allowance_dec)
        total_post_tax_gain_eur = tax_free_portion + taxable_gain * tax_multiplier
    else:
        total_post_tax_gain_eur = total_gain_eur

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
        market_value_eur=market_val_eur,
        cost_value_usd=cost_val,
        total_gain_usd=total_gain_usd,
        total_gain_eur=total_gain_eur,
        total_post_tax_gain_eur=total_post_tax_gain_eur,
        unrealised_gain_percent=unrealised_gain,
        profitable_lot_count=profitable_count,
        high_gain_lot_count=high_gain_count,
    )
