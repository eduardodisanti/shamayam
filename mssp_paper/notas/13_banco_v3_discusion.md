# Banco v3: qué salió y qué no sabemos todavía

> **PARA DISCUSIÓN. No hay conclusiones en esta nota.** El veredicto es el del protocolo ([`10_protocolo_banco_v3.md`](10_protocolo_banco_v3.md), tablas en [`tablas_banco_v3.md`](tablas_banco_v3.md)) y no cambia. La única tabla nueva está en [`tablas_banco_v3_discusion.md`](tablas_banco_v3_discusion.md) (generada por `bench_v3_discussion.py`), hecha después de ver los resultados.

## 1. Qué se probó, en palabras

- Igual que v2: un modelo de fábrica aprendido **solo con lo sano del banco CWRU**, en el cociente completo (preblanqueo, que quita la vía de transmisión y la energía, más remuestreo angular), aplicado a máquinas que nunca vio (Ottawa, IMS y XJTU).
- Lo único que cambia respecto a v2 es **lo que ve el autoencoder**: en vez de la forma de onda blanqueada, su espectro de la envolvente en órdenes (1200 valores, ventanas de 30 vueltas).
- **Controles:** el mismo autoencoder entrenado con ruido blanco (C-ruido) y con el simulador (C-simulador). **Techo:** un modelo por máquina de Ottawa, *in-sample*. **Referencias sin aprendizaje:** curtosis e indicador de envolvente en las mismas ventanas.

## 2. Lo que dice el protocolo (hechos)

- **El modelo del banco no aprende** en ninguna de las 5 semillas (fracción no reconstruida 0,995–1,008). Se aplica la condición registrada: **H1v3 no evaluable con este autoencoder**; H2v3 y H3v3 sin modelo que evaluar.
- Es el mismo desenlace que v2: con este autoencoder, el banco en el cociente completo no se puede representar, sea como forma de onda (v2) o como espectro de la envolvente (v3).

## 3. Observaciones

1. **Ottawa (AUROC por tipo de fallo; FAR 0/51 en todos):**

   | | pista interior | bola | combinado | pista exterior |
   |---|---|---|---|---|
   | C-ruido | 1,000 | 0,602 | 0,998 | 1,000 |
   | C-simulador | 1,000 | 0,68 | 0,63–0,65 | 0,94–0,96 |
   | techo por máquina | 1,000 | 0,79 | 0,997 | 1,000 |
   | curtosis (30 vueltas) | 0,996 | 0,377 | 1,000 | 1,000 |
   | envolvente (30 vueltas) | 1,000 | 0,742 | 0,973 | 0,998 |

   La bola sigue siendo el fallo que casi nada separa, como en v1 y v2.
2. **Con ventanas de 30 vueltas, las referencias clásicas separan mejor que con las de 3 vueltas de v2:** la curtosis pasa de 0,963 / 0,995 / 0,993 a 0,996 / 1,000 / 1,000 en pista interior, combinado y exterior.
3. **IMS, bearing 1 (n = 99):** C-ruido sale en el registro 709, C-simulador en 708–709, curtosis en 709 y envolvente en 704. En la sección sin preblanqueo (q) el autoencoder y el RMS salen en 539. Es el coste declarado en v2: el preblanqueo quita la energía, y el primer síntoma de IMS es energético.
4. **XJTU (H+V, n = 99):** todos los modelos de v3 detectan 6–8 de los 13 rodamientos (FAR en la franja 1,8–4,5%), frente a los 13 de 13 del OEM en la sección q.
5. **Qué calcula el control de ruido.** Su autoencoder no reconstruye nada (no reconstruida 1,000), así que su puntuación es, aproximadamente, la distancia de la representación de la ventana a la media de la del ruido blanco. En la práctica ordena las ventanas como la curtosis: correlación de Spearman 0,83 en Ottawa, 0,71 en IMS y 0,68–0,69 en XJTU; con la envolvente, 0,48–0,68. El C-simulador se parece menos a las dos (0,31–0,79). **No es un modelo aprendido de ninguna máquina.**

## 4. Posibles lecturas (hipótesis, sin decidir)

- **(a)** v1, v2 y v3 marcarían un límite de este autoencoder (error cuadrático, entrada de 1200, código de 16): no representa lo sano del banco una vez quitada la vía de transmisión. Es un límite de la representación, no del cociente, como se declaró en v2.
- **(b)** En el cociente completo la detección funciona sin aprender nada (curtosis, envolvente y el control de ruido, que se comporta como ellas). Coherente con la lectura de v2.
- **(c)** Poner la vía de transmisión en G tiene un coste medido en dos conjuntos: IMS sale más tarde (709 frente a 539) y XJTU detecta menos (~7 de 13 frente a 13 de 13).
- La interpretación del control de ruido más allá de lo que calcula (punto 5) **se deja fuera de esta nota hasta que el autor decida** si y dónde se discute.

## 5. Preguntas abiertas para decidir juntos

1. ~~¿Cómo entran v1, v2 y v3 en el paper?~~ **Decidido 18-oct (D12):** resultados en el cuerpo con una tabla resumen; tablas completas de v2 y v3 en un apéndice.
2. ¿Se cita la mejora de las referencias clásicas con ventanas largas (observación 2), o es un detalle que no aporta a la tesis?
3. ~~¿Se discute el resultado del control de ruido?~~ **Decidido 18-oct (D13):** solo el hecho y qué calcula (observación 5), en una frase del apéndice; sin interpretación.
