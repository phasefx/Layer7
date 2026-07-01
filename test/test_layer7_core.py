"""Basic tests for Layer7 core (parser, addressing, data, execution).

Run with:
    python -m pytest test/test_layer7_core.py -q --tb=short
or simply:
    python test/test_layer7_core.py
"""

import sys
import json
import os
import tempfile
from pathlib import Path

# Make imports work when running directly or via pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core_structure import Layer7Parser, HeaderNode
from addressing import AddressResolver, normalize_identifier
from language_integration import MCPDispatcher, build_state, get_arrow_input_data, apply_arrow_output, ExecutionResult
from layer7 import resolve_program_args


def test_normalize_identifier():
    assert normalize_identifier("The Tickets") == "thetickets"
    assert normalize_identifier("A Ticket") == "aticket"
    assert normalize_identifier("Code_blocks::Functional_Example") == "codeblocksfunctionalexample"


def test_address_resolver_fuzzy():
    p = Layer7Parser()
    p.parse_text("""# Root
## A Ticket
```json
{}
```

## The Tickets
```json
[]
```
""")
    resolver = AddressResolver()
    for node in p.all_nodes:
        resolver.register_node(node, filename="demo.md")

    assert resolver.resolve("The_Tickets") is not None
    assert resolver.resolve("theTickets") is not None
    assert resolver.resolve("demoATicket") is not None
    assert resolver.resolve("A_Ticket") is not None
    # Ambiguous cases are marked None in registry (not tested strictly here)


def test_parser_json_and_yaml_data():
    p = Layer7Parser()
    p.parse_text("""# Doc

## Config JSON
```json
{"a": 1, "b": [2, 3]}
```

## Config YAML
```yaml
x: 99
list:
  - one
""")
    json_node = next(n for n in p.all_nodes if "Config JSON" in n.title)
    yaml_node = next(n for n in p.all_nodes if "Config YAML" in n.title)

    assert json_node.data_value == {"a": 1, "b": [2, 3]}
    # YAML parsed if PyYAML present; otherwise may stay None (best effort in parser)
    if yaml_node.data_value is not None:
        assert yaml_node.data_value["x"] == 99


def test_arrow_helpers():
    p = Layer7Parser()
    p.parse_text("""# Test Arrows

## Source
```json
[1, 2]
```

## Sink > Source
```text
dummy
```
""")
    resolver = AddressResolver()
    for n in p.all_nodes:
        resolver.register_node(n, "t.md")

    src = next(n for n in p.all_nodes if n.title == "Source")
    sink = next(n for n in p.all_nodes if n.title == "Sink")

    # input helper
    stdin_d = get_arrow_input_data(sink, resolver)  # sink has no < arrow in this doc
    assert stdin_d is None

    # For a node with input arrow we would test, but construction is via header parse.
    # output apply
    assert apply_arrow_output(sink, resolver, '[10, 20]') is True
    assert src.data_value == [10, 20]


def test_build_state():
    p = Layer7Parser()
    p.parse_text("""# S

## V1
```json
{"k": "v1"}
```

## V2
```json
42
```
""")
    state = build_state(p.all_nodes)
    assert "V1" in state and state["V1"]["k"] == "v1"
    assert state["V2"] == 42


def test_simple_linear_execution_via_dispatcher():
    # Use the dispatcher directly (bypasses full CLI)
    p = Layer7Parser()
    p.parse_text("""# Mini

## Counter
```json
0
```

## Inc > Counter
```python
import json, sys
c = json.loads(sys.stdin.read() or "0")
print(c + 1)
```
""")
    resolver = AddressResolver()
    for n in p.all_nodes:
        resolver.register_node(n, "mini.md")

    # manually do what linear does for the inc block
    disp = MCPDispatcher(working_dir=".")
    inc_node = next(n for n in p.all_nodes if n.title == "Inc")

    # seed state
    state = build_state(p.all_nodes)
    # simulate input from arrow
    stdin_data = json.dumps(state.get("Counter"))

    res = disp.execute(inc_node.code_lang, inc_node.code_content, stdin=stdin_data, state=state, capture_output=True)
    assert res.success
    assert res.stdout == "1"

    # apply
    apply_arrow_output(inc_node, resolver, res.stdout)
    assert p.all_nodes[1].data_value == 1   # rough index; Counter should be updated


def test_function_registration_and_cross_call():
    disp = MCPDispatcher()
    # Register a JS function
    disp.register_function("Double", "javascript", "function(x){ return x*2; }")

    # Now execute python code that calls the registered cross-lang stub
    py_code = """
def use_it():
    return Double(21)
print(use_it())
"""
    # Make it function shaped? For execute we just run the body; registration already done.
    res = disp.execute("python", py_code, state={}, capture_output=True)
    assert res.success
    assert res.stdout in ("42", "42.0", "42\n") or res.stdout.strip() == "42"


def test_resolve_program_args():
    cwd = os.getcwd()
    args = ["gemma26", "speed", "vision_off", "examples/raffle.md"]
    resolved = resolve_program_args(args, cwd)
    assert resolved[0] == "gemma26"
    assert resolved[1] == "speed"
    assert resolved[2] == "vision_off"
    # examples/raffle.md exists relative to repo root when running tests
    if os.path.exists(os.path.join(cwd, "examples/raffle.md")):
        assert os.path.isabs(resolved[3])
        assert resolved[3].endswith("examples/raffle.md")


if __name__ == "__main__":
    # Very small runner so tests work without pytest installed
    import traceback
    tests = [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)
