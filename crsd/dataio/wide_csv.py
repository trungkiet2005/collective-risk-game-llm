"""Chiếu dữ liệu LONG (games.csv + turns.jsonl) sang định dạng WIDE kiểu FAIRGAME.

Một dòng = một ván, mỗi agent chiếm một khối cột (`agent1_strategies`, `agent1_scores`, …)
— học theo corpus prisoner's-dilemma ở `Prisoner_Dilemma_Game/Dataset/data_fairgame_frontier_llm`
nhưng mở rộng cho CRSD 6 agent. Đặc tả đầy đủ: `plan/aamas2027-plan.md` §9.

Đây là một PHÉP CHIẾU, không phải bản thay thế: `games.csv`/`turns.jsonl` vẫn là nguồn sự
thật, và cây `wide/` sinh lại được bất cứ lúc nào. Nên engine đang chạy không chịu rủi ro gì.

Hai chỗ CRSD khác hẳn prisoner's dilemma, và cách xử lý:

* **Không có payoff theo vòng.** Tiền chỉ kết toán một lần ở cuối, sau xổ số cấp nhóm. Nên
  `agent{i}_scores` ở đây là **tài khoản riêng còn lại sau mỗi vòng**
  (`endowment - cumsum(đóng góp)`) — cùng đơn vị tiền, cùng độ dài 10, để code loader dùng
  chung được với corpus PD. Nó là hàm tất định của `agent{i}_strategies`; phần "phụ thuộc
  người khác" mà cột `scores` của PD mang, ở CRSD nằm ở cấp nhóm trong `pot_cumulative`.
* **Kết cục là của cả nhóm.** Thêm hẳn một khối cột nhóm (`group_contributions`,
  `pot_cumulative`, `target_reached`, `catastrophe`) mà trò chơi 2 người không có tương đương.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict

N_PLAYERS = 6
N_ROUNDS = 10

# Lượt nào không có dòng này là đã bị CẮT trước khi model kịp ra quyết định. Khi đó
# `parse_contribution` rơi xuống nhánh quét mọi chữ số rồi lấy số cuối thuộc {0,2,4} —
# và vẫn trả `parse_failed=False`. Nên `parse_failed` KHÔNG phát hiện được lỗi này;
# phải kiểm sự có mặt của chính dòng marker.
CONTRIB_RE = re.compile(r"CONTRIBUTION\s*:", re.I)


def _pylist(xs) -> str:
    """Python literal (nháy đơn) — KHÔNG phải JSON, để khớp corpus PD.

    Bên đọc dùng ``ast.literal_eval``. Giữ int là int để list không lẫn float xấu xí.
    """
    return repr([int(x) if float(x).is_integer() else float(x) for x in xs])


def infer_endowment(games, default=40.0):
    """Suy vốn ban đầu từ dữ liệu thay vì hardcode.

    Với ván KHÔNG thảm hoạ: ``mean_payoff = endowment - group_total / n``. Ván có thảm hoạ
    cho payoff 0 nên không suy được — bỏ qua chúng. Nếu không ván nào dùng được (ví dụ
    file toàn thảm hoạ ở p = 1.0) thì lấy ``default``.
    """
    cands = set()
    for g in games:
        if int(float(g.get("catastrophe", 0))):
            continue
        cands.add(round(float(g["mean_payoff"]) + float(g["group_total"]) / N_PLAYERS, 6))
    if not cands:
        return default
    if len(cands) > 1:
        raise ValueError(f"endowment khong nhat quan trong cung mot file: {sorted(cands)}")
    return cands.pop()


def group_turns(turns):
    """Gom lượt theo (risk, rep) rồi theo người chơi.

    Khoá là (risk, rep) chứ KHÔNG phải ``game_id``: ở schema cũ, ``game_id`` trong
    turns.jsonl không mang hậu tố ngôn ngữ/rep nên nó trùng nhau giữa các rep.
    """
    out = defaultdict(lambda: defaultdict(dict))
    for t in turns:
        key = (f"{float(t['risk_probability']):.1f}", str(t["rep"]))
        out[key][t["player"]][int(t["round"])] = t
    return out


# Tien to cua ghe robot trong `agent{i}_llm` ("scripted:always_4"). Giu nguyen dau hai
# cham: no la thu phan biet ghe tat dinh voi mot slug model, va `seat_model_tag` dua vao
# day de loai ghe robot ra khoi ten thu muc.
SCRIPTED_PREFIX = "scripted:"

# Windows cấm hẳn những ký tự này trong tên file/thư mục. Ở đây chúng còn nguy hiểm hơn
# một lỗi tên: `"/"` trong một slug thô ("qwen/qwen3-…") sẽ đẻ ra THÊM một cấp thư mục
# giữa `<p>/` và file, làm vỡ luật "dưới `<experiment>/` chỉ có thư mục tên là số".
_FORBIDDEN_IN_NAME = set(r'\/:*?"<>|')

# --- Bảng slug -> model_tag CHÍNH TẮC cho panel 5 model ------------------------------
#
# Vì sao phải có bảng tra, thay vì cứ sanitize slug rồi thôi: **cùng một model tới đây
# dưới nhiều dạng slug khác nhau, và sanitize không gộp chúng lại được.**
#
# Đo thật trên hai ván pilot E3b (10-09-2026): proxy production nhận slug ghế lạ, nhưng
# nó **không chuẩn hoá slug ghế** — chỉ chuẩn hoá slug của model `-m`. Nên cùng một con
# grok ngồi ghế lạ ghi ra `turns.jsonl` hai kiểu, tuỳ người phóng shard gõ gì vào
# `CRG_SEAT_MODELS`:
#
#     pilot b6ce946f  ->  "grok-4.20-0309-non-reasoning"        (không tiền tố nhà)
#     pilot 2dc6beab  ->  "xai/grok-4.20-0309-non-reasoning"    (có tiền tố nhà)
#
# Sanitize đơn thuần cho ra hai tag khác nhau, tức MỘT model mang HAI tên: tên `mix__`
# hết chính tắc (hai shard đối xứng đẻ ra hai thư mục), và cổng cân bằng của
# `verify_wide.py` đếm ra 6 model thay vì 5 rồi báo lệch một cách khó hiểu.
#
# Bảng tra là TƯỜNG MINH, không cắt chuỗi đoán tiền tố: đoán kiểu "phần trước dấu / là
# nhà" sẽ im lặng biến một slug gõ sai thành một tag trông hợp lệ. Slug ngoài panel đi
# đường sanitize cũ NHƯNG kèm cảnh báo stderr — ngoài panel gần như chắc chắn là gõ sai,
# vì panel đã bị khoá ở 5 model.
PANEL_MODELS = (
    ("anthropic", "claude-haiku-4-5-20251001"),
    ("google", "gemini-3.5-flash-lite"),
    ("openai", "gpt-5.6-luna"),
    ("qwen", "qwen3-235b-a22b-instruct-2507"),
    ("xai", "grok-4.20-0309-non-reasoning"),
)

#: 5 tag chính tắc — đúng tên thư mục trong `results/<experiment>/<p>/<model_tag>/`.
PANEL_TAGS = tuple(f"{nha}-{slug}" for nha, slug in PANEL_MODELS)

#: Mọi dạng đã gặp -> tag chính tắc. Khoá gồm slug trần ("grok-4.20-…"), slug có tiền tố
#: nhà sau khi sanitize ("xai-grok-4.20-…" — cũng chính là tag), nên tra hai lượt
#: (thô rồi sanitize) là phủ hết ba dạng trong bảng pilot ở trên.
SLUG_TO_TAG = {}
for _nha, _slug in PANEL_MODELS:
    _tag = f"{_nha}-{_slug}"
    SLUG_TO_TAG[_slug] = _tag          # dạng trần, không tiền tố nhà
    SLUG_TO_TAG[_tag] = _tag           # đã chính tắc rồi (và = sanitize("nha/slug"))
del _nha, _slug, _tag

# Slug lạ đã cảnh báo rồi thì thôi: một shard có 60 lượt/ván nên in mỗi lượt một dòng sẽ
# chôn mất chính cái cảnh báo đó. Test nào cần kiểm cảnh báo thì clear set này trước.
_WARNED_UNKNOWN_SLUGS = set()


def _sanitize_name(s: str) -> str:
    """Quy tắc chuẩn hoá cũ, y hệt cái server dùng cho slug của model `-m`."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s)


