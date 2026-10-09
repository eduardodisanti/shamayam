# MSSP submission checklist

Working control sheet for `mssp_draft.tex`. Ordered by dependency, not by
importance: each phase unblocks the next, and the last two phases are the ones
that must not be started early, because they quote numbers the earlier phases
can still move.

State of the manuscript at the time of the audit: 3,598 lines, ~19,200 words,
42 pages, 0 LaTeX errors, 0 undefined references or citations. The theory and
results sections are complete. Everything below is either at the two ends of
the document or a consequence of something still unresolved.

**Updated 11 Aug 2026 (second revision, after the bibliography audit).** The
manuscript is now ~4,050 lines and every section is written, front matter and
Elsevier apparatus included. Phases 1–4 are closed; **Phase 5 is now closed**
except the acknowledgements decision and the cover letter; Phases 6 and 7 hold
what remains. Each `[x]` added in this revision was checked against the source
or the repo rather than against memory — the two audit errors earlier in this
project both came from reasoning about files instead of reading them, and the
bibliography audit found a third of exactly that kind: six entries that looked
fine in the `.bib` and were being destroyed at BibTeX time.

Mark items `[x]` as they close. Keep the "Verified by" column honest — an item
is done when something checks it, not when it has been written.

---

## Phase 1 — Resolve the NASA IMS discrepancies

**CLOSED.** Neither "discrepancy" survived inspection as an open debt. The
persistence rule was never in conflict — the audit misread module-level
constants that the reporting cell overrides. The aggregation difference is
real inside the notebook but does not touch the manuscript, since every IMS
number reported comes from the same path; and the reduction it uses is the
correct one, now argued in the paper rather than inherited.

No number changed. What changed is that two conventions previously carried as
unresolved are now specified and defended, each with a test pinning the
argument. Phase 4 is unblocked.

The notebook was found in the second mounted folder,
`inverse_problem/journal_paper/bearing_autoencoder_NASA_per_asset.ipynb`, with
its cell outputs saved. Reading it changed the picture.

| # | ✓ | Item | Where | Notes |
|---|---|------|-------|-------|
| 1.1 | [x] | **Discrepancy 1 does NOT exist. The published run already used 8 of 10** | notebook cell 24 | Module-level `PERSISTENCE_Q=3, P=5` belong to the per-asset path. The cell producing the reported results overrides them with `PERSISTENCE_WINDOW=10, PERSISTENCE_REQUIRED=8`. Saved output confirms it: `declaration − onset = 9 = window−1` for all four bearings, impossible under a 5-window |
| 1.2 | [x] | **Lead times 14.5–74.0 h stand. No recomputation needed** | | The audit error was mine: module-level constants read as governing a cell that overrides them |
| 1.3 | [x] | Keep `false_declaration_probability` + tests | `mssp_repro/dynamics.py` | Justifies the published rule rather than merely recording it: at the attained FAR near 5%, 3/5 would give 0.37 spurious-declaration risk against 3.1e-07 for 8/10 |
| 1.4 | [x] | Correct the record in the package README | `experiments/README.md` | Corrected in place, not quietly deleted |
| 1.5 | [x] | **False discrepancy removed from the paper** | `subsec:design_nasa`, `subsec:design_reproducibility`, `subsec:results_nasa` | The 8-of-10 rule is now *specified and justified* in the design section instead of described in the abstract; the remaining caveat is the aggregation alone |
| 1.6 | [x] | **Discrepancy 2 restated correctly in the paper** | notebook, `subsec:design_reproducibility` | Two experiments in the same paper use different aggregations: per-asset path uses the 95th percentile *with a docstring justifying it*; the shared path producing Table 8 uses `np.mean` under a comment reading "Must match the aggregation used in the main NASA experiment" |
| 1.7 | [x] | **DECIDED: the mean is correct, and the paper now argues it** | `subsec:design_reproducibility` | A p95 of 17 windows *is* the sample maximum, and at α=0.05 is not even feasible (floor 19, k=18>17). Overlapping to 33 stays inside the degenerate range [19,39]. And the signature is ubiquitous, not sparse: ~14 defect impulses per 60 ms window at 236 Hz BPFO. Contrast 15.5 vs 9.3 |
| 1.8 | [x] | No rerun needed | | All IMS numbers in the paper already come from the mean path: shared, resampled-commissioning and run-to-failure cells all call `shared_nasa_recording_scores`. The manuscript is internally consistent |
| 1.9 | [x] | **DECIDED: full Layer B pipeline.** Deferred to Phase 7, after the manuscript is complete | see Phase 7 | Layer B improves reproducibility, not the claims; no number changes if the port is correct |

