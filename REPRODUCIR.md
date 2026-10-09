# Reproducibility package

Everything in the manuscript — every number in the prose, all thirty-four
tables and all fourteen figures — is produced by the code in `repro/`
from public data. Nothing is transcribed by hand from a notebook, and no
result in the paper comes from a source that is not listed here.

This file is the whole protocol. Read section 1 to see what you need, run
section 3 in the order given, and use section 6 to check that what you got is
what we got.

---

## 1. What you need

### 1.1 Software

Measured on the machine that produced the numbers in the manuscript:

| | version |
|---|---|
| Python | 3.10.12 |
| numpy | 2.2.6 |
| scipy | 1.15.3 |
| scikit-learn | 1.7.2 |
| pandas | 2.3.3 |
| matplotlib | 3.10.9 |
| wfdb | 4.3.1 |

`wfdb` is needed only by the ECG stage, which reads the MIT-BIH records
directly. `pyarrow` (or `fastparquet`) is needed by pandas to read the
point-machine parquet files. No GPU, no training, no framework: nothing in
this paper is fitted.

```bash
pip install numpy scipy scikit-learn pandas matplotlib wfdb pyarrow
```

### 1.2 Data

Six public sources. None is redistributed with this package.

| domain | source | goes in |
|---|---|---|
| Point machines | Chinese Railway Point Machine dataset (Kaggle) | `datasets/pm/kaggle_nominal/*.parquet` |
| ECG | MIT-BIH Arrhythmia Database (PhysioNet) | `datasets/ecg/mitdb/` |
| Batteries | NASA Ames Prognostics battery dataset | `datasets/batteries/` |
| Tides | NOAA CO-OPS water level, 9 stations | `data/noaa_tides/<station>/*.csv` |
| Solar | NSRDB, 80 stations | `data/nsrdb_solar/<station>/*.csv` |
| Spoken digits | Free Spoken Digit Dataset (Zenodo 10.5281/zenodo.1342401) | `gemo_of_int_mnist/audio_data/recordings/` |

MNIST and the UCI 8×8 digits are downloaded by scikit-learn on first use and
cached inside the run folder; you do not place them yourself.

**Layout.** `--data-root` points at `datasets/`. The tidal, solar and spoken
archives are located by walking up from there (`reproduce.py:_find_dir` tries
`.`, `..`, `../..`, `../../..`), so the three folders sit beside each other:

```
<anywhere>/
├── datasets/          <- --data-root points here
│   ├── pm/
│   ├── ecg/
│   └── batteries/
├── data/
│   ├── noaa_tides/
│   └── nsrdb_solar/
└── gemo_of_int_mnist/audio_data/recordings/
```

If the spoken archive is absent, the convergence stage falls back to
`<run>/cache/spoken.npz` and **prints which source it used**. A run made from
the cache is reproducible; a run made from neither is not, and the stage says
so rather than quietly measuring nine curves where the paper reports ten.

### 1.3 The four preprocessed arrays

Three domains are read as arrays rather than from the raw archive. They are
built by the notebooks at the repository root, once, and are inputs to every
run afterwards:

| array | built by |
|---|---|
| `datasets/pm/mc_pm_dataset.npy` | `PM_dataset_generator.ipynb` |
| `datasets/ecg/mc_ecg_mcsharry_dataset.npy` | `ECG_dataset_mcsharry_generator.ipynb` |
| `datasets/ecg/mc_ecg_gaussian_dataset.npy` | `ECG_dataset_phenom_generator.ipynb` |
| `datasets/batteries/field_discharges_dataset.npy` | `BATTERIES_dataset_preproc.ipynb` |

The first three are the **synthetic generators**. They are controls on the
procedure, not evidence about the phenomena, and the manuscript says so where
they appear. The Monte Carlo draws are seeded inside the notebooks; if you
rebuild them you get the same arrays, and if you skip this step and use the
arrays as shipped you get the manuscript's numbers exactly.

