# CWRU, ablación con 5 semillas: tablas para discutir

*Generado por `reproducibility_package/cwru_ablation_discussion.py` desde `results/cwru_projection/quotient_ablation_5seeds.json`. Hecho después de ver los resultados; **no es un veredicto**. No editar a mano.*

## 1. Falsas alarmas por semilla, en ventanas

| rpm | nivel | sanas | semilla 0 | semilla 1 | semilla 2 | semilla 3 | semilla 4 |
|---|---|---|---|---|---|---|---|
| 1730 | G1 | 47 | 1 | 1 | 4 | 0 | 1 |
| 1730 | G2 | 47 | 2 | 2 | 0 | 2 | 3 |
| 1730 | G3 | 47 | 4 | 1 | 1 | 1 | 0 |
| 1730 | G4 | 47 | 3 | 2 | 6 | 1 | 1 |
| 1750 | G1 | 49 | 0 | 0 | 0 | 0 | 0 |
| 1750 | G2 | 49 | 0 | 0 | 0 | 0 | 0 |
| 1750 | G3 | 49 | 0 | 0 | 0 | 0 | 0 |
| 1750 | G4 | 49 | 0 | 0 | 0 | 0 | 0 |
| 1772 | G1 | 50 | 1 | 0 | 0 | 0 | 2 |
| 1772 | G2 | 50 | 5 | 2 | 0 | 0 | 3 |
| 1772 | G3 | 50 | 0 | 1 | 0 | 1 | 5 |
| 1772 | G4 | 50 | 4 | 0 | 2 | 0 | 7 |

## 2. Comparación pareada con G1 (misma semilla y velocidad)

Diferencia en ventanas con falsa alarma (nivel − G1) en los 15 pares (3 velocidades × 5 semillas). Test de signos exacto, bilateral, sobre los pares no empatados; sin corregir por comparaciones múltiples.

| comparación | pares | peor | mejor | igual | rango (ventanas) | p (signos) |
|---|---|---|---|---|---|---|
| G2 − G1 | 15 | 7 | 1 | 7 | -4 a 4 | 0,070 |
| G3 − G1 | 15 | 5 | 3 | 7 | -3 a 3 | 0,727 |
| G4 − G1 | 15 | 7 | 0 | 8 | 0 a 5 | 0,016 |
