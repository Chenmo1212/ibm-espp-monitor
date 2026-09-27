from datetime import datetime, timedelta
from decimal import Decimal
from ibm_espp_monitor.app import run_once
from ibm_espp_monitor.market_data import MarketDataProvider, MarketHistory, PricePoint
from ibm_espp_monitor.notifications import Notifier


class FakeMarketProvider(MarketDataProvider):
    def __init__(self, current: Decimal, history: MarketHistory):
        self._current = current
        self._history = history

    def get_history(self, symbol: str, days: int) -> MarketHistory:
        return self._history

    def get_latest(self, symbol: str) -> PricePoint:
        return PricePoint(timestamp=datetime(2026, 9, 27, 18, 0), close_usd=self._current)


class FakeNotifier(Notifier):
    def __init__(self):
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


def make_history_for_sell_window() -> MarketHistory:
    prices = [
        PricePoint(datetime(2026, 1, 1) + timedelta(days=i), Decimal(str(200 + i * 0.3)))
        for i in range(210)
    ]
    return MarketHistory(prices=prices)


def test_run_once_evaluates_portfolio_without_sending_trade(tmp_path):
    provider = FakeMarketProvider(
        current=Decimal("275"),
        history=make_history_for_sell_window(),
    )
    notifier = FakeNotifier()
    state_file = tmp_path / "state.json"

    signal = run_once(
        config_path="config/default.toml",
        lots_path="data/espp_lots.csv",
        state_path=state_file,
        market_provider=provider,
        notifier=notifier,
        now=datetime(2026, 9, 27, 18, 0),
    )

    assert signal.status == "SELL_WINDOW"
    assert len(notifier.messages) == 1
    assert "No trade was executed." in notifier.messages[0]
