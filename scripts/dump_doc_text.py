import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
doc_id = sys.argv[1]

with (ROOT / "data" / "processed" / "chunks.jsonl").open(encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        if c["document_id"] == doc_id:
            print(f"--- {c['chunk_id']} (p.{c['page']}) ---")
            print(c["text"])
            print()
