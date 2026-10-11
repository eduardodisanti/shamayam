# CWRU tras corregir la frecuencia de muestreo: resultados

*Rama `mssp`, 11-oct-2026. Todas las cifras salen de
`reproducibility_package/results/cwru_projection/` (`results.json`, `scores.npz`).
Las tablas completas, generadas por script, están en
[`tablas_cwru_proyeccion.md`](tablas_cwru_proyeccion.md).*

## Resumen en cinco frases

1. **El problema estaba ahí.** En la configuración publicada (A), la Normal (48 kHz) se leía como si fuera de 12 kHz frente a fallos `DE12`. Un simple conteo de cruces por cero separa sanos y fallos con AUROC = 1,000 en las cuatro velocidades.
2. **Con la corrección** (B: Normal + `DE48`, ambos con proyección angular), los cruces por cero dejan de separar en tres de las cuatro velocidades (AUROC 0,52–0,91). La confusión por frecuencia de muestreo desaparece.
3. **Pero CWRU sigue siendo trivial para detectar.** Tras la corrección, el autoencoder compartido y el **RMS** dan AUROC = 1,000 en todas las velocidades y familias de fallo. Los ficheros de fallo tienen un RMS de 2 a 9 veces el de la Normal. CWRU no puede demostrar que la representación aporte algo frente a un indicador clásico.
4. **La proyección angular elimina la velocidad, pero no la carga.** El radio calibrado en una condición no sirve para otra (1772 y 1797 rpm caen fuera en un 93–100%). La calibración local es necesaria, y eso sí lo apoya CWRU.
5. **Con ~50 sanas por condición, la falsa alarma real es muy incierta.** El radio certificado con n = 49 da FAR del 0–8,5% en las sanas siguientes, con intervalos del 95% que llegan al 20%. A 1797 rpm solo hay 50 ventanas sanas: la regla online no converge y no queda nada para evaluar.

## Qué se ha hecho

**Configuraciones**, todas con el mismo protocolo:

| | Sanas | Fallos | Dominio | Operador compartido |
|---|---|---|---|---|
| **A** original | Normal (48 kHz) leída como 12 kHz | `DE12` (7/14/21/28) | tiempo, 1200 muestras | entrenado con simulación en tiempo (como el publicado) |
| **B** corregida | Normal (48 kHz) | `DE48` (7/14/21) | órdenes: 400 muestras/vuelta, ventanas de 3 vueltas | entrenado con simulación **proyectada igual** |
| **C** control de cadena | Normal (48 kHz) | `DE12` | órdenes, igual que B | el mismo de B |

**La proyección** está en `mssp_repro/field/order_domain.py`:
- **Velocidad:** se estima por fichero con una suma de armónicos 1–3 en ±4% de la nominal. Las Normal quedan a −0,02% … −0,32% de la nominal. Los ficheros de menos de 3 s (cinco a 1797 rpm) usan la velocidad de la Normal de su condición.
- **Remuestreo:** polifásico, a 400 muestras por vuelta.
- **Ventanas:** de 3 vueltas, sin solape.
- **Simulador:** se proyecta igual, usando su velocidad conocida.
- **Tests:** 9 en `tests/test_order_domain.py`. Comprueban que la estimación de velocidad queda dentro del 0,2%, que dos velocidades y dos frecuencias de muestreo dan la misma ventana proyectada (error < 2%) y que, sin proyectar, las ventanas difieren (> 20%).

**Detectores:**
- el autoencoder compartido (arquitectura y calendario de entrenamiento publicados, semilla 42);
- RMS, curtosis y cruces por cero, puntuados como |valor − mediana sana|.

**Calibraciones:**
- **Transferencia directa:** τ_MC de la simulación.
- **Oráculo:** p98 interpolado sobre todas las sanas, como se publicó.
- **Online:** regla de parada publicada.
- **Certificada:** r₍ₖ₎ sobre las 49 primeras sanas, con la FAR medida en las siguientes.

## 1. La confusión existía y la corrección la elimina

AUROC sano frente a fallo, con los cruces por cero como detector trivial:

| Config | Bola (1730/1750/1772/1797) | Pista int. | Pista ext. |
|---|---|---|---|
| A original | 1,000 / 1,000 / 1,000 / 1,000 | 1,000 / 1,000 / 1,000 / 1,000 | 1,000 / 1,000 / 1,000 / 1,000 |
| B corregida | 0,712 / 0,876 / 0,912 / 1,000 | 0,785 / 0,624 / 0,516 / 1,000 | 0,769 / 0,802 / 0,757 / 0,987 |
| C control | 0,904 / 0,914 / 0,908 / 1,000 | 0,890 / 0,946 / 0,965 / 1,000 | 0,893 / 0,876 / 0,829 / 0,980 |

