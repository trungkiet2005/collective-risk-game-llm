"""Assemble the AAMAS 2027 full-paper upload folder and refuse it if a gate fails.

    python paper/AAMAS/make_full_submission.py

Builds on make_submission.py (PDF gates: eight-page body, fonts, metadata, identifying text) and
writes paper/AAMAS/AAMAS2027_full_submission/:

    main.pdf                    the paper, uploaded in the OpenReview "pdf" field
    supplementary_material.zip  the "supplementary material" field:
        supplementary_material.pdf
        code/   crg_game.py, README, requirements
        data/   every recorded game (the results/ tree) and a README

crg_game.py is kaggle/benchmarks/crg_task_server.py with the evaluation harness swapped out:
the harness client, its re-authentication, the push-validation guard and the task decorator
are removed, submission_kit/router_client.py (calls through any OpenAI-compatible router) takes
their place, and the sweep becomes run_sweep(), started by `python crg_game.py`. Comments and
docstrings that are Vietnamese, name the harness or point at internal scripts are dropped.

Gates on the staged copy: no identifying string anywhere and no mention of the harness in
code/; every top-level definition outside the swapped layer has the same syntax tree as in the
original (docstrings aside), so prompts, parser, retries, seeds, lottery and scripted partners
are the ones that played the games; and one game plays end to end against a local stand-in
router. The copy is staged in the system temp folder because the mixed-table file names pass
the 260-character Windows path limit when nested inside this folder. Nothing is uploaded.
"""
import ast
import csv
import http.server
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tokenize
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "AAMAS2027_full_submission"
STAGE = Path(tempfile.gettempdir()) / "aamas27"
KIT = HERE / "submission_kit"
GAME = REPO / "kaggle" / "benchmarks" / "crg_task_server.py"
ZIP_LIMIT = 25 * 1024 * 1024

GAME_DOC = '''"""Collective-risk social dilemma (Milinski et al. 2008) for language-model agents.

Six players, endowment 40, contributions 0, 2 or 4 in each of ten rounds, target 120; if the
group misses the target, a catastrophe destroys every player's savings with probability p.
Run `python crg_game.py`; every CRG_* environment variable below selects part of the
experiment (README.md gives the settings of each data folder). Model calls go through any
OpenAI-compatible router (OpenRouter by default, see MODEL ROUTER).

Seeds: sampling seed = (BASE + rep) * 1e5 + round * 100 + agent (mod 2^31 - 1); catastrophe
lottery = random.Random(BASE + rep).random() < p, keyed by rep only, so all risk levels share
the draws. Decisions are free text parsed by the anchored CONTRIBUTION: line, with retries.
"""'''

MODEL_DEF = '''# The run-selected model, named as the router names it. Seats listed in CRG_SEAT_MODELS
# may name other models; "self" means this one.
MODEL = os.environ.get("CRG_MODEL", "anthropic/claude-haiku-4.5")
'''

# Top-level definitions that belong to the harness layer and are removed or replaced.
HARNESS_DEFS = {"_no_overrides", "_model_key", "_EXPECTED_MODELS", "IS_PUSH_VALIDATION", "_LLM", "_AUTH_ERR",
                "_SEAT_CLIENTS", "_build_seat_client", "_client_for", "_reauth", "_call_llm"}
# Top-level definitions the swap edits in place; every other one must be unchanged.
EDITED_DEFS = {"MODEL", "collective_risk_baseline", "_check_paraphrase", "_strip_anchors",
               "_to_probe_template"}
# Runtime strings that name the harness, with their replacements.
STRING_EDITS = [
    ("\"arm must be re-derived (and re-checked against \"\n"
     "                \"crsd/prompts/crsd_nohint_en.txt) before it is run.\"",
     "\"arm must be re-derived before it is run.\""),
    ("\"re-derived (and re-checked against crsd/prompts/crsd_comprehension_en.txt)\"\n"
     "            \" before the probe arm is run.\"",
     "\"re-derived before the probe arm is run.\""),
    ("\"template %r carries non-ASCII text (%s). Kaggle's push reads this file \"\n"
     "            \"with the system codepage and has already died on that once.\"",
     "\"template %r carries non-ASCII text (%s); templates must stay ASCII so the \"\n"
     "            \"file reads the same under any system codepage.\""),
    ("503/429/403/404 all surfaced\n    identically as 'Errored' in the Kaggle UI, which has "
     "already cost this repo days\n    of misdiagnosis -- so the HTTP code and a `kind` are "
     "always carried.",
     "The HTTP code and a `kind` are\n    always carried, so failures with the same symptom "
     "can be told apart."),
]

