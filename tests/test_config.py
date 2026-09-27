import pytest
from ibm_espp_monitor.config import load_config


def test_load_config_returns_expected_defaults():
    config = load_config("config/default.toml")

    assert config.lookback_days == 180
    assert config.percentile_threshold == 0.85
    assert config.high_distance_threshold == 0.05
    assert config.min_gain_for_alert == 0.10
    assert config.cooldown_days == 30
    assert config.currency == "EUR"
    assert config.notification_enabled is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("lookback_days", 0),
        ("percentile_threshold", 1.2),
        ("high_distance_threshold", -0.1),
        ("min_gain_for_alert", -0.1),
        ("cooldown_days", -1),
    ],
)
def test_invalid_signal_configuration_is_rejected(tmp_path, field, value):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f"""
[market]
lookback_days = {value if field == "lookback_days" else 180}

[signal]
percentile_threshold = {value if field == "percentile_threshold" else 0.85}
high_distance_threshold = {value if field == "high_distance_threshold" else 0.05}
min_gain_for_alert = {value if field == "min_gain_for_alert" else 0.10}
cooldown_days = {value if field == "cooldown_days" else 30}

[portfolio]
currency = "EUR"

[notification]
enabled = true
"""
    )

    with pytest.raises(ValueError):
        load_config(config_file)
