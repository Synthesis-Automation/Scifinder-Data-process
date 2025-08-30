#!/usr/bin/env python3
"""
Fix registry entries to have proper full names while keeping abbreviations.
"""

import json

def fix_registry_names():
    """Fix registry entries to have proper full names."""
    
    registry_file = 'cas_registry_merged.jsonl'
    
    # Load existing registry
    entries = []
    with open(registry_file, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            entries.append(entry)
    
    print(f"Loaded {len(entries)} entries")
    
    # Fixes to apply
    name_fixes = {
        '865-48-5': {
            'name': 'Sodium tert-butoxide',
            'abbreviation': 'NaOtBu'
        },
        '51364-51-3': {
            'name': 'Tris(dibenzylideneacetone)dipalladium(0)',
            'abbreviation': 'Pd2(dba)3'
        },
        '12150-46-8': {
            'name': '1,1\'-Bis(diphenylphosphino)ferrocene', 
            'abbreviation': 'dppf'
        }
    }
    
    fixed_count = 0
    
    for entry in entries:
        cas = entry.get('cas', '')
        if cas in name_fixes:
            old_name = entry.get('name', '')
            old_abbrev = entry.get('abbreviation', '')
            
            entry['name'] = name_fixes[cas]['name']
            entry['abbreviation'] = name_fixes[cas]['abbreviation']
            
            print(f"Fixed {cas}: '{old_name}' -> '{entry['name']}' (abbrev: '{entry['abbreviation']}')")
            fixed_count += 1
    
    # Save updated registry
    with open(registry_file, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\nFixed {fixed_count} entries")
    print(f"Registry saved with {len(entries)} total entries")

if __name__ == "__main__":
    fix_registry_names()
