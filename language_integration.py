import json
import subprocess
import tempfile
import os
import re
import atexit
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# =============================================================================
# 4. LANGUAGE INTEGRATION (How languages work together)
# =============================================================================
# This file handles the polyglot execution:
# - Cross-language calls (MCP-shaped dispatch via shell-out)
# - Function-shaped header detection and registration
# - Per-language preamble generation (state injection + function stubs)
# - Generic code block execution
#
# KEY CONCEPT: Every code block runs with an invisible preamble prepended.
# The preamble declares all header variables as native variables in the target
# language, and injects callable stubs for all registered cross-language
# functions. Cross-language function calls work by shelling out to the target
# language's interpreter with a wrapper script that deserializes args, calls
# the function, and serializes the result back to JSON.
#
# The user never sees the preamble — it's the "magic" from Section 4 of the
# design doc.  If something hurts, work around it. :-)

# ─── Interpreter / extension maps ───────────────────────────────────────────

INTERPRETERS = {
    'javascript': 'node', 'js': 'node',
    'python': 'python3', 'py': 'python3',
    'ruby': 'ruby', 'rb': 'ruby',
    'perl': 'perl', 'pl': 'perl',
    'bash': 'bash', 'sh': 'sh',
}

EXTENSIONS = {
    'javascript': '.js', 'js': '.js',
    'python': '.py', 'py': '.py',
    'ruby': '.rb', 'rb': '.rb',
    'perl': '.pl', 'pl': '.pl',
    'bash': '.sh', 'sh': '.sh',
}

# ─── Result type ─────────────────────────────────────────────────────────────

@dataclass
class ExecutionResult:
    """Returned by MCPDispatcher.execute()."""
    stdout: str
    stderr: str
    returncode: int

    @property
    def success(self) -> bool:
        return self.returncode == 0


class Layer7Error(Exception):
    """Raised when a code block exits with non-zero status."""
    pass

# ─── Identifier helpers ─────────────────────────────────────────────────────

def title_to_identifiers(title: str) -> List[str]:
    """Generate valid programming-language identifier variants from a header title.

    "The Tickets"      → ["The_Tickets", "TheTickets"]
    "Ticket_Validator"  → ["Ticket_Validator"]
    "A Ticket"          → ["A_Ticket", "ATicket"]
    """
    # Underscore form: spaces become underscores
    underscore = re.sub(r'[^a-zA-Z0-9_]', '', title.replace(' ', '_'))
    # Collapsed form: spaces removed entirely
    collapsed = re.sub(r'[^a-zA-Z0-9_]', '', title.replace(' ', ''))

    # Identifiers can't start with digits in most languages
    if underscore and underscore[0].isdigit():
        underscore = '_' + underscore
    if collapsed and collapsed[0].isdigit():
        collapsed = '_' + collapsed

    result = [underscore]
    if collapsed != underscore:
        result.append(collapsed)
    return result

# ─── Dispatcher ──────────────────────────────────────────────────────────────

