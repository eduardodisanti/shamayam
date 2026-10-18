#!/bin/bash
# Referencia en CPU (D15). Ejecutar en el Mac mini con SAMSUNG-1 montado:
#   bash ~/git/shamayam/reproducibility_package/launchers/ref_cpu.command
#
# 1. Clona el HEAD de ~/git/shamayam en SAMSUNG-1/shamayam_runs/ref_cpu.
# 2. Comprueba que TensorFlow no ve ninguna GPU (Metal) y aborta si la ve.
# 3. Verifica el determinismo en CPU: dos entrenamientos con la misma semilla
#    deben dar residuos idénticos; si no, aborta sin entrenar A2.
# 4. Toma de la regeneración en CPU (results_regen/macos27_tf221) los
#    artefactos de la capa B que no dependen de A2: stability.json y la caché
#    de residuos de IMS.
# 5. Ejecuta run_all.py con un presupuesto de 5000 épocas para A2. El
#    presupuesto es un techo: el entrenamiento para por validación.
# 6. Regenera tablas, figuras y macros, pasa los tests de artefactos y deja
#    todo en reproducibility_package/results_regen/cpu_reference/ del repo,
#    sin commit, para revisarlo antes de que pase a ser la referencia.

RUNS=/Volumes/SAMSUNG-1/shamayam_runs
PY="$RUNS/env312/bin/python"
REPO="$HOME/git/shamayam"
D="$RUNS/ref_cpu"
OUT="$REPO/reproducibility_package/results_regen/cpu_reference"
LOG="$RUNS/logs/ref_cpu.log"

[ -d /Volumes/SAMSUNG-1/datasets ] || { echo "SAMSUNG-1 no está montado"; exit 1; }
[ -x "$PY" ] || { echo "No encuentro $PY"; exit 1; }
mkdir -p "$RUNS/logs"
exec > >(tee -a "$LOG") 2>&1
caffeinate -dimsu -w $$ &
export TF_CPP_MIN_LOG_LEVEL=2 PYTHONUNBUFFERED=1
t0=$(date +%s)
echo "== $(date '+%F %T') referencia en CPU"

rm -rf "$D"
git clone -q "$REPO" "$D" || exit 1
COMMIT=$(git -C "$D" rev-parse HEAD)
echo "commit: $COMMIT"
E="$D/mssp_paper/experiments"
REGEN="$D/reproducibility_package/results_regen/macos27_tf221"
cd "$E" || exit 1

"$PY" - <<'PYEOF' || { echo "!! TensorFlow ve una GPU: abortado (la referencia debe ser CPU)"; exit 1; }
import platform, sys
import numpy, tensorflow as tf
gpus = tf.config.list_physical_devices("GPU")
print(f"python {sys.version.split()[0]} | {platform.platform()} | numpy {numpy.__version__}"
      f" | tensorflow {tf.__version__} | GPU {gpus or 'ninguna'}")
sys.exit(1 if gpus else 0)
PYEOF

echo "== $(date '+%F %T') determinismo en CPU"
"$PY" -m pytest -m slow -q \
  "tests/test_conv_autoencoder.py::test_training_is_reproducible_under_the_seed" \
  || { echo "!! DETERMINISMO FALLA: abortado sin entrenar A2"; exit 1; }

cp "$REGEN/stability.json" "$REGEN/field_residuals_ims.npz" results/ || exit 1

echo "== $(date '+%F %T') run_all (A2, presupuesto 5000)"
"$PY" run_all.py --epochs 5000 || { echo "!! run_all falló"; exit 1; }
"$PY" make_tables.py && "$PY" make_figures.py && "$PY" make_macros.py || exit 1
"$PY" -m pytest -q tests/test_generated_artifacts.py

mkdir -p "$OUT/results" "$OUT/tables" "$OUT/figures"
cp results/*.json results/*.txt results/*.npz "$OUT/results/"
cp ../tables/*.tex "$OUT/tables/"
cp ../figures/*.pdf "$OUT/figures/" 2>/dev/null
echo "$COMMIT" > "$OUT/commit.txt"
echo "== $(date '+%F %T') fin ($(( ($(date +%s) - t0) / 60 )) min) -> $OUT"
grep -i "epochs\|budget\|early" "$OUT/results/layer_a_results.txt" | head -5
