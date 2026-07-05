#!/usr/local/bin/layer7

# Layer7 Model Engine & Inventory
Polyglot Specification for Local LLM Execution on Ampere (RTX 3090)

**Version:** 1.2
**Date:** 2026-07-05
**Status:** Production Ready

This file acts as a human-readable manifest and runtime engine for advanced local models. It uses Markdown layout to structure configuration matrixes, isolating infrastructure paths from operational runtime loops.

Allow exception: level 4 headers

## 1. Global System Infrastructure

Static absolute filesystem paths pointing to binaries and data directories.

### Environment_Paths

```JSON
{
  "llama_bin": "/home/oobabooga/llama.cpp/build/bin/llama-server",
  "models_dir": "/home/oobabooga/text-generation-webui/user_data/models",
  "mmproj_dir": "/home/oobabooga/text-generation-webui/user_data/mmproj",
  "host": "0.0.0.0",
  "port": 5005
}
```

## 2. Model Registry & Load Strategies

Documentation of operational limits, constraints, and hardware interactions.

Running a local model well is a matter of picking a point on several independent axes at once, not finding one "best" setting. This registry and the profiles below cover four of them: **where the model lives** (fully in VRAM vs. spilling into host memory, which decides whether `--no-mmap` helps or hurts), **how precisely the conversation is remembered** (the KV cache quantization discussed in Section 3), **how much gets processed at once** (batch size, also Section 3), and **whether generation gets a head start** (speculative decoding via MTP draft models, see the `-md` entries below). The tier split that follows is really the first of these axes made concrete.

### Tier_1_VRAM_Sweets

Models that sit completely inside the 3090's 24GB VRAM barrier. They optimize for extreme execution speeds and prompt processing by avoiding host bus streaming.

* **`gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf`**
* *Strengths:* Massive reasoning capabilities via Quantization-Aware Training (QAT). Low cognitive decay.
* *Vision Support:* Yes (`gemma-4-26B-A4B-it-qat-UD-Q4_K_XL-mmproj-BF16.gguf`).
* *MTP Assistant:* `gemma-4-26B-A4B-it-Q4_0-MTP.gguf`.

* **`gemma-4-31B-it-qat-UD-Q4_K_XL.gguf`**
* *Strengths:* High parameter density with deep instructional adherence. Ideal daily driver.
* *Vision Support:* Yes (`gemma-4-31B-it-qat-UD-Q4_K_XL-mmproj-BF16.gguf`).
* *MTP Assistant:* `gemma-4-31B-it-Q4_0-MTP.gguf`.

* **`Qwen3.6-27B-UD-Q4_K_XL.gguf`**
* *Strengths:* Excellent structured format generation and general intelligence.
* *Vision Support:* Yes (`qwen3.6-mmproj-F16.gguf`).

* **`Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf`**
* *Strengths:* Deep context code layout logic, agent automation structures.
* *Vision Support:* No.

* **`Qwopus3.6-27B-v2-MTP-Q5_K_M.gguf`**
* *Strengths:* High accuracy Q5 quantization with inline Multi-Token Prediction capability.
* *Vision Support:* No.

### Tier_2_System_Spillers

Models that far exceed VRAM limits and must leverage underlying virtual paging memory tables.

* **`Qwen3-Coder-Next-UD-Q4_K_XL.gguf`** (~47GB)
* *Strengths:* Unmatched multi-file context comprehension and execution path modeling.
* *Vision Support:* Yes (`Qwen3-Coder-Next-UD-Q4_K_XL-mmproj-BF16.gguf`).
* *Strategy:* `Model_Resolver` sets `--no-mmap` for this model to allow kernel Unified Memory fault tracking across the PCIe lanes. This model exceeds VRAM and spills into host memory; without `--no-mmap`, lazy page-in from the memory-mapped file competes unpredictably with that offload path, producing inconsistent step latency. This flag is specific to spillover models — it is deliberately absent from every Tier 1 entry, where it would only slow load time and raise RAM pressure with no compensating benefit.

## 3. Operational Profiles

Configuring data tables for specific processing footprints.

Every token generated leaves a residue: a key and a value vector, cached per layer, per head, so the model doesn't have to recompute attention over the whole prompt on every step. That cache grows linearly with context length, and at full precision (`f16`) it gets expensive fast — a long context can burn more VRAM holding *memory of what's already been said* than the model's own weights take to load. Quantizing the cache (`q4_0`) shrinks that footprint substantially, trading a small amount of attention fidelity for room to breathe. The cost is subtle: fine-grained retrieval over very long contexts degrades a little before generation quality does, so it's a tradeoff worth naming rather than ignoring.

