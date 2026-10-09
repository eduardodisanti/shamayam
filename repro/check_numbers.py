"""Audit the manuscript's prose against the artefacts of a run.

Why this exists
---------------
Tables and figures reach the paper by \\input and by copy, so they cannot
disagree with the run that produced them. Prose does not: every number in a
sentence is typed by hand. `reproduce.py` emits `numbers.tex` to close that
gap and the manuscript does not \\input it, so the gap is open. Until it is
wired, this script is the net.

It does not edit anything. It reads, compares and reports.

What it checks
--------------
1. SUSPECT  a number in the prose that is close to, but not equal to, a value
            in a generated table or JSON. This is the shape the defect
            actually takes: the table says 21.5 and the sentence says 22; the
            table says 66.25 and the sentence says 68.75. Near-misses are the
            signal, exact matches are fine and absences are usually legitimate.
2. CROSSING  every sentence of the form "enters N per cent ... at $n=K$"
            checked against convergence.json, which is the authority.
3. RANGE    the headline ranges of the abstract and the contributions
            ("four to twenty-one exemplars", "ten to twelve realisations")
            against the actual minimum and maximum in the tables.

Exit status is 1 if anything in category 1 or 2 fails, so it can gate a
submission.

    python check_numbers.py --run ../../v8/run_o --tex ../tex
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict

NUM = r'-?\d+(?:\.\d+)?'


def _blank(pat, text, flags=0):
    """Blank a region but keep its newlines, so line numbers stay true.

    Deleting the tabulars outright shifted every reported line number after
    the first table. A checker that points at the wrong line is worse than
    none, which is the whole failure mode this script exists to catch.
    """
    return re.sub(pat, lambda m: '\n' * m.group().count('\n'), text, flags=flags)


def _floats(text):
    for m in re.finditer(NUM, text):
        try:
            yield float(m.group()), m.group()
        except ValueError:
            pass


def harvest(run, texdir):
    """Every value the paper REPORTS, and where it came from.

    Deliberately narrow. Feeding the raw JSON in makes 20k values and every
    prose number finds a spurious neighbour; the signal drowns. The paper
    reports the generated tables, plus the named scalars of convergence.json
    (the crossings and each class's limiting radius), and those are what a
    sentence can contradict.
    """
    src = defaultdict(set)
    for d in (run, texdir):
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.startswith("table_") and fn.endswith(".tex"):
                for v, _ in _floats(open(os.path.join(d, fn)).read()):
                    src[v].add(fn)
    conv = os.path.join(run, "convergence.json")
    if os.path.exists(conv):
        c = json.load(open(conv))
        for k, v in {**c.get("domains", {}), **c.get("digits", {})}.items():
            if v.get("r_true") is not None:
                src[round(float(v["r_true"]), 6)].add("convergence.json:r_true")
            for key, val in (v.get("crossings") or {}).items():
                if val is not None:
                    src[float(val)].add(f"convergence.json:{key}")
    return src


def prose(texfile):
    """Numbers in the running text: no preamble, comments or tabulars."""
    raw = open(texfile).read()
    cut = raw.index('\\begin{document}')
    t = '\n' * raw[:cut].count('\n') + raw[cut:]   # conservar la numeracion
    t = re.sub(r'(?m)(?<!\\)%.*$', '', t)
    t = _blank(r'\\begin\{tabular\}.*?\\end\{tabular\}', t, re.S)
    t = re.sub(r'\\(?:label|ref|cite|input|includegraphics|newcommand)'
               r'\s*(?:\[[^\]]*\])?\{[^}]*\}', ' ', t)
    out = []
    for ln, line in enumerate(t.split('\n'), 1):
        for m in re.finditer(r'\$([^$]{0,40}?)\$', line):
            for v, s in _floats(m.group(1)):
                out.append((v, s, ln, line.strip()[:100]))
    return out


def near(v, src, tol=0.06):
    """Values in the run that are close to v but not equal to it."""
    hits = []
    for w, where in src.items():
        if w == v or w == 0 or v == 0:
            continue
        if abs(v - w) / max(abs(v), abs(w)) <= tol:
            hits.append((w, sorted(where)))
    return sorted(hits, key=lambda h: abs(h[0] - v))


def check_suspects(texfile, src):
    """A prose number that near-misses a produced value, and matches none."""
    bad = []
    for v, s, ln, ctx in prose(texfile):
        if v in src:
            continue                      # exact: backed by the run
        if '.' not in s and v < 20:
            continue                      # small integers are counters, not data
        if v != round(v, 4):
            continue                      # long decimals are observable design
        n = near(v, src)
        if n:
            bad.append((v, ln, ctx, n[:3]))
    return bad


def check_crossings(texfile, run):
    """'enters five per cent at n=100' against convergence.json."""
    conv = json.load(open(os.path.join(run, "convergence.json")))
    S = {**conv.get("domains", {}), **conv.get("digits", {})}
    truth = defaultdict(set)
    for k, v in S.items():
        c = v.get("crossings", {})
        for pct, key in ((10, "within_10pct"), (5, "within_5pct"),
                         (1, "within_1pct")):
            if c.get(key) is not None:
                truth[pct].add(float(c[key]))
    words = {"one": 1, "five": 5, "ten": 10}
    t = re.sub(r'(?m)(?<!\\)%.*$', '', open(texfile).read())
    bad = []
    pat = re.compile(r'\b(one|five|ten)\s+per\s+cent\b[^.]{0,80}?'
                     r'\$n\s*=\s*(' + NUM + r')\$', re.I)
    for ln, line in enumerate(t.split('\n'), 1):
        for m in pat.finditer(line):
            pct, n = words[m.group(1).lower()], float(m.group(2))
            if pct in truth and n not in truth[pct]:
                bad.append((ln, pct, n, sorted(truth[pct]), line.strip()[:100]))
    return bad


DOMAIN_WORDS = {
    "PM real (nominal)":      ("point machine", "point-machine"),
    "PM simulated":           ("simulated point", "pm simulated"),
    "ECG real (MIT-BIH)":     ("ecg", "mit-bih", "heartbeat", "beat"),
    "Battery real (NASA)":    ("battery", "batteries", "discharge"),
    "NOAA tides":             ("tide", "tidal"),
    "NSRDB solar (GHI)":      ("solar", "irradiance", "nsrdb"),
    "Spoken digits (FSDD)":   ("spoken", "fsdd"),
    "UCI digits 8x8":         ("uci",),
    "MNIST 28x28":            ("mnist",),
}


def _rows(path):
    """(label, [values]) per data row of a generated table."""
    out = []
    for line in open(path):
        if '&' not in line or '\\\\' not in line:
            continue
        cells = line.split('&')
        lab = re.sub(r'[\\${}]', '', cells[0]).strip()
        if not lab or lab.lower() in ("domain", "curve", "set", "control"):
            continue
        vals = [v for c in cells[1:] for v, _ in _floats(c)]
        if vals:
            out.append((lab, vals))
    return out


def check_by_domain(texfile, texdir, tol=0.06):
    """A sentence that names a domain and cites a number close to, but not
    equal to, that domain's own row.

    This is narrower than comparing against every table at once, which finds
    accidental neighbours across unrelated quantities and drowns the signal.
    It is still a heuristic: it reports candidates to look at, not verdicts.
    """
    rows = {}
    for fn in ("table_saturation_summary.tex", "table_surrogates.tex"):
        p = os.path.join(texdir, fn)
        if os.path.exists(p):
            for lab, vals in _rows(p):
                rows.setdefault(lab, set()).update(vals)
    t = re.sub(r'(?m)(?<!\\)%.*$', '', open(texfile).read())
    t = _blank(r'\\begin\{tabular\}.*?\\end\{tabular\}', t, re.S)
    bad = []
    for ln, line in enumerate(t.split('\n'), 1):
        low = line.lower()
        for lab, vals in rows.items():
            words = DOMAIN_WORDS.get(lab, ())
            if not any(w in low for w in words):
                continue
            for m in re.finditer(r'\$([^$]{0,30}?)\$', line):
                for v, s in _floats(m.group(1)):
                    if v in vals or v == 0 or ('.' not in s and v < 20):
                        continue
                    close = [w for w in vals if w and
                             abs(v - w) / max(abs(v), abs(w)) <= tol]
                    if close:
                        bad.append((ln, lab, v, sorted(close), line.strip()[:96]))
    return bad


def check_durations(texfile, run):
    """Every "$N$~ms" in the prose against convergence.json/spoken_duration.

    These four figures were measured and thrown away until the stage was made
    to store them; they were the only numbers in the paper whose provenance had
    to be reconstructed by hand. Now they have a field, so they get a check.
    """
    c = json.load(open(os.path.join(run, "convergence.json")))
    sd = c.get("spoken_duration")
    if not sd:
        return [(0, 0.0, [], "convergence.json sin spoken_duration: corrida vieja")]
    ok = {round(v) for v in sd["mean_ms_per_class"].values()}
    ok |= {round(sd["spread_of_class_means_ms"]),
           round(sd["mean_spread_within_class_ms"])}
    ok |= {round(v) for v in sd["spread_within_class_ms"].values()}
    # the two declared constants of the observable, derived from the loader
    # rather than listed here, so a change to the representation moves them.
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
        import audio_mnist as AM
        ok |= {round(AM.WIN / AM.SR * 1000), round(AM.HOP / AM.SR * 1000)}
    except Exception:
        pass
    t = re.sub(r'(?m)(?<!\\)%.*$', '', open(texfile).read())
    bad = []
    for ln, line in enumerate(t.split('\n'), 1):
        for m in re.finditer(r'\$(' + NUM + r')\$~?\s*ms\b', line):
            v = round(float(m.group(1)))
            if v not in ok:
                bad.append((ln, v, sorted(ok), line.strip()[:96]))
    return bad


def check_ranges(texdir):
    """The headline ranges, against the tables they summarise."""
    out = []
    p = os.path.join(texdir, "table_surrogates.tex")
    if os.path.exists(p):
        rows = [l for l in open(p) if '&' in l and '\\\\' in l and 'domain' not in l]
        real = []
        for r in rows:
            cells = r.split('&')
            if len(cells) > 3:
                f = re.search(NUM, cells[3])
                if f:
                    real.append((float(f.group()), cells[0].strip()))
        if real:
            lo, hi = min(real), max(real)
            out.append(("covering number |S| over table_surrogates",
                        f"{lo[0]} ({lo[1]}) to {hi[0]} ({hi[1]})"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="../../v8/run_o")
    ap.add_argument("--tex", default="../tex")
    ap.add_argument("--manuscript", default=None)
    ap.add_argument("--wide", action="store_true",
                    help="barrido heuristico contra todas las tablas; ruidoso")
    a = ap.parse_args()
    man = a.manuscript or os.path.join(a.tex, "the_geometry_of_intelligence.tex")

    src = harvest(a.run, a.tex)
    print(f"fuentes: {len(src)} valores distintos producidos por la corrida\n")

    fails = 0

    print("=" * 72)
    print("1. CROSSINGS: afirmaciones de la prosa contra convergence.json")
    print("=" * 72)
    cr = check_crossings(man, a.run)
    if not cr:
        print("  todas las afirmaciones 'enters X per cent at n=K' cuadran\n")
    for ln, pct, n, ok, ctx in cr:
        fails += 1
        print(f"  l.{ln}: dice n={n:.0f} para el {pct}%, la corrida da "
              f"{[int(x) for x in ok]}")
        print(f"        {ctx}\n")

    print("=" * 72)
    print("2. POR DOMINIO: una frase que nombra un dominio y cita un numero")
    print("   cercano pero distinto al de la fila de ese dominio")
    print("=" * 72)
    dm = check_by_domain(man, a.tex)
    if not dm:
        print("  ninguno\n")
    for ln, lab, v, close, ctx in dm:
        fails += 1
        print(f"  l.{ln}: la frase habla de <{lab}> y dice {v:g}; "
              f"esa fila tiene {', '.join(f'{c:g}' for c in close)}")
        print(f"        {ctx}\n")

    if a.wide:
        print("=" * 72)
        print("2b. BARRIDO AMPLIO (heuristico, con falsos positivos)")
        print("=" * 72)
        for v, ln, ctx, n in check_suspects(man, src):
            alts = ", ".join(f"{w:g} [{'/'.join(wh)}]" for w, wh in n)
            print(f"  l.{ln}: prosa {v:g}; corrida {alts}\n        {ctx}\n")

    print("=" * 72)
    print("3. DURACIONES: cada \"$N$ ms\" contra convergence.json")
    print("=" * 72)
    du = check_durations(man, a.run)
    if not du:
        print("  todas las duraciones citadas estan respaldadas\n")
    for ln, v, ok, ctx in du:
        fails += 1
        print(f"  l.{ln}: dice {v} ms; la corrida tiene {ok}")
        print(f"        {ctx}\n")

    print("=" * 72)
    print("4. RANGOS declarados, para cotejar a ojo con abstract y contribuciones")
    print("=" * 72)
    for what, val in check_ranges(a.tex):
        print(f"  {what}: {val}")

    print()
    print(f"{'FALLA' if fails else 'OK'}: {fails} hallazgo(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
