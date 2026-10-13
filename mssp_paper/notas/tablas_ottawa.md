# Ottawa: velocidad variable dentro del registro

*Generado por `reproducibility_package/ottawa_report.py` desde `results/ottawa/results.json` (`ottawa_variable_speed.py`). No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

Datos: `Ottawa_Bearing_TimeVaryingSpeed`, Mendeley Data version 2, DOI 10.17632/v43hmbwxpm.2 (published 2019-02-06); manifiesto `a93306413a38…`. Puesta en marcha: ventanas sanas del ensayo 1 de un perfil (un registro de 10 s) o de los cuatro; radio r_(k) sobre esas ventanas. Sanos de prueba: 8 registros de los ensayos 2 y 3, nunca usados en la puesta en marcha. Fallos: 12 registros por tipo. Persistencia: 8 de 10 ventanas consecutivas. Semilla de los modelos por máquina 0, del OEM 42; 4000 ventanas aumentadas.

- OEM, cociente: 42/100 épocas, mejor val_loss 0,02340.
- OEM, cociente + ganancia: 29/100 épocas, mejor val_loss 0,05397.

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
| por máquina, crudo | 46,6% [42,3–50,9] | no aprende | 19,7% [16,4–23,3] | 28,8% [25,0–32,9] | 11,6% [9,0–14,6] |
| por máquina, crudo + aumento | no aprende | 8,3% [6,1–11,0] | 13,6% [10,8–16,9] | 26,1% [22,4–30,1] | 9,5% [7,1–12,3] |
| por máquina, cociente | 43,7% [39,4–48,0] | no aprende | 14,3% [11,5–17,6] | 25,7% [22,0–29,6] | 8,2% [6,0–10,8] |
| por máquina, cociente + ganancia | 33,1% [29,1–37,2] | 3,9% [2,4–5,9] | 11,0% [8,5–13,9] | 7,6% [5,5–10,2] | 4,8% [3,2–7,0] |
| OEM, cociente | 29,2% [25,4–33,2] | 2,8% [1,6–4,6] | 10,4% [8,0–13,3] | 11,5% [9,0–14,5] | 4,3% [2,7–6,3] |
| OEM, cociente + ganancia | 2,4% [1,3–4,1] | 10,4% [8,0–13,3] | 2,0% [1,0–3,6] | 5,8% [3,9–8,1] | 3,0% [1,7–4,8] |

## Registros sanos de prueba con alarma persistente

| modelo | A-1 (creciente) | B-1 (decreciente) | C-1 (sube y baja) | D-1 (baja y sube) | los cuatro ensayos 1 |
|---|---|---|---|---|---|
| RMS, tiempo (clásico) | 8/8 | 1/8 | 1/8 | 4/8 | 1/8 |
| curtosis, cociente (clásico) | 0/8 | 1/8 | 0/8 | 0/8 | 0/8 |
| por máquina, crudo | 8/8 | no aprende | 3/8 | 5/8 | 2/8 |
| por máquina, crudo + aumento | no aprende | 1/8 | 2/8 | 5/8 | 1/8 |
| por máquina, cociente | 8/8 | no aprende | 3/8 | 4/8 | 1/8 |
| por máquina, cociente + ganancia | 4/8 | 0/8 | 1/8 | 0/8 | 0/8 |
| OEM, cociente | 4/8 | 1/8 | 2/8 | 2/8 | 1/8 |
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
| por máquina, cociente | 0,0% (0/26) | 11,4% (21/185) | 55,9% (143/256) | 100,0% (71/71) |
| por máquina, cociente + ganancia | 69,2% (18/26) | 14,6% (27/185) | 32,8% (84/256) | 69,0% (49/71) |
| OEM, cociente | 0,0% (0/26) | 9,2% (17/185) | 30,9% (79/256) | 85,9% (61/71) |
| OEM, cociente + ganancia | 3,8% (1/26) | 3,8% (7/185) | 1,6% (4/256) | 1,4% (1/71) |

