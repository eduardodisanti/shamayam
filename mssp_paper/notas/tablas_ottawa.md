# Ottawa: velocidad variable dentro del registro

*Generado por `reproducibility_package/ottawa_report.py` desde `results/ottawa/results.json` (`ottawa_variable_speed.py`). No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

Datos: `Ottawa_Bearing_TimeVaryingSpeed`, Mendeley Data version 2, DOI 10.17632/v43hmbwxpm.2 (published 2019-02-06); manifiesto `a93306413a38…`. Puesta en marcha: ventanas sanas del ensayo 1 de un perfil (un registro de 10 s) o de los cuatro; radio r_(k) sobre esas ventanas. Sanos de prueba: 8 registros de los ensayos 2 y 3, nunca usados en la puesta en marcha. Fallos: 12 registros por tipo. Persistencia: 8 de 10 ventanas consecutivas. Semilla de los modelos por máquina 0, del OEM 42; 4000 ventanas aumentadas.

- OEM, cociente: 39/100 épocas, mejor val_loss 0,02332.
- OEM, cociente + ganancia: 31/100 épocas, mejor val_loss 0,05369.

## Velocidad de cada registro sano (Hz)

| registro | velocidad | ventanas cociente | ventanas tiempo |
|---|---|---|---|
| H-A-1 | 14,3–23,7 | 66 | 66 |
| H-A-2 | 14,2–28,9 | 71 | 66 |
| H-A-3 | 15,2–26,4 | 70 | 66 |
| H-B-1 | 14,1–28,8 | 71 | 66 |
| H-B-2 | 12,1–25,7 | 61 | 66 |
| H-B-3 | 14,1–28,6 | 71 | 66 |
| H-C-1 | 14,9–25,2 | 69 | 66 |
| H-C-2 | 14,5–23,9 | 66 | 66 |
| H-C-3 | 15,5–24,7 | 69 | 66 |
| H-D-1 | 14,9–24,1 | 62 | 66 |
| H-D-2 | 14,1–24,5 | 61 | 66 |
| H-D-3 | 17,0–25,8 | 69 | 66 |

## Falsas alarmas en sanos de prueba (ventanas)

Porcentaje de ventanas sobre el radio, con intervalo Clopper–Pearson al 95%. Columnas: con qué registro(s) se hizo la puesta en marcha.

| modelo | A-1 (creciente) | B-1 (decreciente) | C-1 (sube y baja) | D-1 (baja y sube) | los cuatro ensayos 1 |
|---|---|---|---|---|---|
| RMS, tiempo (clásico) | 38,3% [34,1–42,6] | 6,8% [4,8–9,3] | 9,1% [6,8–11,9] | 21,4% [18,0–25,1] | 9,1% [6,8–11,9] |
| curtosis, cociente (clásico) | 6,3% [4,4–8,7] | 19,7% [16,4–23,3] | 0,6% [0,1–1,6] | 3,3% [2,0–5,2] | 4,8% [3,2–7,0] |
| por máquina, crudo | 46,6% [42,3–50,9] | no aprende | 19,7% [16,4–23,3] | 28,8% [25,0–32,9] | 11,9% [9,3–15,0] |
| por máquina, crudo + aumento | no aprende | 7,8% [5,6–10,4] | 13,3% [10,5–16,5] | 24,4% [20,8–28,3] | 9,7% [7,3–12,5] |
| por máquina, cociente | 43,9% [39,6–48,2] | no aprende | 14,3% [11,5–17,6] | 25,5% [21,8–29,4] | 8,0% [5,8–10,6] |
| por máquina, cociente + ganancia | 25,5% [21,8–29,4] | 4,5% [2,9–6,6] | 8,4% [6,2–11,0] | 5,9% [4,1–8,3] | 4,8% [3,2–7,0] |
| OEM, cociente | 31,8% [27,9–35,9] | 4,1% [2,6–6,1] | 9,9% [7,5–12,7] | 20,1% [16,8–23,7] | 6,5% [4,6–8,9] |
| OEM, cociente + ganancia | 2,2% [1,2–3,9] | 10,6% [8,1–13,5] | 1,7% [0,8–3,2] | 5,0% [3,3–7,2] | 3,2% [1,9–5,0] |

