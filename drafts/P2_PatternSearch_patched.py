import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import time
from collections import deque, defaultdict

class PatternMatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("2D Pattern Matcher Studio - Pro Edition")
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
        self.preset_combo['values'] = ("5x5 Simple", "12x12 Random Int", "8x8 Binary (0/1)", "Pattern Not Found")
        self.preset_combo.pack(fill="x", pady=(5, 15))
        self.preset_combo.bind("<<ComboboxSelected>>", lambda e: self.load_preset(self.preset_var.get()))

        tk.Label(self.sidebar, text="INPUT MATRIX").pack(anchor="w")
        self.matrix_input = tk.Text(self.sidebar, height=6, bg="#0f1117", fg="#e0e0e0", bd=0, font=("Consolas", 10))
        self.matrix_input.pack(fill="x", pady=(5, 10))

        tk.Label(self.sidebar, text="SUB-PATTERN").pack(anchor="w")
        self.pattern_input = tk.Text(self.sidebar, height=3, bg="#0f1117", fg="#e0e0e0", bd=0, font=("Consolas", 10))
        self.pattern_input.pack(fill="x", pady=(5, 10))

        self.algo_var = tk.StringVar(value="naive")
        for text, val in [("Naive", "naive"), ("Rabin-Karp", "rk"), ("KMP", "kmp"), ("Boyer-Moore", "bm"), ("Aho-Corasick", "aho")]:
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

        # --- RIGHT SIDEBAR ---
        self.log_sidebar = tk.Frame(self.root, bg="#13151f", width=280, padx=15, pady=15)
        self.log_sidebar.pack(side="right", fill="y")
        self.log_sidebar.pack_propagate(False)
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
        self.status_lbl = tk.Label(self.ctrl_bar, text="System Ready", bg="#1a1d2e", fg="#a78bfa")
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

    # --- INDIVIDUAL ALGORITHM LOGIC ENGINES ---

    def engine_naive(self, M, P):
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0
        for i in range(NR - PR + 1):
            for j in range(NC - PC + 1):
                is_match, cells = True, []
                for pi in range(PR):
                    for pj in range(PC):
                        comps += 1
                        match_cell = (M[i+pi][j+pj] == P[pi][pj])
                        cells.append((i+pi, j+pj, match_cell))
                        if not match_cell: is_match = False; break
                    if not is_match: break
                if is_match: matches += 1
                steps.append({'pos':(i,j), 'ok':is_match, 'cells':cells, 'm':matches, 'c':comps})
        return steps

    def engine_rk(self, M, P):
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0
        p_hash = sum(sum(row) for row in P)
        for i in range(NR - PR + 1):
            for j in range(NC - PC + 1):
                comps += 1
                m_hash = sum(sum(row[j:j+PC]) for row in M[i:i+PR])
                is_match = False
                if m_hash == p_hash:
                    is_match = True
                    for pi in range(PR):
                        for pj in range(PC):
                            comps += 1
                            if M[i+pi][j+pj] != P[pi][pj]: is_match = False; break
                        if not is_match: break
                if is_match: matches += 1
                steps.append({'pos':(i,j), 'ok':is_match, 'cells':[(i,j,is_match)], 'm':matches, 'c':comps})
        return steps

# --- 1D HELPERS (for KMP / Aho-Corasick over integer sequences) ---

def _kmp_build_lps(self, pat):
    """Build KMP LPS (longest proper prefix which is also suffix) array for a list of ints."""
    lps = [0] * len(pat)
    j = 0
    comps = 0
    for i in range(1, len(pat)):
        while j > 0 and pat[i] != pat[j]:
            comps += 1
            j = lps[j - 1]
        comps += 1  # the equality check below (or the one that breaks the while)
        if pat[i] == pat[j]:
            j += 1
            lps[i] = j
    return lps, comps

def _kmp_search_row(self, text_row, pat, lps):
    """KMP search for pat (list[int]) within text_row (list[int]). Returns (positions, comparisons)."""
    if not pat:
        return [], 0
    res = []
    j = 0
    comps = 0
    for i in range(len(text_row)):
        while j > 0 and text_row[i] != pat[j]:
            comps += 1
            j = lps[j - 1]
        comps += 1
        if text_row[i] == pat[j]:
            j += 1
            if j == len(pat):
                res.append(i - j + 1)
                j = lps[j - 1]
    return res, comps

