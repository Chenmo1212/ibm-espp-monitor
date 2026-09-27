from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ibm_espp_monitor.config import load_config
from ibm_espp_monitor.market_data import (
    MarketDataProvider,
    get_normalized_history,
)
from ibm_espp_monitor.metrics import calculate_market_metrics
from ibm_espp_monitor.notifications import (
    ConsoleNotifier,
    Notifier,
    TelegramNotifier,
    should_notify_concentration,
    should_notify_sell_window,
)
from ibm_espp_monitor.portfolio import load_lots
from ibm_espp_monitor.portfolio_metrics import (
    calculate_lot_metrics,
    calculate_portfolio_metrics,
)
from ibm_espp_monitor.providers.market_provider import YahooMarketProvider, get_live_eur_usd
from ibm_espp_monitor.report import render_concentration_alert, render_report
from ibm_espp_monitor.signal import SellSignal, evaluate_sell_window
from ibm_espp_monitor.state import (
    load_state,
    record_notification,
    save_state,
)


def run_once(
    config_path: str | Path = "config/default.toml",
    lots_path: str | Path = "data/espp_lots.csv",
    state_path: str | Path = "data/notification_state.json",
    market_provider: Optional[MarketDataProvider] = None,
    notifier: Optional[Notifier] = None,
    now: Optional[datetime] = None,
    dry_run: bool = False,
) -> SellSignal:
    current_time = now or datetime.now(timezone.utc)
    config = load_config(config_path)
    lots = load_lots(lots_path)

    provider = market_provider or YahooMarketProvider()

    # Use live EUR/USD rate; fall back to config value if fetch fails
    fx_eur_usd = get_live_eur_usd(fallback=config.fx_eur_usd)

    history = get_normalized_history(
        provider,
        "IBM",
        config.lookback_days,
    )

    latest = provider.get_latest("IBM")

    market_metrics = calculate_market_metrics(
        history,
        latest.close_usd,
    )

    lot_metrics = calculate_lot_metrics(
        lots,
        latest.close_usd,
        fx_eur_usd=fx_eur_usd,
        cgt_rate=config.cgt_rate,
    )

    remaining_allowance = max(
        0.0,
        config.cgt_annual_allowance_eur - config.cgt_used_allowance_eur,
    )
    portfolio_metrics = calculate_portfolio_metrics(
        lot_metrics,
        min_high_gain=config.min_gain_for_alert,
        fx_eur_usd=fx_eur_usd,
        cgt_rate=config.cgt_rate,
        remaining_cgt_allowance_eur=remaining_allowance,
    )

    signal = evaluate_sell_window(
        market_metrics,
        portfolio_metrics,
        lot_metrics,
        config,
    )

    report = render_report(signal, current_time, config, fx_eur_usd=fx_eur_usd)

    if dry_run:
        print(report)
        if signal.is_concentration_breached:
            print("\n" + "=" * 40 + "\n")
            print(render_concentration_alert(signal, current_time, config))
        return signal

    # Print to stdout
    print(report)
    if signal.is_concentration_breached:
        print("\n" + "=" * 40 + "\n")
        print(render_concentration_alert(signal, current_time, config))

    if config.notification_enabled:
        state = load_state(state_path)
        active_notifier = notifier or TelegramNotifier()

        # 1. Check Concentration Alert (independent rule & cooldown)
        if should_notify_concentration(
            signal,
            state,
            current_time,
            config.concentration_cooldown_days,
        ):
            conc_report = render_concentration_alert(signal, current_time, config)
            active_notifier.send(conc_report)
            state = record_notification(
                state,
                current_time,
                alert_type="CONCENTRATION_ALERT",
            )
            save_state(state_path, state)

        # 2. Check Sell Window Alert (price & lot criteria)
        if should_notify_sell_window(
            signal,
            state,
            current_time,
            config.cooldown_days,
        ):
            active_notifier.send(report)
            state = record_notification(
                state,
                current_time,
                alert_type="SELL_WINDOW",
            )
            save_state(state_path, state)

    return signal
