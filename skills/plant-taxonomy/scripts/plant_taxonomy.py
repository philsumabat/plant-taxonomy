#!/usr/bin/env python3
"""Unified CLI for querying global plant taxonomic databases.

Supported databases (no API keys required):
- GBIF Backbone Taxonomy (https://api.gbif.org/v1)
- Kew World Checklist of Vascular Plants / POWO (GBIF dataset f382f0ce-323a-4091-bb9f-add557f3a9a2)
- International Plant Names Index / IPNI (GBIF dataset 046bbc50-cae2-47ff-aa43-729fbf53f7c5)
- World Flora Online / WFO Plant List (ChecklistBank dataset 2004)
- Catalogue of Life / CoL (ChecklistBank dataset 3LR)
- NCBI Entrez Taxonomy (https://eutils.ncbi.nlm.nih.gov/entrez/eutils)
- iNaturalist Taxa API (https://api.inaturalist.org/v1/taxa)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

GBIF_BASE = "https://api.gbif.org/v1"
CLB_BASE = "https://api.checklistbank.org"
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
INAT_BASE = "https://api.inaturalist.org/v1"

DATASET_WCVP = "f382f0ce-323a-4091-bb9f-add557f3a9a2"
DATASET_IPNI = "046bbc50-cae2-47ff-aa43-729fbf53f7c5"
CLB_WFO_KEY = "2004"
CLB_COL_KEY = "3LR"

USER_AGENT = "Antigravity-PlantTaxonomy-Plugin/1.0 (https://gbif.org; botanical-research)"
_LAST_REQUEST_TIME = 0.0
MIN_INTERVAL_SEC = 0.22  # Max ~4.5 req/sec polite rate limit


def _rate_limit() -> None:
    global _LAST_REQUEST_TIME
    elapsed = time.monotonic() - _LAST_REQUEST_TIME
    if elapsed < MIN_INTERVAL_SEC:
        time.sleep(MIN_INTERVAL_SEC - elapsed)
    _LAST_REQUEST_TIME = time.monotonic()


import ssl

def _safe_urlopen(req: urllib.request.Request, timeout: int = 15):
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc):
            ctx = ssl._create_unverified_context()
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        raise


def fetch_json(url: str, params: dict[str, Any] | None = None, retries: int = 3) -> dict[str, Any]:
    if params:
        clean_params = {k: v for k, v in params.items() if v is not None}
        query_str = urllib.parse.urlencode(clean_params, doseq=True)
        url = f"{url}?{query_str}"

    for attempt in range(retries):
        _rate_limit()
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with _safe_urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(1.0 * (2**attempt))
                continue
            return {"error": f"HTTP {exc.code}: {exc.reason}", "url": url}
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(0.8 * (2**attempt))
                continue
            return {"error": str(exc), "url": url}
    return {"error": "Max retries exceeded", "url": url}


def fetch_text(url: str, params: dict[str, Any] | None = None) -> str:
    if params:
        clean_params = {k: v for k, v in params.items() if v is not None}
        url = f"{url}?{urllib.parse.urlencode(clean_params, doseq=True)}"
    _rate_limit()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with _safe_urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return ""


def query_gbif_match(name: str, rank: str | None = None, strict: bool = False) -> dict[str, Any]:
    params: dict[str, Any] = {
        "name": name,
        "kingdom": "Plantae",
        "verbose": "true",
    }
    if rank:
        params["rank"] = rank.upper()
    if strict:
        params["strict"] = "true"
    data = fetch_json(f"{GBIF_BASE}/species/match", params)
    if "error" in data or data.get("matchType") == "NONE":
        return {"matched": False, "raw": data}

    usage_key = data.get("usageKey")
    accepted_key = data.get("acceptedUsageKey")
    result: dict[str, Any] = {
        "matched": True,
        "usage_key": usage_key,
        "scientific_name": data.get("scientificName"),
        "canonical_name": data.get("canonicalName"),
        "rank": data.get("rank"),
        "status": data.get("status"),
        "confidence": data.get("confidence"),
        "match_type": data.get("matchType"),
        "accepted_usage_key": accepted_key,
        "classification": {
            "kingdom": data.get("kingdom"),
            "phylum": data.get("phylum"),
            "class": data.get("class"),
            "order": data.get("order"),
            "family": data.get("family"),
            "genus": data.get("genus"),
            "species": data.get("species"),
        },
    }
    if accepted_key and accepted_key != usage_key:
        acc = fetch_json(f"{GBIF_BASE}/species/{accepted_key}")
        result["accepted_scientific_name"] = acc.get("scientificName")
        result["accepted_canonical_name"] = acc.get("canonicalName")
    return result


def query_gbif_dataset(
    name: str,
    dataset_key: str,
    limit: int = 5,
    exact_canonical: bool = True,
    preferred_nub_keys: set[int] | None = None,
) -> list[dict[str, Any]]:
    data = fetch_json(
        f"{GBIF_BASE}/species/search",
        {"q": name, "datasetKey": dataset_key, "limit": max(limit * 4, 20)},
    )
    results = data.get("results", [])
    candidates: list[dict[str, Any]] = []
    target_lower = name.strip().lower()
    for item in results:
        canon = (item.get("canonicalName") or "").strip().lower()
        sci = (item.get("scientificName") or "").strip().lower()
        if exact_canonical and canon and canon != target_lower and not sci.startswith(target_lower):
            continue
        candidates.append(
            {
                "key": item.get("key"),
                "taxon_id": item.get("taxonID"),
                "scientific_name": item.get("scientificName"),
                "canonical_name": item.get("canonicalName"),
                "authorship": item.get("authorship"),
                "rank": item.get("rank"),
                "taxonomic_status": item.get("taxonomicStatus"),
                "accepted_name": item.get("accepted"),
                "basionym": item.get("basionym"),
                "published_in": item.get("publishedIn"),
                "family": item.get("family"),
                "genus": item.get("genus"),
                "nub_key": item.get("nubKey"),
            }
        )

    def _sort_key(rec: dict[str, Any]) -> tuple[int, int, int]:
        canon_l = (rec.get("canonical_name") or "").strip().lower()
        is_exact = 0 if canon_l == target_lower else 1
        nub_match = 0 if (preferred_nub_keys and rec.get("nub_key") in preferred_nub_keys) else 1
        is_accepted = 0 if rec.get("taxonomic_status") == "ACCEPTED" else 1
        return (is_exact, nub_match, is_accepted)

    candidates.sort(key=_sort_key)
    return candidates[:limit]


def query_checklistbank(name: str, dataset_key: str = CLB_WFO_KEY, limit: int = 3) -> list[dict[str, Any]]:
    data = fetch_json(
        f"{CLB_BASE}/dataset/{dataset_key}/nameusage/search",
        {"q": name, "limit": max(limit * 3, 10)},
    )
    items = data.get("result", [])
    records: list[dict[str, Any]] = []
    target_lower = name.strip().lower()
    for item in items:
        usage = item.get("usage", {})
        name_obj = usage.get("name", {})
        sci_name = name_obj.get("scientificName") or (
            item.get("classification", [{}])[-1].get("name") if item.get("classification") else ""
        )
        authorship = name_obj.get("authorship")
        status = usage.get("status")
        rank = name_obj.get("rank") or (
            item.get("classification", [{}])[-1].get("rank") if item.get("classification") else None
        )
        if sci_name and target_lower not in sci_name.lower() and len(records) >= 1:
            continue

        lineage = [
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "rank": node.get("rank"),
            }
            for node in item.get("classification", [])
        ]
        accepted_obj = usage.get("accepted", {})
        accepted_label = accepted_obj.get("label") if isinstance(accepted_obj, dict) else None
        records.append(
            {
                "id": item.get("id") or usage.get("id"),
                "scientific_name": sci_name,
                "authorship": authorship,
                "label": usage.get("label") or (f"{sci_name} {authorship}".strip() if authorship else sci_name),
                "rank": rank,
                "status": status,
                "accepted": accepted_label,
                "published_in": name_obj.get("publishedIn"),
                "identifiers": name_obj.get("identifier", []),
                "classification": lineage,
            }
        )

    def _clb_sort_key(rec: dict[str, Any]) -> tuple[int, int]:
        sci_l = (rec.get("scientific_name") or "").strip().lower()
        is_exact = 0 if sci_l == target_lower else 1
        is_accepted = 0 if rec.get("status") == "accepted" else 1
        return (is_exact, is_accepted)

    records.sort(key=_clb_sort_key)
    return records[:limit]


def query_ncbi_taxonomy(name: str) -> dict[str, Any]:
    search = fetch_json(
        f"{NCBI_BASE}/esearch.fcgi",
        {
            "db": "taxonomy",
            "term": f"{name}[All Names] AND Viridiplantae[Organism]",
            "retmode": "json",
        },
    )
    id_list = search.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        search = fetch_json(
            f"{NCBI_BASE}/esearch.fcgi",
            {"db": "taxonomy", "term": f"{name}[All Names]", "retmode": "json"},
        )
        id_list = search.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return {"matched": False}

    tax_id = id_list[0]
    xml_text = fetch_text(
        f"{NCBI_BASE}/efetch.fcgi",
        {"db": "taxonomy", "id": tax_id, "retmode": "xml"},
    )
    if not xml_text:
        return {"matched": True, "ncbi_tax_id": tax_id}

    try:
        root = ET.fromstring(xml_text)
        taxon = root.find("Taxon")
        if taxon is None:
            return {"matched": True, "ncbi_tax_id": tax_id}

        sci_name = taxon.findtext("ScientificName")
        rank = taxon.findtext("Rank")
        division = taxon.findtext("Division")

        lineage_ex: list[dict[str, str]] = []
        for node in taxon.findall("./LineageEx/Taxon"):
            lineage_ex.append(
                {
                    "tax_id": node.findtext("TaxId") or "",
                    "name": node.findtext("ScientificName") or "",
                    "rank": node.findtext("Rank") or "clade",
                }
            )

        other_names: list[dict[str, str]] = []
        for oname in taxon.findall("./OtherNames/Name"):
            cde = oname.findtext("ClassCDE") or ""
            disp = oname.findtext("DispName") or ""
            if disp:
                other_names.append({"type": cde, "name": disp})

        return {
            "matched": True,
            "ncbi_tax_id": tax_id,
            "scientific_name": sci_name,
            "rank": rank,
            "division": division,
            "phylogenetic_lineage": lineage_ex,
            "other_names_and_authorities": other_names,
        }
    except ET.ParseError:
        return {"matched": True, "ncbi_tax_id": tax_id}


def cmd_resolve(args: argparse.Namespace) -> dict[str, Any]:
    name = args.name.strip()
    gbif = query_gbif_match(name, rank=args.rank)
    lookup_name = gbif.get("canonical_name") or name
    nub_keys = {k for k in (gbif.get("usage_key"), gbif.get("accepted_usage_key")) if isinstance(k, int)}

    wcvp = query_gbif_dataset(
        lookup_name,
        DATASET_WCVP,
        limit=args.limit,
        exact_canonical=False,
        preferred_nub_keys=nub_keys,
    )
    ipni = query_gbif_dataset(
        lookup_name,
        DATASET_IPNI,
        limit=args.limit,
        exact_canonical=False,
        preferred_nub_keys=nub_keys,
    )
    wfo = query_checklistbank(lookup_name, dataset_key=CLB_WFO_KEY, limit=args.limit)

    return {
        "query": name,
        "gbif_backbone": gbif,
        "kew_wcvp_powo": wcvp,
        "world_flora_online": wfo,
        "ipni_nomenclature": ipni,
    }


def cmd_hierarchy(args: argparse.Namespace) -> dict[str, Any]:
    name = args.name.strip()
    gbif = query_gbif_match(name)
    lookup_name = gbif.get("canonical_name") or name
    wfo = query_checklistbank(lookup_name, dataset_key=CLB_WFO_KEY, limit=1)
    col = query_checklistbank(lookup_name, dataset_key=CLB_COL_KEY, limit=1)
    ncbi = query_ncbi_taxonomy(lookup_name)

    return {
        "query": name,
        "canonical_name": lookup_name,
        "gbif_linnaean_ranks": gbif.get("classification", {}),
        "wfo_classification": wfo[0].get("classification", []) if wfo else [],
        "catalogue_of_life_classification": col[0].get("classification", []) if col else [],
        "ncbi_apg_phylogenetic_lineage": ncbi,
    }


def cmd_synonyms(args: argparse.Namespace) -> dict[str, Any]:
    name = args.name.strip()
    gbif = query_gbif_match(name)
    usage_key = gbif.get("accepted_usage_key") or gbif.get("usage_key")
    nub_keys = {k for k in (gbif.get("usage_key"), gbif.get("accepted_usage_key")) if isinstance(k, int)}
    gbif_synonyms: list[dict[str, Any]] = []
    if usage_key:
        syn_resp = fetch_json(
            f"{GBIF_BASE}/species/{usage_key}/synonyms",
            {"limit": args.limit},
        )
        for s in syn_resp.get("results", []):
            gbif_synonyms.append(
                {
                    "key": s.get("key"),
                    "scientific_name": s.get("scientificName"),
                    "canonical_name": s.get("canonicalName"),
                    "authorship": s.get("authorship"),
                    "taxonomic_status": s.get("taxonomicStatus"),
                    "rank": s.get("rank"),
                    "published_in": s.get("publishedIn"),
                }
            )

    wcvp_records = query_gbif_dataset(
        name,
        DATASET_WCVP,
        limit=args.limit,
        exact_canonical=False,
        preferred_nub_keys=nub_keys,
    )
    ipni_records = query_gbif_dataset(
        name,
        DATASET_IPNI,
        limit=args.limit,
        exact_canonical=False,
        preferred_nub_keys=nub_keys,
    )

    return {
        "query": name,
        "resolved_backbone": {
            "queried_status": gbif.get("status"),
            "queried_scientific_name": gbif.get("scientific_name"),
            "accepted_usage_key": usage_key,
            "accepted_scientific_name": gbif.get("accepted_scientific_name") or gbif.get("scientific_name"),
        },
        "gbif_synonyms_for_accepted_taxon": gbif_synonyms,
        "kew_wcvp_records": wcvp_records,
        "ipni_protologues": ipni_records,
    }


def cmd_profile(args: argparse.Namespace) -> dict[str, Any]:
    name = args.name.strip()
    gbif = query_gbif_match(name)
    usage_key = gbif.get("accepted_usage_key") or gbif.get("usage_key")
    canonical = gbif.get("accepted_canonical_name") or gbif.get("canonical_name") or name

    vernaculars: list[dict[str, Any]] = []
    distributions: list[dict[str, Any]] = []
    children: list[dict[str, Any]] = []

    if usage_key:
        v_resp = fetch_json(f"{GBIF_BASE}/species/{usage_key}/vernacularNames", {"limit": 30})
        seen_v: set[tuple[str, str]] = set()
        for v in v_resp.get("results", []):
            vname = (v.get("vernacularName") or "").strip()
            lang = (v.get("language") or "").strip()
            if args.lang and lang.lower() != args.lang.lower():
                continue
            key_pair = (vname.lower(), lang.lower())
            if vname and key_pair not in seen_v:
                seen_v.add(key_pair)
                vernaculars.append(
                    {
                        "vernacular_name": vname,
                        "language": lang,
                        "country": v.get("country"),
                    }
                )
            if len(vernaculars) >= args.limit:
                break

        d_resp = fetch_json(f"{GBIF_BASE}/species/{usage_key}/distributions", {"limit": args.limit})
        for d in d_resp.get("results", []):
            distributions.append(
                {
                    "locality": d.get("locality"),
                    "country": d.get("country"),
                    "location_id": d.get("locationId"),
                    "establishment_means": d.get("establishmentMeans"),
                    "status": d.get("status"),
                    "threat_status": d.get("threatStatus"),
                }
            )

        c_resp = fetch_json(f"{GBIF_BASE}/species/{usage_key}/children", {"limit": args.limit})
        for c in c_resp.get("results", []):
            children.append(
                {
                    "usage_key": c.get("key"),
                    "scientific_name": c.get("scientificName"),
                    "canonical_name": c.get("canonicalName"),
                    "rank": c.get("rank"),
                    "status": c.get("taxonomicStatus"),
                }
            )

    inat_data = fetch_json(
        f"{INAT_BASE}/taxa",
        {"q": canonical, "iconic_taxa": "Plantae", "per_page": 1},
    )
    inat_summary: dict[str, Any] = {}
    if inat_data.get("results"):
        top = inat_data["results"][0]
        cs = top.get("conservation_status") or {}
        inat_summary = {
            "inat_taxon_id": top.get("id"),
            "name": top.get("name"),
            "preferred_common_name": top.get("preferred_common_name"),
            "observations_count": top.get("observations_count"),
            "wikipedia_url": top.get("wikipedia_url"),
            "extinct": top.get("extinct"),
            "conservation_status": {
                "status": cs.get("status"),
                "status_name": cs.get("status_name"),
                "authority": cs.get("authority"),
                "iucn": cs.get("iucn"),
            }
            if cs
            else None,
        }

    return {
        "query": name,
        "resolved_taxon": gbif,
        "vernacular_names": vernaculars,
        "distributions": distributions,
        "child_taxa": children,
        "inaturalist_conservation_and_summary": inat_summary,
    }


def cmd_batch(args: argparse.Namespace) -> dict[str, Any]:
    names: list[str] = []
    if args.names:
        names.extend(n.strip() for n in args.names if n.strip())
    if args.input_file:
        p = Path(args.input_file)
        content = p.read_text(encoding="utf-8")
        for line in content.splitlines():
            clean = line.strip().strip(",").strip('"').strip("'")
            if clean and not clean.startswith("#"):
                names.append(clean)

    rows: list[dict[str, Any]] = []
    for name in names:
        gbif = query_gbif_match(name)
        canonical = gbif.get("accepted_canonical_name") or gbif.get("canonical_name") or name
        wfo = query_checklistbank(canonical, dataset_key=CLB_WFO_KEY, limit=1)
        wfo_top = wfo[0] if wfo else {}
        cls = gbif.get("classification", {})
        rows.append(
            {
                "input_name": name,
                "matched": gbif.get("matched", False),
                "match_type": gbif.get("match_type"),
                "confidence": gbif.get("confidence"),
                "queried_status": gbif.get("status"),
                "queried_scientific_name": gbif.get("scientific_name"),
                "accepted_scientific_name": gbif.get("accepted_scientific_name") or gbif.get("scientific_name"),
                "canonical_name": canonical,
                "rank": gbif.get("rank"),
                "family": cls.get("family"),
                "order": cls.get("order"),
                "gbif_usage_key": gbif.get("accepted_usage_key") or gbif.get("usage_key"),
                "wfo_id": wfo_top.get("id"),
                "wfo_status": wfo_top.get("status"),
            }
        )

    if args.csv_output:
        csv_path = Path(args.csv_output)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "input_name",
            "matched",
            "match_type",
            "confidence",
            "queried_status",
            "queried_scientific_name",
            "accepted_scientific_name",
            "canonical_name",
            "rank",
            "family",
            "order",
            "gbif_usage_key",
            "wfo_id",
            "wfo_status",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return {"count": len(rows), "results": rows}


def query_bhl(
    name: str,
    limit: int = 15,
    author: str | None = None,
    year: int | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    bhl_key = api_key or os.environ.get("BHL_API_KEY")
    records: list[dict[str, Any]] = []

    # 1. Official BHL APIv3 if API key is provided
    if bhl_key:
        try:
            params = {
                "op": "NameSearch",
                "name": name,
                "apikey": bhl_key,
                "format": "json",
            }
            data = fetch_json("https://www.biodiversitylibrary.org/api3", params)
            if data.get("Status") == "ok":
                for res in data.get("Result", []):
                    name_id = res.get("NameBankID")
                    confirmed = res.get("NameConfirmed")
                    records.append(
                        {
                            "source": "BHL APIv3",
                            "name_bank_id": name_id,
                            "confirmed_name": confirmed,
                            "bhl_url": f"https://www.biodiversitylibrary.org/name/{name_id}" if name_id else None,
                        }
                    )
        except Exception:
            pass

    # 2. Zero-key BHL works via CrossRef (prefix:10.5962 is BHL)
    try:
        query_encoded = urllib.parse.quote(name)
        cr_url = f"https://api.crossref.org/works?query={query_encoded}&filter=prefix:10.5962&rows={max(limit * 2, 10)}"
        cr_data = fetch_json(cr_url)
        cr_items = cr_data.get("message", {}).get("items", [])
        for item in cr_items:
            title_list = item.get("title") or []
            title = title_list[0] if title_list else "Untitled"
            container_list = item.get("container-title") or []
            journal = container_list[0] if container_list else ""
            issued_parts = item.get("issued", {}).get("date-parts", [[None]])
            pub_year = issued_parts[0][0] if issued_parts and issued_parts[0] else None
            author_names = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in item.get("author", [])
            ]
            authors_str = ", ".join(author_names)
            doi = item.get("DOI")
            doi_url = item.get("URL") or (f"https://doi.org/{doi}" if doi else None)

            if author and author.lower() not in authors_str.lower():
                continue
            if year and pub_year != year:
                continue

            records.append(
                {
                    "source": "Biodiversity Heritage Library (BHL DOIs)",
                    "title": title,
                    "journal_or_series": journal,
                    "year": pub_year,
                    "authors": authors_str,
                    "doi": doi,
                    "bhl_part_url": doi_url,
                    "volume": item.get("volume"),
                    "issue": item.get("issue"),
                    "page": item.get("page"),
                }
            )
            if len(records) >= limit:
                break
    except Exception:
        pass

    # 3. GBIF Literature Search (papers, treatments, and monographs citing the species)
    gbif_literature: list[dict[str, Any]] = []
    try:
        gl_data = fetch_json(f"{GBIF_BASE}/literature/search", {"q": name, "limit": 5})
        for gl_item in gl_data.get("results", []):
            gl_authors = [
                f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
                for a in gl_item.get("authors", [])
            ]
            gbif_literature.append(
                {
                    "title": gl_item.get("title"),
                    "year": gl_item.get("year"),
                    "authors": ", ".join(gl_authors),
                    "source": gl_item.get("source"),
                    "doi": gl_item.get("identifiers", {}).get("doi"),
                    "url": (gl_item.get("websites") or [None])[0],
                }
            )
    except Exception:
        pass

    encoded_name = urllib.parse.quote(name)
    portal_urls = {
        "bhl_name_search": f"https://www.biodiversitylibrary.org/search?searchTerm={encoded_name}#/names",
        "bhl_title_search": f"https://www.biodiversitylibrary.org/search?searchTerm={encoded_name}#/titles",
    }

    return {
        "query": name,
        "database": "Biodiversity Heritage Library (BHL) & Taxonomic Literature",
        "portal_links": portal_urls,
        "api_key_configured": bool(bhl_key),
        "bhl_citations_count": len(records),
        "bhl_citations": records[:limit],
        "gbif_literature_count": len(gbif_literature),
        "gbif_literature": gbif_literature,
    }


def cmd_bhl(args: argparse.Namespace) -> dict[str, Any]:
    name = args.name.strip()
    api_key = getattr(args, "api_key", None)
    return query_bhl(name, limit=args.limit, author=args.author, year=args.year, api_key=api_key)


def query_specimens(name: str, limit: int = 10, country: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "scientificName": name,
        "basisOfRecord": "PRESERVED_SPECIMEN",
        "limit": max(limit * 2, 20),
    }
    if country:
        params["country"] = country.upper()
    data = fetch_json(f"{GBIF_BASE}/occurrence/search", params)
    results = data.get("results", [])
    specimens: list[dict[str, Any]] = []
    for item in results:
        media_list = []
        for m in item.get("media", []):
            if m.get("identifier"):
                media_list.append(
                    {
                        "format": m.get("format"),
                        "image_url": m.get("identifier"),
                        "license": m.get("license"),
                    }
                )
        specimens.append(
            {
                "gbif_occurrence_id": item.get("gbifID"),
                "occurrence_url": f"https://www.gbif.org/occurrence/{item.get('gbifID')}" if item.get("gbifID") else None,
                "institution_code": item.get("institutionCode"),
                "collection_code": item.get("collectionCode"),
                "catalog_number": item.get("catalogNumber"),
                "recorded_by": item.get("recordedBy"),
                "record_number": item.get("recordNumber"),
                "event_date": item.get("eventDate"),
                "country": item.get("country"),
                "locality": item.get("locality"),
                "elevation_m": item.get("elevation"),
                "decimal_latitude": item.get("decimalLatitude"),
                "decimal_longitude": item.get("decimalLongitude"),
                "type_status": item.get("typeStatus"),
                "media_images": media_list,
            }
        )
        if len(specimens) >= limit:
            break
    return specimens


def cmd_specimens(args: argparse.Namespace) -> dict[str, Any]:
    name = args.name.strip()
    gbif = query_gbif_match(name)
    lookup_name = gbif.get("accepted_scientific_name") or gbif.get("scientific_name") or name
    records = query_specimens(lookup_name, limit=args.limit, country=args.country)
    return {
        "query": name,
        "resolved_scientific_name": lookup_name,
        "database": "Global Herbarium Preserved Specimens (GBIF)",
        "count": len(records),
        "results": records,
    }


def cmd_dossier(args: argparse.Namespace) -> dict[str, Any]:
    name = args.name.strip()
    res = cmd_resolve(argparse.Namespace(name=name, rank=None, limit=5))
    hier = cmd_hierarchy(argparse.Namespace(name=name))
    syn = cmd_synonyms(argparse.Namespace(name=name, limit=args.limit))
    prof = cmd_profile(argparse.Namespace(name=name, lang=args.lang, limit=args.limit))
    canonical = res.get("gbif_backbone", {}).get("canonical_name") or name
    bhl_data = query_bhl(canonical, limit=5)
    specimen_records = query_specimens(canonical, limit=5)

    return {
        "taxon_query": name,
        "nomenclatural_resolution": res,
        "phylogenetic_and_taxonomic_hierarchy": hier,
        "synonymy_and_protologues": syn,
        "floristics_and_conservation": prof,
        "biodiversity_heritage_library": bhl_data,
        "herbarium_specimens": {
            "count": len(specimen_records),
            "vouchers": specimen_records,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query global plant taxonomic databases (GBIF, Kew WCVP/POWO, WFO, IPNI, CoL, NCBI, BHL)."
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Optional file path to write JSON output to.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_res = sub.add_parser("resolve", help="Resolve a plant name across GBIF, Kew WCVP, WFO, and IPNI.")
    p_res.add_argument("--name", "-n", required=True, help="Scientific or common plant name to resolve.")
    p_res.add_argument("--rank", "-r", help="Optional rank filter (e.g., SPECIES, GENUS, FAMILY).")
    p_res.add_argument("--limit", "-l", type=int, default=5, help="Max records per database (default: 5).")
    p_res.set_defaults(func=cmd_resolve)

    p_hier = sub.add_parser("hierarchy", help="Fetch Linnaean, WFO, CoL, and NCBI APG IV clade hierarchy.")
    p_hier.add_argument("--name", "-n", required=True, help="Plant taxon name.")
    p_hier.set_defaults(func=cmd_hierarchy)

    p_syn = sub.add_parser("synonyms", help="Fetch synonyms, basionyms, and IPNI protologue citations.")
    p_syn.add_argument("--name", "-n", required=True, help="Plant scientific name.")
    p_syn.add_argument("--limit", "-l", type=int, default=15, help="Max synonyms to return (default: 15).")
    p_syn.set_defaults(func=cmd_synonyms)

    p_prof = sub.add_parser("profile", help="Fetch vernacular names, distributions, child taxa, and IUCN status.")
    p_prof.add_argument("--name", "-n", required=True, help="Plant scientific name.")
    p_prof.add_argument("--lang", help="Optional 3-letter ISO language filter for vernacular names (e.g., eng, spa).")
    p_prof.add_argument("--limit", "-l", type=int, default=15, help="Max items per section (default: 15).")
    p_prof.set_defaults(func=cmd_profile)

    p_batch = sub.add_parser("batch", help="Standardize a batch of plant names into accepted taxa and IDs.")
    p_batch.add_argument("--names", "-n", nargs="*", help="List of plant names to standardize.")
    p_batch.add_argument("--input-file", "-i", help="Text/CSV file with one plant name per line.")
    p_batch.add_argument("--csv-output", help="Optional path to write standardized CSV table.")
    p_batch.set_defaults(func=cmd_batch)

    p_bhl = sub.add_parser("bhl", help="Query Biodiversity Heritage Library for literature citations and digitized books.")
    p_bhl.add_argument("--name", "-n", required=True, help="Scientific plant name to search in BHL.")
    p_bhl.add_argument("--author", help="Optional author filter.")
    p_bhl.add_argument("--year", type=int, help="Optional year filter.")
    p_bhl.add_argument("--api-key", help="Optional Biodiversity Heritage Library API key (or set BHL_API_KEY env var).")
    p_bhl.add_argument("--limit", "-l", type=int, default=15, help="Max BHL citations to return (default: 15).")
    p_bhl.set_defaults(func=cmd_bhl)

    p_spec = sub.add_parser("specimens", help="Query global herbaria for digitized preserved plant specimen vouchers.")
    p_spec.add_argument("--name", "-n", required=True, help="Plant scientific name.")
    p_spec.add_argument("--country", help="Optional 2-letter ISO country code filter (e.g., PH, US, ID).")
    p_spec.add_argument("--limit", "-l", type=int, default=10, help="Max specimen vouchers to return (default: 10).")
    p_spec.set_defaults(func=cmd_specimens)

    p_dossier = sub.add_parser("dossier", help="Generate full multi-perspective botanical dossier including BHL literature & specimens.")
    p_dossier.add_argument("--name", "-n", required=True, help="Plant taxon name.")
    p_dossier.add_argument("--lang", help="Optional language filter for vernacular names.")
    p_dossier.add_argument("--limit", "-l", type=int, default=15, help="Max records per category.")
    p_dossier.set_defaults(func=cmd_dossier)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    formatted = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(formatted + "\n", encoding="utf-8")
    else:
        print(formatted)


if __name__ == "__main__":
    main()
