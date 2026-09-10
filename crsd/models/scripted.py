"""Agent KỊCH BẢN (scripted): "backend" tất định, không gọi LLM.

Mỗi chính sách được gói thành một hàm ``send_batch(prompts, seeds=None,
contexts=None)`` — CÙNG giao diện với backend LLM (xem ``crsd.models.factory``) —
nên engine KHÔNG cần bất kỳ nhánh riêng nào: ghế nào cầm chính sách nào chỉ là
chuyện định tuyến (xem ``crsd.models.routing``).

Văn bản trả về LUÔN có dòng ``CONTRIBUTION: <n>`` neo đầu dòng, tức đúng định dạng
mà ``crsd.engine.round.parse_contribution`` nhận (parse_failed=False) -> mọi thứ
phía sau (log, recorder, phân tích) chạy y nguyên, không phải sửa gì.

Chính sách LUÔN TẤT ĐỊNH và ĐỘC LẬP VỚI SEED: ``seeds`` bị bỏ qua hoàn toàn, nên
chạy lại (kể cả vòng retry parse-fail với seed mới) cho ra đúng chuỗi hành động cũ.

Ngữ cảnh (``contexts``) là kênh máy-đọc-được do engine cấp cho từng slot prompt
(xem ``CrsdGame.build_round_contexts``): ghế, vòng, luật chơi, lịch sử. Nhờ nó
chính sách KHÔNG phải bới chữ trong prompt (vốn đổi theo ngôn ngữ/template).
"""
from __future__ import annotations

from typing import Callable, List, Optional

# Tiền tố nhận diện một "model name" thật ra là chính sách kịch bản, dùng trong
# config: "scripted:always_4". Không model LLM nào trong repo bắt đầu bằng chuỗi
# này nên thêm nhánh nhận diện là tương thích ngược tuyệt đối.
SCRIPTED_PREFIX = "scripted:"

# Tập lựa chọn mặc định khi gọi chính sách mà KHÔNG có ngữ cảnh (chỉ hợp lệ với
# các chính sách hằng số) — trùng mặc định của GameConfig.
DEFAULT_OPTIONS = [0, 2, 4]


def is_scripted_model(name) -> bool:
    """``name`` có phải tên chính sách kịch bản ("scripted:xxx") không?"""
    return isinstance(name, str) and name.startswith(SCRIPTED_PREFIX)


def scripted_policy_name(name: str) -> str:
    """"scripted:always_4" -> "always_4" (đã có tiền tố thì cắt, chưa có thì giữ)."""
    return name[len(SCRIPTED_PREFIX):] if is_scripted_model(name) else name


def _fmt(x) -> str:
    """2.0 -> '2' — parser chỉ bắt ``\\d+`` nên phải in ra số nguyên."""
    f = float(x)
    return str(int(f)) if f.is_integer() else str(f)


def nearest_option(value: float, options=None) -> float:
    """Làm tròn ``value`` về lựa chọn HỢP LỆ gần nhất.

    Hoà (cách đều hai mức) -> chọn mức THẤP hơn: bảo thủ, và trùng quy ước fallback
    của ``parse_contribution`` (lấy ``opts[0]``). Tất định nên test khoá được.
    """
    opts = sorted(float(o) for o in (options or DEFAULT_OPTIONS))
    if not opts:
        return 0.0
    best = opts[0]
    best_d = abs(float(value) - best)
    for o in opts[1:]:
        d = abs(float(value) - o)
        if d < best_d - 1e-9:          # strict -> hoà thì GIỮ mức thấp hơn
            best, best_d = o, d
    return best


def _fair_share(ctx: dict) -> float:
    """Phần đóng góp "đúng phần mình" MỖI VÒNG = target / (nPlayers × nRounds).

    Chính là ``{fairShare}`` trong prompt (Milinski: 120/(6×10) = 2).
    """
    n = int(ctx.get("n_players", 6))
    r = int(ctx.get("n_rounds", 10))
    denom = n * r
    return (float(ctx.get("target", 0.0)) / denom) if denom else 0.0


# --- các chính sách: ctx (dict) -> mức đóng góp (đã hợp lệ hoá) ---


def _make_always(k: float) -> Callable[[dict], float]:
    def policy(ctx: dict) -> float:
        return nearest_option(k, ctx.get("options"))
    return policy