def engine_kmp(self, M, P):
    """
    Correct KMP-based 2D matching (row-filter + verify):
    - Use KMP to find occurrences of the first pattern row P[0] in each candidate matrix row M[i].
    - For each candidate column j, verify remaining rows P[1..] at the same (i,j).
    """
    NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
    steps, comps, matches = [], 0, 0

    # Precompute LPS for the first pattern row.
    lps, lps_comps = self._kmp_build_lps(P[0])
    comps += lps_comps

    for i in range(NR - PR + 1):
        candidate_js, row_comps = self._kmp_search_row(M[i], P[0], lps)
        comps += row_comps
        candidate_js = [j for j in candidate_js if j <= NC - PC]

        # To preserve the UI's "step-by-step" behavior, we still emit a step for every (i,j).
        candidate_set = set(candidate_js)

        for j in range(NC - PC + 1):
            is_match = False
            cells = [(i, j, True)]  # lightweight: mark anchor; detailed cell coloring is in naive engine

            if j in candidate_set:
                # Verify full 2D match starting from (i,j)
                is_match = True
                for pi in range(PR):
                    row_slice = M[i + pi][j:j + PC]
                    # Count element comparisons for this row check
                    comps += PC
                    if row_slice != P[pi]:
                        is_match = False
                        break

            if is_match:
                matches += 1

            steps.append({'pos': (i, j), 'ok': is_match, 'cells': cells, 'm': matches, 'c': comps})

    return steps


    def engine_bm(self, M, P):
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0
        bad_char = {val: k for k, val in enumerate(P[0])}
        for i in range(NR - PR + 1):
            j = 0
            while j <= NC - PC:
                k = PC - 1
                while k >= 0:
                    comps += 1
                    if P[0][k] != M[i][j + k]:
                        shift = max(1, k - bad_char.get(M[i][j + k], -1))
                        steps.append({'pos':(i,j), 'ok':False, 'cells':[(i, j+k, False)], 'm':matches, 'c':comps})
                        j += shift; break
                    k -= 1
                else:
                    is_match = all(M[i+pi][j:j+PC] == P[pi] for pi in range(PR))
                    if is_match: matches += 1
                    steps.append({'pos':(i,j), 'ok':is_match, 'cells':[(i,j,True)], 'm':matches, 'c':comps})
                    j += 1
        return steps

