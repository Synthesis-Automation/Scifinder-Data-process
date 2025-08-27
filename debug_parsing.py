#!/usr/bin/env python3
"""
Debug the parsing issue
"""

import sys
import traceback
sys.path.append('.')

def debug_parsing():
    """Debug the parsing issue."""
    try:
        from process_reactions import parse_txt
        
        print("Starting to parse TXT file...")
        reactions = parse_txt(r'c:\Git-ChemRobox\Scifinder-Data-process\dataset\Amide formation\2021-2024\Reaction_20250824_1137.txt')
        print(f"Parsed {len(reactions)} reactions")
        
        if reactions:
            print("First few reaction IDs:")
            for i, (rid, reaction) in enumerate(reactions.items()):
                if i >= 3:
                    break
                print(f"  {rid}: {reaction.get('title', 'No title')[:60]}...")
        else:
            print("No reactions found")
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_parsing()
