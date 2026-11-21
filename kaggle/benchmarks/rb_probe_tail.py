# %% =====================  REBUTTAL PROBES (appended by plan/scripts/make_rb_probe.py)  ===
# This block is appended to the helper part of crg_task_server.py (everything above the
# SWEEP section), so every prompt below is rendered by the SAME _assemble() and decided
# by the SAME decide() that played the 3,950 recorded games. Nothing about the rules,
# the wording or the parser is retyped here.
#
# Three single-call designs, no game is played and no answer enters any game:
#   cf      same-history counterfactual: the exact base decision prompt at a fixed round,
#           only the partners' past moves differ between histories (focal seat random)
#   explain the base decision prompt with the tail asking for 2-4 sentences of reasons
#           before the CONTRIBUTION line
#   recog   the decision prompt (base or neutral wording) with the tail replaced by a
#           question asking which known game or experiment the situation resembles
import csv as _rb_csv
import hashlib as _rb_hashlib
import random as _rb_random

RB_SEED_OFFSET = 900_000_000
RB_SAMPLES_CF = int(os.environ.get("CRG_RB_SAMPLES_CF", "10"))
RB_SAMPLES_EX = int(os.environ.get("CRG_RB_SAMPLES_EX", "5"))
RB_SAMPLES_RC = int(os.environ.get("CRG_RB_SAMPLES_RC", "5"))

_RB_EXPLAIN_TAIL_EN = (
    "Now decide your contribution for round {currentRound}. Allowed choices: "
    "{contributionOptions}.\n"
    "First explain the reasons for your decision in two to four sentences. Then give "
    "your decision as a final line:\n"
    "CONTRIBUTION: <one of {contributionOptions}>\n"
)
_RB_RECOG_Q = (
    "Does the situation described above correspond to a game or experiment that is "
    "known from the research literature? If so, name it and say in one sentence what "
    "it is usually used to study. If not, say so."
)


def _rb_history(hid, focal):
    """(current_round, history) with the focal seat contributing 2 every past round."""
    def rounds(n, partner_moves):
        h = []
        for r in range(n):
            row = [partner_moves[r]] * N_PLAYERS
            row[focal] = 2
            h.append(row)
        return h
    if hid == "r1":
        return 1, []
    if hid == "fair":
        return 6, rounds(5, [2] * 5)
    if hid == "generous":
        return 6, rounds(5, [4] * 5)
    if hid == "settled":
        return 7, rounds(6, [4] * 6)
    if hid == "defect":
        return 6, rounds(5, [0] * 5)
    if hid == "drop":
        return 6, rounds(5, [2, 2, 2, 0, 0])
    raise ValueError(hid)


def _rb_items():
    """Every call of this run, fixed before the first request."""
    items = []
    k = 0
    for hid in ("r1", "fair", "generous", "settled", "defect", "drop"):
        for risk in (0.1, 0.9):
            for s in range(RB_SAMPLES_CF):
                items.append(dict(kind="cf", hid=hid, risk=risk, sample=s, tmpl="baseline", k=k))
                k += 1
    for hid in ("r1", "fair", "settled"):
        for risk in (0.0, 0.1, 0.9):
            for s in range(RB_SAMPLES_EX):
                items.append(dict(kind="explain", hid=hid, risk=risk, sample=s, tmpl="baseline", k=k))
                k += 1
    for tmpl in ("wording", "baseline"):
        for risk in (0.1, 0.9):
            for s in range(RB_SAMPLES_RC):
                items.append(dict(kind="recog", hid="r1", risk=risk, sample=s, tmpl=tmpl, k=k))
                k += 1
    if IS_PUSH_VALIDATION:
        items = [items[0], next(i for i in items if i["kind"] == "explain"),
                 next(i for i in items if i["kind"] == "recog")]
    for it in items:
        rng = _rb_random.Random(1000003 * it["k"] + 17)
        it["focal"] = rng.randrange(N_PLAYERS)
        it["seed"] = (RB_SEED_OFFSET + 7919 * it["k"]) % SAMPLING_SEED_MOD
    return items


