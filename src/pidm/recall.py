"""Scene recall: finished Scene summaries are embedded by the worker into `scene_vec` (sqlite-vec) and the top
Scenes for the player's action join the Turn's context (design: Memory strategy; ADR 0005).

Embedding failure, at load or at runtime, never fails a Turn: recall is skipped with a logged warning.
"""

from __future__ import annotations

import logging
import struct
import threading
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from pidm.models import Scene

log = logging.getLogger("pidm.recall")

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384  # shortcut: the `scene_vec` column is fixed at bge-small's size; another size needs a new migration
RECALLED = 3  # Memory strategy: the top 3 Scenes most similar to the action


class Embedder(Protocol):
    model_id: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedder:
    """A quantised ONNX model through fastembed; the weights come from the image (FASTEMBED_CACHE_PATH)."""

    def __init__(self, model_id: str = DEFAULT_MODEL):
        self.model_id = model_id
        self._model = None
        self._lock = threading.Lock()  # the turn and job threads must not each load the model (memory)

    def embed(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            if self._model is None:  # loaded on first use so a failure is a recall failure, not a startup one
                from fastembed import TextEmbedding
                self._model = TextEmbedding(self.model_id)
            return [v.tolist() for v in self._model.embed(texts)]


def _blob(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def embed_scene(factory: sessionmaker, embedder: Embedder, scene_id: int) -> None:
    """Store the embedding of a Scene's summary with the model id; no summary or a failed embed leaves no row."""
    with factory() as db:
        summary = db.get(Scene, scene_id).summary
    if not summary:
        return
    try:
        vector = embedder.embed([summary])[0]
    except Exception:
        log.warning("Embedding Scene %s failed; it is not recalled", scene_id, exc_info=True)
        return
    with factory() as db:
        db.execute(text("DELETE FROM scene_vec WHERE scene_id = :id"), {"id": scene_id})
        db.execute(text("INSERT INTO scene_vec(scene_id, embedding, model_id) VALUES (:id, :v, :m)"),
                   {"id": scene_id, "v": _blob(vector), "m": embedder.model_id})
        db.commit()


def reembed_stale(factory: sessionmaker, embedder: Embedder) -> None:
    """Startup check: embed every summarised Scene whose stored model id is not the configured one (or has none)."""
    with factory() as db:
        ids = db.scalars(text(
            "SELECT s.id FROM scenes s LEFT JOIN scene_vec v ON v.scene_id = s.id "
            "WHERE s.summary != '' AND (v.model_id IS NULL OR v.model_id != :m)"), {"m": embedder.model_id}).all()
    for scene_id in ids:
        embed_scene(factory, embedder, scene_id)


def recall(factory: sessionmaker, embedder: Embedder | None, campaign_id: int, action: str) -> list[str]:
    """Summaries of the Campaign's Scenes most similar to `action`, best first; [] on any failure."""
    if embedder is None:
        return []
    try:
        vector = embedder.embed([action])[0]
        with factory() as db:
            rows = db.execute(text(
                "SELECT sc.summary FROM scene_vec v JOIN scenes sc ON sc.id = v.scene_id "
                "JOIN sessions se ON se.id = sc.session_id "
                "WHERE se.campaign_id = :c AND v.model_id = :m "
                "ORDER BY vec_distance_L2(v.embedding, :q) LIMIT :n"),
                {"c": campaign_id, "m": embedder.model_id, "q": _blob(vector), "n": RECALLED})
            return [r[0] for r in rows]
    except Exception:
        log.warning("Scene recall failed; this Turn has none", exc_info=True)
        return []
