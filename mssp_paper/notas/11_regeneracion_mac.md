# Regeneración completa en el Mac (B): qué se reproduce y qué no

*16–17-oct-2026. Clon del commit de registro `df51e2a` en SAMSUNG-1, todos los scripts del paquete ejecutados desde cero en el orden documentado. Entorno: Python 3.12.15, macOS 27.0.1 arm64, numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, TensorFlow 2.21.0. Lo publicado se generó con otras versiones: la capa A en macOS 26.5.2 con Python 3.12.13 y numpy 2.1.3, y parte de la capa B (banco v1 y v2, entre otros) en un contenedor Linux.*

*Los resultados regenerados están en `reproducibility_package/results_regen/macos27_tf221/` (sin los pesos `.keras`) y las tablas de notas regeneradas en [`regeneracion_macos27/`](regeneracion_macos27/). Lo publicado no se ha tocado. `git_status_y_diff.txt` lista todos los ficheros que cambiaron.*

## Lo que se reproduce

- **Capa A1 (sin entrenamiento): idéntica byte a byte** en `layer_a_results.txt` (todas las líneas hasta la demostración A2). Las garantías de calibración no dependen de la plataforma.
- **Veredictos de los protocolos del banco:** v1 "opera" (H2) y "no se detecta transferencia con este método" (H1); v2 "no cumple" (H2v2) y "no evaluable con este autoencoder" (H1v2). Iguales.
- **Ley de contaminación n − k:** los recuentos de contaminación tolerada son idénticos; solo cambian en el segundo decimal los radios relativos.
- **IMS, bearing 1:** sale en el **registro 539 (73,83 h)** con todos los radios y todos los brazos que lo sacaban, también con el operador reentrenado.
- **IMS, curva de aprendizaje:** misma lectura. El por máquina en crudo sigue sin alcanzar al OEM; el cociente local y el OEM en el cociente quedan en 0–2% de FAR.
- **CWRU:** el OEM con radio certificado sigue en el punto de operación del específico (detección del 100% en todas las condiciones). La ablación G0–G4 da la misma lectura: el salto está en la fase.
- **Ottawa:** los AUROC quedan prácticamente iguales (diferencias ≤ 0,02, salvo una de 0,09 en la bola, que está cerca de 0,5 en ambos casos) y la lectura por escenario no cambia: la ganancia completa en G hace operar al OEM y le quita la detección de forma. Las FAR del OEM en el cociente, entrenado con una sola semilla en el escenario principal, cambian más: hasta 9 puntos en un escenario (11,5% → 20,1%) y 22 puntos en la banda de velocidad más alta (42,3% → 64,8%). Por eso las cifras del apéndice de velocidad deben ir siempre sobre 5 semillas.

## Lo que no se reproduce (y no debe sostener el texto)

| Afirmación publicada | Publicado | Regenerado | Lectura |
|---|---|---|---|
| IMS bearing 1: 0 falsas alarmas en los sanos tras la puesta en marcha | 0/151, 0/101, 0/51 | 4/151, 1/101, 2/51 (r₍ₖ₎ con n = 49 / 99 / 149) | Depende del entrenamiento concreto del operador; la salida en 539 no |
| IMS bearing 2: salida | 794 (31,3 h) | 709–734 (41–45 h) | Antelación mayor con el operador reentrenado |
| A2: el entrenamiento converge por parada temprana | 372/500 épocas | 500/500, sin converger | TensorFlow 2.21; el aviso del propio script lo marca |
| A2: FAR sana certificada | 2,2% | 3,4% | Mismo orden; nominal 2% |
| Tabla 10 del manuscrito (radios y antelaciones exactos) | — | no idénticos | Los cuatro tests de la Tabla 10 fallan por eso; el test de 1 época falla con TF 2.21 en cualquier plataforma |

## Corrección del orden de la regeneración (18-oct)

El lanzador ejecutó `make_tables.py`, `make_figures.py` y `make_macros.py` justo después de `run_all.py`, **antes** de regenerar `stability.json` y la caché de IMS. Las tablas `stability.tex` y `nasa.tex` y las macros de IMS de la primera pasada salían, por tanto, de los resultados publicados. Se han vuelto a generar desde los resultados regenerados (sin entrenar nada) y sustituyen a las anteriores en `results_regen/macos27_tf221/tables/`. Las figuras no se han vuelto a generar.

## Qué cambia en el texto del manuscrito (`mssp_draft.tex`, numeración de líneas al 18-oct)

**Cifras escritas a mano que vienen de un único entrenamiento y no se reproducen** (no son macros, así que no se actualizan solas; el README dice que todo número del texto es generado, y estas líneas no lo cumplen):

| Líneas | Qué dice | Publicado | Regenerado |
|---|---|---|---|
| 2122–2125 | épocas, mejor época, reducciones del *learning rate* del operador A2 | 372/500, época 347, 9 reducciones | 500/500 (presupuesto agotado), época 500, 7 reducciones |
| 2136–2140 | medianas del residuo: sano / bola / exterior / interior | 2,32·10⁻³ / 6,88·10⁻³ / 1,08·10⁻² / 1,73·10⁻² | 2,25·10⁻³ / 6,69·10⁻³ / 1,04·10⁻² / 1,66·10⁻² |
| 2139 | detección de la bola (escrito a mano, aunque existe la macro `\etoeDetectLo`) | 91,5% | 94,5% |
| 2144–2146 | radios de los cuatro activos simulados y su dispersión | 8,26·10⁻³ a 2,45·10⁻²; 2,97 | 7,42·10⁻³ a 2,11·10⁻²; 2,84 |

