# Layer7: Polyglot Code Organization for Human Cognition

**Version:** 0.7 (Evolved)
**Date:** 2026-06-23
**Status:** Design in progress

Layer7 lets you write code in whatever language you already know for each job, organized as Markdown so you can come back to it later and still understand it. Just your existing skills, sequenced. We're targeting solo hobby coders with ADHD and similar brains; the mixing and matching of languages is feature.

Layer7 aims to be skimmable, gistable, and understandable. It's meant to be readable when you come back to a project after a long absense. It is not trying to be all things to all people, nor is it catering to enterprise software development.

**Core principles:**
- All things allowed with narrative justification. Linter warns; Allow exception: documents.
- Provide friction when the number of "things" goes past 7. This is a signal, not a constraint.
- Unix philosophy: write programs that do one thing well, ensuring they can work together, and using text streams for universal communication. We just use Markdown instead of the Shell for our glue.

---

## 1. The Problem & The Vision

### Why Layer7?

- **Working memory bottleneck:** Humans hold ~7 items in active memory. Software architecture routinely ignores this.
- **The disappearing code problem:** You write code, leave it, return weeks later—it's cryptic.
- **Shame-free pragmatism:** Make trade-offs explicit and move on.
- **Execution without cognitive overhead:** Return to code and understand it without loading 20 mental models.
- **Modality:** Surface one small set of affordances at a time.

### What Layer7 Does

1. **Organizes code as bounded Markdown.** Each module, chunk, and decision is scannable and narratable.
2. **Respects cognitive limits.** ≤7 files per directory, ≤7 chunks per file, ≤7 layers per composition, ≤7 items per data contract. Soft warnings, not errors.
3. **Compiles to executable tools.** A pre-processor turns Markdown into real, runnable processes — each chunk a subprocess in its own language, wired by an invisible generated preamble.
4. **Supports dual execution.** Run via LLM (analysis/debugging) or algorithms (production), against the same underlying tool calls.
5. **Makes exceptions first-class.** Breaking a rule? Document why. It's all recorded.
6. **Separates flow from logic.** Chunks stay pure and linear, if you let them. Branching, looping, and routing may live one level up.
7. **Defers to real languages for what they already do well.** Layer7 narrates and sequences. It does not reinvent objects, types, concurrency, or persistent state — those are a "go write code" problem, not a Layer7 feature request.

---

## 2. Structure & Organization

### File Layout

```
myproject/
├── README.md
├── lib/
│   ├── main.md
│   ├── game_loop.md
│   ├── physics.md
│   └── render.md
├── compositions/
│   └── morning_digest.md
└── .layer7.yml
```

**Horizontal scaling first.** Add files at the same level before going deeper. Depth signals a different level of abstraction, not just more stuff.

**Directory scoping:** Sibling files share a namespace. Child directories are imported explicitly, not auto-visible.

### Header Scope: A File Is an Address Space

Every header in a `.md` file is referenceable, by its identifier, from any code block in that same file — no import, no declaration required. This is the same principle as directory scoping, one level further in: **a file is to its headers what a directory is to its sibling files.**

Cross-file references use a qualified, dotted address:

```
Online_Raffle.A_Ticket
raffle.md-Online_Raffle.A_Ticket
```
Use of cross-file references outside of a composition get soft-flagged by the Linter, and an Allow exception: may provide justification. A common exception would be for utility functions.

Header text resolves to an identifier using shape-insensitive fuzzy matching.  The engine collapses whitespace, strips non-alphanumeric characters, and ignores casing (`The Tickets`, `The_Tickets`, and `theTickets` all map to `thetickets`).  This canonical symbol is what maps to the state table, what gets injected into a chunk's generated preamble (Section 4), and what qualified cross-file addresses resolve through.

### Nested Headers — Addressing Only

Headers may nest (`##` containing `###`) for self-documentation and disambiguation — e.g., grouping `is_valid`, `addTicket`, and `searchByName` under a `Tickets` header to signal they're conceptually related, or to qualify an address as `Tickets.is_valid` when two same-named things exist elsewhere in a large file.

**Nesting carries zero runtime meaning.** A nested header is still just an ordinary chunk or data shape:

- It runs in the same flat, top-to-bottom reading order as every other header in the file — nesting doesn't change execution order.
- It inherits nothing from its parent header — no scope, no language, no implicit binding. Every header is fully self-describing on its own.
- It does not, by itself, turn the parent header into anything other than what it already was (a value, a chunk, whatever). 

