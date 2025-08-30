#!/usr/bin/env python3
"""
Add missing chemicals to the CAS registry.
"""

import json

def add_missing_chemicals():
    """Add chemicals that were identified as missing from reaction processing."""
    
    registry_file = 'cas_registry_merged.jsonl'
    
    # Load existing registry
    existing_entries = []
    existing_cas = set()
    
    with open(registry_file, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            existing_entries.append(entry)
            existing_cas.add(entry.get('cas', ''))
    
    print(f"Loaded {len(existing_entries)} existing entries")
    
    # Missing chemicals to add
    missing_chemicals = [
        {
            'cas': '122-52-1',
            'name': 'Triethyl phosphite',
            'abbreviation': 'P(OEt)3',
            'compound_type': 'reductant',
            'sources': ['manual_correction']
        },
        # Add other missing chemicals if found
    ]
    
    added_count = 0
    
    for chemical in missing_chemicals:
        cas = chemical['cas']
        if cas not in existing_cas:
            entry = {
                'cas': cas,
                'name': chemical['name'],
                'abbreviation': chemical['abbreviation'],
                'generic_core': None,
                'category_hint': None,
                'token': None,
                'compound_type': chemical['compound_type'],
                'sources': chemical['sources']
            }
            existing_entries.append(entry)
            existing_cas.add(cas)
            added_count += 1
            print(f"Added: {cas} - {chemical['name']} ({chemical['abbreviation']}) [{chemical['compound_type']}]")
        else:
            print(f"Already exists: {cas} - {chemical['name']}")
    
    # Save updated registry
    with open(registry_file, 'w', encoding='utf-8') as f:
        for entry in existing_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\nAdded {added_count} new chemicals")
    print(f"Total registry size: {len(existing_entries)}")

if __name__ == "__main__":
    add_missing_chemicals()
