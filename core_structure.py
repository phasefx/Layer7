import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# =============================================================================
# 1. CORE STRUCTURE (What Layer7 is made of)
# =============================================================================
# This file handles the atomic primitives:
# - Parsing markdown into structural blocks
# - Header variables (JSON, YAML, inline shorthand)
# - Code blocks
# - Redirection arrows (<, >, <<, >>)

@dataclass
class HeaderNode:
    """Represents a Markdown header and its associated content."""
    level: int          # 1 for #, 2 for ##, up to 6
    title: str          # The normalized/clean text of the header
    parent: Optional['HeaderNode'] = None
    children: List['HeaderNode'] = field(default_factory=list)
    
    # Payload of the header
    inline_var_type: Optional[str] = None  # e.g., '[]', '{}', 'string'
    code_lang: Optional[str] = None        # e.g., 'Python', 'JSON', 'composition'
    code_content: Optional[str] = None     # The text inside the fenced block
    
    # Redirection arrows
    arrow_direction: Optional[str] = None  # '<', '<<', '>', '>>'
    arrow_target: Optional[str] = None     # The header name it points to
    
    # Internal state for execution
    data_value: Any = None
    
    def get_full_path(self) -> List[str]:
        """Returns the hierarchical path of titles to this node."""
        path = []
        curr = self
        while curr:
            path.insert(0, curr.title)
            curr = curr.parent
        return path

def parse_header_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parses a markdown header line.
    Extracts level, title, arrows, arrow_targets, and inline variables.
    """
    header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
    if not header_match:
        return None
        
    level = len(header_match.group(1))
    text = header_match.group(2).strip()
    
    result = {
        "level": level,
        "title": text,
        "arrow_direction": None,
        "arrow_target": None,
        "inline_var_type": None
    }
    
    # 1. Extract Redirection Arrows
    # Looks for things like: <===, <<=, ===>, ===>>, <-, ->, etc.
    # Outermost glyph determines direction.
    arrow_pattern = r'\s+(<{1,2}[-=]*|[-=]*>{1,2})\s+(.+)$'
    arrow_match = re.search(arrow_pattern, text)
    if arrow_match:
        arrow_str = arrow_match.group(1)
        target = arrow_match.group(2).strip()
        
        # Determine canonical direction
        if '<<' in arrow_str:
            result['arrow_direction'] = '<<'
        elif '<' in arrow_str:
            result['arrow_direction'] = '<'
        elif '>>' in arrow_str:
            result['arrow_direction'] = '>>'
        elif '>' in arrow_str:
            result['arrow_direction'] = '>'
            
        result['arrow_target'] = target
        text = text[:arrow_match.start()].strip() # Remove arrow part from title
        
    # 2. Extract Inline Variables from the remaining title
    # Matches [] or {} or string at the end of the header
    inline_var_pattern = r'\s+(\[\]|\{\}|string)$'
    inline_match = re.search(inline_var_pattern, text)
    if inline_match:
        result['inline_var_type'] = inline_match.group(1)
        text = text[:inline_match.start()].strip() # Remove inline var from title
        
    result['title'] = text
    return result

class Layer7Parser:
    """Parses a Layer7 markdown file into a tree of HeaderNodes."""
    
    def __init__(self):
        self.root = HeaderNode(level=0, title="ROOT")
        self.current_path = [self.root]
        self.all_nodes = []
        
    def parse_text(self, markdown_text: str) -> HeaderNode:
        lines = markdown_text.splitlines()
        
        in_code_block = False
        current_node = self.root
        code_lines = []
        code_lang = None
        
        for line in lines:
            if in_code_block:
                if line.strip().startswith('```'):
                    # End of code block
                    current_node.code_lang = code_lang
                    current_node.code_content = "\n".join(code_lines)
                    in_code_block = False
                    code_lines = []
                    code_lang = None
                else:
                    code_lines.append(line)
                continue
                
            if line.strip().startswith('```'):
                # Start of code block
                in_code_block = True
                lang_match = re.match(r'^```(\w+)', line.strip())
                if lang_match:
                    code_lang = lang_match.group(1).lower()
                else:
                    code_lang = "text"
                continue
                
            header_data = parse_header_line(line)
            if header_data:
                # We found a header
                level = header_data['level']
                
                # Pop nodes from current_path until we find the right parent
                while len(self.current_path) > 1 and self.current_path[-1].level >= level:
                    self.current_path.pop()
                    
                parent = self.current_path[-1]
                
                new_node = HeaderNode(
                    level=level,
                    title=header_data['title'],
                    parent=parent,
                    arrow_direction=header_data['arrow_direction'],
                    arrow_target=header_data['arrow_target'],
                    inline_var_type=header_data['inline_var_type']
                )
                
                # Setup inline data slots early if specified
                if new_node.inline_var_type == '[]':
                    new_node.data_value = []
                elif new_node.inline_var_type == '{}':
                    new_node.data_value = {}
                elif new_node.inline_var_type == 'string':
                    new_node.data_value = ""
                
                parent.children.append(new_node)
                self.current_path.append(new_node)
                self.all_nodes.append(new_node)
                current_node = new_node
                continue
                
        return self.root

