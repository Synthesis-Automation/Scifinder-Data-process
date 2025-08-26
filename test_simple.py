from reaction_markdown_generator import ReactionMarkdownGenerator

gen = ReactionMarkdownGenerator()

# Test examples from the user's problem
test_cases = [
    "| | | |",
    "|Catalysts: Pd(OAc)2|", 
    "|||multiple|||pipes|||",
    "Normal text without pipes",
    "| | | This has content | | |"
]

print("Testing pipe character cleaning:")
print("=" * 50)

for test in test_cases:
    result = gen.clean_original_line(test)
    print(f"Input:  '{test}'")
    print(f"Output: '{result}'")
    print("-" * 30)
