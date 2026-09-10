"""Định tuyến THEO GHẾ: mỗi ghế trong bàn có thể do một backend khác nhau cầm.

``run_games_batched`` gom prompt của (mọi game × mọi ghế) thành MỘT danh sách
phẳng rồi gọi ``send_batch(prompts, seeds)``. Router ở đây bọc lại đúng giao diện
đó: nó cắt danh sách phẳng thành từng nhóm theo model sở hữu slot, gọi MỖI backend
ĐÚNG MỘT LẦN với phần của nó, rồi ghép trả về ĐÚNG THỨ TỰ BAN ĐẦU.

Thứ tự là thứ sống còn: engine ``zip(self.agents, responses)`` theo vị trí, nên
lệch một ô là gán nhầm quyết định cho người chơi khác mà KHÔNG có lỗi nào bật lên.
Vì thế router luôn ghi trả về vào đúng chỉ số gốc (``out[i] = resp[j]``) và kiểm
tra không còn ô trống trước khi trả.

Ghế của từng slot lấy từ ``contexts[i]["seat"]`` (engine cấp — xem
``CrsdGame.build_round_contexts``). Nhờ vậy đường retry (chỉ gửi lại MỘT TẬP CON
các slot hỏng) vẫn định tuyến đúng, thay vì đoán theo ``i % nPlayers``.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Sequence


def wants_context(send_batch) -> bool:
    """Backend này có TỰ KHAI BÁO cần ``contexts`` không? (scripted/router có)."""
    return bool(getattr(send_batch, "wants_context", False))


def call_backend(send_batch, prompts, seeds=None, contexts=None):
    """Gọi một backend, chỉ kèm ``contexts`` khi backend khai báo cần.

    Backend LLM cũ (offline/API/mock) KHÔNG có cờ ``wants_context`` -> được gọi
    Y HỆT như trước (``send_batch(prompts, seeds)``), nên hành vi run cũ không đổi.
    """
    if contexts is not None and wants_context(send_batch):
        return send_batch(prompts, seeds, contexts=contexts)
    return send_batch(prompts, seeds)


def seats_for_slots(n_slots: int, contexts: Optional[Sequence], n_seats: int) -> List[int]:
    """Ghế của từng slot trong một lô prompt phẳng.

    Ưu tiên ``contexts[i]["seat"]`` (chính xác cả với lô con lúc retry). Không có
    contexts thì suy theo VỊ TRÍ (``i % n_seats``) — đúng cho lô lockstep đầy đủ
    (mỗi game đóng góp đúng ``n_seats`` prompt liên tiếp, xem ``run_games_batched``)
    và cho ``CrsdGame.run``; lô con lệch bội số thì báo lỗi thay vì đoán bừa.
    """
    if n_seats <= 0:
        raise ValueError("n_seats phải > 0")
    if contexts is not None:
        if len(contexts) != n_slots:
            raise ValueError(f"{len(contexts)} contexts cho {n_slots} prompt")
        seats: List[int] = []
        for i, c in enumerate(contexts):
            seat = (c or {}).get("seat")
            if seat is None:
                raise ValueError(f"contexts[{i}] thiếu khoá 'seat' — không định tuyến được")
            seat = int(seat)
            if not (0 <= seat < n_seats):
                raise ValueError(f"contexts[{i}]['seat']={seat} ngoài phạm vi 0..{n_seats - 1}")
            seats.append(seat)
        return seats
    if n_slots % n_seats:
        raise ValueError(
            f"không có contexts và {n_slots} prompt không chia hết cho {n_seats} ghế "
            f"-> không suy được ghế theo vị trí"
        )
    return [i % n_seats for i in range(n_slots)]


def make_seat_router(
    seat_models: Sequence[str],
    backend_for: Callable[[str], Callable],
) -> Callable[..., List]:
    """``send_batch`` định tuyến theo ghế.

    ``seat_models[i]`` = tên model/chính sách cầm ghế ``i`` (dài đúng bằng số ghế).
    ``backend_for(name)`` dựng backend cho một tên; mỗi TÊN chỉ dựng một lần, nên
    hai ghế cùng model dùng CHUNG backend và được gộp vào CÙNG một lời gọi.
    """
    seat_models = [str(m) for m in seat_models]
    n_seats = len(seat_models)
    if n_seats == 0:
        raise ValueError("seat_models rỗng")

    backends = {}
    for name in seat_models:
        if name not in backends:
            backends[name] = backend_for(name)

    def route(prompts, seeds=None, contexts=None):
        n = len(prompts)
        seats = seats_for_slots(n, contexts, n_seats)

        # Gom chỉ số gốc theo model. dict giữ thứ tự chèn -> thứ tự gọi backend
        # tất định (cùng input, cùng chuỗi lời gọi) để test/trace ổn định.
        groups = {}
        for i, seat in enumerate(seats):
            groups.setdefault(seat_models[seat], []).append(i)

        out: List = [None] * n
        filled = [False] * n
        for name, idxs in groups.items():
            sub_prompts = [prompts[i] for i in idxs]
            sub_seeds = [seeds[i] for i in idxs] if seeds is not None else None
            sub_ctx = [contexts[i] for i in idxs] if contexts is not None else None
            resp = list(call_backend(backends[name], sub_prompts, sub_seeds, sub_ctx))
            if len(resp) != len(idxs):
                raise RuntimeError(
                    f"backend {name!r} trả về {len(resp)} phản hồi cho {len(idxs)} prompt"
                )
            for j, i in enumerate(idxs):   # ghép về ĐÚNG chỉ số gốc
                out[i] = resp[j]
                filled[i] = True
        if not all(filled):
            missing = [i for i, ok in enumerate(filled) if not ok]
            raise RuntimeError(f"định tuyến bỏ sót slot: {missing[:10]}")
        return out

    route.wants_context = True
    route.seat_models = list(seat_models)
    route.backends = backends
    return route
