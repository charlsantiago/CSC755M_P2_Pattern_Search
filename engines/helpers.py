"""
Shared helpers for the 2D pattern-matching engines.

kmp_build_lps / kmp_search_row
    Classic 1-D KMP primitives used by:
        engine_kmp, engine_bb, engine_kmp_nv

ACNode / ac_build / ac_search_stream
    Aho-Corasick automaton over arbitrary symbols (kept for completeness;
    the live engines use inline dicts for speed, but this object-based
    version is useful for study/extension).
"""

from collections import deque


# ---------------------------------------------------------------------------
# KMP helpers
# ---------------------------------------------------------------------------

def kmp_build_lps(pat):
    """
    Build the Knuth-Morris-Pratt Longest-Proper-Suffix (LPS / failure) array.

    Parameters
    ----------
    pat : list
        The pattern sequence (any comparable elements).

    Returns
    -------
    lps : list[int]
        lps[i] = length of the longest proper prefix of pat[0..i] that is
        also a suffix.
    comps : int
        Number of element comparisons made during construction.
    """
    lps = [0] * len(pat)
    j = 0       # length of previous longest prefix-suffix
    comps = 0
    for i in range(1, len(pat)):
        # Fall back along failure links until we find a matching position or reach 0
        while j > 0 and pat[i] != pat[j]:
            comps += 1
            j = lps[j - 1]
        comps += 1
        if pat[i] == pat[j]:
            j += 1
            lps[i] = j  # a longer prefix-suffix was found
    return lps, comps


def kmp_search_row(text_row, pat, lps):
    """
    Run KMP on a single row (1-D search).

    Parameters
    ----------
    text_row : list
        The text to search in.
    pat : list
        The pattern to look for.
    lps : list[int]
        Precomputed LPS array for pat.

    Returns
    -------
    res : list[int]
        Starting indices where pat occurs in text_row.
    comps : int
        Number of element comparisons made.
    """
    if not pat:
        return [], 0
    res = []
    j = 0       # number of characters matched so far
    comps = 0
    for i in range(len(text_row)):
        # Mismatch: fall back using failure function
        while j > 0 and text_row[i] != pat[j]:
            comps += 1
            j = lps[j - 1]
        comps += 1
        if text_row[i] == pat[j]:
            j += 1
            if j == len(pat):           # full match
                res.append(i - j + 1)
                j = lps[j - 1]          # continue searching for overlapping matches
    return res, comps


# ---------------------------------------------------------------------------
# Aho-Corasick automaton (object-based, for study/extension)
# ---------------------------------------------------------------------------

class ACNode:
    """Single node of an Aho-Corasick trie."""
    __slots__ = ("next", "fail", "out")

    def __init__(self):
        self.next = {}   # symbol -> node index
        self.fail = 0    # failure (suffix) link
        self.out = []    # pattern IDs that end at this node


def ac_build(patterns):
    """
    Build an Aho-Corasick automaton from a list of patterns.

    Parameters
    ----------
    patterns : list[list]
        Each element is a sequence (list) of symbols.

    Returns
    -------
    nodes : list[ACNode]
        The automaton as a flat list of nodes (index 0 = root).
    """
    nodes = [ACNode()]

    # Phase 1: insert all patterns into the trie
    for pid, pat in enumerate(patterns):
        s = 0
        for x in pat:
            if x not in nodes[s].next:
                nodes[s].next[x] = len(nodes)
                nodes.append(ACNode())
            s = nodes[s].next[x]
        nodes[s].out.append(pid)

    # Phase 2: BFS to set failure links
    q = deque()
    for x, nxt in nodes[0].next.items():
        nodes[nxt].fail = 0   # depth-1 nodes fail to root
        q.append(nxt)

    while q:
        v = q.popleft()
        for x, nxt in nodes[v].next.items():
            q.append(nxt)
            # Follow failure links of parent until we can extend with x
            f = nodes[v].fail
            while f and x not in nodes[f].next:
                f = nodes[f].fail
            nodes[nxt].fail = nodes[f].next[x] if x in nodes[f].next else 0
            # Inherit outputs from the suffix link (dictionary link)
            nodes[nxt].out.extend(nodes[nodes[nxt].fail].out)

    return nodes


def ac_search_stream(nodes, stream):
    """
    Search a stream with a prebuilt AC automaton.

    Yields
    ------
    (position, pattern_id) : tuple
        position is the index of the last symbol of the match in stream.
    """
    s = 0
    for i, x in enumerate(stream):
        while s and x not in nodes[s].next:
            s = nodes[s].fail
        s = nodes[s].next.get(x, 0)
        if nodes[s].out:
            for pid in nodes[s].out:
                yield i, pid
