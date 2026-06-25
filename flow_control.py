# =============================================================================
# 3. FLOW CONTROL (How things execute)
# =============================================================================
# This file handles sequencing and control flow:
# - Compositions (orchestration for branching/looping)
# - Sentinels (SKIP short-circuiting)
# - No-composition default (linear execution)

import re

class CompositionEngine:
    """
    Executes flow control logic based on Steps and Routing headers.
    """
    def __init__(self, resolver, dispatcher):
        self.resolver = resolver
        self.dispatcher = dispatcher

    def parse_steps(self, steps_text: str):
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

    def parse_routing(self, routing_text: str):
        """
        Parses english-like routing rules (e.g. "Repeat step 3 until SKIP, then goto step 2").
        For now, returns a simple AST or throws a warning for complex unrecognized ones.
        """
        # Placeholder for real routing logic.
        rules = []
        for line in routing_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if "until SKIP" in line:
                # Basic parsing
                rules.append({"type": "repeat_until_skip", "raw": line})
        return rules

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
                # Execute it
                current_val = self.dispatcher.execute(
                    language=node.code_lang,
                    code=node.code_content,
                    args=[current_val] if current_val else []
                )
                if current_val == "SKIP":
                    return "SKIP"
            elif node.data_value is not None:
                # Or just fetch its data
                current_val = node.data_value
                
        return current_val

    def execute_composition(self, code_content: str):
        """
        Executes a composition DSL string.
        """
        # A quick hack to parse out Steps and Routing from the composition text
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
        routing = self.parse_routing(routing_text)
        
        # Default top-to-bottom execution if no explicit complex routing
        for step_num in sorted(steps.keys()):
            chain = steps[step_num]
            res = self.execute_chain(chain)
            if res == "SKIP":
                print(f"Received SKIP at step {step_num}")
                # handle routing rules for SKIP...
