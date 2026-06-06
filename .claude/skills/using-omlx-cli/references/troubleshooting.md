# omlx troubleshooting

Detailed companion to SKILL.md. Read this when a user reports an omlx failure. On Apple
Silicon nearly every failure is unified-memory pressure in disguise, so most fixes come back
to sizing the model and the hot KV cache (see `memory-tiers.md`).

## Contents

- [Metal OOM crash loop](#metal-oom-crash-loop)
- [Silent memory pressure](#silent-memory-pressure)
- [Mixed-workload instability](#mixed-workload-instability)
- [Model not showing](#model-not-showing)

## Metal OOM crash loop

**Symptom:** `omlx serve` starts loading, then the process is killed by Metal/macOS with an
out-of-memory error, and (under a supervisor or restart wrapper) immediately relaunches and
crashes again — a tight crash loop. May surface as a Metal allocation failure in the logs.

**Root cause:** The model weights plus the hot KV cache plus OS headroom exceed unified
memory. The most common trigger is loading a model one or more tiers too large for the
machine (e.g., a 30B on 16 GB, or an unquantized model).

**Fix:**
1. Drop to a model size that fits the tier in `memory-tiers.md` (and prefer 4-bit weights).
2. Lower `--hot-cache-max-size` so weights + hot cache + ~4 GB headroom stay under RAM; let
   overflow page to the cold tier via `--paged-ssd-cache-dir`.
3. Close other memory-heavy apps before serving.
4. If using a restart wrapper, disable auto-restart until the size is corrected so the loop
   stops masking the real error.

## Silent memory pressure

**Symptom:** No hard crash, but throughput collapses — tokens/sec drops, latency spikes, the
fans spin up, and the machine becomes sluggish. Activity Monitor shows yellow/red memory
pressure and rising swap.

**Root cause:** The workload fits *barely*, so instead of OOM-killing, macOS compresses and
swaps memory to keep going. The hot cache or context length pushed unified memory past the
comfortable point. This is the warning state right before the OOM crash loop.

**Fix:**
1. Lower `--hot-cache-max-size` so more cache lives in the (SSD) cold tier instead of forcing
   swap.
2. Reduce context length or concurrency for the workload.
3. Step down one model tier if pressure persists at idle.
4. Watch `memory_pressure` / `vm_stat` or the Activity Monitor graph while tuning — the goal
   is green pressure with no sustained swap growth.

## Mixed-workload instability

**Symptom:** omlx is stable on its own but becomes erratic — stalls, slowdowns, or
intermittent OOM — when other GPU/memory-heavy apps run (video editing, other ML jobs,
browsers with many tabs, another local model).

**Root cause:** Unified memory and the Metal GPU are shared. A second consumer eats into the
headroom omlx was sized for, tipping the total over the limit. Because everything shares one
pool, omlx cannot reserve memory away from the rest of the system.

**Fix:**
1. Size omlx for the *real* concurrent footprint, not for a quiet machine — leave extra
   headroom if other GPU apps will run.
2. Avoid running two local inference servers at once; they double the resident weights.
3. If the mix is unavoidable, drop omlx a model tier and lower `--hot-cache-max-size` to
   create slack for the other workload.

## Model not showing

**Symptom:** `omlx serve --model <model>` fails to find the model, or `<model>` is absent
from the served/listed models, even though you expected it to be available.

**Root cause:** The model was never pulled, is not in MLX format, lives outside the directory
omlx scans, or the name/identifier does not match what is on disk.

**Fix:**
1. Run `omlx list` to see what is actually registered locally.
2. `omlx pull <model>` (or place the MLX-format weights where omlx expects them) before
   serving.
3. Check the exact identifier — names are case- and path-sensitive; copy the value from
   `omlx list` rather than retyping.
4. Confirm the weights are MLX-format; GGUF/other formats meant for llama.cpp/Ollama will not
   load in omlx.
