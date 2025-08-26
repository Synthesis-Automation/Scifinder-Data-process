#!/usr/bin/env python3
"""
Quick test to check JSONL generation method directly
"""

import json
from datetime import datetime

def test_jsonl_method():
    """Test the JSONL preparation method directly."""
    
    # Create a mock row similar to what assemble_rows produces
    mock_row = {
        'ReactionID': 'TEST-001',
        'ReactionType': 'Buchwald',
        'CatalystCoreDetail': '["Palladium diacetate|3375-31-3"]',
        'CatalystCoreGeneric': '["Pd"]',
        'Ligand': '["XPhos|123-45-6"]',
        'FullCatalyticSystem': '["Palladium diacetate|3375-31-3", "XPhos|123-45-6"]',
        'Reagent': '["Sodium tert-butoxide|865-48-5"]',
        'ReagentRole': '["BASE"]',
        'Solvent': '["Toluene|108-88-3"]',
        'Temperature_C': 110.0,
        'Time_h': 12.5,
        'Yield_%': 85.0,
        'ReactantSMILES': 'CCN.ClCc1ccccc1',
        'ProductSMILES': 'CCNCc1ccccc1',
        'Reference': 'Test Article|Smith, J.; et al|J. Test. Chem. 2024, 1, 1-10.|10.1000/test123',
        'CondKey': 'test_key',
        'CondSig': 'test_sig',
        'FamSig': 'test_fam',
        'RawCAS': 'TEST: 123-45-6',
        'RawData': '{"test": "data"}',
        'RCTName': '["Reactant A"]',
        'PROName': '["Product B"]',
        'RGTName': '["Reagent C"]',
        'CATName': '["Catalyst D"]',
        'SOLName': '["Solvent E"]',
        'original_text': [
            'Steps: 1, Yield: 85%',
            'CAS Reaction Number: TEST-001',
            '1.1|Reagents: Sodium tert-butoxide|',
            '|Catalysts: Palladium diacetate, XPhos|',
            '|Solvents: Toluene; 12.5 h, 110 °C|'
        ]
    }
    
    print("Testing JSONL record preparation...")
    
    try:
        # Import the generator and test the method
        from reaction_markdown_generator import ReactionMarkdownGenerator
        
        generator = ReactionMarkdownGenerator()
        analysis_record = generator.prepare_analysis_record(mock_row)
        
        print("✅ Analysis record created successfully!")
        print(f"📋 Record structure:")
        
        # Show the structure
        structure_summary = {
            'reaction_id': analysis_record.get('reaction_id'),
            'reaction_type': analysis_record.get('reaction_type'),
            'catalyst_cores': len(analysis_record.get('catalyst', {}).get('core', [])),
            'reagent_count': len(analysis_record.get('reagents', [])),
            'conditions': analysis_record.get('conditions'),
            'has_original_text': len(analysis_record.get('original_text', [])) > 0,
            'reference_structure': {
                'title': analysis_record.get('reference', {}).get('title', '')[:30] + '...',
                'doi': analysis_record.get('reference', {}).get('doi', '')
            }
        }
        
        print(json.dumps(structure_summary, indent=2, ensure_ascii=False))
        
        # Test JSONL line creation
        jsonl_line = json.dumps(analysis_record, ensure_ascii=False)
        print(f"\n📊 JSONL line length: {len(jsonl_line)} characters")
        
        # Write a test JSONL file
        with open('test_single_record.jsonl', 'w', encoding='utf-8') as f:
            f.write(jsonl_line + '\n')
        
        print(f"✅ Test JSONL written to: test_single_record.jsonl")
        
        # Verify it can be read back
        with open('test_single_record.jsonl', 'r', encoding='utf-8') as f:
            loaded_record = json.loads(f.readline())
        
        print(f"✅ Record verified - reaction_id: {loaded_record.get('reaction_id')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jsonl_method()
