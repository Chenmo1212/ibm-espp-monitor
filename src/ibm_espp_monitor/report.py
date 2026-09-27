from datetime import datetime
from ibm_espp_monitor.signal import SellSignal


def render_report(signal: SellSignal, as_of: datetime) -> str:
    m = signal.market_metrics
    p = signal.portfolio_metrics

    lines: list[str] = []
    lines.append("IBM SELL MONITOR")
    lines.append(f"As of: {as_of.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("Market")
    lines.append(f"Current price: ${m.current_price_usd:.2f}")
    lines.append(f"180-day percentile: {m.percentile_180d * 100:.1f}%")
    lines.append(f"180-day high: ${m.high_180d_usd:.2f}")
    lines.append(f"Distance to 180-day high: {m.distance_to_high * 100:.1f}%")
    lines.append(f"50-day MA: ${m.ma_50d_usd:.2f}")
    lines.append(f"200-day MA: ${m.ma_200d_usd:.2f}")
    lines.append("")
    lines.append("Portfolio")
    lines.append(f"Shares: {p.total_quantity}")
    lines.append(f"Weighted average cost: ${p.weighted_average_cost_usd:.2f}")
    gain_sign = "+" if p.unrealised_gain_percent >= 0 else ""
    lines.append(f"Unrealised gain: {gain_sign}{p.unrealised_gain_percent * 100:.1f}%")
    lines.append(f"Lots >= 10% gain: {p.high_gain_lot_count}/{p.profitable_lot_count + (len(signal.eligible_lots) - p.high_gain_lot_count if p.profitable_lot_count == 0 else 0)}")  # general format

    lines.append("")
    lines.append(f"Signal: {signal.status}")
    lines.append("")
    lines.append("Reasons:")
    for reason in signal.reasons:
        lines.append(f"- {reason}")

    lines.append("")
    lines.append("This is a relative market/portfolio condition, not a prediction of IBM's future price (Not a price prediction).")
    lines.append("No trade was executed.")

    return "\n".join(lines)
