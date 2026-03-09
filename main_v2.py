import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import time
import math
from statistics import mean
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception as _e:
    Figure = None
    FigureCanvasTkAgg = None

from engines import engine_naive, engine_rk, engine_kmp, engine_bm, engine_aho, engine_bb, engine_kmp_nv


class PatternMatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CSC755M - Project 2 - 2D Pattern Matcher")
        self.root.geometry("1600x950")
        self.root.configure(bg="#0f1117")

        # --- State Management ---
        self.matrix = []
        self.pattern = []
        self.steps = []
        self.step_idx = 0
        self.is_playing = False
        self.mode = "single"
        self.cell_widgets = {}
        self.race_engines = {}
        self.runtime = 0.0

        self.setup_styles()
        self.create_layout()
        self.load_preset("5x5 Simple")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#0f1117")
        style.configure("TLabel", background="#13151f", foreground="#7c85c0", font=("Segoe UI", 9, "bold"))
        style.configure("TCombobox", fieldbackground="#0f1117", background="#2e3250", foreground="#e0e0e0")

    def create_layout(self):
        # --- LEFT SIDEBAR ---
        self.sidebar = tk.Frame(self.root, bg="#13151f", width=320, padx=15, pady=15)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # 🎁 Presets (Restored)
        tk.Label(self.sidebar, text="🎁 LOAD PRESETS").pack(anchor="w")
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(self.sidebar, textvariable=self.preset_var, state="readonly")
        self.preset_combo['values'] = (
                "5x5 Simple",
                "12x12 Random Int",
                "8x8 Binary (0/1)",
                "Pattern Not Found",
                "Naive Friendly",
                "RK Friendly",
                "KMP Friendly",
                "BM Friendly",
                "AHO Friendly",
                "KMP+Naive Friendly",
                "Bird-Baker Friendly",
                "Worst Case Many Matches"
                )
        
        self.preset_combo.pack(fill="x", pady=(5, 15))
        self.preset_combo.bind("<<ComboboxSelected>>", lambda e: self.load_preset(self.preset_var.get()))

        tk.Label(self.sidebar, text="INPUT MATRIX").pack(anchor="w")
        self.matrix_input = tk.Text(self.sidebar, height=6, bg="#0f1117", fg="#e0e0e0", bd=0, font=("Consolas", 10))
        self.matrix_input.pack(fill="x", pady=(5, 10))

        tk.Label(self.sidebar, text="SUB-PATTERN").pack(anchor="w")
        self.pattern_input = tk.Text(self.sidebar, height=3, bg="#0f1117", fg="#e0e0e0", bd=0, font=("Consolas", 10))
        self.pattern_input.pack(fill="x", pady=(5, 10))

        self.algo_var = tk.StringVar(value="naive")
        for text, val in [
            ("Naive", "naive"),
            ("Rabin-Karp (2D Rolling Hash)", "rk"),
            ("KMP (Row-Filter+Verify)", "kmp"),
            ("Boyer-Moore (Row-Filter+Verify)", "bm"),
            ("Aho-Corasick (Row-AC+Align)", "aho"),
            ("Bird-Baker (KMP horiz + AC vert)", "bb"),
            ("KMP horiz + Naive vert", "kmp_nv")
        ]:
            tk.Radiobutton(self.sidebar, text=text, variable=self.algo_var, value=val, bg="#13151f", fg="#ccc", selectcolor="#7c3aed").pack(anchor="w")

        # Results Dashboard
        self.results_card = tk.Frame(self.sidebar, bg="#1a1d2e", pady=15, padx=10, highlightthickness=1, highlightbackground="#2e3250")
        self.results_card.pack(fill="x", pady=15)
        self.stat_matches = self.create_stat_box(self.results_card, "Matches", 0, 0)
        self.stat_comps = self.create_stat_box(self.results_card, "Comparisons", 0, 1)
        self.stat_time = self.create_stat_box(self.results_card, "Time (ms)", 1, 0)
        self.stat_steps = self.create_stat_box(self.results_card, "Steps", 1, 1)

        tk.Button(self.sidebar, text="▶ RUN SINGLE MODE", bg="#7c3aed", fg="white", font=("Segoe UI", 10, "bold"), command=self.run_single, relief="flat").pack(fill="x", pady=5)
        tk.Button(self.sidebar, text="🏁 START MULTI-RACE", bg="#22c55e", fg="white", font=("Segoe UI", 10, "bold"), command=self.run_multi_race, relief="flat").pack(fill="x")
        tk.Button(self.sidebar, text="📈 GROWTH CHART", bg="#0ea5e9", fg="white", font=("Segoe UI", 10, "bold"), command=self.show_growth_chart, relief="flat").pack(fill="x", pady=(5, 0))

        # --- CENTER + TRACELOG in a resizable PanedWindow ---
        self.h_pane = ttk.PanedWindow(self.root, orient="horizontal")
        self.h_pane.pack(side="left", expand=True, fill="both")

        # --- CENTER ---
        self.main_area = tk.Frame(self.h_pane, bg="#0f1117")
        self.h_pane.add(self.main_area, weight=3)

        self.ctrl_bar = tk.Frame(self.main_area, bg="#1a1d2e", padx=10, pady=10)
        self.ctrl_bar.pack(fill="x")
        self.play_btn = tk.Button(self.ctrl_bar, text="▶ Play", width=8, command=self.toggle_play, bg="#0f1117", fg="white")
        self.play_btn.pack(side="left", padx=5)
        self.status_lbl = tk.Label(self.ctrl_bar, text="System Ready", bg="#1a1d2e", fg="#a78bfa")
        self.status_lbl.pack(side="left", padx=20)

        # Scrollable visualization area
        scroll_outer = tk.Frame(self.main_area, bg="#0f1117")
        scroll_outer.pack(fill="both", expand=True)

        v_scroll = tk.Scrollbar(scroll_outer, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        h_scroll = tk.Scrollbar(scroll_outer, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")

        self._viz_canvas = tk.Canvas(
            scroll_outer, bg="#0f1117",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            highlightthickness=0,
        )
        self._viz_canvas.pack(side="left", fill="both", expand=True)
        v_scroll.config(command=self._viz_canvas.yview)
        h_scroll.config(command=self._viz_canvas.xview)

        self.display_container = tk.Frame(self._viz_canvas, bg="#0f1117", padx=20, pady=20)
        self._viz_win = self._viz_canvas.create_window((0, 0), window=self.display_container, anchor="nw")

        self.display_container.bind("<Configure>", self._on_display_configure)
        self._viz_canvas.bind("<Configure>", self._on_viz_canvas_configure)
        # Mousewheel scrolling (bind on canvas and inner frame so it works wherever cursor is)
        for widget in (self._viz_canvas, self.display_container):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel)   # Linux scroll up
            widget.bind("<Button-5>", self._on_mousewheel)   # Linux scroll down

        # --- RIGHT SIDEBAR (tracelog) — draggable via PanedWindow sash ---
        self.log_sidebar = tk.Frame(self.h_pane, bg="#13151f", padx=15, pady=15)
        self.h_pane.add(self.log_sidebar, weight=1)

        self.match_log = tk.Listbox(self.log_sidebar, bg="#0f1117", fg="#22c55e", bd=0, font=("Consolas", 9), highlightthickness=0)
        self.match_log.pack(fill="both", expand=True)

        log_btns = tk.Frame(self.log_sidebar, bg="#13151f", pady=10)
        log_btns.pack(fill="x")
        tk.Button(log_btns, text="Clear", bg="#333", fg="white", command=lambda: self.match_log.delete(0, tk.END)).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(log_btns, text="Export", bg="#333", fg="white", command=self.export_log).pack(side="left", expand=True, fill="x", padx=2)

        # Set initial sash so tracelog starts at ~280 px wide
        self.root.after(50, self._set_initial_sash)

    def create_stat_box(self, parent, label, r, c):
        f = tk.Frame(parent, bg="#0f1117", padx=5, pady=5, highlightthickness=1, highlightbackground="#2e3250")
        f.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
        val_lbl = tk.Label(f, text="0", bg="#0f1117", fg="#a78bfa", font=("Segoe UI", 14, "bold"))
        val_lbl.pack()
        tk.Label(f, text=label, bg="#0f1117", fg="#666", font=("Segoe UI", 7)).pack()
        return val_lbl

    # --- SCROLL / SASH HELPERS ---

    def _on_display_configure(self, event):
        self._viz_canvas.configure(scrollregion=self._viz_canvas.bbox("all"))

    def _on_viz_canvas_configure(self, event):
        # Stretch the inner frame to fill the canvas width so grids aren't left-pinned
        self._viz_canvas.itemconfig(self._viz_win, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:          # Linux scroll up
            self._viz_canvas.yview_scroll(-1, "units")
        elif event.num == 5:        # Linux scroll down
            self._viz_canvas.yview_scroll(1, "units")
        else:                       # Windows / macOS
            self._viz_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _set_initial_sash(self):
        total = self.h_pane.winfo_width()
        if total > 400:
            self.h_pane.sashpos(0, total - 280)

    # --- BENCHMARK HELPERS ---

    def _benchmark_engine(self, engine_func, M, P, min_total_ms=25.0, max_runs=200):
        # Warm up once to reduce one-time interpreter/UI effects on tiny inputs.
        engine_func(M, P)
        runs = 0
        total_ms = 0.0
        last_steps = []
        while runs < max_runs and total_ms < min_total_ms:
            t0 = time.perf_counter()
            last_steps = engine_func(M, P)
            total_ms += (time.perf_counter() - t0) * 1000.0
            runs += 1
        avg_ms = total_ms / runs if runs else 0.0
        return last_steps, avg_ms, runs

    def _engine_summary(self, engine_func, M, P):
        steps, elapsed_ms, _runs = self._benchmark_engine(engine_func, M, P)
        if not steps:
            return 0, 0, elapsed_ms
        last = steps[-1]
        return int(last.get('c', 0)), int(last.get('m', 0)), elapsed_ms

    # --- GROWTH CHART ---

    def show_growth_chart(self):
        if Figure is None or FigureCanvasTkAgg is None:
            messagebox.showerror("Error", "Matplotlib is not installed. Please install it with:\npip install matplotlib")
            return
        if not self.prepare_run():
            return

        P = self.pattern
        pr = len(P) if P else 2
        pc = len(P[0]) if P and P[0] else 2

        # Fixed size range independent of the user's matrix.
        # Each point uses a fresh independent random N×N matrix so curves
        # reflect true algorithmic scaling, not a repeated top-left crop.
        min_n = max(pr, pc) + 1          # smallest valid matrix for this pattern
        all_sizes = [5, 8, 10, 12, 15, 18, 20, 25, 30, 35, 40]
        sizes = [n for n in all_sizes if n >= min_n]
        if not sizes:
            messagebox.showerror("Pattern too large",
                f"Pattern is {pr}×{pc}. Reduce it to use the growth chart.")
            return

        # Derive the alphabet from the user's current matrix so random matrices
        # use the same value range (keeps match density realistic).
        flat = [v for row in self.matrix for v in row]
        lo, hi = (min(flat), max(flat)) if flat else (1, 9)
        if lo == hi:
            lo, hi = lo, lo + 8   # avoid degenerate single-value alphabet

        engines = [
            ("Naive",  engine_naive),
            ("RK",     engine_rk),
            ("KMP",    engine_kmp),
            ("BM",     engine_bm),
            ("AHO",    engine_aho),
            ("BB",     engine_bb),
            ("KMP_NV", engine_kmp_nv),
        ]

        comps_series = {name: [] for name, _ in engines}
        time_series  = {name: [] for name, _ in engines}

        rng = random.Random(42)   # fixed seed → reproducible chart
        for n in sizes:
            M_rand = [[rng.randint(lo, hi) for _ in range(n)] for _ in range(n)]
            for name, func in engines:
                c, _m, t = self._engine_summary(func, M_rand, P)
                comps_series[name].append(c)
                time_series[name].append(t)

        win = tk.Toplevel(self.root)
        win.title("Growth Chart: Comparisons & Execution Time vs Matrix Size")
        win.geometry("1100x820")
        win.configure(bg="#0f1117")

        header = tk.Label(
            win,
            text="Growth Chart: independent random N×N matrices, fixed pattern from input",
            bg="#0f1117", fg="#e0e0e0", font=("Segoe UI", 12, "bold")
        )
        header.pack(pady=(10, 2))

        subheader = tk.Label(
            win,
            text="Note: each engine's 'comparison' unit differs — time chart is the fair cross-algorithm view",
            bg="#0f1117", fg="#f59e0b", font=("Segoe UI", 9)
        )
        subheader.pack(pady=(0, 4))

        fig1 = Figure(figsize=(10, 3.6), dpi=100)
        ax1 = fig1.add_subplot(111)
        for name, _ in engines:
            ax1.plot(sizes, comps_series[name], marker="o", label=name)
        ax1.set_title("Comparisons vs Matrix Size (N×N)  [units differ per engine — see note above]")
        ax1.set_xlabel("Matrix size N  (independent random matrix per point)")
        ax1.set_ylabel("Comparisons (engine-defined)")
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc="upper left", ncols=4, fontsize=8)

        canvas1 = FigureCanvasTkAgg(fig1, master=win)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=False, padx=10, pady=(5, 10))

        fig2 = Figure(figsize=(10, 3.6), dpi=100)
        ax2 = fig2.add_subplot(111)
        for name, _ in engines:
            ax2.plot(sizes, time_series[name], marker="o", label=name)
        ax2.set_title("Execution Time vs Matrix Size (N×N)  [same unit — fair comparison]")
        ax2.set_xlabel("Matrix size N  (independent random matrix per point)")
        ax2.set_ylabel("Time (ms, averaged over runs)")
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc="upper left", ncols=4, fontsize=8)

        canvas2 = FigureCanvasTkAgg(fig2, master=win)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=False, padx=10, pady=(0, 10))

        note = tk.Label(
            win,
            text=(f"Pattern: {pr}×{pc}   |   Matrix values: {lo}–{hi}   |   "
                  f"Sizes: {sizes[0]}–{sizes[-1]}   |   Seed: 42 (reproducible)"),
            bg="#0f1117", fg="#9ca3af", font=("Segoe UI", 9)
        )
        note.pack(pady=(0, 10))

    # --- SINGLE & RACE MODES ---

    def run_single(self):
        self.mode = "single"
        if not self.prepare_run():
            return
        algo = self.algo_var.get()
        t0 = time.perf_counter()
        if algo == "naive":
            self.steps = engine_naive(self.matrix, self.pattern)
        elif algo == "rk":
            self.steps = engine_rk(self.matrix, self.pattern)
        elif algo == "kmp":
            self.steps = engine_kmp(self.matrix, self.pattern)
        elif algo == "bm":
            self.steps = engine_bm(self.matrix, self.pattern)
        elif algo == "aho":
            self.steps = engine_aho(self.matrix, self.pattern)
        elif algo == "bb":
            self.steps = engine_bb(self.matrix, self.pattern)
        elif algo == "kmp_nv":
            self.steps = engine_kmp_nv(self.matrix, self.pattern)
        else:
            self.steps = []
        self.runtime = (time.perf_counter() - t0) * 1000
        self.render_single_grid()
        self.step_idx = 0
        if self.steps:
            self.highlight_step()
        else:
            self.stat_matches.config(text="0")
            self.stat_comps.config(text="0")
            self.stat_steps.config(text="0")
            self.stat_time.config(text=f"{self.runtime:.3f}")

    def run_multi_race(self):
        self.mode = "race"
        if not self.prepare_run():
            return
        for w in self.display_container.winfo_children():
            w.destroy()
        self.race_engines = {}
        self.runtime = 0.0
        engines = [
            ("Naive",  engine_naive),
            ("RK",     engine_rk),
            ("KMP",    engine_kmp),
            ("BM",     engine_bm),
            ("AHO",    engine_aho),
            ("BB",     engine_bb),
            ("KMP_NV", engine_kmp_nv),
        ]
        for idx, (name, engine_func) in enumerate(engines):
            f = tk.Frame(self.display_container, bg="#1a1d2e", bd=1, relief="solid")
            f.grid(row=idx // 3, column=idx % 3, padx=5, pady=5)
            tk.Label(f, text=name, bg="#1a1d2e", fg="#a78bfa").pack()
            grid_f = tk.Frame(f, bg="#0f1117")
            grid_f.pack(padx=5, pady=5)
            cells = {}
            for r in range(len(self.matrix)):
                for c in range(len(self.matrix[0])):
                    l = tk.Label(grid_f, text=str(self.matrix[r][c]), width=2, font=("Arial", 7), bg="#1a1d2e", fg="#555")
                    l.grid(row=r, column=c, padx=1, pady=1)
                    cells[(r, c)] = l

            steps, runtime_ms, bench_runs = self._benchmark_engine(engine_func, self.matrix, self.pattern)
            last = steps[-1] if steps else {'m': 0, 'c': 0}
            self.race_engines[name] = {
                "steps": steps,
                "cells": cells,
                "time_ms": runtime_ms,
                "matches": int(last.get('m', 0)),
                "comparisons": int(last.get('c', 0)),
                "steps_count": len(steps),
                "benchmark_runs": bench_runs,
            }
        self.step_idx = 0
        self.is_playing = False
        self.toggle_play()

    # --- UI HELPERS ---

    def load_preset(self, name):
        self.matrix_input.delete("1.0", tk.END)
        self.pattern_input.delete("1.0", tk.END)
        if name == "5x5 Simple":
            self.matrix_input.insert("1.0",
                "1 2 3 4 5\n"
                "6 7 8 2 3\n"
                "9 1 2 7 8\n"
                "3 2 3 1 2\n"
                "5 7 8 4 5")
            self.pattern_input.insert("1.0",
                "2 3\n"
                "7 8")

        elif name == "12x12 Random Int":
            rows = [" ".join(str(random.randint(1, 9)) for _ in range(12)) for _ in range(12)]
            self.matrix_input.insert("1.0", "\n".join(rows))
            self.pattern_input.insert("1.0",
                "5 5\n"
                "5 5")

        elif name == "8x8 Binary (0/1)":
            rows = [" ".join(str(random.randint(0, 1)) for _ in range(8)) for _ in range(8)]
            self.matrix_input.insert("1.0", "\n".join(rows))
            self.pattern_input.insert("1.0",
                "1 1\n"
                "1 1")

        elif name == "Pattern Not Found":
            self.matrix_input.insert("1.0",
                "1 2 3\n"
                "4 5 6")
            self.pattern_input.insert("1.0",
                "9 9")

        elif name == "Naive Friendly":
            self.matrix_input.insert("1.0",
                "1 2 3 4 5\n"
                "6 7 8 9 1\n"
                "2 3 4 5 6\n"
                "7 8 9 1 2\n"
                "3 4 5 6 7")
            self.pattern_input.insert("1.0",
                "8 9\n"
                "3 4")

        elif name == "BM Friendly":
            self.matrix_input.insert("1.0",
                "10 11 12 13 14 15 16\n"
                "21 22 23 24 25 26 27\n"
                "31 32 33 34 35 36 37\n"
                "41 42 43 44 45 46 47\n"
                "51 52 53 54 55 56 57")
            self.pattern_input.insert("1.0",
                "24 25 26\n"
                "34 35 36")

        elif name == "RK Friendly":
            # Best for Rabin-Karp:
            # - mostly random values
            # - one true match
            # - almost all windows rejected by hash before cell verification
            self.matrix_input.insert("1.0",
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1 1 1")

            self.pattern_input.insert("1.0",
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 2")

        elif name == "KMP Friendly":
            # Best for your kmp.py:
            # - first row has strong prefix/suffix repetition
            # - KMP gains from LPS skipping
            # - lower rows verify only when first row hits
            self.matrix_input.insert("1.0",
                "1 2 1 2 1 2 1 2 1 2 1 3\n"
                "5 6 5 6 5 6 5 6 5 6 5 7\n"
                "9 8 9 8 9 8 9 8 9 8 9 4\n"
                "1 2 1 2 1 2 1 2 1 2 1 3\n"
                "5 6 5 6 5 6 5 6 5 6 5 7\n"
                "9 8 9 8 9 8 9 8 9 8 9 4")
            self.pattern_input.insert("1.0",
                "1 2 1 2 1 2 1 3\n"
                "5 6 5 6 5 6 5 7\n"
                "9 8 9 8 9 8 9 4")

        elif name == "AHO Friendly":
            # Best for your aho_corasick.py:
            # - multiple DISTINCT pattern rows
            # - those rows appear many times in the text
            # - AC can detect all row patterns in one pass per row
            self.matrix_input.insert("1.0",
                "2 2 2 2 2 2 2 2\n"
                "2 2 2 2 2 2 2 2\n"
                "2 2 2 2 2 2 2 2\n"
                "1 2 3 4 5 6 7 8\n"
                "2 2 2 2 2 2 2 2\n"
                "2 2 2 2 2 2 2 2\n"
                "2 2 2 2 2 2 2 2\n"
                "2 2 2 2 2 2 2 2")
            self.pattern_input.insert("1.0",
                "2 2 2 2 2 2\n"
                #"3 3 3 3 3 3") no match test
                "2 2 2 2 2 2")

        elif name == "KMP+Naive Friendly":
            # Best for your kmp_naive.py:
            # - pattern has FEW UNIQUE ROWS
            # - repeated rows benefit because each unique row is KMP-built once
            # - vertical alignment then confirms the match
            self.matrix_input.insert("1.0",
                #"3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                #"3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                #"3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                #"3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                #"3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3\n"
                "3 3 3 3 3 3 3 3 3 3 3 3 3 3 3")
                # test with match
                #"3 3 3 3 3 3 3 4 4 4 4 4 4 4 4\n"
                #"3 3 3 3 3 3 3 4 4 4 4 4 4 4 4")

            self.pattern_input.insert("1.0",
                "3 3 3 3 3 3 3 3\n"
                "4 4 4 4 4 4 4 4\n"
                "4 4 4 4 4 4 4 4")

        elif name == "Bird-Baker Friendly":
            # Best for your bird_baker.py:
            # - it assigns Token 1 to 11111 and Token 2 to 11112
            # - horizontal phase: it effortlessly translates the matrix into a grid of Toekn 1s
            # - vertical phase: it runs 1D KMP down the columns, looking for sequence [1,1,1,2]
            # - since 1D KMP is immune to repetitively false starts due to its LPS array, BB quickly rejects columns
            # with a fraction of the comparisons to the other algorithms
            self.matrix_input.insert("1.0",
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1\n"
                "1 1 1 1 1 1 1 1")

            self.pattern_input.insert("1.0",
                "1 1 1 1\n"
                "1 1 1 1\n"
                "1 1 1 2")

        elif name == "Worst Case Many Matches":
            self.matrix_input.insert("1.0",
                "1 1 1 1 1 1\n"
                "1 1 1 1 1 1\n"
                "1 1 1 1 1 1\n"
                "1 1 1 1 1 1\n"
                "1 1 1 1 1 1")
            self.pattern_input.insert("1.0",
                "1 1 1\n"
                "1 1 1")

        # if name == "5x5 Simple":
        #     self.matrix_input.insert("1.0", "1 2 3 4 5\n6 7 8 2 3\n9 1 2 7 8\n3 2 3 1 2\n5 7 8 4 5")
        #     self.pattern_input.insert("1.0", "2 3\n7 8")
        # elif name == "12x12 Random Int":
        #     rows = [" ".join(str(random.randint(1, 9)) for _ in range(12)) for _ in range(12)]
        #     self.matrix_input.insert("1.0", "\n".join(rows))
        #     self.pattern_input.insert("1.0", "5 5\n5 5")
        # elif name == "8x8 Binary (0/1)":
        #     rows = [" ".join(str(random.randint(0, 1)) for _ in range(8)) for _ in range(8)]
        #     self.matrix_input.insert("1.0", "\n".join(rows))
        #     self.pattern_input.insert("1.0", "1 1\n1 1")
        # elif name == "Pattern Not Found":
        #     self.matrix_input.insert("1.0", "1 2 3\n4 5 6")
        #     self.pattern_input.insert("1.0", "9 9")

    def prepare_run(self):
        try:
            m_t = self.matrix_input.get("1.0", tk.END).strip()
            p_t = self.pattern_input.get("1.0", tk.END).strip()
            self.matrix  = [list(map(int, r.split())) for r in m_t.split('\n') if r.strip()]
            self.pattern = [list(map(int, r.split())) for r in p_t.split('\n') if r.strip()]
            return True
        except Exception:
            messagebox.showerror("Error", "Invalid Input Format")
            return False

    def render_single_grid(self):
        for w in self.display_container.winfo_children():
            w.destroy()
        self.cell_widgets = {}
        frame = tk.Frame(self.display_container, bg="#0f1117")
        frame.pack()
        for r, row in enumerate(self.matrix):
            for c, val in enumerate(row):
                lbl = tk.Label(frame, text=str(val), width=4, height=2, bg="#1a1d2e", fg="#e0e0e0")
                lbl.grid(row=r, column=c, padx=1, pady=1)
                self.cell_widgets[(r, c)] = lbl

    def highlight_step(self):
        if self.mode == "single":
            if not self.steps:
                return False
            step = self.steps[self.step_idx]
            for lbl in self.cell_widgets.values():
                lbl.config(bg="#1a1d2e")
            for r, c, is_m in step['cells']:
                if (r, c) in self.cell_widgets:
                    self.cell_widgets[(r, c)].config(bg="#22c55e" if step['ok'] else ("#ef4444" if not is_m else "#3b82f6"))
            if step['ok']:
                self.match_log.insert(tk.END, f"MATCH: {step['pos']}")
            self.stat_matches.config(text=str(step['m']))
            self.stat_comps.config(text=str(step['c']))
            self.stat_steps.config(text=str(self.step_idx + 1))
            self.stat_time.config(text=f"{self.runtime:.3f}")
            return True
        else:
            active = False
            for name, engine in self.race_engines.items():
                if self.step_idx < len(engine["steps"]):
                    active = True
                    step = engine["steps"][self.step_idx]
                    for lbl in engine["cells"].values():
                        lbl.config(bg="#1a1d2e")
                    for r, c, is_m in step['cells']:
                        if (r, c) in engine["cells"]:
                            engine["cells"][(r, c)].config(bg="#22c55e" if step['ok'] else "#ef4444")
                    if step['ok']:
                        self.match_log.insert(tk.END, f"{name}: {step['pos']}")
            return active

    def auto_play(self):
        if not self.is_playing:
            return
        if self.mode == "single":
            if self.step_idx < len(self.steps) - 1:
                self.step_idx += 1
                self.highlight_step()
                self.root.after(200, self.auto_play)
            else:
                self.finish_run()
        else:
            if self.highlight_step():
                self.step_idx += 1
                self.root.after(300, self.auto_play)
            else:
                self.finish_run()

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.config(text="Pause" if self.is_playing else "Play")
        if self.is_playing:
            self.auto_play()

    def finish_run(self):
        self.is_playing = False
        self.play_btn.config(text="Play")
        self.match_log.insert(tk.END, "🏆 FINAL SUMMARY")
        if self.mode == "race":
            for name, engine in self.race_engines.items():
                self.match_log.insert(
                    tk.END,
                    f"[{name}] Matches:{engine['matches']} Comps:{engine['comparisons']} Steps:{engine['steps_count']} AvgTime(ms):{engine['time_ms']:.3f} Runs:{engine['benchmark_runs']}"
                )
            ranking = sorted(self.race_engines.items(), key=lambda x: x[1]["time_ms"])
            self.match_log.insert(tk.END, "🏅 FASTEST ALGORITHMS")
            for idx, (name, data) in enumerate(ranking, 1):
                self.match_log.insert(
                    tk.END,
                    f"{idx}. {name:<10} - {data['time_ms']:.3f} ms avg over {data['benchmark_runs']} runs (matches={data['matches']} comps={data['comparisons']})"
                )
            if ranking:
                fastest_name, fastest_data = ranking[0]
                self.status_lbl.config(text=f"Fastest: {fastest_name} ({fastest_data['time_ms']:.3f} ms avg)")
        else:
            if self.steps:
                last = self.steps[-1]
                self.match_log.insert(
                    tk.END,
                    f"[{self.algo_var.get().upper()}] Matches:{last['m']} Comps:{last['c']} Steps:{len(self.steps)} Time(ms):{self.runtime:.3f}"
                )
                self.stat_matches.config(text=str(last['m']))
                self.stat_comps.config(text=str(last['c']))
                self.stat_steps.config(text=str(len(self.steps)))
                self.stat_time.config(text=f"{self.runtime:.3f}")
            else:
                self.match_log.insert(tk.END, f"[{self.algo_var.get().upper()}] Matches:0 Comps:0 Steps:0 Time(ms):{self.runtime:.3f}")
                self.stat_matches.config(text="0")
                self.stat_comps.config(text="0")
                self.stat_steps.config(text="0")
                self.stat_time.config(text=f"{self.runtime:.3f}")
            self.status_lbl.config(text="Run complete")
        self.match_log.see(tk.END)

    def export_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.match_log.get(0, tk.END)))


if __name__ == "__main__":
    root = tk.Tk()
    app = PatternMatcherApp(root)
    root.mainloop()
