from datetime import datetime, timedelta
from ibm_espp_monitor.state import NotificationState, load_state, record_notification, save_state


def test_record_notification_updates_timestamp():
    state = NotificationState()
    now = datetime(2026, 9, 27, 18, 0)
    new_state = record_notification(state, now)
    assert new_state.last_sell_window_alert == now


def test_save_and_load_state(tmp_path):
    state_file = tmp_path / "state.json"
    now = datetime(2026, 9, 27, 18, 0)
    state = NotificationState(last_sell_window_alert=now)
    save_state(state_file, state)

    loaded = load_state(state_file)
    assert loaded.last_sell_window_alert == now
