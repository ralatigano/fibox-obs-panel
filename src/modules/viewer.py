import customtkinter as ctk

COLORS = {
    "bg":      "#0f0f0f",
    "surface": "#1a1a1a",
    "accent":  "#e8410a",
    "text":    "#f0f0f0",
    "text_dim": "#888888",
}


class ViewerWindow(ctk.CTkToplevel):
    def __init__(self, parent, ssh, config):
        super().__init__(parent)
        self.ssh = ssh
        self.config = config
        self.title("Visor en vivo")
        self.geometry("640x400")
        self.configure(fg_color=COLORS["bg"])
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="VISOR EN VIVO",
                     font=ctk.CTkFont("Courier New", 13, "bold"),
                     text_color=COLORS["accent"]).pack(pady=(20, 4))

        ctk.CTkLabel(self,
                     text="El visor embebido requiere VLC o mpv instalado en Windows.\nAlternativamente, abrí el stream con el botón de abajo.",
                     text_color=COLORS["text_dim"],
                     font=ctk.CTkFont("Courier New", 10),
                     justify="center").pack(pady=(4, 20))

        ctk.CTkButton(self, text="Abrir stream en VLC / mpv externo",
                      command=self._open_external,
                      fg_color=COLORS["accent"],
                      font=ctk.CTkFont("Courier New", 11, "bold"),
                      corner_radius=4).pack(pady=8)

        ctk.CTkButton(self, text="Cerrar visor",
                      command=self.destroy,
                      fg_color="#2a2a2a",
                      font=ctk.CTkFont("Courier New", 11),
                      corner_radius=4).pack(pady=4)

    def _open_external(self):
        import subprocess
        # Intentá VLC primero, después mpv
        rtmp = self.config.get("stream_url", "")
        if not rtmp:
            ctk.CTkLabel(self, text="stream_url no configurado en settings.json",
                         text_color="#e74c3c").pack()
            return
        for player in ["vlc", "mpv"]:
            try:
                subprocess.Popen([player, rtmp])
                return
            except FileNotFoundError:
                continue
