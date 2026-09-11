# %%
"""Collective-Risk Social Dilemma (Milinski et al. 2008) — FRONTIER arm.

Configured to be BYTE-FOR-BYTE comparable with the open-source arm
`crsd/configs/experiment/exp_baseline.json`, so frontier-model results drop
straight into the same analysis (`results/analyze.py`) and join the open-source
`games.csv` / `turns.jsonl` by (risk_probability, language, rep).

What is held identical to exp_baseline:
  - Game: 6 players, endowment 40, contribute {0,2,4}, target 120, 10 rounds
    (length KNOWN to the agents), temperature 0.7.
  - Conditions swept: risk ∈ {0.90, 0.50, 0.10} × language ∈ {en, vn} × 10 reps
    = 60 games/model. Neutral personas (personas_default), full_history,
    NO framing, showCumulative=FALSE (the running pool is hidden — the deliberate
    design that makes the game a genuine cumulative-state test; see the
    comprehension sub-study "read ≠ add").
  - Prompt: the EXACT crsd_en.txt / crsd_vn.txt templates (same wording, same
    fixed-position history "P1(you)=.., P2=..", no cumulative line).
  - Seeds / CRN: sampling seed = (BASE+rep)*1e5 + round*100 + agent (mod 2^31-1);
    disaster lottery = random.Random(BASE+rep).random() < risk, keyed by rep only
    so EN/VN and all risks SHARE the draw (common random numbers).
  - Elicitation: free-text generation parsed by the anchored `CONTRIBUTION:` regex
    with retry-on-parse-fail (NOT a forced JSON schema) — same as the vLLM arm.

Local run:
    PYTHONUTF8=1 python crg_task.py                        # google/gemini-3.1-flash-lite-preview
    CRG_MODEL="anthropic/claude-haiku-4-5@20251001" python crg_task.py
    # Cheap smoke test (1 rep, EN, high risk only) — check parse-fail% BEFORE a full run:
    CRG_REPS=1 CRG_LANGS=en CRG_RISKS=0.9 python crg_task.py
    # E1, the no-anchor arm (English only) -> results/frontier/<model>/exp_nohint:
    CRG_TEMPLATE=nohint CRG_LANGS=en python crg_task_server.py

Prompt arms (CRG_TEMPLATE, default "baseline"):
  baseline  the EXACT crsd_en.txt / crsd_vn.txt wording, equal-split hint included.
  nohint    experiment E1. The same English template with exactly two spans deleted
            -- the fair-share gloss "(an average of 2 per player per round)" and the
            worked example "(for example, contributing 2 every round leaves you 20 at
            the end)" -- matching crsd/prompts/crsd_nohint_en.txt. Derived from
            TEMPLATE_EN at import, so the two arms can never drift apart in any other
            way. It carries its own checkpoint signature and its own output folder
            (exp_nohint), so it cannot resume or overwrite baseline games.

Comprehension probe (CRG_PROBE, default "" -- OFF, nothing below happens):
  A comma-separated list of question CATEGORIES from crsd/engine/comprehension.py:
    value   experiment E2. The two expected-value questions (value_defect_ev,
            value_compare) whose answers are NOT readable from the prompt: the agent
            has to multiply a probability by money. This is the direct measurement of
            "can the model do the comparison its behaviour appears to obey".
    rules   the eight static rules questions, the usual control axis for E2.
    time    per-round history lookups.   state  cumulative arithmetic.
  Probes fire at CHECKPOINT ROUNDS only (CRG_PROBE_ROUNDS, default 1,5,10) because
  the rules/value answers are static within a game, and each one is a SEPARATE llm
  call issued AFTER that round's decisions are already collected -- so a probe can
  never steer the play it is measuring. Answers are graded here against ground truth
  recomputed server-side and written to probes.jsonl next to games.csv/turns.jsonl,
  in the same record shape as crsd's comprehension.jsonl.

  COST. Extra llm calls per game = seats x checkpoint rounds x questions per round,
  on top of the 60 decisions (6 agents x 10 rounds). With the defaults (seat P1 only,
  rounds 1/5/10):
      CRG_PROBE=value        3 x  2 =   6 calls/game  (1.10x)
      CRG_PROBE=rules,value  3 x 10 =  30 calls/game  (1.50x)
      CRG_PROBE=rules,value,time,state      3 x ~49 = 146 calls/game  (3.43x)
  CRG_PROBE_SEATS=all probes every agent and multiplies those by 6. The exact number
  for the configured arm is printed in the [CRG_START] line as probes_per_game.

  E2 as run:  CRG_PROBE=rules,value CRG_LANGS=en python crg_task_server.py

Mixed groups / scripted seats (CRG_SEAT_MODELS, default "" -- OFF, all six seats
play the model `kaggle b t run -m <slug>` selected, exactly as before):
  A comma-separated list of EXACTLY nPlayers entries, seat P1 first. Each entry is
    <model slug>       another proxy model. The proxy is OpenAI-compatible and the
                       slug travels in the request BODY, so a second model needs no
                       second credential and no second URL -- only a second client
                       built on the same MODEL_PROXY_URL/MODEL_PROXY_API_KEY.
    scripted:<policy>  a deterministic seat that NEVER calls the proxy. Policies:
                       always_0, always_2, always_4, ev_maximiser,
                       conditional_cooperator -- the same five, with the same
                       decision rules, as crsd/models/scripted.py.
    self  (or empty)   the run-selected model.

  E3a, best response (one llm seat against five KNOWN opponents). Only P1 calls the
  proxy, so a game costs 10 calls instead of 60 -- 6x cheaper -- and because the
  opponents are known exactly, "did it best-respond" becomes a number:
      CRG_SEAT_MODELS="self,scripted:always_4,scripted:always_4,scripted:always_4,scripted:always_4,scripted:always_4"

  E3b, mixed model populations (k invaders of one model in a group of another):
      CRG_SEAT_MODELS="self,self,self,gpt-5.4-nano,gpt-5.4-nano,gpt-5.4-nano"

  NOT YET VERIFIED, and it must be settled before E3b is launched: nobody has checked
  that the PRODUCTION proxy serves a slug OTHER than the one `-m` selected. Test it
  with ONE game before committing a shard:
      CRG_SEAT_MODELS="self,<other slug>,..." CRG_REPS=1 CRG_LANGS=en CRG_RISKS=0.9
  A refusal shows up as a [CRG_ERROR] record naming the seat: kind
  "seat_client_failed" if the client cannot even be built, otherwise the call's own
  http code (400/403/404) with seat_model in the record. THE FALLBACK NEEDS NO SECOND
  CLIENT AT ALL: keep exactly one llm seat (the selected model) and make every other
  seat scripted:<policy>. That is E3a, and it is unaffected by the question.

  Mixed runs cannot collide with baseline data: the seat configuration is hashed into
  a seat tag that goes into the output folder, into the game name (hence game_id) and
  into the checkpoint signature. An unset CRG_SEAT_MODELS changes none of the three.
"""
import csv
import hashlib
import io
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path
import contextvars
from concurrent.futures import ThreadPoolExecutor

# Load MODEL_PROXY_* from .env for local runs (harmless on the Kaggle server, which
# injects these as real env vars). Pick the model via CRG_MODEL, else flash-lite.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
# Server-side model selection: `kaggle b t run -m <slug>` sets LLM_DEFAULT in the
# server env BEFORE this module imports. Precedence: explicit CRG_MODEL (local
# override) > server/.env-provided LLM_DEFAULT > flash-lite fallback. This is the
# ONLY behavioural difference from crg_task.py, which hard-pins flash-lite here and
# would therefore silently override the -m flag on the server.
MODEL = (os.environ.get("CRG_MODEL")
         or os.environ.get("LLM_DEFAULT")
         or "google/gemini-3.1-flash-lite-preview")
os.environ["LLM_DEFAULT"] = MODEL

import kaggle_benchmarks as kbench


# %% =====================  BASELINE CONSTANTS (== exp_baseline)  =====================
N_PLAYERS = 6
N_ROUNDS = 10
ENDOWMENT = 40
TARGET = 120
OPTIONS = (0, 2, 4)
N_ROUNDS_KNOWN = True
# Decoding temperature. E6 (robustness) needs a temperature=0 arm so the reviewer
# question "is this just an artifact of sampling?" has an answer, so the value is a
# knob. Same textual shape as every other CRG_* knob, because the server never sees
# shell environment variables: plan/scripts/launch_shard.py rewrites the DEFAULT into
# a copied shard file before pushing it.
# The default is 0.7, the value every game in the corpus so far was played at, so an
# unset environment reproduces the existing sweep byte for byte.
TEMPERATURE = float(os.environ.get("CRG_TEMPERATURE", "0.7"))

# A temperature arm plays the BASELINE wording, so without a suffix its games land in
# the very folder the risk-grid baseline lives in -- and to_wide_csv.py reads the
# experiment name off that folder, so E6's decoding arm would be merged into the
# verified baseline frame. Identical hazard, identical fix, to PROBE_SUFFIX and
# SEAT_SUFFIX further down; the checkpoint signature already keys on temperature, so
# this is the other half, on the output path.
# "%g" renders 0.0 as "0" and 0.3 as "0.3"; the dot becomes "p" because these strings
# become directory names, where "risk-0p9" already sets that convention.
TEMP_SUFFIX = "" if TEMPERATURE == 0.7 else ("_temp%g" % TEMPERATURE).replace(".", "p")
PERSONA_SET = "personas_default"     # neutral agents -> persona block dropped
PLAYER_NAMES = [f"Player_{i + 1}" for i in range(N_PLAYERS)]

# Seed scheme copied verbatim from crsd (engine/game.py + runner/batch.py) so the
# frontier arm shares the SAME reproducibility/CRN structure as the vLLM arm.
BASE_SEED = 12345
SAMPLING_SEED_STRIDE = 100_000
SAMPLING_SEED_MOD = 2_147_483_647    # 2**31 - 1
RETRY_SEED_STEP = 1_000_003
MAX_PARSE_RETRIES = 3
# Tran khi NANG cap luc retry vi bi cat output. Cao hon nua thi tien coc cua proxy
# (dat truoc theo max_output_tokens) bat dau doa 403 tren account gan het quota.
MAX_RETRY_CAP = 8000

# Swept conditions (env-overridable so a smoke test doesn't need code edits).
RISKS = [float(x) for x in os.environ.get("CRG_RISKS", "0.9,0.5,0.1").split(",")]
LANGS = [s.strip() for s in os.environ.get("CRG_LANGS", "en").split(",")]
REPS = int(os.environ.get("CRG_REPS", "10"))
# Chia shard theo rep khi chia theo risk×lang vẫn còn quá đắt cho trần $10/account.
# An toàn về seed: sampling_seed(rep, agent, round) và xổ số thảm hoạ Random(BASE+rep)
# đều keyed theo rep, nên mỗi shard giữ một khoảng rep riêng biệt là bất biến.
# REP_START=5, REPS=5 -> chạy rep 5..9.
REP_START = int(os.environ.get("CRG_REP_START", "0"))

# Persist one atomic shard per completed game. If the process is restarted in the
# same workspace, valid shards are loaded and those (risk, language, rep) cells are
# skipped. Set CRG_RESUME=0 only when a deliberately clean rerun is required.
RESUME = os.environ.get("CRG_RESUME", "1").strip().lower() not in {
    "0", "false", "no", "off",
}

# Which prompt template this sweep plays.
#   "baseline" -- the instrument every existing results/frontier game was measured
#                 with (EN + VN, equal-split hint present). DEFAULT: unset env ->
#                 byte-identical behaviour to before this knob existed.
#   "nohint"   -- experiment E1: the SAME template minus the two equal-split anchors
#                 (see TEMPLATE_EN_NOHINT below). English only, by panel design.
# Same textual shape as every other knob so plan/scripts/launch_shard.py's regex
# rewriter (make_shard_file) can bake the value into a shard copy.
TEMPLATE_VARIANT = os.environ.get("CRG_TEMPLATE", "baseline").strip().lower() or "baseline"
KNOWN_TEMPLATE_VARIANTS = ("baseline", "nohint", "para1", "para2")
if TEMPLATE_VARIANT not in KNOWN_TEMPLATE_VARIANTS:
    # Fail at import, before a single paid call: a typo'd variant that fell back to
    # baseline would spend the shard's budget re-measuring the control arm.
    raise SystemExit("CRG_TEMPLATE=%r is not a known template variant; expected one "
                     "of: %s" % (TEMPLATE_VARIANT, ", ".join(KNOWN_TEMPLATE_VARIANTS)))

# --- Mixed groups and scripted seats (CRG_SEAT_MODELS, default "" -- OFF) ----
# EMPTY IS THE DEFAULT and means exactly what this file has always done: all six
# seats are played by the ONE model `kaggle b t run -m <slug>` selected, through the
# single client the task is handed -- no extra client, no extra column in games.csv,
# no extra key in a checkpoint, no change to a game_id.
# When set, it is a comma-separated list of EXACTLY N_PLAYERS entries (seat P1 first):
#   <slug>             another proxy model. OpenAI-compatible means the slug is a
#                      BODY field, so one credential serves every model; the extra
#                      client is built by _client_for() on the same
#                      MODEL_PROXY_URL/MODEL_PROXY_API_KEY as the selected one.
#   scripted:<policy>  a deterministic seat that never calls the proxy (free, and
#                      immune to a 503). Five policies, reimplemented from
#                      crsd/models/scripted.py further down this file.
#   self / <empty>     the run-selected model.
# Same textual shape as every other knob so plan/scripts/launch_shard.py's regex
# rewriter (make_shard_file) can bake the value into a shard copy: the server does
# NOT receive environment variables, so a knob written any other way cannot be set
# there.
SCRIPTED_PREFIX = "scripted:"
SELF_MODEL = "self"
SCRIPTED_POLICIES = ("always_0", "always_2", "always_4", "ev_maximiser",
                     "conditional_cooperator")
# One character per policy for the seat tag, copied from SEAT_CODE in
# crsd/analysis/scripted_reference.py so a group reads the same in both arms:
# "L44444" is one llm seat against five always_4 opponents.
SEAT_CODE = {"always_0": "0", "always_2": "2", "always_4": "4",
             "ev_maximiser": "E", "conditional_cooperator": "C"}
_SEAT_MODELS_SPEC = os.environ.get("CRG_SEAT_MODELS", "")


def is_scripted_seat(name):
    """Is this seat entry a scripted policy rather than a model slug?"""
    return isinstance(name, str) and name.startswith(SCRIPTED_PREFIX)


def scripted_policy_name(name):
    """"scripted:always_4" -> "always_4" (already bare -> returned unchanged)."""
    return name[len(SCRIPTED_PREFIX):] if is_scripted_seat(name) else name


def _parse_seat_models(spec):
    """CRG_SEAT_MODELS -> one resolved entry per seat, or () when the knob is off.

    Every failure is an import-time SystemExit, before a single paid call. A typo
    that silently fell back to "everyone plays the selected model" is the expensive
    outcome available here: the shard would spend its whole budget re-measuring the
    baseline and hand back a null best-response result that reads like evidence.
    """
    spec = (spec or "").strip()
    if not spec:
        return ()
    entries = [part.strip() for part in spec.split(",")]
    if len(entries) != N_PLAYERS:
        raise SystemExit(
            "CRG_SEAT_MODELS names %d seat(s) but the game has %d: give one entry "
            "per seat, P1 first (a model slug, scripted:<policy>, or self)."
            % (len(entries), N_PLAYERS))
    resolved = []
    for i, entry in enumerate(entries):
        if not entry or entry.lower() == SELF_MODEL:
            resolved.append(MODEL)
            continue
        if is_scripted_seat(entry):
            policy = scripted_policy_name(entry)
            if policy not in SCRIPTED_POLICIES:
                raise SystemExit(
                    "CRG_SEAT_MODELS seat %d asks for scripted policy %r, which does "
                    "not exist (known: %s)"
                    % (i, policy, ", ".join(SCRIPTED_POLICIES)))
            resolved.append(SCRIPTED_PREFIX + policy)
            continue
        if any(ch.isspace() for ch in entry):
            raise SystemExit("CRG_SEAT_MODELS seat %d (%r) contains whitespace; a "
                             "model slug does not." % (i, entry))
        resolved.append(entry)
    return tuple(resolved)


SEAT_MODELS = _parse_seat_models(_SEAT_MODELS_SPEC)
# Seats that actually call the proxy, and the distinct slugs that are NOT the model
# `-m` selected -- the ones whose acceptance by the production proxy is still an open
# question (see the module docstring).
SEAT_LLM_SEATS = tuple(i for i, m in enumerate(SEAT_MODELS)
                       if not is_scripted_seat(m))
SEAT_FOREIGN_SLUGS = tuple(sorted({m for m in SEAT_MODELS
                                   if not is_scripted_seat(m) and m != MODEL}))


def _seat_tag(seat_models):
    """Short, deterministic, filesystem-safe name for ONE seat configuration.

    Readable half: one character per seat ("L" = the selected model, "M" = another
    slug, and the crsd policy codes for scripted seats). Exact half: 8 hex of the
    resolved seat list, so two groups that read alike but are not identical (a
    different invader slug, the same policies in a different order) can never share a
    folder, a game_id or a checkpoint. Empty when the knob is off, which is what
    keeps every existing path byte-for-byte unchanged.
    """
    if not seat_models:
        return ""
    codes = "".join(
        SEAT_CODE.get(scripted_policy_name(m), "?") if is_scripted_seat(m)
        else ("L" if m == MODEL else "M")
        for m in seat_models)
    digest = hashlib.sha256("\x00".join(seat_models).encode("utf-8")).hexdigest()[:8]
    return "seats-%s-%s" % (codes, digest)


