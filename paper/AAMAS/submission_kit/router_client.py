# %% =====================  MODEL ROUTER  ===============================================
# Every model call goes to ONE OpenAI-compatible chat-completions endpoint, so a single
# key reaches every provider. OpenRouter is the default; point CRG_ROUTER_URL at a
# LiteLLM proxy, a vLLM server or a provider's own OpenAI-compatible API to use those
# instead. The seat's model travels in the request body, so a mixed table needs no
# second client.
ROUTER_URL = os.environ.get("CRG_ROUTER_URL", "https://openrouter.ai/api/v1").rstrip("/")
ROUTER_KEY = (os.environ.get("CRG_ROUTER_KEY") or os.environ.get("OPENROUTER_API_KEY")
              or os.environ.get("OPENAI_API_KEY") or "")
# Name of the output-cap field: "max_tokens" for OpenRouter, LiteLLM and vLLM; the
# OpenAI API wants "max_completion_tokens" for its reasoning models.
ROUTER_CAP_FIELD = os.environ.get("CRG_ROUTER_CAP_FIELD", "max_tokens")
ROUTER_TIMEOUT_S = float(os.environ.get("CRG_ROUTER_TIMEOUT", "300"))
_IS_OPENROUTER = "openrouter.ai" in ROUTER_URL


class Usage(object):
    """Token counts of one call, and its cost in nanodollars when the router reports it."""

    def __init__(self, input_tokens=0, output_tokens=0, total_cost_nanodollars=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_cost_nanodollars = total_cost_nanodollars


def _router_chat(model_slug, prompt, seed, cap):
    """One chat completion. Returns (text, Usage); raises RuntimeError naming the HTTP code."""
    body = {"model": model_slug,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": TEMPERATURE,
            "seed": int(seed),
            ROUTER_CAP_FIELD: int(cap)}
    if _IS_OPENROUTER:
        body["usage"] = {"include": True}            # OpenRouter adds the cost in USD
    request = urllib.request.Request(
        ROUTER_URL + "/chat/completions", data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + ROUTER_KEY})
    try:
        with urllib.request.urlopen(request, timeout=ROUTER_TIMEOUT_S) as response:
            reply = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError("HTTP %d: %s" % (exc.code, _clip(detail, 300)))
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError("connection error: %s" % exc)
    if "error" in reply and not reply.get("choices"):
        raise RuntimeError("router error: %s" % _clip(reply["error"], 300))
    choice = (reply.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    usage = reply.get("usage") or {}
    return text, Usage(input_tokens=usage.get("prompt_tokens") or 0,
                       output_tokens=usage.get("completion_tokens") or 0,
                       total_cost_nanodollars=int(round((usage.get("cost") or 0) * 1e9)))


def _call_llm(model_slug, prompt, seed, ctx=None, max_attempts=None,
              cap_override=None):
    """One free-text generation on ONE seat's model. Returns (text, usage).

    `model_slug` None means the run-selected MODEL. Transient errors (429, 5xx,
    timeouts) back off exponentially; an empty reply has its own retry budget and never
    becomes a contribution; any other error, an authentication or quota error included,
    ends the call loudly. `cap_override` lets decide() raise the output cap after a
    truncated reply, since a retry at the same cap is cut off at the same place.
    """
    if max_attempts is None:
        max_attempts = MAX_CALL_ATTEMPTS
    cap = int(cap_override) if cap_override else _max_out_for(model_slug)
    slug = model_slug or MODEL
    if ctx is not None and model_slug is not None and (SEAT_MODELS
                                                       or model_slug != MODEL):
        ctx = dict(ctx, seat_model=model_slug)
    attempt = 0
    empty_retries = 0
    MAX_EMPTY_RETRIES = 15
    while True:
        attempt += 1
        try:
            text, usage = _router_chat(slug, prompt, seed, cap)
        except Exception as e:
            msg = str(e).lower()
            code = _http_code(e)
            if code in (400, 401, 402, 403, 404) or any(t in msg for t in _QUOTA_MARKERS):
                _emit_error("request_refused", e, http=code, fatal=True, ctx=ctx,
                            hint="check CRG_ROUTER_URL, the API key, the model name "
                                 "and the account's credit")
                raise
            if not any(t in msg for t in _TRANSIENT):
                _emit_error("unclassified", e, http=code, fatal=True, ctx=ctx,
                            attempt=attempt)
                raise
            if attempt >= max_attempts:
                _emit_error("transient_exhausted", e, http=code, fatal=True, ctx=ctx,
                            attempt=attempt, max_attempts=max_attempts)
                raise
            sleep_s = min(2 ** attempt, 30)
            _emit_error("transient", e, http=code, fatal=False, ctx=ctx,
                        attempt=attempt, max_attempts=max_attempts, sleep_s=sleep_s)
            time.sleep(sleep_s)
            continue
        if text.strip():
            return text, usage
        # HTTP 200 with no text: a reasoning model spent its whole budget, or the
        # provider hiccuped. Never parse it; retry on its own budget, then fail.
        empty_retries += 1
        if empty_retries > MAX_EMPTY_RETRIES:
            _emit_error("empty_content_exhausted", "%d consecutive empty replies at "
                        "cap=%d" % (empty_retries, cap), http=200, fatal=True,
                        ctx=ctx, cap=cap, hint="raise CRG_MAX_OUT")
            raise RuntimeError("the model returned no text %d times in a row (cap=%d)"
                               % (empty_retries, cap))
        sleep_s = min(5 * empty_retries, 60)
        _emit_error("empty_content", "HTTP 200 with empty content", http=200,
                    fatal=False, ctx=ctx, attempt=empty_retries,
                    max_attempts=MAX_EMPTY_RETRIES, sleep_s=sleep_s, cap=cap)
        time.sleep(sleep_s)
        attempt -= 1


def _require(expected, actual, expectation):
    """End-of-sweep health check: a sweep that fails it is not a valid measurement."""
    if expected != actual:
        raise SystemExit("check failed: %s (expected %r, got %r)"
                         % (expectation, expected, actual))
