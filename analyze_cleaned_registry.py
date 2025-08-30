#!/usr/bin/env python3
"""
Verify the cleaned CAS registry and show statistics about compound types and abbreviations
"""

import json
from collections import Counter

def analyze_cleaned_registry():
    """Analyze the cleaned CAS registry file."""
    
    print("Analyzing cleaned CAS registry...")
    
    entries = []
    compound_types = Counter()
    abbreviations = []
    
    with open('cas_registry_merged.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            entry = json.loads(line)
            entries.append(entry)
            
            # Count compound types
            compound_type = entry.get('compound_type', 'unknown')
            compound_types[compound_type] += 1
            
            # Collect abbreviations
            abbrev = entry.get('abbreviation', '')
            if abbrev:
                abbreviations.append(abbrev)
    
    print(f"\nTotal entries: {len(entries)}")
    
    # Check if 'role' key still exists anywhere
    has_role = any('role' in entry for entry in entries)
    print(f"Any 'role' keys remaining: {has_role}")
    
    print(f"\nCompound types distribution:")
    for compound_type, count in compound_types.most_common():
        print(f"  {compound_type}: {count}")
    
    print(f"\nAbbreviations found: {len([a for a in abbreviations if a])}")
    
    # Show sample entries for each compound type
    print(f"\nSample entries by compound type:")
    samples_shown = set()
    for entry in entries:
        compound_type = entry.get('compound_type', 'unknown')
        if compound_type not in samples_shown:
            print(f"\n  {compound_type}:")
            print(f"    CAS: {entry.get('cas', '')}")
            print(f"    Name: {entry.get('name', '')}")
            print(f"    Abbreviation: {entry.get('abbreviation', '')}")
            samples_shown.add(compound_type)
            
            if len(samples_shown) >= 3:  # Show max 3 samples
                break
    
    # Show some interesting abbreviations
    non_empty_abbrevs = [a for a in abbreviations if a and a.strip()]
    if non_empty_abbrevs:
        print(f"\nSample abbreviations:")
        for abbrev in non_empty_abbrevs[:10]:  # Show first 10
            print(f"  - {abbrev}")

if __name__ == "__main__":
    analyze_cleaned_registry()
