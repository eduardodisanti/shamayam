# Protocolo registrado v2: la firma con el cociente completo (banco CWRU → IMS y Ottawa)

*Escrito el 14-oct, antes de implementar y ejecutar nada. Para revisar y aprobar. Se deriva de la definición del cociente ([`07_definicion_cociente.md`](07_definicion_cociente.md)), no del resultado de v1. **v1 ([`06_protocolo_banco.md`](06_protocolo_banco.md)) se mantiene tal como quedó registrado, y el paper informa de las dos.** Cualquier cambio posterior se anota aquí con fecha y motivo.*

## Por qué

v1 mostró que la forma aprendida en el banco no se detecta en otra máquina con un cociente que quita la velocidad y la ganancia pero no la vía de transmisión (AUROC ≈ 0,5 frente a los controles). La definición del cociente dice por qué: lo que mide el sensor es la firma del fenómeno vista a través de la vía de cada máquina, y lo que se comparaba era la vía, no la firma. v2 pone a prueba el cociente completo, que incluye la vía de transmisión.

## Hipótesis

- **H1v2 (la firma se transfiere).** Con el cociente completo (preblanqueo + remuestreo angular + ganancia), el modelo aprendido solo con lo sano del banco detecta en Ottawa los fallos de pista interior, bola y combinado por encima de los controles.
- **H2v2 (opera).** En IMS, con preblanqueo + remuestreo angular, el modelo del banco saca el fallo del bearing 1.
  - El preblanqueo quita la amplitud espectral, energía incluida, así que este es un coste declarado de antemano. Si el fallo de IMS solo se viera por la energía, H2v2 puede no cumplirse, y eso también es informativo.
- **H0.** Ni con el cociente completo se detecta la transferencia con este método.

## La sección (lo único que cambia respecto a v1)

1. **Preblanqueo cepstral, por registro, en el dominio de Hz:** x ↦ IFFT(X / |X|), es decir, la señal con módulo espectral unidad y su fase (Borghesani et al., 2013).
   - No tiene parámetros que ajustar.
   - Quita la vía de transmisión (resonancias, sensor, montaje) y la ganancia, y deja la estructura de fase, que es donde está la firma impulsiva.
   - Se aplica al registro entero antes del remuestreo angular, porque las resonancias están fijas en Hz.
2. **Remuestreo angular,** como hasta ahora:
   - **CWRU:** la velocidad se estima en la señal *sin* blanquear (el blanqueo aplana los armónicos que usa el estimador) y se aplica al registro blanqueado.
   - **IMS:** velocidad nominal.
   - **Ottawa:** encoder.
3. **Variantes:**
   - **w:** sin normalización por ventana.
   - **wg:** con normalización por ventana (quitar la media, dividir por el RMS).
   - **wg es la variante principal para H1v2,** porque es la continuación directa de qg en v1. w es secundaria y es la de H2v2.

El banco, la separación 80/20, el aumento sobre G, la arquitectura, el programa de entrenamiento, el control de colapso y las semillas (42, 0, 1, 2, 3) son exactamente los de v1. El aumento se aplica después de blanquear y proyectar.

## Controles y referencias (todos en la misma sección)

- **C-ruido:** ruido blanco gaussiano con la misma sección. Mismo papel que en v1.
- **C-simulador:** el OEM del simulador reentrenado con ventanas simuladas que pasan por la misma sección (preblanqueo antes del remuestreo angular, con la velocidad simulada conocida). 5 semillas (42, 0, 1, 2, 3). En v1 se reutilizó el ya calculado; aquí se recalcula porque la sección cambia.
- **Techo:** el modelo por máquina en Ottawa con la misma sección wg, puesta en marcha con los cuatro ensayos 1, 5 semillas (0–4). Es *in-sample*, como en v1.
- **Referencias clásicas en el dominio de la firma, sin aprendizaje:**
  - curtosis de la ventana blanqueada (la práctica habitual tras el preblanqueo);
  - indicador de envolvente: pico sobre mediana del espectro de la envolvente al cuadrado de la ventana blanqueada, órdenes 2–20, sin geometría del rodamiento.

## Criterios (idénticos a v1, aplicados a wg)

- **"La firma se transfiere" para un tipo de fallo** si se cumplen las dos:
  1. AUROC medio sobre 5 semillas ≥ 0,80.
  2. En al menos 4 de 5 semillas, el intervalo al 95% (bootstrap de registros, 2000 remuestreos) de la diferencia pareada con C-ruido y con C-simulador queda entero por encima de 0.
- **H1v2 se cumple** si se cumple para al menos dos de pista interior, bola y combinado. La pista exterior se informa pero no entra en el criterio.
- **Comprobación por velocidad:** se repite solo con las ventanas de 15–25 Hz. Si H1v2 se cumple con todas las ventanas pero no en esa banda, el resultado es **no concluyente**.
- **H2v2:** IMS, variante w, n = 99. Salida del bearing 1 ≤ 549 y FAR ≤ 2% en al menos 4 de 5 semillas.
- **Nombres del resultado:** transfiere / evidencia parcial / no se detecta transferencia con este método. Mismas definiciones que en v1.

## Control de aprendizaje, por etapas (como en v1, con una condición nueva)

1. Se entrena y se miran **solo** los diagnósticos del banco antes de puntuar ningún destino.
2. **Condición nueva, fijada ahora:** el preblanqueo deja una señal con espectro plano, parecida al ruido blanco en amplitud. Puede que el autoencoder no logre representar lo sano blanqueado.
   - Si la fracción no reconstruida en la validación del banco supera 0,95 para wg, se anota antes de seguir.
   - En ese caso H1v2 se declara **no evaluable con este autoencoder**, distinto de "no se detecta transferencia".
   - La prueba de la firma recae entonces en las referencias clásicas del mismo dominio, informadas igual pero sin veredicto sobre el autoencoder.

