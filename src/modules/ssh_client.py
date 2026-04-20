import paramiko
import threading


class SSHClient:
    def __init__(self, config: dict):
        self.host = config["host"]
        self.port = config["port"]
        self.username = config["username"]
        self.password = config["password"]
        self.client = None
        self.tunnel = None
        self._lock = threading.Lock()

    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=10
        )

    def disconnect(self):
        if self.tunnel:
            self.tunnel.stop()
            self.tunnel = None
        if self.client:
            self.client.close()
            self.client = None

    def is_connected(self) -> bool:
        if self.client is None:
            return False
        transport = self.client.get_transport()
        return transport is not None and transport.is_active()

    def run_command(self, command: str) -> tuple[str, str]:
        """Ejecuta un comando remoto. Devuelve (stdout, stderr)."""
        with self._lock:
            if not self.is_connected():
                raise ConnectionError("SSH no conectado")
            _, stdout, stderr = self.client.exec_command(command, timeout=15)
            return stdout.read().decode().strip(), stderr.read().decode().strip()

    def open_tunnel(self, local_port: int, remote_port: int):
        """Abre un túnel SSH local→remoto para el WebSocket de OBS."""
        transport = self.client.get_transport()
        transport.request_port_forward("", local_port)
        self.tunnel = transport.open_channel(
            "direct-tcpip",
            ("localhost", remote_port),
            ("localhost", local_port)
        )
