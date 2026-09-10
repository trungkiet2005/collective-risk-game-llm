"""Kiểm mọi bất biến của cây `results/`. Exit 1 nếu có bất kỳ vi phạm nào.

Đặc tả: `plan/aamas2027-plan.md` §9.5. Chạy sau MỖI lần gom shard, trước khi đưa số vào
paper.

Ba cổng quan trọng nhất, vì chúng bắt loại lỗi ÂM THẦM (dữ liệu sai mà mọi chỉ số tổng hợp
vẫn xanh):

* **Cổng cắt-output.** `agent{i}_parse_failures` đếm cả lượt thiếu marker `CONTRIBUTION:`
  chứ không chỉ cờ `parse_failed`. Khi output bị cắt trước marker, parser quét chữ số trong
  đoạn suy luận rồi bịa ra một quyết định, và vẫn báo `parse_failed=False`. Chỉ số trung
  bình `usage_output_tokens / n_decisions` KHÔNG bắt được: `qwen3-235b` trung bình 8/512
  token (1,6% — xanh rực) trong khi 39,5% số ván của nó đã hỏng.
* **Cổng cân bằng.** Trong mỗi experiment, mọi model phải có ĐÚNG cùng số ván. Lệch nghĩa
  là có shard của model đắt chết mà chưa chạy lại — tức chênh lệch ngân sách đã lặng lẽ
  biến thành chênh lệch kết quả.
* **Cổng ngôn ngữ.** Chỉ `en`. Bắt trường hợp quên cờ `--langs` khi phóng shard.

Dùng:
    python plan/scripts/verify_wide.py
    python plan/scripts/verify_wide.py --wide results --expect-reps 10
"""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import pathlib
import sys

