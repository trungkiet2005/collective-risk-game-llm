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

`<model_tag>` suy ra từ **cấu hình ghế của từng ván** (`crsd.dataio.wide_csv.seat_model_tag`)
chứ không phải từ tên thư mục shard. Bàn đồng nhất và bàn E3a (1 ghế LLM + 5 ghế scripted)
ra đúng cái tên như trước; bàn hỗn hợp E3b ra `mix__<tagA>__<tagB>__k<k>`. Lý do: `-m` chỉ
chọn được MỘT model nên server ghi mọi cặp vào thư mục của model A — lấy tên thư mục thì
cả 4 cặp có model A đè lên nhau và mất luôn thông tin "đối thủ là ai, mấy ghế". Hệ quả:
một shard trộn nhiều cấu hình ghế tự động TÁCH thành nhiều file, không cần cờ nào.

## ⛔ Shard E3b PHẢI gom bằng `--experiment exp_mixed`

Tên thư mục mặc định của shard E3b là `exp_baseline_seats-LLLMMM-<hash>` — **34 ký tự**.
Cộng với tên `mix__<tagA>__<tagB>__k<k>` (tới 80 ký tự) **lặp lại hai lần** (thư mục và
tên file), đường dẫn tuyệt đối của cặp dài nhất (haiku + qwen) ra **261 ký tự**, vượt
trần 260 của Windows. Cái bẫy là nó hỏng MUỘN: `mkdir` qua được (thư mục ngắn hơn file),
rồi bước ghi file mới nổ — sau khi đã đọc và dựng xong toàn bộ dữ liệu.

Nên script kiểm độ dài **trước khi ghi bất cứ gì** và dừng ngay kèm cách chữa. Cách chữa
là ép tên experiment ngắn lại::

    python plan/scripts/to_wide_csv.py --src <shard E3b> --experiment exp_mixed

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
    N_PLAYERS, game_to_wide_row, group_turns, infer_endowment, seat_model_tag,
    wide_fieldnames,
)


# Trần MAX_PATH của Windows là 260 ký tự KỂ CẢ ký tự kết chuỗi, nên đường dẫn dùng được
# dài tối đa 259. Kiểm cả trên Linux chứ không khoanh vùng theo `os.name`: cây `results/`
# được commit vào git và sẽ có người checkout trên Windows, nên một file gom trên Linux mà
# vượt trần là quả bom hẹn giờ — nổ ở máy khác, lúc chỉ đang `git clone`.
WIN_MAX_PATH = 259


