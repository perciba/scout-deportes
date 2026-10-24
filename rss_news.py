"""RSS de noticias de fútbol — contexto, no stats de corners/tiros."""
from __future__ import annotations

import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict

UA = "ScoutDeportes/1.1 (RSS)"
FEEDS = [
    ("BBC Football", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("Guardian Football", "https://www.theguardian.com/football/rss"),
]

_cache: Dict[str, object] = {"t": 0.0, "items": []}
CACHE_TTL = 600


def _text(el) -> str:
    if el is None or el.text is None:
        return ""
    return re.sub(r"\s+", " ", el.text).strip()


def _parse_rss(xml_bytes: bytes, source: str) -> List[dict]:
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items
    for item in root.findall(".//item")[:12]:
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        pub = _text(item.find("pubDate"))
        desc = _text(item.find("description"))
        if title:
            items.append({
                "titulo": title,
                "url": link,
                "fecha": pub[:22] if pub else "",
                "fuente": source,
                "resumen": desc[:180] if desc else "",
            })
    if not items:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//a:entry", ns)[:12]:
            title = _text(entry.find("a:title", ns))
            link_el = entry.find("a:link", ns)
            link = link_el.get("href") if link_el is not None else ""
            if title:
                items.append({
                    "titulo": title,
                    "url": link,
                    "fecha": "",
                    "fuente": source,
                    "resumen": "",
                })
    return items


def fetch_news(limit: int = 15) -> List[dict]:
    now = time.time()
    if _cache["items"] and now - float(_cache["t"]) < CACHE_TTL:
        return list(_cache["items"])[:limit]

    all_items: List[dict] = []
    for name, url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=12) as r:
                xml_bytes = r.read()
            all_items.extend(_parse_rss(xml_bytes, name))
        except Exception:
            continue

    _cache["t"] = now
    _cache["items"] = all_items
    return all_items[:limit]


def news_for_teams(team_names: List[str], limit: int = 8) -> List[dict]:
    keys = []
    for n in team_names:
        base = n.lower().replace(" fc", "").replace(" afc", "").strip()
        keys.append(base)
        if " " in base:
            keys.append(base.split()[0])
    keys = [k for k in keys if len(k) > 3]
    items = fetch_news(40)
    hit = []
    for it in items:
        t = (it["titulo"] + " " + it.get("resumen", "")).lower()
        if any(k in t for k in keys):
            hit.append(it)
        if len(hit) >= limit:
            break
    return hit if hit else items[:limit]
