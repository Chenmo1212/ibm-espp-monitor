from datetime import date, datetime
from decimal import Decimal
from ibm_espp_monitor.metrics import MarketMetrics
from ibm_espp_monitor.notifications import Notifier, should_notify
from ibm_espp_monitor.portfolio_metrics import PortfolioMetrics
from ibm_espp_monitor.signal import SellSignal
from ibm_espp_monitor.state import NotificationState


class FakeNotifier(Notifier):
    def __init__(self):
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


def make_sell_signal(status: str = "SELL_WINDOW") -> SellSignal:
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
    return SellSignal(
        status=status,
        reasons=["Test reason"],
        market_metrics=m,
        portfolio_metrics=p,
        eligible_lots=[],
    )


def test_sell_window_is_not_repeated_within_cooldown():
    signal = make_sell_signal(status="SELL_WINDOW")
    state = NotificationState(last_sell_window_alert=datetime(2026, 9, 20))

    assert (
        should_notify(
            signal,
            state,
            datetime(2026, 9, 27),
            cooldown_days=30,
        )
        is False
    )


def test_sell_window_is_notified_after_cooldown():
    signal = make_sell_signal(status="SELL_WINDOW")
    state = NotificationState(last_sell_window_alert=datetime(2026, 8, 1))

    assert (
        should_notify(
            signal,
            state,
            datetime(2026, 9, 27),
            cooldown_days=30,
        )
        is True
    )


def test_fake_notifier_receives_rendered_report():
    notifier = FakeNotifier()

    notifier.send("IBM SELL MONITOR\nSignal: SELL_WINDOW")

    assert notifier.messages == ["IBM SELL MONITOR\nSignal: SELL_WINDOW"]
