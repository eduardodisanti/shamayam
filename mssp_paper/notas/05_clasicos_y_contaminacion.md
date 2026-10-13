# Indicadores clásicos en IMS y puesta en marcha contaminada (13-oct)

*Sin tablas a mano. Las tablas están en [`tablas_ims_clasicos.md`](tablas_ims_clasicos.md) y [`tablas_contaminacion.md`](tablas_contaminacion.md), generadas por `extra_reports.py` desde `results/ims_classical/results.json` (`ims_classical_features.py`) y `results/contamination/results.json` (`commissioning_contamination.py`). `tests/test_generated_notes.py` las comprueba byte a byte y verifica la regla n − k. Nada se entrena: los dos experimentos son deterministas.*

## 1. IMS: indicadores clásicos con la misma calibración local (D7)

**Qué se ha hecho.** RMS, curtosis, factor de cresta y un indicador de envolvente, cada uno calculado una vez por registro de 1 s. Se aplica el mismo protocolo que al autoencoder: radio r₍ₖ₎ sobre los n primeros registros, FAR en los registros 200–499 y salida persistente (8 de 10).

La envolvente no usa la geometría del rodamiento: es el pico sobre la mediana del espectro de la envolvente en los órdenes 2–20. No se tomaron de la literatura las frecuencias de defecto de los rodamientos de IMS, para no elegir banda ni frecuencia después de ver los datos. Una envolvente con la frecuencia de defecto de pista exterior sería más fuerte; queda como posible mejora, citando la fuente de la geometría.

**Lo que se ve.**
- **El RMS y la envolvente detectan el fallo del bearing 1 en el mismo registro que el autoencoder (539, 73,83 h antes del final), con todas las longitudes de puesta en marcha.** Sus falsas alarmas en la vida sana son del mismo orden: 0–3,7% según bearing e indicador.
- **La curtosis sale más tarde (654, 54,67 h con n ≥ 99)**, y el factor de cresta prácticamente no sirve (977, 0,83 h). El fallo de IMS es sobre todo energético.
- **Los bearings 2–4**, sin fallo documentado, salen en registros distintos según el indicador; como antes, indican sensibilidad, no aciertos.

**Lectura (para discutir).**
- **Refuerza D7 y el tono acordado.** El esquema (modelo estilo OEM + radio local certificado) funciona igual con indicadores de décadas de uso, sin entrenar nada. Lo que hace viable el despliegue es el esquema, no la representación.
- **Pero hay que decirlo con claridad: en IMS el autoencoder no aporta detección sobre el RMS.** En Ottawa pasa algo parecido: el AUROC del autoencoder por tipo de fallo es casi el del RMS, y ninguno ve la pista exterior, que sí ve la curtosis. En estos datos, el residuo del autoencoder se comporta como un indicador de energía.
  - Esto no debilita la tesis: el paper no vende el autoencoder.
  - Pero obliga a que esté en la introducción y en las tablas, no solo en la discusión, porque es lo primero que señalaría un revisor.
  - Y orienta qué contar del cociente. Su valor medido está en la *puesta en marcha corta con un modelo aprendido*: en la curva de aprendizaje de IMS, el modelo por máquina en crudo no llega al OEM ni con 33 h, y en el cociente sí. No está en que el autoencoder detecte más.

## 2. Puesta en marcha contaminada por un fallo ya presente

**Qué se ha hecho.**
- Sobre el único fallo real (IMS, bearing 1), se sustituyen m de los n registros de puesta en marcha por registros de los últimos 100 activos, donde el fallo es inequívoco.
- Se recalcula el radio y se busca la salida en la secuencia real, con 1000 sorteos por casilla.
- Puntuaciones: el OEM publicado, el RMS y la envolvente.

**Resultado, exacto y libre de distribución.** El radio r₍ₖ₎ no se mueve con hasta n − k observaciones contaminadas, siempre que queden por encima de todo lo sano. Por eso el menú de puesta en marcha fija también cuánta contaminación tolera cada longitud:

| Longitud | k | Contaminación tolerada |
|---|---|---|
| n = 49 | 49 | 0 registros |
| n = 99 | 98 | 1 registro |
| n = 149, r₍ₖ₎ | 147 | 2 registros |
| n = 149, tolerancia 0,98/0,95 | 149 | 0 registros |

Los datos lo confirman con las tres puntuaciones: hasta n − k el radio no cambia y el fallo sale con la misma antelación (73,8 h); un registro contaminado más y el radio se multiplica por entre 2 y 10 según la puntuación (hasta 12 con más contaminación).

- **Consecuencia práctica:** con el OEM y el RMS, la antelación mediana cae de 73,8 h a pocas horas (OEM: 7,3 h con n = 49 y un solo registro contaminado); con la envolvente, a 45,5 h. En una parte de los sorteos el fallo no se detecta antes del final (11% con n = 49 y m = 1 en el OEM).
- **La garantía con confianza (tolerancia de Wilks, n = 149) se paga en robustez.** Usa el máximo de la muestra, así que no tolera ni un registro contaminado. r₍ₖ₎ con la misma n tolera dos.

**Lectura (para discutir).**
- **Es un modo de fallo medido y a la vez un argumento a favor del menú.** Las longitudes más largas no solo dan un radio más estable o una garantía con confianza: también absorben una o dos observaciones contaminadas. Encaja con "dónde va la fuerza" sin prometer nada nuevo.
- **No resuelve el caso general.** Si la contaminación es más que n − k, o si el fallo ya presente no supera a lo sano (degradación incipiente), el radio queda inflado y el método no lo detecta. Se declara; la mitigación operativa conocida (inspección en la puesta en marcha, comparar con el radio de flota) queda fuera del paper.
- **Para el texto:** cabe en §7 (una frase y un corolario trivial: el radio r₍ₖ₎ no cambia si se alteran las n − k observaciones mayores mientras sigan por encima de él) y en la tabla de modos de fallo (§11).