---

## Phase 2 — Figures

Three problems found in the audit that need no data at all, plus the NASA
figure, which is now blocked on Phase 7. Items 2.3–2.6 proceed immediately.

| # | ✓ | Item | Where | Notes |
|---|---|------|-------|-------|
| 2.1 | [x] | **NASA degradation figure added** as `fig:nasa` | `make_figures.py::figure_nasa` | Generated from the committed residual cache, so it regenerates without the 523 MB archive. Four panels: shaded commissioning prefix, frozen τ, persistent departure, shaded lead time |
| 2.2 | [x] | Resolved by 1.9: it is generated by the Layer B pipeline like everything else | `experiments/make_figures.py` | |
| 2.3 | [x] | **`distance_proxy_probe.pdf` now included as Fig. `fig:adequacy`** | no `\includegraphics` anywhere | It is the visual evidence for contribution (iii) of the Introduction, which currently exists only as a table |
| 2.4 | [x] | **`estimator_variance.pdf` now included as Fig. `fig:variance`** | no `\includegraphics` anywhere | Supports the degenerate-range argument of Cor. `cor:degenerate_range` |
| 2.5 | [x] | **`fig:saturation` now referenced**, and so is `fig:quotient_manifold_concept` | | The concept figure was a *fourth* orphan the audit missed; the test found it |
| 2.6 | [x] | Three tests added: generated⊆included, included⊆generated, every float referenced | `tests/test_generated_artifacts.py` | Immediately found a fourth orphan I had missed by hand |

---

## Phase 3 — Limitations and Future Work

**DONE.** Both written, and both grew beyond the plan notes because the Layer B
port produced material the notes could not have anticipated: the memorisation
of the CWRU reference arm, the reproducibility failure mode found in the
regulariser reduction, and the scale-versus-geometry separation from the seed
study.

| # | ✓ | Item | Where | Notes |
|---|---|------|-------|-------|
| 3.1 | [x] | **Limitations written** — | `sec:limitations` L3492 | 20 lines of plan notes |
| 3.2 | [x] | Compactness gap stated explicitly: `ass:compact_eta` is **assumed, not verified** for CWRU and NASA — it holds by construction only for the simulator | within 3.1 | Flagged in the source as the item whose absence would be a fair referee criticism |
| 3.3 | [x] | `ass:residual_proxy` stated as empirical, with the probe as its direct test | within 3.1 | |
| 3.4 | [x] | Exchangeability failure stated once under drift / degraded-at-installation assets **once**, not twice | within 3.1 | Same gap as the nominal-initialization limitation |
| 3.5 | [x] | Adaptive stopping and the interpolated estimator both stated of Prop. `prop:coverage` | within 3.1 | `rem:optional_stopping` |
| 3.6 | [x] | **Future Work written** — | `sec:future_work` L3515 | 73 lines of plan notes |
| 3.7 | [x] | Stale number corrected in the planning note; the written prose uses the `\etoeDetect` macros so it cannot recur | | |
| 3.8 | [x] | All 8 call sites land on prose that answers them | | Limitations 82 lines, Future Work 72 |

---

## Phase 4 — Conclusion and abstract

**DONE except the numeric cross-check.** Both are written. The abstract is no
longer a hand-copied summary: it draws its figures from `tables/values.tex`, so
a re-run propagates into it. The Highlights do **not**, and that is now the
open item.

