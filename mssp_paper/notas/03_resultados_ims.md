# IMS: la prueba exigente de viabilidad, recalibrada con radios certificados

> **Aviso (19-oct, D15):** las cifras de esta nota son de la ejecución publicada (GPU Metal). Las de la referencia en CPU están en [`tablas_ims_certificado.md`](tablas_ims_certificado.md), que se genera desde `results/`. La lectura no cambia salvo donde se marca *Corregido*; por ejemplo, el bearing 4 con radio máximo sale en 707 (45,83 h) en lugar de 705 (46,17 h).

*Rama `mssp`, 11-oct-2026. Sin tablas en esta nota: todas están en
[`tablas_ims_certificado.md`](tablas_ims_certificado.md), generadas por
`reproducibility_package/ims_certified_recalibration.py` desde la caché de
residuos publicada (`results/field_residuals_ims.npz`). `tests/test_generated_notes.py`
comprueba que la tabla coincide byte a byte, que la configuración publicada
reproduce la Tabla 10 del manuscrito y que la salida del bearing 1 no depende
del radio. Si alguna cifra del texto difiere de la tabla, manda la tabla.*

> Los rodamientos son solo validación. IMS es la validación exigente: no hay fallos sembrados, el modelo OEM nunca vio estos rodamientos y hay que detectar una degradación incipiente en un ensayo hasta el fallo.

## Qué se ha hecho

- **Lo que no cambia respecto a lo publicado:** el operador compartido (entrenado solo con simulación), los residuos por registro y la regla de persistencia (8 de 10).
- **Lo que cambia es solo el radio.** Además del radio publicado (cuantil interpolado con parada adaptativa), se calculan cuatro radios certificados:
  - r₍ₖ₎ con n = 49, 99 y 149 (cobertura ≥ 0,98 en esperanza);
  - el radio de tolerancia 0,98/0,95 con n = 149: cubre al menos el 98% con probabilidad ≥ 0,95. Es el que necesita un radio congelado, y es nuevo en `mssp_repro/calibration.py` (`tolerance_rank`, `tolerance_order_statistic`, con tests).
- **Todo sale de la caché de 31 kB.** No hace falta reentrenar ni tener el archivo de IMS.

## Resultados

1. **La configuración publicada se reproduce exactamente:** mismos radios y mismas antelaciones de la Tabla 10. Lo fija un test.
2. **El bearing 1, el único fallo real, es robusto al radio.**
   - Con los cinco radios, sale de lo normal en el **registro 539**, 73,83 h antes del final del registro activo, y no vuelve a entrar (100% de excedencias después).
   - En los registros sanos entre la calibración y el 200 no hay ninguna falsa alarma (0/151, 0/101, 0/51).
   - **Corregido 19-oct (D15, D16):** esto era de la ejecución publicada en GPU Metal y no se sostiene. Con la referencia en CPU las falsas alarmas son 4/151, 1/101 y 2/51 (r₍ₖ₎ con n = 49 / 99 / 149) y 1/51 con tolerancia; esperadas según la garantía: 3,0 / 2,0 / 1,0 / 0,3, con P(≥ observado) = 0,32 / 0,76 / 0,27 / 0,26. Se reportan como recuentos con el esperado, sin adjetivos. Lo robusto es la salida en 539, igual con todos los radios y en las dos plataformas.
   - El resultado de viabilidad en IMS **no dependía del estimador A1**: se mantiene igual con la garantía certificada.
3. **Bearings 2 y 3:** salidas prácticamente iguales a las publicadas, con diferencias de 3–4 registros con r₍ₖ₎, n = 149.
4. **El bearing 4 es el que muestra que el radio importa.**
   - Con los radios que son el máximo de la muestra (n = 49 y tolerancia con n = 149), sale más tarde: registro 705 en lugar de 667, con 46,17 h de antelación en lugar de 52,50 h.
   - Con r₍ₖ₎, n = 99 y 149, tiene 2 falsas alarmas sobre los sanos evaluados.
   - Es el de radio más bajo de los cuatro.
