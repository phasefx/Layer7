#!/usr/local/bin/layer7

# Layer7 Codebase Mapper
Architectural extraction and AI synthesis pipeline.

**Version:** 1.4
**Status:** Functional

This script runs a deterministic tree-sitter parse over a target directory, filters the abstract syntax tree into a semantic mental map, and pipes it to a local LLM to generate a human-readable architecture guide.

Allow exception: level 4 headers

## 1. Configuration

### Mapper_Config
```JSON
{
  "host": "127.0.0.1",
  "port": 5005,
  "target_dir": "../",
  "output_file": "ARCHITECTURE_GUIDE.md"
}
```

## 2. Global Runtime State

### Mapper_State {}

## 3. Extraction Pipeline

### Codebase_Scanner > Mapper_State
Executes a rapid structural pass over the codebase.

```bash
TARGET=$(echo "$Mapper_Config" | jq -r '.target_dir')
echo ">>> Scanning codebase topology at $TARGET..." >&2

# Execute the parse command and dump the console noise into a log file
yes | npx -y depwire-cli parse "$TARGET" > depwire_logs.txt 2>&1

# Pass the actual JSON file that Depwire generated into the Mapper_State
echo '{"raw_file": "depwire-output.json"}'
```

### Topology_Reducer >> Mapper_State

Filters the raw output down to just the architectural skeleton and prepares the prompts.

```python
import sys
import json

raw_file = Mapper_State.get("raw_file", "raw_topology.txt")

try:
    with open(raw_file, "r") as f:
        content = f.read()
except FileNotFoundError:
    print(f"Error: Topology file '{raw_file}' not found.", file=sys.stderr)
    sys.exit(1)

# Clean up the string in case the 'yes' pipe output bled into the top of the file
if content.startswith("Add .depwire"):
    content = content.split("\n", 1)[-1]

# Truncating to fit within a standard context window efficiently.
compressed_topology = content[:20000] 

system_prompt = (
    "Act as a principal software architect. Review this codebase topology and write a "
    "3-paragraph executive summary explaining the data flow, the core state-management "
    "mechanisms, and any hidden architectural coupling. Format your response in clean Markdown. "
    "Do not output anything other than the requested Markdown."
)

print(json.dumps({
    "system_prompt": system_prompt,
    "user_prompt": f"Codebase Topology:\n{compressed_topology}"
}))

```

## 4. Narrative Synthesis

### AI_Synthesizer >> Mapper_State

Passes the condensed topology directly to the local Llama.cpp server.

```python
import sys
import json
import urllib.request

system_prompt = Mapper_State['system_prompt']
user_prompt = Mapper_State['user_prompt']

# Construct the URL dynamically to bypass Layer7's auto-linkification
host = Mapper_Config['host']
port = Mapper_Config['port']
url = f"http://{host}:{port}/v1/chat/completions"

headers = {"Content-Type": "application/json"}

data = {
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "temperature": 0.1,
    "max_tokens": 1024
}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)

try:
    print(">>> Generating architectural narrative via local LLM...", file=sys.stderr)
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        generated_text = result['choices'][0]['message']['content']
        print(json.dumps({"markdown_guide": generated_text}))
except Exception as e:
    print(f"Error calling LLM API at {url}: {e}", file=sys.stderr)
    sys.exit(1)

```

### Document_Writer

Intercepts the accumulated state and safely commits the generated guide to disk using Python to avoid Bash command substitutions.

```python
import sys

output_file = Mapper_Config['output_file']
md_content = Mapper_State.get('markdown_guide', '')

# Strip markdown code block wrappers if the LLM generated them
if md_content.startswith("```markdown"):
    md_content = md_content.split("\n", 1)[-1]
elif md_content.startswith("```"):
    md_content = md_content.split("\n", 1)[-1]

if md_content.endswith("```"):
    md_content = md_content.rsplit("\n", 1)[0]

md_content = md_content.strip()

final_output = f"# Codebase Architecture Guide\n\n{md_content}\n"

try:
    with open(output_file, "w") as f:
        f.write(final_output)
    print(f">>> Successfully mapped codebase to {output_file}", file=sys.stderr)
except Exception as e:
    print(f"Error writing to {output_file}: {e}", file=sys.stderr)
    sys.exit(1)

```

## 5. Workflow Manifest

### Steps

1. `Codebase_Scanner` => `Topology_Reducer` => `AI_Synthesizer` => `Document_Writer`

