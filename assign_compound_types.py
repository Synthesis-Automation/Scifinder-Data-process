"""
CLI utility to (re)assign compound_type values in cas_registry_merged.jsonl.

Heuristics (priority order):
1) Ligand (phosphorus-based): if name/abbrev includes phosphine patterns
   - case-insensitive substrings and common abbreviations: "phos", "phosphine",
     PPh3, XPhos, SPhos, JohnPhos, tBuXPhos, dppf/dppb/dppe/dppp, etc.
2) Ligand (nitrogen-based): common N-ligands keywords: bpy, bipyridine, phenanthroline,
   TMEDA, terpyridine/terpy, pybox, diimine, iminopyridine, DMAP (conservative list).
3) Metal: if name/abbrev clearly mentions a transition metal (Pd, Ni, Cu, Pt, Rh, Ru, Ir,
   Co, Fe, Ag, Au, Mn, Cr, Mo, W, V, Ti, Zr, Hf, Sc, Y, La, Zn) using symbols or names.

Default behavior only fills empty/unknown compound_type. Use --force to overwrite.
Writes in-place with a .bak backup by default unless --no-backup is set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from typing import Dict, Any, Iterable, Tuple


def compile_patterns() -> Dict[str, Iterable[re.Pattern]]:
    """Prepare compiled regex patterns for categories."""
    # Phosphine/PR3 ligand patterns (case-insensitive)
    phosphine_keywords = [
        r"phos",  # XPhos, SPhos, JohnPhos, etc.
        r"phosphine",
        r"phosphane",
        r"\bpph\b",  # PPh
        r"\bpph\d\b",  # PPh3
        r"\bxphos\b",
        r"\bsphos\b",
        r"\bjohnphos\b",
        r"\btbuxphos\b",
        r"\bmphos\b",
        r"\bmephos\b",
        r"\bjackiephos\b",
        r"\btrixphos\b",
        # Common diphosphines (do not contain 'phos')
        r"\bdppf\b",
        r"\bdppb\b",
        r"\bdppe\b",
        r"\bdppp\b",
        r"\bdpppe\b",
        # PR3 shorthand
        r"\bpcy3\b",
        r"\bptbu3\b",
        r"p\(tbu\)3",  # P(tBu)3
        r"\bpad3\b",
    ]

    phosphine = [re.compile(pat, re.IGNORECASE) for pat in phosphine_keywords]

    # Nitrogen ligands
    n_ligand_keywords = [
        r"\bbpy\b",  # 2,2'-bipyridine
        r"\bbipyrid",  # bipyridine variants
        r"\bphenanthroline\b",
        r"\b1,10-phen\b",
        r"\btmeda\b",
        r"\bterpy\b",
        r"\bterpyrid",
        r"\bpybox\b",
        r"\bdiimine\b",
        r"\biminopyridin",
        r"\bdmap\b",  # DMAP (often used as ligand/base)
    ]
    n_ligand = [re.compile(pat, re.IGNORECASE) for pat in n_ligand_keywords]

    # Transition metal symbols with safe boundaries (avoid matching parts of words)
    # We'll detect symbol in forms like 'Pd', 'Pd(', 'Pd/', 'Pd ', 'Pd[', 'PdO', etc.
    # Also match full element names.
    metal_symbols = [
        "Pd", "Ni", "Cu", "Pt", "Rh", "Ru", "Ir", "Co", "Fe", "Ag", "Au",
        "Mn", "Cr", "Mo", "W", "V", "Ti", "Zr", "Hf", "Sc", "Y", "La", "Zn",
    ]
    # Build regex that matches symbol with non-letter before/after or start/end
    sym_patterns = []
    for sym in metal_symbols:
        # word boundary-like: (^|[^A-Za-z])Sym([^A-Za-z]|$)
        sym_patterns.append(re.compile(rf"(^|[^A-Za-z]){re.escape(sym)}([^A-Za-z]|$)"))

    metal_names = [
        r"palladium", r"nickel", r"copper", r"platinum", r"rhodium", r"ruthenium",
        r"iridium", r"cobalt", r"iron", r"silver", r"gold", r"manganese", r"chromium",
        r"molybdenum", r"tungsten", r"vanadium", r"titanium", r"zirconium", r"hafnium",
        r"scandium", r"yttrium", r"lanthanum", r"zinc",
    ]
    metal_fullnames = [re.compile(pat, re.IGNORECASE) for pat in metal_names]

    return {
        "phosphine": phosphine,
        "n_ligand": n_ligand,
        "metal_sym": sym_patterns,
        "metal_name": metal_fullnames,
    }


PATTERNS = compile_patterns()


def text_fields(entry: Dict[str, Any]) -> Tuple[str, str]:
    """Return the (name, abbrev) strings from a registry entry if present."""
    name = entry.get("name") or entry.get("chemical_name") or ""
    # Allow a few possible keys users might have used
    abbrev = (
        entry.get("abbrev")
        or entry.get("abbreviation")
        or entry.get("short_name")
        or ""
    )
    return str(name), str(abbrev)


def detect_type(name: str, abbrev: str) -> str | None:
    """Detect a suggested compound_type from name/abbrev using heuristics.

    Priority: phosphine ligand > nitrogen ligand > metal. Returns one of
    {"ligand", "metal"} or None if no classification found.
    """
    # Merge text for searching, keeping originals for symbol-boundary tests.
    name_l = name.lower()
    abbr_l = abbrev.lower()
    combined = f"{name_l} {abbr_l}".strip()

    # 1) Phosphine ligand
    if combined:
        for rx in PATTERNS["phosphine"]:
            if rx.search(combined):
                return "ligand"

    # 2) Nitrogen ligand
    if combined:
        for rx in PATTERNS["n_ligand"]:
            if rx.search(combined):
                return "ligand"

    # 3) Transition metal
    # Check symbol patterns against original text to keep case distinctions (Pd vs pd in words)
    for rx in PATTERNS["metal_sym"]:
        if (name and rx.search(name)) or (abbrev and rx.search(abbrev)):
            return "metal"
    for rx in PATTERNS["metal_name"]:
        if rx.search(combined):
            return "metal"

    return None


def should_update(existing: Any, force: bool) -> bool:
    if force:
        return True
    if existing is None:
        return True
    if isinstance(existing, str) and existing.strip() == "":
        return True
    # Treat placeholder/unknown as updatable
    if isinstance(existing, str) and existing.lower() in {"unknown", "other", "na", "n/a"}:
        return True
    return False


def process_file(
    infile: str,
    force: bool = False,
    dry_run: bool = False,
    backup: bool = True,
) -> Dict[str, Any]:
    """Process JSONL registry and update compound_type in-place unless dry_run.

    Returns stats with counts and sample changes.
    """
    stats = {
        "total": 0,
        "updated": 0,
        "skipped_no_match": 0,
        "skipped_existing": 0,
        "by_type": {"ligand": 0, "metal": 0},
        "samples": [],
    }

    if not os.path.exists(infile):
        raise FileNotFoundError(f"File not found: {infile}")

    # First pass: compute decisions and (if writing) write to temp file
    dirpath, base = os.path.split(infile)
    tmp_path = os.path.join(dirpath, f".{base}.tmp")

    out_fp = None
    if not dry_run:
        out_fp = open(tmp_path, "w", encoding="utf-8", newline="\n")

    with open(infile, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                if out_fp:
                    out_fp.write(line)
                continue
            try:
                obj = json.loads(line)
            except Exception:
                # Preserve unparseable lines verbatim
                if out_fp:
                    out_fp.write(line)
                continue

            stats["total"] += 1
            name, abbr = text_fields(obj)
            suggestion = detect_type(name, abbr)
            existing = obj.get("compound_type")

            if suggestion is None:
                stats["skipped_no_match"] += 1
                if out_fp:
                    out_fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
                continue

            if not should_update(existing, force):
                stats["skipped_existing"] += 1
                if out_fp:
                    out_fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
                continue

            # Apply update
            obj["compound_type"] = suggestion
            stats["updated"] += 1
            stats["by_type"][suggestion] = stats["by_type"].get(suggestion, 0) + 1
            if len(stats["samples"]) < 10:
                stats["samples"].append(
                    {
                        "name": name,
                        "abbrev": abbr,
                        "new_type": suggestion,
                        "prev_type": existing,
                        "cas": obj.get("cas"),
                    }
                )

            if out_fp:
                out_fp.write(json.dumps(obj, ensure_ascii=False) + "\n")

    if out_fp:
        out_fp.close()

    # If not dry-run, replace original with temp and create backup if needed
    if not dry_run:
        if backup:
            bak_path = infile + ".bak"
            shutil.copy2(infile, bak_path)
        os.replace(tmp_path, infile)

    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Assign compound_type in a JSONL CAS registry using simple heuristics",
    )
    p.add_argument(
        "--file",
        "-f",
        default="cas_registry_merged.jsonl",
        help="Path to the JSONL registry file (default: cas_registry_merged.jsonl)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-empty compound_type values",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write changes; just report what would change",
    )
    p.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a .bak backup when writing",
    )
    args = p.parse_args(argv)

    try:
        stats = process_file(
            infile=args.file,
            force=args.force,
            dry_run=args.dry_run,
            backup=not args.no_backup,
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    # Compact report
    print(
        json.dumps(
            {
                "file": os.path.abspath(args.file),
                "dry_run": args.dry_run,
                "force": args.force,
                "total": stats["total"],
                "updated": stats["updated"],
                "skipped_no_match": stats["skipped_no_match"],
                "skipped_existing": stats["skipped_existing"],
                "by_type": stats["by_type"],
                "samples": stats["samples"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
