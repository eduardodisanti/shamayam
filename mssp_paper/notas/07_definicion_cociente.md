# Definición del cociente (propuesta para §4–5 del paper, 14-oct)

*Borrador para discutir. No toca el `.tex`. Recoge lo que han enseñado CWRU, IMS, Ottawa y el banco: el cociente no es un detalle de preprocesado, es la decisión central del método, y hay que definirlo en el paper de forma explícita, con su coste.*

## 1. Modelo de observación

Lo que mide el sensor de la máquina m es el fenómeno visto a través de la máquina:

  x(t) = c + a · (h_m ∗ s)(θ(t)) + n(t),  muestreado a f_s,

donde:
- **s** es la *fuente*, función del ángulo del eje: componentes ligadas al eje y, si hay fallo, los impactos en los órdenes de defecto. **Es la firma del fenómeno.**
- **θ(t)** es el ángulo del eje en el tiempo (la velocidad, constante o variable).
- **h_m** es la vía de transmisión de la máquina m: estructura, resonancias, montaje y sensor. Es aproximadamente lineal e invariante, con respuesta en frecuencia suave y resonancias fijas en Hz.
- **a, c** son la ganancia y el offset.
- **n** es ruido.

## 2. El grupo de perturbaciones G (lo que se declara que no importa)

| Subgrupo | Acción | Sección (representante canónico) | Lo que se vuelve invisible (coste) | Evidencia |
|---|---|---|---|---|
| Reparametrización tiempo–ángulo (velocidad, también variable) y frecuencia de muestreo | θ(t) → θ'(t), f_s → f_s' | Remuestreo angular (computed order tracking; encoder o velocidad estimada) | Nada relevante para detectar | Tests sintéticos (barridos opuestos dan las mismas ventanas); CWRU (DE12/DE48); Ottawa |
| Fase (desplazamiento angular) | θ → θ + φ | Ninguna explícita: inicio arbitrario de ventana y aumento (o el módulo de un espectro) | Nada relevante para detectar | CWRU, ablación: el salto está en la fase |
| Ganancia y offset | x → a·x + c | Normalización por ventana (quitar la media, dividir por el RMS) | Los fallos que solo cambian la energía | Ottawa: aplana la FAR entre velocidades. IMS: con ella se pierde el fallo real, que es energético |
| Vía de transmisión | s ↦ h_m ∗ s, con h_m en una clase de filtros suaves | Preblanqueo (cepstral o espectral) en el dominio de Hz, antes del remuestreo angular | Los fallos que cambian la propia vía (aflojamiento, soporte, precarga) y el reparto de energía entre bandas | Banco v1: sin esta sección, la forma aprendida en una máquina no llega a otra (AUROC ≈ 0,5). Banco v2: el autoencoder no reconstruye la señal blanqueada (no evaluable); la curtosis blanqueada, sin aprendizaje, separa 3 de 4 fallos de Ottawa (08_protocolo_banco_v2) |

**No están en G y van al radio local o a la puesta en marcha:**
- **El ruido:** no es un grupo.
- **La carga:** CWRU, el radio no se transfiere entre cargas.
- **La parte dinámica de la velocidad:** la excitación de las resonancias cambia con la velocidad; Ottawa.
- **La cadena de adquisición cuando no es lineal ni suave:** CWRU, configuración C.

## 3. Orden de las secciones

Cada sección actúa en un dominio distinto, así que el orden importa:

1. **Preblanqueo en Hz:** las resonancias de la vía están fijas en Hz.
2. **Remuestreo angular:** las componentes de la fuente están fijas en órdenes.
3. **Normalización de ganancia y offset por ventana.**

La fase se trata con la ventana. Cada paso es una construcción explícita, no algo que se espera que aprenda el modelo (Remarks 14–15: el residuo del autoencoder no es G-invariante por sí solo).

## 4. Cocientes gruesos: los indicadores clásicos dentro del mismo marco

Los indicadores clásicos son cocientes más gruesos: identifican más señales y por eso ven menos.

| Indicador | Qué conserva | Qué cocienta además |
|---|---|---|
| RMS | Solo la energía | Toda la forma |
| Curtosis | La impulsividad | La ganancia; es poco sensible a la vía |
| Envolvente (pico/mediana del espectro de la envolvente) | Las líneas de modulación (la firma de impactos) | La portadora y la ganancia |
| Autoencoder en el cociente completo | La forma de la firma en órdenes, blanqueada | Solo G |