VIET_MARKS = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ"
                        r"ĂÂĐÊÔƠƯ]")
# Function words of unaccented Vietnamese; three different ones in one comment mark it as Vietnamese.
VIET_WORDS = re.compile(r"\b(khong|cua|nhung|duoc|thi|va|cho|neu|vi|nen|moi|cung|chay|ghi|lai|"
                        r"phai|tu|ra|vao|den|bang|nay|do|cac|mot|hai|ban|van|dung|sai|loi|tat)\b", re.I)
INTERNAL = re.compile(r"plan/|launch_|Legacy_Results|CLAUDE\.md|run_dense|stage_day|drive_neutral"
                      r"|kaggle|kbench|push.validation|crsd/tests|`-m`|production proxy|staging"
                      r"|Model Proxy|SDK|contexts\.enter|supervisor|LLM_DEFAULT", re.I)
# Remaining mentions of the old service in comments and docstrings, made generic.
TEXT_EDITS = [(re.compile(r"(?<!LiteLLM )\b[Pp]roxies\b"), "model services"),
              (re.compile(r"(?<!LiteLLM )\b[Pp]roxy\b"), "model service")]

LEAKS = [r"huynh", r"\bkiet\b", r"trung.?kiet", r"\bchis", r"chunaiu", r"trunkdabest", r"vinhdinh",
         r"foundnot", r"kit567", r"tnkiet", r"kakagotto", r"tonngohan", r"minh2duy", r"boymagic",
         r"trngthtnhi", r"osduyminh", r"The Anh", r"\bHan\b", r"Teesside", r"\bVNU\b", r"HCMUS",
         r"University of Science", r"[\w.+-]+@[\w-]+\.[\w.]+", r"\b[A-Z]:[\\/]+[\w.-]{2,}[\\/]",
         r"/Users/", r"kaggle_for_research", r"KGAT_", r"Legacy_Results", r"CLAUDE\.md",
         r"aamas2027-e0", r"trungkiet2005", r"collective-risk-game-llm", r"23122039", r"plan/scripts"]
CODE_LEAKS = [r"kaggle", r"kbench", r"LLM_DEFAULT", r"LLMS_AVAILABLE", r"MODEL_PROXY"]


def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)


def is_vietnamese(text):
    return bool(VIET_MARKS.search(text)) or len({w.lower() for w in VIET_WORDS.findall(text)}) >= 3


def node_names(node):
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return {t.id for t in targets if isinstance(t, ast.Name)}
    return set()


def with_comments_above(lines, start):
    """First line of the contiguous full-line comment block that ends just above `start`."""
    while start > 0 and lines[start - 1].lstrip().startswith("#") \
            and not lines[start - 1].lstrip().startswith("# %%"):
        start -= 1
    return start


