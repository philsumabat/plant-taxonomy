---
name: plant-taxonomy
description: >
  Query authoritative plant taxonomic databases — GBIF Backbone Taxonomy, Kew's
  World Checklist of Vascular Plants (WCVP / POWO), World Flora Online (WFO),
  International Plant Names Index (IPNI), Catalogue of Life (CoL), NCBI
  Taxonomy, and iNaturalist — to resolve plant scientific names, synonyms,
  basionyms, botanical authorities, protologue publications, APG IV clade
  lineages, vernacular names, distributions, and conservation statuses. Use
  whenever the user asks about plant taxonomy, botanical nomenclature, synonym
  resolution, family/order placement, APG IV clades, or standardizing plant
  species lists.
---

# Plant Taxonomic Databases (`plant-taxonomy`)

## Overview

This skill provides unified, zero-API-key access to seven authoritative global botanical and taxonomic databases via a single Python standard-library CLI tool (`scripts/plant_taxonomy.py`):

| Database | Authority / Scope | Key Identifiers & Data Provided |
| :--- | :--- | :--- |
| **Kew WCVP / POWO** | Royal Botanic Gardens, Kew (via GBIF `f382f0ce-323a-4091-bb9f-add557f3a9a2`) | Consensus vascular plant status (`ACCEPTED` vs. `SYNONYM`), authorship, protologue citation |
| **World Flora Online (WFO)** | WFO Plant List (via ChecklistBank `2004`) | `wfo-...` IDs, subgenus/section placement, consensus status |
| **IPNI** | International Plant Names Index (via GBIF `046bbc50-cae2-47ff-aa43-729fbf53f7c5`) | `urn:lsid:ipni.org:names:...`, nomenclatural authorship, original publication (`publishedIn`), basionyms |
| **BHL** | Biodiversity Heritage Library (`biodiversitylibrary.org`) | Digitized literature, volume/page citations, type descriptions, collector field books |
| **GBIF Backbone** | Global Biodiversity Information Facility (`api.gbif.org/v1`) | `usageKey`, fuzzy name matching, synonyms, vernacular names, TDWG/country distributions, child taxa |
| **GBIF Herbaria** | Global Herbarium Preserved Specimens (`api.gbif.org/v1/occurrence`) | Digitized voucher sheets, catalog numbers, collectors, type statuses, specimen photos |
| **Catalogue of Life (CoL)** | ChecklistBank (`3LR`) | Complete Linnaean rank hierarchy (Domain → Kingdom → Subkingdom → Phylum → Class → Order → Family → Genus → Species) |
| **NCBI Taxonomy** | NCBI Entrez (`eutils.ncbi.nlm.nih.gov`) | `ncbi_tax_id`, APG IV unranked phylogenetic clades (*Mesangiospermae*, *eudicotyledons*, *Gunneridae*, *Pentapetalae*, *rosids*, *asterids*, etc.) |
| **iNaturalist Taxa** | iNaturalist (`api.inaturalist.org/v1/taxa`) | IUCN / conservation status, preferred common names, global observation count, Wikipedia URL |

## Quick Recipes

Always invoke the bundled script `scripts/plant_taxonomy.py` (located at `~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py`) using `python3`.

### 1. Resolve a Plant Name, Authority & Taxonomic Status (`resolve`)

Cross-checks a scientific name (including misspelled names or obsolete synonyms) across GBIF Backbone, Kew WCVP/POWO, World Flora Online (WFO), and IPNI:

```bash
python3 ~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py \
  resolve --name "Solanum lycopersicum" --limit 5
```

- Optional `--rank SPECIES|GENUS|FAMILY` narrows matching to a specific taxonomic rank.
- Optional `--output /tmp/plant_resolve.json` writes JSON directly to disk.

### 2. Full Linnaean & APG IV Phylogenetic Clade Hierarchy (`hierarchy`)

Retrieves both traditional Linnaean ranks (GBIF, WFO subgenera/sections, Catalogue of Life) and the full **APG IV phylogenetic clade lineage** from NCBI Taxonomy:

```bash
python3 ~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py \
  hierarchy --name "Quercus robur"
```

### 3. Synonymy, Basionyms & Protologue Citations (`synonyms`)

Fetches all homotypic and heterotypic synonyms for the accepted taxon from GBIF, plus Kew WCVP synonym mappings and IPNI protologue citations (`publishedIn` and `urn:lsid:ipni.org:names:...`):

