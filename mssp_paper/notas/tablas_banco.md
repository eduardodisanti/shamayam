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
| bench_q | 42 | sí | 0,513 | 16 | 1,21 |
| bench_q | 0 | sí | 0,510 | 15 | 1,18 |
| bench_q | 1 | sí | 0,514 | 15 | 1,17 |
| bench_q | 2 | sí | 0,509 | 15 | 1,18 |
| bench_q | 3 | sí | 0,501 | 22 | 1,29 |
| bench_qg | 42 | sí | 0,519 | 14 | 1,17 |
| bench_qg | 0 | sí | 0,507 | 19 | 1,25 |
| bench_qg | 1 | sí | 0,508 | 17 | 1,23 |
| bench_qg | 2 | sí | 0,519 | 15 | 1,17 |
| bench_qg | 3 | sí | 0,510 | 19 | 1,26 |
| noise_qg | 42 | sí | 1,000 | 13 | 1,00 |
| noise_qg | 0 | sí | 1,000 | 13 | 1,00 |
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
| bench_q | 49 | 0,0% [0,0–0,0]; 539–539 | 0,0% [0,0–0,0]; 709–709 | 0,0% [0,0–0,0]; 881–881 | 1,9% [1,7–2,0]; 656–656 |
| bench_q | 99 | 0,0% [0,0–0,0]; 539–539 | 0,0% [0,0–0,0]; 710–710 | 0,0% [0,0–0,0]; 879–881 | 1,9% [1,7–2,0]; 656–656 |
| bench_q | 149 | 0,0% [0,0–0,0]; 539–539 | 0,0% [0,0–0,0]; 709–709 | 0,0% [0,0–0,0]; 879–879 | 1,9% [1,7–2,0]; 656–656 |
| bench_q | 200 | 0,1% [0,0–0,3]; 538–539 | 0,0% [0,0–0,0]; 709–709 | 0,0% [0,0–0,0]; 878–879 | 1,9% [1,7–2,0]; 656–656 |
| bench_qg | 49 | 0,5% [0,0–1,7]; sin salida | 3,8% [0,3–9,7]; 882–922 | 5,8% [1,0–9,3]; 865–907 | 1,5% [0,0–2,3]; 900–905 |
| bench_qg | 99 | 0,9% [0,3–2,0]; sin salida | 2,9% [0,7–6,3]; 882–918 | 3,3% [1,3–5,7]; 888–901 | 2,5% [1,3–4,3]; 899–900 |
| bench_qg | 149 | 1,1% [0,3–2,3]; sin salida | 2,2% [0,7–4,0]; 882–923 | 2,6% [1,3–5,0]; 891–905 | 2,6% [1,3–5,0]; 899–900 |
| bench_qg | 200 | 0,9% [0,3–1,7]; sin salida | 2,9% [0,7–4,0]; 882–919 | 2,5% [1,3–4,3]; 891–903 | 1,8% [0,3–3,0]; 899–901 |
| noise_qg | 49 | 2,2% [0,3–4,3]; sin salida | 2,2% [0,0–4,0]; sin salida | 0,9% [0,0–2,0]; sin salida | 3,3% [0,0–7,3]; sin salida |
| noise_qg | 99 | 2,2% [1,0–3,0]; sin salida | 2,9% [0,7–6,0]; sin salida | 1,5% [0,3–3,0]; sin salida | 3,5% [1,7–6,0]; sin salida |
| noise_qg | 149 | 2,3% [1,0–4,0]; sin salida | 2,9% [1,0–6,0]; sin salida | 2,2% [0,7–5,3]; sin salida | 3,1% [0,3–6,0]; sin salida |
| noise_qg | 200 | 1,7% [1,0–2,7]; sin salida | 2,8% [1,0–4,3]; sin salida | 1,9% [1,0–3,0]; sin salida | 3,5% [0,3–6,0]; sin salida |

## Ottawa: operación

Media [mín–máx] sobre semillas.

