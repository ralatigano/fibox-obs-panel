import customtkinter as ctk
import threading
import json
import os
from src.modules.ssh_client import SSHClient
from src.modules.obs_ws import OBSWebSocket
from src.modules.watchdog_ctrl import WatchdogController
from src.modules.state_manager import StateManager
from src.modules.schedule_ui import SchedulerWindow
from PIL import Image, ImageTk

# Paleta Fibox — oscuro, minimalista
COLORS = {
    "bg":        "#0d0d1a",   # casi negro con tinte azul
    "surface":   "#22244E",   # azul oscuro Fibox
    "border":    "#2e3170",   # azul medio suavizado
    "accent":    "#E6007E",   # magenta Fibox
    "accent2":   "#b8005e",   # magenta oscuro hover
    "text":      "#f0f0f0",
    "text_dim":  "#9999bb",   # blanco azulado
    "ok":        "#2ecc71",
    "warn":      "#e67e22",
    "error":     "#e74c3c",
}

APP_VERSION = "0.3.1"

CONFIG_PATH = os.path.join(os.path.dirname(
    __file__), "..", "config", "settings.json")


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


class FiboxApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        icon_path = os.path.join(os.path.dirname(__file__), "assets", "F.ico")
        try:
            self.iconbitmap(icon_path)
        except Exception as e:
            print("No se pudo cargar el icono:", e)

        self.config_data = load_config()
        self.state_manager = StateManager()
        self.ssh = None
        self.obs_ws = None
        self.watchdog = None

        ctk.set_appearance_mode("dark")
        self.configure(fg_color=COLORS["bg"])
        self.title(f"Fibox OBS Control Center v{APP_VERSION}")
        self.geometry("520x820")
        self.resizable(True, True)

        self._build_ui()
        self.state_manager.register_callback(self._on_state_change)

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        pad = {"padx": 16, "pady": 6}

        # Header con logo
        header = ctk.CTkFrame(
            self, fg_color=COLORS["surface"], corner_radius=0, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        try:
            from PIL import Image as PILImage
            logo_path = os.path.join(os.path.dirname(
                __file__), "assets", "fibox_logo.png")
            pil_img = PILImage.open(logo_path)
            # Escalar manteniendo aspect ratio a altura 50px
            h = 50
            w = int(pil_img.width * h / pil_img.height)
            logo_img = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=(w, h))
            ctk.CTkLabel(header, image=logo_img, text="").pack(
                side="left", padx=16, pady=10)
        except Exception:
            ctk.CTkLabel(header, text="FIBOX",
                         font=ctk.CTkFont("Courier New", 18, "bold"),
                         text_color=COLORS["accent"]).pack(side="left", padx=16, pady=14)

        ctk.CTkLabel(header, text=f"OBS CONTROL CENTER v{APP_VERSION}",
                     font=ctk.CTkFont("Courier New", 11),
                     text_color=COLORS["text_dim"]).pack(side="left", padx=(0, 0), pady=14)

        self._status_dot = ctk.CTkLabel(header, text="●", font=ctk.CTkFont(size=20),
                                        text_color=COLORS["error"])
        self._status_dot.pack(side="right", padx=20)

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"],
                                        scrollbar_button_color=COLORS["border"])
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        self._section_conexion(scroll, pad)
        self._section_transmision(scroll, pad)
        self._section_obs(scroll, pad)
        self._section_watchdog(scroll, pad)
        self._section_fuentes(scroll, pad)
        self._section_carrusel(scroll, pad)
        self._section_publicidad(scroll, pad)
        self._section_logs(scroll, pad)
        self._section_visor(scroll, pad)
        self._section_programacion(scroll, pad)

        # Textbox
        self._log_box = ctk.CTkTextbox(
            self,
            height=90,
            fg_color=COLORS["surface"],
            text_color=COLORS["text_dim"],
            font=ctk.CTkFont("Courier New", 10),
            corner_radius=0
        )
        self._log_box.pack(fill="x", padx=0, pady=0)
        self._log_box.configure(state="disabled")

        ola_path = os.path.join(os.path.dirname(__file__), "assets", "ola.png")
        ola_pil = Image.open(ola_path).resize((520, 80), Image.LANCZOS)
        self._ola_img = ctk.CTkImage(light_image=ola_pil, size=(520, 80))

        self._ola_label = ctk.CTkLabel(
            self,
            text="",
            image=self._ola_img,
            width=520,
            height=80,
            fg_color=COLORS["surface"],
        )
        self._ola_label.pack(fill="x", padx=0, pady=(0, 0))

    def _card(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["surface"],
                             corner_radius=8, border_width=1,
                             border_color=COLORS["border"])
        frame.pack(fill="x", padx=12, pady=5)
        ctk.CTkLabel(frame, text=title.upper(),
                     font=ctk.CTkFont("Courier New", 10, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", padx=12, pady=(10, 4))
        sep = ctk.CTkFrame(frame, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", padx=12, pady=(0, 8))
        return frame

    def _btn(self, parent, text, command, color=None):
        return ctk.CTkButton(parent, text=text, command=command,
                             fg_color=color or COLORS["accent"],
                             hover_color=COLORS["accent2"] if (
                                 color is None or color == COLORS["accent"]) else COLORS["border"],
                             text_color=COLORS["text"],
                             font=ctk.CTkFont("Courier New", 11, "bold"),
                             corner_radius=4, height=32)

    def _indicator(self, parent, label):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=2)
        dot = ctk.CTkLabel(row, text="●", text_color=COLORS["error"],
                           font=ctk.CTkFont(size=12))
        dot.pack(side="left")
        ctk.CTkLabel(row, text=f"  {label}", text_color=COLORS["text"],
                     font=ctk.CTkFont("Courier New", 11)).pack(side="left")
        return dot

    # ---- Secciones ----

    def _section_conexion(self, parent, pad):
        card = self._card(parent, "🔌 Conexión")
        self._dot_ssh = self._indicator(card, "SSH")
        self._dot_ws = self._indicator(card, "WebSocket OBS")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(6, 12))
        self._btn(row, "Conectar", self._connect).pack(
            side="left", padx=(0, 8))
        self._btn(row, "Desconectar", self._disconnect,
                  color=COLORS["border"]).pack(side="left")

    def _section_transmision(self, parent, pad):
        card = self._card(parent, "📡 Transmisión")
        self._lbl_stream = ctk.CTkLabel(card, text="Estado: desconocido",
                                        text_color=COLORS["text_dim"],
                                        font=ctk.CTkFont("Courier New", 11))
        self._lbl_stream.pack(anchor="w", padx=12, pady=(0, 6))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self._btn(row, "▶  Iniciar", self._stream_start).pack(
            side="left", padx=(0, 8))
        self._btn(row, "■  Detener", self._stream_stop,
                  color="#333").pack(side="left")

    def _section_obs(self, parent, pad):
        card = self._card(parent, "🎥 OBS")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(6, 12))
        self._btn(row, "Iniciar OBS", self._obs_start).pack(
            side="left", padx=(0, 8))
        self._btn(row, "Detener", self._obs_stop, color="#333").pack(
            side="left", padx=(0, 8))
        self._btn(row, "Reiniciar", self._obs_restart,
                  color="#2a2a2a").pack(side="left")

    def _section_watchdog(self, parent, pad):
        card = self._card(parent, "🐶 Watchdog")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(6, 12))
        self._btn(row, "Activar",   self._wdog_start).pack(
            side="left", padx=(0, 8))
        self._btn(row, "Desactivar", self._wdog_stop,
                  color="#333").pack(side="left", padx=(0, 8))
        self._btn(row, "Ver logs",  self._wdog_logs,
                  color="#2a2a2a").pack(side="left")

    def _section_fuentes(self, parent, pad):
        card = self._card(parent, "🎛 Fuentes / Cámara")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self._btn(row, "Reiniciar cámara", self._cam_restart).pack(
            side="left", padx=(0, 8))
        self._btn(row, "Reiniciar video",  self._video_restart,
                  color="#2a2a2a").pack(side="left")

    def _section_publicidad(self, parent, pad):
        card = self._card(parent, "📺 Publicidad")
        self._ad_scripts = []
        self._ad_dropdown = ctk.CTkOptionMenu(card, values=["(conectar primero)"],
                                              fg_color=COLORS["border"],
                                              button_color=COLORS["accent"],
                                              font=ctk.CTkFont("Courier New", 11))
        self._ad_dropdown.pack(fill="x", padx=12, pady=(0, 6))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self._btn(row, "▶  Lanzar ahora", self._ad_launch).pack(
            side="left", padx=(0, 8))
        self._btn(row, "↺  Actualizar lista", self._ad_refresh,
                  color="#2a2a2a").pack(side="left")

    def _section_carrusel(self, parent, pad):
        card = self._card(parent, "📝 Carrusel de texto")
        self._carrusel_entry = ctk.CTkTextbox(card, height=60,
                                              fg_color=COLORS["border"],
                                              text_color=COLORS["text"],
                                              font=ctk.CTkFont("Courier New", 11))
        self._carrusel_entry.pack(fill="x", padx=12, pady=(0, 6))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self._btn(row, "✔  Enviar texto", self._carrusel_send).pack(
            side="left", padx=(0, 8))
        self._btn(row, "👁 Mostrar fuente", self._carrusel_show,
                  color="#2a2a2a").pack(side="left", padx=(0, 8))
        self._btn(row, "✖ Ocultar fuente", self._carrusel_hide,
                  color="#333").pack(side="left")

    def _section_logs(self, parent, pad):
        card = self._card(parent, "📄 Logs")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self._btn(row, "Logs OBS",     self._logs_obs).pack(
            side="left", padx=(0, 8))
        self._btn(row, "Logs sistema", self._logs_sys,
                  color="#2a2a2a").pack(side="left", padx=(0, 8))
        self._btn(row, "Exportar",     self._logs_export,
                  color="#2a2a2a").pack(side="left")

    def _section_visor(self, parent, pad):
        card = self._card(parent, "👁 Visor en vivo")
        self._btn(card, "👁  Abrir visor", self._open_viewer).pack(
            anchor="w", padx=12, pady=(0, 12))

    def _section_programacion(self, parent, pad):
        card = self._card(parent, "📅 Programación")
        self._btn(card, "📅 Programación del canal", self._open_scheduler).pack(
            anchor="w", padx=12, pady=(0, 12)
        )
    # ---------------------------------------------------------------- Lógica --

    def _log(self, msg):
        def _update():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", f"› {msg}\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.after(0, _update)

    def _run_async(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def _on_state_change(self, key, value):
        color_map = {True: COLORS["ok"], False: COLORS["error"]}
        if key == "ssh_connected":
            self._dot_ssh.configure(text_color=color_map[value])
            self._status_dot.configure(text_color=color_map[value])
        elif key == "ws_connected":
            self._dot_ws.configure(text_color=color_map[value])
        elif key == "obs_running":
            self._dot_obs.configure(text_color=color_map[value])
        elif key == "watchdog_active":
            self._dot_wdog.configure(text_color=color_map[value])
        elif key == "stream_running":
            label = "Transmitiendo  🔴" if value else "Detenida"
            color = COLORS["ok"] if value else COLORS["text_dim"]
            self._lbl_stream.configure(
                text=f"Estado: {label}", text_color=color)

    def _connect(self):
        def task():
            try:
                self._log("Conectando SSH...")
                self.ssh = SSHClient(self.config_data["ssh"])
                self.ssh.connect()
                self.state_manager.update("ssh_connected", True)
                self._log("SSH OK")

                # No WebSocket directo — usamos scripts remotos
                self.state_manager.update("ws_connected", True)
                self._log("WebSocket OBS (via script) OK")

                # Inicializar watchdog
                self.watchdog = WatchdogController(
                    self.ssh, self.config_data["watchdog"]
                )

                # Iniciar polling de estado
                self._poll_status()

                # Actualizar lista de scripts de publicidad
                self._ad_refresh()

            except Exception as e:
                self._log(f"Error conexión: {e}")
                self.state_manager.update("ssh_connected", False)
                self.state_manager.update("ws_connected", False)

        self._run_async(task)

    def _disconnect(self):
        def task():
            try:
                if self.obs_ws:
                    self.obs_ws.disconnect()
                if self.ssh:
                    self.ssh.disconnect()
                self.state_manager.update("ssh_connected", False)
                self.state_manager.update("ws_connected", False)
                self._log("Desconectado.")
            except Exception as e:
                self._log(f"Error al desconectar: {e}")
        self._run_async(task)

    def _poll_status(self):
        def task():
            import time
            while self.ssh and self.ssh.is_connected():
                try:
                    out, _ = self.ssh.run_command(
                        "/opt/obs-watchdog/modules/obs_status.sh")
                    self.state_manager.update("obs_running", out == "running")

                    wdog = self.watchdog.get_status()
                    self.state_manager.update(
                        "watchdog_active", wdog == "active")

                    resp = self.ws_request("GetStreamStatus")
                    active = resp.get("outputActive", False)
                    self.state_manager.update("stream_running", active)
                except Exception:
                    pass
                time.sleep(5)
        self._run_async(task)

    def _stream_start(self):
        self._run_async(lambda: self._ws_action(
            lambda: self.ws_request("StartStream"),
            "Transmisión iniciada"
        ))

    def _stream_stop(self):
        self._run_async(lambda: self._ws_action(
            lambda: self.ws_request("StopStream"),
            "Transmisión detenida"
        ))

    def _ws_action(self, fn, ok_msg):
        try:
            fn()
            self._log(ok_msg)
        except Exception as e:
            self._log(f"Error: {e}")

    def _obs_start(self):
        self._run_async(lambda: self._ssh_action(
            "sudo systemctl start obs-studio || DISPLAY=:0 obs --startstreaming &",
            "OBS iniciado"))

    def _obs_stop(self):
        self._run_async(lambda: self._ssh_action("pkill obs", "OBS detenido"))

    def _obs_restart(self):
        self._run_async(lambda: self._ssh_action("pkill obs && sleep 2 && DISPLAY=:0 obs --startstreaming &",
                                                 "OBS reiniciado"))

    def _wdog_start(self):
        self._run_async(lambda: self._ssh_action(
            "sudo systemctl start obs-watchdog.service", "Watchdog activado"))

    def _wdog_stop(self):
        self._run_async(lambda: self._ssh_action(
            "sudo systemctl stop obs-watchdog.service", "Watchdog detenido"))

    def _wdog_logs(self):
        self._run_async(self._show_wdog_logs)

    def _show_wdog_logs(self):
        try:
            logs = self.watchdog.get_logs()
            self._open_log_window("Logs Watchdog", logs)
        except Exception as e:
            self._log(f"Error: {e}")

    def _cam_restart(self):
        self._run_async(lambda: self._ssh_action(
            "systemctl restart camara.service", "Cámara reiniciada"))

    def _video_restart(self):
        self._run_async(lambda: self._ssh_action(
            "pkill mpv && sleep 1 && systemctl restart camara.service", "Video reiniciado"))

    def _ad_refresh(self):
        def task():
            try:
                path = self.config_data["ad_scripts_path"]
                out, _ = self.ssh.run_command(f"ls {path}*.sh 2>/dev/null")
                scripts = [s.split("/")[-1] for s in out.splitlines() if s]
                self._ad_scripts = scripts
                self.after(0, lambda: self._ad_dropdown.configure(
                    values=scripts if scripts else ["(sin scripts)"]))
                self._log(f"{len(scripts)} script(s) encontrado(s)")
            except Exception as e:
                self._log(f"Error al listar scripts: {e}")
        self._run_async(task)

    def _ad_launch(self):
        script = self._ad_dropdown.get()
        if not script or script.startswith("("):
            self._log("Seleccioná un script primero")
            return
        path = self.config_data["ad_scripts_path"] + script
        self._run_async(lambda: self._ssh_action(
            f"bash {path}", f"Publicidad lanzada: {script}"))

    def _carrusel_send(self):
        text = self._carrusel_entry.get("1.0", "end").strip()
        if not text:
            self._log("Carrusel: texto vacío")
            return
        escaped = text.replace("'", "'\\''")
        self._run_async(lambda: self._ssh_action(
            f"echo '{escaped}' > /home/obs-moldes/frase.txt",
            f"Carrusel actualizado: {text[:40]}"
        ))

    def _carrusel_set_visible(self, visible: bool):
        def task():
            try:
                # Paso 1: obtener sceneItemId
                get_id_cmd = (
                    "python3 /opt/obs-watchdog/modules/obs_ws.py GetSceneItemId "
                    "'{\"sceneName\":\"Escena\",\"sourceName\":\"carrusel\"}'"
                )
                out, err = self.ssh.run_command(get_id_cmd)
                if not out:
                    self._log(f"Error obteniendo ID del carrusel: {err}")
                    return
                item_id = json.loads(out).get("sceneItemId")
                if item_id is None:
                    self._log("No se encontró sceneItemId para 'carrusel'")
                    return

                # Paso 2: setear visibilidad
                state_str = "true" if visible else "false"
                set_cmd = (
                    f"python3 /opt/obs-watchdog/modules/obs_ws.py SetSceneItemEnabled "
                    f"'{{\"sceneName\":\"Escena\",\"sceneItemId\":{item_id},\"sceneItemEnabled\":{state_str}}}'"
                )
                self._ssh_action(
                    set_cmd, f"Carrusel {'visible' if visible else 'oculto'}")
            except Exception as e:
                self._log(f"Error carrusel: {e}")
        self._run_async(task)

    def _carrusel_show(self):
        self._carrusel_set_visible(True)

    def _carrusel_hide(self):
        self._carrusel_set_visible(False)

    def _logs_obs(self):
        self._run_async(lambda: self._fetch_and_show_logs(
            "journalctl -u obs-studio -n 100 --no-pager 2>/dev/null || tail -n 100 ~/.config/obs-studio/logs/*.txt 2>/dev/null",
            "Logs OBS"))

    def _logs_sys(self):
        self._run_async(lambda: self._fetch_and_show_logs(
            "journalctl -n 100 --no-pager", "Logs sistema"))

    def _fetch_and_show_logs(self, cmd, title):
        try:
            out, _ = self.ssh.run_command(cmd)
            self._open_log_window(title, out)
        except Exception as e:
            self._log(f"Error: {e}")

    def _logs_export(self):
        def task():
            try:
                import datetime
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(os.path.dirname(
                    __file__), "..", "logs", f"export_{ts}.txt")
                wdog_logs = self.watchdog.get_logs(200)
                obs_out, _ = self.ssh.run_command(
                    "journalctl -u obs-studio -n 200 --no-pager 2>/dev/null")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("=== WATCHDOG ===\n")
                    f.write(wdog_logs)
                    f.write("\n\n=== OBS ===\n")
                    f.write(obs_out)
                self._log(f"Logs exportados: {path}")
            except Exception as e:
                self._log(f"Error exportando: {e}")
        self._run_async(task)

    def _open_viewer(self):
        from modules.viewer import ViewerWindow
        ViewerWindow(self, self.ssh, self.config_data)

    def _ssh_action(self, cmd, ok_msg):
        try:
            out, err = self.ssh.run_command(cmd)
            self._log(ok_msg)
            if err and len(err) > 0:
                self._log(f"  stderr: {err[:80]}")
        except Exception as e:
            self._log(f"Error SSH: {e}")

    def _open_log_window(self, title, content):
        def build():
            win = ctk.CTkToplevel(self)
            win.title(title)
            win.geometry("700x500")
            win.configure(fg_color=COLORS["bg"])
            box = ctk.CTkTextbox(win, fg_color=COLORS["surface"],
                                 text_color=COLORS["text"],
                                 font=ctk.CTkFont("Courier New", 10))
            box.pack(fill="both", expand=True, padx=10, pady=10)
            box.insert("end", content or "(sin contenido)")
            box.configure(state="disabled")
        self.after(0, build)

    def ws_request(self, request_type, data=None):
        """Ejecuta una request OBS WebSocket usando el script remoto obs_ws.py."""
        try:
            payload = json.dumps(data or {})
            cmd = (
                f"python3 /opt/obs-watchdog/modules/obs_ws.py "
                f"{request_type} '{payload}'"
            )
            out, err = self.ssh.run_command(cmd)
            if out:
                return json.loads(out)
            return {}
        except Exception as e:
            self._log(f"WS error: {e}")
            return {}

    def _open_scheduler(self):
        SchedulerWindow(self, COLORS)
