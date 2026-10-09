# Revisión de la Sección 5

No toqué `mssp_draft.tex` para nada de esto. Son hallazgos y propuestas.

**Respuesta corta a tu pregunta: `\EtaSpace` sí es compacto, `\Gnuis` no.** Y no
hace falta que me creas: **el paper ya lo dice**, en L766–774. Estabas cansado
y te acordabas al revés, pero tu texto tiene la versión correcta.

Revisando eso aparecieron cuatro cosas más. Van en orden de gravedad.

---

## 0. `\Gnuis` no es compacto, y el paper lo afirma explícitamente

L758–764 construye `\Gnuis` como el grupo *generado* por `\mathcal{T}`, con
identidad e inversos, y dice que esto vale *"even if the physically motivated
transformations in \mathcal{T} are realized only over bounded operational
ranges"*.

Esa clausura es exactamente lo que rompe la compacidad. El grupo generado por
escalados de amplitud en \([a,b]\) con \(a<1<b\) es todo \((0,\infty)\),
porque componiendo se llega arbitrariamente alto y bajo. El generado por
offsets en \([-c,c]\) es todo \(\R\). Así que `\Gnuis` contiene un subgrupo
isomorfo a \((\R,+)\times(\R_{>0},\cdot)\) y **no es compacto**. Sólo el
desplazamiento de fase, como shift circular sobre una ventana finita, genera
un grupo compacto.

Y L766–774 lo dice sin ambigüedad:

> The compactness argument below does **not** require the full group
> \(\Gnuis\) to be compact; it uses only the compact nuisance parameter set
> \(\EtaSpace\).

Eso es correcto para `prop:compactness`. El problema es que **hay otros dos
lugares donde sí se usa el grupo completo**, y ahí la no compacidad muerde.
Son los puntos 1 y 4.

**Consecuencia inmediata para lo de ayer:** Bredon **no aplica**. El teorema
"espacio de órbitas Hausdorff" pide grupo compacto. Retiro esa propuesta tal
como estaba; abajo va la corregida.

---

## 1. `prop:boundary_invariant` afirma algo que es falso

El enunciado dice:

> In particular the nominal orbit \(\mathcal{O}_{\mathrm N}\) is
> \(\Gnuis\)-invariant **by construction**, so
> \(\partial\mathcal{O}_{\mathrm N}\) is \(\Gnuis\)-invariant and descends to a
> well-defined subset of \(\quotient\).

La primera parte de la proposición —que un \(S\) que *sea* \(\Gnuis\)-invariante
tiene interior, clausura y frontera \(\Gnuis\)-invariantes— es correcta y la
demostración está bien.

Pero \(\mathcal{O}_{\mathrm N}\) **no es \(\Gnuis\)-invariante**, y menos "por
construcción". Es la imagen de un conjunto de parámetros *acotado*:

\[
\mathcal{O}_{\mathrm N}=\{F(\theta_{\mathrm N},\eta):\eta\in\EtaSpace\}.
\]

Tomá \(g\) un escalado por 100, que está en `\Gnuis` por la construcción de
clausura de L758–764. Si `\EtaSpace` tiene amplitudes en \([0.9,1.1]\),
entonces \(g\cdot\mathcal{O}_{\mathrm N}\) tiene amplitudes cerca de 100 y no
está contenido en \(\mathcal{O}_{\mathrm N}\). Luego
\(g\cdot\mathcal{O}_{\mathrm N}\neq\mathcal{O}_{\mathrm N}\).

\(\mathcal{O}_{\mathrm N}\) es invariante bajo el *subconjunto* de
transformaciones que corresponde a `\EtaSpace`, y ese subconjunto **no es un
grupo**: no es cerrado por composición ni por inversos. Que no lo sea es
justamente lo que motivó la construcción de clausura.

Es la misma tensión que L766–774 identifica y después no persigue: ahí decís
que la compacidad no necesita el grupo completo, y tenés razón; pero
`prop:boundary_invariant` sí lo usa, y ahí la identificación entre "el grupo" y
"el rango admisible" que la clausura abandonó vuelve a hacer falta.

