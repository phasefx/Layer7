#!/usr/bin/env python3
# =============================================================================
# LAYER 7 ENGINE (v0.8)
# =============================================================================
# Main orchestrator. 
# Ties together Core Structure, Addressing, Flow Control, and Language Integration.

import argparse
import sys
import json
import os

from core_structure import Layer7Parser
from addressing import AddressResolver
from flow_control import CompositionEngine
from language_integration import MCPDispatcher

def execute_linear(nodes, dispatcher, resolver):
    """
    Default baseline flow: top to bottom.
    Executes code blocks and parses data blocks as they are encountered.
    """
    for node in nodes:
        if node.code_content:
            lang = (node.code_lang or "").lower()
            if lang == "composition":
                # Execute it as a composition DSL
                print(f"[Executing Composition]: {node.title}")
                comp_engine = CompositionEngine(resolver, dispatcher)
                comp_engine.execute_composition(node.code_content)
            elif lang in ("json", "yaml"):
                # Data blocks
                try:
                    if lang == "json":
                        node.data_value = json.loads(node.code_content)
                    else:
                        pass # YAML support left as an exercise or imported via PyYAML
                except Exception as e:
                    print(f"[Warning] Failed to parse data block at '{node.title}': {e}")
            else:
                # Normal code block execution
                print(f"[Executing Block]: {node.title} ({lang})")
                out = dispatcher.execute(lang, node.code_content)
                if out:
                    print(out)

def main():
    parser = argparse.ArgumentParser(description="Layer7 Engine (v0.8)")
    parser.add_argument("file", help="The Layer7 Markdown file to execute")
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        sys.exit(1)
        
    print(f"Starting Layer7 Engine for {args.file}...")
    
    # 1. Parse markdown file (core_structure)
    with open(args.file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()
        
    l7_parser = Layer7Parser()
    root_node = l7_parser.parse_text(markdown_text)
    all_nodes = l7_parser.all_nodes
    
    # 2. Register addresses (addressing)
    resolver = AddressResolver()
    for node in all_nodes:
        resolver.register_node(node, filename=os.path.basename(args.file))
        
    # 3. Execution (flow_control & language_integration)
    dispatcher = MCPDispatcher()
    
    # Check if there is an explicit top-level composition
    compositions = [n for n in all_nodes if n.code_lang == "composition"]
    
    if compositions:
        comp_engine = CompositionEngine(resolver, dispatcher)
        for comp in compositions:
            print(f"[Starting Composition]: {comp.title}")
            comp_engine.execute_composition(comp.code_content)
    else:
        # No composition, execute linearly
        execute_linear(all_nodes, dispatcher, resolver)

if __name__ == "__main__":
    main()