def _ev_maximiser(ctx: dict) -> float:
    """Tối đa hoá kỳ vọng tiền mặt (rủi ro trung lập).

    So sánh hai nước đi thuần:
      - Không đóng gì  -> giữ nguyên ``endowment``, nhưng nhóm trượt target nên chỉ
        sống sót với xác suất ``1 - p``  =>  kỳ vọng = (1 - p) × endowment.
      - Đóng đúng phần mình cả ván -> chi phí = target / nPlayers (chắc chắn).
    Đóng 0 khi ``(1 - p) × endowment > target / nPlayers``; ngược lại đóng phần
    mình mỗi vòng (``fairShare``), làm tròn về lựa chọn hợp lệ.

    Với tham số Milinski (E=40, target=120, n=6) ngưỡng là p* = 1 − 20/40 = 0.5:
    p ≥ 0.5 -> đóng 2/vòng; p < 0.5 -> đóng 0. Chính sách này KHÔNG nhìn lịch sử
    (không đội lốt điều kiện) — nó là mốc "duy lý rủi ro trung lập" thuần tuý.
    """
    p = float(ctx["risk_probability"])
    endowment = float(ctx["endowment"])
    n = int(ctx["n_players"])
    share_cost = (float(ctx["target"]) / n) if n else 0.0
    opts = ctx.get("options")
    if (1.0 - p) * endowment > share_cost:
        return nearest_option(0.0, opts)
    return nearest_option(_fair_share(ctx), opts)


def _conditional_cooperator(ctx: dict) -> float:
    """Hợp tác có điều kiện: bắt chước TRUNG BÌNH của NHỮNG NGƯỜI KHÁC vòng trước.

    Vòng 1 (chưa có lịch sử) -> hợp tác: đóng đúng phần mình (``fairShare``).
    Các vòng sau -> trung bình đóng góp của n−1 người còn lại ở vòng LIỀN TRƯỚC,
    làm tròn về lựa chọn hợp lệ gần nhất (hoà -> mức thấp hơn).
    """
    opts = ctx.get("options")
    history = ctx.get("history") or []
    if not history:
        return nearest_option(_fair_share(ctx), opts)
    seat = int(ctx.get("seat", 0))
    last = list(history[-1])
    others = [float(c) for i, c in enumerate(last) if i != seat]
    mean = (sum(others) / len(others)) if others else 0.0
    return nearest_option(mean, opts)


# name -> (hàm quyết định, có BẮT BUỘC ngữ cảnh không)
_POLICIES = {
    "always_0": (_make_always(0), False),
    "always_2": (_make_always(2), False),
    "always_4": (_make_always(4), False),
    "ev_maximiser": (_ev_maximiser, True),
    "conditional_cooperator": (_conditional_cooperator, True),
}

POLICY_NAMES = tuple(sorted(_POLICIES))


def decide(policy: str, ctx: Optional[dict] = None) -> float:
    """Mức đóng góp mà ``policy`` chọn trong ngữ cảnh ``ctx`` (tất định)."""
    name = scripted_policy_name(policy)
    if name not in _POLICIES:
        raise ValueError(
            f"chính sách kịch bản không tồn tại: {policy!r} (có: {', '.join(POLICY_NAMES)})"
        )
    fn, needs_ctx = _POLICIES[name]
    if ctx is None:
        if needs_ctx:
            raise ValueError(
                f"chính sách {name!r} cần ngữ cảnh (luật chơi/lịch sử) nhưng "
                f"send_batch được gọi KHÔNG kèm contexts"
            )
        ctx = {}
    return fn(ctx)


# Tên trường trong ngữ cảnh <- các tên thuộc tính tương đương ở "view" của lớp
# phân tích offline (vd ``crsd.analysis.scripted_reference.SeatView``). Chỉ ánh xạ,
# KHÔNG nhân bản logic: quyết định vẫn do đúng ``decide`` ở trên đưa ra.
_VIEW_FIELDS = {
    "seat": ("seat",),
    "round": ("round", "round_number"),
    "n_players": ("n_players",),
    "n_rounds": ("n_rounds",),
    "endowment": ("endowment",),
    "target": ("target",),
    "options": ("options", "contribution_options"),
    "risk_probability": ("risk_probability",),
    "history": ("history",),
}


