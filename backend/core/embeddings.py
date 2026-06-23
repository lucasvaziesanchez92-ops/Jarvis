from chromadb.utils import embedding_functions
from loguru import logger

_shared_ef = None

def get_shared_embedding_function():
    """Devuelve un singleton del modelo ONNX de embeddings para evitar duplicar el uso de memoria RAM (OOM en Railway)."""
    global _shared_ef
    if _shared_ef is None:
        logger.info("🧠 Cargando modelo de embeddings en memoria COMPARTIDA (all-MiniLM-L6-v2 vía ONNX)...")
        _shared_ef = embedding_functions.DefaultEmbeddingFunction()
    return _shared_ef
