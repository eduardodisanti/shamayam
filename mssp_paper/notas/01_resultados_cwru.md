# CWRU tras corregir la frecuencia de muestreo: resultados

*Rama `mssp`, 11-oct-2026. Todas las tablas están en [`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md), generadas por `cwru_projection_report.py` desde `results/cwru_projection/` (`results.json`, `scores.npz`, `asset_reference.json`). `tests/test_generated_notes.py` comprueba que coinciden byte a byte con lo que regenera el script. Esta nota no contiene tablas de resultados: las cifras del texto resumen esas tablas y, si alguna difiere, mandan las tablas.*

> Los rodamientos son **solo validación**: el paper es de método (modelo estilo OEM + calibración local, sin datos ni etiquetas del activo) y CWRU/IMS son el banco donde se comprueba que es posible.

## Resultado principal: viabilidad

En la configuración corregida (B), el modelo compartido entrenado **solo con simulación** y con el radio calibrado localmente llega al **mismo punto de operación** que un autoencoder específico entrenado con las sanas de cada condición (la referencia de la Tabla 7 publicada, rehecha con los datos corregidos):

→ Tabla **"Viabilidad: modelo compartido (OEM) frente a modelo específico del activo"** en [`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md). En las cuatro condiciones: misma FAR (2,00–2,08%), detección del 100% en las tres familias de fallo y AUROC 1,000 en ambos.

**Cómo leerlo honestamente:**
- **La igualdad de FAR es aritmética.** Los dos fijan el umbral en el p98 de las mismas n sanas, así que dejan fuera el mismo número de ventanas. Lo que se compara de verdad es la detección (100% en ambos) y la separación sin umbral (AUROC 1,000 en ambos).
- **La referencia está favorecida:** entrena y umbraliza con las mismas ventanas, con memorización (val/train = 1,40–2,34).
- **Con el radio certificado sobre las 49 primeras sanas,** el modelo OEM mantiene el 100% de detección y da FAR del 0–8,5% en las sanas siguientes. La incertidumbre es grande (sección 5).
- **CWRU es un caso fácil:** cualquier modelo de energía llega ahí (sección 2). Demuestra viabilidad, no dificultad. La viabilidad en un caso exigente ya está en IMS (Tabla 10 del manuscrito), ahora recalibrada con radios certificados: ver [`tablas_ims_certificado.md`](tablas_ims_certificado.md).

## Con los mismos datos limitados (49 ventanas sanas)

Un activo nuevo no tiene historial. La alternativa realista al modelo OEM es un modelo específico entrenado con lo que da la puesta en marcha. Los dos reciben exactamente las mismas 49 primeras ventanas sanas de cada condición, y la FAR se mide en las sanas posteriores, que ninguno vio.

