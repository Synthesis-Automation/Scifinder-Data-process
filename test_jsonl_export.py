#!/usr/bin/env python3
"""
Test JSONL export functionality
"""

import os
import json
from reaction_markdown_generator import ReactionMarkdownGenerator

def test_jsonl_export():
    """Test JSONL export with a small dataset."""
    
    # Use the Buchwald dataset for testing
    folder_path = "dataset/Buchwald/2021-2024"
    output_path = "test_buchwald_jsonl.md"
    
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} not found!")
        return
    
    print(f"Testing JSONL export...")
    print(f"Source folder: {folder_path}")
    print(f"Output markdown: {output_path}")
    
    try:
        generator = ReactionMarkdownGenerator()
        
        # Process just the first few files for testing
        pairs = generator.find_rdf_txt_pairs(folder_path)
        if not pairs:
            print("No RDF/TXT pairs found!")
            return
        
        print(f"Found {len(pairs)} pairs, processing first 2 for testing...")
        
        # Process limited pairs for testing
        test_pairs = pairs[:2]
        all_txt = {}
        all_rdf = {}
        
        for txt_path, rdf_path in test_pairs:
            print(f"Processing: {os.path.basename(txt_path)} + {os.path.basename(rdf_path)}")
            
            from process_reactions import parse_txt, parse_rdf
            txt_reactions = parse_txt(txt_path)
            rdf_reactions = parse_rdf(rdf_path)
            
            print(f"  TXT: {len(txt_reactions)} reactions")
            print(f"  RDF: {len(rdf_reactions)} reactions")
            
            all_txt.update(txt_reactions)
            all_rdf.update(rdf_reactions)
        
        # Assemble rows
        from process_reactions import assemble_rows
        rows = assemble_rows(all_txt, all_rdf, generator.cas_map)
        print(f"Assembled {len(rows)} reactions")
        
        # Generate both markdown and JSONL
        generator.generate_markdown_report(rows, output_path, folder_path)
        
        jsonl_path = output_path.replace('.md', '.jsonl')
        generator.generate_jsonl_export(rows, jsonl_path, folder_path)
        
        print(f"\n✅ Files generated:")
        print(f"📄 Markdown: {output_path}")
        print(f"📊 JSONL: {jsonl_path}")
        
        # Verify JSONL format
        if os.path.exists(jsonl_path):
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            print(f"\n📊 JSONL verification:")
            print(f"  - Total records: {len(lines)}")
            
            if lines:
                # Parse first record to show structure
                first_record = json.loads(lines[0])
                print(f"  - First reaction ID: {first_record.get('reaction_id', 'Unknown')}")
                print(f"  - Reaction type: {first_record.get('reaction_type', 'Unknown')}")
                print(f"  - Catalyst cores: {len(first_record.get('catalyst', {}).get('core', []))}")
                print(f"  - Reagents: {len(first_record.get('reagents', []))}")
                print(f"  - Original text lines: {len(first_record.get('original_text', []))}")
                
                # Show a sample of the structure
                print(f"\n📋 Sample record structure:")
                sample_structure = {
                    'reaction_id': first_record.get('reaction_id'),
                    'reaction_type': first_record.get('reaction_type'),
                    'catalyst': {
                        'core_count': len(first_record.get('catalyst', {}).get('core', [])),
                        'ligand_count': len(first_record.get('catalyst', {}).get('ligands', []))
                    },
                    'conditions': first_record.get('conditions', {}),
                    'reference': {
                        'title': first_record.get('reference', {}).get('title', '')[:50] + '...' if first_record.get('reference', {}).get('title', '') else '',
                        'doi': first_record.get('reference', {}).get('doi', '')
                    }
                }
                print(json.dumps(sample_structure, indent=2, ensure_ascii=False))
        
        # Check file sizes
        if os.path.exists(output_path) and os.path.exists(jsonl_path):
            md_size = os.path.getsize(output_path)
            jsonl_size = os.path.getsize(jsonl_path)
            print(f"\n📊 File sizes:")
            print(f"  - Markdown: {md_size:,} bytes")
            print(f"  - JSONL: {jsonl_size:,} bytes")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jsonl_export()
