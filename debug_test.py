import os
import sys

print("Starting test...")

try:
    from reaction_markdown_generator import ReactionMarkdownGenerator
    print("Import successful")
    
    gen = ReactionMarkdownGenerator()
    print("Generator created")
    
    # Test basic functionality
    test_input = "| | | This has content | | |"
    result = gen.clean_original_line(test_input)
    
    print(f"Test completed")
    print(f"Input was: {repr(test_input)}")
    print(f"Result is: {repr(result)}")
    
except Exception as e:
    print(f"Error occurred: {str(e)}")
    import traceback
    traceback.print_exc()

print("Test finished")