→ Tabla **"Igualdad de datos: 49 ventanas sanas para ambos"** en [`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md).

**Lo que se ve:**
- **Detección:** 100% en los dos, en todas las condiciones y semillas.
- **Falsas alarmas en sanas no vistas:** el OEM queda en el 0–8,5%; el específico, entre el 2% y el 57% según condición y semilla (a 1730 rpm, 23–57%). A 1797 no quedan sanas para medir.
- **Entrenamiento:** a 1772 rpm, una de las cinco semillas del específico no llega a aprender.

**Por qué:**
- El modelo específico tiene que calibrar el radio con las mismas ventanas con las que se entrenó. Las memoriza (val/train de 1,28 a 4,85), así que sus residuos de calibración salen más bajos que los de las ventanas nuevas y el radio queda corto.
- Es exactamente la condición que la Proposición 7 exige y que aquí se rompe: los residuos de calibración tienen que ser intercambiables con los futuros.
- El OEM la cumple por construcción. Se entrena con simulación y nunca vio esas ventanas, así que sus residuos de calibración son tan "nuevos" como los que vendrán.
- Para cumplirla, el específico tendría que repartir las 49 ventanas entre entrenar y calibrar. Así quedaría por debajo de 49 para el radio, y no se podría certificar nada.

**Cómo contarlo (tono acordado):**
- No es "el OEM es mejor que un modelo entrenado con el activo". Con todo el historial, el específico llega al mismo punto (sección anterior).
- Lo que muestra es que, cuando los datos del activo son pocos, separar entrenamiento (simulación) y calibración (campo) es lo que permite que la garantía sea válida.
- Lo dejamos como resultado y que el revisor saque la conclusión.
- **Matiz:** es un caso fácil (CWRU), con unas 50 sanas evaluadas por condición, y las cinco semillas comparten esas mismas ventanas, así que los rangos no son independientes.

## Crudo frente a cociente: para qué sirve el método

La referencia que haría un ingeniero sin el método es un autoencoder entrenado con la señal **cruda** del rodamiento: 48 kHz tal cual, ventanas de 1200 muestras, sin proyección ni modelo de perturbaciones. Se compara, con el **mismo tiempo de puesta en marcha** (~5 s), con dos formas de trabajar en el cociente: un modelo local entrenado en el cociente (proyección + aumento sobre el grupo) y el OEM.

→ Tabla **"Crudo frente a cociente, mismo tiempo de puesta en marcha"** en [`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md); el paso intermedio (proyección sin aumento) es la tabla **"Igualdad de datos"**.

**Lo que se ve (1730 / 1750 / 1772 rpm; a 1797 no quedan sanas para medir):**
- **Detección:** 100% de los fallos en todos los modelos.
- **Falsas alarmas en las sanas posteriores, de peor a mejor:**
  - crudo, local: 100% / 100% / 9–14%;
  - solo proyección, local (sin cubrir el resto del grupo): 23–57% / 2–27% / 4–18%;
  - cociente completo, local (proyección + aumento sobre el grupo): 0–4% / 0% / 0–6%;
  - cociente, OEM: 8,5% / 6,1% / 0%.
- **Lectura:** con poco tiempo de puesta en marcha, lo que hace viable el detector es **trabajar en el espacio cociente**. Da igual que el modelo se entrene en el sitio (local, aumentado sobre el grupo) o de fábrica con simulación (OEM): los dos funcionan, y el crudo no. El autoencoder es solo el vehículo.
- **Qué añade el OEM sobre el local en el cociente:** no requiere entrenar nada en el sitio, solo calcular un radio, y el modelo existe antes de instalar el activo. Aquí el local en el cociente da incluso algo menos de FAR.

**Por qué falla el crudo (comprobado y con hipótesis):**
- **Comprobado:** el registro sano es estacionario (media y desviación constantes segundo a segundo). El modelo crudo reconstruye bien ventanas nuevas de esos mismos 5 s, pero las posteriores le dan un error claramente mayor: ha memorizado lo que vio en esos 5 s, no la órbita nominal.
- **Hipótesis, pendiente de verificar con un script:**
  - En el dominio de órdenes, con ventanas de exactamente 3 vueltas, todas las ventanas empiezan en el mismo ángulo del eje: la sección fija la fase del eje.
  - Las ventanas crudas (25 ms, menos de una vuelta) empiezan en un ángulo cualquiera y mezclan componentes no síncronos con el eje.
  - 5 s no bastan para cubrir esa órbita sin el cociente.

**Matices:**
- La ventana cruda de 1200 muestras a 48 kHz es una elección; un ingeniero podría usar ventanas más largas, y se puede probar como variante.
- La referencia cruda con todo el historial solo tiene FAR medida sobre sus propios datos de entrenamiento (2,2–2,5% por construcción). No hay sanas no vistas para evaluarla.
- Caso fácil (CWRU), unas 50 sanas evaluadas en el cociente y unas 200 en crudo por condición, y 3 semillas.

## Resumen en cinco frases

