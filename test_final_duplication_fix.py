#!/usr/bin/env python3
"""
Test the duplication fix by creating a sample reaction and generating markdown.
"""

import json
from reaction_markdown_generator import ReactionMarkdownGenerator

def test_duplication_fix():
    """Test the duplication fix with synthetic data."""
    
    # Create test reaction data that had duplication issues
    test_reactions = [
        {
            "reaction_id": "test_ullman_001",
            "title": "Test Ullman Coupling with DMF",
            "reaction_type": "Ullmann",
            "reactants": "aryl halide + amine",
            "products": "N-aryl amine",
            "conditions": {
                "temperature_c": 120.0,
                "time_h": 12.0,
                "yield_pct": 85.0
            },
            "catalysts": [
                {"name": "Copper(II) acetate", "cas": "142-71-2", "role": "CATALYST_CORE"},
                {"name": "Cu(OAc)2", "cas": "142-71-2", "role": "CATALYST_CORE"}  # This should be deduplicated
            ],
            "ligands": [
                {"name": "N,N'-Dimethylethylenediamine", "cas": "110-70-3", "role": "LIGAND"},
                {"name": "DMEDA", "cas": "110-70-3", "role": "LIGAND"}  # This should be deduplicated
            ],
            "reagents": [
                {"name": "Cesium carbonate", "cas": "534-17-8", "role": "BASE"}
            ],
            "solvents": [
                {"name": "N,N-Dimethylformamide", "cas": "68-12-2", "role": "SOLVENT"},
                {"name": "Dimethylformamide", "cas": "68-12-2", "role": "SOLVENT"},  # This should be deduplicated
                {"name": "DMF", "cas": "68-12-2", "role": "SOLVENT"}  # This should be deduplicated
            ],
            "smiles": {
                "reactants": "Nc1ccccc1.Brc2ccccc2",
                "products": "c1ccc(Nc2ccccc2)cc1"
            },
            "reference": {
                "title": "Test Paper on DMF Duplications",
                "authors": "Test Author",
                "citation": "Test Journal (2024), 1, 1-10.",
                "doi": "10.1000/test.2024.001"
            },
            "original_text": [
                "Steps: 1, Yield: 85%",
                "1.1|Reagents: Cesium carbonate",
                "Catalysts: Copper(II) acetate, N,N'-Dimethylethylenediamine",
                "Solvents: Dimethylformamide; 12 h, 120 °C"
            ]
        }
    ]
    
    # Generate markdown using the enhanced registry
    generator = ReactionMarkdownGenerator()
    output_path = 'test_duplication_fix_final.md'
    
    generator.generate_markdown_report(test_reactions, output_path, 'test_folder')
    
    print(f"Generated test report: {output_path}")
    
    # Check the generated content for duplicates
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count occurrences of DMF variations
    dmf_variations = {
        'N,N-Dimethylformamide': content.count('N,N-Dimethylformamide'),
        'Dimethylformamide': content.count('Dimethylformamide'),
        'DMF': content.count('DMF')
    }
    
    print("\nDMF Variations in report:")
    for name, count in dmf_variations.items():
        print(f"  {name}: {count} occurrences")
    
    # Count ligand variations
    ligand_variations = {
        'N,N\'-Dimethylethylenediamine': content.count('N,N\'-Dimethylethylenediamine'),
        'DMEDA': content.count('DMEDA')
    }
    
    print("\nLigand Variations in report:")
    for name, count in ligand_variations.items():
        print(f"  {name}: {count} occurrences")
    
    # Count catalyst variations
    catalyst_variations = {
        'Copper(II) acetate': content.count('Copper(II) acetate'),
        'Cu(OAc)2': content.count('Cu(OAc)2')
    }
    
    print("\nCatalyst Variations in report:")
    for name, count in catalyst_variations.items():
        print(f"  {name}: {count} occurrences")
    
    print(f"\n✅ Test completed. Check {output_path} for the full report.")

if __name__ == "__main__":
    test_duplication_fix()