class MCPDispatcher:
    """Executes code blocks with full state injection and cross-language dispatch.

    Usage::

        dispatcher = MCPDispatcher(program_args=['input.json'])
        dispatcher.register_function('Validator', 'javascript', 'function(x){…}')
        result = dispatcher.execute('perl', code, state={'Tickets': [...]})
    """

    def __init__(self, program_args: List[str] = None, working_dir: str = None):
        self.program_args = program_args or []
        self.working_dir = working_dir
        self.functions: Dict[str, dict] = {}   # name → {language, code, temp_path}
        self._temp_files: List[str] = []
        atexit.register(self._cleanup)

    def _cleanup(self):
        for path in self._temp_files:
            try:
                os.remove(path)
            except OSError:
                pass

    def _write_temp(self, code: str, language: str) -> str:
        """Write *code* to a temp file with a language-appropriate extension."""
        suffix = EXTENSIONS.get(language, '.txt')
        fd, path = tempfile.mkstemp(suffix=suffix, prefix='layer7_')
        with os.fdopen(fd, 'w') as f:
            f.write(code)
        self._temp_files.append(path)
        return path

    # ─── Function detection ──────────────────────────────────────────────

    def is_function_shaped(self, language: str, code: str) -> bool:
        """Does this code block contain only a single function definition?

        Anonymous functions count (``function(x){…}`` in JS).
        """
        code = code.strip()
        lang = language.lower()
        if lang in ('javascript', 'js'):
            return bool(re.match(r'^function\s*[\w$]*\s*\(', code))
        elif lang in ('python', 'py'):
            return code.startswith('def ')
        elif lang in ('perl', 'pl'):
            return code.startswith('sub ')
        elif lang in ('ruby', 'rb'):
            return code.startswith('def ')
        elif lang in ('bash', 'sh'):
            return bool(re.match(r'^\w+\s*\(\)\s*\{', code))
        return False

    # ─── Function registration ───────────────────────────────────────────

    def register_function(self, name: str, language: str, code: str):
        """Register a function-shaped code block as a callable.

        Writes a standalone wrapper script to a temp file so any language can
        invoke it via shell-out.
        """
        wrapper = self._build_function_wrapper(language, code, name)
        temp_path = self._write_temp(wrapper, language)
        self.functions[name] = {
            'language': language,
            'code': code,
            'temp_path': temp_path,
        }

    def _build_function_wrapper(self, language: str, code: str, name: str) -> str:
        """Build a standalone script that:

        1. Reads JSON args from ``LAYER7_CALL_ARGS`` env var
        2. Calls the function
        3. Outputs JSON result to stdout
        """
        lang = language.lower()
        cs = code.strip()

        if lang in ('javascript', 'js'):
            return (
                f"const __l7fn = {cs};\n"
                "const __l7args = JSON.parse(process.env.LAYER7_CALL_ARGS || '[]');\n"
                "const __l7r = __l7fn(...__l7args);\n"
                "if (__l7r !== undefined) process.stdout.write(JSON.stringify(__l7r));\n"
            )

        elif lang in ('python', 'py'):
            match = re.match(r'def\s+(\w+)', cs)
            fname = match.group(1) if match else '_unnamed'
            return (
                "import json as _l7j, os as _l7o\n"
                f"{cs}\n"
                "_l7a = _l7j.loads(_l7o.environ.get('LAYER7_CALL_ARGS', '[]'))\n"
                f"_l7r = {fname}(*_l7a)\n"
                "if _l7r is not None:\n"
                "    print(_l7j.dumps(_l7r))\n"
            )

        elif lang in ('perl', 'pl'):
            match = re.match(r'sub\s+(\w+)', cs)
            fname = match.group(1) if match else '_unnamed'
            return (
                "use JSON::PP;\n"
                f"{cs}\n"
                "my $_l7a = decode_json($ENV{LAYER7_CALL_ARGS} // '[]');\n"
                f"my $_l7r = {fname}(@$_l7a);\n"
                "if (defined $_l7r) {\n"
                "    print encode_json($_l7r);\n"
                "}\n"
            )

        elif lang in ('ruby', 'rb'):
            match = re.match(r'def\s+(\w+)', cs)
            fname = match.group(1) if match else '_unnamed'
            return (
                "require 'json'\n"
                f"{cs}\n"
                "_l7a = JSON.parse(ENV.fetch('LAYER7_CALL_ARGS', '[]'))\n"
                f"_l7r = {fname}(*_l7a)\n"
                "puts JSON.generate(_l7r) unless _l7r.nil?\n"
            )

        return code  # fallback: return as-is

    # ─── Preamble generation ─────────────────────────────────────────────

    def _generate_var_preamble(self, language: str, state: Dict[str, Any]) -> str:
        """Generate code that loads header variables from a state JSON file
        (pointed to by ``LAYER7_STATE_FILE``) and declares them as native
        variables in the target language."""
        if not state:
            return ""

        lang = language.lower()

        # ── JavaScript ───────────────────────────────────────────────
        if lang in ('javascript', 'js'):
            lines = [
                "const _l7s = JSON.parse("
                "require('fs').readFileSync(process.env.LAYER7_STATE_FILE, 'utf8'));"
            ]
            for title in state:
                for ident in title_to_identifiers(title):
                    lines.append(f"var {ident} = _l7s[{json.dumps(title)}];")
            return '\n'.join(lines) + '\n'

        # ── Python ───────────────────────────────────────────────────
        elif lang in ('python', 'py'):
            lines = [
                "import json as _l7json, os as _l7os",
                "with open(_l7os.environ['LAYER7_STATE_FILE']) as _l7f:",
                "    _l7s = _l7json.load(_l7f)",
            ]
            for title in state:
                for ident in title_to_identifiers(title):
                    lines.append(f"{ident} = _l7s[{json.dumps(title)}]")
            return '\n'.join(lines) + '\n'

        # ── Perl ─────────────────────────────────────────────────────
        elif lang in ('perl', 'pl'):
            lines = [
                "use JSON::PP;",
                "my $_l7s;",
                "{",
                "    local $/;",
                "    open my $_l7fh, '<', $ENV{LAYER7_STATE_FILE}",
                '        or die "Layer7: Cannot read state: $!";',
                "    $_l7s = decode_json(<$_l7fh>);",
                "    close $_l7fh;",
                "}",
            ]
            for title in state:
                idents = title_to_identifiers(title)
                key = json.dumps(title)
                lines.append(f"my ${idents[0]} = $_l7s->{{{key}}};")
                for ident in idents[1:]:
                    lines.append(f"my ${ident} = ${idents[0]};")
            return '\n'.join(lines) + '\n'

        # ── Ruby ─────────────────────────────────────────────────────
        elif lang in ('ruby', 'rb'):
            lines = [
                "require 'json'",
                "_l7s = JSON.parse(File.read(ENV.fetch('LAYER7_STATE_FILE')))",
            ]
            for title in state:
                for ident in title_to_identifiers(title):
                    lines.append(f"{ident} = _l7s[{json.dumps(title)}]")
            return '\n'.join(lines) + '\n'

        # ── Bash ─────────────────────────────────────────────────────
        elif lang in ('bash', 'sh'):
            # Limited: export each value as a JSON-encoded string.
            # Bash can't natively decode JSON, but jq or other tools can.
            lines = []
            for title in state:
                for ident in title_to_identifiers(title):
                    val = json.dumps(json.dumps(state[title]))
                    lines.append(f"{ident}={val}")
            return '\n'.join(lines) + '\n' if lines else ''

        return ""

    def _generate_function_preamble(self, language: str) -> str:
        """Generate callable stubs for all registered cross-language functions.

        Each stub serialises its arguments as JSON, shells out to the
        registered function's wrapper script, and deserialises the result.
        """
        if not self.functions:
            return ""

        lang = language.lower()
        stubs: List[str] = []

        for func_name, func_info in self.functions.items():
            func_lang = func_info['language']
            func_path = func_info['temp_path']
            interpreter = INTERPRETERS.get(func_lang, func_lang)
            idents = title_to_identifiers(func_name)

            # ── Perl stubs ───────────────────────────────────────────
            if lang in ('perl', 'pl'):
                if not stubs:
                    stubs.append("use JSON::PP;")
                for ident in idents:
                    stubs.append(
                        f"sub {ident} {{\n"
                        f"    my @_l7a = @_;\n"
                        f"    $ENV{{LAYER7_CALL_ARGS}} = encode_json(\\@_l7a);\n"
                        f"    my $_l7o = `{interpreter} '{func_path}'`;\n"
                        f"    my $_l7rc = $? >> 8;\n"
                        f"    die \"Layer7: {func_name} failed (exit $_l7rc)\""
                        f" if $_l7rc != 0;\n"
                        f"    chomp $_l7o;\n"
                        f"    return length($_l7o) ? decode_json($_l7o) : undef;\n"
                        f"}}\n"
                    )

            # ── Python stubs ─────────────────────────────────────────
            elif lang in ('python', 'py'):
                for ident in idents:
                    stubs.append(
                        f"def {ident}(*_l7a):\n"
                        f"    import subprocess as _l7sp, json as _l7j, os as _l7o\n"
                        f"    _l7e = _l7o.environ.copy()\n"
                        f"    _l7e['LAYER7_CALL_ARGS'] = _l7j.dumps(list(_l7a))\n"
                        f"    _l7p = _l7sp.run(['{interpreter}', '{func_path}'],\n"
                        f"                     capture_output=True, text=True, env=_l7e)\n"
                        f"    if _l7p.returncode != 0:\n"
                        f"        raise RuntimeError("
                        f"f'Layer7: {func_name} failed: {{_l7p.stderr}}')\n"
                        f"    return _l7j.loads(_l7p.stdout)"
                        f" if _l7p.stdout.strip() else None\n"
                    )

            # ── JavaScript stubs ─────────────────────────────────────
            elif lang in ('javascript', 'js'):
                for ident in idents:
                    stubs.append(
                        f"function {ident}() {{\n"
                        f"    const _l7cp = require('child_process');\n"
                        f"    process.env.LAYER7_CALL_ARGS = "
                        f"JSON.stringify(Array.from(arguments));\n"
                        f"    const _l7o = _l7cp.execFileSync("
                        f"'{interpreter}', ['{func_path}'],\n"
                        f"        {{ env: process.env, encoding: 'utf8' }});\n"
                        f"    return _l7o.trim() ?"
                        f" JSON.parse(_l7o.trim()) : undefined;\n"
                        f"}}\n"
                    )

            # ── Ruby stubs ───────────────────────────────────────────
            elif lang in ('ruby', 'rb'):
                for ident in idents:
                    stubs.append(
                        f"def {ident.lower()}(*_l7a)\n"
                        f"    require 'json'\n"
                        f"    ENV['LAYER7_CALL_ARGS'] = JSON.generate(_l7a)\n"
                        f"    _l7o = `{interpreter} '{func_path}'`\n"
                        f"    raise \"Layer7: {func_name} failed\""
                        f" unless $?.success?\n"
                        f"    _l7o.strip.empty? ? nil : JSON.parse(_l7o.strip)\n"
                        f"end\n"
                    )

            # ── Bash stubs ───────────────────────────────────────────
            elif lang in ('bash', 'sh'):
                for ident in idents:
                    stubs.append(
                        f"{ident}() {{\n"
                        f"    LAYER7_CALL_ARGS=$(python3 -c \""
                        f"import json,sys; print(json.dumps(sys.argv[1:]))\""
                        f" \"$@\")\n"
                        f"    export LAYER7_CALL_ARGS\n"
                        f"    {interpreter} '{func_path}'\n"
                        f"}}\n"
                    )

        return '\n'.join(stubs) + '\n' if stubs else ''

    # ─── Execution ───────────────────────────────────────────────────────

    def execute(self, language: str, code: str, args: List[Any] = None,
                stdin: str = None, state: Dict[str, Any] = None,
                capture_output: bool = True) -> ExecutionResult:
        """Execute a code block with full preamble injection.

        Args:
            language: The code block's language tag (e.g. ``'perl'``).
            code: The raw code from the fenced block.
            args: Command-line arguments.  Defaults to ``self.program_args``.
            stdin: Data to pipe to stdin (for ``<`` arrow blocks).
            state: ``{header_title: data_value}`` for preamble injection.
            capture_output: If False, stdout and stderr stream directly to console.

        Returns:
            `ExecutionResult` with stdout, stderr, returncode.
        """
        if args is None:
            args = list(self.program_args)
        if state is None:
            state = {}

        lang = (language or 'bash').lower()

        # Write state file so the preamble can read variables from disk
        state_path = None
        if state and lang not in ('bash', 'sh'):
            fd, state_path = tempfile.mkstemp(
                suffix='.json', prefix='layer7_state_')
            with os.fdopen(fd, 'w') as f:
                json.dump(state, f)
            self._temp_files.append(state_path)

        # Build preamble  (variables first, then function stubs)
        var_preamble = self._generate_var_preamble(lang, state)
        func_preamble = self._generate_function_preamble(lang)

        # Assemble final code: preamble + user code
        full_code = var_preamble + func_preamble + code

        # Write to temp file and run
        temp_path = self._write_temp(full_code, lang)
        interpreter = INTERPRETERS.get(lang, 'bash')
        cmd = [interpreter, temp_path] + [str(a) for a in args]

        env = os.environ.copy()
        if state_path:
            env['LAYER7_STATE_FILE'] = state_path

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,
            env=env,
            cwd=self.working_dir,
        )
        stdout, stderr = process.communicate(input=stdin)

        # Always return strings (capture=False uses process inheritance for live output;
        # we return '' so callers don't double-print or crash on None).
        stdout = stdout.rstrip('\n') if stdout else ""
        stderr = stderr.rstrip('\n') if stderr else ""

        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            returncode=process.returncode,
        )


