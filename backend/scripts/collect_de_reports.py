"""
collect_de_reports.py — Download Delaware Division of Public Health cancer reports

These PDFs contain Delaware-specific cancer data:
- Annual incidence and mortality rates by cancer type
- Census tract level hotspot analysis
- Racial/ethnic disparity data
- Screening rates and trends
- Geographic analysis (Route 9 Corridor, Wilmington hotspots)

Source: Delaware DHSS Division of Public Health (all public PDFs)
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "de_reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# DELAWARE CANCER REPORTS
# ============================================================

DE_REPORTS = [
    {
        "name": "Cancer Incidence and Mortality in Delaware 2017-2021",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/cim2017-2021.pdf",
        "year": "2024",
        "type": "annual_report",
        "description": "Latest comprehensive cancer report. All-site and site-specific incidence/mortality rates, trends, and demographic breakdowns.",
    },
    {
        "name": "Cancer Incidence and Mortality Data Tables 2017-2021",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/cim2017-2021datatables.pdf",
        "year": "2024",
        "type": "data_tables",
        "description": "Detailed statistical tables — rates by cancer type, age, race, sex, county. Essential for multi-modal RAG (table extraction).",
    },
    {
        "name": "Small Area-Level Cancer Incidence in Delaware 2017-2021",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/smallarea2017-2021.pdf",
        "year": "2024",
        "type": "geographic_analysis",
        "description": "Census tract level cancer rates. Identifies geographic hotspots across the state.",
    },
    {
        "name": "Route 9 Corridor Data Analysis with Delaware Cancer Registry 2025",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/route9corridordataanalysis2025.pdf",
        "year": "2025",
        "type": "special_analysis",
        "description": "Analysis of the Route 9 corridor area near Wilmington with historically elevated cancer rates.",
    },
    {
        "name": "Cancer Incidence and Mortality in Delaware 2016-2020",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/cim2016-2020.pdf",
        "year": "2023",
        "type": "annual_report",
        "description": "Previous period report for trend comparison.",
    },
    {
        "name": "Census Tract Level Cancer Incidence 2016-2020",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/censustractcancer2016-2020.pdf",
        "year": "2023",
        "type": "geographic_analysis",
        "description": "Census tract analysis for the 2016-2020 period.",
    },
    {
        "name": "Colorectal Cancer Data Brief 2016-2020",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/crcbrief2016-2020.pdf",
        "year": "2023",
        "type": "cancer_specific",
        "description": "Focused analysis on colorectal cancer — one of Delaware's Big 4.",
    },
    {
        "name": "Cancer Incidence and Mortality in Delaware 2011-2015",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/cim2011-2015.pdf",
        "year": "2019",
        "type": "annual_report",
        "description": "Historical report for long-term trend analysis.",
    },
    {
        "name": "Elevated Cancer Rates Census Tracts 2012-2016",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/elevated2012-2016.pdf",
        "year": "2020",
        "type": "geographic_analysis",
        "description": "Identifies census tracts with statistically elevated cancer rates.",
    },
    {
        "name": "Disparities in Cancer Incidence and Mortality 2010-2014",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/disparities2010-2014.pdf",
        "year": "2018",
        "type": "disparity_analysis",
        "description": "Detailed analysis of cancer disparities by race, ethnicity, age, and geography.",
    },
    {
        "name": "Cancer Incidence and Mortality in Delaware 2010-2014",
        "url": "https://dhss.delaware.gov/dhss/dph/dpc/files/cim2010-2014.pdf",
        "year": "2018",
        "type": "annual_report",
        "description": "Historical baseline when Delaware ranked 2nd nationally for cancer incidence.",
    },
]


def download_report(report: dict) -> bool:
    """Download a single report PDF."""
    safe_name = report["name"].replace(" ", "_").replace("/", "-").replace(",", "")
    safe_name = safe_name[:80]  # Limit filename length
    filename = f"{safe_name}.pdf"
    filepath = OUTPUT_DIR / filename

    if filepath.exists():
        print(f"  Already downloaded: {filename}")
        report["local_filename"] = filename
        return True

    try:
        response = requests.get(
            report["url"],
            timeout=60,
            headers={"User-Agent": "TrialScopeDE/1.0 (Academic Research Project)"},
        )
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        size_mb = len(response.content) / (1024 * 1024)
        print(f"  Downloaded: {filename} ({size_mb:.1f} MB)")
        report["local_filename"] = filename
        return True

    except requests.exceptions.RequestException as e:
        print(f"  Error: {e}")
        report["local_filename"] = None
        return False


def save_metadata():
    """Save collection metadata."""
    metadata = {
        "collection_date": datetime.now().isoformat(),
        "source": "Delaware Division of Public Health",
        "total_reports": len(DE_REPORTS),
        "reports": [],
    }

    for report in DE_REPORTS:
        filepath = OUTPUT_DIR / (report.get("local_filename") or "")
        metadata["reports"].append({
            "name": report["name"],
            "year": report["year"],
            "type": report["type"],
            "description": report["description"],
            "source_url": report["url"],
            "local_filename": report.get("local_filename"),
            "downloaded": filepath.exists() if report.get("local_filename") else False,
            "file_size_bytes": filepath.stat().st_size if filepath.exists() else 0,
        })

    meta_file = OUTPUT_DIR / "de_reports_metadata.json"
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"\nSaved metadata: {meta_file}")


def main():
    print("=" * 50)
    print("TrialScope DE — Delaware Cancer Reports Collection")
    print("=" * 50)
    print(f"Reports to collect: {len(DE_REPORTS)}")
    print()

    success = 0
    for i, report in enumerate(DE_REPORTS, 1):
        print(f"[{i}/{len(DE_REPORTS)}] {report['name']}")
        print(f"  Type: {report['type']} | Year: {report['year']}")

        if download_report(report):
            success += 1

        time.sleep(1)

    save_metadata()

    print(f"\n{'='*50}")
    print(f"COLLECTION SUMMARY")
    print(f"{'='*50}")
    print(f"Downloaded: {success}/{len(DE_REPORTS)} reports")
    print(f"Output: {OUTPUT_DIR}")
    print(f"\nNext step: python scripts/collect_pubmed.py")


if __name__ == "__main__":
    main()