SEAT_TAG = _seat_tag(SEAT_MODELS)
SEAT_SUFFIX = ("_" + SEAT_TAG) if SEAT_TAG else ""

# Output experiment folder. Baseline keeps its historical name so existing runs and
# results/frontier/<model>/exp_baseline are untouched; every other variant gets its
# own folder, so a nohint sweep can never overwrite (or resume into) baseline data.
# A mixed group appends its seat tag for the same reason one level down: who sits in
# the other five seats is as much the instrument as the prompt is, and a
# best-response shard that resumed into (or overwrote) the baseline shard of the same
# cell would produce one games.csv holding two different experiments.

# Prompt-template variant identifier. The templates below are variant "baseline".
# ANY later prompt arm (a no-hint arm, a framing arm, a computed-totals arm) must
# ship a different value here, because the checkpoint signature keys on it: without
# it a variant run would happily resume a baseline shard and the resulting games.csv
# would silently mix two different instruments. `_prompt_fingerprint()` is the
# belt-and-braces half -- it changes even when someone edits the prompt and forgets
# to change this string.
# It DEFAULTS to the selected template rather than to the literal "baseline", so the
# declared name cannot disagree with the template actually played; set
# CRG_PROMPT_VARIANT by hand only to separate two arms that share one template.
PROMPT_VARIANT = os.environ.get("CRG_PROMPT_VARIANT", "").strip() or TEMPLATE_VARIANT

# --- Comprehension probe (experiment E2) ------------------------------------
# CRG_PROBE is a comma-separated list of question CATEGORIES taken from
# crsd/engine/comprehension.py: "rules", "value", "time", "state". EMPTY IS THE
# DEFAULT and means no probe at all -- not one extra call, not one extra file, not one
# extra byte in a checkpoint -- so an unset environment plays exactly the sweep this
# file played before the knob existed. E2 is CRG_PROBE=rules,value.
# Same textual shape as every other knob so plan/scripts/launch_shard.py's regex
# rewriter (make_shard_file) can bake the value into a shard copy: the server does NOT
# receive environment variables, so a knob written any other way cannot be set there.
KNOWN_PROBE_CATEGORIES = ("rules", "value", "time", "state")
PROBE_CATEGORIES = tuple(
    part.strip().lower()
    for part in os.environ.get("CRG_PROBE", "").split(",")
    if part.strip())
_UNKNOWN_PROBE = [c for c in PROBE_CATEGORIES if c not in KNOWN_PROBE_CATEGORIES]
if _UNKNOWN_PROBE:
    # Fail at import, before a single paid call. A typo'd axis that silently asked
    # nothing would return a shard with zero probe rows, which on the analysis side
    # looks exactly like "the run was fine, the model just never answered".
    raise SystemExit("CRG_PROBE names unknown categories: %s (known: %s)"
                     % (", ".join(_UNKNOWN_PROBE), ", ".join(KNOWN_PROBE_CATEGORIES)))


def _probe_int_list(env_name, spec):
    """Comma-separated ints from one CRG_* knob, or a loud import-time failure."""
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            raise SystemExit("%s=%r is not a comma-separated list of integers"
                             % (env_name, spec))
    return tuple(sorted(set(out)))


# Rounds at which the probe fires. The rules and value answers are STATIC within a
# game -- their ground truth does not move with the history -- so asking them every
# round multiplies the cost without adding information. crsd's exp_evprobe.json pins
# rulesCheckpoints to [1, 5, 10]; this default matches it, and the same gate is
# applied to the time/state axes here so the probe cost of a shard is predictable.
PROBE_ROUNDS = _probe_int_list("CRG_PROBE_ROUNDS",
                               os.environ.get("CRG_PROBE_ROUNDS", "1,5,10"))
_BAD_PROBE_ROUNDS = [r for r in PROBE_ROUNDS if r < 1 or r > N_ROUNDS]
if _BAD_PROBE_ROUNDS:
    raise SystemExit("CRG_PROBE_ROUNDS is outside 1..%d: %s"
                     % (N_ROUNDS, ", ".join(str(r) for r in _BAD_PROBE_ROUNDS)))

# Which seats answer. "0" (the default) matches probePlayers [0] in
# crsd/configs/experiment/exp_evprobe.json: every seat is neutral and sees the same
# rules and the same p, so one seat per game buys the measurement while six seats buy
# six times the bill. "all" probes every agent; a comma-separated list also works.
_PROBE_SEATS_SPEC = os.environ.get("CRG_PROBE_SEATS", "0").strip().lower()
PROBE_SEATS = (tuple(range(N_PLAYERS)) if _PROBE_SEATS_SPEC == "all"
               else _probe_int_list("CRG_PROBE_SEATS", _PROBE_SEATS_SPEC))
_BAD_PROBE_SEATS = [s for s in PROBE_SEATS if s < 0 or s >= N_PLAYERS]
if _BAD_PROBE_SEATS:
    raise SystemExit("CRG_PROBE_SEATS is outside 0..%d: %s"
                     % (N_PLAYERS - 1, ", ".join(str(s) for s in _BAD_PROBE_SEATS)))
if PROBE_CATEGORIES and not (PROBE_ROUNDS and PROBE_SEATS):
    raise SystemExit("CRG_PROBE is on but CRG_PROBE_ROUNDS/CRG_PROBE_SEATS select "
                     "nothing to ask")
# The probe earns a folder suffix for the same reason the template variant does.
# A probe run plays the BASELINE condition (probe questions are separate, stateless
# calls that never enter the history), so without a suffix it lands in the very
# folder baseline data already lives in -- and downstream `to_wide_csv.py` reads the
# experiment name off that folder, so E2 games would be merged into the verified
# baseline frame. The checkpoint signature already refuses to resume across this
# boundary; this is the other half, on the output path.
PROBE_SUFFIX = ("_probe-" + "-".join(PROBE_CATEGORIES)) if PROBE_CATEGORIES else ""

EXPERIMENT_NAME = (("exp_baseline" if TEMPLATE_VARIANT == "baseline"
                    else "exp_" + TEMPLATE_VARIANT)
                   + PROBE_SUFFIX + SEAT_SUFFIX + TEMP_SUFFIX)

_SCRIPTED_PROBE_SEATS = [s for s in PROBE_SEATS
                         if SEAT_MODELS and is_scripted_seat(SEAT_MODELS[s])]
if PROBE_CATEGORIES and _SCRIPTED_PROBE_SEATS:
    # A policy has nothing to comprehend. Asking one anyway would grade a seat that
    # never read the prompt, and the probe accuracy of the shard would be a fiction.
    raise SystemExit("CRG_PROBE asks seat(s) %s, but CRG_SEAT_MODELS makes them "
                     "scripted: point CRG_PROBE_SEATS at an llm seat (%s) instead."
                     % (", ".join(str(s) for s in _SCRIPTED_PROBE_SEATS),
                        ", ".join(str(s) for s in SEAT_LLM_SEATS) or "none"))

# Fan-out caps for the time/state axes, copied from the crsd probe configs
# (maxSeats 4, maxPastRounds null). They do not touch rules/value, which ask one
# question each per round.
PROBE_MAX_SEATS = 4
PROBE_MAX_PAST_ROUNDS = None

# --- Per-model output cap (REQUIRED for expensive models) -------------------
# The Model Proxy RESERVES `max_output_tokens x output price` up front, so an
# UNSET cap makes a pricey model 403 with "max estimated cost of operation
# ($3.200045) exceeds your available quota (based on max_output_tokens)" even
# though the real spend is cents. Observed on claude-opus-4-7 (2026-08-12).
# Reasoning models need a generous cap or they return EMPTY content: measured
# gemini-3.6-flash empty at 64 tokens, gemini-3.5-flash unable to emit a
# parseable answer at 2000; 6000 was enough for every flash variant tested.
_REASONING_HINTS = ("reasoning", "thinking", "-pro", "opus", "gpt-5.5",
                    "gpt-5.6", "3-flash", "3.5-flash", "3.6-flash")
_MAX_OUT_EXPLICIT = int(os.environ.get("CRG_MAX_OUT", "0"))
MAX_OUT = _MAX_OUT_EXPLICIT or (
    6000 if any(h in MODEL.lower() for h in _REASONING_HINTS) else 512
)


def _max_out_for(model_slug):
    """Output cap for ONE seat's model.

    The cap is a property of the MODEL, not of the run: a mixed group that puts a
    reasoning model in seat P4 while the selected model is a cheap one would get
    EMPTY content from P4 at cap 512 (measured on gemini-3.6-flash), and raising the
    cap for everybody would instead risk the cost-reservation 403 on the cheap seats.
    So the same hint rule is applied per slug. An explicit CRG_MAX_OUT still wins for
    every seat -- it is the manual override for exactly the case the hints miss.
    With CRG_SEAT_MODELS unset this can only ever return MAX_OUT.
    """
    if _MAX_OUT_EXPLICIT or model_slug is None or model_slug == MODEL:
        return MAX_OUT
    return 6000 if any(h in model_slug.lower() for h in _REASONING_HINTS) else 512

# --- Self-healing knobs -----------------------------------------------------
# Retry budget for ONE llm call hit by a transient proxy error (429/503/5xx/heavy
# load). "6" is exactly the number this file hard-coded before the knob existed, so
# the default keeps the historical behaviour.
MAX_CALL_ATTEMPTS = int(os.environ.get("CRG_MAX_ATTEMPTS", "6"))
# What happens when ONE game still fails after every retry:
#   "abort" (default, historical): re-raise, the run stops, committed shards stay.
#   "skip":  report the dead cell on the [CRG_ERROR] stream and keep sweeping, so a
#            single poisoned cell cannot cost the shard its remaining games.
# Either way nothing is fabricated: a failed cell is simply absent from games.csv
# and `fill_missing.py` picks it up later.
ON_GAME_ERROR = os.environ.get("CRG_ON_GAME_ERROR", "abort").strip().lower()

# Bump whenever checkpoint compatibility changes. Version 2 invalidated shards made
# before re-auth was guaranteed to preserve the selected model; version 3 adds the
# prompt variant + prompt fingerprint, so a variant run can no longer resume (and
# silently absorb) a baseline shard.
CHECKPOINT_SCHEMA_VERSION = 3

# --- Kaggle push-validation guard ------------------------------------------
# `kaggle b t push` executes the task ONCE on the server default model
# (observed: gemini-3-flash-preview) over the FULL sweep before the task is
# usable. 60 games on that slow reasoning model would cost ~$11 and time out
# the kernel, so collapse to a 1-game smoke for THAT model only. The real run
# (`kaggle b t run -m <model>` -> sets LLM_DEFAULT=<model>) gets the full sweep;
# gpt/claude/deepseek/other Geminis are unaffected. Local CRG_* overrides win.
_no_overrides = not any(os.environ.get(k) for k in ("CRG_RISKS", "CRG_LANGS", "CRG_REPS"))
if "gemini-3-flash-preview" in MODEL and _no_overrides:
    RISKS, LANGS, REPS, REP_START = [0.9], ["en"], 1, 0

# PHAI tinh SAU guard: guard doi REPS/REP_START, neu tinh truoc thi validation
# luc push van chay du so rep cua shard (5 van thay vi 1) tren mot reasoning
# model cham -> ton 5x va co the timeout ca lenh push.
REP_RANGE = range(REP_START, REP_START + REPS)

# Per-round decision concurrency. DEFAULT 1 = fully sequential (reliable on
# capacity-limited proxies like gpt-nano, which 429s under bursts). Set
# CRG_CONCURRENCY>1 (e.g. 6) for the parallel path on higher-capacity models.
_CONCURRENCY = int(os.environ.get("CRG_CONCURRENCY", "1"))

# risk -> crsd game name, so game_id matches the open-source arm's join key.
GAME_NAME = {0.90: "crsd_milinski_high_risk",
             0.50: "crsd_milinski_medium_risk",
             0.10: "crsd_milinski_low_risk"}

# Non-baseline prompt arms mirror the naming the open-weight arm already uses:
# crsd/configs/game/crsd_milinski_high_risk_nohint.json IS the open-source no-anchor
# cell, so the frontier no-anchor cell must carry the SAME name or the two arms
# cannot be joined at all. It also keeps game_id unique once the arms meet in one
# frame -- which is the whole point of E1: baseline and nohint rows for the same
# (risk, language, rep) would otherwise share a game_id and one would win silently.
# Baseline gets "", so the three original names are byte-for-byte untouched.
# A mixed group appends its seat tag on top of that, for the same reason: the
# baseline row and the best-response row of the same (risk, language, rep) would
# otherwise share a game_id, and once the two frames meet one of them wins silently.
# The probe appends here too: a probe game and a baseline game of the same
# (risk, language, rep) are two INDEPENDENT observations -- the proxy does not
# reproduce text from a seed -- so sharing a game_id would let one overwrite the
# other the moment the two frames are concatenated.
GAME_NAME_SUFFIX = (("" if TEMPLATE_VARIANT == "baseline"
                     else "_" + TEMPLATE_VARIANT)
                    + PROBE_SUFFIX + SEAT_SUFFIX + TEMP_SUFFIX)


def game_name(risk: float) -> str:
    """Game name used inside game_id.

    The three original levels keep their exact names -- they are the join key against
    the open-source arm and results/ already holds data under them, so they must not
    move. Any additional level (the revision sweep adds p=0.3 and p=0.7 for reviewer
    Q8) gets a generated name like `crsd_milinski_p030_risk`. The open-source arm has
    no such cell, so there is nothing to collide with and nothing to join.

    A non-baseline prompt arm appends GAME_NAME_SUFFIX (e.g.
    `crsd_milinski_high_risk_nohint`), matching that arm's own game configs.
    """
    key = round(float(risk), 2)
    if key in GAME_NAME:
        return GAME_NAME[key] + GAME_NAME_SUFFIX
    return f"crsd_milinski_p{int(round(key * 100)):03d}_risk" + GAME_NAME_SUFFIX

# Proxy models (esp. non-Gemini on staging) intermittently return 429/503. Retry
# those with exponential backoff; a call that STILL fails is reported on the
# [CRG_ERROR] stream and re-raised, and the sweep loop decides (CRG_ON_GAME_ERROR)
# whether that kills the run or only the cell.
_TRANSIENT = ("429", "503", "500", "502", "504", "overloaded",
              "unavailable", "not reachable", "rate limit", "heavy load",
              "timeout", "timed out", "connection", "temporarily")
# A cost-reservation 403 is NOT retryable and NOT an auth problem: the proxy
# reserves max_output_tokens x output price BEFORE the call, so the only fixes are a
# lower CRG_MAX_OUT or an account with quota left.
_QUOTA_MARKERS = ("max estimated cost", "available quota", "max_output_tokens")
_HTTP_CODE_RE = re.compile(r"\b([45]\d\d)\b")


# %% =====================  STDOUT PROGRESS PROTOCOL  ==================================
# `kaggle b t log <task> -m <model>` is the ONLY live channel from a running server
# task to the local machine, so progress is a stdout LINE protocol:
#   <TAG> <one JSON object>\n
# json.dumps escapes newlines and ensure_ascii keeps the line pure ASCII, so a record
# can never be split across lines nor mangled by the Windows console codepage. These
# lines are ADDITIONAL: every human-readable print stays exactly where it was.
_TAG_START = "[CRG_START]"          # once, after checkpoints are restored
_TAG_PROGRESS = "[CRG_PROGRESS]"    # once per completed game (resumed ones included)
_TAG_ERROR = "[CRG_ERROR]"          # every distinct failure mode, recoverable or not
_TAG_DONE = "[CRG_DONE]"            # once, terminal, status=ok|partial|aborted


def _clip(value, limit=400):
    """Single-line, bounded string for the JSON error stream."""
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[:limit] + "...<clipped>"


def _emit(tag, payload):
    """Write ONE machine-parseable record. sys.stdout.write of a single string is
    atomic under the ThreadPoolExecutor path; print() writes twice and can interleave."""
    try:
        body = json.dumps(payload, ensure_ascii=True, default=str)
    except Exception as exc:                     # logging must never kill a run
        body = json.dumps({"emit_error": _clip(exc)})
    sys.stdout.write(tag + " " + body + "\n")
    sys.stdout.flush()


def _http_code(message):
    """First 4xx/5xx code mentioned by an exception message, else None."""
    m = _HTTP_CODE_RE.search(str(message))
    return int(m.group(1)) if m else None


def _emit_error(kind, message, http=None, fatal=False, ctx=None, **extra):
    """Every distinct failure mode goes through here. 503/429/403/404 all surfaced
    identically as 'Errored' in the Kaggle UI, which has already cost this repo days
    of misdiagnosis -- so the HTTP code and a `kind` are always carried."""
    record = {"kind": kind,
              "http": http if http is not None else _http_code(message),
              "fatal": bool(fatal),
              "message": _clip(message)}
    if ctx:
        for k in ("game_id", "risk", "lang", "rep", "round", "player",
                  "question_id", "seat_model"):
            if k in ctx:
                record[k] = ctx[k]
    record.update(extra)
    _emit(_TAG_ERROR, record)