---

## 2. What is in `repro/`

```
repro/
├── reproduce.py                  the driver: thirteen stages, one command
├── ecg_probe.py                  the window rule (Section 7.3.6)
├── pm_pooling.py                 may the four PM populations be pooled (Appendix D)
├── pm_sets.py                    the same question, the other measurement
├── check_numbers.py              audits the prose against the run (section 6.2)
├── emit_tables.py                generates the tables the manuscript used to carry by hand
│
│   the appendix controls (Step 2b); each writes its criterion or prediction
│   to disk before it measures
├── control_sup.py                metric control: cosine against the supremum norm
├── control_tides.py              the same control on all 24 tidal months on disk
├── check_one_over_n.py           the mean-radius schedule is 1/n (the estimator's)
├── check_boundary_quantile.py    what sets the sample maximum (offending records)
├── check_boundary_noise.py       is what keeps climbing the border or the noise
├── check_boundary_nuisance.py    ... or an undeclared nuisance (time shift)
├── check_nn_cover.py             distance of a new realisation to the nearest exemplar
├── check_border_auc.py           the class against what is not the class (AUC)
├── check_border_auc_deskew.py    MNIST border with its declared quotient (post hoc)
├── emit_maximum_appendix.py      tables + figure of the sample-maximum appendix
├── emit_nn_cover.py              table + figure of the nearest-exemplar measurement
├── emit_border_auc.py            table of the border measurement
├── emit_border_deskew.py         the two tables of the post-hoc MNIST arm
└── src/
    ├── run_experiment.py         metrics: nets, covering numbers, contrasts
    ├── surrogates.py             shuffle / ft / iaaft  (Theiler; Schreiber-Schmitz)
    ├── dimension.py              covering-number slope + calibration
    ├── audio_mnist.py            FSDD loader and the duration quotient
    ├── figstyle.py               the one figure template: page-size, palette, type
    ├── figure_one.py             Figure 1
    ├── figure_bulk_boundary.py   Figure 6
    ├── figure_digits_per_class.py Figure 16 + table_digits_per_class.tex
    ├── figure_generators.py      Figures 4, 5, 7   (the three generator panels)
    ├── figure_multisite.py       Figures 8-11      (NSRDB and NOAA appendices)
    └── figure_convergence.py, figure_exemplars.py, figure_saturation.py,
        figure_saturation_grid.py
```

The four modules on the last line are called by `reproduce.py --figures` and
write into the run folder. **They are diagnostics; none of their output appears
in the manuscript.** The paper's ten figures are the five scripts named above
them, which are run separately (section 4).

---

## 3. The sequence

### Step 1 — the measurement

From `repro/`:

```bash
python reproduce.py --data-root /path/to/datasets --out run_a
```

One command, thirteen stages, in this order. Later stages read the cache the
earlier ones write, so the order is not negotiable:

| # | stage | produces |
|---|---|---|
| 1 | physical domains + surrogate hierarchy | `surrogate_test.json`, `table_surrogates`, `table_draws` |
| 2 | the contrast under both quotients | `physical_contrast.json`, `table_quotient` |
| 3 | ECG mitdb: one heart per curve | detection vs *n* |
| 4 | PM: the four nominal populations | `table_pm_populations`, `table_pm_crosstab` |
| 5 | MNIST: contrast and canonisation controls | `mnist_contrast.json`, `table_controls` |
| 6 | the gate (digits) | `gate.json`, `table_gate` |
| 7 | intrinsic dimension + calibration | `dimension.json`, `table_dimension` |
| 8 | learning curves | `learning.json`, `table_learning`, `table_learning_target` |
| 9 | demanded operating point → memory | `operating.json`, `table_operating`, `table_decision` |
| 10 | NOAA tides (pre-registered test) | `tides.json`, `table_tides`, `table_fiducial` |
| 11 | NSRDB solar (cloud-cover split) | `solar.json`, `table_solar` |
| 12 | radius convergence | `convergence.json`, `table_saturation_summary` |
| 13 | figures and macros | `numbers.tex`, `MANIFEST.json` — see 7.3 |

