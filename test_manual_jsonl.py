#!/usr/bin/env python3
"""
Test JSONL with manually processed data to isolate the issue
"""

import os
import json
from process_reactions import parse_txt, parse_rdf, assemble_rows
from reaction_markdown_generator import ReactionMarkdownGenerator

def test_manual_jsonl():
    """Test JSONL generation with manual data processing."""
    
    print("Testing JSONL with manual processing...")
    
    # Use one specific file pair
    txt_file = "dataset/Buchwald/2021-2024/Reaction_20250824_1117.txt"
    rdf_file = "dataset/Buchwald/2021-2024/Reaction_20250824_1117.rdf"
    
    if not (os.path.exists(txt_file) and os.path.exists(rdf_file)):
        print(f"Files not found!")
        return
    
    try:
        print(f"Processing files...")
        print(f"  TXT: {txt_file}")
        print(f"  RDF: {rdf_file}")
        
        # Parse files
        txt_reactions = parse_txt(txt_file)
        rdf_reactions = parse_rdf(rdf_file)
        
        print(f"  TXT reactions: {len(txt_reactions)}")
        print(f"  RDF reactions: {len(rdf_reactions)}")
        
        if len(txt_reactions) == 0 or len(rdf_reactions) == 0:
            print("❌ No reactions found in files!")
            return
        
        # Assemble rows
        rows = assemble_rows(txt_reactions, rdf_reactions)
        print(f"  Assembled rows: {len(rows)}")
        
        if not rows:
            print("❌ No assembled rows!")
            return
        
        # Test JSONL generation
        generator = ReactionMarkdownGenerator()
        
        # Generate JSONL for first few rows
        test_rows = rows[:3]  # Just first 3 reactions
        jsonl_output = "test_manual.jsonl"
        
        print(f"Generating JSONL for {len(test_rows)} reactions...")
        generator.generate_jsonl_export(test_rows, jsonl_output, "test")
        
        # Check result
        if os.path.exists(jsonl_output):
            with open(jsonl_output, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            print(f"✅ JSONL generated successfully!")
            print(f"  Records: {len(lines)}")
            
            if lines:
                first_record = json.loads(lines[0])
                print(f"  First reaction: {first_record.get('reaction_id')}")
                print(f"  Type: {first_record.get('reaction_type')}")
                print(f"  Catalysts: {len(first_record.get('catalyst', {}).get('core', []))}")
                print(f"  Original text lines: {len(first_record.get('original_text', []))}")
                
                print(f"\n📋 Sample content:")
                sample = {
                    'reaction_id': first_record.get('reaction_id'),
                    'reaction_type': first_record.get('reaction_type'),
                    'catalyst_count': len(first_record.get('catalyst', {}).get('core', [])),
                    'conditions': first_record.get('conditions'),
                    'has_doi': bool(first_record.get('reference', {}).get('doi'))
                }
                print(json.dumps(sample, indent=2))
        else:
            print("❌ JSONL file not created!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_manual_jsonl()
