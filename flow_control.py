# =============================================================================
# 3. FLOW CONTROL (How things execute)
# =============================================================================
# This file handles sequencing and control flow:
# - Compositions (orchestration for branching/looping)
# - Sentinels (SKIP short-circuiting)
# - No-composition default (linear execution)

import re
import json
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List
from language_integration import (
    ExecutionResult,
    build_state,
    get_arrow_input_data,
    apply_arrow_output,
)

@dataclass
class RoutingRule:
    step: int                  # which step this rule governs
    repeat: bool               # True = loop; False = run once, still catch sentinel
    sentinel: str              # what signal to catch ("SKIP")
    then_goto: Optional[int]   # where to jump after sentinel (None = exit composition)

class CompositionEngine:
    """
    Executes flow control logic based on Steps and Routing headers.
    """
    def __init__(self, resolver, dispatcher, all_nodes=None):
        self.resolver = resolver
        self.dispatcher = dispatcher
        self.all_nodes = all_nodes or []

    def parse_steps(self, steps_text: str) -> Dict[int, List[str]]:
        """
        Parses a numbered list of steps, handling chains like:
        1. `NodeA` => `NodeB`
        """
        steps = {}
        for line in steps_text.splitlines():
            line = line.strip()
            # Match "1. `NodeA` => `NodeB`" or "1. NodeA"
            match = re.match(r'^(\d+)\.\s+(.+)$', line)
            if match:
                step_num = int(match.group(1))
                chain_str = match.group(2)
                # Split by => and remove backticks
                chain = [c.strip(" `") for c in chain_str.split("=>")]
                steps[step_num] = chain
        return steps

    def parse_routing(self, routing_text: str) -> Tuple[Dict[int, RoutingRule], List[str]]:
        """
        Parses english-like routing rules (e.g. "Repeat step 3 until SKIP, then goto step 2").
        Returns a simple AST and parse warnings for unrecognized lines.
        """
        rules = {}
        warnings = []
        for line in routing_text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Pattern 1: Repeat step X until Y[, then goto step Z].
            m_repeat = re.match(r'^Repeat step (\d+) until ([a-zA-Z_]+)(?:, then goto step (\d+))?\.?$', line, re.IGNORECASE)
            if m_repeat:
                step = int(m_repeat.group(1))
                sentinel = m_repeat.group(2).upper()
                then_goto = int(m_repeat.group(3)) if m_repeat.group(3) else None
                if step in rules:
                    warnings.append(f"Multiple routing rules for step {step}. Overwriting.")
                rules[step] = RoutingRule(step=step, repeat=True, sentinel=sentinel, then_goto=then_goto)
                continue

            # Pattern 2: If step X returns Y, goto step Z.
            m_if = re.match(r'^If step (\d+) returns ([a-zA-Z_]+), goto step (\d+)\.?$', line, re.IGNORECASE)
            if m_if:
                step = int(m_if.group(1))
                sentinel = m_if.group(2).upper()
                then_goto = int(m_if.group(3))
                if step in rules:
                    warnings.append(f"Multiple routing rules for step {step}. Overwriting.")
                rules[step] = RoutingRule(step=step, repeat=False, sentinel=sentinel, then_goto=then_goto)
                continue

            # If we get here, it didn't match the expected syntax
            warnings.append(f"Unrecognized routing rule: '{line}'")

        return rules, warnings

    def validate_routing(self, steps: Dict[int, List[str]], routing_rules: Dict[int, RoutingRule], parse_warnings: List[str]) -> Dict[int, RoutingRule]:
        warnings = list(parse_warnings)
        for rule in routing_rules.values():
            # Does the rule's target step exist?
            if rule.step not in steps:
                warnings.append(f"Routing references step {rule.step}, which doesn't exist in Steps")

            # Does the then_goto step exist?
            if rule.then_goto is not None and rule.then_goto not in steps:
                warnings.append(f"Routing 'goto step {rule.then_goto}' references a nonexistent step")

        for w in warnings:
            print(f"[Warning] {w}")

        # Filter out rules referencing nonexistent steps so they don't crash
        # the dispatch loop's step_nums.index() call.
        return {k: v for k, v in routing_rules.items() if k in steps
                and (v.then_goto is None or v.then_goto in steps)}

    def execute_chain(self, chain: list):
        """
        Executes a chain of nodes: NodeA => NodeB
        Output of A becomes input of B.
        Returns the final output or "SKIP" if sentineled early.
        """
        current_val = None
        for ref in chain:
            node = self.resolver.resolve(ref)
            if node is None:
                print(f"[Warning] Composition Step: Cannot resolve reference '{ref}'.")
                continue
            elif node == "AMBIGUOUS": # Assuming resolver handles this
                print(f"[Warning] Composition Step: Ambiguous reference '{ref}'.")
                continue

            # If the node has executable code
            if node.code_content:
                print(f"  ⎈▶ {node.title}  ({node.code_lang})")

                # Build state + arrow input using shared helpers
                state = build_state(self.all_nodes)
                stdin_data = get_arrow_input_data(node, self.resolver)

                # Execute it
                res = self.dispatcher.execute(
                    language=node.code_lang,
                    code=node.code_content,
                    args=[current_val] if current_val else [],
                    stdin=stdin_data,
                    state=state
                )

                # Check for errors as in layer7.py
                if not res.success:
                    import sys
                    print(f"\n[Fatal] '{node.title}' exited with code {res.returncode}")
                    if res.stderr:
                        print(res.stderr)
                    sys.exit(res.returncode)

                if res.stdout:
                    # Output arrow logic (shared helper)
                    apply_arrow_output(node, self.resolver, res.stdout)

                    if node.arrow_direction not in ('>', '>>'):
                        print(res.stdout, end="" if res.stdout.endswith("\n") else "\n")

                current_val = res.stdout.strip() if res.stdout else ""

                if current_val == "SKIP":
                    return "SKIP"

            elif node.data_value is not None:
                # Or just fetch its data (e.g. JSON/YAML slot)
                current_val = json.dumps(node.data_value) if not isinstance(node.data_value, str) else node.data_value

        return current_val

    def execute_composition(self, code_content: str):
        """
        Executes a composition DSL string.
        """
        steps_text = ""
        routing_text = ""
        mode = None

        for line in code_content.splitlines():
            if line.lower().startswith("#### steps"):
                mode = "steps"
                continue
            elif line.lower().startswith("#### routing"):
                mode = "routing"
                continue

            if mode == "steps":
                steps_text += line + "\n"
            elif mode == "routing":
                routing_text += line + "\n"

        steps = self.parse_steps(steps_text)
        raw_rules, parse_warnings = self.parse_routing(routing_text)
        routing_rules = self.validate_routing(steps, raw_rules, parse_warnings)

        step_nums = sorted(steps.keys())
        if not step_nums:
            return

        cursor = 0
        while 0 <= cursor < len(step_nums):
            step = step_nums[cursor]
            chain = steps[step]
            rule = routing_rules.get(step)

            if rule and rule.repeat:
                # ── Repeat-until mode ────────────────────────────────
                while True:
                    result = self.execute_chain(chain)
                    if result == rule.sentinel:
                        # Sentinel caught — follow then_goto or exit
                        if rule.then_goto is not None:
                            # Note: Calling index() is O(N), but this is fine
                            # given the 7-chunk friction principle (N <= 7).
                            cursor = step_nums.index(rule.then_goto)
                        else:
                            return                 # exit composition
                        break
                    # No sentinel → loop again

            else:
                # ── Normal: execute once ─────────────────────────────
                result = self.execute_chain(chain)

                if result == "SKIP":
                    if rule and rule.then_goto is not None:
                        # SKIP override without repeat (the "if step N returns SKIP, goto M" form)
                        cursor = step_nums.index(rule.then_goto)
                        continue
                    else:
                        # Implicit exit condition if no rule specifies what to do on SKIP
                        return                     # default: SKIP exits composition

                # Advance to next step
                cursor += 1
