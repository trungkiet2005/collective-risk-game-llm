"""Bounded, post-hoc selection diagnostics using existing saved games only.

Scope registered before computing these diagnostics (2026-09-18): the full five-model
set AND ALL FIVE leave-one-model-out sets; N in {6, 30}; p in {0.1, 0.5, 0.9}; beta=1.
No subset may be selected after inspecting results. Stored composition-dependent
payoffs are unchanged. Removing a model changes the available strategy set and the
uniform mutation destinations, NOT any model's prompt or behaviour. Report every
combination, including failed calculations and changed winners, in the full CSV.
These are post-hoc numerical point estimates, not new uncertainty estimates or ESS
claims. No model calls, paid compute, bootstrap, or modification of existing files.

Also report every ordered single-entrant/resident pair at all three risks (60 cells),
and all their mixed-table compositions (300 cells). The entrant's payoff minus the
resident's SELF-PLAY payoff is not its payoff advantage over the five TABLEMATES,
nor its population fitness advantage, nor its full-path fixation probability.
Population outcomes weight monomorphic self-play outcomes by stationary mass.
At p=.5 report welfare/opt as well as target rate: zero payment and exact threshold
payment both attain welfare 20 per seat, with target rates 0 and 1 respectively.

Numerical gates fixed before execution: stochastic chain/residual and tree/eigen
agreement at 1e-8; full-panel agreement with selection.py at 1e-8 and existing
num_selection.tex macros at their printed precision; balanced existing cells;
no source changes during execution. Failures are saved and return nonzero; they
are never omitted or silently replaced with a successful estimate. This entire
output is classified as diagnostic. The original full-panel results were known
before this additional scope was registered; this is not a preregistered study.

Run from the repository root in WSL:
  /home/crsd-egttools/bin/python -B paper/AAMAS/analysis/review_checks.py
Writes only supplement/tables/s_review_selection.tex, review_selection.csv and
review_selection.json. The JSON records deterministic source hashes, environment,
definitions, checks and errors; the CSV contains all unrounded numerical estimates.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import itertools
import json
import platform
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logsumexp

import selection as sel

cd = sel.cd
ROOT = cd.REPO
OUT = cd.PAPER / "supplement" / "tables"
MODELS = tuple(sel.M)
RISKS = (0.1, 0.5, 0.9)
POPULATIONS = (6, 30)
BETA = 1.0
TOL = 1e-8
SETS = (None, *MODELS)
SHORT = dict(zip(MODELS, ("Haiku", "Flash-Lite", "Luna", "Qwen", "Grok")))


def source_hashes():
    paths = [Path(__file__).resolve(), ROOT / "paper/AAMAS/tables/num_selection.tex"]
    paths += [ROOT / "paper/AAMAS/analysis" / f for f in
              ("selection.py", "crsd_data.py", "crsd_style.py")]
    for exp in ("exp_mixed", "exp_baseline", "exp_evprobe"):
        paths += sorted((ROOT / "results" / exp).glob("*/*/*.csv"))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths))}


def chain_mass(R):
    """Dimension-independent chain; reuse fixation probabilities without renormalizing mass."""
    n = len(R)
    C = R.T.copy() / (n - 1)
    np.fill_diagonal(C, 0)
    np.fill_diagonal(C, 1 - C.sum(axis=1))
    if not np.isfinite(C).all() or C.min() < -TOL or not np.allclose(C.sum(1), 1, atol=TOL):
        raise ValueError("invalid transition matrix")
    vals, vecs = np.linalg.eig(C.T)
    v = np.real(vecs[:, np.argmin(abs(vals - 1))])
    if v.sum() < 0:
        v = -v
    mass = v / v.sum()
    if mass.min() < -TOL:
        raise ValueError("negative stationary mass")
    mass = np.maximum(mass, 0)
    mass /= mass.sum()
    residual = float(np.max(abs(mass @ C - mass)))
    # Directed spanning trees into each root; tiny probabilities stay in log space.
    L = np.full_like(R, -np.inf)
    off = ~np.eye(n, dtype=bool)
    if (R[off] <= 0).any():
        raise ValueError("nonpositive fixation probability; log-space recomputation needed")
    L[off] = np.log(R[off])
    logw = []
    for root in range(n):
        others = [u for u in range(n) if u != root]
        terms = []
        for parents in itertools.product(*[[v for v in range(n) if v != u] for u in others]):
            parent = dict(zip(others, parents))
            valid = True
            for u in others:
                seen = set()
                while u != root and u not in seen:
                    seen.add(u)
                    u = parent[u]
                if u != root:
                    valid = False
                    break
            if valid:
                terms.append(sum(L[v, u] for u, v in parent.items()))
        logw.append(logsumexp(terms))
    tree = np.exp(np.array(logw) - logsumexp(logw))
    agreement = float(np.max(abs(tree - mass)))
    if residual > TOL or agreement > TOL:
        raise ValueError(f"stationary check failed: residual={residual}, tree difference={agreement}")
    return mass, residual, agreement


def check_macros(full):
    text = (cd.TABLES / "num_selection.tex").read_text(encoding="utf-8")
    macros = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^\n]*)\}", text))
    checks = {}

    def check(name, value):
        checks[name] = dict(expected=macros.get(name), recomputed=value,
                            passed=macros.get(name) == value)

    for p, label in zip(RISKS, ("Low", "Mid", "High")):
        check(f"SelWithinQwenMass{label}", cd.fmt(full[(6, p)]["mass_Qwen"], 2))
    for p, label in ((0.5, "Mid"), (0.9, "High")):
        check(f"SelAcrossFlashMass{label}", cd.fmt(full[(30, p)]["mass_Flash-Lite"], 2))
        check(f"SelWithinReach{label}", cd.pct(full[(6, p)]["target_rate"]))
        check(f"SelUniformReach{label}", cd.pct(full[(6, p)]["uniform_target_rate"]))
    check("SelAcrossReachHigh", cd.pct(full[(30, 0.9)]["target_rate"]))
    check("SelWithinPayHigh", cd.fmt(full[(6, 0.9)]["welfare"]))
    check("SelAcrossPayHigh", cd.fmt(full[(30, 0.9)]["welfare"]))
    check("SelAcrossWinnerLow", cd.show(full[(30, 0.1)]["winner"]))
    return checks


def table(lines, columns, heading, rows):
    # Keep the panel label inside its unbreakable tabular, so it cannot be orphaned.
    lines.extend([r"\par\medskip\noindent",
                  r"\begin{tabular}{@{}" + columns + r"@{}}",
                  r"\multicolumn{" + str(len(columns)) + r"}{@{}l}{" + heading + r"} \\[3pt]",
                  r"\toprule"])
    lines.extend(rows)
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\par"])


def render(records, errors):
    lines = ["% Generated by review_checks.py; point estimates from existing data.",
             r"\begingroup\fontsize{8}{9.5}\selectfont\setlength{\tabcolsep}{3pt}",
             r"\noindent Post-hoc selection diagnostics. All entries are point estimates; no new intervals are computed.",
             r"Names: Haiku = Claude Haiku 4.5; Flash-Lite = Gemini 3.5 Flash-Lite; Luna = GPT-5.6 Luna; Qwen = Qwen3-235B; Grok = Grok 4.20.\par"]
    entrants = [r for r in records if r["kind"] == "entrant"]
    for j, p in enumerate(RISKS):
        rows = [r"Resident $B$ & Entrant $A$ & $u_B^{\rm self}$ & $u_A(1)$ & $u_B(5)$ & $\Delta_{\rm self}$ & $\Delta_{\rm table}$ & $\rho_6$ & $\rho_{30}$ \\", r"\midrule"]
        for r in entrants:
            if r["p"] == p:
                values = [SHORT[r["resident"]], SHORT[r["entrant"]]]
                values += [f"{r[k]:.2f}" for k in ("resident_selfplay", "entrant_payoff", "resident_table_payoff", "gap_selfplay", "gap_table")]
                values += [f"{r[k]:.2g}" for k in ("fixation_N6", "fixation_N30")]
                rows.append(" & ".join(values) + r" \\")
        table(lines, "llrrrrrrr", f"(A{j+1}) Single entrant and five residents, $p={p:g}$; fixation at $\\beta=1$.", rows)
    lines += [r"\noindent $\Delta_{\rm self}=u_A(1)-u_B^{\rm self}$ compares separate conditions; $\Delta_{\rm table}=u_A(1)-u_B(5)$ compares seats in the same mixed games.",
              r"Mixed entries average ten games; resident self-play averages twenty. $\rho_N$ is fixation probability from one entrant in a population of size $N$, using all table compositions and $\beta=1$, not just the first payoff gap. Neutral fixation is $1/N$. These comparisons do not establish evolutionary stability.\par"]
    ranks = {(r["omitted"], r["N"], r["p"]): r for r in records if r["kind"] == "ranking"}
    for N in POPULATIONS:
        rows = [r"Omitted model & $p=0.1$: winner (mass) & $p=0.5$: winner (mass) & $p=0.9$: winner (mass) \\", r"\midrule"]
        for omitted in SETS:
            values = ["None (all five)" if omitted is None else SHORT[omitted]]
            for p in RISKS:
                r = ranks[(omitted or "none", N, p)]
                values.append("FAILED" if r["status"] != "ok" else
                              f"{SHORT[r['winner']]} ({r['winner_mass']:.3f})" +
                              (r"$^{*}$" if r["winner_changed"] else ""))
            rows.append(" & ".join(values) + r" \\")
        table(lines, "llll", f"(B{1 if N == 6 else 2}) All candidate sets, $N={N}$ and $\\beta=1$.", rows)
    lines += [r"\noindent $^{*}$Winner differs from the full five-model set, including when that winner is omitted. Removing a candidate leaves every retained payoff unchanged and changes only the available models and mutation destinations.\par"]
    rows = [r"Omitted model & $N$ & Target (\%) & Welfare/seat & Welfare/opt (\%) & Uniform target (\%) & Uniform welfare/opt (\%) \\", r"\midrule"]
    for omitted in SETS:
        for N in POPULATIONS:
            r = ranks[(omitted or "none", N, 0.5)]
            values = ["None" if omitted is None else SHORT[omitted], str(N)]
            values += (["FAILED"] * 5 if r["status"] != "ok" else
                       [f"{100*r['target_rate']:.1f}", f"{r['welfare']:.2f}",
                        f"{100*r['welfare_over_opt']:.1f}", f"{100*r['uniform_target_rate']:.1f}",
                        f"{100*r['uniform_welfare_over_opt']:.1f}"])
            rows.append(" & ".join(values) + r" \\")
    table(lines, "lrrrrrr", r"(C) Target rate and welfare at $p=0.5$, $\beta=1$; $\mathrm{opt}=20$.", rows)
    lines += [r"\noindent Outcomes weight each retained model's self-play by its stationary mass; uniform assigns equal weight to retained models. These are rare-mutation monomorphic outcomes, not success rates during invasion. At $p=0.5$, zero contribution and an exact target both attain welfare 20, although their target rates are 0 and 100\%. Low target rate alone therefore does not imply welfare loss.\par",
              r"\endgroup"]
    return "\n".join(lines) + "\n"


def main():
    before = source_hashes()
    records, errors, checks = [], [], {}
    mx, sp = sel.load()
    identity_error, identity_signs = sel.identity_check(mx)
    mixed, selfc = sel.cell_arrays(mx, sp)
    P, reach, welfare = sel.tables(mixed, selfc)
    # Freeze the numerical arrays locally: candidate removal must not alter payoff estimates.
    for a in (P, reach, welfare):
        a.flags.writeable = False
    full, fix = {}, {}
    for pi, p in enumerate(RISKS):
        for N in POPULATIONS:
            fix[(N, p)] = sel.rho_matrix(P[pi], N, BETA)
    for pi, p in enumerate(RISKS):
        for b, a in itertools.permutations(range(len(MODELS)), 2):
            for k in range(1, 6):
                records.append(dict(kind="composition", status="ok", p=p, resident=MODELS[b],
                                    entrant=MODELS[a], entrant_seats=k, games=10,
                                    entrant_payoff=float(P[pi, a, b, k]),
                                    resident_table_payoff=float(P[pi, b, a, 6-k])))
            r = dict(kind="entrant", status="ok", p=p, resident=MODELS[b], entrant=MODELS[a],
                     entrant_seats=1, games=10, selfplay_games=20,
                     resident_selfplay=float(welfare[pi, b]), entrant_payoff=float(P[pi, a, b, 1]),
                     resident_table_payoff=float(P[pi, b, a, 5]))
            r["gap_selfplay"] = r["entrant_payoff"] - r["resident_selfplay"]
            r["gap_table"] = r["entrant_payoff"] - r["resident_table_payoff"]
            for N in POPULATIONS:
                fa, fb = sel.fitness(P[pi], a, b, N)
                r[f"initial_fitness_gap_N{N}"] = float(fa[0] - fb[0])
                r[f"fixation_N{N}"] = float(fix[(N, p)][a, b])
            records.append(r)
    for omitted in SETS:
        ids = [i for i, m in enumerate(MODELS) if m != omitted]
        for N in POPULATIONS:
            for pi, p in enumerate(RISKS):
                r = dict(kind="ranking", omitted=omitted or "none", N=N, p=p, beta=BETA,
                         status="failed", retained_models="|".join(MODELS[i] for i in ids))
                try:
                    R = fix[(N, p)][np.ix_(ids, ids)]
                    mass, residual, agreement = chain_mass(R)
                    r.update({f"mass_{MODELS[i]}": float(v) for i, v in zip(ids, mass)})
                    winner = MODELS[ids[int(np.argmax(mass))]]
                    opt = float(cd.opt_payoff(p))
                    r.update(status="ok", winner=winner, winner_mass=float(mass.max()),
                             target_rate=float(mass @ reach[pi, ids]), welfare=float(mass @ welfare[pi, ids]),
                             opt=opt, uniform_target_rate=float(reach[pi, ids].mean()),
                             uniform_welfare_over_opt=float(welfare[pi, ids].mean()/opt),
                             stationary_residual=residual, tree_max_error=agreement)
                    r["welfare_over_opt"] = r["welfare"] / opt
                    r["winner_changed"] = omitted is not None and winner != full[(N, p)]["winner"]
                    if omitted is None:
                        ref = sel.outcome(P[pi], reach[pi], welfare[pi],
                                          "within" if N == 6 else "across", BETA, N)
                        if not np.allclose(mass, ref["pi"], rtol=0, atol=TOL):
                            raise ValueError("full-panel masses disagree with selection.py")
                        full[(N, p)] = r
                except Exception as exc:
                    r.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                    errors.append(dict(omitted=r["omitted"], N=N, p=p, error=r["error"]))
                records.append(r)
    if len(full) == 6:
        checks = check_macros(full)
        errors += [dict(check=k, **v) for k, v in checks.items() if not v["passed"]]
    else:
        errors.append(dict(error="full-panel estimates incomplete; macro checks unavailable"))
    raw = pd.concat([cd._read_experiment(e) for e in
                     ("exp_mixed", "exp_baseline", "exp_evprobe")], ignore_index=True)
    used = raw[raw.risk_probability.astype(float).round(3).isin(RISKS)]
    invalid = int(used.n_parse_failures.astype(int).sum())
    if invalid:
        errors.append(dict(error="selected source games contain parse failures", count=invalid))
    after = source_hashes()
    if before != after:
        errors.append(dict(error="source files changed during computation"))
    counts = {k: sum(r["kind"] == k for r in records) for k in ("ranking", "entrant", "composition")}
    if counts != dict(ranking=36, entrant=60, composition=300):
        errors.append(dict(error="incomplete registered scope", counts=counts))
    manifest = dict(evidence_class="diagnostic", scope=__doc__, beta=BETA,
                    risks=RISKS, populations=POPULATIONS, omissions=SETS,
                    counts=counts, selected_games=len(used), parse_failure_count=invalid,
                    failed_rankings=sum(r["kind"] == "ranking" and r["status"] != "ok" for r in records),
                    errors=errors, macro_checks=checks, identity_max_error=identity_error,
                    identity_sign_matches=identity_signs, source_sha256=before,
                    sources_unchanged=before == after, python=platform.python_version(),
                    packages={k: importlib.metadata.version(k) for k in ("numpy", "pandas", "scipy", "egttools")})
    csv = pd.DataFrame(records).to_csv(index=False, float_format="%.17g", lineterminator="\n")
    tex = render(records, errors)
    manifest["output_sha256"] = {"review_selection.csv": hashlib.sha256(csv.encode()).hexdigest(),
                                  "s_review_selection.tex": hashlib.sha256(tex.encode()).hexdigest()}
    for name, content in (("review_selection.csv", csv), ("s_review_selection.tex", tex),
                          ("review_selection.json", json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False)+"\n")):
        (OUT / name).write_text(content, encoding="utf-8", newline="\n")
    print(pd.DataFrame([r for r in records if r["kind"] == "ranking"])[
          ["omitted", "N", "p", "status", "winner", "winner_mass", "target_rate", "welfare_over_opt", "winner_changed"]].to_string(index=False))
    print(f"Rows: {counts}; macro checks: {sum(v['passed'] for v in checks.values())}/{len(checks)}; errors: {len(errors)}")
    for error in errors:
        print(json.dumps(error, sort_keys=True))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
