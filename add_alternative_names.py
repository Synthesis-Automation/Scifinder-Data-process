#!/usr/bin/env python3
"""
Add alternative name entries to the CAS registry to fix duplication issues.
This addresses cases where the same chemical appears with both its full IUPAC name
and common shortened name (e.g., "N,N-Dimethylformamide" vs "Dimethylformamide").
"""

import json

def add_alternative_names():
    """Add alternative name entries for chemicals that commonly appear with multiple names."""
    
    registry_file = 'cas_registry_merged.jsonl'
    
    # Load existing registry
    existing_entries = []
    existing_names = set()
    
    with open(registry_file, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            existing_entries.append(entry)
            existing_names.add(entry.get('name', '').lower())
    
    print(f"Loaded {len(existing_entries)} existing entries")
    
    # Common alternative names that cause duplication issues
    alternative_mappings = [
        # DMF alternatives
        {
            'cas': '68-12-2',
            'primary_name': 'N,N-Dimethylformamide',
            'alternative_names': ['Dimethylformamide', 'DMF'],
            'abbreviation': 'DMF',
            'compound_type': 'solvent'
        },
        # DMSO alternatives
        {
            'cas': '67-68-5',
            'primary_name': 'Dimethyl sulfoxide',
            'alternative_names': ['DMSO'],
            'abbreviation': 'DMSO',
            'compound_type': 'solvent'
        },
        # THF alternatives
        {
            'cas': '109-99-9',
            'primary_name': 'Tetrahydrofuran',
            'alternative_names': ['THF'],
            'abbreviation': 'THF',
            'compound_type': 'solvent'
        },
        # DCM alternatives
        {
            'cas': '75-09-2',
            'primary_name': 'Dichloromethane',
            'alternative_names': ['Methylene chloride', 'DCM'],
            'abbreviation': 'DCM',
            'compound_type': 'solvent'
        },
        # DMEDA alternatives
        {
            'cas': '110-70-3',
            'primary_name': 'N,N\'-Dimethylethylenediamine',
            'alternative_names': ['N,N-Dimethylethylenediamine', 'DMEDA'],
            'abbreviation': 'DMEDA',
            'compound_type': 'ligand'
        },
        # Toluene alternatives
        {
            'cas': '108-88-3',
            'primary_name': 'Toluene',
            'alternative_names': ['Methylbenzene', 'PhMe'],
            'abbreviation': 'PhMe',
            'compound_type': 'solvent'
        },
        # Acetonitrile alternatives
        {
            'cas': '75-05-8',
            'primary_name': 'Acetonitrile',
            'alternative_names': ['MeCN', 'Methyl cyanide'],
            'abbreviation': 'MeCN',
            'compound_type': 'solvent'
        },
        # Copper acetate alternatives
        {
            'cas': '142-71-2',
            'primary_name': 'Copper(II) acetate',
            'alternative_names': ['Cupric acetate', 'Cu(OAc)2'],
            'abbreviation': 'Cu(OAc)2',
            'compound_type': 'catalyst_core'
        },
        # Palladium acetate alternatives
        {
            'cas': '3375-31-3',
            'primary_name': 'Palladium(II) acetate',
            'alternative_names': ['Palladium acetate', 'Pd(OAc)2'],
            'abbreviation': 'Pd(OAc)2',
            'compound_type': 'catalyst_core'
        }
    ]
    
    added_count = 0
    
    for mapping in alternative_mappings:
        cas = mapping['cas']
        primary_name = mapping['primary_name']
        alternatives = mapping['alternative_names']
        
        # Check if primary entry exists and find it
        primary_exists = False
        for entry in existing_entries:
            if entry.get('cas') == cas:
                primary_exists = True
                # Update the primary entry to ensure it has the correct name
                if entry.get('name') != primary_name:
                    print(f"Updating primary name for {cas}: '{entry.get('name')}' → '{primary_name}'")
                    entry['name'] = primary_name
                if not entry.get('abbreviation') and mapping.get('abbreviation'):
                    entry['abbreviation'] = mapping['abbreviation']
                break
        
        if not primary_exists:
            # Add the primary entry
            primary_entry = {
                'cas': cas,
                'name': primary_name,
                'abbreviation': mapping.get('abbreviation', ''),
                'generic_core': None,
                'category_hint': None,
                'token': None,
                'compound_type': mapping['compound_type'],
                'sources': ['alternative_names_fix']
            }
            existing_entries.append(primary_entry)
            existing_names.add(primary_name.lower())
            added_count += 1
            print(f"Added primary entry: {cas} - {primary_name}")
        
        # Add alternative name entries
        for alt_name in alternatives:
            if alt_name.lower() not in existing_names:
                alt_entry = {
                    'cas': cas,
                    'name': alt_name,
                    'abbreviation': mapping.get('abbreviation', ''),
                    'generic_core': None,
                    'category_hint': None,
                    'token': None,
                    'compound_type': mapping['compound_type'],
                    'sources': ['alternative_names_fix', f'alternative_for_{primary_name}']
                }
                existing_entries.append(alt_entry)
                existing_names.add(alt_name.lower())
                added_count += 1
                print(f"Added alternative entry: {cas} - {alt_name} (for {primary_name})")
    
    # Save updated registry
    with open(registry_file, 'w', encoding='utf-8') as f:
        for entry in existing_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\nAdded {added_count} new/updated entries")
    print(f"Total registry size: {len(existing_entries)}")

if __name__ == "__main__":
    add_alternative_names()