## Registros sanos de prueba con alarma persistente

| modelo | A-1 (creciente) | B-1 (decreciente) | C-1 (sube y baja) | D-1 (baja y sube) | los cuatro ensayos 1 |
|---|---|---|---|---|---|
| RMS, tiempo (clásico) | 8/8 | 1/8 | 1/8 | 4/8 | 1/8 |
| curtosis, cociente (clásico) | 0/8 | 1/8 | 0/8 | 0/8 | 0/8 |
| por máquina, crudo | 8/8 | no aprende | 3/8 | 5/8 | 2/8 |
| por máquina, crudo + aumento | no aprende | 1/8 | 2/8 | 5/8 | 1/8 |
| por máquina, cociente | 8/8 | no aprende | 3/8 | 4/8 | 1/8 |
| por máquina, cociente + ganancia | 4/8 | 0/8 | 1/8 | 0/8 | 0/8 |
| OEM, cociente | 4/8 | 1/8 | 2/8 | 3/8 | 1/8 |
| OEM, cociente + ganancia | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 |

## Falsas alarmas por banda de velocidad

Ventanas sanas de prueba sobre el radio, por velocidad media de la ventana. Entre paréntesis, el rango de velocidad que cubrió la puesta en marcha.

### A-1 (creciente) (14,3–23,7 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 12,8% (27/211) | 53,3% (121/227) | 100,0% (54/54) |
| curtosis, cociente (clásico) | 0,0% (0/26) | 3,2% (6/185) | 9,4% (24/256) | 5,6% (4/71) |
| por máquina, crudo | 0,0% (0/36) | 13,3% (28/211) | 72,2% (164/227) | 100,0% (54/54) |
| por máquina, crudo + aumento | — | — | — | — |
| por máquina, cociente | 0,0% (0/26) | 11,4% (21/185) | 56,2% (144/256) | 100,0% (71/71) |
| por máquina, cociente + ganancia | 61,5% (16/26) | 11,9% (22/185) | 23,4% (60/256) | 54,9% (39/71) |
| OEM, cociente | 0,0% (0/26) | 9,7% (18/185) | 34,4% (88/256) | 91,5% (65/71) |
| OEM, cociente + ganancia | 7,7% (2/26) | 3,2% (6/185) | 1,2% (3/256) | 1,4% (1/71) |

### B-1 (decreciente) (14,1–28,8 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 0,5% (1/211) | 13,2% (30/227) | 9,3% (5/54) |
| curtosis, cociente (clásico) | 3,8% (1/26) | 12,4% (23/185) | 27,0% (69/256) | 18,3% (13/71) |
| por máquina, crudo | — | — | — | — |
| por máquina, crudo + aumento | 0,0% (0/36) | 0,9% (2/211) | 14,1% (32/227) | 13,0% (7/54) |
| por máquina, cociente | — | — | — | — |
| por máquina, cociente + ganancia | 26,9% (7/26) | 5,4% (10/185) | 1,2% (3/256) | 5,6% (4/71) |
| OEM, cociente | 0,0% (0/26) | 0,0% (0/185) | 5,5% (14/256) | 11,3% (8/71) |
| OEM, cociente + ganancia | 11,5% (3/26) | 10,3% (19/185) | 10,5% (27/256) | 11,3% (8/71) |

### C-1 (sube y baja) (14,9–25,2 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 2,4% (5/211) | 14,5% (33/227) | 18,5% (10/54) |
| curtosis, cociente (clásico) | 0,0% (0/26) | 0,5% (1/185) | 0,8% (2/256) | 0,0% (0/71) |
| por máquina, crudo | 0,0% (0/36) | 8,5% (18/211) | 18,9% (43/227) | 79,6% (43/54) |
| por máquina, crudo + aumento | 0,0% (0/36) | 6,6% (14/211) | 15,9% (36/227) | 37,0% (20/54) |
| por máquina, cociente | 0,0% (0/26) | 1,6% (3/185) | 14,1% (36/256) | 53,5% (38/71) |
| por máquina, cociente + ganancia | 23,1% (6/26) | 11,4% (21/185) | 3,5% (9/256) | 12,7% (9/71) |
| OEM, cociente | 0,0% (0/26) | 0,0% (0/185) | 11,3% (29/256) | 33,8% (24/71) |
| OEM, cociente + ganancia | 3,8% (1/26) | 3,2% (6/185) | 0,4% (1/256) | 1,4% (1/71) |

