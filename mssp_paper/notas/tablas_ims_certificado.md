# IMS: recalibración certificada desde la caché de residuos

*Generado por `reproducibility_package/ims_certified_recalibration.py` a partir de `results/field_residuals_ims.npz`. No editar a mano: `tests/test_generated_notes.py` comprueba que coincide byte a byte.*

Operador compartido, residuos y regla de persistencia (8 de 10) idénticos a los publicados; solo cambia el radio. La FAR se mide en los registros sanos entre el final de la calibración y el registro 200. Solo el bearing 1 falla (pista exterior); en 2–4 la salida es de su vecindad nominal, no un fallo documentado.

| bearing | radio | n calib. | rango k | τ | FAR sanas (%) | salida (registro) | antelación (h) | excedencia tras salida (%) |
|---|---|---|---|---|---|---|---|---|
| 1 (fallo) | publicado (cuantil interpolado, parada adaptativa) | 49 | — | 0,014150 | 0,00 | 539 | 73,83 | 100,00 |
| 1 (fallo) | r_(k), n=49 | 49 | 49 | 0,014206 | 0,00 (0/151) | 539 | 73,83 | 100,00 |
| 1 (fallo) | r_(k), n=99 | 99 | 98 | 0,014147 | 0,00 (0/101) | 539 | 73,83 | 100,00 |
| 1 (fallo) | r_(k), n=149 | 149 | 147 | 0,014144 | 0,00 (0/51) | 539 | 73,83 | 100,00 |
| 1 (fallo) | tolerancia 0,98/0,95, n=149 | 149 | 149 | 0,014206 | 0,00 (0/51) | 539 | 73,83 | 100,00 |
| 2 | publicado (cuantil interpolado, parada adaptativa) | 54 | — | 0,018596 | 0,00 | 794 | 31,33 | 93,09 |
| 2 | r_(k), n=49 | 49 | 49 | 0,018615 | 0,00 (0/151) | 794 | 31,33 | 92,02 |
| 2 | r_(k), n=99 | 99 | 98 | 0,018605 | 0,00 (0/101) | 794 | 31,33 | 92,02 |
| 2 | r_(k), n=149 | 149 | 147 | 0,018564 | 0,00 (0/51) | 791 | 31,83 | 93,19 |
| 2 | tolerancia 0,98/0,95, n=149 | 149 | 149 | 0,018615 | 0,00 (0/51) | 794 | 31,33 | 92,02 |
| 3 | publicado (cuantil interpolado, parada adaptativa) | 49 | — | 0,021798 | 0,00 | 896 | 14,33 | 100,00 |
| 3 | r_(k), n=49 | 49 | 49 | 0,021930 | 0,00 (0/151) | 896 | 14,33 | 100,00 |
| 3 | r_(k), n=99 | 99 | 98 | 0,021792 | 0,00 (0/101) | 896 | 14,33 | 100,00 |
| 3 | r_(k), n=149 | 149 | 147 | 0,021500 | 0,00 (0/51) | 892 | 15,00 | 100,00 |
| 3 | tolerancia 0,98/0,95, n=149 | 149 | 149 | 0,021930 | 0,00 (0/51) | 896 | 14,33 | 100,00 |
| 4 | publicado (cuantil interpolado, parada adaptativa) | 49 | — | 0,009729 | 1,32 | 667 | 52,50 | 94,92 |
| 4 | r_(k), n=49 | 49 | 49 | 0,009815 | 0,00 (0/151) | 705 | 46,17 | 99,28 |
| 4 | r_(k), n=99 | 99 | 98 | 0,009725 | 1,98 (2/101) | 667 | 52,50 | 94,92 |
| 4 | r_(k), n=149 | 149 | 147 | 0,009709 | 3,92 (2/51) | 667 | 52,50 | 95,24 |
| 4 | tolerancia 0,98/0,95, n=149 | 149 | 149 | 0,009815 | 0,00 (0/51) | 705 | 46,17 | 99,28 |

## Qué garantiza cada longitud de puesta en marcha

Cobertura objetivo 0,98. La cobertura real del radio congelado r_(k) sigue una Beta(k, n − k + 1) bajo intercambiabilidad, sea cual sea la distribución.

| n | rango k | garantía | E[cobertura] | P(cobertura < 0,98) | P(cobertura < 0,95) | horas de puesta en marcha (IMS) |
|---|---|---|---|---|---|---|
| 49 | 49 | en promedio (mínimo absoluto, rango degenerado: máximo) | 0,9800 | 0,372 | 0,081 | 8,2 |
| 99 | 98 | en promedio, fuera del rango degenerado | 0,9800 | 0,409 | 0,039 | 16,5 |
| 149 | 149 | con confianza: cobertura ≥ 0,98 con prob. ≥ 0,95 | 0,9933 | 0,049 | 0,000 | 24,8 |

## Intercambiabilidad en la calibración

Spearman entre el índice temporal y el residuo en los 149 primeros registros (prueba de deriva cronológica, en lugar de la ablación por permutación).

| bearing | ρ | p |
|---|---|---|
| 1 | -0,359 | 6,7e-06 |
| 2 | 0,081 | 0,33 |
| 3 | -0,602 | 4,5e-16 |
| 4 | -0,066 | 0,42 |

Registros activos por bearing (sin los finales con el banco parado): 1: 982, 2: 982, 3: 982, 4: 982.
Intervalo entre registros: 10 min.
