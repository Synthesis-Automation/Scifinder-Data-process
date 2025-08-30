#!/usr/bin/env python3
"""
Test duplication fix by generating a small report with the chemicals that were problematic.
"""

from reaction_markdown_generator import ReactionMarkdownGenerator
import json

def test_duplication_fix():
    """Test the duplication fix on a small dataset."""
    
    # Create test data with the chemicals that had duplication issues
    test_reactions = [
        {
            'title': 'Test Buchwald Coupling Reaction 1',
            'reaction_id': 'test_001',
            'reaction_type': 'Buchwald-Hartwig amination',
            'reactants': 'bromobenzene + aniline',
            'products': 'N-phenylaniline',
            'conditions': 'Pd2(dba)3 as catalyst core, XPhos as ligand, Tripotassium phosphate as base, toluene as solvent at 100°C',
            'yield': '95%',
            'original_text': 'The reaction was performed using bromobenzene, aniline, Pd2(dba)3, XPhos, K3PO4, and toluene.',
            'cas_found': {'7637-07-2': 'Tripotassium phosphate'},  # This was the problematic one
            'schemes': []
        },
        {
            'title': 'Test Buchwald Coupling Reaction 2', 
            'reaction_id': 'test_002',
            'reaction_type': 'Buchwald-Hartwig amination',
            'reactants': 'chlorobenzene + morpholine',
            'products': '4-phenylmorpholine',
            'conditions': 'Copper(I) iodide as catalyst core, N,N\'-Dimethylethylenediamine as ligand, Cesium carbonate as base',
            'yield': '88%',
            'original_text': 'The reaction used chlorobenzene, morpholine, CuI, DMEDA, and Cs2CO3.',
            'cas_found': {
                '7681-65-4': 'Copper(I) iodide', 
                '110-70-3': 'N,N\'-Dimethylethylenediamine',
                '534-17-8': 'Cesium carbonate'
            },
            'schemes': []
        }
    ]
    
    # Generate markdown
    generator = ReactionMarkdownGenerator()
    output_path = 'test_duplication_fix.md'
    generator.generate_markdown_report(test_reactions, output_path, 'test_folder')
    
    print(f"Generated test report: {output_path}")
    
    # Also check what's in our registry for these chemicals
    print("\nChecking registry entries for test chemicals:")
    
    test_cas_numbers = ['7637-07-2', '7681-65-4', '110-70-3', '534-17-8']
    
    with open('cas_registry_merged.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line.strip())
            if entry.get('cas') in test_cas_numbers:
                print(f"CAS {entry['cas']}: {entry['name']} (abbrev: {entry.get('abbreviation', 'N/A')})")

if __name__ == "__main__":
    test_duplication_fix()
