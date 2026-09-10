"""E7 — sinh ĐƯỜNG THAM CHIẾU scripted cho mọi mức rủi ro (chạy offline, 0 lượt API).

Chạy các nhóm 6 agent kịch bản qua ĐÚNG engine (``crsd.engine``) và xuất:

  * ``games.csv``    — mỗi dòng một ván (dùng lại ``recorder.summarize_game`` + cột điều kiện)
  * ``summary.csv``  — mỗi dòng một ô (điều kiện × mức rủi ro): tổng nhóm, tỉ lệ đạt
                       target, payoff trung bình (thực nghiệm) và payoff KỲ VỌNG (giải tích)
  * ``manifest.json``— tham số đã chạy + module chính sách đã dùng
  * ``scripted_reference.png/.pdf`` — hình 6 panel cho paper

Điều kiện (xem ``crsd.analysis.scripted_reference``):
  - 5 nhóm thuần: always_0 / always_2 / always_4 / ev_maximiser / conditional_cooperator
  - quét thành phần hỗn hợp: k = 0..6 ghế ``ev_maximiser`` trộn vào ``conditional_cooperator``

Cách chạy::

    python -m crsd.runner.run_scripted_reference
    python -m crsd.runner.run_scripted_reference --reps 5 --risks 0,0.5,0.9
    python -m crsd.runner.run_scripted_reference --out results/scripted_reference --turns

KHÔNG gọi API, KHÔNG cần GPU. Chính sách tất định nên tổng nhóm giống hệt nhau giữa
các rep; số rep chỉ để ước lượng xổ số thảm hoạ (payoff thực nghiệm) — cột
``expected_mean_payoff`` là giá trị đúng theo giải tích, không có sai số Monte Carlo.

Chính sách LẤY TỪ ``crsd.models.scripted`` và đi qua ``crsd.models.routing`` y như
E3a sẽ làm với bàn 1 LLM + 5 kịch bản — không có cài đặt chính sách thứ hai ở đây.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from ..analysis.scripted_reference import (
    POLICY_MODULE,
    Condition,
    default_conditions,
    expected_payoffs,
    scripted_router,
)
from ..dataio.config_loader import load_json, validate_game
from ..dataio.recorder import summarize_game, write_turns_jsonl
from ..engine.agent import CrsdAgent
from ..engine.game import CrsdGame
from ..engine.state import GameConfig
from ..paths import CONFIGS_DIR, RESULTS_DIR
from .batch import run_games_batched
from .run_experiment import load_template

# Cơ chế game lấy từ config gốc; CHỈ ``riskProbability`` bị ghi đè theo lưới rủi ro.
# (Ba config gốc crsd_milinski_{low,medium,high}_risk giống hệt nhau ngoài mức rủi ro,
# nên ghi đè p trên một base duy nhất tái tạo đúng cả ba — kiểm bằng test.)
BASE_CONFIG = "crsd_milinski_high_risk"

# Mọi mức rủi ro đang có trong repo + hai đầu mút đối chứng (E-ctrl).
DEFAULT_RISKS = (0.0, 0.01, 0.05, 0.1, 0.5, 0.9, 1.0)

# Khoá join sang results/: tên config chuẩn ứng với từng mức rủi ro. Với agent
# scripted, prompt không ảnh hưởng quyết định nên các biến thể prompt (plain_computed)
# chỉ đóng vai trò NHÃN mức rủi ro, không đổi cơ chế.
CANONICAL_CONFIG_BY_RISK = {
    0.0: "crsd_milinski_0pct_risk_plain_computed",
    0.01: "crsd_milinski_1pct_risk_plain_computed",
    0.05: "crsd_milinski_5pct_risk_plain_computed",
    0.1: "crsd_milinski_low_risk",
    0.5: "crsd_milinski_medium_risk",
    0.9: "crsd_milinski_high_risk",
}

MODEL_LABEL = "scripted"          # cột `model` trong games.csv
DEFAULT_OUT = RESULTS_DIR / "scripted_reference"


# --------------------------------------------------------------------------
# Chạy
# --------------------------------------------------------------------------


def build_game(base: dict, condition: Condition, risk: float, rep: int,
               template: str, agents_cfg: dict, language: str = "en",
               base_seed: int = 0) -> CrsdGame:
    """Dựng MỘT ván scripted: cơ chế của ``base``, mức rủi ro ``risk``, ghế theo điều kiện."""
    gd = dict(base)
    gd["riskProbability"] = float(risk)
    cfg = GameConfig.from_dict(gd, language=language, model=MODEL_LABEL)
    names = agents_cfg["names"]
    personas = agents_cfg.get("personas", {}).get(language, [""] * len(names))
    agents = [
        CrsdAgent(
            name=names[i],
            persona_text=personas[i] if i < len(personas) else "",
            # disposition = chính sách của ghế -> turns.jsonl tự mô tả ghế nào chơi gì.
            disposition=condition.seat_policies[i],
        )
        for i in range(cfg.n_players)
    ]
    gid = f"scripted__{condition.name}__p{risk:g}__rep{rep}"
    return CrsdGame(
        cfg, template, agents, gid,
        seed=base_seed + rep,
        persona_set=condition.name,
        sampling_seeds_applied=False,   # backend scripted không dùng seed sinh văn bản
        rep=rep,
        seat_models=condition.seat_models,   # "scripted:<policy>" cho từng ghế
    )


def run_condition(base: dict, condition: Condition, risk: float, reps: int,
                  template: str, agents_cfg: dict, language: str = "en",
                  base_seed: int = 0):
    """Chạy ``reps`` ván của một ô (điều kiện × rủi ro). Trả ``(results, games)``.

    Mọi ván trong ô dùng CHUNG một router theo ghế (cùng thành phần nhóm) nên chạy
    lockstep được qua ``run_games_batched`` — đúng đường ống của run thật, chỉ khác
    là mọi ghế đều là chính sách kịch bản. Tắt retry parse vì chính sách kịch bản
    luôn trả đúng định dạng (retry chỉ dành cho output LLM hỏng).
    """
    if reps < 1:
        raise ValueError("reps phải >= 1")
    games = [
        build_game(base, condition, risk, rep, template, agents_cfg,
                   language=language, base_seed=base_seed)
        for rep in range(reps)
    ]
    results = run_games_batched(
        games, scripted_router(condition.seat_policies), max_parse_retries=0
    )
    return results, games


def summarize_cell(condition: Condition, risk: float, results) -> dict:
    """Gộp các ván của một ô thành một dòng của ``summary.csv``."""
    n = len(results)
    cfg = results[0].config if results else {}
    endowment = float(cfg.get("endowment", 40.0))
    n_players = int(cfg.get("n_players", 6))
    n_rounds = int(cfg.get("n_rounds", 10))

    totals = [float(r.group_total) for r in results]
    reached = [1 if r.target_reached else 0 for r in results]
    catastrophes = [1 if r.catastrophe else 0 for r in results]
    mean_payoffs = [sum(r.payoffs) / len(r.payoffs) for r in results]

    # Payoff KỲ VỌNG (giải tích) — không phụ thuộc kết quả xổ số nên không có nhiễu MC.
    exp_by_seat = [
        expected_payoffs(endowment, r.per_player_totals, r.target, r.risk_probability)
        for r in results
    ]
    exp_mean = [sum(e) / len(e) for e in exp_by_seat]

    # Tách theo loại chính sách của ghế (ai bóc lột ai trong nhóm hỗn hợp).
    per_policy_pay, per_policy_contrib = {}, {}
    for pol in dict.fromkeys(condition.seat_policies):
        seats = [i for i, p in enumerate(condition.seat_policies) if p == pol]
        per_policy_pay[pol] = statistics.fmean(
            [e[i] for e in exp_by_seat for i in seats]
        )
        per_policy_contrib[pol] = statistics.fmean(
            [float(r.per_player_totals[i]) for r in results for i in seats]
        )

    def _sd(xs):
        return statistics.stdev(xs) if len(xs) > 1 else 0.0

    return {
        "condition": condition.name,
        "family": condition.family,
        "k_ev": "" if condition.k_invader is None else condition.k_invader,
        "seat_policies": "|".join(condition.seat_policies),
        "seat_code": condition.seat_code,
        "risk_probability": risk,
        "game_config": CANONICAL_CONFIG_BY_RISK.get(risk, ""),
        "n_games": n,
        "n_players": n_players,
        "n_rounds": n_rounds,
        "target": float(results[0].target) if results else "",
        "group_total_mean": statistics.fmean(totals) if totals else "",
        "group_total_sd": _sd(totals),
        "mean_contribution_per_round": (
            statistics.fmean(totals) / (n_players * n_rounds) if totals else ""
        ),
        "target_reach_rate": statistics.fmean(reached) if reached else "",
        "catastrophe_rate": statistics.fmean(catastrophes) if catastrophes else "",
        "mean_payoff": statistics.fmean(mean_payoffs) if mean_payoffs else "",
        "mean_payoff_sd": _sd(mean_payoffs),
        "expected_mean_payoff": statistics.fmean(exp_mean) if exp_mean else "",
        "expected_payoff_ev": per_policy_pay.get("ev_maximiser", ""),
        "expected_payoff_cc": per_policy_pay.get("conditional_cooperator", ""),
        "contribution_ev": per_policy_contrib.get("ev_maximiser", ""),
        "contribution_cc": per_policy_contrib.get("conditional_cooperator", ""),
        "expected_payoff_by_policy": "|".join(
            f"{k}={v:.4f}" for k, v in per_policy_pay.items()
        ),
        "policy_module": POLICY_MODULE,
    }


def run_sweep(risks=DEFAULT_RISKS, reps: int = 20, conditions=None, base_config: str = BASE_CONFIG,
              language: str = "en", base_seed: int = 0,
              collect_turns: bool = False, verbose: bool = False):
    """Chạy toàn bộ lưới. Trả ``(summary_rows, game_rows, turns)``."""
    base = validate_game(load_json(CONFIGS_DIR / "game" / f"{base_config}.json"))
    template = load_template(base.get("promptTemplate", "crsd"), language)
    agents_cfg = load_json(CONFIGS_DIR / "agents" / f"{base.get('agents', 'personas_default')}.json")
    conditions = list(conditions) if conditions is not None else default_conditions(
        int(base.get("nPlayers", 6))
    )

    summary_rows, game_rows, turns = [], [], []
    for condition in conditions:
        for risk in risks:
            results, games = run_condition(
                base, condition, float(risk), reps, template, agents_cfg,
                language=language, base_seed=base_seed,
            )
            summary_rows.append(summarize_cell(condition, float(risk), results))
            for r in results:
                row = summarize_game(r)
                row["condition"] = condition.name
                row["family"] = condition.family
                row["k_ev"] = "" if condition.k_invader is None else condition.k_invader
                # summarize_game đã ghi cột seat_models ("scripted:<policy>" từng ghế);
                # persona_seats thì suy từ persona nên vô nghĩa với bàn kịch bản -> thay
                # bằng mã chính sách theo ghế, vd "EEECCC".
                row["persona_seats"] = condition.seat_code
                game_rows.append(row)
            if collect_turns:
                for g in games:
                    turns.extend(g.turns)
            if verbose:
                last = summary_rows[-1]
                print(f"[E7] {condition.name:24s} p={risk:<5g} "
                      f"total={last['group_total_mean']:7.1f} "
                      f"reach={last['target_reach_rate']:.2f} "
                      f"E[payoff]={last['expected_mean_payoff']:6.2f}")
    return summary_rows, game_rows, turns


# --------------------------------------------------------------------------
# Ghi kết quả
# --------------------------------------------------------------------------


def write_rows_csv(rows, path) -> None:
    """Ghi list[dict] ra CSV (stdlib — không bắt buộc có pandas)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def make_figure(summary_rows, path, plot_risks=(0.1, 0.5, 0.9)) -> bool:
    """Hình 6 panel. Trả False nếu không có matplotlib (không phải lỗi cứng)."""
    try:
        import matplotlib as mpl
        mpl.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    mpl.rcParams.update({
        "figure.dpi": 150, "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9.5,
        "axes.linewidth": 0.8, "axes.edgecolor": "#3a3a38",
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "legend.fontsize": 7.5, "legend.frameon": False,
        "lines.linewidth": 1.8, "lines.markersize": 5,
        "grid.color": "#e1e0d9", "grid.linewidth": 0.7,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    })
    ink = "#26251f"
    # Nhiều đường TRÙNG NHAU đúng theo kết quả (vd always_2 và conditional_cooperator
    # đều cho 120) -> mỗi điều kiện một (màu, nét, marker) riêng để không cái nào bị che.
    style = {
        "all_always_0": ("#b03a2e", "-", "o"),
        "all_always_2": ("#1f6f8b", "--", "s"),
        "all_always_4": ("#7d3c98", "-", "^"),
        "all_ev_maximiser": ("#c98b1b", "-", "D"),
        "all_conditional_cooperator": ("#2e7d32", ":", "v"),
    }
    label = {
        "all_always_0": "all always_0",
        "all_always_2": "all always_2",
        "all_always_4": "all always_4",
        "all_ev_maximiser": "all ev_maximiser",
        "all_conditional_cooperator": "all conditional_cooperator",
    }

    homo = [r for r in summary_rows if r["family"] == "homogeneous"]
    mix = [r for r in summary_rows if r["family"] == "mix_ev_in_cc"]
    risks = sorted({float(r["risk_probability"]) for r in summary_rows})
    ks = sorted({int(r["k_ev"]) for r in mix}) if mix else []
    shown = [p for p in plot_risks if p in risks] or risks
    target = float(homo[0]["target"]) if homo else 120.0

    fig, axes = plt.subplots(2, 3, figsize=(11.0, 6.2))

    def series(rows, cond, col):
        pts = sorted(
            ((float(r["risk_probability"]), float(r[col]))
             for r in rows if r["condition"] == cond),
            key=lambda t: t[0],
        )
        return [t[0] for t in pts], [t[1] for t in pts]

    panels_top = [
        ("group_total_mean", "Group total", f"(a) Group total (target = {target:g})"),
        ("target_reach_rate", "Target-reach rate", "(b) Target-reach rate"),
        ("expected_mean_payoff", "Expected payoff", "(c) Expected mean payoff"),
    ]
    conds = [c for c in style if any(r["condition"] == c for r in homo)]
    for ax, (col, ylab, title) in zip(axes[0], panels_top):
        for cond in conds:
            xs, ys = series(homo, cond, col)
            color, ls, marker = style[cond]
            ax.plot(xs, ys, marker=marker, ls=ls, color=color, label=label[cond])
        if col == "group_total_mean":
            ax.axhline(target, ls="--", lw=1.0, color=ink, alpha=0.6)
        if col == "target_reach_rate":
            ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel("risk probability p")
        ax.set_ylabel(ylab)
        ax.set_title(title, loc="left", color=ink)
        ax.grid(True, axis="y")
    # Chú giải đặt ở khoảng trống giữa đường 240 và đường 120 của panel (a).
    axes[0][0].legend(loc="upper left", bbox_to_anchor=(0.02, 0.93))

    cmap = ["#b03a2e", "#c98b1b", "#1f6f8b", "#2e7d32", "#7d3c98", "#5d4037", "#37474f"]
    dashes = ["-", "--", ":", "-.", (0, (3, 1, 1, 1)), (0, (5, 2)), (0, (1, 1))]
    risk_color = {p: cmap[i % len(cmap)] for i, p in enumerate(shown)}
    risk_ls = {p: dashes[i % len(dashes)] for i, p in enumerate(shown)}

    def mix_series(p, col):
        pts = sorted(
            ((int(r["k_ev"]), float(r[col]))
             for r in mix if float(r["risk_probability"]) == p and r[col] != ""),
            key=lambda t: t[0],
        )
        return [t[0] for t in pts], [t[1] for t in pts]

    panels_bottom = [
        ("group_total_mean", "Group total",
         "(d) Mixed group: total vs k ev_maximiser"),
        ("target_reach_rate", "Target-reach rate",
         "(e) Mixed group: target-reach vs k"),
    ]
    for ax, (col, ylab, title) in zip(axes[1], panels_bottom):
        for p in shown:
            xs, ys = mix_series(p, col)
            ax.plot(xs, ys, marker="o", ls=risk_ls[p], color=risk_color[p], label=f"p = {p:g}")
        if col == "group_total_mean":
            ax.axhline(target, ls="--", lw=1.0, color=ink, alpha=0.6)
        if col == "target_reach_rate":
            ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel("k = number of ev_maximiser seats")
        ax.set_ylabel(ylab)
        ax.set_title(title, loc="left", color=ink)
        ax.set_xticks(ks)
        ax.grid(True, axis="y")
    axes[1][0].legend(loc="upper right")

    ax = axes[1][2]
    for p in shown:
        xs, ys = mix_series(p, "expected_payoff_ev")
        if xs:
            ax.plot(xs, ys, ls=risk_ls[p], marker="D", color="#c98b1b",
                    label=f"ev_maximiser, p = {p:g}")
        xs, ys = mix_series(p, "expected_payoff_cc")
        if xs:
            ax.plot(xs, ys, ls=risk_ls[p], marker="v", color="#2e7d32",
                    label=f"cond. cooperator, p = {p:g}")
    ax.set_xlabel("k = number of ev_maximiser seats")
    ax.set_ylabel("Expected payoff")
    ax.set_title("(f) Who gains: payoff by seat type", loc="left", color=ink)
    ax.set_xticks(ks)
    ax.grid(True, axis="y")
    ax.legend(loc="best", ncol=1)

    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path.with_suffix(".png"))
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)
    return True


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="E7: đường tham chiếu scripted cho CRSD (offline, không gọi API)"
    )
    ap.add_argument("--risks", default=",".join(f"{p:g}" for p in DEFAULT_RISKS),
                    help="danh sách mức rủi ro, ngăn bằng dấu phẩy")
    ap.add_argument("--reps", type=int, default=20,
                    help="số ván mỗi ô (chính sách tất định; rep chỉ lấy mẫu xổ số)")
    ap.add_argument("--seed", type=int, default=0, help="seed gốc (seed ván = seed + rep)")
    ap.add_argument("--base-config", default=BASE_CONFIG,
                    help="config game lấy cơ chế (chỉ riskProbability bị ghi đè)")
    ap.add_argument("--language", default="en")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--turns", action="store_true",
                    help="ghi thêm turns.jsonl (nặng: có cả prompt của từng lượt)")
    ap.add_argument("--no-figure", action="store_true")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    risks = [float(x) for x in str(args.risks).split(",") if x.strip() != ""]
    out_dir = Path(args.out)

    summary_rows, game_rows, turns = run_sweep(
        risks=risks, reps=args.reps, base_config=args.base_config,
        language=args.language, base_seed=args.seed,
        collect_turns=args.turns, verbose=True,
    )

    write_rows_csv(summary_rows, out_dir / "summary.csv")
    write_rows_csv(game_rows, out_dir / "games.csv")
    if args.turns:
        write_turns_jsonl(turns, out_dir / "turns.jsonl")

    manifest = {
        "experiment": "E7_scripted_reference",
        "base_config": args.base_config,
        "risks": risks,
        "reps": args.reps,
        "seed": args.seed,
        "language": args.language,
        "policy_module": POLICY_MODULE,
        "n_conditions": len({r["condition"] for r in summary_rows}),
        "n_cells": len(summary_rows),
        "n_games": len(game_rows),
        "canonical_config_by_risk": {str(k): v for k, v in CANONICAL_CONFIG_BY_RISK.items()},
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if not args.no_figure:
        if make_figure(summary_rows, out_dir / "scripted_reference"):
            print(f"[E7] hình -> {out_dir / 'scripted_reference.png'}")
        else:
            print("[E7] bỏ qua hình (không có matplotlib)")

    print(f"[E7] {len(game_rows)} ván, {len(summary_rows)} ô, "
          f"chính sách={POLICY_MODULE} -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
