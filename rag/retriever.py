"""FAISS retriever for similar bug fix examples."""

import json
import os
import numpy as np
import faiss
from rag.embedder import embed_text, EMBED_DIM

INDEX_PATH = None
DATA_PATH = None


def set_paths(index_dir: str) -> None:
    global INDEX_PATH, DATA_PATH
    INDEX_PATH = os.path.join(index_dir, "index.faiss")
    DATA_PATH = os.path.join(index_dir, "codexglue_refinement.jsonl")


def build_index(data_file: str, index_file: str) -> int:
    """Build FAISS index from JSONL data file."""
    items = []
    with open(data_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    texts = [item.get("buggy", "") or item.get("buggy_code", "") for item in items]
    from rag.embedder import embed_batch, set_corpus_idf
    set_corpus_idf(texts)
    embeddings = embed_batch(texts)

    index = faiss.IndexFlatL2(EMBED_DIM)
    index.add(embeddings)
    faiss.write_index(index, index_file)

    # Save items for retrieval
    meta_file = index_file.replace(".faiss", "_meta.jsonl")
    with open(meta_file, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    return len(items)


def retrieve(query: str, k: int = 3) -> list[dict]:
    """Retrieve top-k similar bug-fix examples."""
    if not os.path.exists(INDEX_PATH):
        return []

    index = faiss.read_index(INDEX_PATH)
    query_vec = embed_text(query).reshape(1, -1)
    distances, indices = index.search(query_vec, k)

    meta_file = INDEX_PATH.replace(".faiss", "_meta.jsonl")
    if not os.path.exists(meta_file):
        return []

    with open(meta_file, "r", encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(all_items):
            item = dict(all_items[idx])
            item["_distance"] = float(distances[0][i])
            results.append(item)
    return results


def format_few_shot(examples: list[dict]) -> str:
    """Format retrieved examples as few-shot prompt."""
    if not examples:
        return ""
    parts = ["参考以下类似bug的修复方式：\n"]
    for i, ex in enumerate(examples, 1):
        buggy = ex.get("buggy", ex.get("buggy_code", ""))
        fixed = ex.get("fixed", ex.get("fixed_code", ""))
        parts.append(f"--- 案例 {i} ---")
        parts.append(f"修复前: {buggy[:500]}")
        parts.append(f"修复后: {fixed[:500]}")
        parts.append("")
    return "\n".join(parts)
