#!/usr/bin/env python3
"""
Test the title extraction fix with the specific example
"""

import sys
import os
sys.path.append('.')
from process_reactions import parse_txt

def test_title_extraction():
    """Test the title extraction with the sample file."""
    
    txt_file = r"c:\Git-ChemRobox\Scifinder-Data-process\dataset\Amide formation\2021-2024\Reaction_20250824_1137.txt"
    
    if not os.path.exists(txt_file):
        print(f"File not found: {txt_file}")
        return
    
    # Parse the TXT file
    reactions = parse_txt(txt_file)
    
    # Look for the specific reaction ID mentioned in the user's selection
    target_id = "31-363-CAS-23416807"
    
    if target_id in reactions:
        reaction = reactions[target_id]
        print(f"=== Reaction ID: {target_id} ===")
        print(f"Title: {reaction.get('title', 'None')}")
        print(f"Authors: {reaction.get('authors', 'None')}")
        print(f"Citation: {reaction.get('citation', 'None')}")
        print(f"DOI: {reaction.get('doi', 'None')}")
        
        # Create reference string like the markdown generator does
        title = reaction.get('title', '')
        authors = reaction.get('authors', '')
        citation = reaction.get('citation', '')
        doi = reaction.get('doi', '')
        reference = ' | '.join([x for x in [title, authors, citation, doi] if x])
        print(f"\nReference string: {reference}")
        
        # Show what markdown would look like
        parts = [part.strip() for part in reference.split('|')]
        print(f"\n=== Markdown Output ===")
        print(f"**Reference:**")
        if len(parts) >= 1 and parts[0]:
            print(f"  - **Title:** {parts[0]}")
        if len(parts) >= 2 and parts[1]:
            print(f"  - **Authors:** {parts[1]}")
        if len(parts) >= 3 and parts[2]:
            print(f"  - **Citation:** {parts[2]}")
        if len(parts) >= 4 and parts[3]:
            print(f"  - **DOI:** {parts[3]}")
    else:
        print(f"Reaction ID {target_id} not found in parsed reactions")
        print(f"Available IDs: {list(reactions.keys())[:10]}...")  # Show first 10 IDs

if __name__ == "__main__":
    test_title_extraction()