**Cifras del estudio de semillas** (párrafos tras `\input{tables/stability}`):

| Líneas | Qué dice | Publicado | Regenerado |
|---|---|---|---|
| 2640 | el radio se mueve con la semilla | 4,4–6,6% | 4,6–10,8% |
| 2645 | contribución del estimador | 0,5–1,2% | 0,5–1,2% (se reproduce) |
| 2659 | dispersión normalizada por la mediana temprana | 0,7–1,2% | 0,3–0,6% |
| 2663 | n = 49 en *x* de 20 combinaciones | el texto dice 17; **los resultados publicados dan 16** | 18 |
| 2664–2665 | antelación del bearing 1 sobre semillas | 74,2–74,3 h | 74,2–74,3 h (se reproduce) |
| 2666 | diferencia de radios entre operadores | 5,7% | 7,4% |

La línea 2663 tiene además una discrepancia **previa**: con los resultados publicados (`results/stability.json`), n = 49 aparece en 16 de las 20 combinaciones, no en 17.

**Tabla `nasa` (operador publicado, parada adaptativa):** el bearing 2 pasa de n = 54 y 31,33 h a n = 49 y 45,50 h; la antelación media de 43,0 a 46,6 h (macro `\nasaLeadMean`). El *highlight* de la línea 135 ("14–74 h") sigue valiendo (regenerado 14,0–73,8 h).

**Notas (no van al paper tal cual, pero de ellas sale el texto):** `03_resultados_ims.md` afirma 0 falsas alarmas en los sanos tras la puesta en marcha del bearing 1 (0/151, 0/101, 0/51) y que el bearing 4 tiene 2 falsas alarmas con r₍ₖ₎; con el operador reentrenado son 4/151, 1/101, 2/51 en el bearing 1 y 6/151, 6/101, 3/51 en el bearing 4.

## Consecuencias para la escritura

- Las cifras que dependen del entrenamiento concreto del operador (FAR exactas, salidas de los bearings 2–4 de IMS) se citan como rango sobre semillas o con la versión que las produjo, no como valores únicos.
- La salida del bearing 1 en 539 y los veredictos de los protocolos sí se pueden citar como robustos al reentrenamiento y a la plataforma.
- Si se quiere congelar la Tabla 10, hay que guardar los pesos del operador publicado junto con la caché de residuos; la caché ya fija los residuos, pero no el operador.

## Referencia en CPU (19-oct, D15)

Desde el 19-oct la referencia del paper es la ejecución en CPU, no la publicada. La publicada entrenó A2 y el operador de IMS en GPU Metal (TF 2.16–2.19), donde `enable_op_determinism` no garantiza nada; en el Mac solo la CPU es determinista.

- **Ejecución:** `launchers/ref_cpu.command` en `999593e`. TensorFlow sin GPU visible; test de determinismo en CPU superado antes de entrenar (dos entrenamientos con la misma semilla dan historial y residuos idénticos). A2 con presupuesto de 5000 épocas: **converge por parada temprana en 585** (mejor época 545, 12 reducciones del learning rate). La capa B es la de la regeneración en CPU de esta nota.
- **A1 idéntica byte a byte** a la publicada. Las 8 tablas del paper y las 9 tablas de notas generadas aquí son idénticas a las generadas en el Mac.
- **Por qué cambian las cifras:** dispositivo, versión de TF/Keras y de numpy/BLAS, y el número de épocas producen otro operador entrenado, como otra semilla. Lo que no depende del entrenamiento concreto no se mueve (A1, veredictos, salida del bearing 1 en 539). Lo que depende de un solo operador cambia lo que cambia entre semillas (en CPU, la ejecución principal de IMS cae dentro del rango de sus propias semillas). Lo que se calcula sobre 5 semillas es ruidoso por sí mismo (una desviación típica de 5 valores tiene un intervalo del 95% de 0,6 a 2,9 veces el valor). Los cocientes de residuos del PCA son cocientes de ceros numéricos y cambian con BLAS.
- **Lo publicado** se guarda en `reproducibility_package/results_published_metal/` (nada lee de ahí). La tabla de diferencias va al apéndice y al repo (decidido 18-oct).
- **Texto:** cifras de A2 (deriva, adecuación, FAR), del estudio de semillas y sus repeticiones (highlights, introducción, resumen) pasan a macros. Las de §9.3 CWRU y la puesta en marcha permutada de §9.4 son del pipeline anterior (ningún script del paquete las produce): marcadas en el `.tex` como `PRE-D15 NUMBERS`, se sustituyen al reescribir esas secciones.

## Determinismo a escala completa y pesos de referencia (19-oct, D17)

`launchers/ref_cpu_weights.command` en `2a2398a` reentrenó en CPU los dos operadores de los que salen las cifras del paper (A2 hasta converger y el operador compartido de IMS) y comparó con lo guardado: **`data.json`, el fichero de resultados y la caché de IMS salen idénticos** (SHA-256 de los residuos `4ccfd394…` en los dos). El entrenamiento en CPU es determinista a escala completa, no solo en el test de 2 épocas. Informe y huellas en `reproducibility_package/results_regen/determinism_fullscale/`; los pesos (unos 10 MB por operador) están en `SAMSUNG-1/shamayam_runs/weights_reference/`, pendientes de subir a una release.
