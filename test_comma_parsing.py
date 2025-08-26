#!/usr/bin/env python3
"""
Test script to verify the comma parsing fix in _normalize_token_list function.
"""

import sys
import os

# Add the current directory to path so we can import process_reactions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from process_reactions import _normalize_token_list

def test_comma_parsing():
    """Test cases for comma parsing logic"""
    
    test_cases = [
        # Original problem case
        {
            "input": "Diisopropylethylamine, O-(7-Azabenzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium hexafluorophosphate",
            "expected": [
                "Diisopropylethylamine",
                "O-(7-Azabenzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium hexafluorophosphate"
            ],
            "description": "Should split on comma+space but keep commas within compound names"
        },
        
        # Another test case with multiple compounds
        {
            "input": "Triethylamine, O-(7-Azabenzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium hexafluorophosphate",
            "expected": [
                "Triethylamine",
                "O-(7-Azabenzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium hexafluorophosphate"
            ],
            "description": "Another example with the same pattern"
        },
        
        # Test with N,N designators
        {
            "input": "N,N-Diisopropylethylamine, Compound B",
            "expected": [
                "N,N-Diisopropylethylamine",
                "Compound B"
            ],
            "description": "Should keep N,N- designators together"
        },
        
        # Test with parentheses containing commas
        {
            "input": "Compound A-(2,4,6-trimethyl), Compound B",
            "expected": [
                "Compound A-(2,4,6-trimethyl)",
                "Compound B"
            ],
            "description": "Should respect parentheses and not split on commas inside them"
        },
        
        # Single compound with internal commas
        {
            "input": "O-(7-Azabenzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium hexafluorophosphate",
            "expected": [
                "O-(7-Azabenzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium hexafluorophosphate"
            ],
            "description": "Single compound with internal commas should not be split"
        },
        
        # Multiple compounds with various internal comma patterns
        {
            "input": "1-Hydroxybenzotriazole, Diisopropylethylamine, O-(Benzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium tetrafluoroborate",
            "expected": [
                "1-Hydroxybenzotriazole",
                "Diisopropylethylamine", 
                "O-(Benzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium tetrafluoroborate"
            ],
            "description": "Multiple compounds where last one has internal commas"
        }
    ]
    
    print("Testing comma parsing logic...\n")
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        result = _normalize_token_list(test_case["input"])
        expected = test_case["expected"]
        
        print(f"Test {i}: {test_case['description']}")
        print(f"Input: {test_case['input']}")
        print(f"Expected: {expected}")
        print(f"Got:      {result}")
        
        if result == expected:
            print("✅ PASSED\n")
        else:
            print("❌ FAILED\n")
            all_passed = False
    
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return all_passed

if __name__ == "__main__":
    test_comma_parsing()
