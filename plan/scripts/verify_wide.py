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
* **Cổng ĐỦ PANEL.** Cổng cân bằng ở trên chỉ so những model CÓ MẶT, nên nó mù đúng cái
  lỗi nó sinh ra để bắt: shard của một model chết sạch thì model đó biến mất khỏi cây, chỉ
  còn 4 model bằng nhau, và cổng im lặng cho qua. Nên phải khai báo panel kỳ vọng và bắt
  mỗi experiment có ĐỦ cả 5 (`--panel` để ghi đè khi experiment cố ý chỉ chạy một phần).
* **Cổng DANH TÍNH panel.** Một tag viết sai nhưng NHẤT QUÁN (thư mục + tên file + cả 6 ô
  `agent{i}_llm`) vẫn qua được mọi phép kiểm ở trên, vì chúng chỉ đối chiếu tên với nội
  dung chứ không hỏi "tên này có phải một trong 5 model không". Đó đúng là hình dạng của
  bẫy slug không chính tắc: ghế lạ ghi `grok-4.20-…` còn ghế `-m` ghi
  `xai-grok-4.20-…`, nhất quán ở mọi chỗ, và panel hoá 6 model. Nên mỗi `model_tag` xuất
  hiện — kể cả từng vế của tên `mix__` — phải thuộc panel kỳ vọng.
* **Cổng ngôn ngữ.** Chỉ `en`. Bắt trường hợp quên cờ `--langs` khi phóng shard.

## Cân bằng cho bàn HỖN HỢP (E3b) phải đếm theo GHẾ, không theo tên thư mục

Bản đầu đếm `per_model[experiment][<tên thư mục>]`. Với bàn đồng nhất thì tên thư mục
CHÍNH LÀ model nên đếm thế là đúng. Với E3b thì sai hẳn: một ván của cặp (A, B) nằm trong
thư mục `mix__A__B__k3`, nên mỗi cấu hình ghế hoá thành một "model" riêng và cổng cân bằng
đi so `mix__A__B__k1` với `mix__A__B__k2` — tức là so hai mức k của cùng một cặp, thay vì
so model A với model B. Nó xanh trong khi thiếu hẳn một model.

Nên khi experiment có ít nhất một thư mục `mix__`, cổng chuyển sang đếm **theo model có
mặt ở ghế**, và đếm hai kiểu vì chúng bắt hai loại lỗi khác nhau:

* **đếm-ván** — model được tính là có mặt nếu nó giữ ≥ 1 ghế. Thiết kế round-robin
  C(5,2)=10 cặp × k=1..5 × 3 risk × 10 rep cho **600 ván có mặt** cho mỗi model. Phép đếm
  này bắt lỗi "thiếu hẳn một cặp".
* **đếm-ghế-ván** — cộng dồn số ghế model đó giữ. Thiết kế cho **1800 ghế-ván/model** (đồ
  thị đầy đủ K5: với mỗi cặp, tổng k qua k=1..5 bằng 15, và tổng 6−k cũng bằng 15, nên hai
  vai đối xứng). Phép đếm này bắt lỗi "thiếu một mức k" — thiếu k=1 làm lệch ghế-ván mà có
  thể KHÔNG làm lệch đếm-ván, vì cặp đó vẫn còn các mức k khác.

Dùng:
    python plan/scripts/verify_wide.py
    python plan/scripts/verify_wide.py --wide results --expect-reps 10
    python plan/scripts/verify_wide.py --panel any      # tat hai cong panel
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

# Chạy được bằng `python plan/scripts/verify_wide.py` từ bất kỳ CWD nào: gắn gốc repo vào
# sys.path thay vì trông chờ CWD tình cờ đúng.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# Hợp đồng đặt tên nằm ở MỘT chỗ duy nhất — `crsd/dataio/wide_csv.py`. `to_wide_csv.py`
# dùng nó để ĐẶT tên thư mục, file này dùng đúng nó để KIỂM lại tên: chép lại quy tắc ở
# đây sẽ đẻ ra hai nguồn sự thật, và cổng kiểm sẽ hết bắt được lệch giữa hai bên. Panel kỳ
# vọng cũng vậy — `PANEL_TAGS` là cùng cái bảng mà tầng đọc dùng để chuẩn hoá slug, nên
# "tag chính tắc" và "tag được phép xuất hiện" không thể trôi ra khỏi nhau.
from crsd.dataio.wide_csv import PANEL_TAGS, seat_model_tag  # noqa: E402

MIX_PREFIX = "mix__"
# `--panel` nhận một trong những từ này để TẮT hai cổng panel. Có ý để lằng nhằng một
# chút: tắt cổng là quyết định phải gõ ra chứ không phải một cờ trống dễ lỡ tay.
PANEL_OFF = {"any", "none", "off"}


