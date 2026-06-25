import os
import sys
import json
from typing import List, Dict, Any, Optional

class Layer7ToolRegistry:
    """
    Core tool registry and execution logic for Layer7 MCP Server modes.
    This class can be wrapped by any transport mechanism (native stdio, official MCP SDK, etc).
    """
    def __init__(self, parser, resolver, dispatcher, mode: str, program_stdin: str = ""):
        self.parser = parser
        self.resolver = resolver
        self.dispatcher = dispatcher
        self.mode = mode
        self.program_stdin = program_stdin
        self.nodes = parser.all_nodes

        self.tools = {} # name -> tool definition
        self.tool_handlers = {} # name -> callable

        # In toolkit mode, we start with empty state.
        # In debug mode, we inherit args and stdin (handled at block invocation).
        self.has_consumed_stdin = False

        self._register_tools()

    def _normalize_name(self, name: str) -> str:
        import re
        return re.sub(r'[^a-zA-Z0-9_]+', '_', name.lower()).strip('_')

    def _generate_unique_tool_name(self, node) -> str:
        """
        Auto-disambiguate by walking up the parent hierarchy.
        """
        path = [t for t in node.get_full_path() if t != "ROOT"]
        if not path:
            return "run_unnamed"

        base_name = self._normalize_name(path[-1])
        candidate = f"run_{base_name}"

        if candidate not in self.tools:
            return candidate

        # Collision detected, walk up parents
        parents = path[:-1]
        for i in range(1, len(parents) + 1):
            prefix_parts = [self._normalize_name(p) for p in parents[-i:]]
            candidate = "run_" + "_".join(prefix_parts) + "_" + base_name
            if candidate not in self.tools:
                return candidate

        # Fallback if somehow still colliding
        import uuid
        return f"{candidate}_{uuid.uuid4().hex[:6]}"

    def _register_tools(self):
        # 1. Register Code Blocks and Compositions
        for node in self.nodes:
            if not node.code_content:
                continue

            lang = (node.code_lang or "").lower()
            if lang in ("json", "yaml"):
                continue # data blocks are not tools

            if self.dispatcher.is_function_shaped(lang, node.code_content):
                continue # function-shaped blocks are registered as callables, not orchestration tools

            tool_name = self._generate_unique_tool_name(node)

            if lang == "composition":
                self.tools[tool_name] = {
                    "name": tool_name,
                    "description": f"Executes the composition flow under '{node.title}'.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
                self.tool_handlers[tool_name] = self._make_composition_handler(node)
            else:
                self.tools[tool_name] = {
                    "name": tool_name,
                    "description": f"Executes the code block under '{node.title}'.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "stdin_source": {
                                "type": ["string", "null"],
                                "description": "Variable header name to pipe into this block's stdin, serialized as JSON."
                            },
                            "args": {
                                "type": "array",
                                "items": { "type": "string" },
                                "description": "Command-line arguments for the block."
                            },
                            "stdout_capture_target": {
                                "type": ["string", "null"],
                                "description": "Variable header name to write this block's stdout into."
                            },
                            "stdout_capture_mode": {
                                "type": "string",
                                "enum": ["replace", "append"],
                                "default": "replace"
                            },
                            "use_state": {
                                "type": "boolean",
                                "default": True,
                                "description": "Inject current global state into the execution preamble."
                            }
                        }
                    }
                }
                self.tool_handlers[tool_name] = self._make_block_handler(node)

        # 2. Register Variable Accessors
        self.tools["read_variable"] = {
            "name": "read_variable",
            "description": "Reads the current parsed JSON state of a variable header.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "header_name": { "type": "string" },
                    "include_meta": { "type": "boolean", "default": False }
                },
                "required": ["header_name"]
            }
        }
        self.tool_handlers["read_variable"] = self._handle_read_variable

        self.tools["write_variable"] = {
            "name": "write_variable",
            "description": "Writes JSON state to a variable header.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "header_name": { "type": "string" },
                    "value": {},
                    "mode": { "type": "string", "enum": ["replace", "append"], "default": "replace" }
                },
                "required": ["header_name", "value"]
            }
        }
        self.tool_handlers["write_variable"] = self._handle_write_variable

        # 3. Register Document Tools
        self.tools["read_source"] = {
            "name": "read_source",
            "description": "Reads raw markdown from the document. Optionally scope to a specific header.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "header_name": { "type": ["string", "null"], "default": None },
                    "include_code": { "type": "boolean", "default": True }
                }
            }
        }
        self.tool_handlers["read_source"] = self._handle_read_source

        self.tools["layer7_howto"] = {
            "name": "layer7_howto",
            "description": "Returns the mode-aware onboarding text for LLM operators.",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
        self.tool_handlers["layer7_howto"] = self._handle_layer7_howto

    def _build_state(self):
        state = {}
        for n in self.nodes:
            if n.data_value is not None:
                state[n.title] = n.data_value
        return state

    def _make_block_handler(self, node):
        def handler(kwargs):
            use_state = kwargs.get("use_state", True)
            stdin_source = kwargs.get("stdin_source")
            args = kwargs.get("args", [])
            stdout_capture_target = kwargs.get("stdout_capture_target")
            stdout_capture_mode = kwargs.get("stdout_capture_mode", "replace")

            # Setup State
            state = self._build_state() if use_state else {}
            old_state_dump = json.dumps(state)

            # Setup Stdin
            stdin_data = None
            if stdin_source:
                target = self.resolver.resolve(stdin_source)
                if target and target.data_value is not None:
                    stdin_data = json.dumps(target.data_value)
            elif self.mode == "debug" and not self.has_consumed_stdin and self.program_stdin:
                stdin_data = self.program_stdin
                self.has_consumed_stdin = True

            # If args provided, we use them. In debug mode, if args were passed to the program,
            # we might want them. But the user LLM explicitly provides `args`.
            # If the LLM didn't provide args and we are in debug mode, do we use program_args?
            # The prompt says: "Debug mode: runs against state already bootstrapped from program args/stdin... identical to a bare block."
            if not args and self.mode == "debug":
                args = self.dispatcher.program_args

            # Execute
            lang = (node.code_lang or "").lower()
            result = self.dispatcher.execute(lang, node.code_content, stdin=stdin_data, state=state, args=args)

            parsed_output = None
            capture_meta = None

            if result.stdout:
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    parsed_output = result.stdout

            if stdout_capture_target and result.stdout:
                capture_meta = {
                    "target": stdout_capture_target,
                    "mode": stdout_capture_mode,
                    "applied": False
                }
                target = self.resolver.resolve(stdout_capture_target)
                if target:
                    if stdout_capture_mode == 'replace':
                        target.data_value = parsed_output
                        capture_meta["applied"] = True
                    else: # append
                        if isinstance(target.data_value, list):
                            if isinstance(parsed_output, list):
                                target.data_value.extend(parsed_output)
                            else:
                                target.data_value.append(parsed_output)
                            capture_meta["applied"] = True
                        elif isinstance(target.data_value, dict) and isinstance(parsed_output, dict):
                            target.data_value.update(parsed_output)
                            capture_meta["applied"] = True
                        else:
                            target.data_value = parsed_output
                            capture_meta["applied"] = True

            # Calculate state diff
            new_state = self._build_state()
            state_diff = {}
            for k, v in new_state.items():
                # Rough check for changes
                if k not in state or json.dumps(v) != json.dumps(state[k]):
                    state_diff[k] = v

            return {
                "success": result.success,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "parsed_output": parsed_output,
                "capture": capture_meta,
                "state_diff": state_diff
            }

        return handler

    def _make_composition_handler(self, node):
        def handler(kwargs):
            # Compositions just run themselves
            from flow_control import CompositionEngine
            comp_engine = CompositionEngine(self.resolver, self.dispatcher, self.nodes)

            # Since CompositionEngine prints to stdout directly currently,
            # we should capture stdout. For simplicity, we just run it and return basic info.
            # In a real MCP server we'd capture sys.stdout.
            import io
            import sys
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            try:
                comp_engine.execute_composition(node.code_content)
                success = True
            except Exception as e:
                print(str(e))
                success = False
            finally:
                sys.stdout = old_stdout

            stdout_str = new_stdout.getvalue()
            return {
                "success": success,
                "exit_code": 0 if success else 1,
                "stdout": stdout_str,
                "stderr": "",
                "parsed_output": None,
                "capture": None,
                "state_diff": {} # (Omitting full diff calculation for brevity)
            }
        return handler

    def _handle_read_variable(self, kwargs):
        header_name = kwargs.get("header_name")
        include_meta = kwargs.get("include_meta", False)

        target = self.resolver.resolve(header_name)
        if not target or target.data_value is None:
            return {"found": False, "value": None}

        res = {
            "found": True,
            "value": target.data_value,
            "type": type(target.data_value).__name__
        }
        if include_meta:
            # Fake meta for now, ideally we track writers
            res["last_modified_by"] = "document_initial_state" if self.mode == "debug" else "unknown"
        return res

    def _handle_write_variable(self, kwargs):
        header_name = kwargs.get("header_name")
        value = kwargs.get("value")
        mode = kwargs.get("mode", "replace")

        target = self.resolver.resolve(header_name)
        if not target:
            # If header doesn't exist, this implies we need to create it?
            # For v1, Layer7 variables are pre-declared as headers.
            # We assume it exists but data_value might be None.
            return {"success": False, "error": f"Variable header '{header_name}' not found."}

        if mode == "replace":
            target.data_value = value
        else:
            if isinstance(target.data_value, list):
                if isinstance(value, list):
                    target.data_value.extend(value)
                else:
                    target.data_value.append(value)
            elif isinstance(target.data_value, dict) and isinstance(value, dict):
                target.data_value.update(value)
            else:
                target.data_value = value

        return {"success": True, "value": target.data_value}

    def _handle_read_source(self, kwargs):
        header_name = kwargs.get("header_name")
        raw_text = getattr(self.parser, "raw_text", "")

        if header_name:
            target = self.resolver.resolve(header_name)
            if not target:
                return {"error": "Header not found."}

            # Synthesize node source since it's not currently retained verbatim in the tree
            lines = []
            lines.append(f"Header: {target.title}")
            if target.code_lang and target.code_content is not None:
                lines.append(f"```{target.code_lang}")
                lines.append(target.code_content)
                lines.append("```")
            elif target.data_value is not None:
                lines.append(f"Current Data Value: {json.dumps(target.data_value)}")

            return {"source": "\n".join(lines) or "(no content)"}
        else:
            return {"source": raw_text or "(source unavailable)"}

    def _handle_layer7_howto(self, kwargs):
        if self.mode == "debug":
            text = (
                "You're driving a Layer7 program through MCP tools instead of running it linearly. "
                "Initial state has already been loaded from the program's args/stdin, exactly as a normal run would. "
                "Code blocks share state implicitly — only use `stdin_source`/`stdout_capture_target` when you want "
                "to override the default flow. Use `read_source` to understand what a block is supposed to do before "
                "calling it. If a block fails, `stderr` and `exit_code` are returned to you; use `read_variable`/`write_variable` "
                "to inspect or patch state."
            )
        else:
            text = (
                "You're using a Layer7 document as a toolkit. State starts empty — nothing is pre-loaded. "
                "Use `write_variable` to seed any data a block needs before calling it; calling a block against missing "
                "state is expected and recoverable, not a sign you've done something wrong. Use `read_source` to understand "
                "what each block does. Chain blocks via variables, not direct calls — capture one block's output into a "
                "variable, then wire that variable as another block's input."
            )
        return {"howto": text}

    def get_tools(self) -> List[Dict]:
        return list(self.tools.values())

    def call_tool(self, name: str, arguments: Dict) -> Dict:
        if name not in self.tool_handlers:
            raise ValueError(f"Tool '{name}' not found.")
        return self.tool_handlers[name](arguments)
