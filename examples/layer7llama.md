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

### Usage_Guard

Ensures the script is invoked with all required arguments.

```Bash
if [ "$#" -lt 2 ]; then
    echo "Error: Missing required arguments." >&2
    echo "" >&2
    echo "Usage: layer7 layer7llama.md <model_key> <profile> [vision_on|vision_off]" >&2
    echo "" >&2
    echo "Available Models (model_key):" >&2
    echo "  - gemma26       (Gemma 4 26B QAT)" >&2
    echo "  - gemma31       (Gemma 4 31B QAT)" >&2
    echo "  - qwen27        (Qwen 3.6 27B)" >&2
    echo "  - qwencoder30   (Qwen 3 Coder 30B)" >&2
    echo "  - qwopus        (Qwopus 3.6 27B MTP)" >&2
    echo "  - qwencodernext (Qwen 3 Coder Next 47GB)" >&2
    echo "" >&2
    echo "Available Profiles (profile):" >&2
    echo "  - speed         (64k context, Q4_0 KV)" >&2
    echo "  - accuracy      (32k context, F16 KV)" >&2
    echo "  - space         (16k context, Q4_0 KV, low batch)" >&2
    exit 1
fi
```

#### Llama_Runner

Resolves variables and executes the local llama-server instance.

```Bash
# Helper function to parse JSON variables injected by the Layer7 engine
get_l7_var() {
    python3 -c "import json, os; print(json.loads(os.environ.get('$1', '{}')).get('$2', ''))"
}

# 1. Parse Arguments
MODEL_KEY="${1,,}"
PROFILE_NAME="${2,,}"
VISION_TOGGLE="${3,,:-vision_off}"

# 2. Extract paths from Environment_Paths target
BIN=$(get_l7_var Environment_Paths llama_bin)
M_DIR=$(get_l7_var Environment_Paths models_dir)
V_DIR=$(get_l7_var Environment_Paths mmproj_dir)
HOST=$(get_l7_var Environment_Paths host)
PORT=$(get_l7_var Environment_Paths port)

# 3. Model Resolver
case "$MODEL_KEY" in
    "gemma26")
        MODEL_PATH="$M_DIR/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf"
        MTP_PATH="$M_DIR/gemma-4-26B-A4B-it-Q4_0-MTP.gguf"
        MMPROJ_PATH="$V_DIR/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL-mmproj-BF16.gguf"
        EXTRA_ARGS="--speculative-model $MTP_PATH --spec-type draft-mtp --spec-draft-n-max 3"
        ;;
    "gemma31")
        MODEL_PATH="$M_DIR/gemma-4-31B-it-qat-UD-Q4_K_XL.gguf"
        MTP_PATH="$M_DIR/gemma-4-31B-it-Q4_0-MTP.gguf"
        MMPROJ_PATH="$V_DIR/gemma-4-31B-it-qat-UD-Q4_K_XL-mmproj-BF16.gguf"
        EXTRA_ARGS="--speculative-model $MTP_PATH --spec-type draft-mtp --spec-draft-n-max 3"
        ;;
    "qwen27")
        MODEL_PATH="$M_DIR/Qwen3.6-27B-UD-Q4_K_XL.gguf"
        MMPROJ_PATH="$V_DIR/qwen3.6-mmproj-F16.gguf"
        ;;
    "qwencoder30")
        MODEL_PATH="$M_DIR/Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf"
        MMPROJ_PATH=""
        ;;
    "qwopus")
        MODEL_PATH="$M_DIR/Qwopus3.6-27B-v2-MTP-Q5_K_M.gguf"
        MMPROJ_PATH=""
        ;;
    "qwencodernext")
        MODEL_PATH="$M_DIR/Qwen3-Coder-Next-UD-Q4_K_XL.gguf"
        MMPROJ_PATH="$V_DIR/Qwen3-Coder-Next-UD-Q4_K_XL-mmproj-BF16.gguf"
        ;;
    *)
        echo "Error: Unknown model key assignment '$MODEL_KEY'." >&2
        exit 1
        ;;
esac

# 4. Strategy Injector
case "$PROFILE_NAME" in
    "speed")
        CTX=$(get_l7_var Speed_Profile ctx)
        K_TYPE=$(get_l7_var Speed_Profile k_type)
        V_TYPE=$(get_l7_var Speed_Profile v_type)
        BATCH=$(get_l7_var Speed_Profile batch)
        ;;
    "accuracy")
        CTX=$(get_l7_var Accuracy_Profile ctx)
        K_TYPE=$(get_l7_var Accuracy_Profile k_type)
        V_TYPE=$(get_l7_var Accuracy_Profile v_type)
        BATCH=$(get_l7_var Accuracy_Profile batch)
        ;;
    "space")
        CTX=$(get_l7_var Space_Profile ctx)
        K_TYPE=$(get_l7_var Space_Profile k_type)
        V_TYPE=$(get_l7_var Space_Profile v_type)
        BATCH=$(get_l7_var Space_Profile batch)
        ;;
    *)
        echo "Error: Unknown profile name '$PROFILE_NAME'." >&2
        exit 1
        ;;
esac

# Evaluate Multimodal vision request rules
if [ "$VISION_TOGGLE" = "vision_on" ]; then
    if [ -n "$MMPROJ_PATH" ] && [ -f "$MMPROJ_PATH" ]; then
        echo ">>> Vision active: Injecting multimodal matrix mapping" >&2
        EXTRA_ARGS="$EXTRA_ARGS --mmproj $MMPROJ_PATH"
    else
        echo ">>> Warning: Vision requested, but model choice lacks matching project block." >&2
    fi
fi

# 5. Runtime Invocation
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

1. `Usage_Guard` => `Llama_Runner`

```

---

### Key Upgrades in this Design:
* **Vision Isolation Control:** The `Strategy_Injector` evaluates if you asked for `vision_on`. If you choose a model that supports it (like `gemma31`), it appends `--mmproj`. If you choose a model without vision (like `qwencoder30`), it safely ignores the flag and keeps resource usage low.
* **MTP Auto-Linking:** Choosing `gemma26` or `gemma31` automatically hooks their respective companion MTP files (`--speculative-model`) into the launch command arguments for a zero-effort performance increase.
* **Dynamic Variable Substitution:** Cleanly splits files across your project architecture paths while maintaining simple cognitive buckets that align with how your memory organizes information.

