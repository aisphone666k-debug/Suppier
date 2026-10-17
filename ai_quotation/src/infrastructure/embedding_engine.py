import numpy as np
from fastembed import TextEmbedding


class FastEmbedEngine:
    """Local, offline ONNX embedding engine using FastEmbed."""

    _instance: "FastEmbedEngine | None" = None

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", cache_dir: str | None = None) -> None:
        import os
        from pathlib import Path
        if cache_dir is None:
            cache_dir = os.environ.get("FASTEMBED_CACHE_PATH")
        if cache_dir is None:
            local_cache = Path(__file__).resolve().parent.parent.parent / ".cache" / "fastembed"
            local_cache.mkdir(parents=True, exist_ok=True)
            cache_dir = str(local_cache)
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed_text(self, text: str) -> np.ndarray:
        generator = self._model.embed([text])
        vector = next(iter(generator))
        return np.array(vector, dtype=np.float32)

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        generator = self._model.embed(texts)
        return [np.array(v, dtype=np.float32) for v in generator]
