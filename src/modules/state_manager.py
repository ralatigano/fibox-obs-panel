import threading


class StateManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = {
            "ssh_connected": False,
            "ws_connected": False,
            "obs_running": False,
            "stream_running": False,
            "watchdog_active": False,
            "current_scene": "?",
        }
        self._callbacks = []

    def register_callback(self, fn):
        self._callbacks.append(fn)

    def update(self, key: str, value):
        with self._lock:
            if self._state.get(key) == value:
                return
            self._state[key] = value
        for cb in self._callbacks:
            cb(key, value)

    def get(self, key: str):
        with self._lock:
            return self._state.get(key)

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._state)
