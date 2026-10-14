# Varios espacios cociente a la vez, con la garantía

*Generado por `reproducibility_package/extra_reports.py` desde `results/multispace/results.json` (`multispace_union.py`). No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

Alarma si cualquiera de los K espacios supera su radio. Cada radio se toma al nivel 1 − 0,02/K (Bonferroni), de modo que la falsa alarma total queda acotada por 0,02 sin suponer nada sobre la dependencia entre espacios. Precio: con K = 2 hacen falta al menos 99 observaciones de puesta en marcha. Nada se entrena: puntuaciones ya guardadas.

## Ottawa (5 semillas del OEM; la curtosis no depende de la semilla)

FAR por ventana y registros sanos con alarma persistente (de 8); por tipo de fallo, registros detectados (de 12). Media [mín–máx] sobre semillas.

| puesta en marcha | espacios | FAR ventanas | registros sanos con alarma | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|---|---|---|
| los cuatro ensayos 1 | OEM (q) | 8,4% [5,8–10,6] | 1,6 [1,0–2,0] | 12,0 | 0,6 [0,0–1,0] | 7,8 [7,0–8,0] | 12,0 |
| los cuatro ensayos 1 | curtosis (q) | 4,8% | 0,0 | 12,0 | 12,0 | 2,0 | 12,0 |
| los cuatro ensayos 1 | OEM (q) + curtosis (q) | 7,8% [5,8–9,3] | 1,2 [1,0–2,0] | 12,0 | 12,0 | 7,0 [6,0–8,0] | 12,0 |
| A-1 | OEM (q) | 41,1% [29,4–47,0] | 6,8 [4,0–8,0] | 12,0 | 10,0 [7,0–12,0] | 12,0 | 12,0 |
| A-1 | curtosis (q) | 6,3% | 0,0 | 12,0 | 12,0 | 2,0 | 12,0 |
| A-1 | OEM (q) + curtosis (q) | no certificable (pocas observaciones) | — | — | — | — | — |

## IMS (salida y FAR en los registros 200–499)

| bearing | espacios | n = 49 | n = 99 | n = 149 | n = 200 |
|---|---|---|---|---|---|
| 1 | RMS | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% |
| 1 | curtosis | 708 (45,67 h); FAR 0,0% | 654 (54,67 h); FAR 0,7% | 654 (54,67 h); FAR 1,0% | 654 (54,67 h); FAR 1,0% |
| 1 | OEM publicado | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% |
| 1 | RMS + curtosis | no certificable | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% |
| 1 | OEM publicado + curtosis | no certificable | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% | 539 (73,83 h); FAR 0,0% |
| 2 | RMS | 782 (33,33 h); FAR 0,0% | 782 (33,33 h); FAR 0,0% | 710 (45,33 h); FAR 0,0% | 710 (45,33 h); FAR 0,0% |
| 2 | curtosis | sin salida; FAR 0,0% | sin salida; FAR 0,0% | sin salida; FAR 0,0% | sin salida; FAR 0,3% |
| 2 | OEM publicado | 794 (31,33 h); FAR 0,0% | 794 (31,33 h); FAR 0,0% | 791 (31,83 h); FAR 0,0% | 720 (43,67 h); FAR 0,0% |
| 2 | RMS + curtosis | no certificable | 782 (33,33 h); FAR 0,0% | 782 (33,33 h); FAR 0,0% | 782 (33,33 h); FAR 0,0% |
| 2 | OEM publicado + curtosis | no certificable | 794 (31,33 h); FAR 0,0% | 794 (31,33 h); FAR 0,0% | 794 (31,33 h); FAR 0,0% |
| 3 | RMS | 894 (14,67 h); FAR 0,0% | 894 (14,67 h); FAR 0,0% | 894 (14,67 h); FAR 0,0% | 894 (14,67 h); FAR 0,0% |
| 3 | curtosis | sin salida; FAR 0,0% | sin salida; FAR 0,0% | sin salida; FAR 0,0% | sin salida; FAR 0,0% |
| 3 | OEM publicado | 896 (14,33 h); FAR 0,0% | 896 (14,33 h); FAR 0,0% | 892 (15,00 h); FAR 0,0% | 892 (15,00 h); FAR 0,0% |
| 3 | RMS + curtosis | no certificable | 894 (14,67 h); FAR 0,0% | 894 (14,67 h); FAR 0,0% | 894 (14,67 h); FAR 0,0% |
| 3 | OEM publicado + curtosis | no certificable | 896 (14,33 h); FAR 0,0% | 896 (14,33 h); FAR 0,0% | 896 (14,33 h); FAR 0,0% |
| 4 | RMS | 619 (60,50 h); FAR 1,7% | 619 (60,50 h); FAR 1,7% | 619 (60,50 h); FAR 1,7% | 619 (60,50 h); FAR 1,7% |
| 4 | curtosis | sin salida; FAR 0,0% | 939 (7,17 h); FAR 0,3% | 925 (9,50 h); FAR 0,3% | 925 (9,50 h); FAR 0,3% |
| 4 | OEM publicado | 705 (46,17 h); FAR 0,0% | 667 (52,50 h); FAR 1,0% | 667 (52,50 h); FAR 1,0% | 667 (52,50 h); FAR 1,0% |
| 4 | RMS + curtosis | no certificable | 656 (54,33 h); FAR 0,3% | 656 (54,33 h); FAR 0,3% | 656 (54,33 h); FAR 0,7% |
| 4 | OEM publicado + curtosis | no certificable | 705 (46,17 h); FAR 0,0% | 705 (46,17 h); FAR 0,0% | 705 (46,17 h); FAR 0,3% |
