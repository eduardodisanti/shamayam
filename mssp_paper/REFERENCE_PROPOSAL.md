# Propuesta de referencias y prosa

Nada de esto está escrito en `mssp_draft.tex` todavía. Las siete entradas
nuevas sí están en `references.bib`, verificadas contra el registro resuelto
con el mismo estándar que la auditoría, y marcadas como PENDING CITATION.
BibTeX descarta las no citadas en silencio, así que hoy no cuestan nada; si
rechazás una propuesta, borrá su entrada en vez de dejarla ahí.

Los números de línea son sobre el `mssp_draft.tex` del 11 Ago 2026 y se van a
correr a medida que insertes.

---

## 1. El hallazgo que motiva todo: el estimador de dimensión no está atribuido

**Esto no es una referencia huérfana inocua. Es un método con nombre usado sin
nombrarlo.**

`levina2004` estaba en el `.bib` sin ninguna cita. Buscando dónde debía ir
apareció lo siguiente:

- `mssp_repro/dimension.py` implementa `levina_bickel(X, k_values, corrected=True)`
  y su docstring dice, textualmente, *"The estimator is the maximum-likelihood
  construction of Levina and Bickel, with the Mackay-Ghahramani correction of
  averaging inverses rather than estimates"*.
- El manuscrito reporta ese estimador en la Tabla `tab:dimension`, la Figura
  `fig:dimension` y un párrafo entero de Resultados (L2884–2903).
- **Ni "Levina", ni "Bickel", ni "MacKay", ni "Ghahramani" aparecen una sola
  vez en el `.tex`.** Lo verifiqué con grep.
- Peor: L2893 dice *"which is the known negative bias of the estimator"* y el
  caption de la tabla dice *"The estimator is biased downward"*. Se invoca un
  sesgo *conocido* de un estimador que nunca se identifica. Las columnas `k=10,
  k=20, k=40` son los tamaños de vecindario de Levina–Bickel y aparecen sin
  explicación de qué es `k`.

Un referee de MSSP va a preguntar cuál es el estimador, y con razón: el sesgo
negativo sólo es "conocido" si el lector sabe de cuál se habla. Además la
corrección MacKay–Ghahramani que usás (`corrected=True`, promediar inversas)
es exactamente la que ataca el sesgo a `k` chico — o sea que el código ya
mitiga parte del sesgo que el texto atribuye sin matizar.

### Inserción 1a — Resultados, L2891–2895

Reemplazar:

> Each additional parameter raises the estimate by close to one, and the
> single-parameter case is recovered exactly. The residual gap grows with the
> dimension, which is the known negative bias of the estimator rather than an
> unexplained discrepancy; a mistaken reading would fail to track the count at
> all.

Por:

> The estimator is the maximum-likelihood construction of
> \citet{levina2004}, evaluated at several neighbourhood sizes \(k\) and
> combined by averaging the inverse estimates rather than the estimates
> themselves, which is the correction of \citet{mackay2005dimension} and
> removes the strong bias the original averaging shows at small \(k\).
>
> Each additional parameter raises the estimate by close to one, and the
> single-parameter case is recovered exactly. The residual gap grows with the
> dimension, which is the downward bias documented for this estimator on
> manifolds of increasing dimension rather than an unexplained discrepancy; a
> mistaken reading would fail to track the count at all.

### Inserción 1b — caption de `tables/dimension.tex`

Ojo: ese archivo está **generado** por `make_tables.py` y dice "do not edit".
El cambio va en el generador, no en el `.tex`. Sugerencia para el caption:

> Maximum-likelihood intrinsic dimension \citep{levina2004} of the noise-free
> nominal family, against the number of active nuisance parameters, at three
> neighbourhood sizes \(k\). The estimator is biased downward, increasingly so
> with dimension, so the criterion is whether it \emph{tracks} the prediction
> rather than whether it matches it. Ambient dimension is 1200.

