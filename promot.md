I need a Python command-line app that processes a reaction dataset into a standard CSV file (the format is described in `reaction_dataset_schema.md`).

The input will be two files: one in RDF format and one in text format. They contain information for the same reactions, and you need to combine them. Both files contain a reaction ID (in the example provided, for the first reaction the ID is 31-614-CAS-39303569). If needed, you can use the ID to cross-reference the records. The two example input files contain the same 500 reactions. Analyze both files and extract all information for these 500 reactions.

The two example input files are `Reaction_2024-1.rdf` and `Reaction_2024-1.txt`.