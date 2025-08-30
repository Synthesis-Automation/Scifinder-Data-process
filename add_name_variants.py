#!/usr/bin/env python3
"""
Add alternative name entries for chemicals with naming variations.
"""

import json

def add_name_variants():
    """Add alternative name entries for chemicals with common naming variations."""
    
    registry_file = 'cas_registry_merged.jsonl'
    
    # Load existing registry
    entries = []
    existing_cas = set()
    
    with open(registry_file, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            entries.append(entry)
            existing_cas.add(entry.get('cas', ''))
    
    print(f"Loaded {len(entries)} entries")
    
    # Name variants to add (different names for same CAS)
    name_variants = [
        {
            'cas': '12150-46-8',
            'name': '1,1-Bis(diphenylphosphino)ferrocene',  # Without apostrophe
            'abbreviation': 'dppf',
            'compound_type': 'ligand',
            'sources': ['name_variant_addition']
        },
        {
            'cas': '51364-51-3',
            'name': 'Tris(dibenzylideneacetone)dipalladium',  # Without (0)
            'abbreviation': 'Pd2(dba)3',
            'compound_type': 'catalyst_core',
            'sources': ['name_variant_addition']
        }
    ]
    
    added_count = 0
    
    for variant in name_variants:
        # Check if this exact name already exists
        name_exists = any(entry.get('name', '').lower() == variant['name'].lower() 
                         for entry in entries)
        
        if not name_exists:
            entry = {
                'cas': variant['cas'],
                'name': variant['name'],
                'abbreviation': variant['abbreviation'],
                'generic_core': None,
                'category_hint': 'name_variant',
                'token': None,
                'compound_type': variant['compound_type'],
                'sources': variant['sources']
            }
            entries.append(entry)
            added_count += 1
            print(f"Added variant: {variant['cas']} - {variant['name']} ({variant['abbreviation']})")
        else:
            print(f"Variant already exists: {variant['name']}")
    
    # Save updated registry
    with open(registry_file, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\nAdded {added_count} name variants")
    print(f"Total registry size: {len(entries)}")

if __name__ == "__main__":
    add_name_variants()
