# Layer7
Polyglot Code Organization for Human Cognition

**Version:** 0.8 (Evolved)
**Date:** 2026-06-24
**Status:** Design in progress

Layer7 lets you write code in whatever languages you already know for a project, organized as Markdown. It is similar to Jupyter in a way, but is geared toward literate programming, not presentation. We're targeting solo hobby coders with ADHD and similar brains; the mixing and matching of languages is feature. Layer7 aims to be skimmable, gistable, and understandable. It's meant to be readable when you come back to a project after a long absense. It is not trying to be all things to all people, nor is it catering to enterprise software development.

**Core principles:**
- Provide friction when the number of "things" goes past 7. This is a signal, not a constraint. Humans can hold roughly 7 chunks in working memory at one time. A chunk is a unit of information that be perceived and recognized at a glance.
- All things are allowed with narrative justification. The linter or the runtime warns; `Allow exception:` justifies.
- Unix philosophy:
  - write programs that do one thing well
  - ensure they can work together
  - use text streams for universal communication
  We just use code blocks for programs and Markdown instead of the Shell for our glue.

# Table of Contents

## 1. Core Structure (what Layer7 is made of)
- **Header variables** (JSON blocks, inline shorthand)
- **Code blocks**
- **Redirection arrows** (<, >, <<, >>)

These are the atomic primitives. Layer7 without these is just documentation.

## 2. Addressing & Naming (how you reference things)
- **Nested headers** (for disambiguation)
- **Cross-file references** (qualified addresses)
- **Fuzzy matching** (shape-insensitive identifier resolution)

These are all about the namespace and how you find things. They're conceptually distinct from execution.

## 3. Flow Control (how things execute)
- **Compositions** (orchestration of code blocks for branching/looping)
- **Sentinels** (SKIP is the only built-in sentinel for short-circuiting)
- **No-composition default** (linear files need no orchestration)

These are about sequencing and control flow, not about what the code does.

## 4. Language Integration (how languages work together)
- **Cross-language calls** (Perl calling JS, etc.)
- **Function-shaped headers** (callable chunks)
- **Mixed languages** (multiple languages per file with exceptions)

These are all about the polyglot nature of Layer7 and how different languages interoperate.

# Contents

Allow exception: level 4 headers

## 1. Core Structure

Markdown headers provides the core structure for Layer 7. It's meant to allow for quick chunking and navigation, and may benefit from Markdown aware viewers and editors that can fold text at the header level. Headers are reference-able, and may point to code, variables, or other headers.

### Header Variables

#### JSON Example

So here the header--JSON Example--becomes reference-able in code blocks after some generous normalizations. Depending on the language syntax, you may use be able to do things like this in a given code block:  `JSON_Example.position.x` or `$JSON_Example->velocity->dy`

```JSON
    { "position": { "x": 0, "y": 0 }, "velocity": { "dx": 0, "dy":0 }}
```

#### YAML Example

Use this when the expressiveness is an asset. Otherwise, we recommend sticking to JSON as the lingua franca between programs.

```YAML
name: Mini
type: persona
core_personality: |
  You are Mini, an enthusiastic and energetic helper!
voice:
  tone: bright
  formality: casual
  humor: playful
mood: happy
```

#### Inline Example `[]`

This header points to an empty array.

#### Inline Example2 `string`

And this one to an empty string. Layer7 does not have strict type checking, but the linter and the runtime may generate warnings.

#### Another Example `{}`

No harm in doing this. {} gets assigned first, then the JSON block, and the linter/runtime may generate a warning if there's a mismatch.

```JSON
    { "position": { "x": 0, "y": 0 }, "velocity": { "dx": 0, "dy":0 }}
```

### Code Block Headers

#### Procedural Example

```Bash
echo "arg 1: $1"
read --timeout 5 my_stdin
echo "stdin: $my_stdin"
```

If a code block calls `Procedural_Example("hello world")`, then for code like this we'll set the program level argument (the command-line argument) for the program to "hello world". But as written, this code block may execute on its own if reached by the instruction pointer. The section on **Redirection arrows** shows how to use STDIN and STDOUT.

#### Functional Example

If a code block contains only a function, anonymous or otherwise, then an invocation like `Functional_Example("hello world")` will call the function, passing arguments one for one if possible, instead of setting program level arguments. Extra incoming arguments may be get crammed into the last parameter. Redirection may map input from STDIN into the first argument. Normal top to bottom execution just registers the function and moves on.

```Javascript
function print_me(incoming) {
    console.log(incoming);
}
```

### Redirection arrows