Stages 10 and 11 must precede 12: convergence measures ten curves and two of
them are tidal and solar, which it reads from the cache those stages leave. If
you re-run stage 12 alone, `--restage convergence` rebuilds them first rather
than silently reporting eight.

`--skip-mnist` skips stage 5 only. To repeat one stage into an existing run:

```bash
python reproduce.py --restage convergence --data-root /path/to/datasets --out run_a
```

Valid names: `physical`, `pm_populations`, `pm_anomaly`, `ecg_anomaly`,
`mnist`, `gate`, `separability`, `selector`, `dimension`, `learning`,
`operating`, `tides`, `solar`, `convergence`, `figures`, `saturation_table`.

`pm_anomaly` does not run by default. The paper's detector is the ECG one; the
point-machine anomaly material belongs to the phase-diagram work and is not a
result here.

### Step 2 — the three diagnostics

These answer questions about the assets, not claims of the paper, so they are
separate scripts and their output goes to the appendices.

```bash
python ecg_probe.py  --data-dir /path/to/datasets/ecg/mitdb
python pm_pooling.py --data-root /path/to/datasets --out pm_pooling.json
python pm_sets.py    --data-root /path/to/datasets            # writes pm_sets.json
python pm_sets.py    --controls-out pm_controls.json          # the two synthetic controls
```

`ecg_probe.py` is the window rule of Section 7.3.6. `pm_pooling.py` is
Appendix D: whether the four nominal point-machine populations may be pooled,
which is a precondition of the domain and not bookkeeping. `pm_sets.py` asks
the same question with the other measurement; the two can disagree and the
appendix says what it means when they do.

### Step 2b — the appendix controls

Four appendices and two remarks rest on scripts that run **after** Step 1 and
read what it left: the cache in `<run>/cache/` (`mnist.npz`, `spoken.npz`,
`conv_extra.npz`) and, for some, the run's JSON. They import `reproduce.py`
and change one thing each; nothing in `reproduce.py` is modified. Every script
writes its criterion or prediction (`CRITERIO.json` / `PREDICCION.json`)
before it measures, so the file on disk shows what was fixed in advance.

From `repro/`, with `R` the completed run (`../../v8/run_o` for the manuscript),
`D` the datasets folder of 1.2 and `W` any scratch folder:

**Metric control** — Appendix *Metric control: cosine against the supremum
norm*; `table_metric_control.tex`, `table_metric_control_tides.tex`,
`fig_metric_control.png`, and the L∞ column of `table_crossings`.

```bash
python control_sup.py --data-root $D --cache-from $R --reference $R/convergence.json \
    --only "PM real" "PM simulated" "ECG real" "ECG simulated" "Battery" --out $W/sup_a
python control_sup.py --data-root $D --cache-from $R --reference $R/convergence.json \
    --only "UCI digits" "Spoken digits" "NOAA tides" "NSRDB solar" --out $W/sup_b
python control_sup.py --data-root $D --cache-from $R --reference $R/convergence.json \
    --only "MNIST" --out $W/sup_mnist
python control_sup.py --combine $W/sup_a/control_sup.json $W/sup_b/control_sup.json \
    $W/sup_mnist/control_sup.json --out $W/sup_all
cp $W/sup_all/table_control_sup.tex ../tex/table_metric_control.tex
cp $W/sup_all/fig_control_sup.png   ../tex/fig_metric_control.png

python control_tides.py --data-root $D --reference-extra $R/cache/conv_extra.npz --out $W/tides
cp $W/tides/table_control_sup.tex ../tex/table_metric_control_tides.tex
```

