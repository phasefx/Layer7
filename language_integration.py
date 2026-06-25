import json
import subprocess
import tempfile
import os
from typing import Any, List, Optional

# =============================================================================
# 4. LANGUAGE INTEGRATION (How languages work together)
# =============================================================================
# This file handles the polyglot execution:
# - Cross-language calls (MCP-shaped dispatch)
# - Function-shaped headers
# - Mixed languages

class MCPDispatcher:
    """
    A generic dispatcher for executing code blocks across languages.
    Treats every executable block as an MCP-like tool that accepts JSON arguments 
    and returns JSON/STDOUT.
    """
    
    def __init__(self):
        pass

    def is_function_shaped(self, language: str, code: str) -> bool:
        """
        Determines if the code block is a single function definition.
        """
        code = code.strip()
        if language in ('javascript', 'js'):
            return code.startswith('function') or code.startswith('const') and '=>' in code
        elif language in ('python', 'py'):
            return code.startswith('def ')
        elif language in ('perl', 'pl'):
            return code.startswith('sub ')
        elif language in ('ruby', 'rb'):
            return code.startswith('def ')
        elif language in ('bash', 'sh'):
            # Bash functions are trickier, but let's assume it has () {
            return '()' in code and '{' in code
        return False

    def build_wrapper(self, language: str, code: str, is_func: bool) -> str:
        """
        Wraps the code with an MCP-like calling convention.
        If it's a function, we append code to read from a specific JSON payload
        (e.g., passed via an environment variable or a temp file) and call the function.
        For simplicity, we assume arguments are passed via JSON in a known environment variable 'LAYER7_ARGS'.
        """
        # Right now, we will just pass args via command line for procedural,
        # but for functional, we need to deserialize, call, serialize.
        # This is a placeholder for the full wrapper generation.
        if not is_func:
            return code
            
        if language in ('javascript', 'js'):
            return f"""
{code}
// MCP Wrapper
const args = JSON.parse(process.env.LAYER7_ARGS || '[]');
const result = Object.values(module.exports)[0](...args); // simplified
console.log(JSON.stringify(result));
"""
        elif language in ('python', 'py'):
            return f"""
import json
import sys
import os

{code}

# MCP Wrapper
args = json.loads(os.environ.get('LAYER7_ARGS', '[]'))
# Find the function name defined above
import inspect
func = None
for name, obj in list(locals().items()):
    if inspect.isfunction(obj) and obj.__module__ == '__main__':
        func = obj
        break
if func:
    res = func(*args)
    print(json.dumps(res))
"""
        # More languages to be added
        return code

    def execute(self, language: str, code: str, args: List[Any] = None, stdin: str = None) -> str:
        """
        Generic execution wrapper. 
        Shells out to bash, python, ruby, node, perl, etc.
        """
        if args is None:
            args = []
            
        language = (language or "bash").lower()
        is_func = self.is_function_shaped(language, code)
        wrapped_code = self.build_wrapper(language, code, is_func)
        
        # Determine the interpreter
        interpreters = {
            'javascript': 'node',
            'js': 'node',
            'python': 'python3',
            'py': 'python3',
            'ruby': 'ruby',
            'rb': 'ruby',
            'perl': 'perl',
            'bash': 'bash',
            'sh': 'sh'
        }
        interpreter = interpreters.get(language, 'bash')
        
        env = os.environ.copy()
        
        if is_func:
            env['LAYER7_ARGS'] = json.dumps(args)
            cmd_args = []
        else:
            # Procedural: pass arguments directly on command line
            cmd_args = [str(a) for a in args]
            
        # Write code to a temp file and execute
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as f:
            f.write(wrapped_code)
            temp_path = f.name
            
        try:
            cmd = [interpreter, temp_path] + cmd_args
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            stdout, stderr = process.communicate(input=stdin)
            
            if process.returncode != 0:
                print(f"[Warning] Code block failed with return code {process.returncode}")
                print(f"STDERR:\n{stderr}")
                
            return stdout.strip()
        finally:
            os.remove(temp_path)

