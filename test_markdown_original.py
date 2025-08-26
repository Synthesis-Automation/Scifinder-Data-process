#!/usr/bin/env python3
"""
Test script to verify markdown generation with original text
"""

import os
import json
from process_reactions import parse_txt, parse_rdf, assemble_rows
from reaction_markdown_generator import ReactionMarkdownGenerator

def test_markdown_with_original_text():
    """Test markdown generation with original text preservation."""
    
    # Find a test file pair
    test_pairs = []
    for root, dirs, files in os.walk("dataset"):
        txt_files = [f for f in files if f.endswith('.txt')]
        for txt_file in txt_files:
            rdf_file = txt_file.replace('.txt', '.rdf')
            if rdf_file in files:
                txt_path = os.path.join(root, txt_file)
                rdf_path = os.path.join(root, rdf_file)
                test_pairs.append((txt_path, rdf_path))
                if len(test_pairs) >= 1:  # Just test one pair
                    break
        if test_pairs:
            break
    
    if not test_pairs:
        print("No TXT/RDF pairs found for testing")
        return
    
    txt_path, rdf_path = test_pairs[0]
    print(f"Testing markdown generation with: {os.path.basename(txt_path)}")
    
    try:
        # Parse files
        txt_reactions = parse_txt(txt_path)
        rdf_reactions = parse_rdf(rdf_path)
        
        print(f"TXT reactions: {len(txt_reactions)}")
        print(f"RDF reactions: {len(rdf_reactions)}")
        
        # Assemble rows
        rows = assemble_rows(txt_reactions, rdf_reactions)
        print(f"Assembled rows: {len(rows)}")
        
        if not rows:
            print("No assembled rows found!")
            return
        
        # Test markdown generation for first reaction
        generator = ReactionMarkdownGenerator()
        
        # Pick first row
        test_row = rows[0]
        print(f"\nTesting reaction: {test_row.get('ReactionID', 'Unknown')}")
        
        # Check if original_text exists in the row
        if 'original_text' in test_row:
            print(f"Original text found: {len(test_row['original_text'])} lines")
            print("First few lines:")
            for i, line in enumerate(test_row['original_text'][:3]):
                print(f"  {i+1}: {line.strip()}")
        else:
            print("No original_text found in assembled row!")
        
        # Generate markdown for this reaction
        markdown = generator.generate_reaction_markdown(test_row)
        
        # Check if markdown contains original text section
        if "**Original Text:**" in markdown:
            print("\n✅ Original text section found in markdown!")
            
            # Extract the original text section
            lines = markdown.split('\n')
            in_original = False
            original_section = []
            for line in lines:
                if line.strip() == "**Original Text:**":
                    in_original = True
                    original_section.append(line)
                elif in_original:
                    original_section.append(line)
                    if line.strip() == "```" and len(original_section) > 2:
                        break
            
            print("Original text section preview:")
            for line in original_section[:10]:
                print(f"  {line}")
                
        else:
            print("\n❌ Original text section NOT found in markdown!")
            
        # Write a test markdown file
        test_output = "test_markdown_with_original.md"
        with open(test_output, 'w', encoding='utf-8') as f:
            f.write("# Test Markdown with Original Text\n\n")
            f.write(markdown)
        
        print(f"\nTest markdown written to: {test_output}")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_markdown_with_original_text()
