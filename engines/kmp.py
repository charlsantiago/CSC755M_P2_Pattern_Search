"""
KMP Row-Filter + Naive Vertical Verify
========================================
Theory
------
Knuth-Morris-Pratt (KMP) eliminates redundant comparisons via the
*failure function* (LPS array).  In 2D we apply it to the first pattern
row to quickly identify candidate column positions, then verify remaining
rows naively.

Algorithm
---------
1. Build the LPS array for P[0] (first row of pattern).
2. For each text row i that can be the top of a match:
   a. Run KMP on M[i] with P[0] to find all columns j where P[0] matches.
   b. For each such candidate column j, compare P[1..PR-1] row by row
      against M[i+1..i+PR-1] naively.

Complexity
----------
Preprocessing : O(PC)  — build LPS for P[0]
Search        : O(NR * NC + candidates * (PR-1) * PC)
              ≈ O(NR * NC)  when few candidates pass row-0 filter
"""

from .helpers import kmp_build_lps, kmp_search_row


def engine_kmp(M, P):
    """
    KMP on the first pattern row to filter candidates, then naive verify.

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

    # --- Preprocessing: build LPS for the first pattern row ---
    lps, lps_comps = kmp_build_lps(P[0])
    comps += lps_comps
    out_cols = NC - PC + 1

    for i in range(NR - PR + 1):
        # --- Horizontal phase: KMP on M[i] to find candidate columns ---
        candidate_js, row_comps = kmp_search_row(M[i], P[0], lps)
        comps += row_comps
        # Keep only candidates within valid output range
        candidate_set = {j for j in candidate_js if 0 <= j < out_cols}

        for j in range(out_cols):
            if j not in candidate_set:
                # Row 0 did not match at column j — skip
                steps.append({'pos': (i, j), 'ok': False, 'cells': [(i, j, True)], 'm': matches, 'c': comps})
                continue

            # --- Vertical phase: row 0 matched, verify remaining rows naively ---
            ok = True
            cells = []
            # Record row-0 cells as matched (KMP confirmed them)
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
