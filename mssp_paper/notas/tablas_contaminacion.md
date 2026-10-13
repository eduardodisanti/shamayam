# Puesta en marcha contaminada por un fallo ya presente

*Generado por `reproducibility_package/extra_reports.py` desde `results/contamination/results.json` (`commissioning_contamination.py`). No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

IMS, bearing 1 (el único fallo real). Se sustituyen m de los n registros de puesta en marcha por registros elegidos al azar entre los últimos 100 activos (fallo inequívoco), se recalcula el radio y se busca la salida persistente (8 de 10) en la secuencia real. 1000 sorteos por casilla (semilla 20261013). Tolera = n − k: contaminaciones que el radio absorbe sin cambiar, si quedan por encima de todo lo sano.

## OEM publicado

| radio | tolera | m contaminados | fallo no detectado | antelación mediana (h) | radio / radio limpio (mediana) |
|---|---|---|---|---|---|
| r_(k), n=49 | 0 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=49 | 0 | 1 | 10,7% | 7,3 | 3,37 |
| r_(k), n=49 | 0 | 2 | 17,7% | 3,8 | 4,78 |
| r_(k), n=49 | 0 | 3 | 24,0% | 2,5 | 6,15 |
| r_(k), n=49 | 0 | 5 | 37,2% | 1,7 | 10,21 |
| r_(k), n=99 | 1 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=99 | 1 | 1 | 0,0% | 73,8 | 1,00 |
| r_(k), n=99 | 1 | 2 | 1,1% | 45,3 | 2,99 |
| r_(k), n=99 | 1 | 3 | 2,2% | 4,2 | 3,51 |
| r_(k), n=99 | 1 | 5 | 6,1% | 3,7 | 4,29 |
| r_(k), n=149 | 2 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=149 | 2 | 1 | 0,0% | 73,8 | 1,00 |
| r_(k), n=149 | 2 | 2 | 0,0% | 73,8 | 1,00 |
| r_(k), n=149 | 2 | 3 | 0,0% | 45,5 | 2,73 |
| r_(k), n=149 | 2 | 5 | 0,6% | 7,3 | 3,38 |
| tolerancia, n=149 | 0 | 0 | 0,0% | 73,8 | 1,00 |
| tolerancia, n=149 | 0 | 1 | 9,0% | 7,3 | 3,36 |
| tolerancia, n=149 | 0 | 2 | 16,5% | 3,8 | 4,35 |
| tolerancia, n=149 | 0 | 3 | 23,2% | 2,7 | 5,73 |
| tolerancia, n=149 | 0 | 5 | 40,4% | 1,7 | 11,89 |

## RMS

| radio | tolera | m contaminados | fallo no detectado | antelación mediana (h) | radio / radio limpio (mediana) |
|---|---|---|---|---|---|
| r_(k), n=49 | 0 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=49 | 0 | 1 | 8,7% | 7,3 | 2,28 |
| r_(k), n=49 | 0 | 2 | 17,6% | 4,0 | 2,58 |
| r_(k), n=49 | 0 | 3 | 25,3% | 2,8 | 2,96 |
| r_(k), n=49 | 0 | 5 | 39,9% | 2,0 | 4,28 |
| r_(k), n=99 | 1 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=99 | 1 | 1 | 0,0% | 73,8 | 1,00 |
| r_(k), n=99 | 1 | 2 | 0,9% | 45,5 | 2,05 |
| r_(k), n=99 | 1 | 3 | 2,3% | 7,3 | 2,22 |
| r_(k), n=99 | 1 | 5 | 6,0% | 3,7 | 2,54 |
| r_(k), n=149 | 2 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=149 | 2 | 1 | 0,0% | 73,8 | 1,00 |
| r_(k), n=149 | 2 | 2 | 0,0% | 73,8 | 1,00 |
| r_(k), n=149 | 2 | 3 | 0,2% | 45,5 | 1,95 |
| r_(k), n=149 | 2 | 5 | 0,8% | 7,3 | 2,22 |
| tolerancia, n=149 | 0 | 0 | 0,0% | 73,8 | 1,00 |
| tolerancia, n=149 | 0 | 1 | 9,3% | 7,3 | 2,21 |
| tolerancia, n=149 | 0 | 2 | 17,4% | 3,8 | 2,67 |
| tolerancia, n=149 | 0 | 3 | 26,1% | 2,8 | 2,96 |
| tolerancia, n=149 | 0 | 5 | 37,3% | 1,7 | 4,06 |

## envolvente

| radio | tolera | m contaminados | fallo no detectado | antelación mediana (h) | radio / radio limpio (mediana) |
|---|---|---|---|---|---|
| r_(k), n=49 | 0 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=49 | 0 | 1 | 6,4% | 45,5 | 9,78 |
| r_(k), n=49 | 0 | 2 | 14,7% | 45,5 | 10,84 |
| r_(k), n=49 | 0 | 3 | 17,8% | 45,5 | 12,29 |
| r_(k), n=49 | 0 | 5 | 28,7% | 45,5 | 12,68 |
| r_(k), n=99 | 1 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=99 | 1 | 1 | 0,0% | 73,8 | 1,03 |
| r_(k), n=99 | 1 | 2 | 0,5% | 45,5 | 8,31 |
| r_(k), n=99 | 1 | 3 | 1,3% | 45,5 | 9,86 |
| r_(k), n=99 | 1 | 5 | 5,4% | 45,5 | 10,91 |
| r_(k), n=149 | 2 | 0 | 0,0% | 73,8 | 1,00 |
| r_(k), n=149 | 2 | 1 | 0,0% | 73,8 | 1,01 |
| r_(k), n=149 | 2 | 2 | 0,0% | 73,8 | 1,04 |
| r_(k), n=149 | 2 | 3 | 0,1% | 45,7 | 7,44 |
| r_(k), n=149 | 2 | 5 | 0,2% | 45,5 | 9,95 |
| tolerancia, n=149 | 0 | 0 | 0,0% | 73,8 | 1,00 |
| tolerancia, n=149 | 0 | 1 | 7,7% | 45,5 | 9,51 |
| tolerancia, n=149 | 0 | 2 | 12,9% | 45,5 | 10,68 |
| tolerancia, n=149 | 0 | 3 | 21,8% | 45,5 | 12,03 |
| tolerancia, n=149 | 0 | 5 | 36,0% | 45,5 | 12,42 |
