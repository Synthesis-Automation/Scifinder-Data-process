#!/usr/bin/env python3
"""
Test the pipe character cleaning functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from reaction_markdown_generator import ReactionMarkdownGenerator

def test_pipe_cleaning():
    """Test the clean_original_line method"""
    generator = ReactionMarkdownGenerator()
    
    # Test cases with problematic formatting
    test_cases = [
        ("| | | |", ""),  # Only pipes - should be empty
        ("| text with content |", "text with content"),  # Should remove leading/trailing pipes
        ("multiple | pipes | in | middle", "multiple | pipes | in | middle"),  # Should preserve internal pipes
        ("|||multiple|consecutive|||pipes|||", "multiple|consecutive|pipes"),  # Should clean up consecutive pipes
        ("   | spaced  pipes  |   ", "spaced  pipes"),  # Should handle spacing
        ("", ""),  # Empty string
        ("normal text without pipes", "normal text without pipes"),  # Should not change normal text
        ("| | |", ""),  # Another empty case
        ("text|with|pipes|content", "text|with|pipes|content"),  # Should preserve meaningful pipes
    ]
    
    print("Testing pipe character cleaning:")
    print("=" * 60)
    
    for original, expected in test_cases:
        result = generator.clean_original_line(original)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"{status} Input: '{original}'")
        print(f"     Expected: '{expected}'")
        print(f"     Got:      '{result}'")
        print()
    
    # Test format_original_text with a sample
    print("Testing format_original_text method:")
    print("=" * 60)
    
    sample_original_text = [
        "| | | |",
        "| This is a reaction description |",
        "|||multiple|||pipes|||everywhere|||",
        "Normal text line",
        "| Another | formatted | line |",
        "| | |",
        "Final text without pipes"
    ]
    
    formatted_text = generator.format_original_text({'original_text': sample_original_text})
    print("Formatted result:")
    print(formatted_text)

if __name__ == "__main__":
    test_pipe_cleaning()