| # | ✓ | Item | Where | Notes |
|---|---|------|-------|-------|
| 4.1 | [x] | **Conclusion written** | `sec:conclusion` L3997 | One paragraph, no new claims |
| 4.2 | [x] | **Abstract written**, placeholder replaced | L138–190 | Uses `\satMaxZ`, `\etoeDetectLo/Hi`, `\etoeFAR`, `\nasaBearings`, `\nasaNLo/Hi`, `\nasaLeadLo/Hi` — a re-run cannot leave it stale |
| 4.3 | [ ] | Confirm every number in both appears identically in the body | | Narrowed by 4.2: what remains unprotected in the abstract is `1.9` percentage points and the `4`–`7\%` seed spread, both hand-written |
| 4.4 | [x] | Lead times **are** quotable as a headline result | | Resolved by 1.1: the published run used the conservative rule, and the number is the shorter of the two candidates |
| 4.5 | [x] | **Highlights fit the MSSP limit** | L130–136 | 5 bullets, longest 79 characters against a cap of 85. Counted, not estimated |
| 4.6 | [ ] | **Highlights numbers are hand-written and unprotected** | L130–136 | `380`-fold, `14--74` h, `49`, `98\%` are literals. `\newcommand` does not expand inside `\begin{highlights}` in `cas-sc`, so these must be checked by eye against the macros after the final run. This is the single most visible place a stale digit could survive |

---

## Phase 5 — Elsevier apparatus and bibliography

**CLOSED except the acknowledgements decision and the cover letter.** The
bibliography audit ran on 11 Aug 2026 and all 35 entries are now verified.

It did not run through Scholar Sidekick. That connector still returns `You are
not subscribed to this API` from a **fresh conversation**, so the hypothesis
recorded below — that a new session would re-read the configuration — is
**wrong**, and the note is kept only so nobody retries it on that basis. The
audit was done instead by resolving each claimed title against Crossref, JMLR,
arXiv, dblp and iso.org directly, which performs the same title-vs-identifier
cross-check that made the tool worth waiting for.

Three findings, in descending order of severity:

1. **Six entries were silently broken in the source.** The `% UNVERIFIED`
   markers had been written *inside* the entry bodies. BibTeX does not treat
   `%` as a comment inside an entry: it reports "You're missing a field name"
   and discards everything after it. `hinton2006`, `wilks1941`, `lei2018`,
   `devroye1980`, `scholkopf2001` and `kohonen1982` were each being emitted
   with author, title and journal missing. This surfaces as *warnings* in the
   `.blg`, never as an error, so the "0 LaTeX errors" test in 6.3 could not
   have caught it. The file now carries a formatting rule saying so.
2. **`nguyen2025subdomain` named the wrong journal** — Journal of Vibration
   and Control, where the paper is actually in the Journal of Computational
   Methods in Sciences and Engineering, 25(5):3947–3960.
3. **Three near-miss traps** were found and are recorded inline in
   `references.bib` so they cannot be reintroduced: a different 1991 Casdagli
   paper with a nearly identical title, a same-titled Bishop paper from
   ICANN'93, and the 2023 SSRN preprint of `wang2026fleet`. Each has a real,
   resolvable DOI, and each is the *first or second* hit on a title search.

