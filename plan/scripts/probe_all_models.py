"""Parallel liveness probe for every model on the Kaggle Model Proxy.

Reads MODEL_PROXY_URL / MODEL_PROXY_API_KEY from an --env-file, takes the slug
list from `kaggle b t models` output, fires one cheap prompt per model in
parallel and reports which ones actually return content.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PROMPT = "Reply with only the single word: OK"


def load_env(path):
    env = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^([A-Z_0-9]+)=(.*)$", line.strip())
            if m:
                env[m.group(1)] = m.group(2)
    return env


def load_slugs(path):
    slugs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip()
            if not line or line.startswith("Slug") or line.startswith("---"):
                continue
            slug = line.split()[0]
            if slug:
                slugs.append(slug)
    return slugs


def probe(url, key, slug, max_tokens, timeout):
    body = json.dumps({
        "model": slug,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_completion_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/openapi/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            msg = json.loads(raw).get("message") or raw
        except Exception:
            msg = raw
        return {"slug": slug, "status": f"HTTP {e.code}", "detail": msg.strip()[:120],
                "secs": round(time.time() - t0, 1)}
    except Exception as e:  # timeout, connection reset, ...
        return {"slug": slug, "status": type(e).__name__, "detail": str(e)[:120],
                "secs": round(time.time() - t0, 1)}

    choices = payload.get("choices") or []
    text = ""
    finish = ""
    if choices:
        finish = choices[0].get("finish_reason") or ""
        text = (choices[0].get("message") or {}).get("content") or ""
    usage = payload.get("usage") or {}
    cost = usage.get("cost")
    return {
        "slug": slug,
        "status": "OK" if text.strip() else ("EMPTY" if choices else "NO_CHOICES"),
        "reply": text.strip().replace("\n", " ")[:40],
        "finish": finish,
        "in_tok": usage.get("prompt_tokens"),
        "out_tok": usage.get("completion_tokens"),
        "cost_usd": round(cost / 1e9, 8) if isinstance(cost, (int, float)) else None,
        "secs": round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", required=True)
    ap.add_argument("--models-file", required=True)
    ap.add_argument("--workers", type=int, default=13)
    ap.add_argument("--max-tokens", type=int, default=64)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--only", default=None, help="comma-separated slug substrings")
    ap.add_argument("--out", default="probe_results.json")
    args = ap.parse_args()

    env = load_env(args.env_file)
    url, key = env["MODEL_PROXY_URL"], env["MODEL_PROXY_API_KEY"]
    slugs = load_slugs(args.models_file)
    if args.only:
        pats = [p.strip() for p in args.only.split(",") if p.strip()]
        slugs = [s for s in slugs if any(p in s for p in pats)]

    print(f"probing {len(slugs)} models @ {url} (workers={args.workers}, "
          f"max_completion_tokens={args.max_tokens})", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for r in pool.map(lambda s: probe(url, key, s, args.max_tokens, args.timeout), slugs):
            results.append(r)
            print(f"  {r['status']:<12} {r['slug']:<32} {r.get('secs')}s "
                  f"{r.get('reply', r.get('detail', ''))!r}", flush=True)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    ok = [r for r in results if r["status"] == "OK"]
    empty = [r for r in results if r["status"] in ("EMPTY", "NO_CHOICES")]
    bad = [r for r in results if r["status"] not in ("OK", "EMPTY", "NO_CHOICES")]
    total = sum(r.get("cost_usd") or 0 for r in results)
    print(f"\nOK={len(ok)}  EMPTY={len(empty)}  FAILED={len(bad)}  "
          f"total_cost=${total:.6f}  -> {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
