"""Servicio de Cache Vectorial con LanceDB para alta velocidad de respuesta local.

Lazy-loaded: the embedding model (~90MB ONNX) is NOT loaded at import time.
It is loaded on first use (first guardar/buscar call) to keep Railway startup
memory low (~130MB instead of ~700MB).
"""
import os
import lancedb
import pandas as pd
from loguru import logger


class SemanticCache:
    def __init__(self, db_path="data/lancedb_store"):
        os.makedirs(db_path, exist_ok=True)
        self.db = lancedb.connect(db_path)
        self._ef = None
        self._tablas = None

    @property
    def ef(self):
        """Embedding function — loaded lazily on first use to save RAM at startup."""
        if self._ef is None:
            from backend.core.embeddings import get_shared_embedding_function
            logger.info("Cargando modelo de embeddings (all-MiniLM-L6-v2) para LanceDB...")
            self._ef = get_shared_embedding_function()
        return self._ef

    @property
    def tablas(self):
        """Tables — initialized lazily to avoid DB operations at import time."""
        if self._tablas is None:
            self._tablas = {
                "drive": self._obtener_o_crear_tabla("drive_cache"),
                "gmail": self._obtener_o_crear_tabla("gmail_cache"),
                "wiki":  self._obtener_o_crear_tabla("wiki_cache"),
                "perfil": self._obtener_o_crear_tabla_perfil("user_profile_cache")
            }
            logger.info("LanceDB Cache inicializado exitosamente.")
        return self._tablas

    def _obtener_o_crear_tabla(self, nombre_tabla: str):
        if nombre_tabla in self.db.table_names():
            return self.db.open_table(nombre_tabla)
        
        # Esquema inicial vacío con la dimensión exacta del modelo (384)
        schema = {
            "vector": [0.0] * 384,
            "id": "str",
            "titulo": "str",
            "contenido": "str",
            "link_directo": "str",
            "timestamp": "str"
        }
        return self.db.create_table(nombre_tabla, data=[schema], mode="overwrite")

    def _obtener_o_crear_tabla_perfil(self, nombre_tabla: str):
        if nombre_tabla in self.db.table_names():
            return self.db.open_table(nombre_tabla)
        schema = {
            "vector": [0.0] * 384,
            "id_hecho": "str",
            "categoria": "str",
            "hecho_limpio": "str"
        }
        return self.db.create_table(nombre_tabla, data=[schema], mode="overwrite")

    def guardar_en_cache(self, categoria: str, id_doc: str, titulo: str, contenido: str, link: str, timestamp: str):
        """Convierte el contenido en vector y lo guarda en la base de datos incrustada."""
        tabla = self.tablas.get(categoria)
        if tabla is None:
            return

        try:
            # Generar embedding del texto completo (titulo + contenido)
            text_to_embed = f"{titulo} {contenido}"
            vector = self.ef([text_to_embed])[0]
            
            df = pd.DataFrame([{
                "vector": vector,
                "id": id_doc,
                "titulo": titulo,
                "contenido": contenido,
                "link_directo": link,
                "timestamp": timestamp
            }])
            
            # Upsert: Añadir o actualizar datos
            # LanceDB supports merge/upsert if a primary key is defined. For simplicity, we just add here,
            # but ideally we would delete existing or use merge_insert if configured.
            # Using append for now as a basic cache.
            tabla.add(df)
            logger.debug(f"[LanceDB] Documento '{titulo}' guardado en caché de '{categoria}'.")
        except Exception as e:
            logger.error(f"[LanceDB] Error al guardar en caché: {e}")

    def buscar_similitud(self, categoria: str, query_texto: str, umbral: float = 0.70, limit: int = 3) -> list:
        """Realiza una búsqueda semántica de alta velocidad."""
        tabla = self.tablas.get(categoria)
        if tabla is None:
            return []

        try:
            query_vector = self.ef([query_texto])[0]
            
            # Consulta vectorial
            resultados = tabla.search(query_vector).limit(limit).to_pandas()
            
            cache_hits = []
            for _, row in resultados.iterrows():
                # En LanceDB con L2 distance por defecto:
                # Menor distancia significa mayor similitud. 
                # Normalmente la distancia de similitud del coseno se aproxima a esto.
                dist = row.get("_distance", 1.0)
                if dist < (1.0 - umbral):
                    cache_hits.append({
                        "nombre": row["titulo"],
                        "attachment_key": row["id"],
                        "link_directo": row["link_directo"],
                        "contenido": row["contenido"]
                    })
            return cache_hits
        except Exception as e:
            logger.error(f"[LanceDB] Error al buscar similitud: {e}")
            return []

    def guardar_hecho_perfil(self, id_hecho: str, categoria: str, hecho_limpio: str):
        tabla = self.tablas.get("perfil")
        if not tabla: return
        
        try:
            vector = self.ef([hecho_limpio])[0]
            df = pd.DataFrame([{
                "vector": vector,
                "id_hecho": id_hecho,
                "categoria": categoria,
                "hecho_limpio": hecho_limpio
            }])
            tabla.add(df)
            logger.debug(f"[LanceDB] Hecho de perfil guardado: {hecho_limpio}")
        except Exception as e:
            logger.error(f"[LanceDB] Error al guardar hecho de perfil: {e}")

    def obtener_perfil_completo(self) -> list:
        """Recupera todos los hechos guardados sin filtro de distancia."""
        tabla = self.tablas.get("perfil")
        if not tabla: return []
        
        try:
            df = tabla.to_pandas()
            # Filtramos la fila semilla vacía del esquema inicial
            df_filtrado = df[df["hecho_limpio"] != ""]
            return df_filtrado["hecho_limpio"].tolist()
        except Exception as e:
            logger.error(f"[LanceDB] Error al obtener perfil completo: {e}")
            return []

# Singleton instance
semantic_cache = SemanticCache()
