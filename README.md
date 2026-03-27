# TrialScope Delaware 

**An Agentic RAG-powered Clinical Trial Navigator for Delaware Cancer Patients & Researchers**

## The Problem

Delaware ranks among the highest U.S. states for cancer incidence and holds the nation's highest rate of triple-negative breast cancer (TNBC). The state actually has strong clinical trial infrastructure — the Helen F. Graham Cancer Center enrolls ~35% of its cancer patients into trials, well above the national average, and 100+ trials run statewide.

**So trials exist. The problem is the gap between availability and awareness.**

- **Information gap**: Only ~15% of cancer survivors report that clinical trials were discussed with them by their doctor. Most patients never learn about trials they could qualify for.
- **Navigation complexity**: Trial protocols, eligibility criteria, and FDA drug data are buried in thousands of dense, technical documents that patients and even many providers struggle to parse.
- **Access barriers**: Even when patients know about trials, understanding complex eligibility rules, comparing treatment options, and navigating enrollment logistics (travel, costs, time) remain significant hurdles — especially for underserved communities.
- **Racial disparities persist**: Non-Hispanic Black Delawareans face significantly higher mortality for breast and prostate cancers, and geographic hotspots in Wilmington and Middletown show elevated rates of advanced breast cancer linked to screening gaps.

**TrialScope Delaware bridges these gaps** by ingesting clinical trial protocols, FDA drug reviews, Delaware public health reports, and published research — then making all of it searchable through plain-English questions with clear, cited answers.

## What It Does

**For Patients:**
- "Are there breast cancer trials recruiting near Newark, DE?"
- "I'm 55 with stage III colon cancer — which trials might I qualify for?"
- "Explain the side effects of pembrolizumab in simple terms"
- "What's the difference between the immunotherapy options available to me?"

**For Clinicians:**
- "Compare immunotherapy outcomes across Phase 3 lung cancer trials in the Mid-Atlantic"
- "Which TNBC trials are currently enrolling and what are their eligibility criteria?"
- "Summarize the latest ADC breast cancer trial results for Trodelvy vs Enhertu"

**For Public Health Researchers:**
- "How do Delaware's cancer mortality trends for African Americans compare to national averages?"
- "What screening gaps exist in Wilmington's breast cancer hotspots?"
- "Summarize the Route 9 Corridor cancer data findings"

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   React +   │────▶│   FastAPI     │────▶│   AWS Bedrock    │
│  Tailwind   │     │   Backend     │     │   (Claude Agent) │
│  Frontend   │     │              │     │                  │
└─────────────┘     └──────┬───────┘     └────────┬─────────┘
                           │                      │
                    ┌──────▼───────┐        ┌─────▼──────────┐
                    │     S3       │        │   OpenSearch    │
                    │  (Documents) │        │  (Hybrid Search)│
                    └──────┬───────┘        └────────────────┘
                           │
                    ┌──────▼───────┐     ┌──────────────────┐
                    │   Lambda +   │────▶│  Titan Embeddings │
                    │   Textract   │     │  (via Bedrock)    │
                    │  (Extraction)│     └──────────────────┘
                    └──────────────┘
```

## Key Features

- **Agentic RAG** — Multi-step reasoning: the AI plans which tools to call (search papers, search web, analyze figures), executes, observes results, and re-plans until it has a comprehensive answer
- **Hybrid Retrieval** — Combines BM25 keyword search + semantic vector search via OpenSearch for superior accuracy on medical terminology
- **Multi-Modal** — Extracts and understands tables, charts, and figures from PDFs using AWS Textract + Claude Vision
- **Conversational Memory** — DynamoDB-backed session history for natural follow-up questions
- **Real-Time Web Search** — Pulls fresh trials from ClinicalTrials.gov API and latest research from Semantic Scholar
- **Full Citations** — Every answer links back to the exact source document, section, and page number
- **Delaware-Focused** — Curated dataset of Delaware cancer statistics, local trial data, and regional health disparity reports

## Dataset (Collected)

| Source | Records | Description |
|--------|---------|-------------|
| ClinicalTrials.gov | 10,980 trials (1,107 DE-specific) | Trial protocols, eligibility, outcomes, locations for DE/MD/PA/NJ |
| PubMed | 937 articles | Research across TNBC, immunotherapy, disparities, screening, biomarkers |
| Delaware DPH | 11 reports | Annual cancer incidence/mortality, census tract hotspots, disparities |
| FDA openFDA | 10 drug profiles | Labels, adverse events for major cancer drugs (Keytruda, Trodelvy, etc.) |
| Semantic Scholar | Real-time | Latest research via API (queried during agentic search) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Tailwind CSS, Vite, Framer Motion |
| Backend | Python, FastAPI |
| LLM & Embeddings | AWS Bedrock (Claude, Titan Embeddings V2) |
| Agent Orchestration | AWS Bedrock Agents |
| Vector + Keyword Search | Amazon OpenSearch Serverless (hybrid BM25 + vector) |
| Document Storage | Amazon S3 |
| PDF Extraction | Amazon Textract |
| Conversation Memory | Amazon DynamoDB |
| API Gateway | AWS API Gateway + Lambda |
| Real-Time Data | ClinicalTrials.gov API, Semantic Scholar API, PubMed API |
| Deployment | Vercel (frontend), AWS (backend) |

## Project Structure

```
trialscope-de/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── services/     # Business logic (ingestion, retrieval, agent)
│   │   ├── models/       # Pydantic models & schemas
│   │   └── utils/        # AWS clients, chunking, helpers
│   ├── scripts/          # Data collection & ingestion scripts
│   │   ├── collect_trials.py        # ClinicalTrials.gov fetcher
│   │   ├── collect_fda_reviews.py   # FDA drug data fetcher
│   │   ├── collect_de_reports.py    # Delaware DPH report downloader
│   │   ├── collect_pubmed.py        # PubMed article fetcher
│   │   └── upload_to_s3.py          # S3 upload with metadata
│   └── tests/
├── frontend/
│   └── src/
├── data/                 # Collected data (see Dataset section)
├── docs/                 # Architecture & design docs
├── infrastructure/       # AWS CDK / CloudFormation templates
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS Account with Bedrock access enabled (us-east-1)
- AWS CLI configured

### Data Collection
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python scripts/collect_trials.py          # ~10,980 trials
python scripts/collect_fda_reviews.py     # 10 cancer drug profiles
python scripts/collect_de_reports.py      # 11 Delaware cancer reports
python scripts/collect_pubmed.py          # ~937 research articles
python scripts/upload_to_s3.py            # Upload all to S3
```

## Why Delaware?

This isn't a generic tool — it's built for a specific community facing specific challenges:

- **Highest TNBC rate nationally** — Delaware leads the nation in incidence of triple-negative breast cancer, an aggressive subtype that doesn't respond to standard hormonal therapies
- **Geographic hotspots identified** — ChristianaCare research pinpointed Wilmington and Middletown as hotspots for advanced breast cancer, linked to screening gaps and higher TNBC prevalence
- **Persistent racial disparities** — Non-Hispanic Black Delawareans face significantly higher mortality for breast and prostate cancers
- **Strong trial infrastructure, weak information flow** — Delaware has above-average trial enrollment capacity, but most patients are never informed about available trials
- **The Big 4** — Breast, colorectal, lung, and prostate cancers account for 49% of all diagnoses and 49% of all cancer deaths in the state

TrialScope exists to turn Delaware's clinical trial data from inaccessible technical documents into actionable knowledge for patients, clinicians, and researchers.

## License

MIT


