# =============================================================================
# 2. ADDRESSING & NAMING (How you reference things)
# =============================================================================
# This file handles the namespace and finding things:
# - Nested headers (disambiguation)
# - Cross-file references
# - Fuzzy matching (shape-insensitive identifier resolution)

import re
import itertools
from typing import List, Dict, Optional, Any

def normalize_identifier(name: str) -> str:
    """
    Fuzzy matching preparation.
    Collapses spaces, underscores, colons, dots, and makes lowercase.
    Example: 'Functional Example' -> 'functionalexample'
    Example: 'Code_blocks::Functional_Example' -> 'codeblocksfunctionalexample'
    """
    return re.sub(r'[\s_:\.]+', '', name).lower()

class ResolutionError(Exception):
    pass

class AddressResolver:
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        # Maps normalized name -> Node
        # If a name maps to None, it means the name is ambiguous (collision).
        self.registry: Dict[str, Optional[Any]] = {}

    def register_node(self, node: Any, filename: str = None):
        """
        Generate all valid address combinations for a node and register them.
        If a path is ['Core Structure', 'Header Variables', 'JSON Example'],
        the leaf is always included. The prefixes are any combination of the parents.
        """
        # Skip ROOT
        path_titles = [t for t in node.get_full_path() if t != "ROOT"]
        if not path_titles:
            return

        leaf = path_titles[-1]
        parents = path_titles[:-1]

        # We also want to allow prepending the filename for cross-file references.
        # But we only include the filename base, e.g., 'layer7' instead of 'layer7.md'
        if filename:
            base_filename = re.sub(r'\.[^.]+$', '', filename)
            parents.insert(0, base_filename)

        normalized_leaf = normalize_identifier(leaf)

        # Generate all combinations of parents (including empty)
        parent_combinations = []
        for i in range(len(parents) + 1):
            for combo in itertools.combinations(parents, i):
                parent_combinations.append(combo)

        if self.strict_mode:
            # Register exact paths (e.g. leaf, or parent + " " + leaf)
            for combo in parent_combinations:
                exact_name = " ".join(combo + (leaf,))
                if exact_name in self.registry:
                    if self.registry[exact_name] is not node:
                        self.registry[exact_name] = None
                else:
                    self.registry[exact_name] = node
        else:
            for combo in parent_combinations:
                normalized_combo = [normalize_identifier(p) for p in combo]
                # Concatenate them all together
                full_normalized_name = "".join(normalized_combo) + normalized_leaf

                if full_normalized_name in self.registry:
                    # Collision detected!
                    if self.registry[full_normalized_name] is not node:
                        self.registry[full_normalized_name] = None # Mark as ambiguous
                else:
                    self.registry[full_normalized_name] = node

    def resolve(self, reference: str) -> Optional[Any]:
        """
        Find the matching node based on the reference string.
        Returns None if not found or if ambiguous (in normal mode).
        In strict mode, raises ResolutionError if missing or ambiguous.
        """
        if self.strict_mode:
            # Exact match
            node = self.registry.get(reference)
            if node is None:
                if reference in self.registry:
                    raise ResolutionError(f"Ambiguous reference: '{reference}'")
                raise ResolutionError(f"Reference not found: '{reference}'")
            return node

        normalized_ref = normalize_identifier(reference)
        return self.registry.get(normalized_ref)

