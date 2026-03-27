"""
collect_pubmed.py — Fetch cancer research abstracts from PubMed

Uses NCBI E-utilities API (free, no API key required for <3 requests/sec;
API key recommended for higher throughput).

Targets research relevant to:
- Delaware cancer epidemiology
- Clinical trial outcomes for Big 4 cancers (breast, lung, colorectal, prostate)
- Triple-negative breast cancer (Delaware is #1 nationally)
- Cancer health disparities
- Immunotherapy and targeted therapy outcomes
"""

import requests
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "pubmed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# ============================================================
# SEARCH QUERIES
# ============================================================
# Each query targets a specific aspect of our knowledge base.
# PubMed uses boolean operators and field tags for precise search.

SEARCH_QUERIES = [
    {
        "name": "Delaware cancer epidemiology",
        "query": '("Delaware"[Title/Abstract]) AND ("cancer"[Title/Abstract] OR "neoplasm"[Title/Abstract])',
        "max_results": 200,
        "description": "Any published research specifically about cancer in Delaware",
    },
    {
        "name": "Delaware breast cancer TNBC",
        "query": '("Delaware"[Title/Abstract]) AND ("breast cancer"[Title/Abstract] OR "triple negative"[Title/Abstract])',
        "max_results": 100,
        "description": "Delaware-specific breast cancer and TNBC research",
    },
    {
        "name": "TNBC clinical trials outcomes",
        "query": '("triple negative breast cancer"[Title]) AND ("clinical trial"[Publication Type]) AND ("2022"[Date - Publication] : "2026"[Date - Publication])',
        "max_results": 150,
        "description": "Recent TNBC clinical trial results — directly relevant to Delaware's #1 TNBC ranking",
    },
    {
        "name": "Immunotherapy cancer trials outcomes",
        "query": '("pembrolizumab"[Title] OR "nivolumab"[Title]) AND ("clinical trial"[Publication Type]) AND ("overall survival"[Title/Abstract]) AND ("2023"[Date - Publication] : "2026"[Date - Publication])',
        "max_results": 150,
        "description": "Latest checkpoint inhibitor trial results with survival data",
    },
    {
        "name": "Colorectal cancer screening disparities",
        "query": '("colorectal cancer"[Title]) AND ("screening"[Title]) AND ("disparity"[Title/Abstract] OR "inequity"[Title/Abstract]) AND ("2020"[Date - Publication] : "2026"[Date - Publication])',
        "max_results": 100,
        "description": "Screening disparities in CRC — relevant to Delaware's racial disparities",
    },
    {
        "name": "Lung cancer biomarker testing",
        "query": '("lung cancer"[Title]) AND ("biomarker testing"[Title/Abstract] OR "molecular testing"[Title/Abstract]) AND ("2022"[Date - Publication] : "2026"[Date - Publication])',
        "max_results": 100,
        "description": "Delaware has not mandated biomarker testing coverage for lung cancer",
    },
    {
        "name": "Prostate cancer racial disparities",
        "query": '("prostate cancer"[Title]) AND ("African American"[Title/Abstract] OR "Black"[Title/Abstract]) AND ("disparity"[Title/Abstract] OR "mortality"[Title]) AND ("2020"[Date - Publication] : "2026"[Date - Publication])',
        "max_results": 100,
        "description": "Relevant to Delaware's significantly higher prostate cancer mortality among Black men",
    },
    {
        "name": "Cancer clinical trial enrollment barriers",
        "query": '("clinical trial"[Title]) AND ("cancer"[Title]) AND ("enrollment"[Title/Abstract] OR "recruitment"[Title/Abstract] OR "barrier"[Title/Abstract]) AND ("2021"[Date - Publication] : "2026"[Date - Publication])',
        "max_results": 100,
        "description": "Research on why patients don't find or join trials — the core problem TrialScope solves",
    },
    {
        "name": "ADC breast cancer Enhertu Trodelvy",
        "query": '("antibody drug conjugate"[Title] OR "trastuzumab deruxtecan"[Title] OR "sacituzumab govitecan"[Title]) AND ("breast cancer"[Title]) AND ("2023"[Date - Publication] : "2026"[Date - Publication])',
        "max_results": 100,
        "description": "Latest ADC results — Trodelvy is specifically for metastatic TNBC",
    },
    {
        "name": "Cancer geographic hotspot analysis",
        "query": '("cancer"[Title]) AND ("geographic"[Title/Abstract] OR "hotspot"[Title/Abstract] OR "census tract"[Title/Abstract]) AND ("incidence"[Title/Abstract])',
        "max_results": 50,
        "description": "Methods for geographic cancer analysis — similar to Delaware's tract-level studies",
    },
]


def search_pubmed(query: str, max_results: int = 100) -> list:
    """
    Search PubMed and return list of PMIDs.
    Uses esearch endpoint.
    """
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }

    try:
        response = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  Search error: {e}")
        return []


