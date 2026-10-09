"""Emit the tables that the manuscript still carries as hand-typed `tabular`s.

Sixteen tables reach the paper by \\input and are byte-identical to the run.
Ten more were typed into the manuscript. Their numbers are correct --- each was
checked against the run --- but nothing keeps them correct: re-run the pipeline
and the paper keeps the old figure without complaint. This module closes that
by generating them from the same artefacts.

Every emitter here is verified against the table it replaces:

    python emit_tables.py --check      # compare with _work/ref/*.tex, emit nothing
    python emit_tables.py --out ../tex # write them

Sources, all of them already produced by a run:

    table_surrogates_own   surrogate_test.json   *_own, *_own_eps
    table_crossings        convergence.json      crossings
                           + control_sup.json    L-inf column (since 2026-09-23;
                             --check reports DIFF against the pre-control ref
                             for this table, deliberately)
    table_support_growth   surrogate_test.json   growth
    table_cross_ecg        surrogate_test.json + dimension.json
    table_pm_crosstab      pm_pooling.json       cross
    table_pm_settle        pm_pooling.json       convergence
    table_nsat_nsrdb       multisite.json        solar
    table_nsat_tides       multisite.json        tides
"""
from __future__ import annotations

import argparse
import json
import os
import sys

TOP, MID, BOT = "\\toprule", "\\midrule", "\\bottomrule"


def _tab(colspec, header, body, extra_mid=()):
    out = [f"\\begin{{tabular}}{{{colspec}}}", TOP]
    out += header
    out.append(MID)
    for i, r in enumerate(body):
        if i in extra_mid:
            out.append(MID)
        out.append(r)
    out += [BOT, "\\end{tabular}"]
    return "\n".join(out) + "\n"


def _load(run, name):
    p = os.path.join(run, name)
    return json.load(open(p)) if os.path.exists(p) else None


# --------------------------------------------------------------- surrogates
ORDER5 = ["Battery real (NASA)", "ECG real (MIT-BIH)", "ECG simulated",
          "PM real (nominal)", "PM simulated"]


def surrogates_own(run, **kw):
    """|S| of each surrogate at its OWN epsilon, not at the real class's."""
    d = _load(run, "surrogate_test.json")
    head = [" & real & \\textsc{shuffle} & \\textsc{ft} & \\textsc{iaaft} \\\\",
            "domain & $|S|$ ($\\varepsilon$) & $|S|$ ($\\varepsilon$) & "
            "$|S|$ ($\\varepsilon$) & $|S|$ ($\\varepsilon$) \\\\"]
    rows = []
    for k in ORDER5:
        r = d[k]
        cells = [f"{r['real']:.1f} ({r['eps']:.3f})"]
        for s in ("shuffle", "ft", "iaaft"):
            cells.append(f"{r[s + '_own']:.1f} ({r[s + '_own_eps']:.3f})")
        rows.append(f"{k} & " + " & ".join(cells) + " \\\\")
    return _tab("lrrrr", head, rows)


def support_growth(run, **kw):
    """The within-class maximum against n.

    The published table carried a seventh column, an exponent $n^{a}$ fitted to
    each row. The thirty tabulated values reproduce exactly from `growth`, but
    the five exponents do not: a log-log fit over all points, over $n \\ge 25$,
    and over the six tabulated columns give 0.072 / 0.031 / 0.050 for the
    simulated point machine against the 0.02 published, and none of the three
    reproduces all five rows. The method that produced them is not in the code.
    The column is therefore emitted from a DECLARED fit -- ordinary least
    squares on log |S| against log n, over the whole curve -- and the exponents
    it gives differ from the published ones. That is a change to reported
    numbers and is flagged, not hidden.
    """
    import math
    d = _load(run, "surrogate_test.json")
    cols = [25, 50, 100, 200, 400, 600]
    head = ["domain & $n{=}25$ & 50 & 100 & 200 & 400 & 600 & fitted \\\\"]
    rows = []
    for k, r in d.items():
        g = r.get("growth")
        if not g:
            continue
        steps = list(range(1, len(g) + 1))
        vals = [g[min(range(len(steps)), key=lambda i: abs(steps[i] - c))]
                for c in cols]
        lx = [math.log(s) for s in steps]
        ly = [math.log(v) for v in g]
        mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
        slope = (sum((a - mx) * (b - my) for a, b in zip(lx, ly))
                 / sum((a - mx) ** 2 for a in lx))
        rows.append((slope, f"{k} & " + " & ".join(f"{v:.1f}" for v in vals)
                     + f" & $n^{{{slope:.2f}}}$ \\\\"))
    rows.sort()
    return _tab("lrrrrrrl", head, [r for _s, r in rows])


