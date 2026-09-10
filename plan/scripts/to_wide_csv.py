"""Sinh cây `results/` (định dạng wide kiểu FAIRGAME) từ output shard.

    results/<experiment>/<p>/<model_tag>/p<p>_<lang>_<model_tag>.csv

Đọc mọi cặp `games.csv` + `turns.jsonl` nằm bất kỳ đâu dưới `--src` (thư mục shard tải về,
ví dụ `plan/runs/`), chuyển sang wide 82 cột rồi ghi thẳng vào `results/`.

**KHÔNG còn `results/raw/`.** Trước đây có một bước trung gian chép long-format vào
`results/raw/`; bỏ từ 10-09-2026. Hệ quả phải biết: `results/` **không chứa reasoning và
prompt** — chúng chỉ nằm trong `turns.jsonl` của shard gốc dưới `--src`. Muốn giữ lại thì
backup thư mục shard, vì `results/` không dựng lại được chúng.

Gộp shard: nhiều shard cùng đóng góp vào một file đích (sweep hay chia theo risk/rep).
Script gộp hết rồi sắp theo `rep`.

**Trùng `rep` trong cùng một ô là LỖI theo mặc định**, và đây không phải chuyện hiếm: chạy
lại một shard bị 429 sẽ chơi lại đúng những ô nó đã kịp xong. Đo thật 10-09-2026 trên
`qwen3-235b`: **31/54 ô chạy lại cho kết quả KHÁC nhau (57%)** dù cùng `seed` và cùng
`temperature=0.7` — proxy KHÔNG tái lập được văn bản model sinh ra. Nên hai lần chạy cùng
một ô là hai QUAN SÁT khác nhau, không phải bản sao; trộn chúng là trộn hai run.

`--on-conflict`:
  * `error` (mặc định) — dừng, để người chạy quyết. An toàn nhất.
  * `newest` — lấy dòng từ file shard MỚI nhất theo mtime, in cảnh báo kèm số ô bị ghi đè.
    Dùng khi một shard phải chạy lại nhiều lần và bạn muốn giữ lần chạy sau cùng.

Đặc tả schema + quy ước đường dẫn: `plan/aamas2027-plan.md` §9.

Dùng:
    python plan/scripts/to_wide_csv.py --src plan/runs
    python plan/scripts/to_wide_csv.py --src plan/runs --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from crsd.dataio.wide_csv import (  # noqa: E402
    game_to_wide_row, group_turns, infer_endowment, wide_fieldnames,
)


def risk_token(v) -> str:
    """Chuỗi mức risk dùng CHUNG cho tên thư mục và tên file.

    Bỏ số 0 thừa: 0.9 -> "0.9", 1.0 -> "1", 0.0 -> "0". Corpus PD cũng vậy, và loader sắp
    xếp thư mục bằng ``float(p.name)`` nên tên bắt buộc parse được thành số.
    """
    return f"{float(v):.1f}".rstrip("0").rstrip(".") or "0"


def find_shards(src: pathlib.Path, exclude=("SMOKE",)):
    """Mọi thư mục có games.csv là một shard. Bỏ shard smoke: nó chạy đúng ô của shard
    thật nên game_id trùng, giữ lại thì dataset lẫn hai nguồn."""
    out = []
    for g in sorted(src.rglob("games.csv")):
        if any(p.startswith(x) for p in g.parts for x in exclude):
            continue
        t = g.parent / "turns.jsonl"
        if t.is_file():
            out.append((g, t))
        else:
            print(f"  BO QUA {g.parent}: thieu turns.jsonl", file=sys.stderr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", nargs="+", required=True, help="thu muc chua shard da tai ve")
    ap.add_argument("--out", default="results")
    ap.add_argument("--experiment", default=None,
                    help="ep ten experiment; mac dinh lay ten thu muc cha cua games.csv")
    ap.add_argument("--only-model", nargs="*", default=None,
                    help="chi gom nhung model_tag nay (thu muc shard hay lan nhieu model)")
    ap.add_argument("--allow-shrink", action="store_true",
                    help="cho phep ghi de file dang co bang ban IT van hon")
    ap.add_argument("--on-conflict", choices=("error", "newest"), default="error",
                    help="trung rep ma noi dung khac nhau: dung han, hay lay file moi nhat")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shards = [s for d in args.src for s in find_shards(pathlib.Path(d))]
    if not shards:
        print(f"KHONG tim thay games.csv nao duoi {args.src}", file=sys.stderr)
        return 1

    fields = wide_fieldnames()
    buckets: dict[tuple, dict[int, tuple]] = {}
    conflicts = []
    n_games = 0

    for games_p, turns_p in shards:
        experiment = args.experiment or games_p.parent.name
        model_tag = games_p.parent.parent.name
        if args.only_model and model_tag not in args.only_model:
            continue
        games = list(csv.DictReader(games_p.open(encoding="utf-8")))
        if not games:
            continue
        turns = [json.loads(l) for l in turns_p.open(encoding="utf-8")]
        endowment = infer_endowment(games)
        seats_by_game = group_turns(turns)

        for g in games:
            key = (f"{float(g['risk_probability']):.1f}", str(g["rep"]))
            seats = seats_by_game.get(key)
            if not seats:
                print(f"  LOI {games_p}: khong co luot cho risk={key[0]} rep={key[1]}", file=sys.stderr)
                return 1
            row = game_to_wide_row(g, seats, endowment, experiment)
            cell = (experiment, risk_token(g["risk_probability"]), model_tag, g["language"])
            store = buckets.setdefault(cell, {})
            prev = store.get(row["rep"])
            if prev is not None and prev[0] != row:
                if args.on_conflict == "error":
                    err = sys.stderr
                    print(f"  LOI: trung rep={row['rep']} o {cell} nhung noi dung KHAC nhau.", file=err)
                    print("       Day la hai LAN CHAY khac nhau cua cung mot o, khong phai", file=err)
                    print("       ban sao — proxy khong tai lap duoc van ban model sinh ra.", file=err)
                    print(f"       nguon A: {prev[1]}", file=err)
                    print(f"       nguon B: {games_p}", file=err)
                    print("       Dung --on-conflict newest de lay lan chay moi nhat.", file=err)
                    return 1
                conflicts.append((cell, row["rep"]))
                if games_p.stat().st_mtime <= prev[1].stat().st_mtime:
                    continue                      # giu ban moi hon
            store[row["rep"]] = (row, games_p)
            n_games += 1

    out_root = pathlib.Path(args.out)
    # CHOT AN TOAN. Mot lan gom hep pham vi (vd chi mot model) van tro toi cung cay
    # `results/`, va ghi de la ghi de TOAN BO file. File moi it van hon file dang co gan
    # nhu chac chan la mat data am tham -> chan lai. Bat duoc dung ca nay 10-09-2026: gom
    # rieng qwen nhung --src quet trung ca haiku/luna trong cung thu muc account, suyt ghi
    # de file 10 van bang ban 8-9 van.
    shrink = []
    for (experiment, ptok, model_tag, lang), by_rep in sorted(buckets.items()):
        dest = out_root / experiment / ptok / model_tag / f"p{ptok}_{lang}_{model_tag}.csv"
        if dest.is_file():
            have = sum(1 for _ in dest.open(encoding="utf-8")) - 1
            if have > len(by_rep):
                shrink.append((dest, have, len(by_rep)))
    if shrink and not args.allow_shrink:
        err = sys.stderr
        print("", file=err)
        print(f"!! DUNG: {len(shrink)} file se bi ghi de bang BAN IT VAN HON.", file=err)
        for d, a, b in shrink[:8]:
            print(f"   {d}: dang co {a} van -> ban moi chi {b}", file=err)
        print("   Nhieu kha nang --src quet trung model khac. Dung --only-model de thu hep,", file=err)
        print("   hoac --allow-shrink neu that su co y giam so van.", file=err)
        return 1
    n_files = n_rows = 0
    for (experiment, p, model_tag, lang), by_rep in sorted(buckets.items()):
        rows = [by_rep[r][0] for r in sorted(by_rep)]
        dest = out_root / experiment / p / model_tag
        fname = f"p{p}_{lang}_{model_tag}.csv"
        n_files += 1
        n_rows += len(rows)
        if args.dry_run:
            print(f"  [dry] {dest / fname}  ({len(rows)} van)")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        with (dest / fname).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    print(f"\n{len(shards)} shard -> {n_rows} van trong {n_files} file"
          f"{' (dry-run, chua ghi)' if args.dry_run else f' duoi {out_root}/'}")
    print(f"Schema: {len(fields)} cot. Nho chay verify_wide.py sau khi ghi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
