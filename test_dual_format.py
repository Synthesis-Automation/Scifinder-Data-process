#!/usr/bin/env python3
"""
Test the updated app to ensure both MD and JSONL files are generated
"""

import os
from reaction_markdown_generator import ReactionMarkdownGenerator

def test_dual_format_generation():
    """Test that both MD and JSONL files are generated."""
    
    folder_path = "dataset/Buchwald/2021-2024"
    output_path = "test_dual_format_report.md"
    
    if not os.path.exists(folder_path):
        print(f"Test folder not found: {folder_path}")
        return
    
    print("🧪 Testing dual format generation (MD + JSONL)...")
    print(f"📁 Source: {folder_path}")
    print(f"📄 Output: {output_path}")
    
    # Clean up any existing files
    jsonl_path = output_path.replace('.md', '.jsonl')
    for file in [output_path, jsonl_path]:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ Removed existing: {file}")
    
    try:
        generator = ReactionMarkdownGenerator()
        
        def progress_handler(msg):
            print(f"📊 {msg}")
        
        success = generator.process_folder(folder_path, output_path, progress_handler)
        
        if success:
            print(f"\n✅ Processing completed!")
            
            # Check both files
            md_exists = os.path.exists(output_path)
            jsonl_exists = os.path.exists(jsonl_path)
            
            print(f"\n📋 File Generation Results:")
            print(f"  📄 Markdown file: {'✅ Created' if md_exists else '❌ Missing'}")
            print(f"  📊 JSONL file: {'✅ Created' if jsonl_exists else '❌ Missing'}")
            
            if md_exists and jsonl_exists:
                md_size = os.path.getsize(output_path)
                jsonl_size = os.path.getsize(jsonl_path)
                
                print(f"\n📊 File Sizes:")
                print(f"  📄 Markdown: {md_size:,} bytes")
                print(f"  📊 JSONL: {jsonl_size:,} bytes")
                print(f"  📈 JSONL/MD ratio: {jsonl_size/md_size:.2f}x")
                
                # Quick verification of JSONL content
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                print(f"\n🔍 JSONL Verification:")
                print(f"  📊 Records: {len(lines)}")
                
                if lines:
                    import json
                    try:
                        first_record = json.loads(lines[0])
                        print(f"  🧪 First reaction: {first_record.get('reaction_id', 'Unknown')}")
                        print(f"  ⚗️ Reaction type: {first_record.get('reaction_type', 'Unknown')}")
                        print(f"  📝 Has original text: {len(first_record.get('original_text', [])) > 0}")
                        print(f"  🔗 Has DOI: {bool(first_record.get('reference', {}).get('doi', ''))}")
                    except json.JSONDecodeError:
                        print(f"  ❌ Invalid JSON in first line")
                
                print(f"\n🎯 SUCCESS: Both formats generated successfully!")
                return True
            else:
                print(f"\n❌ FAILURE: Missing files")
                return False
        else:
            print(f"\n❌ Processing failed!")
            return False
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_dual_format_generation()
