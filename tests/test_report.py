from datetime import date, datetime
from decimal import Decimal
from ibm_espp_monitor.metrics import MarketMetrics
from ibm_espp_monitor.portfolio import EsppLot
from ibm_espp_monitor.portfolio_metrics import LotMetric, PortfolioMetrics
from ibm_espp_monitor.report import render_report
from ibm_espp_monitor.signal import SellSignal


def make_sell_signal() -> SellSignal:
    m = MarketMetrics(
        current_price_usd=Decimal("275.00"),
        percentile_180d=0.90,
        high_180d_usd=Decimal("281.00"),
        distance_to_high=Decimal("-0.021"),
        ma_50d_usd=Decimal("250.00"),
        ma_200d_usd=Decimal("225.00"),
    )
    p = PortfolioMetrics(
        total_quantity=Decimal("52.52768"),
        weighted_average_cost_usd=Decimal("216.14"),
        market_value_usd=Decimal("14445.11"),
        cost_value_usd=Decimal("11353.33"),
        unrealised_gain_percent=0.272,
        profitable_lot_count=18,
        high_gain_lot_count=14,
    )
    lot = EsppLot(
        allocation_date=date(2026, 7, 23),
        instrument="Purchase Shares",
        contribution_type="Purchase",
        cost_basis_usd=Decimal("172.87"),
        quantity=Decimal("4.40712"),
        available_from=date(2026, 7, 23),
    )
    eligible_lots = [
        LotMetric(
            lot=lot,
            market_value_usd=Decimal("1211.96"),
            gain_percent=0.3045,
            profitable=True,
        )
    ]
    reasons = [
        "180-day price percentile is above configured threshold.",
        "Current price is within configured distance of the 180-day high.",
        "Current price is above the 50-day MA and the 50-day MA is above the 200-day MA.",
        "14 lots have at least 10% unrealised gain.",
    ]
    return SellSignal(
        status="SELL_WINDOW",
        reasons=reasons,
        market_metrics=m,
        portfolio_metrics=p,
        eligible_lots=eligible_lots,
    )


def test_report_contains_decision_relevant_metrics():
    report = render_report(make_sell_signal(), datetime(2026, 9, 27, 18, 0))

    assert "IBM SELL MONITOR" in report
    assert "180-day percentile" in report
    assert "Distance to 180-day high" in report
    assert "50-day MA" in report
    assert "200-day MA" in report
    assert "Not a price prediction" in report
    assert "Not a price prediction." in report
    assert "CGT" in report
    assert "CGT deadline reminder" in report
    assert "Consider selling in tranches" in report


def test_tax_deadline_december_vs_regular():
    from ibm_espp_monitor.report import get_tax_deadline_reminder

    oct_reminder = get_tax_deadline_reminder(datetime(2026, 10, 15))
    assert "15 Dec" in oct_reminder

    dec_reminder = get_tax_deadline_reminder(datetime(2026, 12, 10))
    assert "31 Jan 2027" in dec_reminder


def test_post_tax_gain_deducts_annual_allowance():
    from ibm_espp_monitor.config import MonitorConfig

    config = MonitorConfig(
        lookback_days=180,
        percentile_threshold=0.85,
        high_distance_threshold=0.05,
        min_gain_for_alert=0.10,
        cooldown_days=30,
        notification_enabled=True,
        currency="EUR",
        cgt_rate=0.33,
        cgt_annual_allowance_eur=1270.0,
        cgt_used_allowance_eur=0.0,
    )
    sig = make_sell_signal()
    # lot gain_eur is Decimal("1211.96") - cost ~ 4.40712*172.87/1.08...
    # Let's set an exact eligible lot with gain_eur = 2755.53
    lot = EsppLot(
        allocation_date=date(2026, 7, 23),
        instrument="Purchase Shares",
        contribution_type="Purchase",
        cost_basis_usd=Decimal("100.00"),
        quantity=Decimal("10.0"),
        available_from=date(2026, 7, 23),
    )
    # With gain_eur = Decimal("2755.53"), post_tax should be 1270 + (2755.53 - 1270) * 0.67 = 2265.3051 -> 2,265.31
    eligible_lots = [
        LotMetric(
            lot=lot,
            market_value_usd=Decimal("3000.00"),
            gain_percent=0.50,
            profitable=True,
            gain_eur=Decimal("2755.53"),
        )
    ]
    signal = SellSignal(
        status="SELL_WINDOW",
        reasons=[],
        market_metrics=sig.market_metrics,
        portfolio_metrics=sig.portfolio_metrics,
        eligible_lots=eligible_lots,
    )

    report = render_report(signal, datetime(2026, 9, 27, 18, 0), config)
    assert "Pre-tax €2,755.53 | Est. Post-tax €2,265.31" in report
    assert "Verify allowance against other disposals — maintained manually." in report