### D-1 (baja y sube) (14,9–24,1 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 8,5% (18/211) | 21,6% (49/227) | 85,2% (46/54) |
| curtosis, cociente (clásico) | 0,0% (0/26) | 1,1% (2/185) | 5,9% (15/256) | 1,4% (1/71) |
| por máquina, crudo | 0,0% (0/36) | 10,0% (21/211) | 33,9% (77/227) | 100,0% (54/54) |
| por máquina, crudo + aumento | 0,0% (0/36) | 9,0% (19/211) | 24,7% (56/227) | 100,0% (54/54) |
| por máquina, cociente | 0,0% (0/26) | 7,6% (14/185) | 20,7% (53/256) | 98,6% (70/71) |
| por máquina, cociente + ganancia | 26,9% (7/26) | 5,9% (11/185) | 2,3% (6/256) | 11,3% (8/71) |
| OEM, cociente | 0,0% (0/26) | 5,4% (10/185) | 20,3% (52/256) | 64,8% (46/71) |
| OEM, cociente + ganancia | 11,5% (3/26) | 5,9% (11/185) | 4,3% (11/256) | 2,8% (2/71) |

### los cuatro ensayos 1 (14,1–28,8 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 2,4% (5/211) | 14,5% (33/227) | 18,5% (10/54) |
| curtosis, cociente (clásico) | 0,0% (0/26) | 2,2% (4/185) | 7,8% (20/256) | 2,8% (2/71) |
| por máquina, crudo | 0,0% (0/36) | 5,2% (11/211) | 15,9% (36/227) | 29,6% (16/54) |
| por máquina, crudo + aumento | 0,0% (0/36) | 3,3% (7/211) | 15,0% (34/227) | 18,5% (10/54) |
| por máquina, cociente | 0,0% (0/26) | 0,0% (0/185) | 10,5% (27/256) | 22,5% (16/71) |
| por máquina, cociente + ganancia | 7,7% (2/26) | 8,6% (16/185) | 1,6% (4/256) | 5,6% (4/71) |
| OEM, cociente | 0,0% (0/26) | 0,0% (0/185) | 8,2% (21/256) | 19,7% (14/71) |
| OEM, cociente + ganancia | 7,7% (2/26) | 4,3% (8/185) | 2,3% (6/256) | 1,4% (1/71) |

## Detección por tipo de fallo

Registros con alarma persistente (de 12) y AUROC ventana a ventana frente a los sanos de prueba (el AUROC no depende del radio).

### Puesta en marcha: A-1 (creciente)

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 12/12; 0,529 | 12/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 12/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | 12/12; 0,998 | 12/12; 0,510 | 12/12; 0,833 | 12/12; 0,996 |
| por máquina, crudo + aumento | — | — | — | — |
| por máquina, cociente | 12/12; 0,998 | 11/12; 0,459 | 12/12; 0,810 | 12/12; 0,996 |
| por máquina, cociente + ganancia | 12/12; 0,998 | 0/12; 0,327 | 12/12; 0,836 | 12/12; 0,995 |
| OEM, cociente | 12/12; 0,997 | 7/12; 0,449 | 12/12; 0,797 | 12/12; 0,995 |
| OEM, cociente + ganancia | 4/12; 0,597 | 10/12; 0,457 | 0/12; 0,438 | 8/12; 0,407 |

