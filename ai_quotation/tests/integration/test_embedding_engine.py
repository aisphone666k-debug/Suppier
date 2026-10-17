import numpy as np
import pytest

from src.infrastructure.embedding_engine import FastEmbedEngine


def test_embed_text_returns_dense_vector():
    engine = FastEmbedEngine()
    text = "Bando V-Belt high precision industrial rubber belt"
    vector = engine.embed_text(text)

    assert isinstance(vector, np.ndarray)
    assert len(vector) == 384
    # Ensure vector is non-zero
    assert np.linalg.norm(vector) > 0.0


def test_embed_batch_returns_list_of_vectors():
    engine = FastEmbedEngine()
    texts = ["Bearing 6204ZZ", "Pneumatic cylinder DN50"]
    vectors = engine.embed_batch(texts)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384
