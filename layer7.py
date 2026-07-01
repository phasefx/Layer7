#!/usr/bin/env python3
# =============================================================================
# LAYER 7 ENGINE (v0.8)
# =============================================================================
# Main orchestrator.
# Ties together Core Structure, Addressing, Flow Control, and Language
# Integration.
#
# This file mirrors the Table of Contents of Layer7_Design.md:
#   core_structure.py     → Section 1 (parsing)
#   addressing.py         → Section 2 (namespacing)
#   flow_control.py       → Section 3 (compositions)
#   language_integration.py → Section 4 (polyglot execution)
#   layer7.py (this file) → the glue

import argparse
import sys
import json
import os
import re

from core_structure import Layer7Parser
from addressing import AddressResolver
from flow_control import CompositionEngine
from language_integration import (
    MCPDispatcher,
    ExecutionResult,
    build_state,
    get_arrow_input_data,
    apply_arrow_output,
)

# Optional YAML support (pip install pyyaml)
try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None  # type: ignore


def parse_data_blocks(nodes):
    """Ensure YAML missing warning is shown when yaml blocks are present.

    (JSON/YAML data parsing now happens inside Layer7Parser for both
    linear and MCP paths. This only surfaces the actionable warning.)
    """
    for node in nodes:
        if not node.code_content:
            continue
        lang = (node.code_lang or "").lower()
        if lang == "yaml" and not HAS_YAML:
            print("[Warning] YAML data block encountered but PyYAML not installed. "
                  "pip install pyyaml to enable.")
            # Only warn once per doc even if multiple yaml blocks
            return


# ─── Linear execution ───────────────────────────────────────────────────────
# Uses shared build_state / arrow helpers from language_integration.