def swap_harness(src):
    """Replace the evaluation-harness layer of crg_task_server.py by the router client."""
    for old, new in STRING_EDITS:
        if old not in src:
            fail(f"expected text not found in {GAME.name}: {old[:60]!r}")
        src = src.replace(old, new)
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    cuts = []                                  # (first line, end line, replacement), 0-based
    router = (KIT / "router_client.py").read_text(encoding="utf-8")
    router_done = False
    for node in tree.body:
        names = node_names(node)
        seg = ast.get_source_segment(src, node) or ""
        first = (node.decorator_list[0].lineno if getattr(node, "decorator_list", None)
                 else node.lineno) - 1
        top = with_comments_above(lines, first)
        if isinstance(node, ast.Import) and any(a.name == "kaggle_benchmarks" for a in node.names):
            cuts.append((top, node.end_lineno, "import urllib.error\nimport urllib.request\n"))
        elif names == {"MODEL"}:
            cuts.append((top, node.end_lineno, MODEL_DEF))
        elif isinstance(node, ast.Assign) and ("LLM_DEFAULT" in seg or names == {"_no_overrides"}):
            cuts.append((top, node.end_lineno, ""))
        elif isinstance(node, ast.If) and any(k in seg for k in (
                "IS_PUSH_VALIDATION", "CRG_SKIP_RUN", "gemini-3-flash-preview")):
            cuts.append((top, node.end_lineno, ""))
        elif names & HARNESS_DEFS:
            # the router takes the place of the old client, right before decide()
            cuts.append((top, node.end_lineno, router + "\n\n" if names == {"_LLM"} else ""))
            router_done = router_done or names == {"_LLM"}
        elif names == {"collective_risk_baseline"}:
            cuts.append((top, node.end_lineno, sweep_function(src, node)))
    for top, end, text in sorted(cuts, reverse=True):
        lines[top:end] = [text]
    out = "".join(lines).rstrip() + '\n\n\nif __name__ == "__main__":\n    run_sweep()\n'
    return drop_comment_blocks(out)


def sweep_function(src, node):
    """The task body as a plain function: no decorator, no harness client, no seat preflight."""
    lines = src.splitlines(keepends=True)
    drop = []
    for stmt in ast.walk(node):
        if isinstance(stmt, ast.Global) or (
                isinstance(stmt, ast.Assign) and any(getattr(t, "id", "") == "_LLM" for t in stmt.targets)):
            drop.append((stmt.lineno - 1, stmt.end_lineno))
        elif isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Name) \
                and stmt.test.id == "SEAT_FOREIGN_SLUGS":
            drop.append((with_comments_above(lines, stmt.lineno - 1), stmt.end_lineno))
    body = lines[node.lineno - 1:node.end_lineno]
    base = node.lineno - 1
    for a, b in sorted(drop, reverse=True):
        body[a - base:b - base] = []
    text = "".join(body)
    text = text.replace("def collective_risk_baseline(llm) -> dict:", "def run_sweep() -> dict:")
    text = text.replace("kbench.assertions.assert_equal(", "_require(")
    if "kbench" in text or "_client_for" in text or "def run_sweep" not in text:
        fail("the sweep function still refers to the harness")
    return text


def drop_comment_blocks(src):
    """Remove every full-line comment block that names the harness or an internal script."""
    lines = src.splitlines(keepends=True)
    out, block = [], []
    for line in lines + ["\n"]:
        if line.lstrip().startswith("#") and not line.lstrip().startswith("# %%"):
            block.append(line)
            continue
        if block and not any(INTERNAL.search(b) for b in block) and not is_vietnamese("".join(block)):
            out.extend(block)
        block = []
        out.append(line)
    return "".join(out[:-1])


def docstring_lines(tree):
    lines = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            lines.add(body[0].lineno)
    return lines