Todos se calibran con la misma regla certificada. La tabla de resultados compara cocientes, no modelos rivales, y los indicadores clásicos aparecen como arte previo y práctica actual.

## 5. Lo que esto cambia en el paper

- **El cociente es una decisión de diseño con coste.** Qué se declara en G depende de qué fallos se quiere ver:
  - Si el fallo es energético, como el de IMS, la ganancia no debe estar en G.
  - Si se quiere transferir la forma entre máquinas, la vía de transmisión sí tiene que estar.
  - No hay un cociente único bueno para todo; el paper da la regla para elegirlo y mide su coste.
- **La firma del fenómeno es lo que se conserva en el cociente completo.** Es el objeto que debería transferirse entre máquinas. v1 mostró qué pasa cuando falta la vía; v2 tiene que mostrar si con ella se transfiere.
- **Encaja con la práctica clásica sin competir con ella.** Seguimiento de órdenes, preblanqueo y envolvente son las herramientas que la práctica ya usa (Randall, Antoni, Borghesani). El paper explica por qué funcionan (son secciones de G) y qué cuestan.
- **§4–5 se reescriben con esta estructura:** modelo de observación, G, secciones, orden y coste, y cocientes gruesos. Arzelà–Ascoli y la topología fina van a un apéndice.

## 5b. Varios espacios a la vez (acordado 14-oct)

El método no tiene por qué usar un solo cociente. Se declara un conjunto de espacios, cada uno con su G y su coste, y se vigila en todos: lo que un espacio no ve lo ve otro. Por ejemplo, energía y forma, o forma e impulsividad. Es defendible porque cada cociente tiene su coste declarado.

**La garantía se conserva al combinarlos, con un precio exacto:**
- **Unión de alarmas con nivel repartido (Bonferroni).** Con K espacios, cada radio se toma al nivel 1 − 0,02/K; la falsa alarma total queda acotada por 0,02 sin suponer nada sobre la dependencia entre espacios. El mínimo de puesta en marcha sube: con K = 2 hacen falta n ≥ 99, y con K = 3, n ≥ 149. El menú 49/99/149 se lee también como cuántos espacios se pueden vigilar a la vez con la misma garantía.
- **Alternativa:** una puntuación combinada fijada en fábrica (una función fija de las K puntuaciones). La regla del estadístico de orden se aplica directamente y conserva n = 49. Cuidado: la combinación no puede depender de los datos de la puesta en marcha sin romper la intercambiabilidad.

**Comprobado con puntuaciones ya guardadas** ([`tablas_multiespacio.md`](tablas_multiespacio.md), `multispace_union.py`, sin entrenar nada):
- **Ottawa, con los cuatro ensayos.** Autoencoder en el cociente + curtosis detecta los cuatro tipos de fallo: interior, exterior y combinado en 12 de 12, y bola en 6–8 de 12. La FAR es del 7,8%, no mayor que la del autoencoder solo (8,4%). Por separado, el autoencoder no ve la pista exterior y la curtosis apenas ve la bola.
- **Ottawa con A-1 (un registro, unas 66 ventanas):** la unión de dos espacios **no es certificable**. Es exactamente el precio anunciado.
- **IMS:** RMS + curtosis y OEM + curtosis no son certificables con n = 49. Con n ≥ 99 sacan el fallo del bearing 1 en el registro 539, con FAR 0%, igual que el mejor espacio solo.
- **Una advertencia que vale para todo Ottawa:** la FAR observada (5–10%) supera el 2% nominal. La garantía exige que las ventanas de puesta en marcha sean intercambiables con las de operación, y aquí los ensayos de prueba son otros (lo midió el apéndice de velocidad). No es un fallo de la combinación.

## 6. Siguiente paso propuesto

Protocolo v2 del banco, derivado de esta definición y no ad hoc:
- **Hipótesis:** la firma se transfiere cuando el cociente incluye la vía de transmisión.
- **Lo único que cambia respecto a v1 es la sección,** que pasa a ser preblanqueo + remuestreo angular + ganancia. Los controles, el bootstrap, los criterios y la comprobación por velocidad son los de v1.
- **Referencias:** curtosis y envolvente clásica.
- **Registro previo:** se escribe antes de ejecutar, y v1 se mantiene tal como quedó registrado.