# ─── Shared execution helpers (dedup between linear exec and compositions) ───

def build_state(nodes):
    """Collect every header variable that currently holds data.

    Called fresh before each code block execution so the state dict reflects
    all changes made by prior blocks (e.g. ``>`` arrow writes).
    """
    state = {}
    for node in nodes:
        if node.data_value is not None:
            state[node.title] = node.data_value
    return state


def get_arrow_input_data(node, resolver):
    """Return JSON string for stdin if the node header has an input arrow (< or <<)."""
    if node.arrow_direction in ('<', '<<') and node.arrow_target:
        target = resolver.resolve(node.arrow_target)
        if target and target.data_value is not None:
            return json.dumps(target.data_value)
        elif target is None:
            print(f"[Warning] Input arrow target "
                  f"'{node.arrow_target}' not found")
    return None


def apply_arrow_output(node, resolver, stdout_text):
    """If the node has > or >> output arrow, parse stdout and write/append to target.

    Returns True if an output arrow was applied.
    """
    if node.arrow_direction not in ('>', '>>') or not node.arrow_target:
        return False
    target = resolver.resolve(node.arrow_target)
    if target is None:
        print(f"[Warning] Output arrow target "
              f"'{node.arrow_target}' not found")
        return False
    if not stdout_text:
        return False
    try:
        parsed = json.loads(stdout_text)
    except json.JSONDecodeError:
        parsed = stdout_text

    if node.arrow_direction == '>':
        # Replace
        target.data_value = parsed
    else:
        # Append (>>)
        if isinstance(target.data_value, list):
            if isinstance(parsed, list):
                target.data_value.extend(parsed)
            else:
                target.data_value.append(parsed)
        elif (isinstance(target.data_value, dict)
              and isinstance(parsed, dict)):
            target.data_value.update(parsed)
        else:
            # Can't meaningfully append — overwrite
            target.data_value = parsed
    return True
