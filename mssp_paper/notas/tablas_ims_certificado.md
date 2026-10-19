# IMS: recalibración certificada desde la caché de residuos

*Generado por `reproducibility_package/ims_certified_recalibration.py` a partir de `results/field_residuals_ims.npz`. No editar a mano: `tests/test_generated_notes.py` comprueba que coincide byte a byte.*

Operador compartido, residuos y regla de persistencia (8 de 10) idénticos a los de la referencia; solo cambia el radio. La FAR se mide en los registros sanos entre el final de la calibración y el registro 200. Solo el bearing 1 falla (pista exterior); en 2–4 la salida es de su vecindad nominal, no un fallo documentado.

| bearing | radio | n calib. | rango k | τ | FAR sanas (%) | salida (registro) | antelación (h) | excedencia tras salida (%) |
|---|---|---|---|---|---|---|---|---|
| 1 (fallo) | procedimiento del borrador (cuantil interpolado, parada adaptativa) | 49 | — | 0,014161 | 2,65 | 539 | 73,83 | 100,00 |
| 1 (fallo) | r_(k), n=49 | 49 | 49 | 0,014194 | 2,65 (4/151) | 539 | 73,83 | 100,00 |
| 1 (fallo) | r_(k), n=99 | 99 | 98 | 0,014210 | 0,99 (1/101) | 539 | 73,83 | 100,00 |
| 1 (fallo) | r_(k), n=149 | 149 | 147 | 0,014194 | 3,92 (2/51) | 539 | 73,83 | 100,00 |
| 1 (fallo) | tolerancia 0,98/0,95, n=149 | 149 | 149 | 0,014274 | 1,96 (1/51) | 539 | 73,83 | 100,00 |
| 2 | procedimiento del borrador (cuantil interpolado, parada adaptativa) | 49 | — | 0,018245 | 7,28 | 709 | 45,50 | 91,21 |
| 2 | r_(k), n=49 | 49 | 49 | 0,018305 | 5,30 (8/151) | 711 | 45,17 | 88,93 |
| 2 | r_(k), n=99 | 99 | 98 | 0,018414 | 0,99 (1/101) | 734 | 41,33 | 86,29 |
| 2 | r_(k), n=149 | 149 | 147 | 0,018414 | 0,00 (0/51) | 734 | 41,33 | 86,29 |
| 2 | tolerancia 0,98/0,95, n=149 | 149 | 149 | 0,018425 | 0,00 (0/51) | 734 | 41,33 | 84,68 |
| 3 | procedimiento del borrador (cuantil interpolado, parada adaptativa) | 49 | — | 0,022167 | 0,00 | 898 | 14,00 | 100,00 |
| 3 | r_(k), n=49 | 49 | 49 | 0,022267 | 0,00 (0/151) | 899 | 13,83 | 100,00 |
| 3 | r_(k), n=99 | 99 | 98 | 0,022163 | 0,00 (0/101) | 898 | 14,00 | 100,00 |
| 3 | r_(k), n=149 | 149 | 147 | 0,022155 | 0,00 (0/51) | 898 | 14,00 | 100,00 |
| 3 | tolerancia 0,98/0,95, n=149 | 149 | 149 | 0,022267 | 0,00 (0/51) | 899 | 13,83 | 100,00 |
| 4 | procedimiento del borrador (cuantil interpolado, parada adaptativa) | 49 | — | 0,010083 | 3,97 | 664 | 53,00 | 97,80 |
| 4 | r_(k), n=49 | 49 | 49 | 0,010087 | 3,97 (6/151) | 664 | 53,00 | 97,48 |
| 4 | r_(k), n=99 | 99 | 98 | 0,010083 | 5,94 (6/101) | 664 | 53,00 | 97,80 |
| 4 | r_(k), n=149 | 149 | 147 | 0,010090 | 5,88 (3/51) | 664 | 53,00 | 97,17 |
| 4 | tolerancia 0,98/0,95, n=149 | 149 | 149 | 0,010331 | 0,00 (0/51) | 707 | 45,83 | 98,55 |

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
| 1 | -0,334 | 3,1e-05 |
| 2 | 0,206 | 0,012 |
| 3 | -0,569 | 3,9e-14 |
| 4 | -0,092 | 0,27 |

Registros activos por bearing (sin los finales con el banco parado): 1: 982, 2: 982, 3: 982, 4: 982.
Intervalo entre registros: 10 min.
