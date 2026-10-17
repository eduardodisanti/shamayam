# Banco de pruebas (CWRU) → IMS y Ottawa

*Generado por `reproducibility_package/bench_report.py` desde `results/bench/` (`bench_transfer.py`). Criterios del protocolo registrado `06_protocolo_banco.md` v1, aplicados como código. No editar a mano: `tests/test_generated_notes.py` lo comprueba byte a byte.*

## Banco y entrenamiento (diagnósticos solo del banco)

| carga (rpm) | eje estimado (Hz) | segundos |
|---|---|---|
| 1797 | 29,92 | 5,1 |
| 1772 | 29,53 | 10,1 |
| 1750 | 29,15 | 10,1 |
| 1730 | 28,74 | 10,1 |

| variante | semilla | aprende | no reconstruida (validación) | épocas | val / train |
|---|---|---|---|---|---|
| bench_q | 42 | sí | 0,514 | 16 | 1,23 |
| bench_q | 0 | sí | 0,508 | 14 | 1,17 |
| bench_q | 1 | sí | 0,515 | 15 | 1,17 |
| bench_q | 2 | sí | 0,509 | 15 | 1,18 |
| bench_q | 3 | sí | 0,500 | 21 | 1,28 |
| bench_qg | 42 | sí | 0,521 | 14 | 1,18 |
| bench_qg | 0 | sí | 0,507 | 18 | 1,25 |
| bench_qg | 1 | sí | 0,507 | 17 | 1,23 |
| bench_qg | 2 | sí | 0,518 | 14 | 1,16 |
| bench_qg | 3 | sí | 0,506 | 16 | 1,21 |
| noise_qg | 42 | sí | 1,000 | 13 | 1,00 |
| noise_qg | 0 | sí | 1,000 | 14 | 1,00 |
| noise_qg | 1 | sí | 1,000 | 12 | 1,00 |
| noise_qg | 2 | sí | 1,000 | 12 | 1,00 |
| noise_qg | 3 | sí | 1,000 | 12 | 1,00 |

## H2: opera en IMS (banco en q, n = 99)

| semilla | salida bearing 1 | FAR bearing 1 | cumple |
|---|---|---|---|
| 42 | 539 | 0,0% | sí |
| 0 | 539 | 0,0% | sí |
| 1 | 539 | 0,0% | sí |
| 2 | 539 | 0,0% | sí |
| 3 | 539 | 0,0% | sí |

**Veredicto H2:** opera (criterio: salida ≤ 549 y FAR ≤ 2% en al menos 4 de 5 semillas).

## IMS: todas las variantes

Media [mín–máx] sobre semillas. FAR en los registros 200–499; salida: rango de registros.

| variante | n | bearing 1 | bearing 2 | bearing 3 | bearing 4 |
|---|---|---|---|---|---|
| bench_q | 49 | 0,0% [0,0–0,0]; 539–539 | 0,0% [0,0–0,0]; 709–709 | 0,0% [0,0–0,0]; 881–883 | 1,8% [1,7–2,0]; 656–656 |
| bench_q | 99 | 0,0% [0,0–0,0]; 539–539 | 0,0% [0,0–0,0]; 710–711 | 0,0% [0,0–0,0]; 879–881 | 1,8% [1,7–2,0]; 656–656 |
| bench_q | 149 | 0,0% [0,0–0,0]; 539–539 | 0,0% [0,0–0,0]; 709–709 | 0,0% [0,0–0,0]; 879–879 | 2,0% [1,7–2,3]; 656–656 |
| bench_q | 200 | 0,1% [0,0–0,3]; 539–539 | 0,0% [0,0–0,0]; 709–709 | 0,0% [0,0–0,0]; 878–879 | 2,0% [1,7–2,3]; 656–656 |
| bench_qg | 49 | 0,5% [0,0–1,7]; sin salida | 3,7% [1,3–6,0]; 881–919 | 6,4% [1,7–10,3]; 862–917 | 2,2% [0,0–4,3]; 894–905 |
| bench_qg | 99 | 0,6% [0,0–1,7]; sin salida | 2,4% [0,7–6,0]; 881–921 | 2,7% [0,3–6,3]; 887–917 | 1,8% [0,0–4,0]; 894–905 |
| bench_qg | 149 | 0,5% [0,3–1,0]; sin salida | 2,1% [0,7–6,0]; 881–924 | 2,6% [1,0–5,7]; 888–917 | 1,7% [0,0–3,7]; 894–905 |
| bench_qg | 200 | 0,7% [0,3–1,0]; sin salida | 3,1% [1,0–7,7]; 881–921 | 1,7% [1,0–3,3]; 891–933 | 1,8% [0,0–3,3]; 888–905 |
| noise_qg | 49 | 2,2% [0,3–4,3]; sin salida | 2,2% [0,0–4,0]; sin salida | 0,9% [0,0–2,0]; sin salida | 3,3% [0,0–7,3]; sin salida |
| noise_qg | 99 | 2,2% [1,0–3,0]; sin salida | 2,9% [0,7–6,0]; sin salida | 1,5% [0,3–3,0]; sin salida | 3,5% [1,7–6,0]; sin salida |
| noise_qg | 149 | 2,3% [1,0–4,0]; sin salida | 2,9% [1,0–6,0]; sin salida | 2,2% [0,7–5,3]; sin salida | 3,1% [0,3–6,0]; sin salida |
| noise_qg | 200 | 1,7% [1,0–2,7]; sin salida | 2,8% [1,0–4,3]; sin salida | 1,9% [1,0–3,0]; sin salida | 3,5% [0,3–6,0]; sin salida |

