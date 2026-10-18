# Banco v3: qué mide el control de ruido (tabla para discutir)

*Generado por `reproducibility_package/bench_v3_discussion.py` desde `results/bench_v3/window_scores.npz`. Hecho después de ver los resultados; **no es un veredicto** y no cambia los de [`tablas_banco_v3.md`](tablas_banco_v3.md). No editar a mano.*

Correlación de Spearman entre la puntuación de cada modelo y las referencias clásicas en las mismas ventanas de 30 vueltas, juntando todos los registros del destino. Rango sobre semillas.

| destino | modelo | ρ con curtosis | ρ con envolvente |
|---|---|---|---|
| Ottawa (ventanas) | noise_s | 0,83 | 0,68 |
| Ottawa (ventanas) | sim_s | 0,31–0,33 | 0,79 |
| IMS (registros) | noise_s | 0,71 | 0,48–0,49 |
| IMS (registros) | sim_s | 0,39–0,42 | 0,42–0,44 |
| XJTU (registros, H y V) | noise_s | 0,68–0,69 | 0,58 |
| XJTU (registros, H y V) | sim_s | 0,41–0,44 | 0,41–0,44 |
