"""
collect_trials.py — Fetch cancer clinical trials from ClinicalTrials.gov API v2

Targets: Delaware + surrounding states (Maryland, Pennsylvania, New Jersey)
Focus: All cancer-related trials that are recruiting or recently completed

ClinicalTrials.gov API v2 docs: https://clinicaltrials.gov/data-api/api

What this script collects:
- Trial ID (NCT number)
- Title and brief summary
- Phase (1, 2, 3, 4)
- Status (Recruiting, Active, Completed)
- Conditions (specific cancer types)
- Interventions (drugs, procedures, devices)
- Eligibility criteria (age, sex, inclusion/exclusion)
- Locations (sites in DE, MD, PA, NJ)
- Outcome measures and results (if available)
- Sponsor and collaborators
- Study dates
"""

import requests
import json
import os
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

API_BASE = "https://clinicaltrials.gov/api/v2/studies"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw_trials"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# States to search — Delaware + neighbors for maximum coverage
TARGET_STATES = ["Delaware", "Maryland", "Pennsylvania", "New Jersey"]

# Cancer-related search terms
CANCER_QUERIES = [
    "breast cancer",
    "lung cancer",
    "colorectal cancer",
    "prostate cancer",
    "triple negative breast cancer",
    "melanoma",
    "pancreatic cancer",
    "ovarian cancer",
    "leukemia",
    "lymphoma",
    "bladder cancer",
    "kidney cancer",
    "liver cancer",
    "thyroid cancer",
    "brain cancer",
    "head and neck cancer",
    "immunotherapy cancer",
    "cancer",  # broad catch-all
]

# Fields to retrieve from the API
FIELDS = [
    "NCTId",
    "BriefTitle",
    "OfficialTitle",
    "BriefSummary",
    "DetailedDescription",
    "OverallStatus",
    "Phase",
    "StudyType",
    "EnrollmentCount",
    "EnrollmentType",
    "Condition",
    "InterventionName",
    "InterventionType",
    "InterventionDescription",
    "EligibilityCriteria",
    "Gender",
    "MinimumAge",
    "MaximumAge",
    "HealthyVolunteers",
    "LocationCity",
    "LocationState",
    "LocationFacility",
    "LocationCountry",
    "LocationStatus",
    "PrimaryOutcomeMeasure",
    "PrimaryOutcomeTimeFrame",
    "SecondaryOutcomeMeasure",
    "LeadSponsorName",
    "CollaboratorName",
    "StartDate",
    "CompletionDate",
    "StudyFirstPostDate",
    "LastUpdatePostDate",
    "ResponsiblePartyInvestigatorFullName",
    "ResponsiblePartyInvestigatorAffiliation",
]

# ============================================================
# DATA COLLECTION
# ============================================================

