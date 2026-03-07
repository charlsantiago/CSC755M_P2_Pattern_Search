# CSC755M P2 — 2D Pattern Search Studio

A visual, interactive tool for studying seven 2-D pattern-matching algorithms side-by-side.
Each algorithm searches for a sub-matrix **P** (the pattern) inside a larger integer matrix **M**.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [How to Run](#how-to-run)
3. [Input Format](#input-format)
4. [Sample Dataset (used throughout this document)](#sample-dataset)
5. [Algorithms](#algorithms)
   - [1. Naive (Brute-Force)](#1-naive-brute-force)
   - [2. Rabin-Karp (2D Rolling Hash)](#2-rabin-karp-2d-rolling-hash)
   - [3. KMP Row-Filter + Naive Vertical Verify](#3-kmp-row-filter--naive-vertical-verify)
   - [4. Boyer-Moore Bad-Character Row-Filter](#4-boyer-moore-bad-character-row-filter)
   - [5. Aho-Corasick Multi-Row Search](#5-aho-corasick-multi-row-search)
   - [6. Bird-Baker (AC Horizontal + KMP Vertical)](#6-bird-baker-ac-horizontal--kmp-vertical)
   - [7. KMP Horizontal + Naive Vertical](#7-kmp-horizontal--naive-vertical)
6. [Complexity Summary](#complexity-summary)
7. [Best-Case Datasets](#best-case-datasets)
8. [GUI Guide](#gui-guide)

---

## Project Structure

```
CSC755M_P2_Pattern_Search/
├── main.py                  # GUI application (tkinter)
├── main_v3.py               # Original monolithic backup
├── engines/
│   ├── __init__.py          # Re-exports all 7 engine functions
│   ├── helpers.py           # Shared: kmp_build_lps, kmp_search_row, ACNode, ac_build
│   ├── naive.py             # engine_naive
│   ├── rabin_karp.py        # engine_rk
│   ├── kmp.py               # engine_kmp
│   ├── boyer_moore.py       # engine_bm
│   ├── aho_corasick.py      # engine_aho
│   ├── bird_baker.py        # engine_bb
│   └── kmp_naive.py         # engine_kmp_nv
└── datasets/
    ├── naive_best_matrix.txt / naive_best_pattern.txt
    ├── rk_best_matrix.txt    / rk_best_pattern.txt
    ├── kmp_best_matrix.txt   / kmp_best_pattern.txt
    ├── bm_best_matrix.txt    / bm_best_pattern.txt
    ├── aho_best_matrix.txt   / aho_best_pattern.txt
    ├── bb_best_matrix.txt    / bb_best_pattern.txt
    └── kmp_nv_best_matrix.txt / kmp_nv_best_pattern.txt
```

---

## How to Run

```bash
# Install dependencies (matplotlib for the Growth Chart only)
pip install matplotlib

# Launch the GUI
python main.py
```

Python 3.8 or newer is required. No other third-party packages are needed for core search.

---

## Input Format

Both the matrix and pattern are entered as space-separated integers, one row per line.

```
# Matrix example
1 2 3 4 5
6 7 2 3 8
9 5 6 1 5

# Pattern example
2 3
5 6
```

Values can be any integers. Rows must all have the same number of columns.

---

## Sample Dataset

The following **6×6 matrix** and **2×2 pattern** are used in the walkthroughs below.
Paste them directly into the GUI to follow along.

### Matrix (6 rows × 6 columns)

```
1 2 3 4 5 6
7 2 3 8 2 3
9 5 6 1 5 6
1 2 3 4 5 6
7 2 3 8 2 3
9 5 6 1 5 6
```

### Pattern (2 rows × 2 columns)

```
2 3
5 6
```

### Expected Matches

The pattern `[[2,3],[5,6]]` appears at four positions (top-left corners):

| Match # | Row | Col | Window                        |
|---------|-----|-----|-------------------------------|
| 1       | 1   | 1   | M[1..2][1..2] = `[2,3]/[5,6]` |
| 2       | 1   | 4   | M[1..2][4..5] = `[2,3]/[5,6]` |
| 3       | 4   | 1   | M[4..5][1..2] = `[2,3]/[5,6]` |
| 4       | 4   | 4   | M[4..5][4..5] = `[2,3]/[5,6]` |

---

## Algorithms

### 1. Naive (Brute-Force)

**File:** `engines/naive.py`

#### Theory

The simplest possible approach. Slide the pattern window over every valid position
`(i, j)` in the matrix — there are `(NR-PR+1) × (NC-PC+1)` such positions — and
compare all `PR × PC` cells one by one, stopping early on the first mismatch.

No preprocessing. No skipping.

#### Step-by-step Logic

```
for i in 0 .. NR-PR:          # every valid top row
  for j in 0 .. NC-PC:        # every valid left column
    for pi in 0 .. PR-1:      # pattern row
      for pj in 0 .. PC-1:    # pattern column
        compare M[i+pi][j+pj] vs P[pi][pj]
        if mismatch → break (try next window)
    if all cells matched → record match at (i, j)
```

#### Walkthrough on Sample Dataset

Matrix is 6×6, pattern is 2×2.
Valid window positions: rows 0–4, columns 0–4 → **25 windows**.

| Window | Row-0 check      | Row-1 check      | Result |
|--------|------------------|------------------|--------|
| (0,0)  | M[0][0,1]=[1,2] vs [2,3] → FAIL at col 0 | skipped | No match |
| (0,1)  | M[0][1,2]=[2,3] vs [2,3] → OK           | M[1][1,2]=[2,3] vs [5,6] → FAIL | No match |
| (1,1)  | M[1][1,2]=[2,3] vs [2,3] → OK           | M[2][1,2]=[5,6] vs [5,6] → OK   | **MATCH** |
| (1,4)  | M[1][4,5]=[2,3] vs [2,3] → OK           | M[2][4,5]=[5,6] vs [5,6] → OK   | **MATCH** |
| ...    | ...              | ...              | ...    |

All 25 windows are visited; 4 matches found.

#### Complexity

| Phase       | Time                                      | Space |
|-------------|-------------------------------------------|-------|
| Preprocessing | O(1)                                    | O(1)  |
| Search      | O((NR-PR+1)(NC-PC+1) × PR × PC)          | O(1)  |
| **Total**   | **O(NR × NC × PR × PC)**                 | O(1)  |

#### Best Case

Pattern's first cell does not appear anywhere in the matrix. Every window fails on
the very first comparison → **1 comparison per window**.

---

### 2. Rabin-Karp (2D Rolling Hash)

**File:** `engines/rabin_karp.py`

#### Theory

Instead of comparing cells directly, Rabin-Karp hashes entire windows and only
performs a cell-level verification when a hash matches. The 2D version builds the
hash in two passes:

1. **Horizontal pass** — for each matrix row, compute a sliding-window polynomial
   hash of width `PC`. This produces one hash per valid column start per row.

2. **Vertical pass** — for each valid column start `j`, roll a polynomial hash
   of height `PR` downward over the row-hashes. This gives one 2D hash per window.

3. **Verification** — when the 2D hash equals the pattern hash, compare cells to
   confirm (handles hash collisions).

**Double hashing** uses two independent `(base, mod)` pairs to reduce the
false-positive rate to near zero.

#### Hash Formula (Horner's method)

```
hash(row[0..PC-1]) = row[0]*base^(PC-1) + row[1]*base^(PC-2) + ... + row[PC-1]

# Sliding (remove outgoing, add incoming):
hash_new = (hash_old - row[j-1] * base^(PC-1)) * base + row[j+PC-1]

# Vertical rolling works the same way over row-hashes.
```

#### Step-by-step Logic

```
1. Compute pattern hash ph = vertical_hash(row_hashes(P))
2. For each matrix row r:
       row_h[r] = sliding_window_hashes(M[r], width=PC)
3. For column j, build initial vertical hash over rows 0..PR-1:
       vhash[0][j] = vertical_hash(row_h[0..PR-1][j])
   Roll downward:
       vhash[i][j] = roll(vhash[i-1][j], remove row_h[i-1][j], add row_h[i+PR-1][j])
4. For each window (i, j):
       if vhash[i][j] == ph  →  verify cell-by-cell
       else                  →  skip (record as non-match)
```

#### Walkthrough on Sample Dataset

- Pattern hash `ph` is computed once from `P = [[2,3],[5,6]]`.
- Row hashes are computed for all 6 matrix rows at width PC=2.
- Vertical hashes are rolled for rows 0–4 at each of the 5 column positions.
- At positions (1,1), (1,4), (4,1), (4,4) the hash matches → cell verification confirms **4 matches**.
- All other 21 windows have a different hash → skipped with **1 comparison each**.

#### Complexity

| Phase          | Time                          | Space    |
|----------------|-------------------------------|----------|
| Row hashes     | O(NR × NC)                    | O(NR × NC) |
| Vertical roll  | O(NR × NC)                    | O(NR × NC) |
| Search         | O(NR × NC) avg, O(NR×NC×PR×PC) worst | — |
| **Total**      | **O(NR × NC) average**        | O(NR × NC) |

#### Best Case

All matrix values are identical (e.g., all 1s) and the pattern contains a different
value (e.g., all 9s). The pattern hash never matches any window hash →
**0 cell-level verifications**, only 1 hash comparison per window.

---

### 3. KMP Row-Filter + Naive Vertical Verify

**File:** `engines/kmp.py`

#### Theory

Knuth-Morris-Pratt (KMP) avoids re-examining characters by precomputing a
**Longest Proper Prefix that is also a Suffix (LPS)** array for the pattern.
When a mismatch occurs at position `k`, the LPS tells us the longest border of
`P[0..k-1]`, so the pattern can be shifted to align that border — never re-scanning
already-matched text.

In 2D, KMP is applied to the **first pattern row only** to quickly find which
columns in each text row are possible match starts. Only those candidate columns
proceed to a naive verification of the remaining pattern rows.

#### LPS Array Construction

```
P[0] = [2, 3]
LPS  = [0, 0]

# LPS[i] = length of longest proper prefix of P[0][0..i] that is also a suffix.
# [2,3] has no prefix that is also a suffix → LPS = [0, 0].
```

More complex example:
```
P[0] = [1, 2, 1, 2, 3]
LPS  = [0, 0, 1, 2, 0]
# "1,2,1,2" → prefix "1,2" == suffix "1,2" → length 2
```

#### Step-by-step Logic

```
1. Build LPS for P[0]  (once, O(PC))
2. For each text row i (potential top row):
   a. Run KMP(M[i], P[0], LPS) → set of candidate column starts {j}
   b. For each valid j in {j}:
        Compare P[1], P[2], ... P[PR-1] naively against M[i+1..i+PR-1]
        If all match → record match at (i, j)
```

#### KMP Search Trace (Row 1 of sample matrix)

```
Text row M[1] = [7, 2, 3, 8, 2, 3]
Pattern P[0]  = [2, 3]
LPS           = [0, 0]

t=0: M[1][0]=7 vs P[0][0]=2  → mismatch, j=0 stays at 0, advance t
t=1: M[1][1]=2 vs P[0][0]=2  → match, j→1
t=2: M[1][2]=3 vs P[0][1]=3  → match, j→2 (= PC) → HIT at col 1, j resets via LPS[1]=0
t=3: M[1][3]=8 vs P[0][0]=2  → mismatch, advance t
t=4: M[1][4]=2 vs P[0][0]=2  → match, j→1
t=5: M[1][5]=3 vs P[0][1]=3  → match, j→2 → HIT at col 4

Candidates for row i=1: {1, 4}
```

Both candidates pass the vertical check (P[1]=[5,6] found at M[2][1..2] and M[2][4..5]).

#### Complexity

| Phase         | Time                                 | Space  |
|---------------|--------------------------------------|--------|
| LPS build     | O(PC)                                | O(PC)  |
| KMP scan      | O(NR × NC)                           | O(1)   |
| Vertical verify | O(candidates × (PR-1) × PC)        | O(1)   |
| **Total**     | **O(NR × NC)** when candidates are few | O(PC) |

#### Best Case

P[0][0] does not appear in the matrix. KMP's `j` pointer stays at 0 throughout
every row → no candidates, no vertical verification.

---

### 4. Boyer-Moore Bad-Character Row-Filter

**File:** `engines/boyer_moore.py`

#### Theory

Boyer-Moore scans the pattern **right-to-left** against each text row window.
When a mismatch occurs at pattern position `k`, the **bad-character heuristic**
looks up where that mismatching text character last appears in the pattern and
shifts the pattern to align that occurrence — often skipping several positions
at once.

Only the **bad-character rule** is implemented here (the good-suffix rule is
omitted). After a first-row match, remaining rows are verified naively.

#### Bad-Character Table

```
P[0] = [2, 3]
bad_char = { 2: 0,   # last position of value 2 in P[0]
             3: 1 }  # last position of value 3 in P[0]
# Any value not in the table → treated as position -1 (not present)
```

#### Shift Formula

```
When mismatch at pattern position k, text character is x:
    shift = max(1, k - bad_char.get(x, -1))

Examples:
  x=7 (not in pattern): shift = max(1, k - (-1)) = k + 1  (large jump)
  x=2 (last at pos 0):  shift = max(1, k - 0)   = k       (align occurrence)
  x=3 (last at pos 1):  shift = max(1, k - 1)
```

#### Step-by-step Logic

```
1. Build bad_char table for P[0]
2. For each text row i:
   j = 0   # current window start
   while j <= NC - PC:
     scan P[0] right-to-left (k from PC-1 down to 0):
       compare M[i][j+k] vs P[0][k]
       if mismatch:
         shift = max(1, k - bad_char.get(M[i][j+k], -1))
         j += shift
         break
     else (full P[0] match):
       verify P[1..PR-1] naively
       j += 1
```

#### Walkthrough on Sample Dataset

Text row M[1] = `[7, 2, 3, 8, 2, 3]`, P[0] = `[2, 3]`

```
j=0: scan right-to-left k=1: M[1][1]=2 vs P[0][1]=3 → mismatch
     x=2, bad_char[2]=0, shift = max(1, 1-0) = 1 → j=1

j=1: k=1: M[1][2]=3 vs P[0][1]=3 → OK
     k=0: M[1][1]=2 vs P[0][0]=2 → OK  → full match, verify row 1 → MATCH at (1,1)
     j=2

j=2: k=1: M[1][3]=8 vs P[0][1]=3 → mismatch
     x=8 not in pattern, shift = max(1, 1-(-1)) = 2 → j=4

j=4: k=1: M[1][5]=3 vs P[0][1]=3 → OK
     k=0: M[1][4]=2 vs P[0][0]=2 → OK  → full match, verify row 1 → MATCH at (1,4)
     j=5  (done, 5 > 6-2=4)
```

Only 5 comparisons on row 1 vs 6 for naive.

#### Complexity

| Phase         | Time                              | Space  |
|---------------|-----------------------------------|--------|
| bad_char build | O(PC)                            | O(PC)  |
| Row scan      | O(NC / PC) best, O(NC × PC) worst | O(1)   |
| Vertical verify | O(candidates × (PR-1) × PC)    | O(1)   |
| **Total**     | **O(NR × NC / PC) best-case**     | O(PC)  |

#### Best Case

Matrix is all one value (e.g., all 9s) and the first character of P[0] is different
(e.g., P[0][0]=1). Every right-to-left scan mismatches at position `PC-1` on a
character not in the pattern → shift = `PC` every time →
**minimum possible comparisons**.

---

### 5. Aho-Corasick Multi-Row Search

**File:** `engines/aho_corasick.py`

#### Theory

Aho-Corasick (AC) builds a **finite automaton** (trie + failure links) from
multiple patterns simultaneously. It processes each text row in a single left-to-right
pass, outputting every pattern occurrence without backtracking.

For 2D matching, all `PR` pattern rows are treated as separate 1D patterns in one
AC automaton. After scanning all matrix rows, an alignment check confirms which
windows have all PR rows matching at the same column.

#### Data Structure: AC Automaton

```
Trie node:
  next : dict(symbol → node_id)    # child transitions
  fail : node_id                   # longest proper suffix in the trie
  out  : list[pattern_row_id]      # pattern rows that end at this node
```

#### Phase 1 — Build Trie

Insert each pattern row P[0], P[1], ..., P[PR-1] into the trie one symbol at a time.

```
Pattern rows: P[0]=[2,3]  P[1]=[5,6]

Trie after insertion:
  root --2--> node1 --3--> node2  (out=[0])
  root --5--> node3 --6--> node4  (out=[1])
```

#### Phase 2 — BFS Failure Links

Failure links are computed breadth-first. For a node `u` reached by symbol `s` from
parent `p`, follow `p`'s failure link upward until we find a node that also has a
`s`-transition, or reach root.

```
node1.fail = root  (depth-1 nodes always point to root)
node3.fail = root
node2.fail = root  (no proper suffix of [2,3] is a prefix of any pattern)
node4.fail = root
```

#### Phase 3 — Scan Matrix Rows

```
For each matrix row i, run the automaton left-to-right:
  state = root
  for col, sym in enumerate(M[i]):
    while state != root and sym not in state.next:
      state = state.fail        # follow failure link
    state = state.next[sym] if sym in state.next else root
    for rid in state.out:
      hits[i][rid].add(col - PC + 1)   # record column start
```

#### Phase 4 — Alignment Check

```
For each candidate top-left (top_i, j):
  for rid in 0..PR-1:
    if j not in hits[top_i + rid][rid]:
      → no match, break
  → MATCH
```

#### Walkthrough on Sample Dataset

Scanning M[1] = `[7, 2, 3, 8, 2, 3]` with the automaton:

```
col=0: sym=7, not in root.next → stay at root
col=1: sym=2 → move to node1
col=2: sym=3 → move to node2 → out=[0] → hits[1][0].add(1)
col=3: sym=8, not in node2.next, follow fail → root; 8 not in root.next → stay at root
col=4: sym=2 → node1
col=5: sym=3 → node2 → hits[1][0].add(4)
```

Row 1 hits: `hits[1][0] = {1, 4}` (P[0]=[2,3] found at columns 1 and 4).

Similarly, scanning M[2] = `[9, 5, 6, 1, 5, 6]`:
`hits[2][1] = {1, 4}` (P[1]=[5,6] found at columns 1 and 4).

Alignment check: `(1,1)` → `1 in hits[1][0]` ✓ and `1 in hits[2][1]` ✓ → **MATCH**.

#### Complexity

| Phase         | Time                     | Space        |
|---------------|--------------------------|--------------|
| Build trie    | O(PR × PC)               | O(PR × PC)   |
| Failure links | O(PR × PC)               | —            |
| Scan rows     | O(NR × NC)               | O(NR × NC)   |
| Alignment     | O(out_rows × out_cols × PR) | O(out_rows × NC) |
| **Total**     | **O(NR × NC)**           | O(NR × NC)   |

#### Best Case

The matrix rows are all identical and equal to P[0]. Every position in every row
hits the automaton's output state, producing many hits, and the alignment check
finds all matches quickly. AC shines when many rows share pattern prefixes.

---

### 6. Bird-Baker (AC Horizontal + KMP Vertical)

**File:** `engines/bird_baker.py`

#### Theory

Bird (1977) and Baker (1978) independently extended 1D exact-match algorithms to
two dimensions using a two-phase approach that is strictly more efficient than the
plain Aho-Corasick approach above.

**Key insight:** reduce the 2D problem to two 1D problems using *tokenization*.

1. **Tokenization** — assign a unique integer token to each distinct row of the
   pattern. Identical pattern rows get the same token.

2. **Phase 1 — Horizontal (Aho-Corasick)** — build an AC automaton over the unique
   pattern rows. Scan each matrix row. Whenever a pattern row is found at position
   `(i, col)`, write its token into `token_grid[i][col]`.

3. **Phase 2 — Vertical (KMP)** — for each valid column `j`, extract the column
   vector from `token_grid` and run KMP with the *token sequence* of the pattern.
   A KMP match at row `top_i` means a full 2D match at `(top_i, j)`.

#### Why It Improves on Plain AC

Plain AC alignment is `O(out_rows × out_cols × PR)`. Bird-Baker replaces that with
KMP vertical which is `O(NR × out_cols)` — independent of PR after preprocessing.

#### Step-by-step Logic

```
1. Token assignment:
   unique rows of P → {(2,3): tok=1, (5,6): tok=2}
   tok_seq = [1, 2]   (tokens for P[0], P[1])

2. Build AC automaton over {(2,3), (5,6)}

3. Scan each matrix row; fill token_grid:
   M[1] = [7,2,3,8,2,3] → token_grid[1][1]=1, token_grid[1][4]=1
   M[2] = [9,5,6,1,5,6] → token_grid[2][1]=2, token_grid[2][4]=2
   (other rows: no hits → token_grid entries absent/0)

4. KMP vertical for column j=1:
   stream = [token_grid[0][1], token_grid[1][1], ..., token_grid[5][1]]
          = [0, 1, 2, 0, 1, 2]
   tok_seq = [1, 2]
   KMP finds [1,2] at positions 1 and 4 → matches at (1,1) and (4,1)

5. KMP vertical for column j=4:
   stream = [0, 1, 2, 0, 1, 2]
   KMP finds matches at (1,4) and (4,4)
```

#### Walkthrough — Token Grid

```
         col: 0  1  2  3  4  5
row 0:        0  0  0  0  0  0   (no pattern row matches in "1 2 3 4 5 6")
                                  Wait — [2,3] matches at col 1. So token_grid[0][1]=1.
row 1:        0  1  0  0  1  0   ([2,3] at col 1 and 4)
row 2:        0  2  0  0  2  0   ([5,6] at col 1 and 4)
row 3:        0  1  0  0  1  0
row 4:        0  1  0  0  1  0   (wait — M[3]=[1,2,3,4,5,6] → [2,3] at col 1)
row 5:        0  2  0  0  2  0

Column j=1 stream: [1, 1, 2, 1, 1, 2]
tok_seq = [1, 2]
KMP hits: [1,2] at index 1 (rows 1-2) and index 4 (rows 4-5) → matches at (1,1) and (4,1)
```

#### Complexity

| Phase         | Time                       | Space        |
|---------------|----------------------------|--------------|
| Token assign  | O(PR × PC)                 | O(PR)        |
| AC build      | O(unique_rows × PC)        | O(unique_rows × PC) |
| AC scan rows  | O(NR × NC)                 | O(NR × out_cols) |
| KMP vertical  | O(PR) + O(NR × out_cols)   | O(PR)        |
| **Total**     | **O(NR × NC)**             | O(NR × NC)   |

#### Best Case

All pattern rows are identical (one unique row → single-node AC, KMP over a
length-1 token sequence). The AC phase is maximally fast and the KMP vertical
phase trivially degenerates to a linear scan.

---

### 7. KMP Horizontal + Naive Vertical

**File:** `engines/kmp_naive.py`

#### Theory

This engine is a practical variant that combines KMP efficiency in the horizontal
direction with simplicity in the vertical direction.

**Key optimization:** if the pattern has repeated rows (e.g., P[0] == P[2]),
build and store the LPS array only **once** and reuse it for both rows. This reduces
preprocessing cost proportional to the number of unique rows rather than PR.

#### Step-by-step Logic

```
1. Collect unique rows of P (deduplicate using a set).
2. Build LPS for each unique row (once per unique row).
3. For every matrix row i and every unique pattern row r:
       Run KMP(M[i], r, LPS[r]) → record column starts in row_hits[i][r]
4. For each candidate window (i, j):
       For pi = 0..PR-1:
         if j not in row_hits[i+pi][pat_rows[pi]] → skip
       If all rows hit → full cell-level verify → record match
```

#### Walkthrough on Sample Dataset

```
Unique pattern rows: {(2,3), (5,6)}
pat_rows = [(2,3), (5,6)]   (one entry per pattern row)

LPS for (2,3): [0, 0]
LPS for (5,6): [0, 0]

KMP scan of M[1]=[7,2,3,8,2,3] for (2,3):
  → hits at cols 1 and 4
  row_hits[1][(2,3)] = {1, 4}

KMP scan of M[2]=[9,5,6,1,5,6] for (5,6):
  → hits at cols 1 and 4
  row_hits[2][(5,6)] = {1, 4}

Alignment check (i=1, j=1):
  pi=0: pat_rows[0]=(2,3), check 1 in row_hits[1][(2,3)] = {1,4} → YES
  pi=1: pat_rows[1]=(5,6), check 1 in row_hits[2][(5,6)] = {1,4} → YES
  → full verify → MATCH at (1,1)
```

#### Comparison with Plain KMP (engine_kmp)

| Property              | KMP (engine_kmp)          | KMP-Naive (engine_kmp_nv)           |
|-----------------------|---------------------------|--------------------------------------|
| LPS arrays built      | 1 (for P[0] only)         | 1 per unique pattern row             |
| Horizontal phase      | KMP on P[0] only          | KMP on every unique row × every text row |
| Vertical phase        | Naive compare rows 1..PR-1 | Set-membership lookup then cell verify |
| Best for              | Pattern with many unique rows, good first-row filter | Pattern with many repeated rows |

#### Complexity

| Phase          | Time                                  | Space         |
|----------------|---------------------------------------|---------------|
| LPS build      | O(unique_rows × PC)                   | O(unique_rows × PC) |
| KMP scan       | O(NR × unique_rows × NC)              | O(NR × NC)    |
| Alignment      | O(out_rows × out_cols × PR)           | —             |
| **Total**      | **O(NR × unique_rows × NC)**          | O(NR × NC)    |

#### Best Case

All pattern rows are identical (1 unique row), and that value sequence is not
present in the matrix → row_hits is everywhere empty → alignment check trivially
fails for all windows.

---

## Complexity Summary

| Algorithm    | Preprocessing         | Search (avg)            | Space      |
|--------------|-----------------------|-------------------------|------------|
| Naive        | O(1)                  | O(NR×NC×PR×PC)          | O(1)       |
| Rabin-Karp   | O(NR×NC + PR×PC)      | O(NR×NC)                | O(NR×NC)   |
| KMP          | O(PC)                 | O(NR×NC)                | O(PC)      |
| Boyer-Moore  | O(PC)                 | O(NR×NC/PC) best        | O(PC)      |
| Aho-Corasick | O(PR×PC)              | O(NR×NC)                | O(NR×NC)   |
| Bird-Baker   | O(PR×PC)              | O(NR×NC)                | O(NR×NC)   |
| KMP-Naive    | O(unique×PC)          | O(NR×unique×NC)         | O(NR×NC)   |

> `NR×NC` = matrix size, `PR×PC` = pattern size, `unique` = number of unique pattern rows.

---

## Best-Case Datasets

Each `datasets/{engine}_best_matrix.txt` / `{engine}_best_pattern.txt` pair represents
an input where that engine performs the fewest comparisons relative to the matrix size.

| Engine    | Best-Case Condition                                      | Why                                                     |
|-----------|----------------------------------------------------------|---------------------------------------------------------|
| Naive     | P[0][0] not found anywhere in M                          | 1 comparison per window, immediate break                |
| RK        | All-1s matrix, all-9s pattern                            | Hash never matches → 0 cell verifications               |
| KMP       | P[0][0] not in M                                         | KMP j-pointer stays 0, no candidates forwarded          |
| BM        | All-9s matrix, P[0] = [1,2,3,4,5]                        | Mismatch on char not in pattern → shift = PC every time |
| Aho-Corasick | All-same-row matrix matching P[0], 7-row all-same pattern | AC finds every match instantly, alignment trivial     |
| Bird-Baker   | Same as Aho-Corasick                                     | AC + KMP vertical is always faster than AC alone        |
| KMP-Naive | All-same pattern rows, value not in matrix               | 1 unique LPS built, row_hits empty everywhere           |

---

## GUI Guide

| Control             | Description                                                    |
|---------------------|----------------------------------------------------------------|
| Load Presets        | Quick-fill matrix and pattern with built-in examples           |
| Input Matrix        | Paste space-separated integers, one row per line               |
| Sub-Pattern         | Paste the pattern (same format as matrix)                      |
| Algorithm selector  | Choose which of the 7 engines to visualize                     |
| Run Single Mode     | Animate the selected algorithm step by step                    |
| Start Multi-Race    | Run all 7 engines simultaneously and compare results           |
| Growth Chart        | Plot comparisons and execution time vs. matrix size            |
| Play / Pause        | Control animation speed                                        |
| Tracelog (right)    | Scroll through match positions and final benchmark summary     |
| Sash (divider)      | Drag the vertical bar between visualization and tracelog to resize |
| Scroll              | Mouse-wheel or scrollbars to pan the visualization area        |

### Color Legend (visualization)

| Color  | Meaning                              |
|--------|--------------------------------------|
| Green  | Cell confirmed as part of a full match |
| Red    | Cell that caused a mismatch          |
| Blue   | Cell in a window under examination   |
| Dark   | Idle / not yet visited               |
