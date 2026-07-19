# %%
"""Minimal SERVER-SIDE availability probe for the Kaggle Model Proxy.

Runs ONE cheap prompt against whatever model `kaggle b t run -m <slug>` selects.
Deliberately does NOT set LLM_DEFAULT, so the -m flag actually controls the model
(crg_task.py hard-pins LLM_DEFAULT at import, which would override -m and always
run flash-lite). Purpose: find out whether claude/gpt/deepseek serve on the
PRODUCTION proxy used by server-side runs, vs the staging proxy used locally.
"""
try:
    from dotenv import load_dotenv
    load_dotenv()          # local validation only; the server injects MODEL_PROXY_* itself
except Exception:
    pass

import kaggle_benchmarks as kbench


# %%
@kbench.task(
    name="crg-proxy-probe",
    description="One cheap prompt to check whether a given proxy model actually serves.",
)
def crg_proxy_probe(llm) -> dict:
    with kbench.chats.new("probe", orphan=True) as chat:
        reply = llm.prompt("Reply with only the single word: OK", temperature=0)
    u = chat.usage
    result = {
        "reply": reply.strip()[:80],
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "cost_usd": round((u.total_cost_nanodollars or 0) / 1e9, 6),
    }
    print("PROBE RESULT:", result)
    kbench.assertions.assert_equal(
        True, bool(reply and reply.strip()),
        expectation="Model returned a non-empty reply (it is reachable on this proxy)")
    return result


crg_proxy_probe.run(kbench.llm)
