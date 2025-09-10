"""
CLI utility to (re)assign compound_type values in cas_registry_merged.jsonl,
and to set a generic_core (e.g., Pd, Ni, Cu) for transition-metal-containing entries.
Also supports enriching entries with cheminformatics properties (SMILES, formula,
InChIKey, IUPAC name, molecular weight, exact mass) via PubChem with Cactus fallback.

Heuristics (priority order):
1) Ligand (phosphorus-based): if name/abbrev includes phosphine patterns
   - case-insensitive substrings and common abbreviations: "phos", "phosphine",
     PPh3, XPhos, SPhos, JohnPhos, tBuXPhos, dppf/dppb/dppe/dppp, etc.
2) Ligand (nitrogen-based): common N-ligands keywords: bpy, bipyridine, phenanthroline,
   TMEDA, terpyridine/terpy, pybox, diimine, iminopyridine, DMAP (conservative list).
3) Metal: if name/abbrev clearly mentions a transition metal (Pd, Ni, Cu, Pt, Rh, Ru, Ir,
   Co, Fe, Ag, Au, Mn, Cr, Mo, W, V, Ti, Zr, Hf, Sc, Y, La, Zn) using symbols or names.

Default behavior only fills empty/unknown fields. Use --force to overwrite existing
compound_type and/or generic_core values. Use --fetch-smiles and/or --fetch-props
to add a 'smile' field and other properties conservatively; use --smiles-force or
--props-force to overwrite.
Writes in-place with a .bak backup by default unless --no-backup is set.

How to run:
python Process_compound_registry.py --file cas_registry_merged.jsonl --fetch-smiles --verbose
python Process_compound_registry.py --file cas_registry_merged.jsonl --start-row 700 --fetch-smiles --verbose

"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from urllib.parse import quote
from typing import Dict, Any, Iterable, Tuple, Optional


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
        # Provide the ordered list of symbols for reverse-mapping
        "metal_symbols": metal_symbols,
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


def detect_generic_core(name: str, abbrev: str) -> Optional[str]:
    """Detect a generic core metal symbol (e.g., 'Cu', 'Pd') from name/abbrev.

    Strategy:
    - Prefer explicit element symbols with safe boundaries (Pd, Ni, Cu, ...)
    - Otherwise match full element names (copper, palladium, ...)
    Returns the first symbol found or None.
    """
    # 1) Check symbols with safe boundaries against the original (case-sensitive)
    for sym in PATTERNS.get("metal_symbols", []):
        rx = re.compile(rf"(^|[^A-Za-z]){re.escape(sym)}([^A-Za-z]|$)")
        if (name and rx.search(name)) or (abbrev and rx.search(abbrev)):
            return sym

    # 2) Check full names (case-insensitive) and map to symbols
    name_map = {
        "palladium": "Pd",
        "nickel": "Ni",
        "copper": "Cu",
        "platinum": "Pt",
        "rhodium": "Rh",
        "ruthenium": "Ru",
        "iridium": "Ir",
        "cobalt": "Co",
        "iron": "Fe",
        "silver": "Ag",
        "gold": "Au",
        "manganese": "Mn",
        "chromium": "Cr",
        "molybdenum": "Mo",
        "tungsten": "W",
        "vanadium": "V",
        "titanium": "Ti",
        "zirconium": "Zr",
        "hafnium": "Hf",
        "scandium": "Sc",
        "yttrium": "Y",
        "lanthanum": "La",
        "zinc": "Zn",
    }
    combined = f"{name} {abbrev}".lower()
    for key, sym in name_map.items():
        if key in combined:
            return sym
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
    # SMILES & property enrichment options
    fetch_smiles: bool = False,
    smiles_force: bool = False,
    smiles_source: str = "auto",  # 'pubchem' | 'cactus' | 'auto'
    request_timeout: float = 8.0,
    smiles_delay: float = 0.2,
    smiles_limit: Optional[int] = None,
    # additional properties beyond SMILES
    fetch_props: bool = False,
    props_force: bool = False,
    # processing control
    start_row: int = 1,
    # logging
    verbose: bool = False,
    progress_every: int = 50,
) -> Dict[str, Any]:
    """Process JSONL registry and update compound_type in-place unless dry_run.

    Args:
        start_row: Start processing from this row number (1-indexed, default: 1).
    
    Returns stats with counts and sample changes.
    """
    stats = {
        "total": 0,
        "updated": 0,
        "skipped_no_match": 0,
        "skipped_existing": 0,
        "by_type": {"ligand": 0, "metal": 0},
    "samples": [],
    "generic_core_updates": 0,
    # smiles
    "smiles_updated": 0,
    "smiles_skipped_existing": 0,
    "smiles_not_found": 0,
    "smiles_errors": 0,
    # other props
    "props_updated": 0,
    "formula_updated": 0,
    "inchikey_updated": 0,
    "iupac_name_updated": 0,
    "mw_updated": 0,
    "exact_mass_updated": 0,
    }

    if not os.path.exists(infile):
        raise FileNotFoundError(f"File not found: {infile}")

    # First pass: compute decisions and (if writing) write to temp file
    dirpath, base = os.path.split(infile)
    tmp_path = os.path.join(dirpath, f".{base}.tmp")

    out_fp = None
    if not dry_run:
        out_fp = open(tmp_path, "w", encoding="utf-8", newline="\n")

    # Lazy import requests only if SMILES fetching is enabled
    session = None
    if fetch_smiles or fetch_props:
        try:
            import requests  # type: ignore
            session = requests.Session()
            session.headers.update({"User-Agent": "Scifinder-Data-Process/SMILES-Fetcher"})
        except Exception:
            print("[WARN] 'requests' not available; SMILES fetching disabled.")
            fetch_smiles = False
            fetch_props = False

    def log(msg: str):
        if verbose:
            print(msg, flush=True)

    def info(msg: str):
        # Always show important messages and periodic progress when fetching
        if fetch_smiles or fetch_props:
            print(msg, flush=True)

    def _pubchem_smiles_by_cas(cas: str) -> Optional[str]:
        if not session:
            return None
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/xref/RN/{quote(cas)}/property/IsomericSMILES,CanonicalSMILES/JSON"
        try:
            r = session.get(url, timeout=request_timeout)
            if r.status_code != 200:
                return None
            data = r.json()
            props = (data or {}).get("PropertyTable", {}).get("Properties", [])
            if not props:
                return None
            rec = props[0]
            return rec.get("IsomericSMILES") or rec.get("CanonicalSMILES")
        except Exception:
            return None

    def _pubchem_smiles_by_name(name: str) -> Optional[str]:
        if not session:
            return None
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(name)}/property/IsomericSMILES,CanonicalSMILES/JSON"
        try:
            r = session.get(url, timeout=request_timeout)
            if r.status_code != 200:
                return None
            data = r.json()
            props = (data or {}).get("PropertyTable", {}).get("Properties", [])
            if not props:
                return None
            rec = props[0]
            return rec.get("IsomericSMILES") or rec.get("CanonicalSMILES")
        except Exception:
            return None

    def _pubchem_props_by_cas(cas: str) -> Optional[Dict[str, Any]]:
        if not session:
            return None
        props = "IsomericSMILES,CanonicalSMILES,MolecularFormula,InChIKey,IUPACName,ExactMass,MolecularWeight"
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/xref/RN/{quote(cas)}/property/{props}/JSON"
        try:
            r = session.get(url, timeout=request_timeout)
            if r.status_code != 200:
                return None
            data = r.json()
            arr = (data or {}).get("PropertyTable", {}).get("Properties", [])
            if not arr:
                return None
            rec = arr[0]
            return {
                "smile": rec.get("IsomericSMILES") or rec.get("CanonicalSMILES") or None,
                "formula": rec.get("MolecularFormula"),
                "inchikey": rec.get("InChIKey"),
                "iupac_name": rec.get("IUPACName"),
                "mw": rec.get("MolecularWeight"),
                "exact_mass": rec.get("ExactMass"),
            }
        except Exception:
            return None

    def _pubchem_props_by_name(name: str) -> Optional[Dict[str, Any]]:
        if not session:
            return None
        props = "IsomericSMILES,CanonicalSMILES,MolecularFormula,InChIKey,IUPACName,ExactMass,MolecularWeight"
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(name)}/property/{props}/JSON"
        try:
            r = session.get(url, timeout=request_timeout)
            if r.status_code != 200:
                return None
            data = r.json()
            arr = (data or {}).get("PropertyTable", {}).get("Properties", [])
            if not arr:
                return None
            rec = arr[0]
            return {
                "smile": rec.get("IsomericSMILES") or rec.get("CanonicalSMILES") or None,
                "formula": rec.get("MolecularFormula"),
                "inchikey": rec.get("InChIKey"),
                "iupac_name": rec.get("IUPACName"),
                "mw": rec.get("MolecularWeight"),
                "exact_mass": rec.get("ExactMass"),
            }
        except Exception:
            return None

    def _cactus_smiles(identifier: str) -> Optional[str]:
        if not session:
            return None
        url = f"https://cactus.nci.nih.gov/chemical/structure/{quote(identifier)}/smiles"
        try:
            r = session.get(url, timeout=request_timeout)
            if r.status_code != 200:
                return None
            txt = r.text.strip()
            return txt or None
        except Exception:
            return None

    def _cactus_props(identifier: str) -> Optional[Dict[str, Any]]:
        if not session:
            return None
        base = f"https://cactus.nci.nih.gov/chemical/structure/{quote(identifier)}"
        try:
            props: Dict[str, Any] = {}
            r = session.get(base + "/smiles", timeout=request_timeout)
            if r.status_code == 200:
                props["smile"] = r.text.strip() or None
            r = session.get(base + "/formula", timeout=request_timeout)
            if r.status_code == 200:
                props["formula"] = r.text.strip() or None
            # stdinchikey is preferred
            r = session.get(base + "/stdinchikey", timeout=request_timeout)
            if r.status_code == 200:
                props["inchikey"] = r.text.strip() or None
            return props or None
        except Exception:
            return None

    def _fetch_smiles_for_obj(obj: Dict[str, Any]) -> Optional[str]:
        cas = (obj.get("cas") or "").strip()
        name = (obj.get("name") or obj.get("chemical_name") or obj.get("abbreviation") or "").strip()
        # Try PubChem by CAS first
        if smiles_source in ("pubchem", "auto"):
            if cas:
                s = _pubchem_smiles_by_cas(cas)
                if s:
                    return s
            if name:
                s = _pubchem_smiles_by_name(name)
                if s:
                    return s
        # Fallback to Cactus
        if smiles_source in ("cactus", "auto"):
            for ident in (cas, name):
                if ident:
                    s = _cactus_smiles(ident)
                    if s:
                        return s
        return None

    def _fetch_props_for_obj(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cas = (obj.get("cas") or "").strip()
        name = (obj.get("name") or obj.get("chemical_name") or obj.get("abbreviation") or "").strip()
        # PubChem first
        if smiles_source in ("pubchem", "auto"):
            if cas:
                d = _pubchem_props_by_cas(cas)
                if d:
                    return d
            if name:
                d = _pubchem_props_by_name(name)
                if d:
                    return d
        # Cactus fallback
        if smiles_source in ("cactus", "auto"):
            for ident in (cas, name):
                if ident:
                    d = _cactus_props(ident)
                    if d:
                        return d
        return None

    smiles_updates_done = 0
    props_updates_done = 0

    if fetch_smiles or fetch_props:
        info("Starting processing: {} (from row {})".format(infile, start_row))
        if not verbose:
            info("Tip: add --verbose for per-entry logs. Use --progress-every N to tune progress prints.")
    try:
        with open(infile, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, start=1):
                # Skip rows before start_row, but always write them to output
                if idx < start_row:
                    if out_fp:
                        out_fp.write(line)
                    continue
                    
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
                # Always attempt to determine generic core metal for transition-metal containing entries
                gen_core_suggestion = detect_generic_core(name, abbr)

                # Independently update generic_core when detectable
                if gen_core_suggestion:
                    existing_gc = obj.get("generic_core")
                    if should_update(existing_gc, force):
                        obj["generic_core"] = gen_core_suggestion
                        stats["generic_core_updates"] += 1

                # Optionally enrich SMILES and properties before early-continue so even non-classified entries can be enriched
                did_fetch = False
                if (fetch_smiles or fetch_props) and (smiles_limit is None or (smiles_updates_done + props_updates_done) < smiles_limit):
                    try:
                        data: Optional[Dict[str, Any]] = None
                        if fetch_props:
                            data = _fetch_props_for_obj(obj)
                        elif fetch_smiles:
                            s = _fetch_smiles_for_obj(obj)
                            data = {"smile": s} if s else None
                        if data:
                            # Apply SMILES
                            if "smile" in data and data.get("smile"):
                                if should_update(obj.get("smile"), smiles_force):
                                    obj["smile"] = data["smile"]
                                    stats["smiles_updated"] += 1
                                    smiles_updates_done += 1
                                    log(f"[{idx}] SMILES set for {obj.get('cas') or obj.get('name')}: {obj['smile']}")
                                else:
                                    stats["smiles_skipped_existing"] += 1
                                    log(f"[{idx}] SMILES kept (existing) for {obj.get('cas') or obj.get('name')}")
                            else:
                                stats["smiles_not_found"] += 1
                                log(f"[{idx}] SMILES not found for {obj.get('cas') or obj.get('name')}")
                            # Apply other props (controlled by props_force)
                            def _apply(key: str, stat_key: str):
                                val = data.get(key)
                                if not val:
                                    return
                                if should_update(obj.get(key), props_force):
                                    obj[key] = val
                                    stats[stat_key] += 1
                                    stats["props_updated"] += 1
                                    log(f"[{idx}] {key} set for {obj.get('cas') or obj.get('name')}: {val}")
                            if fetch_props:
                                _apply("formula", "formula_updated")
                                _apply("inchikey", "inchikey_updated")
                                _apply("iupac_name", "iupac_name_updated")
                                _apply("mw", "mw_updated")
                                _apply("exact_mass", "exact_mass_updated")
                            did_fetch = True
                            if smiles_delay:
                                time.sleep(smiles_delay)
                    except Exception:
                        stats["smiles_errors"] += 1
                        log(f"[{idx}] Error fetching properties for {obj.get('cas') or obj.get('name')}")

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

                # Periodic progress
                if progress_every > 0 and (idx % progress_every == 0):
                    msg = (
                        f"[progress] processed {idx} lines | role updates: {stats['updated']} | "
                        f"smiles: {stats['smiles_updated']} | props: {stats['props_updated']}"
                    )
                    if verbose:
                        log(msg)
                    else:
                        info(msg)

                # Always write the processed object
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
    except KeyboardInterrupt:
        # Graceful cleanup of temp file
        try:
            if out_fp and not out_fp.closed:
                out_fp.close()
        finally:
            if not dry_run and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        info("Interrupted by user. Temporary file cleaned up.")
        raise
    except Exception:
        # On unexpected error, best-effort cleanup temp file
        try:
            if out_fp and not out_fp.closed:
                out_fp.close()
        finally:
            if not dry_run and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        raise

    if fetch_smiles or fetch_props:
        info(
            f"Done. Total: {stats['total']}; role updates: {stats['updated']}; smiles: {stats['smiles_updated']}; props: {stats['props_updated']}"
        )
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
    # SMILES enrichment flags
    p.add_argument(
        "--fetch-smiles",
        action="store_true",
        help="Fetch SMILES for registry entries and add a 'smile' field",
    )
    p.add_argument(
        "--smiles-force",
        action="store_true",
        help="Overwrite existing non-empty 'smile' values",
    )
    p.add_argument(
        "--smiles-source",
        choices=["auto", "pubchem", "cactus"],
        default="auto",
        help="Which source to use for SMILES (default: auto)",
    )
    p.add_argument(
        "--smiles-timeout",
        type=float,
        default=8.0,
        help="HTTP timeout (seconds) per request (default: 8)",
    )
    p.add_argument(
        "--smiles-delay",
        type=float,
        default=0.2,
        help="Delay between requests to be polite (default: 0.2s)",
    )
    p.add_argument(
        "--smiles-limit",
        type=int,
        default=None,
        help="Maximum number of SMILES updates to perform (default: unlimited)",
    )
    # Logging
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-entry progress and periodic status to the console",
    )
    p.add_argument(
        "--progress-every",
        type=int,
        default=50,
        help="Print periodic progress every N entries when --verbose is set (default: 50)",
    )
    # Additional property enrichment
    p.add_argument(
        "--fetch-props",
        action="store_true",
        help="Fetch additional properties (formula, InChIKey, IUPAC name, MW, exact mass)",
    )
    p.add_argument(
        "--props-force",
        action="store_true",
        help="Overwrite existing non-empty property fields (formula, InChIKey, etc.)",
    )
    # Processing control
    p.add_argument(
        "--start-row",
        type=int,
        default=1,
        help="Start processing from this row number (1-indexed, default: 1)",
    )
    args = p.parse_args(argv)

    try:
        stats = process_file(
            infile=args.file,
            force=args.force,
            dry_run=args.dry_run,
            backup=not args.no_backup,
            fetch_smiles=args.fetch_smiles,
            smiles_force=args.smiles_force,
            smiles_source=args.smiles_source,
            request_timeout=args.smiles_timeout,
            smiles_delay=args.smiles_delay,
            smiles_limit=args.smiles_limit,
            fetch_props=args.fetch_props,
            props_force=args.props_force,
            start_row=args.start_row,
            verbose=args.verbose,
            progress_every=args.progress_every,
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
                "generic_core_updates": stats.get("generic_core_updates", 0),
                "samples": stats["samples"],
                "smiles_updated": stats.get("smiles_updated", 0),
                "smiles_skipped_existing": stats.get("smiles_skipped_existing", 0),
                "smiles_not_found": stats.get("smiles_not_found", 0),
                "smiles_errors": stats.get("smiles_errors", 0),
                # other props
                "props_updated": stats.get("props_updated", 0),
                "formula_updated": stats.get("formula_updated", 0),
                "inchikey_updated": stats.get("inchikey_updated", 0),
                "iupac_name_updated": stats.get("iupac_name_updated", 0),
                "mw_updated": stats.get("mw_updated", 0),
                "exact_mass_updated": stats.get("exact_mass_updated", 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
