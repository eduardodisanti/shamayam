# Protocolo registrado: modelo de fábrica aprendido en un banco de pruebas (CWRU) y desplegado en IMS y Ottawa

*Versión 1, escrita el 14-oct antes de implementar nada. **Aprobada el 14-oct con cambios** (incorporados abajo: prueba de la forma reforzada, nombres de los resultados, control de aprendizaje por etapas). Cualquier cambio posterior se anota aquí con fecha y motivo, y nunca se cambia nada después de ver los resultados de IMS u Ottawa sin dejarlo escrito.*

## Por qué

Los indicadores clásicos con la misma calibración local detectan lo mismo que el autoencoder entrenado con el simulador (05_clasicos_y_contaminacion). Cuando se quita la energía (normalización de ganancia), el OEM del simulador pierde la detección (AUROC 0,40–0,62 en Ottawa), pero el modelo por máquina no: el autoencoder ve la forma, y lo que falla es la forma nominal que aprende del simulador. La pregunta es si un modelo de fábrica que aprende la forma nominal de un **banco de pruebas real** la transfiere a máquinas que nunca vio, a través del cociente.

Es el escenario realista: el fabricante entrena en su banco y despliega en campo con calibración local.

## Decisión de estructura (acordada 14-oct)

El origen de la puntuación de fábrica es un **eje** del mismo experimento, con todo lo demás igual: sin aprendizaje (cocientes gruesos: RMS, curtosis, envolvente) → aprendido de un simulador simple → aprendido de un banco real. La regla de puesta en marcha certificada, el cociente y los modos de fallo no cambian. La metodología del paper se reescribe en torno a esto, aunque cueste.

## Hipótesis

- **H1 (forma).** Con la normalización de ganancia (sección qg), el OEM del banco detecta en Ottawa los fallos que el modelo por máquina en qg detecta (pista interior, bola, combinado), y el OEM del simulador no.
- **H2 (operación).** Sin normalización (sección q), el OEM del banco mantiene en IMS la salida del bearing 1 y una FAR del orden de la del OEM del simulador.
- **H0.** La forma nominal del banco no se transfiere porque la vía de transmisión (sensor, montaje, estructura) no está en G. El residuo mide el desajuste entre máquinas, como pasó con el simulador.

## Banco

- **Datos:** solo los registros sanos de CWRU: `{rpm}_Normal.npz`, canal DE, 48 kHz, las cuatro cargas (1797, 1772, 1750, 1730 rpm). No se usa ningún registro de fallo de CWRU, y CWRU no se evalúa como destino.
- **Proyección:** la misma que en CWRU. Velocidad estimada por registro (`estimate_shaft_frequency`), remuestreo angular a 400 muestras por vuelta y ventanas de 3 vueltas.
- **Separación entrenamiento/validación:** el 80% inicial de cada registro para entrenar y el 20% final para validar. Sin solape.
- **Aumento sobre G:** el mismo que en los modelos locales en el cociente (inicio aleatorio = fase; ganancia U(0,75; 1,25); offset ±0,1·RMS; ruido 0–5%·RMS). 4000 ventanas de entrenamiento y 1000 de validación, cada conjunto de su parte.
- **Variantes:** `bench_q` (sin normalizar) y `bench_qg` (normalización por ventana: quitar la media y dividir por el RMS, aplicada después del aumento y también a los datos de destino).
- **Operador:** la misma arquitectura (Conv1D, 847.601 parámetros, latente 16), el mismo programa de entrenamiento que el OEM publicado y el escalado estándar ajustado solo con el banco.
- **Control de aprendizaje:** el de colapso de los modelos por máquina (se rechaza solo si queda sin reconstruir más del 98% de la varianza), anotando la fracción no reconstruida. Se fija ahora porque la vibración real es casi ruido y el control publicado (≥ 50% reconstruido) está pensado para el simulador.
- **Semillas:** 42, 0, 1, 2, 3, las mismas que el OEM del simulador.

## Destinos y métricas (sin cambios respecto a lo ya hecho)

- **IMS (los cuatro bearings):** puntuación por registro (media de las ventanas); radio r₍ₖ₎ con n = 49, 99, 149, 200; FAR en los registros 200–499; salida persistente (8 de 10) y antelación. Proyección a la velocidad nominal (2000 rpm), como en la curva de aprendizaje.
- **Ottawa:** proyección con el encoder; escenarios A-1 y los cuatro ensayos 1; FAR por ventana y por banda de velocidad, registros sanos con alarma, y registros detectados y AUROC por tipo de fallo.
- **Comparación:** lado a lado con los resultados ya generados (OEM del simulador q/qg, modelos por máquina, indicadores clásicos). No se reejecutan.