### Arreglos posibles

- **(a)** Aplicar la proposición al conjunto \(\Gnuis\)-invariante correcto, que
  es la órbita completa \(\Gnuis\cdot\mathcal{O}_{\mathrm N}\), y decir que
  *esa* tiene frontera bien definida en el cociente. Es cierto, pero cambia el
  objeto: la órbita completa incluye ventanas de amplitud arbitraria.
- **(b)** Restringir la proposición al subgrupo compacto (los shifts de fase),
  donde la invariancia sí vale por construcción, y decir que amplitud y offset
  se tratan aparte.
- **(c)** Enunciarla condicionalmente: "si \(S\) es \(\Gnuis\)-invariante,
  entonces…", y no aplicarla a \(\mathcal{O}_{\mathrm N}\).

La **(c)** es la de menor costo y no pierde nada, porque —hasta donde pude
rastrear— la frontera invariante no se usa cuantitativamente después. La **(a)**
es la honesta si querés conservar la lectura de "la frontera vive en el
cociente".

---

## 2. `ass:residual_proxy` usa una distancia que nunca se definió

Este es el que más me preocupa, porque es el supuesto central de toda la parte
computacional.

`ass:residual_proxy` escribe

\[
\residual(x)\;\approx\;d\bigl([x],\Mnominal\bigr),
\]

o sea una distancia **en el cociente**. Pero a `\quotient` sólo se le pone la
topología cociente (L798–800) y nunca una métrica. `d` sobre `\quotient` no está
definida en ningún lado del paper.

Y hay una segunda mitad: **la sonda que testea este supuesto no mide eso.**
`probes.py::_pairwise_min_distance` calcula distancia euclídea mínima entre
filas de ventanas crudas, es decir en \(\X\), no en `\quotient`. El propio
docstring dice *"compare their residual against their true distance to the
nominal sample"* — la muestra nominal, en el espacio ambiente.

Así que el supuesto enunciado y el supuesto testeado son objetos distintos.

La métrica cociente natural sería

\[
d([x],[y])=\inf_{g,h\in\Gnuis}\lVert g\cdot x-h\cdot y\rVert,
\]

y acá la no compacidad de `\Gnuis` vuelve a morder: con escalados no acotados
ese ínfimo es 0 para todo par de ventanas no nulas, porque podés encoger las
dos hacia el origen. **La métrica cociente colapsa a la trivial.** No es un
tecnicismo: dice que si el grupo es el generado, el cociente no tiene geometría
que medir.

### Arreglo propuesto

El más honesto y el que menos cambia: **decir que la distancia se mide en
\(\X\), no en `\quotient`**, que es lo que el código hace. O sea reemplazar
\(d([x],\Mnominal)\) por \(d(x,\mathcal{O}_{\mathrm N})\) con la norma de
\(\X\), y agregar una frase diciendo que la lectura en el cociente es
estructural —explica *por qué* hay una región nominal— mientras que toda
cantidad calculada vive en el espacio ambiente.

Eso es consistente con `rem:topology_vs_statistics`, donde ya separás la ruta
topológica de la estadística por lo que cada una entrega. Acá haría falta la
separación análoga entre lo que el cociente explica y lo que el ambiente mide.

---

## 3. `prop:compactness` usa Arzelà–Ascoli donde alcanza Heine–Borel

La proposición es **verdadera**. La demostración es válida pero está
sobredimensionada, y el supuesto que invoca es inerte.

`\X` es \(\subset\R^{n_w}\) con \(n_w\) fijo (Sección 4, L556). Una ventana es
un vector de dimensión finita. Para aplicar Arzelà–Ascoli hay que ver cada
ventana como función sobre el conjunto de índices \(\{0,\dots,n_w-1\}\), que es
**finito y discreto**. En un dominio finito discreto la equicontinuidad es
vacua: tomando \(\delta<1\), la condición \(|j-k|<\delta\) sólo se cumple con
\(j=k\), y ahí la diferencia es 0.

