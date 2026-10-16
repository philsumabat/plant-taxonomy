# Plant Taxonomy & Botanical Nomenclature Rules

When answering questions involving plant species, botanical nomenclature, floristics, ethnobotany, or plant phylogenetics:

1. **Follow International Code of Nomenclature (ICN) Formatting**:
   - Italicize scientific names at the genus, species, and infraspecific ranks (e.g., *Quercus robur*, *Brassica oleracea* var. *capitata*).
   - Do **not** italicize taxonomic authorities, rank connecting terms (`subsp.`, `var.`, `subvar.`, `f.`, `sect.`, `subg.`), hybrid multiplication signs (`×`), or indeterminate qualifiers (`sp.`, `spp.`, `cf.`, `aff.`). Example: *Quercus robur* L., *Mentha* × *piperita* L.
   - Capitalize higher taxonomic ranks (Family, Order, Class) without italics in standard botanical prose (e.g., Fagaceae, Fabales), while italicizing unranked phylogenetic clades only when following PhyloCode conventions or matching the source database.

2. **Verify Taxonomic Status Across Authoritative Databases**:
   - Use the `plant-taxonomy` skill (`scripts/plant_taxonomy.py`) to verify whether a plant name is currently **ACCEPTED** or a **SYNONYM** rather than relying solely on training memory, as circumscriptions frequently change under APG IV and recent molecular revisions.
   - Cross-reference complementary authorities:
     - **Kew's World Checklist of Vascular Plants (WCVP / POWO)** for vascular plant consensus taxonomy.
     - **World Flora Online (WFO)** for global flora consensus and subgeneric/sectional placement (`wfo-...` IDs).
     - **International Plant Names Index (IPNI)** for nomenclatural protologues, publication dates (`publishedIn`), and LSIDs.
     - **GBIF Backbone Taxonomy** for global biodiversity cross-referencing, vernacular names, and occurrence-linked keys.
     - **NCBI Taxonomy** for APG IV unranked phylogenetic clade lineages (*Mesangiospermae*, *eudicotyledons*, *rosids*, *asterids*, etc.) and molecular sequence links.

3. **Always Report Identifiers and Authorities**:
   - Include the botanical authority string on first mention of a scientific name (e.g., *Arabidopsis thaliana* (L.) Heynh.).
   - When resolving synonyms, explicitly state both the queried synonym (with its authority) and the currently accepted scientific name (with its authority) and source database ID (`GBIF`, `WCVP`, `WFO`, `IPNI`, or `NCBI TaxID`).