def execute_linear(all_nodes, dispatcher, resolver, program_stdin="", silent=False):
    """Default baseline flow: top to bottom.

    For each node in document order:

    1. **Data blocks** (JSON/YAML) → parsed into ``node.data_value``
    2. **Function-shaped blocks** → registered as callables, *skipped*
    3. **Composition blocks** → executed via the CompositionEngine inline
    4. **Regular code blocks** → executed with full preamble + arrow wiring
    """
    stdin_consumed = False

    for node in all_nodes:
        if not node.code_content:
            continue

        lang = (node.code_lang or "").lower()

        # Data blocks are already parsed upfront via parse_data_blocks()
        if lang in ("json", "yaml"):
            continue

        # ── Function-shaped blocks: register, don't execute ──────────
        if dispatcher.is_function_shaped(lang, node.code_content):
            print(f"  ƒ  {node.title}  ({lang} — registered as callable)")
            dispatcher.register_function(node.title, lang, node.code_content)
            continue

        # ── Composition blocks: execute inline ───────────────────────
        if lang == "composition":
            if getattr(resolver, 'strict_mode', False):
                raise SyntaxError(f"[Layer7 Strict Mode Error] Composition DSL is disabled. Header: '{node.title}'")
            print(f"  ⎈  {node.title}  (composition)")
            comp_engine = CompositionEngine(resolver, dispatcher, all_nodes)
            comp_engine.execute_composition(node.code_content)
            continue

        # ── Regular code blocks ──────────────────────────────────────

        # Build state fresh (reflects changes from all prior blocks)
        state = build_state(all_nodes)

        # Arrow wiring: INPUT  (< or <<)
        stdin_data = get_arrow_input_data(node, resolver)
        if stdin_data is None and program_stdin and not stdin_consumed:
            stdin_data = program_stdin
            stdin_consumed = True

        # Execute
        arrow_label = ""
        if node.arrow_direction and node.arrow_target:
            arrow_label = f"  {node.arrow_direction} {node.arrow_target}"
        print(f"  ▶  {node.title}  ({lang}{arrow_label})")

        # Determine if we should capture output
        capture_output = silent or (node.arrow_direction in ('>', '>>'))
        capture_stderr = capture_output or getattr(resolver, 'strict_mode', False)

        result = dispatcher.execute(
            lang, node.code_content, stdin=stdin_data, state=state, 
            capture_output=capture_output, capture_stderr=capture_stderr)

        # Arrow wiring: OUTPUT  (> or >>)
        apply_arrow_output(node, resolver, result.stdout)

        # Error propagation: non-zero exit is fatal
        if not result.success:
            if getattr(resolver, 'strict_mode', False) and node.start_line is not None:
                print(f"\n[Layer7 Error] Block: '{node.title}' (Starts at Markdown Line: {node.start_line})")
                translated_stderr = result.stderr
                if translated_stderr:
                    preamble_len = getattr(result, 'preamble_length', 0)
                    def replacer_word(match):
                        line_no = int(match.group(1))
                        if line_no > preamble_len:
                            return f"line {line_no - preamble_len + node.start_line}"
                        return match.group(0)
                    def replacer_colon(match):
                        line_no = int(match.group(1))
                        if line_no > preamble_len:
                            return f":{line_no - preamble_len + node.start_line}:"
                        return match.group(0)
                    translated_stderr = re.sub(r'line\s+(\d+)', replacer_word, translated_stderr)
                    translated_stderr = re.sub(r':(\d+):', replacer_colon, translated_stderr)
                print(f"Original Error:\n{translated_stderr}")
                print("\n--- Boundary State at Execution ---")
                for k, v in state.items():
                    try:
                        print(f"{k}: {json.dumps(v)}")
                    except Exception as e:
                        print(f"{k}: <Unserializable: {e}>")
                sys.exit(result.returncode)
            else:
                print(f"\n[Fatal] '{node.title}' exited with code"
                      f" {result.returncode}")
                # Only reprint stderr here if we captured it. In live (non-capture)
                # mode the child inherited stderr and the user already saw the
                # output as it happened.
                if result.stderr and capture_output:
                    print(result.stderr)
                sys.exit(result.returncode)

        # Print stdout for blocks that don't capture output via arrows
        if result.stdout and node.arrow_direction not in ('>', '>>') and not silent:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Layer7 Engine (v0.8) — "
                    "Polyglot Code Organization for Human Cognition")
    parser.add_argument("--serve", action="store_true", help="Start MCP server")
    parser.add_argument("--silent", action="store_true", help="Suppress live console output for commands without output arrows")
    parser.add_argument("--mode", choices=["debug", "toolkit"], help="MCP server mode")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind for SSE server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, help="Port to bind for SSE server (triggers network mode)")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode (disables fuzzy resolution)")
    parser.add_argument("file", help="The Layer7 Markdown file to execute")
    parser.add_argument("args", nargs="*",
                        help="Arguments passed through to code blocks "
                             "(e.g. an input filename)")
    args = parser.parse_args()

    if args.serve and not args.mode:
        print("Error: --serve requires --mode=debug or --mode=toolkit")
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        sys.exit(1)

    # Resolve extra positional args relative to the directory the user
    # invoked the command from. We deliberately chdir subprocesses to the
    # directory containing the .md file, so user-supplied filenames (like
    # "examples/good_tickets.json") must be turned into absolute paths so
    # they remain valid inside the child's (different) cwd.
    invocation_dir = os.getcwd()
    resolved_args = []
    for a in args.args:
        if os.path.isabs(a):
            resolved_args.append(a)
        else:
            resolved_args.append(os.path.abspath(os.path.join(invocation_dir, a)))

    program_stdin = ""
    if not args.serve and not sys.stdin.isatty():
        program_stdin = sys.stdin.read()

    if not args.serve:
        print(f"Layer7 v0.8 — {args.file}")
        print("─" * 40)

    # 1. Parse markdown file  (core_structure)
    with open(args.file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    l7_parser = Layer7Parser()
    l7_parser.raw_text = markdown_text
    root_node = l7_parser.parse_text(markdown_text)

    # Apply CLI override if present
    if getattr(args, 'strict', False):
        l7_parser.strict_mode = True

    all_nodes = l7_parser.all_nodes

    # Parse data blocks (JSON always, YAML if PyYAML present) — happens early
    # so data is available for both linear execution and MCP server modes.
    parse_data_blocks(all_nodes)

    # 2. Register addresses  (addressing)
    resolver = AddressResolver(strict_mode=l7_parser.strict_mode)
    for node in all_nodes:
        resolver.register_node(node, filename=os.path.basename(args.file))

    # 3. Execution  (flow_control + language_integration)
    working_dir = os.path.dirname(os.path.abspath(args.file))
    dispatcher = MCPDispatcher(
        program_args=resolved_args, working_dir=working_dir)

    if args.serve:
        from mcp_registry import Layer7ToolRegistry
        registry = Layer7ToolRegistry(l7_parser, resolver, dispatcher, mode=args.mode, program_stdin=program_stdin)

        try:
            import mcp
            # Use the official SDK server if available
            from mcp_sdk_server import SDKMCPServer
            server = SDKMCPServer(registry)
        except ImportError:
            # Fallback to the dependency-free native server
            from mcp_native_server import NativeMCPServer
            server = NativeMCPServer(registry)

        if args.port is not None:
            if hasattr(server, "serve_sse"):
                server.serve_sse(args.host, args.port)
            else:
                print("Error: The native server fallback does not support SSE. Please install the official SDK (pip install mcp[cli] starlette uvicorn).")
                sys.exit(1)
        else:
            server.serve_stdio()
    else:
        # Always use linear execution.
        # Compositions execute inline at their position in the document.
        execute_linear(all_nodes, dispatcher, resolver, program_stdin=program_stdin, silent=args.silent)


if __name__ == "__main__":
    main()