def canonical_model_tag(seat_model: str) -> str:
    """Slug ghế (dạng bất kỳ) -> `<model_tag>` chính tắc.

    Ba dạng dưới đây PHẢI về cùng một tag, vì chúng là cùng một model::

        grok-4.20-0309-non-reasoning
        xai/grok-4.20-0309-non-reasoning
        xai-grok-4.20-0309-non-reasoning   ->  "xai-grok-4.20-0309-non-reasoning"

    Ghế ``scripted:`` trả về nguyên văn: nó không phải model proxy, không bao giờ phải
    join với tên thư mục, và đổi thành "scripted-always_4" chỉ làm mất dấu hiệu đây là
    ghế tất định.

    Ngoài panel -> sanitize như cũ **kèm cảnh báo stderr**. Không raise, vì tầng đọc còn
    phải gom được data thăm dò ngoài panel; nhưng cũng không im lặng, vì panel đang bị
    khoá ở 5 model nên một slug lạ gần như chắc chắn là gõ sai.
    """
    raw = ("" if seat_model is None else str(seat_model)).strip()
    if raw.startswith(SCRIPTED_PREFIX):
        return raw
    tag = SLUG_TO_TAG.get(raw)
    if tag is not None:
        return tag
    clean = _sanitize_name(raw)
    tag = SLUG_TO_TAG.get(clean)
    if tag is not None:
        return tag
    if raw and raw not in _WARNED_UNKNOWN_SLUGS:
        _WARNED_UNKNOWN_SLUGS.add(raw)
        print(f"  CANH BAO: slug ghe {raw!r} KHONG nam trong panel 5 model; dat tag "
              f"{clean!r} bang quy tac sanitize. Panel dang khoa o: "
              f"{', '.join(PANEL_TAGS)}.", file=sys.stderr)
    return clean