### Puesta en marcha: B-1 (decreciente)

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 0/12; 0,529 | 9/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 12/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | — | — | — | — |
| por máquina, crudo + aumento | 12/12; 0,998 | 0/12; 0,542 | 12/12; 0,840 | 12/12; 0,996 |
| por máquina, cociente | — | — | — | — |
| por máquina, cociente + ganancia | 12/12; 0,987 | 0/12; 0,252 | 12/12; 0,881 | 12/12; 0,997 |
| OEM, cociente | 12/12; 0,997 | 0/12; 0,449 | 6/12; 0,797 | 12/12; 0,995 |
| OEM, cociente + ganancia | 9/12; 0,597 | 10/12; 0,457 | 0/12; 0,438 | 10/12; 0,407 |

### Puesta en marcha: C-1 (sube y baja)

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 0/12; 0,529 | 12/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 1/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | 12/12; 0,998 | 8/12; 0,558 | 12/12; 0,839 | 12/12; 0,996 |
| por máquina, crudo + aumento | 12/12; 0,998 | 2/12; 0,573 | 12/12; 0,845 | 12/12; 0,996 |
| por máquina, cociente | 12/12; 0,998 | 2/12; 0,470 | 12/12; 0,811 | 12/12; 0,996 |
| por máquina, cociente + ganancia | 12/12; 0,999 | 0/12; 0,338 | 12/12; 0,859 | 12/12; 0,995 |
| OEM, cociente | 12/12; 0,997 | 1/12; 0,449 | 8/12; 0,797 | 12/12; 0,995 |
| OEM, cociente + ganancia | 3/12; 0,597 | 10/12; 0,457 | 0/12; 0,438 | 8/12; 0,407 |

### Puesta en marcha: D-1 (baja y sube)

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 8/12; 0,529 | 12/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 12/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | 12/12; 0,998 | 10/12; 0,527 | 12/12; 0,830 | 12/12; 0,996 |
| por máquina, crudo + aumento | 12/12; 0,998 | 9/12; 0,518 | 12/12; 0,846 | 12/12; 0,996 |
| por máquina, cociente | 12/12; 0,998 | 6/12; 0,468 | 12/12; 0,810 | 12/12; 0,996 |
| por máquina, cociente + ganancia | 12/12; 0,998 | 0/12; 0,343 | 12/12; 0,852 | 12/12; 0,994 |
| OEM, cociente | 12/12; 0,997 | 2/12; 0,449 | 12/12; 0,797 | 12/12; 0,995 |
| OEM, cociente + ganancia | 8/12; 0,597 | 10/12; 0,457 | 0/12; 0,438 | 9/12; 0,407 |

### Puesta en marcha: los cuatro ensayos 1

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 0/12; 0,529 | 12/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 12/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | 12/12; 0,998 | 1/12; 0,539 | 12/12; 0,844 | 12/12; 0,996 |
| por máquina, crudo + aumento | 12/12; 0,998 | 0/12; 0,531 | 12/12; 0,845 | 12/12; 0,996 |
| por máquina, cociente | 12/12; 0,998 | 0/12; 0,461 | 8/12; 0,811 | 12/12; 0,996 |
| por máquina, cociente + ganancia | 12/12; 0,999 | 0/12; 0,288 | 12/12; 0,849 | 12/12; 0,995 |
| OEM, cociente | 12/12; 0,997 | 0/12; 0,449 | 7/12; 0,797 | 12/12; 0,995 |
| OEM, cociente + ganancia | 6/12; 0,597 | 10/12; 0,457 | 0/12; 0,438 | 9/12; 0,407 |

## Modelos por máquina: entrenamiento

Ventanas de entrenamiento; varianza no reconstruida (se rechaza solo el colapso, > 0,98); val_loss / train_loss.