1. **El problema estaba ahí.** En la configuración publicada (A), la Normal (48 kHz) se leía como si fuera de 12 kHz frente a fallos `DE12`. Un simple conteo de cruces por cero separa sanos y fallos con AUROC = 1,000 en las cuatro velocidades.
2. **Con la corrección** (B: Normal + `DE48`, ambos con proyección angular), los cruces por cero dejan de separar en tres de las cuatro velocidades (AUROC 0,52–0,91). La confusión por frecuencia de muestreo desaparece.
3. **La detección en CWRU es fácil, y para una afirmación de viabilidad eso basta.** Tras la corrección, el autoencoder compartido (estilo OEM, sin datos del activo) y el **RMS** dan AUROC = 1,000 en todas las velocidades y familias de fallo. Los ficheros de fallo tienen un RMS de 2 a 9 veces el de la Normal. El objetivo del paper no es ser mejor, sino mostrar que *es posible* llegar al punto de operación de un modelo específico del activo con un modelo compartido y calibración local. CWRU lo muestra, aunque en un problema fácil. El RMS con calibración local es otro modelo estilo OEM: el más simple.
4. **La proyección angular elimina la velocidad, pero no la carga.** El radio calibrado en una condición no sirve para otra (1772 y 1797 rpm caen fuera en un 93–100%). La calibración local es necesaria, y eso sí lo apoya CWRU.
5. **Con ~50 sanas por condición, la falsa alarma real es muy incierta.** El radio certificado con n = 49 da FAR del 0–8,5% en las sanas siguientes, con intervalos del 95% que llegan al 20%. A 1797 rpm solo hay 50 ventanas sanas: la regla online no converge y no queda nada para evaluar.

## Qué se ha hecho

**Configuraciones**, todas con el mismo protocolo:

| | Sanas | Fallos | Dominio | Operador compartido |
|---|---|---|---|---|
| **A** original | Normal (48 kHz) leída como 12 kHz | `DE12` (7/14/21/28) | tiempo, 1200 muestras | entrenado con simulación en tiempo (como el publicado) |
| **B** corregida | Normal (48 kHz) | `DE48` (7/14/21) | órdenes: 400 muestras/vuelta, ventanas de 3 vueltas | entrenado con simulación **proyectada igual** |
| **C** control de cadena | Normal (48 kHz) | `DE12` | órdenes, igual que B | el mismo de B |

**La proyección** está en `mssp_repro/field/order_domain.py`:
- **Velocidad:** se estima por fichero con una suma de armónicos 1–3 en ±4% de la nominal. Las Normal quedan a −0,02% … −0,32% de la nominal. Los ficheros de menos de 3 s (cinco a 1797 rpm) usan la velocidad de la Normal de su condición.
- **Remuestreo:** polifásico, a 400 muestras por vuelta.
- **Ventanas:** de 3 vueltas, sin solape.
- **Simulador:** se proyecta igual, usando su velocidad conocida.
- **Tests:** 9 en `tests/test_order_domain.py`. Comprueban que la estimación de velocidad queda dentro del 0,2%, que dos velocidades y dos frecuencias de muestreo dan la misma ventana proyectada (error < 2%) y que, sin proyectar, las ventanas difieren (> 20%).

**Detectores:**
- el autoencoder compartido (arquitectura y calendario de entrenamiento publicados, semilla 42);
- RMS, curtosis y cruces por cero, puntuados como |valor − mediana sana|.

**Calibraciones:**
- **Transferencia directa:** τ_MC de la simulación.
- **Oráculo:** p98 interpolado sobre todas las sanas, como se publicó.
- **Online:** regla de parada publicada.
- **Certificada:** r₍ₖ₎ sobre las 49 primeras sanas, con la FAR medida en las siguientes.

## 1. La confusión existía y la corrección la elimina

AUROC sano frente a fallo, con los cruces por cero como detector trivial:

→ Tabla **"AUROC sano vs fallo (sin umbral)"**, fila `zcr` de cada configuración, en [`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md).

Mediana de cruces por cero en A: sanas 0,17–0,21 frente a fallos 0,43–0,50, un factor ~2,5 que es la huella del factor 4 de escala temporal. En B, sanas y fallos quedan en 0,42–0,47, salvo 1797 (véase el punto 5).

**C frente a B:** usar `DE12` con la Normal proyectada separa más que B (AUROC 0,83–0,97 frente a 0,52–0,91). Es la diferencia de cadena de adquisición que la proyección no elimina. Confirma que hay que emparejar la Normal con `DE48`.

## 2. La detección en CWRU es fácil para cualquier modelo compartido

AUROC del autoencoder compartido y del RMS en B: **1,000 en las 12 combinaciones** de velocidad y familia, para los dos detectores. Con calibración certificada (n = 49), el RMS detecta el 100% de los fallos en todas las velocidades, igual que el autoencoder.

→ Tabla **"Medianas de los descriptores (qué separa)"**, configuración B, en [`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md).

**Consecuencia para un paper de viabilidad:** el 100% de detección en CWRU sigue siendo cierto tras la corrección. No sirve para decir que el método es *mejor* (lo conseguiría cualquier indicador de energía), y tampoco hace falta, porque esa no es la afirmación. Sirve para decir que el esquema OEM + radio local *llega* al punto de operación esperado. Conviene reconocer que CWRU es fácil (Smith & Randall, 2015, MSSP) y que la demostración exigente está en IMS (detección temprana en run-to-failure).

**La comparación de viabilidad** (modelo OEM frente a modelo específico del activo) está en la sección "Resultado principal" de arriba: mismo punto de operación en las cuatro condiciones.

La curtosis es el único descriptor que no llega a 1,000 (bola 0,78–0,87). Es coherente con que los fallos de bola de CWRU son los menos impulsivos.

## 3. La proyección quita la velocidad, no la carga: el radio no se transfiere

Radio oráculo del autoencoder calibrado en la fila y aplicado a las sanas de la columna (% fuera del radio). En B:

→ Tabla **"Transferencia del radio entre velocidades (solo sanas)"**, B — ae, en [`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md). Calibrado en 1730 o 1750, deja fuera el 92,9% de las sanas de 1772 y el 100% de las de 1797.

Radios oráculo en B: 0,0579 / 0,0583 / 0,0680 / 0,0871, un factor 1,50 entre extremos. El RMS sano también cambia con la condición (0,057–0,072) y su radio tampoco se transfiere.

**Lectura:**
- Entre 1730 y 1772 rpm la velocidad cambia un 2%, pero la carga pasa de 3 a 1 HP. La carga no es una reparametrización del tiempo, así que no está en el grupo que proyectamos.
- La parte de la tesis del paper de que **la representación se comparte y la escala del radio es local** queda bien apoyada, y por un motivo físico identificable.

## 4. Transferencia directa del umbral simulado

En B, τ_MC = 0,1096 queda entre 1,26 y 1,89 veces por encima del oráculo local:
- FAR = 0% en las cuatro velocidades.
- Detección del 99,3–100%, porque los fallos están muy lejos.

En A (este reentrenamiento), τ_MC = 0,0452 queda a 0,78–1,04 del oráculo, y la FAR de la transferencia directa va del 0,25% al 76,85% (1797).

**Matiz para el paper:** la versión publicada decía que la transferencia directa marca el 100% de las sanas (τ_MC = 0,1027 frente a un oráculo ~0,35). Con el mismo código y otra versión de TensorFlow, la escala del operador cambia un orden de magnitud (oráculo 0,046 frente a 0,358). Eso refuerza que la escala no se transfiere, pero también indica que **la dirección del error de la transferencia directa depende del entrenamiento**. No conviene afirmar que la transferencia directa "falla siempre por exceso de falsas alarmas".

## 5. Calibración con pocas sanas: la garantía es marginal

FAR en sanas **no vistas** tras calibrar, autoencoder compartido, con intervalo de Clopper–Pearson al 95%:

→ Tablas **"FAR en sanas no vistas, con IC 95% de Clopper–Pearson"** y **"Deriva cronológica de las sanas"** en [`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md).

