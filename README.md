# TrialScope Delaware

**A Retrieval-Augmented Generation (RAG) clinical trial navigator for Delaware cancer patients, clinicians, and researchers.**

Ask a plain-English question and get a clear, cited answer drawn from real clinical trial protocols, research papers, FDA drug data, and Delaware public-health reports.

## The problem

Delaware ranks among the highest U.S. states for cancer incidence and holds the nation's highest rate of triple-negative breast cancer (TNBC). The state actually has strong clinical trial infrastructure, but there's a gap between trials existing and patients hearing about them.

- **Information gap:** only about 15% of cancer survivors report that clinical trials were ever discussed with them.
- **Complexity:** trial protocols, eligibility rules, and FDA drug data are buried in thousands of dense technical documents that patients and even many providers struggle to parse.

TrialScope bridges that gap by making all of it searchable through plain-English questions with clear, cited answers.

## What it does

Patients: "Are there breast cancer trials recruiting near Newark, DE?" · "I'm 55 with stage III colon cancer, which trials might I qualify for?" · "Explain the side effects of pembrolizumab in plain terms."

Clinicians: "Which TNBC trials are currently enrolling and what are their eligibility criteria?"

Every answer cites its sources by trial NCT ID or PubMed ID.

## How it works (architecture)

TrialScope is a single-pass RAG pipeline. In plain terms: it turns the documents into searchable vectors ahead of time, and at question time it finds the most relevant pieces and asks a language model to answer using only those pieces.

```
   React + Tailwind frontend
            |
            v
      FastAPI backend
            |
   ┌────────┴─────────┐
   |                  |
   v                  v
Titan Embeddings   FAISS index
(AWS Bedrock)      (vector search)
   |                  |
   └────────┬─────────┘
            v
   top-8 relevant chunks
   (labeled by source type)
            |
            v
   Groq / Llama 3.3 70B
   (generates a cited answer)
            |
            v
   Answer + sources + latency
```

**Step by step:**

1. **Offline ingestion.** Documents from ClinicalTrials.gov, PubMed, FDA, and Delaware DPH are chunked with semantic chunking that preserves each trial's structure (eligibility, interventions, locations as distinct pieces). Each chunk is embedded into a 1024-dimension vector using AWS Bedrock Titan Embeddings V2 and stored in a FAISS index, alongside a metadata file recording each chunk's source type, NCT ID / PubMed ID, and title.

2. **At query time**, the FastAPI `/ask` endpoint:
   - embeds the user's question with Titan Embeddings (Bedrock),
   - runs a similarity search over the FAISS index and takes the top 8 chunks,
   - labels each retrieved chunk by source type (`[Trial: NCT...]` or `[PubMed: ...]`) so trials are clearly distinguished and citable,
   - builds a grounded prompt instructing the model to use only the retrieved context and to cite sources,
   - calls Groq / Llama 3.3 70B to generate the answer,
   - returns the answer, the top 5 sources, and the response latency.

**Grounding and citations.** The prompt explicitly tells the model to answer only from the retrieved context and to cite each claim with its trial NCT ID or PubMed ID. This keeps answers traceable and reduces hallucination — the model works from real retrieved documents, not its own memory.

## Dataset

| Source | Records | Description |
|---|---|---|
| ClinicalTrials.gov | 10,980 trials (1,107 DE-specific) | Protocols, eligibility, outcomes, locations for DE/MD/PA/NJ |
| PubMed | 937 articles | Research across TNBC, immunotherapy, disparities, screening |
| Delaware DPH | 11 reports | Cancer incidence/mortality, census-tract hotspots |
| FDA openFDA | 10 drug profiles | Labels and adverse events for major cancer drugs |

Processed into roughly 34,690 semantic chunks, embedded with Titan Embeddings V2 (1024-dim) and indexed in FAISS for sub-second similarity search.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React, Tailwind CSS, Vite |
| Backend | Python, FastAPI |
| Embeddings | AWS Bedrock — Titan Embeddings V2 (1024-dim) |
| Vector search | FAISS (similarity search) |
| LLM | Groq / Llama 3.3 70B |
| Data sources | ClinicalTrials.gov API, PubMed, FDA openFDA, Delaware DPH |

## Retrieval design notes

- **Semantic chunking that preserves trial structure.** Early on, retrieval kept surfacing research papers instead of the actual trials patients needed. The fix was to chunk each trial so its eligibility criteria and locations stay as distinct, searchable pieces, and to label chunks by source type so clinical questions surface real trial data with their NCT IDs. The lesson: retrieval quality is usually fixed in how you structure and retrieve the data, not by prompting the model harder.
- **Grounded generation.** The model is instructed to answer only from retrieved context and to cite every claim, which keeps answers traceable to a specific trial or paper.

## Project structure

```
trialscope-de/
├── backend/          # FastAPI app, ingestion + retrieval
│   ├── app/          # API, services, models
│   ├── scripts/      # data collection (trials, PubMed, FDA, DPH)
│   └── data/         # FAISS index + chunk metadata
├── frontend/         # React + Tailwind chat interface
└── README.md
```

## Running it

Prerequisites: Python 3.11+, Node 18+, an AWS account with Bedrock access (us-east-1) for Titan embeddings, and a Groq API key.

```
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# set AWS credentials and GROQ_API_KEY in your environment
uvicorn app.main:app --reload
```
---

Built by Chandra Darapaneni.
