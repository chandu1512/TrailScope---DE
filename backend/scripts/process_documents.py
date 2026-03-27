"""
TrialScope DE - Phase 2: Document Processor
Converts raw data into semantic chunks ready for embedding.
"""
import json
import uuid
import re
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "processed_chunks"
OUTPUT_DIR.mkdir(exist_ok=True)


def process_trial(trial_data):
    chunks = []
    protocol = trial_data.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    nct_id = ident.get("nctId", "unknown")
    title = ident.get("briefTitle", "Untitled")
    status_mod = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    desc = protocol.get("descriptionModule", {})
    elig = protocol.get("eligibilityModule", {})
    outcomes = protocol.get("outcomesModule", {})
    arms = protocol.get("armsInterventionsModule", {})
    contacts = protocol.get("contactsLocationsModule", {})
    conditions = protocol.get("conditionsModule", {})
    sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
    
    base = {"source_type": "clinical_trial", "nct_id": nct_id, "title": title}
    
    # Overview chunk
    phase = ", ".join(design.get("phases", ["N/A"]))
    status = status_mod.get("overallStatus", "Unknown")
    sponsor = sponsor_mod.get("leadSponsor", {}).get("name", "N/A")
    conds = ", ".join(conditions.get("conditions", []))
    
    chunks.append({"chunk_id": f"{nct_id}_overview", "section": "overview",
        "text": f"Trial: {title}\nNCT ID: {nct_id}\nPhase: {phase}\nStatus: {status}\nSponsor: {sponsor}\nConditions: {conds}",
        "metadata": {**base, "phase": phase, "status": status}})
    
    # Description chunk
    brief = desc.get("briefSummary", "")
    if brief:
        chunks.append({"chunk_id": f"{nct_id}_description", "section": "description",
            "text": f"{title} ({nct_id})\n\n{brief}", "metadata": base})
    
    # Eligibility chunk
    elig_text = elig.get("eligibilityCriteria", "")
    if elig_text:
        min_age = elig.get("minimumAge", "N/A")
        max_age = elig.get("maximumAge", "N/A")
        sex = elig.get("sex", "All")
        chunks.append({"chunk_id": f"{nct_id}_eligibility", "section": "eligibility",
            "text": f"Eligibility for {title} ({nct_id})\nAge: {min_age} to {max_age}\nSex: {sex}\n\n{elig_text}",
            "metadata": {**base, "min_age": min_age, "max_age": max_age, "sex": sex}})
    
    # Interventions chunk
    interventions = arms.get("interventions", [])
    if interventions:
        lines = [f"Interventions for {title} ({nct_id}):"]
        for inv in interventions:
            lines.append(f"- {inv.get('type','')}: {inv.get('name','')} - {inv.get('description','')}")
        chunks.append({"chunk_id": f"{nct_id}_interventions", "section": "interventions",
            "text": "\n".join(lines), "metadata": base})
    
    # Locations chunk
    locations = contacts.get("locations", [])
    if locations:
        de_sites = [l for l in locations if l.get("state","").lower() in ["delaware","de"]]
        lines = [f"Locations for {title} ({nct_id}):"]
        for loc in locations[:15]:
            lines.append(f"- {loc.get('facility','')}, {loc.get('city','')}, {loc.get('state','')} {loc.get('zip','')}")
        chunks.append({"chunk_id": f"{nct_id}_locations", "section": "locations",
            "text": "\n".join(lines), "metadata": {**base, "has_de_site": len(de_sites) > 0}})
    
    return chunks


def process_all_trials():
    trials_dir = DATA_DIR / "raw_trials"
    files = list(trials_dir.glob("NCT*.json"))
    print(f"Processing {len(files)} clinical trials...")
    
    all_chunks = []
    for i, f in enumerate(files):
        if (i+1) % 2000 == 0:
            print(f"  {i+1}/{len(files)} trials processed...")
        try:
            with open(f) as fp:
                data = json.load(fp)
            all_chunks.extend(process_trial(data))
        except Exception as e:
            pass
    
    out = OUTPUT_DIR / "trial_chunks.json"
    with open(out, "w") as fp:
        json.dump({"total_chunks": len(all_chunks), "chunks": all_chunks}, fp)
    print(f"  Generated {len(all_chunks)} trial chunks -> {out}")
    return len(all_chunks)


def process_all_pubmed():
    pubmed_dir = DATA_DIR / "pubmed"
    files = [f for f in pubmed_dir.glob("*.json") if "metadata" not in f.name]
    print(f"Processing {len(files)} PubMed files...")
    
    all_chunks = []
    for f in files:
        try:
            with open(f) as fp:
                data = json.load(fp)
            articles = data if isinstance(data, list) else data.get("articles", [data])
            for art in articles:
                pmid = art.get("pmid", "unknown")
                title = art.get("title", "")
                abstract = art.get("abstract", "")
                authors = ", ".join(art.get("authors", [])[:5])
                if abstract:
                    all_chunks.append({
                        "chunk_id": f"pubmed_{pmid}",
                        "section": "abstract",
                        "text": f"{title}\nAuthors: {authors}\n\n{abstract}",
                        "metadata": {"source_type": "pubmed", "pmid": pmid, "title": title,
                                     "category": art.get("category", "general")}
                    })
        except Exception:
            pass
    
    out = OUTPUT_DIR / "pubmed_chunks.json"
    with open(out, "w") as fp:
        json.dump({"total_chunks": len(all_chunks), "chunks": all_chunks}, fp)
    print(f"  Generated {len(all_chunks)} PubMed chunks -> {out}")
    return len(all_chunks)


def process_all_fda():
    fda_dir = DATA_DIR / "fda_reviews"
    print("Processing FDA drug data...")
    
    all_chunks = []
    for f in fda_dir.glob("*.json"):
        try:
            with open(f) as fp:
                data = json.load(fp)
            drugs = data.get("drugs", [data]) if "drugs" in data else [data]
            for drug in drugs:
                name = drug.get("drug_name", drug.get("name", "Unknown"))
                for section, text in drug.get("label_sections", {}).items():
                    if text and len(str(text)) > 20:
                        all_chunks.append({
                            "chunk_id": f"fda_{name}_{section}".replace(" ","_").lower(),
                            "section": section,
                            "text": f"{name} - {section.replace('_',' ').title()}\n\n{text}",
                            "metadata": {"source_type": "fda_drug", "drug_name": name, "section": section}
                        })
        except Exception:
            pass
    
    out = OUTPUT_DIR / "fda_chunks.json"
    with open(out, "w") as fp:
        json.dump({"total_chunks": len(all_chunks), "chunks": all_chunks}, fp)
    print(f"  Generated {len(all_chunks)} FDA chunks -> {out}")
    return len(all_chunks)


if __name__ == "__main__":
    print("=" * 50)
    print("TrialScope DE - Phase 2: Document Processing")
    print("=" * 50)
    
    total = 0
    total += process_all_trials()
    total += process_all_pubmed()
    total += process_all_fda()
    
    print(f"\nTotal chunks generated: {total}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("Next step: Phase 3 - Embed chunks and index in OpenSearch")