The three batches are not arbitrary: `control_sup.py` writes table rows in the
order the parts are combined, so the order above is the order in the
manuscript. The values do not depend on the batching. `--reference` checks
that the cosine arm reproduces `convergence.json` and prints `IDENTICO` when it
does.

**What the sample maximum measures** — Remark *Why the unsettled maximum…*
and its appendix; `table_one_over_n.tex`, `table_max_concentration.tex`,
`fig_max_offenders.png`, `fig_one_over_n.png`.

```bash
python check_one_over_n.py --data-root $D --cache-from $R \
    --convergence $R/convergence.json --out $W/one_over_n
python check_boundary_quantile.py --data-root $D --cache-from $R --out $W/quantile
python emit_maximum_appendix.py --one-over-n $W/one_over_n --quantile $W/quantile --out ../tex
cp $W/one_over_n/fig_one_over_n.png ../tex/

# the two alternative explanations the appendix tests; prose only, no table
python check_boundary_noise.py    --data-root $D --cache-from $R --skip-mnist --out $W/noise
python check_boundary_nuisance.py --data-root $D --cache-from $R --only "PM real" "ECG real" --out $W/nuisance
```

`check_boundary_quantile.py` reads the five field and simulated time-series
pools by construction (no `--only` needed).

**The class, against what is not the class** — Remark *Why this is not an
effect of the density* and its appendix; `table_nn_cover.tex`,
`fig_nn_cover.png`, `table_border_auc.tex`, `table_border_deskew.tex`,
`table_border_horizon.tex`.

```bash
python check_nn_cover.py --data-root $D --cache-from $R --dimension $R/dimension.json --out $W/nn
python emit_nn_cover.py --parts $W/nn/nn_cover.json \
    --one-over-n $W/one_over_n/one_over_n.json --out ../tex --json-out $W/nn_all

python check_border_auc.py --data-root $D --cache-from $R --out $W/border
python emit_border_auc.py --parts $W/border/border_auc.json --out ../tex --json-out $W/border_all

# post hoc, and declared as such in the script, its CRITERIO.json and the paper
python check_border_auc_deskew.py --cache-from $R --out $W/border_deskew
python emit_border_deskew.py --json $W/border_deskew/border_auc_deskew.json --out ../tex
```

`check_nn_cover.py` and `check_border_auc.py` accept `--only` and may be run in
batches, as they were for the manuscript; their emitters take several
`--parts` and order the rows themselves, so batching changes nothing.
`check_border_auc_deskew.py` was run after the $\ell_2$ MNIST arm had failed
the border criterion. It keeps the criterion and the draws and changes only
the quotient, and it recomputes the $\ell_2$ arm in the same run: if that arm
does not reproduce `table_border_auc` (AUC 0.768 / 0.881 / 0.935 / 0.980,
settling at 800), the deskew arm is not to be read.

**Cost.** The physical and cached domains take seconds to a couple of minutes
each; the MNIST arms dominate, at tens of minutes per script on one or two
cores. Nothing needs a GPU.

### Step 3 — the figures

The paper's ten figures are **not** produced by `reproduce.py`. Run them
against the completed run and write straight into `tex/`:

```bash
cd repro
python src/figure_one.py             /path/to/datasets run_a ../tex/fig1_seven_phenomena.png
python src/figure_bulk_boundary.py   run_a ../tex/fig_bulk_boundary.png
python src/figure_digits_per_class.py run_a ../tex        # figure + its table
python src/figure_generators.py      /path/to/datasets ../tex
python src/figure_multisite.py compute /path/to/data multisite.json
python src/figure_multisite.py plot    multisite.json ../tex
```

`figure_multisite.py` is split in two because the compute pass reads about a
gigabyte of CSV across 89 stations; the cache lets you redraw without repeating
it. Its `n_sat` estimator is seeded per station — the notebook version it was
ported from shuffled with the global RNG and was not reproducible run to run.