### Inserción 1c — `rem:fill_rate`, L1874

Reemplazar *"and Experiment~7 measures \(d\) rather than assuming it"* por:

> and Experiment~7 measures \(d\) with the maximum-likelihood estimator of
> \citet{levina2004} rather than assuming it.

---

## 2. Takens: tenías razón, pero el problema es dónde falta

Takens **sí** está citado — en `rem:delay_embedding` (L599) y mencionado en la
Discusión (L3615). Lo que pasa es otra cosa, y son dos cosas distintas.

### 2a. Falta por completo de Related Work

La Sección 3 tiene siete párrafos: monitoreo/ISO, novelty detection, aprendizaje
como problema inverso, invariancia/geometric DL, domain adaptation, SOM/JEPA, y
tolerancia distribution-free. **No hay ninguno sobre reconstrucción de espacio
de estados.** Takens, Sauer y Casdagli aparecen sólo dentro de un remark del
modelo de observación, y Levina–Bickel en ningún lado.

Eso es raro de leer: la ventana-como-vector-de-retardos es lo que justifica el
objeto de observación entero y lo que hace usable el argumento de covering en
dimensión ambiente 1200, pero un lector que sólo lee Related Work no se entera
de que hay una tradición detrás.

**Propuesta: párrafo nuevo en Sección 3**, insertado entre *"Learning as an
inverse problem"* (termina L468) y *"Invariance and geometric representation
learning"* (empieza L470). Le da casa a `levina2004` en Related Work y de paso
resuelve el ítem 6.9 del checklist.

> \paragraph{State-space reconstruction and intrinsic dimension.}
> Treating a fixed-length window as a delay-coordinate vector is the standard
> device of state-space reconstruction. \citet{takens1981} showed that for a
> deterministic system with a compact invariant \emph{manifold} of dimension
> \(d\), a generic delay map into \(\R^{m}\) with \(m \ge 2d+1\) is an
> embedding; \citet{sauer1991} extended the statement to invariant sets that
> are merely compact, with \(m > 2d\) for \(d\) the box-counting dimension.
> Both require determinism, and reconstruction in the presence of measurement
> noise is a separate and weaker theory \citep{casdagli1991}. The consequence
> used here is not a reconstruction claim but a dimension claim: the nominal
> set inherits an intrinsic dimension far below the ambient window length,
> which is what makes a covering argument usable at \(n_w=1200\). That
> dimension is measured rather than assumed, with the maximum-likelihood
> estimator of \citet{levina2004}.

### 2b. La atribución en `rem:delay_embedding` está mal (L597–600)

El texto actual dice:

> If the underlying mechanical process is deterministic with a compact
> invariant set of box-counting dimension \(d\), then by the embedding theorems
> of \citet{takens1981} and \citet{sauer1991} the map \eqref{eq:delay_vector}
> is generically an embedding whenever \(m>2d\)

Ese enunciado —conjunto compacto cualquiera, dimensión box-counting, \(m>2d\)—
es **Sauer–Yorke–Casdagli, no Takens**. Takens pide una variedad compacta y
\(m \ge 2d+1\). Atribuir a los dos un enunciado que sólo uno demostró es el
tipo de imprecisión que un referee con formación en sistemas dinámicos marca, y
además debilita el argumento: la versión SYC es *más fuerte* para vos, porque
tu conjunto invariante no tiene por qué ser una variedad.

**Propuesta de reemplazo:**

> If the underlying mechanical process is deterministic with a compact
> invariant set, then \eqref{eq:delay_vector} is generically an embedding
> once \(m\) is large enough: \(m \ge 2d+1\) for an invariant manifold of
> dimension \(d\) \citep{takens1981}, and \(m > 2d\) for a compact invariant
> set of box-counting dimension \(d\), which is the form due to
> \citet{sauer1991} and the one that applies here, since nothing guarantees
> the nominal set is a manifold. Under either statement \(\X\) contains a
> diffeomorphic copy of that set and its topological invariants are preserved.

