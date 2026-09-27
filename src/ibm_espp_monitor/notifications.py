from datetime import datetime, timedelta
import os
import urllib.parse
import urllib.request
from typing import Protocol
from ibm_espp_monitor.signal import SellSignal
from ibm_espp_monitor.state import NotificationState


class Notifier(Protocol):
    def send(self, message: str) -> None:
        ...


def should_notify(
    signal: SellSignal,
    state: NotificationState,
    now: datetime,
    cooldown_days: int,
) -> bool:
    if signal.status != "SELL_WINDOW":
        return False
    if state.last_sell_window_alert is None:
        return True
    return now - state.last_sell_window_alert >= timedelta(days=cooldown_days)


class TelegramNotifier(Notifier):
    """Sends notification to Telegram via Bot API. Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in env."""

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    def send(self, message: str) -> None:
        if not self.bot_token or not self.chat_id:
            # If not configured, fail quietly or log
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": self.chat_id, "text": message}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception:
            pass


class ConsoleNotifier(Notifier):
    def send(self, message: str) -> None:
        print(message)
