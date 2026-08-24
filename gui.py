import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import os

import engine


# ============================================================
# THEME
# ============================================================

BG = "#0f0f0f"
PANEL = "#171717"
PANEL_2 = "#1d1d1d"
BORDER = "#292929"
TEXT = "#eeeeee"
MUTED = "#777777"
ACCENT = "#d6ff3f"
RED = "#ff5c5c"


# ============================================================
# CONSTANTS
# ============================================================

EXT_TO_ALGORITHM = {
    ".hy1": "zip",
    ".hy2": "gzip",
    ".hy3": "lzma",
}

ALGORITHM_TO_EXTENSION = {
    "zip": ".hy1",
    "gzip": ".hy2",
    "lzma": ".hy3",
}

CHUNK_OPTIONS = [
    ("64 KB", 64 * 1024),
    ("128 KB", 128 * 1024),
    ("256 KB", 256 * 1024),
    ("512 KB", 512 * 1024),
    ("1 MB", 1024 * 1024),
    ("2 MB", 2 * 1024 * 1024),
    ("4 MB", 4 * 1024 * 1024),
    ("8 MB", 8 * 1024 * 1024),
    ("16 MB", 16 * 1024 * 1024),
]


def format_size(size):
    if size < 1024:
        return f"{size} B"

    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"

    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"

    return f"{size / (1024 * 1024 * 1024):.2f} GB"


def format_chunk(size):
    if size < 1024 * 1024:
        return f"{size // 1024} KB"

    return f"{size / (1024 * 1024):g} MB"


# ============================================================
# APP
# ============================================================