def clean_game(src):
    """New module docstring; light commenting: section headers, short inline notes and the
    first paragraph of each docstring stay, everything else goes."""
    tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    tree = ast.parse(src)
    docs = docstring_lines(tree)
    sole = {n.body[0].lineno for n in ast.walk(tree)
            if isinstance(getattr(n, "body", None), list) and len(n.body) == 1}
    module_doc = next(t for t in tokens if t.type == tokenize.STRING)
    out = []
    for tok in tokens:
        # untokenize places each token by the positions it carries, not by its text, so a
        # replacement may have any number of lines
        if tok is module_doc:
            tok = tok._replace(string=GAME_DOC)
        elif tok.type == tokenize.COMMENT:
            full_line = tok.line.strip().startswith("#")
            keep = (tok.string.startswith("# %%") and tok.string.strip() != "# %%" if full_line
                    else len(tok.string) <= MAX_INLINE_COMMENT)
            if keep and full_line:                   # section header: drop internal labels
                tok = tok._replace(string=re.sub(r"\s*\(==[^)]*\)|\bE\d+: ", "", tok.string))
            if not keep or is_vietnamese(tok.string) or INTERNAL.search(tok.string) \
                    or (not full_line and "crsd" in tok.string):
                tok = tok._replace(string="#")
            else:
                tok = tok._replace(string=generic(tok.string))
        elif tok.type == tokenize.STRING and tok.start[0] in docs:
            if is_vietnamese(tok.string) or INTERNAL.search(tok.string):
                tok = tok._replace(string="pass" if tok.start[0] in sole else "")
            else:
                doc = generic(first_paragraph(tok.string))
                tok = tok._replace(string=doc or ("pass" if tok.start[0] in sole else ""))
        out.append(tok)
    text = tokenize.untokenize(out)
    text = re.sub(r"^[ \t]*#[ \t]*\n", "", text, flags=re.M)      # emptied comment lines
    text = re.sub(r"[ \t]+#[ \t]*$", "", text, flags=re.M)        # emptied trailing comments
    text = re.sub(r"(:[ \t]*\n)[ \t]+\n", r"\1", text)           # removed docstrings
    text = re.sub(r"^[ \t]*\n(?=[ \t]*\n)", "", text, flags=re.M)  # runs of blank lines ...
    text = re.sub(r"(\n\n)(?=(def |class |@|# %%))", "\n\n\n", text)  # ... two before top-level defs
    return text


MAX_INLINE_COMMENT = 60


def generic(text):
    """Old-service wording made generic; references to the unshipped crsd package dropped."""
    for pat, repl in TEXT_EDITS:
        text = pat.sub(repl, text)
    text = re.sub(r"\s*\([^()]*crsd[^()]*\)", "", text)
    if "crsd" not in text:
        return text
    m = re.match(r'([rRuUbBfF]*)("""|\'\'\')(.*?)(\2)$', text, re.S)
    if not m:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", m.group(3).strip())
    kept = " ".join(x for x in sentences if "crsd" not in x)
    return m.group(1) + m.group(2) + kept + m.group(2) if kept else ""


def first_paragraph(doc):
    """A docstring cut to its first paragraph."""
    m = re.match(r'([rRuUbBfF]*)("""|\'\'\')(.*?)(\2)$', doc, re.S)
    if not m:
        return doc
    head = re.split(r"\n[ \t]*\n", m.group(3), maxsplit=1)[0].rstrip()
    return m.group(1) + m.group(2) + head + m.group(2)


def unchanged_outside_swap(original, shipped):
    """Names of top-level definitions outside the swapped layer whose code differs."""
    def table(src):
        tree = ast.parse(src)
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                    and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
        return [(node_names(n), ast.dump(n)) for n in tree.body]
    shipped_dumps = {d for _, d in table(shipped)}
    changed = []
    for names, dump in table(original):
        if names & (HARNESS_DEFS | EDITED_DEFS):
            continue
        if dump not in shipped_dumps and "kaggle_benchmarks" not in dump \
                and "LLM_DEFAULT" not in dump and "IS_PUSH_VALIDATION" not in dump \
                and "CRG_SKIP_RUN" not in dump and "gemini-3-flash-preview" not in dump:
            changed.append(sorted(names) or dump[:80])
    return changed