## Criterios de lectura (aprobados 14-oct)

La transferencia de la forma (H1) es el resultado más importante, así que su prueba tiene que ser a prueba de balas: controles que separen la forma aprendida del banco de cualquier otra explicación, intervalos que respeten que las ventanas de un mismo registro no son independientes, y una comprobación de que la velocidad no confunde.

**Controles (todos en la sección qg, misma arquitectura, mismo programa, mismas semillas):**
- **C-ruido:** el mismo autoencoder entrenado con ventanas de ruido blanco gaussiano normalizadas (un "banco" sin estructura). Si alcanza el mismo AUROC, la detección viene de la arquitectura y la normalización, no de la forma aprendida.
- **C-simulador:** el OEM del simulador en qg (ya calculado).
- **Referencias:** el modelo por máquina en qg (techo, *in-sample*) y la curtosis en el cociente (indicador clásico invariante a la ganancia).

**Estadística:**
- AUROC ventana a ventana por tipo de fallo y semilla, frente a los sanos de prueba.
- Intervalo al 95% por *bootstrap* de registros: se remuestrean registros completos, sanos y de fallo, 2000 veces, no ventanas sueltas.
- Diferencia pareada con cada control: AUROC(banco) − AUROC(control) sobre los mismos remuestreos.

**"La forma se transfiere" para un tipo de fallo** si se cumplen las dos:
1. AUROC medio sobre las 5 semillas ≥ 0,80.
2. En al menos 4 de 5 semillas, el intervalo de la diferencia pareada queda entero por encima de 0 frente a C-ruido y frente a C-simulador.

**H1 se cumple** si la forma se transfiere en al menos dos de pista interior, bola y combinado. La pista exterior se informa, pero no entra en el criterio (en estos datos solo la curtosis la ve).

**Comprobación de confusión por velocidad:** se repite el AUROC con solo las ventanas de 15–25 Hz (rango común a sanos y fallos). Si H1 se cumple con todas las ventanas pero no en esa banda, se informa como **no concluyente**.

**Secundario:** en IMS, salida del bearing 1 con el OEM del banco en qg.

**"Opera" (H2):** en IMS con n = 99, el bearing 1 sale como mucho 10 registros después del 539 en al menos 4 de 5 semillas, con FAR ≤ 2% en el bearing 1.

**Cómo se nombra el resultado:**
- **Transfiere:** se cumple el criterio.
- **Evidencia parcial:** se cumple para un tipo de fallo, o solo en parte de las semillas. Se describe qué y dónde.
- **No se detecta transferencia con este método:** no sabemos si la forma transfiere; este método (este autoencoder, esta sección, estos datos) no la detecta. No se afirma que no transfiera.

## Control de aprendizaje, por etapas

1. Se entrena con el banco y se miran **solo** los diagnósticos del banco (fracción no reconstruida y generalización en la validación del banco), antes de puntuar ningún destino.
2. Si la fracción no reconstruida en la validación supera 0,95 ("aprende poco"), se anota aquí antes de seguir. No es una parada, pero se interpreta con eso delante.
3. El control C-ruido no pasa el filtro de colapso (no hay nada que aprender); se registra su fracción no reconstruida y se usa igualmente.

## Lo que no se hará

- No se ajusta nada del banco (bandas, filtros, aumento, épocas, elección de cargas) después de ver IMS u Ottawa.
- No se evalúa en CWRU.
- No se añaden variantes que no estén aquí sin anotarlas antes como versión nueva.

## Salidas y reproducibilidad

- Código: `bench_transfer.py`. Resultados en `results/bench/` (json con las puntuaciones por ventana y por registro).
- Informe: `bench_report.py` → `tablas_banco.md`, comprobado byte a byte por `tests/test_generated_notes.py`.
- Datos fijados por manifiesto, como el resto.

## Coste estimado

Tres variantes (banco q, banco qg, C-ruido qg) por 5 semillas, unos 15 min por entrenamiento en esta máquina: ~4 h. La evaluación es rápida porque los destinos ya están proyectados.

## Consecuencias para el paper según el resultado

- **Transfiere:** el banco pasa a ser la instancia principal (banco del fabricante → campo) y el simulador queda como ablación.
- **Parcial o no transfiere:** se mantiene el eje de tres escalones. El banco es un límite medido; la vía de transmisión en G y la fidelidad del modelo de fábrica quedan como trabajo futuro.
- En cualquier caso, la columna del paper (regla de puesta en marcha certificada, cociente, modos de fallo) no cambia.
