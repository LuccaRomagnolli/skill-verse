"""Placa retangular de Kirchhoff sob carga uniforme — diferenças finitas (somente stdlib).

Bordas: 'A' (simplesmente apoiada) ou 'E' (engastada). Bordas livres não são suportadas
(balanços: use laje armada em uma direção).

Ordem das bordas em `bordas`: (x=0, x=lx, y=0, y=ly)  — esquerda, direita, inferior, superior.
Resultados adimensionais, no formato das tabelas de Czerny/Bares:
  w = cw · q·lx⁴/D      m = cm · q·lx²       (lx = vão na direção x)
"""
from __future__ import annotations

import math


def _solve_banded(n: int, bw: int, rows: dict[int, dict[int, float]], rhs: list[float]) -> list[float]:
    """Eliminação de Gauss em matriz de banda (SPD, sem pivotamento)."""
    A = [dict(rows[i]) for i in range(n)]
    b = rhs[:]
    for k in range(n):
        piv = A[k][k]
        rk = A[k]
        top = min(n, k + bw + 1)
        for i in range(k + 1, top):
            ri = A[i]
            f = ri.get(k)
            if not f:
                continue
            f /= piv
            for j, v in rk.items():
                if j >= k:
                    ri[j] = ri.get(j, 0.0) - f * v
            b[i] -= f * b[k]
    x = [0.0] * n
    for k in range(n - 1, -1, -1):
        s = b[k] - sum(v * x[j] for j, v in A[k].items() if j > k)
        x[k] = s / A[k][k]
    return x


def resolver(lx: float, ly: float, bordas: str, nu: float = 0.2, div: int = 24) -> dict:
    """Retorna coeficientes adimensionais de flecha e momentos.

    div = número de divisões no menor vão (precisão ~1% com 24).
    """
    bordas = bordas.upper()
    if len(bordas) != 4 or set(bordas) - {"A", "E"}:
        raise ValueError("bordas deve ter 4 letras A/E: esquerda, direita, inferior, superior")
    lmin = min(lx, ly)
    nx = max(4, round(div * lx / lmin))
    ny = max(4, round(div * ly / lmin))
    hx, hy = lx / nx, ly / ny
    mx_, my_ = nx - 1, ny - 1  # nós internos
    N = mx_ * my_

    def idx(i: int, j: int) -> int:
        return (j - 1) * mx_ + (i - 1)

    # nó fantasma: apoio → −w(vizinho); engaste → +w(vizinho)
    sx0 = 1 if bordas[0] == "E" else -1
    sx1 = 1 if bordas[1] == "E" else -1
    sy0 = 1 if bordas[2] == "E" else -1
    sy1 = 1 if bordas[3] == "E" else -1

    def ref(i: int, j: int) -> tuple[int, int, float] | None:
        """Mapeia (i,j) possivelmente fantasma para nó interno com sinal; None se w=0."""
        s = 1.0
        if i == -1:
            i, s = 1, s * sx0
        elif i == nx + 1:
            i, s = nx - 1, s * sx1
        if j == -1:
            j, s = 1, s * sy0
        elif j == ny + 1:
            j, s = ny - 1, s * sy1
        if i <= 0 or i >= nx or j <= 0 or j >= ny:
            return None
        return i, j, s

    ax, ay, axy = 1 / hx ** 4, 1 / hy ** 4, 2 / (hx ** 2 * hy ** 2)
    stencil: list[tuple[int, int, float]] = [
        (-2, 0, ax), (-1, 0, -4 * ax), (0, 0, 6 * ax), (1, 0, -4 * ax), (2, 0, ax),
        (0, -2, ay), (0, -1, -4 * ay), (0, 0, 6 * ay), (0, 1, -4 * ay), (0, 2, ay),
        (1, 1, axy), (-1, 1, axy), (1, -1, axy), (-1, -1, axy),
        (0, 1, -2 * axy), (0, -1, -2 * axy), (1, 0, -2 * axy), (-1, 0, -2 * axy), (0, 0, 4 * axy),
    ]
    rows: dict[int, dict[int, float]] = {}
    for j in range(1, ny):
        for i in range(1, nx):
            r: dict[int, float] = {}
            for di, dj, c in stencil:
                m = ref(i + di, j + dj)
                if m is None:
                    continue
                k = idx(m[0], m[1])
                r[k] = r.get(k, 0.0) + c * m[2]
            rows[idx(i, j)] = r
    # D·∇⁴w = q  →  com q = 1, D = 1: w em unidades de q/D
    w = _solve_banded(N, 2 * mx_, rows, [1.0] * N)

    def W(i: int, j: int) -> float:
        m = ref(i, j)
        return 0.0 if m is None else m[2] * w[idx(m[0], m[1])]

    def wxx(i, j): return (W(i - 1, j) - 2 * W(i, j) + W(i + 1, j)) / hx ** 2
    def wyy(i, j): return (W(i, j - 1) - 2 * W(i, j) + W(i, j + 1)) / hy ** 2

    mx_pos = my_pos = wmax = 0.0
    for j in range(1, ny):
        for i in range(1, nx):
            a, b_ = wxx(i, j), wyy(i, j)
            mx_pos = max(mx_pos, -(a + nu * b_))
            my_pos = max(my_pos, -(b_ + nu * a))
            wmax = max(wmax, W(i, j))
    # momentos de engaste (máximo ao longo da borda): M = −D·w_nn
    neg = {}
    nomes = ("esquerda", "direita", "inferior", "superior")
    for k, nome in enumerate(nomes):
        if bordas[k] != "E":
            continue
        if k < 2:
            i = 0 if k == 0 else nx
            neg[nome] = min(-wxx(i, j) for j in range(1, ny))
        else:
            j = 0 if k == 2 else ny
            neg[nome] = min(-wyy(i, j) for i in range(1, nx))
    l4, l2 = lx ** 4, lx ** 2
    return {
        "cw": wmax / l4, "cmx": mx_pos / l2, "cmy": my_pos / l2,
        "cneg": {k: v / l2 for k, v in neg.items()},
        "malha": [nx, ny], "nu": nu, "bordas": bordas,
    }


def resolver_refinado(lx: float, ly: float, bordas: str, nu: float = 0.2) -> dict:
    """Extrapolação de Richardson (h e h/2·…): erro O(h²) → praticamente exato."""
    a = resolver(lx, ly, bordas, nu, div=16)
    b = resolver(lx, ly, bordas, nu, div=24)
    r = (24 / 16) ** 2

    def ex(u, v):
        return v + (v - u) / (r - 1)
    out = dict(b)
    for k in ("cw", "cmx", "cmy"):
        out[k] = ex(a[k], b[k])
    out["cneg"] = {k: ex(a["cneg"][k], b["cneg"][k]) for k in b["cneg"]}
    out["metodo"] = "diferenças finitas (Kirchhoff) com extrapolação de Richardson"
    return out


if __name__ == "__main__":  # verificação rápida contra Timoshenko (ν = 0,3)
    r = resolver_refinado(1, 1, "AAAA", nu=0.3)
    print("SS quadrada  cw=%.5f (0.00406) cmx=%.4f (0.0479)" % (r["cw"], r["cmx"]))
    r = resolver_refinado(1, 1, "EEEE", nu=0.3)
    print("Eng. quadrada cw=%.5f (0.00126) cmx=%.4f (0.0231) cneg=%.4f (-0.0513)" % (r["cw"], r["cmx"], r["cneg"]["esquerda"]))
    _ = math
