#!/usr/bin/env python3
"""
Test to verify that name_cas key has been removed from output
"""

import json
import sys
sys.path.append('.')

def test_name_cas_removal():
    """Test that name_cas key is no longer in the JSONL output."""
    
    # Read the first few lines of the new JSONL file
    with open('test_no_name_cas.jsonl', 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 3:  # Test first 3 records
                break
                
            record = json.loads(line)
            
            # Check catalyst section
            catalyst = record.get('catalyst', {})
            for category in ['core', 'ligands', 'full_system']:
                for compound in catalyst.get(category, []):
                    if 'name_cas' in compound:
                        print(f"❌ Found name_cas in catalyst.{category}: {compound}")
                        return False
            
            # Check reagents section
            for reagent in record.get('reagents', []):
                if 'name_cas' in reagent:
                    print(f"❌ Found name_cas in reagents: {reagent}")
                    return False
            
            # Check solvents section
            for solvent in record.get('solvents', []):
                if 'name_cas' in solvent:
                    print(f"❌ Found name_cas in solvents: {solvent}")
                    return False
                    
            print(f"✅ Record {i+1}: No name_cas key found")
    
    print("✅ All tests passed - name_cas key successfully removed!")
    return True

if __name__ == "__main__":
    test_name_cas_removal()
