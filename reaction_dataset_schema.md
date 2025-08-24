# Reaction Dataset Schema (Single-Table, JSON‑Token Format)

This Markdown document summarises the **final design** for our flat-file reaction
dataset.  Every reaction lives in **one row**, yet the structure still supports
instant condition matching, family grouping, and human‑readable filtering.

---

## Core Idea

* **List‑type fields** (`CoreDetail`, `Ligand`, `ReagentRaw`, `Solvent`, …) are
  stored as **JSON arrays** – no character‑escape problems and trivially parsed
  by Pandas, DuckDB, BigQuery, etc.
* Two pre‑computed 8‑byte hashes give constant‑time look‑ups:
  * **CondSig** – exact‑condition fingerprint.
  * **FamSig**  – family fingerprint (collapses metal precursor & reagent class).
* **CondKey** – a short, human‑readable tag like  
  `Pd/XPhos/K2CO3/Tol` for dashboards, logs, and search boxes.

---

## Column Specification

| Column | Type / example | Purpose |
|--------|----------------|---------|
| `ReactionID` | `"RXN000452"` | Primary key – never reused. |
| `ReactionType` | `"Buchwald"` \| `"Ullmann"` … | High‑level class of coupling. |
| `CoreDetail` | `["Pd(OAc)2","Pd2(dba)3·CHCl3"]` | *Exact* precursor(s), JSON array. |
| `CoreGeneric` | `["Pd","Cu(I)"]` | Generic metal tags, JSON array.<br>Used in CondSig/FamSig. |
| `Ligand` | `["XPhos","L-proline"]` | JSON array; `"none"` if absent. |
| `ReagentRaw` | `["Cs2CO3","Ag2CO3","NEt3"]` | As reported. |
| `ReagentRole` | `["BASE","OX","ADD"]` | Same length; `UNK` if unclear. |
| `Solvent` | `["Tol","EtOH"]` | Primary solvent(s). |
| `Temperature_C` | `110` | Float °C (blank if n/a). |
| `Time_h` | `12` | Float hours. |
| `Yield_%` | `88` | As reported. |
| `ReactantSMILES` | `"... . ..."` | Dot‑concatenated SMILES. |
| `ProductSMILES` | `"... . ..."` | Dot‑concatenated SMILES. |
| `Reference` | `"WO2020‑123456"` | Citation or ELN ID. |
| `CondKey` | `"Pd/XPhos/Cs2CO3/Tol"` | Human‑readable summary token. |
| `CondSig` | `"93A1F2BC"` | xxHash32 of *CoreGeneric∣Ligand∣ReagentRaw∣Solvent*. |
| `FamSig` | `"1F77C8E0"` | Same hash after collapsing precursors & reagent classes. |
| `RawCAS` | `"51364-51-3 + 98327-87-8 + ..."` | Untouched audit trail. |

---

## Building the Keys

```python
import json, xxhash, re

def build_condkey(row):
    cg = "+".join(sorted(json.loads(row["CoreGeneric"]))) or "none"
    lig = "+".join(sorted(json.loads(row["Ligand"]))) or "none"
    bas = "+".join(sorted(json.loads(row["ReagentRaw"]))) or "none"
    solv = "+".join(sorted(json.loads(row["Solvent"]))) or "none"
    return f"{cg}/{lig}/{bas}/{solv}"

def hash32(s): return xxhash.xxh32_hexdigest(s)

def build_condsig(row):
    key = "|".join([ "+".join(sorted(json.loads(row[c]))) 
                     for c in ["CoreGeneric","Ligand","ReagentRaw","Solvent"] ])
    return hash32(key)

def build_famsig(row):
    # Collapse metal detail and reagent subclasses
    core = [re.sub(r"\(.*?\)", "", c) for c in json.loads(row["CoreGeneric"])]
    reag = [r.split("-")[0] for r in json.loads(row["ReagentRaw"])]
    key  = "|".join(["+".join(sorted(core)),
                     "+".join(sorted(json.loads(row["Ligand"]))),
                     "+".join(sorted(reag)),
                     "+".join(sorted(json.loads(row["Solvent"])))])
    return hash32(key)
```

---

## Query Examples

```python
# all Pd + XPhos reactions
mask = df.CoreGeneric.apply(lambda x: "Pd" in json.loads(x)) &        df.Ligand.apply(lambda x: "XPhos" in json.loads(x))
hits = df[mask]

# exact precedent
prec = df[df.CondSig == query_sig]

# same family (ligand + solvent + base identical, Pd precursor can differ)
fam_hits = df[df.FamSig == query_fam_sig]
```

---

## Advantages

1. **Human‑readable**: chemists see real names, not cryptic codes.  
2. **Collision‑proof**: JSON keeps every “+”, “|”, or exotic character intact.  
3. **Fast retrieval**: hashes give O(1) equality; list filters stay vectorised.  
4. **Evolvable**: new tokens just extend the JSON arrays; schemas remain stable.  

---

*End of schema description.*