Esto también hace juego con `rem:manifold_terminology`, donde ya sos cuidadoso
en **no** reclamar estructura de variedad. Hoy el remark de embedding la asume
implícitamente vía Takens y el otro remark la niega.

---

## 3. Espacios cociente: Grenander + invariancia en aprendizaje

Elegiste estas dos direcciones. Aviso primero: **la Sección 5, que es el núcleo
matemático y da título al paper, hoy no cita literatura externa de cocientes.**
Sus únicas citas son Rudin (Arzelà–Ascoli y clausura/interior), Bronstein, y
tus dos reportes propios. Ninguna de las dos direcciones que elegiste tapa ese
agujero del todo —para eso haría falta grupos de transformaciones tipo Bredon—
pero las dos sí dan precedente y las dos entran limpio.

### 3a. Grenander — teoría de patrones, en el Modelo de Observación

El lugar natural **no** es Related Work sino justo donde introducís
\(x = F(\theta,\eta)\), en L580–584. Es literalmente el modelo de plantilla más
deformación.

**Insertar después de la ecuación `eq:forward_model` (L584):**

> This decomposition of an observation into a latent object and a group of
> transformations acting on it is the organizing idea of pattern theory
> \citep{grenander1994}, where an observed pattern is a template acted on by a
> deformation group and inference proceeds modulo that group. The
> specialization here is that the group is a nuisance group with no diagnostic
> content, so the object recovered is an equivalence class rather than a
> deformed template, and that the quotient is taken explicitly in
> Section~\ref{sec:quotient_formulation} rather than marginalized over.

Ganancia concreta: le da un antecedente de cincuenta años a \(x=F(\theta,\eta)\)
y te permite decir en qué te diferenciás, que es más fuerte que presentarlo sin
linaje.

### 3b. Higgins y Cohen–Welling — en el párrafo de invariancia de Related Work

Van en el párrafo *"Invariance and geometric representation learning"*
(L470–484), que hoy se apoya sólo en Bronstein.

