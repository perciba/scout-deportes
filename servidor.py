#!/usr/bin/env python3
"""Scout Deportes — datos reales + modelo Poisson + RSS.
Uso educativo. No es consejo de apuestas.
"""
import json
import urllib.request
from collections import defaultdict
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from modelo import analizar_partido
from rss_news import fetch_news, news_for_teams

DIR = Path(__file__).resolve().parent
DATOS = DIR / "datos" / "ligas_reales.json"
PORT = 8780
SEASON = "2025-26"
LEAGUES = {
    "en.1": "Premier League",
    "es.1": "La Liga",
    "de.1": "Bundesliga",
    "it.1": "Serie A",
    "fr.1": "Ligue 1",
}
CACHE = None


def parse_ft(score):
    if score is None:
        return None
    if isinstance(score, dict) and "ft" in score:
        ft = score["ft"]
        if isinstance(ft, (list, tuple)) and len(ft) == 2:
            return int(ft[0]), int(ft[1])
    if isinstance(score, (list, tuple)) and len(score) == 2:
        return int(score[0]), int(score[1])
    return None


def build_league(code: str) -> dict:
    name = LEAGUES[code]
    url = f"https://raw.githubusercontent.com/openfootball/football.json/master/{SEASON}/{code}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "ScoutDeportes/1.1"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode())
    matches = d.get("matches") or []
    stats = defaultdict(lambda: {
        "pj": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "gc": 0,
        "form": [],
        "home": {"pj": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "gc": 0},
        "away": {"pj": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "gc": 0},
    })
    finished = []
    for m in matches:
        ft = parse_ft(m.get("score"))
        rec = {
            "round": m.get("round"), "date": m.get("date"),
            "team1": m.get("team1"), "team2": m.get("team2"),
            "score_ft": list(ft) if ft else None,
        }
        finished.append(rec)
        if not ft:
            continue
        g1, g2 = ft
        for team, gf, gc, home in [(m["team1"], g1, g2, True), (m["team2"], g2, g1, False)]:
            s = stats[team]
            s["pj"] += 1
            s["gf"] += gf
            s["gc"] += gc
            if gf > gc:
                s["w"] += 1
                res = "W"
            elif gf == gc:
                s["d"] += 1
                res = "D"
            else:
                s["l"] += 1
                res = "L"
            s["form"].append(res)
            side = s["home"] if home else s["away"]
            side["pj"] += 1
            side["gf"] += gf
            side["gc"] += gc
            if gf > gc:
                side["w"] += 1
            elif gf == gc:
                side["d"] += 1
            else:
                side["l"] += 1
    teams = {}
    for team, s in stats.items():
        pts = s["w"] * 3 + s["d"]
        gd = s["gf"] - s["gc"]
        teams[team] = {
            "nombre": team,
            "pj": s["pj"], "w": s["w"], "d": s["d"], "l": s["l"],
            "gf": s["gf"], "gc": s["gc"], "gd": gd, "pts": pts,
            "gf_pg": round(s["gf"] / s["pj"], 2) if s["pj"] else 0,
            "gc_pg": round(s["gc"] / s["pj"], 2) if s["pj"] else 0,
            "form": "".join(s["form"][-5:]),
            "home": s["home"], "away": s["away"],
        }
    table = sorted(teams.values(), key=lambda x: (x["pts"], x["gd"], x["gf"]), reverse=True)
    for i, t in enumerate(table, 1):
        teams[t["nombre"]]["pos"] = i
        t["pos"] = i
    return {
        "liga": name, "season": SEASON, "code": code,
        "fuente": f"openfootball · {SEASON}/{code}.json",
        "actualizado": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "partidos_jugados": sum(1 for m in finished if m["score_ft"]),
        "partidos_total": len(matches),
        "equipos": teams,
        "tabla": [{"pos": t["pos"], "nombre": t["nombre"], "pj": t["pj"], "pts": t["pts"],
                   "gf": t["gf"], "gc": t["gc"], "gd": t["gd"], "form": t["form"]} for t in table],
        "partidos": finished,
    }