O sea que la cláusula de equicontinuidad de `ass:compact_eta` **no hace ningún
trabajo**, y lo que queda es: subconjunto uniformemente acotado de
\(\R^{n_w}\) es relativamente compacto. Eso es Heine–Borel.

Hay un problema adicional de señalización: citar Arzelà–Ascoli le dice a un
referee que el autor cree que \(\X\) es de dimensión infinita. Sospecho que la
demostración viene de pensar en la señal en tiempo continuo antes de muestrear
—donde A–A **sí** es la herramienta correcta— pero la proposición está enunciada
sobre \(\mathcal{O}_{\mathrm N}\subset\X\), que es finito-dimensional.

### Y hay una versión más fuerte, gratis

`cor:bounded_manifold` ya supone, dos líneas después, que
\(\eta\mapsto F(\theta_{\mathrm N},\eta)\) es **continua** (la necesita para
conexidad). Con esa continuidad:

> \(\EtaSpace\) compacto \(+\) \(\eta\mapsto F(\theta_{\mathrm N},\eta)\)
> continua \(\Rightarrow\) \(\mathcal{O}_{\mathrm N}\) es imagen continua de un
> compacto \(\Rightarrow\) \(\mathcal{O}_{\mathrm N}\) es **compacto**, y por
> tanto cerrado.

Es decir: podés concluir **compacto** en vez de *relativamente* compacto, sin
clausuras, sin Arzelà–Ascoli, sin equicontinuidad, en una línea, usando un
supuesto que ya hacés. Y como bonus desaparecen todas las
\(\overline{\mathcal{O}_{\mathrm N}}\) del resto de la sección.

Reemplazo sugerido para `ass:compact_eta`: cambiar *"uniformly bounded and
equicontinuous"* por *"continuous"*. Es más débil, más verificable y más fácil
de defender físicamente.

---

## 4. `def:nuisance_equivalence` y `eq:orbit` definen objetos distintos

`def:nuisance_equivalence` dice que \(x_1\sim x_2\) si existe \(g\) con
\(x_2=g\cdot x_1\) **y** ambas corresponden al mismo estado latente
\(\theta\). Es una conjunción de dos condiciones.

`eq:orbit` define \([x]=\{g\cdot x:g\in\Gnuis\}\), la órbita completa, **sin**
la cláusula de \(\theta\). Y `eq:quotient` define `\quotient` como el conjunto
de esos \([x]\).

Entonces `\quotient` es el espacio de órbitas \(\X/\Gnuis\), no el cociente
por \(\sim\). Son el mismo objeto sólo si la acción preserva \(\theta\) —que es
precisamente lo que `prop:quotient_diagnosis` *supone* más adelante, en vez de
tenerlo garantizado.

Es circular en un sentido leve: la definición mete en la equivalencia la
propiedad que después se asume como hipótesis. Dos salidas limpias:

- Declarar la preservación de \(\theta\) como **propiedad de la acción** al
  definir `\Gnuis` (que es lo que físicamente querés decir: el nuisance no
  cambia el estado), y entonces sacar la cláusula de `def:nuisance_equivalence`,
  que pasa a ser redundante. `prop:quotient_diagnosis` deja de necesitar esa
  hipótesis.
- O dejar la cláusula y aceptar que \([x]\) es un subconjunto de la órbita, con
  lo cual `eq:orbit` hay que reescribirla.

La primera es la que refleja tu intención.

---

## Resumen

| # | Hallazgo | Severidad |
|---|----------|-----------|
| 0 | `\Gnuis` no es compacto — tu paper ya lo dice, tu recuerdo estaba invertido | Aclaración |
| 1 | `prop:boundary_invariant`: "\(\mathcal{O}_{\mathrm N}\) es \(\Gnuis\)-invariante por construcción" es **falso** | **Error** |
| 2 | `ass:residual_proxy` usa \(d\) en `\quotient`, que nunca se define; y la sonda mide en \(\X\). Con `\Gnuis` no compacto la métrica cociente colapsa | **Error / hueco** |
| 3 | `prop:compactness`: A–A donde alcanza Heine–Borel; equicontinuidad inerte. Se puede fortalecer a *compacto* gratis | Mejorable |
| 4 | `def:nuisance_equivalence` vs `eq:orbit` definen objetos distintos | Inconsistencia |

