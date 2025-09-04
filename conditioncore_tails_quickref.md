# ConditionCore & Tails — Quick Reference

**ConditionCore** = minimal catalytic/activator system (e.g., `Pd/XPhos`, `Ni/dtbbpy`, `Cu/phen`, `HATU/DMAP`).  
**Tails** = operational settings around the core: base, solvent(s), temperature, time, concentration, atmosphere, additives, and order of addition.

What are ConditionCore and Tails?

ConditionCore = the minimal catalytic system that largely dictates the reaction mechanism and substrate scope.

Usually: Metal/ligand (e.g., Pd/XPhos, Ni/dtbbpy, Cu/phen)

Sometimes: Single catalyst (Ru(bpy)3, Ir[dF(CF3)ppy]2(dtbbpy)), or Activator system for non-metal cases (HATU/DMAP, TEMPO/NaNO2)

Purpose: compact classification, retrieval, and diversification (“try another core family”)

Tails = the operational recipe that surrounds the core.

Includes: base, solvent(s)/cosolvent, temperature, time, concentration, atmosphere, light (if any), additives, and order of addition

Purpose: tune kinetics/solubility/selectivity while staying within the same core

## Minimal schema

```json
{
  "ConditionCore": "Pd/XPhos",
  "Tails": {
    "base": "K3PO4",
    "solvent": ["toluene"],
    "cosolvent_vv": "10–20% DMA (optional)",
    "temperature_C": [100, 110],
    "time_h": [6, 12],
    "concentration_M": [0.3, 0.6],
    "atmosphere": "N2",
    "additives": [],
    "order_of_addition": [
      "catalyst",
      "ligand",
      "base",
      "solvent",
      "aryl halide",
      "nucleophile"
    ]
  }
}
```

## Tiny examples

| Reaction                       | ConditionCore | Typical Tails (very short)     |
| ------------------------------ | ------------- | ------------------------------ |
| Buchwald C–N (Ar–Br + aniline) | Pd/SPhos      | Cs2CO3; 1,4-dioxane; 90–100 °C |
| Ni amination (aliphatic amine) | Ni/dtbbpy     | NaOtBu; dioxane/DMA; 70–90 °C  |
| Ullmann N-arylation            | Cu/phen       | K2CO3; DMSO/DMA; 100–120 °C    |
| Suzuki–Miyaura                 | Pd/XPhos      | K3PO4; dioxane/H2O; 60–100 °C  |
| Amide coupling                 | HATU/DMAP     | DIPEA; DMF/DMA/MeCN; 0–25 °C   |

## Usage

1. Pick or retrieve **ConditionCore** candidates.
2. Compose **Tails** (base/solvent/temp/time/conc).
3. If weak support, propose a **2×3 mini‑screen** (base × temp).
