# Protocolo registrado v3: la firma con el cociente completo y una representación que el autoencoder pueda reconstruir

*Escrito el 16-oct, antes de implementar y ejecutar nada. Para revisar y aprobar. Responde a la decisión pendiente de D9 y de [`08_protocolo_banco_v2.md`](08_protocolo_banco_v2.md): "probar la transferencia de la firma con un modelo aprendido exigiría otra representación, bajo un protocolo v3 registrado antes". **v1 y v2 se mantienen tal como quedaron registrados; el paper informa de las tres.** Cualquier cambio posterior se anota aquí con fecha y motivo.*

## Por qué

- v2 dejó H1v2 **no evaluable con este autoencoder**: el autoencoder de error cuadrático sobre la forma de onda no reconstruye la vibración blanqueada, venga de donde venga.
- Las referencias clásicas mostraron que la firma **sí está** en el cociente completo (curtosis blanqueada: Ottawa pista interior 0,96, combinado 0,995, exterior 0,99; bola no).
- v3 cambia **solo la representación** que ve el autoencoder: en lugar de la forma de onda blanqueada (casi ruido blanco), el **espectro de la envolvente al cuadrado** de esa misma señal, en órdenes. Es la herramienta diagnóstica habitual tras el preblanqueo (Borghesani et al., 2013; Randall y Antoni, 2011). En una máquina sana es casi plano salvo los armónicos del eje; la firma de un fallo de rodamiento son líneas en sus órdenes característicos.

## Hipótesis

- **H1v3 (la firma se transfiere).** Con el cociente completo y la representación s, el modelo aprendido solo con lo sano del banco CWRU detecta en Ottawa los fallos de pista interior, bola y combinado por encima de los controles.
- **H2v3 (opera en IMS).** En IMS, el modelo del banco en s saca el fallo del bearing 1.
  - Como en v2, el preblanqueo quita la energía, que es el primer síntoma de IMS: es un coste declarado de antemano.
- **H3v3 (opera en XJTU, secundario).** Mismos criterios de "opera" que H1 del protocolo XJTU ([`09_protocolo_xjtu.md`](09_protocolo_xjtu.md)), con el modelo del banco en s.
- **H0.** Ni con esta representación se detecta la transferencia con este método.

## La sección y la representación

1. **Preblanqueo cepstral por registro, en Hz**, y **remuestreo angular**, exactamente como en v2 (CWRU: velocidad estimada en la señal sin blanquear; IMS y XJTU: velocidad nominal; Ottawa: encoder).
2. **Ventanas de 30 vueltas** (12 000 muestras a 400 por vuelta), sin solape. Hace falta una ventana más larga que las 3 vueltas de v1/v2 para resolver órdenes.
   - CWRU sano: unas 9 ventanas por carga y registro (y cualquier inicio para el aumento). IMS: 1 por registro (33 vueltas). XJTU: 1 por registro (45–51 vueltas). Ottawa: varias por registro; la velocidad de la ventana es la media de la de sus muestras.
3. **Representación s** de cada ventana:
   - envolvente al cuadrado |hilbert(x)|² de la ventana entera;
   - su espectro por Welch: segmentos de Hann de 10 vueltas con salto de 5 (5 segmentos), quitando la media de cada uno. Resolución 0,1 órdenes; promediar divide por unas cuatro la varianza de cada bin frente a un periodograma único, que es casi todo ruido en una máquina sana blanqueada;
   - los 1200 bins de los órdenes 0,1 a 120 (sin el término de continua);
   - **s = log(SES / mediana(SES))** en esos bins. La división por la mediana es la sección de ganancia de esta representación; el logaritmo comprime las líneas.
   - 1200 bins es la longitud de entrada de la arquitectura publicada: **no cambia el modelo**.
   - Elegida antes de entrenar nada con ella; no se ha mirado ningún dato del banco ni de los destinos en esta representación.
4. **Aumento** (en el tiempo, antes de la representación, como en v1/v2): cualquier inicio (fase), ganancia U(0,75; 1,25), offset ±0,1 RMS y ruido 0–5% RMS. Con el blanqueo y la mediana, ganancia y offset apenas cambian s; se mantienen por continuidad.