### B-1 (decreciente) (14,1–28,8 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 0,5% (1/211) | 13,2% (30/227) | 9,3% (5/54) |
| curtosis, cociente (clásico) | 3,8% (1/26) | 12,4% (23/185) | 27,0% (69/256) | 18,3% (13/71) |
| por máquina, crudo | — | — | — | — |
| por máquina, crudo + aumento | 0,0% (0/36) | 1,4% (3/211) | 14,5% (33/227) | 14,8% (8/54) |
| por máquina, cociente | — | — | — | — |
| por máquina, cociente + ganancia | 30,8% (8/26) | 4,3% (8/185) | 0,8% (2/256) | 4,2% (3/71) |
| OEM, cociente | 0,0% (0/26) | 0,0% (0/185) | 3,5% (9/256) | 8,5% (6/71) |
| OEM, cociente + ganancia | 7,7% (2/26) | 10,8% (20/185) | 10,9% (28/256) | 8,5% (6/71) |

### C-1 (sube y baja) (14,9–25,2 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 2,4% (5/211) | 14,5% (33/227) | 18,5% (10/54) |
| curtosis, cociente (clásico) | 0,0% (0/26) | 0,5% (1/185) | 0,8% (2/256) | 0,0% (0/71) |
| por máquina, crudo | 0,0% (0/36) | 8,5% (18/211) | 18,9% (43/227) | 79,6% (43/54) |
| por máquina, crudo + aumento | 0,0% (0/36) | 7,1% (15/211) | 15,9% (36/227) | 38,9% (21/54) |
| por máquina, cociente | 0,0% (0/26) | 1,6% (3/185) | 14,1% (36/256) | 53,5% (38/71) |
| por máquina, cociente + ganancia | 26,9% (7/26) | 14,1% (26/185) | 5,1% (13/256) | 18,3% (13/71) |
| OEM, cociente | 0,0% (0/26) | 0,5% (1/185) | 10,9% (28/256) | 38,0% (27/71) |
| OEM, cociente + ganancia | 0,0% (0/26) | 3,2% (6/185) | 1,6% (4/256) | 1,4% (1/71) |

### D-1 (baja y sube) (14,9–24,1 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 8,5% (18/211) | 21,6% (49/227) | 85,2% (46/54) |
| curtosis, cociente (clásico) | 0,0% (0/26) | 1,1% (2/185) | 5,9% (15/256) | 1,4% (1/71) |
| por máquina, crudo | 0,0% (0/36) | 10,0% (21/211) | 33,9% (77/227) | 100,0% (54/54) |
| por máquina, crudo + aumento | 0,0% (0/36) | 10,0% (21/211) | 27,8% (63/227) | 100,0% (54/54) |
| por máquina, cociente | 0,0% (0/26) | 7,6% (14/185) | 21,1% (54/256) | 98,6% (70/71) |
| por máquina, cociente + ganancia | 23,1% (6/26) | 9,2% (17/185) | 4,3% (11/256) | 9,9% (7/71) |
| OEM, cociente | 0,0% (0/26) | 0,5% (1/185) | 12,1% (31/256) | 42,3% (30/71) |
| OEM, cociente + ganancia | 7,7% (2/26) | 7,0% (13/185) | 5,5% (14/256) | 2,8% (2/71) |

### los cuatro ensayos 1 (14,1–28,8 Hz)