## Ottawa: operación

Media [mín–máx] sobre semillas.

| variante | puesta en marcha | FAR ventanas | registros sanos con alarma (de 8) | AUROC pista interior | AUROC bola | AUROC combinado | AUROC pista exterior |
|---|---|---|---|---|---|---|---|
| bench_q | los cuatro ensayos 1 | 7,7% [6,9–8,4] | 1,0 [1,0–1,0] | 0,997 [0,997–0,997] | 0,809 [0,798–0,822] | 0,995 [0,995–0,995] | 0,479 [0,421–0,527] |
| bench_q | A-1 | 40,7% [38,5–43,3] | 8,0 [8,0–8,0] | 0,997 [0,997–0,997] | 0,809 [0,798–0,822] | 0,995 [0,995–0,995] | 0,479 [0,421–0,527] |
| bench_qg | los cuatro ensayos 1 | 1,4% [0,4–2,0] | 0,0 [0,0–0,0] | 0,551 [0,513–0,570] | 0,516 [0,492–0,534] | 0,608 [0,546–0,676] | 0,642 [0,583–0,686] |
| bench_qg | A-1 | 1,6% [0,2–3,2] | 0,0 [0,0–0,0] | 0,551 [0,513–0,570] | 0,516 [0,492–0,534] | 0,608 [0,546–0,676] | 0,642 [0,583–0,686] |
| noise_qg | los cuatro ensayos 1 | 2,0% [1,1–2,6] | 0,0 [0,0–0,0] | 0,510 [0,483–0,541] | 0,506 [0,466–0,550] | 0,495 [0,480–0,521] | 0,501 [0,445–0,542] |
| noise_qg | A-1 | 3,0% [0,7–9,1] | 0,0 [0,0–0,0] | 0,510 [0,483–0,541] | 0,506 [0,466–0,550] | 0,495 [0,480–0,521] | 0,501 [0,445–0,542] |

## H1: ¿se transfiere la forma? (sección qg, Ottawa)

AUROC ventana a ventana, media [mín–máx] sobre 5 semillas. Intervalos por bootstrap de registros (2000 remuestreos). 'Supera controles': semillas en que el intervalo de la diferencia pareada con C-ruido y con C-simulador queda entero por encima de 0.

### Todas las ventanas

| fallo | banco qg | C-ruido qg | C-simulador qg | por máquina qg (techo) | curtosis | supera controles | se transfiere |
|---|---|---|---|---|---|---|---|
| pista interior | 0,551 [0,513–0,570] | 0,510 [0,483–0,541] | 0,603 [0,590–0,627] | 0,999 [0,997–1,000] | 0,991 [0,991–0,991] | 0/5 | no |
| bola | 0,516 [0,492–0,534] | 0,506 [0,466–0,550] | 0,476 [0,438–0,528] | 0,849 [0,841–0,854] | 0,507 [0,507–0,507] | 0/5 | no |
| combinado | 0,608 [0,546–0,676] | 0,495 [0,480–0,521] | 0,405 [0,393–0,412] | 0,995 [0,993–0,996] | 1,000 [1,000–1,000] | 4/5 | no |
| pista exterior | 0,642 [0,583–0,686] | 0,501 [0,445–0,542] | 0,445 [0,432–0,457] | 0,305 [0,288–0,317] | 0,988 [0,988–0,988] | 5/5 | no (no entra en H1) |

### Solo ventanas de 15–25 Hz

| fallo | banco qg | C-ruido qg | C-simulador qg | por máquina qg (techo) | curtosis | supera controles | se transfiere |
|---|---|---|---|---|---|---|---|
| pista interior | 0,564 [0,511–0,597] | 0,512 [0,480–0,557] | 0,609 [0,600–0,630] | 0,999 [0,997–1,000] | 0,989 [0,989–0,989] | 0/5 | no |
| bola | 0,529 [0,498–0,553] | 0,504 [0,453–0,553] | 0,489 [0,452–0,536] | 0,866 [0,858–0,871] | 0,507 [0,507–0,507] | 0/5 | no |
| combinado | 0,618 [0,547–0,690] | 0,501 [0,487–0,528] | 0,422 [0,412–0,428] | 0,995 [0,993–0,996] | 1,000 [1,000–1,000] | 4/5 | no |
| pista exterior | 0,663 [0,611–0,705] | 0,501 [0,433–0,543] | 0,451 [0,442–0,461] | 0,346 [0,326–0,361] | 0,990 [0,990–0,990] | 5/5 | no (no entra en H1) |

**Veredicto H1:** no se detecta transferencia con este método.
