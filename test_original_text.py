#!/usr/bin/env python3
"""
Test script to verify original text preservation functionality
"""

import os
import sys
from process_reactions import parse_txt

def test_original_text_preservation():
    """Test the original text preservation on a small TXT file."""
    
    # Find a test TXT file
    test_files = []
    for root, dirs, files in os.walk("dataset"):
        for file in files:
            if file.endswith('.txt'):
                test_files.append(os.path.join(root, file))
                if len(test_files) >= 3:  # Just test a few files
                    break
        if len(test_files) >= 3:
            break
    
    if not test_files:
        print("No TXT files found for testing")
        return
    
    print(f"Testing original text preservation on {len(test_files)} files:")
    for txt_file in test_files:
        print(f"\n--- Testing: {txt_file} ---")
        
        try:
            reactions = parse_txt(txt_file)
            print(f"Found {len(reactions)} reactions")
            
            for rid, reaction in reactions.items():
                print(f"\nReaction {rid}:")
                print(f"  - Reagents: {len(reaction.get('reagents', []))}")
                print(f"  - Catalysts: {len(reaction.get('catalysts', []))}")
                print(f"  - Solvents: {len(reaction.get('solvents', []))}")
                
                # Check original text
                original_text = reaction.get('original_text', [])
                print(f"  - Original text lines: {len(original_text)}")
                
                if original_text:
                    print("  - First few original lines:")
                    for i, line in enumerate(original_text[:3]):
                        print(f"    {i+1}: {line.strip()}")
                    if len(original_text) > 3:
                        print(f"    ... and {len(original_text) - 3} more lines")
                else:
                    print("  - No original text captured!")
                
                # Only show first reaction for brevity
                break
                
        except Exception as e:
            print(f"Error processing {txt_file}: {e}")

if __name__ == "__main__":
    test_original_text_preservation()