Mediana de cruces por cero en A: sanas 0,17–0,21 frente a fallos 0,43–0,50, un factor ~2,5 que es la huella del factor 4 de escala temporal. En B, sanas y fallos quedan en 0,42–0,47, salvo 1797 (véase el punto 5).

**C frente a B:** usar `DE12` con la Normal proyectada separa más que B (AUROC 0,83–0,97 frente a 0,52–0,91). Es la diferencia de cadena de adquisición que la proyección no elimina. Confirma que hay que emparejar la Normal con `DE48`.

## 2. CWRU no discrimina entre métodos

AUROC del autoencoder compartido y del RMS en B: **1,000 en las 12 combinaciones** de velocidad y familia, para los dos detectores. Con calibración certificada (n = 49), el RMS detecta el 100% de los fallos en todas las velocidades, igual que el autoencoder.

| Mediana RMS en B | Sanas | Bola | Pista int. | Pista ext. |
|---|---|---|---|---|
| 1730 | 0,058 | 0,151 | 0,280 | 0,451 |
| 1750 | 0,057 | 0,151 | 0,280 | 0,471 |
| 1772 | 0,061 | 0,148 | 0,281 | 0,527 |
| 1797 | 0,072 | 0,152 | 0,582 | 0,499 |

**Consecuencia:** el 100% de detección en CWRU sigue siendo cierto tras la corrección, pero no es evidencia a favor del método. Lo conseguiría cualquier indicador de energía. Es la crítica conocida a CWRU (Smith & Randall, 2015, MSSP).

La curtosis es el único descriptor que no llega a 1,000 (bola 0,78–0,87). Es coherente con que los fallos de bola de CWRU son los menos impulsivos.

## 3. La proyección quita la velocidad, no la carga: el radio no se transfiere

Radio oráculo del autoencoder calibrado en la fila y aplicado a las sanas de la columna (% fuera del radio). En B:

| Calibrada en \ evaluada en | 1730 | 1750 | 1772 | 1797 |
|---|---|---|---|---|
| 1730 | 2,1 | 3,1 | 92,9 | 100,0 |
| 1750 | 1,0 | 2,0 | 92,9 | 100,0 |
| 1772 | 0,0 | 0,0 | 2,0 | 100,0 |
| 1797 | 0,0 | 0,0 | 0,0 | 2,0 |

Radios oráculo en B: 0,0579 / 0,0583 / 0,0680 / 0,0871, un factor 1,50 entre extremos. El RMS sano también cambia con la condición (0,057–0,072) y su radio tampoco se transfiere.

**Lectura:**
- Entre 1730 y 1772 rpm la velocidad cambia un 2%, pero la carga pasa de 3 a 1 HP. La carga no es una reparametrización del tiempo, así que no está en el grupo que proyectamos.
- La parte de la tesis del paper de que **la representación se comparte y la escala del radio es local** queda bien apoyada, y por un motivo físico identificable.

## 4. Transferencia directa del umbral simulado

En B, τ_MC = 0,1096 queda entre 1,26 y 1,89 veces por encima del oráculo local:
- FAR = 0% en las cuatro velocidades.
- Detección del 99,3–100%, porque los fallos están muy lejos.

En A (este reentrenamiento), τ_MC = 0,0452 queda a 0,78–1,04 del oráculo, y la FAR de la transferencia directa va del 0,25% al 76,85% (1797).

**Matiz para el paper:** la versión publicada decía que la transferencia directa marca el 100% de las sanas (τ_MC = 0,1027 frente a un oráculo ~0,35). Con el mismo código y otra versión de TensorFlow, la escala del operador cambia un orden de magnitud (oráculo 0,046 frente a 0,358). Eso refuerza que la escala no se transfiere, pero también indica que **la dirección del error de la transferencia directa depende del entrenamiento**. No conviene afirmar que la transferencia directa "falla siempre por exceso de falsas alarmas".

## 5. Calibración con pocas sanas: la garantía es marginal

FAR en sanas **no vistas** tras calibrar, autoencoder compartido, con intervalo de Clopper–Pearson al 95%:

| Config | rpm | Certificado n = 49 | Online (regla publicada) |
|---|---|---|---|
| B | 1730 | 4/47 = 8,5% [2,4; 20,4] | 3/21 = 14,3% [3,0; 36,3] (n = 75) |
| B | 1750 | 3/49 = 6,1% [1,3; 16,9] | 3/49 = 6,1% [1,3; 16,9] (n = 49) |
| B | 1772 | 0/50 = 0% [0; 7,1] | 0/43 = 0% [0; 8,2] (n = 56) |
| B | 1797 | 0/1 (no evaluable) | **no converge** (solo 50 sanas) |
| A | 1730 | 8/355 = 2,3% [1,0; 4,4] | 11/346 = 3,2% [1,6; 5,6] |
| A | 1750 | 9/355 = 2,5% [1,2; 4,8] | 13/343 = 3,8% [2,0; 6,4] |
| A | 1772 | **30/354 = 8,5% [5,8; 11,9]** | 34/354 = 9,6% [6,7; 13,2] |
| A | 1797 | 5/154 = 3,2% [1,1; 7,4] | 7/154 = 4,5% [1,8; 9,1] |

**Lectura:**
- Con el máximo de 49, la cobertura realizada sigue una Beta(49, 1): P(FAR > 5%) ≈ 8%. Los valores de B son compatibles con eso, pero con 50 sanas no se puede distinguir nada.
- A 1772 rpm en A, un 8,5% sobre 354 sanas tendría una probabilidad de ~1% bajo intercambiabilidad. Hay **deriva cronológica dentro del registro**: Spearman entre el índice temporal y el residuo da +0,21 (p = 3·10⁻⁵) en 1730 y 1772 en A, +0,26 (p = 0,01) en 1750 en B y +0,29 (p = 0,045) en 1797 en B.
- **Cuidado al leer A:** sus ventanas sanas duran 25 ms, así que sus 49 primeras cubren solo 1,2 s de registro. En B cubren unos 5 s.

**Para el paper:** CWRU no tiene suficientes sanas para validar la cobertura certificada con n ≥ 99 ni para medir la FAR con precisión. Sirve como ilustración del procedimiento, no como validación de la garantía.

## 6. 1797 rpm es un caso aparte

- Su Normal dura la mitad (5,1 s a 48 kHz, 50 ventanas de 3 vueltas).
- Su espectro es distinto: la mediana de cruces por cero en B es 0,566, frente a 0,42–0,43 en las otras tres Normal.
- Con cruces por cero separa todos los fallos de su condición (AUROC ≥ 0,98), mientras que en las otras tres no.
- Su radio es el mayor y ningún otro radio la cubre.

**Propuesta:** tratar 1797 como condición con datos insuficientes, ya sea excluyéndola del análisis de calibración o reportándola aparte con esa etiqueta.

## 7. Otras observaciones

- **Velocidades de los `B_28_DE12`:** se estiman un 2% por debajo del resto de su condición (28,14 Hz a 1730 y 28,58 Hz a 1750). `1772_OR@12_7_DE12` da 29,94 Hz, que corresponde a 1797 rpm. Son posibles inconsistencias del propio archivo CWRU. Solo afectan a C, porque en B no hay ficheros de 28.
- **Operadores:**
  - En tiempo: 72 épocas, val_loss 0,0237.
  - En órdenes: 31 épocas, val_loss 0,0647. El residuo nominal es mayor en órdenes, quizá porque la resonancia se mueve en orden con la velocidad simulada (±10%).
- **El test preexistente `test_conv_autoencoder.py::test_operator_validates_input` falla en este entorno** (TensorFlow 2.21, CPU): el autoencoder de ese test no aprende. No lo he tocado. Conviene mirarlo en tu Mac.
- **IMS no se ha tocado.** Ahí no hay problema de frecuencia de muestreo, pero si adoptamos la proyección como parte del método, IMS debería pasar por ella también para ser coherentes (2000 rpm constantes, 20 kHz → 400 muestras por vuelta).

## Cómo reproducir

```bash
cd reproducibility_package
python3 -m pytest tests/test_order_domain.py -q
python3 cwru_projection_experiment.py --cwru-root PATH/CWRU_Bearing_NumPy/Data \
        --out results/cwru_projection          # ~35 min en CPU
python3 cwru_projection_report.py results/cwru_projection > ../mssp_paper/notas/tablas_cwru_proyeccion.md
```

Hacen falta los ficheros `Normal`, `DE48` y `DE12` (B, IR, OR) del redistribuible de srigas. `download_datasets.sh` ya lo baja entero.