Every figure is authored at the width it is included at, so the point sizes in
`figstyle.py` are the point sizes on the page. If you change an
`\includegraphics` width in the `.tex`, change the `F.size(frac, …)` call to
match or the type will no longer be the size it says it is.

### Step 3b — the ten derived tables

Ten tables are not written by a stage but assembled by `emit_tables.py` from
what Steps 1–3 left: the run, the two point-machine diagnostics, the multisite
cache, the synthetic controls of `pm_sets.py`, and the combined metric control
of Step 2b (for the L∞ column of `table_crossings`).

```bash
python emit_tables.py --run run_a --pooling pm_pooling.json --multisite multisite.json \
    --sets pm_sets.json --controls pm_controls.json \
    --control $W/sup_all/control_sup.json --out ../tex
```

Without arguments the script reads the author's paths; pass them explicitly
as above. `--check` compares each table against the hand-typed one it
replaced (section 7).

### Step 4 — the manuscript

```bash
cd ../tex
pdflatex the_geometry_of_intelligence
pdflatex the_geometry_of_intelligence
bibtex   the_geometry_of_intelligence
pdflatex the_geometry_of_intelligence
pdflatex the_geometry_of_intelligence
```

Expected: **74 pages, 0 undefined references, 0 undefined citations, 0 bibtex
warnings, 0 overfull boxes above 20 pt.**

---

## 4. Cost

The full run is a few hours on one core, dominated by stage 12 (convergence,
which repeats every estimate over five arrival orders) and by the solar stage,
which reads 80 station-archives. `--restage convergence` alone is about three
minutes on a warm cache. Nothing needs a GPU.

Fixed constants, at the top of `reproduce.py`: `SEED = 0`, `ORDERS = 5`
(arrival orders per net measurement), `REPS = 20` (random subsets per size in
the contrast).

---

## 5. What the run writes

Thirty artefacts: twelve `.json` with the measurements, seventeen `.tex`
tables, and `MANIFEST.json`. The manifest records a hash of every output, of
every input file, and of every source file that ran — so a run can be shown to
have come from a stated version of the code and a stated version of the data.

The `.tex` tables are `\input` by the manuscript. Copy them into `tex/` to
adopt a new run:

```bash
cp run_a/table_*.tex ../tex/
```

---

## 6. Checking a reproduction

### 6.1 Artefact by artefact

```bash
python reproduce.py --compare run_a run_o
```

This compares two manifests and prints, per artefact, `OK` or `DIFF`. It
distinguishes three cases that are easy to confuse:

- **the code differs** — it names which source files, before comparing outputs;
- **the inputs differ** — it says comparing outputs is meaningless until that
  is fixed;
- **an artefact exists in only one run** — reported as `SOLO-A` / `SOLO-B`, a
  stage added or removed, not a determinism failure.

If the outputs match while the code differs, it says the change was inert. If
the outputs match while the *inputs* differ, it warns: that should not happen
and is worth understanding before trusting anything.

`run_o` is the run the submitted manuscript reports.

### 6.2 The prose against the run

Tables and figures reach the paper by `\input` and by copy, so they cannot
disagree with the run. Prose does not: every number in a sentence is typed by
hand, because `numbers.tex` is emitted and never wired in (section 7.3). Until
it is, `check_numbers.py` is the net:

```bash
cd repro
python check_numbers.py --run ../../v8/run_o --tex ../tex
```

It reads, compares and reports; it edits nothing, and exits 1 if anything
fails. Two checks:

**Crossings.** Every sentence of the form *"enters N per cent … at $n=K$"* is
parsed and checked against `convergence.json`, which is the authority for that
quantity. This check has no false positives: the claim and the source are the
same number.

**By domain.** A sentence that names a domain and cites a number close to, but
not equal to, that domain's own row in `table_saturation_summary` or
`table_surrogates`. This is a heuristic and it does produce false positives —
a rounded ratio, or a number from a different quantity that happens to be
close. It reports candidates to look at, not verdicts. `--wide` adds a broader
sweep against every table at once, which is noisier still and is off by
default.

