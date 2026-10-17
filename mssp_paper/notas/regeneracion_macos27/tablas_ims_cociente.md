# IMS: curva de aprendizaje, por máquina frente a OEM en el cociente

*Generado por `reproducibility_package/ims_learning_curve_report.py` desde `results/ims_quotient/learning_curve.json` (`ims_quotient_learning_curve.py`). No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

Puesta en marcha con los n primeros registros (10 min entre registros); radio r_(k) sobre esos n. FAR sobre los registros 200–499 (300 registros, ~50 h de vida sana). Salida: primera persistente (8 de 10) tras la puesta en marcha. Solo el bearing 1 falla. Velocidad nominal (2000 rpm). Una semilla por modelo local (0); por máquina en el cociente con 4000 ventanas aumentadas.

OEM en el cociente: 31/100 épocas, mejor val_loss 0,06214.

## Falsas alarmas en la vida sana

| modelo | n puesta en marcha | bearing 1 (fallo) | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 (~8,2 h) | 1,7% (5/300) | 0,3% (1/300) | 0,0% (0/300) | 9,3% (28/300) |
| por máquina, señal cruda | 99 (~16,5 h) | 19,0% (57/300) | 1,7% (5/300) | 0,0% (0/300) | 7,7% (23/300) |
| por máquina, señal cruda | 149 (~24,8 h) | 9,0% (27/300) | 0,0% (0/300) | 0,0% (0/300) | 7,7% (23/300) |
| por máquina, señal cruda | 200 (~33,3 h) | 6,7% (20/300) | 0,7% (2/300) | 0,0% (0/300) | 4,3% (13/300) |
| por máquina, en el cociente | 49 (~8,2 h) | 0,3% (1/300) | 0,3% (1/300) | no aprende | 1,0% (3/300) |
| por máquina, en el cociente | 99 (~16,5 h) | 0,7% (2/300) | 0,3% (1/300) | 0,0% (0/300) | 2,0% (6/300) |
| por máquina, en el cociente | 149 (~24,8 h) | 2,0% (6/300) | 0,0% (0/300) | 0,0% (0/300) | 2,3% (7/300) |
| por máquina, en el cociente | 200 (~33,3 h) | 2,3% (7/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| OEM en el cociente (simulación) | 49 (~8,2 h) | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 1,0% (3/300) |
| OEM en el cociente (simulación) | 99 (~16,5 h) | 0,7% (2/300) | 0,0% (0/300) | 0,0% (0/300) | 1,0% (3/300) |
| OEM en el cociente (simulación) | 149 (~24,8 h) | 1,0% (3/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| OEM en el cociente (simulación) | 200 (~33,3 h) | 1,3% (4/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| OEM publicado (tiempo) | 49 (~8,2 h) | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| OEM publicado (tiempo) | 99 (~16,5 h) | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 2,0% (6/300) |
| OEM publicado (tiempo) | 149 (~24,8 h) | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 1,3% (4/300) |
| OEM publicado (tiempo) | 200 (~33,3 h) | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 1,3% (4/300) |

## Salida de lo normal (registro y antelación al final)

| modelo | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 | 538 (74,00 h) | 709 (45,50 h) | 896 (14,33 h) | 616 (61,00 h) |
| por máquina, señal cruda | 99 | 527 (75,83 h) | 709 (45,50 h) | 897 (14,17 h) | 616 (61,00 h) |
| por máquina, señal cruda | 149 | 538 (74,00 h) | 709 (45,50 h) | 899 (13,83 h) | 616 (61,00 h) |
| por máquina, señal cruda | 200 | 538 (74,00 h) | 709 (45,50 h) | 897 (14,17 h) | 616 (61,00 h) |
| por máquina, en el cociente | 49 | 538 (74,00 h) | 709 (45,50 h) | no aprende | 657 (54,17 h) |
| por máquina, en el cociente | 99 | 538 (74,00 h) | 709 (45,50 h) | 893 (14,83 h) | 654 (54,67 h) |
| por máquina, en el cociente | 149 | 538 (74,00 h) | 709 (45,50 h) | 897 (14,17 h) | 656 (54,33 h) |
| por máquina, en el cociente | 200 | 538 (74,00 h) | 709 (45,50 h) | 896 (14,33 h) | 657 (54,17 h) |
| OEM en el cociente (simulación) | 49 | 539 (73,83 h) | 709 (45,50 h) | 882 (16,67 h) | 661 (53,50 h) |
| OEM en el cociente (simulación) | 99 | 538 (74,00 h) | 709 (45,50 h) | 881 (16,83 h) | 661 (53,50 h) |
| OEM en el cociente (simulación) | 149 | 538 (74,00 h) | 709 (45,50 h) | 881 (16,83 h) | 657 (54,17 h) |
| OEM en el cociente (simulación) | 200 | 538 (74,00 h) | 709 (45,50 h) | 881 (16,83 h) | 657 (54,17 h) |
| OEM publicado (tiempo) | 49 | 539 (73,83 h) | 711 (45,17 h) | 899 (13,83 h) | 664 (53,00 h) |
| OEM publicado (tiempo) | 99 | 539 (73,83 h) | 734 (41,33 h) | 898 (14,00 h) | 664 (53,00 h) |
| OEM publicado (tiempo) | 149 | 539 (73,83 h) | 734 (41,33 h) | 898 (14,00 h) | 664 (53,00 h) |
| OEM publicado (tiempo) | 200 | 539 (73,83 h) | 712 (45,00 h) | 894 (14,67 h) | 666 (52,67 h) |

## Modelos por máquina: varianza no reconstruida en entrenamiento

La vibración de IMS es casi ruido de banda ancha: un autoencoder por máquina reconstruye solo parte de la varianza. Se rechaza solo el colapso (> 0,98, equivalente a predecir una constante).

| modelo | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 | 0,72 | 0,64 | 0,68 | 0,54 |
| por máquina, señal cruda | 99 | 0,63 | 0,62 | 0,82 | 0,68 |
| por máquina, señal cruda | 149 | 0,69 | 0,63 | 0,83 | 0,72 |
| por máquina, señal cruda | 200 | 0,69 | 0,63 | 0,84 | 0,74 |
| por máquina, en el cociente | 49 | 0,69 | 0,60 | — | 0,74 |
| por máquina, en el cociente | 99 | 0,69 | 0,59 | 0,81 | 0,72 |
| por máquina, en el cociente | 149 | 0,68 | 0,60 | 0,81 | 0,73 |
| por máquina, en el cociente | 200 | 0,69 | 0,61 | 0,81 | 0,76 |

## Generalización de los modelos por máquina (val_loss / train_loss)

| modelo | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 | 1,13 | 1,20 | 1,34 | 1,63 |
| por máquina, señal cruda | 99 | 1,25 | 1,20 | 1,08 | 1,25 |
| por máquina, señal cruda | 149 | 1,14 | 1,17 | 1,06 | 1,16 |
| por máquina, señal cruda | 200 | 1,12 | 1,15 | 1,02 | 1,14 |
| por máquina, en el cociente | 49 | 1,13 | 1,15 | — | 1,14 |
| por máquina, en el cociente | 99 | 1,12 | 1,16 | 1,09 | 1,20 |
| por máquina, en el cociente | 149 | 1,14 | 1,16 | 1,11 | 1,18 |
| por máquina, en el cociente | 200 | 1,13 | 1,13 | 1,09 | 1,13 |

## Variabilidad entre semillas

Misma configuración; cada modelo se reentrena con cada semilla. Por máquina: semillas 0 (tabla anterior) y 1, 2, 3, 4, bearings 1, 4. OEM en el cociente: semillas 42 (tabla anterior) y 0, 1, 2, 3, los cuatro bearings. Media y rango de la FAR en los registros 200–499; entre paréntesis, entrenamientos que colapsaron.

| modelo | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 | 9,1% [1,7–23,3] | — | — | 9,3% [7,3–11,0] |
| por máquina, señal cruda | 99 | 18,0% [17,3–19,0] | — | — | 6,9% [6,7–7,7] |
| por máquina, señal cruda | 149 | 8,6% [4,3–13,3] | — | — | 7,3% [6,0–7,7] |
| por máquina, señal cruda | 200 | 4,5% [3,7–6,7] | — | — | 4,7% [4,0–5,7] |
| por máquina, en el cociente | 49 | 0,6% [0,3–0,7] | — | — | 1,5% [1,0–2,7] |
| por máquina, en el cociente | 99 | 1,2% [0,7–2,7] | — | — | 1,7% [0,7–3,7] |
| por máquina, en el cociente | 149 | 1,6% [1,0–2,0] | — | — | 1,8% [1,3–2,3] |
| por máquina, en el cociente | 200 | 1,6% [1,0–2,3] | — | — | 1,7% [1,3–2,0] |
| OEM en el cociente (simulación) | 49 | 0,3% [0,0–0,7] | 0,0% [0,0–0,0] | 0,0% [0,0–0,0] | 1,7% [1,0–2,7] |
| OEM en el cociente (simulación) | 99 | 0,5% [0,0–1,0] | 0,0% [0,0–0,0] | 0,0% [0,0–0,0] | 1,7% [1,0–2,7] |
| OEM en el cociente (simulación) | 149 | 0,9% [0,7–1,3] | 0,0% [0,0–0,0] | 0,0% [0,0–0,0] | 2,5% [1,7–3,7] |
| OEM en el cociente (simulación) | 200 | 1,3% [0,7–1,7] | 0,0% [0,0–0,0] | 0,0% [0,0–0,0] | 2,0% [1,3–3,0] |

### Salida del bearing 1 (fallo) por semilla

| modelo | n | registro de salida (rango) | semillas |
|---|---|---|---|
| por máquina, señal cruda | 49 | 527–538 | 5 |
| por máquina, señal cruda | 99 | 527–536 | 5 |
| por máquina, señal cruda | 149 | 532–538 | 5 |
| por máquina, señal cruda | 200 | 538–538 | 5 |
| por máquina, en el cociente | 49 | 538–538 | 5 |
| por máquina, en el cociente | 99 | 538–538 | 5 |
| por máquina, en el cociente | 149 | 538–538 | 5 |
| por máquina, en el cociente | 200 | 538–538 | 5 |
| OEM en el cociente (simulación) | 49 | 538–539 | 5 |
| OEM en el cociente (simulación) | 99 | 538–539 | 5 |
| OEM en el cociente (simulación) | 149 | 538–539 | 5 |
| OEM en el cociente (simulación) | 200 | 538–539 | 5 |