def context_from(view) -> dict:
    """Chuẩn hoá một "view" trạng thái (dict hoặc object) về ngữ cảnh chính sách."""
    if isinstance(view, dict):
        return view
    ctx = {}
    for key, names in _VIEW_FIELDS.items():
        for name in names:
            if hasattr(view, name):
                ctx[key] = getattr(view, name)
                break
    if ctx.get("history") is not None:
        ctx["history"] = [list(r) for r in ctx["history"]]
    if ctx.get("options") is not None:
        ctx["options"] = list(ctx["options"])
    return ctx


def policy_for_view(policy: str) -> Callable[[object], float]:
    """Chính sách dạng ``policy(view) -> mức đóng góp`` (KHÔNG qua send_batch).

    Dành cho các lớp chạy chính sách ngoài vòng lặp batch — vd đường tham chiếu
    offline trong ``crsd.analysis`` — để chúng dùng CHUNG một cài đặt chính sách
    với bàn chơi thật thay vì tự viết lại. ``view`` là dict ngữ cảnh, hoặc bất kỳ
    object nào có các thuộc tính tương ứng (xem ``_VIEW_FIELDS``).

    CỐ Ý KHÔNG đặt tên ``get_policy``: ``crsd.analysis.scripted_reference`` dò đúng
    tên đó để TỰ ĐỘNG thay chính sách nội bộ của nó bằng module này. ``ev_maximiser``
    ở đây là mốc EV THUẦN (chỉ so (1-p)·endowment với target/n), còn bản của E7 còn
    biết dừng khi target đã đạt/không thể đạt — tự động tráo sẽ âm thầm đổi đường
    tham chiếu của E7. Muốn hợp nhất thì phải chốt ngữ nghĩa trước, rồi thêm
    "policy_for_view" vào ``_EXTERNAL_LOOKUPS`` bên đó.
    """
    name = scripted_policy_name(policy)
    if name not in _POLICIES:
        raise ValueError(
            f"chính sách kịch bản không tồn tại: {policy!r} (có: {', '.join(POLICY_NAMES)})"
        )

    def policy_fn(view) -> float:
        return decide(name, context_from(view))

    policy_fn.policy_name = name
    return policy_fn


def render_response(policy: str, value: float) -> str:
    """Văn bản trả về cho engine — dòng CONTRIBUTION đúng định dạng parser nhận.

    Dòng đầu là dấu vết kiểm toán (``[scripted:xxx]``) để log ``reasoning`` nói rõ
    lượt này do chính sách nào ra quyết định; ``parse_contribution`` vẫn lấy đúng
    dòng CONTRIBUTION cuối nên con số trong tên chính sách không gây nhầm.
    """
    return f"[{SCRIPTED_PREFIX}{scripted_policy_name(policy)}]\nCONTRIBUTION: {_fmt(value)}"


def make_scripted_send_batch(policy: str) -> Callable[..., List[str]]:
    """Trả về ``send_batch`` cho một chính sách kịch bản (cùng giao diện backend LLM).

    Hàm trả về mang cờ ``wants_context = True`` -> ``crsd.models.routing.call_backend``
    (và qua đó ``run_games_batched``) sẽ kèm theo ``contexts``. Backend LLM KHÔNG có
    cờ này nên vẫn được gọi đúng hai tham số như trước.
    """
    name = scripted_policy_name(policy)
    if name not in _POLICIES:
        raise ValueError(
            f"chính sách kịch bản không tồn tại: {policy!r} (có: {', '.join(POLICY_NAMES)})"
        )

    def send(prompts, seeds=None, contexts=None) -> List[str]:
        n = len(prompts)
        if contexts is None:
            ctxs = [None] * n
        else:
            ctxs = list(contexts)
            if len(ctxs) != n:
                raise ValueError(
                    f"scripted[{name}]: {len(ctxs)} contexts cho {n} prompt"
                )
        # seeds bị BỎ QUA có chủ đích: chính sách tất định, seed không đổi kết quả.
        return [render_response(name, decide(name, ctx)) for ctx in ctxs]

    send.wants_context = True
    send.is_scripted = True
    send.policy_name = name
    return send