El banco, la separación 80/20, la arquitectura, el programa de entrenamiento, el control de colapso y las semillas (42, 0, 1, 2, 3) son exactamente los de v1 y v2.

## Controles y referencias (todos en la misma sección y representación)

- **C-ruido:** ruido blanco gaussiano con la misma sección y representación.
- **C-simulador:** el simulador (parámetros de Ottawa, como en v2), con registros lo bastante largos para 30 vueltas, preblanqueado antes del remuestreo con su velocidad conocida. 5 semillas.
- **Techo:** modelo por máquina en Ottawa con los cuatro ensayos 1, misma representación, 5 semillas (0–4). *In-sample*, como en v1 y v2.
- **Referencias clásicas, sin aprendizaje, en la misma ventana de 30 vueltas:** curtosis de la ventana blanqueada e indicador de envolvente (pico sobre mediana del SES, órdenes 2–20).

## Criterios (idénticos a v2)

- **"La firma se transfiere" para un tipo de fallo** si se cumplen las dos:
  1. AUROC medio sobre 5 semillas ≥ 0,80.
  2. En al menos 4 de 5 semillas, el intervalo al 95% (bootstrap de registros, 2000 remuestreos) de la diferencia pareada con C-ruido y con C-simulador queda entero por encima de 0.
- **H1v3 se cumple** si se cumple para al menos dos de pista interior, bola y combinado. La pista exterior se informa pero no entra en el criterio.
- **Comprobación por velocidad:** se repite con las ventanas de 15–25 Hz. Si H1v3 se cumple con todas pero no en esa banda, el resultado es **no concluyente**.
- **H2v3:** IMS, n = 99. Salida del bearing 1 ≤ 549 y FAR ≤ 2% en al menos 4 de 5 semillas.
- **H3v3:** como H1 de XJTU, con bench_s.
- **Nombres:** transfiere / evidencia parcial / no se detecta transferencia con este método; mismas definiciones que en v1.

## Control de aprendizaje, por etapas (como en v2)

1. Se entrena y se miran **solo** los diagnósticos del banco antes de puntuar ningún destino.
2. Si la fracción no reconstruida en la validación del banco supera 0,95 para bench_s, H1v3 se declara **no evaluable con este autoencoder**, y la prueba recae en las referencias clásicas.

## Lo que no se hará

- No se ajusta nada (longitud de ventana, banda de órdenes, logaritmo, normalización, épocas) después de ver IMS, Ottawa o XJTU.
- No se usa la geometría de ningún rodamiento.
- No se evalúa en CWRU.
- Si v3 tampoco es evaluable, no hay v4 en este paper: se informa como límite de la representación.

## Salidas

- Código: `bench_transfer_v3.py` y `bench_report_v3.py` (criterios como código), en git **antes** de la ejecución completa. v1 y v2 no se tocan.
- Resultados en `results/bench_v3/`; tablas en `tablas_banco_v3.md`, comprobadas byte a byte.
- Pesos de los modelos en el disco de datos (`shamayam_runs/models/bench_v3`), para que esta vez se conserven.

## Coste estimado

Unos 20 entrenamientos (bench_s, C-ruido y C-simulador con 5 semillas cada uno, y el techo con 5), más la evaluación en IMS, Ottawa y XJTU.

## Registro de ejecución

- **16-oct, etapa 1 (entrenamiento) y etapa 2 (evaluación), sin cambios respecto a lo registrado** (commit `df51e2a`; macOS 27.0.1, TensorFlow 2.21.0). Tablas en [`tablas_banco_v3.md`](tablas_banco_v3.md).
  - **Banco s:** 0 de 5 modelos aprenden (fracción no reconstruida en la validación del banco 0,995–1,008). Se aplica la condición fijada antes: **H1v3 no evaluable con este autoencoder**; H2v3 y H3v3 sin modelo que evaluar.
  - **Controles y techo:** fracción no reconstruida de C-ruido 1,000 (como se esperaba), de C-simulador 0,861–0,877 y del techo por máquina en Ottawa 0,014–0,015.
  - **Referencias clásicas en ventanas de 30 vueltas:** en IMS, curtosis sale en 709 y envolvente en 704 con n = 99, como en v2 con ventanas de 3 vueltas.
  - Como se fijó en "Lo que no se hará", no hay v4 en este paper.
