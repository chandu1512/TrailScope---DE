"""
collect_fda_reviews.py — Download FDA drug review documents for cancer therapies

These are the detailed medical/scientific review PDFs that FDA publishes
when approving a new drug. They contain:
- Clinical trial results (efficacy tables, survival curves)
- Safety data (adverse events, side effects with frequency)
- Statistical review (p-values, confidence intervals, methodology)
- Pharmacology review (mechanism of action, dosing)

Source: FDA Drugs@FDA database (public, no API key needed)
URL pattern: https://www.accessdata.fda.gov/drugsatfda_docs/nda/{app_number}/{review_type}.pdf

We focus on cancer drugs approved 2020-2026, especially:
- Immunotherapies (pembrolizumab, nivolumab, atezolizumab)
- Targeted therapies (PARP inhibitors, CDK4/6 inhibitors)
- Drugs relevant to Delaware's top cancers (breast, lung, colorectal, prostate)
"""

import requests
import json
import os
import time
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "fda_reviews"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# CANCER DRUGS TO COLLECT
# ============================================================
# Each entry: drug name, generic name, cancer type(s), FDA app number,
# and the URLs for key review documents

CANCER_DRUGS = [
    {
        "brand_name": "Keytruda",
        "generic_name": "pembrolizumab",
        "cancer_types": ["melanoma", "lung cancer", "colorectal cancer", "breast cancer", "head and neck cancer"],
        "manufacturer": "Merck",
        "approval_year": 2014,
        "description": "PD-1 blocking antibody (checkpoint inhibitor). One of the most widely used immunotherapies. Relevant to multiple Delaware cancer types.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/125514s142lbl.pdf",
    },
    {
        "brand_name": "Opdivo",
        "generic_name": "nivolumab",
        "cancer_types": ["melanoma", "lung cancer", "kidney cancer", "colorectal cancer", "liver cancer"],
        "manufacturer": "Bristol-Myers Squibb",
        "approval_year": 2014,
        "description": "PD-1 checkpoint inhibitor. Used alone or with ipilimumab for multiple cancers.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/125554s123lbl.pdf",
    },
    {
        "brand_name": "Ibrance",
        "generic_name": "palbociclib",
        "cancer_types": ["breast cancer"],
        "manufacturer": "Pfizer",
        "approval_year": 2015,
        "description": "CDK4/6 inhibitor for HR+/HER2- metastatic breast cancer. Critical for Delaware's high breast cancer rates.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/207103s021lbl.pdf",
    },
    {
        "brand_name": "Lynparza",
        "generic_name": "olaparib",
        "cancer_types": ["breast cancer", "ovarian cancer", "prostate cancer"],
        "manufacturer": "AstraZeneca",
        "approval_year": 2014,
        "description": "PARP inhibitor for BRCA-mutated cancers. Relevant to TNBC (Delaware has highest TNBC rate nationally).",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/208558s028lbl.pdf",
    },
    {
        "brand_name": "Tagrisso",
        "generic_name": "osimertinib",
        "cancer_types": ["lung cancer"],
        "manufacturer": "AstraZeneca",
        "approval_year": 2015,
        "description": "EGFR tyrosine kinase inhibitor for non-small cell lung cancer. Lung cancer is deadliest of Delaware's 'Big 4'.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/208065s029lbl.pdf",
    },
    {
        "brand_name": "Enhertu",
        "generic_name": "trastuzumab deruxtecan",
        "cancer_types": ["breast cancer", "lung cancer", "gastric cancer"],
        "manufacturer": "Daiichi Sankyo / AstraZeneca",
        "approval_year": 2019,
        "description": "Antibody-drug conjugate for HER2+ cancers. Breakthrough therapy with practice-changing trial results.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761139s026lbl.pdf",
    },
    {
        "brand_name": "Trodelvy",
        "generic_name": "sacituzumab govitecan",
        "cancer_types": ["breast cancer", "bladder cancer"],
        "manufacturer": "Gilead Sciences",
        "approval_year": 2020,
        "description": "Antibody-drug conjugate for metastatic TNBC. Directly relevant to Delaware's #1 national TNBC ranking.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761115s020lbl.pdf",
    },
    {
        "brand_name": "Opdualag",
        "generic_name": "nivolumab and relatlimab",
        "cancer_types": ["melanoma"],
        "manufacturer": "Bristol-Myers Squibb",
        "approval_year": 2022,
        "description": "First LAG-3 blocking antibody combo with nivolumab for melanoma.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761208s005lbl.pdf",
    },
    {
        "brand_name": "Lumakras",
        "generic_name": "sotorasib",
        "cancer_types": ["lung cancer"],
        "manufacturer": "Amgen",
        "approval_year": 2021,
        "description": "First KRAS G12C inhibitor. Targets a mutation previously considered 'undruggable'.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/214665s003lbl.pdf",
    },
    {
        "brand_name": "Xtandi",
        "generic_name": "enzalutamide",
        "cancer_types": ["prostate cancer"],
        "manufacturer": "Pfizer / Astellas",
        "approval_year": 2012,
        "description": "Androgen receptor inhibitor for prostate cancer. Relevant to Delaware's disparity in prostate cancer mortality among Black men.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/203415s024lbl.pdf",
    },
    {
        "brand_name": "Stivarga",
        "generic_name": "regorafenib",
        "cancer_types": ["colorectal cancer", "liver cancer"],
        "manufacturer": "Bayer",
        "approval_year": 2012,
        "description": "Multi-kinase inhibitor for metastatic colorectal cancer. Colorectal is one of Delaware's Big 4.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/203085s012lbl.pdf",
    },
    {
        "brand_name": "Verzenio",
        "generic_name": "abemaciclib",
        "cancer_types": ["breast cancer"],
        "manufacturer": "Eli Lilly",
        "approval_year": 2017,
        "description": "CDK4/6 inhibitor with unique continuous dosing. Used in early-stage HR+/HER2- breast cancer.",
        "fda_label_url": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/208716s013lbl.pdf",
    },
]


