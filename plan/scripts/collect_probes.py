"""Gom cau tra loi probe cua E2 vao results/ — neu khong lam, KET QUA E2 BIEN MAT.

Wide CSV 82 cot mo ta VAN CHOI. Cau tra loi probe khong phai van choi: no la phep do
rieng (model co hieu luat khong, co so sanh duoc ky vong khong), va no chi nam trong
`probes.jsonl` o thu muc shard tai ve — ma thu muc do da gitignore. Nghia la sau khi
don dep may, `results/` van xanh cong nhung E2 khong con ket qua nao.

Ghi ra HAI file o goc `results/` (goc, chu khong phai duoi `results/<experiment>/`:
luat duong dan §9.1 chi cho phep thu muc TEN LA SO duoi do, mot file lac vao se lam
`float(p.name)` nem ValueError va giet ca lan doc):

  exp_evprobe_probes.jsonl   toan bo ban ghi, khong mat mat gi
  exp_evprobe_probes.csv     bang phang de doc bang pandas/R ngay

Chong trung: khoa (game_id, round, player_index, question_id, params). Mot o chay lai
sinh game_id khac nhau chi khi seat/template khac; trong cung mot wave thi trung khoa
nghia la cung mot cau hoi tai ve hai lan qua hai shard -> giu ban dau tien.

    python plan/scripts/collect_probes.py            # xem truoc
    python plan/scripts/collect_probes.py --write
"""
import argparse
import csv
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "results"
SRC_GLOB = "D:/tmp/crgdl/*/crg-e2-evprobe/**/probes.jsonl"
OUT_JSONL = RESULTS / "exp_evprobe_probes.jsonl"
OUT_CSV = RESULTS / "exp_evprobe_probes.csv"

# Cot cua ban phang. `params` va cac truong list duoc JSON-hoa de mot o luon la mot
# chuoi — cung quy uoc voi cot list cua wide CSV (§9.4).
COLS = ["game_id", "model", "risk_probability", "language", "round", "player",
        "player_index", "category", "question_id", "params", "question_text",
        "raw_response", "parsed_answer", "ground_truth", "correct", "parse_failed",
        "answer_kind", "answerable_from_prompt"]


def load():
    rows, seen = [], set()
    for f in sorted(glob.glob(SRC_GLOB, recursive=True)):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                key = (r["game_id"], r["round"], r["player_index"], r["question_id"],
                       json.dumps(r.get("params"), sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                rows.append(r)
    rows.sort(key=lambda r: (r["model"], r["risk_probability"], r["game_id"],
                             r["round"], r["player_index"], r["question_id"]))
    return rows


def flat(r):
    out = {}
    for c in COLS:
        v = r.get(c)
        out[c] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rows = load()
    if not rows:
        print(f"Khong tim thay probes.jsonl nao khop {SRC_GLOB}")
        return 1

    by_model = defaultdict(lambda: [0, 0])
    by_cat = defaultdict(lambda: [0, 0])
    games, failed = set(), 0
    for r in rows:
        games.add(r["game_id"])
        failed += int(r.get("parse_failed", False))
        for d, k in ((by_model, r["model"]), (by_cat, r["category"])):
            d[k][0] += 1
            d[k][1] += int(r["correct"])

    print(f"{len(rows)} ban ghi · {len(games)} van · parse_failed={failed}")
    print("\ndo chinh xac theo nhom cau hoi:")
    for k, (n, ok) in sorted(by_cat.items()):
        print(f"  {k:<10} {ok:>5}/{n:<6} = {ok/n:6.1%}")
    print("\ndo chinh xac theo model:")
    for k, (n, ok) in sorted(by_model.items()):
        print(f"  {k:<42} {ok:>5}/{n:<6} = {ok/n:6.1%}")

    # Can bang: E2 phai co dung cung so cau hoi cho ca 5 model (luat §7).
    counts = sorted({n for n, _ in by_model.values()})
    print(f"\ncan bang: {counts} " + ("OK" if len(counts) == 1 else "!! LECH"))
    if failed:
        print(f"!! {failed} cau parse that bai — kiem truoc khi dua vao paper")

    if not args.write:
        print("\n(xem truoc — them --write de ghi)")
        return 0

    OUT_JSONL.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                for r in rows), encoding="utf-8")
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(flat(r))
    print(f"\nDa ghi {OUT_JSONL.name} ({OUT_JSONL.stat().st_size/1024:.0f} KB)"
          f" va {OUT_CSV.name} ({OUT_CSV.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
