from reaction_markdown_generator import ReactionMarkdownGenerator

gen = ReactionMarkdownGenerator()

# Test cases based on user's examples
test_cases = [
    "| | | |",                           # Should be empty
    "| | | This has content | | |",      # Should be "This has content"
    "|Catalysts: Pd(OAc)2|",            # Should be "Catalysts: Pd(OAc)2"
    "|||multiple|||pipes|||",           # Should be "multiple|||pipes"
    "Normal text without pipes",         # Should stay the same
    "   | | |   ",                      # Should be empty  
    "| text | in | middle |",           # Should be "text | in | middle"
]

print("Testing improved pipe character cleaning:")
print("=" * 60)

for test in test_cases:
    result = gen.clean_original_line(test)
    print(f"Input:  '{test}'")
    print(f"Output: '{result}'")
    print("-" * 40)
    
# Test the format_original_text method
print("\nTesting format_original_text method:")
print("=" * 60)

sample_data = {
    'original_text': [
        "| | | |",
        "| This is a reaction description |",
        "|||multiple|||pipes|||everywhere|||",
        "Normal text line",
        "| Another | formatted | line |",
        "| | |",
        "Final text without pipes"
    ]
}

formatted = gen.format_original_text(sample_data)
print("Formatted output:")
print(formatted)