def _progress_record(done, total, row, resumed, parse_failed, game_cost_nano,
                     cost_nano, elapsed_s, game_elapsed_s=None, probes=None):
    """One completed game, in the shape the local supervisor parses."""
    record = {
        "done": done,
        "total": total,
        "model": row.get("model"),
        "risk": row.get("risk_probability"),
        "lang": row.get("language"),
        "rep": row.get("rep"),
        "game_id": row.get("game_id"),
        "reached": bool(row.get("target_reached")),
        "group_total": row.get("group_total"),
        "disaster": bool(row.get("catastrophe")),
        "parse_failed": parse_failed,
        "game_cost_usd": round((game_cost_nano or 0) / 1e9, 6),
        "cost_usd": round((cost_nano or 0) / 1e9, 6),
        "elapsed_s": elapsed_s,
        "game_elapsed_s": game_elapsed_s,
        "resumed": bool(resumed),
    }
    if probes is not None:
        # Probe keys appear only on a probe run, so the record a supervisor already
        # parses is unchanged for every other sweep.
        record["probes"] = len(probes)
        record["probes_correct"] = sum(1 for p in probes if p.get("correct"))
    return record


# %% =====================  PROMPT (exact copy of crsd_en.txt / crsd_vn.txt)  ==========
TEMPLATE_EN = """{persona}: [{personaText}

]{framing}: [You are a participant in a paid economics experiment. The only thing that matters to you is your own final cash payoff. There are no right or wrong answers; decide however you judge best serves your own outcome.

]You are {currentPlayerName}, player {playerPosition} of {nPlayers}, in a group experiment that simulates a collective-risk social dilemma.

At the start, each player privately receives an endowment of {endowment} monetary units. Your final cash payoff depends on the rules below. {gameLength}: [The game lasts exactly {nRounds} rounds.]

Each round, all {nPlayers} players decide simultaneously and in private how much to put into a shared "climate account". The only amounts allowed are {contributionOptions}.

The group's target: by the end of the game, the combined contributions of all {nPlayers} players must reach at least {target} (an average of {fairShare} per player per round).
- If the group reaches {target}: every player keeps, in cash, whatever they did not contribute (for example, contributing {fairShare} every round leaves you {fairShareKept} at the end).
- If the group does not reach {target}: the computer runs a lottery: with probability {riskPercent}% the group is hit by a disaster and every player loses all of their remaining money (final cash payoff 0); with the remaining {safePercent}% probability, each player keeps their remaining money.
- Money put into the climate account is gone for good and is never refunded, whether or not the target is reached.

After each round, all {nPlayers} contributions for that round are revealed to everyone. Names are hidden, but each player always appears in the same fixed position. Players cannot talk to or message each other.

Current state:
- Round {currentRound} of {nRounds}.
- Your remaining money: {remainingEndowment}.
{showCumulative}: [- The climate account so far holds {groupAccount} of the {target} target.]
{history}: [
Previous rounds (each player keeps the same position; you are position {playerPosition}):
{historyText}
]
Now decide your contribution for round {currentRound}. Allowed choices: {contributionOptions}.
Output only your decision as a final line:
CONTRIBUTION: <one of {contributionOptions}>
"""

TEMPLATE_VN = """{persona}: [{personaText}

]{framing}: [Bạn là người tham gia một thí nghiệm kinh tế có trả tiền thật. Điều duy nhất quan trọng với bạn là số tiền mặt cuối cùng của chính bạn. Không có đáp án đúng hay sai; hãy tự quyết định theo cách bạn thấy có lợi nhất cho mình.

]Bạn là {currentPlayerName}, người chơi số {playerPosition} trong {nPlayers} người, trong một thí nghiệm mô phỏng "tình thế lưỡng nan rủi ro tập thể".

Khi bắt đầu, mỗi người chơi được nhận riêng một khoản vốn {endowment} đơn vị tiền. Số tiền mặt cuối cùng bạn thực nhận phụ thuộc vào các quy tắc dưới đây. {gameLength}: [Trò chơi kéo dài đúng {nRounds} vòng.]

Mỗi vòng, tất cả {nPlayers} người chơi đồng thời và riêng tư quyết định đóng bao nhiêu vào một "quỹ khí hậu" chung. Các mức được phép chỉ gồm {contributionOptions}.

Mục tiêu của nhóm: đến cuối trò chơi, tổng đóng góp của cả {nPlayers} người chơi phải đạt ít nhất {target} (trung bình {fairShare} mỗi người mỗi vòng).
- Nếu nhóm đạt {target}: mỗi người giữ lại (bằng tiền mặt) toàn bộ số tiền mình không đóng góp (ví dụ, đóng {fairShare} mỗi vòng thì cuối cùng bạn còn {fairShareKept}).
- Nếu nhóm không đạt {target}: máy tính quay xổ số: với xác suất {riskPercent}% nhóm gặp thảm hoạ và mọi người chơi mất tất cả số tiền còn lại (tiền mặt cuối cùng = 0); với xác suất {safePercent}% còn lại, mỗi người giữ được số tiền còn lại của mình.
- Tiền đã bỏ vào quỹ khí hậu là mất hẳn, không bao giờ được hoàn lại, dù có đạt mục tiêu hay không.

Sau mỗi vòng, đóng góp của cả {nPlayers} người trong vòng đó được hiển thị cho mọi người. Danh tính được ẩn, nhưng mỗi người luôn xuất hiện ở cùng một vị trí cố định. Người chơi không được trao đổi hay nhắn tin cho nhau.

Tình trạng hiện tại:
- Vòng {currentRound} trên tổng {nRounds}.
- Số tiền còn lại của bạn: {remainingEndowment}.
{showCumulative}: [- Quỹ khí hậu đến lúc này có {groupAccount} trên mục tiêu {target}.]
{history}: [
Các vòng trước (mỗi người giữ nguyên vị trí; bạn là vị trí {playerPosition}):
{historyText}
]
Bây giờ hãy quyết định mức đóng góp của bạn cho vòng {currentRound}. Các lựa chọn hợp lệ: {contributionOptions}.
Chỉ xuất ra quyết định của bạn ở dòng cuối:
CONTRIBUTION: <một trong các giá trị {contributionOptions}>
"""

# %% ---------- nohint variant: baseline MINUS the equal-split anchors ----------
# E1 asks what the equal-split anchor does to behaviour. That is only interpretable
# if the anchor is the ONLY thing that moved, so this template is DERIVED from
# TEMPLATE_EN by deleting exactly two spans -- never retyped, which is how a stray
# comma turns an anchor experiment into a wording experiment:
#   1. the fair-share gloss on the target sentence, and
#   2. the worked example on the target-reached payoff line.
# Each deletion swallows its own leading space and leaves the sentence's full stop in
# place. That is precisely how crsd/prompts/crsd_nohint_en.txt differs from
# crsd_en.txt -- verified by diff: those two lines, and nothing else in the file.
_ANCHOR_SPANS = (
    " (an average of {fairShare} per player per round)",
    " (for example, contributing {fairShare} every round leaves you "
    "{fairShareKept} at the end)",
)


def _strip_anchors(template):
    """TEMPLATE_EN minus the equal-split anchors, or a loud failure.

    Every span must occur EXACTLY once. A silent no-op is the worst outcome available
    here: the no-anchor arm would quietly play the baseline prompt, spend the shard's
    real money, and return a null result that reads like evidence about the anchor.
    """
    text = template
    for span in _ANCHOR_SPANS:
        found = text.count(span)
        if found != 1:
            raise SystemExit(
                "nohint template: expected exactly 1 occurrence of %r in the baseline "
                "template, found %d -- the baseline wording changed, so the no-anchor "
                "arm must be re-derived (and re-checked against "
                "crsd/prompts/crsd_nohint_en.txt) before it is run." % (span, found))
        text = text.replace(span, "")
    return text


TEMPLATE_EN_NOHINT = _strip_anchors(TEMPLATE_EN)

# The panel is English-only, so there is deliberately NO Vietnamese no-anchor
# template. TEMPLATE_VN stays exactly as it is; a nohint sweep that asks for "vn" is
# refused below rather than quietly served the baseline Vietnamese wording (which
# still carries the anchor, and would poison the contrast).
# %% ---------- E6: two paraphrases of the baseline wording ----------
# W6 in the risk register: every result so far rests on ONE way of phrasing the game.
# E6 re-runs the pivotal cells under two rewrites. For the contrast to mean "wording",
# the rewrites must change nothing else, so both keep every placeholder, every
# conditional block, the equal-split anchor (that is E1's variable, not E6's), and the
# decision tail byte for byte -- changing the answer-format instructions would mix the
# parse rate into what should be a wording effect. _check_paraphrase below enforces
# all four, at import, before a single paid call.
# para1 is plainer and re-ordered; para2 is formal and legalistic. They differ from the
# baseline and from each other in register and sentence structure, not in content.
TEMPLATE_EN_PARA1 = """{persona}: [{personaText}

]{framing}: [This is a paid economics experiment. The only thing you care about is the cash you walk away with. Nothing here is graded; choose whatever you judge leaves you best off.

]In this study you take the role of {currentPlayerName}, seated in position {playerPosition} among {nPlayers} participants, in a task that models a collective-risk social dilemma.

Every participant starts with a private endowment of {endowment} monetary units, and what you finally take home is set by the rules that follow. {gameLength}: [There are exactly {nRounds} rounds, no more and no fewer.]

In every round the {nPlayers} of you choose, at the same time and without seeing each other's choices, an amount to move into a common "climate account". The permitted amounts are {contributionOptions}.

What the group has to achieve: the contributions of all {nPlayers} participants, added up across the whole game, must come to {target} or more (an average of {fairShare} per player per round).
- Should the group get to {target}: each participant walks away, in cash, with whatever they held back (for example, contributing {fairShare} every round leaves you {fairShareKept} at the end).
- Should the group fall short of {target}: a lottery is drawn. With probability {riskPercent}% a disaster strikes and every participant loses all the money they still hold (final cash payoff 0); with the remaining {safePercent}% probability, everyone keeps what they still hold.
- Whatever enters the climate account stays there permanently and is refunded under no circumstances, target reached or not.

Once a round closes, the {nPlayers} amounts contributed in it are shown to everyone. Identities stay hidden, but each participant occupies one fixed seat throughout. Participants cannot talk to or message one another.

Where things stand:
- This is round {currentRound} out of {nRounds}.
- Money still in your hands: {remainingEndowment}.
{showCumulative}: [- The climate account currently stands at {groupAccount} against the {target} target.]
{history}: [
Earlier rounds (seats never change; yours is position {playerPosition}):
{historyText}
]
Now decide your contribution for round {currentRound}. Allowed choices: {contributionOptions}.
Output only your decision as a final line:
CONTRIBUTION: <one of {contributionOptions}>
"""

TEMPLATE_EN_PARA2 = """{persona}: [{personaText}

]{framing}: [You have joined a paid economics experiment. The sole criterion that matters to you is your own end-of-game cash. No answer is correct or incorrect; act in whatever manner you consider most advantageous to yourself.

]You have been assigned the role of {currentPlayerName} and hold position {playerPosition} out of {nPlayers} in a group task modelling a collective-risk social dilemma.

Each participant is granted, in private, a starting sum of {endowment} monetary units. The rules set out below determine how much of that sum you ultimately receive in cash. {gameLength}: [Play continues for precisely {nRounds} rounds.]

Round by round, the {nPlayers} participants independently and secretly nominate a sum to transfer into a jointly held "climate account". The admissible sums are {contributionOptions}, and no others.

The collective requirement: when play ends, the total transferred by the {nPlayers} participants must amount to no less than {target} (an average of {fairShare} per player per round).
- In the event that the total reaches {target}: every participant retains as cash the portion of their endowment that was never transferred (for example, contributing {fairShare} every round leaves you {fairShareKept} at the end).
- In the event that the total falls below {target}: the computer conducts a draw. With probability {riskPercent}% a disaster occurs and the residual holdings of every participant are forfeited in full (final cash payoff 0); with the complementary probability of {safePercent}%, each participant retains their residual holdings.
- Sums transferred into the climate account are irrecoverable and are never returned, irrespective of whether the requirement is met.

At the close of each round, the {nPlayers} amounts transferred during that round are disclosed to all participants. Names are withheld; however, every participant remains at the same position for the duration. Communication of any kind between participants is not permitted.

Present position:
- Round {currentRound} of {nRounds} is underway.
- Funds you still retain: {remainingEndowment}.
{showCumulative}: [- Holdings of the climate account to date: {groupAccount}, measured against the {target} requirement.]
{history}: [
Record of previous rounds (positions are fixed; yours is position {playerPosition}):
{historyText}
]
Now decide your contribution for round {currentRound}. Allowed choices: {contributionOptions}.
Output only your decision as a final line:
CONTRIBUTION: <one of {contributionOptions}>
"""

TEMPLATE_SETS = {
    "baseline": {"en": TEMPLATE_EN, "vn": TEMPLATE_VN},
    "nohint": {"en": TEMPLATE_EN_NOHINT},
    "para1": {"en": TEMPLATE_EN_PARA1},
    "para2": {"en": TEMPLATE_EN_PARA2},
}
TEMPLATES = TEMPLATE_SETS[TEMPLATE_VARIANT]

# LANGS is final by this point (the push-validation guard above may have narrowed it),
# so an impossible sweep dies at import instead of at the first Vietnamese cell --
# after the English half of the shard has already been paid for.
_MISSING_LANGS = [lang for lang in LANGS if lang not in TEMPLATES]
if _MISSING_LANGS:
    raise SystemExit(
        "CRG_TEMPLATE=%s has no template for language(s): %s (available: %s). The "
        "panel is English-only, so run this variant with CRG_LANGS=en."
        % (TEMPLATE_VARIANT, ", ".join(_MISSING_LANGS), ", ".join(sorted(TEMPLATES))))

# %% ---------- probe template: the decision tail swapped for a question ----------
# crsd asks its probes with crsd_comprehension_<lang>.txt, which IS crsd_<lang>.txt
# with the "now decide" tail replaced by a question plus an ANSWER: anchor (verified
# by diff: those five lines, and two computedTotals blocks the baseline instrument
# never renders). So the probe template here is DERIVED from the ACTIVE decision
# template exactly the way the nohint arm is derived -- never retyped. A probe that
# described the game even slightly differently from the decision prompt would measure
# comprehension of a prompt no agent ever played.
_DECISION_TAIL_EN = (
    "Now decide your contribution for round {currentRound}. Allowed choices: "
    "{contributionOptions}.\n"
    "Output only your decision as a final line:\n"
    "CONTRIBUTION: <one of {contributionOptions}>\n"
)
_QUESTION_TAIL_EN = (
    "Now answer the following question about the game described above. This is a "
    "comprehension check, not a move: do not make any contribution decision.\n"
    "{questionText}\n"
    "Answer with a single final line in exactly this format, and write nothing after "
    "it:\n"
    "ANSWER: <your answer>\n"
)


def _placeholders(text):
    return set(re.findall(r"\{(\w+)\}", text))


def _block_keys(text):
    return set(re.findall(r"\{(\w+)\}: \[", text))


def _check_paraphrase(name, text):
    """A paraphrase must change the WORDING and nothing else, or fail loudly.

    E6 asks whether the cooperation result survives a rewrite of the prompt, and that
    is only interpretable if the rewrite left the GAME identical. The cheap silent
    failure is a paraphrase that quietly drops a placeholder -- the round number, the
    risk, the anchor -- and so changes what the agent was actually told, while still
    rendering into fluent English and costing a full shard to discover.
    """
    miss = _placeholders(TEMPLATE_EN) - _placeholders(text)
    extra = _placeholders(text) - _placeholders(TEMPLATE_EN)
    if miss or extra:
        raise SystemExit(
            "template %r: placeholder set differs from the baseline (missing %s, "
            "unexpected %s) -- the paraphrase changed the GAME, not just the wording."
            % (name, sorted(miss), sorted(extra)))
    if _block_keys(text) != _block_keys(TEMPLATE_EN):
        raise SystemExit(
            "template %r: conditional block keys differ from the baseline (%s vs %s)."
            % (name, sorted(_block_keys(text)), sorted(_block_keys(TEMPLATE_EN))))
    found = text.count(_DECISION_TAIL_EN)
    if found != 1:
        raise SystemExit(
            "template %r: must carry the baseline decision tail exactly once (found "
            "%d). Rewording the answer-format instructions would fold the parse rate "
            "into what is supposed to be a wording effect." % (name, found))
    if text == TEMPLATE_EN:
        raise SystemExit("template %r is byte-identical to the baseline, so it is not "
                         "a paraphrase and its arm would re-measure the control."
                         % name)
    try:
        text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise SystemExit(
            "template %r carries non-ASCII text (%s). Kaggle's push reads this file "
            "with the system codepage and has already died on that once." % (name, exc))
    return text


for _para_name in ("para1", "para2"):
    _check_paraphrase(_para_name, TEMPLATE_SETS[_para_name]["en"])
if TEMPLATE_SETS["para1"]["en"] == TEMPLATE_SETS["para2"]["en"]:
    raise SystemExit("para1 and para2 are identical: E6 would run one arm twice.")


