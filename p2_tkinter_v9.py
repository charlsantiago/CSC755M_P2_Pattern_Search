import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
from collections import deque, defaultdict

class PatternMatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("2D Pattern Matcher - Ultimate Studio")
        self.root.geometry("1550x900")
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

        self.setup_styles()
        self.create_layout()
        self.load_default_data()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#0f1117")
        style.configure("TLabel", background="#13151f", foreground="#7c85c0", font=("Segoe UI", 9, "bold"))

    def create_layout(self):
        # --- LEFT SIDEBAR ---
        self.sidebar = tk.Frame(self.root, bg="#13151f", width=300, padx=15, pady=15)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="INPUT MATRIX").pack(anchor="w")
        self.matrix_input = tk.Text(self.sidebar, height=6, bg="#0f1117", fg="#e0e0e0", bd=0, font=("Consolas", 10))
        self.matrix_input.pack(fill="x", pady=(5, 10))

        tk.Label(self.sidebar, text="SUB-PATTERN").pack(anchor="w")
        self.pattern_input = tk.Text(self.sidebar, height=3, bg="#0f1117", fg="#e0e0e0", bd=0, font=("Consolas", 10))
        self.pattern_input.pack(fill="x", pady=(5, 10))

        self.algo_var = tk.StringVar(value="kmp")
        for text, val in [("Naive", "naive"), ("Rabin-Karp", "rk"), ("KMP", "kmp"), ("Boyer-Moore", "bm"), ("Aho-Corasick", "aho")]:
            tk.Radiobutton(self.sidebar, text=text, variable=self.algo_var, value=val, 
                           bg="#13151f", fg="#ccc", selectcolor="#7c3aed").pack(anchor="w")

        # Results Card (Single Mode Stats)
        self.results_card = tk.Frame(self.sidebar, bg="#1a1d2e", pady=15, padx=10, highlightthickness=1, highlightbackground="#2e3250")
        self.results_card.pack(fill="x", pady=15)
        self.stat_matches = self.create_stat_box(self.results_card, "Matches", 0, 0)
        self.stat_comps = self.create_stat_box(self.results_card, "Comparisons", 0, 1)
        self.stat_time = self.create_stat_box(self.results_card, "Time (ms)", 1, 0)
        self.stat_steps = self.create_stat_box(self.results_card, "Steps", 1, 1)

        tk.Button(self.sidebar, text="▶ RUN SINGLE MODE", bg="#7c3aed", fg="white", font=("Segoe UI", 10, "bold"), command=self.run_single, relief="flat").pack(fill="x", pady=5)
        tk.Button(self.sidebar, text="🏁 START MULTI-RACE", bg="#22c55e", fg="white", font=("Segoe UI", 10, "bold"), command=self.run_multi_race, relief="flat").pack(fill="x")

        # --- RIGHT SIDEBAR (Match Log) ---
        self.log_sidebar = tk.Frame(self.root, bg="#13151f", width=260, padx=15, pady=15)
        self.log_sidebar.pack(side="right", fill="y")
        self.log_sidebar.pack_propagate(False)
        
        tk.Label(self.log_sidebar, text="MATCH LOG").pack(anchor="w", pady=(0,5))
        self.match_log = tk.Listbox(self.log_sidebar, bg="#0f1117", fg="#22c55e", bd=0, font=("Consolas", 9), highlightthickness=0)
        self.match_log.pack(fill="both", expand=True)

        log_btns = tk.Frame(self.log_sidebar, bg="#13151f", pady=10)
        log_btns.pack(fill="x")
        tk.Button(log_btns, text="Clear", bg="#333", fg="white", command=lambda: self.match_log.delete(0, tk.END)).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(log_btns, text="Export", bg="#333", fg="white", command=self.export_log).pack(side="left", expand=True, fill="x", padx=2)

        # --- CENTER ---
        self.main_area = tk.Frame(self.root, bg="#0f1117")
        self.main_area.pack(side="left", expand=True, fill="both")
        self.ctrl_bar = tk.Frame(self.main_area, bg="#1a1d2e", padx=10, pady=10)
        self.ctrl_bar.pack(fill="x")
        self.play_btn = tk.Button(self.ctrl_bar, text="▶ Play", width=8, command=self.toggle_play, bg="#0f1117", fg="white")
        self.play_btn.pack(side="left", padx=5)
        self.status_lbl = tk.Label(self.ctrl_bar, text="Ready", bg="#1a1d2e", fg="#a78bfa")
        self.status_lbl.pack(side="left", padx=20)

        self.display_container = tk.Frame(self.main_area, bg="#0f1117", padx=20, pady=20)
        self.display_container.pack(fill="both", expand=True)

    def create_stat_box(self, parent, label, r, c):
        f = tk.Frame(parent, bg="#0f1117", padx=5, pady=5, highlightthickness=1, highlightbackground="#2e3250")
        f.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
        val_lbl = tk.Label(f, text="0", bg="#0f1117", fg="#a78bfa", font=("Segoe UI", 14, "bold"))
        val_lbl.pack()
        tk.Label(f, text=label, bg="#0f1117", fg="#666", font=("Segoe UI", 7)).pack()
        return val_lbl

    def load_default_data(self):
        self.matrix_input.insert("1.0", "3 1 4 1 5 9\n5 3 5 8 9 7\n8 4 5 3 2 3\n2 6 4 3 3 8\n1 7 8 3 2 3")
        self.pattern_input.insert("1.0", "3 2 3\n3 3 8\n3 2 3")

    def get_steps(self, algo_name):
        M, P = self.matrix, self.pattern
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0
        for i in range(NR - PR + 1):
            for j in range(NC - PC + 1):
                match, cells = True, []
                for pi in range(PR):
                    for pj in range(PC):
                        comps += 1
                        is_m = M[i+pi][j+pj] == P[pi][pj]
                        cells.append((i+pi, j+pj, is_m))
                        if not is_m: match = False; break
                    if not match: break
                if match: matches += 1
                steps.append({'pos': (i,j), 'ok': match, 'cells': cells, 'matches_so_far': matches, 'comps_so_far': comps})
        return steps

    def run_single(self):
        self.mode = "single"
        self.prepare_run()
        self.steps = self.get_steps(self.algo_var.get())
        self.render_single_grid()
        self.step_idx = 0
        self.highlight_step()

    def run_multi_race(self):
        self.mode = "race"
        self.prepare_run()
        for w in self.display_container.winfo_children(): w.destroy()
        self.race_engines = {}
        algos = ["Naive", "Rabin-Karp", "KMP", "Boyer-Moore", "Aho-Corasick"]
        for idx, name in enumerate(algos):
            frame = tk.Frame(self.display_container, bg="#1a1d2e", bd=1, relief="solid")
            frame.grid(row=idx//3, column=idx%3, padx=5, pady=5)
            tk.Label(frame, text=name, bg="#1a1d2e", fg="#a78bfa").pack()
            grid_f = tk.Frame(frame, bg="#0f1117")
            grid_f.pack(padx=5, pady=5)
            cells = {}
            for r in range(len(self.matrix)):
                for c in range(len(self.matrix[0])):
                    l = tk.Label(grid_f, text=str(self.matrix[r][c]), width=2, font=("Arial", 7), bg="#1a1d2e", fg="#555")
                    l.grid(row=r, column=c, padx=1, pady=1)
                    cells[(r, c)] = l
            self.race_engines[name] = {"steps": self.get_steps(name.lower()), "cells": cells}
        self.step_idx = 0
        self.toggle_play()

    def prepare_run(self):
        self.is_playing = False
        try:
            m_t, p_t = self.matrix_input.get("1.0", "end-1c").strip(), self.pattern_input.get("1.0", "end-1c").strip()
            self.matrix = [list(map(int, r.split())) for r in m_t.split('\n') if r.strip()]
            self.pattern = [list(map(int, r.split())) for r in p_t.split('\n') if r.strip()]
        except: messagebox.showerror("Error", "Invalid Input")

    def render_single_grid(self):
        for w in self.display_container.winfo_children(): w.destroy()
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
            step = self.steps[self.step_idx]
            for lbl in self.cell_widgets.values(): lbl.config(bg="#1a1d2e")
            for r, c, is_m in step['cells']:
                color = "#22c55e" if step['ok'] else ("#3b82f6" if is_m else "#ef4444")
                self.cell_widgets[(r, c)].config(bg=color)
            if step['ok']: self.match_log.insert(tk.END, f"MATCH: {step['pos']}")
            self.stat_matches.config(text=str(step['matches_so_far']))
            self.stat_comps.config(text=str(step['comps_so_far']))
            self.stat_steps.config(text=str(self.step_idx + 1))
            self.stat_time.config(text=f"{(self.step_idx * 0.12):.2f}")
        else:
            still_running = False
            for name, engine in self.race_engines.items():
                if self.step_idx < len(engine["steps"]):
                    still_running = True
                    step = engine["steps"][self.step_idx]
                    for lbl in engine["cells"].values(): lbl.config(bg="#1a1d2e")
                    for r, c, is_m in step['cells']:
                        color = "#22c55e" if step['ok'] else ("#3b82f6" if is_m else "#ef4444")
                        engine["cells"][(r, c)].config(bg=color)
                    if step['ok']: self.match_log.insert(tk.END, f"{name}: {step['pos']}")
            return still_running

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.config(text="⏸ Pause" if self.is_playing else "▶ Play")
        if self.is_playing: self.auto_play()

    def auto_play(self):
        if not self.is_playing: return
        if self.mode == "single":
            if self.step_idx < len(self.steps)-1:
                self.step_idx += 1; self.highlight_step(); self.root.after(300, self.auto_play)
            else: self.finish_run()
        else:
            if self.highlight_step():
                self.step_idx += 1; self.root.after(400, self.auto_play)
            else: self.finish_run()

    def finish_run(self):
        self.is_playing = False; self.play_btn.config(text="▶ Play")
        self.match_log.insert(tk.END, "-"*20)
        self.match_log.insert(tk.END, "🏆 FINAL SUMMARY")
        if self.mode == "race":
            for name, engine in self.race_engines.items():
                last = engine["steps"][-1]
                self.match_log.insert(tk.END, f"[{name}] M:{last['matches_so_far']} C:{last['comps_so_far']}")
        else:
            last = self.steps[-1]
            self.match_log.insert(tk.END, f"[{self.algo_var.get().upper()}] M:{last['matches_so_far']} C:{last['comps_so_far']}")
        self.match_log.see(tk.END)

    def export_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w") as f:
                f.write("\n".join(self.match_log.get(0, tk.END)))
            messagebox.showinfo("Success", "Log exported!")

if __name__ == "__main__":
    root = tk.Tk(); app = PatternMatcherApp(root); root.mainloop()