def cross_ecg(run, **kw):
    """The two instruments that describe the ECG generator."""
    s = _load(run, "surrogate_test.json")
    dm = _load(run, "dimension.json")["domains"]
    head = [" & exemplars at its own resolution & intrinsic dimension \\\\"]
    rows = []
    for k in ("ECG real (MIT-BIH)", "ECG simulated"):
        d = dm[k]
        rows.append(f"{k} & ${s[k]['real']:.1f} \\pm {s[k]['real_sd']:.1f}$ & "
                    f"${d['dim']:.2f} \\pm {d['stderr']:.2f}$ \\\\")
    return _tab("lrr", head, rows)


# --------------------------------------------------------------- crossings
def crossings(run, control=None, **kw):
    """Where each curve enters a tolerance and does not leave again.

    The first three columns are the paper's metric (cosine), from the run. The
    last is the same reading, five per cent, in the supremum norm -- the norm
    the theory is stated in -- from the metric control (control_sup.py,
    Appendix app:metric-control). The control's cosine arm is checked here
    against the run, reading by reading: if the two disagree, the column would
    not be comparable with the rest of the row and the table is not emitted.

    The tidal row carries a spade. At 159 lunar days per station the control
    has no resolution there; control_tides.py repeats it on all 24 months on
    disk, and the manuscript's note under the table reports that result.
    """
    c = _load(run, "convergence.json")
    S = {**c.get("domains", {}), **c.get("digits", {})}
    if not control or not os.path.exists(control):
        raise FileNotFoundError(f"metric control not found: {control}")
    L = json.load(open(control))["domains"]
    head = [" & \\multicolumn{3}{c}{cosine} & $L_\\infty$ \\\\",
            "\\cmidrule(lr){2-4}\\cmidrule(lr){5-5}",
            "curve & within 10\\% & within 5\\% & within 1\\% & within 5\\% \\\\"]
    rows = []
    for k, v in S.items():
        cr = v.get("crossings", {})
        if L[k]["cos"]["crossings"] != cr:
            raise ValueError(f"{k}: control cosine arm differs from the run")
        li = L[k]["linf"]["crossings"].get("within_5pct")
        g = lambda x: ("---" if cr.get(x) is None else f"{cr[x]:g}")
        name = k + ("$^{\\spadesuit}$" if k == "NOAA tides" else "")
        rows.append(((cr.get("within_10pct") or 1e9, cr.get("within_5pct") or 1e9, k),
                     f"{name} & {g('within_10pct')} & {g('within_5pct')} & "
                     f"{g('within_1pct')} & {'---' if li is None else f'{li:g}'} \\\\"))
    rows.sort()
    return _tab("lrrrr", head, [r for _s, r in rows])


# ---------------------------------------------------------------- point machine
PM = [("J1_normal_to_reverse", "J1 normal $\\to$ reverse"),
      ("J1_reverse_to_normal", "J1 reverse $\\to$ normal"),
      ("J2_normal_to_reverse", "J2 normal $\\to$ reverse"),
      ("J2_reverse_to_normal", "J2 reverse $\\to$ normal")]
RUL = ["J1 n$\\to$r", "J1 r$\\to$n", "J2 n$\\to$r", "J2 r$\\to$n", "all four"]


def pm_crosstab(pooling=None, **kw):
    """|S| of each population measured with every population's own ruler."""
    d = json.load(open(pooling))
    eps, S = d["cross"]["eps"], d["cross"]["S"]
    head = ["$|S|$ at the tolerance of $\\to$ & " + " & ".join(RUL) + " \\\\",
            " & " + " & ".join(f"{e:.4f}" for e in eps) + " \\\\"]
    rows = [f"{lab} & " + " & ".join(f"{v:.2f}" for v in S[k]) + " \\\\"
            for k, lab in PM]
    tot = [sum(S[k][j] for k, _ in PM) for j in range(len(eps))]
    big = [max(S[k][j] for k, _ in PM) for j in range(len(eps))]
    rows.append("all four together & "
                + " & ".join(f"{v:.2f}" for v in S["POOLED"]) + " \\\\")
    rows.append("sum of the four & " + " & ".join(f"{v:.2f}" for v in tot) + " \\\\")
    rows.append("all four $/$ largest & "
                + " & ".join(f"{S['POOLED'][j] / big[j]:.2f}"
                             for j in range(len(eps))) + " \\\\")
    return _tab("lrrrrr", head, rows, extra_mid={4})


