#!/usr/bin/env python3
"""
Quick test of the updated CAS registry
"""

from reaction_markdown_generator import CASRegistry

def main():
    registry = CASRegistry()
    
    # Test BrettPhos
    cas = "1028206-60-1"
    print(f"Testing CAS: {cas}")
    print(f"  Abbreviation: {registry.get_compound_abbreviation(cas)}")
    print(f"  Type: {registry.get_compound_type(cas)}")
    print(f"  Name: {registry.get_compound_name(cas)}")
    print(f"  Display: {registry.get_display_name('BrettPhos', cas)}")
    
    # Test DMF
    cas2 = "68-12-2"
    print(f"\nTesting CAS: {cas2}")
    print(f"  Abbreviation: {registry.get_compound_abbreviation(cas2)}")
    print(f"  Type: {registry.get_compound_type(cas2)}")
    print(f"  Name: {registry.get_compound_name(cas2)}")
    print(f"  Display: {registry.get_display_name('Dimethylformamide', cas2)}")

if __name__ == "__main__":
    main()