| puesta en marcha | modelo | ventanas | no reconstruida | generalización |
|---|---|---|---|---|
| A-1 (creciente) | por máquina, crudo | 66 | 0,86 | 1,57 |
| A-1 (creciente) | por máquina, crudo + aumento | — | colapso | — |
| A-1 (creciente) | por máquina, cociente | 4000 | 0,79 | 1,12 |
| A-1 (creciente) | por máquina, cociente + ganancia | 4000 | 0,78 | 1,11 |
| B-1 (decreciente) | por máquina, crudo | — | colapso | — |
| B-1 (decreciente) | por máquina, crudo + aumento | 4000 | 0,74 | 1,21 |
| B-1 (decreciente) | por máquina, cociente | — | colapso | — |
| B-1 (decreciente) | por máquina, cociente + ganancia | 4000 | 0,80 | 1,12 |
| C-1 (sube y baja) | por máquina, crudo | 66 | 0,73 | 1,51 |
| C-1 (sube y baja) | por máquina, crudo + aumento | 4000 | 0,70 | 1,18 |
| C-1 (sube y baja) | por máquina, cociente | 4000 | 0,83 | 1,09 |
| C-1 (sube y baja) | por máquina, cociente + ganancia | 4000 | 0,82 | 1,09 |
| D-1 (baja y sube) | por máquina, crudo | 66 | 0,90 | 1,17 |
| D-1 (baja y sube) | por máquina, crudo + aumento | 4000 | 0,72 | 1,18 |
| D-1 (baja y sube) | por máquina, cociente | 4000 | 0,83 | 1,11 |
| D-1 (baja y sube) | por máquina, cociente + ganancia | 4000 | 0,81 | 1,11 |
| los cuatro ensayos 1 | por máquina, crudo | 264 | 0,73 | 1,06 |
| los cuatro ensayos 1 | por máquina, crudo + aumento | 4000 | 0,76 | 1,12 |
| los cuatro ensayos 1 | por máquina, cociente | 4000 | 0,82 | 1,12 |
| los cuatro ensayos 1 | por máquina, cociente + ganancia | 4000 | 0,83 | 1,09 |

## Variabilidad entre semillas

Semillas 0, 1, 2, 3, 4 (modelos por máquina; el OEM con semillas 42, 0, 1, 2, 3). Media [mínimo–máximo]; entre paréntesis, entrenamientos que colapsaron. Escenarios de puesta en marcha: A-1 (creciente), los cuatro ensayos 1.

### Puesta en marcha: A-1 (creciente)

| modelo | FAR ventanas | registros sanos con alarma (de 8) | AUROC pista interior | AUROC pista exterior | AUROC bola | AUROC combinado |
|---|---|---|---|---|---|---|
| RMS, tiempo (clásico) | 38,3% [38,3–38,3] | 8,0 [8,0–8,0] | 0,998 [0,998–0,998] | 0,529 [0,529–0,529] | 0,830 [0,830–0,830] | 0,996 [0,996–0,996] |
| curtosis, cociente (clásico) | 6,3% [6,3–6,3] | 0,0 [0,0–0,0] | 0,991 [0,991–0,991] | 0,988 [0,988–0,988] | 0,507 [0,507–0,507] | 1,000 [1,000–1,000] |
| por máquina, crudo | 46,6% [46,6–46,6] | 8,0 [8,0–8,0] | 0,998 [0,998–0,998] | 0,510 [0,509–0,510] | 0,833 [0,833–0,833] | 0,996 [0,996–0,996] |
| por máquina, crudo + aumento | 44,1% (4) | 8,0 | 0,998 | 0,481 | 0,833 | 0,996 |
| por máquina, cociente | 42,8% [41,4–44,2] (1) | 8,0 [8,0–8,0] | 0,998 [0,998–0,998] | 0,463 [0,457–0,468] | 0,809 [0,809–0,810] | 0,996 [0,996–0,996] |
| por máquina, cociente + ganancia | 33,9% [25,5–42,2] | 4,8 [4,0–6,0] | 0,995 [0,988–0,998] | 0,301 [0,280–0,327] | 0,836 [0,828–0,843] | 0,992 [0,987–0,997] |
| OEM, cociente | 37,1% [29,0–45,4] | 6,2 [4,0–8,0] | 0,997 [0,997–0,998] | 0,466 [0,449–0,489] | 0,787 [0,782–0,797] | 0,995 [0,994–0,995] |
| OEM, cociente + ganancia | 1,4% [0,6–2,2] | 0,0 [0,0–0,0] | 0,603 [0,590–0,627] | 0,445 [0,432–0,457] | 0,476 [0,438–0,528] | 0,405 [0,393–0,412] |

### Puesta en marcha: los cuatro ensayos 1