| # | ✓ | Item | Where | Notes |
|---|---|------|-------|-------|
| 5.1 | [x] | **Highlights written** | L130–136 | 5 bullets, longest 79 chars. See 4.5–4.6 |
| 5.2 | [x] | **CRediT author statement** | L121–123, `\printcredits` L4034 | |
| 5.3 | [x] | **Declaration of competing interest** | L4037 | Author declares none |
| 5.4 | [x] | **Data availability statement** | L4044 | Package public; CWRU and NASA IMS named as third-party archives, not redistributed |
| 5.5 | [ ] | Acknowledgements | new | Optional. Still absent — decide whether anyone is owed one |
| 5.6 | [x] | **Corresponding author, email, ORCID in the preamble** | L118–128 | ORCID 0000-0003-3784-8382, `\ead{eduardo.disanti@colorado.edu}`, `\cormark`/`\cortext` |
| 5.7 | [x] | **DOIs: 21 of 35 entries now have one** | `references.bib` | 14 need none and each says why in a comment above it: 6 books, the ISO standard, 3 JMLR papers, 2 NeurIPS papers and the 2 unpublished `disanti2026` technical reports. `assran2023` did have one after all: `10.1109/CVPR52729.2023.01499` |
| 5.8 | [x] | **The 6 entries added from memory were all correct** | `references.bib` | `iso20816`, `bishop1994`, `scholkopf1999`, `devito2005`, `kohonen1982`, `assran2023` all confirmed field by field. The two flagged as highest risk were both right: the `assran2023` CVPR pages are 15619–15629, and `bishop1994` is IEE Proc. 141(4), start page 217 |
| 5.9 | [x] | **Domain-adaptation entries merged and cited** | `mssp_draft.tex` L488–496 | `nguyen2025subdomain`, `ning2026digitaltwin`, `wang2026fleet`, `roelofs2024transfer`, `zhao2019`. No `[PENDING]` marker survives in the source |
| 5.10 | [x] | **Full bibliography audit DONE** — 35/35 entries, title checked against the resolved record | `references.bib` | Not via Scholar Sidekick, which is still dead. One wrong journal found, three near-miss DOI traps documented. No retractions, corrections or expressions of concern on the five post-2018 entries, which is where that risk is concentrated |
| 5.11 | [x] | **`grep -c UNVERIFIED references.bib` returns 0** | `references.bib` | And the markers turned out to be worse than unfinished: written inside the entry bodies, they were deleting six entries at BibTeX time. See the three findings above |
| 5.12 | [x] | **`arXiv:2512.05089` confirmed** | `disanti2026blueprints` | The abstract page resolves to exactly the cited title. DOI `10.48550/arXiv.2512.05089` added |
| 5.14 | [ ] | **Confirm the `disanti2026inverse` repository URL resolves** | `references.bib` | The one entry the audit could **not** clear. `scholar.colorado.edu/concern/reports/fn107102t` returned no machine-readable content and the title is not indexed anywhere reachable. Institutional repositories index poorly, so this is not evidence it is wrong — but you own this record and should open the URL yourself |
| 5.13 | [ ] | Cover letter and suggested reviewers | outside the repo | Required by the Elsevier submission system, not by the manuscript. Easy to forget because nothing in the `.tex` prompts for it |

### Scholar Sidekick: the "fresh conversation" fix does not work

Kept as a record so the same fix is not tried a seventh time. The connector
returns `You are not subscribed to this API` on every call, including the first
call of a brand-new conversation on 11 Aug 2026. Whatever the cause, it is not
session state. The RapidAPI account carries an active Basic plan and the same
request from the RapidAPI playground returns `200 OK`, so the connector is
presenting a different key than the one configured.

**This no longer blocks anything.** The audit was completed against Crossref,
JMLR, arXiv, dblp and iso.org directly. That path performs the same essential
check — comparing the *claimed title* against the record the identifier
actually resolves to — and it found the failure mode it was meant to find,
three times over. If the connector is ever fixed it is worth a re-run for the
retraction screen, which was only spot-checked here.

The reason this check is not optional: while collecting the DOI for
`wilks1941`, the search engine offered `10.1214/aoms/1177730044` — a real,
resolvable DOI belonging to a *different* 1949 paper. A referee following it
would have landed on a working page for the wrong work. The audit found three
more of exactly this shape (`casdagli1991`, `bishop1994`, `wang2026fleet`), and
in each case the wrong DOI was the *first or second* search hit. All four are
now recorded inline in `references.bib` as `NOTE:` lines naming the DOI not to
use, so a future editor cannot re-introduce them by searching again.

---

## Phase 6 — Final pass

**6.1 is now known to be necessary, not precautionary.** `results/data.json`
is dated 31 Jul; `field_residuals_ims.npz`, `stability.json`,
`cwru_oracle_probe.json` and every file in `tables/` are dated 11 Aug. The
Layer A results the paper quotes are therefore two weeks older than the Layer B
results beside them, and `make_macros.py` has been emitting `sat*` and `etoe*`
macros from the older file.

