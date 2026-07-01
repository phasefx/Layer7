# Layer7: Agent Strict Mode Implementation Plan

This plan outlines the steps for implementing `Mode: Strict` and agent-friendly error handling in Layer7. The goal is to provide LLM agents with a deterministic, loud-failing runtime environment that provides the exact causal feedback needed for single-turn self-correction.

## Phase 1: The Pragma and State

The document itself must declare its mode so it is self-describing.

1. **Update `core_structure.py` (Parser)**
   - Add logic to scan for the pragma `Mode: Strict` (case-insensitive) during the initial document parsing phase.
   - Attach a `strict_mode` boolean to the root `Document` or `RuntimeState` object.
2. **Update CLI (`layer7.py`)**
   - Optionally support `--strict` as a CLI override, but the primary mechanism should be the document pragma.

## Phase 2: Enforcing Determinism

Agents need strict interfaces; fuzzy magic causes hallucination loops.

1. **Update `addressing.py` (Fuzzy Resolution)**
   - When `strict_mode == True`, disable all fuzzy resolution algorithms (no case folding, no space-to-underscore coercion).
   - Require exact literal matches for header references. Throw a `ResolutionError` immediately if a reference is missing.
2. **Update `flow_control.py` (Composition DSL)**
   - When `strict_mode == True`, disable the NLP-like `Steps` and `Routing` DSL.
   - Restrict orchestration strictly to the explicit dataflow arrows (`=>`, `<<`, etc.) or linear top-to-bottom execution. Throw a `SyntaxError` if NLP routing is attempted.

## Phase 3: Source Mapping (The Tricky Part)

When a script fails, the agent must see the error mapped back to the Markdown file it actually wrote, not the temporary script executed by the runtime.

1. **Track Line Numbers (`core_structure.py`)**
   - Ensure `HeaderNode` / `CodeBlock` objects store their `start_line` and `end_line` relative to the original Markdown file.
2. **Calculate Preamble Offsets (`language_integration.py`)**
   - When generating the final executable string (preamble + user code), record the number of lines consumed by the preamble (`preamble_length`).
3. **Trace Translation (`layer7.py` / Execution Engine)**
   - When a subprocess exits with a non-zero status, catch `STDERR`.
   - Apply a regex/parser specific to the language (e.g., Python `File "...", line X`) to extract the failing line number.
   - Subtract `preamble_length` and add `block.start_line`.
   - Format the output specifically for the agent: 
     `[Layer7 Error] Block: 'Process_Data' | Markdown Line: 42 | Original Error: ...`

## Phase 4: Boundary State & Loud Failures

Silent type coercions across language boundaries (e.g., passing a Python class instance to a JSON boundary) mask the true cause of failure.

1. **Loud Boundary Serialization (`language_integration.py`)**
   - Modify the preambles (Python, Node, Ruby, etc.) to wrap the JSON serialization/deserialization steps in explicit `try/catch` blocks.
   - If a variable fails to serialize, exit immediately with a distinct error code and message: 
     `[Layer7 Boundary Error] Failed to serialize variable 'User_Input'. Type 'X' cannot cross the language boundary.`
2. **State Dumps on Failure**
   - If a block fails for *any* reason (syntax, runtime, or boundary), the Layer7 orchestrator must catch the failure and print the explicit state that was passed *into* the block.
   - Example output to append to the error:
     ```text
     --- Boundary State at Execution ---
     User_Input: {"name": "Alice", "id": 123}
     ```

---

## Tactical Execution Notes

- **Start with Phase 3 & 4 (Error Handling):** Building the error translation first is highly recommended, as it will make debugging Phase 2 much easier for the agent.
- **Language Support:** Start by implementing the preamble error-wrapping and trace translation for Python and Bash first, as they are the most common glue languages. Node/Ruby can follow.
