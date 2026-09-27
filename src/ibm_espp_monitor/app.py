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
    should_notify,
)
from ibm_espp_monitor.portfolio import load_lots
from ibm_espp_monitor.portfolio_metrics import (
    calculate_lot_metrics,
    calculate_portfolio_metrics,
)
from ibm_espp_monitor.providers.market_provider import YahooMarketProvider
from ibm_espp_monitor.report import render_report
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
    )

    portfolio_metrics = calculate_portfolio_metrics(
        lot_metrics,
        min_high_gain=config.min_gain_for_alert,
    )

    signal = evaluate_sell_window(
        market_metrics,
        portfolio_metrics,
        lot_metrics,
        config,
    )

    report = render_report(signal, current_time)

    if dry_run:
        print(report)
        return signal

    # Print to stdout
    print(report)

    if config.notification_enabled:
        state = load_state(state_path)
        active_notifier = notifier or TelegramNotifier()

        if should_notify(signal, state, current_time, config.cooldown_days):
            active_notifier.send(report)
            updated_state = record_notification(state, current_time)
            save_state(state_path, updated_state)

    return signal