| # | ✓ | Item | Where | Notes |
|---|---|------|-------|-------|
| 6.1 | [ ] | **Re-run the chain**: `run_all.py --layer all` → `make_tables.py` → `make_figures.py` → `make_macros.py` | `experiments/` | **Confirmed stale**: `data.json` 31 Jul vs everything else 11 Aug. Watch for the `_carried_over` warning `make_macros.py` prints |
| 6.2 | [ ] | Full test suite, including `-m slow` | `experiments/tests` | 151 fast + 4 slow at last count, plus the field and dependency tests added since |
| 6.3 | [ ] | Compile clean under `cas-sc`: 0 errors, 0 undefined refs/citations | | Currently compiling under the stand-in class |
| 6.4 | [ ] | Check the 60 hand-written numeric literals in Results and Discussion against the current run | `sed -n '2637,3490p'` | Not covered by macros; the one already found stale was L3558. Do this **after** 6.1, or it checks against the old numbers |
| 6.5 | [~] | Check for overfull boxes under the real class, especially the 9-column `tab:saturation` | | `cas-sc` is single-column, so it should fit; verify. **Build of 11 Aug: exactly one overfull hbox in the whole document, 117pt, at `\maketitle` — it is the `keywords` line at L191–194, six terms joined by `\sep`. `tab:saturation` is clean.** Drop one keyword or shorten "Nuisance invariance" |
| 6.9 | [x] | **The intrinsic-dimension estimator is now named** | `mssp_draft.tex`, `mssp_repro/dimension.py` | Chasing the orphan `levina2004` found that the estimator was used but never attributed: `dimension.py` implements Levina–Bickel with the MacKay–Ghahramani inverse-averaging correction, the paper reports it in `tab:dimension` / `fig:dimension` / Results, and invoked "the known negative bias of the estimator" without saying whose. Now cited in four places. The generated caption was fixed **in `make_tables.py`**, not in the `.tex`, and `tables/dimension.tex` was regenerated from it. Verified by regenerating all eight tables into a scratch directory and diffing against the committed ones: **only the dimension caption changed, the other seven are byte-identical**, which also confirms the generator is reproducible against the current `data.json`. Note `scikit-learn` is needed to import `mssp_repro` and was not present in a clean environment |
| 6.10 | [x] | **Takens attribution corrected** | `rem:delay_embedding`, `sec:related` | The statement as written — compact invariant set, box-counting dimension, `m>2d` — is Sauer–Yorke–Casdagli, not Takens, who requires a compact *manifold* and `m>=2d+1`. Both forms are now stated separately, with SYC named as the one that applies, since nothing guarantees the nominal set is a manifold. This also removes a quiet inconsistency: the old wording assumed the manifold structure `rem:manifold_terminology` explicitly declines to claim |
| 6.11 | [x] | **Related Work now has a state-space-reconstruction paragraph** | `sec:related` | It had seven paragraphs and none on delay embedding, so Takens, Sauer and Casdagli lived only inside a Section 4 remark. The new paragraph also gives `levina2004` its home |
| 6.12 | [x] | **All 42 entries cited, both directions checked** | `references.bib` | 42 entries, 42 `\citation` keys, no entry uncited and no citation without an entry. Build: 0 BibTeX warnings, 0 errors, 0 undefined citations, 0 undefined references, 48 pages |
| 6.13 | [x] | **Section 5 proof review: three of four findings fixed, one open** | `sec:quotient_formulation`, `SECTION5_REVIEW.md` | `\Gnuis` is **not** compact — the paper says so itself at L766–774, and the generated-group construction is what makes it so. **(1) FIXED.** `prop:boundary_invariant` claimed `\mathcal{O}_N` is `\Gnuis`-invariant "by construction". It is not, and the contradiction is internal: an invariant set containing a non-zero point contains an unbounded ray, contradicting the boundedness `prop:compactness` proves. The proposition is now stated for a general invariant `S` and `rem:orbit_not_invariant` records that `\mathcal{O}_N` fails the hypothesis, the correct set being the saturation. **(2) FIXED.** `ass:residual_proxy` now reads `r(x) ≈ d(x, \mathcal{O}_N)` with `d` the distance of `\X`, and `rem:distance_lives_in_X` states why: the quotient pseudometric is degenerate under unbounded scalings, so the quotient supplies the statement of the problem and not the geometry, and the residual's invariance is a property of the trained operator. Cross-referenced from Limitations. **(3) FIXED by declaration.** Arzelà–Ascoli is retained deliberately — it survives the passage to function-valued observations and Heine–Borel does not — and `rem:why_arzela_ascoli` says so, notes the equicontinuity hypothesis is vacuous on a finite index set, and records the free strengthening to *compact* under continuity in η. **(4) FIXED.** `def:nuisance_equivalence` (same orbit **and** same θ) and `eq:orbit` (full orbit) defined different objects. The θ-clause is gone: `~` is now pure orbit equivalence, so it is an equivalence relation by the group structure alone, and `\quotient = X/\Gnuis` is consistent with `eq:orbit`. θ-preservation became `ass:action_preserves_state`, and `prop:quotient_diagnosis` cites it instead of re-assuming it. Two things surfaced while fixing it: the old clause presupposed that θ is a function of x — never stated anywhere in the paper, and without it `~` is not even transitive — now `ass:state_identifiable`; and **transitivity is what forces `\Gnuis` to be non-compact**, since the equivalence relation generated by a bounded family has as classes the orbits of the generated group. That last point reframes the closure construction from an apology into a structural fact, and it is now stated as such: one can have a quotient space or a bounded transformation family, not both. **No experimental result is affected** |
| 6.15 | [x] | **Bredon withdrawn** | `REFERENCE_PROPOSAL.md` §5 | It requires a compact group. Palais does not save it either — the scaling action on `\R^{n_w}` is not proper, since the origin has the whole group as stabilizer. No new quotient reference was needed in the end: 6.13(2) was closed by stating that the geometry is measured in `\X`. Burago–Burago–Ivanov remains available if a quotient-metric citation is ever wanted |
| 6.16 | [ ] | **`rem:why_arzela_ascoli` is not cross-referenced** | `mssp_draft.tex` | Harmless — an unreferenced `\label` costs nothing and the remark sits immediately after the proof it explains. Noted only so it is a decision rather than an oversight |
| 6.14 | [ ] | **Word count grew** | | The manuscript is now **50 pages against 46** at the start of this session. Already long for MSSP at ~19,200 words (item 7.2), and this is now the largest open risk on the list. If trimming is needed, the new Related Work paragraphs are the cheapest to cut back — but the Levina–Bickel attribution and the Section 5 corrections are not optional |
| 6.17 | [x] | **`ass:state_identifiable` is a precondition, not a limitation** | `sec:observation_model`, `sec:limitations` | It was briefly recorded in Limitations alongside `ass:action_preserves_state` on the claim that they "fail together". They do not, and the claim was wrong. `ass:state_identifiable` is about **F and the sensing chain** — two health states producing identical windows — and its remedy is instrumentation; `ass:action_preserves_state` is about **`\mathcal{T}` and the modelling** — declaring something nuisance that carries diagnostic content — and its remedy is a better nuisance model. They are independent. The first is a precondition of the whole problem class (a fixed threshold needs it too) and now stays where it is stated, with a concrete failure example; only the second appears in Limitations |
| 6.18 | [x] | **`rem:boundary_invariance_scope` now covers both directions** | `sec:quotient_formulation` | It described only a `\mathcal{T}` that is too narrow, whose symptom is false alarms. The mirror case — `\mathcal{T}` too broad, which is exactly `ass:action_preserves_state` failing — gives **missed detections**, and is the more dangerous of the two because calibration cannot reveal it: coverage is attained exactly as promised, on a nominal set that has been made too large |
| 6.6 | [ ] | Repo hygiene: `rm -f .git/index.lock .git/_probe`; `git rm` the superseded stubs | `calibration_arms.py`, `controls.py`, `results_*.txt`, `_results_section.tex` | Carried over from earlier sessions |
| 6.7 | [ ] | **Confirm every `\newcommand` in `tables/values.tex` still exists after the re-run** | `tables/values.tex` | 37 macros at last count. A section that fails to produce leaves the macro undefined and the build stops — which is the design, but it must be caught here rather than at submission |
| 6.8 | [ ] | **Confirm the committed caches are in the commit, not just on disk** | `results/*.npz`, `results/*.json` | I cannot inspect git state; you own commits. `field_residuals_ims.npz` is 24 kB and is what lets a reader without the 523 MB archive rebuild every field table |