def load_all(force=False):
    global CACHE
    if CACHE and not force:
        return CACHE
    data = {}
    for code in LEAGUES:
        try:
            data[code] = build_league(code)
            print(f"  OK {code}")
        except Exception as e:
            print(f"  FAIL {code}: {e}")
    if not data and DATOS.exists():
        data = json.loads(DATOS.read_text(encoding="utf-8"))
    CACHE = data
    if data:
        DATOS.parent.mkdir(parents=True, exist_ok=True)
        DATOS.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def h2h(partidos, t1, t2, limit=10):
    out = []
    for m in reversed(partidos):
        if not m.get("score_ft"):
            continue
        if {m["team1"], m["team2"]} == {t1, t2}:
            out.append(m)
            if len(out) >= limit:
                break
    return out


def comparar(liga_code, local, visitante):
    data = load_all()
    if liga_code not in data:
        return {"error": "Liga no disponible"}
    L = data[liga_code]
    eq = L["equipos"]
    if local not in eq or visitante not in eq:
        return {"error": "Equipo no encontrado", "equipos": sorted(eq.keys())}
    a, b = eq[local], eq[visitante]
    notes = []
    if a["gf_pg"] > b["gf_pg"] + 0.3:
        notes.append(f"{local} marca más goles por partido ({a['gf_pg']} vs {b['gf_pg']}).")
    if b["gf_pg"] > a["gf_pg"] + 0.3:
        notes.append(f"{visitante} marca más goles por partido ({b['gf_pg']} vs {a['gf_pg']}).")
    if a["gc_pg"] + 0.3 < b["gc_pg"]:
        notes.append(f"{local} encaja menos ({a['gc_pg']} vs {b['gc_pg']} GC/partido).")
    if b["gc_pg"] + 0.3 < a["gc_pg"]:
        notes.append(f"{visitante} encaja menos ({b['gc_pg']} vs {a['gc_pg']} GC/partido).")
    if a["home"]["pj"]:
        hw = a["home"]["w"] / a["home"]["pj"] * 100
        notes.append(f"{local} en casa: {a['home']['w']}W-{a['home']['d']}D-{a['home']['l']}L ({hw:.0f}% victorias).")
    if b["away"]["pj"]:
        aw = b["away"]["w"] / b["away"]["pj"] * 100
        notes.append(f"{visitante} fuera: {b['away']['w']}W-{b['away']['d']}D-{b['away']['l']}L ({aw:.0f}% victorias).")

    pred = analizar_partido(a, b)
    try:
        noticias = news_for_teams([local, visitante], limit=6)
    except Exception:
        noticias = []

    return {
        "liga": L["liga"], "season": L["season"], "fuente": L["fuente"],
        "actualizado": L.get("actualizado"),
        "local": a, "visitante": b,
        "h2h": h2h(L["partidos"], local, visitante),
        "notas": notes,
        "prediccion": pred,
        "noticias": noticias,
        "aviso": (
            "Datos reales (goles) + modelo Poisson educativo. "
            "RSS = noticias, no stats de corners/tiros. "
            "No es consejo de apuestas ni ganador garantizado."
        ),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(DIR / "static"), **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def _json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path == "/api/ligas":
            data = load_all()
            self._json(200, {"ligas": [
                {"code": c, "nombre": LEAGUES[c], "equipos": len(data[c]["equipos"]),
                 "partidos_jugados": data[c]["partidos_jugados"]} for c in data
            ], "fuente": "openfootball"})
            return
        if u.path == "/api/equipos":
            code = (qs.get("liga") or ["en.1"])[0]
            data = load_all()
            if code not in data:
                return self._json(404, {"error": "liga"})
            self._json(200, {"equipos": sorted(data[code]["equipos"].keys())})
            return
        if u.path == "/api/comparar":
            code = (qs.get("liga") or ["en.1"])[0]
            local = (qs.get("local") or [""])[0]
            vis = (qs.get("visitante") or [""])[0]
            return self._json(200, comparar(code, local, vis))
        if u.path == "/api/noticias":
            try:
                items = fetch_news(int((qs.get("n") or ["12"])[0]))
            except Exception as e:
                return self._json(502, {"error": str(e)})
            return self._json(200, {"noticias": items})
        if u.path == "/api/refresh":
            load_all(force=True)
            return self._json(200, {"ok": True})
        if u.path in ("/", "/index.html"):
            self.path = "/index.html"
            return super().do_GET()
        return super().do_GET()

    def log_message(self, fmt, *args):
        if "/api/" in (fmt % args):
            print(" ", fmt % args)


def main():
    print("=" * 56)
    print("  SCOUT · reales + Poisson + RSS")
    print("=" * 56)
    load_all(force=True)
    print(f"  http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