Nesting depth follows the same horizontal-first stance as directories: ≤2 levels is the soft default, deeper nesting is a linter warning (not an error) the same way directory depth or chunk count is. If you find yourself reaching for nesting as a way to express something *other* than addressing — inheritance, shared state, automatic scoping — that's the signal to stop and reconsider, not to add a feature.

### Module Anatomy

Each `.md` file is a **module**. Standard structure:

```markdown
# Module: Physics

Handles collisions and movement.

## integrate velocity

Apply velocity to position each frame.

```python
def integrate_velocity(entity, delta):
    entity.position.x += entity.velocity.x * delta
    entity.position.y += entity.velocity.y * delta
    return entity
```
```

**Key features:**

- **Header arrows (`=>`, `<=`):** stdin/stdout redirection, spelled with Layer7's own arrows instead of shell's `>`/`<`. `=>` means "this chunk's output becomes this named thing." `<=` means "this named thing becomes this chunk's input." See Section 3.
- **Data Shapes:** A header followed directly by a fenced data block (JSON, or a bare type keyword — see below) declares a named value, not a chunk. No code runs; it's a slot.
- **Narrative:** Why you're doing this. Guides reasoning (human or LLM).
- **Code blocks:** Actual, executable code, in any language. Exactly one per chunk.
- **Exceptions:** Where you break the rules and why.

### Inline Type Shorthand for Simple Data Shapes

For simple values, a full JSON fence is unnecessary ceremony. A header may declare its shape inline:

```markdown
## Tickets []
## Score number
## IsComplete boolean
## Config {}
```

This is pure shorthand for the equivalent fenced JSON block — `## Tickets []` means the same thing as `## Tickets` followed by a ` ```json\n[]\n``` ` block. YAML may be supported the same way for structured defaults, where YAML's lighter syntax is worth it.

### What Is a Chunk?

A **chunk** is a unit of meaning:
- Single cohesive purpose
- Understandable in one reading
- ≤7 lines of code (soft warning, not error)
- Exactly one code block, in one language
- Preceded by narrative
- **Pure by default.** Given what's injected into its preamble, it produces its declared output. No hidden reads or writes beyond what the preamble made visible.

Chunks are the atomic unit of Layer7. They are not where flow control lives — see Section 5.

---

## 3. Data Flow

### Header Arrows Are Redirection, Not a Dependency List

`=>` and `<=` name the chunk's **primary** stdin/stdout pipe — the one thing it's explicitly fed and explicitly produces, same spirit as shell redirection:

```markdown
## Acquiring the Tickets => The Tickets
```bash
jq . $1
```
```

```markdown
## Chicken Dinner <= The Tickets
```python
import sys, json
tickets = json.loads(sys.stdin.read())
...
```
```

A header with no arrow simply doesn't have a declared primary pipe — it can still reference any other header in the file by name (Section 4), it just isn't piped a value as its main stdin, and its stdout isn't captured as anyone's named input.

### Whole-Value Replacement Is the Default Mutation Story

