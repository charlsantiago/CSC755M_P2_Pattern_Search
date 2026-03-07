"""
Boyer-Moore Bad-Character Row-Filter + Naive Vertical Verify
=============================================================
Theory
------
Boyer-Moore scans P[0] right-to-left against each text row and uses the
*bad-character* heuristic to skip forward when a mismatch is found.  This
can skip large portions of the text in practice (sub-linear on typical
inputs).  After a row-0 match the remaining rows are verified naively.

Algorithm
---------
1. Build the bad-character table for P[0]:
       bc[x] = last occurrence index of symbol x in P[0]
2. For each text row i that could be the top of a match:
   a. Slide j along the row using BM bad-character shifts.
   b. When P[0] fully matches at (i, j), verify P[1..PR-1] naively.

Complexity
----------
Preprocessing : O(PC + alphabet_size)
Search        : O(NR * NC / PC) best-case, O(NR * NC * PC) worst-case
"""


def engine_bm(M, P):
    """
    Boyer-Moore bad-character on first pattern row + naive vertical verify.

    Parameters
    ----------
    M : list[list[int]]  — text matrix  (NR × NC)
    P : list[list[int]]  — pattern       (PR × PC)

    Returns
    -------
    steps : list[dict]
        Each dict: 'pos', 'ok', 'cells', 'm', 'c'  (see naive.py for schema)
    """
    steps, comps, matches = [], 0, 0

    if not M or not P or not M[0] or not P[0]:
        return steps
    NR, NC, PR, PC = len(M), len(M[0]), len(P), len(P[0])
    if PR > NR or PC > NC:
        return steps

    # --- Bad-character table: maps each symbol to its last position in P[0] ---
    # If a symbol is not in P[0] we treat its last position as -1 (not found).
    bad_char = {val: k for k, val in enumerate(P[0])}
    # Note: iterating left-to-right overwrites earlier positions, leaving the
    # rightmost occurrence for each symbol — exactly what bad-character needs.

    for i in range(NR - PR + 1):
        j = 0   # current window start column
        while j <= NC - PC:
            # Scan P[0] right-to-left against M[i][j..j+PC-1]
            k = PC - 1
            cells = []
            while k >= 0:
                comps += 1
                ok_cell = (P[0][k] == M[i][j + k])
                cells.append((i, j + k, ok_cell))
                if not ok_cell:
                    # Bad-character shift: align P[0]'s last occurrence of the
                    # mismatching text character with position k, but shift at
                    # least 1 to guarantee progress.
                    shift = max(1, k - bad_char.get(M[i][j + k], -1))
                    steps.append({'pos': (i, j), 'ok': False, 'cells': cells, 'm': matches, 'c': comps})
                    j += shift
                    break
                k -= 1
            else:
                # P[0] fully matched at (i, j) — verify remaining rows naively
                is_match = True
                cells = []
                for pj in range(PC):
                    cells.append((i, j + pj, True))   # row-0 is already confirmed

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
                j += 1  # after a full match, advance by 1 (good-suffix not implemented here)

    return steps