| modelo | 10–15 Hz | 15–20 Hz | 20–25 Hz | 25–30 Hz |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 0,0% (0/36) | 2,4% (5/211) | 14,5% (33/227) | 18,5% (10/54) |
| curtosis, cociente (clásico) | 0,0% (0/26) | 2,2% (4/185) | 7,8% (20/256) | 2,8% (2/71) |
| por máquina, crudo | 0,0% (0/36) | 5,2% (11/211) | 15,4% (35/227) | 27,8% (15/54) |
| por máquina, crudo + aumento | 0,0% (0/36) | 3,3% (7/211) | 15,0% (34/227) | 16,7% (9/54) |
| por máquina, cociente | 0,0% (0/26) | 0,0% (0/185) | 11,7% (30/256) | 19,7% (14/71) |
| por máquina, cociente + ganancia | 3,8% (1/26) | 7,6% (14/185) | 2,3% (6/256) | 7,0% (5/71) |
| OEM, cociente | 0,0% (0/26) | 0,0% (0/185) | 5,1% (13/256) | 14,1% (10/71) |
| OEM, cociente + ganancia | 7,7% (2/26) | 4,3% (8/185) | 2,0% (5/256) | 1,4% (1/71) |

## Detección por tipo de fallo

Registros con alarma persistente (de 12) y AUROC ventana a ventana frente a los sanos de prueba (el AUROC no depende del radio).

### Puesta en marcha: A-1 (creciente)

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 12/12; 0,529 | 12/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 12/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | 12/12; 0,998 | 12/12; 0,510 | 12/12; 0,833 | 12/12; 0,996 |
| por máquina, crudo + aumento | — | — | — | — |
| por máquina, cociente | 12/12; 0,998 | 10/12; 0,459 | 12/12; 0,809 | 12/12; 0,996 |
| por máquina, cociente + ganancia | 12/12; 0,994 | 0/12; 0,318 | 12/12; 0,832 | 12/12; 0,990 |
| OEM, cociente | 12/12; 0,997 | 9/12; 0,466 | 12/12; 0,791 | 12/12; 0,994 |
| OEM, cociente + ganancia | 6/12; 0,616 | 10/12; 0,450 | 0/12; 0,476 | 8/12; 0,411 |

### Puesta en marcha: B-1 (decreciente)

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 0/12; 0,529 | 9/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 12/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | — | — | — | — |
| por máquina, crudo + aumento | 12/12; 0,998 | 0/12; 0,530 | 12/12; 0,842 | 12/12; 0,996 |
| por máquina, cociente | — | — | — | — |
| por máquina, cociente + ganancia | 12/12; 0,984 | 0/12; 0,259 | 10/12; 0,880 | 12/12; 0,996 |
| OEM, cociente | 12/12; 0,997 | 0/12; 0,466 | 4/12; 0,791 | 12/12; 0,994 |
| OEM, cociente + ganancia | 10/12; 0,616 | 10/12; 0,450 | 0/12; 0,476 | 9/12; 0,411 |

### Puesta en marcha: C-1 (sube y baja)

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 0/12; 0,529 | 12/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 1/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | 12/12; 0,998 | 8/12; 0,556 | 12/12; 0,839 | 12/12; 0,996 |
| por máquina, crudo + aumento | 12/12; 0,998 | 2/12; 0,569 | 12/12; 0,844 | 12/12; 0,996 |
| por máquina, cociente | 12/12; 0,998 | 2/12; 0,468 | 12/12; 0,812 | 12/12; 0,996 |
| por máquina, cociente + ganancia | 12/12; 0,999 | 0/12; 0,435 | 12/12; 0,864 | 12/12; 0,995 |
| OEM, cociente | 12/12; 0,997 | 1/12; 0,466 | 9/12; 0,791 | 12/12; 0,994 |
| OEM, cociente + ganancia | 4/12; 0,616 | 10/12; 0,450 | 0/12; 0,476 | 8/12; 0,411 |

### Puesta en marcha: D-1 (baja y sube)

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 8/12; 0,529 | 12/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 12/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | 12/12; 0,998 | 10/12; 0,527 | 12/12; 0,830 | 12/12; 0,996 |
| por máquina, crudo + aumento | 12/12; 0,998 | 10/12; 0,519 | 12/12; 0,846 | 12/12; 0,996 |
| por máquina, cociente | 12/12; 0,998 | 6/12; 0,467 | 12/12; 0,810 | 12/12; 0,996 |
| por máquina, cociente + ganancia | 12/12; 1,000 | 0/12; 0,345 | 12/12; 0,848 | 12/12; 0,995 |
| OEM, cociente | 12/12; 0,997 | 1/12; 0,466 | 10/12; 0,791 | 12/12; 0,994 |
| OEM, cociente + ganancia | 9/12; 0,616 | 10/12; 0,450 | 0/12; 0,476 | 9/12; 0,411 |

