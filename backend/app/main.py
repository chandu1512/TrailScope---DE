from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json, os, time, numpy as np
from pathlib import Path
import boto3, faiss
from groq import Groq

app = FastAPI(title="TrialScope DE API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DATA_DIR = Path(__file__).parent.parent / "data"

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load FAISS index on startup
INDEX_DIR = DATA_DIR / "faiss_index"
index = faiss.read_index(str(INDEX_DIR / "trialscope.index"))
with open(INDEX_DIR / "chunks_metadata.json") as f:
    chunks = json.load(f)
print(f"Loaded {index.ntotal} vectors")

class Query(BaseModel):
    question: str

def get_embedding(text):
    if len(text) > 30000: text = text[:30000]
    response = bedrock.invoke_model(modelId="amazon.titan-embed-text-v2:0", contentType="application/json", accept="application/json",
        body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}))
    return json.loads(response["body"].read())["embedding"]

@app.get("/health")
def health():
    return {"status": "ok", "vectors": index.ntotal}

@app.post("/ask")
def ask(query: Query):
    start = time.time()
    qv = get_embedding(query.question)
    scores, indices = index.search(np.array([qv], dtype="float32"), 8)
    results = [{**chunks[idx], "score": float(s)} for s, idx in zip(scores[0], indices[0]) if idx < len(chunks)]
    
    context_parts = []
    sources = []
    for chunk in results:
        meta = chunk.get("metadata", {})
        st = meta.get("source_type", "")
        if st == "clinical_trial":
            label = f"[Trial: {meta.get('nct_id','')}]"
            sources.append({"type": "trial", "id": meta.get("nct_id",""), "title": meta.get("title",""), "score": chunk["score"]})
        elif st == "pubmed":
            label = f"[PubMed: {meta.get('pmid','')}]"
            sources.append({"type": "pubmed", "id": meta.get("pmid",""), "title": meta.get("title",""), "score": chunk["score"]})
        else:
            label = "[Source]"
            sources.append({"type": "other", "score": chunk["score"]})
        context_parts.append(f"{label}\n{chunk.get('text','')}")
    
    context = "\n\n---\n\n".join(context_parts)
    prompt = f"""You are TrialScope DE, a clinical trial navigator for Delaware cancer patients.
Use ONLY the context below. Cite sources with [Trial: NCTxx] or [PubMed: xx].
Be specific and helpful. Use plain language.

Context:
{context}

Question: {query.question}"""

    response = groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=2000)
    answer = response.choices[0].message.content
    
    return {"answer": answer, "sources": sources[:5], "time": round(time.time() - start, 2)}
