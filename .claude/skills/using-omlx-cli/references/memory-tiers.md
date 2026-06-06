# Memory tiers and two-tier KV-cache tuning

Detailed companion to SKILL.md. Read this when sizing a model to a Mac's unified memory or
tuning the hot/cold KV cache. The numbers are conservative starting points, not hard limits —
the right value depends on quantization, context length, and concurrency.

## Why unified memory is the whole game

On Apple Silicon there is no separate VRAM. Model weights, the KV cache, the OS, and every
other app share one pool of unified memory. The budget is roughly:

```
unified_memory  >=  weights + hot_KV_cache + OS_and_app_headroom
```

Leave headroom (a few GB for the OS, more if other apps are running). Ignoring the KV-cache
and headroom terms is the direct cause of the Metal OOM crash loop (see `troubleshooting.md`).

## Per-tier model-size recommendations

Sizes assume 4-bit/quantized MLX weights and a single moderate-context session. Drop a tier
if you run long contexts, high concurrency, or keep heavy apps open.

| Unified memory | Comfortable | Tight (watch memory pressure) | Avoid |
|----------------|-------------|-------------------------------|-------|
| 16 GB | up to ~7–8B | ~13B at low context | 30B+ (OOM loop) |
| 24 GB | up to ~13–14B | ~20B | 70B |
| 32 GB | up to ~20B | ~32B | 70B (no headroom for KV) |
| 64 GB | up to ~70B (quantized) | 70B at long context | unquantized 70B |

Quantization notes:
- 4-bit quantization roughly quarters weight memory vs fp16; it is the default assumption
  above. Higher-precision (8-bit, fp16) weights move each row up at least one tier.
- A 70B model at 4-bit is ~40 GB of weights alone — hence 64 GB is the realistic entry tier
  for it, and only with disciplined KV-cache limits.

## Two-tier KV cache: hot vs cold

The KV cache grows with `context_length × layers × concurrency`. omlx splits it:

- **Hot tier** — in unified memory, fast. Capped by `--hot-cache-max-size`.
- **Cold tier** — paged to SSD at `--paged-ssd-cache-dir`, slower but lets total context
  exceed RAM instead of crashing.

The strategy: cap the hot tier so weights + hot cache + headroom fit in RAM, and let overflow
spill to SSD. Latency on cold reads is the price for not OOM-ing.

### Hot-cache sizing per tier

Approximate `--hot-cache-max-size` after reserving weights + ~4 GB OS headroom:

| Unified memory | Example model | ~Weights | Suggested `--hot-cache-max-size` |
|----------------|---------------|----------|----------------------------------|
| 16 GB | 7–8B @ 4-bit | ~5 GB | ~4–6 GB |
| 24 GB | 13–14B @ 4-bit | ~8 GB | ~8–10 GB |
| 32 GB | 20B @ 4-bit | ~12 GB | ~12–14 GB |
| 64 GB | 70B @ 4-bit | ~40 GB | ~16–18 GB |

If a workload routinely needs more KV than the hot cap, that is expected — the cold tier
absorbs it. If you see swap thrash (silent memory pressure in `troubleshooting.md`), the hot
cap is too high for the chosen model; lower it.

### Cold-tier (SSD) guidance

- Point `--paged-ssd-cache-dir` at fast internal SSD, not an external/USB or network volume —
  cold-read latency dominates long-context throughput.
- Ensure free SSD space comfortably exceeds the expected cold-tier size; a full disk stalls
  paging.
- Clear the directory between serving sessions to reclaim space.

## Worked example

64 GB M3 Max, serving a 70B 4-bit model for long-context RAG:

```bash
omlx serve --model <70b-4bit> \
  --hot-cache-max-size 16GB \
  --paged-ssd-cache-dir /var/tmp/omlx-kv
```

Budget: ~40 GB weights + 16 GB hot cache + ~4 GB headroom ≈ 60 GB, under 64 GB, with the
cold tier on SSD handling context beyond the 16 GB hot cap.