def tag_components(model_tag: str) -> list:
    """`<model_tag>` -> danh sách model mà nó nói là có mặt.

    Bàn đồng nhất -> chính nó. Bàn hỗn hợp `mix__<A>__<B>__k<N>` -> [A, B]. Tách bằng
    `"__"` chứ không bằng `"-"`: tag thật đầy dấu gạch ngang ("xai-grok-4.20-0309-…") nên
    cắt theo `"-"` sẽ băm tag ra thành mảnh vụn rồi báo hàng loạt lỗi giả.
    """
    if not model_tag.startswith(MIX_PREFIX):
        return [model_tag]
    body = model_tag[len(MIX_PREFIX):]
    head, sep, k = body.rpartition("__")
    if not sep or not k.startswith("k"):
        return [model_tag]                       # không đúng dạng -> để cổng khác báo
    return head.split("__")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wide", default="results", help="goc cay ket qua")
    ap.add_argument("--expect-reps", type=int, default=None,
                    help="neu dat, moi o (experiment, thu muc model, risk) phai co dung "
                         "ngan nay van — voi ban hon hop thu muc la (cap, k)")
    ap.add_argument("--panel", default=None,
                    help="panel ky vong, cac model_tag ngan cach bang dau phay. Mac dinh "
                         "la panel 5 model: moi experiment phai co DU ca 5, va moi tag "
                         "xuat hien phai thuoc panel. Dat 'any' de tat hai cong nay — "
                         "chi dung cho experiment CO Y chay mot phan panel")
    args = ap.parse_args()

    if args.panel is None:
        panel = set(PANEL_TAGS)
    elif args.panel.strip().lower() in PANEL_OFF:
        panel = None
    else:
        panel = {t.strip() for t in args.panel.split(",") if t.strip()}
        if not panel:
            print("--panel rong: dat 'any' neu that su muon tat cong panel", file=sys.stderr)
            return 1

    root = pathlib.Path(args.wide)
    # CHI file dung o do sau <experiment>/<p>/<model_tag>/x.csv moi la CSV van. File
    # phu o GOC results/ (vi du exp_evprobe_probes.csv - cau tra loi probe cua E2, la
    # phep do rieng chu khong phai van choi) khong duoc coi la van: doc no vao day se
    # bao "thu muc muc risk '' khong phai so", tuc la cong bao dong sai cho.
    files = sorted(p for p in root.rglob("*.csv")
                   if len(p.relative_to(root).parts) == 4)
    if not files:
        print(f"KHONG tim thay file .csv nao duoi {root}", file=sys.stderr)
        return 1

    errs = []
    n_rows = 0
    per_model = collections.defaultdict(collections.Counter)   # exp -> thu muc -> so van
    cells = collections.Counter()                              # (exp, thu muc, risk) -> so van
    seen = set()                                               # trung lap (exp, thu muc, risk, rep)
    # Hai phep dem theo GHE, dung cho experiment hon hop (xem docstring dau file).
    present = collections.defaultdict(collections.Counter)     # exp -> model -> so van CO MAT
    seat_games = collections.defaultdict(collections.Counter)  # exp -> model -> so GHE-VAN
    mixed_exps = set()                                         # exp co it nhat mot thu muc mix__

    for f in files:
        model_tag = f.parent.name
        risk_dir = f.parent.parent.name
        experiment = f.parent.parent.parent.name   # results/<exp>/<p>/<model>/x.csv
        if model_tag.startswith("mix__"):
            mixed_exps.add(experiment)

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
            # Ten thu muc phai la ten SUY RA TU 6 GHE, khong chi tu ghe 1. Ban cu chi so
            # `agent1_llm` roi bo qua han khi ten chua "mix__" — nghia la ca lop bo hon
            # hop khong duoc kiem ten, va mot file `mix__A__B__k3` chua toan van k=2 se
            # loi qua. `seat_model_tag` kiem duoc ca hai lop bang cung mot hop dong.
            seat_llms = [row.get(f"agent{k}_llm", "") for k in range(1, N_PLAYERS + 1)]
            try:
                derived = seat_model_tag(seat_llms)
            except Exception as e:                                   # noqa: BLE001
                errs.append(f"{where}: khong dat duoc ten tu 6 ghe ({e})")
                derived = None
            if derived is not None and derived != model_tag:
                errs.append(f"{where}: ten suy tu 6 ghe = {derived!r} != model_tag thu muc {model_tag!r}")

            key = (experiment, model_tag, risk_dir, row["rep"])
            if key in seen:
                errs.append(f"{where}: TRUNG (experiment, model, risk, rep) = {key}")
            seen.add(key)
            per_model[experiment][model_tag] += 1
            cells[(experiment, model_tag, risk_dir)] += 1

            # Dem theo ghe. Lam cho MOI experiment (re) nhung chi dung de gac o nhanh hon
            # hop — bo bang dong nhat de dong in ra khong doi.
            held = collections.Counter(s for s in seat_llms
                                       if s and not str(s).startswith("scripted:"))
            for m, n_seats in held.items():
                present[experiment][m] += 1
                seat_games[experiment][m] += n_seats

    # Cong can bang: trong moi experiment, moi model phai co DUNG cung so van.
    for exp, counts in sorted(per_model.items()):
        if exp in mixed_exps:
            # Ban hon hop: ten thu muc la mot CAU HINH GHE (mix__A__B__k3), khong phai mot
            # model, nen so sanh giua cac thu muc la so nham. Doi sang dem theo model co
            # mat o ghe, va gac ca hai phep dem (xem docstring dau file: dem-van bat
            # "thieu ca mot cap", dem-ghe-van bat "thieu mot muc k").
            pres, sgames = present[exp], seat_games[exp]
            u_pres, u_seat = set(pres.values()), set(sgames.values())
            bad = False
            if len(u_pres) > 1:
                errs.append(f"CONG CAN BANG [{exp}] HON HOP: so VAN CO MAT lech giua cac "
                            f"model -> {dict(sorted(pres.items()))}")
                bad = True
            if len(u_seat) > 1:
                errs.append(f"CONG CAN BANG [{exp}] HON HOP: so GHE-VAN lech giua cac "
                            f"model -> {dict(sorted(sgames.items()))}")
                bad = True
            head = "can bang OK" if not bad else "LECH"
            print(f"  {exp:<16} hon hop: {len(pres)} model, {len(counts)} cau hinh ghe — {head}")
            for m in sorted(pres):
                print(f"      {m:<44} {pres[m]:>6} van co mat  {sgames[m]:>6} ghe-van")
        else:
            uniq = set(counts.values())
            if len(uniq) > 1:
                errs.append(f"CONG CAN BANG [{exp}]: so van lech giua cac model -> {dict(counts)}")
            else:
                print(f"  {exp:<16} {len(counts)} model x {uniq.pop()} van — can bang OK")

    # Cong DU PANEL + cong DANH TINH PANEL.
    #
    # Cong can bang o tren chi so nhung model CO MAT voi nhau, nen no mu dung cai truong
    # hop no sinh ra de bat: shard cua mot model chet SACH thi model do bien mat khoi
    # experiment, bon model con lai van bang nhau, va cong in ra "4 model x 30 van — can
    # bang OK" roi exit 0. Da kiem bang cach gai loi 11-09-2026: xoa han gpt-5.6-luna khoi
    # exp_nohint van qua duoc cong.
    #
    # Cong danh tinh bat mot loai loi khac ma moi phep kiem NOI BO deu chiu thua: mot tag
    # viet sai nhung NHAT QUAN o moi cho (thu muc + ten file + ca 6 o agent{i}_llm) thi
    # khong co gi mau thuan voi gi ca. Day dung la bay slug ghe la cua E3b — proxy khong
    # chuan hoa slug ghe la, nen `grok-4.20-...` xuat hien y het mot model that va panel
    # hoa 6 model. Chi co mot bang panel BEN NGOAI moi noi duoc "cai tag nay khong ton tai".
    if panel is not None:
        for exp in sorted(per_model):
            # Ban hon hop: ten thu muc la mot CAU HINH GHE (mix__A__B__k3), khong phai ten
            # model, nen danh tinh phai lay tu cac o agent{i}_llm. Ban dong nhat thi hai
            # nguon trung nhau; lay ca hai cho chac.
            identities = set(present[exp])
            if exp not in mixed_exps:
                identities |= set(per_model[exp])
            missing = panel - identities
            if missing:
                errs.append(f"CONG DU PANEL [{exp}]: thieu han {len(missing)}/{len(panel)} "
                            f"model -> {sorted(missing)}. Nhieu kha nang shard cua chung "
                            f"chet ma chua chay lai. Dat --panel any neu experiment nay CO Y "
                            f"chi chay mot phan panel.")
            unknown = identities - panel
            if unknown:
                errs.append(f"CONG DANH TINH PANEL [{exp}]: {len(unknown)} tag khong thuoc "
                            f"panel -> {sorted(unknown)}. Tag viet sai nhung nhat quan thi "
                            f"moi phep kiem noi bo deu cho qua; chi bang panel bat duoc.")

    if args.expect_reps:
        # Don vi o day la o (thu muc, risk), khong phai (model, risk) — co y. Voi ban dong
        # nhat thu muc = model nen doc nhu cu; voi ban hon hop thu muc = (cap, k) va thiet
        # ke cung cho dung `--expect-reps` rep moi (cap, k, risk), nen khong bao dong gia.
        wrong = {k: v for k, v in cells.items() if v != args.expect_reps}
        if wrong:
            errs.append(f"So van moi (exp, thu muc model, risk) != {args.expect_reps}: "
                        f"{dict(list(wrong.items())[:6])}")

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