5. **La vida temprana no es intercambiable, pero en la dirección conservadora.**
   - En los bearings 1 y 3 el residuo **baja** con el tiempo durante los primeros 149 registros (Spearman negativo y muy significativo). Parece un rodaje: el radio calculado al principio queda holgado, y por eso la FAR sale 0.
   - Hay que decirlo en el paper: el supuesto de intercambiabilidad no se cumple del todo, y la consecuencia es menos falsas alarmas, no más.
6. **Tres longitudes, dos tipos de garantía** (tabla "Qué garantiza cada longitud de puesta en marcha" en [`tablas_ims_certificado.md`](tablas_ims_certificado.md)):
   - **n = 49:** cobertura ≥ 0,98 *en promedio* sobre puestas en marcha (Prop. 7); es el mínimo absoluto y el radio es el máximo de la muestra.
   - **n = 99:** la *misma* garantía en promedio, pero fuera del rango degenerado (Cor. 7): el radio deja de ser el máximo y varía menos. Es la recomendación del manuscrito.
   - **n = 149:** *otra* garantía. El radio concreto que se congela cubre ≥ 0,98 con probabilidad ≥ 0,95 (tolerancia de Wilks). Es la que responde a la pregunta operativa de si este radio congelado cubre lo que dice.
   - En IMS, con registros cada 10 min, son unas 8, 16,5 y 25 h de puesta en marcha.
   - **El paper no elige una, propone las tres.** Es un compromiso entre tiempo de puesta en marcha y riesgo de falsas alarmas: quien tolere algunas al principio puede operar desde ~8 h; quien necesite garantía sobre el radio congelado espera ~25 h.
   - **Variante natural (a discutir):** empezar a operar con n = 49 y refinar el radio a 99 y 149 a medida que llegan registros. El cuidado es que esos registros posteriores tienen que seguir siendo nominales: si la degradación empieza antes de completar la puesta en marcha, contamina el radio.

## Qué significa para el paper

- **La afirmación de viabilidad en un caso exigente ya está demostrada** y queda más fuerte. Con la garantía certificada, incluso en su versión con confianza, el modelo OEM anticipa unas 74 h el único fallo documentado, sin falsas alarmas en la vida sana.
- **Bearings 2–4** se presentan como salidas de su vecindad nominal hacia el final del ensayo, no como "antelación a fallo". Son útiles para mostrar que el radio es individual (radios distintos con la misma representación) y para ver la sensibilidad al estimador (bearing 4).
- **La Tabla 10 del manuscrito** puede pasar a tener las columnas del radio certificado (n = 99 o n = 149) y una fila de tolerancia. La calibración A1 queda como referencia histórica o desaparece.
- **Comparación con un modelo específico de la máquina en IMS:** hecha. Ver la curva de aprendizaje y el estudio con 5 semillas más abajo (por máquina en crudo y en el cociente, con proyección angular, frente al OEM).
- **Conviene contrastar el registro 539** con el inicio de degradación que reporta la literatura para el bearing 1 de este ensayo, citando la fuente concreta.


## Curva de aprendizaje: por máquina frente a OEM, en crudo y en el cociente (12-oct)

*Tablas en [`tablas_ims_cociente.md`](tablas_ims_cociente.md), generadas por `ims_learning_curve_report.py` desde `results/ims_quotient/learning_curve.json` y comprobadas por `tests/test_generated_notes.py`.*

**Pregunta:** ¿cuánto tiempo de datos de la propia máquina necesita un modelo por máquina para igualar al OEM, y qué cambia si trabaja en el cociente?

**Montaje:**
- Puesta en marcha con 49, 99, 149 y 200 registros (~8, 16,5, 25 y 33 h).
- Radio r₍ₖ₎ sobre esos registros.
- FAR sobre los registros 200–499: ~50 h de vida sana, días después de la puesta en marcha.
- Salida con la regla 8 de 10.
- Cuatro modelos: por máquina en crudo, por máquina en el cociente (proyección + aumento sobre el grupo), OEM en el cociente y OEM publicado.
- Velocidad nominal (2000 rpm): con registros de 1 s, la estimación por registro tiene un ±2% de ruido y metería una perturbación artificial.