---

## Not blocking, but worth deciding

| # | ✓ | Item | Notes |
|---|---|------|-------|
| 7.1 | [ ] | Is the novelty claim in contribution (ii) defensible as written? | "to our knowledge, have not been stated for it" — the mathematics is Wilks 1941 and elementary; the claim is only that it has not been stated for the diagnostic radius. Softer alternative: "which do not appear to have been made explicit in the diagnostic literature" |
| 7.2 | [ ] | Word count against MSSP expectations | ~19,200 words is long for the journal; if trimming is needed, Section 7 is the longest at 522 lines of prose |

---

## Phase 7 — Full Layer B pipeline

**Decided:** one script regenerates every number in the paper, field results
included. Deferred until the manuscript is complete, because the port improves
reproducibility rather than the claims, and a port that shifts a published
number is easier to diagnose against a stable text.

Scope measured from the notebooks: 6,043 lines total, of which **3,442 are
logic**. The calibration, convergence rule, coverage machinery, Conv1D
operator and persistence rule are already ported and tested, so roughly
**2,000 new lines** remain, plus tests.

**Design.** Layer B has four stages: raw archive → windows → trained operator
→ per-recording residuals → radii, departures, tables, figures. All of the
paper's mathematics lives in the last stage, which is pure numpy and runs in
seconds; the first three are data production. The pipeline therefore caches
the stage-3 output — a few KB of residual series — versioned in the repo.

