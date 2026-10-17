# XJTU-SY: quince fallos reales hasta el final de vida

*Generado por `reproducibility_package/xjtu_report.py` desde `results/xjtu/` (`xjtu_experiment.py`). Criterios de `09_protocolo_xjtu.md`, como código registrado antes de la ejecución. No editar a mano: lo comprueba un test byte a byte.*

Sección q: velocidad nominal, 400 muestras/vuelta, ventanas de 3 vueltas; un valor por registro (media de las ventanas). Radio r₍ₖ₎ con α = 0,02 (α/2 por canal en H+V); 149t = tolerancia 0,98/0,95 con n = 149. FAR en la franja sana declarada: registros [150, ⌊L/2⌋) de 2_1, 2_3, 3_1, 3_2 y 3_4, agregada.

## H1 (principal): oem_q, H+V, n = 99

| semilla | salen antes del final | FAR franja | cumple |
|---|---|---|---|
| 42 | 13/13 | 5,9% | no |
| 0 | 13/13 | 5,3% | no |
| 1 | 13/13 | 5,5% | no |
| 2 | 13/13 | 5,8% | no |
| 3 | 13/13 | 6,1% | no |

**Veredicto H1:** opera en parte.

## Por rodamiento: oem_q, H+V, n = 99 (rango sobre semillas)

| rodamiento | fallo | vida (min) | salida (registro) | antelación (min) | fracción de vida | salida temprana |
|---|---|---|---|---|---|---|
| 1_1 | pista exterior | 123 | 106–107 | 16–17 | 0,86–0,87 | 0/5 |
| 1_2 | pista exterior | 161 | 135 | 26 | 0,84 | 0/5 |
| 1_3 | pista exterior | 158 | 106 | 52 | 0,67 | 0/5 |
| 1_4 | jaula | 122 | 111–121 | 1–11 | 0,91–0,99 | 0/5 |
| 1_5 | pista interior y exterior | 52 | no comisionable | — | — | — |
| 2_1 | pista interior | 491 | 460 | 31 | 0,94 | 0/5 |
| 2_2 | pista exterior | 161 | 107–108 | 53–54 | 0,66–0,67 | 0/5 |
| 2_3 | jaula | 533 | 146–151 | 382–387 | 0,27–0,28 | 5/5 |
| 2_4 | pista exterior | 42 | no comisionable | — | — | — |
| 2_5 | pista exterior | 339 | 128 | 211 | 0,38 | 5/5 |
| 3_1 | pista exterior | 2538 | 2349–2354 | 184–189 | 0,93–0,93 | 0/5 |
| 3_2 | pista interior, bola, jaula y pista exterior | 2496 | 1238–1239 | 1257–1258 | 0,50–0,50 | 5/5 |
| 3_3 | pista interior | 371 | 348 | 23 | 0,94 | 0/5 |
| 3_4 | pista interior | 1515 | 1017–1422 | 93–498 | 0,67–0,94 | 0/5 |
| 3_5 | pista exterior | 114 | 106 | 8 | 0,93 | 0/5 |

## Menú de puesta en marcha: todos los modelos sin entrenamiento local

Salen = rodamientos comisionables con salida antes del final; rango sobre semillas cuando hay varias.

| modelo | canal | n | salen | FAR franja | salidas tempranas |
|---|---|---|---|---|---|
| oem_q | H | 49 | 12/13 | 4,5%–4,6% | 6 |
| oem_q | H | 99 | 11–12/13 | 4,6%–4,6% | 3 |
| oem_q | H | 149 | 9/9 | 4,6%–4,8% | 3 |
| oem_q | H | 149t | 8/9 | 3,6%–4,0% | 3 |
| oem_q | V | 49 | 13/13 | 4,5%–6,0% | 5 |
| oem_q | V | 99 | 13/13 | 1,4%–2,5% | 1 |
| oem_q | V | 149 | 8/9 | 1,6%–2,3% | 2 |
| oem_q | V | 149t | 8/9 | 0,4%–0,6% | 1 |
| oem_q | H+V | 99 | 13/13 | 5,3%–6,1% | 3 |
| oem_q | H+V | 149 | 9/9 | 3,8%–4,3% | 3 |
| bench_q | H | 49 | 12/13 | 5,0%–5,0% | 6 |
| bench_q | H | 99 | 12/13 | 5,0%–5,1% | 3 |
| bench_q | H | 149 | 9/9 | 5,0%–5,1% | 3 |
| bench_q | H | 149t | 8/9 | 4,0%–4,0% | 3 |
| bench_q | V | 49 | 13/13 | 4,3%–4,3% | 5 |
| bench_q | V | 99 | 13/13 | 1,3%–1,4% | 1 |
| bench_q | V | 149 | 8/9 | 1,3%–1,5% | 2 |
| bench_q | V | 149t | 8/9 | 0,3%–0,3% | 1 |
| bench_q | H+V | 99 | 12/13 | 4,7%–4,7% | 3 |
| bench_q | H+V | 149 | 9/9 | 4,1%–4,2% | 3 |
| rms | H | 49 | 13/13 | 8,6% | 6 |
| rms | H | 99 | 12/13 | 6,0% | 3 |
| rms | H | 149 | 9/9 | 5,1% | 3 |
| rms | H | 149t | 9/9 | 3,2% | 3 |
| rms | V | 49 | 13/13 | 5,2% | 5 |
| rms | V | 99 | 13/13 | 4,7% | 2 |
| rms | V | 149 | 8/9 | 3,8% | 2 |
| rms | V | 149t | 8/9 | 2,4% | 2 |
| rms | H+V | 99 | 12/13 | 5,5% | 3 |
| rms | H+V | 149 | 9/9 | 3,6% | 3 |
| kurtosis | H | 49 | 8/13 | 4,8% | 3 |
| kurtosis | H | 99 | 6/13 | 4,6% | 1 |
| kurtosis | H | 149 | 5/9 | 2,1% | 0 |
| kurtosis | H | 149t | 5/9 | 0,8% | 0 |
| kurtosis | V | 49 | 9/13 | 7,2% | 4 |
| kurtosis | V | 99 | 5/13 | 7,2% | 2 |
| kurtosis | V | 149 | 5/9 | 5,3% | 2 |
| kurtosis | V | 149t | 4/9 | 2,8% | 1 |
| kurtosis | H+V | 99 | 6/13 | 7,1% | 2 |
| kurtosis | H+V | 149 | 5/9 | 3,0% | 1 |
| crest | H | 49 | 7/13 | 6,2% | 3 |
| crest | H | 99 | 4/13 | 6,9% | 1 |
| crest | H | 149 | 3/9 | 4,5% | 0 |
| crest | H | 149t | 3/9 | 2,3% | 0 |
| crest | V | 49 | 3/13 | 6,6% | 1 |
| crest | V | 99 | 2/13 | 7,6% | 1 |
| crest | V | 149 | 4/9 | 5,8% | 1 |
| crest | V | 149t | 1/9 | 2,6% | 0 |
| crest | H+V | 99 | 5/13 | 7,8% | 1 |
| crest | H+V | 149 | 4/9 | 4,7% | 0 |
| envelope | H | 49 | 10/13 | 3,8% | 5 |
| envelope | H | 99 | 7/13 | 3,3% | 2 |
| envelope | H | 149 | 6/9 | 2,4% | 2 |
| envelope | H | 149t | 6/9 | 1,2% | 1 |
| envelope | V | 49 | 11/13 | 11,5% | 4 |
| envelope | V | 99 | 7/13 | 11,6% | 1 |
| envelope | V | 149 | 6/9 | 0,8% | 0 |
| envelope | V | 149t | 6/9 | 0,1% | 0 |
| envelope | H+V | 99 | 7/13 | 11,4% | 3 |
| envelope | H+V | 149 | 6/9 | 1,3% | 1 |

