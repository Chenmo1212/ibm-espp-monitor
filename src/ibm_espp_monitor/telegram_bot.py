"""
Telegram Bot — interactive command interface for IBM ESPP Monitor.

Supported commands:
  /start, /help       — command reference
  /check              — run a full dry-run report and send it back
  /lots               — list all ESPP lots with current gain/loss
  /add_lot            — add a new lot (guided multi-step flow)
  /config             — show current configuration values
  /set <key> <value>  — update a single config value in default.toml

Requires env vars:
  TELEGRAM_BOT_TOKEN  — bot token from @BotFather
  TELEGRAM_CHAT_ID    — your personal chat ID (bot only responds to this ID)
"""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "default.toml"
LOTS_PATH = PROJECT_ROOT / "data" / "espp_lots.csv"
STATE_PATH = PROJECT_ROOT / "data" / "notification_state.json"

# ---------------------------------------------------------------------------
# Telegram API helpers
# ---------------------------------------------------------------------------

def _api(token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _send(token: str, chat_id: str, text: str) -> None:
    """Send a plain-text message, splitting if it exceeds Telegram's 4096-char limit."""
    limit = 4096
    while text:
        chunk, text = text[:limit], text[limit:]
        _api(token, "sendMessage", {"chat_id": chat_id, "text": chunk})


def _get_updates(token: str, offset: int) -> list[dict]:
    try:
        result = _api(token, "getUpdates", {"offset": offset, "timeout": 30})
        return result.get("result", [])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

HELP_TEXT = """\
IBM ESPP Monitor — available commands:

Daily check
  /check       Run a full portfolio report right now

Holdings
  /lots        List all ESPP lots with current gain/loss

Configuration
  /config      Show current configuration values
  /set <key> <value>
               Update a config value, e.g.:
                 /set cgt_used_allowance_eur 800
                 /set percentile_threshold 0.80
                 /set cooldown_days 14
                 /set min_gain_for_alert 0.15
                 /set max_position_value_eur 15000
                 /set fx_eur_usd 1.12

  /add_lot <date> <cost_usd> <qty> [available_from]
               Add a new lot to espp_lots.csv, e.g.:
                 /add_lot 2025-10-23 198.50 3.12450
                 /add_lot 2025-10-23 198.50 3.12450 2025-10-23

Help
  /help        Show this message
"""

# Keys that /set is allowed to modify and which TOML section they live in.
_SETTABLE: dict[str, tuple[str, type]] = {
    "percentile_threshold":      ("signal",    float),
    "high_distance_threshold":   ("signal",    float),
    "min_gain_for_alert":        ("signal",    float),
    "cooldown_days":             ("signal",    int),
    "max_position_value_eur":    ("portfolio", float),
    "fx_eur_usd":                ("portfolio", float),
    "concentration_cooldown_days": ("portfolio", int),
    "cgt_rate":                  ("tax",       float),
    "cgt_annual_allowance_eur":  ("tax",       float),
    "cgt_used_allowance_eur":    ("tax",       float),
}


def cmd_help() -> str:
    return HELP_TEXT


def cmd_check() -> str:
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from ibm_espp_monitor.app import run_once
        from ibm_espp_monitor.report import render_concentration_alert

        now = datetime.now(timezone.utc)
        signal = run_once(
            config_path=CONFIG_PATH,
            lots_path=LOTS_PATH,
            state_path=STATE_PATH,
            dry_run=True,
        )

        from ibm_espp_monitor.config import load_config
        from ibm_espp_monitor.report import render_report
        from ibm_espp_monitor.providers.market_provider import get_live_eur_usd

        config = load_config(CONFIG_PATH)
        fx = get_live_eur_usd(fallback=config.fx_eur_usd)
        report = render_report(signal, now, config, fx_eur_usd=fx)

        if signal.is_concentration_breached:
            report += "\n\n" + "=" * 40 + "\n"
            report += render_concentration_alert(signal, now, config)

        return report
    except Exception as e:
        return f"Error running check: {e}"


def cmd_lots() -> str:
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from ibm_espp_monitor.config import load_config
        from ibm_espp_monitor.portfolio import load_lots
        from ibm_espp_monitor.portfolio_metrics import calculate_lot_metrics
        from ibm_espp_monitor.providers.market_provider import YahooMarketProvider, get_live_eur_usd

        config = load_config(CONFIG_PATH)
        lots = load_lots(LOTS_PATH)
        provider = YahooMarketProvider()
        latest = provider.get_latest("IBM")
        fx = get_live_eur_usd(fallback=config.fx_eur_usd)
        metrics = calculate_lot_metrics(lots, latest.close_usd, fx_eur_usd=fx, cgt_rate=config.cgt_rate)
        metrics_sorted = sorted(metrics, key=lambda m: m.lot.allocation_date)

        lines = [f"ESPP Lots  (IBM @ ${latest.close_usd:.2f}, EUR/USD {fx:.4f})", ""]
        lines.append(f"{'Date':<12} {'Type':<10} {'Cost':>8} {'Qty':>8} {'Gain%':>7} {'Gain EUR':>10}")
        lines.append("-" * 60)
        for m in metrics_sorted:
            sign = "+" if m.gain_percent >= 0 else ""
            lines.append(
                f"{m.lot.allocation_date.isoformat():<12} "
                f"{m.lot.contribution_type[:10]:<10} "
                f"${m.lot.cost_basis_usd:>7.2f} "
                f"{m.lot.quantity:>8.5f} "
                f"{sign}{m.gain_percent * 100:>6.1f}% "
                f"€{m.gain_eur:>9,.2f}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching lots: {e}"


def cmd_config() -> str:
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from ibm_espp_monitor.config import load_config

        c = load_config(CONFIG_PATH)
        lines = [
            "Current configuration:",
            "",
            "[market]",
            f"  lookback_days                = {c.lookback_days}",
            "",
            "[signal]",
            f"  percentile_threshold         = {c.percentile_threshold}",
            f"  high_distance_threshold      = {c.high_distance_threshold}",
            f"  min_gain_for_alert           = {c.min_gain_for_alert}",
            f"  cooldown_days                = {c.cooldown_days}",
            "",
            "[portfolio]",
            f"  currency                     = {c.currency}",
            f"  max_position_value_eur       = {c.max_position_value_eur}",
            f"  fx_eur_usd (fallback)        = {c.fx_eur_usd}",
            f"  concentration_cooldown_days  = {c.concentration_cooldown_days}",
            "",
            "[tax]",
            f"  cgt_rate                     = {c.cgt_rate}",
            f"  cgt_annual_allowance_eur     = {c.cgt_annual_allowance_eur}",
            f"  cgt_used_allowance_eur       = {c.cgt_used_allowance_eur}",
            "",
            "[notification]",
            f"  enabled                      = {c.notification_enabled}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading config: {e}"


def cmd_set(key: str, raw_value: str) -> str:
    if key not in _SETTABLE:
        allowed = ", ".join(sorted(_SETTABLE))
        return f"Unknown key '{key}'.\nAllowed keys: {allowed}"

    section, cast = _SETTABLE[key]
    try:
        value = cast(raw_value)
    except ValueError:
        return f"Invalid value '{raw_value}' for {key} (expected {cast.__name__})."

    try:
        text = CONFIG_PATH.read_text(encoding="utf-8")
        # Replace the value inside the correct section only.
        # Strategy: find the [section] header, then replace the first matching key=value after it.
        section_pattern = re.compile(
            r"(\[" + re.escape(section) + r"\][^\[]*)",
            re.DOTALL,
        )
        m = section_pattern.search(text)
        if not m:
            return f"Section [{section}] not found in config."

        section_text = m.group(1)
        key_pattern = re.compile(r"^(" + re.escape(key) + r"\s*=\s*)(.+)$", re.MULTILINE)
        if not key_pattern.search(section_text):
            return f"Key '{key}' not found in [{section}] section."

        new_section = key_pattern.sub(lambda _m: _m.group(1) + str(value), section_text, count=1)
        new_text = text[: m.start(1)] + new_section + text[m.end(1):]
        CONFIG_PATH.write_text(new_text, encoding="utf-8")
        return f"✅ Updated [{section}] {key} = {value}"
    except Exception as e:
        return f"Error updating config: {e}"


def cmd_add_lot(args: list[str]) -> str:
    """
    Usage: /add_lot <allocation_date> <cost_basis_usd> <quantity> [available_from]
    contribution_type defaults to "Purchase", instrument to "Purchase Shares".
    available_from defaults to allocation_date if omitted.
    """
    if len(args) < 3:
        return (
            "Usage: /add_lot <date> <cost_usd> <qty> [available_from]\n"
            "Example: /add_lot 2025-10-23 198.50 3.12450"
        )
    try:
        allocation_date = args[0].strip()
        cost_basis_usd = float(args[1])
        quantity = float(args[2])
        available_from = args[3].strip() if len(args) >= 4 else allocation_date

        # Validate date formats
        datetime.strptime(allocation_date, "%Y-%m-%d")
        datetime.strptime(available_from, "%Y-%m-%d")
        if cost_basis_usd <= 0:
            return "Error: cost_basis_usd must be positive."
        if quantity <= 0:
            return "Error: quantity must be positive."

        row = (
            f"{allocation_date},"
            f"Purchase Shares,"
            f"Purchase,"
            f"{cost_basis_usd:.4f},"
            f"{quantity:.5f},"
            f"{available_from}\n"
        )
        with LOTS_PATH.open("a", encoding="utf-8") as f:
            f.write(row)

        return (
            f"✅ Lot added:\n"
            f"  Date:          {allocation_date}\n"
            f"  Cost basis:    ${cost_basis_usd:.4f}\n"
            f"  Quantity:      {quantity:.5f}\n"
            f"  Available from: {available_from}"
        )
    except ValueError as e:
        return f"Error: {e}\nExpected format: /add_lot YYYY-MM-DD cost qty [available_from]"


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def dispatch(text: str) -> str:
    text = text.strip()
    parts = text.split()
    cmd = parts[0].lower().split("@")[0] if parts else ""

    if cmd in ("/start", "/help"):
        return cmd_help()
    if cmd == "/check":
        return cmd_check()
    if cmd == "/lots":
        return cmd_lots()
    if cmd == "/config":
        return cmd_config()
    if cmd == "/set":
        if len(parts) < 3:
            return "Usage: /set <key> <value>\nType /help for available keys."
        return cmd_set(parts[1], parts[2])
    if cmd == "/add_lot":
        return cmd_add_lot(parts[1:])

    return f"Unknown command '{cmd}'. Type /help for available commands."


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def run_bot() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set.")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID environment variable is not set.")

    print("IBM ESPP Telegram bot started. Waiting for commands...")
    _send(token, chat_id, "✅ IBM ESPP Monitor bot is online. Type /help for available commands.")

    offset = 0
    while True:
        updates = _get_updates(token, offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            from_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "")

            # Only respond to the configured chat — ignore everything else
            if from_id != chat_id:
                continue
            if not text.startswith("/"):
                continue

            reply = dispatch(text)
            _send(token, chat_id, reply)
