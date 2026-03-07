"""
2D Rabin-Karp (Double Rolling Hash)
=====================================
Theory
------
Rabin-Karp extends the classic 1-D rolling hash to two dimensions:

  1. **Row hashes** — for each matrix row, compute a sliding window hash of
     width PC using a polynomial base (base_col).  This gives one hash per
     valid column start per row.

  2. **Vertical rolling hash** — treat the PR consecutive row-hashes for a
     column position as a new 1-D string and roll a hash of length PR
     downward.  The result is one 2D hash per valid (i, j) window.

  3. **Verification** — when the 2D hash matches the pattern hash, do a
     cell-by-cell comparison to confirm (handles hash collisions).

Double hashing (two independent (base, mod) pairs) makes the false-positive
probability negligibly small.

Complexity
----------
Preprocessing : O(NR * NC + PR * PC)
Search        : O(NR * NC) average  (O(NR*NC*PR*PC) worst-case on many collisions)
Space         : O(NR * NC) for the row-hash arrays
"""


def engine_rk(M, P):
    """
    2D Rabin-Karp with double rolling hash plus verification.

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

    if PR == 0 or PC == 0 or NR == 0 or NC == 0 or PR > NR or PC > NC:
        return steps

    # --- Hash parameters (two independent moduli for double hashing) ---
    mod1, mod2         = 1_000_000_007, 1_000_000_009
    base_col1, base_col2 = 911382323,   972663749    # bases for horizontal (column) hash
    base_row1, base_row2 = 972663749,   911382323    # bases for vertical (row) hash

    def norm(v, mod):
        """Map a cell value into [0, mod)."""
        return v % mod

    def row_window_hashes(row, win, base, mod):
        """
        Return the list of polynomial rolling hashes for all windows of
        length `win` in `row`, using Horner's method then sliding removal.
        """
        if win > len(row):
            return []
        pow_base = pow(base, win - 1, mod)  # precompute base^(win-1) for leading-digit removal
        # Compute hash of the first window
        h = 0
        for k in range(win):
            h = (h * base + norm(row[k], mod)) % mod
        out = [h]
        # Slide: remove leading digit, add trailing digit
        for j in range(1, len(row) - win + 1):
            lead = norm(row[j - 1], mod)
            newv = norm(row[j + win - 1], mod)
            h = (h - lead * pow_base) % mod   # subtract contribution of outgoing element
            h = (h * base + newv) % mod        # shift left and add incoming element
            out.append(h)
        return out

    # --- Compute pattern hash (vertical hash over pattern row-hashes) ---
    p_row_h1 = [row_window_hashes(P[r], PC, base_col1, mod1)[0] for r in range(PR)]
    p_row_h2 = [row_window_hashes(P[r], PC, base_col2, mod2)[0] for r in range(PR)]
    ph1, ph2 = 0, 0
    for r in range(PR):
        ph1 = (ph1 * base_row1 + p_row_h1[r]) % mod1
        ph2 = (ph2 * base_row2 + p_row_h2[r]) % mod2
    p_hash = (ph1, ph2)

    # --- Compute row-hashes for every row of the matrix ---
    row_h1 = [row_window_hashes(M[r], PC, base_col1, mod1) for r in range(NR)]
    row_h2 = [row_window_hashes(M[r], PC, base_col2, mod2) for r in range(NR)]

    out_rows = NR - PR + 1
    out_cols = NC - PC + 1
    pow_row1 = pow(base_row1, PR - 1, mod1)   # for vertical rolling removal
    pow_row2 = pow(base_row2, PR - 1, mod2)

    # --- Build vertical (2D) hash grid via downward rolling ---
    vhash = [[(0, 0)] * out_cols for _ in range(out_rows)]
    for j in range(out_cols):
        # Initial vertical hash for the topmost window at column j
        h1, h2 = 0, 0
        for k in range(PR):
            h1 = (h1 * base_row1 + row_h1[k][j]) % mod1
            h2 = (h2 * base_row2 + row_h2[k][j]) % mod2
        vhash[0][j] = (h1, h2)

        # Roll the vertical window downward
        for i in range(1, out_rows):
            # Remove the outgoing top row-hash
            top1, top2 = row_h1[i - 1][j], row_h2[i - 1][j]
            # Add the incoming bottom row-hash
            bot1, bot2 = row_h1[i + PR - 1][j], row_h2[i + PR - 1][j]

            h1 = (h1 - top1 * pow_row1) % mod1
            h1 = (h1 * base_row1 + bot1) % mod1

            h2 = (h2 - top2 * pow_row2) % mod2
            h2 = (h2 * base_row2 + bot2) % mod2

            vhash[i][j] = (h1, h2)

    # --- Search: hash comparison + verification on match ---
    for i in range(out_rows):
        for j in range(out_cols):
            comps += 1
            if vhash[i][j] != p_hash:
                # Hash mismatch — skip without cell-level comparison
                steps.append({'pos': (i, j), 'ok': False, 'cells': [(i, j, False)], 'm': matches, 'c': comps})
                continue

            # Potential match — verify cell by cell to rule out collision
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
