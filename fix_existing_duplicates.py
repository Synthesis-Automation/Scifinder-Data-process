#!/usr/bin/env python3
"""
Post-process existing reaction JSONL files to remove duplicates caused by name variations.
This fixes duplicates in already-processed data using the enhanced CAS registry.
"""

import json
import os
from pathlib import Path

def load_cas_registry():
    """Load the CAS registry with alternative names."""
    registry = {}
    
    with open('cas_registry_merged.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            cas = entry.get('cas', '')
            name = entry.get('name', '')
            if cas and name:
                # Map both the name and CAS to the same CAS number
                registry[name.lower()] = cas
                registry[cas] = cas
    
    print(f"Loaded {len(registry)} name-to-CAS mappings")
    return registry

def deduplicate_compounds(compounds_list, registry):
    """Remove duplicates from a list of compound objects using CAS registry."""
    if not compounds_list:
        return compounds_list
    
    # Group by CAS number
    by_cas = {}
    for compound in compounds_list:
        name = compound.get('name', '')
        cas = compound.get('cas', '')
        
        # Normalize the CAS using registry
        normalized_cas = cas
        if not cas and name:
            # Try to find CAS from name
            normalized_cas = registry.get(name.lower(), '')
        elif cas and name:
            # Verify CAS is correct for this name
            name_cas = registry.get(name.lower(), '')
            if name_cas and name_cas != cas:
                print(f"  CAS mismatch for '{name}': file has {cas}, registry has {name_cas}")
                normalized_cas = name_cas
        
        if not normalized_cas:
            # Keep compounds without CAS as-is (might be valid unknowns)
            normalized_cas = f"unknown_{name.lower()}"
        
        if normalized_cas not in by_cas:
            by_cas[normalized_cas] = compound.copy()
        else:
            # Merge information, preferring non-empty values
            existing = by_cas[normalized_cas]
            
            # Use the name from registry if available, otherwise prefer non-empty names
            if normalized_cas in registry:
                # Find the primary name for this CAS
                primary_name = None
                for reg_name, reg_cas in registry.items():
                    if reg_cas == normalized_cas and not reg_name.startswith('unknown_'):
                        # Prefer full chemical names over abbreviations
                        if not primary_name or (len(reg_name) > len(primary_name) and ',' in reg_name):
                            primary_name = reg_name
                
                if primary_name:
                    existing['name'] = primary_name
            elif not existing.get('name') and compound.get('name'):
                existing['name'] = compound['name']
            
            # Ensure CAS is set
            if not existing.get('cas') and cas:
                existing['cas'] = cas
            
            # Preserve role information
            if not existing.get('role') and compound.get('role'):
                existing['role'] = compound['role']
    
    return list(by_cas.values())

def fix_reaction_duplicates(file_path):
    """Fix duplicates in a single reaction JSONL file."""
    print(f"\nProcessing: {file_path}")
    
    registry = load_cas_registry()
    fixed_reactions = []
    fixes_applied = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                reaction = json.loads(line.strip())
                original_reaction = json.dumps(reaction, sort_keys=True)
                
                # Fix compounds in different categories
                compound_fields = ['catalysts', 'ligands', 'reagents', 'solvents', 'reactants', 'products']
                
                for field in compound_fields:
                    if field in reaction and isinstance(reaction[field], list):
                        original_count = len(reaction[field])
                        reaction[field] = deduplicate_compounds(reaction[field], registry)
                        new_count = len(reaction[field])
                        
                        if original_count != new_count:
                            print(f"  Line {line_num}, {field}: {original_count} → {new_count} (-{original_count - new_count})")
                            fixes_applied += 1
                
                # Check if anything changed
                if json.dumps(reaction, sort_keys=True) != original_reaction:
                    fixes_applied += 1
                
                fixed_reactions.append(reaction)
                
            except json.JSONDecodeError as e:
                print(f"  Warning: Failed to parse line {line_num}: {e}")
                continue
    
    # Write fixed reactions back
    if fixes_applied > 0:
        backup_path = file_path + '.backup'
        os.rename(file_path, backup_path)
        print(f"  Created backup: {backup_path}")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for reaction in fixed_reactions:
                f.write(json.dumps(reaction, ensure_ascii=False) + '\n')
        
        print(f"  Applied {fixes_applied} fixes")
    else:
        print(f"  No fixes needed")
    
    return fixes_applied

def main():
    """Fix duplicates in all reaction JSONL files."""
    
    # Find all reaction JSONL files
    reaction_files = []
    
    # Look for files in the dataset folders
    dataset_path = Path('dataset')
    if dataset_path.exists():
        for jsonl_file in dataset_path.rglob('*.jsonl'):
            if 'reaction' in jsonl_file.name.lower():
                reaction_files.append(str(jsonl_file))
    
    # Also check for files in the current directory
    for jsonl_file in Path('.').glob('*reaction*.jsonl'):
        reaction_files.append(str(jsonl_file))
    
    if not reaction_files:
        print("No reaction JSONL files found")
        return
    
    print(f"Found {len(reaction_files)} reaction files to process:")
    for f in reaction_files:
        print(f"  {f}")
    
    total_fixes = 0
    for file_path in reaction_files:
        fixes = fix_reaction_duplicates(file_path)
        total_fixes += fixes
    
    print(f"\n✅ Total fixes applied: {total_fixes}")
    print("Duplication fixes completed!")

if __name__ == "__main__":
    main()
