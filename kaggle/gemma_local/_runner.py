# %% =====================  LOCAL RUNNER: batched transformers generator + workload  ==========
import glob as _glob
import queue as _queue
import subprocess as _subprocess
import threading as _threading
import traceback as _traceback
from types import SimpleNamespace as _NS

_T0 = time.time()
WORK = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path("./work")
WORK.mkdir(parents=True, exist_ok=True)
HARD_DEADLINE_S = float(os.environ.get("GL_HARD_DEADLINE_H", "3.6")) * 3600
SOFT_TARGET_START_S = float(os.environ.get("GL_TARGET_START_H", "2.4")) * 3600
SMOKE = os.environ.get("GL_SMOKE", "0") == "1"
N_WORKERS = int(os.environ.get("GL_WORKERS", "2"))
MAX_BATCH = int(os.environ.get("GL_MAX_BATCH", "8"))
IDLE_GAP_S = float(os.environ.get("GL_IDLE_GAP", "2.0"))
SELF_REPS = int(os.environ.get("GL_SELF_REPS", "10"))
_PLOG = WORK / "progress.log"
_PLOG_LOCK = _threading.Lock()


def plog(msg):
    line = "[%s +%6.0fs] %s" % (time.strftime("%H:%M:%S"), time.time() - _T0, msg)
    with _PLOG_LOCK:
        with open(_PLOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    print(line, flush=True)


STATS = {"batches": 0, "gen_tokens": 0, "gen_seconds": 0.0, "requests": 0, "oom_splits": 0,
         "load_seconds": None, "phase": "start"}


def write_status(extra=None):
    d = dict(STATS)
    d["elapsed_s"] = time.time() - _T0
    if extra:
        d.update(extra)
    try:
        (WORK / "status.json").write_text(json.dumps(d, indent=1, default=str), encoding="utf-8")
    except Exception:
        pass


def _watchdog_fire():
    plog("WATCHDOG: hard deadline reached, flushing and exiting")
    try:
        flush_all()
        write_status({"watchdog": True})
    finally:
        os._exit(0)


_wd = _threading.Timer(HARD_DEADLINE_S, _watchdog_fire)
_wd.daemon = True
_wd.start()

# ---- hardware guard -------------------------------------------------------------------
_smi = _subprocess.run("nvidia-smi -L", shell=True, capture_output=True, text=True)
plog("nvidia-smi -L:\n" + (_smi.stdout or _smi.stderr))
_l4 = [ln for ln in (_smi.stdout or "").splitlines() if "L4" in ln]
if len(_l4) != 4 and os.environ.get("GL_ALLOW_ANY_HW") != "1":
    plog("HARDWARE GUARD: expected 4x NVIDIA L4, got %d; exiting" % len(_l4))
    write_status({"hardware_guard": "fail", "smi": _smi.stdout})
    sys.exit(42)

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, LogitsProcessor, LogitsProcessorList

plog("torch %s transformers %s cuda_devices=%d" % (torch.__version__, transformers.__version__,
                                                  torch.cuda.device_count()))


def _find_model_dir():
    for c in _glob.glob("/kaggle/input/**/config.json", recursive=True):
        d = os.path.dirname(c)
        if "gemma-4-31b-it" in d and not d.endswith("assistant"):
            return d
    raise SystemExit("gemma-4-31b-it model dir not found under /kaggle/input")


class _Req:
    __slots__ = ("prompt", "seed", "cap", "event", "result", "error", "prio", "n")

    def __init__(self, prompt, seed, cap, prio=1):
        self.prompt, self.seed, self.cap, self.prio = prompt, int(seed), int(cap), prio
        self.event = _threading.Event()
        self.result = None
        self.error = None


class _Gumbel(LogitsProcessor):
    """Pure temperature sampling with a private RNG stream per row (Gumbel-max trick):
    argmax(logits / T + Gumbel) is a draw from softmax(logits / T). No top-k, no top-p."""

    def __init__(self, seeds, temperature):
        self.seeds, self.t, self.gens = seeds, temperature, None

    def __call__(self, input_ids, scores):
        s = scores.float() / self.t
        if self.gens is None:
            self.gens = [torch.Generator(device=s.device).manual_seed(sd) for sd in self.seeds]
        for i, g in enumerate(self.gens):
            u = torch.rand(s.shape[-1], generator=g, device=s.device).clamp_(1e-20, 1 - 1e-7)
            s[i] -= torch.log(-torch.log(u))
        return s


class LocalGen:
    def __init__(self):
        mdir = _find_model_dir()
        plog("model dir: %s files=%s" % (mdir, sorted(os.listdir(mdir))[:12]))
        t = time.time()
        self.tok = AutoTokenizer.from_pretrained(mdir)
        self.tok.padding_side = "left"
        try:
            self.model = AutoModelForCausalLM.from_pretrained(mdir, dtype=torch.bfloat16, device_map="balanced")
            plog("device_map=balanced")
        except Exception as exc:
            plog("balanced device_map failed (%r); falling back to auto with caps" % (exc,))
            torch.cuda.empty_cache()
            self.model = AutoModelForCausalLM.from_pretrained(
                mdir, dtype=torch.bfloat16, device_map="auto",
                max_memory={0: "14GiB", 1: "16GiB", 2: "16GiB", 3: "17GiB"})
        self.model.eval()
        STATS["load_seconds"] = time.time() - t
        plog("model loaded in %.0fs" % STATS["load_seconds"])
        hf_map = getattr(self.model, "hf_device_map", None)
        devs = {}
        for n, p in list(self.model.named_parameters()):
            devs[str(p.device)] = devs.get(str(p.device), 0) + p.numel() * p.element_size()
        plog("param bytes per device: %s dtype=%s hf_device_map_present=%s" % (
            {k: round(v / 2**30, 2) for k, v in devs.items()}, next(self.model.parameters()).dtype,
            hf_map is not None))
        bad = [d for d in devs if not d.startswith("cuda")]
        if bad:
            raise SystemExit("parameters on non-CUDA devices %s: refusing CPU/disk offload" % bad)
        for i in range(torch.cuda.device_count()):
            plog("gpu%d alloc %.1f GiB free %.1f GiB" % (i, torch.cuda.memory_allocated(i) / 2**30,
                                                      torch.cuda.mem_get_info(i)[0] / 2**30))
        eos = self.model.generation_config.eos_token_id
        self.eos = set([eos] if isinstance(eos, int) else (eos or []))
        if self.tok.eos_token_id is not None:
            self.eos.add(self.tok.eos_token_id)
        self.pad = self.tok.pad_token_id if self.tok.pad_token_id is not None else 0
        self.q = _queue.PriorityQueue()
        self.counter = 0
        self.max_batch = MAX_BATCH
        self.lock = _threading.Lock()
        self.deferred = []
        self.workers = [_threading.Thread(target=self._loop, name="gen%d" % i, daemon=True)
                        for i in range(N_WORKERS)]
        for w in self.workers:
            w.start()
        self.sample_logged = 0

    def submit(self, prompt, seed, cap, prio=1):
        r = _Req(prompt, seed, cap, prio)
        with self.lock:
            self.counter += 1
            r.n = self.counter
        self.q.put((prio, r.n, r))
        r.event.wait()
        if r.error is not None:
            raise RuntimeError(r.error)
        return r.result

    def _take(self):
        with self.lock:
            cand = self.deferred
            self.deferred = []
        first = cand.pop(0) if cand else self.q.get()[2]
        batch, rest = [first], []
        for r in cand:
            (batch if r.cap == first.cap and len(batch) < self.max_batch else rest).append(r)
        last = time.time()
        while len(batch) < self.max_batch:
            try:
                r = self.q.get(timeout=0.25)[2]
            except _queue.Empty:
                if time.time() - last >= IDLE_GAP_S:
                    break
                continue
            last = time.time()
            (batch if r.cap == first.cap else rest).append(r)
        if rest:
            with self.lock:
                self.deferred.extend(rest)
        return batch

    def _loop(self):
        while True:
            batch = self._take()
            try:
                self._run(batch)
            except Exception as exc:
                plog("worker error %r\n%s" % (exc, _traceback.format_exc()))
                for r in batch:
                    if not r.event.is_set():
                        r.error = repr(exc)
                        r.event.set()

    def _run(self, batch):
        try:
            self._generate(batch)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            STATS["oom_splits"] += 1
            if len(batch) == 1:
                raise
            self.max_batch = max(1, len(batch) // 2)
            plog("OOM on batch of %d: splitting, max_batch now %d" % (len(batch), self.max_batch))
            h = len(batch) // 2
            self._run(batch[:h])
            self._run(batch[h:])

    def _generate(self, batch):
        cap = batch[0].cap
        texts = []
        for r in batch:
            try:
                t = self.tok.apply_chat_template([{"role": "user", "content": r.prompt}], tokenize=False,
                                                 add_generation_prompt=True, enable_thinking=False)
            except TypeError:
                t = self.tok.apply_chat_template([{"role": "user", "content": r.prompt}], tokenize=False,
                                                 add_generation_prompt=True)
            texts.append(t)
        enc = self.tok(texts, return_tensors="pt", padding=True, add_special_tokens=False)
        enc = {k: v.to(self.model.device) for k, v in enc.items()}
        n_in = enc["input_ids"].shape[1]
        t0 = time.time()
        with torch.inference_mode():
            out = self.model.generate(
                **enc, max_new_tokens=cap, do_sample=False, top_k=None, top_p=None, temperature=None,
                repetition_penalty=1.0, pad_token_id=self.pad,
                logits_processor=LogitsProcessorList([_Gumbel([r.seed for r in batch], TEMPERATURE)]))
        dt = time.time() - t0
        new = out[:, n_in:].cpu()
        total_tok = 0
        for i, r in enumerate(batch):
            ids = new[i].tolist()
            n = len(ids)
            for j, tid in enumerate(ids):
                if tid in self.eos:
                    n = j
                    break
            total_tok += n
            text = self.tok.decode(ids[:n], skip_special_tokens=True).strip()
            tin = int(enc["attention_mask"][i].sum().item())
            r.result = (text, _NS(input_tokens=tin, output_tokens=n, total_cost_nanodollars=0))
        STATS["batches"] += 1
        STATS["gen_tokens"] += total_tok
        STATS["gen_seconds"] += dt
        STATS["requests"] += len(batch)
        plog("batch rows=%d prompt_len=%d cap=%d steps=%d %.0fs max_out=%d mean_out=%.0f" % (
            len(batch), n_in, cap, new.shape[1], dt, max(x.result[1].output_tokens for x in batch),
            total_tok / len(batch)))
        if self.sample_logged < 3:
            self.sample_logged += 1
            plog("SAMPLE prompt tail: %r" % batch[0].prompt[-200:])
            plog("SAMPLE reply: %r" % batch[0].result[0][:600])
        for r in batch:
            r.event.set()


GEN = None


def _call_llm(model_slug, prompt, seed, ctx=None, max_attempts=None, cap_override=None):
    cap = int(cap_override) if cap_override else MAX_OUT
    return GEN.submit(prompt, seed, cap, 0 if (ctx and "game_id" in ctx) else 1)


# ---- output writers -------------------------------------------------------------------
_OUT_LOCK = _threading.Lock()
PROBE_OUT = {}      # name -> dict(dir, rows)
SELF = {"dir": WORK / "crg-gen-selfplay-p0" / "gemma-local", "games": [], "turns": []}


def _probe_dir(name):
    d = WORK / name / "gemma-local"
    d.mkdir(parents=True, exist_ok=True)
    return d


def flush_probe(name):
    with _OUT_LOCK:
        st = PROBE_OUT.get(name)
        if not st or not st["rows"]:
            return
        rows = sorted(st["rows"], key=lambda r: r["item"])
        cols = list(rows[0].keys())
        buf = io.StringIO(newline="")
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        _atomic_write_text(st["dir"] / "games.csv", buf.getvalue())
        _atomic_write_text(st["dir"] / "probes.jsonl",
                           "".join(json.dumps(r, ensure_ascii=True, default=str) + "\n" for r in rows))


def flush_self():
    with _OUT_LOCK:
        if SELF["games"]:
            SELF["dir"].mkdir(parents=True, exist_ok=True)
            _write_materialized_outputs(SELF["dir"], SELF["games"], SELF["turns"])


def flush_all():
    for n in list(PROBE_OUT):
        flush_probe(n)
    flush_self()


def run_probe_set(name, rb_set, limit=None):
    global RB_SET
    RB_SET = rb_set
    items = _rb_items()
    if limit:
        items = items[:limit]
    PROBE_OUT[name] = {"dir": _probe_dir(name), "rows": []}
    plog("probe set %s (%s): %d items" % (name, rb_set, len(items)))
    errors, done = [], [0]

    def one(it):
        try:
            row = _rb_one(it)
        except Exception as exc:
            errors.append({"k": it["k"], "err": repr(exc)[:300]})
            plog("probe item %s failed: %r" % (it["k"], exc))
            return
        with _OUT_LOCK:
            PROBE_OUT[name]["rows"].append(row)
            done[0] += 1
            n = done[0]
        if n % 10 == 0 or n == len(items):
            flush_probe(name)
            plog("probe %s: %d/%d done" % (name, n, len(items)))

    from concurrent.futures import ThreadPoolExecutor as _TPE
    with _TPE(max_workers=len(items) or 1) as pool:
        futs = [pool.submit(one, it) for it in items]
        for f in futs:
            f.result()
    flush_probe(name)
    rows = PROBE_OUT[name]["rows"]
    pf = sum(r["parse_failed"] for r in rows if r["kind"] != "recog")
    plog("probe set %s finished: %d rows, %d errors, parse_failed(decisions)=%d" % (name, len(rows), len(errors), pf))
    return {"rows": len(rows), "planned": len(items), "errors": errors, "parse_failed": pf}


def run_selfplay(reps):
    model_tag = re.sub(r"[^A-Za-z0-9._-]+", "-", MODEL)
    plog("self-play p=0: %d games, tag %s" % (len(reps), model_tag))
    res = {"done": 0, "planned": len(reps), "errors": [], "parse_failed": 0}

    def one(rep):
        sink = []
        try:
            row, pf, ti, to, cn = play_game(None, 0.0, "en", rep, model_tag, sink)
        except Exception as exc:
            res["errors"].append({"rep": rep, "err": repr(exc)[:300]})
            plog("game rep%d failed: %r" % (rep, exc))
            return
        with _OUT_LOCK:
            SELF["games"].append(row)
            SELF["turns"].extend(sink)
            res["done"] += 1
            res["parse_failed"] += pf
        flush_self()
        plog("game rep%d done: group_total=%s parse_failed=%d tok_out=%d (%d/%d)" % (
            rep, row["group_total"], pf, to, res["done"], res["planned"]))

    threads = [_threading.Thread(target=one, args=(r,), name="game%d" % r) for r in reps]
    for t in threads:
        t.start()
    return threads, res


def main():
    global GEN
    write_status()
    try:
        GEN = LocalGen()
        summary = {}
        reps = list(range(SELF_REPS))
        if SMOKE:
            STATS["phase"] = "smoke"
            summary["probe"] = run_probe_set("crg-gen-probe", "main", limit=6)
            global N_ROUNDS
            N_ROUNDS = 1
            gthreads, gres = run_selfplay([0])
            for t in gthreads:
                t.join()
            summary["selfplay"] = gres
        else:
            STATS["phase"] = "main"
            gthreads, gres = run_selfplay(reps)
            summary["probe"] = run_probe_set("crg-gen-probe", "main")
            write_status({"summary": summary})
            if time.time() - _T0 < SOFT_TARGET_START_S:
                STATS["phase"] = "target"
                summary["target"] = run_probe_set("crg-rb-target", "target")
            else:
                plog("skipping target set: elapsed %.0fs beyond start limit" % (time.time() - _T0))
                summary["target"] = {"skipped": True}
            STATS["phase"] = "waiting_selfplay"
            for t in gthreads:
                t.join()
            summary["selfplay"] = gres
        STATS["phase"] = "done"
    except SystemExit:
        raise
    except BaseException as exc:
        plog("FATAL %r\n%s" % (exc, _traceback.format_exc()))
        summary = {"fatal": repr(exc)}
    finally:
        flush_all()
        write_status({"summary": summary})
        plog("finished; summary=%s" % json.dumps(summary, default=str)[:1500])


main()
os._exit(0)
