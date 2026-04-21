import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os
import uuid
from datetime import datetime

PROGRAMS_PATH = os.path.join(os.path.dirname(
    __file__), "..", "..", "data", "programs.json")

DAY_ORDER = ["lu", "ma", "mi", "ju", "vi", "sa", "do"]
DAY_LABELS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
DAY_FORM_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DAY_FORM_KEYS = ["lu", "ma", "mi", "ju", "vi", "sa", "do"]


def load_programs():
    if not os.path.exists(PROGRAMS_PATH):
        os.makedirs(os.path.dirname(PROGRAMS_PATH), exist_ok=True)
        return []
    try:
        with open(PROGRAMS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_programs(programs):
    os.makedirs(os.path.dirname(PROGRAMS_PATH), exist_ok=True)
    with open(PROGRAMS_PATH, "w", encoding="utf-8") as f:
        json.dump(programs, f, indent=4, ensure_ascii=False)


def time_to_fraction(hhmm):
    try:
        h, m = hhmm.split(":")
        return (int(h) * 60 + int(m)) / (24 * 60)
    except Exception:
        return 0


class SchedulerWindow(ctk.CTkToplevel):
    def __init__(self, master, colors):
        super().__init__(master)
        self.master = master
        self.colors = colors
        self.programs = load_programs()

        self.title("Programación del canal")
        self.geometry("960x620")
        self.configure(fg_color=colors["bg"])
        self.resizable(True, True)

        self._build_ui()
        self.bind("<Configure>", lambda e: self.after(50, self._draw_calendar))

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        tabs = ctk.CTkTabview(self, fg_color=self.colors["bg"],
                              segmented_button_fg_color=self.colors["surface"],
                              segmented_button_selected_color=self.colors["accent"],
                              segmented_button_selected_hover_color=self.colors["accent2"])
        tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_calendar_tab(tabs.add("📅 Calendario"))
        self._build_programs_tab(tabs.add("📋 Programas"))

    # ---------------------------------------------------------------- CALENDAR TAB --

    def _build_calendar_tab(self, parent):
        # Header días
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=4, pady=(4, 0))

        # Espacio para el eje de horas
        ctk.CTkLabel(header, text="", width=36).pack(side="left")

        for lbl in DAY_LABELS:
            ctk.CTkLabel(
                header, text=lbl,
                text_color=self.colors["text"],
                font=ctk.CTkFont("Courier New", 12, "bold"),
                width=0
            ).pack(side="left", expand=True, fill="x")

        # Canvas
        canvas_frame = ctk.CTkFrame(parent, fg_color=self.colors["bg"])
        canvas_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg=self.colors["bg"],
            highlightthickness=0,
            cursor="hand2"
        )
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical",
                                 command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", lambda e: self._draw_calendar())

        # Guardamos los bloques para hit-testing: lista de dicts
        self._blocks = []  # {x1,y1,x2,y2, prog_id, is_x}

    def _draw_calendar(self):
        self.canvas.delete("all")
        self._blocks = []

        canvas_w = self.canvas.winfo_width() or 900
        HOUR_AXIS = 36
        col_w = (canvas_w - HOUR_AXIS) / 7
        ROW_H = 48  # píxeles por hora
        TOTAL_H = ROW_H * 24

        self.canvas.configure(scrollregion=(0, 0, canvas_w, TOTAL_H))

        # Ejes
        for h in range(25):
            y = h * ROW_H
            self.canvas.create_line(HOUR_AXIS, y, canvas_w, y,
                                    fill=self.colors["border"])
            if h < 24:
                self.canvas.create_text(
                    HOUR_AXIS - 4, y + ROW_H / 2,
                    text=f"{h:02d}",
                    fill=self.colors["text_dim"],
                    font=("Courier New", 9),
                    anchor="e"
                )

        for i in range(8):
            x = HOUR_AXIS + i * col_w
            self.canvas.create_line(
                x, 0, x, TOTAL_H, fill=self.colors["border"])

        # Línea de hora actual
        now = datetime.now()
        now_frac = (now.hour * 60 + now.minute) / (24 * 60)
        now_y = now_frac * TOTAL_H
        now_col = now.weekday()  # 0=lunes
        now_x1 = HOUR_AXIS + now_col * col_w
        now_x2 = now_x1 + col_w
        self.canvas.create_line(now_x1, now_y, now_x2, now_y,
                                fill=self.colors["ok"], width=2)

        # Bloques de programas
        for prog in self.programs:
            self._draw_block(prog, HOUR_AXIS, col_w, ROW_H, TOTAL_H)

    def _draw_block(self, prog, hour_axis, col_w, row_h, total_h):
        name = prog.get("name", "?")
        days = prog.get("days", [])
        start = prog.get("start", "00:00")
        end = prog.get("end", "00:00")

        sf = time_to_fraction(start)
        ef = time_to_fraction(end)

        # Programa activo ahora
        now = datetime.now()
        now_day = DAY_ORDER[now.weekday()]
        now_frac = (now.hour * 60 + now.minute) / (24 * 60)
        is_now = (now_day in days and sf <= now_frac <= ef)

        fill = self.colors["ok"] if is_now else self.colors["accent"]
        outline = "#ffffff" if is_now else self.colors["accent2"]

        for d in days:
            if d not in DAY_ORDER:
                continue
            col = DAY_ORDER.index(d)
            x1 = hour_axis + col * col_w + 2
            x2 = hour_axis + (col + 1) * col_w - 2
            y1 = sf * total_h + 1
            y2 = ef * total_h - 1

            # Mínimo visual
            if y2 - y1 < 14:
                y2 = y1 + 14

            rect = self.canvas.create_rectangle(x1, y1, x2, y2,
                                                fill=fill, outline=outline, width=1)
            # Nombre
            self.canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2,
                text=name, fill=self.colors["text"],
                font=("Courier New", 9, "bold"),
                width=int(x2 - x1 - 4)
            )

            # X en esquina superior derecha
            X_SIZE = 12
            x_x1 = x2 - X_SIZE - 2
            x_y1 = y1 + 2
            x_x2 = x2 - 2
            x_y2 = y1 + X_SIZE + 2

            self.canvas.create_rectangle(x_x1, x_y1, x_x2, x_y2,
                                         fill=self.colors["accent2"],
                                         outline="", width=0)
            self.canvas.create_text(
                (x_x1 + x_x2) / 2, (x_y1 + x_y2) / 2,
                text="✕", fill="white",
                font=("Courier New", 8, "bold")
            )

            # Registrar zonas de hit-test
            self._blocks.append({
                "x1": x_x1, "y1": x_y1, "x2": x_x2, "y2": x_y2,
                "prog_id": prog["id"], "is_x": True
            })
            self._blocks.append({
                "x1": x1, "y1": y1, "x2": x_x1, "y2": y2,
                "prog_id": prog["id"], "is_x": False
            })

    def _on_canvas_click(self, event):
        # Ajustar por scroll
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        for block in reversed(self._blocks):
            if block["x1"] <= cx <= block["x2"] and block["y1"] <= cy <= block["y2"]:
                prog = next(
                    (p for p in self.programs if p["id"] == block["prog_id"]), None)
                if prog is None:
                    return
                if block["is_x"]:
                    self._confirm_delete(prog)
                else:
                    self._open_form(prog)
                return

    def _confirm_delete(self, prog):
        if messagebox.askyesno(
            "Eliminar programa",
            f"¿Eliminás '{prog['name']}'?\nEsta acción no se puede deshacer.",
            parent=self
        ):
            self.programs = [p for p in self.programs if p["id"] != prog["id"]]
            save_programs(self.programs)
            self._sync_to_obs()
            self._refresh_list()
            self._draw_calendar()

    # ---------------------------------------------------------------- PROGRAMS TAB --

    def _build_programs_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=self.colors["surface"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.program_listbox = tk.Listbox(
            frame,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            selectbackground=self.colors["accent"],
            selectforeground=self.colors["text"],
            font=("Courier New", 12),
            activestyle="none",
            height=20,
            relief="flat",
            borderwidth=0
        )
        self.program_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.program_listbox.bind(
            "<Double-Button-1>", lambda e: self._edit_selected())

        self._refresh_list()

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(btn_row, text="➕ Agregar",
                      fg_color=self.colors["accent"],
                      hover_color=self.colors["accent2"],
                      font=ctk.CTkFont("Courier New", 11, "bold"),
                      command=lambda: self._open_form(None)).pack(side="left", padx=4)

        ctk.CTkButton(btn_row, text="✏️ Editar",
                      fg_color=self.colors["border"],
                      font=ctk.CTkFont("Courier New", 11, "bold"),
                      command=self._edit_selected).pack(side="left", padx=4)

        ctk.CTkButton(btn_row, text="🗑️ Eliminar",
                      fg_color="#333",
                      font=ctk.CTkFont("Courier New", 11, "bold"),
                      command=self._delete_selected).pack(side="left", padx=4)

    def _refresh_list(self):
        self.program_listbox.delete(0, "end")
        if not self.programs:
            self.program_listbox.insert("end", "  (sin programas)")
            return
        for prog in self.programs:
            days = ",".join(prog.get("days", []))
            line = f"  {prog['name']:20s} | {prog.get('source', '?'):15s} | {days:14s} | {prog.get('start', '?')} – {prog.get('end', '?')}"
            self.program_listbox.insert("end", line)

    def _edit_selected(self):
        sel = self.program_listbox.curselection()
        if not sel:
            return
        prog = self.programs[sel[0]]
        self._open_form(prog)

    def _delete_selected(self):
        sel = self.program_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Seleccioná un programa.", parent=self)
            return
        prog = self.programs[sel[0]]
        self._confirm_delete(prog)

    # ---------------------------------------------------------------- FORM --

    def _open_form(self, program):
        ProgramForm(self, program, self.colors, self._on_save)

    def _on_save(self, data):
        existing = next(
            (p for p in self.programs if p["id"] == data["id"]), None)
        if existing:
            idx = self.programs.index(existing)
            self.programs[idx] = data
        else:
            self.programs.append(data)

        save_programs(self.programs)
        self._sync_to_obs()
        self._refresh_list()
        self._draw_calendar()

    # ---------------------------------------------------------------- SYNC --

    def _sync_to_obs(self):
        """Copia programs.json a la PC OBS vía SSH."""
        try:
            app = self.master
            if not (hasattr(app, 'ssh') and app.ssh and app.ssh.is_connected()):
                return
            remote_path = "/opt/obs-watchdog/data/programs.json"
            content = json.dumps(self.programs, indent=4, ensure_ascii=False)
            # Escribir vía echo+ssh para evitar dependencia de SFTP
            escaped = content.replace("'", "'\\''")
            app.ssh.run_command(f"echo '{escaped}' > {remote_path}")
        except Exception as e:
            print(f"[SchedulerWindow] Error sync SSH: {e}")


# ---------------------------------------------------------------- FORM WINDOW --

class ProgramForm(ctk.CTkToplevel):
    def __init__(self, master, program, colors, callback):
        super().__init__(master)
        self.program = program
        self.colors = colors
        self.callback = callback

        self.title("Editar programa" if program else "Nuevo programa")
        self.geometry("440x480")
        self.configure(fg_color=colors["bg"])
        self.resizable(False, False)
        self.grab_set()

        self._build()
        if program:
            self._load(program)

    def _build(self):
        C = self.colors
        pad = {"padx": 20, "pady": 6}

        ctk.CTkLabel(self, text="Nombre del programa:",
                     text_color=C["text"],
                     font=ctk.CTkFont("Courier New", 11)).pack(anchor="w", **pad)
        self.name_entry = ctk.CTkEntry(self, fg_color=C["surface"],
                                       text_color=C["text"],
                                       font=ctk.CTkFont("Courier New", 11),
                                       width=380)
        self.name_entry.pack(**pad)

        ctk.CTkLabel(self, text="Fuente en OBS (nombre exacto):",
                     text_color=C["text"],
                     font=ctk.CTkFont("Courier New", 11)).pack(anchor="w", **pad)
        self.source_entry = ctk.CTkEntry(self, fg_color=C["surface"],
                                         text_color=C["text"],
                                         font=ctk.CTkFont("Courier New", 11),
                                         width=380,
                                         placeholder_text="Ej: camara, locutor, musica")
        self.source_entry.pack(**pad)

        ctk.CTkLabel(self, text="Días:",
                     text_color=C["text"],
                     font=ctk.CTkFont("Courier New", 11)).pack(anchor="w", **pad)

        self.day_vars = {}
        days_frame = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=6)
        days_frame.pack(fill="x", padx=20, pady=4)

        # 2 filas: Lun–Jue y Vie–Dom
        row1 = ctk.CTkFrame(days_frame, fg_color="transparent")
        row1.pack(fill="x", pady=2)

        row2 = ctk.CTkFrame(days_frame, fg_color="transparent")
        row2.pack(fill="x", pady=2)

        for i, (label, key) in enumerate(zip(DAY_FORM_LABELS, DAY_FORM_KEYS)):
            var = tk.BooleanVar()
            chk = ctk.CTkCheckBox(
                row1 if i < 4 else row2,
                text=label,
                variable=var,
                text_color=C["text"],
                checkmark_color=C["text"],
                fg_color=C["accent"],
                hover_color=C["accent2"],
                font=ctk.CTkFont("Courier New", 11)
            )
            chk.pack(side="left", padx=6, pady=4)
            self.day_vars[key] = var

        time_row = ctk.CTkFrame(self, fg_color="transparent")
        time_row.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(time_row, text="Inicio (HH:MM):",
                     text_color=self.colors["text"],
                     font=ctk.CTkFont("Courier New", 11)).pack(side="left")
        self.start_entry = ctk.CTkEntry(time_row, width=90,
                                        fg_color=self.colors["surface"],
                                        text_color=self.colors["text"],
                                        font=ctk.CTkFont("Courier New", 11),
                                        placeholder_text="08:00")
        self.start_entry.pack(side="left", padx=(8, 24))

        ctk.CTkLabel(time_row, text="Fin (HH:MM):",
                     text_color=self.colors["text"],
                     font=ctk.CTkFont("Courier New", 11)).pack(side="left")
        self.end_entry = ctk.CTkEntry(time_row, width=90,
                                      fg_color=self.colors["surface"],
                                      text_color=self.colors["text"],
                                      font=ctk.CTkFont("Courier New", 11),
                                      placeholder_text="12:00")
        self.end_entry.pack(side="left", padx=8)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=20)

        ctk.CTkButton(btn_row, text="Cancelar",
                      fg_color=C["surface"], hover_color=C["border"],
                      font=ctk.CTkFont("Courier New", 11, "bold"),
                      command=self.destroy).pack(side="left", padx=10)

        ctk.CTkButton(btn_row, text="Guardar",
                      fg_color=C["accent"], hover_color=C["accent2"],
                      font=ctk.CTkFont("Courier New", 11, "bold"),
                      command=self._save).pack(side="left", padx=10)

    def _load(self, prog):
        self.name_entry.insert(0, prog.get("name", ""))
        self.source_entry.insert(0, prog.get("source", ""))
        self.start_entry.insert(0, prog.get("start", ""))
        self.end_entry.insert(0, prog.get("end", ""))
        for key in DAY_FORM_KEYS:
            if key in prog.get("days", []):
                self.day_vars[key].set(True)

    def _save(self):
        name = self.name_entry.get().strip()
        source = self.source_entry.get().strip()
        start = self.start_entry.get().strip()
        end = self.end_entry.get().strip()
        days = [k for k in DAY_FORM_KEYS if self.day_vars[k].get()]

        if not all([name, source, start, end, days]):
            messagebox.showwarning("Campos incompletos",
                                   "Completá todos los campos y seleccioná al menos un día.",
                                   parent=self)
            return

        # Validar formato HH:MM
        for label, val in [("Inicio", start), ("Fin", end)]:
            try:
                h, m = val.split(":")
                assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
            except Exception:
                messagebox.showwarning("Formato inválido",
                                       f"{label}: usá formato HH:MM (ej: 08:00)",
                                       parent=self)
                return

        prog_id = self.program["id"] if self.program else str(uuid.uuid4())[:8]

        self.callback({
            "id": prog_id,
            "name": name,
            "source": source,
            "start": start,
            "end": end,
            "days": days
        })
        self.destroy()
