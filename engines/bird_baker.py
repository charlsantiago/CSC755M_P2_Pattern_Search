"""
Bird-Baker 2D Pattern Search
==============================
Theory
------
Bird (1977) and Baker (1978) independently extended 1D exact-match algorithms
to two dimensions using a two-phase approach:

  **Phase 1 — Horizontal (Aho-Corasick over unique pattern rows)**
    Assign an integer *token* to each unique row of the pattern.  Build an
    Aho-Corasick automaton over those unique rows and scan every matrix row.
    Whenever a pattern row is fully matched at position (matrix_row, col), write
    its token into token_grid[matrix_row][col].

  **Phase 2 — Vertical (KMP over token columns)**
    For each valid column j, read the column of the token grid as a 1D stream
    and run KMP with the *token sequence* (the sequence of tokens for pattern
    rows 0..PR-1).  A KMP match at row top_i means a full 2D match at (top_i, j).

Why it works
------------
- Token equality ↔ exact row equality (tokens are unique per distinct row).
- A KMP match in the vertical token stream means all PR rows are present in
  the correct order at the same column.

Complexity
----------
Phase 1 : O(NR * NC)  — AC scan
Phase 2 : O(PR)  preprocessing + O(NR * out_cols)  KMP search
Total   : O(NR * NC)
"""

from collections import deque, defaultdict
from .helpers import kmp_build_lps, kmp_search_row


def engine_bb(M, P):
    """
    Bird-Baker: Aho-Corasick horizontal phase + KMP vertical phase.

    Parameters
    ----------
    M : list[list[int]]  — text matrix  (NR × NC)
    P : list[list[int]]  — pattern       (PR × PC)

    Returns
    -------
    steps : list[dict]
        Each dict: 'pos', 'ok', 'cells', 'm', 'c'  (see naive.py for schema)
    """
    NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
    steps, comps, matches = [], 0, 0

    if PR == 0 or PC == 0 or PR > NR or PC > NC:
        return steps

    # --- Token assignment: one unique integer per distinct pattern row ---
    row_to_tok = {}   # tuple(row) -> token integer
    tok_seq = []      # token sequence for the full pattern (length PR)
    next_tok = 1
    for row in P:
        key = tuple(row)
        if key not in row_to_tok:
            row_to_tok[key] = next_tok
            next_tok += 1
        tok_seq.append(row_to_tok[key])

    # --- Phase 1: Build AC automaton over unique pattern rows ---
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
        nodes[s]['out'].append(tok)   # this node outputs the row's token

    for pat_tuple, tok in row_to_tok.items():
        add_row(pat_tuple, tok)

    # BFS to build failure (suffix) links
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
            nodes[u]['fail'] = nodes[f]['next'][sym] if sym in nodes[f]['next'] else 0
            nodes[u]['out'].extend(nodes[nodes[u]['fail']]['out'])

    # --- Scan every matrix row; write token hits into token_grid ---
    # token_grid[i][j] = token of the pattern row that exactly matches M[i][j..j+PC-1]
    out_cols = NC - PC + 1
    token_grid = [defaultdict(int) for _ in range(NR)]

    for i in range(NR):
        state = 0
        for col, sym in enumerate(M[i]):
            comps += 1
            while state != 0 and sym not in nodes[state]['next']:
                comps += 1
                state = nodes[state]['fail']
            state = nodes[state]['next'].get(sym, 0)
            if nodes[state]['out']:
                for tok in nodes[state]['out']:
                    start = col - PC + 1   # left edge of the match
                    if 0 <= start < out_cols:
                        token_grid[i][start] = tok

    # --- Phase 2: KMP on each vertical token column ---
    lps, lps_comps = kmp_build_lps(tok_seq)
    comps += lps_comps

    candidates = set()
    for j in range(out_cols):
        # Build the vertical token stream for column j
        stream = [token_grid[i].get(j, 0) for i in range(NR)]
        # A 0 token means no pattern row matched at (i, j) — guaranteed mismatch
        rows, row_comps = kmp_search_row(stream, tok_seq, lps)
        comps += row_comps
        for top_i in rows:
            if 0 <= top_i <= NR - PR:
                candidates.add((top_i, j))

    # --- Emit one step per valid window position ---
    for i in range(NR - PR + 1):
        for j in range(out_cols):
            comps += 1
            ok = (i, j) in candidates
            if ok:
                matches += 1
            # Show entire matched window on success; just the anchor cell otherwise
            cells = (
                [(ri, cj, True) for ri in range(i, i + PR) for cj in range(j, j + PC)]
                if ok else [(i, j, False)]
            )
            steps.append({'pos': (i, j), 'ok': ok, 'cells': cells, 'm': matches, 'c': comps})

    return steps
