# Protocolo v2: la firma con el cociente completo (banco CWRU → IMS y Ottawa)

*Generado por `reproducibility_package/bench_report_v2.py` desde `results/bench_v2/` (`bench_transfer_v2.py`). Criterios de `08_protocolo_banco_v2.md`, como código registrado antes de la ejecución. No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

Sección: preblanqueo cepstral por registro (Hz) → remuestreo angular → (wg) normalización por ventana.

## Entrenamiento (diagnósticos solo del banco, de los controles y del techo)

| modelo | semilla | aprende | no reconstruida | épocas | val / train |
|---|---|---|---|---|---|
| bench_w | 42 | colapso | 1,000 | — | — |
| bench_w | 0 | colapso | 1,000 | — | — |
| bench_w | 1 | colapso | 1,000 | — | — |
| bench_w | 2 | colapso | 1,000 | — | — |
| bench_w | 3 | colapso | 1,000 | — | — |
| bench_wg | 42 | colapso | 1,000 | — | — |
| bench_wg | 0 | colapso | 1,000 | — | — |
| bench_wg | 1 | colapso | 1,000 | — | — |
| bench_wg | 2 | colapso | 1,000 | — | — |
| bench_wg | 3 | colapso | 1,000 | — | — |
| noise_wg | 42 | sí | 1,000 | 13 | 1,00 |
| noise_wg | 0 | sí | 1,000 | 13 | 1,00 |
| noise_wg | 1 | sí | 1,000 | 12 | 1,00 |
| noise_wg | 2 | sí | 1,000 | 12 | 1,00 |
| noise_wg | 3 | sí | 1,000 | 12 | 1,00 |
| sim_wg | 42 | colapso | 1,000 | — | — |
| sim_wg | 0 | colapso | 0,982 | — | — |
| sim_wg | 1 | colapso | 1,000 | — | — |
| sim_wg | 2 | sí | 0,973 | 15 | 1,07 |
| sim_wg | 3 | sí | 0,971 | 15 | 1,07 |
| local_wg | 0 | colapso | — | — | — |
| local_wg | 1 | colapso | — | — | — |
| local_wg | 2 | colapso | — | — | — |
| local_wg | 3 | colapso | — | — | — |
| local_wg | 4 | colapso | — | — | — |

## H2v2: IMS, bearing 1, banco w, n = 99

| semilla | salida | FAR | cumple |
|---|---|---|---|
| 42 | colapso | — | no |
| 0 | colapso | — | no |
| 1 | colapso | — | no |
| 2 | colapso | — | no |
| 3 | colapso | — | no |

**Veredicto H2v2:** no cumple el criterio.

## IMS: todos los modelos

Media [mín–máx] sobre semillas; FAR en los registros 200–499; salida del bearing 1 (rango).

| modelo | n | FAR bearing 1 | salida bearing 1 |
|---|---|---|---|
| bench_w | 49 | colapso | — |
| bench_w | 99 | colapso | — |
| bench_w | 149 | colapso | — |
| bench_w | 200 | colapso | — |
| bench_wg | 49 | colapso | — |
| bench_wg | 99 | colapso | — |
| bench_wg | 149 | colapso | — |
| bench_wg | 200 | colapso | — |
| noise_wg | 49 | 1,7% [0,0–5,7] | sin salida |
| noise_wg | 99 | 1,7% [0,0–5,3] | sin salida |
| noise_wg | 149 | 0,9% [0,3–2,0] | sin salida |
| noise_wg | 200 | 1,1% [0,3–2,0] | sin salida |
| sim_wg | 49 | 6,3% [3,3–9,3] | sin salida |
| sim_wg | 99 | 3,2% [1,7–4,7] | sin salida |
| sim_wg | 149 | 3,3% [2,0–4,7] | sin salida |
| sim_wg | 200 | 3,5% [2,3–4,7] | sin salida |
| kurt_w | 49 | 0,0% | 710–710 |
| kurt_w | 99 | 0,3% | 709–709 |
| kurt_w | 149 | 0,3% | 709–709 |
| kurt_w | 200 | 0,3% | 709–709 |
| env_w | 49 | 4,0% | 704–704 |
| env_w | 99 | 3,7% | 704–704 |
| env_w | 149 | 1,3% | 705–705 |
| env_w | 200 | 2,0% | 705–705 |

## Ottawa: operación (los cuatro ensayos 1)

| modelo | FAR ventanas | registros sanos con alarma | AUROC pista interior | AUROC bola | AUROC combinado | AUROC pista exterior |
|---|---|---|---|---|---|---|
| bench_w | colapso | — | — | — | — | — |
| bench_wg | colapso | — | — | — | — | — |
| noise_wg | 1,9% [0,7–2,6] | 0,0 [0,0–0,0] | 0,504 [0,473–0,527] | 0,506 [0,459–0,534] | 0,491 [0,474–0,507] | 0,500 [0,442–0,542] |
| sim_wg | 3,3% [2,6–4,1] | 0,0 [0,0–0,0] | 0,376 [0,364–0,388] | 0,431 [0,429–0,433] | 0,487 [0,476–0,497] | 0,475 [0,468–0,481] |
| kurt_w | 5,4% | 0,0 | 0,963 | 0,466 | 0,995 | 0,993 |
| env_w | 2,6% | 0,0 | 0,792 | 0,558 | 0,305 | 0,231 |

## H1v2: ¿se transfiere la firma? (banco wg, Ottawa)

Modelos del banco wg que aprenden con no reconstruida ≤ 0,95: 0 de 5.

### Todas las ventanas

| fallo | banco wg | C-ruido wg | C-simulador wg | por máquina wg (techo) | curtosis w | envolvente w | supera controles | se transfiere |
|---|---|---|---|---|---|---|---|---|
| pista interior | — | 0,504 [0,473–0,527] | 0,376 [0,364–0,388] | — | 0,963 | 0,792 | 0/0 | no |
| bola | — | 0,506 [0,459–0,534] | 0,431 [0,429–0,433] | — | 0,466 | 0,558 | 0/0 | no |
| combinado | — | 0,491 [0,474–0,507] | 0,487 [0,476–0,497] | — | 0,995 | 0,305 | 0/0 | no |
| pista exterior | — | 0,500 [0,442–0,542] | 0,475 [0,468–0,481] | — | 0,993 | 0,231 | 0/0 | no (no entra en H1) |

### Solo ventanas de 15–25 Hz

| fallo | banco wg | C-ruido wg | C-simulador wg | por máquina wg (techo) | curtosis w | envolvente w | supera controles | se transfiere |
|---|---|---|---|---|---|---|---|---|
| pista interior | — | 0,507 [0,469–0,544] | 0,371 [0,358–0,385] | — | 0,966 | 0,805 | 0/0 | no |
| bola | — | 0,504 [0,444–0,541] | 0,415 [0,406–0,424] | — | 0,488 | 0,567 | 0/0 | no |
| combinado | — | 0,494 [0,478–0,508] | 0,491 [0,475–0,507] | — | 0,998 | 0,292 | 0/0 | no |
| pista exterior | — | 0,501 [0,430–0,541] | 0,468 [0,454–0,482] | — | 0,996 | 0,210 | 0/0 | no (no entra en H1) |

**Veredicto H1v2:** no evaluable con este autoencoder (0 de 5 modelos del banco aprenden).