def fetch_abstracts(pmids: list) -> list:
    """
    Fetch full article details for a list of PMIDs.
    Uses efetch endpoint returning XML.
    """
    if not pmids:
        return []

    articles = []

    # Process in batches of 50
    for i in range(0, len(pmids), 50):
        batch = pmids[i:i+50]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
            "rettype": "abstract",
        }

        try:
            response = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=params, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            for article_elem in root.findall(".//PubmedArticle"):
                article = parse_article(article_elem)
                if article:
                    articles.append(article)

        except Exception as e:
            print(f"  Fetch error for batch starting at {i}: {e}")

        time.sleep(0.4)  # Rate limiting (max 3 req/sec without API key)

    return articles


def parse_article(elem) -> dict:
    """Parse a PubmedArticle XML element into a clean dict."""
    try:
        medline = elem.find(".//MedlineCitation")
        if medline is None:
            return None

        pmid = medline.findtext("PMID", "")
        article = medline.find("Article")
        if article is None:
            return None

        # Title
        title = article.findtext("ArticleTitle", "")

        # Abstract
        abstract_parts = []
        abstract_elem = article.find("Abstract")
        if abstract_elem is not None:
            for text in abstract_elem.findall("AbstractText"):
                label = text.get("Label", "")
                content = text.text or ""
                # Also grab any tail text from child elements
                full_text = ET.tostring(text, encoding="unicode", method="text").strip()
                if label:
                    abstract_parts.append(f"{label}: {full_text}")
                else:
                    abstract_parts.append(full_text)
        abstract = "\n".join(abstract_parts)

        # Authors
        authors = []
        author_list = article.find("AuthorList")
        if author_list is not None:
            for author in author_list.findall("Author"):
                last = author.findtext("LastName", "")
                first = author.findtext("ForeName", "")
                if last:
                    authors.append(f"{last} {first}".strip())

        # Journal
        journal = article.find("Journal")
        journal_title = journal.findtext("Title", "") if journal is not None else ""
        pub_date = ""
        if journal is not None:
            jissue = journal.find("JournalIssue")
            if jissue is not None:
                pd = jissue.find("PubDate")
                if pd is not None:
                    year = pd.findtext("Year", "")
                    month = pd.findtext("Month", "")
                    pub_date = f"{year} {month}".strip()

        # MeSH terms
        mesh_terms = []
        mesh_list = medline.find("MeshHeadingList")
        if mesh_list is not None:
            for mesh in mesh_list.findall("MeshHeading"):
                descriptor = mesh.findtext("DescriptorName", "")
                if descriptor:
                    mesh_terms.append(descriptor)

        # Keywords
        keywords = []
        kw_list = medline.find("KeywordList")
        if kw_list is not None:
            for kw in kw_list.findall("Keyword"):
                if kw.text:
                    keywords.append(kw.text)

        # DOI
        doi = ""
        id_list = elem.find(".//PubmedData/ArticleIdList")
        if id_list is not None:
            for aid in id_list.findall("ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = aid.text or ""

        return {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal_title,
            "publication_date": pub_date,
            "doi": doi,
            "mesh_terms": mesh_terms,
            "keywords": keywords,
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }

    except Exception as e:
        return None


def main():
    print("=" * 50)
    print("TrialScope DE — PubMed Research Collection")
    print("=" * 50)
    print(f"Search queries: {len(SEARCH_QUERIES)}")
    print()

    all_articles = {}  # PMID -> article (dedup)

    for i, sq in enumerate(SEARCH_QUERIES, 1):
        print(f"[{i}/{len(SEARCH_QUERIES)}] {sq['name']}")
        print(f"  Query: {sq['query'][:80]}...")

        pmids = search_pubmed(sq["query"], sq["max_results"])
        print(f"  Found {len(pmids)} results")

        if pmids:
            articles = fetch_abstracts(pmids)
            new_count = 0
            for article in articles:
                if article["pmid"] not in all_articles:
                    article["search_category"] = sq["name"]
                    all_articles[article["pmid"]] = article
                    new_count += 1
            print(f"  Fetched {len(articles)} abstracts, {new_count} new")

        time.sleep(0.5)

    # Save all articles
    articles_list = list(all_articles.values())
    output_file = OUTPUT_DIR / "all_pubmed_articles.json"
    with open(output_file, "w") as f:
        json.dump(articles_list, f, indent=2)

    # Save individual articles
    for article in articles_list:
        article_file = OUTPUT_DIR / f"PMID_{article['pmid']}.json"
        with open(article_file, "w") as f:
            json.dump(article, f, indent=2)

    # Save metadata
    metadata = {
        "collection_date": datetime.now().isoformat(),
        "total_unique_articles": len(all_articles),
        "queries": [
            {
                "name": sq["name"],
                "description": sq["description"],
                "max_results": sq["max_results"],
            }
            for sq in SEARCH_QUERIES
        ],
        "articles_by_category": {},
    }

    for article in articles_list:
        cat = article.get("search_category", "unknown")
        metadata["articles_by_category"][cat] = metadata["articles_by_category"].get(cat, 0) + 1

    meta_file = OUTPUT_DIR / "pubmed_metadata.json"
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n{'='*50}")
    print(f"COLLECTION SUMMARY")
    print(f"{'='*50}")
    print(f"Total unique articles: {len(all_articles)}")
    print(f"\nBy category:")
    for cat, count in sorted(metadata["articles_by_category"].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nOutput: {OUTPUT_DIR}")
    print(f"\nNext step: python scripts/upload_to_s3.py")


if __name__ == "__main__":
    main()
