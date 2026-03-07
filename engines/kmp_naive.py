"""
KMP Horizontal (per unique row) + Naive Vertical Verify
=========================================================
Theory
------
This engine deduplicates the pattern rows: each *unique* pattern row gets its
own KMP automaton, which is built once and reused every time that row appears
in the text matrix.  The horizontal phase produces a lookup table of which
columns each unique row matched in each text row.  The vertical phase then
checks, for each candidate window, whether every pattern row matched at the
required column.

Algorithm
---------
1. Collect the set of unique rows in P.
2. Build an LPS array (KMP failure function) for each unique row.
3. For every matrix row i and every unique pattern row r:
       Run KMP → record all column starts where r matches in M[i].
4. For each candidate window (i, j):
       Verify that pat_rows[pi] matched at column j in matrix row (i + pi)
       for every 0 ≤ pi < PR.

Complexity
----------
Preprocessing : O(unique_rows * PC)
Search        : O(NR * unique_rows * NC)  — better than naive when few unique rows
Verify        : O(matches * PR * PC)      — only needed for confirmed candidates
"""

from collections import defaultdict
from .helpers import kmp_build_lps, kmp_search_row


def engine_kmp_nv(M, P):
    """
    KMP per unique pattern row (horizontal) + naive vertical check.

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

    # Convert pattern rows to tuples for hashing
    pat_rows = [tuple(row) for row in P]

    # --- Preprocessing: build LPS for each unique pattern row ---
    unique_rows = list(set(pat_rows))
    lps_map = {}
    for r in unique_rows:
        lps, lps_comps = kmp_build_lps(list(r))
        lps_map[r] = lps
        comps += lps_comps

    # --- Horizontal phase: KMP scan every matrix row for every unique pattern row ---
    # row_hits[i][r] = set of column starts where pattern row `r` matches in M[i]
    row_hits = [defaultdict(set) for _ in range(NR)]
    for i in range(NR):
        text_row = M[i]
        for r in unique_rows:
            cols, row_comps = kmp_search_row(text_row, list(r), lps_map[r])
            comps += row_comps
            for c0 in cols:
                if c0 <= NC - PC:   # only valid start positions
                    row_hits[i][r].add(c0)

    # --- Vertical phase: check alignment for every candidate window ---
    for i in range(NR - PR + 1):
        for j in range(NC - PC + 1):
            comps += 1
            ok = True

            # Quick check: does each pattern row appear at column j in the right text row?
            for pi in range(PR):
                if j not in row_hits[i + pi][pat_rows[pi]]:
                    ok = False
                    break

            if ok:
                # Full cell-level verify (also builds the cells list for the GUI)
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
            else:
                cells = [(i, j, False)]   # anchor cell only for skipped windows

            if ok:
                matches += 1

            steps.append({'pos': (i, j), 'ok': ok, 'cells': cells, 'm': matches, 'c': comps})

    return steps
