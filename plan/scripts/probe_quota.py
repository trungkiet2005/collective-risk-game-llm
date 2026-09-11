"""Do QUOTA CON LAI cua tung account, khong chi con/het.

`probe_accounts.py` chi tra loi CON/HET key. Do la lo hong da tra gia that: toi
10-09-2026, 19/23 account probe XANH, roi 9/12 shard chet giua chung vi 403 het quota
o muc chi $0,24-$1,37. Probe xanh vi xin key khong ton quota.

CACH DO -- dung chinh thong bao loi lam thuoc do:

    403 ... 'The max estimated cost of operation ($0.018209) exceeds your available
             quota (based on max_output_tokens).'

Proxy DAT COC TRUOC theo `max_output_tokens`, va no NOI RA so tien dat coc. Tien coc
ti le thuan voi `max_output_tokens`. Vay:

  * goi voi max_output_tokens = M ma 403  -> quota con lai < chi phi(M)
  * goi voi max_output_tokens = M ma OK   -> quota con lai >= chi phi(M)

Do nhi phan tren M -> kep duoc quota con lai trong mot khoang hep. Moi lan goi THANH
CONG chi sinh 1 token that, nen ca lan do ton duoi mot xu; lan 403 khong ton gi.

⚠️ Day la PROBE, khong sinh data. Ket qua KHONG duoc ghi vao results/.

⚠️ Quota la CUA SO TRUOT 24H, khong reset luc nua dem. Account tieu $7 luc 22:00 thi
   phai toi 22:00 hom sau moi day lai. Nen "het quota" hom nay khong co nghia la
   "sang mai co ngay" -- no hoi lai dan theo dung gio da tieu.

Dung:
    python plan/scripts/probe_quota.py                     # tat ca account
    python plan/scripts/probe_quota.py --only acc1 acc2
    python plan/scripts/probe_quota.py --need 3.5          # danh dau account du cho shard $3.5
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from launch_shard import ACCOUNTS  # noqa: E402  — dung CHUNG bang credential

# Model re nhat con song, de tien coc gan nhu ca la phan output -> do nhay hon.
PROBE_MODEL = "gemini-3.5-flash-lite"
# Bien do do: 64 token la san duoi, 4 trieu la "tran" xin.
#
# ⚠️ TRAN THAT SU THAP HON NHIEU. Proxy KEP `max_output_tokens` xuong gioi han output
# cua model truoc khi tinh tien coc, nen xin 4 trieu token khong tao ra tien coc 4 trieu
# token. Do that 10-09-2026 tren gemini-3.5-flash-lite: tien coc o M_HI chi ~$0,03.
# Nghia la phep do nay CHI phan biet duoc "duoi ~$0,03" voi "tren ~$0,03" -- no KHONG
# noi duoc mot account con $0,04 hay con $10. Muon tran cao hon thi phai do bang model
# co gia output cao hon (va con song tren proxy dang dung).
M_LO, M_HI = 64, 4_000_000
STEPS = 12          # log2(4e6/64) ~ 16; 12 buoc du hep de ra 2 chu so co nghia


def _auth(name, cfg, timeout=120):
    """Xin proxy key cho account. Tra (url, key) hoac (None, ly_do)."""
    kind, path = ACCOUNTS[name]
    if not Path(path).is_file():
        return None, "THIEU_FILE"
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
            return None, "KHONG_CO_TOKEN"
        env["KAGGLE_API_TOKEN"] = m.group(0)
    else:
        shutil.copyfile(path, cfg / "kaggle.json")

    env_file = cfg / "account.env"
    r = subprocess.run(["kaggle", "benchmarks", "auth", "-y", "--env-file", str(env_file)],
                       env=env, capture_output=True, text=True, timeout=timeout)
    if not env_file.is_file():
        blob = (r.stdout or "") + (r.stderr or "")
        return None, ("403_VERIFY" if "verification" in blob.lower() else "AUTH_LOI")
    conf = dict(re.findall(r"^(\w+)=(.*)$", env_file.read_text(encoding="utf-8"), re.M))
    if "MODEL_PROXY_API_KEY" not in conf:
        return None, "KHONG_CO_KEY"
    return (conf["MODEL_PROXY_URL"], conf["MODEL_PROXY_API_KEY"]), None


def _call(url, key, max_out, timeout=60):
    """Goi 1 lan. Tra ('ok', None) | ('403', tien_coc) | ('loi', mo_ta)."""
    body = json.dumps({
        "model": PROBE_MODEL,
        "messages": [{"role": "user", "content": "hi"}],
        "max_completion_tokens": max_out,
    }).encode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/openapi/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return ("ok", None) if r.status == 200 else ("loi", f"http {r.status}")
    except urllib.error.HTTPError as e:
        blob = e.read().decode("utf-8", "replace")
        if e.code == 403 and "exceeds your available quota" in blob:
            m = re.search(r"\$([0-9.]+)\)? exceeds", blob)
            return "403", float(m.group(1)) if m else None
        return "loi", f"http {e.code}: {blob[:80]}"
    except Exception as e:                                          # noqa: BLE001
        return "loi", str(e)[:80]


def measure(name):
    """Kep quota con lai bang do nhi phan tren max_output_tokens."""
    cfg = Path(tempfile.mkdtemp(prefix=f"kq_{name}_"))
    try:
        auth, err = _auth(name, cfg)
        if err:
            return name, err, None, None
        url, key = auth

        # San: goi nho nhat. 403 ngay -> can kiet, khong do duoc nua.
        st, cost = _call(url, key, M_LO)
        if st == "403":
            return name, "CAN_KIET", 0.0, cost
        if st == "loi":
            return name, "LOI", None, cost

        # Tran: goi lon nhat. Qua duoc -> con nhieu hon suc do cua thang do.
        st_hi, cost_hi = _call(url, key, M_HI)
        if st_hi == "ok":
            # Qua duoc muc dat coc lon nhat ma phep do tao ra duoc. Chi ket luan duoc
            # "tren tran do", KHONG ket luan duoc "con nguyen $10".
            return name, "TREN_TRAN", None, None
        if st_hi == "loi":
            return name, "LOI", None, cost_hi

        lo, hi = M_LO, M_HI          # lo: da OK · hi: da 403
        lo_cost, hi_cost = 0.0, cost_hi
        for _ in range(STEPS):
            if hi - lo <= 1:
                break
            mid = (lo + hi) // 2
            st, c = _call(url, key, mid)
            if st == "ok":
                lo = mid
            elif st == "403":
                hi, hi_cost = mid, (c if c is not None else hi_cost)
            else:
                break
        # Quota con lai nam giua chi phi(lo) va chi phi(hi). Suy chi phi(lo) tu ti le
        # tuyen tinh cua chi phi(hi) da biet -- day la can duoi chac chan.
        if hi_cost:
            lo_cost = hi_cost * lo / hi
        return name, "CON", lo_cost, hi_cost
    except Exception as e:                                          # noqa: BLE001
        return name, "LOI", None, str(e)[:80]
    finally:
        shutil.rmtree(cfg, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--model", default=None,
                    help="do bang model khac (quota co the tinh THEO MODEL)")
    ap.add_argument("--need", type=float, default=None,
                    help="danh dau account co quota >= so nay")
    args = ap.parse_args()

    global PROBE_MODEL
    if args.model:
        PROBE_MODEL = args.model
    names = args.only or sorted(ACCOUNTS)
    print(f"Do quota {len(names)} account ({args.workers} luong) · model {PROBE_MODEL}")
    print("Moi lan goi THANH CONG sinh 1 token that -> ca lan do duoi mot xu.\n")

    rows = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for name, st, lo, hi in ex.map(measure, names):
            if st == "CON":
                txt = f"${lo:.2f} - ${hi:.2f}" if isinstance(hi, float) else f">= ${lo:.2f}"
            elif st == "TREN_TRAN":
                txt = "> tran phep do (~$0,03) — KHONG biet la $0,04 hay $10"
            elif st == "CAN_KIET":
                txt = f"< ${hi:.4f}" if isinstance(hi, float) else "~ $0"
            else:
                txt = str(hi or "")
            print(f"  {name:<16} {st:<10} {txt}")
            rows.append((name, st, lo))

    # Khong co --need thi CHI account tren tran do moi dang thu: mot account do duoc
    # $0,02 la da can kiet trong thuc te, dung goi no la "dung duoc".
    usable = [(n, lo) for n, st, lo in rows
              if st == "TREN_TRAN"
              or (st == "CON" and args.need is not None and (lo or 0) >= args.need)]
    print(f"\n{len(usable)}/{len(names)} account CON DANG THU"
          + (f" (>= ${args.need})" if args.need else "")
          + " - 'tren tran do' KHONG bao dam du cho ca shard")
    if usable:
        print("  " + " ".join(n for n, _ in usable))
    dry = [n for n, st, _ in rows if st == "CAN_KIET"]
    if dry:
        print(f"\nCan kiet ({len(dry)}): " + " ".join(dry))
    print("\nNho: quota la CUA SO TRUOT 24H. 'Het' hom nay se hoi lai dan theo dung gio da tieu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
