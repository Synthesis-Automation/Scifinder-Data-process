import io
import json
import os
import sys
from pathlib import Path
import tempfile

import pytest

# Ensure the repository root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Compound_registry_generator import ComprehensiveCASRegistry


def test_extract_cas_from_text(tmp_path: Path):
    p = tmp_path / "notes.txt"
    p.write_text(
        """
        Some random text.
        Valid: 67-56-1; Also 7732-18-5.
        Invalid: 12-34-56 (bad checksum)
        Another valid is 75-09-2.
        """,
        encoding="utf-8",
    )
    reg = ComprehensiveCASRegistry()
    found = reg.extract_cas_from_text(str(p))
    assert "67-56-1" in found
    assert "7732-18-5" in found
    assert "75-09-2" in found
    assert "12-34-56" not in found


def test_abbreviation_filtering_conservative(monkeypatch):
    reg = ComprehensiveCASRegistry()

    # Simulate PubChem synonyms including code-like IDs and a good one
    synonyms = [
        "FD21675",
        "DB01345",
        "NSC-12345",
        "DMF",
    ]
    abbr = reg._choose_abbreviation("68-12-2", "Dimethylformamide", synonyms)
    assert abbr == "DMF"

    # If only code-like entries, returns empty
    synonyms2 = ["FD21675", "DB01345", "NSC-12345"]
    abbr2 = reg._choose_abbreviation("7732-18-5", "Water", synonyms2)
    assert abbr2 == ""


def test_jsonl_append_and_update(tmp_path: Path, monkeypatch):
    reg = ComprehensiveCASRegistry()

    # Prepare empty JSONL
    jsonl = tmp_path / "cas_registry_merged.jsonl"
    jsonl.write_text("", encoding="utf-8")

    # Add one CAS (use MeCN which has known abbr MeCN)
    to_add = ["75-05-8"]

    # Avoid network calls in tests: make lookup_pubchem return None
    monkeypatch.setattr(ComprehensiveCASRegistry, "lookup_pubchem", lambda self, cas: None)

    added, skipped = reg.add_to_jsonl_registry(str(jsonl), to_add, dry_run=False)
    assert added == 1 and skipped == 0

    # Add same again should skip
    added2, skipped2 = reg.add_to_jsonl_registry(str(jsonl), to_add, dry_run=False)
    assert added2 == 0 and skipped2 == 1

    # Update existing should not change anything important but should succeed with zero updates
    updated, not_found = reg.update_jsonl_registry(str(jsonl), to_add, dry_run=True)
    assert not_found == 0
    assert updated in (0, 1)  # may update sources if empty

    # Ensure JSONL is valid one-line JSON
    lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj.get("cas") == "75-05-8"
    assert obj.get("abbreviation") in ("MeCN", "")
