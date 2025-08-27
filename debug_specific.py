#!/usr/bin/env python3
"""
Debug the specific parsing of reaction 31-363-CAS-23416807
"""

import sys
import re
sys.path.append('.')

def debug_specific_reaction():
    """Debug parsing of the specific reaction."""
    
    with open(r'c:\Git-ChemRobox\Scifinder-Data-process\dataset\Amide formation\2021-2024\Reaction_20250824_1137.txt', 'r', encoding='utf-8', errors='ignore') as f:
        lines = [ln.rstrip('\n') for ln in f]
    
    # Find the exact line with the target CAS number
    target_cas = "31-363-CAS-23416807"
    cas_line_index = None
    
    for i, line in enumerate(lines):
        if target_cas in line:
            cas_line_index = i
            print(f"Found target CAS at line {i+1}: {line.strip()}")
            break
    
    if cas_line_index is None:
        print(f"CAS number {target_cas} not found")
        return
    
    # Now work backwards to find the title, authors, citation
    print(f"\nWorking backwards from line {cas_line_index+1}:")
    
    current_title = ""
    current_authors = ""
    current_citation = ""
    current_doi = ""
    
    # Look backwards up to 50 lines to find the title block
    for i in range(cas_line_index, max(0, cas_line_index-50), -1):
        line = lines[i].strip()
        
        if not line:
            continue
            
        print(f"  Line {i+1}: {line}")
        
        # Check for title-like lines
        if line and not line.startswith(('Steps:', 'CAS Reaction Number:', 'View All', 'Reactions (', 'Search', 'Filtered By:', 'Scheme')) and not line.startswith('By:') and not line.startswith('10.'):
            # Check if this looks like a journal citation
            if re.search(r"\(20\d{2}\).*\d+.*\d+", line):
                print(f"    -> This looks like a citation: {line}")
                if not current_citation:  # Take the first (closest) citation we find
                    current_citation = line
            elif not re.search(r"\(20\d{2}\)", line):
                print(f"    -> This looks like a title: {line}")
                if not current_title:  # Take the first (closest) title we find
                    current_title = line
        
        if line.startswith('By:'):
            print(f"    -> This is authors: {line}")
            if not current_authors:
                current_authors = line.replace('By:', '').strip()
        
        if line.startswith('10.'):
            print(f"    -> This is DOI: {line}")
            if not current_doi:
                current_doi = line
    
    print(f"\nFinal extracted values:")
    print(f"Title: {current_title}")
    print(f"Authors: {current_authors}")
    print(f"Citation: {current_citation}")
    print(f"DOI: {current_doi}")

if __name__ == "__main__":
    debug_specific_reaction()
