#!/usr/bin/env python3
"""
Search for the SK-575 reaction specifically
"""

import sys
sys.path.append('.')
from process_reactions import parse_txt

def search_sk575():
    """Search for the SK-575 reaction."""
    reactions = parse_txt(r'c:\Git-ChemRobox\Scifinder-Data-process\dataset\Amide formation\2021-2024\Reaction_20250824_1137.txt')
    
    # Search for SK-575 or PARP1
    for rid, reaction in reactions.items():
        title = reaction.get('title', '')
        if 'SK-575' in title or 'PARP1' in title:
            print(f'Found matching reaction: {rid}')
            print(f'Title: {title}')
            print(f'Authors: {reaction.get("authors", "None")}')
            print(f'Citation: {reaction.get("citation", "None")}')
            print(f'DOI: {reaction.get("doi", "None")}')
            
            # Create reference string
            authors = reaction.get('authors', '')
            citation = reaction.get('citation', '')
            doi = reaction.get('doi', '')
            reference = ' | '.join([x for x in [title, authors, citation, doi] if x])
            
            print(f'\n=== Markdown Output ===')
            parts = [part.strip() for part in reference.split('|')]
            print(f'**Reference:**')
            if len(parts) >= 1 and parts[0]:
                print(f'  - **Title:** {parts[0]}')
            if len(parts) >= 2 and parts[1]:
                print(f'  - **Authors:** {parts[1]}')
            if len(parts) >= 3 and parts[2]:
                print(f'  - **Citation:** {parts[2]}')
            if len(parts) >= 4 and parts[3]:
                print(f'  - **DOI:** {parts[3]}')
            return
    
    print('SK-575/PARP1 reaction not found. Checking if 31-363-CAS-23416807 exists:')
    target_id = "31-363-CAS-23416807"
    if target_id in reactions:
        reaction = reactions[target_id]
        print(f'Found {target_id}:')
        print(f'Title: {reaction.get("title", "None")}')
    else:
        print(f'{target_id} not found')
        print('Available reactions:', list(reactions.keys())[:5])

if __name__ == "__main__":
    search_sk575()
