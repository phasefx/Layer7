#!/usr/local/bin/layer7

# Layer7 Model Engine & Inventory
Polyglot Specification for Local LLM Execution on Ampere (RTX 3090)

**Version:** 1.1
**Date:** 2026-06-27
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
* *Strategy:* Requires `--no-mmap` exclusion to allow kernel Unified Memory fault tracking across the PCIe lanes.

## 3. Operational Profiles

Configuring data tables for specific processing footprints.

### Speed_Profile

Maximizes output velocity by scaling down KV context precision to free up GPU calculation registers.

```JSON
{
  "ctx": 65536,
  "k_type": "q4_0",
  "v_type": "q4_0",
  "batch": 4096
}
```

### Accuracy_Profile

Maintains strict reference precision at the cost of VRAM footprint. Best for complex code bases or zero-shot extraction parsing.

```JSON
{
  "ctx": 32768,
  "k_type": "f16",
  "v_type": "f16",
  "batch": 2048
}
```

### Space_Profile

Aggressive constraint scaling designed to isolate the background execution footprint during concurrent system use.

```JSON
{
  "ctx": 16384,
  "k_type": "q4_0",
  "v_type": "q4_0",
  "batch": 512
}
```

## 4. Orchestration Engine

The executable glue layers mapping Layer7 variable definitions into native system memory calls.

### Runtime_State {}

### Argument_Parser > Runtime_State

Translates incoming CLI inputs into structured environment parameters.

```python
import sys
import json

if len(sys.argv) < 3:
    print("Usage: layer7 layer7llama.md <model_key> <profile> [vision_on|vision_off]", file=sys.stderr)
    print("Example: layer7 layer7llama.md gemma31 accuracy vision_on", file=sys.stderr)
    sys.exit(1)

model_key = sys.argv[1].lower()
profile_name = sys.argv[2].lower()
vision_toggle = sys.argv[3].lower() if len(sys.argv) > 3 else "vision_off"

print(json.dumps({
    "model_key": model_key,
    "profile_name": profile_name,
    "vision_toggle": vision_toggle
}))
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

Applies runtime profile data parameters and hooks the vision projector layer if requested and available.

```python
import sys
import json
import os

profile_name = Runtime_State['profile_name']
vision_toggle = Runtime_State['vision_toggle']
mmproj_path = Runtime_State['mmproj_path']
extra_args = Runtime_State['extra_args']

if profile_name == "speed":
    prof = Speed_Profile
elif profile_name == "accuracy":
    prof = Accuracy_Profile
elif profile_name == "space":
    prof = Space_Profile
else:
    print(f"Error: Unknown profile name '{profile_name}'.")
    sys.exit(1)

ctx = prof['ctx']
k_type = prof['k_type']
v_type = prof['v_type']
batch = prof['batch']

if vision_toggle == "vision_on":
    if mmproj_path and os.path.exists(mmproj_path):
        print(">>> Vision active: Injecting multimodal matrix mapping", file=sys.stderr)
        extra_args += f" --mmproj {mmproj_path}"
    else:
        print(">>> Warning: Vision requested, but model choice lacks matching project block.", file=sys.stderr)

print(json.dumps({
    "ctx": ctx,
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
BATCH=$(echo "$Runtime_State" | jq -r '.batch')
K_TYPE=$(echo "$Runtime_State" | jq -r '.k_type')
V_TYPE=$(echo "$Runtime_State" | jq -r '.v_type')
EXTRA_ARGS=$(echo "$Runtime_State" | jq -r '.extra_args')

echo -e "\n>>> Invoking llama.cpp:"
echo "nice -n 15 $BIN --model $MODEL_PATH --ctx-size $CTX --parallel 1 --n-gpu-layers 100 --batch-size $BATCH --cache-type-k $K_TYPE --cache-type-v $V_TYPE --flash-attn on --jinja --host $HOST --port $PORT $EXTRA_ARGS"
echo

nice -n 15 "$BIN" \
  --model "$MODEL_PATH" \
  --ctx-size "$CTX" \
  --parallel 1 \
  --n-gpu-layers 100 \
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
* **Vision Isolation Control:** The `Strategy_Injector` evaluates if you asked for `vision_on`. If you choose a model that supports it (like `gemma31`), it appends `--mmproj`. If you choose a model without vision (like `qwencoder30`), it safely ignores the flag and keeps resource usage low.
* **MTP Auto-Linking:** Choosing `gemma26` or `gemma31` automatically hooks their respective companion MTP files (`--speculative-model`) into the launch command arguments for a zero-effort performance increase.
* **Dynamic Variable Substitution:** Cleanly splits files across your project architecture paths while maintaining simple cognitive buckets that align with how your memory organizes information.
