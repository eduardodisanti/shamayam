# Protocolo v3: la firma con el cociente completo, vista en el espectro de la envolvente (banco CWRU → IMS, Ottawa y XJTU)

*Generado por `reproducibility_package/bench_report_v3.py` desde `results/bench_v3/` (`bench_transfer_v3.py`). Criterios de `10_protocolo_banco_v3.md`, como código registrado antes de la ejecución. No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

Sección: preblanqueo cepstral por registro (Hz) → remuestreo angular → ventanas de 30 vueltas → s = log(SES de Welch / mediana), órdenes 0,1–120.

## Entrenamiento (diagnósticos solo del banco, de los controles y del techo)

| modelo | semilla | aprende | no reconstruida | épocas | val / train |
|---|---|---|---|---|---|
| bench_s | 42 | colapso | 0,997 | — | — |
| bench_s | 0 | colapso | 0,995 | — | — |
| bench_s | 1 | colapso | 1,008 | — | — |
| bench_s | 2 | colapso | 1,005 | — | — |
| bench_s | 3 | colapso | 0,998 | — | — |
| noise_s | 42 | sí | 1,000 | 27 | 1,00 |
| noise_s | 0 | sí | 1,000 | 17 | 1,00 |
| noise_s | 1 | sí | 1,000 | 13 | 1,00 |
| noise_s | 2 | sí | 1,000 | 17 | 1,00 |
| noise_s | 3 | sí | 1,000 | 29 | 1,00 |
| sim_s | 42 | sí | 0,869 | 14 | 1,11 |
| sim_s | 0 | sí | 0,877 | 15 | 1,09 |
| sim_s | 1 | sí | 0,861 | 16 | 1,07 |
| sim_s | 2 | sí | 0,866 | 15 | 1,06 |
| sim_s | 3 | sí | 0,868 | 15 | 1,05 |
| local_s | 0 | sí | 0,014 | — | 1,44 |
| local_s | 1 | sí | 0,014 | — | 1,42 |
| local_s | 2 | sí | 0,015 | — | 1,40 |
| local_s | 3 | sí | 0,014 | — | 1,47 |
| local_s | 4 | sí | 0,014 | — | 1,38 |

## H2v3: IMS, bearing 1, banco s, n = 99

| semilla | salida | FAR | cumple |
|---|---|---|---|
| 42 | colapso | — | no |
| 0 | colapso | — | no |
| 1 | colapso | — | no |
| 2 | colapso | — | no |
| 3 | colapso | — | no |

**Veredicto H2v3:** no cumple el criterio.

## IMS: todos los modelos

Media [mín–máx] sobre semillas; FAR en los registros 200–499; salida del bearing 1 (rango).

| modelo | n | FAR bearing 1 | salida bearing 1 |
|---|---|---|---|
| bench_s | 49 | colapso | — |
| bench_s | 99 | colapso | — |
| bench_s | 149 | colapso | — |
| bench_s | 200 | colapso | — |
| noise_s | 49 | 0,0% [0,0–0,0] | 980–980 |
| noise_s | 99 | 2,9% [2,7–3,0] | 709–709 |
| noise_s | 149 | 2,9% [2,7–3,0] | 709–709 |
| noise_s | 200 | 2,9% [2,7–3,0] | 709–709 |
| sim_s | 49 | 0,9% [0,7–1,3] | 709–709 |
| sim_s | 99 | 1,7% [1,0–2,7] | 708–709 |
| sim_s | 149 | 2,1% [1,0–2,7] | 708–709 |
| sim_s | 200 | 2,7% [1,7–3,7] | 708–708 |
| kurt_s | 49 | 0,0% | 712–712 |
| kurt_s | 99 | 0,0% | 709–709 |
| kurt_s | 149 | 0,0% | 709–709 |
| kurt_s | 200 | 0,0% | 709–709 |
| env_s | 49 | 0,0% | 706–706 |
| env_s | 99 | 0,0% | 704–704 |
| env_s | 149 | 0,0% | 639–639 |
| env_s | 200 | 0,0% | 639–639 |

## Ottawa: operación (los cuatro ensayos 1)

| modelo | FAR ventanas | registros sanos con alarma | AUROC pista interior | AUROC bola | AUROC combinado | AUROC pista exterior |
|---|---|---|---|---|---|---|
| bench_s | colapso | — | — | — | — | — |
| noise_s | 0,0% [0,0–0,0] | 0,0 [0,0–0,0] | 1,000 [1,000–1,000] | 0,602 [0,601–0,604] | 0,998 [0,998–0,998] | 1,000 [1,000–1,000] |
| sim_s | 0,0% [0,0–0,0] | 0,0 [0,0–0,0] | 1,000 [1,000–1,000] | 0,684 [0,672–0,692] | 0,633 [0,626–0,645] | 0,948 [0,941–0,962] |
| kurt_s | 0,0% | 0,0 | 0,996 | 0,377 | 1,000 | 1,000 |
| env_s | 0,0% | 0,0 | 1,000 | 0,742 | 0,973 | 0,998 |

## H1v3: ¿se transfiere la firma? (banco s, Ottawa)

Modelos del banco s que aprenden con no reconstruida ≤ 0,95: 0 de 5.

### Todas las ventanas

