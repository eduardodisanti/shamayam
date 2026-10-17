# IMS: indicadores clásicos con la misma calibración local

*Generado por `reproducibility_package/extra_reports.py` desde `results/ims_classical/results.json` (`ims_classical_features.py`). No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

Sin entrenamiento: un valor por registro de 1 s (dominio temporal, banda completa, 20 kHz). Radio r_(k) sobre los n primeros registros; FAR sobre los registros 200–499; salida: primera persistente (8 de 10). La envolvente no usa la geometría del rodamiento: pico sobre mediana del espectro de la envolvente en los órdenes 2–20. Solo el bearing 1 falla.

## Falsas alarmas en la vida sana

| indicador | n | bearing 1 (fallo) | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| OEM publicado (autoencoder, referencia) | 49 | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| OEM publicado (autoencoder, referencia) | 99 | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 2,0% (6/300) |
| OEM publicado (autoencoder, referencia) | 149 | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 1,3% (4/300) |
| OEM publicado (autoencoder, referencia) | 200 | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 1,3% (4/300) |
| RMS | 49 | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| RMS | 99 | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| RMS | 149 | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| RMS | 200 | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 1,7% (5/300) |
| curtosis | 49 | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) |
| curtosis | 99 | 0,7% (2/300) | 0,0% (0/300) | 0,0% (0/300) | 0,3% (1/300) |
| curtosis | 149 | 1,0% (3/300) | 0,0% (0/300) | 0,0% (0/300) | 0,3% (1/300) |
| curtosis | 200 | 1,0% (3/300) | 0,3% (1/300) | 0,0% (0/300) | 0,3% (1/300) |
| factor de cresta | 49 | 0,0% (0/300) | 0,3% (1/300) | 4,3% (13/300) | 0,0% (0/300) |
| factor de cresta | 99 | 1,7% (5/300) | 0,0% (0/300) | 0,3% (1/300) | 0,0% (0/300) |
| factor de cresta | 149 | 1,7% (5/300) | 0,3% (1/300) | 0,3% (1/300) | 0,0% (0/300) |
| factor de cresta | 200 | 1,7% (5/300) | 0,7% (2/300) | 0,3% (1/300) | 0,3% (1/300) |
| envolvente (pico/mediana, órdenes 2–20) | 49 | 0,3% (1/300) | 0,0% (0/300) | 0,0% (0/300) | 0,0% (0/300) |
| envolvente (pico/mediana, órdenes 2–20) | 99 | 0,3% (1/300) | 1,0% (3/300) | 0,0% (0/300) | 2,3% (7/300) |
| envolvente (pico/mediana, órdenes 2–20) | 149 | 0,3% (1/300) | 1,0% (3/300) | 0,0% (0/300) | 3,7% (11/300) |
| envolvente (pico/mediana, órdenes 2–20) | 200 | 0,3% (1/300) | 1,0% (3/300) | 1,3% (4/300) | 3,7% (11/300) |

## Salida de lo normal (registro y antelación al final)

| indicador | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| OEM publicado (autoencoder, referencia) | 49 | 539 (73,83 h) | 711 (45,17 h) | 899 (13,83 h) | 664 (53,00 h) |
| OEM publicado (autoencoder, referencia) | 99 | 539 (73,83 h) | 734 (41,33 h) | 898 (14,00 h) | 664 (53,00 h) |
| OEM publicado (autoencoder, referencia) | 149 | 539 (73,83 h) | 734 (41,33 h) | 898 (14,00 h) | 664 (53,00 h) |
| OEM publicado (autoencoder, referencia) | 200 | 539 (73,83 h) | 712 (45,00 h) | 894 (14,67 h) | 666 (52,67 h) |
| RMS | 49 | 539 (73,83 h) | 782 (33,33 h) | 894 (14,67 h) | 619 (60,50 h) |
| RMS | 99 | 539 (73,83 h) | 782 (33,33 h) | 894 (14,67 h) | 619 (60,50 h) |
| RMS | 149 | 539 (73,83 h) | 710 (45,33 h) | 894 (14,67 h) | 619 (60,50 h) |
| RMS | 200 | 539 (73,83 h) | 710 (45,33 h) | 894 (14,67 h) | 619 (60,50 h) |
| curtosis | 49 | 708 (45,67 h) | sin salida | sin salida | sin salida |
| curtosis | 99 | 654 (54,67 h) | sin salida | sin salida | 939 (7,17 h) |
| curtosis | 149 | 654 (54,67 h) | sin salida | sin salida | 925 (9,50 h) |
| curtosis | 200 | 654 (54,67 h) | sin salida | sin salida | 925 (9,50 h) |
| factor de cresta | 49 | sin salida | sin salida | sin salida | sin salida |
| factor de cresta | 99 | 977 (0,83 h) | sin salida | sin salida | sin salida |
| factor de cresta | 149 | 977 (0,83 h) | sin salida | sin salida | sin salida |
| factor de cresta | 200 | 977 (0,83 h) | sin salida | sin salida | sin salida |
| envolvente (pico/mediana, órdenes 2–20) | 49 | 539 (73,83 h) | 899 (13,83 h) | 882 (16,67 h) | 707 (45,83 h) |
| envolvente (pico/mediana, órdenes 2–20) | 99 | 539 (73,83 h) | 895 (14,50 h) | 879 (17,17 h) | 706 (46,00 h) |
| envolvente (pico/mediana, órdenes 2–20) | 149 | 539 (73,83 h) | 895 (14,50 h) | 879 (17,17 h) | 706 (46,00 h) |
| envolvente (pico/mediana, órdenes 2–20) | 200 | 539 (73,83 h) | 895 (14,50 h) | 877 (17,50 h) | 706 (46,00 h) |
