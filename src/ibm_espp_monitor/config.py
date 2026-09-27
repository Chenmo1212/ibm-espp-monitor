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
    max_position_value_eur: float = 0.0
    fx_eur_usd: float = 1.08
    concentration_cooldown_days: int = 90
    cgt_rate: float = 0.33
    cgt_annual_allowance_eur: float = 1270.0
    cgt_used_allowance_eur: float = 0.0


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

    portfolio_sec = data.get("portfolio", {})
    max_position_value_eur = float(portfolio_sec.get("max_position_value_eur", 0.0))
    fx_eur_usd = float(portfolio_sec.get("fx_eur_usd", 1.08))
    concentration_cooldown_days = int(portfolio_sec.get("concentration_cooldown_days", 90))

    tax_sec = data.get("tax", {})
    cgt_rate = float(tax_sec.get("cgt_rate", 0.33))
    cgt_annual_allowance_eur = float(tax_sec.get("cgt_annual_allowance_eur", 1270.0))
    cgt_used_allowance_eur = float(tax_sec.get("cgt_used_allowance_eur", 0.0))

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
    if max_position_value_eur < 0.0:
        raise ValueError("max_position_value_eur must be non-negative")
    if fx_eur_usd <= 0.0:
        raise ValueError("fx_eur_usd must be positive")
    if concentration_cooldown_days < 0:
        raise ValueError("concentration_cooldown_days must be non-negative")
    if not (0.0 <= cgt_rate <= 1.0):
        raise ValueError("cgt_rate must be between 0.0 and 1.0")

    return MonitorConfig(
        lookback_days=lookback_days,
        percentile_threshold=percentile_threshold,
        high_distance_threshold=high_distance_threshold,
        min_gain_for_alert=min_gain_for_alert,
        cooldown_days=cooldown_days,
        notification_enabled=notification_enabled,
        currency=currency,
        max_position_value_eur=max_position_value_eur,
        fx_eur_usd=fx_eur_usd,
        concentration_cooldown_days=concentration_cooldown_days,
        cgt_rate=cgt_rate,
        cgt_annual_allowance_eur=cgt_annual_allowance_eur,
        cgt_used_allowance_eur=cgt_used_allowance_eur,
    )
