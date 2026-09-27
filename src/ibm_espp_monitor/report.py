from datetime import datetime
from decimal import Decimal
from ibm_espp_monitor.config import MonitorConfig
from ibm_espp_monitor.signal import SellSignal


def get_tax_deadline_reminder(as_of: datetime) -> str:
    """Returns the Irish CGT payment & filing deadline reminder."""
    # 1 Jan - 30 Nov -> payment due 15 Dec of current tax year
    # 1 Dec - 31 Dec -> payment due 31 Jan of following year
    if as_of.month <= 11:
        return f"税务申报期限提醒: 1月-11月发生的卖出，须于当年12月15日前完成CGT缴税。"
    else:
        next_year = as_of.year + 1
        return f"税务申报期限提醒: 12月发生的卖出，须于次年({next_year}年)1月31日前完成CGT缴税。"


def render_report(
    signal: SellSignal,
    as_of: datetime,
    config: MonitorConfig | None = None,
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
        tax_mult = Decimal(str(1.0 - config.cgt_rate))
        lines.append("")
        lines.append("Irish CGT Tax Summary:")
        lines.append(f"- Annual allowance: €{config.cgt_annual_allowance_eur:,.2f} (Remaining: €{remaining_allowance:,.2f})")
        if eligible_count > 0:
            lines.append(
                f"- Eligible lots gain: Pre-tax €{eligible_gain_eur:,.2f} | Est. Post-tax €{eligible_gain_eur * tax_mult:,.2f}"
            )
            if float(eligible_gain_eur) > remaining_allowance:
                lines.append("  ⚠️ 提示: 建议卖出批次收益超出年度免税额，超出部分需缴纳 33% 爱尔兰资本利得税 (CGT)。")
            else:
                lines.append("  ✅ 提示: 建议卖出批次收益在剩余免税额度内。")

    lines.append("")
    lines.append(f"Signal: {signal.status}")
    lines.append("")
    lines.append("Reasons:")
    for reason in signal.reasons:
        lines.append(f"- {reason}")

    if signal.status == "SELL_WINDOW":
        lines.append("")
        lines.append("Execution Guidance:")
        lines.append("- 💡 建议分批卖出 (例如先卖出 1/3)，若价格继续创出新高可保留剩余批次继续观察。")

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
    lines.append("- ⚠️ 单一标的持仓市值已超过风险上限，建议无视技术择时信号，优先减仓至目标限额以下以控制组合集中度风险。")
    lines.append("")
    lines.append(f"Tax Deadline: {get_tax_deadline_reminder(as_of)}")
    return "\n".join(lines)