Los puntos 1 y 2 los corregiría antes de mandar. El 3 y el 4 son de rigor y de
cómo lo lee un referee matemático, no de corrección de resultados.

**Nada de esto toca los resultados experimentales.** La cobertura, el radio, los
tiempos de anticipación y la sonda de adecuación se calculan todos en \(\X\) y
no dependen de la construcción del cociente. Lo que está en juego es el
andamiaje que explica *por qué* existe una región nominal, no los números.

---
---

# Segunda ronda — respuestas a tus tres objeciones

## R1. Sí, es falso, y la demostración usa tu propia proposición

Tenías razón en no aceptarlo porque sí. Acá va el argumento, y no depende de
ninguna interpretación mía de la construcción: sale de poner tus dos
proposiciones una al lado de la otra.

**Afirmación.** Bajo la construcción de L758–764, si
\(\mathcal{O}_{\mathrm N}\) es \(\Gnuis\)-invariante entonces
\(\mathcal{O}_{\mathrm N}\subseteq\{0\}\).

**Demostración.** Supongamos \(\mathcal{O}_{\mathrm N}\)
\(\Gnuis\)-invariante, y sea \(x\in\mathcal{O}_{\mathrm N}\) con \(x\neq 0\).

El escalado de amplitud está en \(\mathcal{T}\) (Sección 4, lista de nuisance).
Por la construcción de clausura de L758–764, \(\Gnuis\) contiene el grupo
generado por esos escalados, que es \(\{g_\lambda:\lambda>0\}\cong(\R_{>0},\cdot)\):
componiendo escalados en \([a,b]\) con \(a<1<b\) se alcanza cualquier
\(\lambda>0\), y los inversos están incluidos por construcción.

Por invariancia, \(g_\lambda\cdot x=\lambda x\in\mathcal{O}_{\mathrm N}\) para
todo \(\lambda>0\). Luego
\(\mathcal{O}_{\mathrm N}\supseteq\{\lambda x:\lambda>0\}\), que es no acotado
porque \(x\neq0\).

Pero `prop:compactness` afirma que \(\mathcal{O}_{\mathrm N}\) es relativamente
compacto, en particular **acotado**. Contradicción. Luego no existe tal \(x\), y
\(\mathcal{O}_{\mathrm N}\subseteq\{0\}\). \(\qquad\blacksquare\)

**Lo que esto dice.** No es que `prop:boundary_invariant` sea "discutible": es
que **`prop:compactness` y `prop:boundary_invariant` se contradicen**. La
primera dice acotado, la segunda dice invariante bajo un grupo con órbitas no
acotadas, y las dos sólo pueden ser ciertas a la vez si el conjunto nominal es
el origen. Están a sesenta líneas de distancia en la misma sección.

Dicho de otro modo, y quizá más útil: \(\mathcal{O}_{\mathrm N}\) es
\(\Gnuis\)-invariante si y sólo si `\EtaSpace` es invariante bajo la acción
inducida en parámetros, y un `\EtaSpace` **compacto** no puede ser invariante
bajo un grupo con órbitas no acotadas. Tu `ass:compact_eta` y la invariancia
piden cosas incompatibles.

### Texto propuesto

La salida más barata, y que no pierde nada porque la frontera invariante no se
usa cuantitativamente después. Reemplazar la última oración de
`prop:boundary_invariant`:

> In particular the nominal orbit \(\mathcal{O}_{\mathrm N}\) is
> \(\Gnuis\)-invariant by construction, so \(\partial\mathcal{O}_{\mathrm N}\)
> is \(\Gnuis\)-invariant and descends to a well-defined subset of
> \(\quotient\).

por