Batch size is a different lever — it governs how many tokens get processed in parallel during prompt ingestion, not generation. A larger batch means the GPU chews through a long prompt faster, at the cost of holding more intermediate activations in memory at once. A smaller batch is gentler on VRAM but processes prompts more slowly, token-chunk by token-chunk.

The three profiles below are just named points on that shared tradeoff surface. `Speed_Profile` quantizes the cache and maximizes batch size — fast prompt processing, fast generation, some precision given up. `Accuracy_Profile` holds the cache at full precision and shrinks the batch — slower, but nothing about the model's attention is approximated. `Space_Profile` quantizes the cache like Speed but keeps the batch small too, minimizing the footprint for running alongside other work rather than maximizing throughput.

### Speed_Profile

Maximizes output velocity by scaling down KV context precision to free up GPU calculation registers.

```JSON
{
  "k_type": "q4_0",
  "v_type": "q4_0",
  "batch": 4096
}
```

### Accuracy_Profile

Maintains strict reference precision at the cost of VRAM footprint. Best for complex code bases or zero-shot extraction parsing.

```JSON
{
  "k_type": "f16",
  "v_type": "f16",
  "batch": 2048
}
```

### Space_Profile

Aggressive constraint scaling designed to isolate the background execution footprint during concurrent system use.

```JSON
{
  "k_type": "q4_0",
  "v_type": "q4_0",
  "batch": 512
}
```

## 4. Orchestration Engine

The executable glue layers mapping Layer7 variable definitions into native system memory calls.

### Runtime_State {}

### Argument_Parser > Runtime_State

Translates incoming CLI inputs into structured environment parameters. Uses named flags rather than positional order. `--ctx` and `--ngl` are optional escape hatches; when omitted, context size and GPU layer count are left off the `llama-server` invocation entirely so llama.cpp auto-fits both.

```python
import sys
import json

USAGE = (
    "Usage: layer7 layer7llama.md --model <key> --profile <speed|accuracy|space> "
    "[--vision] [--ctx N] [--ngl N]\n"
    "Example: layer7 layer7llama.md --model gemma31 --profile accuracy --vision"
)

args = sys.argv[1:]

state = {
    "model_key": None,
    "profile_name": None,
    "vision_toggle": "vision_off",
    "ctx_override": None,
    "ngl_override": None,
}

FLAGS_NEEDING_VALUE = {"--model", "--profile", "--ctx", "--ngl"}

i = 0
while i < len(args):
    flag = args[i]

    if flag in FLAGS_NEEDING_VALUE:
        if i + 1 >= len(args):
            print(f"Error: {flag} requires a value", file=sys.stderr)
            sys.exit(1)
        value = args[i + 1]
        i += 2
    elif flag in ("--vision", "--no-vision"):
        value = None
        i += 1
    else:
        print(f"Error: Unknown argument '{flag}'", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    if flag == "--model":
        state["model_key"] = value.lower()
    elif flag == "--profile":
        state["profile_name"] = value.lower()
    elif flag == "--vision":
        state["vision_toggle"] = "vision_on"
    elif flag == "--no-vision":
        state["vision_toggle"] = "vision_off"
    elif flag == "--ctx":
        try:
            state["ctx_override"] = int(value)
        except ValueError:
            print(f"Error: --ctx expects an integer, got '{value}'", file=sys.stderr)
            sys.exit(1)
    elif flag == "--ngl":
        try:
            state["ngl_override"] = int(value)
        except ValueError:
            print(f"Error: --ngl expects an integer, got '{value}'", file=sys.stderr)
            sys.exit(1)

if not state["model_key"] or not state["profile_name"]:
    print("Error: --model and --profile are required.", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    sys.exit(1)

print(json.dumps(state))
```

### Model_Resolver >> Runtime_State

Resolves shorthand keys into exact target paths, speculative configurations, and matching multimodal project tracks.

