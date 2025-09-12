# Agents Guide: SciFinder Data Processing Repo

This document orients code-assist agents working in this repository. It summarizes goals, entrypoints, data contracts, and guardrails so you can make safe, surgical changes.

## Objectives

- Merge SciFinder TXT and RDF exports into a flat CSV for downstream use.
- Generate rich Markdown + JSONL reports from RDF/TXT pairs or RDF-only folders for human review and analytics.
- Maintain a JSONL-based CAS registry (names, abbreviations, types) and use it to normalize outputs.

## Primary Entrypoints

- `process_reactions.py` (CLI): TXT+RDF → CSV. Key APIs:
  - `process_reactions.py:372` `parse_txt(path)`
  - `process_reactions.py:607` `parse_rdf(path)`
  - `process_reactions.py:796` `load_cas_maps(paths)`
  - `process_reactions.py:786` `infer_reaction_type(core_generic_tokens)`
  - `process_reactions.py:1321` `assemble_rows(txt, rdf, cas_map, *, txt_preferred=False)`

- `reaction_markdown_generator.py` (library/GUI helper): builds Markdown and JSONL from parsed rows.
  - `reaction_markdown_generator.py:74` `class CASRegistry`
  - `reaction_markdown_generator.py:338` `class ReactionMarkdownGenerator`

- `Scifinder_rdf_processer.py` (GUI): RDF folder → Markdown + JSONL.
  - `Scifinder_rdf_processer.py:52` `class RDFWorker`
  - `Scifinder_rdf_processer.py:407` `class RDFProcessorWindow`

- CAS registry tooling:
  - `Compound_registry_generator.py:56` `class ComprehensiveCASRegistry`
  - `Process_compound_registry.py:41` classification/props CLI for JSONL registry entries

## Install & Run

- Install runtime deps (RDKit optional):
  - `pip install -r requirements.txt`
  - Optional: `pip install rdkit` (SMILES extraction; app works without it)
  - Optional GUI: `pip install PySide6` or keep `PyQt6` from requirements

- TXT+RDF → CSV:
  - `python process_reactions.py --rdf .\Reaction.rdf --txt .\Reaction.txt --out .\reactions.csv`

- RDF folder → Markdown + JSONL (GUI):
  - `python .\Scifinder_rdf_processer.py`

- Markdown/JSONL generation (helper used by GUI):
  - Import `ReactionMarkdownGenerator` from `reaction_markdown_generator.py` and call its methods.

- CAS registry actions (JSONL at repo root: `cas_registry_merged.jsonl`):
  - Add/update via `Compound_registry_generator.py` (see “CAS Registry” below).

## Data Contracts (be careful)

- CSV column values for list fields are JSON strings of arrays (e.g., `Ligand`, `Reagent`, `Solvent`). Keep this convention stable.
- Compounds are rendered as `"name|cas"` pairs (either side may be a single space when missing). Maintain this in rows and Markdown.
- Hashes (`CondSig`, `FamSig`) are `xxhash`-based when `xxhash` is installed; otherwise empty strings. Don’t silently change algorithms.
- RDKit is optional: when unavailable, SMILES fields must be present but may be blank.

## Code Map & Heuristics

- TXT tokenization and splitting rules (names with locants/designators):
  - `process_reactions.py:145` `_normalize_token_list`

- Detect condition fragments (time/temp keywords):
  - `process_reactions.py:261` `_is_condition_token`

- Catalyst vs ligand split and metal tagging:
  - `process_reactions.py:279` `_classify_catalyst_or_ligand`
  - `process_reactions.py:786` `infer_reaction_type`

- Reagent role classification (BASE, WORKUP, OX, NUC, UNK):
  - `process_reactions.py:353` `_classify_reagent_role`

- RDF parsing (CAS lists, CTAB/MOL blocks, yield, reference):
  - `process_reactions.py:607` `parse_rdf`

