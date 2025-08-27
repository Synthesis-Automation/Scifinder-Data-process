#!/usr/bin/env python3
"""
Look at the exact text around the SK-575 reaction
"""

def examine_sk575_section():
    """Look at the text around the SK-575 reaction."""
    with open(r'c:\Git-ChemRobox\Scifinder-Data-process\dataset\Amide formation\2021-2024\Reaction_20250824_1137.txt', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Find the line with "Discovery of SK-575"
    for i, line in enumerate(lines):
        if 'Discovery of SK-575' in line:
            print(f"Found SK-575 title at line {i+1}: {line.strip()}")
            
            # Show context around this line
            start = max(0, i-10)
            end = min(len(lines), i+20)
            
            print(f"\nContext (lines {start+1} to {end}):")
            for j in range(start, end):
                marker = ">>> " if j == i else "    "
                print(f"{marker}{j+1:4d}: {lines[j].rstrip()}")
            
            # Look for the CAS reaction number that follows
            for j in range(i, min(len(lines), i+50)):
                if 'CAS Reaction Number:' in lines[j]:
                    print(f"\nFound CAS number at line {j+1}: {lines[j].strip()}")
                    break
            break
    else:
        print("SK-575 title not found in file")

if __name__ == "__main__":
    examine_sk575_section()