N_PLAYERS = 6
LANGS_ALLOWED = {"en"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wide", default="results", help="goc cay ket qua")
    ap.add_argument("--expect-reps", type=int, default=None,
                    help="neu dat, moi (experiment, model, risk) phai co dung ngan nay van")
    args = ap.parse_args()

    root = pathlib.Path(args.wide)
    files = sorted(root.rglob("*.csv"))
    if not files:
        print(f"KHONG tim thay file .csv nao duoi {root}", file=sys.stderr)
        return 1

    errs = []
    n_rows = 0
    per_model = collections.defaultdict(collections.Counter)   # exp -> model -> so van
    cells = collections.Counter()                              # (exp, model, risk) -> so van
    seen = set()                                               # trung lap (exp, model, risk, rep)

    for f in files:
        model_tag = f.parent.name
        risk_dir = f.parent.parent.name
        experiment = f.parent.parent.parent.name   # results/<exp>/<p>/<model>/x.csv

        # Thu muc muc risk PHAI parse duoc thanh so: loader sap xep bang float(p.name),
        # mot thu muc la ten chu se lam vo ca ingest chu khong bi bo qua.
        try:
            float(risk_dir)
        except ValueError:
            errs.append(f"{f}: thu muc muc risk '{risk_dir}' khong phai so")
            continue

        for i, row in enumerate(csv.DictReader(f.open(encoding="utf-8")), start=2):
            n_rows += 1
            where = f"{f}:{i}"

            def L(col):
                return ast.literal_eval(row[col])

            try:
                played = int(row["played_rounds"])
                group = L("group_contributions")
                pot = L("pot_cumulative")
                cat = int(row["catastrophe"])
                reached = int(row["target_reached"])
                target = float(row["target"])
                total = float(row["group_total"])
            except Exception as e:                                   # noqa: BLE001
                errs.append(f"{where}: khong doc duoc cot co ban ({e})")
                continue

            if row["language"] not in LANGS_ALLOWED:
                errs.append(f"{where}: CONG NGON NGU — language={row['language']!r}, chi cho phep {LANGS_ALLOWED}")
            if f"{float(row['risk_probability']):.1f}" != f"{float(risk_dir):.1f}":
                errs.append(f"{where}: risk trong file ({row['risk_probability']}) != thu muc ({risk_dir})")
            if len(group) != played or len(pot) != played:
                errs.append(f"{where}: do dai list nhom != played_rounds ({played})")
                continue

            # pot phai la cong don cua group
            acc, run = 0.0, []
            for x in group:
                acc += x
                run.append(acc)
            if [round(x, 6) for x in run] != [round(x, 6) for x in pot]:
                errs.append(f"{where}: pot_cumulative != cumsum(group_contributions)")
            if round(pot[-1], 6) != round(total, 6):
                errs.append(f"{where}: group_total ({total}) != pot_cumulative[-1] ({pot[-1]})")
            if reached != int(total >= target):
                errs.append(f"{where}: target_reached={reached} nhung group_total={total}, target={target}")
            if reached and cat:
                errs.append(f"{where}: catastrophe=1 trong khi target_reached=1 — xo so chi dien ra khi truot")

            # Khoi tung agent
            per_round = [0.0] * played
            fails_total = 0
            for k in range(1, N_PLAYERS + 1):
                try:
                    strat = L(f"agent{k}_strategies")
                    score = L(f"agent{k}_scores")
                except Exception as e:                               # noqa: BLE001
                    errs.append(f"{where}: agent{k} list hong ({e})")
                    continue
                if len(strat) != played or len(score) != played:
                    errs.append(f"{where}: agent{k} list dai {len(strat)}/{len(score)}, cho {played}")
                    continue
                if any(score[j] > score[j - 1] + 1e-9 for j in range(1, played)):
                    errs.append(f"{where}: agent{k}_scores tang len — tai khoan rieng phai khong tang")
                exp_pay = 0.0 if cat else score[-1]
                if round(float(row[f"agent{k}_payoff"]), 6) != round(exp_pay, 6):
                    errs.append(f"{where}: agent{k}_payoff={row[f'agent{k}_payoff']}, cho {exp_pay} (catastrophe={cat})")
                fails = int(row[f"agent{k}_parse_failures"])
                fails_total += fails
                if fails:
                    errs.append(f"{where}: CONG CAT-OUTPUT — agent{k} co {fails} luot hong/bi cat")
                for j, x in enumerate(strat):
                    per_round[j] += x

            if [round(x, 6) for x in per_round] != [round(x, 6) for x in group]:
                errs.append(f"{where}: tong dong gop 6 ghe tung vong != group_contributions")
            if int(row["n_parse_failures"]) != fails_total:
                errs.append(f"{where}: n_parse_failures={row['n_parse_failures']}, cong tay ra {fails_total}")
            if row["agent1_llm"] != model_tag and "mix__" not in model_tag:
                errs.append(f"{where}: agent1_llm={row['agent1_llm']!r} != model_tag thu muc {model_tag!r}")

            key = (experiment, model_tag, risk_dir, row["rep"])
            if key in seen:
                errs.append(f"{where}: TRUNG (experiment, model, risk, rep) = {key}")
            seen.add(key)
            per_model[experiment][model_tag] += 1
            cells[(experiment, model_tag, risk_dir)] += 1

    # Cong can bang: trong moi experiment, moi model phai co DUNG cung so van.
    for exp, counts in sorted(per_model.items()):
        uniq = set(counts.values())
        if len(uniq) > 1:
            errs.append(f"CONG CAN BANG [{exp}]: so van lech giua cac model -> {dict(counts)}")
        else:
            print(f"  {exp:<16} {len(counts)} model x {uniq.pop()} van — can bang OK")

    if args.expect_reps:
        wrong = {k: v for k, v in cells.items() if v != args.expect_reps}
        if wrong:
            errs.append(f"So van moi (exp, model, risk) != {args.expect_reps}: {dict(list(wrong.items())[:6])}")

    print(f"\nDa kiem {n_rows} van trong {len(files)} file.")
    if errs:
        print(f"\n{len(errs)} VI PHAM:", file=sys.stderr)
        for e in errs[:40]:
            print(f"  - {e}", file=sys.stderr)
        if len(errs) > 40:
            print(f"  ... va {len(errs) - 40} loi nua", file=sys.stderr)
        return 1
    print("Moi bat bien OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
