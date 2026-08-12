# Referencias y prosa — estado

**Secciones 1–4: ESCRITAS** en `mssp_draft.tex` el 11 Ago 2026. Las siete
entradas nuevas están citadas, el build da 0 warnings de BibTeX, 0 citas
indefinidas, 0 referencias indefinidas, 48 páginas.

**Sección 5: PROPUESTA**, nada escrito. Son las referencias que pediste para
mirar el agujero de la Sección 5 del paper.

---

## 1. Estimador de dimensión intrínseca — ESCRITO

`levina2004` estaba en el `.bib` sin citar. Buscando su lugar apareció que
**el estimador se usaba sin nombrarlo**: `dimension.py` implementa
Levina–Bickel con la corrección MacKay–Ghahramani de promediar inversas, el
paper lo reporta en `tab:dimension`, `fig:dimension` y Resultados, y escribía
*"the known negative bias of the estimator"* sin decir de cuál.

Escrito en tres sitios: Resultados (párrafo nuevo que nombra el estimador y la
corrección), `rem:fill_rate`, y el párrafo nuevo de Related Work de §2.

### Pendiente tuyo

`tables/dimension.tex` está **generado** y dice "do not edit". El caption hay
que arreglarlo en `make_tables.py`. Texto sugerido:

> Maximum-likelihood intrinsic dimension \citep{levina2004} of the noise-free
> nominal family, against the number of active nuisance parameters, at three
> neighbourhood sizes \(k\). The estimator is biased downward, increasingly so
> with dimension, so the criterion is whether it \emph{tracks} the prediction
> rather than whether it matches it. Ambient dimension is 1200.

Queda anotado como parte del ítem 6.9 del checklist.

---

## 2. Takens — ESCRITO

Dos cambios.

**Atribución corregida** en `rem:delay_embedding`. Antes decía que "por los
teoremas de Takens y Sauer" el mapa es embedding cuando \(m>2d\) con \(d\) la
dimensión box-counting de un conjunto compacto. Eso es Sauer–Yorke–Casdagli.
Ahora los dos enunciados están separados: Takens pide variedad compacta y
\(m\ge 2d+1\); Sauer et al. debilitan la hipótesis a conjunto compacto y dan
\(m>2d\), y el texto dice explícitamente que **esa** es la forma que aplica,
porque nada garantiza que el conjunto nominal sea una variedad.

Efecto secundario que no había anticipado: esto elimina una inconsistencia
interna. La redacción vieja asumía vía Takens la estructura de variedad que
`rem:manifold_terminology` se cuida explícitamente de no reclamar.

**Párrafo nuevo en Related Work**, "State-space reconstruction and intrinsic
dimension", entre "Learning as an inverse problem" e "Invariance and geometric
representation learning".

---

## 3. Cociente: Grenander e invariancia — ESCRITO

`grenander1994` después de `eq:forward_model`, en el Modelo de Observación:
\(x=F(\theta,\eta)\) es literalmente plantilla más deformación de grupo, y el
texto dice en qué se especializa (grupo de puro nuisance, cociente explícito
en vez de marginalizado).

`cohen2016group` e `higgins2018` en el párrafo de invariancia de Related Work,
y —lo que más rinde— `higgins2018` otra vez al cerrar ese párrafo, enganchado
con tu sonda de adecuación: una representación puede satisfacer exactamente
una condición de equivariancia y aun así inducir una región aceptada de la
forma equivocada, porque la condición gobierna cómo transforma la
representación y no hasta dónde se extiende el residual.

---

## 4. Autoencoders — ESCRITO, y tu objeción cambió el párrafo

Tenías razón en desconfiar, y resulta que **tu propio código ya lo había
resuelto mejor de lo que yo lo había planteado**. El docstring de
`conv_autoencoder.py` dice:

> All activations are ReLU except the latent and the output, which are linear.
> A ReLU network is piecewise affine and therefore extrapolates affinely
> outside the training region, which is a legitimate reason to doubt that it
> avoids the pathology of a purely linear operator; the distance-proxy probe
> in `probes.py` settles the question empirically rather than by appeal to
> nonlinearity.

Así que la posición correcta no es la que yo había propuesto ni la que temías.
No es "somos PCA" ni es "somos no lineales, luego estamos a salvo". Es más
fuerte que las dos:

1. **En el caso lineal la pregunta está cerrada**: el autoencoder lineal
   recupera el subespacio principal (`bourlard1988`, `baldi1989`), su residual
   es exactamente distancia a un subespacio y su región aceptada es una losa,
   no acotada en cada dirección retenida. Por eso el brazo lineal de tu sonda
   es un **control principiado** y no un baseline débil.
2. **Tu operador no está cubierto por ese resultado** — es convolucional con
   ReLU. El párrafo lo dice explícitamente.
3. **Pero la no linealidad tampoco lo exime**: ReLU es afín a trozos y
   extrapola afínmente, así que *podría* heredar la misma patología. Esto es
   lo que evita el sobre-reclamo que te preocupaba.
4. **Se mide, no se asume**: la sonda da 4 órdenes de magnitud de diferencia
   en crecimiento del residual. El lineal acepta a 380× el espaciado nominal
   con residual \(10^{-28}\); el convolucional rechaza más allá de 1.6×.

O sea que lo que la no linealidad compra es un **hallazgo empírico** tuyo, no
un supuesto. Eso es más defendible ante un referee que cualquiera de las dos
posiciones fáciles, y es exactamente el punto que vos estabas protegiendo.