def pm_settle(pooling=None, **kw):
    """Where each population's radius estimate settles, and its residual."""
    d = json.load(open(pooling))["convergence"]
    cols = [5, 20, 50, 200]
    head = ["set & settles at & " + " & ".join(f"$n{{=}}{c}$" for c in cols)
            + " \\\\"]
    rows = []
    for k, lab in PM + [("POOLED", "all four together")]:
        c = d[k]
        st, rm, rt = c["steps"], c["r_mean"], c["r_true"]
        cells = []
        for want in cols:
            j = min(range(len(st)), key=lambda i: abs(st[i] - want))
            v = rm[j][0] if isinstance(rm[j], (list, tuple)) else rm[j]
            cells.append(f"{abs(v - rt) / rt * 100:.1f}")
        rows.append(f"{lab} & {rt:.5f} & " + " & ".join(cells) + " \\\\")
    return _tab("lrrrrr", head, rows)


def pm_control(controls=None, **kw):
    """The two controls the pair table is normalised against.

    Synthetic, seeded, and cheap: two compact manifolds of the same kind must
    give a ratio near one and separability near a half; two in different
    subspaces a clearly larger ratio and separability near one. `pm_sets.py`
    computed these and printed them; `--controls-out` now writes them, which is
    what makes this table and the next generable.
    """
    c = json.load(open(controls))
    head = ["control & $\\rho$ & separability \\\\"]
    rows = [f"same manifold & {c['same']['rho']:.2f} & "
            f"{c['same']['separability']:.3f} \\\\",
            f"different manifolds & {c['different']['rho']:.2f} & "
            f"{c['different']['separability']:.3f} \\\\"]
    return _tab("lrr", head, rows)


SHORT = {"J1_normal_to_reverse": "J1 n$\\to$r", "J1_reverse_to_normal": "J1 r$\\to$n",
         "J2_normal_to_reverse": "J2 n$\\to$r", "J2_reverse_to_normal": "J2 r$\\to$n"}


def _kind(a, b):
    ua, ub = a[:2], b[:2]
    da, db = a[3:], b[3:]
    if ua == ub:
        return "same unit, both directions"
    if da == db:
        return "same direction, different unit"
    return "cross"


def pm_pairs(sets=None, controls=None, **kw):
    """Every pair of nominal populations, against the two controls.

    The last-but-one column is the position of the pair between the controls,
    not between one and two: (rho - rho_same) / (rho_diff - rho_same). That is
    what reproduces the published percentages, and it was not written down
    anywhere.
    """
    d = json.load(open(sets))["pairs"]
    c = json.load(open(controls))
    lo, hi = c["same"]["rho"], c["different"]["rho"]
    head = ["pair & $\\bar\\rho$ & asym. & separability & "
            "of the way to ``two'' & kind \\\\"]
    rows = []
    for k, v in d.items():
        a, b = k.split("|")
        ra, rb = v["a_to_b"][2], v["b_to_a"][2]
        sa, sb = v["a_to_b"][3], v["b_to_a"][3]
        rho, asym, sep = (ra + rb) / 2, abs(ra - rb), (sa + sb) / 2
        pct = (round(rho, 2) - lo) / (hi - lo) * 100
        rows.append((rho, f"{SHORT[a]} $+$ {SHORT[b]} & {rho:.2f} & {asym:.2f} & "
                          f"{sep:.3f} & {pct:.0f}\\% & {_kind(a, b)} \\\\"))
    rows.sort()
    return _tab("lrrrrl", head, [r for _s, r in rows])


# ------------------------------------------------------------------- n_sat
def _days(x, unit="days"):
    """Print a saturation scale without inventing precision.

    n_sat is a count of days on an integer grid, so a whole value prints
    whole (192, not 192.00) and a half-integer median prints with the one
    decimal it actually has (21.5). Statistics that are genuinely fractional
    -- the mean, the standard deviation -- keep two decimals. Trailing zeros
    are stripped, never significant digits.
    """
    return f"{x:.2f}".rstrip("0").rstrip(".") + f" {unit}"


