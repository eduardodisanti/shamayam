# Qué escribir y cómo: propuesta para discutir

*Borrador de discusión. No toca el `.tex`. Se apoya en
[`01_resultados_cwru.md`](01_resultados_cwru.md) y en la revisión del 9-oct.*

## 1. La historia del paper después de estos resultados

**Antes:** una representación compartida entrenada en simulación detecta el 100% de los fallos en CWRU, y basta con calibrar localmente el radio con 49 observaciones.

**Ahora,** lo que los datos sostienen:

1. **El cociente se implementa, no solo se declara.** La velocidad y la frecuencia de muestreo se eliminan con una sección explícita del mapa cociente: el remuestreo angular. Es una construcción, no una hipótesis sobre lo que aprende el autoencoder.
2. **Lo que no está en el grupo queda en la escala local.** La carga cambia el nivel nominal (radios ×1,5 entre condiciones de CWRU) y el radio no se transfiere entre condiciones. Por eso la calibración es local, y esto ahora tiene una razón física, no solo empírica.
3. **La calibración es distribution-free, pero marginal.** Con n = 49 la cobertura realizada es aleatoria: Beta(49, 1), con P(FAR > 5%) ≈ 8%. Para una garantía con confianza hace falta n ≥ 149 (contenido 0,98, confianza 0,95). El paper debe dar las dos versiones y decir cuál pide la monitorización con radio congelado.
4. **La afirmación es de viabilidad, no de superioridad.** Un modelo estilo OEM, entrenado sin datos del activo y calibrado localmente sin etiquetas, alcanza el punto de operación de un modelo específico entrenado con el histórico del activo. CWRU lo muestra en un caso fácil; IMS (detección temprana en run-to-failure) y el dominio nuevo en casos exigentes. Los indicadores clásicos con calibración local no son rivales a batir: son otros modelos estilo OEM, y que funcionen refuerza que lo que hace viable el despliegue es el esquema.

> **Alcance:** los rodamientos son *solo* validación. El paper es de método para cualquier activo; CWRU e IMS se usan porque son públicos y conocidos, no porque el paper sea de rodamientos. Hay que decirlo en la introducción y en el título del §9 ("Validation on bearing data").

> **Propuesta de tesis en una frase:** *es posible desplegar en un activo nuevo un detector de anomalías estilo OEM, sin datos ni etiquetas de ese activo: las invariancias conocidas se implementan con una sección del cociente y todo lo demás queda en un radio local, que se certifica sin etiquetas con un número de observaciones que el paper calcula.*

## 2. Sección por sección

| Sección actual | Qué hacer | Por qué |
|---|---|---|
| **Título** | Quitar "Classification" y "Functional Manifolds". Propuesta: *"Label-free commissioning of shared anomaly detectors: quotient sections and distribution-free local radii"* | No hay experimentos de clasificación, y la Remark 3 dice que no son variedades |
| **Abstract / highlights** | Quitar "49 observations suffice to certify". Poner: "49 for coverage in expectation, 149 for 95% confidence"; detección demostrada en IMS y en el dominio nuevo; CWRU como ilustración | Lo pide la sección 5 de 01_resultados |
| **§1 Introducción** | Mantener el planteamiento como problema inverso. Añadir el párrafo "sección explícita frente a invariancia aprendida" | Es el aporte conceptual nuevo |
| **§4–5 Cociente** | Recortar. Dejar: (a) grupo declarado = {fase, ganancia, velocidad, frecuencia de muestreo}; (b) **sección** = remuestreo angular + normalización; (c) qué no está en G (carga, cadena de adquisición, resonancias fijas en Hz) y por qué va al radio local. Pasar Arzelà–Ascoli y la topología del cociente a un apéndice | Es lo que decide el pipeline. La topología fina no |
| **§6 Clasificación** | Pasar a la discusión o eliminar | No hay experimentos |
| **§7 Calibración** | Núcleo del paper. Prop. 7 (marginal) + **nuevo corolario β-contenido/γ-confianza** + la longitud de commissioning que sale de cada uno. Unificar el lenguaje de novedad: la contribución es identificar y usar estas garantías, no el teorema | Sección 5 de 01_resultados y punto 2 de la revisión |
| **§7.5 Regla de parada** | Corregir la frase del sesgo (es conservadora, no a la baja). Decir que con < ~70 sanas la regla puede no converger (1797) | 01_resultados §5 |
| **§8 Protocolo** | Nuevo §8.x "Proyección angular" (estimación de velocidad, 400 muestras/vuelta, 3 vueltas, simulador proyectado igual). Decir explícitamente: Normal CWRU a 48 kHz, emparejada con `DE48` | Reproducibilidad, y Smith & Randall |
| **§9.3 CWRU** | Reescribir entera (ver punto 3) | |
| **§9.4 IMS** | Solo el bearing 1 es fallo. Recalcular con proyección, r₍ₖ₎ y n ≥ 99. Corregir "clearing the degenerate range" | Revisión, punto 1 |
| **§9.x Dominio nuevo** | Añadir | Ver punto 5 |
| **§10 Discusión** | Añadir "qué no está en el grupo" y la lectura de CWRU como benchmark trivial para detección | |
| **§11 Limitaciones** | Añadir: proyección aproximada para resonancias; garantía marginal; CWRU con pocas sanas | |

## 3. Cómo contar CWRU (propuesta)

