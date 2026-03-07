"""
Aho-Corasick Multi-Row Search + Alignment Check
=================================================
Theory
------
Aho-Corasick (AC) builds a finite automaton from multiple patterns
simultaneously and processes the text in a single linear pass per row —
no backtracking.  For 2D matching we treat each of the PR pattern rows as
a separate pattern in the AC automaton, search every matrix row once, record
which pattern row matched and at which column, then check vertical alignment.

Algorithm
---------
1. Build AC automaton from {P[0], P[1], …, P[PR-1]}.
2. For each matrix row i, run the automaton; record hits:
       hits[i][row_id].add(col)   — P[row_id] ends at column col in M[i]
3. For each candidate window (top_i, j):
       Check that for every 0 ≤ rid < PR, j ∈ hits[top_i + rid][rid].

Complexity
----------
Preprocessing : O(PR * PC)  — build trie + failure links
Search        : O(NR * NC + matches)
Alignment     : O(out_rows * out_cols * PR)
"""

from collections import deque, defaultdict


def engine_aho(M, P):
    """
    Aho-Corasick over all PR pattern rows, then alignment check.

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

    # --- Phase 1: Build AC automaton ---
    # Each node is a dict with 'next', 'fail', 'out' (pattern-row IDs)
    nodes = [{'next': {}, 'fail': 0, 'out': []}]

    def add_pattern(row_id, pat):
        nonlocal comps
        s = 0
        for sym in pat:
            comps += 1
            nxt = nodes[s]['next'].get(sym)
            if nxt is None:
                # Create a new trie node for this symbol
                nodes.append({'next': {}, 'fail': 0, 'out': []})
                nxt = len(nodes) - 1
                nodes[s]['next'][sym] = nxt
            s = nxt
        nodes[s]['out'].append(row_id)   # this node terminates pattern row_id

    for rid in range(PR):
        add_pattern(rid, P[rid])

    # BFS to compute failure (suffix) links
    q = deque()
    for sym, nxt in nodes[0]['next'].items():
        nodes[nxt]['fail'] = 0   # depth-1 nodes: suffix is root
        q.append(nxt)

    while q:
        r = q.popleft()
        for sym, u in nodes[r]['next'].items():
            q.append(u)
            # Walk failure links of r until we can extend with sym
            f = nodes[r]['fail']
            while f != 0 and sym not in nodes[f]['next']:
                comps += 1
                f = nodes[f]['fail']
            nodes[u]['fail'] = nodes[f]['next'][sym] if sym in nodes[f]['next'] else 0
            # Output links: inherit outputs of the suffix-link target
            nodes[u]['out'].extend(nodes[nodes[u]['fail']]['out'])

    # --- Phase 2: Scan every matrix row with the AC automaton ---
    # hits[i][rid] = set of column-start positions where P[rid] matches in M[i]
    hits = [defaultdict(set) for _ in range(NR)]
    for i in range(NR):
        state = 0
        for col, sym in enumerate(M[i]):
            comps += 1
            # Follow failure links until we can transition on sym
            while state != 0 and sym not in nodes[state]['next']:
                comps += 1
                state = nodes[state]['fail']
            state = nodes[state]['next'].get(sym, 0)

            if nodes[state]['out']:
                for rid in nodes[state]['out']:
                    # Pattern P[rid] ends at column `col`; start = col - PC + 1
                    start = col - PC + 1
                    if start >= 0:
                        hits[i][rid].add(start)

    # --- Phase 3: Alignment check ---
    out_rows = NR - PR + 1
    out_cols = NC - PC + 1
    for top_i in range(out_rows):
        for j in range(out_cols):
            ok = True
            for rid in range(PR):
                comps += 1
                # Each pattern row must match at the same column j in the corresponding matrix row
                if j not in hits[top_i + rid].get(rid, set()):
                    ok = False
                    break
            if ok:
                matches += 1
            steps.append({'pos': (top_i, j), 'ok': ok, 'cells': [(top_i, j, ok)], 'm': matches, 'c': comps})

    return steps
