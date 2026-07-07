# PRIMER: Layer7 Polyglot Orchestration
*For LLM agents authoring and executing Layer7 documents*

---

## 0. Always Start With This

```
Mode: Strict
```

Put this on the first non-blank line of every Layer7 document you write. It enables exact-match naming, disables the NLP composition DSL, and makes errors loud and debuggable. The rest of this primer assumes strict mode.

---

## 1. The Core Mental Model

**Data lives in the Headers. Code lives in the blocks.**

Unlike a standard script where variables live inside the code, in Layer7 headers *are* variables:

- `## User_Database` is a variable named `User_Database`
- `## Results {}` is a variable named `Results`, initialized to an empty object
- `## Items []` is a variable named `Items`, initialized to an empty array

Code blocks are stateless processors. They read from headers, do work, write back to headers. The headers are the shared memory. The blocks are the functions.

---

## 2. Automatic State Injection (The Preamble)

You do **not** need to manually load JSON or parse environment variables for header data.

When a block runs, the engine injects a hidden preamble that pre-declares all current header values as native variables:

| Language | How headers arrive | Access example |
| :--- | :--- | :--- |
| **Python** | Native dicts/lists/values | `User_Database['name']` |
| **JavaScript** | Native objects/arrays | `User_Database.name` |
| **Perl** | Native hashref/arrayref | `$User_Database->{name}` |
| **Ruby** | Native hash/array | `User_Database['name']` |
| **Bash** | JSON strings in variables | `echo "$User_Database" \| jq -r '.name'` |

Bash cannot natively decode JSON — use `jq` or pass the variable to Python/Perl for processing.

---

## 3. Data Flow: Redirection Arrows

To move data between blocks, add arrows to the header line. Input and output arrows can appear **on the same header simultaneously**:

```
## Block_Name <=== Source_Header ===> Target_Header
```

- **Input arrow (`<===`)**: pipes `Source_Header`'s current value into this block's **STDIN**
- **Output arrow (`===>`**): captures this block's **STDOUT** and writes it into `Target_Header`

**Critical rule:** if you want a block's result to be available to later blocks, you **must** use an output arrow. Without one, stdout is printed and discarded.

Append semantics: `===>>` appends to an array or merges into an object instead of replacing.

### Language output protocols

For the engine to capture your output arrow correctly, stdout must be valid JSON:

| Language | Read from input arrow | Write to output arrow |
| :--- | :--- | :--- |
| **Python** | `data = json.loads(sys.stdin.read())` | `print(json.dumps(result))` |
| **JavaScript** | `require('fs').readFileSync('/dev/stdin','utf8')` (or `readFileSync(0,'utf8')`) | `console.log(JSON.stringify(result))` |
| **Bash** | `cat` or `read` from stdin | `echo '{"key":"value"}'` |
| **Perl** | `my $in = do { local $/; <STDIN> };` | `print encode_json($result)` |

---

## 4. Cross-Language Function Calls

A block containing **only** a single function definition is registered as a callable, not executed directly.

```javascript
// ## Validate_Ticket
function(ticket) {
    return typeof ticket.name === "string" && typeof ticket.tickets_bought === "number";
}
```

To call it from another language, use the **header name** (not the internal function name):

```perl
# In a Perl block — Validate_Ticket is injected as a native subroutine
if (!Validate_Ticket($ticket)) { die "Invalid ticket"; }
```

```python
# In a Python block
if not Validate_Ticket(ticket):
    raise ValueError("Invalid ticket")
```

> **Naming rule:** Layer7 normalizes header names to underscores. `## My Function` becomes `My_Function`, `## Validate Ticket` becomes `Validate_Ticket`. Use the underscore form in all code references.

The engine wraps the function and generates language-appropriate stubs automatically. You call the header name; the engine handles serialization across the language boundary.

---

## 5. Linear Execution and the `SKIP` Sentinel

In strict mode, execution is **top to bottom**. Blocks execute in document order unless a block outputs the exact string `SKIP`, which exits the current composition early.

For loops and branching: **write them inside a code block** using the host language's native control flow. A Python `for` loop inside one block is simpler, more debuggable, and more reliable than trying to orchestrate looping at the document level.

```python
# Do this — loop inside the block
results = []
for item in Items:
    results.append(process(item))
print(json.dumps(results))
```

---

## 6. Structure and Friction

**7-Chunk Rule:** If a section has more than 7 sub-headers, consider splitting the file or refactoring. This applies to LLM authors too — a block that does 12 things is harder to debug than two blocks that do 6 things each.

**`Allow exception:`**: if you genuinely need more than 7 items somewhere, add this pragma on the line before the offending header:

```
Allow exception: large configuration object
## Many_Keys {}
```

The runtime will suppress the friction warning. The justification is for future readers, including yourself.

---

## 7. Standard Document Architecture

Follow this structure for reliable Layer7 programs:

```markdown
Mode: Strict

## 1. Configuration
### Config {}
(JSON block with settings)

## 2. State
### Results []
### Errors []

## 3. Ingestion
### Load_Data ===> Raw_Input
(bash/python block that reads external data and writes to state)

## 4. Processing  
### Process_Data <=== Raw_Input ===> Results
(python/JS block that transforms data)

## 5. Output
### Report <=== Results
(block that formats and prints final output)
```

---

## 8. Error Surfaces in Strict Mode

When a block fails in strict mode, the engine surfaces:

- **Which block failed** and its starting line in the Markdown file
- **Translated line number** — the error line mapped back to your code, not the injected preamble
- **Boundary state** — all variables that were injected into the block at execution time

Use the boundary state dump to diagnose type mismatches between blocks. If `Results` shows `null` when you expected an array, the upstream block's output arrow didn't fire correctly — check that it printed valid JSON to stdout.

---

## 9. Self-Check Before Executing

- [ ] Does the document start with `Mode: Strict`?
- [ ] Are all header variable names exact matches to how I reference them in code?
- [ ] Does every block that needs to pass data forward have an `===>` output arrow?
- [ ] Does every block reading from an arrow use the correct stdin read pattern for its language?
- [ ] Are cross-language function calls using the **header name**, not the internal function name?
- [ ] Is logic that needs loops or branching handled **inside** a block, not at the document level?
- [ ] Does every block that writes to an output arrow print **valid JSON** to stdout?
