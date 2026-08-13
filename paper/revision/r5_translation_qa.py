"""R1/Q2 — Vietnamese translation QA, from the comprehension battery.

Reviewer Q2: "For Vietnamese, what translation/validation procedures were used? Can you
provide back-translated examples and/or minimal QA evidence that numerical cues and key
conditionals were faithfully preserved?"

A back-translation table is prose evidence and belongs in the supplement. This script
supplies the *behavioural* half, which is stronger, because it tests the translation
through the agents rather than through a second translator: if the Vietnamese prompt
had corrupted a number, a rule or a conditional, the agents reading it would answer
questions about that number, rule or conditional worse. The comprehension battery
already measures exactly that, per question, in both languages, against the engine's
ground truth.

Three checks:

1. RULE AND NUMBER FIDELITY. Per-question accuracy in each language on the Rules axis,
   which is where the endowment, target, action set, round count and catastrophe
   probability live. A faithful translation shows no language gap here.

2. THE CONDITIONAL. `rules_risk` asks the agent to state the catastrophe probability of
   the game it is in — the one number carried by the conditional clause the reviewer is
   worried about ("if the group does not reach 120, then with probability p ..."). We
   report it separately.

3. WHERE THE LANGUAGE GAP ACTUALLY IS. The same table shows the gap concentrated on the
   State axis, i.e. on arithmetic the agent must perform, not on anything the prompt
   states. That localises the Vietnamese effect to computation rather than to
   comprehension of the translated text.

Also emits a prompt-geometry audit (line counts, placeholder parity, number parity)
between crsd_en.txt and crsd_vn.txt, which catches a mistranslated or dropped numeric
placeholder mechanically.

Output: paper/revision/out/r5_translation_qa.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _data import OUT, RESULTS, label                 # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "crsd" / "prompts"
COMP = RESULTS / "open_source" / "crsd_comprehension_all_models.csv"


def prompt_audit() -> dict:
    """Mechanical parity check between the English and Vietnamese templates."""
    en = (PROMPTS / "crsd_en.txt").read_text(encoding="utf-8")
    vn = (PROMPTS / "crsd_vn.txt").read_text(encoding="utf-8")

    ph = re.compile(r"\{([A-Za-z]+)\}")
    en_ph = sorted(ph.findall(en))
    vn_ph = sorted(ph.findall(vn))

    # numerals written literally in the template (there should be none that carry
    # game parameters -- every game number must arrive through a placeholder)
    lit = re.compile(r"(?<![\w{])\d+(?![\w}])")
    return {
        "lines_en": len(en.strip().splitlines()),
        "lines_vn": len(vn.strip().splitlines()),
        "placeholders_en": len(en_ph),
        "placeholders_vn": len(vn_ph),
        "placeholder_multiset_identical": en_ph == vn_ph,
        "placeholders_only_in_en": sorted(set(en_ph) - set(vn_ph)),
        "placeholders_only_in_vn": sorted(set(vn_ph) - set(en_ph)),
        "literal_numbers_en": lit.findall(en),
        "literal_numbers_vn": lit.findall(vn),
        "answer_token_identical": ("CONTRIBUTION:" in en) and ("CONTRIBUTION:" in vn),
    }


def comprehension_by_language() -> dict:
    df = pd.read_csv(COMP)
    # weight by number of probes, not by cell, so a model with more probes is not
    # under-counted; accuracy in the csv is already n_correct / n
    df["w"] = df["n"]

    def acc(sub: pd.DataFrame) -> float:
        return float(sub["n_correct"].sum() / sub["n"].sum())

    out = {}
    for cat, sub in df.groupby("category"):
        by_lang = {lang: round(acc(s) * 100, 2) for lang, s in sub.groupby("language")}
        out[cat] = {"by_language_pct": by_lang,
                    "gap_pp": round(by_lang.get("en", float("nan"))
                                    - by_lang.get("vn", float("nan")), 2),
                    "n_probes": int(sub["n"].sum())}

    per_q = {}
    for qid, sub in df.groupby("question_id"):
        by_lang = {lang: round(acc(s) * 100, 2) for lang, s in sub.groupby("language")}
        per_q[qid] = {"category": sub["category"].iloc[0],
                      "by_language_pct": by_lang,
                      "gap_pp": round(by_lang.get("en", float("nan"))
                                      - by_lang.get("vn", float("nan")), 2),
                      "n_probes": int(sub["n"].sum())}

    rules = df[df.category == "rules"]
    per_model_rules = {}
    for model, sub in rules.groupby("model"):
        by_lang = {lang: round(acc(s) * 100, 2) for lang, s in sub.groupby("language")}
        per_model_rules[label(model)] = {
            "by_language_pct": by_lang,
            "gap_pp": round(by_lang.get("en", float("nan"))
                            - by_lang.get("vn", float("nan")), 2)}

    return {"by_category": out, "by_question": per_q,
            "rules_by_model": per_model_rules}


def tokenisation_audit(sample_per_cell: int = 40) -> dict:
    """How much longer is the Vietnamese prompt, in tokens the model actually sees?

    The reviewer raises tokenisation as a possible confound of the language effect.
    We measure it on the *rendered* prompts logged in turns.jsonl (not the template),
    matched by round so the comparison is like for like. cl100k/o200k are proxies for
    the hosted tokenisers, which are not public; the point is the ratio, not the
    absolute count.
    """
    try:
        import tiktoken
    except Exception:
        return {"note": "tiktoken unavailable"}

    enc = tiktoken.get_encoding("o200k_base")
    out = {}
    for model_dir in sorted((RESULTS / "frontier").glob("*/exp_baseline/turns.jsonl")):
        counts = {"en": [], "vn": []}
        rounds = {"en": [], "vn": []}
        with open(model_dir, encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                lang = d.get("language")
                if lang not in counts or len(counts[lang]) >= sample_per_cell * 10:
                    continue
                counts[lang].append(len(enc.encode(d["prompt"])))
                rounds[lang].append(d.get("round"))
        if not counts["en"] or not counts["vn"]:
            continue
        df = pd.DataFrame({
            "lang": ["en"] * len(counts["en"]) + ["vn"] * len(counts["vn"]),
            "round": rounds["en"] + rounds["vn"],
            "tok": counts["en"] + counts["vn"],
        })
        matched = df.groupby(["round", "lang"])["tok"].mean().unstack()
        matched = matched.dropna()
        if matched.empty:
            continue
        out[label(model_dir.parts[-3])] = {
            "mean_tokens_en": round(float(matched["en"].mean()), 1),
            "mean_tokens_vn": round(float(matched["vn"].mean()), 1),
            "vn_over_en": round(float((matched["vn"] / matched["en"]).mean()), 3),
            "rounds_matched": int(len(matched)),
        }
    return out


def main() -> None:
    report = {"prompt_audit": prompt_audit(),
              "comprehension": comprehension_by_language(),
              "tokenisation": tokenisation_audit()}
    (OUT / "r5_translation_qa.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    pa = report["prompt_audit"]
    print("== template parity, crsd_en.txt vs crsd_vn.txt ==")
    print(f"  lines                     {pa['lines_en']} vs {pa['lines_vn']}")
    print(f"  placeholder count         {pa['placeholders_en']} vs {pa['placeholders_vn']}")
    print(f"  placeholder sets identical {pa['placeholder_multiset_identical']}")
    if pa["placeholders_only_in_en"] or pa["placeholders_only_in_vn"]:
        print(f"    only in EN: {pa['placeholders_only_in_en']}")
        print(f"    only in VN: {pa['placeholders_only_in_vn']}")
    print(f"  literal numbers in template  EN={pa['literal_numbers_en']} "
          f"VN={pa['literal_numbers_vn']}")

    print("\n== comprehension accuracy by axis and language ==")
    for cat, d in report["comprehension"]["by_category"].items():
        b = d["by_language_pct"]
        print(f"  {cat:8s} en {b.get('en'):6.2f}%  vn {b.get('vn'):6.2f}%  "
              f"gap {d['gap_pp']:+6.2f} pp  (n={d['n_probes']})")

    print("\n== the Rules questions, one by one (this is the translation test) ==")
    q = report["comprehension"]["by_question"]
    for qid, d in sorted(q.items(), key=lambda kv: (kv[1]["category"], kv[0])):
        if d["category"] != "rules":
            continue
        b = d["by_language_pct"]
        print(f"  {qid:22s} en {b.get('en'):6.2f}%  vn {b.get('vn'):6.2f}%  "
              f"gap {d['gap_pp']:+6.2f} pp")

    print("\n== rules_target, the one Rules question with a gap, by model ==")
    dfq = pd.read_csv(COMP)
    tq = dfq[dfq.question_id == "rules_target"]
    for model, sub in tq.groupby("model"):
        b = {lang: round(float(s["n_correct"].sum() / s["n"].sum()) * 100, 2)
             for lang, s in sub.groupby("language")}
        print(f"  {label(model):22s} en {b.get('en'):6.2f}%  vn {b.get('vn'):6.2f}%")

    print("\n== prompt length in tokens (o200k proxy), matched by round ==")
    for m, d in report["tokenisation"].items():
        print(f"  {m:24s} en {d['mean_tokens_en']:7.1f}  vn {d['mean_tokens_vn']:7.1f}  "
              f"ratio {d['vn_over_en']:.3f}")

    print("\n== largest language gaps anywhere in the battery ==")
    worst = sorted(q.items(), key=lambda kv: -abs(kv[1]["gap_pp"]))[:6]
    for qid, d in worst:
        b = d["by_language_pct"]
        print(f"  {qid:22s} [{d['category']:5s}] en {b.get('en'):6.2f}%  "
              f"vn {b.get('vn'):6.2f}%  gap {d['gap_pp']:+6.2f} pp")


if __name__ == "__main__":
    main()