def download_fda_label(drug: dict) -> bool:
    """Download the FDA drug label PDF."""
    url = drug["fda_label_url"]
    filename = f"{drug['generic_name'].replace(' ', '_')}_label.pdf"
    filepath = OUTPUT_DIR / filename

    if filepath.exists():
        print(f"  Already downloaded: {filename}")
        return True

    try:
        response = requests.get(url, timeout=60, headers={
            "User-Agent": "TrialScopeDE/1.0 (Academic Research Project)"
        })
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        size_mb = len(response.content) / (1024 * 1024)
        print(f"  Downloaded: {filename} ({size_mb:.1f} MB)")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  Error downloading {filename}: {e}")
        return False


def save_drug_metadata():
    """Save a JSON index of all collected drugs and their metadata."""
    metadata = {
        "collection_date": datetime.now().isoformat(),
        "total_drugs": len(CANCER_DRUGS),
        "drugs": [],
    }

    for drug in CANCER_DRUGS:
        filename = f"{drug['generic_name'].replace(' ', '_')}_label.pdf"
        filepath = OUTPUT_DIR / filename

        metadata["drugs"].append({
            "brand_name": drug["brand_name"],
            "generic_name": drug["generic_name"],
            "cancer_types": drug["cancer_types"],
            "manufacturer": drug["manufacturer"],
            "approval_year": drug["approval_year"],
            "description": drug["description"],
            "local_filename": filename,
            "downloaded": filepath.exists(),
            "file_size_bytes": filepath.stat().st_size if filepath.exists() else 0,
        })

    meta_file = OUTPUT_DIR / "drug_metadata.json"
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"\nSaved drug metadata: {meta_file}")


def main():
    print("=" * 50)
    print("TrialScope DE — FDA Drug Review Collection")
    print("=" * 50)
    print(f"Drugs to collect: {len(CANCER_DRUGS)}")
    print()

    success_count = 0
    for i, drug in enumerate(CANCER_DRUGS, 1):
        print(f"[{i}/{len(CANCER_DRUGS)}] {drug['brand_name']} ({drug['generic_name']})")
        print(f"  Cancer types: {', '.join(drug['cancer_types'])}")

        if download_fda_label(drug):
            success_count += 1

        time.sleep(1)  # Be respectful to FDA servers

    save_drug_metadata()

    print(f"\n{'='*50}")
    print(f"COLLECTION SUMMARY")
    print(f"{'='*50}")
    print(f"Successfully downloaded: {success_count}/{len(CANCER_DRUGS)} drug labels")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"\nNext step: python scripts/collect_de_reports.py")


if __name__ == "__main__":
    main()
