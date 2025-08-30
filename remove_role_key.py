#!/usr/bin/env python3
"""
Remove the 'role' key from CAS registry JSONL file since we already have 'compound_type'
"""

import json

def remove_role_key():
    """Remove the role key from all entries in the CAS registry file."""
    
    input_file = 'cas_registry_merged.jsonl'
    output_file = 'cas_registry_merged_no_role.jsonl'
    
    print(f"Reading from {input_file}...")
    
    entries = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            try:
                entry = json.loads(line)
                
                # Remove the 'role' key if it exists
                if 'role' in entry:
                    del entry['role']
                
                entries.append(entry)
                
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
    
    print(f"Processed {len(entries)} entries")
    
    # Write the updated entries
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print("Done! The 'role' key has been removed from all entries.")
    
    # Show a sample of the result
    print("\nSample of updated entries:")
    for i, entry in enumerate(entries[:3]):
        print(f"  {i+1}: {json.dumps(entry, ensure_ascii=False)}")

if __name__ == "__main__":
    remove_role_key()
