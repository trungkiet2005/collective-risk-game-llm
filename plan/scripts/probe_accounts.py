"""Probe nhanh: account nào còn xin được Model Proxy key HÔM NAY.

Chạy `kaggle benchmarks auth` song song cho từng account, mỗi account một
`KAGGLE_CONFIG_DIR` riêng (nếu không credential đè lẫn nhau). Xong trong ~1 phút.

**Đây là PROBE, không sinh data.** Nó không gọi model, không tốn quota — chỉ xin key.

Vì sao phải probe lại trước mỗi đợt chạy lớn, đừng tin danh sách cũ:

* Sức khoẻ account TRÔI theo thời gian — mất 2/17 account trong 4 tuần, cùng một lỗi
  `403 missing phone/identity verification`. Login và xem model list vẫn được, nên nhìn
  bằng mắt sẽ tưởng còn dùng tốt.
* Quota là **cửa sổ trượt 24h, không reset lúc nửa đêm**. Account chạy shard $7 lúc 22:00
  thì tới 22:00 hôm sau mới dùng lại được.

⚠️ **Probe này chỉ trả lời CÒN/HẾT, không trả lời CÒN BAO NHIÊU.** Xin được key không có
nghĩa là đủ quota cho shard của bạn. Muốn biết còn bao nhiêu thì cộng
`usage_total_cost_usd` của các shard đã chạy trên account đó rồi lấy $10 trừ đi — rẻ và
chính xác hơn probe.

Dùng:
    python plan/scripts/probe_accounts.py
    python plan/scripts/probe_accounts.py --workers 8
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from launch_shard import ACCOUNTS  # noqa: E402  — dùng CHUNG bảng credential, đừng chép lại


def probe(name: str, timeout: int = 120):
    kind, path = ACCOUNTS[name]
    if not Path(path).is_file():
        return name, "THIEU_FILE", str(path)
    cfg = Path(tempfile.mkdtemp(prefix=f"kprobe_{name}_"))
    try:
        env = dict(os.environ)
        env["KAGGLE_CONFIG_DIR"] = str(cfg)
        env["PYTHONIOENCODING"] = "utf-8"
        for k in ("KAGGLE_API_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY"):
            env.pop(k, None)
        if kind == "token_txt":
            env["KAGGLE_API_TOKEN"] = Path(path).read_text(encoding="utf-8").strip()
        elif kind == "token_md":
            m = re.search(r"KGAT_[A-Za-z0-9_-]+", Path(path).read_text(encoding="utf-8"))
            if not m:
                return name, "KHONG_CO_TOKEN", str(path)
            env["KAGGLE_API_TOKEN"] = m.group(0)
        else:
            shutil.copyfile(path, cfg / "kaggle.json")

        env_file = cfg / "account.env"
        r = subprocess.run(
            ["kaggle", "benchmarks", "auth", "-y", "--env-file", str(env_file)],
            env=env, capture_output=True, text=True, timeout=timeout,
        )
        blob = (r.stdout or "") + (r.stderr or "")
        if env_file.is_file() and "MODEL_PROXY_API_KEY" in env_file.read_text(encoding="utf-8"):
            return name, "OK", ""
        if "phone" in blob.lower() or "verification" in blob.lower():
            return name, "403_VERIFY", "can verify SDT — bo qua account nay"
        return name, "LOI", blob.strip().replace("\n", " ")[:110]
    except subprocess.TimeoutExpired:
        return name, "TIMEOUT", f">{timeout}s"
    except Exception as e:                                          # noqa: BLE001
        return name, "LOI", str(e)[:110]
    finally:
        shutil.rmtree(cfg, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--only", nargs="*", help="chi probe nhung account nay")
    args = ap.parse_args()

    names = args.only or sorted(ACCOUNTS)
    print(f"Probe {len(names)} account, {args.workers} luong song song...\n")
    rows = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for name, status, note in ex.map(probe, names):
            mark = "OK  " if status == "OK" else "FAIL"
            print(f"  [{mark}] {name:<16} {status:<14} {note}")
            rows.append((name, status))

    alive = [n for n, s in rows if s == "OK"]
    print(f"\n{len(alive)}/{len(names)} account xin duoc proxy key:")
    print("  " + " ".join(alive) if alive else "  (khong co account nao)")
    if not alive:
        return 1
    print("\nNho: 'xin duoc key' != 'du quota cho shard cua ban'. Xem docstring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
