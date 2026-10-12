# IMS: curva de aprendizaje, por máquina frente a OEM en el cociente

*Generado por `reproducibility_package/ims_learning_curve_report.py` desde `results/ims_quotient/learning_curve.json` (`ims_quotient_learning_curve.py`). No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

Puesta en marcha con los n primeros registros (10 min entre registros); radio r_(k) sobre esos n. FAR sobre los registros 200–499 (300 registros, ~50 h de vida sana). Salida: primera persistente (8 de 10) tras la puesta en marcha. Solo el bearing 1 falla. Velocidad nominal (2000 rpm). Una semilla por modelo local (0); por máquina en el cociente con 4000 ventanas aumentadas.

OEM en el cociente: 30/100 épocas, mejor val_loss 0,06227.

## Falsas alarmas en la vida sana

| modelo | n puesta en marcha | bearing 1 (fallo) | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 (~8,2 h) | 1,7% (5/300) | 0,3% (1/300) | 0,0% (0/300) | 7,7% (23/300) |
| por máquina, señal cruda | 99 (~16,5 h) | 19,0% (57/300) | 1,7% (5/300) | 0,0% (0/300) | 8,0% (24/300) |
| por máquina, señal cruda | 149 (~24,8 h) | 9,3% (28/300) | 0,0% (0/300) | 0,0% (0/300) | 8,0% (24/300) |
| por máquina, señal cruda | 200 (~33,3 h) | 11,7% (35/300) | 0,3% (1/300) | 0,0% (0/300) | 6,0% (18/300) |
| por máquina, en el cociente | 49 (~8,2 h) | 0,3% (1/300) | 0,3% (1/300) | no aprende | 1,0% (3/300) |
| por máquina, en el cociente | 99 (~16,5 h) | 1,0% (3/300) | 0,0% (0/300) | 0,0% (0/300) | 3,0% (9/300) |
| por máquina, en el cociente | 149 (~24,8 h) | 1,7% (5/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| por máquina, en el cociente | 200 (~33,3 h) | 2,0% (6/300) | 0,0% (0/300) | 0,0% (0/300) | 2,0% (6/300) |
| OEM en el cociente (simulación) | 49 (~8,2 h) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 1,0% (3/300) |
| OEM en el cociente (simulación) | 99 (~16,5 h) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 2,0% (6/300) |
| OEM en el cociente (simulación) | 149 (~24,8 h) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 2,0% (6/300) |
| OEM en el cociente (simulación) | 200 (~33,3 h) | 1,3% (4/300) | 0,0% (0/300) | 0,0% (0/300) | 2,0% (6/300) |
| OEM publicado (tiempo) | 49 (~8,2 h) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) |
| OEM publicado (tiempo) | 99 (~16,5 h) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 1,0% (3/300) |
| OEM publicado (tiempo) | 149 (~24,8 h) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 1,0% (3/300) |
| OEM publicado (tiempo) | 200 (~33,3 h) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 1,0% (3/300) |

## Salida de lo normal (registro y antelación al final)

| modelo | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 | 538 (74,00 h) | 709 (45,50 h) | 896 (14,33 h) | 616 (61,00 h) |
| por máquina, señal cruda | 99 | 527 (75,83 h) | 709 (45,50 h) | 898 (14,00 h) | 616 (61,00 h) |
| por máquina, señal cruda | 149 | 538 (74,00 h) | 709 (45,50 h) | 899 (13,83 h) | 616 (61,00 h) |
| por máquina, señal cruda | 200 | 538 (74,00 h) | 709 (45,50 h) | 897 (14,17 h) | 616 (61,00 h) |
| por máquina, en el cociente | 49 | 539 (73,83 h) | 709 (45,50 h) | no aprende | 657 (54,17 h) |
| por máquina, en el cociente | 99 | 538 (74,00 h) | 709 (45,50 h) | 888 (15,67 h) | 619 (60,50 h) |
| por máquina, en el cociente | 149 | 538 (74,00 h) | 709 (45,50 h) | 897 (14,17 h) | 657 (54,17 h) |
| por máquina, en el cociente | 200 | 538 (74,00 h) | 709 (45,50 h) | 896 (14,33 h) | 656 (54,33 h) |
| OEM en el cociente (simulación) | 49 | 539 (73,83 h) | 709 (45,50 h) | 882 (16,67 h) | 661 (53,50 h) |
| OEM en el cociente (simulación) | 99 | 539 (73,83 h) | 709 (45,50 h) | 882 (16,67 h) | 661 (53,50 h) |
| OEM en el cociente (simulación) | 149 | 538 (74,00 h) | 709 (45,50 h) | 881 (16,83 h) | 661 (53,50 h) |
| OEM en el cociente (simulación) | 200 | 538 (74,00 h) | 709 (45,50 h) | 881 (16,83 h) | 661 (53,50 h) |
| OEM publicado (tiempo) | 49 | 539 (73,83 h) | 794 (31,33 h) | 896 (14,33 h) | 705 (46,17 h) |
| OEM publicado (tiempo) | 99 | 539 (73,83 h) | 794 (31,33 h) | 896 (14,33 h) | 667 (52,50 h) |
| OEM publicado (tiempo) | 149 | 539 (73,83 h) | 791 (31,83 h) | 892 (15,00 h) | 667 (52,50 h) |
| OEM publicado (tiempo) | 200 | 539 (73,83 h) | 720 (43,67 h) | 892 (15,00 h) | 667 (52,50 h) |

## Modelos por máquina: varianza no reconstruida en entrenamiento

La vibración de IMS es casi ruido de banda ancha: un autoencoder por máquina reconstruye solo parte de la varianza. Se rechaza solo el colapso (> 0,98, equivalente a predecir una constante).

| modelo | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 | 0,73 | 0,63 | 0,70 | 0,55 |
| por máquina, señal cruda | 99 | 0,64 | 0,63 | 0,82 | 0,69 |
| por máquina, señal cruda | 149 | 0,69 | 0,62 | 0,83 | 0,73 |
| por máquina, señal cruda | 200 | 0,69 | 0,64 | 0,84 | 0,71 |
| por máquina, en el cociente | 49 | 0,70 | 0,59 | — | 0,76 |
| por máquina, en el cociente | 99 | 0,69 | 0,60 | 0,81 | 0,72 |
| por máquina, en el cociente | 149 | 0,69 | 0,60 | 0,81 | 0,75 |
| por máquina, en el cociente | 200 | 0,69 | 0,60 | 0,82 | 0,76 |

## Generalización de los modelos por máquina (val_loss / train_loss)

| modelo | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| por máquina, señal cruda | 49 | 1,13 | 1,20 | 1,31 | 1,59 |
| por máquina, señal cruda | 99 | 1,25 | 1,20 | 1,08 | 1,25 |
| por máquina, señal cruda | 149 | 1,14 | 1,19 | 1,07 | 1,14 |
| por máquina, señal cruda | 200 | 1,13 | 1,14 | 1,02 | 1,18 |
| por máquina, en el cociente | 49 | 1,12 | 1,16 | — | 1,11 |
| por máquina, en el cociente | 99 | 1,11 | 1,15 | 1,10 | 1,20 |
| por máquina, en el cociente | 149 | 1,12 | 1,15 | 1,11 | 1,15 |
| por máquina, en el cociente | 200 | 1,12 | 1,14 | 1,08 | 1,13 |