### Puesta en marcha: los cuatro ensayos 1

| modelo | pista interior | pista exterior | bola | combinado |
|---|---|---|---|---|
| RMS, tiempo (clásico) | 12/12; 0,998 | 0/12; 0,529 | 12/12; 0,830 | 12/12; 0,996 |
| curtosis, cociente (clásico) | 12/12; 0,991 | 12/12; 0,988 | 2/12; 0,507 | 12/12; 1,000 |
| por máquina, crudo | 12/12; 0,998 | 1/12; 0,543 | 12/12; 0,844 | 12/12; 0,996 |
| por máquina, crudo + aumento | 12/12; 0,998 | 0/12; 0,540 | 12/12; 0,844 | 12/12; 0,996 |
| por máquina, cociente | 12/12; 0,998 | 0/12; 0,464 | 8/12; 0,810 | 12/12; 0,996 |
| por máquina, cociente + ganancia | 12/12; 0,999 | 0/12; 0,294 | 12/12; 0,854 | 12/12; 0,995 |
| OEM, cociente | 12/12; 0,997 | 0/12; 0,466 | 6/12; 0,791 | 12/12; 0,994 |
| OEM, cociente + ganancia | 6/12; 0,616 | 10/12; 0,450 | 0/12; 0,476 | 8/12; 0,411 |

## Modelos por máquina: entrenamiento

Ventanas de entrenamiento; varianza no reconstruida (se rechaza solo el colapso, > 0,98); val_loss / train_loss.

| puesta en marcha | modelo | ventanas | no reconstruida | generalización |
|---|---|---|---|---|
| A-1 (creciente) | por máquina, crudo | 66 | 0,86 | 1,57 |
| A-1 (creciente) | por máquina, crudo + aumento | — | colapso | — |
| A-1 (creciente) | por máquina, cociente | 4000 | 0,79 | 1,12 |
| A-1 (creciente) | por máquina, cociente + ganancia | 4000 | 0,78 | 1,11 |
| B-1 (decreciente) | por máquina, crudo | — | colapso | — |
| B-1 (decreciente) | por máquina, crudo + aumento | 4000 | 0,75 | 1,19 |
| B-1 (decreciente) | por máquina, cociente | — | colapso | — |
| B-1 (decreciente) | por máquina, cociente + ganancia | 4000 | 0,80 | 1,12 |
| C-1 (sube y baja) | por máquina, crudo | 66 | 0,73 | 1,52 |
| C-1 (sube y baja) | por máquina, crudo + aumento | 4000 | 0,69 | 1,19 |
| C-1 (sube y baja) | por máquina, cociente | 4000 | 0,83 | 1,10 |
| C-1 (sube y baja) | por máquina, cociente + ganancia | 4000 | 0,82 | 1,09 |
| D-1 (baja y sube) | por máquina, crudo | 66 | 0,90 | 1,17 |
| D-1 (baja y sube) | por máquina, crudo + aumento | 4000 | 0,72 | 1,19 |
| D-1 (baja y sube) | por máquina, cociente | 4000 | 0,82 | 1,11 |
| D-1 (baja y sube) | por máquina, cociente + ganancia | 4000 | 0,81 | 1,11 |
| los cuatro ensayos 1 | por máquina, crudo | 264 | 0,76 | 1,02 |
| los cuatro ensayos 1 | por máquina, crudo + aumento | 4000 | 0,77 | 1,12 |
| los cuatro ensayos 1 | por máquina, cociente | 4000 | 0,82 | 1,12 |
| los cuatro ensayos 1 | por máquina, cociente + ganancia | 4000 | 0,82 | 1,09 |