**Lo que se ve:**
- **Fallo del bearing 1:** todos los modelos salen entre los registros 527 y 539 (~74 h antes del final). Con este fallo, la detección no distingue modelos.
- **Falsas alarmas en la vida sana:**
  - por máquina en crudo: 1,7–19% en el bearing 1 y 6–8% en el bearing 4, y **no mejora con más datos** (ni con 200 registros, 33 h);
  - por máquina en el cociente: 0–3%, desde 49 registros;
  - OEM en el cociente: 0–2%;
  - OEM publicado: 0–1%.
- **El OEM publicado, en dominio temporal, también funciona.** IMS va a velocidad y frecuencia de muestreo constantes, así que la proyección cambia poco. El simulador publicado ya varía la fase, y con eso el OEM tenía el cociente relevante aprendido de la simulación.
- **Un caso de colapso:** el modelo por máquina en el cociente del bearing 3 con n = 49 no aprendió (más del 98% de varianza sin reconstruir) y se reporta así.

**Respuesta a las dos preguntas:**
1. **¿Un modelo por máquina normal iguala al OEM con 99 registros?** No. Ni con 200 (33 h): sigue con más falsas alarmas en los bearings 1 y 4. El OEM da su punto de operación desde 8 h.
2. **¿El cociente con simulación generaliza mejor que el cociente local?** A lo largo de días de vida sana, **generalizan igual** (0–2% frente a 0–3%; se mantiene con 5 semillas, ver más abajo), igual que en CWRU. La contribución es el cociente; el simulador aporta no tener que entrenar nada en la máquina.

**Matices:**
- Esta sección usa una semilla por modelo local; la variabilidad con 5 semillas está en la sección siguiente.
- La ventana de FAR (200–499) es una elección: empieza tras la puesta en marcha más larga y acaba antes de la degradación documentada del bearing 1.
- Bearings 2–4 no tienen fallo documentado, así que sus salidas (que difieren entre modelos: el 2 sale en 709 con todos los nuevos y en 720–794 con el publicado) indican sensibilidad, no aciertos.
- La vibración real de IMS es casi ruido: los autoencoders por máquina reconstruyen solo el 16–45% de la varianza. Para ellos se ha sustituido el control publicado ("reconstruye al menos la mitad") por uno que solo rechaza el colapso; está documentado en el script y en la tabla.



## Con 5 semillas (12–13 oct)

*Tabla "Variabilidad entre semillas" en [`tablas_ims_cociente.md`](tablas_ims_cociente.md), generada desde `results/ims_quotient/seeds.json` (`ims_seed_study.py`) y comprobada por el test.*

**Qué se ha añadido:** cuatro semillas más para los modelos por máquina (bearings 1 y 4, donde había diferencias) y cuatro más para el OEM en el cociente (los cuatro bearings). Son cinco semillas por modelo en total.

**Lo que se mantiene (media sobre 5 semillas, FAR en los registros 200–499):**
- **Por máquina en crudo:** 2,4–17,5% en el bearing 1 y 5,7–8,0% en el bearing 4, según la longitud de puesta en marcha. Sigue sin alcanzar al OEM con 33 h.
- **Por máquina en el cociente:** 0,7–1,5% (bearing 1) y 1,6–2,0% (bearing 4).
- **OEM en el cociente:** 0,1–1,2% (bearing 1), 1,3–2,3% (bearing 4) y 0% en los bearings 2 y 3.
- **Los rangos del cociente local y del OEM se solapan** en todas las longitudes. "Generalizan igual" se sostiene con la variación entre entrenamientos.
- **Salida del bearing 1:** entre los registros 527 y 539 en todas las semillas y modelos; con el cociente, 538–539 siempre.

**Lo que aclaran las semillas:**
- **La curva cruda no monótona del bearing 1 no es ruido de semilla:** con 99 registros da 10,3–21,7% en las cinco semillas, peor que con 49 (1,7–3,3%). Hipótesis, sin verificar: la vida temprana del bearing 1 no es estacionaria (el residuo baja en los primeros registros, ver la prueba de Spearman). Un modelo crudo calibrado con 99 registros fija un radio que no representa la vida sana posterior. En el cociente esto no aparece.
- **No hay colapsos** en las semillas nuevas. El único sigue siendo el del bearing 3, cociente local, 8 h, semilla 0.

**Para el paper:** las tablas de IMS pueden darse como media [rango] sobre 5 semillas, que es lo mismo que la Tabla 11 publicada.
