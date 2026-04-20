import websocket
import json
import hashlib
import base64
import threading


class OBSWebSocket:
    def __init__(self, port: int, password: str = ""):
        self.port = port
        self.password = password
        self.ws = None
        self._lock = threading.Lock()
        self._message_id = 0
        self.connected = False

    def connect(self):
        url = f"ws://localhost:{self.port}"
        self.ws = websocket.WebSocket()
        self.ws.connect(url, timeout=5)
        self._authenticate()
        self.connected = True

    def disconnect(self):
        if self.ws:
            self.ws.close()
            self.ws = None
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected and self.ws is not None

    def _next_id(self) -> str:
        self._message_id += 1
        return str(self._message_id)

    def _authenticate(self):
        hello = json.loads(self.ws.recv())
        auth_data = hello.get("d", {}).get("authentication")
        if not auth_data:
            return  # Sin contraseña requerida

        challenge = auth_data["challenge"]
        salt = auth_data["salt"]
        secret = base64.b64encode(
            hashlib.sha256((self.password + salt).encode()).digest()
        ).decode()
        auth_response = base64.b64encode(
            hashlib.sha256((secret + challenge).encode()).digest()
        ).decode()

        self._send({
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "authentication": auth_response
            }
        })
        self.ws.recv()  # Espera confirmación

    def _send(self, payload: dict) -> dict:
        with self._lock:
            self.ws.send(json.dumps(payload))
            return json.loads(self.ws.recv())

    def request(self, request_type: str, data: dict = {}) -> dict:
        payload = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": self._next_id(),
                "requestData": data
            }
        }
        return self._send(payload)

    # --- Acciones principales ---

    def get_stream_status(self) -> dict:
        return self.request("GetStreamStatus")

    def start_stream(self):
        return self.request("StartStream")

    def stop_stream(self):
        return self.request("StopStream")

    def get_current_scene(self) -> str:
        resp = self.request("GetCurrentProgramScene")
        return resp.get("d", {}).get("responseData", {}).get("currentProgramSceneName", "?")

    def get_scene_list(self) -> list:
        resp = self.request("GetSceneList")
        scenes = resp.get("d", {}).get("responseData", {}).get("scenes", [])
        return [s["sceneName"] for s in scenes]

    def set_scene(self, scene_name: str):
        return self.request("SetCurrentProgramScene", {"sceneName": scene_name})
