"""Núcleo de cálculo de concreto armado — ABNT NBR 6118:2023 (somente biblioteca padrão).

Unidades internas: N e mm (MPa = N/mm²). As funções públicas recebem/devolvem
as unidades indicadas nos docstrings (cm, kN, kN·m, cm²).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

GAMMA_C = 1.4
GAMMA_S = 1.15
ES = 210_000.0  # MPa

ACOS = {"CA-25": 250.0, "CA-50": 500.0, "CA-60": 600.0}

# Bitolas comerciais (mm) e massa linear (kg/m) — NBR 7480
BITOLAS = {5.0: 0.154, 6.3: 0.245, 8.0: 0.395, 10.0: 0.617, 12.5: 0.963,
           16.0: 1.578, 20.0: 2.466, 25.0: 3.853, 32.0: 6.313}

# Taxa mínima de armadura de flexão (%), seção retangular, CA-50 — NBR 6118 Tabela 17.3
RHO_MIN = {20: 0.150, 25: 0.150, 30: 0.150, 35: 0.164, 40: 0.179, 45: 0.194, 50: 0.208,
           55: 0.211, 60: 0.219, 65: 0.226, 70: 0.233, 75: 0.239, 80: 0.245, 85: 0.251, 90: 0.256}

# Cobrimento nominal (mm) por classe de agressividade — NBR 6118 Tabela 7.2 (Δc = 10 mm)
COBRIMENTO = {"I": {"laje": 20, "viga": 25, "pilar": 25},
              "II": {"laje": 25, "viga": 30, "pilar": 30},
              "III": {"laje": 35, "viga": 40, "pilar": 40},
              "IV": {"laje": 45, "viga": 50, "pilar": 50}}


# Classe mínima de concreto armado por CAA — NBR 6118 Tabela 7.1
FCK_MIN_CAA = {"I": 20, "II": 25, "III": 30, "IV": 40}


def caa_do_projeto(caa: str | None, contexto: str | None = "projeto-contexto.json") -> tuple[str, str]:
    """CAA informada > ficha do projeto (skill contexto-do-projeto) > padrão II (urbano)."""
    if caa:
        return caa, "informada"
    f = Path(contexto) if contexto else None
    if f and f.is_file():
        c = (json.loads(f.read_text(encoding="utf-8")).get("caa") or {})
        if c.get("classe") in FCK_MIN_CAA:
            return c["classe"], f"ficha do projeto (ambiente {c.get('ambiente')})"
    return "II", "padrão — sem ficha do projeto; confirme o ambiente da obra"


def checar_durabilidade(fck: float, caa: str, mem: "Memoria") -> None:
    mem.add("Durabilidade (Tab. 7.1)", f"CAA {caa} exige concreto ≥ C{FCK_MIN_CAA[caa]}")
    if fck < FCK_MIN_CAA[caa]:
        mem.alerta(f"fck = {fck:g} MPa abaixo do mínimo C{FCK_MIN_CAA[caa]} para CAA {caa} (NBR 6118, Tab. 7.1).")


# ------------------------------------------------------------------ materiais

@dataclass
class Concreto:
    fck: float  # MPa
    agregado: str = "granito"  # basalto, granito, calcario, arenito

    def __post_init__(self) -> None:
        if not 20 <= self.fck <= 90:
            raise ValueError("fck deve estar entre 20 e 90 MPa (NBR 6118)")

    @property
    def fcd(self) -> float:
        return self.fck / GAMMA_C

    @property
    def alpha_c(self) -> float:
        return 0.85 if self.fck <= 50 else 0.85 * (1 - (self.fck - 50) / 200)

    @property
    def lam(self) -> float:
        return 0.8 if self.fck <= 50 else 0.8 - (self.fck - 50) / 400

    @property
    def eps_c2(self) -> float:
        return 0.002 if self.fck <= 50 else 0.002 + 0.000085 * (self.fck - 50) ** 0.53

    @property
    def eps_cu(self) -> float:
        return 0.0035 if self.fck <= 50 else 0.0026 + 0.035 * ((90 - self.fck) / 100) ** 4

    @property
    def n_parabola(self) -> float:
        return 2.0 if self.fck <= 50 else 1.4 + 23.4 * ((90 - self.fck) / 100) ** 4

    @property
    def xd_lim(self) -> float:
        """Limite de ductilidade x/d (item 14.6.4.3)."""
        return 0.45 if self.fck <= 50 else 0.35

    @property
    def fctm(self) -> float:
        if self.fck <= 50:
            return 0.3 * self.fck ** (2 / 3)
        return 2.12 * math.log(1 + 0.11 * self.fck)

    @property
    def fctk_inf(self) -> float:
        return 0.7 * self.fctm

    @property
    def fctd(self) -> float:
        return self.fctk_inf / GAMMA_C

    @property
    def Eci(self) -> float:
        alpha_e = {"basalto": 1.2, "diabasio": 1.2, "granito": 1.0, "gnaisse": 1.0,
                   "calcario": 0.9, "arenito": 0.7}[self.agregado]
        if self.fck <= 50:
            return alpha_e * 5600 * math.sqrt(self.fck)
        return 21_500 * alpha_e * (self.fck / 10 + 1.25) ** (1 / 3)

    @property
    def Ecs(self) -> float:
        alpha_i = min(1.0, 0.8 + 0.2 * self.fck / 80)
        return alpha_i * self.Eci

    def sigma(self, eps: float) -> float:
        """Diagrama parábola-retângulo (compressão positiva), MPa."""
        if eps <= 0:
            return 0.0
        f = self.alpha_c * self.fcd
        if eps >= self.eps_c2:
            return f
        return f * (1 - (1 - eps / self.eps_c2) ** self.n_parabola)


@dataclass
class Aco:
    tipo: str = "CA-50"

    @property
    def fyk(self) -> float:
        return ACOS[self.tipo]

    @property
    def fyd(self) -> float:
        return self.fyk / GAMMA_S

    @property
    def eps_yd(self) -> float:
        return self.fyd / ES

    def sigma(self, eps: float) -> float:
        return max(-self.fyd, min(self.fyd, ES * eps))


def rho_min(fck: float) -> float:
    """Taxa mínima (fração) para seção retangular — interpola a Tabela 17.3."""
    keys = sorted(RHO_MIN)
    fck = min(max(fck, keys[0]), keys[-1])
    for a, b in zip(keys, keys[1:]):
        if a <= fck <= b:
            return (RHO_MIN[a] + (RHO_MIN[b] - RHO_MIN[a]) * (fck - a) / (b - a)) / 100
    return RHO_MIN[keys[-1]] / 100


# ------------------------------------------------------------------ memória de cálculo

@dataclass
class Memoria:
    titulo: str
    passos: list[tuple[str, str]] = field(default_factory=list)  # (descrição, expressão = valor)
    alertas: list[str] = field(default_factory=list)

    def add(self, desc: str, expr: str) -> None:
        self.passos.append((desc, expr))

    def alerta(self, msg: str) -> None:
        self.alertas.append(msg)

    def markdown(self) -> str:
        out = [f"### {self.titulo}", "", "| Passo | Cálculo |", "|---|---|"]
        out += [f"| {d} | {e} |" for d, e in self.passos]
        if self.alertas:
            out += ["", "**Alertas:**"] + [f"- {a}" for a in self.alertas]
        return "\n".join(out)

    def dict(self) -> dict:
        return {"titulo": self.titulo, "passos": [{"descricao": d, "calculo": e} for d, e in self.passos],
                "alertas": self.alertas}


def fmt(v: float, nd: int = 2) -> str:
    return f"{v:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------------ flexão simples

def flexao_simples(Md_kNm: float, b_cm: float, h_cm: float, d_cm: float, conc: Concreto, aco: Aco,
                   d2_cm: float | None = None, mem: Memoria | None = None, laje: bool = False) -> dict:
    """Armadura longitudinal de seção retangular à flexão simples (bloco retangular, item 17.2.2).

    Retorna As (tração) e As2 (compressão, 0 se armadura simples), em cm².
    """
    mem = mem or Memoria("Flexão simples")
    Md = abs(Md_kNm) * 1e6
    b, h, d = b_cm * 10, h_cm * 10, d_cm * 10
    d2 = (d2_cm * 10) if d2_cm else (h - d)
    fcd, fyd, ac, lam = conc.fcd, aco.fyd, conc.alpha_c, conc.lam
    mem.add("Resistências de cálculo", f"fcd = {fmt(conc.fck,0)}/1,4 = {fmt(fcd)} MPa; fyd = {fmt(aco.fyk,0)}/1,15 = {fmt(fyd)} MPa")
    mem.add("Parâmetros do bloco", f"αc = {fmt(ac,3)}; λ = {fmt(lam,3)}; (x/d)lim = {fmt(conc.xd_lim)}")

    xlim = conc.xd_lim * d
    Mlim = ac * fcd * b * lam * xlim * (d - lam * xlim / 2)
    disc = 1 - 2 * Md / (ac * fcd * b * d * d)
    As2 = 0.0
    if disc >= 0 and (x := d / lam * (1 - math.sqrt(disc))) <= xlim:
        As = Md / (fyd * (d - lam * x / 2))
        mem.add("Linha neutra", f"x = d/λ·[1 − √(1 − 2Md/(αc·fcd·b·d²))] = {fmt(x/10)} cm (x/d = {fmt(x/d,3)})")
        mem.add("Armadura de tração", f"As = Md / [fyd·(d − λx/2)] = {fmt(As/100)} cm²")
    else:
        x = xlim
        M2 = Md - Mlim
        eps2 = conc.eps_cu * (xlim - d2) / xlim
        sig2 = min(ES * eps2, fyd)
        As2 = M2 / (sig2 * (d - d2))
        As = Mlim / (fyd * (d - lam * xlim / 2)) + M2 / (fyd * (d - d2))
        mem.add("Armadura dupla", f"x/d > limite ⇒ x = xlim = {fmt(xlim/10)} cm; Mlim = {fmt(Mlim/1e6)} kN·m")
        mem.add("Armadura de compressão", f"σs' = {fmt(sig2)} MPa; As' = (Md − Mlim)/[σs'(d − d')] = {fmt(As2/100)} cm²")
        mem.add("Armadura de tração", f"As = {fmt(As/100)} cm²")
        mem.alerta("Seção com armadura dupla: considere aumentar a altura da seção.")

    Ac = b * h
    rmin = rho_min(conc.fck)
    As_min = rmin * Ac
    mem.add("Armadura mínima (Tab. 17.3)", f"As,mín = {fmt(rmin*100,3)}% · {fmt(Ac/100,0)} cm² = {fmt(As_min/100)} cm²")
    As_ef = max(As, As_min)
    if As + As2 > 0.04 * Ac:
        mem.alerta("As + As' excede 4% de Ac (item 17.3.5.2.4): redimensione a seção.")
    return {"x_cm": x / 10, "x_d": x / d, "As_cm2": As_ef / 100, "As_calc_cm2": As / 100,
            "As2_cm2": As2 / 100, "As_min_cm2": As_min / 100, "dominio_ok": x / d <= conc.xd_lim + 1e-9}


# ------------------------------------------------------------------ cisalhamento (Modelo I)

def cisalhamento_modelo1(Vsd_kN: float, bw_cm: float, d_cm: float, conc: Concreto, aco: Aco,
                         mem: Memoria | None = None) -> dict:
    """Estribos verticais (α = 90°), Modelo de cálculo I — item 17.4.2.2. Retorna Asw/s em cm²/m."""
    mem = mem or Memoria("Força cortante — Modelo I")
    V = abs(Vsd_kN) * 1e3
    bw, d = bw_cm * 10, d_cm * 10
    av2 = 1 - conc.fck / 250
    VRd2 = 0.27 * av2 * conc.fcd * bw * d
    mem.add("Biela comprimida", f"VRd2 = 0,27·αv2·fcd·bw·d = 0,27·{fmt(av2,3)}·{fmt(conc.fcd)}·{fmt(bw,0)}·{fmt(d,0)} = {fmt(VRd2/1e3)} kN")
    Vc = 0.6 * conc.fctd * bw * d
    mem.add("Parcela do concreto", f"Vc = 0,6·fctd·bw·d = 0,6·{fmt(conc.fctd,3)}·{fmt(bw,0)}·{fmt(d,0)} = {fmt(Vc/1e3)} kN")
    fywd = min(aco.fyd, 435.0)
    Vsw = max(V - Vc, 0.0)
    asw = Vsw / (0.9 * d * fywd)  # mm²/mm
    rho_sw_min = 0.2 * conc.fctm / aco.fyk
    asw_min = rho_sw_min * bw
    mem.add("Armadura calculada", f"Asw/s = (VSd − Vc)/(0,9·d·fywd) = {fmt(asw*10)} cm²/m")
    mem.add("Armadura mínima", f"ρsw,mín = 0,2·fct,m/fywk = {fmt(rho_sw_min*100,4)}% ⇒ {fmt(asw_min*10)} cm²/m")
    ok = V <= VRd2
    if not ok:
        mem.alerta(f"VSd = {fmt(V/1e3)} kN > VRd2 = {fmt(VRd2/1e3)} kN: esmagamento da biela — aumente bw ou fck.")
    # espaçamento máximo (item 18.3.3.2)
    smax = min(0.6 * d, 300) if V <= 0.67 * VRd2 else min(0.3 * d, 200)
    mem.add("Espaçamento máximo", f"smáx = {fmt(smax/10,1)} cm")
    return {"VRd2_kN": VRd2 / 1e3, "Vc_kN": Vc / 1e3, "Asw_s_cm2_m": max(asw, asw_min) * 10,
            "Asw_s_min_cm2_m": asw_min * 10, "s_max_cm": smax / 10, "biela_ok": ok}


def escolher_estribo(asw_s_cm2_m: float, s_max_cm: float, ramos: int = 2) -> dict:
    for phi in (5.0, 6.3, 8.0, 10.0):
        area = ramos * math.pi * phi ** 2 / 4 / 100  # cm²
        s = min(area / asw_s_cm2_m * 100, s_max_cm)  # cm
        s = math.floor(s * 2) / 2  # arredonda para baixo a cada 0,5 cm
        if s >= 7.0:
            return {"phi_mm": phi, "ramos": ramos, "s_cm": s, "texto": f"φ{_phi(phi)} c/ {fmt(s,1)} cm ({ramos} ramos)"}
    return {"phi_mm": None, "texto": "estribo maior que φ10 — rever seção"}


# ------------------------------------------------------------------ escolha de barras

def _phi(p: float) -> str:
    return f"{p:g}".replace(".", ",")


def escolher_barras(As_cm2: float, b_cm: float, cobrimento_mm: float, phi_t_mm: float = 5.0,
                    d_agr_mm: float = 19.0, camadas_max: int = 2) -> list[dict]:
    """Combinações viáveis de barras (uma bitola) que cabem na largura — item 18.3.2.2."""
    opcoes = []
    for phi in (8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0):
        a1 = math.pi * phi ** 2 / 4 / 100
        n = max(2, math.ceil(As_cm2 / a1 - 1e-9))
        ah = max(20.0, phi, 1.2 * d_agr_mm)
        livre = b_cm * 10 - 2 * (cobrimento_mm + phi_t_mm)
        por_camada = max(1, int((livre + ah) // (phi + ah)))
        camadas = math.ceil(n / por_camada)
        if camadas <= camadas_max and por_camada >= 2:
            opcoes.append({"n": n, "phi_mm": phi, "As_ef_cm2": round(n * a1, 2), "camadas": camadas,
                           "texto": f"{n} φ{_phi(phi)} ({fmt(n*a1)} cm²)" + (f" em {camadas} camadas" if camadas > 1 else "")})
    opcoes.sort(key=lambda o: (o["camadas"], o["As_ef_cm2"]))
    return opcoes[:3]


def barras_por_metro(As_cm2_m: float, h_cm: float) -> dict:
    """Armadura de laje: bitola e espaçamento (s ≤ 2h e ≤ 20 cm — item 20.1)."""
    smax = min(2 * h_cm, 20.0)
    for phi in (5.0, 6.3, 8.0, 10.0, 12.5, 16.0):
        a1 = math.pi * phi ** 2 / 4 / 100
        s = math.floor(min(a1 / As_cm2_m * 100, smax) * 2) / 2
        if s >= 8.0 and phi <= h_cm * 10 / 8:
            return {"phi_mm": phi, "s_cm": s, "As_ef_cm2_m": round(a1 * 100 / s, 2), "texto": f"φ{_phi(phi)} c/ {fmt(s,1)} cm"}
    return {"phi_mm": None, "texto": "armadura muito alta para a espessura — aumentar h"}


# ------------------------------------------------------------------ seção retangular: flexo-compressão

@dataclass
class Camada:
    y_mm: float      # distância à borda comprimida de referência (topo)
    frac: float      # fração da armadura total nesta camada


def esforcos_secao(x: float, b: float, h: float, camadas: list[Camada], As: float,
                   conc: Concreto, aco: Aco, nfib: int = 80) -> tuple[float, float]:
    """(N, M) resistentes (N, N·mm) para linha neutra x (mm, a partir do topo), domínios 2–5.

    Compressão positiva; M em relação ao centro geométrico, positivo comprimindo o topo.
    """
    d = max(c.y_mm for c in camadas)
    ecu, ec2 = conc.eps_cu, conc.eps_c2
    x23 = ecu / (ecu + 0.010) * d
    if x <= x23:                               # domínio 2: pivô A (εs = 10‰ na camada mais tracionada)
        k = 0.010 / (d - x)
    elif x <= h:                               # domínios 3, 4, 4a: pivô B (εcu no topo)
        k = ecu / x
    else:                                      # domínio 5: pivô C
        yc = (1 - ec2 / ecu) * h
        k = ec2 / (x - yc)

    def eps(y: float) -> float:
        return k * (x - y)

    N = M = 0.0
    dy = h / nfib
    for i in range(nfib):
        y = (i + 0.5) * dy
        f = conc.sigma(eps(y)) * b * dy
        N += f
        M += f * (h / 2 - y)
    for c in camadas:
        e = eps(c.y_mm)
        a = As * c.frac
        f = aco.sigma(e) * a - (conc.sigma(e) * a if e > 0 else 0.0)  # desconta concreto deslocado
        N += f
        M += f * (h / 2 - c.y_mm)
    return N, M


def momento_resistente(Nd: float, b: float, h: float, camadas: list[Camada], As: float,
                       conc: Concreto, aco: Aco) -> float | None:
    """MRd (N·mm) para o esforço normal Nd (N). None se Nd não for resistido."""
    lo, hi = 1e-3, 1e6 * h
    n_lo, _ = esforcos_secao(lo, b, h, camadas, As, conc, aco)
    n_hi, _ = esforcos_secao(hi, b, h, camadas, As, conc, aco)
    if not n_lo <= Nd <= n_hi:
        return None
    for _ in range(80):
        mid = math.sqrt(lo * hi) if hi / lo > 4 else (lo + hi) / 2
        n_mid, _ = esforcos_secao(mid, b, h, camadas, As, conc, aco)
        if n_mid < Nd:
            lo = mid
        else:
            hi = mid
    return abs(esforcos_secao((lo + hi) / 2, b, h, camadas, As, conc, aco)[1])


def camadas_retangulo(h: float, d2: float, barras_por_face: int, faces: int) -> list[Camada]:
    """Distribuição simétrica: 2 faces (só nas faces perpendiculares à flexão) ou 4 faces."""
    if faces == 2 or barras_por_face <= 2:
        return [Camada(d2, 0.5), Camada(h - d2, 0.5)]
    n = barras_por_face
    total = 4 * n - 4
    ys = [d2 + i * (h - 2 * d2) / (n - 1) for i in range(n)]
    out = [Camada(ys[0], n / total), Camada(ys[-1], n / total)]
    out += [Camada(y, 2 / total) for y in ys[1:-1]]
    return out