def fetch_trials(query: str, location: str, page_size: int = 100) -> list:
    """
    Fetch trials from ClinicalTrials.gov API v2.

    The API returns paginated results. We use the pageToken
    parameter to iterate through all pages.
    """
    all_studies = []
    next_page_token = None

    while True:
        params = {
            "query.cond": query,
            "query.locn": location,
            "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,COMPLETED",
            "pageSize": page_size,
            "format": "json",
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        try:
            response = requests.get(API_BASE, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching {query} in {location}: {e}")
            break

        studies = data.get("studies", [])
        all_studies.extend(studies)

        next_page_token = data.get("nextPageToken")
        if not next_page_token or not studies:
            break

        # Be respectful to the API
        time.sleep(0.5)

    return all_studies


def collect_all_trials() -> dict:
    """
    Collect trials across all cancer types and target states.
    Deduplicates by NCT ID since the same trial may appear
    in multiple searches.
    """
    all_trials = {}  # NCT ID -> study data (dedup)
    total_queries = len(CANCER_QUERIES) * len(TARGET_STATES)
    current = 0

    for state in TARGET_STATES:
        for query in CANCER_QUERIES:
            current += 1
            print(f"[{current}/{total_queries}] Searching: '{query}' in {state}...")

            trials = fetch_trials(query, state)

            new_count = 0
            for trial in trials:
                nct_id = trial.get("protocolSection", {}).get(
                    "identificationModule", {}
                ).get("nctId", "UNKNOWN")

                if nct_id not in all_trials:
                    all_trials[nct_id] = trial
                    new_count += 1

            print(f"  Found {len(trials)} results, {new_count} new (total: {len(all_trials)})")
            time.sleep(0.3)  # Rate limiting

    return all_trials


def extract_trial_summary(study: dict) -> dict:
    """
    Extract a clean summary from the raw API response.
    This structured format is what goes into our S3 bucket
    and eventually gets chunked for the RAG pipeline.
    """
    protocol = study.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    status_module = protocol.get("statusModule", {})
    desc = protocol.get("descriptionModule", {})
    design = protocol.get("designModule", {})
    eligibility = protocol.get("eligibilityModule", {})
    contacts = protocol.get("contactsLocationsModule", {})
    outcomes = protocol.get("outcomesModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {})

    # Extract locations in our target states
    locations = []
    for loc in contacts.get("locations", []):
        state = loc.get("state", "")
        if state in TARGET_STATES:
            locations.append({
                "facility": loc.get("facility", ""),
                "city": loc.get("city", ""),
                "state": state,
                "zip": loc.get("zip", ""),
                "status": loc.get("status", ""),
            })

    # Extract interventions
    interventions = []
    for intervention in arms.get("interventions", []):
        interventions.append({
            "name": intervention.get("name", ""),
            "type": intervention.get("type", ""),
            "description": intervention.get("description", ""),
        })

    # Extract outcome measures
    primary_outcomes = []
    for outcome in outcomes.get("primaryOutcomes", []):
        primary_outcomes.append({
            "measure": outcome.get("measure", ""),
            "timeFrame": outcome.get("timeFrame", ""),
            "description": outcome.get("description", ""),
        })

    return {
        "nct_id": ident.get("nctId", ""),
        "brief_title": ident.get("briefTitle", ""),
        "official_title": ident.get("officialTitle", ""),
        "brief_summary": desc.get("briefSummary", ""),
        "detailed_description": desc.get("detailedDescription", ""),
        "overall_status": status_module.get("overallStatus", ""),
        "phase": design.get("phases", []),
        "study_type": design.get("studyType", ""),
        "enrollment": design.get("enrollmentInfo", {}).get("count", 0),
        "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
        "interventions": interventions,
        "eligibility": {
            "criteria": eligibility.get("eligibilityCriteria", ""),
            "gender": eligibility.get("sex", ""),
            "min_age": eligibility.get("minimumAge", ""),
            "max_age": eligibility.get("maximumAge", ""),
            "healthy_volunteers": eligibility.get("healthyVolunteers", False),
        },
        "locations": locations,
        "primary_outcomes": primary_outcomes,
        "sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
        "collaborators": [
            c.get("name", "")
            for c in sponsor.get("collaborators", [])
        ],
        "start_date": status_module.get("startDateStruct", {}).get("date", ""),
        "completion_date": status_module.get("completionDateStruct", {}).get("date", ""),
        "last_updated": status_module.get("lastUpdateSubmitDate", ""),
    }


def save_results(all_trials: dict):
    """Save both raw and processed trial data."""

    # Save raw data (complete API responses)
    raw_file = OUTPUT_DIR / "raw_api_responses.json"
    with open(raw_file, "w") as f:
        json.dump(list(all_trials.values()), f, indent=2)
    print(f"\nSaved raw data: {raw_file} ({len(all_trials)} trials)")

    # Save processed summaries (structured for RAG ingestion)
    summaries = []
    for nct_id, study in all_trials.items():
        summary = extract_trial_summary(study)
        summaries.append(summary)

        # Also save individual trial files for S3 upload
        trial_file = OUTPUT_DIR / f"{nct_id}.json"
        with open(trial_file, "w") as f:
            json.dump(summary, f, indent=2)

    # Save combined summaries
    summaries_file = OUTPUT_DIR / "all_trials_processed.json"
    with open(summaries_file, "w") as f:
        json.dump(summaries, f, indent=2)
    print(f"Saved processed data: {summaries_file}")

    # Save collection metadata
    metadata = {
        "collection_date": datetime.now().isoformat(),
        "total_trials": len(all_trials),
        "target_states": TARGET_STATES,
        "cancer_queries": CANCER_QUERIES,
        "trials_by_status": {},
        "trials_by_phase": {},
        "trials_in_delaware": 0,
    }

    for summary in summaries:
        status = summary["overall_status"]
        metadata["trials_by_status"][status] = metadata["trials_by_status"].get(status, 0) + 1

        for phase in summary["phase"]:
            metadata["trials_by_phase"][phase] = metadata["trials_by_phase"].get(phase, 0) + 1

        if any(loc["state"] == "Delaware" for loc in summary["locations"]):
            metadata["trials_in_delaware"] += 1

    meta_file = OUTPUT_DIR / "collection_metadata.json"
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata: {meta_file}")

    # Print summary
    print(f"\n{'='*50}")
    print(f"COLLECTION SUMMARY")
    print(f"{'='*50}")
    print(f"Total unique trials: {len(all_trials)}")
    print(f"Trials with Delaware locations: {metadata['trials_in_delaware']}")
    print(f"\nBy status:")
    for status, count in sorted(metadata["trials_by_status"].items(), key=lambda x: -x[1]):
        print(f"  {status}: {count}")
    print(f"\nBy phase:")
    for phase, count in sorted(metadata["trials_by_phase"].items()):
        print(f"  {phase}: {count}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("TrialScope DE — Clinical Trials Data Collection")
    print("=" * 50)
    print(f"Target states: {', '.join(TARGET_STATES)}")
    print(f"Cancer queries: {len(CANCER_QUERIES)}")
    print()

    all_trials = collect_all_trials()
    save_results(all_trials)

    print("\nDone! Next step: python scripts/upload_to_s3.py")
