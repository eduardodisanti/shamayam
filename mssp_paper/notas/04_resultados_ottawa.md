# Ottawa: velocidad variable dentro del registro (13-oct)

*Sin tablas a mano: todas están en [`tablas_ottawa.md`](tablas_ottawa.md), generadas por `ottawa_report.py` desde `results/ottawa/results.json` (`ottawa_variable_speed.py`) y comprobadas byte a byte por `tests/test_generated_notes.py`. Una semilla (0 para los modelos por máquina, 42 para el OEM); las semillas 1–4 están en ejecución. Si alguna cifra del texto difiere de la tabla, manda la tabla.*

> Los rodamientos son solo validación. Ottawa cubre el flanco que CWRU e IMS no tocaban: la velocidad cambiando *dentro* de cada registro (factor ~2, 10–29 Hz), que es la parte de G que más distingue el método.

## Qué se ha hecho

- **Datos.** `Ottawa_Bearing_TimeVaryingSpeed` (Mendeley v2, CC BY 4.0), fijado por manifiesto. 60 registros de 10 s a 200 kHz: sano y cuatro fallos (pista interior, pista exterior, bola, combinado); cuatro perfiles de velocidad (sube, baja, sube y baja, baja y sube); tres ensayos cada uno. Encoder de 1024 pulsos por vuelta.
- **Proyección con velocidad variable.** El ángulo del eje se lee de los flancos del encoder. El remuestreo angular se hace en dos etapas: un paso bajo fijo en tiempo y una diezma en el dominio del ángulo, cuyo filtro es fijo en órdenes e igual a cualquier velocidad. Lo comprueban tests sintéticos: un barrido 12→28 Hz y su inverso dan las mismas ventanas (<2% de diferencia).
- **Secciones comparadas.**
  - **Tiempo:** sin sección.
  - **Cociente (q):** la proyección angular.
  - **Cociente + ganancia (qg):** q seguido de quitar la media y dividir por el RMS de cada ventana, que es la sección del offset y la ganancia de G.
- **Modelos.**
  - Por máquina: en crudo; en crudo con aumento; en el cociente; en el cociente con ganancia. "Crudo + aumento" y "cociente" difieren solo en la proyección angular.
  - OEM entrenado solo con simulación, en q y en qg. El simulador usa solo hechos documentados de la adquisición (200 kHz, eje nominal 20 Hz) y sus valores por defecto para todo lo demás.
  - Dos rasgos clásicos con la misma calibración: el RMS en tiempo y la curtosis en el cociente.
- **Puesta en marcha.** El ensayo 1 de un perfil (un registro, ~66 ventanas, cubre parte del rango de velocidad) o los cuatro ensayos 1 (todo el rango). El radio es r₍ₖ₎.
- **Evaluación.** Sanos de prueba: los 8 registros de los ensayos 2 y 3. Se mide la FAR por ventana (total y por banda de velocidad), los registros sanos con alarma persistente (8 de 10) y, por tipo de fallo, los registros detectados y el AUROC.

## Lo que se ve

1. **En este banco la velocidad no es solo una escala de tiempo.**
   - La amplitud de la vibración sube con la velocidad: la correlación del RMS con la velocidad pasa de 0,95 en todos los registros sanos.
   - La proyección angular quita la parte temporal, pero no la ganancia ni el desplazamiento en órdenes de las resonancias fijas en Hz.
   - La comparación limpia lo confirma. "Crudo + aumento" y "cociente" (solo cambia la proyección) dan FAR parecidas: con los cuatro ensayos, 9,5% frente a 8,2%; con C-1, 13,6% frente a 14,3%.
2. **Las falsas alarmas vienen de las velocidades que la puesta en marcha no vio.**
   - Con A-1 (14–24 Hz), la banda de 25–30 Hz da 86–100% de FAR en todos los modelos sensibles a la energía.
   - Con los cuatro ensayos, que cubren todo el rango, baja a 3–12% en total.
   - Es lo mismo que la carga en CWRU: el radio local certifica las condiciones representadas en la puesta en marcha. Si la operación sale de ese rango, las ventanas de puesta en marcha dejan de ser intercambiables con las de operación y la garantía no se aplica.
3. **La sección de ganancia aplana la FAR entre bandas, pero no basta.**
   - El OEM en qg tiene la FAR más plana: 0–10,9% en cada banda y ningún registro sano con alarma persistente en ningún escenario. Es la parte de ganancia de lo que hace la velocidad, quitada por la sección.
   - Pero su detección se hunde (AUROC 0,41–0,62). Normalizado, el simulador ya no se parece al banco real: el residuo mide el desajuste del modelo y no el fallo.
   - El modelo por máquina en qg conserva la detección de pista interior, bola y combinado. Sin embargo, sube su FAR a 10–15 Hz, donde la puesta en marcha tuvo pocas ventanas.
4. **Ninguna representación detecta todos los fallos.**
   - Pista exterior: invisible para todo modelo de residuo o de energía (AUROC 0,26–0,57), pero la curtosis en el cociente la detecta (0,988).
   - Bola: al revés. La curtosis no la ve (0,51) y los autoencoders sí (≈0,8).
   - Pista interior y combinado son fáciles para todos (≥0,99), salvo el OEM en qg.
   - Con los cuatro ensayos, la curtosis en el cociente da 4,8% de FAR, 0 de 8 registros sanos con alarma y detecta interior, exterior y combinado en 12 de 12. El OEM en q da 4,3% de FAR, 1 de 8 registros, e interior y combinado en 12 de 12.
5. **Entrenamiento.** Como en IMS, la vibración es casi ruido: los autoencoders por máquina dejan sin reconstruir entre el 69% y el 90% de la varianza. Hubo tres colapsos de 20 (A-1 crudo + aumento; B-1 crudo; B-1 cociente), que se reportan como tales; las semillas dirán si es inestabilidad del entrenamiento.

## Qué significa para el paper (para discutir)

- **El flanco de la velocidad queda cubierto, pero no como esperábamos.**
  - La proyección angular funciona (lo prueban los tests) y es necesaria para que la representación tenga sentido con velocidad variable.
  - En un banco real, sin embargo, la velocidad actúa también como ganancia y mueve las resonancias.
  - Lo honesto es declarar que G tiene una parte que la sección angular no cubre, y que la puesta en marcha debe cubrir el rango de velocidad de operación. Si no, el radio debe condicionarse a la velocidad, que en este caso se mide.
  - Encaja con la tesis de viabilidad y con los límites ya acordados: es otra variable fuera del grupo, como la carga.
- **La ganancia es el ejemplo perfecto de lo que dijimos.** Cocientar quita una variación (la FAR se aplana) y a la vez quita información (el OEM pierde detección). Es el coste de identificabilidad, medido.
- **El resultado de los rasgos clásicos apoya D7 y el tono de respeto a la práctica clásica.** El esquema (modelo estilo OEM + radio local) funciona con distintas representaciones, y la curtosis, que tiene décadas de uso en rodamientos, es aquí la mejor en pista exterior. No vendemos el autoencoder: vendemos el cociente y la calibración.
- **Siguiente paso natural, si lo quieres:** radio condicionado a la velocidad (un r₍ₖ₎ por banda, con la velocidad del encoder). Es barato porque las semillas ya guardan las puntuaciones por ventana.

## Pendiente

- Semillas 1–4 (en ejecución, varias horas en esta máquina): variabilidad y si los colapsos se repiten.
- Variante sin encoder (velocidad estimada de la propia vibración), si se decide que entra.
