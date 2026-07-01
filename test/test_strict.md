Mode: Strict

## My Input

```json
{"name": "Alice"}
```

## setup

```python
def setup():
    class Foo:
        pass
    return Foo()
```

## Process Data => Output

```python
x = setup()
print("x is", x)
```

## Output []