def _to_probe_template(template):
    """Decision template -> comprehension template, or a loud failure.

    The silent no-op is the expensive outcome here as well: a probe prompt that kept
    the "CONTRIBUTION:" tail would be answered with a move, every answer would fail to
    parse, and the shard would report 0% comprehension.
    """
    found = template.count(_DECISION_TAIL_EN)
    if found != 1:
        raise SystemExit(
            "probe template: expected exactly 1 decision tail in the active template, "
            "found %d -- the prompt wording changed, so the probe template must be "
            "re-derived (and re-checked against crsd/prompts/crsd_comprehension_en.txt)"
            " before the probe arm is run." % found)
    return template.replace(_DECISION_TAIL_EN, _QUESTION_TAIL_EN)


# The question bank is ENGLISH ONLY: this file must not grow non-ASCII text (Kaggle's
# push reads it with the system codepage, which has already killed one push), and the
# E2 panel is English anyway. A probe run that asks for another language is refused
# here rather than served English questions about a Vietnamese prompt.
PROBE_TEMPLATES = ({"en": _to_probe_template(TEMPLATES["en"])}
                   if PROBE_CATEGORIES and "en" in TEMPLATES else {})
if PROBE_CATEGORIES:
    _PROBE_MISSING_LANGS = [lang for lang in LANGS if lang not in PROBE_TEMPLATES]
    if _PROBE_MISSING_LANGS:
        raise SystemExit(
            "CRG_PROBE is on but there is no probe question bank for language(s): %s "
            "(available: %s). The bank is English-only, so run the probe arm with "
            "CRG_LANGS=en." % (", ".join(_PROBE_MISSING_LANGS),
                               ", ".join(sorted(PROBE_TEMPLATES)) or "none"))

_BLOCK_RE = re.compile(r"\{(\w+)\}:\s*\[(.*?)\]", re.DOTALL)
# Anchored `CONTRIBUTION:` parse — identical to crsd/engine/round.py.
_CONTRIB_LINE_RE = re.compile(r"^\s*CONTRIBUTION\s*[:=]\s*(\d+)", flags=re.IGNORECASE | re.MULTILINE)


def _fmt(x) -> str:
    """40.0 -> '40'; 0.9 -> '0.9' (avoid stray .0 in the prompt)."""
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def _resolve_blocks(template: str, enabled: dict) -> str:
    return _BLOCK_RE.sub(lambda m: m.group(2) if enabled.get(m.group(1), False) else "", template)


def build_history_text(history, player_index, language):
    """Fixed-position display (P1..Pn, own seat marked), NO cumulative — matches
    crsd build_history_text with show_cumulative=False, show_individual=True."""
    if not history:
        return ""
    you = "(bạn)" if language == "vn" else "(you)"
    lines = []
    for r, rc in enumerate(history, start=1):
        labeled = ", ".join(f"P{i + 1}{you if i == player_index else ''}={_fmt(c)}"
                            for i, c in enumerate(rc))
        lines.append((f"Vòng {r}: {labeled}." if language == "vn" else f"Round {r}: {labeled}."))
    return "\n".join(lines)


def assemble_prompt(language, player_index, current_round, history, risk):
    """Faithful reimplementation of crsd/engine/prompt.build_prompt for the BASELINE
    condition (neutral persona, no framing, full_history, showCumulative=False)."""
    return _assemble(TEMPLATES[language], language, player_index, current_round,
                     history, risk)


def assemble_probe_prompt(language, player_index, current_round, history, risk,
                          question_text):
    """The SAME prompt the seat decides on, with the decision tail replaced by one
    comprehension question. Same rules, same state, same history -- only the tail
    differs, which is exactly how crsd builds its comprehension prompts."""
    return _assemble(PROBE_TEMPLATES[language], language, player_index, current_round,
                     history, risk, question_text=question_text)


def _assemble(template, language, player_index, current_round, history, risk,
              question_text=""):
    """Shared renderer. `question_text` is empty for every decision prompt, and the
    decision templates carry no {questionText} placeholder, so the rendered bytes of
    a decision prompt are unchanged by its existence."""
    own_total = sum(r[player_index] for r in history)
    remaining = max(0.0, ENDOWMENT - own_total)
    risk_percent = round(risk * 100)
    denom = N_PLAYERS * N_ROUNDS
    fair_share = (TARGET / denom) if denom else 0.0
    fair_share_kept = ENDOWMENT - fair_share * N_ROUNDS
    has_history = current_round > 1 and bool(history)

    enabled = {
        "persona": False,            # personas_default -> empty -> block dropped
        "framing": False,
        "gameLength": N_ROUNDS_KNOWN,
        "history": has_history,
        "showCumulative": False,     # pool hidden (baseline)
        # Harmless on both templates shipped here (the probe tail is inlined, not a
        # block); present so a later block-form question tail cannot render empty.
        "question": bool(question_text),
    }
    text = _resolve_blocks(template, enabled)

    replacements = {
        "personaText": "",
        "currentPlayerName": PLAYER_NAMES[player_index],
        "playerPosition": player_index + 1,
        "nPlayers": N_PLAYERS,
        "endowment": _fmt(ENDOWMENT),
        "nRounds": N_ROUNDS,
        "contributionOptions": ", ".join(_fmt(o) for o in OPTIONS),
        "target": _fmt(TARGET),
        "fairShare": _fmt(fair_share),
        "fairShareKept": _fmt(fair_share_kept),
        "riskPercent": risk_percent,
        "safePercent": 100 - risk_percent,
        "currentRound": current_round,
        "groupAccount": _fmt(sum(sum(r) for r in history)),
        "remainingEndowment": _fmt(remaining),
        "historyText": build_history_text(history, player_index, language),
        "questionText": question_text or "",
    }
    for k, v in replacements.items():
        text = text.replace("{" + k + "}", str(v))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def parse_contribution(response, options=OPTIONS):
    """(value, parse_failed) — anchored on the last formatted `CONTRIBUTION:` line;
    value outside the option set is a protocol violation -> parse_failed. Copied from
    crsd/engine/round.parse_contribution so both arms score decisions identically."""
    opts = [int(o) for o in options]
    if not response:
        return opts[0], True
    line_matches = _CONTRIB_LINE_RE.findall(response)
    if line_matches:
        v = int(line_matches[-1])
        if v in opts:
            return v, False
        return opts[0], True
    nums = [int(x) for x in re.findall(r"\d+", response)]
    valid = [n for n in nums if n in opts]
    if valid:
        return valid[-1], False
    return opts[0], True


def extract_reasoning(text):
    """Reasoning = response minus the CONTRIBUTION line(s) (baseline has no NOTE)."""
    if not text:
        return ""
    lines = [ln for ln in text.splitlines()
             if not re.match(r"\s*CONTRIBUTION\s*[:=]", ln, flags=re.IGNORECASE)]
    return "\n".join(lines).strip()


# %% =====================  PROBE BANK (== crsd/engine/comprehension.py, EN)  =========
# Port of the comprehension question bank for ENGLISH. This file does not import crsd
# by design, so the question texts, the enumeration and the ground truth are
# reproduced here; crsd/tests/test_kaggle_probe.py walks BOTH banks over the same game
# states and asserts that every question id, every parameter set, every rendered
# question and every ground-truth value agrees, item by item. That test, not this
# comment, is what keeps the two from drifting.
#
# The two "value" questions are the point of experiment E2 and neither is answerable
# from the prompt: the agent has to multiply a probability by money. For the Milinski
# parameters (endowment 40, target 120, 6 players, 10 rounds) the closed forms are
#   value_defect_ev  = round((1 - p) * 40)          -> 36 / 20 / 4  at p = .1 / .5 / .9
#   value_compare    = 1 if 40 - 120/6 > (1-p)*40 else 2 (0 on a tie)
#                                                   ->  2 /  0 / 1  at p = .1 / .5 / .9
PROBE_SHOW_CUMULATIVE = False    # baseline: the running pool is hidden from the agent
PROBE_SHOW_INDIVIDUAL = True     # baseline: per-seat contributions ARE shown

# Anchored on a formatted `ANSWER:` line at the start of a line, last match wins --
# models like to think out loud and only then commit, same as parse_contribution.
_ANSWER_LINE_RE = re.compile(r"^\s*ANSWER\s*[:=]\s*(.+?)\s*$",
                             flags=re.IGNORECASE | re.MULTILINE)


def _parse_probe_int(captured):
    """FIRST integer on the ANSWER line ('the answer is X'), not the last: it has to
    survive a trailing gloss like 'ANSWER: 80 (still needed to reach 120)'."""
    nums = re.findall(r"-?\d+", captured)
    if not nums:
        return None, True
    return int(nums[0]), False


def _parse_probe_int_set(captured):
    nums = re.findall(r"-?\d+", captured)
    if not nums:
        return None, True
    return set(int(x) for x in nums), False


def _parse_probe_yesno(captured):
    """English yes/no. crsd also accepts the other four panel languages, whose markers
    are not ASCII; the probe arm here is English-only for exactly that reason.
    Negation is tested first, matching crsd's order."""
    s = captured.strip().lower()
    if re.search(r"\bno\b", s):
        return False, False
    if re.search(r"\byes\b", s):
        return True, False
    return None, True


def parse_probe_answer(text, kind):
    """(parsed, parse_failed) from the LAST formatted `ANSWER:` line."""
    if not text:
        return None, True
    matches = _ANSWER_LINE_RE.findall(text)
    if not matches:
        return None, True
    captured = matches[-1].strip()
    if kind == "int":
        return _parse_probe_int(captured)
    if kind == "int_set":
        return _parse_probe_int_set(captured)
    if kind == "yesno":
        return _parse_probe_yesno(captured)
    return None, True


def score_probe_answer(parsed, ground_truth, kind, parse_failed):
    """Grade one probe. A malformed answer counts as WRONG (conservative); the record
    keeps parse_failed so a sensitivity pass can drop those rows instead."""
    if parse_failed or parsed is None:
        return False
    if kind == "int":
        return int(parsed) == int(ground_truth)
    if kind == "int_set":
        return set(parsed) == set(int(x) for x in ground_truth)
    if kind == "yesno":
        return bool(parsed) == bool(ground_truth)
    return False


def _probe_jsonable(value):
    """set -> sorted list, so a parsed int_set survives json.dumps."""
    if isinstance(value, set):
        return sorted(value)
    return value


def _probe_fmt_num(x):
    """40.0 -> '40' (crsd comprehension._fmt_num, reproduced exactly)."""
    return str(int(x)) if float(x).is_integer() else str(x)