- Row assembly + pairing TXT names with RDF CAS:
  - `process_reactions.py:1321` `assemble_rows`

- Markdown/JSONL report building with validation, ConditionCore label, roles:
  - `reaction_markdown_generator.py:338` `ReactionMarkdownGenerator`

- RDF-only GUI processing pipeline:
  - `Scifinder_rdf_processer.py:52` worker; `:407` window

## CAS Registry

- JSONL registry file: `cas_registry_merged.jsonl` (root). One JSON object per line with keys like `cas`, `name`, `abbreviation`, `compound_type`, `generic_core`, etc.
- Add/update entries programmatically:
  - `from Compound_registry_generator import ComprehensiveCASRegistry`
  - `reg.add_to_jsonl_registry(registry_path, ["75-05-8"], dry_run=False)`
  - `reg.update_jsonl_registry(registry_path, ["75-05-8"], dry_run=True)`
- Classifier and enrichment heuristics live in `Compound_registry_generator.py` and `Process_compound_registry.py`.
- GUI/reporting reads abbreviations and types through `CASRegistry` in `reaction_markdown_generator.py`.

## Datasets and Overrides

- Temperature/Time overrides come from `dataset/temp_time.md` when present and are applied in RDF-only flows.
- Example RDF test/corpus folders under `dataset/` produce Markdown and JSONL siblings (see existing `rdf_reactions_rich.*`).

## Testing

- Unit tests:
  - `tests/test_process_reactions.py`: parsing, pairing, roles, SMILES presence
  - `tests/test_cas_registry_tool.py`: CAS extraction, abbreviation filtering, JSONL add/update
- Run:
  - `pytest -q` (install `pytest` if `requirements-dev.txt` is missing)
- Tests avoid network; when adding tests, mock or disable online lookups.

## Common Tasks (safe change points)

- Improve name tokenization or locant handling:
  - Edit `process_reactions.py:145` `_normalize_token_list` and add unit tests.

- Adjust ligand/core heuristics or roles:
  - `process_reactions.py:279` `_classify_catalyst_or_ligand`
  - `process_reactions.py:353` `_classify_reagent_role`

- Enhance ConditionCore label in Markdown:
  - `reaction_markdown_generator.py:338` `ReactionMarkdownGenerator._compute_condition_core_label`

- Extend CAS registry abbreviations or types:
  - Update JSONL in place (keep one object per line) and/or tweak
    `Compound_registry_generator.py` selection logic.

## Guardrails for Agents

- Be surgical: don’t rename files or change public function signatures without coordinating updates across GUI, CLI, and tests.
- Preserve CSV/Markdown/JSONL formats; adding fields is okay if backward compatible and reflected in docs/tests.
- Keep RDKit optional; never hard-require it.
- Avoid network calls in tests and default code paths; gating via `requests` presence is acceptable.
- Large text/CTAB parsing must be streaming-friendly; avoid loading giant files into memory unnecessarily.

## Naming Drift Notes

- README references `cas_registry_tool.py` and `Combined_md_to_rich_report.py`, but the repo currently ships:
  - `Compound_registry_generator.py` and `Process_compound_registry.py`
  - `Scifinder_rdf_processer.py` and `reaction_markdown_generator.py`
- Prefer the files that exist in this tree; if you add compatibility shims, keep imports stable and tests green.

## Quick Commands

- Install: `pip install -r requirements.txt`
- Run CLI: `python process_reactions.py --rdf path.rdf --txt path.txt --out out.csv`
- Run RDF GUI: `python Scifinder_rdf_processer.py`
- Run tests: `pytest -q`

## Where to Look First

- For merging logic and schema: `process_reactions.py:1321`
- For Markdown layout & validation: `reaction_markdown_generator.py:338`
- For CAS normalization: `Compound_registry_generator.py:56`

If you need anything else scoped (e.g., add a CLI, fix a parser quirk), propose the change with a tiny plan and add narrow tests in `tests/` covering your change.

