#!/usr/bin/env python3
"""
Simple test to generate JSONL export from existing working dataset
"""

import os
import json
from reaction_markdown_generator import ReactionMarkdownGenerator

def test_jsonl_simple():
    """Test JSONL export using the working Buchwald dataset."""
    
    # Use a smaller folder or limit the number of reactions
    folder_path = "dataset/Buchwald/2021-2024"
    output_path = "test_small_buchwald.md"
    
    print(f"Testing JSONL export with full pipeline...")
    
    try:
        generator = ReactionMarkdownGenerator()
        
        # Use the existing working process_folder method
        success = generator.process_folder(folder_path, output_path)
        
        if success:
            print(f"✅ Processing successful!")
            
            # Check both files
            jsonl_path = output_path.replace('.md', '.jsonl')
            
            if os.path.exists(jsonl_path):
                print(f"📊 JSONL file created: {jsonl_path}")
                
                # Analyze the JSONL content
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                print(f"📋 JSONL Analysis:")
                print(f"  - Total records: {len(lines)}")
                
                if lines:
                    # Parse first record
                    first_record = json.loads(lines[0])
                    print(f"  - First reaction: {first_record.get('reaction_id', 'Unknown')}")
                    print(f"  - Reaction type: {first_record.get('reaction_type', 'Unknown')}")
                    
                    # Show key statistics
                    total_with_catalyst = sum(1 for line in lines[:10] if json.loads(line).get('catalyst', {}).get('core', []))
                    total_with_conditions = sum(1 for line in lines[:10] if json.loads(line).get('conditions', {}).get('temperature_c') is not None)
                    
                    print(f"  - Records with catalyst (first 10): {total_with_catalyst}/10")
                    print(f"  - Records with temperature (first 10): {total_with_conditions}/10")
                    
                    # Show structure of first record
                    print(f"\n📋 Sample JSONL record structure:")
                    sample = {
                        'reaction_id': first_record.get('reaction_id'),
                        'reaction_type': first_record.get('reaction_type'),
                        'catalyst_cores': len(first_record.get('catalyst', {}).get('core', [])),
                        'reagent_count': len(first_record.get('reagents', [])),
                        'conditions': first_record.get('conditions', {}),
                        'has_original_text': len(first_record.get('original_text', [])) > 0,
                        'reference_doi': first_record.get('reference', {}).get('doi', '')
                    }
                    print(json.dumps(sample, indent=2, ensure_ascii=False))
                    
                    # Show file sizes
                    md_size = os.path.getsize(output_path)
                    jsonl_size = os.path.getsize(jsonl_path)
                    print(f"\n📊 File comparison:")
                    print(f"  - Markdown: {md_size:,} bytes")
                    print(f"  - JSONL: {jsonl_size:,} bytes")
                    print(f"  - Ratio: {jsonl_size/md_size:.2f}x")
                    
            else:
                print(f"❌ JSONL file not created!")
        else:
            print(f"❌ Processing failed!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jsonl_simple()
