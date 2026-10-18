"""Bipartite b-matching with lower bounds, by max flow (Dinic).

Left and right vertices are row classes (identical rows collapsed) with a
multiplicity and a mandatory count. An edge means "a row of this left class may be
paired with a row of this right class". The question answered is whether a pairing
exists in which every class pairs at least its mandatory count and at most its
multiplicity. Unbounded enumeration is never used (scorer spec v2, section 6).
"""

from __future__ import annotations

from collections import deque


class Dinic:
    def __init__(self, n):
        self.n = n
        self.head = [-1] * n
        self.to = []
        self.cap = []
        self.nxt = []

    def add(self, u, v, c):
        self.to.append(v); self.cap.append(c); self.nxt.append(self.head[u]); self.head[u] = len(self.to) - 1
        self.to.append(u); self.cap.append(0); self.nxt.append(self.head[v]); self.head[v] = len(self.to) - 1
        return len(self.to) - 2

    def maxflow(self, s, t, limit=None):
        flow = 0
        INF = float("inf")
        while True:
            level = [-1] * self.n
            level[s] = 0
            q = deque([s])
            while q:
                u = q.popleft()
                e = self.head[u]
                while e != -1:
                    if self.cap[e] > 0 and level[self.to[e]] < 0:
                        level[self.to[e]] = level[u] + 1
                        q.append(self.to[e])
                    e = self.nxt[e]
            if level[t] < 0:
                return flow
            it = list(self.head)

            def dfs(u, f):
                # Layered paths in these networks are short (source, class, class, sink
                # plus the circulation edges), so recursion depth stays small.
                if u == t:
                    return f
                while it[u] != -1:
                    e = it[u]
                    v = self.to[e]
                    if self.cap[e] > 0 and level[v] == level[u] + 1:
                        d = dfs(v, min(f, self.cap[e]))
                        if d > 0:
                            self.cap[e] -= d
                            self.cap[e ^ 1] += d
                            return d
                    it[u] = self.nxt[e]
                return 0

            while True:
                f = dfs(s, INF)
                if f == 0:
                    break
                flow += f
                if limit is not None and flow >= limit:
                    return flow


def feasible(left, right, edges):
    """left/right: lists of (mandatory, multiplicity); edges: iterable of (i, j).

    True when a pairing exists that gives each class between `mandatory` and
    `multiplicity` partners. Lower bounds are handled by the standard circulation
    reduction.
    """
    nl, nr = len(left), len(right)
    S, T = nl + nr, nl + nr + 1
    SS, TT = nl + nr + 2, nl + nr + 3
    g = Dinic(nl + nr + 4)
    excess = [0] * (nl + nr + 4)
    big = sum(m for _, m in left) + sum(m for _, m in right) + 1
    for i, (lo, hi) in enumerate(left):
        if lo > hi:
            return False
        if hi - lo:
            g.add(S, i, hi - lo)
        excess[S] -= lo
        excess[i] += lo
    for j, (lo, hi) in enumerate(right):
        if lo > hi:
            return False
        if hi - lo:
            g.add(nl + j, T, hi - lo)
        excess[nl + j] -= lo
        excess[T] += lo
    for i, j in edges:
        g.add(i, nl + j, big)
    g.add(T, S, big)
    need = 0
    for v, x in enumerate(excess):
        if x > 0:
            g.add(SS, v, x)
            need += x
        elif x < 0:
            g.add(v, TT, -x)
    return g.maxflow(SS, TT) == need
