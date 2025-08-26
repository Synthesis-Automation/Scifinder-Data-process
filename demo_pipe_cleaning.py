#!/usr/bin/env python3
"""
Demonstration of pipe character cleaning improvement
"""

from reaction_markdown_generator import ReactionMarkdownGenerator

def demonstrate_pipe_cleaning():
    """Show before and after examples of pipe cleaning"""
    
    gen = ReactionMarkdownGenerator()
    
    # Real examples from SciFinder data (based on what we found)
    original_text_examples = [
        "| | | |",
        "|Reagents: 1-Ethyl-3-(3′-dimethylaminopropyl)carbodiimide, 1-Hydroxybenzotriazole|",
        "|Catalysts: 4-(Dimethylamino)pyridine|",
        "|Solvents: Dimethylformamide; 30 min, 0 °C|",
        "|||multiple|||pipes|||everywhere|||",
        "Normal text without pipes",
        "| | |",
        "||",
        "   | spaced content |   ",
        "Discovery of HDAC6, HDAC8, and 6/8 Inhibitors",
    ]
    
    print("PIPE CHARACTER CLEANING DEMONSTRATION")
    print("=" * 70)
    print("This shows how the original text cleaning removes unnecessary")
    print("pipe characters from SciFinder format while preserving content.")
    print("=" * 70)
    print()
    
    for i, original in enumerate(original_text_examples, 1):
        cleaned = gen.clean_original_line(original)
        status = "REMOVED" if cleaned == "" else "CLEANED"
        
        print(f"Example {i}:")
        print(f"  Original: '{original}'")
        print(f"  Cleaned:  '{cleaned}' ({status})")
        print()
    
    # Test with a full original text block
    print("FULL ORIGINAL TEXT BLOCK EXAMPLE")
    print("=" * 70)
    
    sample_original_text = [
        "Steps: 1, Yield: 80%",
        "CAS Reaction Number: 31-117-CAS-22288687",
        "1.1|Reagents: 1-Ethyl-3-(3′-dimethylaminopropyl)carbodiimide, 1-Hydroxybenzotriazole|",
        "|Catalysts: 4-(Dimethylamino)pyridine|",
        "|Solvents: Dimethylformamide; 30 min, 0 °C|",
        "1.2|15 min, 0 °C; 35 °C|",
        "56. Scheme 56 (1 Reaction)",
        "|",
        "|",
        "|",
        "|",
        "||",
        "Discovery of HDAC6, HDAC8, and 6/8 Inhibitors",
        "By: Yu, Wei-Chieh; et al"
    ]
    
    # Show original format_original_text output
    sample_data = {'original_text': sample_original_text}
    formatted_output = gen.format_original_text(sample_data)
    
    print("Cleaned original text output:")
    print(formatted_output)
    
    print("SUMMARY")
    print("=" * 70)
    print("✓ Empty pipe lines (| | | |) are completely removed")
    print("✓ Leading and trailing pipes are stripped from content lines")
    print("✓ Multiple consecutive spaces are consolidated")
    print("✓ Meaningful content is preserved")
    print("✓ Both Markdown and JSONL outputs now use cleaned text")
    print("\nThe original text is now much more readable!")

if __name__ == "__main__":
    demonstrate_pipe_cleaning()
