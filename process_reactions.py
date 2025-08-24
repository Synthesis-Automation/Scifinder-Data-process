#!/usr/bin/env python3
"""
CLI to parse a SciFinder TXT export and a RXN/RDF export, merge by Reaction ID,
and write a flat CSV conforming to reaction_dataset_schema.md.

Assumptions and heuristics:
- TXT is the primary source for names of catalysts, ligands, reagents, solvents, time, temp.
- RXN/RDF is the authoritative source for ReactionID, CAS lists, and reported yield.
- Ligands are items listed under "Catalysts:" that do not look like metal salts/precursors.
- ReactionType is inferred from presence of metal: Cu -> "Ullmann", Pd -> "Buchwald", else "Other".
- Time_h = sum of all durations found across steps; Temperature_C = max numeric temperature found;
  "rt" -> 25 °C; "overnight" -> 16 h; "reflux" ignored (cannot infer solvent boiling point robustly).
- JSON arrays are stored as strings of JSON lists as per schema.

Usage:
    python process_reactions.py --rdf Reaction_2024-1.rdf --txt Reaction_2024-1.txt --out reactions.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional

try:
    import xxhash  # type: ignore
except Exception:  # pragma: no cover
    xxhash = None  # We'll check at runtime

# RDKit is optional; enable SMILES extraction when available
try:  # pragma: no cover - import tested in runtime
    from rdkit import Chem  # type: ignore
except Exception:  # pragma: no cover
    Chem = None  # type: ignore


# ------------------------------ Schema helpers ------------------------------

def _json_list(items: List[str]) -> str:
    # Keep stable ordering: unique preserving first-seen order
    seen = set()
    out: List[str] = []
    for it in items:
        key = it.strip()
        if not key:
            continue
        if key not in seen:
            seen.add(key)
            out.append(key)
    return json.dumps(out, ensure_ascii=False)


def _json_pairs(pairs: List[Dict[str, str]]) -> str:
    """Serialize a list of {name, cas} pairs as JSON for machine-friendly consumption.
    Values may be empty strings when unknown.
    """
    # Normalize keys and remove exact duplicates while preserving order
    seen = set()
    norm: List[Dict[str, str]] = []
    for p in pairs:
        name = (p.get('name') or '').strip()
        cas = (p.get('cas') or '').strip()
        key = (name, cas)
        if key in seen:
            continue
        seen.add(key)
        norm.append({'name': name, 'cas': cas})
    return json.dumps(norm, ensure_ascii=False)


def _pair_str(name: str | None, cas: str | None) -> str:
    """Render a single compound as "name|cas" using a single space when missing."""
    nm = (name or '').strip() or ' '
    cs = (cas or '').strip() or ' '
    return f"{nm}|{cs}"


def _hash32_hex(s: str) -> str:
    if xxhash is None:
        return ""
    return xxhash.xxh32_hexdigest(s)


def build_condkey(row: Dict[str, str]) -> str:
    def _join(col):
        try:
            return "+".join(sorted(json.loads(row.get(col, "[]")))) or "none"
        except Exception:
            return "none"

    cg = _join("CatalystCoreGeneric")
    lig = _join("Ligand")
    bas = _join("Reagent")
    solv = _join("Solvent")
    return f"{cg}/{lig}/{bas}/{solv}"


def build_condsig(row: Dict[str, str]) -> str:
    parts = []
    for c in ["CatalystCoreGeneric", "Ligand", "Reagent", "Solvent"]:
        try:
            parts.append("+".join(sorted(json.loads(row.get(c, "[]")))))
        except Exception:
            parts.append("")
    return _hash32_hex("|".join(parts))


def build_famsig(row: Dict[str, str]) -> str:
    # collapse metal detail: here CatalystCoreGeneric is already generic tokens
    try:
        core = json.loads(row.get("CatalystCoreGeneric", "[]"))
        lig = json.loads(row.get("Ligand", "[]"))
        reag = json.loads(row.get("Reagent", "[]"))
        solv = json.loads(row.get("Solvent", "[]"))
    except Exception:
        return ""

    # collapse reagents by head token before '-' (very rough)
    reag_collapsed = [r.split("-")[0] for r in reag]
    key = "|".join([
        "+".join(sorted(core)),
        "+".join(sorted(lig)),
        "+".join(sorted(reag_collapsed)),
        "+".join(sorted(solv)),
    ])
    return _hash32_hex(key)


# --------------------------- Parsing the TXT file ---------------------------

_RE_TIME = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>h|hr|hrs|hour|hours|min|mins|minute|minutes|d|day|days)\b", re.I)
_RE_TEMP_C = re.compile(r"(?P<val>-?\d+(?:\.\d+)?)\s*[^A-Za-z0-9]{0,3}C\b")  # tolerate broken degree symbol


def _normalize_token_list(s: str) -> List[str]:
    """Split a comma-separated list into tokens, but keep substituent designators
    like N,N′-, N,O-, O,O′- together as a single chemical name.

    Heuristic:
    - Initially split on commas.
    - Then merge runs of single-letter designators (N/O/S/P/C) that precede a token
      starting with a designator prefix such as "N-", "N′-", "O-", or with a space
      (e.g., "N diethyl...").
    This reconstructs names like "N,N-diisopropylethylamine" and "N,O-bis(...)".
    """
    raw = [t.strip().strip(';').strip() for t in s.split(',')]
    raw = [t for t in raw if t]

    def _is_single_designator(tok: str) -> bool:
        return tok in {"N", "O", "S", "P", "C"}

    def _is_numeric_locant(tok: str) -> bool:
        # pure integer like 1, 2, 4,6 etc. (after initial split by comma we see one at a time)
        return bool(re.fullmatch(r"\d+", tok))

    def _is_letter_index_locant(tok: str) -> bool:
        # N1, N2, O1 style locants
        return bool(re.fullmatch(r"[NOSPC]\d+", tok, flags=re.IGNORECASE))

    def _starts_with_designator_prefix(tok: str) -> bool:
        # Accept N-, N′-, N1-, O-, S-, or with space after the designator
        return bool(re.match(r"^[NOSPC](?:\d+)?(?:['′])?(?:-|\s).+", tok, flags=re.IGNORECASE))

    def _starts_with_numeric_prefix(tok: str) -> bool:
        # Accept leading number like 2-..., 2,4-..., 12 ... (with hyphen or space)
        return bool(re.match(r"^\d+(?:-|\s).+", tok))

    merged: List[str] = []
    i = 0
    while i < len(raw):
        # 1) Merge numeric locant runs like "1,2-..." into a single token
        j = i
        nums: List[str] = []
        while j < len(raw) and _is_numeric_locant(raw[j]):
            nums.append(raw[j])
            j += 1
        if nums and j < len(raw) and _starts_with_numeric_prefix(raw[j]):
            merged.append(",".join(nums + [raw[j]]))
            i = j + 1
            continue

        # 2) Merge heteroatom locants like "N1,N2-..." and simple designators like "N,N-..."
        j = i
        desigs: List[str] = []
        while j < len(raw) and (_is_single_designator(raw[j]) or _is_letter_index_locant(raw[j])):
            desigs.append(raw[j])
            j += 1
        if desigs and j < len(raw) and _starts_with_designator_prefix(raw[j]):
            merged.append(",".join(desigs + [raw[j]]))
            i = j + 1
            continue

        # 3) Default: keep token as is
        merged.append(raw[i])
        i += 1

    return merged


def _is_condition_token(tok: str) -> bool:
    """Return True if the token looks like a condition fragment (time/temperature keywords)."""
    t = tok.strip()
    if not t:
        return False
    if _RE_TEMP_C.search(t):
        return True
    if _RE_TIME.search(t):
        return True
    tlo = t.lower()
    if tlo in {"rt", "room temperature", "reflux", "overnight"}:
        return True
    # simple catch: tokens like "120C" without space
    if re.search(r"\b\d+\s*(?:c|°c)\b", tlo):
        return True
    return False


def _classify_catalyst_or_ligand(name: str) -> Tuple[str, str]:
    """Return (kind, generic) where kind in {"core", "ligand"} and generic metal tag.
    generic may be "Pd", "Cu(I)", "Cu(II)", "Cu", "Ni", "Ir", "Rh", or "".
    """
    n = name.lower()
    metal = ""
    if any(x in n for x in ["palladium", "pd("]):
        metal = "Pd"
    if any(x in n for x in ["nickel", "ni("]):
        metal = "Ni"
    if any(x in n for x in ["iridium", "ir("]):
        metal = "Ir"
    if any(x in n for x in ["rhodium", "rh("]):
        metal = "Rh"
    if "cuprous" in n or "cu(i)" in n:
        metal = "Cu(I)"
    elif "cupric" in n or "cu(ii)" in n:
        metal = "Cu(II)"
    elif "copper" in n or n.startswith("cu ") or n.startswith("cu-") or n == "cu":
        metal = "Cu"

    # Decide ligand-like patterns (typical Pd/Cu ligands): phosphines, bipyridines, phenanthrolines, common trade names
    ligand_keywords = [
        "xphos", "sphos", "ruph", "brettphos", "johnphos", "tbu xphos", "ruphose", "ruphose",
        "binap", "segphos", "xantphos", "dppf", "dppe", "dppp", "dppb", "pph3", "pcy3", "p(o)ph3",
        "phosphine", "phosphite", "phosphonite",
        "bpy", "bipyridine", "2,2'-bipyridine", "phenanthroline", "phen",
        "imes", "ipr", "simes", "nhc",
    ]
    ligand_like = any(k in n for k in ligand_keywords)
    # Metal precursors (cores) include explicit metal salts/precursors
    is_metal_precursor = bool(metal) or (any(k in n for k in ["oxide", "bromide", "iodide", "chloride", "acetate", "triflate", "acac", "sulfate"]) and ("copper" in n or "palladium" in n or "nickel" in n))
    # Heuristic: if it looks like those ligands, call it ligand; otherwise treat as core (covers organocatalysts like DMAP)
    kind = "ligand" if (ligand_like and not is_metal_precursor) else "core"
    return kind, metal


def _is_metal_like_name(name: str) -> bool:
    n = name.lower().strip()
    # quick element/metal salt cues
    metal_words = ["copper", "palladium", "nickel", "iridium", "rhodium", "silver", "gold", "zinc", "iron", "ruthenium"]
    metal_symbols = ["cu", "pd", "ni", "ir", "rh", "ag", "au", "zn", "fe", "ru"]
    if any(w in n for w in metal_words):
        return True
    # standalone or prefixed symbols
    if re.match(r"^(cu|pd|ni|ir|rh|ag|au|zn|fe|ru)\b", n):
        return True
    # salts/precursor cues when combined with a metal word in the full token
    salt_cues = ["oxide", "bromide", "iodide", "chloride", "acetate", "triflate", "acac", "sulfate", "carbonate"]
    if any(k in n for k in salt_cues) and any(w in n for w in metal_words):
        return True
    return False


def _classify_reagent_role(name: str) -> str:
    n = name.lower()
    if any(k in n for k in [
        "carbonate", "phosphate", "tripotassium phosphate", "dipotassium phosphate",
        "methoxide", "ethoxide", "tert-butoxide", "t-butoxide",
        "trimethylsilanolate", "triethylamine", "diisopropylethylamine", "hunig",
        "pyridine", "imidazole", "dmf base", "koh", "naoh", "hydroxide",
        "potassium tert-butoxide", "cesium carbonate", "sodium carbonate"
    ]):
        return "BASE"
    if any(k in n for k in ["water", "h2o", "brine", "nh4cl", "ammonium chloride", "work-up"]):
        return "WORKUP"
    if any(k in n for k in ["oxygen", "air", "peroxide", "selenium", "nbs", "ncs", "silver fluoride"]):
        return "OX"
    if any(k in n for k in ["sodium azide", "azide", "amine", "morpholine", "aniline", "indole", "carbazole"]):
        return "NUC"
    return "UNK"


def parse_txt(path: str) -> Dict[str, Dict[str, Any]]:
    reactions: Dict[str, Dict[str, Any]] = {}
    current_title = ""
    current_authors = ""
    current_citation = ""

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [ln.rstrip('\n') for ln in f]

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Capture Title / Authors / Citation blocks
        if line and not line.startswith(('Steps:', 'CAS Reaction Number:', 'View All', 'Reactions (', 'Search', 'Filtered By:', 'Scheme')) and not line.startswith('By:') and not line.startswith('10.'):
            # Likely a title line (very heuristic)
            current_title = line
        if line.startswith('By:'):
            current_authors = line.replace('By:', '').strip()
        # Journal/citation line often contains a year in parentheses
        if re.search(r"\(20\d{2}\)", line):
            # Prefer the line that looks like Journal (year), vol, pages.
            current_citation = line.strip()

        # If we hit a reaction header, start collecting
        if line.startswith('Steps:'):
            # Parse the yield on same line if present
            m = re.search(r"Yield:\s*([0-9]{1,3})\s*%", line)
            pending_yield = int(m.group(1)) if m else None
            # Look ahead for the first CAS Reaction Number in this block (robust window)
            j = i + 1
            rid = None
            while j < len(lines):
                sj = lines[j].strip()
                if sj.startswith('CAS Reaction Number:'):
                    rid = sj.split(':', 1)[1].strip()
                    break
                # stop if we hit the next block header to avoid crossing blocks
                if sj.startswith('Steps:') or sj.startswith('Scheme '):
                    break
                # hard stop window to avoid pathological scans
                if j - i > 200:
                    break
                j += 1
            if rid:
                # Init record
                rec = reactions.setdefault(rid, {
                    'title': current_title,
                    'authors': current_authors,
                    'citation': current_citation,
                    'txt_yield': pending_yield,
                    'reagents': [],
                    'catalysts': [],
                    'solvents': [],
                    'all_condition_lines': [],
                })

                # Collect step details until the next blank separator or next scheme/title block
                # Collect step details for this block starting after the Steps: line
                k = i + 1
                while k < len(lines):
                    s = lines[k].strip()
                    if not s:
                        k += 1
                        continue
                    # Stop if we hit the next top-level block: a title line (not starting with digit or label) followed by By:/Steps
                    if s.startswith('Steps:') or s.startswith('Scheme '):
                        break
                    # Many blocks end with a line that's just a '?'
                    if s == '?':
                        k += 1
                        break
                    # Collect content; SciFinder often uses '|' separators and step prefixes like '1.1|'
                    segments = [seg.strip() for seg in (s.split('|') if '|' in s else [s]) if seg.strip()]
                    for seg in segments:
                        rec['all_condition_lines'].append(seg)
                    low = s.lower()
                    # Support label variants like "Reagent(s):", "Additives:", "Catalyst(s):", "Solvent(s):", "Base:"
                    def _after_label(lbls: List[str]) -> Optional[str]:
                        for lbl in lbls:
                            if low.startswith(lbl):
                                return s.split(':', 1)[1].strip() if ':' in s else s[len(lbl):].strip()
                        return None
                    # Extract and split while dropping trailing condition fragments after ';'
                    def _list_from_rest(rest: str) -> List[str]:
                        before = rest.split(';', 1)[0].strip()
                        toks = [t for t in _normalize_token_list(before) if not _is_condition_token(t)]
                        return toks

                    handled = False
                    for seg in segments:
                        lowseg = seg.lower()
                        # Reagents/Additives
                        if any(lowseg.startswith(lbl) for lbl in ['reagents:', 'reagent:', 'reagent(s):', 'additives:', 'additive:']):
                            rest = seg.split(':', 1)[1].strip() if ':' in seg else ''
                            rec['reagents'].extend(_list_from_rest(rest))
                            handled = True
                            continue
                        # Catalysts
                        if any(lowseg.startswith(lbl) for lbl in ['catalysts:', 'catalyst:', 'catalyst(s):']):
                            rest = seg.split(':', 1)[1].strip() if ':' in seg else ''
                            rec['catalysts'].extend(_list_from_rest(rest))
                            handled = True
                            continue
                        # Base
                        if any(lowseg.startswith(lbl) for lbl in ['base:', 'base(s):', 'bases:']):
                            rest = seg.split(':', 1)[1].strip() if ':' in seg else ''
                            toks = _list_from_rest(rest)
                            rec['reagents'].extend(toks)
                            rec.setdefault('base_from_txt', []).extend(toks)
                            handled = True
                            continue
                        # Solvents
                        if any(lowseg.startswith(lbl) for lbl in ['solvents:', 'solvent:', 'solvent(s):']):
                            rest = seg.split(':', 1)[1].strip() if ':' in seg else ''
                            parts = [p.strip() for p in rest.split(';')]
                            if parts:
                                rec['solvents'].extend(_normalize_token_list(parts[0]))
                            handled = True
                            continue
                    if handled:
                        k += 1
                        continue
                    k += 1
                # advance
                i = k
                continue

        i += 1

    # Post-process: dedupe tokens and compute time/temp
    for rid, rec in reactions.items():
        # Dedupe
        rec['reagents'] = list(dict.fromkeys([x.strip() for x in rec['reagents'] if x.strip()]))
        rec['catalysts'] = list(dict.fromkeys([x.strip() for x in rec['catalysts'] if x.strip()]))
        rec['solvents'] = list(dict.fromkeys([x.strip() for x in rec['solvents'] if x.strip()]))

        # Parse time and temperature across all condition lines
        total_h = 0.0
        max_c = -math.inf
        had_rt = False
        for ln in rec.get('all_condition_lines', []):
            # time
            for m in _RE_TIME.finditer(ln):
                num = float(m.group('num'))
                unit = m.group('unit').lower()
                if unit.startswith('min'):
                    total_h += num / 60.0
                elif unit.startswith('d'):
                    total_h += num * 24.0
                else:
                    total_h += num
            if re.search(r"\bovernight\b", ln, re.I):
                total_h += 16.0
            # temperature
            for m in _RE_TEMP_C.finditer(ln):
                val = float(m.group('val'))
                if val > max_c:
                    max_c = val
            if re.search(r"\brt\b|room temperature", ln, re.I):
                had_rt = True
        temperature_c = max_c if max_c != -math.inf else (25.0 if had_rt else None)

        rec['time_h'] = round(total_h, 3) if total_h > 0 else None
        rec['temperature_c'] = round(temperature_c, 1) if temperature_c is not None else None

    return reactions


# --------------------------- Parsing the RXN/RDF ----------------------------

def parse_rdf(path: str) -> Dict[str, Dict[str, Any]]:
    reactions: Dict[str, Dict[str, Any]] = {}
    pending_key = None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [ln.rstrip('\n') for ln in f]

    def _ensure(rid: str) -> Dict[str, Any]:
        return reactions.setdefault(rid, {
            'rct_cas': [],
            'pro_cas': [],
            'rgt_cas': [],
            'cat_cas': [],
            'sol_cas': [],
            # capture CTAB/MOL blocks for SMILES extraction
            'rct_mol': [],
            'pro_mol': [],
            'yield_pct': None,
            'title': None,
            'authors': None,
            'citation': None,
            'notes': [],
        })

    current_rid: str | None = None
    # queue pending RXN mol blocks (reactants/products) until we see the CAS Reaction Number
    pending_rxn_sets: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Capture RXN header + MOL blocks (V2000/V3000). Format:
        # $RXN ... [counts line with two ints] then $MOL blocks for reactants then products.
        if line.strip().startswith('$RXN'):
            i += 1
            # find counts line like "  2  1"
            rct_count = 0
            pro_count = 0
            counts_re = re.compile(r"^\s*(\d+)\s+(\d+)\s*$")
            while i < len(lines):
                if lines[i].strip().startswith('$MOL'):
                    # counts line missing; break to MOL parsing
                    break
                m = counts_re.match(lines[i])
                if m:
                    rct_count, pro_count = int(m.group(1)), int(m.group(2))
                    i += 1
                    break
                i += 1
            total_needed = (rct_count + pro_count) if (rct_count + pro_count) > 0 else None
            mol_blocks: List[str] = []
            # collect $MOL blocks until we have total_needed (if known), else until next $DTYPE/$RXN
            while i < len(lines):
                if lines[i].strip().startswith('$MOL'):
                    j = i + 1
                    block_lines: List[str] = []
                    while j < len(lines):
                        block_lines.append(lines[j])
                        if lines[j].strip() == 'M  END':
                            j += 1
                            break
                        # stop if another record starts unexpectedly
                        if lines[j].startswith('$') and not lines[j].startswith('M '):
                            break
                        j += 1
                    mol_blocks.append('\n'.join(block_lines).rstrip())
                    i = j
                    if total_needed is not None and len(mol_blocks) >= total_needed:
                        break
                    continue
                # stop at next rxn or dtype if no more mols
                if lines[i].strip().startswith('$RXN') or lines[i].strip().startswith('$DTYPE'):
                    break
                i += 1
            # push pending set; will be assigned to the next CAS Reaction Number encountered
            pending_rxn_sets.append({
                'rct_count': rct_count,
                'pro_count': pro_count,
                'mol_blocks': mol_blocks,
            })
            # do not increment i here further; continue loop
            continue
        if line.startswith('$DTYPE'):
            pending_key = line.split(' ', 1)[1].strip()
            # Prepare to read $DATUM
            i += 1
            # Expect $DATUM next, but handle robustness
            if i < len(lines) and lines[i].startswith('$DATUM'):
                # Capture $DATUM content including continuation lines until next '$'
                first = lines[i][len('$DATUM '):]
                datum_lines = [first]
                i += 1
                while i < len(lines) and not lines[i].startswith('$'):
                    datum_lines.append(lines[i])
                    i += 1
                key = pending_key or ''
                # For CTAB/MOL blocks, preserve newlines; for others, join with space
                if key.endswith(':CTAB') or key.endswith(':MOL'):
                    datum = '\n'.join(datum_lines).rstrip()
                else:
                    datum = ' '.join(p.strip() for p in datum_lines).strip()

                # Route datum into the appropriate bucket
                if 'CAS_Reaction_Number' in key:
                    current_rid = datum
                    _ensure(current_rid)
                    # attach earliest pending RXN set if present
                    if pending_rxn_sets:
                        rxnset = pending_rxn_sets.pop(0)
                        blocks: List[str] = rxnset.get('mol_blocks', []) or []
                        rct_n = int(rxnset.get('rct_count') or 0)
                        # if counts missing, split by heuristic: half reactants, rest products
                        if rct_n <= 0 and blocks:
                            rct_n = max(0, min(len(blocks), len(blocks) - 1))
                        _ensure(current_rid)['rct_mol'].extend(blocks[:rct_n])
                        _ensure(current_rid)['pro_mol'].extend(blocks[rct_n:])
                elif ':RCT(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['rct_cas'].append(datum)
                elif ':PRO(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['pro_cas'].append(datum)
                elif ':RGT(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['rgt_cas'].append(datum)
                elif ':CAT(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['cat_cas'].append(datum)
                elif ':SOL(' in key and key.endswith('CAS_RN'):
                    if current_rid:
                        _ensure(current_rid)['sol_cas'].append(datum)
                elif ':RCT(' in key and (key.endswith(':CTAB') or key.endswith(':MOL')):
                    if current_rid:
                        _ensure(current_rid)['rct_mol'].append(datum)
                elif ':PRO(' in key and (key.endswith(':CTAB') or key.endswith(':MOL')):
                    if current_rid:
                        _ensure(current_rid)['pro_mol'].append(datum)
                elif key.endswith(':PRO(1):YIELD'):
                    if current_rid:
                        try:
                            _ensure(current_rid)['yield_pct'] = int(float(datum))
                        except Exception:
                            _ensure(current_rid)['yield_pct'] = None
                elif key.endswith(':REFERENCE(1):TITLE'):
                    if current_rid:
                        _ensure(current_rid)['title'] = datum
                elif key.endswith(':REFERENCE(1):AUTHOR'):
                    if current_rid:
                        _ensure(current_rid)['authors'] = datum
                elif key.endswith(':REFERENCE(1):CITATION'):
                    if current_rid:
                        _ensure(current_rid)['citation'] = datum
                elif key.endswith(':NOTES'):
                    if current_rid:
                        _ensure(current_rid)['notes'].append(datum)
                # do not increment i here; we already moved to next line or stop
                continue
            else:
                # No $DATUM where expected; continue
                continue
        else:
            i += 1

    # Deduplicate lists
    for rid, rec in reactions.items():
        for k in ['rct_cas', 'pro_cas', 'rgt_cas', 'cat_cas', 'sol_cas', 'notes']:
            rec[k] = list(dict.fromkeys(rec.get(k, [])))
        # de-dupe mol blocks while preserving order
        for k in ['rct_mol', 'pro_mol']:
            seen: set[str] = set()
            uniq: List[str] = []
            for mb in rec.get(k, []) or []:
                if mb not in seen:
                    seen.add(mb)
                    uniq.append(mb)
            rec[k] = uniq
    return reactions


# ------------------------------- Row assembly -------------------------------

def infer_reaction_type(core_generic_tokens: List[str]) -> str:
    s = set(t.lower() for t in core_generic_tokens)
    if any(t.startswith('pd') for t in s):
        return 'Buchwald'
    if any(t.startswith('cu') for t in s):
        return 'Ullmann'
    if any(t.startswith('ni') for t in s):
        return 'Ullmann'  # generalized copper/nickel-mediated C–N
    return 'Other'

def load_cas_maps(paths: List[str]) -> Dict[str, Dict[str, str]]:
    """Load one or more CSV mapping files into a dict: CAS -> {Name, GenericCore, Role, CategoryHint, Token}.
    Accepts slightly different headers; missing fields are blank. CAS keys are normalized as plain strings.
    """
    import csv as _csv
    mapping: Dict[str, Dict[str, str]] = {}
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    cas = (row.get('CAS') or '').strip()
                    if not cas:
                        continue
                    entry = mapping.setdefault(cas, {})
                    # Copy known fields if present
                    for k in ['Name', 'GenericCore', 'Role', 'CategoryHint', 'Token']:
                        v = row.get(k)
                        if v:
                            entry[k] = v.strip()
        except Exception:
            # ignore file-specific issues
            pass
    return mapping


def _cas_to_names(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[str]:
    out: List[str] = []
    for cas in cases:
        name = cas_map.get(cas, {}).get('Name')
        out.append(name or cas)
    return out


def _generic_from_cas_list(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[str]:
    out: List[str] = []
    for cas in cases:
        e = cas_map.get(cas) or {}
        gen = (e.get('GenericCore') or '').strip()
        if not gen and (e.get('CategoryHint') or '').lower().startswith('copper'):
            # crude inference
            gen = 'Cu'
        if gen:
            out.append(gen)
    return out


def _tokens_from_cas_list(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[str]:
    """Return normalized short tokens for CAS list using mapping: prefer Token, then Name, else CAS."""
    out: List[str] = []
    for cas in cases:
        e = cas_map.get(cas) or {}
        tok = (e.get('Token') or '').strip()
        if not tok:
            tok = (e.get('Name') or '').strip()
        if not tok:
            tok = cas
        out.append(tok)
    # stable de-dupe while preserving order
    seen = set()
    uniq: List[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def _pairs_from_cas_list(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    pairs: List[Dict[str, str]] = []
    for cas in cases or []:
        e = cas_map.get(cas) or {}
        name = (e.get('Name') or cas).strip()
        pairs.append({'name': name, 'cas': cas})
    return pairs


def _name_variants(nm: str) -> List[str]:
    """Generate normalized, lowercase variants of a chemical name to improve exact-match enrichment.
    Includes common oxidation-state synonyms (cuprous->copper(i), cupric->copper(ii), etc.).
    """
    base = (nm or '').strip().lower()
    if not base:
        return []
    variants: set[str] = set([base])
    rep_map = {
        r"\bcuprous\b": "copper(i)",
        r"\bcupric\b": "copper(ii)",
        r"\bferrous\b": "iron(ii)",
        r"\bferric\b": "iron(iii)",
        r"\bstannous\b": "tin(ii)",
        r"\bstannic\b": "tin(iv)",
        r"\bmercurous\b": "mercury(i)",
        r"\bmercuric\b": "mercury(ii)",
        r"\bplumbous\b": "lead(ii)",
        r"\bplumbic\b": "lead(iv)",
        r"\bchromous\b": "chromium(ii)",
        r"\bchromic\b": "chromium(iii)",
        r"\bnickelous\b": "nickel(ii)",
        r"\bnickelic\b": "nickel(iii)",
    }
    norm = base
    for pat, repl in rep_map.items():
        norm = re.sub(pat, repl, norm)
    variants.add(norm)
    # Also include a version with multiple spaces normalized and hyphens collapsed
    variants.add(re.sub(r"\s+", " ", norm))
    variants.add(norm.replace('-', ' '))
    return list(variants)


def _build_name_to_cas_index(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """Build a lowercase name -> CAS map for the provided CAS list using the mapping names.
    Skip ambiguous names that point to multiple CAS in this role.
    """
    name_to_cas: Dict[str, str] = {}
    ambiguous: set[str] = set()
    for cas in cases or []:
        e = cas_map.get(cas) or {}
        candidates: List[str] = []
        nm = (e.get('Name') or '').strip()
        tok = (e.get('Token') or '').strip()
        if nm:
            candidates.extend(_name_variants(nm))
        if tok:
            candidates.extend(_name_variants(tok))
        for key in candidates:
            if not key:
                continue
            if key in ambiguous:
                continue
            if key in name_to_cas and name_to_cas[key] != cas:
                ambiguous.add(key)
                name_to_cas.pop(key, None)
            else:
                name_to_cas[key] = cas
    return name_to_cas


def _build_global_name_to_cas_index(cas_map: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """Build a lowercase name -> CAS map from the entire mapping (Name and Token), skipping ambiguous names."""
    name_to_cas: Dict[str, str] = {}
    ambiguous: set[str] = set()
    for cas, e in (cas_map or {}).items():
        candidates: List[str] = []
        nm = (e.get('Name') or '').strip()
        tok = (e.get('Token') or '').strip()
        if nm:
            candidates.extend(_name_variants(nm))
        if tok:
            candidates.extend(_name_variants(tok))
        for key in candidates:
            if not key:
                continue
            if key in ambiguous:
                continue
            if key in name_to_cas and name_to_cas[key] != cas:
                ambiguous.add(key)
                name_to_cas.pop(key, None)
            else:
                name_to_cas[key] = cas
    return name_to_cas


def _pair_strings_from_cas_and_names(cases: List[str], cas_map: Dict[str, Dict[str, str]], extra_names: List[str], name_hints: Optional[Dict[str, str]] = None) -> List[str]:
    """Combine CAS-derived pairs and extra TXT names into a de-duplicated list of "name|cas" strings.
    Heuristics:
    - Treat TXT tokens that look like CAS numbers as CAS, not names.
    - If mapping lacks a Name for a CAS and TXT provides exactly one non-CAS name with exactly one CAS, pair them.
    - If counts of non-CAS TXT names equals counts of CAS, pair by order.
    - Remaining non-CAS TXT names are emitted as name-only entries (name| ).
    """
    def is_cas_like(s: str) -> bool:
        s = (s or '').strip()
        if not re.fullmatch(r"\d{2,7}-\d{2}-\d", s):
            return False
        # Optional: verify checksum to reduce false positives
        try:
            digits = s.replace('-', '')
            check = int(digits[-1])
            body = list(map(int, digits[:-1]))
            # weights from rightmost body digit: 1,2,3,... per CAS spec
            total = 0
            w = 1
            for d in reversed(body):
                total += d * w
                w += 1
            return total % 10 == check
        except Exception:
            return True  # if any issue, still treat as CAS-like

    out: List[str] = []
    seen: set[str] = set()

    cas_list = cases or []
    txt_names = extra_names or []
    txt_noncas = [n for n in txt_names if not is_cas_like(n)]
    txt_cas = [n for n in txt_names if is_cas_like(n)]

    # Prepare assignments for CAS -> name (from mapping or TXT pairing)
    assigned_names: Dict[str, str] = {}
    # If TXT includes explicit CAS tokens, align by the order they appear to pair with following names when possible
    if txt_cas and txt_noncas:
        # simple heuristic: zip the CAS tokens with the first N non-CAS names
        for cas, nm in zip(txt_cas, txt_noncas):
            assigned_names[cas] = nm
    # Else, pair by count equality or single-single case
    elif len(txt_noncas) == len(cas_list) and len(cas_list) > 0:
        for cas, nm in zip(cas_list, txt_noncas):
            assigned_names[cas] = nm
    elif len(cas_list) == 1 and len(txt_noncas) == 1:
        assigned_names[cas_list[0]] = txt_noncas[0]
    # Else: we keep mapping names or cas fallback

    used_noncas: set[str] = set()
    # Emit CAS-derived entries, overlaying assigned TXT names when present
    for cas in cas_list:
        e = cas_map.get(cas) or {}
        mapped_name = (e.get('Name') or e.get('Token') or '').strip()
        # Prefer mapped name when available; fall back to TXT-assigned name
        nm = (mapped_name or assigned_names.get(cas) or '').strip()
        if nm:
            used_noncas.add(nm)
        else:
            # still no name from mapping nor pairing; leave as CAS itself to avoid empty name
            nm = cas
        s = _pair_str(nm, cas)
        if s not in seen:
            seen.add(s)
            out.append(s)

    # Emit remaining TXT names that are not CAS-like and not already used in assignments
    for nm in txt_noncas:
        if nm in used_noncas:
            continue
        # Try to enrich with CAS if we have an exact, unambiguous hint for this role
        cas_hint = None
        if name_hints is not None:
            cas_hint = name_hints.get(nm.lower())
        s = _pair_str(nm, cas_hint or '')
        if s not in seen:
            seen.add(s)
            out.append(s)

    # Do not emit TXT CAS-like tokens separately; they are already represented via CAS entries
    return out


def _roles_from_cas_list(cases: List[str], cas_map: Dict[str, Dict[str, str]]) -> List[str]:
    roles: List[str] = []
    for cas in cases:
        role = (cas_map.get(cas, {}).get('Role') or '').strip().upper()
        roles.append(role if role else 'UNK')
    return roles


def _split_cat_vs_lig_from_cas(cat_cas: List[str], cas_map: Dict[str, Dict[str, str]]) -> Tuple[List[str], List[str], List[str]]:
    """Split catalyst CAS list into (core_catalyst_cas, ligand_cas, other_cas) using Role/Category/GenericCore hints."""
    core: List[str] = []
    lig: List[str] = []
    other: List[str] = []
    for cas in cat_cas or []:
        e = cas_map.get(cas) or {}
        role = (e.get('Role') or '').strip().upper()
        hint = (e.get('CategoryHint') or '').strip().lower()
        gen = (e.get('GenericCore') or '').strip()
        name = (e.get('Name') or '').strip().lower()
        if role.startswith('LIG') or 'ligand' in hint:
            lig.append(cas)
        elif role.startswith('CAT') or gen or any(m in name for m in ['palladium', 'copper', 'nickel', 'iridium', 'rhodium']):
            core.append(cas)
        else:
            other.append(cas)
    return core, lig, other


def _molblock_to_smiles(mb: str) -> str:
    """Convert a V2000/V3000 mol block to a canonical SMILES using RDKit if available."""
    if not Chem:
        return ''
    mol = None
    try:
        mol = Chem.MolFromMolBlock(mb, sanitize=True, removeHs=True)
    except Exception:
        mol = None
    if mol is None:
        try:
            mol = Chem.MolFromMolBlock(mb, sanitize=False, removeHs=True)
            if mol is not None:
                try:
                    Chem.SanitizeMol(mol)
                except Exception:
                    pass
        except Exception:
            mol = None
    if mol is None:
        return ''
    try:
        return Chem.MolToSmiles(mol, isomericSmiles=True)
    except Exception:
        return ''


def assemble_rows(txt: Dict[str, Dict[str, Any]], rdf: Dict[str, Dict[str, Any]], cas_map: Optional[Dict[str, Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    ids = sorted(set(txt.keys()) | set(rdf.keys()))
    rows: List[Dict[str, Any]] = []
    for rid in ids:
        t = txt.get(rid, {})
        r = rdf.get(rid, {})

        # Catalysts split into core vs ligand, also gather generic tags
        core_detail: List[str] = []
        ligands: List[str] = []
        core_generic: List[str] = []

        # Prefer CAS-role-based split if mapping available
        cat_core_cas: List[str] = []
        cat_lig_cas: List[str] = []
        if cas_map and r.get('cat_cas'):
            cat_core_cas, cat_lig_cas, cat_other_cas = _split_cat_vs_lig_from_cas(r.get('cat_cas', []), cas_map)
            # Any unclassified catalyst CAS default to core
            if cat_other_cas:
                cat_core_cas = list(dict.fromkeys(list(cat_core_cas) + list(cat_other_cas)))
            # Names/tokens from CAS for ligands
            ligands.extend(_tokens_from_cas_list(cat_lig_cas, cas_map))
            # Core generic metal tags from catalyst CAS
            core_generic.extend(_generic_from_cas_list(cat_core_cas, cas_map))

        # Also include TXT catalysts; classify into core vs ligand and extract generic tags
        txt_cats = list(t.get('catalysts', []))
        # First pass: inspect for any metal generic tag among TXT catalysts
        txt_classified = [(_classify_catalyst_or_ligand(item), item) for item in txt_cats]
        any_metal_present = any(gen for ((kind, gen), _it) in txt_classified)
        for (kind_gen, item) in txt_classified:
            kind, gen = kind_gen
            # If any metal present in the set, treat non-metal items as ligands
            if any_metal_present and not gen:
                kind = 'ligand'
            if kind == 'core':
                core_detail.append(item)
            else:
                ligands.append(item)
            if gen:
                core_generic.append(gen)

        # If still no core_generic but copper-like catalyst present explicitly, infer
        if not core_generic and any('copper' in c.lower() for c in core_detail):
            core_generic.append('Cu')

        # Reagents and roles (prefer RDF CAS; merge TXT names; roles from map or TXT heuristics)
        txt_reagents: List[str] = list(t.get('reagents', []))
        reagents: List[str]
        roles: List[str] = []
        if r.get('rgt_cas'):
            reagents = _tokens_from_cas_list(r.get('rgt_cas', []), cas_map or {})
            if cas_map:
                roles.extend(_roles_from_cas_list(r.get('rgt_cas', []), cas_map or {}))
            else:
                roles.extend(['UNK'] * len(reagents))
        else:
            reagents = []
        # Merge in TXT reagents (names) and accumulate roles by heuristic
        for name in txt_reagents:
            if name and name not in reagents:
                reagents.append(name)
            role = _classify_reagent_role(name)
            roles.append(role)
        # If we now have any specific role, drop UNK entries
        if any(r != 'UNK' for r in roles):
            roles = [r for r in roles if r != 'UNK']

        # Note: We no longer output a dedicated Base column (user request)

        # Solvents: compute pair strings later
        solvents: List[str] = []

        # Time / Temp / Yield
        temp_c = t.get('temperature_c')
        time_h = t.get('time_h')
        yield_pct = r.get('yield_pct') if r.get('yield_pct') is not None else t.get('txt_yield')

        # Reference priority: TXT-derived title/authors/citation; fallback to RDF
        title = t.get('title') or r.get('title') or ''
        authors = t.get('authors') or r.get('authors') or ''
        citation = t.get('citation') or r.get('citation') or ''
        reference = ' | '.join([x for x in [title, authors, citation] if x])

        # RawCAS trail
        def join_plus(lst):
            return ' + '.join(lst) if lst else ''
        rawcas_parts = []
        if r.get('rct_cas'):
            rawcas_parts.append(f"RCT: {join_plus(r['rct_cas'])}")
        if r.get('pro_cas'):
            rawcas_parts.append(f"PRO: {join_plus(r['pro_cas'])}")
        if r.get('rgt_cas'):
            rawcas_parts.append(f"RGT: {join_plus(r['rgt_cas'])}")
        if r.get('cat_cas'):
            rawcas_parts.append(f"CAT: {join_plus(r['cat_cas'])}")
        if r.get('sol_cas'):
            rawcas_parts.append(f"SOL: {join_plus(r['sol_cas'])}")
        raw_cas = ' | '.join(rawcas_parts)

        # Name arrays from CAS mapping (if provided)
        rct_names = _cas_to_names(r.get('rct_cas', []), cas_map or {})
        pro_names = _cas_to_names(r.get('pro_cas', []), cas_map or {})
        rgt_names = _cas_to_names(r.get('rgt_cas', []), cas_map or {})
        # Avoid ligand leakage into CATName by excluding cas tagged as ligand
        if cas_map and r.get('cat_cas'):
            cat_core_only = [c for c in r.get('cat_cas', []) if c not in (cat_lig_cas or [])]
        else:
            cat_core_only = r.get('cat_cas', [])
        cat_names = _cas_to_names(cat_core_only, cas_map or {})
        sol_names = _cas_to_names(r.get('sol_cas', []), cas_map or {})
        # Keep empty lists empty; do not add placeholders like "none|"

        # SMILES from MOL blocks if RDKit is available
        rct_smiles_list: List[str] = []
        pro_smiles_list: List[str] = []
        for mb in r.get('rct_mol', []) or []:
            smi = _molblock_to_smiles(mb)
            if smi:
                rct_smiles_list.append(smi)
        for mb in r.get('pro_mol', []) or []:
            smi = _molblock_to_smiles(mb)
            if smi:
                pro_smiles_list.append(smi)

        # Compose compound lists as "name|cas" strings
        rgt_name_idx = _build_name_to_cas_index(r.get('rgt_cas', []), cas_map or {}) if cas_map is not None else {}
        sol_name_idx = _build_name_to_cas_index(r.get('sol_cas', []), cas_map or {}) if cas_map is not None else {}
        lig_name_idx = _build_name_to_cas_index(cat_lig_cas or [], cas_map or {}) if cas_map is not None else {}
        # For core matching, prefer catalyst CAS names; then fall back to any reaction CAS to help attach CAS
        # to obvious core names like "Cuprous iodide" or "Cupric acetate" when RDF listed them under other roles.
        all_cat_for_core_idx = (cat_core_cas or []) + (cat_lig_cas or [])
        core_name_idx = _build_name_to_cas_index(all_cat_for_core_idx, cas_map or {}) if cas_map is not None else {}
        # Reaction-wide indices (filtered to catalyst-like entries, then full union as last resort)
    if cas_map is not None:
            all_rxn_cas = (r.get('rct_cas', []) or []) + (r.get('pro_cas', []) or []) + (r.get('rgt_cas', []) or []) + (r.get('cat_cas', []) or []) + (r.get('sol_cas', []) or [])
            # Filter to CAS that look catalyst-like per mapping (Role startswith CAT or has GenericCore)
            catlike_cas = []
            for c in all_rxn_cas:
                e = (cas_map or {}).get(c) or {}
                role = (e.get('Role') or '').strip().upper()
                gen = (e.get('GenericCore') or '').strip()
                if role.startswith('CAT') or gen:
                    catlike_cas.append(c)
            rxn_catlike_idx = _build_name_to_cas_index(catlike_cas, cas_map or {})
            rxn_all_idx = _build_name_to_cas_index(all_rxn_cas, cas_map or {})
            merged_core_hints = dict(core_name_idx)
            merged_core_hints.update(rxn_catlike_idx)
            merged_core_hints.update(rxn_all_idx)
            # Finally, allow a global mapping fallback for well-known names (do not override existing hints)
            global_idx = _build_global_name_to_cas_index(cas_map or {})
            for k, v in global_idx.items():
                if k not in merged_core_hints:
                    merged_core_hints[k] = v
    else:
            merged_core_hints = core_name_idx

            reagent_pairs = _pair_strings_from_cas_and_names(r.get('rgt_cas', []), cas_map or {}, txt_reagents, rgt_name_idx)
            solvent_pairs = _pair_strings_from_cas_and_names(r.get('sol_cas', []), cas_map or {}, t.get('solvents', []) or [], sol_name_idx)
            ligand_pairs = _pair_strings_from_cas_and_names(cat_lig_cas or [], cas_map or {}, ligands, lig_name_idx)
            core_pairs = _pair_strings_from_cas_and_names(cat_core_cas or [], cas_map or {}, core_detail, merged_core_hints)

            # Raw data bundle for traceability
            rawdata_obj = {
            'txt': {
                'title': t.get('title'),
                'authors': t.get('authors'),
                'citation': t.get('citation'),
                'reagents': t.get('reagents'),
                'catalysts': t.get('catalysts'),
                'solvents': t.get('solvents'),
                'base_from_txt': t.get('base_from_txt'),
                'all_condition_lines': t.get('all_condition_lines'),
            },
            'rdf': {
                'rct_cas': r.get('rct_cas'),
                'pro_cas': r.get('pro_cas'),
                'rgt_cas': r.get('rgt_cas'),
                'cat_cas': r.get('cat_cas'),
                'sol_cas': r.get('sol_cas'),
                'notes': r.get('notes'),
            }
            }
            row = {
                'ReactionID': rid,
                'ReactionType': infer_reaction_type(core_generic),
                'CatalystCoreDetail': _json_list(core_pairs),
                'CatalystCoreGeneric': _json_list(core_generic),
                'Ligand': _json_list(ligand_pairs),
                'Reagent': _json_list(reagent_pairs),
                'ReagentRole': _json_list(roles),
                'Solvent': _json_list(solvent_pairs),
                'Temperature_C': temp_c if temp_c is not None else '',
                'Time_h': time_h if time_h is not None else '',
                'Yield_%': yield_pct if yield_pct is not None else '',
                'ReactantSMILES': ' . '.join(rct_smiles_list) if rct_smiles_list else '',
                'ProductSMILES': ' . '.join(pro_smiles_list) if pro_smiles_list else '',
                'Reference': reference,
                'CondKey': '',  # fill after
                'CondSig': '',  # fill after
                'FamSig': '',   # fill after
                'RawCAS': raw_cas,
                'RawData': json.dumps(rawdata_obj, ensure_ascii=False),
                # Optional enrichment (JSON arrays of names; falls back to CAS when unknown)
                'RCTName': _json_list(rct_names),
                'PROName': _json_list(pro_names),
                'RGTName': _json_list(rgt_names),
                'CATName': _json_list(cat_names),
                'SOLName': _json_list(sol_names),
            }

            # Build keys/hashes
            row['CondKey'] = build_condkey(row)
            row['CondSig'] = build_condsig(row)
            row['FamSig'] = build_famsig(row)

            rows.append(row)

    return rows


def write_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    # Ensure consistent column order per schema
    cols = [
        'ReactionID', 'ReactionType', 'CatalystCoreDetail', 'CatalystCoreGeneric', 'Ligand',
        'Reagent', 'ReagentRole', 'Solvent', 'Temperature_C', 'Time_h',
        'Yield_%', 'ReactantSMILES', 'ProductSMILES', 'Reference',
        'CondKey', 'CondSig', 'FamSig', 'RawCAS', 'RawData',
        # enrichment columns (optional)
    'RCTName', 'PROName', 'RGTName', 'CATName', 'SOLName',
    ]
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, '') for k in cols})


def main():
    ap = argparse.ArgumentParser(description="Merge SciFinder TXT + RXN/RDF into schema CSV")
    ap.add_argument('--rdf', required=True, help='Path to Reaction_*.rdf file')
    ap.add_argument('--txt', required=True, help='Path to Reaction_*.txt file')
    ap.add_argument('--out', required=True, help='Output CSV path')
    ap.add_argument('--cas-map', action='append', help='Optional CAS->Name mapping CSV (can be used multiple times)')
    ap.add_argument('--no-auto-cas-maps', action='store_true', help='Disable auto-detection of built-in CAS maps')
    args = ap.parse_args()

    if xxhash is None:
        print("Warning: xxhash not installed; CondSig/FamSig will be blank. Install 'xxhash' for hashes.")

    txt_map = parse_txt(args.txt)
    rdf_map = parse_rdf(args.rdf)

    # Collect mapping files
    cas_map_paths: List[str] = []
    if args.cas_map:
        cas_map_paths.extend(args.cas_map)
    if not args.no_auto_cas_maps:
        # Try auto-known paths if present
        here = os.path.dirname(os.path.abspath(__file__))
        maybe = [
            os.path.join(here, 'Buchwald', 'cas_dictionary.csv'),
            os.path.join(here, 'Ullman', '新建文件夹', 'ullmann_cas_to_name_mapping.csv'),
        ]
        cas_map_paths.extend([p for p in maybe if os.path.exists(p)])
    cas_map = load_cas_maps(cas_map_paths) if cas_map_paths else {}

    rows = assemble_rows(txt_map, rdf_map, cas_map)
    write_csv(rows, args.out)
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == '__main__':
    main()
