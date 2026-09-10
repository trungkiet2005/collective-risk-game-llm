"""Nhập lưới risk B (thí nghiệm B, §7.0 của plan) từ Legacy_Results vào results/.

Data cũ ở `Legacy_Results/results/frontier/dense_grid/` đã chạy đúng config baseline
tiếng Anh trên lưới risk 11 điểm (0.0 -> 1.0, bước 0.1) cho cả 5 model panel. Script này
lọc ra tập con SẠCH và CÂN BẰNG rồi ghi thẳng ra `results/exp_baseline/<p>/<model_tag>/` (định dạng wide, §9).

Ba việc nó làm, theo đúng thứ tự:

1. **Loại lượt bị cắt output.** Một `raw_response` không chứa `CONTRIBUTION:` nghĩa là
   model bị cắt trước khi kịp ra quyết định; parser rơi xuống nhánh quét chữ số và bịa ra
   một con số từ chính đoạn suy luận, rồi vẫn trả `parse_failed=False`. Ván nào dính dù
   chỉ MỘT lượt như vậy cũng bị loại cả ván (60 quyết định của ván đó đã lệch quỹ đạo).
   `qwen3-235b` mất sạch vì lý do này -> nó KHÔNG có trong danh sách nhập, phải chạy lại.

2. **Chọn cùng một tập rep cho mọi mức risk.** Xổ số thảm hoạ chỉ phụ thuộc `rep`, nên
   cùng `rep` ở hai mức risk khác nhau dùng chung một số ngẫu nhiên (common random
   numbers) — kỹ thuật giảm phương sai khi so risk theo cặp. Vì vậy phải lấy GIAO của các
   rep sạch trên cả 11 mức, không phải lấy đủ số lượng ở từng mức.

3. **Cân bằng tuyệt đối.** Mọi model lấy đúng `--reps` rep (mặc định 10) trên đúng 11 mức
   -> mỗi model đúng 110 ván. Luật cân bằng ở §7 của plan: số ván do thiết kế quyết định,
   không bao giờ do giá model quyết định.

Dùng:
    python plan/scripts/import_legacy_b.py --dry-run     # xem trước, không ghi
    python plan/scripts/import_legacy_b.py               # ghi vào results/
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from crsd.dataio.wide_csv import (  # noqa: E402
    game_to_wide_row, group_turns, infer_endowment, wide_fieldnames,
)
from to_wide_csv import risk_token  # noqa: E402

SRC = pathlib.Path("Legacy_Results/results/frontier/dense_grid")
DST = pathlib.Path("results")
EXPERIMENT = "exp_baseline"
RISKS = [f"{x / 10:.1f}" for x in range(11)]

# qwen3-235b KHONG co trong danh sach: 0 rep sach tren ca 11 muc (xem plan §7.0).
MODELS = [
    "anthropic-claude-haiku-4-5-20251001",
    "google-gemini-3.5-flash-lite",
    "openai-gpt-5.6-luna",
    "xai-grok-4.20-0309-non-reasoning",
]

CONTRIB_RE = re.compile(r"CONTRIBUTION\s*:", re.I)


def rkey(v) -> str:
    """Chuẩn hoá mức risk thành chuỗi 1 chữ số thập phân — khoá join duy nhất.

    games.csv ghi "1.0" còn turns.jsonl ghi 1.0 (float); so chuỗi thô sẽ trượt.
    """
    return f"{float(v):.1f}"


def scan_turns(path):
    """Trả về (mọi lượt theo ván, tập ván có ít nhất một lượt bị cắt).

    Khoá ván ở đây là (risk, rep) chứ không phải `game_id`: trong schema cũ, `game_id`
    của turns.jsonl KHÔNG mang hậu tố ngôn ngữ/rep nên nó trùng nhau giữa các rep.
    """
    by_game = collections.defaultdict(list)
    truncated = set()
    for line in path.open(encoding="utf-8"):
        t = json.loads(line)
        key = (rkey(t["risk_probability"]), str(t["rep"]))
        by_game[key].append(t)
        if not CONTRIB_RE.search(t.get("raw_response") or ""):
            truncated.add(key)
    return by_game, truncated


def pick_reps(games, truncated, n):
    """n rep nhỏ nhất SẠCH ở CẢ 11 mức risk (giao, không phải min từng cột)."""
    have = collections.defaultdict(set)
    for g in games:
        key = (rkey(g["risk_probability"]), str(g["rep"]))
        if key not in truncated:
            have[key[0]].add(int(key[1]))
    missing = [r for r in RISKS if r not in have]
    if missing:
        return [], missing
    return sorted(set.intersection(*[have[r] for r in RISKS]))[:n], []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=10, help="so rep moi muc risk (mac dinh 10)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SRC.is_dir():
        print(f"KHONG thay {SRC}", file=sys.stderr)
        return 1

    total_games = 0
    prov = {}
    for model in MODELS:
        d = SRC / model / "exp_baseline"
        games_p, turns_p = d / "games.csv", d / "turns.jsonl"
        if not (games_p.is_file() and turns_p.is_file()):
            print(f"  BO QUA {model}: thieu games.csv hoac turns.jsonl", file=sys.stderr)
            continue

        games = list(csv.DictReader(games_p.open(encoding="utf-8")))
        by_game, truncated = scan_turns(turns_p)
        reps, missing = pick_reps(games, truncated, args.reps)

        if missing:
            print(f"  LOI {model}: thieu han muc risk {missing}", file=sys.stderr)
            return 1
        if len(reps) < args.reps:
            print(f"  LOI {model}: chi co {len(reps)} rep sach chung, can {args.reps}", file=sys.stderr)
            return 1

        want = {(r, str(p)) for r in RISKS for p in reps}
        keep_games = [g for g in games if (rkey(g["risk_probability"]), str(g["rep"])) in want]
        keep_turns = [t for k in sorted(want) for t in by_game.get(k, [])]

        expect = len(RISKS) * args.reps
        if len(keep_games) != expect:
            print(f"  LOI {model}: chon duoc {len(keep_games)} van, cho {expect}", file=sys.stderr)
            return 1
        if len(keep_turns) != expect * 60:
            print(f"  LOI {model}: {len(keep_turns)} luot, cho {expect * 60}", file=sys.stderr)
            return 1

        print(f"  {model:<38} {len(keep_games):>4} van, {len(keep_turns):>6} luot, "
              f"rep {reps[0]}..{reps[-1]}, {len(truncated)} van bi loai vi cat output")
        total_games += len(keep_games)

        if args.dry_run:
            continue

        # Ghi THANG sang layout moi (khong con buoc trung gian results/raw/).
        endowment = infer_endowment(keep_games)
        seats_by_game = group_turns(keep_turns)
        cells = {}
        for g in keep_games:
            k = (rkey(g["risk_probability"]), str(g["rep"]))
            row = game_to_wide_row(g, seats_by_game[k], endowment, EXPERIMENT)
            cells.setdefault((risk_token(g["risk_probability"]), g["language"]), []).append(row)
        for (ptok, lang), rows in sorted(cells.items()):
            rows.sort(key=lambda r: r["rep"])
            dest = DST / EXPERIMENT / ptok / model
            dest.mkdir(parents=True, exist_ok=True)
            with (dest / f"p{ptok}_{lang}_{model}.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=wide_fieldnames())
                w.writeheader()
                w.writerows(rows)
        prov[model] = {
            "imported_from": str(d).replace("\\", "/"),
            "risk_levels": RISKS,
            "reps": reps,
            "n_games": len(keep_games),
            "games_dropped_truncated": len(truncated),
        }

    if not args.dry_run:
        (DST / "PROVENANCE.json").write_text(json.dumps({
            "generated_by": "plan/scripts/import_legacy_b.py",
            "date": "2026-09-10",
            "experiment": EXPERIMENT,
            "note": "Luoi risk B (plan §7.0). Da loai van co luot bi cat output; reps chon theo "
                    "giao tren ca 11 muc de giu common random numbers. Hai cot risk_framing / "
                    "show_computed_totals KHONG co trong schema cu -> dien mac dinh lottery/0 "
                    "(dung cau hinh baseline goc, nhung la SUY RA chu khong doc tu file).",
            "models": prov,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nTONG: {total_games} van vao {DST}{' (dry-run, chua ghi)' if args.dry_run else ''}")
    print("Con thieu: qwen3-235b — phai chay lai server-side (plan §11, ngay 12/09).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