class _StandInRouter(http.server.BaseHTTPRequestHandler):
    """Answers every chat completion with a fair-share decision, like a router would."""

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body["messages"][0]["content"].startswith("You are Player_")
        reply = {"choices": [{"message": {"content": "I will pay my share.\nCONTRIBUTION: 2"}}],
                 "usage": {"prompt_tokens": 500, "completion_tokens": 9}}
        data = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def play_one_game(game_py):
    """Play one game per seat layout through a local stand-in router; return the games.csv rows."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StandInRouter)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    rows = {}
    try:
        for label, seats in (("self-play", ""),
                             ("scripted", "self," + ",".join(["scripted:always_0"] * 5))):
            with tempfile.TemporaryDirectory() as tmp:
                env = dict(os.environ, CRG_ROUTER_URL=f"http://127.0.0.1:{server.server_port}/v1",
                           CRG_ROUTER_KEY="test", CRG_MODEL="test/model", CRG_RISKS="0.9",
                           CRG_REPS="1", CRG_OUT=str(Path(tmp) / "out"), CRG_SEAT_MODELS=seats,
                           PYTHONIOENCODING="utf-8")
                r = subprocess.run([sys.executable, str(game_py)], cwd=tmp, env=env,
                                   capture_output=True, text=True, timeout=300)
                if r.returncode:
                    fail(f"crg_game.py ({label}) failed against the stand-in router:\n"
                         + r.stdout[-1500:] + r.stderr[-1500:])
                with open(Path(tmp) / "out" / "games.csv", encoding="utf-8") as f:
                    rows[label] = list(csv.DictReader(f))
    finally:
        server.shutdown()
    return rows


def stage():
    if STAGE.exists():
        shutil.rmtree(STAGE)
    code, data = STAGE / "code", STAGE / "data"
    code.mkdir(parents=True)
    src = GAME.read_text(encoding="utf-8")
    game = clean_game(swap_harness(src))
    changed = unchanged_outside_swap(src, game)
    if changed:
        fail(f"definitions outside the harness layer changed: {changed}")
    (code / "crg_game.py").write_text(game, encoding="utf-8", newline="\n")
    shutil.copyfile(KIT / "README_code.md", code / "README.md")
    shutil.copyfile(KIT / "requirements_code.txt", code / "requirements.txt")
    results = REPO / "results"
    for f in results.rglob("*"):
        if f.is_file() and f.name not in ("DATA_CARD.md", "PROVENANCE.json"):
            dst = data / f.relative_to(results)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dst)
    shutil.copyfile(KIT / "README_data.md", data / "README.md")


def gates():
    for f in STAGE.rglob("*"):
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        pats = LEAKS + (CODE_LEAKS if f.parent.name == "code" else [])
        for pat in pats:
            m = re.search(pat, text, flags=0 if re.search(r"[A-Z]", pat.replace("\\b", "")) else re.I)
            if m:
                line = text[:m.start()].count("\n") + 1
                fail(f"{f.relative_to(STAGE)}:{line}: '{m.group(0)}' matches {pat}")
    game = STAGE / "code" / "crg_game.py"
    left = len(VIET_MARKS.findall(game.read_text(encoding="utf-8")))
    print(f"note: {left} Vietnamese characters left in crg_game.py, all in runtime strings "
          f"(the unused Vietnamese prompt template)")
    rows = play_one_game(game)
    selfplay, scripted = rows["self-play"], rows["scripted"]
    if len(selfplay) != 1 or float(selfplay[0]["group_total"]) != 120 or selfplay[0]["target_reached"] != "1":
        fail(f"stand-in self-play game is wrong: {selfplay}")
    if len(scripted) != 1 or float(scripted[0]["group_total"]) != 20:
        fail(f"stand-in scripted game is wrong: {scripted}")
    print("stand-in router: self-play game reached 120, scripted-partner game totalled 20 (as expected)")
    for junk in STAGE.rglob("__pycache__"):
        shutil.rmtree(junk)


def main():
    # The authors keep their en and em dashes (decided 7 October 2026).
    r = subprocess.run([sys.executable, str(HERE / "make_submission.py"), "--allow-dashes"],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        fail("make_submission.py gates failed")
    stage()
    gates()
    OUT.mkdir(exist_ok=True)
    shutil.copyfile(HERE / "submission" / "main.pdf", OUT / "main.pdf")
    zpath = OUT / "supplementary_material.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(HERE / "supplement" / "supplement.pdf", "supplementary_material.pdf")
        for f in sorted(STAGE.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(STAGE))
    size = zpath.stat().st_size
    if size > ZIP_LIMIT:
        fail(f"zip is {size / 1e6:.1f} MB, over the 25 MB limit")
    n_data = sum(1 for f in (STAGE / "data").rglob("*") if f.is_file())
    print(f"OK {OUT}\n   main.pdf, supplementary_material.zip {size / 1e6:.2f} MB "
          f"(supplement PDF, code/ 3 files, data/ {n_data} files)")


if __name__ == "__main__":
    main()
