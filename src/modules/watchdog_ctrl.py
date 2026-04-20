import threading


class WatchdogController:
    def __init__(self, ssh_client, config: dict):
        self.ssh = ssh_client
        self.script_path = config["script_path"]
        self.state_file = config["state_file"]
        self.log_file = config["log_file"]

    def get_status(self) -> str:
        out, _ = self.ssh.run_command(
            "systemctl is-active obs-watchdog.service")
        return out  # "active" o "inactive"

    def start(self):
        self.ssh.run_command("systemctl start obs-watchdog.service")

    def stop(self):
        self.ssh.run_command("systemctl stop obs-watchdog.service")

    def restart(self):
        self.ssh.run_command("systemctl restart obs-watchdog.service")

    def get_state_json(self) -> str:
        out, _ = self.ssh.run_command(f"cat {self.state_file}")
        return out

    def get_logs(self, lines: int = 100) -> str:
        out, _ = self.ssh.run_command(f"tail -n {lines} {self.log_file}")
        return out
