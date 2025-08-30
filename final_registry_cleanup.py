#!/usr/bin/env python3
"""
Final cleanup to fix any remaining abbreviation names that should be full names.
"""

import json

def final_registry_cleanup():
    """Fix any remaining abbreviation names in the registry."""
    
    registry_file = 'cas_registry_merged.jsonl'
    
    # Load existing registry
    entries = []
    
    with open(registry_file, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            entries.append(entry)
    
    print(f"Loaded {len(entries)} registry entries")
    
    # Additional fixes for remaining abbreviation names
    final_fixes = {
        '534-17-8': {
            'name': 'Cesium carbonate',
            'abbreviation': 'Cs2CO3'
        },
        # Check for any other common ones that might have been missed
        '6381-92-6': {
            'name': 'Disodium hydrogen phosphate',
            'abbreviation': 'Na2HPO4'
        } if any(e.get('cas') == '6381-92-6' and e.get('name') == 'Na2HPO4' for e in entries) else None
    }
    
    # Remove None entries
    final_fixes = {k: v for k, v in final_fixes.items() if v is not None}
    
    fixed_count = 0
    
    for entry in entries:
        cas = entry.get('cas', '')
        if cas in final_fixes:
            fix_data = final_fixes[cas]
            old_name = entry.get('name', '')
            entry['name'] = fix_data['name']
            entry['abbreviation'] = fix_data['abbreviation']
            fixed_count += 1
            print(f"Fixed {cas}: '{old_name}' → '{fix_data['name']}' (abbrev: {fix_data['abbreviation']})")
    
    # Look for any other entries where name equals abbreviation (potential issues)
    potential_issues = []
    for entry in entries:
        name = entry.get('name', '')
        abbrev = entry.get('abbreviation', '')
        if name == abbrev and len(name) < 10 and any(char in name for char in ['(', ')', '2', '3', '4']):
            potential_issues.append(f"CAS {entry.get('cas')}: {name}")
    
    if potential_issues:
        print(f"\nPotential remaining issues (name = abbreviation):")
        for issue in potential_issues[:10]:  # Show first 10
            print(f"  {issue}")
        if len(potential_issues) > 10:
            print(f"  ... and {len(potential_issues) - 10} more")
    
    # Save updated registry
    with open(registry_file, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\nFixed {fixed_count} additional entries")
    print(f"Total registry size: {len(entries)}")

if __name__ == "__main__":
    final_registry_cleanup()
