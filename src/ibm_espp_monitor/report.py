from datetime import datetime
from decimal import Decimal
from ibm_espp_monitor.config import MonitorConfig
from ibm_espp_monitor.signal import SellSignal


def get_tax_deadline_reminder(as_of: datetime) -> str:
    """Returns the Irish CGT payment & filing deadline reminder."""
    # 1 Jan - 30 Nov -> payment due 15 Dec of current tax year
    # 1 Dec - 31 Dec -> payment due 31 Jan of following year
    if as_of.month <= 11:
        return f"CGT deadline reminder: Disposals in Jan–Nov must be paid by 15 Dec of the same tax year."
    else:
        next_year = as_of.year + 1
        return f"CGT deadline reminder: Disposals in Dec must be paid by 31 Jan {next_year}."


def render_report(
    signal: SellSignal,
    as_of: datetime,
    config: MonitorConfig | None = None,
    fx_eur_usd: float | None = None,
) -> str:
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
    if fx_eur_usd is not None:
        lines.append(f"EUR/USD rate: {fx_eur_usd:.4f} (live)")
    lines.append(f"Shares: {p.total_quantity}")
    lines.append(f"Market value: €{p.market_value_eur:,.2f} (${p.market_value_usd:,.2f})")
    lines.append(f"Weighted average cost: ${p.weighted_average_cost_usd:.2f}")
    gain_sign = "+" if p.unrealised_gain_percent >= 0 else ""
    lines.append(f"Unrealised gain: {gain_sign}{p.unrealised_gain_percent * 100:.1f}%")
    
    # Pre-tax and Post-tax gains in EUR
    lines.append(
        f"Gain (Pre-tax / Est. Post-tax @33% CGT): €{p.total_gain_eur:,.2f} / €{p.total_post_tax_gain_eur:,.2f}"
    )

    eligible_count = len(signal.eligible_lots)
    min_gain_pct = int(config.min_gain_for_alert * 100) if config else 10
    lines.append(f"Lots >= {min_gain_pct}% gain: {eligible_count}/{p.profitable_lot_count}")

    # Irish CGT Allowance Check for eligible lots
    if config:
        eligible_gain_eur = sum((lot.gain_eur for lot in signal.eligible_lots), Decimal("0"))
        remaining_allowance = max(
            0.0,
            config.cgt_annual_allowance_eur - config.cgt_used_allowance_eur,
        )
        rem_allowance_dec = Decimal(str(remaining_allowance))
        tax_mult = Decimal(str(1.0 - config.cgt_rate))
        if eligible_gain_eur > Decimal("0"):
            tax_free_portion = min(eligible_gain_eur, rem_allowance_dec)
            taxable_gain = max(Decimal("0"), eligible_gain_eur - rem_allowance_dec)
            post_tax_eligible_gain = tax_free_portion + taxable_gain * tax_mult
        else:
            post_tax_eligible_gain = eligible_gain_eur

        lines.append("")
        lines.append("Irish CGT Tax Summary:")
        lines.append(
            f"- Annual allowance: €{config.cgt_annual_allowance_eur:,.2f} "
            f"(Remaining: €{remaining_allowance:,.2f}, Used: €{config.cgt_used_allowance_eur:,.2f})"
        )
        if eligible_count > 0:
            lines.append(
                f"- Eligible lots gain: Pre-tax €{eligible_gain_eur:,.2f} | Est. Post-tax €{post_tax_eligible_gain:,.2f}"
            )
            if float(eligible_gain_eur) > remaining_allowance:
                lines.append("  ⚠️  Note: Eligible lot gains exceed the annual exemption — the surplus will be subject to 33% Irish CGT.")
            else:
                lines.append("  ✅  Note: Eligible lot gains are within the remaining annual exemption.")
        lines.append("  ℹ️  Note: cgt_used_allowance_eur must be maintained manually. The system has no visibility of disposals outside this ESPP — verify that the allowance has not already been consumed by other assets.")

    lines.append("")
    lines.append(f"Signal: {signal.status}")
    lines.append("")
    lines.append("Reasons:")
    for reason in signal.reasons:
        lines.append(f"- {reason}")

    if signal.status == "SELL_WINDOW":
        lines.append("")
        lines.append("Execution Guidance:")
        lines.append("- 💡 Consider selling in tranches (e.g. sell 1/3 first). Retain remaining lots if price continues to make new highs.")

    lines.append("")
    lines.append(f"Tax Deadline: {get_tax_deadline_reminder(as_of)}")
    lines.append("")
    lines.append("This is a relative market/portfolio condition, not a prediction of IBM's future price (Not a price prediction).")
    lines.append("No trade was executed.")

    return "\n".join(lines)


def render_concentration_alert(
    signal: SellSignal,
    as_of: datetime,
    config: MonitorConfig,
) -> str:
    p = signal.portfolio_metrics
    lines: list[str] = []
    lines.append("⚠️ IBM POSITION CONCENTRATION ALERT")
    lines.append(f"As of: {as_of.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"Total Position Value: €{p.market_value_eur:,.2f} (${p.market_value_usd:,.2f})")
    lines.append(f"Configured Max Limit: €{config.max_position_value_eur:,.2f}")
    lines.append(f"Excess Amount: €{float(p.market_value_eur) - config.max_position_value_eur:,.2f}")
    lines.append("")
    lines.append("Recommendation:")
    lines.append("- ⚠️  Position size exceeds the concentration limit. Regardless of technical timing signals, consider reducing the position below the configured threshold to manage single-stock concentration risk.")
    lines.append("")
    lines.append(f"Tax Deadline: {get_tax_deadline_reminder(as_of)}")
    return "\n".join(lines)
