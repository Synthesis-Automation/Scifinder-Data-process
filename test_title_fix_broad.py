#!/usr/bin/env python3
"""
Test the fixed parsing logic on multiple reactions to ensure titles are correct
"""

import sys
sys.path.append('.')
from process_reactions import parse_txt

def test_multiple_reactions():
    """Test parsing multiple reactions to verify titles are correct."""
    
    # Parse the file
    reactions = parse_txt(r'c:\Git-ChemRobox\Scifinder-Data-process\dataset\Amide formation\2021-2024\Reaction_20250824_1137.txt')
    
    print(f"Total reactions parsed: {len(reactions)}")
    
    # Test a few different reactions
    test_cases = [
        "31-363-CAS-23416807",  # SK-575 reaction
        "31-614-CAS-31632737",  # Previous reaction
    ]
    
    for cas in test_cases:
        if cas in reactions:
            reaction = reactions[cas]
            print(f"\nReaction {cas}:")
            print(f"  Title: {reaction.get('title', 'NOT SET')[:80]}...")
            print(f"  Authors: {reaction.get('authors', 'NOT SET')}")
            print(f"  Year from citation: {reaction.get('citation', '')[:30]}...")
            print(f"  DOI: {reaction.get('doi', 'NOT SET')}")
            print(f"  Yield: {reaction.get('txt_yield', 'NOT SET')}")
        else:
            print(f"\nReaction {cas}: NOT FOUND")
    
    # Check that we have reasonable distribution of titles (not all the same)
    titles = [r.get('title', '') for r in reactions.values() if r.get('title')]
    unique_titles = set(titles)
    print(f"\nTitle statistics:")
    print(f"  Total reactions with titles: {len(titles)}")
    print(f"  Unique titles: {len(unique_titles)}")
    print(f"  Title diversity ratio: {len(unique_titles)/len(titles) if titles else 0:.2f}")
    
    # Show a few sample titles
    sample_titles = list(unique_titles)[:5]
    print(f"\nSample titles:")
    for i, title in enumerate(sample_titles, 1):
        print(f"  {i}. {title[:80]}...")

if __name__ == "__main__":
    test_multiple_reactions()
