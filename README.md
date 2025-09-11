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

## Combined Markdown ➜ Rich Report/JSONL

If you have a single pre-combined Markdown file that interleaves TXT and RDF code blocks, convert it to the rich Markdown report and JSONL:

```powershell
python .\Combined_md_to_rich_report.py --input .\dataset\Amide formation\Reaction_20250824_1136.rtf.md --output .\dataset\Amide formation\rich
# Show help
python .\Combined_md_to_rich_report.py --help
```

Notes:

- The parser is tolerant of code-fence starts like ```` ```$RXN ```` and preserves full MOL/RXN text.
- Time and temperature heuristics: "overnight" → 16 h; "rt" → 25 °C; skips DOI lines; keeps solvent visibility.
- The generator centralizes any data quality notes into a "Data Quality Warnings" section (no inline [Corrected from: ...]).

## CAS Registry Tool (JSONL)

Maintain `cas_registry_merged.jsonl`: validate CAS, look up names, append missing entries, update existing entries, and scan text/CSV files.

Add a single CAS (dry-run first):

```powershell
python .\cas_registry_tool.py --add-cas 7718-54-9 --registry .\cas_registry_merged.jsonl --dry-run
python .\cas_registry_tool.py --add-cas 7718-54-9 --registry .\cas_registry_merged.jsonl
```

Add from a CSV (first column is CAS):

```powershell
python .\cas_registry_tool.py --add-csv .\new_cas.csv --registry .\cas_registry_merged.jsonl --dry-run
```

Scan a text file for CAS and add:

```powershell
python .\cas_registry_tool.py --add-text .\notes.txt --registry .\cas_registry_merged.jsonl --dry-run
```

Update existing JSONL entries to fill missing fields (name/abbreviation/type), with a dry-run diff:

```powershell
# Update all entries
python .\cas_registry_tool.py --update-existing --registry .\cas_registry_merged.jsonl --dry-run

# Or update a subset of CAS
python .\cas_registry_tool.py --update-existing --add-csv .\subset.csv --registry .\cas_registry_merged.jsonl --dry-run
```

Abbreviations follow a conservative allowlist (e.g., DMF, THF, MeOH) and avoid code-like IDs (e.g., FD21675, DB01345). If nothing suitable is found, the abbreviation field is left empty.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest -q
```

The tests do not require RDKit; when RDKit is available, SMILES extraction is also exercised.

## RDF-only GUI

Use a lightweight GUI to process a folder of `.rdf` files and generate Markdown and JSONL:

```powershell
python .\Scifinder_rdf_processer.py
```

- Select a folder containing `.rdf` files
- Output Markdown path also produces a sibling `.jsonl`
- RDKit is optional; SMILES fields are blank when RDKit is unavailable

## Temperature/Time Overrides

`Scifinder_rdf_processer.py` enriches `Temperature_C` and `Time_h` using `dataset/temp_time.md` by matching blocks that start with:

```
CAS Reaction Number: <ID>
```

Within each block, it:
- Sums times in h/hr/hrs/hour, min/mins/minute (minutes → hours), and d/day/days (×24); treats "overnight" as 16 h
- Takes the max numeric Celsius (e.g., `80 °C` or `100 C`); if only `rt`/`room temperature` appears, uses 25 °C
- These values override RDF-derived heuristics and flow into both Markdown and JSONL outputs

Keep this file updated at: `dataset/temp_time.md`

## RTF Folder → Markdown

Combine all `.rtf` files’ text in a folder into a single Markdown file (images ignored):

```powershell
python .\rtf_folder_to_md.py
```

- Pick a folder (optionally recurse subfolders)
- See per-file log lines and a progress bar during extraction
- Output is a `.md` with per-file sections
