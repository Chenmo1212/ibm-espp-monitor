from datetime import date
from decimal import Decimal
from ibm_espp_monitor.config import MonitorConfig
from ibm_espp_monitor.metrics import MarketMetrics
from ibm_espp_monitor.portfolio import EsppLot
from ibm_espp_monitor.portfolio_metrics import LotMetric, PortfolioMetrics
from ibm_espp_monitor.signal import evaluate_sell_window


def default_config() -> MonitorConfig:
    return MonitorConfig(
        lookback_days=180,
        percentile_threshold=0.85,
        high_distance_threshold=0.05,
        min_gain_for_alert=0.10,
        cooldown_days=30,
        notification_enabled=True,
        currency="EUR",
    )


def make_market_metrics(
    percentile_180d: float = 0.90,
    distance_to_high: Decimal = Decimal("-0.02"),
    current_price: Decimal = Decimal("275"),
    ma_50: Decimal = Decimal("250"),
    ma_200: Decimal = Decimal("225"),
    high_180d: Decimal = Decimal("280"),
) -> MarketMetrics:
    return MarketMetrics(
        current_price_usd=current_price,
        percentile_180d=percentile_180d,
        high_180d_usd=high_180d,
        distance_to_high=distance_to_high,
        ma_50d_usd=ma_50,
        ma_200d_usd=ma_200,
    )


def make_portfolio_metrics(
    unrealised_gain: float = 0.20,
    total_quantity: Decimal = Decimal("50"),
    weighted_average_cost: Decimal = Decimal("210"),
) -> PortfolioMetrics:
    return PortfolioMetrics(
        total_quantity=total_quantity,
        weighted_average_cost_usd=weighted_average_cost,
        market_value_usd=Decimal("13000"),
        cost_value_usd=Decimal("10500"),
        unrealised_gain_percent=unrealised_gain,
        profitable_lot_count=3,
        high_gain_lot_count=2,
    )


def make_lot_metrics(profits: list[float]) -> list[LotMetric]:
    metrics: list[LotMetric] = []
    for i, p in enumerate(profits):
        lot = EsppLot(
            allocation_date=date(2026, 1, i + 1),
            instrument="Purchase Shares",
            contribution_type="Purchase",
            cost_basis_usd=Decimal("200"),
            quantity=Decimal("5"),
            available_from=date(2026, 1, i + 1),
        )
        metrics.append(
            LotMetric(
                lot=lot,
                market_value_usd=Decimal("1000") * (Decimal("1") + Decimal(str(p))),
                gain_percent=p,
                profitable=p > 0,
            )
        )
    return metrics


def test_sell_window_requires_high_market_position_and_profitable_lots():
    market = make_market_metrics(
        percentile_180d=0.90,
        distance_to_high=Decimal("-0.02"),
        current_price=Decimal("275"),
        ma_50=Decimal("250"),
        ma_200=Decimal("225"),
    )
    portfolio = make_portfolio_metrics(unrealised_gain=0.20)
    lots = make_lot_metrics(profits=[0.25, 0.35, 0.08])

    signal = evaluate_sell_window(market, portfolio, lots, default_config())

    assert signal.status == "SELL_WINDOW"
    assert any("180-day price percentile" in reason for reason in signal.reasons)
    assert len(signal.eligible_lots) == 2


def test_low_price_does_not_trigger_sell_window():
    market = make_market_metrics(
        percentile_180d=0.45,
        distance_to_high=Decimal("-0.30"),
        current_price=Decimal("220"),
        ma_50=Decimal("240"),
        ma_200=Decimal("230"),
    )
    portfolio = make_portfolio_metrics(unrealised_gain=0.03)
    lots = make_lot_metrics(profits=[0.05, 0.08])

    signal = evaluate_sell_window(market, portfolio, lots, default_config())

    assert signal.status == "HOLD"


def test_exact_85th_percentile_is_eligible():
    market = make_market_metrics(percentile_180d=0.85, distance_to_high=Decimal("-0.05"))
    portfolio = make_portfolio_metrics(unrealised_gain=0.10)
    lots = make_lot_metrics(profits=[0.10])

    signal = evaluate_sell_window(market, portfolio, lots, default_config())

    assert signal.status == "SELL_WINDOW"
