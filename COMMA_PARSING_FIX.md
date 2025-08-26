# Chemical Compound Name Parsing Fix

## Problem
The original parsing logic was incorrectly splitting compound names at **every** comma, which broke chemical names containing commas as part of their structure.

**Example of the problem:**
```
Input: "Diisopropylethylamine, O-(7-Azabenzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium hexafluorophosphate"
```

**Incorrect parsing (before fix):**
- "Diisopropylethylamine"
- "O-(7-Azabenzotriazol-1-yl)-N"
- "N"
- "N′"
- "N′-tetramethyluronium hexafluorophosphate"

## Solution
Modified the `_normalize_token_list()` function in `process_reactions.py` to split only on **commas followed by spaces**, which are true separators between different compounds.

**Key insight:** Commas without spaces after them are part of chemical names.

**Correct parsing (after fix):**
- "Diisopropylethylamine"
- "O-(7-Azabenzotriazol-1-yl)-N,N,N′,N′-tetramethyluronium hexafluorophosphate"

## Implementation Details

### Before (line ~169):
```python
if ch == ',' and paren == 0 and square == 0 and curly == 0:
    token = ''.join(buf).strip().strip(';').strip()
    if token:
        raw.append(token)
    buf = []
```

### After:
```python
if ch == ',' and paren == 0 and square == 0 and curly == 0:
    # Check if the comma is followed by a space (indicating a true separator)
    next_char = s[i + 1] if i + 1 < len(s) else ''
    if next_char == ' ':
        # This is a true separator (comma followed by space)
        token = ''.join(buf).strip().strip(';').strip()
        if token:
            raw.append(token)
        buf = []
    else:
        # This comma is part of a compound name (no space after)
        buf.append(ch)
```

## Testing
Created `test_comma_parsing.py` with comprehensive test cases:

✅ All 6 test cases pass:
1. Original problem case with HATU reagent
2. Multiple compound variations
3. N,N-designator preservation
4. Parentheses handling
5. Single compound with internal commas
6. Multiple compounds with complex internal comma patterns

## Impact
- ✅ Fixed parsing of complex chemical names
- ✅ Maintained backward compatibility  
- ✅ Improved data quality in generated reports
- ✅ Enhanced accuracy for chemical reaction processing

This fix ensures that chemical compound names are correctly preserved in both CSV processing and markdown report generation.
