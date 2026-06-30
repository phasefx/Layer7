# Composition Demo

Demonstrates the composition DSL for non-linear control flow using `Steps`, `Routing`, and the `SKIP` sentinel.

We use a simple counter that is decreased by a work block. The composition repeats the work step until the counter hits zero (the block emits SKIP).

This shows branching/looping without the linear document order doing all the work.

Allow exception: level 4 headers

## Remaining

```json
3
```

## Do Work > Remaining

"Does work" (prints a message), decreases the remaining count, publishes the new value via stdout (applied by `>` arrow).

When remaining reaches 0, emit SKIP (as stdout) to stop the repeat.

```python
def do_work():
    import sys
    # Remaining injected as int from the JSON header
    count = Remaining
    if count <= 0:
        print("SKIP")
    else:
        new_count = count - 1
        print(f"Work step done. {count} -> {new_count}", file=sys.stderr)
        # publish for the output arrow
        print(new_count)

do_work()
```

## Summarize

```python
def summarize():
    print("All work completed via composition loop!")

summarize()
```

## Main Loop

```composition

#### Steps

1. `Do Work`

2. `Summarize`

#### Routing

Repeat step 1 until SKIP, then goto step 2.

```

Run:

    python3 layer7.py examples/composition_demo.md

You will see three "Work step done" messages (via stderr) followed by the summary. The composition engine handles the looping and exit via SKIP.
