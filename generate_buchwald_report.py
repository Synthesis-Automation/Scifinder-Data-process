#!/usr/bin/env python3
"""
Generate a full markdown report for the Buchwald dataset with original text preservation
"""

import os
from reaction_markdown_generator import ReactionMarkdownGenerator

def generate_buchwald_report_with_original_text():
    """Generate a complete Buchwald report with original text preservation."""
    
    # Use the Buchwald dataset
    folder_path = "dataset/Buchwald/2021-2024"
    output_path = "buchwald_report_with_original_text.md"
    
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} not found!")
        return
    
    print(f"Generating Buchwald report with original text...")
    print(f"Source folder: {folder_path}")
    print(f"Output file: {output_path}")
    
    try:
        generator = ReactionMarkdownGenerator()
        
        # Process the folder
        success = generator.process_folder(folder_path, output_path)
        
        if success:
            print(f"\n✅ Report generated successfully!")
            print(f"📄 Report saved to: {output_path}")
            
            # Check file size
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"📊 Report size: {size:,} bytes")
                
        else:
            print("\n❌ Report generation failed!")
            
    except Exception as e:
        print(f"Error during report generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_buchwald_report_with_original_text()
