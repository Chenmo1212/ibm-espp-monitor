from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json


@dataclass(frozen=True)
class NotificationState:
    last_sell_window_alert: datetime | None = None
    last_concentration_alert: datetime | None = None


def load_state(path: str | Path) -> NotificationState:
    file_path = Path(path)
    if not file_path.exists():
        return NotificationState()
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            last_sell_alert_str = data.get("last_sell_window_alert")
            last_conc_alert_str = data.get("last_concentration_alert")
            last_sell = (
                datetime.fromisoformat(last_sell_alert_str)
                if last_sell_alert_str
                else None
            )
            last_conc = (
                datetime.fromisoformat(last_conc_alert_str)
                if last_conc_alert_str
                else None
            )
            return NotificationState(
                last_sell_window_alert=last_sell,
                last_concentration_alert=last_conc,
            )
    except Exception:
        pass
    return NotificationState()


def save_state(path: str | Path, state: NotificationState) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_sell_window_alert": (
            state.last_sell_window_alert.isoformat()
            if state.last_sell_window_alert
            else None
        ),
        "last_concentration_alert": (
            state.last_concentration_alert.isoformat()
            if state.last_concentration_alert
            else None
        ),
    }
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_notification(
    state: NotificationState,
    now: datetime,
    alert_type: str = "SELL_WINDOW",
) -> NotificationState:
    if alert_type == "CONCENTRATION_ALERT":
        return NotificationState(
            last_sell_window_alert=state.last_sell_window_alert,
            last_concentration_alert=now,
        )
    return NotificationState(
        last_sell_window_alert=now,
        last_concentration_alert=state.last_concentration_alert,
    )
