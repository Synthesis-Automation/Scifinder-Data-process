#!/usr/bin/env python3
"""
Comprehensive fix for registry entries to have proper full names as primary names.
This addresses the systematic duplication issue where text parsing finds full names
but registry only has abbreviations.
"""

import json

def fix_registry_full_names():
    """Fix registry entries to have full names as primary names."""
    
    registry_file = 'cas_registry_merged.jsonl'
    
    # Load existing registry
    entries = []
    with open(registry_file, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            entries.append(entry)
    
    print(f"Loaded {len(entries)} entries")
    
    # Comprehensive name fixes - full chemical names as primary names
    name_fixes = {
        # Bases
        '7778-53-2': {'name': 'Tripotassium phosphate', 'abbreviation': 'K3PO4'},
        '584-08-7': {'name': 'Potassium carbonate', 'abbreviation': 'K2CO3'},  
        '497-19-8': {'name': 'Sodium carbonate', 'abbreviation': 'Na2CO3'},
        '144-55-8': {'name': 'Sodium bicarbonate', 'abbreviation': 'NaHCO3'},
        '534-15-6': {'name': 'Cesium carbonate', 'abbreviation': 'Cs2CO3'},
        '121-44-8': {'name': 'Triethylamine', 'abbreviation': 'TEA'},
        '7087-68-5': {'name': 'N,N-Diisopropylethylamine', 'abbreviation': 'DIEA'},
        '110-86-1': {'name': 'Pyridine', 'abbreviation': 'Py'},
        
        # Catalyst cores  
        '142-71-2': {'name': 'Copper(II) acetate', 'abbreviation': 'Cu(OAc)2'},
        '7758-89-6': {'name': 'Copper(I) chloride', 'abbreviation': 'CuCl'},
        '7447-39-4': {'name': 'Copper(II) chloride', 'abbreviation': 'CuCl2'},
        '544-92-3': {'name': 'Copper(I) cyanide', 'abbreviation': 'CuCN'},
        '7681-65-4': {'name': 'Copper(I) iodide', 'abbreviation': 'CuI'},
        '3375-31-3': {'name': 'Palladium(II) acetate', 'abbreviation': 'Pd(OAc)2'},
        
        # Ligands
        '603-35-0': {'name': 'Triphenylphosphine', 'abbreviation': 'PPh3'},
        '1663-45-2': {'name': '1,1\'-Bis(diphenylphosphino)ferrocene', 'abbreviation': 'dppf'},
        '98886-44-3': {'name': '2,2\'-Bis(diphenylphosphino)-1,1\'-binaphthyl', 'abbreviation': 'BINAP'},
        '564483-18-7': {'name': '2-Dicyclohexylphosphino-2\',6\'-dimethoxybiphenyl', 'abbreviation': 'SPhos'},
        '564483-19-8': {'name': '2-Dicyclohexylphosphino-2\',4\',6\'-triisopropylbiphenyl', 'abbreviation': 'XPhos'},
        '110-70-3': {'name': 'N,N\'-Dimethylethylenediamine', 'abbreviation': 'DMEDA'},
        
        # Solvents
        '68-12-2': {'name': 'N,N-Dimethylformamide', 'abbreviation': 'DMF'},
        '67-68-5': {'name': 'Dimethyl sulfoxide', 'abbreviation': 'DMSO'},
        '109-99-9': {'name': 'Tetrahydrofuran', 'abbreviation': 'THF'},
        '75-09-2': {'name': 'Dichloromethane', 'abbreviation': 'DCM'},
        '108-88-3': {'name': 'Toluene', 'abbreviation': 'PhMe'},
        '67-56-1': {'name': 'Methanol', 'abbreviation': 'MeOH'},
        '64-17-5': {'name': 'Ethanol', 'abbreviation': 'EtOH'},
        '67-63-0': {'name': '2-Propanol', 'abbreviation': 'iPrOH'},
        '141-78-6': {'name': 'Ethyl acetate', 'abbreviation': 'EtOAc'},
        '60-29-7': {'name': 'Diethyl ether', 'abbreviation': 'Et2O'},
        '123-91-1': {'name': '1,4-Dioxane', 'abbreviation': 'dioxane'},
        
        # Activators
        '1892-57-5': {'name': '1-Ethyl-3-(3-dimethylaminopropyl)carbodiimide', 'abbreviation': 'EDC'},
        '25952-53-8': {'name': '1-Ethyl-3-(3-dimethylaminopropyl)carbodiimide hydrochloride', 'abbreviation': 'EDC·HCl'},
        '538-75-0': {'name': 'N,N\'-Dicyclohexylcarbodiimide', 'abbreviation': 'DCC'},
        '693-13-0': {'name': 'N,N\'-Diisopropylcarbodiimide', 'abbreviation': 'DIC'},
        '148893-10-1': {'name': 'O-(7-Azabenzotriazol-1-yl)-N,N,N\',N\'-tetramethyluronium hexafluorophosphate', 'abbreviation': 'HATU'},
        '94790-37-1': {'name': 'O-Benzotriazol-1-yl-N,N,N\',N\'-tetramethyluronium hexafluorophosphate', 'abbreviation': 'HBTU'},
        '1003-73-2': {'name': '4-Dimethylaminopyridine', 'abbreviation': 'DMAP'},
    }
    
    fixed_count = 0
    
    for entry in entries:
        cas = entry.get('cas', '')
        if cas in name_fixes:
            old_name = entry.get('name', '')
            old_abbrev = entry.get('abbreviation', '')
            
            # Update to proper full name and abbreviation
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
    fix_registry_full_names()
