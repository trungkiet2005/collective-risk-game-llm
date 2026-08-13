"""Gom các shard đã tải về thành một dataset exp_baseline hoàn chỉnh cho mỗi model.

Mỗi shard là output của một `kaggle b t run` chạy một phần sweep (ví dụ 1 mức risk,
hoặc 1 cặp risk×lang). Script này đi tìm mọi games.csv/turns.jsonl trong thư mục tải về,
gộp theo model, kiểm tra phủ đủ 60 cell (3 risk × 2 lang × 10 rep), rồi ghi ra
results/frontier/<model_tag>/exp_baseline/.

An toàn về seed: sampling_seed phụ thuộc (rep, agent, round) và xổ số thảm hoạ chỉ phụ
thuộc rep — cả hai KHÔNG phụ thuộc shard. Nên chia sweep theo risk/lang cho ra kết quả
byte-identical với một run không chia.

Dùng:
    # xem trước, không ghi gì
    python plan/scripts/merge_shards.py --src downloads/ --dry-run

    # ghi thật
    python plan/scripts/merge_shards.py --src downloads/ --out results/frontier

    # chỉ gom 1 model
    python plan/scripts/merge_shards.py --src downloads/ --only claude-opus-5
"""
import argparse
import csv
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

EXPECTED_RISKS = {0.9, 0.5, 0.1}
EXPECTED_LANGS = {"en", "vn"}
EXPECTED_REPS = set(range(10))
EXPECTED_CELLS = len(EXPECTED_RISKS) * len(EXPECTED_LANGS) * len(EXPECTED_REPS)  # 60


def find_shards(srcs, exclude=("SMOKE",)):
    """Mọi thư mục có games.csv là một shard. Trả về [(games_path, turns_path)].

    Bỏ qua đường dẫn chứa tiền tố trong `exclude`: shard smoke chạy đúng cell
    (0.9, en, rep0) nên game_id của nó TRÙNG với shard thật của cell đó. Giữ lại
    thì dataset cuối lẫn một ván có nguồn gốc khác — loại cho sạch provenance.
    """
    shards = []
    seen_paths = set()
    for src in ([srcs] if isinstance(srcs, (str, Path)) else srcs):
      for games in sorted(Path(src).rglob("games.csv")):
        parts = set(games.parts)
        if any(any(p.startswith(x) for p in parts) for x in exclude):
            continue
        key = games.resolve()
        if key in seen_paths:
            continue
        seen_paths.add(key)
        turns = games.parent / "turns.jsonl"
        shards.append((games, turns if turns.is_file() else None))
    return shards


