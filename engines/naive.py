"""
Naive (Brute-Force) 2D Pattern Search
======================================
Theory
------
Slide the pattern over every valid (i, j) position in the matrix and compare
all PR*PC cells one by one.  No preprocessing, no skipping.

Complexity
----------
Time  : O((NR - PR + 1) * (NC - PC + 1) * PR * PC)  ≈ O(NR * NC * PR * PC)
Space : O(1)  (output steps list aside)

Key idea
--------
Simplest possible approach — it is the baseline against which all other
algorithms are compared.
"""


def engine_naive(M, P):
    """
    Brute-force 2D pattern search.

    Parameters
    ----------
    M : list[list[int]]  — the text matrix  (NR × NC)
    P : list[list[int]]  — the pattern       (PR × PC)

    Returns
    -------
    steps : list[dict]
        Each dict has:
          'pos'   : (i, j)         — top-left corner of the current window
          'ok'    : bool           — True if this window is a full match
          'cells' : [(r, c, bool)] — cells checked (with per-cell match flag)
          'm'     : int            — running match count
          'c'     : int            — running comparison count
    """
    steps, comps, matches = [], 0, 0

    # Guard: empty inputs or pattern larger than matrix
    if not M or not P or not M[0] or not P[0]:
        return steps
    NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
    if PR > NR or PC > NC:
        return steps

    # Outer loops: slide window over all valid top-left corners
    for i in range(NR - PR + 1):
        for j in range(NC - PC + 1):
            is_match = True
            cells = []

            # Inner loops: compare every cell inside the window
            for pi in range(PR):
                for pj in range(PC):
                    comps += 1
                    match_cell = (M[i + pi][j + pj] == P[pi][pj])
                    cells.append((i + pi, j + pj, match_cell))
                    if not match_cell:
                        is_match = False
                        break           # early exit on first mismatch in this row
                if not is_match:
                    break               # early exit on first mismatched row

            if is_match:
                matches += 1
            steps.append({'pos': (i, j), 'ok': is_match, 'cells': cells, 'm': matches, 'c': comps})

    return steps