class HydraulicApp(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("HYDRAULIC")
        self.geometry("900x720")
        self.minsize(780, 650)
        self.configure(bg=BG)

        self.source = None
        self.analysis = None

        self.mode = "compress"
        self.busy = False
        self.cancel_event = None

        self.algorithm = tk.StringVar(value="gzip")
        self.pressure = tk.IntVar(value=5)
        self.chunk_index = tk.IntVar(value=4)

        self._setup_style()
        self._build()

    # ========================================================
    # STYLE
    # ========================================================

    def _setup_style(self):

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TButton",
            font=("Segoe UI", 10),
            padding=(15, 9),
            background=PANEL_2,
            foreground=TEXT,
            borderwidth=0,
        )

        style.map(
            "TButton",
            background=[
                ("active", "#292929"),
                ("disabled", "#141414"),
            ],
            foreground=[
                ("disabled", "#555555"),
            ],
        )

        style.configure(
            "Accent.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(20, 10),
            background=ACCENT,
            foreground="#111111",
            borderwidth=0,
        )

        style.map(
            "Accent.TButton",
            background=[
                ("active", "#e4ff71"),
                ("disabled", "#3a3f25"),
            ],
        )

        style.configure(
            "Cancel.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(20, 10),
            background="#321919",
            foreground=RED,
            borderwidth=0,
        )

        style.map(
            "Cancel.TButton",
            background=[
                ("active", "#452020"),
                ("disabled", "#211414"),
            ],
        )

        style.configure(
            "TCombobox",
            fieldbackground=PANEL_2,
            background=PANEL_2,
            foreground=TEXT,
            arrowcolor=TEXT,
            borderwidth=0,
            padding=8,
        )

        style.map(
            "TCombobox",
            fieldbackground=[("readonly", PANEL_2)],
            foreground=[("readonly", TEXT)],
        )

    # ========================================================
    # BUILD
    # ========================================================

    def _build(self):

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=BG)

        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=34,
            pady=(25, 12),
        )

        tk.Label(
            header,
            text="HYDRAULIC",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI Semibold", 25),
        ).pack(side="left")

        tk.Label(
            header,
            text="  compression, under pressure",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(
            side="left",
            pady=(9, 0),
        )

        self.main = tk.Frame(self, bg=BG)

        self.main.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=34,
            pady=(0, 20),
        )

        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        self._build_file_area()
        self._build_content()
        self._build_status()

    # ========================================================
    # FILE AREA
    # ========================================================

    def _build_file_area(self):

        self.file_frame = tk.Frame(
            self.main,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        self.file_frame.grid(
            row=0,
            column=0,
            sticky="ew",
        )

        self.file_frame.columnconfigure(0, weight=1)

        tk.Label(
            self.file_frame,
            text="FILE",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI Semibold", 9),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=24,
            pady=(18, 4),
        )

        self.file_name = tk.Label(
            self.file_frame,
            text="No file selected",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 15),
        )

        self.file_name.grid(
            row=1,
            column=0,
            sticky="w",
            padx=24,
        )

        self.file_size = tk.Label(
            self.file_frame,
            text="Choose a file to begin",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        )

        self.file_size.grid(
            row=2,
            column=0,
            sticky="w",
            padx=24,
            pady=(3, 18),
        )

        self.mode_label = tk.Label(
            self.file_frame,
            text="COMPRESS",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 8),
        )

        self.mode_label.grid(
            row=0,
            column=1,
            padx=(0, 24),
            pady=(18, 0),
        )

        self.choose_btn = ttk.Button(
            self.file_frame,
            text="CHOOSE FILE",
            command=self.choose_file,
        )

        self.choose_btn.grid(
            row=1,
            column=1,
            rowspan=2,
            padx=24,
        )

    # ========================================================
    # CONTENT
    # ========================================================

    def _build_content(self):

        if hasattr(self, "content"):
            self.content.destroy()

        self.content = tk.Frame(
            self.main,
            bg=BG,
        )

        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=(18, 0),
        )

        self.content.columnconfigure(0, weight=1)
        self.content.columnconfigure(1, weight=1)
        self.content.rowconfigure(0, weight=1)

        if self.mode == "compress":
            self._build_compression_analysis()
        else:
            self._build_decompression_info()

        self._build_controls()

    # ========================================================
    # COMPRESSION ANALYSIS
    # ========================================================

    def _build_compression_analysis(self):

        frame = tk.Frame(
            self.content,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8),
        )

        tk.Label(
            frame,
            text="ANALYSIS",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI Semibold", 9),
        ).pack(
            anchor="w",
            padx=22,
            pady=(20, 14),
        )

        self.entropy_label = tk.Label(
            frame,
            text="0.0000 / 8",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 22),
        )

        self.entropy_label.pack(
            anchor="w",
            padx=22,
        )

        tk.Label(
            frame,
            text="ENTROPY",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
            pady=(0, 14),
        )

        self.entropy_canvas = tk.Canvas(
            frame,
            height=8,
            bg=PANEL,
            highlightthickness=0,
        )

        self.entropy_canvas.pack(
            fill="x",
            padx=22,
        )

        self.entropy_canvas.create_rectangle(
            0,
            0,
            1,
            8,
            fill=ACCENT,
            outline="",
            tags="bar",
        )

        tk.Label(
            frame,
            text="COMPRESSIBILITY",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
            pady=(22, 3),
        )

        self.compressibility_label = tk.Label(
            frame,
            text="—",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 13),
        )

        self.compressibility_label.pack(
            anchor="w",
            padx=22,
        )

        self.recommendation_label = tk.Label(
            frame,
            text="Select a file to analyze it.",
            bg=PANEL,
            fg=MUTED,
            justify="left",
            wraplength=320,
            font=("Segoe UI", 9),
        )

        self.recommendation_label.pack(
            anchor="w",
            padx=22,
            pady=(18, 20),
        )

    # ========================================================
    # DECOMPRESSION INFO
    # ========================================================

    def _build_decompression_info(self):

        frame = tk.Frame(
            self.content,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8),
        )

        tk.Label(
            frame,
            text="HYDRAULIC ARCHIVE",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI Semibold", 9),
        ).pack(
            anchor="w",
            padx=22,
            pady=(20, 14),
        )

        extension = (
            self.source.suffix.lower()
            if self.source
            else ""
        )

        algorithm = EXT_TO_ALGORITHM.get(
            extension,
            "unknown",
        )

        tk.Label(
            frame,
            text=extension.upper(),
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 30),
        ).pack(
            anchor="w",
            padx=22,
        )

        tk.Label(
            frame,
            text="FORMAT",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
            pady=(0, 18),
        )

        tk.Label(
            frame,
            text=algorithm.upper(),
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 15),
        ).pack(
            anchor="w",
            padx=22,
        )

        tk.Label(
            frame,
            text="compression engine",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
            pady=(2, 18),
        )

        tk.Label(
            frame,
            text=(
                "The archive format determines "
                "the decompression engine automatically."
            ),
            bg=PANEL,
            fg=MUTED,
            justify="left",
            wraplength=320,
            font=("Segoe UI", 9),
        ).pack(
            anchor="w",
            padx=22,
        )

    # ========================================================
    # CONTROLS
    # ========================================================

    def _build_controls(self):

        frame = tk.Frame(
            self.content,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        frame.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(8, 0),
        )

        title = (
            "COMPRESSION"
            if self.mode == "compress"
            else "DECOMPRESSION"
        )

        tk.Label(
            frame,
            text=title,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI Semibold", 9),
        ).pack(
            anchor="w",
            padx=22,
            pady=(20, 14),
        )

        if self.mode == "compress":
            self._build_compression_controls(frame)
        else:
            self._build_decompression_controls(frame)

    def _build_compression_controls(self, frame):

        tk.Label(
            frame,
            text="ENGINE",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
        )

        combo = ttk.Combobox(
            frame,
            textvariable=self.algorithm,
            values=("zip", "gzip", "lzma"),
            state="readonly",
        )

        combo.pack(
            fill="x",
            padx=22,
            pady=(5, 15),
        )

        tk.Label(
            frame,
            text="PRESSURE",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
        )

        self.pressure_scale = tk.Scale(
            frame,
            from_=1,
            to=9,
            orient="horizontal",
            variable=self.pressure,
            showvalue=False,
            resolution=1,
            bg=PANEL,
            troughcolor=BORDER,
            activebackground=ACCENT,
            highlightthickness=0,
            bd=0,
            command=self._pressure_changed,
        )

        self.pressure_scale.pack(
            fill="x",
            padx=18,
        )

        self.pressure_label = tk.Label(
            frame,
            text="MEDIUM · 5",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 10),
        )

        self.pressure_label.pack(
            anchor="w",
            padx=22,
            pady=(0, 15),
        )

        self._build_chunk_slider(frame)

        self.compress_btn = ttk.Button(
            frame,
            text="COMPRESS",
            style="Accent.TButton",
            command=self.start_compression,
        )

        self.compress_btn.pack(
            fill="x",
            padx=22,
            pady=(4, 8),
        )

        self._build_cancel_button(frame)

        self.benchmark_btn = ttk.Button(
            frame,
            text="BENCHMARK",
            command=self.start_benchmark,
        )

        self.benchmark_btn.pack(
            fill="x",
            padx=22,
            pady=(8, 20),
        )

    def _build_decompression_controls(self, frame):

        extension = (
            self.source.suffix.lower()
            if self.source
            else ""
        )

        algorithm = EXT_TO_ALGORITHM.get(
            extension,
            "unknown",
        )

        tk.Label(
            frame,
            text="ENGINE",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
        )

        tk.Label(
            frame,
            text=algorithm.upper(),
            bg=PANEL_2,
            fg=ACCENT,
            font=("Segoe UI Semibold", 12),
            anchor="w",
        ).pack(
            fill="x",
            padx=22,
            pady=(5, 20),
            ipady=8,
        )

        self._build_chunk_slider(frame)

        self.decompress_btn = ttk.Button(
            frame,
            text="DECOMPRESS",
            style="Accent.TButton",
            command=self.start_decompression,
        )

        self.decompress_btn.pack(
            fill="x",
            padx=22,
            pady=(4, 8),
        )

        self._build_cancel_button(frame)

        tk.Label(
            frame,
            text="Output will be restored beside the archive.",
            bg=PANEL,
            fg="#555555",
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
            pady=(10, 20),
        )

    def _build_chunk_slider(self, frame):

        tk.Label(
            frame,
            text="I/O BUFFER",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=22,
        )

        self.chunk_scale = tk.Scale(
            frame,
            from_=0,
            to=len(CHUNK_OPTIONS) - 1,
            orient="horizontal",
            variable=self.chunk_index,
            showvalue=False,
            resolution=1,
            bg=PANEL,
            troughcolor=BORDER,
            activebackground=ACCENT,
            highlightthickness=0,
            bd=0,
            command=self._chunk_changed,
        )

        self.chunk_scale.pack(
            fill="x",
            padx=18,
        )

        name, _ = CHUNK_OPTIONS[
            self.chunk_index.get()
        ]

        self.chunk_label = tk.Label(
            frame,
            text=f"{name}  ·  streaming buffer",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 10),
        )

        self.chunk_label.pack(
            anchor="w",
            padx=22,
            pady=(0, 20),
        )

    def _build_cancel_button(self, frame):

        self.cancel_btn = ttk.Button(
            frame,
            text="CANCEL",
            style="Cancel.TButton",
            command=self.cancel_operation,
            state="disabled",
        )

        self.cancel_btn.pack(
            fill="x",
            padx=22,
            pady=(0, 8),
        )

    # ========================================================
    # STATUS
    # ========================================================

    def _build_status(self):

        self.status = tk.Label(
            self.main,
            text="READY",
            bg=BG,
            fg=MUTED,
            anchor="w",
            font=("Segoe UI", 8),
        )

        self.status.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

    # ========================================================
    # FILE LOADING
    # ========================================================

    def choose_file(self):

        if self.busy:
            return

        path = filedialog.askopenfilename(
            title="Choose a file"
        )

        if not path:
            return

        self.load_file(path)

    def load_file(self, path):

        self.source = Path(path)
        self.analysis = None

        extension = self.source.suffix.lower()

        if extension in EXT_TO_ALGORITHM:
            self.mode = "decompress"
            self.algorithm.set(
                EXT_TO_ALGORITHM[extension]
            )
        else:
            self.mode = "compress"

        self.file_name.config(
            text=self.source.name
        )

        try:
            self.file_size.config(
                text=format_size(
                    self.source.stat().st_size
                )
            )
        except OSError:
            self.file_size.config(
                text="Unknown size"
            )

        self.mode_label.config(
            text=(
                "DECOMPRESS"
                if self.mode == "decompress"
                else "COMPRESS"
            )
        )

        self.mode_label.config(
            fg=(
                RED
                if self.mode == "decompress"
                else ACCENT
            )
        )

        self.status.config(
            text=(
                "READY TO DECOMPRESS"
                if self.mode == "decompress"
                else "ANALYZING..."
            ),
            fg=(
                RED
                if self.mode == "decompress"
                else TEXT
            ),
        )

        self._build_content()

        self.choose_btn.config(
            state="normal"
        )

        if self.mode == "compress":
            self._analyze_file()

    # ========================================================
    # ANALYSIS
    # ========================================================

    def _analyze_file(self):

        self.choose_btn.config(
            state="disabled"
        )

        threading.Thread(
            target=self._analyze_worker,
            daemon=True,
        ).start()

    def _analyze_worker(self):

        try:

            info = engine.analyse(
                self.source
            )

            recommendation = engine.reccomend_algo(
                info
            )

            self.after(
                0,
                lambda: self._analysis_finished(
                    info,
                    recommendation,
                ),
            )

        except Exception as exc:

            self.after(
                0,
                lambda: self._error(
                    "Analysis failed",
                    exc,
                ),
            )

    def _analysis_finished(
        self,
        info,
        recommendation,
    ):

        self.analysis = info

        self.choose_btn.config(
            state="normal"
        )

        self.entropy_label.config(
            text=f"{info.entropy:.4f} / 8"
        )

        self.compressibility_label.config(
            text=info.compressibility.upper()
        )

        self.entropy_canvas.update_idletasks()

        width = max(
            1,
            self.entropy_canvas.winfo_width()
        )

        ratio = min(
            1,
            max(
                0,
                info.entropy / 8
            )
        )

        self.entropy_canvas.delete(
            "bar"
        )

        self.entropy_canvas.create_rectangle(
            0,
            0,
            width * ratio,
            8,
            fill=ACCENT,
            outline="",
            tags="bar",
        )

        algorithm = recommendation.get(
            "algorithm"
        )

        if algorithm in (
            "zip",
            "gzip",
            "lzma",
        ):
            self.algorithm.set(
                algorithm
            )

        pressure = recommendation.get(
            "pressure",
            "medium",
        )

        self.pressure.set(
            engine.pressure_to_level(
                pressure
            )
        )

        self._update_pressure_label()

        reason = recommendation.get(
            "reason",
            "",
        )

        self.recommendation_label.config(
            text=(
                f"RECOMMENDED\n"
                f"{algorithm.upper() if algorithm else 'NONE'}"
                f" · {pressure.upper()}\n\n"
                f"{reason}"
            )
        )

        self.status.config(
            text="READY TO COMPRESS",
            fg=MUTED,
        )

    # ========================================================
    # SLIDERS
    # ========================================================

    def _pressure_changed(self, _=None):

        self._update_pressure_label()

    def _update_pressure_label(self):

        level = self.pressure.get()

        if level <= 2:
            name = "LOW"
        elif level <= 6:
            name = "MEDIUM"
        elif level <= 8:
            name = "HIGH"
        else:
            name = "MAXIMUM"

        self.pressure_label.config(
            text=f"{name} · {level}"
        )

    def _chunk_changed(self, _=None):

        index = self.chunk_index.get()

        index = max(
            0,
            min(
                index,
                len(CHUNK_OPTIONS) - 1,
            ),
        )

        name, _ = CHUNK_OPTIONS[index]

        self.chunk_label.config(
            text=f"{name}  ·  streaming buffer"
        )

    def _get_chunk_size(self):

        index = self.chunk_index.get()

        index = max(
            0,
            min(
                index,
                len(CHUNK_OPTIONS) - 1,
            ),
        )

        return CHUNK_OPTIONS[index][1]

    # ========================================================
    # COMPRESSION
    # ========================================================

    def start_compression(self):

        if self.mode != "compress":
            return

        if not self.source:
            return

        if not self.analysis:
            return

        if self.busy:
            return

        algorithm = self.algorithm.get()
        level = self.pressure.get()
        chunk_size = self._get_chunk_size()

        self.busy = True
        self.cancel_event = threading.Event()

        self.compress_btn.config(
            state="disabled"
        )

        self.benchmark_btn.config(
            state="disabled"
        )

        self.choose_btn.config(
            state="disabled"
        )

        self.cancel_btn.config(
            state="normal"
        )

        extension = ALGORITHM_TO_EXTENSION[
            algorithm
        ]

        output = self.source.with_name(
            self.source.stem
            + "_hydraulic"
            + extension
        )

        self.status.config(
            text="COMPRESSING · 0%",
            fg=ACCENT,
        )

        threading.Thread(
            target=self._compression_worker,
            args=(
                algorithm,
                level,
                chunk_size,
                output,
            ),
            daemon=True,
        ).start()

    def _compression_worker(
        self,
        algorithm,
        level,
        chunk_size,
        output,
    ):

        try:

            result = engine.compress(
                self.source,
                output,
                algorithm=algorithm,
                pressure=level,
                chunk_size=chunk_size,
                progress_callback=lambda p: self.after(
                    0,
                    self._update_progress,
                    p.percent,
                ),
                cancel_event=self.cancel_event,
            )

            self.after(
                0,
                lambda: self._compression_finished(
                    result
                ),
            )

        except engine.HydraulicCancelled:

            self.after(
                0,
                self._cancelled,
            )

        except Exception as exc:

            self.after(
                0,
                lambda: self._error(
                    "Compression failed",
                    exc,
                ),
            )

    # ========================================================
    # DECOMPRESSION
    # ========================================================

    def start_decompression(self):

        if self.mode != "decompress":
            return

        if not self.source:
            return

        if self.busy:
            return

        extension = self.source.suffix.lower()

        algorithm = EXT_TO_ALGORITHM.get(
            extension
        )

        if not algorithm:
            messagebox.showerror(
                "HYDRAULIC",
                "Unknown HYDRAULIC archive type.",
            )
            return

        chunk_size = self._get_chunk_size()

        output = self._decompression_output()

        self.busy = True
        self.cancel_event = threading.Event()

        self.decompress_btn.config(
            state="disabled"
        )

        self.choose_btn.config(
            state="disabled"
        )

        self.cancel_btn.config(
            state="normal"
        )

        self.status.config(
            text="DECOMPRESSING · 0%",
            fg=ACCENT,
        )

        threading.Thread(
            target=self._decompression_worker,
            args=(
                algorithm,
                chunk_size,
                output,
            ),
            daemon=True,
        ).start()

    def _decompression_output(self):

        name = self.source.stem

        if name.endswith("_hydraulic"):
            name = name[:-10]

        else:
            name += "_restored"

        return self.source.with_name(
            name
        )

    def _decompression_worker(
        self,
        algorithm,
        chunk_size,
        output,
    ):

        try:

            engine.decompress(
                self.source,
                output,
                algorithm,
                progress_callback=lambda p: self.after(
                    0,
                    self._update_progress,
                    p.percent,
                ),
                cancel_event=self.cancel_event,
                chunk_size=chunk_size,
            )

            self.after(
                0,
                lambda: self._decompression_finished(
                    output,
                    algorithm,
                ),
            )

        except engine.HydraulicCancelled:

            self.after(
                0,
                self._cancelled,
            )

        except Exception as exc:

            self.after(
                0,
                lambda: self._error(
                    "Decompression failed",
                    exc,
                ),
            )

    def _decompression_finished(
        self,
        output,
        algorithm,
    ):

        self.busy = False
        self.cancel_event = None

        self.decompress_btn.config(
            state="normal"
        )

        self.choose_btn.config(
            state="normal"
        )

        self.cancel_btn.config(
            state="disabled"
        )

        self._show_decompression_result(
            output,
            algorithm,
        )

    # ========================================================
    # PROGRESS
    # ========================================================

    def _update_progress(self, percent):

        if not self.busy:
            return

        operation = (
            "COMPRESSING"
            if self.mode == "compress"
            else "DECOMPRESSING"
        )

        self.status.config(
            text=f"{operation} · {percent:.1f}%",
            fg=ACCENT,
        )

    # ========================================================
    # CANCEL
    # ========================================================

    def cancel_operation(self):

        if not self.busy:
            return

        if self.cancel_event:
            self.cancel_event.set()

        self.cancel_btn.config(
            state="disabled"
        )

        self.status.config(
            text="CANCELLING...",
            fg=RED,
        )

    def _cancelled(self):

        self.busy = False
        self.cancel_event = None

        self.choose_btn.config(
            state="normal"
        )

        self.cancel_btn.config(
            state="disabled"
        )

        if self.mode == "compress":

            self.compress_btn.config(
                state="normal"
            )

            self.benchmark_btn.config(
                state="normal"
            )

        else:

            self.decompress_btn.config(
                state="normal"
            )

        self.status.config(
            text="CANCELLED",
            fg=RED,
        )

    # ========================================================
    # COMPRESSION RESULT
    # ========================================================

    def _compression_finished(
        self,
        result,
    ):

        self.busy = False
        self.cancel_event = None

        self.compress_btn.config(
            state="normal"
        )

        self.benchmark_btn.config(
            state="normal"
        )

        self.choose_btn.config(
            state="normal"
        )

        self.cancel_btn.config(
            state="disabled"
        )

        self._show_compression_result(
            result
        )

    def _show_compression_result(
        self,
        result,
    ):

        for widget in self.content.winfo_children():
            widget.destroy()

        frame = tk.Frame(
            self.content,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        frame.pack(
            fill="both",
            expand=True,
        )

        tk.Label(
            frame,
            text="COMPRESSION COMPLETE",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 13),
        ).pack(
            anchor="w",
            padx=28,
            pady=(28, 4),
        )

        tk.Label(
            frame,
            text=Path(result.output).name,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(
            anchor="w",
            padx=28,
        )

        sizes = tk.Frame(
            frame,
            bg=PANEL,
        )

        sizes.pack(
            anchor="w",
            padx=28,
            pady=(35, 8),
        )

        tk.Label(
            sizes,
            text=format_size(
                result.original_size
            ),
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 20),
        ).pack(side="left")

        tk.Label(
            sizes,
            text="  →  ",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 18),
        ).pack(side="left")

        tk.Label(
            sizes,
            text=format_size(
                result.compressed_size
            ),
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 20),
        ).pack(side="left")

        tk.Label(
            frame,
            text=(
                f"{result.reduction_percent:.2f}% REDUCTION"
            ),
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 11),
        ).pack(
            anchor="w",
            padx=28,
        )

        stats = tk.Frame(
            frame,
            bg=PANEL,
        )

        stats.pack(
            fill="x",
            padx=28,
            pady=25,
        )

        self._stat(
            stats,
            "ENGINE",
            result.algorithm.upper(),
            0,
        )

        self._stat(
            stats,
            "LEVEL",
            str(result.level),
            1,
        )

        self._stat(
            stats,
            "BUFFER",
            format_chunk(
                self._get_chunk_size()
            ),
            2,
        )

        self._stat(
            stats,
            "SAVED",
            format_size(
                result.saved_bytes
            ),
            3,
        )

        self._stat(
            stats,
            "RATIO",
            f"{result.compression_ratio:.2f}:1",
            4,
        )

        self._stat(
            stats,
            "VERIFIED",
            "YES ✓"
            if result.verified
            else "NO ✗",
            5,
        )

        buttons = tk.Frame(
            frame,
            bg=PANEL,
        )

        buttons.pack(
            anchor="w",
            padx=28,
        )

        ttk.Button(
            buttons,
            text="OPEN OUTPUT",
            command=lambda: self._open_output(
                result.output
            ),
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            buttons,
            text="BACK",
            command=self._reset_content,
        ).pack(
            side="left",
        )

        self.status.config(
            text="COMPLETE",
            fg=ACCENT,
        )

    # ========================================================
    # DECOMPRESSION RESULT
    # ========================================================

    def _show_decompression_result(
        self,
        output,
        algorithm,
    ):

        for widget in self.content.winfo_children():
            widget.destroy()

        frame = tk.Frame(
            self.content,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        frame.pack(
            fill="both",
            expand=True,
        )

        tk.Label(
            frame,
            text="DECOMPRESSION COMPLETE",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 13),
        ).pack(
            anchor="w",
            padx=28,
            pady=(28, 4),
        )

        tk.Label(
            frame,
            text=Path(output).name,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(
            anchor="w",
            padx=28,
        )

        try:
            size = output.stat().st_size
            size_text = format_size(size)
        except OSError:
            size_text = "Unknown size"

        tk.Label(
            frame,
            text=size_text,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 24),
        ).pack(
            anchor="w",
            padx=28,
            pady=(35, 5),
        )

        tk.Label(
            frame,
            text=f"RESTORED USING {algorithm.upper()}",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 10),
        ).pack(
            anchor="w",
            padx=28,
        )

        tk.Label(
            frame,
            text=(
                f"BUFFER · "
                f"{format_chunk(self._get_chunk_size())}"
            ),
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(
            anchor="w",
            padx=28,
            pady=(4, 25),
        )

        ttk.Button(
            frame,
            text="OPEN OUTPUT",
            command=lambda: self._open_output(
                output
            ),
        ).pack(
            anchor="w",
            padx=28,
        )

        ttk.Button(
            frame,
            text="BACK",
            command=self._reset_content,
        ).pack(
            anchor="w",
            padx=28,
            pady=8,
        )

        self.status.config(
            text="COMPLETE",
            fg=ACCENT,
        )

    # ========================================================
    # BENCHMARK
    # ========================================================

    def start_benchmark(self):

        if self.mode != "compress":
            return

        if not self.source:
            return

        if self.busy:
            return

        self.busy = True
        self.cancel_event = threading.Event()

        chunk_size = self._get_chunk_size()

        self.compress_btn.config(
            state="disabled"
        )

        self.benchmark_btn.config(
            state="disabled"
        )

        self.choose_btn.config(
            state="disabled"
        )

        self.cancel_btn.config(
            state="normal"
        )

        self.status.config(
            text=(
                f"BENCHMARKING · "
                f"{format_chunk(chunk_size)} BUFFER"
            ),
            fg=ACCENT,
        )

        threading.Thread(
            target=self._benchmark_worker,
            args=(chunk_size,),
            daemon=True,
        ).start()

    def _benchmark_worker(
        self,
        chunk_size,
    ):

        try:

            results = engine.benchmark(
                self.source,
                algorithms=[
                    "zip",
                    "gzip",
                    "lzma",
                ],
                levels=[
                    1,
                    5,
                    9,
                ],
                cancel_event=self.cancel_event,
                chunk_size=chunk_size,
            )

            self.after(
                0,
                lambda: self._show_benchmark(
                    results,
                    chunk_size,
                ),
            )

        except engine.HydraulicCancelled:

            self.after(
                0,
                self._cancelled,
            )

        except Exception as exc:

            self.after(
                0,
                lambda: self._error(
                    "Benchmark failed",
                    exc,
                ),
            )

    def _show_benchmark(
        self,
        results,
        chunk_size,
    ):

        self.busy = False
        self.cancel_event = None

        self.compress_btn.config(
            state="normal"
        )

        self.benchmark_btn.config(
            state="normal"
        )

        self.choose_btn.config(
            state="normal"
        )

        self.cancel_btn.config(
            state="disabled"
        )

        for widget in self.content.winfo_children():
            widget.destroy()

        frame = tk.Frame(
            self.content,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        frame.pack(
            fill="both",
            expand=True,
        )

        tk.Label(
            frame,
            text="BENCHMARK",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 13),
        ).pack(
            anchor="w",
            padx=24,
            pady=(22, 2),
        )

        tk.Label(
            frame,
            text=(
                f"BUFFER · "
                f"{format_chunk(chunk_size)}"
            ),
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=24,
            pady=(0, 18),
        )

        table = tk.Frame(
            frame,
            bg=PANEL,
        )

        table.pack(
            fill="x",
            padx=24,
        )

        headers = [
            "ENGINE",
            "LEVEL",
            "SIZE",
            "REDUCTION",
            "TIME",
        ]

        for col, text in enumerate(headers):

            tk.Label(
                table,
                text=text,
                bg=PANEL,
                fg=MUTED,
                font=("Segoe UI Semibold", 8),
                anchor="w",
            ).grid(
                row=0,
                column=col,
                sticky="ew",
                padx=5,
                pady=(0, 8),
            )

        valid = []

        for row, result in enumerate(
            results,
            start=1,
        ):

            if result.error:

                values = [
                    result.algorithm.upper(),
                    str(result.level),
                    "ERROR",
                    "",
                    "",
                ]

            else:

                valid.append(result)

                values = [
                    result.algorithm.upper(),
                    str(result.level),
                    format_size(
                        result.compressed_size
                    ),
                    f"{result.reduction_percent:.2f}%",
                    f"{result.elapsed_seconds:.3f}s",
                ]

            for col, value in enumerate(values):

                tk.Label(
                    table,
                    text=value,
                    bg=(
                        PANEL_2
                        if row % 2 == 0
                        else PANEL
                    ),
                    fg=(
                        RED
                        if result.error
                        else TEXT
                    ),
                    font=("Segoe UI", 9),
                    anchor="w",
                ).grid(
                    row=row,
                    column=col,
                    sticky="ew",
                    padx=5,
                    pady=3,
                )

        for col in range(5):
            table.columnconfigure(
                col,
                weight=1,
            )

        if valid:

            smallest = min(
                valid,
                key=lambda r: r.compressed_size,
            )

            fastest = min(
                valid,
                key=lambda r: r.elapsed_seconds,
            )

            tk.Label(
                frame,
                text=(
                    "BEST SIZE   "
                    f"{smallest.algorithm.upper()} "
                    f"{smallest.level}   ·   "
                    f"{format_size(smallest.compressed_size)}"
                ),
                bg=PANEL,
                fg=ACCENT,
                font=("Segoe UI Semibold", 10),
            ).pack(
                anchor="w",
                padx=24,
                pady=(24, 0),
            )

            tk.Label(
                frame,
                text=(
                    "FASTEST     "
                    f"{fastest.algorithm.upper()} "
                    f"{fastest.level}   ·   "
                    f"{fastest.elapsed_seconds:.3f}s"
                ),
                bg=PANEL,
                fg=MUTED,
                font=("Segoe UI", 9),
            ).pack(
                anchor="w",
                padx=24,
                pady=(5, 0),
            )

        ttk.Button(
            frame,
            text="BACK",
            command=self._reset_content,
        ).pack(
            anchor="w",
            padx=24,
            pady=18,
        )

        self.status.config(
            text="BENCHMARK COMPLETE",
            fg=ACCENT,
        )

    # ========================================================
    # HELPERS
    # ========================================================

    def _stat(
        self,
        parent,
        title,
        value,
        column,
    ):

        box = tk.Frame(
            parent,
            bg=PANEL_2,
        )

        box.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=3,
            pady=3,
        )

        parent.columnconfigure(
            column,
            weight=1,
        )

        tk.Label(
            box,
            text=title,
            bg=PANEL_2,
            fg=MUTED,
            font=("Segoe UI", 7),
        ).pack(
            anchor="w",
            padx=10,
            pady=(9, 0),
        )

        tk.Label(
            box,
            text=value,
            bg=PANEL_2,
            fg=TEXT,
            font=("Segoe UI Semibold", 9),
        ).pack(
            anchor="w",
            padx=10,
            pady=(2, 9),
        )

    def _reset_content(self):

        self._build_content()

        if self.mode == "compress" and self.analysis:

            try:
                recommendation = engine.reccomend_algo(
                    self.analysis
                )

                self._analysis_finished(
                    self.analysis,
                    recommendation,
                )

            except Exception:
                pass

    def _open_output(self, path):

        try:
            os.startfile(str(path))

        except Exception as exc:

            messagebox.showerror(
                "HYDRAULIC",
                f"Could not open output:\n{exc}",
            )

    def _error(self, title, exc):

        self.busy = False
        self.cancel_event = None

        self.choose_btn.config(
            state="normal"
        )

        if hasattr(self, "compress_btn"):
            self.compress_btn.config(
                state="normal"
            )

        if hasattr(self, "decompress_btn"):
            self.decompress_btn.config(
                state="normal"
            )

        if hasattr(self, "benchmark_btn"):
            self.benchmark_btn.config(
                state="normal"
            )

        if hasattr(self, "cancel_btn"):
            self.cancel_btn.config(
                state="disabled"
            )

        self.status.config(
            text="ERROR",
            fg=RED,
        )

        messagebox.showerror(
            title,
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    app = HydraulicApp()
    app.mainloop()