def engine_aho(self, M, P):
    """
    Correct Aho-Corasick-inspired 2D matching (multi-pattern row scan + vertical alignment):

    1) Treat each pattern row P[r] as a 1D pattern.
    2) Build an Aho-Corasick automaton over the alphabet of integers for these PR patterns.
    3) Scan each matrix row M[i] once, recording where each pattern row matches (start column j).
    4) A 2D match exists at (top_i, j) iff:
          row 0 matches at (top_i, j),
          row 1 matches at (top_i+1, j),
          ...
          row PR-1 matches at (top_i+PR-1, j).

    This is a true AC-style approach (useful when PR is large or when searching many patterns).
    """
    NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
    steps, comps, matches = [], 0, 0

    # --- Build AC automaton for pattern rows ---
    # Each node: {'next': {sym: nxt}, 'fail': int, 'out': [row_ids]}
    nodes = [{'next': {}, 'fail': 0, 'out': []}]  # root

    def add_pattern(row_id, pat):
        state = 0
        for sym in pat:
            comps_local[0] += 1
            nxt = nodes[state]['next'].get(sym)
            if nxt is None:
                nodes.append({'next': {}, 'fail': 0, 'out': []})
                nxt = len(nodes) - 1
                nodes[state]['next'][sym] = nxt
            state = nxt
        nodes[state]['out'].append(row_id)

    def build_failures():
        q = deque()
        # depth-1 nodes fail to root
        for sym, nxt in nodes[0]['next'].items():
            nodes[nxt]['fail'] = 0
            q.append(nxt)

        while q:
            r = q.popleft()
            for sym, u in nodes[r]['next'].items():
                q.append(u)
                f = nodes[r]['fail']
                while f != 0 and sym not in nodes[f]['next']:
                    comps_local[0] += 1
                    f = nodes[f]['fail']
                if sym in nodes[f]['next']:
                    nodes[u]['fail'] = nodes[f]['next'][sym]
                else:
                    nodes[u]['fail'] = 0
                nodes[u]['out'].extend(nodes[nodes[u]['fail']]['out'])

    comps_local = [0]
    for rid in range(PR):
        add_pattern(rid, P[rid])
    build_failures()
    comps += comps_local[0]

    # --- Scan each matrix row and record matches ---
    # hits[row_index][pattern_row_id] = set(start_columns)
    hits = [defaultdict(set) for _ in range(NR)]
    for i in range(NR):
        state = 0
        for col, sym in enumerate(M[i]):
            comps += 1
            while state != 0 and sym not in nodes[state]['next']:
                comps += 1
                state = nodes[state]['fail']
            if sym in nodes[state]['next']:
                state = nodes[state]['next'][sym]
            else:
                state = 0
            if nodes[state]['out']:
                # We matched one or more pattern rows ending at 'col'
                for rid in nodes[state]['out']:
                    start = col - PC + 1
                    if start >= 0:
                        hits[i][rid].add(start)

    # --- Generate steps for every candidate top-left (i,j) ---
    for top_i in range(NR - PR + 1):
        for j in range(NC - PC + 1):
            ok = True
            # alignment check across PR rows
            for rid in range(PR):
                comps += 1
                if j not in hits[top_i + rid].get(rid, set()):
                    ok = False
                    break
            if ok:
                matches += 1
            steps.append({'pos': (top_i, j), 'ok': ok, 'cells': [(top_i, j, ok)], 'm': matches, 'c': comps})

    return steps


    # --- EXECUTION MODES ---

    def run_single(self):
        self.mode = "single"
        if not self.prepare_run(): return
        algo = self.algo_var.get()
        t0 = time.perf_counter()
        if algo == "naive": self.steps = self.engine_naive(self.matrix, self.pattern)
        elif algo == "rk": self.steps = self.engine_rk(self.matrix, self.pattern)
        elif algo == "kmp": self.steps = self.engine_kmp(self.matrix, self.pattern)
        elif algo == "bm": self.steps = self.engine_bm(self.matrix, self.pattern)
        elif algo == "aho": self.steps = self.engine_aho(self.matrix, self.pattern)
        self.runtime = (time.perf_counter() - t0) * 1000
        self.render_single_grid(); self.step_idx = 0; self.highlight_step()

    def run_multi_race(self):
        self.mode = "race"
        if not self.prepare_run(): return
        for w in self.display_container.winfo_children(): w.destroy()
        self.race_engines = {}
        engines = [("Naive", self.engine_naive), ("RK", self.engine_rk), ("KMP", self.engine_kmp), ("BM", self.engine_bm), ("AHO", self.engine_aho)]
        for idx, (name, engine_func) in enumerate(engines):
            f = tk.Frame(self.display_container, bg="#1a1d2e", bd=1, relief="solid")
            f.grid(row=idx//3, column=idx%3, padx=5, pady=5)
            tk.Label(f, text=name, bg="#1a1d2e", fg="#a78bfa").pack()
            grid_f = tk.Frame(f, bg="#0f1117"); grid_f.pack(padx=5, pady=5)
            cells = {}
            for r in range(len(self.matrix)):
                for c in range(len(self.matrix[0])):
                    l = tk.Label(grid_f, text=str(self.matrix[r][c]), width=2, font=("Arial", 7), bg="#1a1d2e", fg="#555")
                    l.grid(row=r, column=c, padx=1, pady=1); cells[(r, c)] = l
            self.race_engines[name] = {"steps": engine_func(self.matrix, self.pattern), "cells": cells}
        self.step_idx = 0; self.toggle_play()

    # --- HELPERS ---
    def load_preset(self, name):
        self.matrix_input.delete("1.0", tk.END); self.pattern_input.delete("1.0", tk.END)
        if name == "5x5 Simple":
            self.matrix_input.insert("1.0", "1 2 3 4 5\n6 7 8 2 3\n9 1 2 7 8\n3 2 3 1 2\n5 7 8 4 5")
            self.pattern_input.insert("1.0", "2 3\n7 8")
        elif name == "12x12 Random Int":
            rows = [" ".join(str(random.randint(1, 9)) for _ in range(12)) for _ in range(12)]
            self.matrix_input.insert("1.0", "\n".join(rows))
            self.pattern_input.insert("1.0", "5 5\n5 5")
        elif name == "8x8 Binary (0/1)":
            rows = [" ".join(str(random.randint(0, 1)) for _ in range(8)) for _ in range(8)]
            self.matrix_input.insert("1.0", "\n".join(rows))
            self.pattern_input.insert("1.0", "1 1\n1 1")
        elif name == "Pattern Not Found":
            self.matrix_input.insert("1.0", "1 2 3\n4 5 6")
            self.pattern_input.insert("1.0", "9 9")

    def prepare_run(self):
        try:
            m_t, p_t = self.matrix_input.get("1.0", tk.END).strip(), self.pattern_input.get("1.0", tk.END).strip()
            self.matrix = [list(map(int, r.split())) for r in m_t.split('\n') if r.strip()]
            self.pattern = [list(map(int, r.split())) for r in p_t.split('\n') if r.strip()]; return True
        except: messagebox.showerror("Error", "Invalid Input Format"); return False

    def render_single_grid(self):
        for w in self.display_container.winfo_children(): w.destroy()
        self.cell_widgets = {}
        frame = tk.Frame(self.display_container, bg="#0f1117"); frame.pack()
        for r, row in enumerate(self.matrix):
            for c, val in enumerate(row):
                lbl = tk.Label(frame, text=str(val), width=4, height=2, bg="#1a1d2e", fg="#e0e0e0")
                lbl.grid(row=r, column=c, padx=1, pady=1); self.cell_widgets[(r, c)] = lbl

    def highlight_step(self):
        if self.mode == "single":
            step = self.steps[self.step_idx]
            for lbl in self.cell_widgets.values(): lbl.config(bg="#1a1d2e")
            for r, c, is_m in step['cells']:
                if (r, c) in self.cell_widgets:
                    self.cell_widgets[(r, c)].config(bg="#22c55e" if step['ok'] else ("#ef4444" if not is_m else "#3b82f6"))
            if step['ok']: self.match_log.insert(tk.END, f"MATCH: {step['pos']}")
            self.stat_matches.config(text=str(step['m'])); self.stat_comps.config(text=str(step['c']))
            self.stat_steps.config(text=str(self.step_idx + 1))
            self.stat_time.config(text=f"{(self.runtime * (self.step_idx/len(self.steps))):.2f}")
        else:
            active = False
            for name, engine in self.race_engines.items():
                if self.step_idx < len(engine["steps"]):
                    active = True; step = engine["steps"][self.step_idx]
                    for lbl in engine["cells"].values(): lbl.config(bg="#1a1d2e")
                    for r, c, is_m in step['cells']:
                        if (r, c) in engine["cells"]: engine["cells"][(r, c)].config(bg="#22c55e" if step['ok'] else "#ef4444")
                    if step['ok']: self.match_log.insert(tk.END, f"{name}: {step['pos']}")
            return active

    def auto_play(self):
        if not self.is_playing: return
        if self.mode == "single":
            if self.step_idx < len(self.steps)-1:
                self.step_idx += 1; self.highlight_step(); self.root.after(200, self.auto_play)
            else: self.finish_run()
        else:
            if self.highlight_step():
                self.step_idx += 1; self.root.after(300, self.auto_play)
            else: self.finish_run()

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.config(text="Pause" if self.is_playing else "Play")
        if self.is_playing: self.auto_play()

    def finish_run(self):
        self.is_playing = False; self.play_btn.config(text="Play")
        self.match_log.insert(tk.END, "🏆 FINAL SUMMARY")
        if self.mode == "race":
            for name, engine in self.race_engines.items():
                last = engine["steps"][-1]
                self.match_log.insert(tk.END, f"[{name}] Matches:{last['m']} Comps:{last['c']}")
        else:
            last = self.steps[-1]
            self.match_log.insert(tk.END, f"[{self.algo_var.get().upper()}] Matches:{last['m']} Comps:{last['c']}")
        self.match_log.see(tk.END)

    def export_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w") as f: f.write("\n".join(self.match_log.get(0, tk.END)))

if __name__ == "__main__":
    root = tk.Tk(); app = PatternMatcherApp(root); root.mainloop()