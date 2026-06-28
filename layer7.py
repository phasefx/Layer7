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

from core_structure import Layer7Parser
from addressing import AddressResolver
from flow_control import CompositionEngine
from language_integration import MCPDispatcher, ExecutionResult

# ─── State helpers ───────────────────────────────────────────────────────────

def build_state(nodes):
    """Collect every header variable that currently holds data.

    Called fresh before each code block execution so the state dict reflects
    all changes made by prior blocks (e.g. ``>`` arrow writes).
    """
    state = {}
    for node in nodes:
        if node.data_value is not None:
            state[node.title] = node.data_value
    return state

# ─── Linear execution ───────────────────────────────────────────────────────

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

        # ── Data blocks ──────────────────────────────────────────────
        if lang in ("json", "yaml"):
            try:
                if lang == "json":
                    node.data_value = json.loads(node.code_content)
                # YAML: add PyYAML when needed
            except Exception as e:
                print(f"[Warning] Failed to parse data at '{node.title}': {e}")
            continue

        # ── Function-shaped blocks: register, don't execute ──────────
        if dispatcher.is_function_shaped(lang, node.code_content):
            print(f"  ƒ  {node.title}  ({lang} — registered as callable)")
            dispatcher.register_function(node.title, lang, node.code_content)
            continue

        # ── Composition blocks: execute inline ───────────────────────
        if lang == "composition":
            print(f"  ⎈  {node.title}  (composition)")
            comp_engine = CompositionEngine(resolver, dispatcher, all_nodes)
            comp_engine.execute_composition(node.code_content)
            continue

        # ── Regular code blocks ──────────────────────────────────────

        # Build state fresh (reflects changes from all prior blocks)
        state = build_state(all_nodes)

        # Arrow wiring: INPUT  (< or <<)
        stdin_data = None
        if node.arrow_direction in ('<', '<<') and node.arrow_target:
            target = resolver.resolve(node.arrow_target)
            if target and target.data_value is not None:
                stdin_data = json.dumps(target.data_value)
            elif target is None:
                print(f"[Warning] Input arrow target "
                      f"'{node.arrow_target}' not found")
        elif program_stdin and not stdin_consumed:
            stdin_data = program_stdin
            stdin_consumed = True

        # Execute
        arrow_label = ""
        if node.arrow_direction and node.arrow_target:
            arrow_label = f"  {node.arrow_direction} {node.arrow_target}"
        print(f"  ▶  {node.title}  ({lang}{arrow_label})")

        # Determine if we should capture output
        capture_output = silent or (node.arrow_direction in ('>', '>>'))

        result = dispatcher.execute(
            lang, node.code_content, stdin=stdin_data, state=state, capture_output=capture_output)

        # Arrow wiring: OUTPUT  (> or >>)
        if node.arrow_direction in ('>', '>>') and node.arrow_target:
            target = resolver.resolve(node.arrow_target)
            if target is None:
                print(f"[Warning] Output arrow target "
                      f"'{node.arrow_target}' not found")
            elif result.stdout:
                try:
                    parsed = json.loads(result.stdout)
                except json.JSONDecodeError:
                    parsed = result.stdout

                if node.arrow_direction == '>':
                    # Replace
                    target.data_value = parsed
                else:
                    # Append (>>)
                    if isinstance(target.data_value, list):
                        if isinstance(parsed, list):
                            target.data_value.extend(parsed)
                        else:
                            target.data_value.append(parsed)
                    elif (isinstance(target.data_value, dict)
                          and isinstance(parsed, dict)):
                        target.data_value.update(parsed)
                    else:
                        # Can't meaningfully append — overwrite
                        target.data_value = parsed

        # Error propagation: non-zero exit is fatal
        if not result.success:
            print(f"\n[Fatal] '{node.title}' exited with code"
                  f" {result.returncode}")
            if result.stderr:
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
    all_nodes = l7_parser.all_nodes

    # 2. Register addresses  (addressing)
    resolver = AddressResolver()
    for node in all_nodes:
        resolver.register_node(node, filename=os.path.basename(args.file))

    # 3. Execution  (flow_control + language_integration)
    working_dir = os.path.dirname(os.path.abspath(args.file))
    dispatcher = MCPDispatcher(
        program_args=args.args, working_dir=working_dir)

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
