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

## Consecuencias para la escritura

- Las cifras que dependen del entrenamiento concreto del operador (FAR exactas, salidas de los bearings 2–4 de IMS) se citan como rango sobre semillas o con la versión que las produjo, no como valores únicos.
- La salida del bearing 1 en 539 y los veredictos de los protocolos sí se pueden citar como robustos al reentrenamiento y a la plataforma.
- Si se quiere congelar la Tabla 10, hay que guardar los pesos del operador publicado junto con la caché de residuos; la caché ya fija los residuos, pero no el operador.