## Lo que no se hará

- No se ajusta nada (forma de blanqueo, bandas, órdenes, aumento, épocas) después de ver IMS u Ottawa.
- No se prueban otras secciones ni otras representaciones (por ejemplo, un autoencoder sobre el espectro de la envolvente) sin un protocolo v3 registrado antes.
- No se evalúa en CWRU.

## Salidas y reproducibilidad

- Código: `bench_transfer.py` con la sección como opción, y `bench_report.py` con los mismos criterios como código. Ambos se suben a git **antes** de la ejecución completa.
- Resultados en `results/bench_v2/`; tablas en `tablas_banco_v2.md`, comprobadas byte a byte; el análisis por *bootstrap* se guarda y un test lo recalcula exactamente.

## Coste estimado

Unos 25 entrenamientos: banco w y wg, C-ruido wg y C-simulador wg con 5 semillas cada uno, más el techo por máquina con 5. A unos 5 min cada uno, ~2,5 h, más la evaluación.

## Consecuencias para el paper según el resultado

- **Se transfiere:** la definición del cociente queda validada en su punto central. El cociente completo hace transferible la firma del fenómeno, y v1 muestra qué pasa cuando falta la vía. Pasaría a ser un resultado principal.
- **Evidencia parcial o no se detecta:** se informa con v1 como límite medido del método. La definición del cociente se mantiene como marco y la transferencia de la firma queda como trabajo futuro.
- **No evaluable con este autoencoder:** se informa como límite de la representación, no del cociente. Las referencias clásicas en el dominio de la firma dicen si la firma está ahí.

## Registro de ejecución

- **14–15-oct, etapa 1 (solo entrenamiento, antes de puntuar ningún destino).**
  - **Banco w y banco wg:** 0 de 5 modelos aprenden cada uno; la fracción no reconstruida en la validación del banco es 1,000 en los diez.
  - **Techo por máquina en Ottawa (wg):** 0 de 5 aprenden.
  - **C-simulador wg:** 2 de 5 aprenden, y apenas (0,97).
  - **C-ruido:** 1,000, como se esperaba.

  Se aplica la condición fijada antes de ejecutar: **H1v2 queda no evaluable con este autoencoder**. El autoencoder de error cuadrático sobre la forma de onda no logra representar la vibración blanqueada, venga del banco, de la propia máquina o del simulador. Es un límite de la representación, no del cociente. Se pasa a la etapa 2 sin cambios para obtener las referencias clásicas y la tabla de IMS.

- **14-oct, etapa 2 (evaluación, sin cambios respecto a lo registrado).** Tablas en [`tablas_banco_v2.md`](tablas_banco_v2.md), generadas por `bench_report_v2.py` y comprobadas byte a byte; el análisis se recalcula exactamente con un test.
  - **H1v2: no evaluable con este autoencoder** (0 de 5 modelos del banco wg aprenden). Es lo que fija la condición previa; no se dice "no se detecta transferencia".
  - **H2v2: no cumple.** El banco w no aprende en ninguna semilla, así que no hay salida del bearing 1. No dice nada sobre si el fallo de IMS se ve en el dominio blanqueado; eso lo dicen las referencias clásicas.
  - **Controles:** C-ruido en azar (AUROC 0,49–0,51 en Ottawa; FAR en IMS 1–2%). C-simulador wg (2 semillas que aprenden) por debajo del azar en Ottawa (0,38–0,49) y sin salida en IMS.
  - **Referencias clásicas en el dominio de la firma (sin aprendizaje, misma regla certificada):**
    - **Ottawa, los cuatro ensayos 1:** la curtosis de la ventana blanqueada separa pista interior 0,963, combinado 0,995 y pista exterior 0,993, pero no la bola (0,466); FAR 5,4%. El indicador de envolvente separa pista interior (0,792) y queda por debajo del azar en combinado (0,305) y pista exterior (0,231); FAR 2,6%. Los valores en la banda de 15–25 Hz son prácticamente iguales.
    - **IMS, bearing 1, n = 99:** curtosis sale en el registro 709 (FAR 0,3%) y envolvente en 704 (FAR 3,7%), frente al 539 de RMS o del autoencoder en q. Es el coste declarado de antemano: el preblanqueo quita la energía, y el primer síntoma de IMS es energético.

  **Lectura (para discutir, no es veredicto del protocolo):**
  - El autoencoder de error cuadrático sobre la forma de onda no representa la vibración blanqueada, ni del banco, ni de la propia máquina, ni del simulador. Es un límite de la representación, no del cociente.
  - En el cociente completo la firma sí está y es detectable sin aprendizaje y con la regla certificada: la curtosis blanqueada separa tres de los cuatro fallos de Ottawa con una puesta en marcha local. Esto apoya la definición del cociente sin decir nada sobre la transferencia de un modelo aprendido.
  - La envolvente por debajo del azar en combinado y pista exterior indica que, en ventanas blanqueadas de 3 vueltas, el pico sobre mediana no es el indicador adecuado para esos fallos. Se informa tal cual; no se ajusta (bandas u órdenes) después de verlo.
  - Probar la transferencia de la firma con un modelo aprendido exigiría otra representación (por ejemplo, un autoencoder sobre el espectro de la envolvente, o sobre otra representación que el modelo pueda reconstruir), bajo un protocolo v3 registrado antes. Decisión pendiente del autor.