def over_long_paths(dests, limit: int = WIN_MAX_PATH):
    """Những đường dẫn đích vượt trần, kèm độ dài thật. Đo trên đường dẫn TUYỆT ĐỐI.

    Phải là tuyệt đối vì Windows tính trần trên đường dẫn đầy đủ; đo tương đối thì
    `results/...` luôn xanh trong khi bản thật dài hơn cả trăm ký tự.
    """
    out = []
    for d in dests:
        n = len(str(pathlib.Path(d).resolve()))
        if n > limit:
            out.append((d, n))
    return out


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
                    help="ep ten experiment; mac dinh lay ten thu muc cha cua games.csv. "
                         "Shard E3b BAT BUOC dat --experiment exp_mixed: ten mac dinh "
                         "exp_baseline_seats-LLLMMM-<hash> day duong dan vuot tran 260 "
                         "ky tu cua Windows")
    ap.add_argument("--only-model", nargs="*", default=None,
                    help="chi gom nhung model_tag nay — loc theo tag SUY RA tu cau hinh "
                         "ghe, nen ban hon hop phai viet du ten mix__A__B__kN")
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

    # Ten thu muc server mang hau to noi bo (seat tag bam, probe) KHONG phai ten experiment
    # trong results/: E2 -> exp_evprobe, E3a -> exp_bestresponse_*, E8 -> exp_showpool_
    # bestresponse_*, exp_evprobe_p0. Quen --experiment thi cay results/ moc ra mot thu muc
    # `exp_*_seats-L00000-<hash>` ma khong loader nao doc.
    internal = sorted({g.parent.name for g, _ in shards
                       if "_seats-" in g.parent.name or "_probe-" in g.parent.name})
    if internal and not args.experiment:
        print(f"!! DUNG: thu muc server {internal} can --experiment <ten trong results/> "
              f"(xem plan/scripts/launch_e8.py gather_hint)", file=sys.stderr)
        return 1

    for games_p, turns_p in shards:
        experiment = args.experiment or games_p.parent.name
        games = list(csv.DictReader(games_p.open(encoding="utf-8")))
        if not games:
            continue
        # BO QUA RE cho --only-model. Tag that chi biet duoc sau khi dung xong dong wide,
        # nhung khi shard KHONG bat CRG_SEAT_MODELS thi ca 6 ghe deu la model `-m`, nen
        # cot `model` cua games.csv (chinh la tag server ghi ra) da du de loai tru. Chi bo
        # khi CHAC CHAN khong dong nao khop — nho vay --only-model khong con phai doc
        # turns.jsonl cua nhung shard vo can, tuc khong cham hon truoc.
        if args.only_model and not any(g.get("seat_models") for g in games):
            if not {g.get("model") for g in games} & set(args.only_model):
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
            # Ten thu muc/file suy tu CHINH cau hinh ghe cua van nay, khong lay ten thu
            # muc shard nua: `kaggle b t run -m <slug>` chi chon duoc mot model, nen ban
            # hon hop (E3b) bi server ghi vao thu muc cua model A va ca 4 cap co model A
            # se de len nhau. Suy sau khi co `row` la sach nhat — `game_to_wide_row` da
            # chuan hoa slug thanh tag trong cac o `agent{i}_llm`.
            model_tag = seat_model_tag([row[f"agent{i}_llm"]
                                        for i in range(1, N_PLAYERS + 1)])
            if args.only_model and model_tag not in args.only_model:
                continue
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

    # CONG DO DAI DUONG DAN — chay TRUOC moi thao tac ghi, ke ca truoc mkdir.
    # Ten `mix__<tagA>__<tagB>__k<k>` lap lai HAI lan (thu muc + ten file), nen cong voi
    # ten thu muc mac dinh cua shard E3b (`exp_baseline_seats-LLLMMM-<hash>`, 34 ky tu)
    # thi cap dai nhat (haiku + qwen) ra 261 ky tu > tran 260 cua Windows. Neu de no chay
    # tiep thi `mkdir` QUA DUOC (thu muc ngan hon file) roi buoc ghi moi hong — tuc hong
    # muon, sau khi da doc va dung xong toan bo du lieu, va mot phan file da nam tren dia.
    dests = {}
    for experiment, ptok, model_tag, lang in buckets:
        dests[(experiment, ptok, model_tag, lang)] = (
            out_root / experiment / ptok / model_tag / f"p{ptok}_{lang}_{model_tag}.csv")
    too_long = over_long_paths(dests.values())
    if too_long:
        err = sys.stderr
        print("", file=err)
        print(f"!! DUNG: {len(too_long)} duong dan dich vuot tran {WIN_MAX_PATH + 1} ky tu "
              f"cua Windows (chua ghi gi ca).", file=err)
        for d, n in sorted(too_long, key=lambda x: -x[1])[:5]:
            print(f"   {n} ky tu: {pathlib.Path(d).resolve()}", file=err)
        print("   CACH CHUA: ep ten experiment ngan lai —", file=err)
        print("     python plan/scripts/to_wide_csv.py --src ... --experiment exp_mixed", file=err)
        print("   (ten mac dinh cua shard E3b la exp_baseline_seats-LLLMMM-<hash>, 34 ky", file=err)
        print("    tu; ten `mix__A__B__kN` con lap lai hai lan nen khong con cho.)", file=err)
        print(f"   Hoac chon --out nong hon: hien tai la {out_root.resolve()}", file=err)
        return 1

    # CHOT AN TOAN. Mot lan gom hep pham vi (vd chi mot model) van tro toi cung cay
    # `results/`, va ghi de la ghi de TOAN BO file. File moi it van hon file dang co gan
    # nhu chac chan la mat data am tham -> chan lai. Bat duoc dung ca nay 10-09-2026: gom
    # rieng qwen nhung --src quet trung ca haiku/luna trong cung thu muc account, suyt ghi
    # de file 10 van bang ban 8-9 van.
    shrink = []
    for cell, by_rep in sorted(buckets.items()):
        dest = dests[cell]
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
    for cell, by_rep in sorted(buckets.items()):
        rows = [by_rep[r][0] for r in sorted(by_rep)]
        dest = dests[cell]
        n_files += 1
        n_rows += len(rows)
        if args.dry_run:
            print(f"  [dry] {dest}  ({len(rows)} van)")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    print(f"\n{len(shards)} shard -> {n_rows} van trong {n_files} file"
          f"{' (dry-run, chua ghi)' if args.dry_run else f' duoi {out_root}/'}")
    print(f"Schema: {len(fields)} cot. Nho chay verify_wide.py sau khi ghi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
