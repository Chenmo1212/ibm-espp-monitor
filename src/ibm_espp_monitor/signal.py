from dataclasses import dataclass
from typing import Sequence
from ibm_espp_monitor.config import MonitorConfig
from ibm_espp_monitor.metrics import MarketMetrics
from ibm_espp_monitor.portfolio_metrics import LotMetric, PortfolioMetrics


@dataclass(frozen=True)
class SellSignal:
    status: str  # "HOLD", "WATCH", or "SELL_WINDOW"
    reasons: list[str]
    market_metrics: MarketMetrics
    portfolio_metrics: PortfolioMetrics
    eligible_lots: list[LotMetric]
    is_concentration_breached: bool = False
    concentration_reason: str = ""


def evaluate_sell_window(
    market: MarketMetrics,
    portfolio: PortfolioMetrics,
    lot_metrics: Sequence[LotMetric],
    config: MonitorConfig,
) -> SellSignal:
    market_high = (
        market.percentile_180d >= config.percentile_threshold
        and market.distance_to_high >= -config.high_distance_threshold
    )

    trend_positive = (
        market.current_price_usd >= market.ma_50d_usd
        and market.ma_50d_usd >= market.ma_200d_usd
    )

    eligible_lots = [
        metric for metric in lot_metrics
        if metric.gain_percent >= config.min_gain_for_alert
    ]

    reasons: list[str] = []
    reasons.append(f"180-day price percentile: {market.percentile_180d * 100:.1f}% (threshold: {config.percentile_threshold * 100:.1f}%)")
    reasons.append(f"Distance from 180-day high: {market.distance_to_high * 100:.1f}% (threshold: -{config.high_distance_threshold * 100:.1f}%)")
    reasons.append(f"Current price >= 50-day MA: {'yes' if market.current_price_usd >= market.ma_50d_usd else 'no'} (${market.current_price_usd:.2f} vs ${market.ma_50d_usd:.2f})")
    reasons.append(f"50-day MA >= 200-day MA: {'yes' if market.ma_50d_usd >= market.ma_200d_usd else 'no'} (${market.ma_50d_usd:.2f} vs ${market.ma_200d_usd:.2f})")
    reasons.append(f"Lots with >= {config.min_gain_for_alert * 100:.0f}% gain: {len(eligible_lots)}/{len(lot_metrics)}")

    # Check concentration threshold in EUR
    is_concentration_breached = False
    concentration_reason = ""
    if config.max_position_value_eur > 0:
        total_eur = float(portfolio.market_value_eur)
        if total_eur > config.max_position_value_eur:
            is_concentration_breached = True
            concentration_reason = (
                f"Position value €{total_eur:,.2f} exceeds threshold €{config.max_position_value_eur:,.2f}"
            )

    if market_high and trend_positive and eligible_lots:
        status = "SELL_WINDOW"
    elif market_high or trend_positive:
        status = "WATCH"
    else:
        status = "HOLD"

    return SellSignal(
        status=status,
        reasons=reasons,
        market_metrics=market,
        portfolio_metrics=portfolio,
        eligible_lots=eligible_lots,
        is_concentration_breached=is_concentration_breached,
        concentration_reason=concentration_reason,
    )
