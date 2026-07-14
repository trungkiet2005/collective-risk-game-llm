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
import json
import os
import random
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutureTimeout
from pathlib import Path

# Load MODEL_PROXY_* from .env for local runs (harmless on the Kaggle server, which
# injects these as real env vars). Pick the model via CRG_MODEL, else flash-lite.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
MODEL = os.environ.get("CRG_MODEL", "google/gemini-3.1-flash-lite-preview")
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
# Hard per-request wall timeout (s), enforced by a THREAD watchdog (below). The proxy
# intermittently leaves a request hanging forever and the OpenAI/httpx `timeout` does
# NOT reliably fire on it (observed: a call stalled >11 min). Normal calls are ~1-2s,
# so 60s is huge headroom but bounds a stall so the run self-heals instead of freezing.
REQUEST_TIMEOUT = 60

# Swept conditions (env-overridable so a smoke test doesn't need code edits).
RISKS = [float(x) for x in os.environ.get("CRG_RISKS", "0.9,0.5,0.1").split(",")]
LANGS = [s.strip() for s in os.environ.get("CRG_LANGS", "en,vn").split(",")]
REPS = int(os.environ.get("CRG_REPS", "10"))

# risk -> crsd game name, so game_id matches the open-source arm's join key.
GAME_NAME = {0.90: "crsd_milinski_high_risk",
             0.50: "crsd_milinski_medium_risk",
             0.10: "crsd_milinski_low_risk"}

# Proxy models (esp. non-Gemini on staging) intermittently return 429/503. Retry
# those; if a call STILL fails after retries, raise so the run aborts loudly.
_TRANSIENT = ("429", "503", "500", "502", "504", "overloaded",
              "unavailable", "not reachable", "rate limit", "heavy load",
              "timeout", "timed out", "connection", "read operation")


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


# Watchdog runs each proxy call in a worker thread so a stalled request can be
# ABANDONED (Python can't kill the thread, but we stop waiting and retry on a fresh
# client). Generous worker count absorbs the occasional leaked hung thread.
_EXECUTOR = ThreadPoolExecutor(max_workers=32, thread_name_prefix="llm")


def _rebuild_client():
    """Rebuild the client with a fresh connection pool (no re-auth) — drops a stuck socket."""
    global _LLM
    from kaggle_benchmarks.kaggle.models import load_default_model
    _LLM = load_default_model()


def _reauth():
    """Refresh the proxy token AND rebuild the client so a long run survives expiry."""
    global _LLM
    print("[auth] refreshing token (`kaggle b auth -y`) + rebuild client ...", flush=True)
    subprocess.run(["kaggle", "b", "auth", "-y"], capture_output=True, text=True)
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)                   # pull the fresh MODEL_PROXY_API_KEY
    except Exception:
        pass
    from kaggle_benchmarks.kaggle.models import load_default_model
    _LLM = load_default_model()                      # uses LLM_DEFAULT (still set) + new key


def _one_shot(prompt, seed):
    with kbench.chats.new("turn", orphan=True) as chat:
        text = _LLM.prompt(prompt, temperature=TEMPERATURE, seed=seed,
                           extra_api_params={"timeout": REQUEST_TIMEOUT})
    return text, chat.usage


def _call_llm(llm, prompt, seed, max_attempts=8):
    """One free-text generation via the (rebuildable) global client `_LLM`, under a hard
    thread watchdog. Returns (text, usage). Recovers from: proxy stalls (watchdog ->
    rebuild client), token expiry (401 -> reauth), transient 429/503 (exp backoff)."""
    attempt = 0
    hangs = 0
    auth_retries = 0
    while True:
        attempt += 1
        try:
            fut = _EXECUTOR.submit(_one_shot, prompt, seed)
            return fut.result(timeout=REQUEST_TIMEOUT)
        except _FutureTimeout:
            hangs += 1
            if hangs > 8:
                raise TimeoutError(
                    f"LLM call stalled {hangs}x (>{REQUEST_TIMEOUT}s each) — proxy hanging")
            print(f"[watchdog] call stalled >{REQUEST_TIMEOUT}s (hang #{hangs}) -> "
                  f"{'reauth' if hangs >= 2 else 'rebuild client'} + retry", flush=True)
            _reauth() if hangs >= 2 else _rebuild_client()   # 2nd stall: maybe token expiry
            attempt -= 1                                       # a stall isn't a bad answer
            continue
        except Exception as e:
            msg = str(e).lower()
            if any(t in msg for t in _AUTH_ERR):              # token expired -> refresh
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
        # All N prompts built from COMPLETED-round history -> genuinely simultaneous.
        round_contribs = []
        for pid in range(N_PLAYERS):
            prompt = assemble_prompt(language, pid, r, history, risk)
            base_seed = sampling_seed(rep, pid, r)
            text, value, failed, ti, to, cn = decide(llm, prompt, base_seed)
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


# %% =====================  SWEEP (== exp_baseline: 3 risk × 2 lang × 10 rep)  =========
@kbench.task(
    name="collective-risk-baseline",
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
    out_dir = Path(os.environ.get("CRG_OUT", f"frontier_results/{model_tag}/exp_baseline"))
    out_dir.mkdir(parents=True, exist_ok=True)

    games, turns = [], []
    tok_in = tok_out = cost = parse_failed = 0
    total = len(RISKS) * len(LANGS) * REPS
    done = 0
    t0 = time.time()

    def _flush():
        """Rewrite both crsd-schema files after each game -> live progress + crash recovery."""
        with open(out_dir / "turns.jsonl", "w", encoding="utf-8") as f:
            for t in turns:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        if games:
            with open(out_dir / "games.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(games[0].keys()))
                w.writeheader(); w.writerows(games)

    for risk in RISKS:
        for language in LANGS:
            for rep in range(REPS):
                row, pf, ti, to, cn = play_game(llm, risk, language, rep, model_tag, turns)
                games.append(row)
                tok_in += ti; tok_out += to; cost += cn; parse_failed += pf
                done += 1
                _flush()                                     # persist after every game
                el = time.time() - t0
                eta = el / done * (total - done)
                print(f"[{done}/{total}] {row['game_id']}  reach={row['target_reached']} "
                      f"GT={row['group_total']} disaster={row['catastrophe']} parse_fail={pf} "
                      f"| {el/60:.1f}min in, ETA {eta/60:.1f}min", flush=True)

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
        # str keys: kbench serializes the return dict to run.json and chokes on float keys.
        "reach_by_risk": {str(r): reach_rate(lambda g, r=r: g["risk_probability"] == r) for r in RISKS},
        "reach_by_lang": {l: reach_rate(lambda g, l=l: g["language"] == l) for l in LANGS},
        "mean_group_total": round(sum(g["group_total"] for g in games) / len(games), 2),
        "usage_input_tokens": tok_in,
        "usage_output_tokens": tok_out,
        "usage_total_cost_usd": round(cost / 1e9, 6),
        # games per $10 = 10 / cost-per-game (not 10 / whole-run cost).
        "games_per_10usd": int(10 * len(games) / (cost / 1e9)) if cost else None,
        "elapsed_sec": round(time.time() - t0, 1),
        "out_dir": str(out_dir),
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
if __name__ == "__main__":
    collective_risk_baseline.run(kbench.llm)
    # Results are already on disk (written per-game). Force-exit so any worker thread
    # still stuck on a hung proxy socket can't block interpreter shutdown.
    os._exit(0)
