"""Second-stage probe: do the live proxy models answer a real CRG decision prompt?

Sends one Milinski-style collective-risk turn and checks the reply parses as the
contribution JSON the CRSD harness expects. Parallel over all given slugs.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PROMPT = (
    "You are Player A in a 6-round collective-risk game with 2 other players. "
    "Each round every player may contribute 0, 2, or 4 from a private endowment of 40. "
    "If total group contributions reach 120 by the end of round 6, everyone keeps "
    "whatever is left of their endowment. Otherwise there is a 90% chance you lose everything. "
    "It is round 1 and the group total so far is 0. "
    'Answer with ONLY a JSON object: {"contribution": <0|2|4>, "reason": "<one short sentence>"}'
)

MAX_TOKENS = 6000


def probe(url, key, slug):
    body = json.dumps({
        "model": slug,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_completion_tokens": MAX_TOKENS,
    }).encode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/openapi/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            msg = json.loads(raw).get("message") or raw
        except Exception:
            msg = raw
        return {"slug": slug, "status": f"HTTP {e.code}", "detail": msg.strip()[:100],
                "secs": round(time.time() - t0, 1)}
    except Exception as e:
        return {"slug": slug, "status": type(e).__name__, "detail": str(e)[:100],
                "secs": round(time.time() - t0, 1)}

    ch = (payload.get("choices") or [{}])[0]
    text = ((ch.get("message") or {}).get("content") or "").strip()
    usage = payload.get("usage") or {}
    contribution = None
    m = re.search(r'"contribution"\s*:\s*(\d+)', text)
    if m:
        contribution = int(m.group(1))
    return {
        "slug": slug,
        "status": "PARSED" if contribution is not None else ("TEXT_ONLY" if text else "EMPTY"),
        "contribution": contribution,
        "finish": ch.get("finish_reason"),
        "in_tok": usage.get("prompt_tokens"),
        "out_tok": usage.get("completion_tokens"),
        "reply_head": text.replace("\n", " ")[:90],
        "secs": round(time.time() - t0, 1),
    }


def main():
    env_file, slugs_csv = sys.argv[1], sys.argv[2]
    env = {}
    with open(env_file, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^([A-Z_0-9]+)=(.*)$", line.strip())
            if m:
                env[m.group(1)] = m.group(2)
    slugs = [s for s in slugs_csv.split(",") if s]
    url, key = env["MODEL_PROXY_URL"], env["MODEL_PROXY_API_KEY"]
    print(f"CRG prompt probe: {len(slugs)} models, max_completion_tokens={MAX_TOKENS}\n", flush=True)
    out = []
    with ThreadPoolExecutor(max_workers=len(slugs)) as pool:
        for r in pool.map(lambda s: probe(url, key, s), slugs):
            out.append(r)
            print(f"  {r['status']:<10} {r['slug']:<32} contrib={r.get('contribution')} "
                  f"out_tok={r.get('out_tok')} {r['secs']}s | {r.get('reply_head', r.get('detail'))}",
                  flush=True)
    json.dump(out, open("probe_crg.json", "w", encoding="utf-8"), indent=2)


if __name__ == "__main__":
    main()
