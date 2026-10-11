# IMS: la prueba exigente de viabilidad, recalibrada con radios certificados

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
   - El resultado de viabilidad en IMS **no dependía del estimador A1**: se mantiene igual con la garantía certificada.
3. **Bearings 2 y 3:** salidas prácticamente iguales a las publicadas, con diferencias de 3–4 registros con r₍ₖ₎, n = 149.
4. **El bearing 4 es el que muestra que el radio importa.**
   - Con los radios que son el máximo de la muestra (n = 49 y tolerancia con n = 149), sale más tarde: registro 705 en lugar de 667, con 46,17 h de antelación en lugar de 52,50 h.
   - Con r₍ₖ₎, n = 99 y 149, tiene 2 falsas alarmas sobre los sanos evaluados.
   - Es el de radio más bajo de los cuatro.
5. **La vida temprana no es intercambiable, pero en la dirección conservadora.**
   - En los bearings 1 y 3 el residuo **baja** con el tiempo durante los primeros 149 registros (Spearman negativo y muy significativo). Parece un rodaje: el radio calculado al principio queda holgado, y por eso la FAR sale 0.
   - Hay que decirlo en el paper: el supuesto de intercambiabilidad no se cumple del todo, y la consecuencia es menos falsas alarmas, no más.
6. **Coste de la garantía con confianza:** n = 149 registros a 10 min son unas 25 h de commissioning, frente a unas 8 h con n = 49. Es el precio operativo de pasar de "en esperanza" a "con confianza del 95%".

## Qué significa para el paper

- **La afirmación de viabilidad en un caso exigente ya está demostrada** y queda más fuerte. Con la garantía certificada, incluso en su versión con confianza, el modelo OEM anticipa unas 74 h el único fallo documentado, sin falsas alarmas en la vida sana.
- **Bearings 2–4** se presentan como salidas de su vecindad nominal hacia el final del ensayo, no como "antelación a fallo". Son útiles para mostrar que el radio es individual (radios distintos con la misma representación) y para ver la sensibilidad al estimador (bearing 4).
- **La Tabla 10 del manuscrito** puede pasar a tener las columnas del radio certificado (n = 99 o n = 149) y una fila de tolerancia. La calibración A1 queda como referencia histórica o desaparece.
- **Pendiente para cerrar del todo la comparación de viabilidad en IMS:** un modelo específico entrenado con la vida temprana del bearing 1, el equivalente a la referencia de CWRU. Necesita el archivo bruto de IMS. También aplicar la proyección angular, por coherencia, si se adopta como parte del método (D1).
- **Conviene contrastar el registro 539** con el inicio de degradación que reporta la literatura para el bearing 1 de este ensayo, citando la fuente concreta.