**Lectura:**
- Con el máximo de 49, la cobertura realizada sigue una Beta(49, 1): P(FAR > 5%) ≈ 8%. Los valores de B son compatibles con eso, pero con 50 sanas no se puede distinguir nada.
- A 1772 rpm en A, un 8,5% sobre 354 sanas tendría una probabilidad de ~1% bajo intercambiabilidad. Hay **deriva cronológica dentro del registro**: Spearman entre el índice temporal y el residuo da +0,21 (p = 3·10⁻⁵) en 1730 y 1772 en A, +0,26 (p = 0,01) en 1750 en B y +0,29 (p = 0,045) en 1797 en B.
- **Cuidado al leer A:** sus ventanas sanas duran 25 ms, así que sus 49 primeras cubren solo 1,2 s de registro. En B cubren unos 5 s.

**Para el paper:** CWRU no tiene suficientes sanas para validar la cobertura certificada con n ≥ 99 ni para medir la FAR con precisión. Sirve como ilustración del procedimiento, no como validación de la garantía.

## 6. 1797 rpm es un caso aparte

- Su Normal dura la mitad (5,1 s a 48 kHz, 50 ventanas de 3 vueltas).
- Su espectro es distinto: la mediana de cruces por cero en B es 0,566, frente a 0,42–0,43 en las otras tres Normal.
- Con cruces por cero separa todos los fallos de su condición (AUROC ≥ 0,98), mientras que en las otras tres no.
- Su radio es el mayor y ningún otro radio la cubre.

**Propuesta:** tratar 1797 como condición con datos insuficientes, ya sea excluyéndola del análisis de calibración o reportándola aparte con esa etiqueta.

## 7. Otras observaciones

- **Velocidades de los `B_28_DE12`:** se estiman un 2% por debajo del resto de su condición (28,14 Hz a 1730 y 28,58 Hz a 1750). `1772_OR@12_7_DE12` da 29,94 Hz, que corresponde a 1797 rpm. Son posibles inconsistencias del propio archivo CWRU. Solo afectan a C, porque en B no hay ficheros de 28.
- **Operadores:**
  - En tiempo: 72 épocas, val_loss 0,0237.
  - En órdenes: 31 épocas, val_loss 0,0647. El residuo nominal es mayor en órdenes, quizá porque la resonancia se mueve en orden con la velocidad simulada (±10%).
- **El test preexistente `test_conv_autoencoder.py::test_operator_validates_input` falla en este entorno** (TensorFlow 2.21, CPU): el autoencoder de ese test no aprende. No lo he tocado. Conviene mirarlo en tu Mac.
- **IMS no se ha tocado.** Ahí no hay problema de frecuencia de muestreo, pero si adoptamos la proyección como parte del método, IMS debería pasar por ella también para ser coherentes (2000 rpm constantes, 20 kHz → 400 muestras por vuelta).

## Cómo reproducir

```bash
cd reproducibility_package
python3 -m pytest tests/test_order_domain.py -q
python3 cwru_projection_experiment.py --cwru-root PATH/CWRU_Bearing_NumPy/Data \
        --out results/cwru_projection          # ~35 min en CPU
python3 cwru_asset_reference.py --cwru-root PATH/CWRU_Bearing_NumPy/Data \
        --out results/cwru_projection          # ~2 min
python3 cwru_projection_report.py results/cwru_projection > ../mssp_paper/notas/tablas_cwru_proyeccion.md
```

Hacen falta los ficheros `Normal`, `DE48` y `DE12` (B, IR, OR) del redistribuible de srigas. `download_datasets.sh` ya lo baja entero.
