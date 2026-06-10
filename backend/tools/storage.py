"""Storage tools — manage files in Railway Object Storage bucket (or local fallback).

These wrap the upload_bytes / download_bytes / delete_file / list_files
primitives in core.storage so the LLM can list, read, and delete files
that the user has uploaded to the bucket via /api/files/upload.
"""
from langchain_core.tools import tool


@tool
def list_storage_files(prefix: str = "", limit: int = 50) -> str:
    """List files in the storage bucket. Optional prefix to filter by folder/prefix. Useful for finding previously uploaded files."""
    from backend.core.storage import list_files
    try:
        items = list_files(prefix=prefix)
        if not items:
            return "No hay archivos en el storage."
        lines = [f"{len(items[:limit])} archivos:"]
        for item in items[:limit]:
            key = item["Key"]
            size = item.get("Size", 0)
            last_mod = item.get("LastModified", "")
            if hasattr(last_mod, "isoformat"):
                last_mod = last_mod.isoformat()
            size_str = f" ({size / 1024:.1f}KB)" if size else ""
            lines.append(f"- {key}{size_str} (modificado: {last_mod[:19] if last_mod else 'N/A'})")
        return "\n".join(lines)
    except RuntimeError as e:
        return f"Error listando storage: {e}"


@tool
def read_storage_file(key: str) -> str:
    """Read the content of a file in storage by its key. Returns text content (up to 10000 chars) for text files, or a binary description for non-text."""
    from backend.core.storage import download_bytes
    try:
        data = download_bytes(key)
        # Try to decode as UTF-8 text first
        try:
            text = data.decode("utf-8")
            if len(text) > 10000:
                text = text[:10000] + "\n... (truncado, " + str(len(data)) + " bytes total)"
            return f"Contenido de {key} ({len(data)} bytes):\n\n{text}"
        except UnicodeDecodeError:
            return f"Archivo binario {key} ({len(data)} bytes). Usá un tool específico para analizar (PDF, imagen, etc.)."
    except RuntimeError as e:
        return f"Error leyendo storage: {e}"


@tool
def delete_storage_file(key: str) -> str:
    """Delete a file from storage by its key. This cannot be undone."""
    from backend.core.storage import delete_file
    try:
        delete_file(key)
        return f"Archivo {key} eliminado del storage."
    except RuntimeError as e:
        return f"Error eliminando storage: {e}"
