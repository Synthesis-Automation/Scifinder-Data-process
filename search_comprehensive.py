#!/usr/bin/env python3
"""
Search for any mention of SK-575 or PARP1 in the parsed data
"""

import sys
sys.path.append('.')
from process_reactions import parse_txt

def search_comprehensive():
    """Search comprehensively for SK-575 or PARP1."""
    reactions = parse_txt(r'c:\Git-ChemRobox\Scifinder-Data-process\dataset\Amide formation\2021-2024\Reaction_20250824_1137.txt')
    
    print(f"Total reactions parsed: {len(reactions)}")
    
    # Search for SK-575 or PARP1 in any field
    found_reactions = []
    for rid, reaction in reactions.items():
        # Check all text fields
        all_text = " ".join([
            str(reaction.get('title', '')),
            str(reaction.get('authors', '')),
            str(reaction.get('citation', '')),
            str(reaction.get('doi', '')),
            " ".join(reaction.get('all_condition_lines', [])),
            " ".join(reaction.get('original_text', []))
        ]).lower()
        
        if 'sk-575' in all_text or 'parp1' in all_text or 'parp-1' in all_text:
            found_reactions.append((rid, reaction))
    
    if found_reactions:
        print(f"\nFound {len(found_reactions)} reactions with SK-575 or PARP1:")
        for rid, reaction in found_reactions:
            print(f"\n=== {rid} ===")
            print(f"Title: {reaction.get('title', 'None')}")
            print(f"Authors: {reaction.get('authors', 'None')}")
            print(f"Citation: {reaction.get('citation', 'None')}")
            print(f"DOI: {reaction.get('doi', 'None')}")
            if reaction.get('original_text'):
                print(f"Original text (first 5 lines): {reaction['original_text'][:5]}")
    else:
        print("\nNo reactions found with SK-575 or PARP1")
        
        # Let's check a specific reaction ID that should have this
        # Look at the text around line 8930-8945
        print("\nLet's look at specific reaction 31-363-CAS-23416807:")
        if "31-363-CAS-23416807" in reactions:
            reaction = reactions["31-363-CAS-23416807"]
            print(f"Title: {reaction.get('title', 'None')}")
            print(f"Authors: {reaction.get('authors', 'None')}")
            print(f"Citation: {reaction.get('citation', 'None')}")
            print(f"DOI: {reaction.get('doi', 'None')}")
            if reaction.get('original_text'):
                print(f"Original text: {reaction['original_text']}")
        else:
            print("Reaction 31-363-CAS-23416807 not found")

if __name__ == "__main__":
    search_comprehensive()
