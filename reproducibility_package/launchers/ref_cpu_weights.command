#!/bin/bash
# D17: weights of the reference operators, and a full-scale determinism check.
#   bash ~/git/shamayam/reproducibility_package/launchers/ref_cpu_weights.command
#
# Retrains, in the CPU reference environment, the two operators the paper's
# numbers come from, saves their weights, and checks that everything they
# produce is IDENTICAL to what is committed:
#   A2 operator      run_all.py --epochs 5000   -> data.json and the results
#                    file must match the committed ones (timestamps aside)
#   IMS operator     build_field_cache.py       -> the residual cache must
#                    match the committed one bit for bit (SHA-256 of scores)
# Weights stay on SAMSUNG-1 (shamayam_runs/weights_reference/) for a release;
# the repository receives only metadata, digests and the comparison report.

RUNS=/Volumes/SAMSUNG-1/shamayam_runs
PY="$RUNS/env312/bin/python"
REPO="$HOME/git/shamayam"
D="$RUNS/ref_cpu_weights"
W="$RUNS/weights_reference"
OUT="$REPO/reproducibility_package/results_regen/determinism_fullscale"
LOG="$RUNS/logs/ref_cpu_weights.log"

[ -d /Volumes/SAMSUNG-1/datasets ] || { echo "SAMSUNG-1 no está montado"; exit 1; }
[ -x "$PY" ] || { echo "No encuentro $PY"; exit 1; }
mkdir -p "$RUNS/logs"
exec > >(tee -a "$LOG") 2>&1
caffeinate -dimsu -w $$ &
export TF_CPP_MIN_LOG_LEVEL=2 PYTHONUNBUFFERED=1
t0=$(date +%s)
echo "== $(date '+%F %T') pesos de referencia + determinismo a escala completa"

rm -rf "$D" "$W"
git clone -q "$REPO" "$D" || exit 1
COMMIT=$(git -C "$D" rev-parse HEAD)
echo "commit: $COMMIT"
E="$D/mssp_paper/experiments"
P="$D/reproducibility_package"
mkdir -p "$W" "$D/committed"
cp "$E/results/data.json" "$E/results/layer_a_results.txt" "$P/results/field_residuals_ims.npz" "$D/committed/" || exit 1

"$PY" - <<'PYEOF' || { echo "!! TensorFlow ve una GPU: abortado"; exit 1; }
import platform, sys
import numpy, tensorflow as tf
gpus = tf.config.list_physical_devices("GPU")
print(f"python {sys.version.split()[0]} | {platform.platform()} | numpy {numpy.__version__}"
      f" | tensorflow {tf.__version__} | GPU {gpus or 'ninguna'}")
sys.exit(1 if gpus else 0)
PYEOF

echo "== $(date '+%F %T') tests: determinismo y guardar/cargar"
( cd "$E" && "$PY" -m pytest -m slow -q \
    "tests/test_conv_autoencoder.py::test_training_is_reproducible_under_the_seed" \
    "tests/test_conv_autoencoder.py::test_saved_operator_reloads_to_identical_residuals" ) \
  || { echo "!! los tests fallan: abortado"; exit 1; }

echo "== $(date '+%F %T') A2 (presupuesto 5000)"
( cd "$E" && "$PY" run_all.py --epochs 5000 --save-operator "$W/a2_operator" ) || { echo "!! run_all falló"; exit 1; }

echo "== $(date '+%F %T') operador de IMS y caché de residuos"
( cd "$P" && "$PY" build_field_cache.py --save-operator "$W/ims_operator" ) || { echo "!! build_field_cache falló"; exit 1; }

echo "== $(date '+%F %T') comparación"
mkdir -p "$OUT"
"$PY" - "$D" "$E" "$P" "$W" "$OUT" "$COMMIT" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path
D, E, P, W, OUT, COMMIT = [Path(a) for a in sys.argv[1:6]] + [sys.argv[6]]
sys.path.insert(0, str(P))
from mssp_repro.field.residuals import load_cache
L = [f"commit {COMMIT}"]
ok = True

a, b = json.loads((D / "committed/data.json").read_text()), json.loads((E / "results/data.json").read_text())
a.pop("_meta", None); b.pop("_meta", None)
same = a == b
ok &= same
L.append(f"data.json (sin _meta): {'IDENTICO' if same else 'DIFIERE'}")
if not same:
    L += [f"  difiere en: {k}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]

def strip(t):
    return [l for l in t.splitlines() if not l.startswith("generated ") and "operator saved to" not in l]
same = strip((D / "committed/layer_a_results.txt").read_text()) == strip((E / "results/layer_a_results.txt").read_text())
ok &= same
L.append(f"layer_a_results.txt (sin fecha): {'IDENTICO' if same else 'DIFIERE'}")

c0, c1 = load_cache(D / "committed/field_residuals_ims.npz"), load_cache(P / "results/field_residuals_ims.npz")
same = c0["meta"]["sha256"] == c1["meta"]["sha256"]
ok &= same
L.append(f"caché de IMS (SHA-256 de los residuos): {'IDENTICA' if same else 'DIFIERE'}"
         f"  {c0['meta']['sha256'][:16]} / {c1['meta']['sha256'][:16]}")
same = c0["meta"].get("tau_mc") == c1["meta"].get("tau_mc")
L.append(f"tau_MC del operador de IMS: {'IDENTICO' if same else 'DIFIERE'}")

sums = []
for f in sorted(W.rglob("*")):
    if f.is_file():
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        sums.append(f"{h}  {f.relative_to(W)}")
(W / "SHA256SUMS").write_text("\n".join(sums) + "\n")
(OUT / "SHA256SUMS").write_text("\n".join(sums) + "\n")
for name in ("a2_operator", "ims_operator"):
    (OUT / f"{name}.json").write_text((W / name / "operator.json").read_text())
L.append("")
L.append("RESULTADO: " + ("todo idéntico: el entrenamiento en CPU es determinista a escala completa" if ok
                          else "HAY DIFERENCIAS: no usar estos pesos como referencia sin revisar"))
(OUT / "report.txt").write_text("\n".join(L) + "\n")
print("\n".join(L))
PYEOF
echo "== $(date '+%F %T') fin ($(( ($(date +%s) - t0) / 60 )) min). Pesos en $W; informe en $OUT"
