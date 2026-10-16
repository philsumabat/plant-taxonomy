<img src="assets/logo.svg" width="88" align="right" alt="Plant Taxonomy Plugin Logo" />

# Plant Taxonomy (`plant-taxonomy`)

An **Antigravity Plugin** that queries nine authoritative global plant taxonomic and biodiversity literature databases—without requiring any API keys—to resolve scientific and vernacular names, trace homotypic and heterotypic synonyms, inspect nomenclatural protologues, retrieve Linnaean and APG IV phylogenetic hierarchies, search digitized historic literature on the Biodiversity Heritage Library (BHL), locate preserved herbarium specimen vouchers, and standardize botanical species lists.

---

## Supported Taxonomic & Literature Databases

| Database | Authority / Publisher | Scope & Identifiers Returned | Data License |
| :--- | :--- | :--- | :--- |
| **Kew WCVP / POWO** | Royal Botanic Gardens, Kew (via GBIF dataset `f382f0ce-323a-4091-bb9f-add557f3a9a2`) | Consensus vascular plant status (`ACCEPTED` vs. `SYNONYM`), authorship, protologue citation | CC BY 4.0 |
| **World Flora Online (WFO)** | WFO Plant List (via ChecklistBank dataset `2004`) | `wfo-...` IDs, subgenus & botanical section placement, cross-database identifiers | CC0 1.0 |
| **IPNI** | International Plant Names Index (via GBIF dataset `046bbc50-cae2-47ff-aa43-729fbf53f7c5`) | `urn:lsid:ipni.org:names:...`, nomenclatural authorship, original protologue (`publishedIn`), basionyms | CC0 / Public |
| **Biodiversity Heritage Library (BHL)** | BHL Consortium (`biodiversitylibrary.org`) | Digitized historic biodiversity literature, direct page links, journal volumes, collector field notes, plates | CC BY 4.0 / Public Domain |
| **GBIF Backbone Taxonomy** | Global Biodiversity Information Facility (`api.gbif.org/v1`) | `usageKey`, fuzzy/exact name matching, synonyms, multilingual vernacular names, TDWG/country distributions, child taxa | CC0 / CC BY 4.0 |
| **GBIF Herbaria** | Global Preserved Herbarium Specimens (`api.gbif.org/v1/occurrence`) | Digitized herbarium sheets, catalog numbers, collectors, collection dates, type statuses, high-res photos | CC0 / CC BY 4.0 |
| **Catalogue of Life (CoL)** | ChecklistBank (`3LR`) | Complete Linnaean rank hierarchy (Domain → Kingdom → Subkingdom → Phylum → Class → Order → Family → Genus → Species) | CC BY 4.0 |
| **NCBI Taxonomy** | NCBI Entrez (`eutils.ncbi.nlm.nih.gov`) | `ncbi_tax_id`, APG IV unranked phylogenetic clades (*Mesangiospermae*, *eudicotyledons*, *Gunneridae*, *Pentapetalae*, *rosids*, *asterids*, etc.) | Public Domain |
| **iNaturalist Taxa** | iNaturalist (`api.inaturalist.org/v1/taxa`) | IUCN Red List / conservation status, preferred common names, global observation count, Wikipedia URL | CC BY-NC / Public API |

---

## Installation

Clone this repository into your global Antigravity plugins directory (`~/.gemini/config/plugins/plant-taxonomy`) and restart Antigravity:

```bash
git clone https://github.com/philsumabat/plant-taxonomy.git ~/.gemini/config/plugins/plant-taxonomy
```

---

## Repository Structure

```text
plant-taxonomy/
├── plugin.json                                     # Antigravity plugin manifest
├── README.md                                       # Documentation & CLI reference
├── LICENSE                                         # MIT License
├── .gitignore                                      # Standard Python/macOS ignore rules
├── assets/
│   └── logo.svg                                    # Minimal Google Material Symbols badge
├── agents/                                         # Autonomous specialized botanical agents
│   ├── curator.md                                  # Herbarium & Squad Orchestrator
│   ├── taxonomist.md                               # Botanical Nomenclature & ICN Specialist
│   ├── phylogeneticist.md                          # Plant Systematist & APG IV Clade Specialist
│   ├── floristics.md                               # Biogeography, Endemism & Conservation Agent
│   └── bibliographer.md                            # Historic Literature & BHL Specialist
├── rules/
│   └── AGENTS.md                                   # ICN botanical nomenclature & citation rules
└── skills/
    └── plant-taxonomy/
        ├── SKILL.md                                # Agent skill instructions & recipes
        └── scripts/
            └── plant_taxonomy.py                   # Zero-dependency Python 3 stdlib CLI
```

---

## The Botanical Multi-Agent Squad

The plugin provides a team of autonomous botanical agents designed to work collaboratively:

- **`curator` (Lead Orchestrator)**: Deconstructs complex floristic inquiries, dispatches research tasks to the specialist squad in parallel, reconciles taxonomic circumscriptions, and compiles comprehensive monographs.
- **`taxonomist` (Nomenclature Specialist)**: Validates scientific binomials, verifies author citations, traces basionyms, audits homotypic/heterotypic synonyms, and cross-checks protologues across Kew WCVP, WFO, IPNI, and GBIF.
- **`phylogeneticist` (Systematist)**: Traces unranked APG IV / PPG I phylogenetic lineages (*Angiosperms* → *eudicots* → *asterids*), explains family transfers (e.g. *Theaceae* to *Pentaphylacaceae*), and links NCBI TaxIDs.
- **`floristics` (Biogeography Agent)**: Analyzes TDWG geographic distributions, native vs. introduced statuses, island endemism, IUCN Red List threat ratings, and iNaturalist community occurrences.
- **`bibliographer` (Literature Historian)**: Searches Biodiversity Heritage Library (BHL) archives for historic protologues, volume/page citations, type descriptions, and collector field books.

---

## CLI Usage (`plant_taxonomy.py`)

`scripts/plant_taxonomy.py` uses only the Python 3 standard library (`urllib`, `xml.etree.ElementTree`, `json`, `csv`, `argparse`) and enforces automatic polite rate-limiting, SSL fallbacks, and retry backoff.

### 1. Resolve a Plant Name (`resolve`)

Cross-checks a scientific or vernacular name across GBIF Backbone, Kew WCVP/POWO, World Flora Online (WFO), and IPNI:

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  resolve --name "Solanum lycopersicum" --limit 5
```

### 2. Full Linnaean & APG IV Clade Hierarchy (`hierarchy`)

Retrieves Linnaean ranks (GBIF, WFO subgenera/sections, Catalogue of Life) alongside the full **APG IV phylogenetic clade lineage** from NCBI Taxonomy:

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  hierarchy --name "Quercus robur"
```

### 3. Synonyms, Basionyms & Protologues (`synonyms`)

Fetches homotypic and heterotypic synonyms from GBIF, Kew WCVP synonym mappings, and IPNI protologue citations (`publishedIn` and `urn:lsid:ipni.org:names:...`):

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  synonyms --name "Lycopersicon esculentum" --limit 20
```

### 4. Vernacular Names, Distributions & Conservation (`profile`)

Retrieves multilingual common names, geographic distribution records, child taxa (subspecies, varieties, or species within a genus), and IUCN conservation status:

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  profile --name "Araucaria araucana" --lang eng --limit 15
```

### 5. Batch Taxonomic Standardization (`batch`)

Standardizes a list of raw plant names (via `--names` or `--input-file`) into accepted names, authorities, families, orders, `gbif_usage_key`, and `wfo_id`, optionally exporting a CSV table:

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  batch --names "Quercus robur" "Lycopersicon esculentum" "Poa annua" "Taraxacum officinale" \
  --csv-output standardized_plants.csv
```

### 6. Biodiversity Heritage Library Literature (`bhl`)

Queries the Biodiversity Heritage Library for historical taxonomic literature citations, monographs, collector field books, and direct URLs to high-resolution digitized page scans:

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  bhl --name "Ternstroemia toquian" --limit 15
```

Filter by historical author or publication year:

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  bhl --name "Ternstroemia toquian" --author "Merrill" --limit 10
```

### 7. Digitized Preserved Herbarium Specimens (`specimens`)

Queries global herbaria (Kew, Naturalis Leiden, Smithsonian US, California Academy of Sciences CAS, etc.) for preserved specimen vouchers, collector names, collection dates, type statuses, and specimen sheet photographs:

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  specimens --name "Ternstroemia toquian" --limit 10
```

### 8. Full Botanical Dossier (`dossier`)

Synthesizes all nomenclatural, phylogenetic, synonymy, biogeographical, BHL historic literature, and herbarium specimen data in a single multi-perspective query:

```bash
python3 skills/plant-taxonomy/scripts/plant_taxonomy.py \
  dossier --name "Ternstroemia toquian"
```

---

## Example Prompts in Antigravity

- *"Assemble the botanical squad to compile a complete dossier on Ternstroemia toquian"*
- *"Search Biodiversity Heritage Library (BHL) literature citations and historic protologues for Ternstroemia toquian"*
- *"Find preserved herbarium type specimens and collection records for Ternstroemia toquian"*
- *"Resolve the taxonomic status, basionym, and accepted name for Solanum lycopersicum"*
- *"Compare the APG IV clade lineage and WFO/WCVP classification of Quercus robur"*
- *"Standardize a list of plant species names and flag any synonyms or spelling variants"*

---

## License

Code in this repository is released under the [MIT License](LICENSE). Underlying taxonomic data are subject to the open licenses of their respective providers (Kew WCVP, WFO, IPNI, GBIF, Catalogue of Life, NCBI, and iNaturalist).
