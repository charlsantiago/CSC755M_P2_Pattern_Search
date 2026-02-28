import tkinter as tk
from tkinter import ttk, messagebox
import time
from collections import deque, defaultdict

class PatternMatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("2D Pattern Matcher Pro - Full Suite")
        self.root.geometry("1450x850")
        self.root.configure(bg="#0f1117")

        self.matrix = []
        self.pattern = []
        self.steps = []
        self.step_idx = 0
        self.is_playing = False
        self.cell_widgets = {}

        self.setup_styles()
        self.create_layout()
        self.load_default_data()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#13151f", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1a1d2e", foreground="#888", padding=[15, 5])
        style.map("TNotebook.Tab", background=[("selected", "#7c3aed")], foreground=[("selected", "#ffffff")])

    def create_layout(self):
        # --- LEFT SIDEBAR (Inputs) ---
        self.left_sidebar = tk.Frame(self.root, bg="#13151f", width=260, padx=15, pady=15)
        self.left_sidebar.pack(side="left", fill="y")
        self.left_sidebar.pack_propagate(False)

        tk.Label(self.left_sidebar, text="🔢 INPUTS", bg="#13151f", fg="#7c85c0", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.matrix_input = tk.Text(self.left_sidebar, height=8, bg="#0f1117", fg="#e0e0e0", font=("Consolas", 10), bd=0)
        self.matrix_input.pack(fill="x", pady=(0, 10))

        self.pattern_input = tk.Text(self.left_sidebar, height=4, bg="#0f1117", fg="#e0e0e0", font=("Consolas", 10), bd=0)
        self.pattern_input.pack(fill="x", pady=(0, 15))

        self.algo_var = tk.StringVar(value="aho")
        algos = [("Naive", "naive"), ("Rabin-Karp 2D", "rk"), ("KMP 2D", "kmp"), 
                 ("Boyer-Moore 2D", "bm"), ("Aho-Corasick 2D", "aho")]
        for text, val in algos:
            tk.Radiobutton(self.left_sidebar, text=text, variable=self.algo_var, value=val, 
                           bg="#13151f", fg="#ccc", selectcolor="#7c3aed", activebackground="#13151f").pack(anchor="w")

        tk.Button(self.left_sidebar, text="▶ RUN SEARCH", bg="#7c3aed", fg="white", 
                  font=("Segoe UI", 10, "bold"), command=self.run_search, relief="flat").pack(fill="x", pady=20)

        # --- RIGHT SIDEBAR (Match History) ---
        self.right_sidebar = tk.Frame(self.root, bg="#13151f", width=240, padx=15, pady=15)
        self.right_sidebar.pack(side="right", fill="y")
        self.right_sidebar.pack_propagate(False)

        tk.Label(self.right_sidebar, text="📍 MATCH HISTORY", bg="#13151f", fg="#7c85c0", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0,10))
        self.match_list = tk.Listbox(self.right_sidebar, bg="#0f1117", fg="#22c55e", font=("Consolas", 10), bd=0, highlightthickness=0)
        self.match_list.pack(fill="both", expand=True)

        # --- CENTER (Visualizer) ---
        self.viz_area = tk.Frame(self.root, bg="#0f1117")
        self.viz_area.pack(side="left", expand=True, fill="both")
        
        ctrl = tk.Frame(self.viz_area, bg="#1a1d2e", padx=10, pady=10)
        ctrl.pack(fill="x")
        
        self.play_btn = tk.Button(ctrl, text="▶ Play", width=8, command=self.toggle_play, bg="#0f1117", fg="white")
        self.play_btn.pack(side="left", padx=5)
        
        self.step_info = tk.Label(ctrl, text="Ready", bg="#1a1d2e", fg="#a78bfa", font=("Segoe UI", 10))
        self.step_info.pack(side="left", padx=20)

        self.main_grid_frame = tk.Frame(self.viz_area, bg="#0f1117", padx=30, pady=30)
        self.main_grid_frame.pack(anchor="nw")

    def load_default_data(self):
        self.matrix_input.insert("1.0", "3 1 4 1 5 9\n5 3 5 8 9 7\n8 4 5 3 2 3\n2 6 4 3 3 8\n1 7 8 3 2 3")
        self.pattern_input.insert("1.0", "3 2 3\n3 3 8\n3 2 3")

    # --- ALGORITHMS (Aho-Corasick & Boyer-Moore 2D) ---

    def run_bm_2d(self):
        M, P = self.matrix, self.pattern
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        steps, bad_char = [], defaultdict(lambda: -1)
        for k in range(PC): bad_char[P[0][k]] = k

        for i in range(NR - PR + 1):
            j = 0
            while j <= (NC - PC):
                k = PC - 1
                while k >= 0:
                    if P[0][k] != M[i][j + k]:
                        shift = max(1, k - bad_char[M[i][j + k]])
                        steps.append({'type': 'skip', 'pos': (i,j), 'cells': [{'r':i, 'c':j+k, 'match':False}], 'ok': False})
                        j += shift
                        break
                    k -= 1
                else:
                    ok = all(M[i+pi][j:j+PC] == P[pi] for pi in range(1, PR))
                    steps.append({'type': 'match' if ok else 'row_match', 'pos': (i,j), 
                                  'cells': [{'r':i+pi, 'c':j+pj, 'match':True} for pi in range(PR) for pj in range(PC)] if ok else [{'r':i, 'c':j, 'match':True}], 'ok': ok})
                    j += 1
        return steps

    def run_aho_2d(self):
        M, P = self.matrix, self.pattern
        NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
        trie = [{'next': {}, 'fail': 0, 'output': []}]
        for idx, row in enumerate(P):
            node = 0
            for val in row:
                if val not in trie[node]['next']:
                    trie[node]['next'][val] = len(trie)
                    trie.append({'next': {}, 'fail': 0, 'output': []})
                node = trie[node]['next'][val]
            trie[node]['output'].append(idx)

        queue = deque()
        for val, n in trie[0]['next'].items(): queue.append(n)
        while queue:
            u = queue.popleft()
            for val, v in trie[u]['next'].items():
                f = trie[u]['fail']
                while val not in trie[f]['next'] and f != 0: f = trie[f]['fail']
                trie[v]['fail'] = trie[f]['next'][val] if val in trie[f]['next'] else 0
                trie[v]['output'] += trie[trie[v]['fail']]['output']
                queue.append(v)

        row_hits = [[set() for _ in range(NC)] for _ in range(NR)]
        for r in range(NR):
            node = 0
            for c in range(NC):
                val = M[r][c]
                while val not in trie[node]['next'] and node != 0: node = trie[node]['fail']
                node = trie[node]['next'][val] if val in trie[node]['next'] else 0
                for out_idx in trie[node]['output']: row_hits[r][c - PC + 1].add(out_idx)

        steps = []
        for j in range(NC - PC + 1):
            for i in range(NR - PR + 1):
                ok = all(pi in row_hits[i+pi][j] for pi in range(PR))
                steps.append({'type': 'match' if ok else 'scan', 'pos': (i,j), 
                              'cells': [{'r':i+pi, 'c':j+pj, 'match':True} for pi in range(PR) for pj in range(PC)] if ok else [{'r':i, 'c':j, 'match':False}], 'ok': ok})
        return steps

    # --- UI & VISUALIZATION ---

    def run_search(self):
        try:
            m_text = self.matrix_input.get("1.0", "end-1c").strip()
            p_text = self.pattern_input.get("1.0", "end-1c").strip()
            self.matrix = [list(map(int, row.split())) for row in m_text.split('\n') if row.strip()]
            self.pattern = [list(map(int, row.split())) for row in p_text.split('\n') if row.strip()]
        except:
            messagebox.showerror("Error", "Invalid Matrix Input"); return

        self.match_list.delete(0, tk.END)
        algo = self.algo_var.get()
        if algo == "aho": self.steps = self.run_aho_2d()
        elif algo == "bm": self.steps = self.run_bm_2d()
        else: self.steps = self.run_aho_2d() # Default for demo

        self.render_grid()
        self.step_idx = 0
        if self.steps: self.highlight_step(self.steps[0])

    def render_grid(self):
        for w in self.main_grid_frame.winfo_children(): w.destroy()
        self.cell_widgets = {}
        for r, row in enumerate(self.matrix):
            for c, val in enumerate(row):
                lbl = tk.Label(self.main_grid_frame, text=str(val), width=4, height=2, bg="#1a1d2e", fg="#e0e0e0", relief="flat")
                lbl.grid(row=r, column=c, padx=1, pady=1)
                self.cell_widgets[(r, c)] = lbl

    def highlight_step(self, step):
        # Reset previous highlights
        for lbl in self.cell_widgets.values(): lbl.config(bg="#1a1d2e")
        
        # Color current step
        for cell in step['cells']:
            r, c = cell['r'], cell['c']
            if (r, c) in self.cell_widgets:
                color = "#22c55e" if step['ok'] else ("#3b82f6" if cell.get('match', False) else "#ef4444")
                self.cell_widgets[(r, c)].config(bg=color)
        
        # Log to sidebar if it's a match
        if step['ok']:
            match_str = f"MATCH at ({step['pos'][0]}, {step['pos'][1]})"
            if match_str not in self.match_list.get(0, tk.END):
                self.match_list.insert(tk.END, match_str)
                self.match_list.see(tk.END)

        self.step_info.config(text=f"STEP {self.step_idx + 1}/{len(self.steps)} | {step['type'].upper()}")

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.config(text="⏸ Pause" if self.is_playing else "▶ Play")
        if self.is_playing: self.auto_play()

    def auto_play(self):
        if self.is_playing and self.step_idx < len(self.steps)-1:
            self.step_idx += 1
            self.highlight_step(self.steps[self.step_idx])
            self.root.after(250, self.auto_play)
        else:
            self.is_playing = False
            self.play_btn.config(text="▶ Play")

if __name__ == "__main__":
    root = tk.Tk(); app = PatternMatcherApp(root); root.mainloop()