**Insertar después de la primera oración (L473, tras "…the group they
respect."):**

> The mechanism is made concrete by group-equivariant architectures, in which
> the weight sharing of a convolution is generalized to an arbitrary symmetry
> group \citep{cohen2016group}, and the goal is made precise by the
> group-theoretic definition of a disentangled representation
> \citep{higgins2018}, which asks that a symmetry acting on the world act on
> the representation as a direct-sum decomposition. Both take the group as
> given and shape the representation around it, which is also what is done
> here when the operator is chosen to be convolutional.

Y —esto es lo que hace que valga la pena— **enganchar con tu propio resultado
negativo**, que hoy queda un poco huérfano. Al final del párrafo, después de
*"it does not by itself certify the decision region built on top of it"*:

> The distinction matters more once invariance is stated as a property of the
> representation, as in \citet{higgins2018}: a representation can satisfy an
> equivariance condition exactly and still induce an accepted region of the
> wrong shape, because the condition constrains how the representation
> transforms and not how far the residual extends.

Eso convierte la sonda de adecuación de una observación empírica suelta en una
objeción dirigida a una definición publicada. Es el uso más rentable de esas
dos citas.

---

## 4. Autoencoders

No contestaste esta pregunta, así que dejo tres propuestas y una recomendación
en vez de decidir por vos. Hoy la base es `hinton2006` + `sakurada2014`, que
para MSSP es fina.

### 4a. RECOMENDADO — autoencoder lineal = PCA, en Related Work

`bourlard1988` y `baldi1989`. Esta es la que más rinde y no por completitud
bibliográfica sino porque **sostiene un resultado tuyo**.

Reportás (L479–484 y en Resultados) una sonda donde un operador **lineal**
alcanza la cobertura objetivo aceptando puntos a cientos de veces el
espaciado nominal. Sin cita, un lector puede leer eso como "probamos un
baseline débil y falló". Con la cita, es "el control es el subespacio de PCA,
que es exactamente lo que un autoencoder lineal aprende, y aún así pasa el
test de cobertura" — o sea, la cobertura no distingue geometría.

**Al final del párrafo de novelty detection (después de L443):**

> The reconstruction residual is not a neutral score. For a linear operator the
> optimum is the principal subspace \citep{bourlard1988,baldi1989}, so the
> residual measures distance to a hyperplane and the accepted region is a slab;
> the adequacy probe of Section~\ref{sec:results} uses exactly this to show
> that attaining the target coverage does not constrain the shape of the region
> attaining it.

### 4b. RECOMENDADO — el modo de falla, para la Discusión o Limitations

`gong2019memae`. El hallazgo de memorización de CWRU que tenés en Limitations
es un caso conocido y documentado: el autoencoder generaliza lo suficiente como
para reconstruir bien también lo anómalo, y el residual deja de separar. Citarlo
convierte una debilidad reportada en una debilidad *reconocida por el campo*,
que se defiende mucho mejor ante un referee.

Sitio sugerido: donde discutís la memorización del brazo de referencia CWRU en
`sec:limitations`. Necesito que me digas la línea exacta o la busco.

### 4c. OPCIONAL — variantes modernas

Vincent et al. (denoising) y Kingma–Welling (VAE), para el "¿por qué no un
VAE?". Es la más floja de las tres: responde a una pregunta que nadie hizo
todavía y agrega dos citas que no sostienen ningún resultado tuyo. **No las
verifiqué ni las agregué al `.bib`.** Si las querés, las traigo.

### 4d. Lo que NO propongo

Autoencoders aplicados a maquinaria rotante. Es la opción que parece más
obvia para MSSP y es la que menos aporta: `zhao2019` ya cubre el survey de
representaciones aprendidas en machine health monitoring, y agregar tres o
cuatro papers de AE-para-rodamientos engorda el conteo de palabras —que ya
está en ~19,200 y es largo para la revista, ítem 7.2 del checklist— sin
sostener ninguna afirmación. Si un referee lo pide, se agrega entonces.

---

## Resumen de decisiones que te tocan

| # | Propuesta | Mi lectura |
|---|-----------|------------|
| 1 | Nombrar Levina–Bickel y MacKay–Ghahramani | **Hacelo.** No es opcional; hoy hay un método con nombre usado sin atribuir |
| 2a | Párrafo de reconstrucción de espacio de estados en Related Work | **Hacelo.** Cierra el hueco que notaste y resuelve el 6.9 |
| 2b | Corregir la atribución Takens vs Sauer | **Hacelo.** Es un error, y la versión correcta te conviene más |
| 3a | Grenander en el modelo de observación | Fuerte. Da linaje a \(x=F(\theta,\eta)\) |
| 3b | Cohen–Welling e Higgins en Related Work | Fuerte, sobre todo el enganche con la sonda de adecuación |
| 4a | AE lineal = PCA | Fuerte. Sostiene un resultado propio |
| 4b | MemAE junto al hallazgo de CWRU | Fuerte. Convierte una debilidad en una reconocida |
| 4c | Denoising / VAE | Prescindible |
| 4d | AE en maquinaria rotante | No, salvo pedido de referee |

**Lo que no cubre esta propuesta:** el agujero real de la Sección 5 sigue
abierto. Para *"el cociente de un compacto por una acción de grupo compacto es
compacto Hausdorff"* hace falta una referencia de grupos de transformaciones
(Bredon, tom Dieck) y ninguna de las dos direcciones que elegiste la reemplaza.
Grenander da precedente aplicado y Higgins da la definición en aprendizaje,
pero ninguno de los dos es la cita que respalda el paso topológico. Decime si
querés que la traiga.
