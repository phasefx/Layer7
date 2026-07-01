import json, sys
from core_structure import Layer7Parser
from language_integration import MCPDispatcher
from layer7 import build_state

with open("test_strict.md") as f:
    text = f.read()

p = Layer7Parser()
n = p.parse_text(text)
m = MCPDispatcher()
state = build_state(p.all_nodes)
print(m._generate_var_preamble("py", state))