| variante | puesta en marcha | FAR ventanas | registros sanos con alarma (de 8) | AUROC pista interior | AUROC bola | AUROC combinado | AUROC pista exterior |
|---|---|---|---|---|---|---|---|
| bench_q | los cuatro ensayos 1 | 7,9% [7,4–8,4] | 1,0 [1,0–1,0] | 0,997 [0,997–0,997] | 0,806 [0,798–0,816] | 0,995 [0,995–0,995] | 0,493 [0,449–0,529] |
| bench_q | A-1 | 40,6% [39,2–43,3] | 8,0 [8,0–8,0] | 0,997 [0,997–0,997] | 0,806 [0,798–0,816] | 0,995 [0,995–0,995] | 0,493 [0,449–0,529] |
| bench_qg | los cuatro ensayos 1 | 1,6% [0,6–2,6] | 0,0 [0,0–0,0] | 0,545 [0,516–0,593] | 0,502 [0,471–0,526] | 0,586 [0,542–0,688] | 0,647 [0,623–0,676] |
| bench_qg | A-1 | 3,1% [0,4–11,7] | 0,0 [0,0–0,0] | 0,545 [0,516–0,593] | 0,502 [0,471–0,526] | 0,586 [0,542–0,688] | 0,647 [0,623–0,676] |
| noise_qg | los cuatro ensayos 1 | 2,0% [1,1–2,6] | 0,0 [0,0–0,0] | 0,510 [0,483–0,541] | 0,506 [0,466–0,550] | 0,495 [0,480–0,521] | 0,501 [0,445–0,542] |
| noise_qg | A-1 | 3,0% [0,7–9,1] | 0,0 [0,0–0,0] | 0,510 [0,483–0,541] | 0,506 [0,466–0,550] | 0,495 [0,480–0,521] | 0,501 [0,445–0,542] |

## H1: ¿se transfiere la forma? (sección qg, Ottawa)

AUROC ventana a ventana, media [mín–máx] sobre 5 semillas. Intervalos por bootstrap de registros (2000 remuestreos). 'Supera controles': semillas en que el intervalo de la diferencia pareada con C-ruido y con C-simulador queda entero por encima de 0.

### Todas las ventanas

| fallo | banco qg | C-ruido qg | C-simulador qg | por máquina qg (techo) | curtosis | supera controles | se transfiere |
|---|---|---|---|---|---|---|---|
| pista interior | 0,545 [0,516–0,593] | 0,510 [0,483–0,541] | 0,605 [0,596–0,615] | 0,998 [0,990–1,000] | 0,991 [0,991–0,991] | 0/5 | no |
| bola | 0,502 [0,471–0,526] | 0,506 [0,466–0,550] | 0,479 [0,441–0,506] | 0,850 [0,835–0,856] | 0,507 [0,507–0,507] | 0/5 | no |
| combinado | 0,586 [0,542–0,688] | 0,495 [0,480–0,521] | 0,405 [0,401–0,411] | 0,994 [0,988–0,997] | 1,000 [1,000–1,000] | 3/5 | no |
| pista exterior | 0,647 [0,623–0,676] | 0,501 [0,445–0,542] | 0,447 [0,430–0,462] | 0,297 [0,282–0,319] | 0,988 [0,988–0,988] | 5/5 | no (no entra en H1) |

### Solo ventanas de 15–25 Hz

| fallo | banco qg | C-ruido qg | C-simulador qg | por máquina qg (techo) | curtosis | supera controles | se transfiere |
|---|---|---|---|---|---|---|---|
| pista interior | 0,557 [0,526–0,615] | 0,512 [0,480–0,557] | 0,611 [0,604–0,620] | 0,997 [0,987–1,000] | 0,989 [0,989–0,989] | 0/5 | no |
| bola | 0,516 [0,484–0,541] | 0,504 [0,453–0,553] | 0,493 [0,457–0,514] | 0,867 [0,853–0,875] | 0,507 [0,507–0,507] | 0/5 | no |
| combinado | 0,598 [0,548–0,701] | 0,501 [0,487–0,528] | 0,422 [0,419–0,427] | 0,994 [0,986–0,997] | 1,000 [1,000–1,000] | 3/5 | no |
| pista exterior | 0,670 [0,650–0,701] | 0,501 [0,433–0,543] | 0,454 [0,439–0,471] | 0,335 [0,319–0,360] | 0,990 [0,990–0,990] | 5/5 | no (no entra en H1) |

**Veredicto H1:** no se detecta transferencia con este método.