Code block headers may reference header variables with redirection arrows. The parser looks for <, <<, >, and >>, but these may be decorated however you wish. For example: <, <=, <-, and ---<=== are equivalent.

#### Example 1 <=== JSON Example

This takes the header variable we defined earlier, `JSON Example`, and provides it as input for any code block found within this `Example 1` header. I'm not going to provide one in this case, and that's not an error, though it will generate a warning unless we do the following:

Allow exception: missing code block

#### Example 2 ===> JSON Example

If a code block within this `Example 2` header returns a value as a function, or outputs a value to STDOUT otherwise, then that value replaces the value held by the `JSON Example` header variable.

#### Example 3 ===>> Inline Example

In this case, we would not replace the value for `Inline Example`, but append to it, if it holds an array, or set a key/value pair if it holds an object. This is how you might output to a stream.

#### Example 4 <<=== Inline Example

Streaming input. Hrmm. Let's skip this one until we hit a need for it.

#### And referencing code block headers here?

We don't try to handle code block headers pointing to code block headers: `Example 2 ===> Example 1`
All things allowed with justification... if you implement it. This gets into orchestration territory.

## 2. Addressing & Naming

Headers are addresses. They are hierarchal and you can express enough of the hierarchy as needed to remove ambiguity. For example, referring to `Functional_Example` within this file will find the `#### Functional Example` header from the Code Blocks section. But if there are more than one these, which we don't recommend doing, you could include more of the full address/pathing, such as `Code_blocks_Functional_Example`, `Core_Structure_Code_blocks_Functional_Example`, or even `filename_Core_Structure_Code_blocks_Functional_Example`--whatever is enough to disambiguate.

All combinations of inclusion or exclusion with these sub-headers is made available, with ones that show up more than once thrown out as being ambigious. So, for example, filename_Functional_Example may be valid, as well as Core_Structure_Functional_Example. Depending on the target language, using . or :: may be available as the separator. For example, `Code_blocks::Functional_Example`. All lower-case variants will be provided, as well as collapsed space versus underscore as space variants. For example, `FunctionalExample` and `functionalexample` will both usually be permitted, but I don't claim to know how identifiers work in every language we'll be supporting. Is this a good idea? Not really. But it reduces friction at the point of writing. Some code is better than no code. Tooling can help.

Cross-file references are possible, but will generate warnings outside of use by orchestration, though `Allow exception: cross-file reference` may silence those.

All of this is made possible by invisible preambles/injections that run before any given code block. Adjacent code blocks in the same language or on the same runtime may be combined into one process. Cross-language functions are made available as MCP tools, both for LLM execution and internally. No, I do not care about performance hits here. If something hurts, work around it. :-)

## 3. Flow Control

There is a baseline flow for execution: top to bottom. All headers in a given file are immediately available for reference, but code and data blocks must be executed/processed before such references are actually used. The headers may serve as forward declarations or prototypes.

A composition is either a code block, a header, or a whole Markdown file whose sole purpose is to stitch code block headers together and handle non-linearity. We provide a small DSL for this, but for anything complicated you may, of course, use any language you're familiar with in a code block. The DSL has one built-in sentinel value that it looks for: SKIP. If a code block outputs that then the composition will treat it like a signal. The only thing that really distinguishes a composition from any other code block is convention.

```composition

This is an empty composition as a code block. No logic in this example. The composition DSL is essentially Markdown with some expected structure.

```

### Composition: This is an example header composition. They keyword `Composition`, case-insensitive, triggers it.

The first bit of structure with the composition DSL is a header starting with the keyword `Steps`

#### Steps

This is where we're allowed to chain code block headers together. By convention we number the references, but this is only necessary if we need to refer to specific steps that re-use the same Header references. Random text gets ignored.

1. `Non-existent header.`

It's okay to do this. The linter will throw a warning.

2. `Start Screen`

These are being executed as read, left to right, top to bottom. A code block returning 'SKIP' exits the composition by default. The Routing header is where we make exceptions.  Compositions may be followed by other compositions.

3. `Player input` => `Physics engine` => `Render engine`

#### Routing

Repeat step 3 until SKIP, then goto step 2.

Random text gets ignored.  But something like this will throw a warning:
Repeat step gobbligook until.

## 4. Language Integration

It's magic and, yes, that can be a bad thing. But we're always building on abstractions upon abstractions. You're squinting at this one because you don't trust it yet.

```Perl
if ($JSON_Example->player->x == 0 && $JSON_Example->velocity->dx == 0) {
    some_javascript_could_be_wrapped_by_this('no movement on the X axis');
}
```

Yes, now Perl has even _more_ magic variables. :-)