If a chunk needs to produce an updated version of something — say, a filtered or appended `TheTickets` — the answer is the same mechanism, not a new one: that chunk declares itself the `=>` producer for that header and emits the entire new value on stdout. No partial mutation, no setters, no method calls. Build the whole new value in memory (trivial — it's one process, run once) and emit it whole.

This keeps the Unix-pipe model intact: every chunk is still just "transform what I'm given into what I produce," nothing more. If a header genuinely needs more than one chunk able to update it independently over the file's lifetime, treat it as a **stream** (Section 6), not as an object with mutator methods (Section 9 covers why object semantics were considered and set aside).

---

## 4. The Pre-Processor's Real Job: Generated Preambles

This is the mechanism that makes Section 3 work, and it's worth stating plainly, because it resolves what would otherwise be a real ambiguity problem.

**Before a chunk's own code runs, the pre-processor generates a preamble — native to that chunk's language — that binds every other header in file scope as an ordinary variable or function in that language.** The chunk's own code is then run, unmodified, with that preamble in front of it. The chunk author never sees the preamble; what they wrote is what stays on the page.

What the preamble contains depends entirely on what kind of thing the referenced header is:

- **A data slot** → inject a literal value, deserialized into that language's native shape (`my $TheTickets = decode_json('...');` for Perl; a real array literal for Python/JS, since JSON is nearly already their native literal syntax).
- **A chunk in a *different* language** → inject a callable wrapping a subprocess call to that chunk's compiled tool — see Section 6, Cross-Language Calls.
- **A chunk in the *same* language** → inject the other chunk's actual function definition directly into the preamble and call it in-process. No subprocess, no RPC, free. Cost is paid only at an actual language boundary, never within one.

**Why this resolves the disambiguation problem cleanly:** because every reference becomes an ordinary binding in the target language before the chunk's own code runs, "which `Name` did I mean" stops being a Layer7-level parsing question and becomes ordinary variable scoping — a problem every language already has well-understood rules for (inner scope shadows outer). Layer7 doesn't need a special marker (no `$$`, no sigil) to tell file-scoped references apart from local variables; it just inherits whatever scoping the target language already does.

A chunk needing nothing from file scope gets an empty preamble and is just... the code you wrote, run as-is, in its language, unmodified. The simplest case stays the simplest case.

---

## 5. Compositions — Where Flow Control Lives

### The Core Separation

A single Unix pipe never branches or loops — that's not the pipe's job, it's the shell script wrapped around it. Layer7 makes the same split formal:

- **Chunks** are the small programs. Pure, linear, narratable in one reading.
- **Compositions** are the shell script. A separate `.md` file (or, for a single linear file with no branching, no separate composition is needed at all — see below) whose entire purpose is sequencing, branching, and looping over chunks that already exist.

### Default: No Orchestration Needed

If a file's chunks just run top to bottom with no branching, **no composition file is needed at all** — the file's own header order *is* the execution order, by default, with no orchestration syntax anywhere. This was true of `raffle.md` end to end: every section ran in document order, and the only flow-control behavior in the whole file was implicit — a chunk that `die`s halts everything after it. No `GOTO`, no `WHEN`, no keywords. Failure propagation through ordinary error exits *is* the default flow-control mechanism, the same way `set -e` works in a shell script.

A separate composition file remains the right tool when a project's flow needs to be assembled from chunks that live in *different* files, or when the same chunks need to be sequenced more than one way for more than one purpose.

### Composition Anatomy (When Used)

```markdown
# Composition: morning_digest

Orchestrates the digest pipeline.

## Layers

1. `check_inbox`
2. `summarize`
3. `send`

## Routing Rules

- If `check_inbox` returns sentinel `NO_NEW`: skip to `send`
```

- **`## Layers`:** the ordered list. Narrative order is execution order.
- **`## Routing Rules`:** conditions and loop bounds named explicitly, separate from the linear list.
- **Constraint:** ≤7 layers per composition, same soft-warning/exception treatment as everything else.
- **Scoping rule (open question, carried from v0.4):** does a composition referencing another composition see only its sentinel/output, or its internals too? Leaning toward opaque-step-only, not yet settled.

### Sentinels — Short-Circuit Without Monads

A chunk with nothing to contribute says so in plain text:

```markdown
If inbox_state.has_new is false, output exactly: SKIP
```

Downstream logic checks for the sentinel and branches. This remains the one piece of monad-shaped behavior Layer7 adopts directly — because it's a plain string a human reads at a glance, not an abstraction a human has to learn first.

### No Concurrency Primitive

Layer7 does not have, and does not currently need, an async/await or concurrency model. A real-time loop (a game's physics/input/render cycle) is not a counter-example — it's the same linear composition, run once per tick; the apparent concurrency is just serial steps repeated, not two timelines actually running at once. If a genuine need for concurrent execution ever appears, the right shape is an explicit, narratable fan-out step *in a composition* (declared concurrency, visible in one place) — not an implicit non-blocking primitive inside a chunk. Not building this until a real case demands it.

---

## 6. Streams, Cross-Language Calls & Two Namespaces

### Two Namespaces, Different Collision Rules

- **Function/chunk names**: unique by default. **Collision is a hard error** — the one hard rule in Layer7, and a different *category* of problem than the soft constraints (it's an ambiguity the pre-processor has no principled way to resolve, not a quality issue with a sensible fallback).
- **Stream names**: open by default — many writers, many readers is normal. Undocumented convergence (two writers to one stream with no narrative indicating intent) is a soft warning, not an error.

### Streams — When a Single Producer-Per-Header Isn't Enough

Most headers have exactly one `=>` producer over a file's lifetime — whole-value replacement (Section 3) covers them. Streams are the documented exception for when a value genuinely needs more than one independent writer over time:

```markdown
## log result

Exception: Publishes to an open stream — any number of downstream
modules may subscribe without this chunk changing.

Publishes: result_log
```

**The reading-order constraint:** a chunk may only subscribe to a stream published by something earlier in reading order — same file, or an explicitly imported file wholly "above" it. Forward references are illegal. This is what keeps streams legible top-to-bottom instead of becoming an event bus.

### Cross-Language Calls

Calling into a chunk written in a different language is the one place where something has to happen beyond ordinary scoping — no version of "just inject a reference" lets a Perl scalar hold a live pointer into a separate Node process.

The mechanism (Section 4): the pre-processor generates a wrapper in the calling chunk's language that shells out to the target chunk's compiled tool, passes arguments, and captures the result. From the calling chunk's own code, this is invisible — it reads as an ordinary function call, because as far as the chunk's author is concerned, it is one.

**Open question, deliberately not settled in v0.5:** whether this becomes a real MCP-protocol call (the original, longer-term vision) or stays a lighter local subprocess RPC. The v0.5 raffle prototype used the latter — plain subprocess shelling, plain-text returns for trivial cases — specifically to test whether the *model* holds before investing in the protocol layer. Both are valid targets for the same generated-preamble mechanism; switching from one to the other later shouldn't require rewriting any chunk's own code, only the pre-processor's code generation.

---

## 7. Constraints & Soft Warnings

- ⚠️ File has 9 chunks (limit: 7)
- ⚠️ Composition has 9 layers (limit: 7)
- ⚠️ Header nesting is 3 levels deep (consider flattening, or document why)
- ⚠️ Two chunks both produce the same header with no narrative indicating intent (race condition, or should this be a stream?)
- ⚠️ Multiple languages in one file without exception narrative (first language is free; every additional one needs justification)

These are all **soft** — suppressible with documented justification.

There is exactly one **hard** error:

- 🛑 Two chunks in the same scope share a function/chunk name. No sensible fallback exists, unlike every soft constraint above.

---

## 8. Nesting Rules (Directories)

### Horizontal First

Scale horizontally before going deeper. A directory should have ≤7 items. Depth signals a different level of abstraction, not just more stuff — the same stance now applies one level further in, to headers within a file (Section 2).

---

## 9. What Layer7 Defers to Real Languages

This section exists because of a recurring pattern across this design's evolution: a real programming-language concept shows up at the door — monads, async/concurrency, tiered constraint profiles, typed sentinels, and most recently, stateful objects with method dispatch — and each time, the right call turned out to be the same one: **the underlying languages already solve this well. Layer7 doesn't need to model it; it just needs to let a chunk reach out and use it.**

### The Object Temptation, and Why It Was Set Aside

A natural extension once headers can have nested sub-headers: a header with a JSON data shape *and* nested method-like sub-headers (`is_valid`, `addTicket`, `searchByName`) starts to look like an object — call its methods, mutate its internal state, from any chunk, in any file, in any language, via generated RPC glue.

This was considered and set aside, for two reasons:

1. **The trigger was invisible.** Whether a header is "just a value" or "a long-running stateful service callable from anywhere" would have been signaled only by whether it happened to have nested sub-headers underneath it — the single biggest lifecycle distinction in the system, hanging on the same syntax used for purely cosmetic addressing (Section 2). Keeping nesting meaning-free avoids this collapsing into one thing.
2. **It's the global-mutable-object problem again, with friendlier syntax.** A stateful header with exposed mutator methods, callable from anywhere, in any order, is structurally the thing Layer7 has been trying to avoid since v0.3 — multiple writers with no visible ownership — just wearing a method-call face instead of a global-variable face.

**The resolution:** if a project genuinely needs persistent, mutable, multi-writer state with real method semantics — a real ticket ledger, a real entity table — that's a signal to **write an actual small service in real code**, and have Layer7 chunks call out to it the same way they'd call any external dependency. The impurity is delegated openly to something whose entire job is being stateful, rather than absorbed into Layer7's own vocabulary. Layer7 narrates and sequences; it does not reimplement what a real language or a small real service already does well.

This is now a standing design checkpoint, not a one-time decision: **when a proposed Layer7 feature starts reaching for objects, types, concurrency, or persistent shared state, that's the signal to ask "should this just be code instead" before adding new syntax.**

---

## 10. Language Support

### Mixed Languages

Layer7 is language-agnostic. Code blocks can use any language. The first language used in a file is free; additional languages require an `Allow exception:` line naming the language.

```markdown
## fast math

Allow exception: c

```c
void vec_add(float* a, float* b, float* out, int n) {
    for (int i = 0; i < n; i++) out[i] = a[i] + b[i];
}
```
```

---

## 11. Getting Started

1. Write a `.md` file. If it's just linear chunks with no branching, that's the whole program — no composition file needed.
2. If the logic needs branching or looping, write a separate composition referencing existing chunks.
3. Run the pre-processor — it parses headers, builds per-chunk preambles, and runs each chunk as a real process in its own language.
4. Choose execution mode: algorithmic (composition or default top-to-bottom order drives sequencing) or LLM-assisted (MCP server, LLM as the calling client).

### What Layer7 Is NOT

- A new programming language for *modules* (code blocks are real languages; module structure is just narrative + arrows)
- ~~A composition language~~ — compositions, when used, do have their own small grammar (`Layers`, `Routing Rules`). This is acknowledged directly rather than denied; see v0.4 changelog.
- A runtime (compiles to standard executables/subprocesses)
- For everyone (designed for ADHD, working memory constraints, vibe coding)
- A silver bullet
- A place to reimplement objects, types, concurrency, or persistent state — see Section 9

### What Layer7 Is

- A code organization system respecting cognitive limits
- A bridge between narrative and execution
- Genuinely language-agnostic at the chunk level — chunks run as real subprocesses in their real languages, wired by generated preambles, not by a shared runtime
- Dual-executable: algorithms and LLMs, against the same underlying tool calls
- Split cleanly between pure logic (chunks), flow (compositions), and "go write real code" (Section 9)

---

## 12. The Vision

Layer7 is not trying to make you a "better" programmer. It's trying to make you a **less exhausted** programmer.

By encoding cognitive limits into structure, by treating exceptions as features, by generating the hard parts invisibly instead of asking you to write them, and by knowing when to defer to a real language instead of reinventing one of its features — it might let you write software that feels like *thinking*, not *remembering*.

You return to code after a week and it reads like someone left you instructions. Because they did. You did.

**All things allowed with narrative justification. That's the deal.**

---

## Changelog from v0.5

- **Clarification on header normalization for referencing.** Reduces cognitive friction by allowing more variation.

## Changelog from v0.4

- **Replaced `$$Name` substitution with generated preambles.** The pre-processor now injects native bindings (values or callables) into a per-chunk preamble before running it, rather than pattern-matching special tokens inside the code. Chunk code is now ordinary, unmarked code in its own language — no Layer7-specific syntax inside a code block at all.
- **Header arrows reframed as stdin/stdout redirection**, not a dependency list — `=>`/`<=` name the primary pipe only; all other file-scope references are resolved ambiently via the preamble.
- **File scope formalized**: every header in a file is referenceable from any code block in that file, same principle as directory-level sibling scoping, one level further in.
- **Nested headers added, explicitly scoped to addressing/documentation only** — zero runtime meaning, no inheritance, same horizontal-first soft-warning treatment as directory depth.
- **Inline type shorthand** for simple data shapes (`## Tickets []`, `## Score number`) as sugar over a full JSON fence.
- **Cross-language calls and same-language calls now both resolved through the same preamble mechanism** — same-language calls inline for free (in-process), cross-language calls generate subprocess RPC glue. Cost is paid only at an actual language boundary.
- **Considered and explicitly set aside: headers-as-stateful-objects** with method dispatch and RPC-backed mutator methods. Documented in new Section 9 as a standing design checkpoint — "should this just be code instead" — rather than a one-time rejection, since the same pattern (a real-language concept knocking at the door) recurred multiple times this iteration (monads, concurrency, constraint tiers, typed sentinels, now objects).
- **No-composition-needed default made explicit**: a file with no branching needs no separate composition at all; reading order is execution order, failure propagation is the default flow control. Validated end-to-end against a real four-language prototype (`raffle.md`, Section 6 / Section 4 examples).
- **Honest acknowledgment that compositions are a small real grammar**, not "not a new language" — v0.4's blanket claim is narrowed to apply to modules, not compositions.
