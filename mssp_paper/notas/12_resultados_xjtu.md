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

## 2b. Cómo se lee H1: dentro y fuera del diseño (decidido 18-oct)

**El veredicto registrado no cambia: "opera en parte".** Es la aplicación mecánica del criterio (FAR agregada ≤ 5%) y renombrarlo después de ver los datos sería cambiar el criterio. Lo que sí se especifica es *qué parte* no cumple y por qué: el método garantiza algo bajo supuestos declarados, y la parte que no cumple es la que viola uno de ellos.

| Supuesto del método | Qué garantiza si se cumple | ¿Se cumple en XJTU? |
|---|---|---|
| **S1.** Lo que varía está en G: velocidad (constante, nominal), fase, ganancia, offset, frecuencia de muestreo | la sección q lo elimina | sí: condiciones constantes en cada rodamiento |
| **S2.** Lo que no está en G (carga, vía de transmisión) no cambia durante la operación | el radio local sigue siendo válido | sí: carga y montaje fijos en cada ensayo |
| **S3.** La puesta en marcha es intercambiable con la operación sana que sigue | FAR ≤ α (en media con n = 49/99; con confianza 0,95 con n = 149) | **no en 2_3**: el RMS sube de forma monótona desde el ~27% de la vida, así que la franja declarada no es sana. Dudoso en 3_4 (rodaje, en dirección conservadora) |
| **S4.** La puesta en marcha termina antes de que empiece la degradación | el radio describe lo sano | **no en los rodamientos cortos con n = 99**: 1_2, 2_2 y 3_5 (la puesta en marcha ocupa el 61–87% de la vida) |

**Formulación para el paper:**
- **Dentro del diseño** (S1–S4 sin violación visible): el modelo de fábrica, con un cociente simple (sección q) y sin ningún dato del activo, da alarma antes del final en los 13 rodamientos comisionables, y las falsas alarmas agregadas en 2_1, 3_1, 3_2 y 3_4 son 1,6–2,3% (H+V, n = 99; nominal 2%; `tablas_xjtu_discusion.md`, sección 4).
- **Fuera del diseño:** donde falla S3 (2_3) no se pueden medir falsas alarmas, porque la referencia sana no lo es; el método da alarma pronto, igual que el RMS. Donde falla S4, el radio se calcula en parte sobre registros que ya no son de régimen estable.
- **El veredicto registrado** se informa tal cual, con una frase que diga que la parte que no cumple es la que viola S3.

**Condición de honestidad:** la clasificación de 2_3 como fuera de S3 se hizo **después de ver los datos**. El diagnóstico declarado de antemano (Spearman del RMS en la franja) es significativo en los cinco rodamientos largos, porque con cientos de registros cualquier tendencia lo es, así que no sirve como clasificador; lo que distingue a 2_3 es el tamaño del cambio (×1,3 y subiendo), no el p-valor. Se dice así en el texto.

**Sin más experimentos (decidido 18-oct).** Una prueba registrada de S3 basada en tamaño del efecto (por ejemplo, franja válida solo si su RMS mediano queda a ±10% del de la puesta en marcha) y cualquier otro arreglo o mejora del protocolo quedan como **trabajo futuro**, no se ejecutan en este paper.

## 2c. Puesta en marcha corta: el OEM frente al RMS (decidido 18-oct)

**Entra en el paper como resultado**, desde la tabla registrada (`tablas_xjtu.md`, menú de puesta en marcha), sin el desglose posterior:

- Canal H, n = 49: **OEM 4,5–4,6% frente a RMS 8,6%** de falsas alarmas en la franja: 4 puntos porcentuales menos, **la mitad**.
- Se da la tabla completa, no solo esa casilla: canal H con n = 99 y 149 (OEM 4,6–4,8% frente a RMS 6,0% y 5,1%), canal V con n = 49 (4,5–6,0% frente a 5,2%) y la unión H+V con n = 99, que es el análisis principal (5,3–6,1% frente a 5,5%).
- Frase propuesta: *con puesta en marcha corta, el modelo de fábrica tiene la mitad de falsas alarmas que el RMS en el canal horizontal; la diferencia se cierra al alargar la puesta en marcha, y en el vertical no la hay.* La segunda parte es la predicción del método: el OEM trae de fábrica la varianza normal y el RMS tiene que verla en la puesta en marcha.
- Se escribe en puntos porcentuales y en proporción ("4 puntos", "la mitad"), no "un 4% menos".

## 3. Observaciones (tablas en `tablas_xjtu_discusion.md`)