def _rb_prompt(it):
    rnd, hist = _rb_history(it["hid"], it["focal"])
    base = TEMPLATE_SETS[it["tmpl"]]["en"]
    if it["kind"] == "cf":
        tmpl = base
        q = ""
    elif it["kind"] == "explain":
        if base.count(_DECISION_TAIL_EN) != 1:
            raise SystemExit("explain tail: decision tail not found exactly once")
        tmpl = base.replace(_DECISION_TAIL_EN, _RB_EXPLAIN_TAIL_EN)
        q = ""
    else:
        tmpl = _to_probe_template(base)
        q = _RB_RECOG_Q
    return _assemble(tmpl, "en", it["focal"], rnd, hist, it["risk"], question_text=q), rnd, hist


def _rb_one(it):
    prompt, rnd, hist = _rb_prompt(it)
    ctx = {"kind": it["kind"], "hid": it["hid"], "risk": it["risk"], "k": it["k"]}
    row = dict(item=it["k"], kind=it["kind"], history=it["hid"], risk=it["risk"],
               sample=it["sample"], template=it["tmpl"], focal_seat=it["focal"] + 1,
               round=rnd, pool_before=sum(sum(r) for r in hist), model=MODEL,
               prompt_sha=_rb_hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16])
    if it["kind"] in ("cf", "explain"):
        text, value, failed, ti, to, cost = decide(None, prompt, it["seed"], ctx=ctx)
        row.update(raw_response=text, value=value, parse_failed=int(bool(failed)),
                   tok_in=ti, tok_out=to, cost_nano=cost)
    else:
        text, usage = _call_llm(None, prompt, it["seed"], ctx=ctx)
        m = re.findall(r"^\s*ANSWER\s*:\s*(.+)$", text or "", flags=re.IGNORECASE | re.MULTILINE)
        row.update(raw_response=text, value=(m[-1].strip() if m else ""),
                   parse_failed=int(not m), tok_in=usage.input_tokens or 0,
                   tok_out=usage.output_tokens or 0,
                   cost_nano=usage.total_cost_nanodollars or 0)
    sys.stdout.write("[RB_REC] " + json.dumps(row, ensure_ascii=True, default=str) + "\n")
    sys.stdout.flush()
    return row


@kbench.task(
    name="collective-risk-baseline-srv",
    description="Rebuttal probes for the CRG panel: same-history counterfactual "
                "decisions, explained decisions, game-recognition question. Single calls.",
)
def collective_risk_baseline(llm) -> dict:
    global _LLM
    _LLM = llm
    model_tag = re.sub(r"[^A-Za-z0-9._-]+", "-", MODEL)
    out_dir = Path(os.environ.get("CRG_OUT", f"results/frontier/{model_tag}/exp_rb_probe"))
    out_dir.mkdir(parents=True, exist_ok=True)
    items = _rb_items()
    _emit(_TAG_START, {"n_items": len(items), "model": MODEL})
    rows, errors = [], []
    from concurrent.futures import ThreadPoolExecutor as _TPE
    with _TPE(max_workers=max(1, _CONCURRENCY)) as pool:
        futs = [pool.submit(_rb_one, it) for it in items]
        for it, f in zip(items, futs):
            try:
                rows.append(f.result())
            except Exception as exc:
                errors.append({"k": it["k"], "err": _clip(exc)})
                _emit_error("rb_item_failed", str(exc), fatal=False, ctx={"k": it["k"]})
    rows.sort(key=lambda r: r["item"])
    cols = list(rows[0].keys()) if rows else ["item"]
    with open(out_dir / "games.csv", "w", newline="", encoding="utf-8") as fh:
        w = _rb_csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(out_dir / "probes.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=True, default=str) + "\n")
    pf = sum(r["parse_failed"] for r in rows if r["kind"] != "recog")
    _emit(_TAG_DONE, {"status": "ok" if not errors else "partial", "n_games": len(rows),
                      "failed_games": len(errors), "failed_cells": errors[:5],
                      "parse_failed": pf, "model": MODEL})
    kbench.assertions.assert_equal(0, len(errors), expectation="Every probe item returned")
    return {"n_items": len(rows), "parse_failed_decisions": pf, "errors": len(errors)}


if os.environ.get("CRG_SKIP_RUN") != "1":
    collective_risk_baseline.run(kbench.llm)
