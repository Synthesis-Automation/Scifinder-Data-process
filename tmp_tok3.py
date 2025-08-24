from process_reactions import _normalize_token_list
s = 'Cuprous iodide, 2-Pyridinamine, N-(2,4,6-trimethylphenyl)-, 1-oxide'
print(_normalize_token_list(s))
# Also full label form
s2 = 'Catalysts: Cuprous iodide, 2-Pyridinamine, N-(2,4,6-trimethylphenyl)-, 1-oxide'
rest = s2.split(':',1)[1].strip()
print(_normalize_token_list(rest))