1. **La FAR de H1 se concentra en un rodamiento.** En 2_3 la franja está al 100% por encima del radio con todos los modelos, también con el RMS. En los demás: 2_1 0%, 3_1 0,1%, 3_2 ~2%, 3_4 3–7% (sección 1).
2. **El RMS de 2_3 sube a partir del ~27% de la vida y no vuelve a bajar** (×1,3 al 30%, ×2 al 60%, ×8 al 70%). Lo mismo, con escalón más tardío, en 2_5 (desde el ~40%) y 3_2 (desde el ~50%). Las salidas del OEM en esos tres caen justo en esos escalones (secciones 2 y 3).
3. **Cuándo suena la alarma: el OEM sale casi siempre en el mismo registro que el RMS** (11 de 13, con uno o dos registros de diferencia). El modelo del banco también. La excepción es 1_4 (jaula), donde el OEM da alarma por el canal vertical y el RMS no la da (sección 2). *Esto se refiere solo al momento de la alarma, no a las falsas alarmas: ver la observación 7.*
4. **En los rodamientos cortos, la puesta en marcha con n = 99 ocupa buena parte de la vida** (61% en 1_2 y en 2_2, 87% en 3_5) y en algunos el RMS ya ha cambiado dentro de ella (1_2 sube ×3 entre el 30 y el 40% de la vida, 2_2 ×2 entre el 30 y el 50%; 3_5 empieza a la mitad del nivel que luego tiene). El radio de esos rodamientos se calcula, al menos en parte, sobre registros que no son de régimen estable.
5. **3_4** es el único caso en que algunas semillas dan alarma temprana (registro ~1017) sin que el RMS cambie; el RMS horizontal queda hasta un ~18% por debajo del de la puesta en marcha y el vertical, plano, hasta el ~95% de la vida.
6. **Por máquina, n = 49:** casi toda su FAR viene de 2_3 (100%) y de 3_2 (64–77%); en 2_1, 3_1 y 3_4 es 0%. **H2 se decide en 3_2**, porque en 2_3 todos los modelos están igual.
7. **Falsas alarmas con puesta en marcha corta: el OEM tiene menos que el RMS** (sección 4, sin 2_3). En el canal horizontal, con 49 minutos, OEM 0,8% frente a RMS 5,0%; con 99, 0,8–0,9% frente a 2,2%; con 149, 1,0–1,1% frente a 2,2%. El OEM ya está estable con n = 49; el RMS mejora al ver más puesta en marcha y sigue por encima. En el canal vertical y en la unión H+V los dos quedan parecidos (1–2%).
8. **En 3_2, la puntuación de los modelos por máquina sube un 40–75% justo al salir de la puesta en marcha**, mientras la del OEM sube un 2% y el RMS un 5% (sección 5). En los otros rodamientos con franja sana, todas las puntuaciones *bajan* un 5–20% en ese tramo (como en IMS: dirección conservadora). Por eso los modelos por máquina dan alarma en 3_2 en los registros 66–89 con n = 49 y 177 con n = 99, entre el 3 y el 7% de su vida, cuando el RMS no cambia hasta el ~50%.
9. **Los modelos por máquina, con los registros que tienen, quedan por encima del RMS calibrado igual** (sección 4: con n = 99, 6–15% frente a 2,2% en H). En IMS pasaba algo parecido con el crudo (bearing 1, 200 registros: crudo 11,7%, cociente 2,0%, RMS 0%; semilla 0).

## 4. Posibles lecturas (hipótesis, sin decidir)

- **(a)** En 2_3 (y quizá 2_5 y 3_2) la degradación empezaría pronto y la franja declarada no sería sana; entonces esas "falsas alarmas" serían detecciones. **Lo que apoya:** el perfil del RMS (subida monótona) y que el diagnóstico declarado lo marcaba (ρ = +0,48 en 2_3). **Lo que falta:** cualquier dato independiente del inicio del fallo; sin etiqueta, no se puede distinguir de un cambio de régimen del banco.
- **(b)** En cuanto al *momento* de la alarma, el OEM se comportaría en XJTU como un indicador de energía, como ya vimos en IMS y Ottawa (no en cuanto a las falsas alarmas: observación 7). **Lo que falta:** saber si es por el autoencoder, por la sección o por cómo es la vibración de XJTU.
- **(c)** Con ensayos acelerados, n = 99 sería demasiado largo para los rodamientos cortos y el radio quedaría inflado. **Lo que falta:** medir cuánto, por ejemplo comparando radios con n = 49 y n = 99 en esos rodamientos.
- **(d)** En 3_2, los modelos por máquina fallarían por no ver en 49 minutos la variabilidad de 20 horas de vida sana; con 99 registros mejora (del ~70% al 17–27%), lo que es coherente con esto. **Lo que falta:** saber qué cambia en la señal de 3_2 tras la primera hora; si cambia la forma y no la energía, sería sensibilidad (a un fallo o a un cambio de régimen del banco, sin poder distinguirlos).
- **(e)** El sesgo de calibrar con los mismos registros con que se entrena **parece poco probable** como explicación general: en los rodamientos estables las puntuaciones bajan tras la puesta en marcha, no suben (observación 8).
- **(f)** Puesta en marcha corta (*cold start*): el OEM trae de fábrica la varianza normal y el RMS, o cualquier radio local, tiene que verla en la puesta en marcha; eso explicaría la observación 7. **Lo que falta:** es una lectura de un desglose posterior y depende del canal (en V no hay diferencia).
- **(g)** Hipótesis del autor (18-oct): con *toda* la varianza normal, un autoencoder por máquina sería mucho mejor que el RMS. **Estado:** los datos actuales no la apoyan ni la descartan; ninguna configuración ha visto toda la varianza normal, y las que han visto más (n = 99 en XJTU, 200 registros en IMS) siguen por encima del RMS (observación 9). Probarla exigiría un brazo techo (autoencoder por máquina con toda la vida sana conocida) registrado antes. **Fuera del foco actual (decidido 18-oct): solo se deja escrito.**

## 5. Preguntas abiertas para decidir juntos

1. ~~¿Cómo se presenta H1 en el paper?~~ **Decidido 18-oct:** veredicto registrado + especificación dentro/fuera del diseño (sección 2b).
2. ¿Hace falta una forma independiente de saber cuándo empieza la degradación en XJTU (literatura sobre el *first predicting time* de cada rodamiento, por ejemplo) antes de decir nada sobre 2_3?
3. ¿Se discute la puesta en marcha larga en ensayos acelerados como limitación del menú 49/99/149?
4. ¿Queremos entender por qué el OEM ve energía y no forma, o se queda como está (D7)?