> The hypothesis is not satisfied by \(\mathcal{O}_{\mathrm N}\) itself.
> \(\mathcal{O}_{\mathrm N}\) is the image of the bounded parameter set
> \(\EtaSpace\), whereas \(\Gnuis\) is the group \emph{generated} by the
> nuisance transformations and has unbounded orbits; a set invariant under it
> and bounded in the sense of Proposition~\ref{prop:compactness} would have to
> be trivial. What is \(\Gnuis\)-invariant is the saturated set
> \(\Gnuis\cdot\mathcal{O}_{\mathrm N}\), and it is that set whose boundary
> descends to \(\quotient\). The distinction is the same one recorded before
> Definition~\ref{def:nuisance_equivalence}: the group is a mathematical
> closure of a physically bounded family, and statements that quantify over
> the whole group apply to the saturation rather than to the observed orbit.

---

## R2. En X no hay daño a los números. El costo es una afirmación, no un resultado

Tenés razón en no ver el problema, porque en los números no lo hay. Déjame
separar qué se rompe y qué no.

**No se rompe nada de lo medido.** Cobertura, \(\tau\), tiempos de
anticipación, saturación, sonda de adecuación: todo se calcula sobre
\(\residual(x)\in\R\) y sobre distancias euclídeas en \(\X\). Ninguna línea de
código toca `\quotient`. Los resultados quedan como están.

**Lo que se pierde es una atribución.** Con la distancia en \(\X\), dos
ventanas nuisance-equivalentes —la misma señal a amplitud 1.0 y a 1.1— están a
distancia **no nula**. La norma euclídea de \(\X\) no es invariante por el
nuisance. Entonces:

> La invariancia del residual **no es una consecuencia de la construcción del
> cociente. Es una propiedad empírica del operador entrenado.**

El cociente explica por qué *debería* existir una región nominal y por qué
tiene sentido buscarla; no es lo que produce la invariancia observada. Eso lo
produce el entrenamiento.

**Y acá está lo bueno: tus propios datos ya dicen exactamente eso.** La
invariancia es real y es parcial, y la midieron:

- L2880–2882: la escala del residual se dispersa por un factor de \(2.97\)
  entre el mayor y el menor. `rem:scale_not_invariant` ya lo predice.
- §7.2 completa: *"the transferable object is the representation, not its
  scale"*.
- Ítem 7.7c del checklist: \(\tau\) se dispersa 4.4–6.6% entre semillas, pero
  **normalizado por el residual mediano del rodamiento se dispersa 0.7–1.2%**.

Si el cociente removiera de verdad el escalado de amplitud, \(\tau\) sería
independiente del activo sin normalizar. No lo es. Lo que 7.7c muestra es
invariancia **tras normalizar**, que es un hallazgo empírico y no una identidad
estructural.

**Entonces el daño real es el riesgo de referee.** Alguien lee
`ass:residual_proxy`, ve \(d([x],\Mnominal)\) y pregunta con qué métrica. Si la
respuesta es "en realidad medimos en \(\X\)", la segunda pregunta es inevitable:
*¿entonces qué compró el cociente?* Contestarla de antemano es mucho más fuerte
que que te la hagan.

Y la respuesta es buena: el cociente compra el **planteo del problema** —
qué objeto se recupera, por qué la no inyectividad no es ruido sino estructura,
por qué la decisión es pertenencia y no umbral. No compra la métrica. Es
exactamente la división que ya hacés en `rem:topology_vs_statistics` entre la
ruta topológica y la estadística, aplicada un nivel más abajo.

### Texto propuesto

Reemplazar \(\residual(x)\approx d([x],\Mnominal)\) por

\[
\residual(x)\;\approx\;d\bigl(x,\mathcal{O}_{\mathrm N}\bigr),
\]

con \(d\) la distancia de \(\X\), y agregar debajo de la assumption:

> The distance is taken in \(\X\), not in \(\quotient\). This is deliberate.
> \(\quotient\) carries only the quotient topology, and the natural quotient
> pseudometric induced by \(\Gnuis\) is degenerate here, since unbounded
> scalings drive the infimum to zero for any pair of non-zero windows. The
> quotient construction is what states the problem --- which object is
> recovered, and why non-injectivity is structure rather than noise --- while
> every quantity computed in this paper is computed in the ambient space.
> Consequently the nuisance-invariance of \(\residual\) is an empirical
> property of the trained operator and not a consequence of the construction,
> which is why Section~\ref{subsec:disc_scale} measures it rather than
> asserting it.

