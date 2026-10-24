# Scout Deportes · estilo Windrawwin

Datos **reales** de resultados + **modelo Poisson** (probabilidades 1X2) + **RSS** de noticias.

## Cómo usar

```bash
python3 servidor.py
```

Abre http://127.0.0.1:8780

## Qué hace el algoritmo

1. Calcula goles esperados (λ) con ataque/defensa y forma (casa/fuera).
2. Distribución de Poisson → P(1), P(X), P(2), Over/Under 2.5, marcadores más probables.
3. Cuotas implícitas ≈ 1/probabilidad.

**No determina el ganador real.** Es un modelo estadístico educativo.

## Fuentes

| Dato | Fuente |
|------|--------|
| Resultados / tabla / forma | openfootball (GitHub) |
| Probabilidades | modelo Python local |
| Noticias | RSS BBC + Guardian |

## Limitaciones

- Sin corners, tiros, tarjetas (openfootball no los trae).
- RSS no rellena stats de partido; solo titulares.
- Para stats avanzadas hace falta API-Football (clave free).

Uso educativo. No es consejo de apuestas.
