"""R2/Q3 — the expected-value probe: can the models do the comparison they appear to obey?

Reviewer Q3: "Could you add a simple probe for expected-value comparison (e.g. 'Which
action has higher expected value for you at the current p?') to the comprehension
battery for open-weight models...?"

The paper's sharpest result is that two commercial models behave exactly as an
expected-value calculation prescribes while eleven others ignore p entirely. That
leaves one alternative reading open: perhaps the eleven cannot perform the comparison
at all, in which case the null is an arithmetic ceiling rather than a behavioural
finding. The revision adds a fourth probe axis, `value`, whose two questions ask for
the comparison directly (crsd/engine/comprehension.py):

    value_defect_ev  expected cash from withholding all game -> (1-p) * endowment
    value_compare    which strategy pays more on average     -> 2 / 0 / 1 at p = .1/.5/.9

Neither is answerable from the prompt: the agent has to multiply a probability by
money. That makes the cross-tabulation at the end of this script the point of the whole
exercise -- accuracy on the probe against EV-optimality in play, cell by cell:

    knows and acts            the EV models, if they also score well
    KNOWS BUT DOES NOT ACT    the strongest possible version of the paper's claim:
                              capability is there, it simply does not reach behaviour
    acts without knowing      EV-shaped play arriving by some other route
    neither                   the null is at least partly an arithmetic ceiling

Three deliberate choices:

1. GROUND TRUTH IS RECOMPUTED, not read. The script re-derives both answers from the
   game config (endowment, target, players, rounds, p) with the same closed form as
   crsd/engine/comprehension.py::_ev_compare_gt, then checks the recomputation against
   the `ground_truth` written into every log line. A mismatch is reported loudly rather
   than averaged over: it would mean the run scored itself against a different rule.

2. THE ANSWER DISTRIBUTION IS REPORTED, not just accuracy. `value_compare` has three
   possible answers and the correct one moves with p, so a model that always says
   "cooperating is better" scores 33% while performing no comparison at all. Only the
   per-risk answer mix distinguishes those two cases.

3. THE NEW CATEGORY IS AUDITED. `value` is a fourth axis alongside rules/time/state.
   Anything that groups the comprehension battery by category -- figure 4, r5's
   per-axis language table -- silently gains a group when the new run lands. The
   inventory section reports which sources carry a `value` category, so that hazard is
   visible instead of being discovered in a redrawn figure. `rules` is carried in the
   probe run as a control: if it drops against the earlier comprehension run on the
   same models, the fault is in the setup, not in the new axis.

Output: paper/revision/out/r9_ev_probe.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paper.Interface_Focus.revision._data import (OUT, RESULTS, ROOT, comprehension_categories,  # noqa: E402
                   discover_comprehension, discover_files, discover_games,
                   discover_turns, label, rel_to_root)

VALUE_CATEGORY = "value"
VALUE_QUESTIONS = ("value_defect_ev", "value_compare")
GAME_CONFIGS = ROOT / "crsd" / "configs" / "game"
# The aggregate every by-category figure and table in the paper reads.
LEGACY_COMP_CSV = RESULTS / "open_source" / "crsd_comprehension_all_models.csv"

# Fallback Milinski parameters, used only if the configs cannot be read.
FALLBACK = {"endowment": 40.0, "target": 120.0, "n_players": 6, "n_rounds": 10}


# --------------------------------------------------------------------------- #
# ground truth, recomputed from the configs
# --------------------------------------------------------------------------- #
def game_parameters() -> dict:
    """Endowment/target/players/rounds, read from the three shipped game configs.

    They are identical apart from riskProbability; if they ever stop being, the
    disagreement is reported rather than silently resolved.
    """
    seen, files = {}, []
    for name in ("low", "medium", "high"):
        p = GAME_CONFIGS / f"crsd_milinski_{name}_risk.json"
        if not p.exists():
            continue
        cfg = json.loads(p.read_text(encoding="utf-8"))
        files.append(p.name)
        seen[cfg["riskProbability"]] = {
            "endowment": float(cfg["endowment"]), "target": float(cfg["target"]),
            "n_players": int(cfg["nPlayers"]), "n_rounds": int(cfg["nRounds"]),
        }
    if not seen:
        return {**FALLBACK, "source": "fallback constants (configs not found)"}
    base = next(iter(seen.values()))
    consistent = all(v == base for v in seen.values())
    return {**base, "source": ", ".join(files),
            "configs_agree_apart_from_risk": consistent,
            "risk_levels_in_configs": sorted(seen)}


def ev_truth(p: float, g: dict) -> dict:
    """The two `value` answers at risk p, and the EV-optimal action that follows.

    Mirrors crsd/engine/comprehension.py: `keep_if_cooperate` is what is left after
    paying an equal share of the target, `ev_if_defect` is the lottery.
    """
    keep = g["endowment"] - g["target"] / g["n_players"]
    ev_defect = (1.0 - p) * g["endowment"]
    if abs(keep - ev_defect) < 1e-9:
        compare, action, group = 0, None, None
    elif keep > ev_defect:
        compare = 1
        action = g["target"] / (g["n_players"] * g["n_rounds"])
        group = g["target"]
    else:
        compare, action, group = 2, 0.0, 0.0
    return {"value_defect_ev": int(round(ev_defect)), "value_compare": compare,
            "keep_if_cooperate": keep, "ev_if_defect": ev_defect,
            "ev_action": action, "ev_group_total": group}


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #
def _pct(x) -> str:
    return "  --" if x is None else f"{x:.2f}"


def wilson(k: int, n: int, z: float = 1.959964) -> list:
    """Wilson 95% interval: the accuracies here hit 0 and 1, where normal CIs fail."""
    if n == 0:
        return [None, None]
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return [round(float(max(0.0, c - h)), 4), round(float(min(1.0, c + h)), 4)]


def welch(a, b) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return {"n_a": int(len(a)), "n_b": int(len(b)), "p": None}
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    if se == 0:
        return {"n_a": int(len(a)), "n_b": int(len(b)),
                "mean_a": float(a.mean()), "mean_b": float(b.mean()), "p": None}
    t = (b.mean() - a.mean()) / se
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    try:
        from scipy import stats
        p = float(2 * stats.t.sf(abs(t), dof))
    except Exception:                                        # noqa: BLE001
        from math import erfc, sqrt
        p = float(erfc(abs(t) / sqrt(2)))
    return {"n_a": int(len(a)), "n_b": int(len(b)), "mean_a": float(a.mean()),
            "mean_b": float(b.mean()), "t": float(t), "p": p}


def accuracy(sub: pd.DataFrame) -> dict:
    n = int(len(sub))
    if n == 0:
        return {"n": 0}
    k = int(sub["correct"].astype(bool).sum())
    pf = int(sub["parse_failed"].astype(bool).sum())
    parsed = sub[~sub["parse_failed"].astype(bool)]
    return {"n": n, "n_correct": k, "accuracy": round(k / n, 4),
            "ci95": wilson(k, n), "n_parse_failed": pf,
            "accuracy_of_parsed": (round(float(parsed["correct"].astype(bool).mean()), 4)
                                   if len(parsed) else None)}


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #
def category_inventory(files: list) -> dict:
    """Which sources carry which probe axes -- the `value` regression check.

    Counted straight off the raw lines (see _data.comprehension_categories), so the
    audit is cheap even against a full battery of several hundred thousand probes.
    """
    out = {"raw_logs": {}, "legacy_aggregate": {}}
    for f in files:
        e = out["raw_logs"].setdefault(f["experiment"],
                                       {"categories": {}, "models": [],
                                        "has_value_axis": False})
        for cat, n in f["categories"].items():
            e["categories"][cat] = e["categories"].get(cat, 0) + int(n)
        if f["model"] not in e["models"]:
            e["models"].append(f["model"])
    for e in out["raw_logs"].values():
        e["categories"] = dict(sorted(e["categories"].items()))
        e["models"].sort()
        e["has_value_axis"] = VALUE_CATEGORY in e["categories"]
    if LEGACY_COMP_CSV.exists():
        df = pd.read_csv(LEGACY_COMP_CSV)
        cats = sorted(df["category"].unique())
        out["legacy_aggregate"] = {
            "path": rel_to_root(LEGACY_COMP_CSV),
            "categories": cats,
            "has_value_axis": VALUE_CATEGORY in cats,
            "verdict": (
                "the aggregate now carries a FOURTH axis: every by-category output "
                "(figure 4, r5's per-axis table) gains a group and must be redrawn "
                "or filtered to rules/time/state"
                if VALUE_CATEGORY in cats else
                "three axes only, so the by-category figures and tables that read "
                "this file are unaffected by the new probe"),
        }
    return out


def truth_table(g: dict, risks) -> dict:
    return {str(p): {k: v for k, v in ev_truth(float(p), g).items()} for p in risks}


def check_ground_truth(val: pd.DataFrame, g: dict) -> dict:
    """Does the recomputed answer agree with what the run scored itself against?"""
    rows, bad = 0, []
    for _, r in val.iterrows():
        want = ev_truth(float(r["risk_probability"]), g).get(r["question_id"])
        if want is None:
            continue
        rows += 1
        try:
            got = int(r["ground_truth"])
        except (TypeError, ValueError):
            got = str(r["ground_truth"])
        if got != want:
            bad.append({"question_id": str(r["question_id"]),
                        "risk": float(r["risk_probability"]),
                        "logged": got, "recomputed": want})
    return {"rows_checked": rows, "n_mismatched": len(bad),
            "examples": bad[:5],
            "verdict": ("recomputed ground truth matches the log exactly"
                        if not bad else
                        "MISMATCH: the run was scored against a different rule")}


def score_value(val: pd.DataFrame) -> dict:
    out = {"by_question": {}, "by_model": {}, "by_model_risk": {}, "by_language": {}}
    for q, sub in val.groupby("question_id"):
        out["by_question"][q] = accuracy(sub)
    for m, sub in val.groupby("model"):
        out["by_model"][label(m)] = {q: accuracy(s) for q, s in
                                     sub.groupby("question_id")}
        out["by_model"][label(m)]["all_value"] = accuracy(sub)
    for (m, p), sub in val.groupby(["model", "risk_probability"]):
        out["by_model_risk"].setdefault(m, {})[str(p)] = {
            q: accuracy(s) for q, s in sub.groupby("question_id")}
    for (lg, q), sub in val.groupby(["language", "question_id"]):
        out["by_language"].setdefault(lg, {})[q] = accuracy(sub)
    return out


def answer_mix(val: pd.DataFrame, g: dict) -> dict:
    """What did they actually answer to value_compare, risk by risk?

    A model that names the same strategy at every p is not comparing anything, even
    when that constant answer is right a third of the time.
    """
    cmp_rows = val[val.question_id == "value_compare"]
    out = {}
    for m, sub in cmp_rows.groupby("model"):
        per_risk, modal = {}, {}
        for p, s in sub.groupby("risk_probability"):
            counts = s["parsed_answer"].value_counts(dropna=False)
            total = int(counts.sum())
            per_risk[str(p)] = {
                "n": total,
                "answers": {str(k): int(v) for k, v in counts.items()},
                "correct_answer": ev_truth(float(p), g)["value_compare"],
                "modal_answer": (str(counts.index[0]) if total else None),
            }
            modal[str(p)] = per_risk[str(p)]["modal_answer"]
        out[label(m)] = {
            "by_risk": per_risk,
            "modal_answer_by_risk": modal,
            "constant_across_risk": len(set(modal.values())) == 1 and len(modal) > 1,
        }
    return out


def behaviour(turns: pd.DataFrame, games: pd.DataFrame, g: dict, source: str) -> dict:
    """EV-optimal play per (model, risk), measured two ways.

    The EV-optimal action is the one the probe asks about: withhold while the lottery
    is worth more than the certain remainder, pay the equal share once it is not. At
    p = 0.5 the two are exactly equal, so both count as aligned and the cell is
    flagged as a tie rather than scored.

    `ev_aligned_rate` is the strict per-turn version: the fraction of turns taking
    exactly that action. `ev_outcome_aligned_rate` is the coarse per-game version the
    paper itself uses -- did the group end on the side of the target that expected
    value prescribes -- which does not punish a model for overshooting the equal share
    when cooperation is the right call. The cross-tabulation prefers the coarse one
    and falls back to the strict one when no games.csv accompanies the turns.
    """
    out = {"source": source, "by_model_risk": {}}
    if turns.empty:
        return out
    t = turns[~turns["parse_failed"].fillna(False).astype(bool)].copy()
    share = g["target"] / (g["n_players"] * g["n_rounds"])
    # Group on the display label, not the raw model string: two raw names can share
    # one label (the nano runs write their own model string as well as living in a
    # directory of another name), and grouping on the raw name would let the second
    # source silently overwrite the first cell instead of being pooled into it.
    t["label"] = t["model"].map(label)
    for (m, p), sub in t.groupby(["label", "risk_probability"]):
        tr = ev_truth(float(p), g)
        c = sub["contribution"].dropna()
        if tr["ev_action"] is None:
            aligned = float(c.isin([0.0, share]).mean()) if len(c) else None
        else:
            aligned = float((c == tr["ev_action"]).mean()) if len(c) else None
        out["by_model_risk"].setdefault(m, {})[str(p)] = {
            "n_turns": int(len(c)),
            "mean_contribution": round(float(c.mean()), 3) if len(c) else None,
            "ev_action": tr["ev_action"],
            "ev_aligned_rate": round(aligned, 4) if aligned is not None else None,
            "ev_outcome_aligned_rate": None,
            "reach_rate": None,
            "tie": tr["ev_action"] is None,
        }
    if games is None or games.empty:
        return out
    games = games.copy()
    games["label"] = games["model"].map(label)
    for (m, p), sub in games.groupby(["label", "risk_probability"]):
        cell = out["by_model_risk"].get(m, {}).get(str(p))
        if cell is None:
            continue
        tr = ev_truth(float(p), g)
        reach = sub["target_reached"].astype(float)
        cell["n_games"] = int(len(sub))
        cell["reach_rate"] = round(float(reach.mean()), 4)
        if tr["ev_group_total"] is None:
            cell["ev_outcome_aligned_rate"] = 1.0          # indifferent: either is fine
        else:
            want = 1.0 if tr["ev_group_total"] == g["target"] else 0.0
            cell["ev_outcome_aligned_rate"] = round(float((reach == want).mean()), 4)
    return out


def crosstab(scores: dict, beh: dict, threshold: float = 0.5) -> dict:
    """Probe accuracy against EV-optimal play, one cell per (model, risk)."""
    cells, quad = [], {"knows_and_acts": 0, "knows_but_does_not_act": 0,
                       "acts_without_knowing": 0, "neither": 0, "tie_cells": 0}
    for m, per_risk in scores.get("by_model_risk", {}).items():
        for p, qs in per_risk.items():
            acc = qs.get("value_compare", {}).get("accuracy")
            b = beh.get("by_model_risk", {}).get(m, {}).get(p)
            if acc is None or b is None:
                continue
            coarse = b.get("ev_outcome_aligned_rate")
            rate = coarse if coarse is not None else b["ev_aligned_rate"]
            if rate is None:
                continue
            cell = {"model": m, "risk": float(p), "probe_accuracy": acc,
                    "behaviour_rate": rate,
                    "behaviour_measure": ("game outcome vs EV prescription" if coarse
                                          is not None else "exact EV action per turn"),
                    "ev_action_rate": b["ev_aligned_rate"]}
            if b["tie"]:
                quad["tie_cells"] += 1
                cell["quadrant"] = "tie (EV is indifferent at this p)"
                cells.append(cell)
                continue
            knows, acts = acc >= threshold, rate >= threshold
            cell["quadrant"] = ("knows_and_acts" if knows and acts else
                                "knows_but_does_not_act" if knows else
                                "acts_without_knowing" if acts else "neither")
            quad[cell["quadrant"]] += 1
            cells.append(cell)
    scored = [c for c in cells if not c["quadrant"].startswith("tie")]
    r = None
    if len(scored) >= 3:
        x = np.array([c["probe_accuracy"] for c in scored])
        y = np.array([c["behaviour_rate"] for c in scored])
        if x.std() > 0 and y.std() > 0:
            r = round(float(np.corrcoef(x, y)[0, 1]), 3)
    return {"threshold": threshold, "quadrants": quad, "cells": cells,
            "pearson_r_probe_vs_behaviour": r,
            "reading": ("a high count in knows_but_does_not_act is the strong result: "
                        "the comparison is within reach and still does not drive play")}


def within_game_link(val: pd.DataFrame, turns: pd.DataFrame, source: str) -> dict:
    """Inside one model: do the games whose probe was answered correctly play differently?

    The probe is put to one seat (probePlayers = [0]) at the rules checkpoints, so the
    probed player's own contributions in that same game are the matching behaviour.
    Only meaningful when the turns come from the probe run itself; on the fallback
    source the join lands on a different run that merely shares the game ids.
    """
    out = {}
    if turns.empty or val.empty:
        return {"note": "needs both comprehension.jsonl and turns.jsonl from the run"}
    cmp_rows = val[(val.question_id == "value_compare") & (~val.parse_failed.astype(bool))]
    for m, sub in cmp_rows.groupby("model"):
        tsub = turns[turns.model == m]
        if tsub.empty:
            continue
        # one verdict per game: correct if the probed seat got it right every time
        verdict = sub.groupby(["game_id", "player_index"])["correct"] \
                     .apply(lambda s: bool(s.astype(bool).all())).reset_index()
        verdict["player"] = "Player_" + (verdict["player_index"] + 1).astype(int).astype(str)
        own = tsub.merge(verdict[["game_id", "player", "correct"]],
                         on=["game_id", "player"], how="inner")
        if own.empty:
            continue
        a = own[~own["correct"]]["contribution"].dropna()
        b = own[own["correct"]]["contribution"].dropna()
        res = welch(a, b)
        out[label(m)] = {
            "mean_contribution_probe_wrong": round(float(a.mean()), 3) if len(a) else None,
            "mean_contribution_probe_right": round(float(b.mean()), 3) if len(b) else None,
            "test": res,
        }
    if not out:
        return {"note": "no game_id overlap between probes and turns"}
    return {"source": source, "by_model": out}


def rules_control(comp: pd.DataFrame, probe_experiment: str) -> dict:
    """Rules accuracy in the probe run vs the earlier battery, same models."""
    if comp.empty:
        return {}
    rules = comp[comp.category == "rules"]
    new = rules[rules.experiment == probe_experiment]
    old = rules[rules.experiment != probe_experiment]
    if new.empty or old.empty:
        return {"note": "no rules axis on both sides to compare"}
    out = {}
    for m in sorted(set(new.model) & set(old.model)):
        n_new, n_old = new[new.model == m], old[old.model == m]
        out[label(m)] = {
            "rules_accuracy_probe_run": round(float(n_new["correct"].astype(bool).mean()), 4),
            "rules_accuracy_earlier_run": round(float(n_old["correct"].astype(bool).mean()), 4),
        }
        out[label(m)]["delta_pp"] = round(
            (out[label(m)]["rules_accuracy_probe_run"]
             - out[label(m)]["rules_accuracy_earlier_run"]) * 100, 2)
    return out


# --------------------------------------------------------------------------- #
def main() -> None:
    g = game_parameters()
    comp = discover_comprehension()
    val = comp[comp.category == VALUE_CATEGORY].copy() if not comp.empty \
        else pd.DataFrame()

    report = {
        "experiment": "exp_evprobe (probe axis `value`)",
        "game_parameters": g,
        "expected_value_truth_table": truth_table(g, (0.1, 0.5, 0.9)),
        "category_inventory": category_inventory(comprehension_categories()),
        "evprobe_files_found": [rel_to_root(p) for p, _, _ in
                                discover_files("comprehension.jsonl", "exp_evprobe")],
    }

    print("== the comparison the probe asks about, recomputed from the game configs ==")
    print(f"   ({g['source']})")
    for p, d in report["expected_value_truth_table"].items():
        tie = " (tie)" if d["value_compare"] == 0 else ""
        print(f"  p={p:<4} withhold pays {d['ev_if_defect']:5.1f} on average, "
              f"paying the share leaves {d['keep_if_cooperate']:5.1f} for certain "
              f"-> answer {d['value_compare']}{tie}, EV action "
              f"{d['ev_action'] if d['ev_action'] is not None else 'either'}")

    print("\n== probe axes present in the logs (the `value` regression check) ==")
    for exp, d in report["category_inventory"]["raw_logs"].items():
        cats = ", ".join(f"{c}={n}" for c, n in d["categories"].items())
        print(f"  {exp:20s} {cats}")
    lg = report["category_inventory"].get("legacy_aggregate")
    if lg:
        print(f"  {lg['path']}")
        print(f"    categories {lg['categories']} -> {lg['verdict']}")

    if val.empty:
        report["status"] = "awaiting data"
        report["note"] = (
            "No comprehension row carries category='value' anywhere under results/. "
            "Unpack evprobe_results.zip into results/raw/ and re-run; the loader "
            "accepts results/raw/crsd_results/<model>/exp_evprobe/ as written by the "
            "notebook, and any other layout that keeps the exp_evprobe directory.")
        # the behaviour half can be shown now, so the cross-tabulation is half-ready
        bt, bg = discover_turns("exp_baseline"), discover_games("exp_baseline")
        beh = behaviour(bt, bg, g,
                        "exp_baseline (stand-in until the probe run lands)")
        report["behaviour_ready"] = beh
        (OUT / "r9_ev_probe.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        print("\n== no `value` probes found -- nothing to score yet ==")
        print("  " + report["note"].replace(". ", ".\n  "))
        print("\n== the behaviour half of the cross-tabulation, already measurable ==")
        print("   (action = share of turns taking the exact EV action; "
              "outcome = share of games landing on the EV side of the target)")
        for m, per_risk in sorted(beh["by_model_risk"].items()):
            cells = "  ".join(f"p={p}: {_pct(d['ev_aligned_rate'])}/"
                              f"{_pct(d['ev_outcome_aligned_rate'])}"
                              f"{'*' if d['tie'] else ''}"
                              for p, d in sorted(per_risk.items()))
            print(f"  {m:24s} {cells}")
        print("   * p=0.5 is an EV tie; both actions count as aligned there.")
        print(f"\nwrote {OUT / 'r9_ev_probe.json'}")
        return

    report["status"] = "scored"
    report["value_experiments"] = sorted(val["experiment"].unique())
    probe_exp = val["experiment"].mode().iloc[0]
    report["ground_truth_check"] = check_ground_truth(val, g)
    report["accuracy"] = score_value(val)
    report["answer_mix"] = answer_mix(val, g)
    report["rules_control"] = rules_control(comp, probe_exp)

    turns, games = discover_turns(probe_exp), discover_games(probe_exp)
    src = probe_exp
    if turns.empty:
        turns, games = discover_turns("exp_baseline"), discover_games("exp_baseline")
        src = "exp_baseline (the probe run left no turns.jsonl)"
    beh = behaviour(turns, games, g, src)
    report["behaviour"] = beh
    report["crosstab"] = crosstab(report["accuracy"], beh)
    report["within_game"] = within_game_link(val, turns, src)

    (OUT / "r9_ev_probe.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")

    gt = report["ground_truth_check"]
    print(f"\n== ground truth: {gt['verdict']} "
          f"({gt['rows_checked']} rows, {gt['n_mismatched']} mismatched) ==")

    print("\n== accuracy on the value axis ==")
    for q, d in report["accuracy"]["by_question"].items():
        print(f"  {q:18s} {d['accuracy']*100:6.2f}%  "
              f"[{d['ci95'][0]*100:.1f}, {d['ci95'][1]*100:.1f}]  n={d['n']}  "
              f"parse-fail {d['n_parse_failed']}")
    print("\n  per model:")
    for m, d in report["accuracy"]["by_model"].items():
        parts = "  ".join(f"{q.replace('value_', ''):11s} {d[q]['accuracy']*100:6.2f}%"
                          for q in VALUE_QUESTIONS if q in d)
        print(f"    {m:24s} {parts}")

    print("\n== what they answered to value_compare (correct answer moves with p) ==")
    for m, d in report["answer_mix"].items():
        modal = "  ".join(f"p={p}: said {v} (right: "
                          f"{d['by_risk'][p]['correct_answer']})"
                          for p, v in sorted(d["modal_answer_by_risk"].items()))
        flag = "   <- same answer at every p: no comparison performed" \
            if d["constant_across_risk"] else ""
        print(f"  {m:24s} {modal}{flag}")

    if report["rules_control"] and "note" not in report["rules_control"]:
        print("\n== rules control: did the probe run break anything? ==")
        for m, d in report["rules_control"].items():
            print(f"  {m:24s} {d['rules_accuracy_earlier_run']*100:6.2f}% -> "
                  f"{d['rules_accuracy_probe_run']*100:6.2f}%  "
                  f"({d['delta_pp']:+.2f} pp)")

    print(f"\n== cross-tabulation: probe accuracy vs EV-optimal play ==")
    print(f"   (behaviour from {beh['source']})")
    ct = report["crosstab"]
    for c in sorted(ct["cells"], key=lambda c: (c["model"], c["risk"])):
        print(f"  {c['model']:24s} p={c['risk']:<4} probe {c['probe_accuracy']*100:6.2f}%"
              f"   plays EV-optimal {c['behaviour_rate']*100:6.2f}%"
              f" (exact action {c['ev_action_rate']*100:6.2f}%)   {c['quadrant']}")
    print("  quadrant counts: " + ", ".join(f"{k}={v}" for k, v in
                                            ct["quadrants"].items()))
    print(f"  corr(probe accuracy, EV-aligned play) = "
          f"{ct['pearson_r_probe_vs_behaviour']}")

    wg = report["within_game"]
    if "note" not in wg:
        print("\n== within model: games where the probe was answered correctly ==")
        print(f"   (own contributions of the probed seat, from {wg['source']})")
        for m, d in wg["by_model"].items():
            p = d["test"].get("p")
            print(f"  {m:24s} wrong {d['mean_contribution_probe_wrong']}  "
                  f"right {d['mean_contribution_probe_right']}  "
                  f"P={p if p is None else round(p, 4)}")
    print(f"\nwrote {OUT / 'r9_ev_probe.json'}")


if __name__ == "__main__":
    main()
