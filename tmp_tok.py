from process_reactions import _normalize_token_list
samples = [
    'Catalysts: trans-1,2-Diaminocyclohexane, Cuprous iodide',
    'Reagents: N, N-diisopropylethylamine, potassium carbonate',
]
for s in samples:
    rest = s.split(':',1)[1].strip() if ':' in s else s
    print(s)
    print(' ->', _normalize_token_list(rest))