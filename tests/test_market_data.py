from datetime import datetime
from decimal import Decimal
import pytest
from ibm_espp_monitor.market_data import (
    MarketDataError,
    MarketDataProvider,
    MarketHistory,
    PricePoint,
    get_normalized_history,
    normalize_history,
)


class FakeProvider(MarketDataProvider):
    def __init__(self, history: MarketHistory, latest: PricePoint | None = None):
        self._history = history
        self._latest = latest or (history.prices[-1] if history.prices else PricePoint(datetime(2026, 1, 1), Decimal("100")))

    def get_history(self, symbol: str, days: int) -> MarketHistory:
        return self._history

    def get_latest(self, symbol: str) -> PricePoint:
        return self._latest


def test_normalized_history_is_sorted_and_duplicate_free():
    history = MarketHistory([
        PricePoint(datetime(2026, 9, 2), Decimal("230")),
        PricePoint(datetime(2026, 9, 1), Decimal("225")),
        PricePoint(datetime(2026, 9, 2, 12), Decimal("231")),
    ])

    normalized = normalize_history(history)

    assert [p.close_usd for p in normalized.prices] == [
        Decimal("225"),
        Decimal("231"),
    ]


def test_empty_provider_response_raises_market_data_error():
    provider = FakeProvider(history=MarketHistory([]))

    with pytest.raises(MarketDataError):
        get_normalized_history(provider, "IBM", 180)


def test_price_point_rejects_non_positive_values():
    with pytest.raises(ValueError, match="Price must be positive"):
        PricePoint(datetime(2026, 1, 1), Decimal("0"))

    with pytest.raises(ValueError, match="Price must be positive"):
        PricePoint(datetime(2026, 1, 1), Decimal("-10.5"))