def _seat_llm(seat_model: str | None, fallback: str) -> str:
    """Tên model của một ghế, CÙNG DẠNG với ``<model_tag>`` trong đường dẫn.

    Task server ghi ``seat_model`` là **slug thô** ("qwen/qwen3-235b-…") trong khi thư
    mục và cột ``model`` dùng tag đã chuẩn hoá ("qwen-qwen3-235b-…"). Để nguyên slug thì
    ``agent1_llm`` không join được với đường dẫn, và ``verify_wide.py`` báo lỗi trên
    **từng dòng** — đúng cái đã xảy ra khi gom E3a lần đầu.

    Chuẩn hoá đi qua :func:`canonical_model_tag` chứ không phải sanitize trần, để ghế lạ
    và ghế `-m` của cùng một model không ra hai tên (xem bảng pilot ở trên).
    """
    return canonical_model_tag(seat_model if seat_model else fallback)


def seat_model_tag(seat_llms) -> str:
    """Tên ``<model_tag>`` của MỘT ván, suy ra từ chính cấu hình ghế.

    Nhận danh sách 6 giá trị ``agent{i}_llm`` (đã chuẩn hoá bởi :func:`_seat_llm`, tức
    cùng dạng với tên thư mục) và trả về tên dùng cho CẢ thư mục lẫn tên file.

    Vì sao không lấy tên thư mục shard như trước: ``kaggle b t run -m <slug>`` chỉ chọn
    được MỘT model, nên với bàn hỗn hợp (E3b) server ghi output vào thư mục của model A và
    thông tin "đối thủ là ai, mấy ghế" biến mất khỏi đường dẫn — cả 4 cặp có model A sẽ đổ
    về đúng một tên và đè lên nhau.

    Quy tắc:

    * Ghế ``scripted:`` bị BỎ QUA — robot không phải model. Nhờ vậy E3a (1 ghế LLM + 5 ghế
      scripted) vẫn ra đúng tên đồng nhất như hiện tại.
    * Còn đúng một model -> trả về chính nó (nhánh đồng nhất, giữ nguyên 100% dữ liệu cũ).
    * Hai model -> ``mix__<tagA>__<tagB>__k<k>`` với (tagA, tagB) **sắp xếp từ điển** và
      ``k`` = số ghế tagA giữ. Sắp xếp từ điển làm tên CHÍNH TẮC: cùng một cặp model ra
      cùng một tên bất kể model nào được chọn làm ``-m`` lúc chạy, nên hai shard đối xứng
      không đẻ ra hai thư mục khác nhau cho cùng một cấu hình.
    * Từ ba model trở lên, hay không còn model nào -> ``ValueError``. Thiết kế E3b chỉ có
      CẶP; ba model trong một ván nghĩa là cấu hình ghế sai, và đoán im lặng ở đây sẽ ghi
      ra một cái tên vô nghĩa mà không ai kiểm lại được.
    * Hai model mà **vẫn còn ghế scripted** -> ``ValueError``. Xem lý do ngay dưới.

    Ô trống cũng là lỗi (không phải "ghế không có model"): nuốt nó đi sẽ làm ``k`` lệch
    một cách âm thầm, và ``k`` chính là biến độc lập của E3b.

    **Vì sao hỗn hợp + robot bị TỪ CHỐI thay vì được đặt tên dài hơn.** Robot bị loại
    trước khi đếm, nên ``[A,A,A,A,B,B]`` và ``[A,A,A,A,B,scripted:always_4]`` cùng ra
    ``mix__A__B__k4`` rồi bị gom vào MỘT file — hai cấu hình khác hẳn nhau (5 người chơi
    thật với 6, và bàn có robot với bàn không) nằm chung một dòng dữ liệu. Thiết kế E3b
    không trộn robot vào bàn hỗn hợp nên ca này không xảy ra trong thực tế; nhưng "không
    xảy ra" không phải lý do để gom nhầm im lặng, và từ chối rẻ hơn nhiều so với việc
    phát hiện ra sau khi đã phân tích. E3a (1 ghế LLM + 5 robot) không bị ảnh hưởng: ở đó
    chỉ còn MỘT model nên nó rơi vào nhánh đồng nhất.
    """
    models, n_scripted = [], 0
    for i, raw in enumerate(seat_llms, 1):
        s = ("" if raw is None else str(raw)).strip()
        if s.startswith(SCRIPTED_PREFIX):
            n_scripted += 1
            continue
        if not s:
            raise ValueError(f"ghe {i} khong co ten model (agent{i}_llm rong)")
        bad = "".join(sorted(set(s) & _FORBIDDEN_IN_NAME))
        if bad:
            raise ValueError(
                f"ghe {i}: {s!r} chua ky tu cam trong ten file ({bad!r}). Rat co the do "
                f"slug tho lot vao agent{i}_llm ma chua qua chuan hoa.")
        models.append(s)

    uniq = sorted(set(models))
    if not uniq:
        raise ValueError("ca 6 ghe deu scripted: khong co model nao de dat ten thu muc")
    if len(uniq) == 1:
        return uniq[0]
    if len(uniq) > 2:
        raise ValueError(
            "%d model khac nhau trong cung mot van (%s) — thiet ke E3b chi co CAP, "
            "day la cau hinh ghe sai" % (len(uniq), ", ".join(uniq)))
    if n_scripted:
        raise ValueError(
            "ban HON HOP (%s) ma con %d ghe scripted — thiet ke E3b khong tron robot vao "
            "ban hon hop. Ten mix__ bo qua ghe robot, nen cau hinh nay se bi gom chung "
            "file voi cau hinh KHONG co robot; tu choi dat ten thay vi gom nham."
            % (", ".join(uniq), n_scripted))
    a, b = uniq
    return "mix__%s__%s__k%d" % (a, b, models.count(a))


