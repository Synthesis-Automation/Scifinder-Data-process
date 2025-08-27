#!/usr/bin/env python3
"""
Test how parse_txt() actually processes the SK-575 reaction
"""

import sys
sys.path.append('.')
from process_reactions import parse_txt

def test_sk575_parsing():
    """Test parsing the specific SK-575 reaction."""
    
    # Parse the file
    reactions = parse_txt(r'c:\Git-ChemRobox\Scifinder-Data-process\dataset\Amide formation\2021-2024\Reaction_20250824_1137.txt')
    
    # Look for our target reaction
    target_cas = "31-363-CAS-23416807"
    
    if target_cas in reactions:
        reaction = reactions[target_cas]
        print(f"Found reaction {target_cas}:")
        print(f"  Title: {reaction.get('title', 'NOT SET')}")
        print(f"  Authors: {reaction.get('authors', 'NOT SET')}")
        print(f"  Citation: {reaction.get('citation', 'NOT SET')}")
        print(f"  DOI: {reaction.get('doi', 'NOT SET')}")
        print(f"  Yield: {reaction.get('txt_yield', 'NOT SET')}")
        
        # Print the original text to see what was captured
        if 'original_text' in reaction:
            print(f"\nOriginal text lines captured:")
            for i, line in enumerate(reaction['original_text'][:10]):  # First 10 lines
                print(f"    {i+1}: {line}")
    else:
        print(f"Reaction {target_cas} not found")
        print(f"Available reactions: {list(reactions.keys())[:10]}...")  # First 10
        
    # Also check the reaction that comes before it to see if it has the correct title
    prev_cas = "31-614-CAS-31632737"  # This was in the debug output before our target
    if prev_cas in reactions:
        prev_reaction = reactions[prev_cas]
        print(f"\nPrevious reaction {prev_cas}:")
        print(f"  Title: {prev_reaction.get('title', 'NOT SET')}")
        print(f"  Authors: {prev_reaction.get('authors', 'NOT SET')}")

if __name__ == "__main__":
    test_sk575_parsing()
