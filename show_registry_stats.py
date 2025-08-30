#!/usr/bin/env python3
"""
Script to show statistics for the expanded CAS registry.
"""

import json
from collections import defaultdict

def show_registry_statistics():
    """Load and show statistics for the current registry."""
    
    registry_file = 'cas_registry_merged.jsonl'
    entries = []
    
    # Load all entries
    with open(registry_file, 'r', encoding='utf-8') as f:
        for line in f:
            entries.append(json.loads(line.strip()))
    
    # Generate statistics
    type_counts = defaultdict(int)
    total_with_abbreviations = 0
    source_counts = defaultdict(int)
    
    for entry in entries:
        # Handle compound type (including None values)
        compound_type = entry.get('compound_type', 'unknown')
        if compound_type is None:
            compound_type = 'unknown'
        type_counts[compound_type] += 1
        
        # Count abbreviations
        abbreviation = entry.get('abbreviation', '')
        if abbreviation and abbreviation.strip():
            total_with_abbreviations += 1
        
        # Count sources
        sources = entry.get('sources', [])
        for source in sources:
            source_counts[source] += 1
    
    # Show statistics
    print(f"=== CAS Registry Statistics ===")
    print(f"Total entries: {len(entries)}")
    print(f"Entries with abbreviations: {total_with_abbreviations}")
    
    print(f"\nBy compound type:")
    for compound_type, count in sorted(type_counts.items()):
        print(f"  {compound_type}: {count}")
    
    print(f"\nBy source:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")
    
    # Show some examples of newly added entries
    print(f"\nRecent additions (last 10 entries):")
    for i, entry in enumerate(entries[-10:], 1):
        cas = entry.get('cas', 'N/A')
        name = entry.get('name', 'N/A')
        abbrev = entry.get('abbreviation', '')
        comp_type = entry.get('compound_type', 'unknown')
        if comp_type is None:
            comp_type = 'unknown'
        
        abbrev_str = f" ({abbrev})" if abbrev else ""
        print(f"  {len(entries)-10+i:3d}. {cas} - {name}{abbrev_str} [{comp_type}]")

if __name__ == "__main__":
    show_registry_statistics()
