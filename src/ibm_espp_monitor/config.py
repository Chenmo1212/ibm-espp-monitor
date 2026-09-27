from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class MonitorConfig:
    lookback_days: int
    percentile_threshold: float
    high_distance_threshold: float
    min_gain_for_alert: float
    cooldown_days: int
    notification_enabled: bool
    currency: str


def load_config(path: str | Path) -> MonitorConfig:
    with Path(path).open("rb") as file:
        data = tomllib.load(file)

    lookback_days = data["market"]["lookback_days"]
    percentile_threshold = data["signal"]["percentile_threshold"]
    high_distance_threshold = data["signal"]["high_distance_threshold"]
    min_gain_for_alert = data["signal"]["min_gain_for_alert"]
    cooldown_days = data["signal"]["cooldown_days"]
    notification_enabled = data["notification"]["enabled"]
    currency = data["portfolio"]["currency"]

    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")
    if not (0.0 <= percentile_threshold <= 1.0):
        raise ValueError("percentile_threshold must be between 0.0 and 1.0")
    if high_distance_threshold < 0.0:
        raise ValueError("high_distance_threshold must be non-negative")
    if min_gain_for_alert < 0.0:
        raise ValueError("min_gain_for_alert must be non-negative")
    if cooldown_days < 0:
        raise ValueError("cooldown_days must be non-negative")

    return MonitorConfig(
        lookback_days=lookback_days,
        percentile_threshold=percentile_threshold,
        high_distance_threshold=high_distance_threshold,
        min_gain_for_alert=min_gain_for_alert,
        cooldown_days=cooldown_days,
        notification_enabled=notification_enabled,
        currency=currency,
    )