| fallo | banco s | C-ruido s | C-simulador s | por máquina s (techo) | curtosis (30 vueltas) | envolvente (30 vueltas) | supera controles | se transfiere |
|---|---|---|---|---|---|---|---|---|
| pista interior | — | 1,000 [1,000–1,000] | 1,000 [1,000–1,000] | 1,000 [1,000–1,000] | 0,996 | 1,000 | 0/0 | no |
| bola | — | 0,602 [0,601–0,604] | 0,684 [0,672–0,692] | 0,787 [0,776–0,799] | 0,377 | 0,742 | 0/0 | no |
| combinado | — | 0,998 [0,998–0,998] | 0,633 [0,626–0,645] | 0,997 [0,996–0,998] | 1,000 | 0,973 | 0/0 | no |
| pista exterior | — | 1,000 [1,000–1,000] | 0,948 [0,941–0,962] | 1,000 [1,000–1,000] | 1,000 | 0,998 | 0/0 | no (no entra en H1) |

### Solo ventanas de 15–25 Hz

| fallo | banco s | C-ruido s | C-simulador s | por máquina s (techo) | curtosis (30 vueltas) | envolvente (30 vueltas) | supera controles | se transfiere |
|---|---|---|---|---|---|---|---|---|
| pista interior | — | 1,000 [1,000–1,000] | 1,000 [1,000–1,000] | 1,000 [1,000–1,000] | 0,998 | 1,000 | 0/0 | no |
| bola | — | 0,612 [0,610–0,614] | 0,690 [0,674–0,697] | 0,797 [0,790–0,807] | 0,390 | 0,775 | 0/0 | no |
| combinado | — | 1,000 [1,000–1,000] | 0,630 [0,624–0,643] | 0,999 [0,999–0,999] | 1,000 | 0,974 | 0/0 | no |
| pista exterior | — | 1,000 [1,000–1,000] | 0,944 [0,938–0,959] | 1,000 [1,000–1,000] | 1,000 | 0,998 | 0/0 | no (no entra en H1) |

**Veredicto H1v3:** no evaluable con este autoencoder (0 de 5 modelos del banco aprenden).

## H3v3 (secundario): XJTU, banco s, H+V, n = 99

| semilla | salen antes del final | FAR franja | cumple |
|---|---|---|---|

**Veredicto H3v3:** sin datos.

### XJTU: todos los modelos

| modelo | canal | n | salen | FAR franja |
|---|---|---|---|---|
| noise_s | H | 49 | 10/13 | 0,8%–0,9% |
| noise_s | H | 99 | 7/13 | 1,3%–1,4% |
| noise_s | H | 149 | 6/9 | 1,0%–1,2% |
| noise_s | H | 149t | 5/9 | 0,7%–0,7% |
| noise_s | V | 49 | 9/13 | 4,1%–4,2% |
| noise_s | V | 99 | 7/13 | 4,7%–4,9% |
| noise_s | V | 149 | 4/9 | 1,9%–2,1% |
| noise_s | V | 149t | 4/9 | 1,2%–1,3% |
| noise_s | H+V | 99 | 7/13 | 3,6%–3,8% |
| noise_s | H+V | 149 | 5/9 | 1,8%–1,9% |
| sim_s | H | 49 | 8–9/13 | 1,5%–1,9% |
| sim_s | H | 99 | 5/13 | 1,5%–2,3% |
| sim_s | H | 149 | 5/9 | 1,5%–2,3% |
| sim_s | H | 149t | 4–5/9 | 0,4%–1,1% |
| sim_s | V | 49 | 5–8/13 | 0,7%–1,1% |
| sim_s | V | 99 | 4–5/13 | 2,0%–3,1% |
| sim_s | V | 149 | 3–4/9 | 2,0%–3,2% |
| sim_s | V | 149t | 2–4/9 | 0,7%–1,1% |
| sim_s | H+V | 99 | 6–8/13 | 1,8%–2,2% |
| sim_s | H+V | 149 | 5–6/9 | 1,4%–1,8% |
| kurt_s | H | 49 | 10/13 | 1,8% |
| kurt_s | H | 99 | 7/13 | 2,4% |
| kurt_s | H | 149 | 6/9 | 1,9% |
| kurt_s | H | 149t | 6/9 | 0,8% |
| kurt_s | V | 49 | 11/13 | 3,8% |
| kurt_s | V | 99 | 7/13 | 4,5% |
| kurt_s | V | 149 | 5/9 | 1,4% |
| kurt_s | V | 149t | 4/9 | 0,4% |
| kurt_s | H+V | 99 | 7/13 | 4,5% |
| kurt_s | H+V | 149 | 6/9 | 1,1% |
| env_s | H | 49 | 10/13 | 1,6% |
| env_s | H | 99 | 6/13 | 1,7% |
| env_s | H | 149 | 6/9 | 1,6% |
| env_s | H | 149t | 6/9 | 0,0% |
| env_s | V | 49 | 10/13 | 1,2% |
| env_s | V | 99 | 7/13 | 1,9% |
| env_s | V | 149 | 6/9 | 2,0% |
| env_s | V | 149t | 4/9 | 0,9% |
| env_s | H+V | 99 | 7/13 | 2,4% |
| env_s | H+V | 149 | 6/9 | 0,9% |
