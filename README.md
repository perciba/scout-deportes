# Scout Deportes

Analizador de **fútbol con datos reales** (resultados openfootball).

HTML + Python. Sin API key.

## Qué incluye

- Premier League, La Liga, Bundesliga, Serie A, Ligue 1 (temporada en el JSON público)
- Tabla, goles a favor/contra, forma (últimos 5), casa/fuera
- Comparador local vs visitante + H2H de la temporada
- Lectura automática simple de desequilibrios

## Qué NO incluye (aún)

Corners, tiros, tarjetas, atajadas y stats de jugador detalladas: no vienen en openfootball.
Eso requiere otra API (p. ej. API-Football free con clave).

## Cómo usar

```bash
cd scout-deportes
python3 servidor.py
```

Abre http://127.0.0.1:8780

## Fuente

[openfootball/football.json](https://github.com/openfootball/football.json) — resultados públicos reales.

Uso educativo. No es predicción ni consejo de apuestas.
