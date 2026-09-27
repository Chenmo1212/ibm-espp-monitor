from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence
from ibm_espp_monitor.market_data import MarketHistory


@dataclass(frozen=True)
class MarketMetrics:
    current_price_usd: Decimal
    percentile_180d: float
    high_180d_usd: Decimal
    distance_to_high: Decimal
    ma_50d_usd: Decimal
    ma_200d_usd: Decimal


def percentile_rank(values: Sequence[Decimal], current: Decimal) -> float:
    if not values:
        raise ValueError("At least one price is required")
    less_or_equal = sum(value <= current for value in values)
    return less_or_equal / len(values)


def moving_average(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("At least one price is required")
    return sum(values, Decimal("0")) / Decimal(len(values))


def calculate_market_metrics(
    history: MarketHistory, current_price_usd: Decimal
) -> MarketMetrics:
    if not history.prices:
        raise ValueError("Market history cannot be empty")

    all_prices = [p.close_usd for p in history.prices]

    # Lookback 180 observations for 180d percentile and high
    lookback_180 = all_prices[-180:] if len(all_prices) >= 180 else all_prices
    percentile_180d = percentile_rank(lookback_180, current_price_usd)
    high_180d_usd = max(max(lookback_180), current_price_usd)

    if high_180d_usd <= Decimal("0"):
        distance_to_high = Decimal("0")
    else:
        distance_to_high = (current_price_usd - high_180d_usd) / high_180d_usd

    # Moving averages use the latest 50 and 200 available observations
    obs_50 = all_prices[-50:]
    ma_50d_usd = moving_average(obs_50)

    obs_200 = all_prices[-200:]
    ma_200d_usd = moving_average(obs_200)

    return MarketMetrics(
        current_price_usd=current_price_usd,
        percentile_180d=percentile_180d,
        high_180d_usd=high_180d_usd,
        distance_to_high=distance_to_high,
        ma_50d_usd=ma_50d_usd,
        ma_200d_usd=ma_200d_usd,
    )