def _probe_representative_seats(history, player_index, n_players, k):
    """Up to `k` REPRESENTATIVE seats (0-based): self + the free-rider (lowest total)
    + the altruist (highest) + one in the middle, so the contrast is kept without
    asking about all six. Deterministic given the history -- a rerun asks the same."""
    if k <= 0:
        return []
    others = [s for s in range(n_players) if s != player_index]
    if not history:
        return ([player_index] + others)[:k]
    totals = [sum(row[s] for row in history) for s in range(n_players)]
    by_total = sorted(others, key=lambda s: (totals[s], s))
    picks = [player_index]
    if by_total:
        picks += [by_total[0], by_total[-1], by_total[len(by_total) // 2]]
    seen, uniq = set(), []
    for s in picks + others:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
        if len(uniq) >= k:
            break
    return uniq[:k]


def _probe_select_rounds(num_past, cap):
    """Past rounds 1..num_past, evenly sampled down to `cap` (first and last always
    kept) when there are more than that. Deterministic."""
    rounds = list(range(1, num_past + 1))
    if cap is None or num_past <= cap or cap <= 1:
        return rounds
    idxs = sorted(set(round(j * (num_past - 1) / (cap - 1)) for j in range(cap)))
    return [rounds[i] for i in idxs]


def _probe_seat_label(x_pos, player_index):
    """'P3', or 'P1 (you)' for the seat being probed (English marker, as in crsd)."""
    if x_pos - 1 == player_index:
        return "P%d (you)" % x_pos
    return "P%d" % x_pos


def _probe_pool(history):
    return int(sum(sum(row) for row in history))


def _probe_own_total(history, player_index):
    return int(sum(row[player_index] for row in history))


def _ev_compare_gt(risk):
    """Ground truth for value_compare (crsd comprehension._ev_compare_gt).

    Contributing your fair share leaves `endowment - target/n_players` for certain;
    withholding everything is worth `(1 - p) * endowment` on average. 1 = cooperating
    pays more, 2 = withholding pays more, 0 = exactly equal.
    """
    keep_if_cooperate = ENDOWMENT - (TARGET / N_PLAYERS)
    ev_if_defect = (1.0 - risk) * ENDOWMENT
    if abs(keep_if_cooperate - ev_if_defect) < 1e-9:
        return 0
    return 1 if keep_if_cooperate > ev_if_defect else 2


# Question texts, copied verbatim from the "en" entries of crsd's _Q_TEXT.
_PROBE_Q_TEXT = {
    "rules_actions":
        "Which contribution amounts are you allowed to choose each round?",
    "rules_endowment":
        "How many monetary units did each player receive as their starting endowment?",
    "rules_target":
        "What combined total must all players reach by the end of the game to avoid "
        "the risk?",
    "rules_n_rounds":
        "How many rounds does the game last in total?",
    "rules_risk_pct":
        "If the group does NOT reach the target, what is the percent chance (0-100) "
        "that everyone loses all of their remaining money?",
    "rules_payoff_disaster":
        "If the group fails to reach the target and the disaster does strike, what is "
        "your final cash payoff?",
    "rules_max_contrib":
        "What is the largest amount any single player may put into the climate account "
        "in one round?",
    "rules_min_contrib":
        "What is the smallest amount any single player may put into the climate "
        "account in one round?",
    "value_defect_ev":
        "Suppose you contribute 0 in every round and the group ends up NOT reaching "
        "the target. On average, over many such games, how much cash would you end up "
        "with? Give a single whole number.",
    "value_compare":
        "Compare two strategies for the whole game. (A) You contribute 2 in every one "
        "of the {n} rounds and the group reaches the target, so you finish with {keep} "
        "for certain. (B) You contribute 0 in every round and the group does not reach "
        "the target, so you keep {endow} unless the disaster strikes. Which gives the "
        "higher AVERAGE final cash? Answer 1 if A is higher, 2 if B is higher, 0 if "
        "they are exactly equal.",
    "time_round":
        "Which round is the game currently in (the round you are about to play)?",
    "time_action_i":
        "In round {i}, how much did the player in position {seat} put into the climate "
        "account?",
    "time_own_action_i":
        "In round {i}, how much did YOU (position P{pnum}) put into the climate "
        "account?",
    "time_round_total_i":
        "In round {i}, what was the combined total that all {n} players put into the "
        "climate account?",
    "state_pool":
        "Across all rounds played so far, what is the total amount currently in the "
        "climate account (all players combined)?",
    "state_remaining_to_target":
        "How much more must the group still put into the climate account to reach the "
        "target?",
    "state_X_total":
        "Across all rounds so far, what is the total amount the player in position "
        "{seat} has put into the climate account?",
    "state_own_total":
        "Across all rounds so far, what is the total amount YOU (position P{pnum}) "
        "have put into the climate account?",
    "state_own_remaining":
        "Right now, how much of your own endowment do you have left (the part not yet "
        "contributed)?",
    "state_count_p":
        "Across all rounds so far, how many times has the player in position {seat} "
        "contributed exactly {p}?",
    "state_rounds_left":
        "Including the current round, how many rounds are left to play?",
    "state_target_reached":
        "Has the group already reached the target? Answer yes or no.",
}


class ProbeQuestion(object):
    """One kind of comprehension question -- the server-side twin of crsd's
    QuestionSpec, minus the cfg argument (the game constants are module-level here).

      render(risk, history, r, pi, params) -> the question as the agent reads it
      truth (risk, history, r, pi, params) -> the engine's answer
      enum  (history, r, pi)               -> the parameter sets to ask about
      answerable                           -> is the answer PRINTED in the prompt
                                              (read) or must it be COMPUTED (add)
    """

    __slots__ = ("id", "category", "answer_kind", "render", "ground_truth", "enum",
                 "answerable")

    def __init__(self, qid, category, answer_kind, render, ground_truth, enum,
                 answerable):
        self.id = qid
        self.category = category
        self.answer_kind = answer_kind
        self.render = render
        self.ground_truth = ground_truth
        self.enum = enum
        self.answerable = answerable


def _probe_enum_none(H, r, pi):
    """One question, no parameters (also covers crsd's scalar-state enumerator)."""
    return [{}]


def _probe_enum_time_rounds(H, r, pi):
    return [{"i": i} for i in _probe_select_rounds(r - 1, PROBE_MAX_PAST_ROUNDS)]


def _probe_enum_time_action(H, r, pi):
    past = _probe_select_rounds(r - 1, PROBE_MAX_PAST_ROUNDS)
    seats = _probe_representative_seats(H, pi, N_PLAYERS, PROBE_MAX_SEATS)
    others = [s for s in seats if s != pi]        # 'you' is time_own_action_i already
    return [{"i": i, "x": s + 1} for i in past for s in others]


def _probe_enum_state_x_total(H, r, pi):
    if r <= 1:
        return []                                  # no history yet -> nothing to ask
    seats = _probe_representative_seats(H, pi, N_PLAYERS, PROBE_MAX_SEATS)
    return [{"x": s + 1} for s in seats if s != pi]


def _probe_enum_state_count(H, r, pi):
    if r <= 1:
        return []
    seats = _probe_representative_seats(H, pi, N_PLAYERS, PROBE_MAX_SEATS)
    return [{"x": s + 1, "p": int(p)} for s in seats for p in OPTIONS]


# Order matters and matches crsd's REGISTRY exactly: it fixes the per-seat question
# ordinal that keys each probe's sampling seed.
PROBE_REGISTRY = [
    # ---------------- RULES (the answer is printed in the rules) ----------------
    ProbeQuestion(
        "rules_actions", "rules", "int_set",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["rules_actions"],
        lambda risk, H, r, pi, p: set(int(o) for o in OPTIONS),
        _probe_enum_none, True),
    ProbeQuestion(
        "rules_endowment", "rules", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["rules_endowment"],
        lambda risk, H, r, pi, p: int(round(ENDOWMENT)),
        _probe_enum_none, True),
    ProbeQuestion(
        "rules_target", "rules", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["rules_target"],
        lambda risk, H, r, pi, p: int(round(TARGET)),
        _probe_enum_none, True),
    ProbeQuestion(
        "rules_n_rounds", "rules", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["rules_n_rounds"],
        lambda risk, H, r, pi, p: int(N_ROUNDS),
        _probe_enum_none, True),
    ProbeQuestion(
        "rules_risk_pct", "rules", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["rules_risk_pct"],
        lambda risk, H, r, pi, p: int(round(risk * 100)),
        _probe_enum_none, True),
    ProbeQuestion(
        "rules_payoff_disaster", "rules", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["rules_payoff_disaster"],
        lambda risk, H, r, pi, p: 0,
        _probe_enum_none, True),
    ProbeQuestion(
        "rules_max_contrib", "rules", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["rules_max_contrib"],
        lambda risk, H, r, pi, p: int(max(OPTIONS)),
        _probe_enum_none, True),
    ProbeQuestion(
        "rules_min_contrib", "rules", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["rules_min_contrib"],
        lambda risk, H, r, pi, p: int(min(OPTIONS)),
        _probe_enum_none, True),

    # ------------- VALUE (experiment E2: probability x money, not readable) -------
    ProbeQuestion(
        "value_defect_ev", "value", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["value_defect_ev"],
        lambda risk, H, r, pi, p: int(round((1.0 - risk) * ENDOWMENT)),
        _probe_enum_none, False),
    ProbeQuestion(
        "value_compare", "value", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["value_compare"].format(
            n=int(N_ROUNDS),
            keep=_probe_fmt_num(ENDOWMENT - (TARGET / (N_PLAYERS * N_ROUNDS))
                                * N_ROUNDS),
            endow=_probe_fmt_num(ENDOWMENT)),
        lambda risk, H, r, pi, p: _ev_compare_gt(risk),
        _probe_enum_none, False),

    # ---------------------------- TIME (history lookup) --------------------------
    ProbeQuestion(
        "time_round", "time", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["time_round"],
        lambda risk, H, r, pi, p: int(r),
        _probe_enum_none, True),
    ProbeQuestion(
        "time_action_i", "time", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["time_action_i"].format(
            i=p["i"], seat=_probe_seat_label(p["x"], pi)),
        lambda risk, H, r, pi, p: int(H[p["i"] - 1][p["x"] - 1]),
        _probe_enum_time_action, PROBE_SHOW_INDIVIDUAL),
    ProbeQuestion(
        "time_own_action_i", "time", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["time_own_action_i"].format(
            i=p["i"], pnum=pi + 1),
        lambda risk, H, r, pi, p: int(H[p["i"] - 1][pi]),
        _probe_enum_time_rounds, PROBE_SHOW_INDIVIDUAL),
    ProbeQuestion(
        "time_round_total_i", "time", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["time_round_total_i"].format(
            i=p["i"], n=N_PLAYERS),
        lambda risk, H, r, pi, p: int(sum(H[p["i"] - 1])),
        _probe_enum_time_rounds, False),

    # ------------------- STATE (cumulative arithmetic: read != add) --------------
    ProbeQuestion(
        "state_pool", "state", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["state_pool"],
        lambda risk, H, r, pi, p: _probe_pool(H),
        _probe_enum_none, PROBE_SHOW_CUMULATIVE),
    ProbeQuestion(
        "state_remaining_to_target", "state", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["state_remaining_to_target"],
        lambda risk, H, r, pi, p: int(max(0, int(round(TARGET)) - _probe_pool(H))),
        _probe_enum_none, False),
    ProbeQuestion(
        "state_X_total", "state", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["state_X_total"].format(
            seat=_probe_seat_label(p["x"], pi)),
        lambda risk, H, r, pi, p: int(sum(row[p["x"] - 1] for row in H)),
        _probe_enum_state_x_total, False),
    ProbeQuestion(
        "state_own_total", "state", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["state_own_total"].format(pnum=pi + 1),
        lambda risk, H, r, pi, p: _probe_own_total(H, pi),
        _probe_enum_none, False),
    ProbeQuestion(
        "state_own_remaining", "state", "int",   # CONTROL: this number IS in the prompt
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["state_own_remaining"],
        lambda risk, H, r, pi, p: int(round(max(
            0.0, float(ENDOWMENT) - float(_probe_own_total(H, pi))))),
        _probe_enum_none, True),
    ProbeQuestion(
        "state_count_p", "state", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["state_count_p"].format(
            seat=_probe_seat_label(p["x"], pi), p=_fmt(p["p"])),
        lambda risk, H, r, pi, p: int(sum(1 for row in H
                                          if int(row[p["x"] - 1]) == int(p["p"]))),
        _probe_enum_state_count, False),
    ProbeQuestion(
        "state_rounds_left", "state", "int",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["state_rounds_left"],
        lambda risk, H, r, pi, p: int(N_ROUNDS - r + 1),
        _probe_enum_none, False),
    ProbeQuestion(
        "state_target_reached", "state", "yesno",
        lambda risk, H, r, pi, p: _PROBE_Q_TEXT["state_target_reached"],
        lambda risk, H, r, pi, p: bool(_probe_pool(H) >= int(round(TARGET))),
        _probe_enum_none, False),
]

PROBE_REGISTRY_BY_ID = {q.id: q for q in PROBE_REGISTRY}


def probe_items(current_round, history, player_index):
    """[(question, params)] to ask ONE seat at ONE round, in crsd REGISTRY order.

    Note the one deliberate difference from crsd: there, only rules/value are gated to
    the checkpoint rounds while time/state are asked every round. Here EVERY axis is
    gated by CRG_PROBE_ROUNDS, so the probe bill of a shard is fixed and knowable
    before the run instead of growing with the round number.
    """
    out = []
    for question in PROBE_REGISTRY:
        if question.category not in PROBE_CATEGORIES:
            continue
        for params in question.enum(history, current_round, player_index):
            out.append((question, params))
    return out


def probes_per_game():
    """EXACT number of extra llm calls one game costs.

    The enumeration depends on the ROUND and the caps, never on what the agents
    actually contributed, so this is knowable before a run (budgeting) and checkable
    against a resumed shard afterwards (nothing lost, nothing re-asked).
    """
    if not PROBE_CATEGORIES:
        return 0
    total = 0
    for r in PROBE_ROUNDS:
        history = [[0] * N_PLAYERS for _ in range(r - 1)]
        for pid in PROBE_SEATS:
            total += len(probe_items(r, history, pid))
    return total


# %% =====================  SCRIPTED SEATS (== crsd/models/scripted.py)  ============
# Five deterministic, non-LLM policies. They exist so a group can be MIXED without
# paying for six models: the best-response arm puts ONE llm seat against five
# scripted opponents, which costs 10 calls per game instead of 60 and -- the point --
# makes the opponents' behaviour KNOWN, so the distance between what the model did
# and what it should have done is a number rather than an impression.
#
# This file does not import crsd (by design), so the policies are reimplemented here.
# crsd/tests/test_kaggle_seat_models.py walks BOTH implementations over the same game
# states and asserts they choose the same contribution, case by case. That test, not
# this comment, is what keeps the two from drifting.


def _nearest_option(value, options=OPTIONS):
    """`value` rounded to the nearest LEGAL contribution; a tie keeps the LOWER one.

    Same rule as crsd's nearest_option: conservative, deterministic, and matching
    parse_contribution's own fallback (opts[0]), so a policy can never produce an
    amount that would have been rejected coming from a model.
    """
    opts = sorted(int(o) for o in options)
    if not opts:
        return 0
    best = opts[0]
    best_d = abs(float(value) - best)
    for o in opts[1:]:
        d = abs(float(value) - o)
        if d < best_d - 1e-9:            # strict -> a tie KEEPS the lower option
            best, best_d = o, d
    return best


def _scripted_fair_share():
    """Equal-split contribution per player per round = target / (n x rounds).

    The same {fairShare} the prompt quotes (Milinski: 120 / (6 x 10) = 2).
    """
    denom = N_PLAYERS * N_ROUNDS
    return (TARGET / denom) if denom else 0.0


def scripted_decide(policy, risk, history, player_index):
    """What `policy` contributes now. Deterministic and seed-free, so a replayed cell
    faces exactly the same opponents, move for move.

    always_0 / always_2 / always_4
        the constant, snapped to the legal option set.
    ev_maximiser
        risk-neutral pure expected value, and deliberately BLIND to the history:
        paying a fair share all game costs target/n for certain, contributing nothing
        is worth (1-p)*endowment on average, so it withholds while
        (1-p)*endowment > target/n and pays its share otherwise. With the Milinski
        parameters (E=40, target=120, n=6) the switch sits at p* = 0.5. This is the
        normative benchmark, not an equilibrium.
    conditional_cooperator
        round 1 pays a fair share; from round 2 it matches the MEAN of the OTHER
        seats' previous round, snapped to the legal set.
    """
    name = scripted_policy_name(policy)
    if name not in SCRIPTED_POLICIES:
        raise ValueError("unknown scripted policy %r (known: %s)"
                         % (policy, ", ".join(SCRIPTED_POLICIES)))
    if name == "always_0":
        return _nearest_option(0)
    if name == "always_2":
        return _nearest_option(2)
    if name == "always_4":
        return _nearest_option(4)
    if name == "ev_maximiser":
        share_cost = (TARGET / N_PLAYERS) if N_PLAYERS else 0.0
        if (1.0 - float(risk)) * ENDOWMENT > share_cost:
            return _nearest_option(0)
        return _nearest_option(_scripted_fair_share())
    # conditional_cooperator
    if not history:
        return _nearest_option(_scripted_fair_share())
    last = list(history[-1])
    others = [float(c) for i, c in enumerate(last) if i != player_index]
    mean = (sum(others) / len(others)) if others else 0.0
    return _nearest_option(mean)


def scripted_response_text(policy, value):
    """The reply a scripted seat hands back instead of a model's text.

    Byte-shape copied from crsd's render_response: an audit line naming the policy,
    then the anchored CONTRIBUTION line the parser accepts. So turns.jsonl reads the
    same in both arms, re-parsing a scripted turn yields the same number, and a
    reader can always see WHICH policy produced the move.
    """
    return "[%s%s]\nCONTRIBUTION: %s" % (SCRIPTED_PREFIX,
                                          scripted_policy_name(policy), _fmt(value))


# %% =====================  SEED SCHEME (== crsd)  =====================
def sampling_seed(rep, agent_idx, round_number):
    seed = BASE_SEED + rep
    return (seed * SAMPLING_SEED_STRIDE + round_number * 100 + agent_idx) % SAMPLING_SEED_MOD


# The proxy token expires ~1h < a full 60-game run. The key is baked into the model
# client at construction, so on a 401 we refresh .env AND rebuild the client in place.
_LLM = None                                          # current model client (task sets it)
_AUTH_ERR = ("expired token", "authentication", "unauthorized", "401",
             "invalid api key", "invalid_api_key", "403")

# Extra seat clients, only ever populated when CRG_SEAT_MODELS names a slug other
# than the selected one. The proxy is OpenAI-compatible and the model slug travels in
# the request BODY, so a second model needs no second credential and no second URL:
# kaggle_benchmarks.kaggle.models.load_model(slug) builds a client on the SAME
# MODEL_PROXY_URL + MODEL_PROXY_API_KEY that load_default_model() used, with a
# different slug baked in. Keyed by slug, so two seats on one model share a client --
# and so _reauth() has an exact list of what to rebuild when the token rolls over.
_SEAT_CLIENTS = {}


def _build_seat_client(model_slug):
    """One client for `model_slug`, on the CURRENT proxy credential.

    Construction is local work -- it builds an http client, it does not call the
    proxy -- so every seat client can be built up front (see the preflight in the
    task body) and a typo'd slug or a missing credential surfaces before a cent is
    spent. What this does NOT settle is whether the production proxy will SERVE a
    slug other than the one `kaggle b t run -m` selected: that only shows up on the
    first real call, as an http error whose [CRG_ERROR] record carries seat_model.
    """
    from kaggle_benchmarks.kaggle.models import load_model
    try:
        client = load_model(model_slug)
    except Exception as exc:
        _emit_error("seat_client_failed", exc, fatal=True, seat_model=model_slug,
                    hint="the seat's slug could not be turned into a client; check "
                         "CRG_SEAT_MODELS, or make that seat scripted:<policy> -- a "
                         "scripted seat needs no client at all")
        raise
    got = getattr(client, "model", None)
    if got is not None and got != model_slug:
        # Same reason _reauth verifies its rebuilt client: a seat that quietly played
        # a different model would file its turns under the wrong name, which is
        # unrecoverable data corruption rather than a failed run.
        _emit_error("model_drift", "seat client built on '%s', expected '%s'"
                    % (got, model_slug), fatal=True, expected=model_slug, got=got,
                    seat_model=model_slug)
        raise RuntimeError("seat client for %r reports model %r" % (model_slug, got))
    return client


def _client_for(model_slug):
    """The client that must serve `model_slug`.

    None -- and the run-selected MODEL -- resolve to the global `_LLM`: the only
    client a default run ever has, and the one _reauth() rebuilds in place. So with
    CRG_SEAT_MODELS unset every call takes exactly the path it took before this
    function existed. Any other slug gets its own client, built once and cached.
    Two threads racing to build the same slug under CRG_CONCURRENCY build it twice
    and one wins; the client holds no per-call state, so that costs nothing.
    """
    if model_slug is None or model_slug == MODEL:
        return _LLM
    client = _SEAT_CLIENTS.get(model_slug)
    if client is None:
        client = _build_seat_client(model_slug)
        _SEAT_CLIENTS[model_slug] = client
    return client


def _reauth():
    """Refresh the proxy token and rebuild the client so a long run survives expiry."""
    global _LLM
    print("[auth] token rejected -> `kaggle b auth -y` + rebuild client ...", flush=True)
    subprocess.run(["kaggle", "b", "auth", "-y"], capture_output=True, text=True)
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)                   # pull the fresh MODEL_PROXY_API_KEY
    except Exception:
        pass
    # `kaggle b auth` also rewrites LLM_DEFAULT in .env. Re-pin the task-selected
    # model after loading the new credential or a long run can silently switch to
    # the account default model at the first token refresh.
    os.environ["LLM_DEFAULT"] = MODEL
    from kaggle_benchmarks.kaggle.models import load_default_model
    _LLM = load_default_model()                      # selected MODEL + refreshed key
    # Verify, do not trust. The client carries the model it was built with, and a
    # refresh that quietly downgraded to the account default would file every
    # remaining game under the SELECTED model's name while a different model played
    # it -- unrecoverable data corruption, worse than an abort.
    rebuilt = getattr(_LLM, "model", None)
    if rebuilt is not None and rebuilt != MODEL:
        _emit_error("model_drift",
                    "re-auth rebuilt the client on '%s', expected '%s'" % (rebuilt, MODEL),
                    fatal=False, expected=MODEL, got=rebuilt)
        from kaggle_benchmarks.kaggle.models import load_model
        _LLM = load_model(MODEL)                     # force the selected model back
        rebuilt = getattr(_LLM, "model", None)
        if rebuilt is not None and rebuilt != MODEL:
            _emit_error("model_drift", "cannot restore model '%s' (client reports "
                        "'%s')" % (MODEL, rebuilt), fatal=True, expected=MODEL,
                        got=rebuilt)
            raise RuntimeError("re-auth cannot restore model %r (client reports %r) "
                               "- refusing to keep sweeping under the wrong model"
                               % (MODEL, rebuilt))
    # A seat client bakes the key in at construction as well, so a refresh that
    # rebuilt only `_LLM` would leave every other seat holding the dead token and
    # re-authing once per call for the rest of the run.
    for slug in list(_SEAT_CLIENTS):
        _SEAT_CLIENTS[slug] = _build_seat_client(slug)
    print("[auth] client rebuilt on model=%s (+%d seat client(s))"
          % (rebuilt or MODEL, len(_SEAT_CLIENTS)), flush=True)


def _call_llm(model_slug, prompt, seed, ctx=None, max_attempts=None,
               cap_override=None):
    """One free-text generation on ONE seat's model. Returns (text, usage).

    `model_slug` is None (or the run-selected MODEL) for every call a default run
    makes, which resolves to the rebuildable global client `_LLM` -- the historical
    path, unchanged. A mixed group passes the seat's own slug and gets that seat's
    own client, resolved on EVERY attempt so a token refresh mid-retry is picked up.

    Auto-reauths on token expiry; exponential backoff on transient 429/503/5xx; empty
    content gets its own budget; a cost-cap 403 is reported as its own kind because
    retrying it is useless. Every branch writes one [CRG_ERROR] record carrying the
    HTTP code.
    """
    if max_attempts is None:
        max_attempts = MAX_CALL_ATTEMPTS
    # The cap follows the MODEL, not the run: see _max_out_for. Equal to MAX_OUT for
    # every call a default run makes. `cap_override` is used by decide() to ESCALATE
    # the cap after a truncated reply -- retrying a cut-off answer at the same cap
    # just cuts it off again.
    cap = int(cap_override) if cap_override else _max_out_for(model_slug)
    if ctx is not None and model_slug is not None and (SEAT_MODELS
                                                       or model_slug != MODEL):
        # In a mixed group every [CRG_ERROR] record must name the seat's model, or a
        # failure cannot be attributed to the model that produced it.
        ctx = dict(ctx, seat_model=model_slug)
    attempt = 0
    auth_retries = 0
    # Empty content has its OWN retry budget. Measured 13-08-2026: opus-5 returns
    # empty content non-deterministically at BOTH cap 6000 and 16000 (same Vietnamese
    # cell; one shard died, its sibling finished), so it is a transient proxy/model
    # hiccup rather than an exhausted token budget. Sharing the transient budget
    # would let one burst of empties kill the run and lose the games NOT yet played.
    empty_retries = 0
    MAX_EMPTY_RETRIES = 15
    while True:
        attempt += 1
        text = None
        # Resolved outside the try: a seat whose client cannot be BUILT is not a
        # transient failure and must not be retried six times -- _build_seat_client
        # has already emitted its own fatal record naming the slug.
        client = _client_for(model_slug)
        try:
            with kbench.chats.new("turn", orphan=True) as chat:
                text = client.prompt(prompt, temperature=TEMPERATURE, seed=seed,
                                     extra_api_params={"max_completion_tokens": cap})
            if text is not None and text.strip():
                return text, chat.usage
            if text is not None:
                # HTTP 200 but NO text. Two known causes: the model spent its whole
                # output budget in a reasoning channel (gemini-3.6-flash at cap 64,
                # gpt-oss-120b at any cap), or an intermittent proxy/model hiccup
                # (opus-5 on Vietnamese prompts, at BOTH cap 6000 and 16000).
                # This must NEVER fall through to a parsed contribution -- run 1
                # fabricated all-zero "games" exactly that way. Retry generously on
                # its own budget, then fail loudly.
                empty_retries += 1
                if empty_retries > MAX_EMPTY_RETRIES:
                    _emit_error("empty_content_exhausted",
                                "%d consecutive empty replies at "
                                "max_completion_tokens=%d" % (empty_retries, cap),
                                http=200, fatal=True, ctx=ctx, cap=cap,
                                hint="raise CRG_MAX_OUT (--max-out) or lower "
                                     "CRG_CONCURRENCY; the proxy may be overloaded")
                    raise RuntimeError(
                        "empty-content %dx in a row: the model returned no text "
                        "(max_completion_tokens=%d). Not a token-budget problem if a "
                        "higher cap was already tried -- check the proxy."
                        % (empty_retries, cap))
                sleep_s = min(5 * empty_retries, 60)
                _emit_error("empty_content", "HTTP 200 with empty content", http=200,
                            fatal=False, ctx=ctx, attempt=empty_retries,
                            max_attempts=MAX_EMPTY_RETRIES, sleep_s=sleep_s,
                            cap=cap)
                print("[empty-content] %d/%d, waiting %ds then retrying (cap=%d)"
                      % (empty_retries, MAX_EMPTY_RETRIES, sleep_s, cap), flush=True)
                time.sleep(sleep_s)
                attempt -= 1          # does not consume the transient budget
                continue
            # Parallel path: contexts.enter can SWALLOW a proxy error inside a
            # worker thread (the run ContextVar does not propagate), leaving
            # text=None. Raise a synthetic transient so the backoff below retries.
            raise RuntimeError("503 no-text: proxy error swallowed under concurrency")
        except Exception as e:
            msg = str(e).lower()
            code = _http_code(e)
            # A cost-reservation 403 is NOT an auth failure. `_AUTH_ERR` contains
            # "403", so without this guard a quota 403 would burn six `kaggle b auth`
            # reauth cycles and then surface the wrong cause. Reauth cannot fix it:
            # lower CRG_MAX_OUT or use an account with quota left.
            if any(t in msg for t in _QUOTA_MARKERS):
                _emit_error("quota_cap_403", e, http=code or 403, fatal=True, ctx=ctx,
                            max_out=cap,
                            hint="the proxy reserves max_output_tokens x output price "
                                 "BEFORE the call: lower CRG_MAX_OUT (--max-out) or "
                                 "switch account. Retrying cannot help.")
                raise
            if any(t in msg for t in _AUTH_ERR):     # token expired -> refresh, don't burn budget
                auth_retries += 1
                _emit_error("auth_refresh", e, http=code or 401,
                            fatal=auth_retries > 6, ctx=ctx, attempt=auth_retries,
                            max_attempts=6)
                if auth_retries > 6:
                    raise
                _reauth()
                attempt -= 1
                continue
            if not any(t in msg for t in _TRANSIENT):
                _emit_error("unclassified", e, http=code, fatal=True, ctx=ctx,
                            attempt=attempt)
                raise
            if attempt >= max_attempts:
                _emit_error("transient_exhausted", e, http=code, fatal=True, ctx=ctx,
                            attempt=attempt, max_attempts=max_attempts)
                raise
            sleep_s = min(2 ** attempt, 30)
            _emit_error("transient", e, http=code, fatal=False, ctx=ctx,
                        attempt=attempt, max_attempts=max_attempts, sleep_s=sleep_s)
            time.sleep(sleep_s)


# Reply that ran INTO the output cap. This is the signal `parse_failed` cannot give:
# when a model reasons past the cap it is cut off BEFORE the `CONTRIBUTION:` line, and
# parse_contribution then falls through to its prose-scan rule (documented step 2) and
# happily returns a digit lifted out of the reasoning -- with parse_failed=False.
# Measured 10-09-2026 on qwen3-235b: 0.88% of turns, which is 39.5% of GAMES, every one
# of them recorded green. The average-token check cannot see it either (qwen averages
# 8 tokens against a 512 cap) because only the tail of the distribution overruns.
_CAP_TOLERANCE = 2          # providers occasionally report cap-1


def _hit_output_cap(usage, cap):
    out = getattr(usage, "output_tokens", None)
    return out is not None and cap and out >= cap - _CAP_TOLERANCE


def decide(model_slug, prompt, base_seed, ctx=None):
    """Free-text + `CONTRIBUTION:` parse + retry-on-parse-fail (fresh seed each retry),
    mirroring crsd/runner/batch. Returns (text, value, failed, tok_in, tok_out, cost).

    `model_slug` picks the seat's model (None = the run-selected one); every retry
    stays on that same model, so one seat's parse failures can never be answered by
    another seat's model.
    """
    tok_in = tok_out = cost = 0
    cap = _max_out_for(model_slug)
    text, usage = _call_llm(model_slug, prompt, base_seed, ctx=ctx)
    tok_in += usage.input_tokens or 0
    tok_out += usage.output_tokens or 0
    cost += usage.total_cost_nanodollars or 0
    value, failed = parse_contribution(text)
    truncated = _hit_output_cap(usage, cap)
    attempt = 0
    # Retry on EITHER condition. `truncated` is the one that matters in practice:
    # `failed` alone almost never fires, because a reply cut off mid-reasoning still
    # contains a 0/2/4 somewhere for the prose-scan rule to pick up.
    while (failed or truncated) and attempt < MAX_PARSE_RETRIES:
        attempt += 1
        if truncated:
            # Escalate, or the retry is cut off at exactly the same place.
            cap = min(cap * 4, MAX_RETRY_CAP)
            _emit_error("truncated_retry",
                        "reply hit the output cap before the CONTRIBUTION line",
                        http=200, fatal=False, ctx=ctx, attempt=attempt,
                        max_attempts=MAX_PARSE_RETRIES, cap=cap,
                        reply=_clip(text, 200))
        else:
            _emit_error("parse_retry", "no legal CONTRIBUTION line in the reply",
                        http=200, fatal=False, ctx=ctx, attempt=attempt,
                        max_attempts=MAX_PARSE_RETRIES, reply=_clip(text, 200))
        seed = (base_seed + attempt * RETRY_SEED_STEP) % SAMPLING_SEED_MOD
        text, usage = _call_llm(model_slug, prompt, seed, ctx=ctx, cap_override=cap)
        tok_in += usage.input_tokens or 0
        tok_out += usage.output_tokens or 0
        cost += usage.total_cost_nanodollars or 0
        value, failed = parse_contribution(text)
        truncated = _hit_output_cap(usage, cap)
    if truncated and not failed:
        # The prose-scan rule produced a value, but from a reply we KNOW was cut off
        # -- that number came out of the reasoning, not out of a decision. Force the
        # failure flag so the end-of-sweep assertion refuses the run instead of
        # shipping a fabricated contribution.
        failed = True
    if failed:
        # Recorded as parse_failed=1 (never silently dropped) and asserted on at the
        # end of the sweep: a run with parse failures is not a valid measurement.
        _emit_error("parse_failed", "no usable CONTRIBUTION after %d retries "
                    "(last cap=%d)" % (MAX_PARSE_RETRIES, cap), http=200,
                    fatal=False, ctx=ctx, reply=_clip(text, 200))
    return text, value, failed, tok_in, tok_out, cost


# %% =====================  ASK ONE ROUND'S PROBES  ===================================
# Probe seeds live in their own slice of the seed space so a probe can never draw the
# same sample as a decision. Offsets copied from crsd/engine/game.py.
PROBE_SEED_OFFSET = 700_000_000
PROBE_SEED_STRIDE = 10_000


def probe_seed(rep, agent_idx, round_number, q_ord):
    base = sampling_seed(rep, agent_idx, round_number)
    return (base + PROBE_SEED_OFFSET + q_ord * PROBE_SEED_STRIDE) % SAMPLING_SEED_MOD


def run_probes(model_slug, risk, language, rep, current_round, history, game_id,
               model_tag):
    """Ask and grade every probe due at `current_round`.

    Returns (records, tok_in, tok_out, cost); ([], 0, 0, 0) when the probe is off or
    this round is not a checkpoint. The caller invokes this AFTER the round's six
    decisions are already in hand and BEFORE the round is applied, so `history` is
    exactly the state the agents decided on. Each probe is its own orphan chat, so it
    cannot reach the decision it follows -- and the decision was already made anyway.

    A probe that cannot be answered at all (the proxy is down, or the model returns
    empty content past its retry budget) propagates the exception and kills the cell,
    which is the honest outcome: recording it as a wrong answer would put a
    fabricated failure into an accuracy measurement.
    """
    if not PROBE_CATEGORIES or current_round not in PROBE_ROUNDS:
        return [], 0, 0, 0

    jobs = []
    for pid in PROBE_SEATS:
        # q_ord restarts per seat, exactly as in crsd build_comprehension_prompts.
        for q_ord, (question, params) in enumerate(
                probe_items(current_round, history, pid)):
            jobs.append((pid, q_ord, question, params))
    if not jobs:
        return [], 0, 0, 0

    def _ask_one(job):
        pid, q_ord, question, params = job
        qtext = question.render(risk, history, current_round, pid, params)
        prompt = assemble_probe_prompt(language, pid, current_round, history, risk,
                                       qtext)
        seed = probe_seed(rep, pid, current_round, q_ord)
        ctx = {"game_id": game_id, "risk": risk, "lang": language, "rep": rep,
               "round": current_round, "player": PLAYER_NAMES[pid],
               "question_id": question.id}
        # A probe measures the comprehension of the seat that is playing, so it is
        # asked of THAT seat's model. (Scripted seats are refused at import, so a
        # probed seat always has one.)
        seat = SEAT_MODELS[pid] if SEAT_MODELS else model_slug
        text, usage = _call_llm(seat, prompt, seed, ctx=ctx)
        return job, qtext, seed, text, usage

    if _CONCURRENCY <= 1:
        results = [_ask_one(job) for job in jobs]
    else:
        with ThreadPoolExecutor(max_workers=_CONCURRENCY) as _ex:
            _futs = [_ex.submit(contextvars.copy_context().run, _ask_one, job)
                     for job in jobs]
            results = [f.result() for f in _futs]

    records = []
    tok_in = tok_out = cost = 0
    for (pid, q_ord, question, params), qtext, seed, text, usage in results:
        seat = SEAT_MODELS[pid] if SEAT_MODELS else model_slug
        tok_in += usage.input_tokens or 0
        tok_out += usage.output_tokens or 0
        cost += usage.total_cost_nanodollars or 0
        truth = question.ground_truth(risk, history, current_round, pid, params)
        parsed, failed = parse_probe_answer(text, question.answer_kind)
        correct = score_probe_answer(parsed, truth, question.answer_kind, failed)
        if failed:
            # Not fatal and not retried (crsd scores a malformed answer as wrong), but
            # never silent: a model that stops emitting ANSWER: lines turns the whole
            # probe into a measurement of formatting.
            _emit_error("probe_parse_failed", "no ANSWER line in the probe reply",
                        http=200, fatal=False,
                        ctx={"game_id": game_id, "risk": risk, "lang": language,
                             "rep": rep, "round": current_round,
                             "player": PLAYER_NAMES[pid],
                             "question_id": question.id},
                        reply=_clip(text, 200))
        record = {
            "game_id": game_id,
            "round": current_round,
            "player": PLAYER_NAMES[pid],
            "player_index": pid,
            "question_id": question.id,
            "category": question.category,
            "params": dict(params),
            "question_text": qtext,
            "raw_response": text or "",
            "parsed_answer": _probe_jsonable(parsed),
            "ground_truth": _probe_jsonable(truth),
            "correct": bool(correct),
            "parse_failed": bool(failed),
            "answer_kind": question.answer_kind,
            "answerable_from_prompt": bool(question.answerable),
            "language": language,
            "risk_probability": risk,
            "model": model_tag,
            "show_cumulative": PROBE_SHOW_CUMULATIVE,
            "sampling_seed": seed,
            "rep": rep,
        }
        if SEAT_MODELS:
            # Only a mixed run says anything about seats, so a probe record from any
            # other sweep is byte-for-byte what it always was.
            record["seat_model"] = seat
        records.append(record)
    return records, tok_in, tok_out, cost


def _probe_summary(probes):
    """Overall / per-question / per-risk accuracy -- the numbers E2 exists to produce,
    small enough to travel on the [CRG_DONE] line."""
    n = len(probes)
    if not n:
        return {"n_probes": 0, "probe_correct": 0, "probe_accuracy": None,
                "probe_parse_failed": 0}
    by_question = {}
    by_risk = {}
    for record in probes:
        for key, bucket in ((record.get("question_id"), by_question),
                            (record.get("risk_probability"), by_risk)):
            agg = bucket.setdefault(key, [0, 0])
            agg[0] += 1
            agg[1] += int(bool(record.get("correct")))
    correct = sum(1 for record in probes if record.get("correct"))
    return {
        "n_probes": n,
        "probe_correct": correct,
        "probe_accuracy": round(correct / n, 4),
        "probe_parse_failed": sum(1 for record in probes
                                  if record.get("parse_failed")),
        "probe_accuracy_by_question": {
            str(k): round(v[1] / v[0], 4) for k, v in sorted(
                by_question.items(), key=lambda kv: str(kv[0]))},
        "probe_accuracy_by_risk": {
            str(k): round(v[1] / v[0], 4) for k, v in sorted(
                by_risk.items(), key=lambda kv: str(kv[0]))},
    }


# %% =====================  ONE GAME (simultaneous within a round)  =====================
def play_game(model_slug, risk, language, rep, model_tag, turns_sink,
              probes_sink=None):
    """One complete game. `model_slug` is the model every seat plays (None = the
    run-selected one); when CRG_SEAT_MODELS is set it is overridden per seat, and a
    scripted seat is answered here without touching the proxy at all."""
    balances = [ENDOWMENT] * N_PLAYERS
    own_totals = [0] * N_PLAYERS
    history = []                                   # completed rounds only (lockstep)
    game_id = f"{game_name(risk)}__{model_tag}__{language}__rep{rep}"
    tok_in = tok_out = cost = 0
    parse_failed = 0

    for r in range(1, N_ROUNDS + 1):
        # All N prompts built from COMPLETED-round history -> genuinely simultaneous,
        # so the N per-round decisions are INDEPENDENT and run concurrently. Results
        # are gathered in fixed player order (ThreadPoolExecutor.map preserves input
        # order) and all bookkeeping/logging below stays single-threaded, so the output
        # is byte-identical to the sequential version (seeds fixed per (rep, pid, round);
        # history is only read inside the threads and appended after the batch).
        def _decide_one(pid, _r=r):
            prompt = assemble_prompt(language, pid, _r, history, risk)
            base_seed = sampling_seed(rep, pid, _r)
            seat = SEAT_MODELS[pid] if SEAT_MODELS else model_slug
            if SEAT_MODELS and is_scripted_seat(seat):
                # Resolved right here: no call, no token, no cost, and no way for a
                # transient 503 to kill the cell. The prompt is still built and still
                # logged, so a scripted turn carries exactly the fields an llm turn
                # does -- and the same fields the open-weight arm writes, which routes
                # its scripted seats through the same kind of stub.
                policy = scripted_policy_name(seat)
                value = scripted_decide(policy, risk, history, pid)
                return (pid, prompt, base_seed, scripted_response_text(policy, value),
                        value, False, 0, 0, 0)
            # The context travels with the call so every [CRG_ERROR] line names the
            # exact cell/round/seat that failed, instead of an anonymous 'Errored'.
            ctx = {"game_id": game_id, "risk": risk, "lang": language, "rep": rep,
                   "round": _r, "player": PLAYER_NAMES[pid]}
            text, value, failed, ti, to, cn = decide(seat, prompt, base_seed, ctx=ctx)
            return pid, prompt, base_seed, text, value, failed, ti, to, cn

        if _CONCURRENCY <= 1:
            # Sequential (default): transient 429/503 retried in-thread; reliable on
            # capacity-limited proxies. Byte-identical output to the parallel path.
            round_results = [_decide_one(pid) for pid in range(N_PLAYERS)]
        else:
            with ThreadPoolExecutor(max_workers=_CONCURRENCY) as _ex:
                # copy_context() per worker so the SDK active-run ContextVar propagates
                # into the threads (else contexts.enter swallows proxy errors and
                # _call_llm cannot retry). Futures in player order -> deterministic.
                _futs = [_ex.submit(contextvars.copy_context().run, _decide_one, pid)
                         for pid in range(N_PLAYERS)]
                round_results = [f.result() for f in _futs]

        round_contribs = []
        for pid, prompt, base_seed, text, value, failed, ti, to, cn in round_results:
            tok_in += ti; tok_out += to; cost += cn
            parse_failed += int(failed)

            remaining = ENDOWMENT - own_totals[pid]   # clamp like crsd (rarely binds)
            if value > remaining:
                allowed = [o for o in OPTIONS if o <= remaining]
                value = max(allowed) if allowed else 0
            round_contribs.append(value)

            turn = {
                "game_id": game_id, "round": r, "player": PLAYER_NAMES[pid],
                "contribution": value, "parse_failed": failed,
                "reasoning": extract_reasoning(text), "raw_response": text,
                "prompt": prompt, "logprobs": None, "latency_ms": None, "note": None,
                "sampling_seed": base_seed, "disposition": "neutral",
                "risk_probability": risk, "language": language,
                "persona_set": PERSONA_SET, "memory_mode": "full_history",
                "framing": False, "rep": rep,
            }
            if SEAT_MODELS:
                # Who actually produced this move. Same key as the open-weight arm's
                # TurnRecord.seat_model, and present ONLY on a mixed run, so every
                # other sweep writes the record it always wrote.
                turn["seat_model"] = SEAT_MODELS[pid]
            turns_sink.append(turn)
        # Comprehension probe (E2). Issued as its OWN llm call, AFTER every decision
        # of this round is already collected and BEFORE the round is applied -- so it
        # asks about exactly the state the agents decided on, and cannot influence a
        # single contribution. Off (and free) unless CRG_PROBE names a category.
        if probes_sink is not None:
            probe_records, p_ti, p_to, p_cn = run_probes(
                model_slug, risk, language, rep, r, history, game_id, model_tag)
            probes_sink.extend(probe_records)
            tok_in += p_ti; tok_out += p_to; cost += p_cn

        for pid in range(N_PLAYERS):               # apply AFTER all decide
            balances[pid] -= round_contribs[pid]
            own_totals[pid] += round_contribs[pid]
        history.append(round_contribs)

    pot = sum(own_totals)
    target_met = pot >= TARGET
    # Disaster lottery: first (only) draw of random.Random(BASE+rep) — keyed by rep,
    # so EN/VN & all risks share the uniform (CRN). Identical to crsd scoring.
    disaster = (not target_met) and (random.Random(BASE_SEED + rep).random() < risk)
    payoffs = [0.0] * N_PLAYERS if disaster else list(balances)

    game_row = {
        "game_id": game_id, "model": model_tag, "language": language,
        "risk_probability": risk, "persona_set": PERSONA_SET,
        "persona_seats": "N" * N_PLAYERS, "memory_mode": "full_history", "framing": 0,
        # float group_total/target + unrounded mean_payoff == crsd summarize_game types.
        "group_total": float(pot), "target": float(TARGET), "target_reached": int(target_met),
        "catastrophe": int(disaster), "mean_payoff": sum(payoffs) / N_PLAYERS,
        "rep": rep, "seed": BASE_SEED + rep,
    }
    if SEAT_MODELS:
        # Group composition, seat order preserved, "|"-separated exactly as
        # crsd/dataio/recorder.py writes it -- so games.csv describes the opponents
        # without anyone having to open turns.jsonl, and the two arms' columns match.
        game_row["seat_models"] = "|".join(SEAT_MODELS)
    return game_row, parse_failed, tok_in, tok_out, cost


# %% =====================  CHECKPOINT / RESUME  =====================
def _condition_key(risk, language, rep):
    """Canonical key for one completed experimental cell."""
    return f"{float(risk):.12g}|{language}|{int(rep)}"


def _checkpoint_filename(risk, language, rep):
    risk_tag = f"{float(risk):.12g}".replace(".", "p").replace("-", "m")
    return f"risk-{risk_tag}__lang-{language}__rep-{int(rep):03d}.json"


def _probe_fingerprint():
    """Hash of the probe INSTRUMENT: every question this arm will ask at every
    checkpoint round, as rendered, together with the answer the engine expects.

    Same job as _prompt_fingerprint and the same reason: a shard is only resumable if
    the questions AND the grading behind it were the ones this run would ask. Editing
    a question text, a ground truth or a fan-out cap moves this hash, so a half-done
    probe run cannot be finished with a different bank and reported as one number.
    Pure string work: no model call, no cost. Empty string when the probe is off, so
    the signature of a non-probe run is byte-for-byte what it always was.
    """
    if not PROBE_CATEGORIES:
        return ""
    parts = []
    for r in PROBE_ROUNDS:
        history = [[0, 2, 4, 0, 2, 4] for _ in range(r - 1)]
        for pid in PROBE_SEATS:
            for question, params in probe_items(r, history, pid):
                parts.append("%s|%s|%s|%s" % (
                    question.id, sorted(params.items()),
                    question.render(0.9, history, r, pid, params),
                    _probe_jsonable(question.ground_truth(0.9, history, r, pid,
                                                          params))))
    blob = "\x00".join(parts).encode("utf-8", "replace")
    return hashlib.sha256(blob).hexdigest()[:16]


def _prompt_fingerprint():
    """Hash of the RENDERED prompt for one fixed probe case.

    This is the half of the signature that cannot be forgotten. It changes whenever
    the instrument changes -- template wording, the template VARIANT selected by
    CRG_TEMPLATE, the block toggles in assemble_prompt (persona / framing /
    showCumulative) or any game constant that reaches the text -- so a later prompt
    arm cannot resume a baseline shard even if whoever added it forgot to set
    CRG_PROMPT_VARIANT. Pure string work: no model call, no cost.

    The probe walks the ACTIVE variant's languages in sorted order; for "baseline"
    that is exactly ("en", "vn"), so the historical hash of a baseline sweep is
    unchanged and existing baseline checkpoints still resume.
    """
    probe_history = [[0, 2, 4, 0, 2, 4]]
    parts = []
    for language in sorted(TEMPLATES):
        try:
            parts.append(assemble_prompt(language, 0, 2, probe_history, 0.9))
        except Exception:            # prompt builder changed shape -> hash raw templates
            parts.append(TEMPLATES.get(language, ""))
    blob = "\x00".join(parts).encode("utf-8", "replace")
    return hashlib.sha256(blob).hexdigest()[:16]


def _checkpoint_signature(model_tag):
    """Fields that must match before a shard is safe to resume.

    Anything that changes the MEANING of a result belongs here. Two entries earn
    their place the hard way: `prompt_variant` (declared) and `prompt_fingerprint`
    (measured). Without them a no-hint run and a baseline run of the same model
    produce the same signature, and the no-hint run silently inherits baseline games
    -- one games.csv holding two instruments, with nothing in the file to show it.
    """
    signature = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "model": model_tag,
        "prompt_variant": PROMPT_VARIANT,
        "prompt_fingerprint": _prompt_fingerprint(),
        "risks": RISKS,
        "languages": LANGS,
        "reps": REPS,
        "rep_start": REP_START,
        "max_completion_tokens": MAX_OUT,
        "n_players": N_PLAYERS,
        "n_rounds": N_ROUNDS,
        "endowment": ENDOWMENT,
        "target": TARGET,
        "options": list(OPTIONS),
        "temperature": TEMPERATURE,
        "base_seed": BASE_SEED,
        "persona_set": PERSONA_SET,
        "memory_mode": "full_history",
        "framing": False,
    }
    if SEAT_MODELS:
        # Added ONLY when the group is mixed, so every shard already on disk keeps
        # resuming: a normal run produces exactly the signature it did before this
        # block existed. When it IS set, who sat in the other five seats is part of
        # the instrument, so a baseline shard (or a shard of a DIFFERENT mix) no
        # longer matches and is replayed instead of silently adopted.
        signature["seats"] = {
            "models": list(SEAT_MODELS),
            "tag": SEAT_TAG,
            # Per-seat caps: a seat on another model may carry another output cap
            # (see _max_out_for), which is part of how that seat was measured.
            "max_completion_tokens": {slug: _max_out_for(slug)
                                      for slug in SEAT_FOREIGN_SLUGS},
        }
    if PROBE_CATEGORIES:
        # Added ONLY when the probe is on, so every shard already on disk keeps
        # resuming: a non-probe run produces exactly the signature it did before this
        # block existed. When it IS on, a shard written without probes (or with a
        # different bank, rounds or seats) no longer matches and is replayed rather
        # than adopted with its probe rows missing.
        signature["probe"] = {
            "categories": list(PROBE_CATEGORIES),
            "rounds": list(PROBE_ROUNDS),
            "seats": list(PROBE_SEATS),
            "max_seats": PROBE_MAX_SEATS,
            "max_past_rounds": PROBE_MAX_PAST_ROUNDS,
            "questions_per_game": probes_per_game(),
            "fingerprint": _probe_fingerprint(),
        }
    return signature