(El label correcto es `subsec:disc_scale`, L3572 — verificado, no
`disc_transferable`, que no existe.)

Con eso el "agujero de la Sección 5" se cierra sin bibliografía nueva.

---

## R3. Arzelà–Ascoli: podés quedártelo, y hay una buena razón para hacerlo

Concedo. **A–A no es incorrecto** y no te obliga a nada.

- El teorema es verdadero y sus hipótesis, como están en `ass:compact_eta`, se
  cumplen. La demostración es válida. No hay error.
- Heine–Borel: en \(\R^{n_w}\) con \(n_w\) fijo todas las normas son
  equivalentes, así que sup-norma y euclídea dan la misma topología; un
  conjunto acotado tiene clausura cerrada y acotada, luego compacta. Es
  literalmente la misma conclusión con menos maquinaria.
- Lo único que señalo es que **sobre un conjunto de índices finito la
  equicontinuidad es vacua**: con \(\delta<1\), la condición \(|j-k|<\delta\)
  sólo se cumple si \(j=k\), y ahí la diferencia es \(0\). O sea que esa
  cláusula de la hipótesis no hace trabajo.

**La buena razón para quedártelo.** L559–560 dice que la formulación *"does not
depend on this particular sensing modality"*. Si alguna vez el paper aplica a
señales en tiempo continuo, a ventanas de largo variable, o a observaciones que
son funciones y no vectores, **A–A es exactamente la herramienta correcta y el
enunciado sobrevive sin cambios**. Heine–Borel no.

Así que la recomendación se invierte respecto de lo que dije: no lo saques,
**declaralo**. Una frase después de la demostración:

> The statement is given in the sup-norm form because it then applies verbatim
> when observations are functions rather than fixed-length vectors, which the
> formulation of Section~\ref{sec:observation_model} explicitly allows. For the
> finite windows used here \(\X\subset\R^{n_w}\) is finite-dimensional, the
> equicontinuity hypothesis is satisfied vacuously, and the argument reduces to
> the Heine--Borel theorem.

Eso convierte lo que un referee podría leer como sobredimensionamiento en una
generalidad deliberada, y de paso te blinda contra que te pregunten por qué la
equicontinuidad no hace nada.

**Lo que sigue valiendo del punto 3:** el fortalecimiento a *compacto* es
independiente de esto y sigue siendo gratis. Con \(\eta\mapsto
F(\theta_{\mathrm N},\eta)\) continua —que `cor:bounded_manifold` ya supone—
\(\mathcal{O}_{\mathrm N}\) es imagen continua de un compacto, luego compacto y
cerrado, y desaparecen las clausuras del resto de la sección. Podés tener las
dos: A–A como enunciado general, y la observación de que bajo continuidad se
obtiene compacidad directa.

---

## Sobre la propuesta de referencias de ayer

Queda corregida así:

- **Bredon** — retirado. Pide grupo compacto.
- **Palais (1961)**, DOI `10.2307/1970335`, verificado — pasa a ser la
  referencia relevante si querés la ruta de acciones propias para grupo no
  compacto. Pero ojo: la acción de escalado sobre \(\R^{n_w}\) **no es propia**
  (el origen tiene estabilizador todo el grupo), así que tampoco la salva.
- **Burago, Burago & Ivanov (2001)**, DOI `10.1090/gsm/033`, verificado —
  **sube de prioridad**. Es la referencia para métrica cociente y para el hecho
  de que en general es sólo una pseudométrica, que es exactamente el punto 2.

Mi lectura: el arreglo del punto 2 no es citar más topología, es reconocer que
la geometría se mide en \(\X\). Si hacés eso, no hace falta ninguna referencia
nueva de cocientes, y el "agujero de la Sección 5" se cierra por aclaración en
lugar de por bibliografía.
