"""Render the in-game questions verbatim for the supplementary material.

Run from the repository root:
    python paper/AAMAS/supplement/make_questions.py

Writes paper/AAMAS/supplement/questions.tex: (i) the full prompt the questioned seat
receives for one question, rendered for an example state, and (ii) a table of all ten
questions as asked, with label, answer format and the correct answer at each risk level.

The text comes from the task that produced the data (kaggle/benchmarks/crg_task_server.py),
imported offline with the question condition switched on, so the supplement cannot drift
from what the models were asked. Every rendered question text is asserted equal to the text
recorded with the answers, and every correct answer from the program's ground-truth
function is asserted equal to the ground truth recorded with the answers. No model is called.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
ANALYSIS = REPO / "paper" / "AAMAS" / "analysis"
TASK = REPO / "kaggle" / "benchmarks" / "crg_task_server.py"
OUT = HERE / "questions.tex"
for path in (HERE, ANALYSIS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import crsd_data as cd  # noqa: E402
import supp_probes as sp  # noqa: E402
from make_prompts import esc  # noqa: E402

SOURCE = "paper/AAMAS/supplement/make_questions.py"
RISKS = (0.1, 0.5, 0.9)
ROUNDS = (1, 5, 10)
# The question condition as it was run: base prompt, English, rule and value questions,
# first seat, rounds 1, 5 and 10.
TASK_ENV = {"CRG_SKIP_RUN": "1", "CRG_LANGS": "en", "CRG_TEMPLATE": "baseline",
            "CRG_PROBE": "rules,value", "CRG_PROBE_ROUNDS": "1,5,10", "CRG_PROBE_SEATS": "0"}
# Example state: seat 1, round 5, p = 0.9, four rounds of history.
EXAMPLE_HISTORY = [[2, 2, 2, 2, 4, 2], [2, 0, 2, 2, 4, 2], [2, 2, 2, 2, 2, 2], [4, 2, 2, 0, 2, 2]]
STATE = dict(language="en", player_index=0, current_round=5, history=EXAMPLE_HISTORY, risk=0.9)
EXAMPLE_QUESTION = "value_compare"

FORMAT = {"int": "A number", "int_set": "A list of numbers"}
FORMAT_OVERRIDE = {"value_compare": "A code: 1, 2 or 0"}
CODE_NAME = {1: "1 (A)", 2: "2 (B)", 0: "0 (equal)"}


def load_task():
    saved = {k: os.environ.get(k) for k in TASK_ENV}
    here = os.getcwd()
    os.environ.update(TASK_ENV)
    os.chdir(tempfile.mkdtemp())        # the task decorator writes a .task.json into CWD
    try:
        spec = importlib.util.spec_from_file_location("crg_supp_questions", TASK)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        os.chdir(here)
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def history_before(round_no: int):
    return [list(r) for r in (EXAMPLE_HISTORY * 3)[: round_no - 1]]


def canon(value):
    """One comparable form for a ground truth: a sorted tuple for a set of numbers (the
    answer file stores it as the text of a list), an int otherwise."""
    if isinstance(value, str):
        value = ast.literal_eval(value)
    if isinstance(value, (set, list, tuple)):
        return tuple(sorted(int(v) for v in value))
    if isinstance(value, bool) or float(value) != int(value):
        raise AssertionError(f"unexpected ground truth {value!r}")
    return int(value)


def check_against_data(mod) -> dict:
    """Assert the program's questions and ground truth match the recorded answers.
    Returns {question id: {p: correct answer}}."""
    probes = cd.load_probes()
    if list(mod.PROBE_ROUNDS) != list(ROUNDS) or list(mod.PROBE_SEATS) != [0]:
        raise AssertionError(f"task asks rounds {mod.PROBE_ROUNDS}, seats {mod.PROBE_SEATS}")
    if sorted(set(probes["round"])) != list(ROUNDS) or set(probes["player_index"]) != {0}:
        raise AssertionError("recorded answers come from other rounds or seats")
    for p in RISKS:
        prefix = mod.game_name(p) + "__"
        rows = probes[probes["risk_probability"] == p]
        if not rows["game_id"].str.startswith(prefix).all():
            raise AssertionError(f"p={p}: recorded games are not from the base question condition")
    for r in ROUNDS:
        ids = [q.id for q, _ in mod.probe_items(r, history_before(r), 0)]
        if ids != sp.QUESTIONS:
            raise AssertionError(f"round {r}: program asks {ids}, tables assume {sp.QUESTIONS}")

    truth = {}
    for qid in sp.QUESTIONS:
        q = mod.PROBE_REGISTRY_BY_ID[qid]
        rec = probes[probes["question_id"] == qid]
        texts = set(rec["question_text"])
        rendered = {q.render(p, history_before(r), r, 0, {}) for p in RISKS for r in ROUNDS}
        if len(rendered) != 1 or texts != rendered:
            raise AssertionError(f"{qid}: rendered text differs from the recorded text")
        if set(rec["category"]) != {q.category} or set(rec["answer_kind"]) != {q.answer_kind}:
            raise AssertionError(f"{qid}: category or answer kind differs from the record")
        truth[qid] = {}
        for p in RISKS:
            prog = {canon(q.ground_truth(p, history_before(r), r, 0, {})) for r in ROUNDS}
            data = {canon(v) for v in rec.loc[rec["risk_probability"] == p, "ground_truth"]}
            if len(prog) != 1:
                raise AssertionError(f"{qid} p={p}: ground truth varies with the round")
            if data != prog:
                raise AssertionError(f"{qid} p={p}: program says {prog}, data say {data}")
            truth[qid][p] = next(iter(prog))
    return truth


def answer_text(qid: str, value) -> str:
    if isinstance(value, tuple):
        return ", ".join(str(v) for v in value)
    if qid == "value_compare":
        return CODE_NAME[int(value)]
    return str(value)


def prompt_box(mod) -> str:
    qtext = mod.PROBE_REGISTRY_BY_ID[EXAMPLE_QUESTION].render(
        STATE["risk"], STATE["history"], STATE["current_round"], STATE["player_index"], {})
    probe = mod.assemble_probe_prompt(question_text=qtext, **STATE)
    decision = mod.assemble_prompt(**STATE)
    head = decision.split("Now decide your contribution")[0]
    if not probe.startswith(head) or head == decision:
        raise AssertionError("the question prompt does not share the decision prompt's text")
    tail_start = probe.index("Now answer the following question")
    if probe[:tail_start] != head:
        raise AssertionError("text between the rules and the question tail differs")
    out = []
    in_tail = False
    for line in probe.split("\n"):
        if line.startswith("Now answer the following question"):
            in_tail = True
        body = esc(line)
        if in_tail and body.strip():
            body = r"\textbf{" + body + "}"
        out.append(body if body.strip() else r"\vspace{2pt}")
    while out and out[-1] == r"\vspace{2pt}":
        out.pop()
    if not in_tail or qtext not in probe:
        raise AssertionError("question tail missing from the rendered prompt")
    return "\\begin{promptbox}\n" + "\\par\n".join(out) + "\n\\end{promptbox}\n"


def question_table(mod, truth: dict) -> str:
    head = " & ".join(f"$p={p:g}$" for p in RISKS)
    lines = [
        "\\begin{center}",
        "\\small",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\begin{tabular}{@{}p{0.15\\linewidth}p{0.45\\linewidth}p{0.12\\linewidth}lll@{}}",
        "\\toprule",
        "Label & Question as asked & Answer & \\multicolumn{3}{l}{Correct answer} \\tabularnewline",
        "\\cmidrule(l){4-6}",
        f" & & format & {head} \\tabularnewline",
        "\\midrule",
    ]
    for group, ids in (("Rule questions", sp.RULES), ("Value questions", sp.VALUES)):
        if group != "Rule questions":
            lines.append("\\midrule")
        lines.append(f"\\multicolumn{{6}}{{@{{}}l}}{{\\emph{{{group}}}}} \\tabularnewline")
        lines.append("\\addlinespace[2pt]")
        for qid in ids:
            q = mod.PROBE_REGISTRY_BY_ID[qid]
            text = q.render(0.9, history_before(5), 5, 0, {})
            fmt = FORMAT_OVERRIDE.get(qid, FORMAT[q.answer_kind])
            cells = [r"\raggedright " + sp.LABELS[qid],
                     r"\raggedright\ttfamily " + esc(text),
                     r"\raggedright " + fmt]
            cells += [answer_text(qid, truth[qid][p]) for p in RISKS]
            lines.append(" & ".join(cells) + " \\tabularnewline")
            lines.append("\\addlinespace[3pt]")
    if lines[-1].startswith("\\addlinespace"):
        lines.pop()
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{center}"]
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    mod = load_task()
    truth = check_against_data(mod)
    parts = [
        f"% Generated by {SOURCE}. Do not edit by hand.",
        "\\subsection{A question as the agent receives it}",
        "The prompt seat 1 receives in round 5 at $p=0.9$ for the question that compares two "
        "strategies (the history is an example). It is the decision prompt of that round with "
        "the final instruction replaced; the replacement is in bold.",
        prompt_box(mod),
        "\\subsection{The ten questions}",
        "Each question is asked in rounds 1, 5 and 10 of every game, in a separate call. No "
        "question text depends on the round or the risk level.",
        question_table(mod, truth),
    ]
    text = "\n".join(parts) + "\n"
    body = text.split("\n", 1)[1]
    for bad in ("--", "\u2013", "\u2014", "exp_", "evprobe", ".csv", "_probes"):
        if bad in body:
            raise AssertionError(f"forbidden text {bad!r} in questions.tex")
    for qid in sp.QUESTIONS:
        if qid in body:
            raise AssertionError(f"question id {qid} in questions.tex")
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}")
    for qid in sp.QUESTIONS:
        print(f"  {sp.LABELS[qid]:36} " + "  ".join(answer_text(qid, truth[qid][p]) for p in RISKS))


if __name__ == "__main__":
    main()
