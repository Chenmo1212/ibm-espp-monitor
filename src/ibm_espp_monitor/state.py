from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json


@dataclass(frozen=True)
class NotificationState:
    last_sell_window_alert: datetime | None = None


def load_state(path: str | Path) -> NotificationState:
    file_path = Path(path)
    if not file_path.exists():
        return NotificationState()
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            last_alert_str = data.get("last_sell_window_alert")
            if last_alert_str:
                return NotificationState(
                    last_sell_window_alert=datetime.fromisoformat(last_alert_str)
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
        )
    }
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record_notification(state: NotificationState, now: datetime) -> NotificationState:
    return NotificationState(last_sell_window_alert=now)