def load_shard(games_path, turns_path):
    with open(games_path, encoding="utf-8-sig", newline="") as f:
        games = list(csv.DictReader(f))
    turns = []
    if turns_path:
        with open(turns_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    turns.append(json.loads(line))
    return games, turns


def merge(srcs, out, only=None, dry_run=False, want_experiment="exp_baseline", exclude=None):
    shards = find_shards(srcs, tuple(x for x in (exclude or "").split(",") if x) or ("SMOKE",))
    if not shards:
        print(f"KHONG tim thay games.csv nao duoi {srcs}", file=sys.stderr)
        return 1

    by_model_games = defaultdict(dict)   # model_tag -> {game_id: row}
    by_model_turns = defaultdict(list)
    conflicts = []
    shard_info = []

    for games_path, turns_path in shards:
        # Tên thư mục chứa games.csv là tên experiment (exp_baseline, exp_persona, ...).
        # Phải tách theo experiment: cùng một model có nhiều experiment, gộp chung là
        # trộn dataset của 2 thí nghiệm khác nhau.
        experiment = games_path.parent.name
        if experiment != want_experiment:
            continue
        games, turns = load_shard(games_path, turns_path)
        if not games:
            continue
        tag = games[0]["model"]
        if only and only not in tag:
            continue
        added = 0
        fresh = set()          # game_id mà CHÍNH shard này đóng góp
        for row in games:
            gid = row["game_id"]
            if gid in by_model_games[tag]:
                # Cùng game_id ở 2 shard: chỉ báo động nếu nội dung khác nhau.
                if by_model_games[tag][gid] != row:
                    conflicts.append((tag, gid, str(games_path)))
                continue
            by_model_games[tag][gid] = row
            fresh.add(gid)
            added += 1
        # CHỈ lấy lượt của những ván shard này thực sự đóng góp. Nếu lấy theo
        # `game_id in <tất cả đã thấy>` thì một game_id trùng ở 2 shard sẽ nhân đôi
        # số lượt (1 ván 120 lượt) trong khi ván chỉ được đếm 1 lần — sai lệch âm
        # thầm, chỉ lộ ra ở phép kiểm 60-lượt/ván.
        by_model_turns[tag].extend(t for t in turns if t["game_id"] in fresh)
        shard_info.append((tag, str(games_path.parent), len(games), added))

    if conflicts:
        print(f"\n!! {len(conflicts)} game_id trung nhau nhung NOI DUNG KHAC:", file=sys.stderr)
        for tag, gid, p in conflicts[:10]:
            print(f"   {tag} {gid}  <- {p}", file=sys.stderr)
        print("   Nghia la 2 shard chay cung mot cell -> kiem lai cach chia sweep.",
              file=sys.stderr)

    print(f"\nDoc {len(shard_info)} shard:")
    for tag, d, n, added in shard_info:
        print(f"  {n:>3} van ({added:>3} moi)  {tag:<42} {d}")

    exit_code = 0
    for tag in sorted(by_model_games):
        games = list(by_model_games[tag].values())
        turns = by_model_turns[tag]

        # --- kiem tra phu cell ---
        risks = {round(float(g["risk_probability"]), 2) for g in games}
        langs = {g["language"] for g in games}
        reps = {int(g["rep"]) for g in games}
        cells = {(round(float(g["risk_probability"]), 2), g["language"], int(g["rep"]))
                 for g in games}
        missing = {(r, l, p) for r in EXPECTED_RISKS for l in EXPECTED_LANGS
                   for p in EXPECTED_REPS} - cells
        pf = sum(int(t.get("parse_failed", 0)) for t in turns)

        print(f"\n=== {tag}")
        print(f"  van        : {len(games)} / {EXPECTED_CELLS}")
        print(f"  risk       : {sorted(risks, reverse=True)}")
        print(f"  language   : {sorted(langs)}")
        print(f"  rep        : {min(reps) if reps else '-'}..{max(reps) if reps else '-'}"
              f" ({len(reps)} gia tri)")
        print(f"  luot        : {len(turns)}  (ky vong {len(games) * 60})")
        print(f"  parse_failed: {pf}")

        ok = True
        if missing:
            ok = False
            print(f"  THIEU {len(missing)} cell, vi du: {sorted(missing)[:6]}")
        if pf:
            ok = False
            print("  parse_failed > 0 -> KHONG dung ket qua nay truoc khi dieu tra")
        if len(turns) != len(games) * 60:
            ok = False
            print("  so luot khong khop 60/van -> shard bi cat giua duong?")
        print("  => " + ("DAY DU" if ok else "CHUA DUNG DUOC"))
        if not ok:
            exit_code = 1

        if dry_run:
            continue

        # --- ghi ra ---
        dest = Path(out) / tag / want_experiment
        dest.mkdir(parents=True, exist_ok=True)
        games.sort(key=lambda g: (-float(g["risk_probability"]), g["language"], int(g["rep"])))
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(games[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(games)
        (dest / "games.csv").write_text(buf.getvalue(), encoding="utf-8")

        order = {g["game_id"]: i for i, g in enumerate(games)}
        turns.sort(key=lambda t: (order.get(t["game_id"], 10**9), t["round"], t["player"]))
        with open(dest / "turns.jsonl", "w", encoding="utf-8") as f:
            for t in turns:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        print(f"  ghi -> {dest}")

    return exit_code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, nargs="+",
                    help="mot hoac nhieu thu muc chua shard da tai ve")
    ap.add_argument("--out", default="results/frontier")
    ap.add_argument("--only", default=None, help="chi gom model co ten chua chuoi nay")
    ap.add_argument("--experiment", default="exp_baseline",
                    help="ten experiment = ten thu muc chua games.csv (mac dinh exp_baseline)")
    ap.add_argument("--exclude", default="SMOKE",
                    help="bo qua shard co duong dan chua tien to nay (phay ngan cach)")
    ap.add_argument("--dry-run", action="store_true", help="chi kiem tra, khong ghi")
    args = ap.parse_args()
    return merge(args.src, args.out, args.only, args.dry_run, args.experiment, args.exclude)


if __name__ == "__main__":
    sys.exit(main())
