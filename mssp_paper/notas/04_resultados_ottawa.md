# Ottawa: velocidad variable dentro del registro (13-oct)

*Sin tablas a mano: todas están en [`tablas_ottawa.md`](tablas_ottawa.md), generadas por `ottawa_report.py` desde `results/ottawa/results.json` (`ottawa_variable_speed.py`) y comprobadas byte a byte por `tests/test_generated_notes.py`. La tabla principal es de una semilla (0 para los modelos por máquina, 42 para el OEM) y los cinco escenarios de puesta en marcha. La variabilidad entre semillas (0–4) y el apéndice de velocidad se hacen para los dos escenarios clave (A-1 y los cuatro ensayos 1) y salen en la misma tabla generada cuando terminan. Si alguna cifra del texto difiere de la tabla, manda la tabla.*

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
   - La amplitud de la vibración sube con la velocidad: ventana a ventana, la correlación del RMS con la velocidad está entre 0,92 y 0,99 en los 12 registros sanos, y el RMS crece aproximadamente como la velocidad elevada a 1,05–1,5 (tabla del apéndice).
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

## Cómo lo leemos (acordado 13-oct)

- **El método no falla; el espacio cociente está incompleto.** La sección angular elimina la parte *cinemática* de la velocidad (el cambio de escala temporal): lo prueban los tests sintéticos y lo confirma que el contenido ligado al eje cae en órdenes fijos. No elimina la parte *dinámica*: más velocidad, más vibración, y otra excitación de las resonancias. Hemos declarado una acción de G más pobre que la real. El cociente es tan completo como la acción de G que se declara.
- **Un modelo por máquina tiene la misma dificultad.** Las velocidades no vistas en la puesta en marcha son un problema para cualquier método calibrado localmente: con A-1, en la banda de 25–30 Hz, el modelo por máquina en crudo y en el cociente dan 100% de FAR, igual que el RMS, y el OEM en el cociente 86%. El modelo por máquina nunca queda mejor que el OEM. La comparación sigue siendo justa: aquí el cociente no aporta, pero tampoco pierde.
- **La normalización de ganancia por ventana es demasiado.** Cocienta la ganancia entera, incluida la energía del fallo, y por eso el OEM pierde la detección. Lo que habría que quitar es solo la ganancia que impone la velocidad (una ley de la amplitud nominal con la velocidad, un subgrupo ligado a la velocidad medida), no toda la ganancia libre. Queda como trabajo futuro.
- **No modificamos ahora el emulador ni el cocientador.** Sería un ajuste hecho después de ver el fallo; el emulador simula ±10% de velocidad y Ottawa varía el doble, y darle física de amplitud es física nueva. Un fallo medido y explicado aporta más credibilidad a una tesis de viabilidad que un parche.

## Cómo va en el paper (acordado 13-oct)

- **Resultados (§9.x Ottawa):** el resultado tal cual, con una sola frase de límite: *la sección angular elimina la parte cinemática de la velocidad, no la dinámica (Apéndice X)*.
- **Discusión (§10):** el cociente es tan completo como la acción de G que se declara; Ottawa es el caso en que la declarada se queda corta. Junto a la carga: lo que no está en G va al radio, y el radio solo certifica lo que estaba en la puesta en marcha. Consecuencia operativa: la puesta en marcha debe cubrir el rango de velocidad de operación (con los cuatro ensayos, la FAR baja al 3–12%).
- **Limitaciones (§11):** la parte dinámica de la velocidad no está en G; la sección de ganancia completa sacrifica identificabilidad.
- **Apéndice X, "La velocidad más allá del cambio de escala temporal".** *No se propone como método*: es análisis del fallo. Contenido, todo generado (sección "Apéndice" de [`tablas_ottawa.md`](tablas_ottawa.md)):
  1. La amplitud sigue a la velocidad: correlación y exponente por registro sano.
  2. FAR por banda de velocidad sumada sobre semillas, con su dispersión entre bandas: el fallo se concentra en las velocidades no vistas.
  3. La sección de ganancia: aplana la FAR entre bandas pero el OEM pierde la detección. El coste de identificabilidad, medido.
  4. Radio condicionado a la velocidad, como análisis. Condicionar no crea cobertura donde no la hay: si la puesta en marcha no tiene ventanas en una banda, esa banda no tiene radio. Y cada banda necesita su propio mínimo (49 ventanas para la garantía en promedio), de modo que la puesta en marcha tiene que barrer el rango de velocidad con suficientes ventanas en cada banda. La tabla da cuántas ventanas de prueba quedan sin cubrir.
  5. Trabajo futuro: completar la acción de G con la parte dinámica.
- **Rasgos clásicos.** Que la curtosis en el cociente sea la mejor en pista exterior y los autoencoders en bola apoya D7 y el tono acordado: el esquema (modelo estilo OEM + radio local) funciona con distintas representaciones. No vendemos el autoencoder, sino el cociente y la calibración.

## Pendiente

- Semillas 0–4 de los escenarios A-1 y los cuatro ensayos 1, con las puntuaciones por ventana guardadas (la semilla 0 se repite para guardarlas y, de paso, comprobar que el resultado se reproduce). Al terminar: `ottawa_speed_appendix.py` y `ottawa_report.py`, y comprobar si los colapsos se repiten.
- Variante sin encoder (velocidad estimada de la propia vibración): no entra en este paper salvo que se decida lo contrario.