def _nsat(multisite, key, unit="days"):
    """Summary statistics of the saturation scale across stations.

    The two hand-typed versions of this table disagreed in their formatting --
    the solar one printed whole numbers, the tidal one two decimals -- because
    each was typed separately. Generating both unifies them on one rule (see
    _days): significant digits only. No value changes.
    """
    import statistics as st
    v = sorted(r["n_sat"] for r in json.load(open(multisite))[key])
    q = lambda p: st.quantiles(v, n=100, method="inclusive")[p - 1]
    body = [("Number of stations", f"{len(v)}"),
            ("Mean $n_{\\mathrm{sat}}$", _days(st.mean(v), unit)),
            ("Std. dev.", _days(st.stdev(v), unit)),
            ("Median $n_{\\mathrm{sat}}$", _days(st.median(v), unit)),
            ("25th percentile", _days(q(25), unit)),
            ("75th percentile", _days(q(75), unit)),
            ("Minimum", _days(min(v), unit)),
            ("Maximum", _days(max(v), unit))]
    for th in ((30, 40) if key == "solar" else (15, int(max(v)))):
        f = sum(1 for x in v if x <= th) / len(v) * 100
        body.append((f"Fraction with $n_{{\\mathrm{{sat}}}} \\leq {th}$",
                     f"{f:.2f}".rstrip("0").rstrip(".") + "\\%"))
    head = ["\\textbf{Statistic} & \\textbf{Value} \\\\"]
    return _tab("lc", head, [f"{a} & {b} \\\\" for a, b in body])


def nsat_nsrdb(multisite=None, **kw): return _nsat(multisite, "solar")
def nsat_tides(multisite=None, **kw): return _nsat(multisite, "tides")


TABLES = {"table_pm_control": pm_control,
          "table_pm_pairs":   pm_pairs,
          "table_surrogates_own": surrogates_own,
          "table_support_growth": support_growth,
          "table_cross_ecg":      cross_ecg,
          "table_crossings":      crossings,
          "table_pm_crosstab":    pm_crosstab,
          "table_pm_settle":      pm_settle,
          "table_nsat_nsrdb":     nsat_nsrdb,
          "table_nsat_tides":     nsat_tides}

def _norm(s):
    """Line-wise normalisation for --check.

    A trailing space in a hand-typed reference is not a numerical difference.
    Comparing normalised text keeps DIFF meaning "a value moved", which is the
    only thing this check exists to catch.
    """
    return "\n".join(l.rstrip() for l in s.strip().split("\n"))


REF = {"table_pm_control": "pm_control", "table_pm_pairs": "pm_pairs",
       "table_surrogates_own": "surrogates_own", "table_crossings": "crossings",
       "table_support_growth": "support_growth", "table_cross_ecg": "cross_ecg",
       "table_pm_crosstab": "pm_crosstab", "table_pm_settle": "pm_settle",
       "table_nsat_nsrdb": "nsat_nsrdb", "table_nsat_tides": "nsat_tides"}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="../../v8/run_o")
    ap.add_argument("--pooling", default="../../v8/pm_pooling.json")
    ap.add_argument("--multisite", default="../../v8/_figcheck/multisite.json")
    ap.add_argument("--sets", default="../../v8/pm_sets.json")
    ap.add_argument("--controls", default="../_work/pm_controls.json")
    ap.add_argument("--control",
                    default="../_work/control_sup_run/all/control_sup.json",
                    help="metric control (control_sup.py) for table_crossings")
    ap.add_argument("--out", default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ref", default="../_work/ref")
    a = ap.parse_args()

    bad = 0
    for name, fn in TABLES.items():
        try:
            tex = fn(run=a.run, pooling=a.pooling, multisite=a.multisite,
                     sets=a.sets, controls=a.controls, control=a.control)
        except Exception as e:
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
            bad += 1
            continue
        if a.check:
            rp = os.path.join(a.ref, REF[name] + ".tex")
            ref = open(rp).read() if os.path.exists(rp) else None
            if ref is None:
                print(f"  ?     {name}: sin referencia")
            elif _norm(ref) == _norm(tex):
                print(f"  OK    {name}")
            else:
                bad += 1
                print(f"  DIFF  {name}")
                import difflib
                for l in list(difflib.unified_diff(
                        _norm(ref).split("\n"), _norm(tex).split("\n"),
                        "manuscrito", "generada", lineterm=""))[2:14]:
                    print("        " + l)
        if a.out:
            open(os.path.join(a.out, name + ".tex"), "w").write(tex)
            print(f"  escrita {name}.tex")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
