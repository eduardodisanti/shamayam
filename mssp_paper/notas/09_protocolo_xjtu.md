# Protocolo registrado: XJTU-SY, quince fallos reales hasta el final de vida

*Escrito el 16-oct, antes de implementar y ejecutar nada sobre XJTU-SY, y sin haber mirado sus señales más allá de contar ficheros y leer la introducción de los autores. Para revisar y aprobar. Cualquier cambio posterior se anota aquí con fecha y motivo.*

> Los rodamientos son solo validación. XJTU-SY no cambia el alcance (maquinaria rotativa, D5): añade fallos reales donde IMS solo tiene uno.

## Por qué

- **IMS tiene un único fallo real** (bearing 1). Es el flanco más débil de la validación exigente.
- **XJTU-SY tiene quince**, en otro banco, con otro rodamiento y en tres condiciones de velocidad y carga, y con varios tipos de fallo (pista exterior, pista interior, jaula, combinados).
- Es un ensayo **acelerado**: vidas de 42 min a 42 h y degradación rápida. Pone a prueba el menú de puesta en marcha en una escala de tiempo distinta (un registro por minuto) y la tolerancia a la contaminación n − k.

## Datos

- **XJTU-SY** (Wang, Lei, Li y Li, *IEEE Trans. Reliability* 69(1), 2020, doi:10.1109/TR.2018.2882682). Registrado en `datasets/registry.json` con manifiesto SHA-256 (9217 ficheros). Sin licencia explícita: los autores lo declaran público para validar algoritmos de pronóstico y piden citar el artículo.
- Rodamiento LDK UER204 (8 bolas, 7,92 mm; diámetro medio 34,55 mm; ángulo de contacto 0°).
- 25,6 kHz, 32 768 muestras (1,28 s) cada minuto, dos acelerómetros a 90° (columna 1 horizontal, columna 2 vertical).
- Cada ensayo termina cuando la amplitud máxima horizontal **o** vertical supera 10 veces la de la fase normal.

| Condición | Rodamiento | Registros | Vida | Elemento con fallo (Tabla 2 de los autores) |
|---|---|---|---|---|
| 35 Hz / 12 kN | 1_1 | 123 | 2 h 3 min | pista exterior |
| | 1_2 | 161 | 2 h 41 min | pista exterior |
| | 1_3 | 158 | 2 h 38 min | pista exterior |
| | 1_4 | 122 | 2 h 2 min | jaula |
| | 1_5 | 52 | 52 min | pista interior y exterior |
| 37,5 Hz / 11 kN | 2_1 | 491 | 8 h 11 min | pista interior |
| | 2_2 | 161 | 2 h 41 min | pista exterior |
| | 2_3 | 533 | 8 h 53 min | jaula |
| | 2_4 | 42 | 42 min | pista exterior |
| | 2_5 | 339 | 5 h 39 min | pista exterior |
| 40 Hz / 10 kN | 3_1 | 2538 | 42 h 18 min | pista exterior |
| | 3_2 | 2496 | 41 h 36 min | pista interior, bola, jaula y exterior |
| | 3_3 | 371 | 6 h 11 min | pista interior |
| | 3_4 | 1515 | 25 h 15 min | pista interior |
| | 3_5 | 114 | 1 h 54 min | pista exterior |

## La sección del cociente

- **Igual que en IMS:** velocidad constante y nominal por condición (35; 37,5; 40 Hz), remuestreo angular fijo a 400 muestras por vuelta, ventanas de 3 vueltas (1200 muestras), sin solape, desde el principio del registro.
  - Son 14, 16 y 17 ventanas por registro según la condición.
  - No se estima la velocidad por registro: con 1,28 s el estimador es más ruidoso que la regulación del motor. Se declara como limitación, como en IMS.
- **Puntuación por registro:** media de los residuos de sus ventanas, como en IMS.

## Canales (decidido antes de mirar)