| modelo | FAR ventanas | registros sanos con alarma (de 8) | AUROC pista interior | AUROC pista exterior | AUROC bola | AUROC combinado |
|---|---|---|---|---|---|---|
| RMS, tiempo (clásico) | 9,1% [9,1–9,1] | 1,0 [1,0–1,0] | 0,998 [0,998–0,998] | 0,529 [0,529–0,529] | 0,830 [0,830–0,830] | 0,996 [0,996–0,996] |
| curtosis, cociente (clásico) | 4,8% [4,8–4,8] | 0,0 [0,0–0,0] | 0,991 [0,991–0,991] | 0,988 [0,988–0,988] | 0,507 [0,507–0,507] | 1,000 [1,000–1,000] |
| por máquina, crudo | 13,1% [10,4–16,3] | 1,6 [1,0–2,0] | 0,998 [0,998–0,998] | 0,539 [0,524–0,545] | 0,842 [0,839–0,844] | 0,996 [0,996–0,996] |
| por máquina, crudo + aumento | 9,7% [9,5–10,0] (1) | 1,0 [1,0–1,0] | 0,998 [0,998–0,998] | 0,527 [0,523–0,531] | 0,845 [0,844–0,846] | 0,996 [0,996–0,996] |
| por máquina, cociente | 7,5% [7,1–8,0] (3) | 1,0 [1,0–1,0] | 0,998 [0,998–0,998] | 0,458 [0,455–0,461] | 0,811 [0,811–0,811] | 0,996 [0,996–0,996] |
| por máquina, cociente + ganancia | 4,9% [4,1–6,3] | 0,4 [0,0–1,0] | 0,999 [0,997–1,000] | 0,305 [0,288–0,317] | 0,849 [0,841–0,854] | 0,995 [0,993–0,996] |
| OEM, cociente | 7,3% [5,2–10,4] | 1,2 [1,0–2,0] | 0,997 [0,997–0,998] | 0,466 [0,449–0,489] | 0,787 [0,782–0,797] | 0,995 [0,994–0,995] |
| OEM, cociente + ganancia | 3,2% [1,5–4,8] | 0,0 [0,0–0,0] | 0,603 [0,590–0,627] | 0,445 [0,432–0,457] | 0,476 [0,438–0,528] | 0,405 [0,393–0,412] |

## Apéndice: la velocidad más allá del cambio de escala temporal

*Análisis, no método: nada se entrena aquí. Generado por `ottawa_speed_appendix.py` → `results/ottawa/appendix.json`.*

### La amplitud sigue a la velocidad (registros sanos)

Correlación ventana a ventana entre el RMS (ventanas de tiempo) y la velocidad, y exponente α de RMS ∝ velocidad^α.

| registro | correlación | α | velocidad (Hz) |
|---|---|---|---|
| H-A-1 | 0,956 | 1,05 | 14,3–23,7 |
| H-A-2 | 0,982 | 1,17 | 14,2–28,8 |
| H-A-3 | 0,968 | 1,12 | 15,2–26,4 |
| H-B-1 | 0,958 | 1,15 | 14,2–28,7 |
| H-B-2 | 0,985 | 1,28 | 11,8–25,7 |
| H-B-3 | 0,971 | 1,16 | 14,1–28,6 |
| H-C-1 | 0,978 | 1,26 | 14,9–25,2 |
| H-C-2 | 0,977 | 1,37 | 14,4–24,0 |
| H-C-3 | 0,946 | 1,11 | 15,5–24,7 |
| H-D-1 | 0,931 | 1,07 | 14,9–24,1 |
| H-D-2 | 0,975 | 1,20 | 14,1–24,4 |
| H-D-3 | 0,917 | 1,53 | 17,1–25,8 |

### Falsas alarmas por banda de velocidad, todas las semillas

Ventanas sanas de prueba sobre el radio global, sumadas sobre semillas. La dispersión entre bandas mide cuánto depende la puntuación de la velocidad.