`gong2019memae` quedó en Limitations, junto al hallazgo de memorización de
CWRU, señalando que degrada el residual como proxy de distancia en la misma
dirección que la patología de la losa.

### No incluido

Denoising / VAE (§4c de la propuesta anterior) y autoencoders aplicados a
maquinaria rotante (§4d). El segundo sobre todo: `zhao2019` ya cubre el survey
y agregar papers de AE-para-rodamientos engorda un manuscrito que ya está
largo para MSSP sin sostener ninguna afirmación.

---

## 5. PROPUESTA — el agujero de la Sección 5

Esto es lo que pediste mirar. **Nada de esto está escrito ni agregado al
`.bib`.**

Releí la sección para ubicar qué referencia hace falta exactamente, y el
problema es más específico de lo que había dicho. No es "falta bibliografía de
cocientes" en abstracto; son dos huecos concretos.

### Hueco A — `\quotient` nunca se muestra Hausdorff

Le ponés a \(\quotient\) la topología cociente y decís que \(\pi\) es continua
por construcción. Eso es todo lo que se dice del espacio. Después
`cor:bounded_manifold` concluye que \(\pi(\overline{\mathcal{O}_{\mathrm N}})\)
es **compacto en \(\quotient\)**.

El problema: en un espacio no Hausdorff, un conjunto compacto **no tiene por
qué ser cerrado**, y los cocientes por acciones de grupo son un vivero de
espacios no Hausdorff — el ejemplo estándar es la acción de \(\R^*\) sobre
\(\R\). Todo lo que viene después trata a \(\Mnominal\) como una región con
frontera y con un radio, lo cual presupone bastante más que compacidad
topológica.

La buena noticia: **para una acción continua de un grupo compacto sobre un
espacio Hausdorff, el espacio de órbitas es Hausdorff y el mapa de órbitas es
cerrado**. Y tu grupo es plausiblemente compacto — escalado en un intervalo
acotado, fase en el círculo, etc. Si lo es, tenés el resultado gratis y sólo
hay que citarlo y verificar la hipótesis. Si no lo es, la condición correcta
es que la acción sea **propia**, y ahí entra Palais.

**Referencia primaria:**

> Bredon, G. E. (1972). *Introduction to Compact Transformation Groups*.
> Pure and Applied Mathematics 46, Academic Press.
> DOI `10.1016/S0079-8169(08)X6007-6` — VERIFICADO en Crossref 11 Ago 2026.

Capítulo I es donde está el material de espacio de órbitas: órbitas cerradas,
mapa de órbitas cerrado, \(X/G\) Hausdorff para \(G\) compacto.

**Para el caso no compacto:**

> Palais, R. S. (1961). On the existence of slices for actions of non-compact
> Lie groups. *The Annals of Mathematics* 73(2), 295.
> DOI `10.2307/1970335` — VERIFICADO en Crossref 11 Ago 2026.

**Alternativa a Bredon:** tom Dieck, *Transformation Groups*, de Gruyter
Studies in Mathematics 8, 1987. **No lo pude verificar en Crossref** — los
libros de de Gruyter de esa época no están registrados, y lo único que
devuelve es su *Transformation Groups and Representation Theory* (LNM 766,
1979), que es otro libro. Si lo querés usar, verificalo contra el catálogo del
editor antes; no lo cito de memoria después de lo que encontró la auditoría.

### Hueco B — el radio es una distancia en el cociente, y no hay métrica

Todo el marco descansa en un radio: `\tau`, la distancia a \(\Mnominal\), la
saturación. Pero \(\quotient\) sólo tiene topología cociente. La construcción
natural es la métrica cociente

\[ d([x],[y]) = \inf_{g,h\in\Gnuis} \lVert g\cdot x - h\cdot y\rVert, \]

y el punto delicado es que en general esto es una **pseudométrica**: es métrica
si las órbitas son cerradas, que es otra vez la condición del Hueco A. Vale la
pena porque conecta los dos huecos con una sola hipótesis.

> Burago, D., Burago, Y. & Ivanov, S. (2001). *A Course in Metric Geometry*.
> Graduate Studies in Mathematics 33, American Mathematical Society.
> DOI `10.1090/gsm/033` — VERIFICADO en Crossref 11 Ago 2026.

El material de métricas cociente y de identificación por semimétricas está en
el Capítulo 3.

### Cómo lo encararía

No como una sección nueva de matemática, que alargaría un manuscrito ya largo,
sino como **un remark después de `cor:bounded_manifold`** que haga tres cosas:
nombre la hipótesis bajo la cual \(\quotient\) es Hausdorff, cite a Bredon, y
diga honestamente si esa hipótesis se verifica para tu \(\Gnuis\) o si se
asume — igual que hacés con `ass:compact_eta`, que ya declarás como asumida y
no verificada para CWRU y NASA.

Eso convierte un hueco silencioso en una limitación declarada, que es el
patrón que ya usás en todo el paper y el que mejor resiste a un referee.

### Lo que necesito de vos

Una pregunta de hecho que no puedo contestar leyendo el `.tex`: **¿\(\Gnuis\)
es un grupo compacto?** El paper dice que \(\EtaSpace\) es compacto
(`ass:compact_eta`) pero eso es el espacio de parámetros, no el grupo. Si el
escalado de amplitud vive en \([a,b]\) con \(a>0\) y la fase en el círculo,
entonces sí y todo el Hueco A se cierra citando a Bredon. Si el escalado es
\(\R^{>0}\) sin acotar, no, y hay que ir por properness.
