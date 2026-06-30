# Layer7

**Polyglot Code Organization for Human Cognition**

Layer7 lets you write code in whatever languages you already know, organized inside a single Markdown file. It is literate programming for humans first — especially solo hobbyists and people who benefit from skimmable, chunked, narrative-driven code.

Inspired by the Unix philosophy and the reality that humans can comfortably hold about **7** things in working memory at once.

- Version: 0.8 (Evolved)
- Status: Usable + evolving
- Primary doc: [`Layer7_Design.md`](Layer7_Design.md)

## Why Layer7?

- **Skimmable after a long break** — Markdown headers give instant structure and folding in good editors.
- **Polyglot without pain** — Mix Bash, Python, JavaScript, Perl, Ruby (more easy to add) in one file. Cross-language function calls "just work".
- **Visual dataflow** — Use arrows in headers (`<`, `>`, `<<`, `>>`) to wire data between chunks instead of temp files and shell glue.
- **7-chunk friction** — The runtime warns you when sections grow past ~7 children (you can `Allow exception:`).
- **LLM / agent friendly** — Run with `--serve` to expose every block and variable as MCP tools.

It is explicitly *not* aimed at large enterprise teams.

## Quickstart

### Prerequisites

- Python 3.10+
- The interpreters you want to use (bash, python3, node, perl, ruby are supported out of the box)
- (Optional) `pip install pyyaml` for YAML data blocks
- (Optional, for MCP server) `pip install "mcp[cli]" starlette uvicorn`

### Run an example

```bash
# Using the raffle demo (polyglot dataflow + cross-language calls)
python3 layer7.py examples/raffle.md examples/good_tickets.json

# Or pipe data
python3 layer7.py examples/raffle.md << 'JSON'
[{"name":"Alice","tickets_bought":5},{"name":"Bob","tickets_bought":12}]
JSON
```

See the raffle output a winner using Bash → Perl (with JS validator callable) → Python.

Other example:

```bash
python3 layer7.py examples/layer7llama.md gemma31 accuracy vision_on
# (custom paths in that file; demonstrates real orchestration)
```

### Run as MCP tool server (for LLMs / UIs)

```bash
python3 layer7.py --serve --mode=debug path/to/your.layer7.md
# or with network for some UIs:
python3 layer7.py --serve --mode=toolkit --port 8765 your.md
```

In debug mode initial state/args/stdin are preloaded. Toolkit mode starts empty so the LLM can seed via tools.

## Core Concepts

A Layer7 document is normal Markdown + a few powerful conventions.

### Headers are addresses + variables

```markdown
## The Tickets

```json
[]
```
```

Any later code block can see `The_Tickets`, `TheTickets`, `theTickets` etc. thanks to fuzzy addressing.

### Data blocks (JSON or YAML)

```yaml
name: Mini
mood: happy
```

```json
{ "position": { "x": 0 } }
```

Parsed into the header name and injected as native variables in subsequent code blocks.

### Code blocks

Any fenced block with a language tag runs in that interpreter with a hidden preamble:

- All current data headers injected as variables (multiple spellings)
- Stubs for any registered cross-language functions

Function-shaped blocks (top-level `def`, `function`, `sub`) are **registered** rather than executed immediately, making them callable from other languages.

### Arrows for data flow (no temp files)

```markdown
## Load Data => The Tickets

```bash
jq . "${1:-/dev/stdin}"
```

## Process <= The Tickets

```python
# "The Tickets" is already in scope or via stdin
...
```
```

- `Header => Target` or `Target <= Header` etc. — all variants of `< > << >>` with decoration are accepted.
- `>` / `=` replace
- `>>` / `==>>` append (lists or dicts)

### Compositions (optional non-linear flow)

See `Layer7_Design.md` for the `Steps` + `Routing` DSL using `SKIP` sentinels for loops/gotos.

Linear top-to-bottom is the default and often all you need.

### "Allow exception"

```markdown
Allow exception: 7-chunk
Allow exception: bash
Allow exception: cross-file reference
```

Tells the linter/runtime "I know what I'm doing."

## Shell completion

Source the provided completion scripts:

```bash
source layer7-completion.bash
# or the llama-specific one
```

## Architecture (high level)

```
layer7.py (CLI + linear exec + MCP entry)
├── core_structure.py   # parser → HeaderNode tree + data
├── addressing.py       # fuzzy name resolution
├── flow_control.py     # composition DSL (Steps + Routing)
└── language_integration.py  # preambles, cross-lang calls, execution
    └── mcp_*.py        # tool registry + stdio / SDK servers
```

Every code block gets a fresh preamble + runs in its own process. State lives in the in-memory nodes and is snapshotted to JSON for non-bash languages.

## Development / Contributing

The project is small and intentionally opinionated.

- Run examples frequently while changing code.
- Tests live in `test/` (expand them!).
- Make a commit at each natural milestone.

See `Layer7_Design.md` for the detailed spec and philosophy.

## License

No formal license yet — personal / hobby project. Use at your own risk and joy.

---

Made with ❤️ for readable, mixed-language, human-scale programs.
