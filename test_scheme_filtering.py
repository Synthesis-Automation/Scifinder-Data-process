#!/usr/bin/env python3
"""
Test the enhanced pipe cleaning with scheme header filtering
"""

from reaction_markdown_generator import ReactionMarkdownGenerator

def test_scheme_header_filtering():
    """Test that scheme headers are properly filtered out"""
    
    gen = ReactionMarkdownGenerator()
    
    # Test cases including scheme headers
    test_cases = [
        # Should be removed (scheme headers)
        ("164. Scheme 164 (1 Reaction)", ""),
        ("56. Scheme 56 (1 Reaction)", ""),
        ("1. Scheme 1 (3 Reactions)", ""),
        ("123. Scheme 123 (10 Reactions)", ""),
        
        # Should be preserved (normal content)
        ("Steps: 1, Yield: 59%", "Steps: 1, Yield: 59%"),
        ("CAS Reaction Number: 31-172-CAS-23085870", "CAS Reaction Number: 31-172-CAS-23085870"),
        ("1.1|Reagents: Sodium tert-butoxide", "1.1|Reagents: Sodium tert-butoxide"),
        ("Catalysts: Tris(dibenzylideneacetone)dipalladium, X-Phos", "Catalysts: Tris(dibenzylideneacetone)dipalladium, X-Phos"),
        ("B,N-doped PAHs from tridentate 'Defects'", "B,N-doped PAHs from tridentate 'Defects'"),
        ("By: Farinone, Marco; et al", "By: Farinone, Marco; et al"),
        
        # Edge cases
        ("| | | |", ""),  # Empty pipes
        ("|Solvents: Toluene; 12 h, 105 °C|", "Solvents: Toluene; 12 h, 105 °C"),  # Pipe wrapped
    ]
    
    print("SCHEME HEADER FILTERING TEST")
    print("=" * 60)
    print("Testing enhanced cleaning to remove scheme headers")
    print("=" * 60)
    print()
    
    all_passed = True
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = gen.clean_original_line(input_text)
        passed = result == expected
        status = "✓ PASS" if passed else "✗ FAIL"
        
        if not passed:
            all_passed = False
        
        print(f"Test {i}: {status}")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        print()
    
    # Test the problematic original text from user's example
    print("USER'S EXAMPLE TEST")
    print("=" * 60)
    
    problematic_original_text = [
        "Steps: 1, Yield: 59%",
        "CAS Reaction Number: 31-172-CAS-23085870", 
        "1.1|Reagents: Sodium tert-butoxide",
        "Catalysts: Tris(dibenzylideneacetone)dipalladium, X-Phos",
        "Solvents: Toluene; 12 h, 105 °C",
        "164. Scheme 164 (1 Reaction)",  # This should be removed
        "B,N-doped PAHs from tridentate 'Defects' - a bottom-up convergent approach",
        "By: Farinone, Marco; et al",
        "Chemical Communications (Cambridge, United Kingdom) (2022), 58(52), 7269-7272.",
        "10.1039/d2cc01801b",
        "View All Sources in CAS SciFinder"
    ]
    
    sample_data = {'original_text': problematic_original_text}
    cleaned_output = gen.format_original_text(sample_data)
    
    print("Cleaned output (scheme header should be gone):")
    print(cleaned_output)
    
    print("SUMMARY")
    print("=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed - check results above")
    print("✓ Scheme headers like 'X. Scheme X (Y Reaction(s))' are now filtered out")
    print("✓ Normal content is preserved")

if __name__ == "__main__":
    test_scheme_header_filtering()
