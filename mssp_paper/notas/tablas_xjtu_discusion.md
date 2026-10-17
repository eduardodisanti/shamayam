# XJTU-SY: tablas descriptivas para discutir (posteriores a ver los resultados)

*Generado por `reproducibility_package/xjtu_discussion.py` desde `results/xjtu/`. **No son veredictos** ni cambian los de [`tablas_xjtu.md`](tablas_xjtu.md): se hicieron después de ver los resultados, para entenderlos. No editar a mano.*

## 1. Falsas alarmas en la franja sana declarada, por rodamiento

Porcentaje de registros de la franja [150, ⌊L/2⌋) por encima del radio. El veredicto H1 usa la suma de los cinco rodamientos.

| modelo | 2_1 [150, 245) | 2_3 [150, 266) | 3_1 [150, 1269) | 3_2 [150, 1248) | 3_4 [150, 757) |
|---|---|---|---|---|---|
| OEM, H+V, n = 99 (H1) | 0,0% | 100,0% | 0,1% | 2,1–2,3% | 3,3–7,1% |
| OEM, solo H, n = 99 | 0,0% | 100,0% | 0,0% | 2,1–2,3% | 0,0% |
| OEM, solo V, n = 99 | 0,0% | 11,2–19,0% | 0,1% | 0,2% | 4,0–8,9% |
| RMS, H+V, n = 99 | 0,0% | 100,0% | 2,0% | 2,1% | 1,0% |
| por máquina crudo, H, n = 49 (H2) | 0,0% | 100,0% | 0,0% | 70,5–77,1% | 0,0% |
| por máquina cociente, H, n = 49 (H2) | 0,0% | 100,0% | 0,0% | 63,7–73,3% | 0,0% |

## 2. Registro de salida por modelo (n = 99)

Primer registro con 8 de los 10 últimos por encima del radio. Rango sobre semillas en los modelos entrenados. Última columna: RMS horizontal en la salida del OEM (mediana de semillas) dividido por la mediana del RMS de la puesta en marcha.

| rod. | fallo | vida | OEM H+V | OEM H | OEM V | banco H+V | RMS H+V | curtosis H+V | envolvente H+V | RMS H en la salida |
|---|---|---|---|---|---|---|---|---|---|---|
| 1_1 | pista exterior | 123 | 106–107 | 105 | 105–106 | 107 | 107 | no sale | no sale | 4,40 |
| 1_2 | pista exterior | 161 | 135 | 158 | 134–135 | 135–136 | 134 | no sale | no sale | 3,25 |
| 1_3 | pista exterior | 158 | 106 | 105–106 | 105 | 106 | 106 | 116 | 106 | 1,95 |
| 1_4 | jaula | 122 | 111–121 | no sale | 110–121 | no sale | no sale | no sale | no sale | 5,09 |
| 2_1 | pista interior | 491 | 460 | 459–460 | 460–461 | 460 | 459 | 459 | 460 | 2,58 |
| 2_2 | pista exterior | 161 | 107–108 | 155–157 | 105–106 | 107 | 107 | no sale | no sale | 4,81 |
| 2_3 | jaula | 533 | 146–151 | 134–142 | 280–309 | 158 | 134 | 129 | 172 | 1,28 |
| 2_5 | pista exterior | 339 | 128 | 128 | 148 | 128 | 128 | no sale | 128 | 1,33 |
| 3_1 | pista exterior | 2538 | 2349–2354 | 2393 | 2349–2354 | 2349–2350 | 2342 | 862 | 127 | 1,21 |
| 3_2 | pista interior, bola, jaula y pista exterior | 2496 | 1238–1239 | 1238–1239 | 1923 | 1238 | 1238 | no sale | no sale | 1,31 |
| 3_3 | pista interior | 371 | 348 | 348 | 348 | 348 | 348 | 346 | 347 | 5,15 |
| 3_4 | pista interior | 1515 | 1017–1422 | 1424 | 1010–1421 | 1424 | 1006 | 1424 | 1424 | 0,92 |
| 3_5 | pista exterior | 114 | 106 | 112–113 | 105 | 106 | 106 | no sale | no sale | 1,42 |

## 3. RMS a lo largo de la vida, relativo a la puesta en marcha

RMS del registro dividido por la mediana de los 99 primeros; mediana móvil de ±5 registros alrededor de cada fracción de vida.

