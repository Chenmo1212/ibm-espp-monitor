from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PricePoint:
    timestamp: datetime
    close_usd: Decimal

    def __post_init__(self):
        if self.close_usd <= Decimal("0"):
            raise ValueError(f"Price must be positive, got {self.close_usd}")


@dataclass
class MarketHistory:
    prices: list[PricePoint]


class MarketDataError(Exception):
    """Raised when market data retrieval or normalization fails."""
    pass


class MarketDataProvider(Protocol):
    def get_history(self, symbol: str, days: int) -> MarketHistory:
        ...

    def get_latest(self, symbol: str) -> PricePoint:
        ...


def normalize_history(history: MarketHistory) -> MarketHistory:
    if not history.prices:
        raise MarketDataError("No market history observations provided")

    # Map by date to deduplicate, keeping the latest timestamp for each calendar date
    by_date: dict[datetime.date, PricePoint] = {}
    # Sort chronologically first
    sorted_prices = sorted(history.prices, key=lambda p: p.timestamp)
    for p in sorted_prices:
        by_date[p.timestamp.date()] = p

    normalized_prices = [by_date[d] for d in sorted(by_date.keys())]
    return MarketHistory(prices=normalized_prices)


def get_normalized_history(
    provider: MarketDataProvider, symbol: str, days: int
) -> MarketHistory:
    # Always request at least 200 days if days < 200, as required by spec for 200d MA
    request_days = max(days, 200)
    history = provider.get_history(symbol, request_days)
    normalized = normalize_history(history)
    if not normalized.prices:
        raise MarketDataError(f"No usable market observations for symbol {symbol}")
    return normalized
