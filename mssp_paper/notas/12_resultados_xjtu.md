# XJTU-SY: qué salió y qué no sabemos todavía

> **PARA DISCUSIÓN. No hay conclusiones en esta nota.** Los veredictos son los del protocolo ([`09_protocolo_xjtu.md`](09_protocolo_xjtu.md), tablas en [`tablas_xjtu.md`](tablas_xjtu.md)) y no cambian. Todo lo demás son observaciones y preguntas hechas *después* de ver los resultados, con sus tablas en [`tablas_xjtu_discusion.md`](tablas_xjtu_discusion.md) (generadas por `xjtu_discussion.py`). Nada de esto va al paper hasta discutirlo.

## 1. Qué se midió, en palabras

- **Puesta en marcha.** Para cada rodamiento se toman sus primeros n registros (n = 49, 99 o 149; un registro por minuto) y, con la puntuación de un modelo, se calcula el **radio**: un umbral tal que, si esos n registros son sanos e intercambiables con los que vienen, solo un 2% de los registros sanos futuros lo superarían.
- **Salida.** El primer registro, después de la puesta en marcha, en el que 8 de los 10 últimos superan el radio. Es la alarma del método.
- **"Sale antes del final"** quiere decir que hubo alarma antes de que acabara el ensayo. No dice si la alarma fue en el momento correcto, porque XJTU no etiqueta cuándo empieza el fallo.
- **Franja sana declarada.** Para poder medir falsas alarmas sin etiquetas, el protocolo supuso que la primera mitad de la vida de los cinco rodamientos más largos es sana, y midió qué fracción de esos registros supera el radio (FAR).
- **Modelos.** OEM (entrenado solo con el simulador), modelo del banco CWRU, indicadores clásicos (RMS, curtosis, cresta, envolvente) y modelos por máquina (entrenados con los primeros n registros del propio rodamiento, en crudo o en el cociente).

## 2. Lo que dice el protocolo (hechos)

- **H1, opera en parte.** El OEM, con los dos canales y n = 99, da alarma antes del final en los 13 rodamientos comisionables y en las 5 semillas, pero la FAR en la franja sana es 5,3–6,1%, por encima del 5% fijado.
- **H2, no se replica.** Con n = 49, los modelos por máquina tienen una FAR en la franja de ~30% (crudo 30,7%, cociente 28,9%); el OEM, 4,6%.

## 3. Observaciones (tablas en `tablas_xjtu_discusion.md`)

1. **La FAR de H1 se concentra en un rodamiento.** En 2_3 la franja está al 100% por encima del radio con todos los modelos, también con el RMS. En los demás: 2_1 0%, 3_1 0,1%, 3_2 ~2%, 3_4 3–7% (sección 1).
2. **El RMS de 2_3 sube a partir del ~27% de la vida y no vuelve a bajar** (×1,3 al 30%, ×2 al 60%, ×8 al 70%). Lo mismo, con escalón más tardío, en 2_5 (desde el ~40%) y 3_2 (desde el ~50%). Las salidas del OEM en esos tres caen justo en esos escalones (secciones 2 y 3).
3. **El OEM sale casi siempre en el mismo registro que el RMS** (11 de 13, con uno o dos registros de diferencia). El modelo del banco también. La excepción es 1_4 (jaula), donde el OEM da alarma por el canal vertical y el RMS no la da (sección 2).
4. **En los rodamientos cortos, la puesta en marcha con n = 99 ocupa buena parte de la vida** (61% en 1_2 y en 2_2, 87% en 3_5) y en algunos el RMS ya ha cambiado dentro de ella (1_2 sube ×3 entre el 30 y el 40% de la vida, 2_2 ×2 entre el 30 y el 50%; 3_5 empieza a la mitad del nivel que luego tiene). El radio de esos rodamientos se calcula, al menos en parte, sobre registros que no son de régimen estable.
5. **3_4** es el único caso en que algunas semillas dan alarma temprana (registro ~1017) sin que el RMS cambie; el RMS horizontal queda hasta un ~18% por debajo del de la puesta en marcha y el vertical, plano, hasta el ~95% de la vida.
6. **Por máquina, n = 49:** casi toda su FAR viene de 2_3 (100%) y de 3_2 (64–77%); en 2_1, 3_1 y 3_4 es 0%.

## 4. Posibles lecturas (hipótesis, sin decidir)

- **(a)** En 2_3 (y quizá 2_5 y 3_2) la degradación empezaría pronto y la franja declarada no sería sana; entonces esas "falsas alarmas" serían detecciones. **Lo que apoya:** el perfil del RMS (subida monótona) y que el diagnóstico declarado lo marcaba (ρ = +0,48 en 2_3). **Lo que falta:** cualquier dato independiente del inicio del fallo; sin etiqueta, no se puede distinguir de un cambio de régimen del banco.
- **(b)** El OEM se comportaría en XJTU como un indicador de energía, como ya vimos en IMS y Ottawa. **Lo que falta:** saber si es por el autoencoder, por la sección o por cómo es la vibración de XJTU.
- **(c)** Con ensayos acelerados, n = 99 sería demasiado largo para los rodamientos cortos y el radio quedaría inflado. **Lo que falta:** medir cuánto, por ejemplo comparando radios con n = 49 y n = 99 en esos rodamientos.
- **(d)** Los modelos por máquina fallarían en 3_2 por no ver en 49 minutos la variabilidad de 20 horas de vida sana. **Lo que falta:** verlo en las puntuaciones a lo largo de la franja.

## 5. Preguntas abiertas para decidir juntos

1. ¿Cómo se presenta H1 en el paper: solo el veredicto, o el veredicto más la FAR por rodamiento, más algo de lo anterior marcado como posterior?
2. ¿Hace falta una forma independiente de saber cuándo empieza la degradación en XJTU (literatura sobre el *first predicting time* de cada rodamiento, por ejemplo) antes de decir nada sobre 2_3?
3. ¿Se discute la puesta en marcha larga en ensayos acelerados como limitación del menú 49/99/149?
4. ¿Queremos entender por qué el OEM ve energía y no forma, o se queda como está (D7)?
