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
"""
import csv
import io
import json
import os
import random
import re
import subprocess
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
TEMPERATURE = 0.7
PERSONA_SET = "personas_default"     # neutral agents -> persona block dropped
PLAYER_NAMES = [f"Player_{i + 1}" for i in range(N_PLAYERS)]

# Seed scheme copied verbatim from crsd (engine/game.py + runner/batch.py) so the
# frontier arm shares the SAME reproducibility/CRN structure as the vLLM arm.
BASE_SEED = 12345
SAMPLING_SEED_STRIDE = 100_000
SAMPLING_SEED_MOD = 2_147_483_647    # 2**31 - 1
RETRY_SEED_STEP = 1_000_003
MAX_PARSE_RETRIES = 3

# Swept conditions (env-overridable so a smoke test doesn't need code edits).
RISKS = [float(x) for x in os.environ.get("CRG_RISKS", "0.9,0.5,0.1").split(",")]
LANGS = [s.strip() for s in os.environ.get("CRG_LANGS", "en,vn").split(",")]
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
MAX_OUT = int(os.environ.get("CRG_MAX_OUT", "0")) or (
    6000 if any(h in MODEL.lower() for h in _REASONING_HINTS) else 512
)
# Bump whenever checkpoint compatibility changes. Version 2 invalidates shards
# produced before re-auth was guaranteed to preserve the selected model.
CHECKPOINT_SCHEMA_VERSION = 2

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

# Proxy models (esp. non-Gemini on staging) intermittently return 429/503. Retry
# those; if a call STILL fails after retries, raise so the run aborts loudly.
_TRANSIENT = ("429", "503", "500", "502", "504", "overloaded",
              "unavailable", "not reachable", "rate limit", "heavy load")


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

TEMPLATES = {"en": TEMPLATE_EN, "vn": TEMPLATE_VN}
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
    }
    text = _resolve_blocks(TEMPLATES[language], enabled)

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


# %% =====================  SEED SCHEME (== crsd)  =====================
def sampling_seed(rep, agent_idx, round_number):
    seed = BASE_SEED + rep
    return (seed * SAMPLING_SEED_STRIDE + round_number * 100 + agent_idx) % SAMPLING_SEED_MOD


# The proxy token expires ~1h < a full 60-game run. The key is baked into the model
# client at construction, so on a 401 we refresh .env AND rebuild the client in place.
_LLM = None                                          # current model client (task sets it)
_AUTH_ERR = ("expired token", "authentication", "unauthorized", "401",
             "invalid api key", "invalid_api_key", "403")


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


def _call_llm(llm, prompt, seed, max_attempts=6):
    """One free-text generation via the (rebuildable) global client `_LLM`. Returns
    (text, usage). Auto-reauths on token expiry; exp-backoff on transient 429/503."""
    attempt = 0
    auth_retries = 0
    while True:
        attempt += 1
        text = None
        try:
            with kbench.chats.new("turn", orphan=True) as chat:
                text = _LLM.prompt(prompt, temperature=TEMPERATURE, seed=seed,
                                   extra_api_params={"max_completion_tokens": MAX_OUT})
            if text is not None and text.strip():
                return text, chat.usage
            if text is not None:
                # HTTP 200 but NO text: the model burned its whole output budget in a
                # reasoning channel (measured on gemini-3.6-flash at 64 tokens, and
                # gpt-oss-120b returns '' at any cap). This must NEVER fall through to
                # a parsed contribution -- run 1 fabricated all-zero "games" that way.
                raise RuntimeError(
                    f"503 empty-content: model returned no text "
                    f"(max_completion_tokens={MAX_OUT}); raise CRG_MAX_OUT if it persists")
            # Parallel path: contexts.enter can SWALLOW a proxy error inside a
            # worker thread (the run ContextVar does not propagate), leaving
            # text=None. Raise a synthetic transient so the backoff below retries.
            raise RuntimeError("503 no-text: proxy error swallowed under concurrency")
        except Exception as e:
            msg = str(e).lower()
            # A cost-reservation 403 is NOT an auth failure. `_AUTH_ERR` contains
            # "403", so without this guard a quota 403 would burn six `kaggle b auth`
            # reauth cycles and then surface the wrong cause. Reauth cannot fix it:
            # lower CRG_MAX_OUT or use an account with quota left.
            if "max estimated cost" in msg or "available quota" in msg:
                raise
            if any(t in msg for t in _AUTH_ERR):     # token expired -> refresh, don't burn budget
                auth_retries += 1
                if auth_retries > 6:
                    raise
                _reauth()
                attempt -= 1
                continue
            if attempt >= max_attempts or not any(t in msg for t in _TRANSIENT):
                raise
            time.sleep(min(2 ** attempt, 30))


def decide(llm, prompt, base_seed):
    """Free-text + `CONTRIBUTION:` parse + retry-on-parse-fail (fresh seed each retry),
    mirroring crsd/runner/batch. Returns (text, value, failed, tok_in, tok_out, cost)."""
    tok_in = tok_out = cost = 0
    text, usage = _call_llm(llm, prompt, base_seed)
    tok_in += usage.input_tokens or 0
    tok_out += usage.output_tokens or 0
    cost += usage.total_cost_nanodollars or 0
    value, failed = parse_contribution(text)
    attempt = 0
    while failed and attempt < MAX_PARSE_RETRIES:
        attempt += 1
        seed = (base_seed + attempt * RETRY_SEED_STEP) % SAMPLING_SEED_MOD
        text, usage = _call_llm(llm, prompt, seed)
        tok_in += usage.input_tokens or 0
        tok_out += usage.output_tokens or 0
        cost += usage.total_cost_nanodollars or 0
        value, failed = parse_contribution(text)
    return text, value, failed, tok_in, tok_out, cost


# %% =====================  ONE GAME (simultaneous within a round)  =====================
def play_game(llm, risk, language, rep, model_tag, turns_sink):
    balances = [ENDOWMENT] * N_PLAYERS
    own_totals = [0] * N_PLAYERS
    history = []                                   # completed rounds only (lockstep)
    game_id = f"{GAME_NAME[risk]}__{model_tag}__{language}__rep{rep}"
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
            text, value, failed, ti, to, cn = decide(llm, prompt, base_seed)
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

            turns_sink.append({
                "game_id": game_id, "round": r, "player": PLAYER_NAMES[pid],
                "contribution": value, "parse_failed": failed,
                "reasoning": extract_reasoning(text), "raw_response": text,
                "prompt": prompt, "logprobs": None, "latency_ms": None, "note": None,
                "sampling_seed": base_seed, "disposition": "neutral",
                "risk_probability": risk, "language": language,
                "persona_set": PERSONA_SET, "memory_mode": "full_history",
                "framing": False, "rep": rep,
            })
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
    return game_row, parse_failed, tok_in, tok_out, cost


# %% =====================  CHECKPOINT / RESUME  =====================
def _condition_key(risk, language, rep):
    """Canonical key for one completed experimental cell."""
    return f"{float(risk):.12g}|{language}|{int(rep)}"


def _checkpoint_filename(risk, language, rep):
    risk_tag = f"{float(risk):.12g}".replace(".", "p").replace("-", "m")
    return f"risk-{risk_tag}__lang-{language}__rep-{int(rep):03d}.json"


def _checkpoint_signature(model_tag):
    """Fields that must match before a shard is safe to resume."""
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "model": model_tag,
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


def _write_materialized_outputs(out_dir, games, turns):
    """Refresh analysis-friendly outputs after every durable game shard."""
    out_dir = Path(out_dir)
    turns_text = "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in turns)
    _atomic_write_text(out_dir / "turns.jsonl", turns_text)

    if games:
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=list(games[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(games)
        _atomic_write_text(out_dir / "games.csv", buf.getvalue())


def _save_game_checkpoint(checkpoint_dir, signature, row, game_turns,
                          parse_failed, tok_in, tok_out, cost):
    """Commit one complete game. An interrupted game never produces a valid shard."""
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
    path = Path(checkpoint_dir) / _checkpoint_filename(
        row["risk_probability"], row["language"], row["rep"])
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def _load_game_checkpoints(checkpoint_dir, signature):
    """Load only complete, compatible shards and return them in sweep order."""
    checkpoint_dir = Path(checkpoint_dir)
    expected_order = [
        _condition_key(risk, language, rep)
        for risk in RISKS for language in LANGS for rep in REP_RANGE
    ]
    expected = set(expected_order)
    records = {}

    if checkpoint_dir.is_dir():
        for path in sorted(checkpoint_dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    record = json.load(f)
                key = record["condition_key"]
                if record.get("signature") != signature or key not in expected:
                    print(f"[checkpoint] ignore incompatible shard: {path.name}", flush=True)
                    continue
                if key in records:
                    raise ValueError(f"duplicate checkpoint condition {key}")
                if len(record.get("turns", [])) != N_PLAYERS * N_ROUNDS:
                    raise ValueError("incomplete turn count")
                records[key] = record
            except Exception as exc:
                print(f"[checkpoint] ignore invalid shard {path.name}: {exc}", flush=True)

    ordered = [records[key] for key in expected_order if key in records]
    games = [record["game"] for record in ordered]
    turns = [turn for record in ordered for turn in record["turns"]]
    stats = {
        "parse_failed": sum(record["parse_failed"] for record in ordered),
        "tok_in": sum(record["usage_input_tokens"] for record in ordered),
        "tok_out": sum(record["usage_output_tokens"] for record in ordered),
        "cost": sum(record["usage_total_cost_nanodollars"] for record in ordered),
    }
    return games, turns, stats, set(records)


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
    # One filesystem+CSV-safe tag (no '/','@') used consistently in folder AND game_id,
    # mirroring the open-source arm's hyphenated model names (e.g. qwen25-7b-instruct).
    model_tag = re.sub(r"[^A-Za-z0-9._-]+", "-", MODEL)
    out_dir = Path(os.environ.get("CRG_OUT", f"results/frontier/{model_tag}/exp_baseline"))
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = out_dir / "checkpoints"
    signature = _checkpoint_signature(model_tag)
    if RESUME:
        games, turns, prior, completed = _load_game_checkpoints(checkpoint_dir, signature)
    else:
        games, turns = [], []
        prior = {"parse_failed": 0, "tok_in": 0, "tok_out": 0, "cost": 0}
        completed = set()
    resumed_games = len(games)
    if resumed_games:
        _write_materialized_outputs(out_dir, games, turns)
        print(f"[resume] restored {resumed_games}/{len(RISKS) * len(LANGS) * REPS} "
              f"completed games from {checkpoint_dir}", flush=True)

    tok_in = prior["tok_in"]
    tok_out = prior["tok_out"]
    cost = prior["cost"]
    parse_failed = prior["parse_failed"]
    total = len(RISKS) * len(LANGS) * REPS
    done = resumed_games
    t0 = time.time()

    # One banner line so a shard's log identifies itself without guessing.
    print(f"[cfg] model={MODEL} tag={model_tag} risks={RISKS} langs={LANGS} "
          f"reps={REPS} games={total} max_completion_tokens={MAX_OUT} "
          f"concurrency={_CONCURRENCY} out={out_dir}", flush=True)

    for risk in RISKS:
        for language in LANGS:
            for rep in REP_RANGE:
                key = _condition_key(risk, language, rep)
                if key in completed:
                    print(f"[resume {done}/{total}] skip risk={risk} lang={language} rep={rep}",
                          flush=True)
                    continue

                game_turns = []
                row, pf, ti, to, cn = play_game(
                    llm, risk, language, rep, model_tag, game_turns)
                checkpoint_path = _save_game_checkpoint(
                    checkpoint_dir, signature, row, game_turns, pf, ti, to, cn)
                games.append(row)
                turns.extend(game_turns)
                tok_in += ti; tok_out += to; cost += cn; parse_failed += pf
                completed.add(key)
                done += 1
                _write_materialized_outputs(out_dir, games, turns)
                print(f"[checkpoint {done}/{total}] {row['game_id']}  "
                      f"reach={row['target_reached']} GT={row['group_total']} "
                      f"disaster={row['catastrophe']} parse_fail={pf} "
                      f"saved={checkpoint_path.name}", flush=True)

    # One final materialization is cheap and guarantees analysis files agree with shards.
    _write_materialized_outputs(out_dir, games, turns)

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
        "overall_reach_rate": round(reached / len(games), 3),
        "reach_by_risk": {str(r): reach_rate(lambda g, r=r: g["risk_probability"] == r) for r in RISKS},
        "reach_by_lang": {l: reach_rate(lambda g, l=l: g["language"] == l) for l in LANGS},
        "mean_group_total": round(sum(g["group_total"] for g in games) / len(games), 2),
        "usage_input_tokens": tok_in,
        "usage_output_tokens": tok_out,
        "usage_total_cost_usd": round(cost / 1e9, 6),
        "games_per_10usd": int(10 / (cost / 1e9)) if cost else None,
        "elapsed_sec": round(time.time() - t0, 1),
        "out_dir": str(out_dir),
        "checkpoint_dir": str(checkpoint_dir),
        "resumed_games": resumed_games,
        "new_games": len(games) - resumed_games,
    }

    print("\n===== COLLECTIVE-RISK BASELINE (frontier) — SUMMARY =====")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("=========================================================\n")

    # Health check only (reach-rate itself is a finding, not an assertion): the pipeline
    # is valid iff every decision parsed. Run-1 lesson: check parse-fail BEFORE interpreting.
    kbench.assertions.assert_equal(0, parse_failed,
                                   expectation="All agent decisions parsed a legal CONTRIBUTION (0/2/4)")
    return result


# %%
# The Kaggle server executes this as a module (__name__ != "__main__"), so this must
# fire by default. CRG_SKIP_RUN=1 exists solely for import-time unit tests.
if os.environ.get("CRG_SKIP_RUN") != "1":
    collective_risk_baseline.run(kbench.llm)