The cache is **not a shortcut but a verifiable assertion**: a reader with the
archive runs the full chain and the pipeline compares its output against the
committed cache, failing on mismatch. A reader without it regenerates every
table and figure from the cache. The one-minute A1 path is preserved.

| # | ✓ | Item | Notes |
|---|---|------|-------|
| 7.1 | [x] | **Archives reachable and verified readable** | `inverse_problem/` was mounted from the start. IMS `2nd_test`: 984 ASCII recordings, 20480×4 at 20 kHz = 1.02 s each, 17 windows of 1200 — confirms the aggregation analysis. CWRU: 161 `.npz` across four RPM folders. 523 MB + 631 MB |
| 7.1b | [ ] | **Case-sensitivity trap**: the notebook opens `../NASA_Bearing/IMS`, the directory is `NASA_bearing/IMS` | Works on macOS (case-insensitive), fails on Linux. Fix during the port or the pipeline breaks for anyone else |
| 7.2 | [x] | Stage 4 (NASA): `commission_bearing` + `describe_trajectory` in one place, NASA figure | Commissioning logic was spelled out in every caller; now one function, used by the figure, the stability experiment and the tables |
| 7.2b | [x] | **Found: the last two IMS recordings were taken with the rig stopped** | Signal sd near 0.001 against 0.13–0.48 running. They diluted post-departure exceedance, added 20 min to every lead time, and drew a two-decade cliff on the log axis. Now detected and excluded, with the criterion relative to the commissioning minimum so it catches all four bearings |
| 7.2c | [ ] | Stage 4 (CWRU): `tab:cwru_*` from the pipeline | **Still hand-written.** Confirmed: no `tables/cwru*.tex` exists. `cwru_operator.py` and `results/cwru_oracle_probe.json` (11 Aug) already contain the material; what is missing is the emitter and the `\input` |
| 7.3 | [x] | **Stage 3 done**: `mssp_repro/field/residuals.py` + `build_field_cache.py` | Batched scoring (one pass, not one `predict` per recording — 3,936 calls became 4): 984x4 in ~1 min, verified identical to the per-recording path |
| 7.3b | [x] | **Mechanism validated end to end on the real archive** | With a deliberately undertrained 3-epoch operator, departure indices land at 538 / 729 / 893 / 664 against the published 539 / 750 / 896 / 657, and lead times at 74.3 / 42.5 / 15.2 / 53.3 h against 74.0 / 38.8 / 14.5 / 54.3 |
| 7.3c | [x] | **Cache built with the real operator** | `results/field_residuals_ims.npz`, 24 kB, 11 Aug. `make_macros.py::nasa` reads it directly rather than going through `data.json`. Commit state is yours to confirm — see 6.8 |
| 7.4 | [x] | **Stage 2 done and VERIFIED**: shared operator ported, `verify_operator.py` passes 7/7 | Training data bit-identical to a literal transcription; tau_MC 0.011571 against the published 0.012016 (3.7%), val_loss 0.00693 against 0.0073 |
| 7.4b | [x] | **Keras regulariser-reduction defect found and fixed** | `BatchMeanL1` + `assert_operator_learned` in `conv_autoencoder.py`, guarding **both** layers. The notebook as written no longer reproduces on TF≥2.17: the latent collapses and the loss curve still looks healthy |
| 7.5 | [ ] | Stage 1: raw IMS and CWRU loading and windowing | ~1 GB for IMS Experiment 2 alone |
| 7.6 | [x] | **`--check` implemented**: recomputes from the archive and compares | Not by equality — TF is not reproducible across builds. Three diagnostics: rank correlation of each series, median level shift, and whether the derived departure index moves |
| 7.7 | [x] | **Every published field number survives the port** | All four published lead times fall inside the seed-to-seed range; the published tau_MC (0.012016) falls inside [0.010190, 0.012585]. No seed "exploded" and the manuscript reports no outlier |
| 7.7b | [x] | **Seed-stability study added to the package and to the paper** | `stability_experiment.py` + `tables/stability.tex` + a new paragraph in `subsec:results_nasa`. It was measured in the notebook but never in the package, and never for the operator the paper actually uses |
| 7.7c | [x] | **New positive result: the decision is invariant under operator scale** | tau spreads 4.4-6.6% across seeds; normalised by the bearing's median residual it spreads 0.7-1.2%. Bearing 1's lead time varies 0.12% on a 74-hour forecast while its radius varies 5.7% |
| 7.7d | [x] | H1 and H2 both ruled out | Estimator-only spread 0.5-1.2% (so n=49 is comfortably clear of the degenerate range); 16/16 latent units active under every seed, correlation of code concentration with tau +0.13 |
| 7.8 | [ ] | `run_all.py --layer b`, and `--layer all` meaning all three | **Confirmed open**: `run_all.py` L845 still declares `choices=("a1","a2","all")`. Layer B is reachable only through its three separate entry points (`verify_operator.py`, `build_field_cache.py`, `stability_experiment.py`) |
| 7.9 | [x] | **CWRU oracle probe run and its findings settled** | `results/cwru_oracle_probe.json`, 11 Aug. Established that the 1797 RPM false-alarm rate is a sample-size artefact (all four speeds hit exactly 2.46% at n=203) while the threshold is not, and that 1797 is the one speed that does not memorise |
| 7.10 | [ ] | **Fold the oracle-probe findings into the CWRU results prose** | `subsec:results_cwru` | Depends on 7.2c. The probe answered the 1797 question; the paper should say so rather than leave the outlier unexplained, since a referee will ask |