```python
import sys
import json

m_dir = Environment_Paths['models_dir']
v_dir = Environment_Paths['mmproj_dir']
model_key = Runtime_State['model_key']

extra_args = ""
mmproj_path = ""
mtp_path = ""

if model_key == "gemma26":
    model_path = f"{m_dir}/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf"
    mtp_path = f"{m_dir}/gemma-4-26B-A4B-it-Q4_0-MTP.gguf"
    mmproj_path = f"{v_dir}/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL-mmproj-BF16.gguf"
    extra_args = f"-md {mtp_path} --spec-type draft-mtp --spec-draft-n-max 3"
elif model_key == "gemma31":
    model_path = f"{m_dir}/gemma-4-31B-it-qat-UD-Q4_K_XL.gguf"
    mtp_path = f"{m_dir}/gemma-4-31B-it-Q4_0-MTP.gguf"
    mmproj_path = f"{v_dir}/gemma-4-31B-it-qat-UD-Q4_K_XL-mmproj-BF16.gguf"
    extra_args = f"-md {mtp_path} --spec-type draft-mtp --spec-draft-n-max 3"
elif model_key == "qwen27":
    model_path = f"{m_dir}/Qwen3.6-27B-UD-Q4_K_XL.gguf"
    mmproj_path = f"{v_dir}/qwen3.6-mmproj-F16.gguf"
elif model_key == "qwencoder30":
    model_path = f"{m_dir}/Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf"
elif model_key == "qwopus":
    model_path = f"{m_dir}/Qwopus3.6-27B-v2-MTP-Q5_K_M.gguf"
elif model_key == "qwencodernext":
    model_path = f"{m_dir}/Qwen3-Coder-Next-UD-Q4_K_XL.gguf"
    mmproj_path = f"{v_dir}/Qwen3-Coder-Next-UD-Q4_K_XL-mmproj-BF16.gguf"
    extra_args = "--no-mmap"
else:
    print(f"Error: Unknown model key assignment '{model_key}'.")
    sys.exit(1)

print(json.dumps({
    "model_path": model_path,
    "mtp_path": mtp_path,
    "mmproj_path": mmproj_path,
    "extra_args": extra_args
}))
```

### Strategy_Injector >> Runtime_State

Applies runtime profile data parameters and hooks the vision projector layer if requested and available. Context size and GPU layer count are no longer sourced from the profile by default — they stay `null` (and therefore omitted from the final command) unless the caller explicitly passed `--ctx` / `--ngl`, so llama.cpp auto-fits both against the model and available VRAM.

```python
import sys
import json
import os

profile_name = Runtime_State['profile_name']
vision_toggle = Runtime_State['vision_toggle']
mmproj_path = Runtime_State['mmproj_path']
extra_args = Runtime_State['extra_args']
ctx_override = Runtime_State['ctx_override']
ngl_override = Runtime_State['ngl_override']

if profile_name == "speed":
    prof = Speed_Profile
elif profile_name == "accuracy":
    prof = Accuracy_Profile
elif profile_name == "space":
    prof = Space_Profile
else:
    print(f"Error: Unknown profile name '{profile_name}'.")
    sys.exit(1)

k_type = prof['k_type']
v_type = prof['v_type']
batch = prof['batch']

# ctx/ngl are override-only: omitted (null) unless the caller asked for a
# specific value. A null here means the flag is left off the invocation
# entirely, so llama.cpp auto-fits.
ctx = ctx_override
ngl = ngl_override

if ctx_override is not None:
    print(f">>> Context override: forcing --ctx-size {ctx_override}", file=sys.stderr)
if ngl_override is not None:
    print(f">>> GPU layer override: forcing --n-gpu-layers {ngl_override}", file=sys.stderr)

if vision_toggle == "vision_on":
    if mmproj_path and os.path.exists(mmproj_path):
        print(">>> Vision active: Injecting multimodal matrix mapping", file=sys.stderr)
        extra_args += f" --mmproj {mmproj_path}"
    else:
        print(">>> Warning: Vision requested, but model choice lacks matching project block.", file=sys.stderr)

print(json.dumps({
    "ctx": ctx,
    "ngl": ngl,
    "k_type": k_type,
    "v_type": v_type,
    "batch": batch,
    "extra_args": extra_args
}))
```

### Runtime_Invocation

Fires the optimized compute loop cleanly onto target hardware execution threads.

```bash
BIN=$(echo "$Environment_Paths" | jq -r '.llama_bin')
HOST=$(echo "$Environment_Paths" | jq -r '.host')
PORT=$(echo "$Environment_Paths" | jq -r '.port')

MODEL_PATH=$(echo "$Runtime_State" | jq -r '.model_path')
CTX=$(echo "$Runtime_State" | jq -r '.ctx')
NGL=$(echo "$Runtime_State" | jq -r '.ngl')
BATCH=$(echo "$Runtime_State" | jq -r '.batch')
K_TYPE=$(echo "$Runtime_State" | jq -r '.k_type')
V_TYPE=$(echo "$Runtime_State" | jq -r '.v_type')
EXTRA_ARGS=$(echo "$Runtime_State" | jq -r '.extra_args')

# ctx/ngl are only added to the invocation when explicitly overridden
# (--ctx / --ngl). Left unset, llama.cpp auto-fits context and GPU
# layer count against the model and available VRAM.
CTX_ARG=()
if [ "$CTX" != "null" ] && [ -n "$CTX" ]; then
  CTX_ARG=(--ctx-size "$CTX")
fi

NGL_ARG=()
if [ "$NGL" != "null" ] && [ -n "$NGL" ]; then
  NGL_ARG=(--n-gpu-layers "$NGL")
fi

echo -e "\n>>> Invoking llama.cpp:"
echo "nice -n 15 $BIN --model $MODEL_PATH ${CTX_ARG[*]} --parallel 1 ${NGL_ARG[*]} --batch-size $BATCH --cache-type-k $K_TYPE --cache-type-v $V_TYPE --flash-attn on --jinja --host $HOST --port $PORT $EXTRA_ARGS"
echo

read -p ">>> Press enter to fire this invocation... " _ < /dev/tty

nice -n 15 "$BIN" \
  --model "$MODEL_PATH" \
  "${CTX_ARG[@]}" \
  --parallel 1 \
  "${NGL_ARG[@]}" \
  --batch-size "$BATCH" \
  --cache-type-k "$K_TYPE" \
  --cache-type-v "$V_TYPE" \
  --flash-attn on \
  --jinja \
  --host "$HOST" \
  --port "$PORT" \
  $EXTRA_ARGS
```