- **Principal: los dos canales como dos espacios vigilados a la vez** (unión de alarmas con nivel repartido, Bonferroni, como en [`07_definicion_cociente.md`](07_definicion_cociente.md)). Cada radio se toma al nivel 1 − 0,02/2, y por eso exige **n ≥ 99**.
  - **Por qué:** el propio criterio de fin de ensayo de los autores usa el horizontal *o* el vertical, y la dirección en que se manifiesta cada fallo cambia de un rodamiento a otro. Elegir un canal sería elegir de antemano dónde aparece el fallo.
- **Secundario:** cada canal por separado, con el menú completo (49 / 99 / 149 y tolerancia 0,98/0,95 con 149).
- **Modelos por máquina (curva de aprendizaje):** solo el horizontal, por coste de cómputo. Se fija ahora y no se cambia después de ver resultados.

## Modelos (puntuaciones)

1. **oem_q** — el OEM del simulador en el cociente, exactamente como `oem_q` de IMS (programa NASA publicado, ventanas simuladas proyectadas con su velocidad conocida). Nunca vio datos reales. 5 semillas (42, 0, 1, 2, 3), reentrenadas en esta ejecución.
2. **bench_q** — el modelo de fábrica aprendido en el banco CWRU, sección q, exactamente como en el protocolo v1 del banco. 5 semillas (42, 0, 1, 2, 3), reentrenadas en esta ejecución (los pesos de v1 no se conservaron). Secundario.
3. **Indicadores clásicos**, sin entrenamiento (D7): RMS, curtosis, factor de cresta e indicador de envolvente (pico sobre mediana del espectro de la envolvente, órdenes 2–20 de la velocidad nominal, sin geometría del rodamiento). Por registro, banda completa, dominio del tiempo, como en `ims_classical_features.py`.
4. **Por máquina** (réplica de la curva de aprendizaje de IMS), canal horizontal:
   - **raw:** autoencoder sobre las ventanas crudas (1200 muestras a 25,6 kHz) de los primeros n registros;
   - **quot:** autoencoder en el cociente: ventanas proyectadas de los primeros n registros, aumentadas sobre G (fase, ganancia, offset, ruido; rangos *wide*), 4000 ventanas;
   - n ∈ {49, 99}; semillas 0–4; filtro de aprendizaje solo contra colapso (> 0,98 no reconstruido), como en IMS.
   - Se ejecuta **por semilla** (la semilla 0 en todos los rodamientos, luego la 1…), para que, si el tiempo no alcanza, queden semillas completas y no rodamientos sueltos.

## Puesta en marcha y medidas

- **Radio** r₍ₖ₎ sobre los primeros n registros, α = 0,02; n ∈ {49, 99, 149}; tolerancia 0,98/0,95 con n = 149. En la unión de canales, α/2 por canal.
- **Comisionable:** vida L ≥ n + 10 (hacen falta 10 registros después para la regla de persistencia). Con n = 49 no lo son 1_5 ni 2_4; se declaran **no comisionables**, como 1797 rpm en CWRU. Con n = 99 son 13 rodamientos.
- **Salida:** primera salida persistente (8 de 10) después de la puesta en marcha. Se informa como antelación hasta el final del registro (minutos) y como fracción de vida.
- **XJTU no tiene etiquetado el inicio del fallo.** Por eso:
  - **Franja sana declarada para la FAR:** solo en los rodamientos largos 2_1, 2_3, 3_1, 3_2 y 3_4, registros [150, ⌊L/2⌋). El supuesto (la primera mitad de la vida es sana) se declara; como diagnóstico, sin efecto sobre el veredicto, se informa la tendencia de Spearman del RMS en la franja.
  - **Salida temprana:** una salida antes de ⌊L/2⌋ se informa como tal, sin clasificarla como falsa alarma ni como detección: puede ser una degradación temprana.
- **Contaminación:** en los rodamientos cortos la puesta en marcha puede incluir degradación. Se informa con la tolerancia exacta n − k ya establecida en IMS, sin veredicto.

