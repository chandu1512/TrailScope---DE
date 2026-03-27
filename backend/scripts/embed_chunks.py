import json, os, time, sys
from pathlib import Path
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "trialscope-de-documents")

DATA_DIR = Path(__file__).parent.parent / "data"
CHUNKS_DIR = DATA_DIR / "processed_chunks"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
EMBEDDINGS_DIR.mkdir(exist_ok=True)

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)

def get_embedding(text):
    if len(text) > 30000:
        text = text[:30000]
    try:
        response = bedrock.invoke_model(
            modelId=EMBEDDING_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}),
        )
        result = json.loads(response["body"].read())
        return result["embedding"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ThrottlingException":
            print("    Rate limited, waiting 5s...")
            time.sleep(5)
            return get_embedding(text)
        print(f"    Error: {e}")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None

def embed_chunks_file(input_path, output_path):
    print(f"\nEmbedding: {input_path.name}")
    with open(input_path) as f:
        data = json.load(f)
    chunks = data.get("chunks", [])
    print(f"  Total chunks: {len(chunks)}")
    
    embedded = []
    if output_path.exists():
        with open(output_path) as f:
            embedded = json.load(f).get("chunks", [])
        print(f"  Already done: {len(embedded)}, resuming...")
    
    done_ids = {c["chunk_id"] for c in embedded}
    remaining = [c for c in chunks if c["chunk_id"] not in done_ids]
    print(f"  Remaining: {len(remaining)}")
    
    if not remaining:
        return len(embedded)
    
    start = time.time()
    for i, chunk in enumerate(remaining):
        text = chunk.get("text", "")
        if len(text.strip()) < 10:
            continue
        emb = get_embedding(text)
        if emb:
            chunk["embedding"] = emb
            embedded.append(chunk)
        if (i+1) % 50 == 0:
            elapsed = time.time() - start
            rate = (i+1)/elapsed
            eta = (len(remaining)-i-1)/rate/60 if rate > 0 else 0
            print(f"  {i+1}/{len(remaining)} [{rate:.1f}/s, ~{eta:.1f}min left]")
            with open(output_path, "w") as f:
                json.dump({"metadata": {"model": EMBEDDING_MODEL_ID, "total": len(embedded)}, "chunks": embedded}, f)
        time.sleep(0.05)
    
    with open(output_path, "w") as f:
        json.dump({"metadata": {"model": EMBEDDING_MODEL_ID, "total": len(embedded), "date": datetime.now().isoformat()}, "chunks": embedded}, f)
    print(f"  Done! {len(embedded)} embedded in {(time.time()-start)/60:.1f}min")
    return len(embedded)

if __name__ == "__main__":
    print("=" * 50)
    print("TrialScope DE - Phase 3: Embeddings")
    print("=" * 50)
    
    print("\nTesting Bedrock...")
    test = get_embedding("test")
    if test:
        print(f"  Connected! Dimensions: {len(test)}")
    else:
        print("  ERROR: Cannot connect to Bedrock!")
        sys.exit(1)
    
    total = 0
    for name in ["trial_chunks", "pubmed_chunks", "fda_chunks"]:
        inp = CHUNKS_DIR / f"{name}.json"
        out = EMBEDDINGS_DIR / f"{name.replace('_chunks','')}_embeddings.json"
        if inp.exists():
            total += embed_chunks_file(inp, out)
    
    print(f"\nTotal embedded: {total}")
    print("Next: Index in OpenSearch")