## H2: por máquina, canal horizontal (crudo frente a cociente)

| modelo | n | semillas | FAR franja (mediana) | FAR franja (rango) | salen |
|---|---|---|---|---|---|
| raw | 49 | 5 | 30,7% | 29,3%–31,7% | 12–13/13 |
| raw | 99 | 5 | 10,0% | 9,8%–15,7% | 11–12/13 |
| quot | 49 | 5 | 28,9% | 26,9%–30,3% | 11–12/13 |
| quot | 99 | 5 | 13,3% | 12,5%–19,9% | 11–12/13 |
| oem_q | 49 | 5 | 4,6% | 4,5%–4,6% | 12/13 |
| oem_q | 99 | 5 | 4,6% | 4,6%–4,6% | 11–12/13 |

**Veredicto H2** (n = 49; mediana raw 30,7%, quot 28,9%): no se replica.

## Diagnóstico de la franja sana (sin efecto sobre los veredictos)

Tendencia de Spearman del RMS dentro de la franja.

| rodamiento | canal | registros | ρ | p |
|---|---|---|---|---|
| 2_1 | H | 150–244 | -0,46 | 2.1e-06 |
| 2_1 | V | 150–244 | -0,20 | 5.1e-02 |
| 2_3 | H | 150–265 | 0,48 | 5.1e-08 |
| 2_3 | V | 150–265 | 0,46 | 1.9e-07 |
| 3_1 | H | 150–1268 | -0,16 | 5.8e-08 |
| 3_1 | V | 150–1268 | 0,07 | 2.3e-02 |
| 3_2 | H | 150–1247 | 0,24 | 2.2e-16 |
| 3_2 | V | 150–1247 | -0,29 | 1.8e-22 |
| 3_4 | H | 150–756 | -0,66 | 1.8e-77 |
| 3_4 | V | 150–756 | -0,71 | 1.5e-95 |

## Entrenamiento de los modelos de fábrica

| modelo | semilla | aprende | épocas | no reconstruida |
|---|---|---|---|---|
| oem_q | 42 | sí | 31 | — |
| oem_q | 0 | sí | 34 | — |
| oem_q | 1 | sí | 32 | — |
| oem_q | 2 | sí | 36 | — |
| oem_q | 3 | sí | 39 | — |
| bench_q | 42 | sí | 16 | 0,514 |
| bench_q | 0 | sí | 14 | 0,508 |
| bench_q | 1 | sí | 15 | 0,515 |
| bench_q | 2 | sí | 15 | 0,509 |
| bench_q | 3 | sí | 21 | 0,500 |

## Entrenamiento por máquina

| semilla | brazo | modelos | aprenden | no reconstruida |
|---|---|---|---|---|
| 0 | raw | 26 | 26 | 0,119–0,969 |
| 0 | quot | 26 | 25 | 0,129–0,763 |
| 1 | raw | 26 | 26 | 0,130–0,747 |
| 1 | quot | 26 | 25 | 0,119–0,768 |
| 2 | raw | 26 | 25 | 0,118–0,799 |
| 2 | quot | 26 | 24 | 0,122–0,729 |
| 3 | raw | 26 | 25 | 0,131–0,741 |
| 3 | quot | 26 | 25 | 0,125–0,765 |
| 4 | raw | 26 | 26 | 0,121–0,969 |
| 4 | quot | 26 | 24 | 0,116–0,771 |
