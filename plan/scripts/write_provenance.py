"""Dung lai results/PROVENANCE.json tu chinh cay results/ dang co.

`to_wide_csv.py` ghi CSV nhung KHONG dung provenance, nen sau moi lan gom phai chay
script nay -- neu khong, `results/` co du lieu ma khong co ban ghi "van nao tu dau ra",
tuc la mat dung cai ma DATA_CARD.md hua co.

Ban dau PROVENANCE.json chi mo ta MOT experiment (exp_baseline nhap tu Legacy_Results).
Tu 11-09-2026 no giu NHIEU experiment duoi khoa "experiments"; phan exp_baseline cu duoc
BE NGUYEN vao do, khong viet lai, vi no la ban ghi duy nhat noi 440/550 van baseline
den tu dau.

    python plan/scripts/write_provenance.py            # xem truoc
    python plan/scripts/write_provenance.py --write
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "results"
PROV = RESULTS / "PROVENANCE.json"

# Experiment sinh trong vong chay nay -> mo ta cach no duoc tao ra.
RUN_NOTES = {
    "exp_baseline": {
        "source": ("440 van nhap tu Legacy_Results (4 model) + 110 van qwen3-235b chay "
                   "lai server-side 10-09-2026 bang task `collective-risk-baseline-srv`"),
        "produced": "toi 10-09-2026 (nhap) · 10-09-2026 (qwen)",
        "config": "template baseline · CRG_LANGS=en · CRG_MAX_OUT=3000 (qwen)",
        "note": ("Ban ghi NHAP legacy giu nguyen o khoa `legacy_import` ben duoi -- do la "
                 "ban ghi duy nhat noi 440 van kia den tu dau. Khoa `models` la so DEM "
                 "THAT tren dia hom nay, nen no gom ca 110 van qwen ma ban ghi cu thieu. "
                 "qwen phai chay lai vi ban dau bi loi cat output (xem CLAUDE.md)."),
    },
    **{f"exp_bestresponse_{k}": {
        "source": f"Kaggle Benchmarks server-side, task `crg-e3a-{k}`",
        "produced": "2026-09-11",
        "config": (f"CRG_SEAT_MODELS=self + 5 x scripted:{pol} · "
                   "CRG_RISKS=0.1,0.3,0.5,0.7,0.9 · CRG_LANGS=en · CRG_MAX_OUT=3000"),
        "note": ("E3a §7.3: 1 ghe LLM (P1) giua 5 ghe scripted tat dinh. Chi P1 goi "
                 "proxy -> 10 lenh goi/van thay vi 60. Doi thu biet truoc chinh xac nen "
                 "best response tinh duoc tung o, va `agent1_*` la ghe LLM con "
                 "`agent2..6_llm` ghi thang ten chinh sach (`scripted:<policy>`). Thu muc "
                 "tren server mang seat tag bam (vd `exp_baseline_seats-L44444-...`); ten "
                 "trong results/ dat bang --experiment."),
    } for k, pol in (("defect", "always_0"), ("coop", "always_2"),
                     ("carry", "always_4"), ("cond", "conditional_cooperator"))},
    "exp_evprobe": {
        "source": "Kaggle Benchmarks server-side, task `crg-e2-evprobe`",
        "produced": "2026-09-10/11",
        "config": ("CRG_PROBE=rules,value · CRG_PROBE_ROUNDS=1,5,10 · CRG_PROBE_SEATS=0 · "
                   "CRG_LANGS=en · CRG_MAX_OUT=3000 · CRG_CONCURRENCY=4"),
        "probe_file": "exp_evprobe_probes.jsonl (+ .csv), o GOC results/",
        "note": ("E2: van choi y het dieu kien baseline -- cau hoi probe la loi goi RIENG, "
                 "khong chen vao lich su -- nen chenh lech so voi exp_baseline la nhieu lay "
                 "mau chu khong phai hieu ung cua probe. KET QUA CUA E2 KHONG NAM TRONG "
                 "wide CSV: 4.500 cau tra loi nam o exp_evprobe_probes.jsonl. Thu muc "
                 "output tren server la `exp_baseline_probe-rules-value` (hau to probe "
                 "them 10-09-2026 de van E2 khong roi vao thu muc baseline); ten "
                 "experiment trong results/ la exp_evprobe, dat bang --experiment."),
    },
    "exp_neutral": {
        "source": "Kaggle Benchmarks server-side, task `crg-e6-neutral` (launch_e6.py --arms neutral)",
        "produced": "2026-09-17",
        "config": "CRG_TEMPLATE=neutral · CRG_RISKS=0,0.1,0.9 · CRG_LANGS=en · CRG_MAX_OUT=3000 · "
                  "CRG_CONCURRENCY=4",
        "note": ("Kiem soat demand effect theo review AAMAS: template baseline, thay dung cac "
                 "cum co chuan muc hoac goi ten game ('collective-risk social dilemma', "
                 "'climate account', 'must reach', 'disaster') va BAT khoi {framing} ('the only "
                 "thing that matters to you is your own final cash payoff'). Giu nguyen mo neo "
                 "equal-split (do la bien cua E1). Cot framing=1 trong moi dong. p=0 la o quyet "
                 "dinh: o do dong gop bi troi bat ke niem tin."),
    },
    "exp_wording": {
        "source": "Kaggle Benchmarks server-side, task `crg-e6-wording` (drive_neutral.py --arm wording)",
        "produced": "2026-09-17",
        "config": "CRG_TEMPLATE=wording · CRG_RISKS=0,0.1,0.9 · CRG_LANGS=en · CRG_MAX_OUT=3000 · "
                  "CRG_EXPECT_MODEL=<slug> · Haiku chia 5 shard 2 rep",
        "note": ("Tach doi exp_neutral: DUNG template neutral (bo 'collective-risk social dilemma', "
                 "'climate account', 'must reach', 'disaster') nhung KHONG bat khoi {framing}, nen "
                 "muc tieu 'chi tien cua ban' khong duoc neu. baseline -> wording = hieu ung cua tu "
                 "ngu; wording -> neutral = hieu ung cua cau muc tieu. framing=0 trong moi dong. "
                 "Moi shard mot user Kaggle rieng (xem ALIASES trong launch_shard.py)."),
    },
    "exp_nohint": {
        "source": "Kaggle Benchmarks server-side, task `crg-e1-nohint`",
        "produced": "2026-09-10/11",
        "config": "CRG_TEMPLATE=nohint · CRG_LANGS=en · CRG_MAX_OUT=3000 · CRG_CONCURRENCY=4",
        "note": ("E1: cung template baseline nhung xoa dung hai doan mo neo equal-split "
                 "(xem crsd/prompts/crsd_nohint_en.txt). Chay lam nhieu dot vi quota "
                 "moi account can giua chung; MOI O (risk, rep) chi chay MOT LAN -- "
                 "`fill_wave_e12.py` doc data da co roi chi chay o con thieu, nen khong "
                 "o nao bi tron tu hai run khac nhau."),
    },
}


def scan():
    """experiment -> model_tag -> {risk_levels, reps, n_games}."""
    out = defaultdict(lambda: defaultdict(lambda: {"risk_levels": set(),
                                                   "reps": set(), "n_games": 0}))
    for csv_path in RESULTS.glob("*/*/*/*.csv"):
        exp = csv_path.parts[-4]
        with open(csv_path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                tag = row.get("agent1_llm") or "?"
                e = out[exp][tag]
                e["risk_levels"].add(csv_path.parts[-3])
                e["reps"].add(int(row["rep"]))
                e["n_games"] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    old = json.loads(PROV.read_text(encoding="utf-8")) if PROV.is_file() else {}
    # Ban cu la tai lieu MOT experiment -> be nguyen vao khoa "experiments".
    experiments = old.get("experiments")
    if experiments is None:
        experiments = {}
        if "models" in old and old.get("experiment"):
            experiments[old["experiment"]] = {k: v for k, v in old.items()
                                              if k not in ("experiments",)}

    found = scan()
    for exp, models in sorted(found.items()):
        if exp in experiments and exp not in RUN_NOTES:
            continue                      # ban ghi cu, khong dung toi
        entry = dict(RUN_NOTES.get(exp, {}))
        # Ban ghi cu cua experiment nay (neu co) duoc BE NGUYEN xuong mot khoa rieng,
        # khong ghi de: no ke lai lich su ma phep dem tren dia khong the dung lai.
        prior = experiments.get(exp)
        if prior and "models" in prior and prior.get("imported_from") is None:
            if any(m.get("imported_from") for m in prior["models"].values()):
                entry["legacy_import"] = prior
        entry["models"] = {
            tag: {"risk_levels": sorted(d["risk_levels"], key=float),
                  "reps": sorted(d["reps"]), "n_games": d["n_games"]}
            for tag, d in sorted(models.items())}
        entry["n_games_total"] = sum(d["n_games"] for d in models.values())
        experiments[exp] = entry

    doc = {
        "generated_by": "plan/scripts/write_provenance.py",
        "date": "2026-09-11",
        "note": ("Mot khoa moi experiment. exp_baseline giu nguyen ban ghi nhap tu "
                 "Legacy_Results; cac experiment khac sinh server-side trong vong chay "
                 "AAMAS 2027 (nhanh aamas2027-e0)."),
        "experiments": experiments,
    }
    blob = json.dumps(doc, indent=2, ensure_ascii=False)
    for exp, e in sorted(experiments.items()):
        n = e.get("n_games_total") or sum(m["n_games"] for m in e["models"].values())
        print(f"  {exp:<28} {len(e['models'])} model · {n} van")
    if args.write:
        PROV.write_text(blob + "\n", encoding="utf-8")
        print(f"\nDa ghi {PROV}")
    else:
        print("\n(xem truoc — them --write de ghi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
