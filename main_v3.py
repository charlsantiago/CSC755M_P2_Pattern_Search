import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import time
from collections import deque, defaultdict
import math
from statistics import mean
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception as _e:
    Figure = None
    FigureCanvasTkAgg = None

# --- Aho-Corasick over integer tokens (Bird-Baker vertical phase) ---
class _ACNode:
    __slots__ = ("next", "fail", "out")
    def __init__(self):
        self.next = {}
        self.fail = 0
        self.out = []

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
        tk.Button(self.sidebar, text="📈 GROWTH CHART", bg="#0ea5e9", fg="white", font=("Segoe UI", 10, "bold"), command=self.show_growth_chart, relief="flat").pack(fill="x", pady=(5,0))

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
                        if not match_cell:
                            is_match = False
                            break
                    if not is_match:
                        break
                if is_match:
                    matches += 1
                steps.append({'pos': (i, j), 'ok': is_match, 'cells': cells, 'm': matches, 'c': comps})
        return steps

    def engine_rk(self, M, P):
        """
        2D Rabin–Karp with rolling hash (horizontal + vertical), plus verification.
        """
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0

        if PR == 0 or PC == 0 or NR == 0 or NC == 0 or PR > NR or PC > NC:
            return steps

        mod1, mod2 = 1_000_000_007, 1_000_000_009
        base_col1, base_col2 = 911382323, 972663749
        base_row1, base_row2 = 972663749, 911382323

        def norm(v, mod):
            return v % mod

        def row_window_hashes(row, win, base, mod):
            if win > len(row):
                return []
            pow_base = pow(base, win - 1, mod)
            h = 0
            for k in range(win):
                h = (h * base + norm(row[k], mod)) % mod
            out = [h]
            for j in range(1, len(row) - win + 1):
                lead = norm(row[j - 1], mod)
                newv = norm(row[j + win - 1], mod)
                h = (h - lead * pow_base) % mod
                h = (h * base + newv) % mod
                out.append(h)
            return out

        p_row_h1 = [row_window_hashes(P[r], PC, base_col1, mod1)[0] for r in range(PR)]
        p_row_h2 = [row_window_hashes(P[r], PC, base_col2, mod2)[0] for r in range(PR)]
        ph1 = 0
        ph2 = 0
        for r in range(PR):
            ph1 = (ph1 * base_row1 + p_row_h1[r]) % mod1
            ph2 = (ph2 * base_row2 + p_row_h2[r]) % mod2
        p_hash = (ph1, ph2)

        row_h1 = [row_window_hashes(M[r], PC, base_col1, mod1) for r in range(NR)]
        row_h2 = [row_window_hashes(M[r], PC, base_col2, mod2) for r in range(NR)]

        out_rows = NR - PR + 1
        out_cols = NC - PC + 1
        pow_row1 = pow(base_row1, PR - 1, mod1)
        pow_row2 = pow(base_row2, PR - 1, mod2)

        vhash = [[(0, 0) for _ in range(out_cols)] for __ in range(out_rows)]
        for j in range(out_cols):
            h1 = 0
            h2 = 0
            for k in range(PR):
                h1 = (h1 * base_row1 + row_h1[k][j]) % mod1
                h2 = (h2 * base_row2 + row_h2[k][j]) % mod2
            vhash[0][j] = (h1, h2)

            for i in range(1, out_rows):
                top1 = row_h1[i - 1][j]
                bot1 = row_h1[i + PR - 1][j]
                h1 = (h1 - top1 * pow_row1) % mod1
                h1 = (h1 * base_row1 + bot1) % mod1

                top2 = row_h2[i - 1][j]
                bot2 = row_h2[i + PR - 1][j]
                h2 = (h2 - top2 * pow_row2) % mod2
                h2 = (h2 * base_row2 + bot2) % mod2

                vhash[i][j] = (h1, h2)

        for i in range(out_rows):
            for j in range(out_cols):
                comps += 1
                if vhash[i][j] != p_hash:
                    steps.append({'pos': (i, j), 'ok': False, 'cells': [(i, j, False)], 'm': matches, 'c': comps})
                    continue

                is_match = True
                cells = []
                for pi in range(PR):
                    for pj in range(PC):
                        comps += 1
                        ok_cell = (M[i + pi][j + pj] == P[pi][pj])
                        cells.append((i + pi, j + pj, ok_cell))
                        if not ok_cell:
                            is_match = False
                            break
                    if not is_match:
                        break

                if is_match:
                    matches += 1
                steps.append({'pos': (i, j), 'ok': is_match, 'cells': cells, 'm': matches, 'c': comps})

        return steps

    # --- 1D HELPERS ---

    def _kmp_build_lps(self, pat):
        lps = [0] * len(pat)
        j = 0
        comps = 0
        for i in range(1, len(pat)):
            while j > 0 and pat[i] != pat[j]:
                comps += 1
                j = lps[j - 1]
            comps += 1
            if pat[i] == pat[j]:
                j += 1
                lps[i] = j
        return lps, comps

    def _kmp_search_row(self, text_row, pat, lps):
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
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0

        if PR == 0 or PC == 0 or PR > NR or PC > NC:
            return steps

        lps, lps_comps = self._kmp_build_lps(P[0])
        comps += lps_comps
        out_cols = NC - PC + 1

        for i in range(NR - PR + 1):
            candidate_js, row_comps = self._kmp_search_row(M[i], P[0], lps)
            comps += row_comps
            candidate_set = {j for j in candidate_js if 0 <= j < out_cols}

            for j in range(out_cols):
                ok = False
                cells = [(i, j, True)]
                if j in candidate_set:
                    ok = True
                    cells = []
                    # log row-0 cells too so the trace shows the actual checked window
                    for pj in range(PC):
                        cells.append((i, j + pj, True))
                    for pi in range(1, PR):
                        for pj in range(PC):
                            comps += 1
                            match_cell = (M[i + pi][j + pj] == P[pi][pj])
                            cells.append((i + pi, j + pj, match_cell))
                            if not match_cell:
                                ok = False
                                break
                        if not ok:
                            break
                    if ok:
                        matches += 1
                steps.append({'pos': (i, j), 'ok': ok, 'cells': cells, 'm': matches, 'c': comps})

        return steps

    def engine_bm(self, M, P):
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0
        bad_char = {val: k for k, val in enumerate(P[0])}
        for i in range(NR - PR + 1):
            j = 0
            while j <= NC - PC:
                k = PC - 1
                cells = []
                while k >= 0:
                    comps += 1
                    ok_cell = (P[0][k] == M[i][j + k])
                    cells.append((i, j + k, ok_cell))
                    if not ok_cell:
                        shift = max(1, k - bad_char.get(M[i][j + k], -1))
                        steps.append({'pos': (i, j), 'ok': False, 'cells': cells, 'm': matches, 'c': comps})
                        j += shift
                        break
                    k -= 1
                else:
                    is_match = True
                    cells = []
                    for pj in range(PC):
                        cells.append((i, j + pj, True))
                    for pi in range(1, PR):
                        for pj in range(PC):
                            comps += 1
                            ok_cell = (M[i + pi][j + pj] == P[pi][pj])
                            cells.append((i + pi, j + pj, ok_cell))
                            if not ok_cell:
                                is_match = False
                                break
                        if not is_match:
                            break
                    if is_match:
                        matches += 1
                    steps.append({'pos': (i, j), 'ok': is_match, 'cells': cells, 'm': matches, 'c': comps})
                    j += 1
        return steps

    def engine_aho(self, M, P):
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0

        if PR == 0 or PC == 0 or PR > NR or PC > NC:
            return steps

        nodes = [{'next': {}, 'fail': 0, 'out': []}]

        def add_pattern(row_id, pat):
            nonlocal comps
            s = 0
            for sym in pat:
                comps += 1
                nxt = nodes[s]['next'].get(sym)
                if nxt is None:
                    nodes.append({'next': {}, 'fail': 0, 'out': []})
                    nxt = len(nodes) - 1
                    nodes[s]['next'][sym] = nxt
                s = nxt
            nodes[s]['out'].append(row_id)

        for rid in range(PR):
            add_pattern(rid, P[rid])

        q = deque()
        for sym, nxt in nodes[0]['next'].items():
            nodes[nxt]['fail'] = 0
            q.append(nxt)

        while q:
            r = q.popleft()
            for sym, u in nodes[r]['next'].items():
                q.append(u)
                f = nodes[r]['fail']
                while f != 0 and sym not in nodes[f]['next']:
                    comps += 1
                    f = nodes[f]['fail']
                if sym in nodes[f]['next']:
                    nodes[u]['fail'] = nodes[f]['next'][sym]
                else:
                    nodes[u]['fail'] = 0
                nodes[u]['out'].extend(nodes[nodes[u]['fail']]['out'])

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
                    for rid in nodes[state]['out']:
                        start = col - PC + 1
                        if start >= 0:
                            hits[i][rid].add(start)

        out_rows = NR - PR + 1
        out_cols = NC - PC + 1
        for top_i in range(out_rows):
            for j in range(out_cols):
                ok = True
                for rid in range(PR):
                    comps += 1
                    if j not in hits[top_i + rid].get(rid, set()):
                        ok = False
                        break
                if ok:
                    matches += 1
                steps.append({'pos': (top_i, j), 'ok': ok, 'cells': [(top_i, j, ok)], 'm': matches, 'c': comps})

        return steps

    def engine_kmp_nv(self, M, P):
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0

        pat_rows = [tuple(row) for row in P]
        unique_rows = list(set(pat_rows))
        lps_map = {}
        for r in unique_rows:
            lps, lps_comps = self._kmp_build_lps(list(r))
            lps_map[r] = lps
            comps += lps_comps

        row_hits = [defaultdict(set) for _ in range(NR)]
        for i in range(NR):
            text_row = M[i]
            for r in unique_rows:
                cols, row_comps = self._kmp_search_row(text_row, list(r), lps_map[r])
                comps += row_comps
                for c0 in cols:
                    if c0 <= NC - PC:
                        row_hits[i][r].add(c0)

        for i in range(NR - PR + 1):
            for j in range(NC - PC + 1):
                comps += 1
                ok = True
                for pi in range(PR):
                    if j not in row_hits[i + pi][pat_rows[pi]]:
                        ok = False
                        break

                cells = [(i, j, ok)]
                if ok:
                    cells = []
                    for pi in range(PR):
                        for pj in range(PC):
                            comps += 1
                            match_cell = (M[i + pi][j + pj] == P[pi][pj])
                            cells.append((i + pi, j + pj, match_cell))
                            if not match_cell:
                                ok = False
                                break
                        if not ok:
                            break

                if ok:
                    matches += 1

                steps.append({'pos': (i, j), 'ok': ok, 'cells': cells, 'm': matches, 'c': comps})

        return steps

    def engine_bb(self, M, P):
        """
        Standard Bird-Baker style:
        1) Horizontal multi-row matching with Aho-Corasick over the unique pattern rows.
        2) Vertical matching of the token sequence with KMP.
        No extra cell-by-cell verify is needed because row tokens come from exact row matches.
        """
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, comps, matches = [], 0, 0

        if PR == 0 or PC == 0 or PR > NR or PC > NC:
            return steps

        # Assign one token per unique pattern row.
        row_to_tok = {}
        tok_seq = []
        next_tok = 1
        for row in P:
            key = tuple(row)
            if key not in row_to_tok:
                row_to_tok[key] = next_tok
                next_tok += 1
            tok_seq.append(row_to_tok[key])

        unique_rows = list(row_to_tok.keys())

        # --- Horizontal phase: Aho-Corasick over unique pattern rows ---
        nodes = [{'next': {}, 'fail': 0, 'out': []}]

        def add_row(pat_tuple, tok):
            nonlocal comps
            s = 0
            for sym in pat_tuple:
                comps += 1
                nxt = nodes[s]['next'].get(sym)
                if nxt is None:
                    nodes.append({'next': {}, 'fail': 0, 'out': []})
                    nxt = len(nodes) - 1
                    nodes[s]['next'][sym] = nxt
                s = nxt
            nodes[s]['out'].append(tok)

        for pat_tuple, tok in row_to_tok.items():
            add_row(pat_tuple, tok)

        q = deque()
        for sym, nxt in nodes[0]['next'].items():
            nodes[nxt]['fail'] = 0
            q.append(nxt)

        while q:
            r = q.popleft()
            for sym, u in nodes[r]['next'].items():
                q.append(u)
                f = nodes[r]['fail']
                while f != 0 and sym not in nodes[f]['next']:
                    comps += 1
                    f = nodes[f]['fail']
                if sym in nodes[f]['next']:
                    nodes[u]['fail'] = nodes[f]['next'][sym]
                else:
                    nodes[u]['fail'] = 0
                nodes[u]['out'].extend(nodes[nodes[u]['fail']]['out'])

        # token_grid[i][j] = token of the row pattern that matches exactly at text row i, start col j
        out_cols = NC - PC + 1
        token_grid = [defaultdict(int) for _ in range(NR)]
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
                    for tok in nodes[state]['out']:
                        start = col - PC + 1
                        if 0 <= start < out_cols:
                            token_grid[i][start] = tok

        # --- Vertical phase: KMP over token sequence ---
        lps, lps_comps = self._kmp_build_lps(tok_seq)
        comps += lps_comps
        candidates = set()
        for j in range(out_cols):
            stream = [token_grid[i].get(j, 0) for i in range(NR)]
            rows, row_comps = self._kmp_search_row(stream, tok_seq, lps)
            comps += row_comps
            for top_i in rows:
                if 0 <= top_i <= NR - PR:
                    candidates.add((top_i, j))

        for i in range(NR - PR + 1):
            for j in range(out_cols):
                comps += 1
                ok = (i, j) in candidates
                if ok:
                    matches += 1
                # For GUI, show the whole window only on matches; otherwise show anchor cell.
                cells = ([(ri, cj, True) for ri in range(i, i + PR) for cj in range(j, j + PC)]
                         if ok else [(i, j, False)])
                steps.append({'pos': (i, j), 'ok': ok, 'cells': cells, 'm': matches, 'c': comps})

        return steps

    def _ac_build(self, patterns):
        nodes = [_ACNode()]
        for pid, pat in enumerate(patterns):
            s = 0
            for x in pat:
                if x not in nodes[s].next:
                    nodes[s].next[x] = len(nodes)
                    nodes.append(_ACNode())
                s = nodes[s].next[x]
            nodes[s].out.append(pid)

        q = deque()
        for x, nxt in nodes[0].next.items():
            nodes[nxt].fail = 0
            q.append(nxt)

        while q:
            v = q.popleft()
            for x, nxt in nodes[v].next.items():
                q.append(nxt)
                f = nodes[v].fail
                while f and x not in nodes[f].next:
                    f = nodes[f].fail
                nodes[nxt].fail = nodes[f].next[x] if x in nodes[f].next else 0
                nodes[nxt].out.extend(nodes[nodes[nxt].fail].out)
        return nodes

    def _ac_search_stream(self, nodes, stream):
        s = 0
        for i, x in enumerate(stream):
            while s and x not in nodes[s].next:
                s = nodes[s].fail
            s = nodes[s].next.get(x, 0)
            if nodes[s].out:
                for pid in nodes[s].out:
                    yield i, pid

    # --- GROWTH CHART ---
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

    def show_growth_chart(self):
        if Figure is None or FigureCanvasTkAgg is None:
            messagebox.showerror("Error", "Matplotlib is not installed. Please install it with:\npip install matplotlib")
            return
        if not self.prepare_run():
            return
        pr = len(self.pattern) if self.pattern else 2
        pc = len(self.pattern[0]) if self.pattern and self.pattern[0] else 2

        NR = len(self.matrix)
        NC = len(self.matrix[0]) if self.matrix else 0
        maxN = min(NR, NC)

        if maxN < max(pr, pc):
            messagebox.showerror(
                "Matrix too small",
                f"Your matrix is {NR}x{NC} but pattern is {pr}x{pc}. Increase the matrix size or reduce the pattern."
            )
            return

        startN = max(pr, pc)
        step = 2 if maxN - startN >= 6 else 1
        sizes = list(range(startN, maxN + 1, step))
        if len(sizes) > 12:
            sizes = sizes[:12]

        engines = [
            ("Naive", self.engine_naive),
            ("RK", self.engine_rk),
            ("KMP", self.engine_kmp),
            ("BM", self.engine_bm),
            ("AHO", self.engine_aho),
            ("BB", self.engine_bb),
            ("KMP_NV", self.engine_kmp_nv),
        ]

        comps_series = {name: [] for name, _ in engines}
        time_series = {name: [] for name, _ in engines}

        for n in sizes:
            M_crop = [row[:n] for row in self.matrix[:n]]
            P = self.pattern
            for name, func in engines:
                c, _m, t = self._engine_summary(func, M_crop, P)
                comps_series[name].append(c)
                time_series[name].append(t)

        win = tk.Toplevel(self.root)
        win.title("Growth Chart: Comparisons & Execution Time (Current Input)")
        win.geometry("1100x800")
        win.configure(bg="#0f1117")

        header = tk.Label(
            win,
            text="Growth Chart (current input): comparisons & runtime vs cropped matrix size",
            bg="#0f1117", fg="#e0e0e0", font=("Segoe UI", 12, "bold")
        )
        header.pack(pady=(10, 5))

        fig1 = Figure(figsize=(10, 3.6), dpi=100)
        ax1 = fig1.add_subplot(111)
        for name, _ in engines:
            ax1.plot(sizes, comps_series[name], marker="o", label=name)
        ax1.set_title("Comparisons vs Cropped Matrix Size (N×N)")
        ax1.set_xlabel("Cropped matrix size N")
        ax1.set_ylabel("Comparisons")
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc="upper left", ncols=4, fontsize=8)

        canvas1 = FigureCanvasTkAgg(fig1, master=win)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=False, padx=10, pady=(5, 10))

        fig2 = Figure(figsize=(10, 3.6), dpi=100)
        ax2 = fig2.add_subplot(111)
        for name, _ in engines:
            ax2.plot(sizes, time_series[name], marker="o", label=name)
        ax2.set_title("Execution Time vs Cropped Matrix Size (N×N)")
        ax2.set_xlabel("Cropped matrix size N")
        ax2.set_ylabel("Time (ms)")
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc="upper left", ncols=4, fontsize=8)

        canvas2 = FigureCanvasTkAgg(fig2, master=win)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=False, padx=10, pady=(0, 10))

        note = tk.Label(
            win,
            text=f"Pattern size used: {pr}×{pc}   |   Trials per size: 1   |   Input source: current matrix crop",
            bg="#0f1117", fg="#9ca3af", font=("Segoe UI", 9)
        )
        note.pack(pady=(0, 10))

    def run_single(self):
        self.mode = "single"
        if not self.prepare_run():
            return
        algo = self.algo_var.get()
        t0 = time.perf_counter()
        if algo == "naive":
            self.steps = self.engine_naive(self.matrix, self.pattern)
        elif algo == "rk":
            self.steps = self.engine_rk(self.matrix, self.pattern)
        elif algo == "kmp":
            self.steps = self.engine_kmp(self.matrix, self.pattern)
        elif algo == "bm":
            self.steps = self.engine_bm(self.matrix, self.pattern)
        elif algo == "aho":
            self.steps = self.engine_aho(self.matrix, self.pattern)
        elif algo == "bb":
            self.steps = self.engine_bb(self.matrix, self.pattern)
        elif algo == "kmp_nv":
            self.steps = self.engine_kmp_nv(self.matrix, self.pattern)
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
            ("Naive", self.engine_naive),
            ("RK", self.engine_rk),
            ("KMP", self.engine_kmp),
            ("BM", self.engine_bm),
            ("AHO", self.engine_aho),
            ("BB", self.engine_bb),
            ("KMP_NV", self.engine_kmp_nv)
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
        self.toggle_play()

    # --- HELPERS ---
    def load_preset(self, name):
        self.matrix_input.delete("1.0", tk.END)
        self.pattern_input.delete("1.0", tk.END)
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
            m_t = self.matrix_input.get("1.0", tk.END).strip()
            p_t = self.pattern_input.get("1.0", tk.END).strip()
            self.matrix = [list(map(int, r.split())) for r in m_t.split('\n') if r.strip()]
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