## Criterios (como código, comprometidos antes de la ejecución)

- **H1 (opera; principal): oem_q, unión H∪V, n = 99, sobre los 13 rodamientos comisionables.** En al menos 4 de 5 semillas:
  1. salida antes del final del registro en al menos 10 de 13 rodamientos, y
  2. FAR agregada en la franja sana de los 5 rodamientos largos ≤ 5%.
  - El 5% es 2,5 veces el nominal: deja margen a la falta de intercambiabilidad ya medida en IMS y Ottawa. Se fija ahora.
  - **Nombres:** *opera* (se cumplen las dos); *opera en parte* (solo una, o solo en 2–3 semillas; se describe cuál); *no opera*.
- **H2 (el cociente frente al crudo por máquina; horizontal).** Se replica la lectura de IMS si, con n = 49, la mediana sobre semillas de la FAR agregada en la franja sana es > 5% para raw y ≤ 5% para quot. Si no, *no se replica*, y se informa igual.
- **Secundario, sin veredicto:** cada canal por separado con el menú completo; bench_q; indicadores clásicos; antelaciones y fracciones de vida; contaminación.

## Lo que no se hará

- No se ajusta nada (sección, ventanas, órdenes, franja, umbrales, épocas) después de ver XJTU.
- No se transfieren radios entre rodamientos ni entre condiciones.
- No se estima vida remanente ni se diagnostica el tipo de fallo: el método detecta.
- No se usa XJTU para elegir nada de IMS, CWRU u Ottawa.

## Salidas y reproducibilidad

- Código: `xjtu_experiment.py` (puntuaciones y modelos), `xjtu_report.py` (criterios como código y tablas). Se suben a git **antes** de la ejecución completa.
- Caché de registros (`.npz`, float32) en el disco de datos, reconstruible desde el manifiesto.
- Resultados en `results/xjtu/`; tablas en `tablas_xjtu.md`, comprobadas byte a byte por un test.

## Coste estimado

- 10 entrenamientos de fábrica (oem_q y bench_q) más unos 260 por máquina (13 rodamientos × 2 valores de n × 2 brazos × 5 semillas), más la evaluación. El tiempo por entrenamiento se mide en la prueba de humo antes de lanzar.

## Registro de ejecución

- **16–17-oct, ejecución completa** (commit de registro `df51e2a`; macOS 27.0.1, Python 3.12.15, TensorFlow 2.21.0; todas las etapas sin cambios respecto a lo registrado). Tablas en [`tablas_xjtu.md`](tablas_xjtu.md), generadas por `xjtu_report.py` y comprobadas byte a byte.
  - **H1: opera en parte.** Los 13 rodamientos comisionables salen antes del final en las 5 semillas, pero la FAR agregada en la franja sana es 5,3–6,1%, por encima del 5% fijado.
  - **H2: no se replica.** Con n = 49, la mediana de la FAR en la franja es 30,7% para el crudo por máquina y 28,9% para el cociente por máquina (OEM: 4,6%).
  - **Diagnóstico declarado:** la tendencia de Spearman del RMS en la franja es significativa en los cinco rodamientos largos; en 2_3 es creciente (ρ = 0,48 en H, 0,46 en V).

  **Lectura (para discutir, no es veredicto del protocolo; desglose hecho después de ver los resultados):**
  - El exceso de FAR viene de 2_3 (jaula): está al 100% sobre el radio durante toda su franja con todos los modelos, también con el RMS, y todos salen en los registros 146–151 (27% de la vida). El supuesto de que la primera mitad de la vida es sana no se cumple en 2_3, y el diagnóstico declarado lo señalaba.
  - Sin 2_3, la FAR agregada del OEM (H+V, n = 99) sería 1,6–2,3%; la de los modelos por máquina con n = 49 seguiría en 24–29%, sobre todo por 3_2 (≈ 70% de la franja sobre el radio).
  - El veredicto registrado no cambia: "opera en parte".