| rod. | canal | 0,10 | 0,20 | 0,30 | 0,40 | 0,50 | 0,60 | 0,70 | 0,80 | 0,90 | 0,95 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1_1 | H | 0,87 | 0,95 | 1,00 | 0,99 | 1,01 | 1,16 | 3,36 | 4,12 | 4,42 | 4,58 |
| 1_1 | V | 0,96 | 0,98 | 1,00 | 1,00 | 1,00 | 1,11 | 2,83 | 3,60 | 3,83 | 3,96 |
| 1_2 | H | 0,67 | 0,69 | 0,96 | 3,25 | 2,89 | 3,28 | 2,89 | 3,65 | 3,66 | 4,58 |
| 1_2 | V | 0,54 | 0,73 | 0,99 | 3,21 | 3,08 | 2,82 | 2,89 | 3,81 | 4,16 | 5,51 |
| 1_3 | H | 0,98 | 1,00 | 0,99 | 1,09 | 1,32 | 1,59 | 2,09 | 2,83 | 3,27 | 7,21 |
| 1_3 | V | 0,98 | 1,00 | 0,99 | 1,13 | 1,40 | 1,67 | 2,46 | 3,20 | 4,89 | 10,82 |
| 1_4 | H | 0,97 | 0,94 | 0,96 | 0,97 | 1,00 | 1,03 | 1,18 | 1,21 | 1,19 | 1,19 |
| 1_4 | V | 0,96 | 0,93 | 0,94 | 0,96 | 1,01 | 1,04 | 1,15 | 1,17 | 1,19 | 1,20 |
| 2_1 | H | 1,00 | 0,95 | 0,95 | 0,94 | 0,92 | 0,91 | 0,92 | 0,90 | 0,89 | 4,75 |
| 2_1 | V | 0,98 | 0,99 | 0,97 | 0,95 | 0,96 | 0,95 | 0,95 | 0,93 | 0,94 | 3,94 |
| 2_2 | H | 0,79 | 0,77 | 0,98 | 1,64 | 2,21 | 4,69 | 4,33 | 3,95 | 4,44 | 6,72 |
| 2_2 | V | 0,77 | 0,77 | 0,96 | 2,20 | 3,36 | 6,49 | 7,13 | 6,36 | 7,24 | 6,93 |
| 2_3 | H | 0,96 | 1,01 | 1,32 | 1,37 | 1,46 | 2,04 | 7,91 | 8,78 | 9,31 | 10,31 |
| 2_3 | V | 0,98 | 1,05 | 1,17 | 1,24 | 1,27 | 1,59 | 3,96 | 8,35 | 6,91 | 7,03 |
| 2_5 | H | 1,05 | 0,98 | 0,95 | 1,36 | 2,08 | 4,72 | 4,07 | 6,98 | 7,74 | 10,01 |
| 2_5 | V | 1,06 | 0,97 | 0,95 | 1,21 | 1,74 | 3,04 | 3,98 | 4,55 | 6,52 | 7,41 |
| 3_1 | H | 1,00 | 1,03 | 1,02 | 1,00 | 1,00 | 1,02 | 1,01 | 1,05 | 1,06 | 1,97 |
| 3_1 | V | 0,98 | 1,02 | 1,02 | 1,00 | 0,99 | 0,99 | 0,99 | 1,04 | 1,03 | 1,55 |
| 3_2 | H | 0,95 | 0,99 | 0,90 | 0,95 | 1,20 | 1,22 | 1,35 | 1,51 | 2,57 | 2,04 |
| 3_2 | V | 0,89 | 0,89 | 0,86 | 0,85 | 0,95 | 0,96 | 1,08 | 1,20 | 1,48 | 1,45 |
| 3_3 | H | 1,03 | 0,99 | 0,96 | 0,93 | 0,89 | 0,88 | 0,87 | 0,84 | 0,80 | 6,93 |
| 3_3 | V | 1,04 | 0,99 | 0,97 | 0,92 | 0,90 | 0,87 | 0,87 | 0,84 | 0,82 | 6,55 |
| 3_4 | H | 0,90 | 0,85 | 0,83 | 0,84 | 0,81 | 0,82 | 0,80 | 0,90 | 0,88 | 2,32 |
| 3_4 | V | 1,00 | 0,99 | 0,98 | 0,96 | 0,96 | 0,96 | 0,90 | 1,05 | 1,05 | 2,25 |
| 3_5 | H | 0,53 | 0,78 | 1,02 | 0,99 | 1,04 | 1,03 | 1,05 | 1,24 | 1,38 | 1,42 |
| 3_5 | V | 0,49 | 0,58 | 1,03 | 1,20 | 0,98 | 0,98 | 1,35 | 1,51 | 2,39 | 2,45 |
