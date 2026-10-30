"""Local dense embeddings with exact, owner-selected source references.

Unlike keyword search, query and source text are encoded by the same trained
sentence model. Vectors are stored in the existing encrypted document store.
"""
import base64
from functools import lru_cache
import hashlib
import os
import re

import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MAX_SEGMENTS = 30000


class SemanticUnavailable(ValueError):
    pass


@lru_cache(maxsize=1)
def encoder():
    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=MODEL_NAME, threads=2, cuda=False,
                         cache_dir=os.path.join(os.getenv("STUDY_MODEL_DIR", ".study-models"), "embeddings"),
                         local_files_only=os.getenv("STUDY_MODELS_OFFLINE", "false").lower() == "true")


def fingerprint(passages):
    digest = hashlib.sha256(MODEL_NAME.encode())
    for passage in passages:
        digest.update(passage["id"].encode() + b"\x00" + passage["text"].encode() + b"\x00")
    return digest.hexdigest()


def build_index(passages: list[dict], model=None) -> dict:
    segments, texts = [], []
    for passage in passages:
        text = passage["text"]
        for start in range(0, len(text), 800):
            end = min(len(text), start + 800)
            if text[start:end].strip():
                segments.append({"source_id": passage["id"], "start": start, "end": end})
                texts.append(text[start:end])
    if not segments or len(segments) > MAX_SEGMENTS:
        raise SemanticUnavailable("This material exceeds the semantic indexing limit or has no readable passages.")
    try:
        vectors = np.asarray(list((model or encoder()).passage_embed(texts, batch_size=32)), dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[0] != len(segments) or not 1 <= vectors.shape[1] <= 2048 or not np.isfinite(vectors).all():
            raise ValueError("Invalid embedding dimensions")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise ValueError("Zero embedding")
        vectors = (vectors / norms).astype("<f2")
        return {"model": MODEL_NAME, "fingerprint": fingerprint(passages), "segments": segments,
                "shape": list(vectors.shape), "vectors": base64.b64encode(vectors.tobytes()).decode()}
    except SemanticUnavailable:
        raise
    except Exception as error:
        raise SemanticUnavailable("The local semantic model is unavailable. Retry after the server's models are prepared.") from error


def search(passages: list[dict], index: dict, query: str, *, limit=5, threshold=0.64, model=None) -> list[dict]:
    if not 2 <= len(query.strip()) <= 300 or not 1 <= limit <= 100 or not -1 <= threshold <= 1:
        raise ValueError("Enter a search query of 2–300 characters and a valid result limit.")
    try:
        shape = index["shape"]
        if len(shape) != 2 or not 1 <= shape[0] <= MAX_SEGMENTS or not 1 <= shape[1] <= 2048:
            raise ValueError("Invalid index dimensions")
        raw = base64.b64decode(index["vectors"], validate=True)
        if len(raw) != shape[0] * shape[1] * 2 or len(index["segments"]) != shape[0]:
            raise ValueError("Invalid index payload")
        vectors = np.frombuffer(raw, dtype="<f2").reshape(shape).astype(np.float32)
        query_vectors = list((model or encoder()).query_embed(query.strip()))
        if len(query_vectors) != 1:
            raise ValueError("Invalid query embedding")
        vector = np.asarray(query_vectors[0], dtype=np.float32)
        if vector.shape != (shape[1],) or not np.isfinite(vector).all() or not np.isfinite(vectors).all() or not np.linalg.norm(vector):
            raise ValueError("Invalid query vector")
        scores = vectors @ (vector / np.linalg.norm(vector))
        selected = {p["id"]: p for p in passages}
        # A small exact-term tie-breaker preserves explicit nouns such as
        # "proteins" without replacing dense semantic ranking with keywords.
        query_terms = {term for term in re.findall(r"\w+", query.casefold()) if len(term) >= 4}
        rank_scores = scores.copy()
        for row, segment in enumerate(index["segments"]):
            source = selected.get(segment["source_id"])
            if source:
                terms = set(re.findall(r"\w+", source["text"][segment["start"]:segment["end"]].casefold()))
                rank_scores[row] += 0.04 * min(2, len(query_terms & terms))
        hits, seen = [], set()
        for row in np.argsort(-rank_scores, kind="stable"):
            segment = index["segments"][int(row)]
            source_id = segment["source_id"]
            if float(scores[row]) < threshold:
                continue
            if source_id not in selected or source_id in seen:
                continue
            passage = selected[source_id]
            start, end = segment["start"], segment["end"]
            if not 0 <= start < end <= len(passage["text"]):
                raise ValueError("Index reference is outside its passage")
            hits.append({"source_id": source_id, "page": passage["page"], "section_id": passage["section_id"],
                         "quote": passage["text"][start:end], "score": round(float(scores[row]), 4), "start": start, "end": end})
            seen.add(source_id)
            if len(hits) == limit:
                break
        return hits
    except Exception as error:
        raise SemanticUnavailable("Semantic search could not use this index. Rebuild it or retry.") from error
