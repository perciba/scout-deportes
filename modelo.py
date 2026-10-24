"""
Modelo algorítmico transparente estilo Windrawwin (educativo).
No predice el futuro con certeza: combina fuerza ofensiva/defensiva,
forma reciente y factor local en un Poisson de goles.
"""
from __future__ import annotations

import math
from typing import List, Tuple


def _pois_pmf(lmb: float, k: int) -> float:
    lmb = max(0.05, float(lmb))
    return math.exp(-lmb) * (lmb ** k) / math.factorial(k)


def form_factor(form: str) -> float:
    if not form:
        return 1.0
    pts = sum(1.0 if c == "W" else 0.5 if c == "D" else 0.0 for c in form[-5:])
    max_pts = max(len(form[-5:]), 1) * 1.0
    ratio = pts / max_pts
    return 0.85 + 0.30 * ratio


def expected_goals(
    gf_pg_home: float,
    gc_pg_home: float,
    gf_pg_away: float,
    gc_pg_away: float,
    form_home: str = "",
    form_away: str = "",
    home_boost: float = 1.12,
) -> Tuple[float, float]:
    att_h = max(0.3, gf_pg_home)
    def_h = max(0.3, gc_pg_home)
    att_a = max(0.3, gf_pg_away)
    def_a = max(0.3, gc_pg_away)
    la = ((att_h + def_a) / 2.0) * home_boost * form_factor(form_home)
    lb = ((att_a + def_h) / 2.0) * form_factor(form_away)
    return max(0.15, la), max(0.15, lb)


def score_matrix(la: float, lb: float, max_goals: int = 7):
    p_h = p_d = p_a = 0.0
    scores = []
    for i in range(0, max_goals + 1):
        for j in range(0, max_goals + 1):
            p = _pois_pmf(la, i) * _pois_pmf(lb, j)
            scores.append((i, j, p))
            if i > j:
                p_h += p
            elif i == j:
                p_d += p
            else:
                p_a += p
    total = p_h + p_d + p_a
    if total <= 0:
        return 1 / 3, 1 / 3, 1 / 3, []
    scores.sort(key=lambda x: -x[2])
    return p_h / total, p_d / total, p_a / total, scores[:5]


def implied_odds(p: float) -> float:
    if p <= 0.001:
        return 99.0
    return round(1.0 / p, 2)


def analizar_partido(local: dict, visitante: dict) -> dict:
    gf_h = local["gf_pg"]
    gc_h = local["gc_pg"]
    if local.get("home", {}).get("pj", 0) >= 3:
        hh = local["home"]
        gf_h = hh["gf"] / hh["pj"]
        gc_h = hh["gc"] / hh["pj"]

    gf_a = visitante["gf_pg"]
    gc_a = visitante["gc_pg"]
    if visitante.get("away", {}).get("pj", 0) >= 3:
        aa = visitante["away"]
        gf_a = aa["gf"] / aa["pj"]
        gc_a = aa["gc"] / aa["pj"]

    la, lb = expected_goals(
        gf_h, gc_h, gf_a, gc_a,
        form_home=local.get("form") or "",
        form_away=visitante.get("form") or "",
    )
    p1, px, p2, top = score_matrix(la, lb)

    p_over = 0.0
    for i in range(0, 8):
        for j in range(0, 8):
            if i + j >= 3:
                p_over += _pois_pmf(la, i) * _pois_pmf(lb, j)
    p_under = max(0.0, 1.0 - p_over)

    favorito = "LOCAL" if p1 >= px and p1 >= p2 else ("EMPATE" if px >= p2 else "VISITANTE")
    conf = max(p1, px, p2)

    return {
        "modelo": "Poisson · ataque/defensa + forma + factor local",
        "lambda_local": round(la, 2),
        "lambda_visitante": round(lb, 2),
        "prob_1": round(p1 * 100, 1),
        "prob_x": round(px * 100, 1),
        "prob_2": round(p2 * 100, 1),
        "cuota_impl_1": implied_odds(p1),
        "cuota_impl_x": implied_odds(px),
        "cuota_impl_2": implied_odds(p2),
        "favorito": favorito,
        "confianza_pct": round(conf * 100, 1),
        "over25_pct": round(min(p_over, 1.0) * 100, 1),
        "under25_pct": round(max(p_under, 0.0) * 100, 1),
        "marcadores_probables": [
            {"marcador": f"{i}-{j}", "prob_pct": round(p * 100, 1)}
            for i, j, p in top
        ],
        "aviso": (
            "Modelo estadístico educativo. No determina el ganador real. "
            "No es consejo de apuestas."
        ),
    }
