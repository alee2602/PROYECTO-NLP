import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

chunks_by_doc = {}
with (ROOT / "data" / "processed" / "chunks.jsonl").open(encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        chunks_by_doc.setdefault(c["document_id"], []).append(c)

documents = json.loads((ROOT / "data" / "processed" / "documents.json").read_text(encoding="utf-8"))
titles = {d["document_id"]: d["title"] for d in documents}

for doc_id in sorted(chunks_by_doc):
    chunks = chunks_by_doc[doc_id]
    print(f"=== {doc_id}: {titles.get(doc_id)} ({len(chunks)} chunks) ===")
    for c in chunks[:3]:
        print(f"  p.{c['page']} [{c['chunk_id']}]: {c['text'][:250]}")
    print()