---

## What is actually left

Ordered by what blocks what. Everything else above is closed.

**The bibliography is done** (5.7, 5.8, 5.10, 5.11, 5.12 all closed 11 Aug
2026), so it no longer heads this list. What remains:

1. **CWRU table emitter** (7.2c) → **CWRU prose** (7.10).
2. **Re-run the full chain** (6.1) — required, `data.json` is two weeks stale.
3. **Then and only then**: the numeric cross-checks (4.3, 4.6, 6.4), which are
   meaningless before step 2.
4. **Compile under the real `cas-sc`** (6.3, 6.5), test suite (6.2), repo
   hygiene (6.6), commit the caches (6.8). Partial credit on 6.3 and 6.5: a
   full build of `mssp_draft.tex` against the `cas-sc.cls` in this repo was run
   during the bibliography audit and gave **0 undefined citations, 0 undefined
   references, 0 overfull hboxes, 46 pages**. The only error was a missing
   decorative `thumbnails/cas-email.jpeg` from the CAS bundle. That is not a
   substitute for 6.3 — it was run before the re-run of step 2 — but it does
   mean the class and the `.bst` are working.
5. **Confirm the `disanti2026inverse` URL** (5.14) — the one reference item
   left, and only you can check it.
6. **Outside the repo**: cover letter, suggested reviewers (5.13),
   acknowledgements decision (5.5), and the two open judgement calls in
   "Not blocking, but worth deciding".

The two items that are pure judgement and need no machine: 7.1 (softening the
novelty claim) and 7.2 (word count against MSSP's expectations at ~19,200
words).
