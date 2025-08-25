# SciFinder Reaction Processor

Command-line tool to merge a SciFinder TXT export and RXN/RDF export into a single CSV following `reaction_dataset_schema.md`.

## Install (main Python)

```powershell
pip install -r requirements.txt
```

No conda required. RDKit is optional; the app runs without it.

Optional RDKit via pip (availability depends on your Python/OS; if this fails, just skip it and SMILES will be blank):

```powershell
pip install rdkit
```

Optional Qt GUI (PySide6 or PyQt6):

```powershell
pip install PySide6 # or: pip install PyQt6
```

Optional (use a venv instead of the main Python):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python process_reactions.py --rdf .\Reaction_2024-1.rdf --txt .\Reaction_2024-1.txt --out .\reactions_2024-1.csv
```

GUI launcher (optional):

```powershell
python .\Scifinder_data_processer.py
```

Notes for the GUI:
- The default mode is “Process a folder of pairs.” Select a folder that contains matching `.rdf` and `.txt` files with the same basename.
- If you switch to the single-file mode, provide one RDF and one TXT file.

## Notes
- Hash fields (`CondSig`, `FamSig`) require the `xxhash` package; otherwise they will be blank.
- Time and temperature are heuristically parsed from the TXT (e.g., "overnight" = 16 h, "rt" = 25 °C). Reflux is not converted.
- Ligand vs. core catalyst split is heuristic; refine `_classify_catalyst_or_ligand` if needed.
- Optional: If RDKit is present in your environment, ReactantSMILES/ProductSMILES will be filled from RDF CTAB blocks. If not installed, these fields stay blank (the app runs either way).
- Optional: Provide one or more `--cas-map` CSVs with headers like `CAS,Name,GenericCore,Role,CategoryHint,Token` to normalize short solvent/base tokens and enrich names.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest -q
```

The tests do not require RDKit; when RDKit is available, SMILES extraction is also exercised.
