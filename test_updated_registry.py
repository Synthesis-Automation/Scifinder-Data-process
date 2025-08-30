#!/usr/bin/env python3
"""
Test the updated CAS registry integration with the reaction markdown generator
"""

import sys
sys.path.append('.')

from reaction_markdown_generator import CASRegistry

def test_updated_registry():
    """Test the updated CAS registry functionality."""
    
    registry = CASRegistry()
    
    print("Testing updated CAS registry...")
    print(f"Loaded {len(registry.registry_data)} entries from registry")
    
    # Test some known compounds
    test_cases = [
        ("1028206-60-1", "BrettPhos"),
        ("1038-95-5", "P(p-tol)3"), 
        ("106-42-3", "p-Xylene"),
        ("68-12-2", "DMF"),  # Test if abbreviation is used
    ]
    
    for cas, expected_name in test_cases:
        print(f"\nTesting CAS: {cas}")
        
        # Test individual methods
        entry = registry.get_registry_entry(cas)
        if entry:
            print(f"  Registry entry: {entry}")
        else:
            print(f"  Not found in registry")
        
        name = registry.get_compound_name(cas)
        print(f"  Name: {name}")
        
        abbreviation = registry.get_compound_abbreviation(cas)
        print(f"  Abbreviation: {abbreviation}")
        
        compound_type = registry.get_compound_type(cas)
        print(f"  Type: {compound_type}")
        
        display_name = registry.get_display_name(expected_name, cas)
        print(f"  Display name: {display_name}")
        
        # Test validation
        corrected_name, corrected_cas, warnings = registry.validate_compound_pair(expected_name, cas)
        print(f"  Validation: name='{corrected_name}', cas='{corrected_cas}'")
        if warnings:
            print(f"  Warnings: {warnings}")

if __name__ == "__main__":
    test_updated_registry()