What it does **not** cover: numbers in the prose of the Step 2b appendices,
which come from the JSON those scripts write and are checked by reading, and
any prose figure that names no domain.

Status on 2026-09-24. Check 1 passes: every crossing claim matches
`convergence.json`. Check 2 raised twelve candidates:

* five already verified by hand: the battery residual of $2.5\%$ at $n=50$
  (the near value is the $51\times$ compression factor), and the four for
  $9.6$ and $19.8$ exemplars, which are the `|S| real` rows of `table_gate`;
* six from the appendices added on 2026-09-23, each a different quantity close
  to a table row: the border AUC $\ge 0.996$ (three times; its source is
  `table_border_auc`, not `table_surrogates`), the tidal border settling at
  $n=20$, the $24$ months on disk, and "from $n=20$ on" in the $1/n$ appendix;
* **one real discrepancy, corrected on 2026-09-24**: the bulk--boundary
  paragraph said the maximum was "$3.5$ times the median at $n=320$" for the
  point machine and "$12.5$ times" for the measured ECG. `src/figure_bulk_boundary.py`,
  which draws Figure 6 from the same run, prints $3.16$ and $12.70$ ($38.79$ for
  the battery, printed correctly as $39$). The prose now says $3.2$ and $12.7$,
  and check 2 raises eleven candidates, all explained above.

### 6.3 Verification of 2026-09-24

What was re-run, and what it was compared with. Paths are the author's.

**Every table and figure in the manuscript has a generator, and was checked
against it.**

* The fifteen tables `reproduce.py` writes are byte-identical to `v8/run_o`.
* `emit_tables.py` regenerates its ten tables byte-identical to `tex/`, also
  with every input passed explicitly as in Step 3b and with `pm_controls.json`
  regenerated by `pm_sets.py --controls-out` (itself byte-identical).
* `src/figure_digits_per_class.py` and `src/figure_bulk_boundary.py`
  regenerate their table and figures byte-identical from `run_o`.
* The Step 2b emitters regenerate every table and figure they own
  byte-identical from the JSON behind the manuscript: `emit_nn_cover.py`,
  `emit_border_auc.py`, `emit_maximum_appendix.py`, `emit_border_deskew.py`,
  and `control_sup.py --combine` for the metric control.

**The Step 2b measurements were re-run from the data with the current code,
and match the JSON behind the manuscript exactly:**

* `control_sup.py` on all five physical domains and on UCI;
* `control_tides.py` on all nine stations (its table byte-identical);
* `check_one_over_n.py`, `check_boundary_quantile.py`,
  `check_boundary_noise.py`, `check_nn_cover.py` and `check_border_auc.py` on
  the battery domain, and `check_boundary_nuisance.py` on the point machine;
* the $\ell_2$ MNIST border arm, recomputed inside
  `check_border_auc_deskew.py` on a different machine; one class of the deskew
  arm re-run from scratch, bit-identical.

**One provenance note.** The JSON behind `table_metric_control` records the
hash of `control_sup.py` it was produced with (`cb4d7365…`); the file in
`repro/` today hashes to `686df09c…`, because it was edited afterwards when
`control_tides.py` was added. The current file reproduces those numbers
exactly on every domain re-run, so the edit is inert for this output.

**The manuscript compiles** to 74 pages with 0 undefined references, 0
undefined citations, 0 bibtex warnings and 0 overfull boxes.

**Not re-run from data this time:** the MNIST and spoken-digit arms of the
Step 2b scripts other than the border (tens of minutes each), and the Step 3
figures that read the raw archives.

---

## 7. Four honest notes