## 5. Workflow Manifest

### Steps

1. `Argument_Parser` => `Model_Resolver` => `Strategy_Injector` => `Runtime_Invocation`

---

### Key Upgrades in this Design:
* **Named Arguments:** CLI inputs are `--model`, `--profile`, `--vision`/`--no-vision`, `--ctx`, `--ngl` — no more positional ordering to remember.
* **Auto-Fit by Default:** `--ctx-size` and `--n-gpu-layers` are omitted from the `llama-server` invocation unless you explicitly pass `--ctx N` or `--ngl N`. Left alone, llama.cpp auto-fits both against the model and available VRAM. Profiles still govern `batch`/`k_type`/`v_type`.
* **Vision Isolation Control:** The `Strategy_Injector` evaluates if you asked for `--vision`. If you choose a model that supports it (like `gemma31`), it appends `--mmproj`. If you choose a model without vision (like `qwencoder30`), it safely ignores the flag and keeps resource usage low.
* **MTP Auto-Linking:** Choosing `gemma26` or `gemma31` automatically hooks their respective companion MTP files (`-md`) into the launch command arguments for a zero-effort performance increase.
* **Dynamic Variable Substitution:** Cleanly splits files across your project architecture paths while maintaining simple cognitive buckets that align with how your memory organizes information.

## 6. Llama.cpp Parameter Reference

The `Runtime_Invocation` block executes `llama-server` using several optimized arguments. Here is the rationale based on the `llama.cpp` documentation:

*   **`--model FNAME`**: The main model path to load.
*   **`--ctx-size N`**: Size of the prompt context. **Omitted by default** — only added when `--ctx N` is passed on the CLI. Without it, llama.cpp auto-fits context size against the model and available VRAM.
*   **`--parallel 1`**: Sets the number of server slots to 1. Optimized for single-user, heavy reasoning batch processing.
*   **`--n-gpu-layers N`**: Max number of layers to store in VRAM. **Omitted by default** — only added when `--ngl N` is passed on the CLI. Without it, llama.cpp auto-fits GPU offload.
*   **`--batch-size N`**: Logical maximum batch size for prompt processing (dynamically controlled by Profile).
*   **`--cache-type-k TYPE` / `--cache-type-v TYPE`**: KV cache data types. We scale these between `q4_0` and `f16` depending on the Profile to manage VRAM footprint vs accuracy.
*   **`--flash-attn on`**: Hard-coded to enabled. Flash Attention significantly reduces memory bandwidth requirements during long context generation.
*   **`--jinja`**: Forces the use of the model's native Jinja template engine for proper chat formatting.
*   **`--host HOST` / `--port PORT`**: Network binding addresses, controlled by the `Environment_Paths` JSON.

### Optional Extra Arguments (Injected dynamically)

*   **`--mmproj FILE`**: Path to a multimodal projector file. Automatically appended if `--vision` is passed and the model supports it.
*   **`-md FNAME`** (formerly `--model-draft`): The draft model path used for speculative decoding (MTP).
*   **`--spec-type draft-mtp`**: Instructs the server to use the Multi-Token Prediction (MTP) speculative decoding method designed for architectures like Gemma.
*   **`--spec-draft-n-max 3`**: Maximum number of draft tokens to propose per step (set to 3 for stable acceptance rates).
*   **`--no-mmap`**: Forces the full model file to be read into memory upfront instead of memory-mapped and paged in lazily. `Model_Resolver` sets this automatically for Tier 2 spillover models to keep host-memory offload behavior deterministic; it's deliberately withheld from Tier 1 models, which fit in VRAM and benefit from mmap's faster reload and lower peak RAM use.