```bash
python3 ~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py \
  synonyms --name "Lycopersicon esculentum" --limit 20
```

### 4. Vernacular Names, Geographic Distributions, Subtaxa & Conservation (`profile`)

Retrieves multilingual common names, geographic distribution records, child taxa (subspecies, varieties, or species within a genus), and IUCN conservation status:

```bash
python3 ~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py \
  profile --name "Araucaria araucana" --lang eng --limit 15
```

### 5. Batch Taxonomic Standardization (`batch`)

Resolves a list of raw plant names (from CLI arguments or a line-delimited text file) into a standardized table with accepted names, authorities, families, orders, `gbif_usage_key`, and `wfo_id`:

```bash
python3 ~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py \
  batch --names "Quercus robur" "Lycopersicon esculentum" "Poa annua" "Taraxacum officinale" \
  --csv-output /tmp/standardized_plants.csv
```

### 6. Biodiversity Heritage Library Citations & Digitized Volumes (`bhl`)

Queries BHL for historical taxonomic literature citations, author volumes, and direct URLs to digitized pages:

```bash
python3 ~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py \
  bhl --name "Ternstroemia toquian" --limit 15
```

### 7. Digitized Preserved Herbarium Specimens (`specimens`)

Queries global herbaria (Kew, Naturalis, CAS, US, etc.) for preserved specimen vouchers, collector details, type statuses, and specimen sheet photographs:

```bash
python3 ~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py \
  specimens --name "Ternstroemia toquian" --limit 10
```

### 8. Full Multi-Perspective Botanical Dossier (`dossier`)

Synthesizes nomenclatural, phylogenetic, synonymy, biogeographical, BHL literature, and herbarium specimen data in a single multi-perspective query:

```bash
python3 ~/.gemini/config/plugins/plant-taxonomy/skills/plant-taxonomy/scripts/plant_taxonomy.py \
  dossier --name "Ternstroemia toquian"
```

## The Botanical Multi-Agent Squad

The plugin bundles five specialized autonomous agents in `agents/`:

| Subagent | Role | Specialty |
| :--- | :--- | :--- |
| **`curator`** | Botanical Squad Orchestrator | Decomposes complex plant queries, coordinates squad subagents in parallel, and compiles structured monographs. |
| **`taxonomist`** | Botanical Nomenclature Specialist | Resolves binomials, verifies author citations, traces basionyms, and audits homotypic/heterotypic synonymy under ICN rules. |
| **`phylogeneticist`** | Plant Systematist & APG IV Specialist | Traces evolutionary lineages, unranked APG IV/PPG I clades, family reassignment histories, and NCBI TaxIDs. |
| **`floristics`** | Biogeography & Conservation Agent | Analyzes native/introduced ranges, TDWG distributions, regional endemism, IUCN threat statuses, and vernacular names. |
| **`bibliographer`** | Historic Literature & Protologue Specialist | Searches Biodiversity Heritage Library (BHL) records, collector field notes, and digitized taxonomic monographs. |

### Multi-Agent Orchestration Patterns

When conducting a comprehensive species monograph or resolving a complex taxonomic dispute:
1. **Parallel Dispatch**: The `curator` invokes `taxonomist`, `phylogeneticist`, `floristics`, and `bibliographer` concurrently using `invoke_subagent`.
2. **Specialist Verification**: Each subagent queries their respective primary data sources via `plant_taxonomy.py` and returns structured findings.
3. **Consensus Synthesis**: The `curator` reconciles differences (e.g. historical Theaceae vs. modern Pentaphylacaceae placement, basionym publication details) and outputs a comprehensive, publication-grade botanical report.

## Reporting Guidelines

1. **Consensus Comparison**: When databases differ (for example, a split vs. lumped genus), present both the **Kew WCVP / WFO** botanical consensus and the **GBIF Backbone** status clearly.
2. **ICN Formatting**: Italicize genus, species, and infraspecific epithets (*Genus species*), and keep authorities (`L.`, `(Blanco) Fern.-Vill.`) and rank connecting terms (`subsp.`, `var.`, `f.`, `×`) roman (unitalicized).
3. **Database Provenance**: Include persistent identifiers (`wfo-...`, `urn:lsid:ipni.org:names:...`, `GBIF usageKey`, `NCBI TaxID`) in summary tables so the user can trace every taxonomic decision.