def _signature_diff(stored, expected):
    """Which signature fields disagree, so a rejected shard can say WHY it was
    rejected instead of only that it was."""
    if not isinstance(stored, dict):
        return {"signature": ["missing-or-invalid", "dict"]}
    keys = sorted(set(stored) | set(expected))
    return {k: [stored.get(k), expected.get(k)] for k in keys
            if stored.get(k) != expected.get(k)}


def _atomic_write_text(path, text):
    """Durably replace a text file without exposing a half-written checkpoint."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _write_materialized_outputs(out_dir, games, turns, probes=None):
    """Refresh analysis-friendly outputs after every durable game shard."""
    out_dir = Path(out_dir)
    turns_text = "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in turns)
    _atomic_write_text(out_dir / "turns.jsonl", turns_text)

    if PROBE_CATEGORIES:
        # One record per probe, in the same field shape as crsd's comprehension.jsonl
        # (plus `rep`, the frontier arm's join key) so the existing readers work on it.
        # Written only by a probe run: a baseline sweep leaves no probes.jsonl behind.
        probes_text = "".join(json.dumps(p, ensure_ascii=False) + "\n"
                              for p in (probes or []))
        _atomic_write_text(out_dir / "probes.jsonl", probes_text)

    if games:
        # Column set = ordered UNION over rows, missing cells left empty. Rows built
        # by this file are homogeneous, so the output is unchanged; the union only
        # matters on resume, where a shard written by an older schema would otherwise
        # make DictWriter raise and leave games.csv holding the previous, shorter
        # sweep. A half-written analysis file is the one thing worse than none.
        fieldnames = []
        for row in games:
            for k in row:
                if k not in fieldnames:
                    fieldnames.append(k)
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n",
                                restval="")
        writer.writeheader()
        writer.writerows(games)
        _atomic_write_text(out_dir / "games.csv", buf.getvalue())


def _save_game_checkpoint(checkpoint_dir, signature, row, game_turns,
                          parse_failed, tok_in, tok_out, cost, probes=None):
    """Commit one complete game. An interrupted game never produces a valid shard.

    The probe rows travel INSIDE the shard, not in a file of their own, so a game and
    its probes are committed by the same atomic write: a resumed run can never end up
    with the decisions of a game but not its answers, or the other way round.
    """
    payload = {
        "signature": signature,
        "condition_key": _condition_key(
            row["risk_probability"], row["language"], row["rep"]),
        "game": row,
        "turns": game_turns,
        "parse_failed": int(parse_failed),
        "usage_input_tokens": int(tok_in),
        "usage_output_tokens": int(tok_out),
        "usage_total_cost_nanodollars": int(cost),
    }
    if PROBE_CATEGORIES:
        payload["probes"] = list(probes or [])
    path = Path(checkpoint_dir) / _checkpoint_filename(
        row["risk_probability"], row["language"], row["rep"])
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def _load_game_checkpoints(checkpoint_dir, signature):
    """Load only complete, compatible shards and return them in sweep order.

    Returns (games, turns, stats, completed_keys, records). A shard is accepted only
    when every one of these holds, because a resumed run that mixes instruments or
    counts a game twice is far worse than one that re-runs a cell:
      - the signature matches EXACTLY (model, sweep, cap, prompt variant + hash);
      - its condition belongs to THIS sweep;
      - the game row carries a game_id no other shard has already claimed;
      - the row's own (risk, language, rep) agrees with the cell it is filed under;
      - it holds a full N_PLAYERS x N_ROUNDS turn block, every turn tagged with that
        same game_id -- a half-written game is replayed, never half-counted;
      - it holds exactly the number of probe rows this arm asks per game (0 when the
        probe is off), every one tagged with that same game_id -- so a resumed probe
        run neither loses answers nor re-asks (and re-pays for) the ones it has.
    Everything rejected is reported on stdout in both channels and simply re-run.
    """
    checkpoint_dir = Path(checkpoint_dir)
    expected_order = [
        _condition_key(risk, language, rep)
        for risk in RISKS for language in LANGS for rep in REP_RANGE
    ]
    expected = set(expected_order)
    expected_probes = probes_per_game()
    records = {}
    seen_game_ids = {}
    rejected = 0

    if checkpoint_dir.is_dir():
        for path in sorted(checkpoint_dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    record = json.load(f)
                key = record["condition_key"]
                stored_signature = record.get("signature")
                if stored_signature != signature or key not in expected:
                    rejected += 1
                    print(f"[checkpoint] ignore incompatible shard: {path.name}", flush=True)
                    if rejected <= 5:
                        if stored_signature != signature:
                            detail = _clip(json.dumps(
                                _signature_diff(stored_signature, signature),
                                default=str), 300)
                            reason = ("signature mismatch: the shard came from a "
                                      "different configuration")
                        else:
                            detail = key
                            reason = "condition is outside this sweep"
                        _emit_error("checkpoint_incompatible", reason, fatal=False,
                                    shard=path.name, detail=detail)
                    continue
                game = record.get("game") or {}
                game_id = game.get("game_id")
                if not isinstance(game_id, str) or not game_id:
                    raise ValueError("game row has no game_id")
                if game_id in seen_game_ids:
                    raise ValueError("duplicate game_id %s (already loaded from %s)"
                                     % (game_id, seen_game_ids[game_id]))
                if key in records:
                    raise ValueError(f"duplicate checkpoint condition {key}")
                for field in ("risk_probability", "language", "rep"):
                    if field not in game:
                        raise ValueError(f"game row is missing {field}")
                if _condition_key(game["risk_probability"], game["language"],
                                  game["rep"]) != key:
                    raise ValueError("game row disagrees with the cell it is filed under")
                game_turns = record.get("turns", [])
                if len(game_turns) != N_PLAYERS * N_ROUNDS:
                    raise ValueError("incomplete turn count %d (expected %d)"
                                     % (len(game_turns), N_PLAYERS * N_ROUNDS))
                foreign = [t for t in game_turns if t.get("game_id") != game_id]
                if foreign:
                    raise ValueError("%d turns belong to another game" % len(foreign))
                game_probes = record.get("probes", [])
                if len(game_probes) != expected_probes:
                    raise ValueError("probe count %d (expected %d)"
                                     % (len(game_probes), expected_probes))
                foreign_probes = [p for p in game_probes
                                  if p.get("game_id") != game_id]
                if foreign_probes:
                    raise ValueError("%d probes belong to another game"
                                     % len(foreign_probes))
                records[key] = record
                seen_game_ids[game_id] = path.name
            except Exception as exc:
                rejected += 1
                print(f"[checkpoint] ignore invalid shard {path.name}: {exc}", flush=True)
                if rejected <= 5:
                    _emit_error("checkpoint_invalid", exc, fatal=False, shard=path.name)

    if rejected > 5:
        _emit_error("checkpoint_invalid",
                    "%d shards rejected in total (only the first 5 are itemised)"
                    % rejected, fatal=False, rejected=rejected)

    ordered = [records[key] for key in expected_order if key in records]
    games = [record["game"] for record in ordered]
    turns = [turn for record in ordered for turn in record["turns"]]
    stats = {
        "parse_failed": sum(record["parse_failed"] for record in ordered),
        "tok_in": sum(record["usage_input_tokens"] for record in ordered),
        "tok_out": sum(record["usage_output_tokens"] for record in ordered),
        "cost": sum(record["usage_total_cost_nanodollars"] for record in ordered),
    }
    return games, turns, stats, set(records), ordered


# %% =====================  SWEEP (== exp_baseline: 3 risk × 2 lang × 10 rep)  =========
@kbench.task(
    name="collective-risk-baseline-srv",
    description="Milinski 2008 collective-risk dilemma, frontier arm — faithful port of "
                "crsd exp_baseline (6 agents, 10 rounds, risk×lang×rep). Measures "
                "reach-rate + cost/game; output joins the open-source games.csv.",
)
def collective_risk_baseline(llm) -> dict:
    global _LLM
    _LLM = llm                                   # rebuilt in place by _reauth() on token expiry
    if SEAT_FOREIGN_SLUGS:
        # Build every non-selected seat client NOW. Construction is local work (no
        # proxy call, no cost), so a typo'd slug or a missing credential fails on line
        # one instead of twenty games into the sweep. It does NOT prove the proxy will
        # serve those slugs -- that is still open, and shows up on the first real call.
        for slug in SEAT_FOREIGN_SLUGS:
            _client_for(slug)
        listed = [s.strip() for s in os.environ.get("LLMS_AVAILABLE", "").split(",")
                  if s.strip()]
        unlisted = [s for s in SEAT_FOREIGN_SLUGS if listed and s not in listed]
        if unlisted:
            # A warning, not a refusal: what LLMS_AVAILABLE means on the production
            # server has never been pinned down, so it is evidence rather than truth.
            _emit_error("seat_model_unlisted",
                        "seat slug(s) absent from LLMS_AVAILABLE: %s"
                        % ", ".join(unlisted), fatal=False, unlisted=unlisted,
                        available=listed[:20],
                        hint="if the proxy refuses them, make those seats "
                             "scripted:<policy> -- no second client needed")
    # One filesystem+CSV-safe tag (no '/','@') used consistently in folder AND game_id,
    # mirroring the open-source arm's hyphenated model names (e.g. qwen25-7b-instruct).
    model_tag = re.sub(r"[^A-Za-z0-9._-]+", "-", MODEL)
    # EXPERIMENT_NAME is "exp_baseline" for the default variant and "exp_nohint" for
    # CRG_TEMPLATE=nohint, so the two arms land in separate folders and neither the
    # materialized games.csv/turns.jsonl nor the checkpoint shards can collide.
    out_dir = Path(os.environ.get(
        "CRG_OUT", f"results/frontier/{model_tag}/{EXPERIMENT_NAME}"))
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = out_dir / "checkpoints"
    signature = _checkpoint_signature(model_tag)
    if RESUME:
        games, turns, prior, completed, records = _load_game_checkpoints(
            checkpoint_dir, signature)
    else:
        games, turns, records = [], [], []
        prior = {"parse_failed": 0, "tok_in": 0, "tok_out": 0, "cost": 0}
        completed = set()
    # Probe rows come back with the shards that carry them, in sweep order, so a
    # resumed run reports (and rewrites) every answer it has already paid for.
    probes = [p for record in records for p in record.get("probes", [])]
    resumed_games = len(games)
    # Second, independent guard against double counting: `completed` keys the sweep
    # grid, this keys the rows that actually reach games.csv.
    seen_game_ids = {record["game"]["game_id"] for record in records}
    if resumed_games:
        _write_materialized_outputs(out_dir, games, turns, probes)
        print(f"[resume] restored {resumed_games}/{len(RISKS) * len(LANGS) * REPS} "
              f"completed games from {checkpoint_dir}", flush=True)

    tok_in = prior["tok_in"]
    tok_out = prior["tok_out"]
    cost = prior["cost"]
    parse_failed = prior["parse_failed"]
    total = len(RISKS) * len(LANGS) * REPS
    done = resumed_games
    failed_games = []
    t0 = time.time()

    # One banner line so a shard's log identifies itself without guessing.
    probe_per_game = probes_per_game()
    print(f"[cfg] model={MODEL} tag={model_tag} template={TEMPLATE_VARIANT} "
          f"risks={RISKS} langs={LANGS} "
          f"reps={REPS} games={total} max_completion_tokens={MAX_OUT} "
          f"concurrency={_CONCURRENCY} out={out_dir}", flush=True)
    if SEAT_MODELS:
        # Who is sitting at the table, and what the shard will therefore cost. A
        # scripted seat never calls the proxy, so the call count is the honest
        # measure of the bill (E3a: 10 calls a game instead of 60).
        print(f"[cfg] seats={'|'.join(SEAT_MODELS)} tag={SEAT_TAG} "
              f"llm_seats={list(SEAT_LLM_SEATS)} "
              f"llm_calls/game={len(SEAT_LLM_SEATS) * N_ROUNDS} "
              f"(of {N_PLAYERS * N_ROUNDS})", flush=True)
        if SEAT_FOREIGN_SLUGS:
            print("[cfg] WARNING: seat(s) ask the proxy for slug(s) other than the "
                  "selected model (%s). Nobody has verified the production proxy "
                  "allows this -- check ONE game before a full shard; the fallback "
                  "(scripted opponents) needs no second client."
                  % ", ".join(SEAT_FOREIGN_SLUGS), flush=True)
    if PROBE_CATEGORIES:
        # The probe bill, before it is spent: extra calls per game and for the shard.
        print(f"[cfg] probe={','.join(PROBE_CATEGORIES)} rounds={list(PROBE_ROUNDS)} "
              f"seats={list(PROBE_SEATS)} probes/game={probe_per_game} "
              f"(decisions/game={N_PLAYERS * N_ROUNDS}) "
              f"extra_calls={probe_per_game * total}", flush=True)
    # The same banner, machine-parseable. The local supervisor sees ONLY stdout
    # (`kaggle b t log <task> -m <model>`), so it must be able to learn the sweep
    # size, the cap and the checkpoint layout from the log alone.
    start_record = {
        "model": model_tag,
        "model_slug": MODEL,
        "template_variant": TEMPLATE_VARIANT,
        "experiment": EXPERIMENT_NAME,
        "prompt_variant": PROMPT_VARIANT,
        "prompt_fingerprint": signature["prompt_fingerprint"],
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "risks": RISKS,
        "langs": LANGS,
        "reps": REPS,
        "rep_start": REP_START,
        "total": total,
        "resumed": resumed_games,
        "remaining": total - resumed_games,
        "max_completion_tokens": MAX_OUT,
        "concurrency": _CONCURRENCY,
        "resume": RESUME,
        "on_game_error": ON_GAME_ERROR,
        "max_call_attempts": MAX_CALL_ATTEMPTS,
        "out_dir": str(out_dir),
        "checkpoint_dir": str(checkpoint_dir),
    }
    if SEAT_MODELS:
        # Only a mixed run says anything about seats, so the banner a supervisor
        # already parses is unchanged for every other sweep.
        start_record.update({
            "seat_models": list(SEAT_MODELS),
            "seat_tag": SEAT_TAG,
            "llm_seats": list(SEAT_LLM_SEATS),
            "foreign_slugs": list(SEAT_FOREIGN_SLUGS),
            "llm_calls_per_game": len(SEAT_LLM_SEATS) * N_ROUNDS,
        })
    if PROBE_CATEGORIES:
        # Only a probe run says anything about probes, so the banner a supervisor
        # already parses is unchanged for every other sweep.
        start_record.update({
            "probe_categories": list(PROBE_CATEGORIES),
            "probe_rounds": list(PROBE_ROUNDS),
            "probe_seats": list(PROBE_SEATS),
            "probes_per_game": probe_per_game,
            "probe_fingerprint": signature["probe"]["fingerprint"],
            "probes_resumed": len(probes),
        })
    _emit(_TAG_START, start_record)
    # One [CRG_PROGRESS] per game the supervisor should count, restored games
    # included, so `done` walks 1..total across a chain of resumed runs.
    running_cost = 0
    for i, record in enumerate(records, start=1):
        running_cost += record["usage_total_cost_nanodollars"]
        _emit(_TAG_PROGRESS, _progress_record(
            i, total, record["game"], resumed=True,
            parse_failed=record["parse_failed"],
            game_cost_nano=record["usage_total_cost_nanodollars"],
            cost_nano=running_cost, elapsed_s=0.0,
            probes=record.get("probes") if PROBE_CATEGORIES else None))

    def _done_payload(status, error=None):
        """Terminal record, emitted on EVERY exit path including an abort: a
        supervisor that never sees a terminal line cannot tell a dead run from a
        slow one."""
        n_done_turns = len(turns)
        payload = {
            "status": status,
            "model": model_tag,
            "template_variant": TEMPLATE_VARIANT,
            "experiment": EXPERIMENT_NAME,
            "prompt_variant": PROMPT_VARIANT,
            "done": done,
            "total": total,
            "resumed_games": resumed_games,
            "new_games": len(games) - resumed_games,
            "failed_games": len(failed_games),
            "n_games": len(games),
            "n_decisions": n_done_turns,
            "parse_failed": parse_failed,
            "parse_fail_rate": (round(parse_failed / n_done_turns, 4)
                                if n_done_turns else None),
            "reached": sum(int(g.get("target_reached", 0)) for g in games),
            "usage_input_tokens": tok_in,
            "usage_output_tokens": tok_out,
            "cost_usd": round(cost / 1e9, 6),
            "elapsed_s": round(time.time() - t0, 1),
            "out_dir": str(out_dir),
            "checkpoint_dir": str(checkpoint_dir),
        }
        if SEAT_MODELS:
            payload["seat_models"] = list(SEAT_MODELS)
            payload["seat_tag"] = SEAT_TAG
        if PROBE_CATEGORIES:
            payload["probe_categories"] = list(PROBE_CATEGORIES)
            payload["probe_rounds"] = list(PROBE_ROUNDS)
            payload["probe_seats"] = list(PROBE_SEATS)
            payload["probes_per_game"] = probe_per_game
            payload.update(_probe_summary(probes))
        if failed_games:
            payload["failed_cells"] = failed_games[:10]
        if error is not None:
            payload["error"] = _clip(error)
        return payload

    try:
        for risk in RISKS:
            for language in LANGS:
                for rep in REP_RANGE:
                    key = _condition_key(risk, language, rep)
                    if key in completed:
                        print(f"[resume {done}/{total}] skip risk={risk} lang={language} rep={rep}",
                              flush=True)
                        continue

                    t_game = time.time()
                    game_turns = []
                    game_probes = [] if PROBE_CATEGORIES else None
                    try:
                        row, pf, ti, to, cn = play_game(
                            None, risk, language, rep, model_tag, game_turns,
                            game_probes)
                    except Exception as exc:
                        # The cell is lost either way (a half-played game is never
                        # committed), but the REST of the shard need not be: under
                        # CRG_ON_GAME_ERROR=skip the sweep carries on and
                        # fill_missing.py picks the cell up later.
                        skipping = ON_GAME_ERROR == "skip"
                        failed_games.append({"risk": risk, "lang": language,
                                             "rep": rep, "error": _clip(exc, 200)})
                        _emit_error("game_failed", exc, fatal=not skipping,
                                    ctx={"risk": risk, "lang": language, "rep": rep},
                                    action="skip" if skipping else "abort",
                                    done=done, total=total)
                        print(f"[game-failed] risk={risk} lang={language} rep={rep}: "
                              f"{_clip(exc, 200)}", flush=True)
                        if not skipping:
                            raise
                        continue

                    if row["game_id"] in seen_game_ids:
                        # Unreachable while `completed` is honoured; if it ever does
                        # happen, dropping the duplicate keeps games.csv honest.
                        _emit_error("duplicate_game_id",
                                    f"{row['game_id']} is already recorded; refusing "
                                    f"to append it twice", fatal=False,
                                    ctx={"game_id": row["game_id"], "risk": risk,
                                         "lang": language, "rep": rep})
                        completed.add(key)
                        continue

                    checkpoint_path = _save_game_checkpoint(
                        checkpoint_dir, signature, row, game_turns, pf, ti, to, cn,
                        probes=game_probes)
                    games.append(row)
                    turns.extend(game_turns)
                    if game_probes:
                        probes.extend(game_probes)
                    tok_in += ti; tok_out += to; cost += cn; parse_failed += pf
                    completed.add(key)
                    seen_game_ids.add(row["game_id"])
                    done += 1
                    _write_materialized_outputs(out_dir, games, turns, probes)
                    print(f"[checkpoint {done}/{total}] {row['game_id']}  "
                          f"reach={row['target_reached']} GT={row['group_total']} "
                          f"disaster={row['catastrophe']} parse_fail={pf} "
                          f"saved={checkpoint_path.name}", flush=True)
                    _emit(_TAG_PROGRESS, _progress_record(
                        done, total, row, resumed=False, parse_failed=pf,
                        game_cost_nano=cn, cost_nano=cost,
                        elapsed_s=round(time.time() - t0, 1),
                        game_elapsed_s=round(time.time() - t_game, 1),
                        probes=game_probes))
    except BaseException as exc:
        # Keep what was already paid for: shards are committed game by game, so the
        # materialized files are refreshed once more before the exception leaves.
        _write_materialized_outputs(out_dir, games, turns, probes)
        _emit(_TAG_DONE, _done_payload("aborted", error=exc))
        raise

    # One final materialization is cheap and guarantees analysis files agree with shards.
    _write_materialized_outputs(out_dir, games, turns, probes)

    n_turns = len(turns)
    reached = sum(g["target_reached"] for g in games)

    def reach_rate(pred):
        cells = [g for g in games if pred(g)]
        return round(sum(g["target_reached"] for g in cells) / len(cells), 3) if cells else None

    result = {
        "model": model_tag,
        "n_games": len(games),
        "n_decisions": n_turns,
        "parse_fail_rate": round(parse_failed / n_turns, 4) if n_turns else None,
        "overall_reach_rate": round(reached / len(games), 3) if games else None,
        "reach_by_risk": {str(r): reach_rate(lambda g, r=r: g["risk_probability"] == r) for r in RISKS},
        "reach_by_lang": {l: reach_rate(lambda g, l=l: g["language"] == l) for l in LANGS},
        "mean_group_total": (round(sum(g["group_total"] for g in games) / len(games), 2)
                             if games else None),
        "usage_input_tokens": tok_in,
        "usage_output_tokens": tok_out,
        "usage_total_cost_usd": round(cost / 1e9, 6),
        "games_per_10usd": int(10 / (cost / 1e9)) if cost else None,
        "elapsed_sec": round(time.time() - t0, 1),
        "out_dir": str(out_dir),
        "checkpoint_dir": str(checkpoint_dir),
        "resumed_games": resumed_games,
        "new_games": len(games) - resumed_games,
        "failed_games": len(failed_games),
        "failed_cells": failed_games[:10],
        "template_variant": TEMPLATE_VARIANT,
        "experiment": EXPERIMENT_NAME,
        "prompt_variant": PROMPT_VARIANT,
        "prompt_fingerprint": signature["prompt_fingerprint"],
        "on_game_error": ON_GAME_ERROR,
    }
    if SEAT_MODELS:
        result["seat_models"] = "|".join(SEAT_MODELS)
        result["seat_tag"] = SEAT_TAG
        result["llm_seats"] = list(SEAT_LLM_SEATS)
        result["llm_calls_per_game"] = len(SEAT_LLM_SEATS) * N_ROUNDS
    if PROBE_CATEGORIES:
        result["probe_categories"] = ",".join(PROBE_CATEGORIES)
        result["probe_rounds"] = list(PROBE_ROUNDS)
        result["probe_seats"] = list(PROBE_SEATS)
        result["probes_per_game"] = probe_per_game
        result["probes_file"] = str(out_dir / "probes.jsonl")
        result.update(_probe_summary(probes))

    print("\n===== COLLECTIVE-RISK BASELINE (frontier) — SUMMARY =====")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("=========================================================\n")

    # Terminal record for the local supervisor. status is "ok", "partial" (a cell was
    # skipped under CRG_ON_GAME_ERROR=skip) or "aborted" (emitted above, then raised).
    _emit(_TAG_DONE, _done_payload("partial" if failed_games else "ok"))

    # Health check only (reach-rate itself is a finding, not an assertion): the pipeline
    # is valid iff every decision parsed. Run-1 lesson: check parse-fail BEFORE interpreting.
    kbench.assertions.assert_equal(0, parse_failed,
                                   expectation="All agent decisions parsed a legal CONTRIBUTION (0/2/4)")
    # Completeness is the other half. With CRG_ON_GAME_ERROR=abort (the default) this
    # line is only ever reached with an empty list, so the check costs nothing; under
    # "skip" it stops a shard that quietly lost cells from reading as a clean sweep.
    kbench.assertions.assert_equal(0, len(failed_games),
                                   expectation="Every cell of the sweep produced a game (none abandoned)")
    return result


# %%
# The Kaggle server executes this as a module (__name__ != "__main__"), so this must
# fire by default. CRG_SKIP_RUN=1 exists solely for import-time unit tests.
if os.environ.get("CRG_SKIP_RUN") != "1":
    collective_risk_baseline.run(kbench.llm)
