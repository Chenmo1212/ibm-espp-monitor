from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from ibm_espp_monitor.market_data import MarketHistory, PricePoint
from ibm_espp_monitor.metrics import calculate_market_metrics, moving_average, percentile_rank


def test_percentile_is_high_when_current_price_is_near_recent_high():
    history = MarketHistory([
        PricePoint(datetime(2026, 1, 1) + timedelta(days=i), Decimal(str(100 + i)))
        for i in range(180)
    ])

    metrics = calculate_market_metrics(history, Decimal("279"))

    assert metrics.percentile_180d > 0.85
    assert metrics.high_180d_usd == Decimal("279")


def test_moving_averages_use_latest_observations():
    history = MarketHistory(
        [PricePoint(datetime(2026, 1, 1) + timedelta(days=i), Decimal("100")) for i in range(200)]
    )

    metrics = calculate_market_metrics(history, Decimal("110"))

    assert metrics.ma_50d_usd == Decimal("100")
    assert metrics.ma_200d_usd == Decimal("100")


def test_distance_to_high_is_zero_at_high():
    history = MarketHistory([
        PricePoint(datetime(2026, 1, 1) + timedelta(days=i), Decimal(str(100 + i)))
        for i in range(200)
    ])

    metrics = calculate_market_metrics(history, Decimal("299"))

    assert metrics.distance_to_high == Decimal("0")


def test_empty_history_raises_value_error():
    with pytest.raises(ValueError, match="Market history cannot be empty"):
        calculate_market_metrics(MarketHistory([]), Decimal("100"))