Que CWRU sea trivial para detectar no es un problema si se cuenta bien. Lo usaría para lo que sí demuestra:

1. **Viabilidad frente a la referencia específica.** Modelo OEM + radio local frente a un modelo entrenado con el histórico de cada condición (Tabla 7 rehecha en la configuración corregida). El mensaje es "llega al mismo punto de operación", no "es mejor".
2. **Tabla de AUROC** (autoencoder compartido, RMS, curtosis, cruces por cero) en la configuración corregida. Se dice abiertamente que la detección en CWRU es fácil: todos los modelos compartidos de energía llegan a 1,000. Esto vacuna contra el revisor que suspira al leer "CWRU" y remite la demostración exigente a IMS, que ya está en el manuscrito y ahora recalibrada con radios certificados (03_resultados_ims).
3. **Tabla de transferencia del radio entre condiciones.** Es la evidencia de que la escala es local y de que la carga no está en G.
4. **Calibración con FAR en sanas no vistas e intervalos.** Se presenta como ilustración del procedimiento con la incertidumbre real. 1797 va aparte, como condición con datos insuficientes.
5. **Una frase metodológica sobre el emparejamiento Normal/`DE48`,** citando a Smith & Randall. ¿Contamos que la versión anterior usaba `DE12`? Yo no lo contaría como historia. Bastaría con la nota metodológica y quizá con el control de cruces por cero como figura pequeña: "por qué hay que emparejar adquisiciones". Esto lo decidimos juntos.

## 4. Decisiones abiertas

| # | Decisión | Opciones | Mi recomendación |
|---|---|---|---|
| D1 | ¿La proyección angular es parte del método o un preprocesado? | Método (en §5) / preprocesado (en §8) | **Método.** Es la sección del cociente, y da coherencia a la teoría |
| D2 | ¿Aplicamos la proyección también a IMS? | Sí / no | **Sí,** por coherencia. IMS va a velocidad constante, así que el cambio debería ser pequeño |
| D3 | ¿1797 rpm dentro o fuera? | Dentro con etiqueta / fuera de calibración | Dentro en AUROC, fuera en la tabla de calibración |
| D4 | ¿Qué garantía es la "oficial"? | Marginal (49) / con confianza (149) | **Las dos.** 149 como recomendación operativa, 49 como mínimo absoluto |
| D5 | ¿Qué dominio nuevo? | Point machines públicas (CRPM) / circuitos de vía (privado) / otro | CRPM, por ser público y no de rodamientos. Lo vemos |
| D6 | ¿Contamos el error de `DE12`? | Nota metodológica / sección / nada | Nota metodológica + figura pequeña opcional |
| D7 | ¿Qué papel tienen RMS, curtosis, etc.? | Rivales a batir / otros modelos estilo OEM | **Otros modelos estilo OEM** con la misma calibración local, en todas las tablas. No se compite con ellos: muestran que el esquema funciona con distintas representaciones |
| D8 | ¿Semillas? | Una / cinco | Cinco para el operador compartido. La tabla de estabilidad ya existe para IMS |

## 5. Experimentos pendientes, por orden

0. ~~**Referencia específica por activo en CWRU corregido (B).**~~ **Hecho** (11-oct): mismo punto de operación que el modelo OEM en las cuatro condiciones. Ver 01_resultados, "Resultado principal".
1. **IMS.** ✔ Recalibración certificada desde la caché (11-oct, ver 03_resultados_ims): el bearing 1 sale en el registro 539 con todos los radios. Pendiente, con el archivo bruto:
   - referencia específica: un modelo entrenado con la vida temprana del bearing 1 (comparación de viabilidad, como en CWRU);
   - otros modelos estilo OEM (RMS, curtosis, envolvente) con la misma calibración;
   - proyección angular, si se adopta D1.
2. **Dominio nuevo,** con el mismo protocolo.
3. **Corolario β-contenido** (un test en `tests/test_coverage_exact.py`, además de la prueba en el `.tex`).
4. **Cinco semillas** del operador en órdenes, para ver cuánto cambian los radios de CWRU.
5. **Unificar cifras:** todas las tablas generadas desde una sola ejecución (como ya hace el paquete).

## 6. Cifras e inconsistencias que hay que limpiar al reescribir

Son de la revisión del 9-oct y siguen pendientes:
- lead times de IMS (14–74 h, 14,3–73,8, 14,5–74,0, 14,7–74,3);
- factor PCA frente al autoencoder (380×, 381,6×, 382×, 240×);
- "four / thirty / twenty-five orders";
- dispersiones de radios (2,97 frente a 2,49; 2,24 frente a 2,8);
- §9.4 "clearing the degenerate range" (es al revés);
- §7.5 sesgo a la baja frente a conservador;
- "falsification mechanism" → "refutation test", y la ablación por permutación, que no testea la intercambiabilidad: sustituir por Spearman cronológico (ya calculado en CWRU, en 01_resultados §5).

## 7. Cómo propongo trabajar el texto

- Tú escribes en LaTeX; yo propongo **ediciones puntuales** por sección, no reescrituras completas.
- **Orden:** §7 (calibración, que es lo más sólido) → §5 (sección del cociente) → §8–9 (protocolo y resultados, cuando estén IMS y el dominio nuevo) → introducción y abstract al final.
- **Ninguna cifra a mano:** cada tabla sale de un script, como ya hace `make_tables.py`. `cwru_projection_report.py` sigue ese patrón.