**The observable is a choice, and it is declared.** Every measurement is cosine
distance on a fixed-length resampled vector. The theory in Section 3 is stated
in `C⁰([0,T])` with the supremum norm. On the discretised vectors the two
induce the same topology but not the same constants or rates, and nothing here
proves that a rate measured in one transfers to the other. The metric control
of Step 2b measures the join on the data instead: the same convergence
measurement in the supremum norm, on the same vectors, quotient and draws,
settles no later than cosine in any domain. Reproducing these numbers
reproduces a measurement under a declared metric, which is what the paper
claims and all it claims.

**No table is written by hand any more.** Ten used to be; `emit_tables.py`
generates all ten from artefacts a run already produces, and the manuscript
takes thirty-four tables by `\input`. `python emit_tables.py --check` compares
each emitter against the table it replaced, at any time.

Six reproduce the hand-typed table byte for byte. Four differ, and each
difference is a defect the generation exposed rather than introduced:

* **the tidal $n_{\mathrm{sat}}$ summary** differs only in formatting: it had
  been typed with two decimals on whole day counts, and the emitter prints the
  whole numbers. No value moves.
* **`table_crossings`** differs from its reference because the reference
  predates the L∞ column added with the metric control (Step 2b). The cosine
  columns are unchanged.
* **the growth of $|S|$** — the thirty tabulated values reproduce exactly, the
  five fitted exponents did not. A log-log fit over the whole curve, over
  $n \ge 25$, and over the six tabulated columns give 0.072, 0.031 and 0.050
  for the simulated point machine against the 0.02 that was published, and no
  fit reproduces all five rows: the method was not in the code. The column is
  now ordinary least squares on $\log|S|$ against $\log n$ over the whole
  curve, the manuscript states that, and the five exponents changed to 0.07,
  0.10, 0.24, 0.33 and 0.49. Their span changed with them, from a factor of
  twenty-seven to a factor of seven.
* **the point-machine pair table** moved in the third digit on six values
  (1.27 to 1.28 twice, 0.740 to 0.741, 0.665 to 0.666, 0.769 to 0.770, 0.578 to
  0.577, and an asymmetry from 0.28 to 0.29). The published figures cannot be
  derived from `pm_sets.json` by any rounding rule — two of them were truncated
  and one, 0.578 against a raw 0.5773, matches neither truncation nor rounding.
  They came from a run of `pm_sets.py` that no longer exists on disk. The table
  now comes from the JSON that does.

Recovering these needed two things that were not written down anywhere: the
tolerances of the body and of the appendix differ because one measures over the
whole set and the other over a 600-point subsample, and the "of the way" column
is normalised against the two synthetic controls, not against 2. `pm_sets.py`
computed those controls in `selftest()` and printed them; `--controls-out` now
writes them to a JSON, which is what made the last two tables generable.

**`numbers.tex` is emitted but not wired in.** Stage 13 writes 164 LaTeX
macros holding every number that appears in the prose, and its own docstring
says the point is that "the paper cannot say something the run did not
produce". That mechanism is not connected: the manuscript does not `\input`
the file, so every number in the prose is typed by hand, and the copy in
`tex/numbers.tex` has drifted from the tables it was meant to guarantee
(`\numSPmReal` is 5.2 against 4.8 in `table_surrogates`; `\numCompPmReal` is
115 against 123). `run_o`, the run the submitted manuscript reports, does not
contain `numbers.tex` at all — it was assembled stage by stage with
`--restage` rather than in one pass. None of this affects the tables or the
figures, which are `\input` and copied from the run directly and which we do
check. It does mean that a prose number and its table agreeing has been
verified by reading, not by construction. Wiring the macros in is the obvious
next improvement to this package and we name it rather than leave a reader to
find it.

**Non-convergence is a result, not a failure.** If you run this on a domain
where the estimate does not settle, the framework is working: H1, H2 and H3 are
claims about the world, stated per domain in Section 6.5 before anything is
measured, and a domain that does not settle is a domain where one of them does
not hold. Report it as such.
