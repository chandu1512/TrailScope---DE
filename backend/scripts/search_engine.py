import json, os, sys, time
import numpy as np
from pathlib import Path
import boto3
import faiss
from groq import Groq

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

DATA_DIR = Path(__file__).parent.parent / "data"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
INDEX_DIR = DATA_DIR / "faiss_index"
INDEX_DIR.mkdir(exist_ok=True)

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_embedding(text):
    if len(text) > 30000: text = text[:30000]
    try:
        response = bedrock.invoke_model(modelId=EMBEDDING_MODEL, contentType="application/json", accept="application/json",
            body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}))
        return json.loads(response["body"].read())["embedding"]
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

def load_faiss_index():
    index_path = INDEX_DIR / "trialscope.index"
    meta_path = INDEX_DIR / "chunks_metadata.json"
    if not index_path.exists():
        print("Building FAISS index...")
        all_chunks, all_vectors = [], []
        for emb_file in EMBEDDINGS_DIR.glob("*_embeddings.json"):
            print(f"  Loading {emb_file.name}...")
            with open(emb_file) as f:
                data = json.load(f)
            for chunk in data.get("chunks", []):
                if "embedding" in chunk:
                    all_vectors.append(chunk["embedding"])
                    all_chunks.append({k: v for k, v in chunk.items() if k != "embedding"})
        vectors = np.array(all_vectors, dtype="float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(index_path))
        with open(meta_path, "w") as f: json.dump(all_chunks, f)
        print(f"  Built index: {index.ntotal} vectors")
        return index, all_chunks
    index = faiss.read_index(str(index_path))
    with open(meta_path) as f: chunks = json.load(f)
    print(f"Loaded FAISS index: {index.ntotal} vectors")
    return index, chunks

def search(query, index, chunks, top_k=8):
    qv = get_embedding(query)
    if not qv: return []
    scores, indices = index.search(np.array([qv], dtype="float32"), top_k)
    return [{**chunks[idx], "score": float(s)} for s, idx in zip(scores[0], indices[0]) if idx < len(chunks)]

def ask_llm(query, results):
    context_parts = []
    for chunk in results:
        meta = chunk.get("metadata", {})
        st = meta.get("source_type", "")
        if st == "clinical_trial": label = f"[Trial: {meta.get('nct_id','')}]"
        elif st == "pubmed": label = f"[PubMed: {meta.get('pmid','')}]"
        elif st == "fda_drug": label = f"[FDA: {meta.get('drug_name','')}]"
        else: label = "[Source]"
        context_parts.append(f"{label}\n{chunk.get('text','')}")
    context = "\n\n---\n\n".join(context_parts)
    prompt = f"""You are TrialScope DE, a clinical trial navigator for Delaware cancer patients.
Use ONLY the context below. Cite sources with [Trial: NCTxx] or [PubMed: xx] labels.
Be specific and helpful for cancer patients in Delaware.

Context:
{context}

Question: {query}"""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print("=" * 60)
    print("TrialScope DE - Clinical Trial Navigator")
    print("Powered by FAISS + Groq Llama 3.3 70B")
    print("=" * 60)
    index, chunks = load_faiss_index()
    if not index: sys.exit(1)
    print("\nAsk me about Delaware cancer trials! (type 'quit' to exit)\n")
    while True:
        query = input("Your question: ").strip()
        if query.lower() in ["quit","exit","q"]: break
        if not query: continue
        print("\nSearching...")
        start = time.time()
        results = search(query, index, chunks)
        print(f"Found {len(results)} sources ({time.time()-start:.2f}s)")
        for r in results[:5]:
            m = r.get("metadata",{})
            st = m.get("source_type","")
            if st == "clinical_trial": print(f"  [{r['score']:.3f}] Trial: {m.get('nct_id','')} - {m.get('title','')[:50]}")
            elif st == "pubmed": print(f"  [{r['score']:.3f}] PubMed: {m.get('title','')[:50]}")
        print("\nGenerating answer...")
        answer = ask_llm(query, results)
        print(f"\n{'='*60}\nANSWER:\n{'='*60}\n{answer}\n")