#### A-1 (creciente)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz | dispersión (puntos) |
|---|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% | 12,8% | 53,3% | 100,0% | 100,0 |
| curtosis, cociente (clásico) | 0,0% | 3,2% | 9,4% | 5,6% | 9,4 |
| por máquina, crudo | 0,0% | 13,3% | 72,2% | 100,0% | 100,0 |
| por máquina, crudo + aumento | 0,0% | 13,3% | 66,5% | 100,0% | 100,0 |
| por máquina, cociente | 0,0% | 11,2% | 54,2% | 100,0% | 100,0 |
| por máquina, cociente + ganancia | 68,5% | 18,2% | 33,0% | 65,9% | 50,3 |
| OEM, cociente | 0,0% | 9,9% | 43,8% | 97,5% | 97,5 |
| OEM, cociente + ganancia | 2,3% | 2,1% | 1,1% | 0,6% | 1,7 |

#### los cuatro ensayos 1

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz | dispersión (puntos) |
|---|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% | 2,4% | 14,5% | 18,5% | 18,5 |
| curtosis, cociente (clásico) | 0,0% | 2,2% | 7,8% | 2,8% | 7,8 |
| por máquina, crudo | 0,0% | 5,8% | 16,4% | 36,7% | 36,7 |
| por máquina, crudo + aumento | 0,0% | 3,6% | 15,0% | 18,1% | 18,1 |
| por máquina, cociente | 0,0% | 0,0% | 10,2% | 20,4% | 20,4 |
| por máquina, cociente + ganancia | 10,8% | 8,3% | 1,9% | 5,1% | 8,9 |
| OEM, cociente | 0,0% | 0,0% | 9,5% | 21,4% | 21,4 |
| OEM, cociente + ganancia | 6,2% | 3,2% | 3,2% | 2,3% | 3,9 |

### Radio condicionado a la velocidad (análisis)

Cada banda recibe su propio r_(k) solo si la puesta en marcha tiene al menos 49 ventanas en ella; si no, no existe radio libre de distribución al 0,98 y sus ventanas de prueba quedan sin cubrir. FAR global frente a condicionada (solo en bandas cubiertas), sumadas sobre semillas.

#### A-1 (creciente)

Ventanas de puesta en marcha por banda (cociente): 10–15 Hz: 3, 15–20 Hz: 25, 20–25 Hz: 38, 25–30 Hz: 0.

| modelo | FAR, radio global | FAR, radio por banda (bandas cubiertas) | ventanas de prueba sin cubrir |
|---|---|---|---|
| RMS, tiempo (clásico) | 38,3% | — | 100,0% (2640/2640) |
| curtosis, cociente (clásico) | 6,3% | — | 100,0% (2690/2690) |
| por máquina, crudo | 46,6% | — | 100,0% (2640/2640) |
| por máquina, crudo + aumento | 44,1% | — | 100,0% (528/528) |
| por máquina, cociente | 42,8% | — | 100,0% (2152/2152) |
| por máquina, cociente + ganancia | 33,9% | — | 100,0% (2690/2690) |
| OEM, cociente | 37,1% | — | 100,0% (2690/2690) |
| OEM, cociente + ganancia | 1,4% | — | 100,0% (2690/2690) |

#### los cuatro ensayos 1

Ventanas de puesta en marcha por banda (cociente): 10–15 Hz: 8, 15–20 Hz: 102, 20–25 Hz: 132, 25–30 Hz: 26.

| modelo | FAR, radio global | FAR, radio por banda (bandas cubiertas) | ventanas de prueba sin cubrir |
|---|---|---|---|
| RMS, tiempo (clásico) | 9,1% | 14,6% | 17,0% (450/2640) |
| curtosis, cociente (clásico) | 4,8% | 10,4% | 18,0% (485/2690) |
| por máquina, crudo | 13,1% | 16,3% | 17,0% (450/2640) |
| por máquina, crudo + aumento | 9,7% | 14,8% | 17,0% (360/2112) |
| por máquina, cociente | 7,5% | 15,1% | 18,0% (194/1076) |
| por máquina, cociente + ganancia | 4,9% | 6,5% | 18,0% (485/2690) |
| OEM, cociente | 7,3% | 14,2% | 18,0% (485/2690) |
| OEM, cociente + ganancia | 3,2% | 3,0% | 18,0% (485/2690) |