def game_to_wide_row(game: dict, seats: dict, endowment: float, experiment: str) -> dict:
    """Một ván -> một dict 82 cột. ``seats`` = {player_name: {round: turn}}."""
    names = sorted(seats, key=lambda p: int(p.rsplit("_", 1)[-1]))
    if len(names) != N_PLAYERS:
        raise ValueError(f"{game['game_id']}: {len(names)} ghe, cho {N_PLAYERS}")

    rounds = sorted({r for s in seats.values() for r in s})
    played = len(rounds)
    catastrophe = int(float(game.get("catastrophe", 0)))

    per_seat, contribs = {}, {}
    for i, p in enumerate(names, 1):
        by_round = seats[p]
        if sorted(by_round) != rounds:
            raise ValueError(f"{game['game_id']}/{p}: thieu vong {set(rounds) - set(by_round)}")
        c = [float(by_round[r]["contribution"]) for r in rounds]
        run, acc = [], 0.0
        for x in c:
            acc += x
            run.append(endowment - acc)
        fails = sum(
            1 for r in rounds
            if by_round[r].get("parse_failed")
            or not CONTRIB_RE.search(by_round[r].get("raw_response") or "")
        )
        contribs[i] = c
        per_seat[i] = {
            f"agent{i}_name": p,
            f"agent{i}_llm": _seat_llm(by_round[rounds[0]].get("seat_model"),
                                       game["model"]),
            f"agent{i}_personality": by_round[rounds[0]].get("disposition") or "",
            f"agent{i}_knows_opponent_with_prob": 0,
            f"agent{i}_strategies": _pylist(c),
            f"agent{i}_scores": _pylist(run),
            f"agent{i}_messages": "[]",
            f"agent{i}_payoff": 0.0 if catastrophe else round(run[-1], 6),
            f"agent{i}_parse_failures": fails,
        }

    group = [sum(contribs[i][k] for i in contribs) for k in range(played)]
    pot, acc = [], 0.0
    for x in group:
        acc += x
        pot.append(acc)

    opts = sorted({int(x) for c in contribs.values() for x in c})

    row = {
        # A — định danh ván & thiết kế
        "game_id": game["game_id"],
        "experiment": experiment,
        "language": game["language"],
        "rep": int(game["rep"]),
        "seed": int(game["seed"]),
        "persona_set": game.get("persona_set", ""),
        "persona_seats": game.get("persona_seats", ""),
        "memory_mode": game.get("memory_mode", "full_history"),
        "opponent_profile": game.get("opponent_profile", ""),
        "framing": int(float(game.get("framing", 0))),
        # Hai cột dưới không tồn tại trong schema cũ. Mặc định = cấu hình baseline gốc
        # (xổ số kiểu lottery, prompt KHÔNG đưa sẵn tổng tính trước). Ván nào nhập từ
        # data cũ đều ghi rõ trong PROVENANCE.json cạnh file raw.
        "risk_framing": game.get("risk_framing") or "lottery",
        "show_computed_totals": int(float(game.get("show_computed_totals") or 0)),
        # B — luật chơi
        "n_players": N_PLAYERS,
        "endowment": endowment,
        "contribution_options": repr(opts),
        "target": float(game["target"]),
        "risk_probability": float(game["risk_probability"]),
        "n_rounds_is_known": True,
        "max_rounds": N_ROUNDS,
        "played_rounds": played,
        "agents_communicate": False,
        # C — kết cục nhóm
        "group_contributions": _pylist(group),
        "pot_cumulative": _pylist(pot),
        "group_total": float(game["group_total"]),
        "target_reached": int(float(game["target_reached"])),
        "catastrophe": catastrophe,
        "mean_payoff": float(game["mean_payoff"]),
        "n_parse_failures": sum(s[f"agent{i}_parse_failures"] for i, s in per_seat.items()),
    }
    for i in sorted(per_seat):
        row.update(per_seat[i])
    return row


def wide_fieldnames() -> list:
    """Thứ tự cột cố định — dùng cho mọi file để schema đồng nhất."""
    head = [
        "game_id", "experiment", "language", "rep", "seed", "persona_set", "persona_seats",
        "memory_mode", "opponent_profile", "framing", "risk_framing", "show_computed_totals",
        "n_players", "endowment", "contribution_options", "target", "risk_probability",
        "n_rounds_is_known", "max_rounds", "played_rounds", "agents_communicate",
        "group_contributions", "pot_cumulative", "group_total", "target_reached",
        "catastrophe", "mean_payoff", "n_parse_failures",
    ]
    for i in range(1, N_PLAYERS + 1):
        head += [f"agent{i}_{k}" for k in (
            "name", "llm", "personality", "knows_opponent_with_prob",
            "strategies", "scores", "messages", "payoff", "parse_failures")]
    return head
