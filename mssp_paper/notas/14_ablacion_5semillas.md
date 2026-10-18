# CWRU, ablación del cociente con 5 semillas: qué salió

> **PARA DISCUSIÓN. No hay conclusiones en esta nota.** Tablas en [`tablas_cwru_ablacion_5semillas.md`](tablas_cwru_ablacion_5semillas.md) (el informe) y [`tablas_cwru_ablacion_discusion.md`](tablas_cwru_ablacion_discusion.md) (por semilla y comparaciones pareadas, hechas después de ver los resultados). La ablación registrada con 2–3 semillas ([`01_resultados_cwru.md`](01_resultados_cwru.md)) no se toca.

## 1. Qué se probó, en palabras

- Un modelo **local** por condición de CWRU, entrenado con los mismos ~5 s de puesta en marcha (49 ventanas en el cociente), siempre con 4000 ventanas de entrenamiento, describiendo el grupo de perturbaciones cada vez con más elementos: **G1** fase, **G2** + ganancia, **G3** + offset, **G4** + ruido (grupo completo). G0 (solo proyección) es el brazo de datos limitados, ya con 5 semillas.
- Radio r₍ₖ₎ con las 49 ventanas de puesta en marcha; FAR en las ~50 ventanas sanas que siguen; detección en todos los fallos DE48.
- La extensión pone **5 semillas en G1–G4** (antes 2–3). 1797 rpm queda fuera, como antes (solo una ventana sana después).

## 2. Hechos

- **Detección del 100%** en todos los niveles, velocidades y semillas.
- **FAR media [mín–máx] sobre 5 semillas:**

  | nivel | 1730 rpm (47 sanas) | 1750 rpm (49) | 1772 rpm (50) |
  |---|---|---|---|
  | G0 (datos limitados, publicado) | 23,4–57,4% | 2,0–26,5% | 4,0–18,0% |
  | G1 + fase | 3,0% [0,0–8,5] | 0,0% | 1,2% [0,0–4,0] |
  | G2 + ganancia | 3,8% [0,0–6,4] | 0,0% | 4,0% [0,0–10,0] |
  | G3 + offset | 3,0% [0,0–8,5] | 0,0% | 2,8% [0,0–10,0] |
  | G4 + ruido | 5,5% [2,1–12,8] | 0,0% | 5,2% [0,0–14,0] |

- **Lo que ya decía la nota 01 se mantiene con 5 semillas:** el salto está en la fase (G0 → G1), y de G1 a G4 no hay mejora.

## 3. Observación nueva (posterior a ver los resultados)

- **G4 no mejora a G1 y, si acaso, empeora un poco.** Pareando por semilla y velocidad (15 pares), G4 tiene más falsas alarmas que G1 en 7 pares, menos en 0 e igual en 8 (los 5 de 1750 rpm están a 0 en todos los niveles). La diferencia es de 0 a 5 ventanas. Test de signos sobre los pares no empatados: p = 0,016 sin corregir; con tres comparaciones (G2, G3 y G4 frente a G1), 0,047 con Bonferroni.
- G2 frente a G1: 7 peor, 1 mejor (p = 0,070). G3 frente a G1: 5 peor, 3 mejor (p = 0,73).

**Cautelas:** las cinco semillas comparten las mismas ventanas sanas de prueba (los pares no son independientes en el conjunto de prueba), son unas 50 ventanas por condición (una ventana es ~2 puntos de FAR), y la comparación se hizo después de ver los datos.

## 4. Posibles lecturas (hipótesis, sin decidir)

- **(a)** Como ya se escribió en la nota 01: describir mejor el cociente ayuda cuando se añade la perturbación que de verdad varía en los datos (la fase, en un único registro de 10 s). Ganancia, offset y ruido no varían dentro de ese registro, así que añadirlos no aporta.
- **(b)** Añadir al entrenamiento variaciones que no están en los datos podría ensanchar lo que el modelo reconstruye bien sin cambiar las 49 ventanas reales con que se calibra el radio, y eso movería un poco la FAR. **Lo que falta:** no se ha mirado el mecanismo; con estas cifras (0–5 ventanas) puede ser también ruido.

## 5. Preguntas abiertas para decidir juntos

1. ¿El paper dice solo "de G1 a G4 no hay mejora medible" (lo registrado) o también menciona la ligera subida con G4, como observación posterior?
2. ¿Se informan G1–G4 con 5 semillas en lugar de 2–3 en la tabla del paper?
