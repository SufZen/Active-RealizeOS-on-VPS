# Shared Registry — Entity & Identity Index

The **source of truth** for WHO exists in the Suf Zen ecosystem.

## Design Principle

Every entity (person, company, venture, brand, platform) gets a unique **ENT-XX** or **PER-XX** ID. These IDs serve as foreign keys across the entire system — referenced in shared-library methods, entity system state maps, and cross-entity protocols.

**Change an entity file here → every system that references it stays current.**

---

## Entity Registry (ENT-XX)

| ID | Name | Type | Status | System Folder |
|----|------|------|--------|---------------|
| ENT-00 | Asaf Eyzenkot (Suf Zen) | person | active | — (shared-core) |
| ENT-01 | Realization | venture-studio | active | Realization-System |
| ENT-02 | Burtucala | venture-studio | active | Burtucala-System |
| ENT-03 | HomeAid | venture | active | HomeAid-System (future) |
| ENT-04 | Arena Habitat | development-project | active | MarvelousCreations-System |
| ENT-05 | Marvelous Creations LDA | spv | active | MarvelousCreations-System |
| ENT-06 | Boa Arc | brand | active | — (operates under Marvelous Creations) |
| ENT-07 | Second Base | platform | active | — (future system) |
| ENT-08 | Sexy.Barcelona | platform | active | — (future system) |

## Person Registry (PER-XX)

| ID | Name | Relationship | Notes |
|----|------|-------------|-------|
| PER-00 | Asaf Eyzenkot | Owner / Founder | See shared-core/ for full identity |
| PER-01 | Meirav Gonen | Partner (personal + professional) | See persons/PER-01-meirav.md |
| PER-02 | Noam Perets | Burtucala Co-Founder | See persons/PER-02-noam-perets.md |
| PER-03 | Roy Hadar | Arena Habitat GP (Finance) | See persons/PER-03-roy-hadar.md |
| PER-04 | Eldad Stinbook | Arena Habitat LP (Investor) | See persons/PER-04-eldad-stinbook.md |

---

## Directory Structure

```
shared-registry/
    _index.md                   ← YOU ARE HERE
    entities/                   ← ENT-XX entity definitions
    persons/                    ← PER-XX person files
    shared-core/                ← Asaf's personal identity layer (universal)
    personal-system/            ← Personal agents (non-brand)
```

## How to Use IDs

- **In agent files:** Reference `ENT-01` when writing Realization-specific logic
- **In state maps:** Map `MTH-XX` methods to `ENT-XX` entities with context parameters
- **In B-brain files:** Link knowledge to its owning entity with `entity: ENT-XX`
- **Cross-system references:** Always use the ID, never hard-code entity names in logic

## Adding a New Entity

1. Assign the next available `ENT-XX` ID
2. Create the entity file in `entities/` using the standard template
3. Update this index table
4. If the entity needs its own system, create `[Name]-System/` folder
5. Follow `MTH-45-entity-lifecycle-protocol` in shared-library

---

> Last updated: 2026-02-09
