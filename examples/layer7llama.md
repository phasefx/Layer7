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

### Argument_Parser

Translates incoming CLI inputs into structured environment parameters.

```Bash
MODEL_KEY="${1,,}"
PROFILE_NAME="${2,,}"
VISION_TOGGLE="${3,,:-vision_off}"

# Set paths from Layer7 configuration targets
BIN=$Environment_Paths.llama_bin
M_DIR=$Environment_Paths.models_dir
V_DIR=$Environment_Paths.mmproj_dir

EXTRA_ARGS=""
```

### Model_Resolver

Resolves shorthand keys into exact target paths, speculative configurations, and matching multimodal project tracks.

```Bash
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
        echo "Error: Unknown model key assignment."
        exit 1
        ;;
esac

```

### Strategy_Injector

Applies runtime profile data parameters and hooks the vision projector layer if requested and available.

```Bash
case "$PROFILE_NAME" in
    "speed")
        CTX=$Speed_Profile.ctx
        K_TYPE=$Speed_Profile.k_type
        V_TYPE=$Speed_Profile.v_type
        BATCH=$Speed_Profile.batch
        ;;
    "accuracy")
        CTX=$Accuracy_Profile.ctx
        K_TYPE=$Accuracy_Profile.k_type
        V_TYPE=$Accuracy_Profile.v_type
        BATCH=$Accuracy_Profile.batch
        ;;
    "space")
        CTX=$Space_Profile.ctx
        K_TYPE=$Space_Profile.k_type
        V_TYPE=$Space_Profile.v_type
        BATCH=$Space_Profile.batch
        ;;
esac

# Evaluate Multimodal vision request rules
if [ "$VISION_TOGGLE" = "vision_on" ]; then
    if [ -n "$MMPROJ_PATH" ] && [ -f "$MMPROJ_PATH" ]; then
        echo ">>> Vision active: Injecting multimodal matrix mapping"
        EXTRA_ARGS="$EXTRA_ARGS --mmproj $MMPROJ_PATH"
    else
        echo ">>> Warning: Vision requested, but model choice lacks matching project block."
    fi
fi

```

### Runtime_Invocation

Fires the optimized compute loop cleanly onto target hardware execution threads.

```Bash
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
  --host $Environment_Paths.host \
  --port $Environment_Paths.port \
  $EXTRA_ARGS

```

## 5. Workflow Manifest

### Steps

1. `Argument_Parser` => `Model_Resolver` => `Strategy_Injector` => `Runtime_Invocation`

```

---

### Key Upgrades in this Design:
* **Vision Isolation Control:** The `Strategy_Injector` evaluates if you asked for `vision_on`. If you choose a model that supports it (like `gemma31`), it appends `--mmproj`. If you choose a model without vision (like `qwencoder30`), it safely ignores the flag and keeps resource usage low.
* **MTP Auto-Linking:** Choosing `gemma26` or `gemma31` automatically hooks their respective companion MTP files (`--speculative-model`) into the launch command arguments for a zero-effort performance increase.
* **Dynamic Variable Substitution:** Cleanly splits files across your project architecture paths while maintaining simple cognitive buckets that align with how your memory organizes information.

