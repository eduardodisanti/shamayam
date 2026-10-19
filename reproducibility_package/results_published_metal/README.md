# Published results before D15 (kept as a record)

These are the files of `results/` as they stood before the reference was moved
to the CPU run on 19-oct-2026 (decision D15 in `mssp_paper/notas/02_plan_escritura.md`).

- Layer A2 and the IMS field operator were trained on Apple Metal (GPU),
  TensorFlow 2.16-2.19, where `enable_op_determinism` gives no guarantee;
  some Layer B results (bench v1/v2) came from a Linux container.
- The current `results/` come from one environment: macOS 27.0.1, Python
  3.12.15, numpy 2.5.4, TensorFlow 2.21.0, CPU, deterministic within that build.
  Layer A1 is byte-identical between the two; verdicts are identical; numbers
  that depend on one trained operator differ by about what a change of seed
  changes them (see `mssp_paper/notas/11_regeneracion_mac.md`).
- `cwru_projection/quotient_ablation_5seeds.json` is a copy of the current file
  (it was produced in the CPU environment and is not a published result).

Nothing reads from this folder.
