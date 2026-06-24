"""Background worker para sincronizar Drive, Gmail y Wiki hacia LanceDB (Delta Sync)."""
import asyncio
from datetime import datetime
from loguru import logger

from backend.services.lancedb_cache import semantic_cache
from backend.services.drive_service import list_files
from backend.services.gmail_service import list_emails

class CacheWorker:
    def __init__(self, interval_seconds=600, initial_delay_seconds=45):
        self.interval_seconds = interval_seconds
        self.initial_delay_seconds = initial_delay_seconds
        self.running = False
        self.last_sync_drive = None  # ISO 8601 datetime string

    async def start(self):
        """Inicia el ciclo asíncrono del worker en segundo plano."""
        self.running = True
        logger.info(f"🚀 [CacheWorker] Iniciando Delta Sync de LanceDB cada {self.interval_seconds} segundos. Primer sync en {self.initial_delay_seconds}s.")
        
        # Wait before first sync so the server is fully ready and accepting requests
        await asyncio.sleep(self.initial_delay_seconds)
        
        while self.running:
            try:
                await self.sync_drive()
                # await self.sync_gmail()
                # await self.sync_wiki()
            except Exception as e:
                logger.error(f"[CacheWorker] Error durante la sincronización: {e}")
            
            # Suspende el hilo sin consumir CPU
            await asyncio.sleep(self.interval_seconds)

    def stop(self):
        """Detiene el worker."""
        self.running = False
        logger.info("🛑 [CacheWorker] Detenido.")

    async def sync_drive(self):
        """Descarga e indexa los archivos nuevos o modificados (Delta Sync)."""
        logger.debug("[CacheWorker] Iniciando escaneo de Google Drive...")
        
        try:
            # En una aplicación real usaríamos "q" con self.last_sync_drive
            recent_files = await asyncio.to_thread(list_files, max_results=20)
            
            nuevos = 0
            for f in recent_files:
                ftype = f.get("mimeType", "")
                if ftype == "application/vnd.google-apps.folder":
                    continue
                
                # Upsert en LanceDB
                semantic_cache.guardar_en_cache(
                    categoria="drive",
                    id_doc=f["id"],
                    titulo=f["name"],
                    contenido="",  # El título es suficiente para semantic routing por ahora
                    link=f.get("webViewLink", ""),
                    timestamp=f.get("modifiedTime", "")
                )
                nuevos += 1
                
                # Actualizar last_sync_drive al más reciente
                mod_time = f.get("modifiedTime")
                if mod_time:
                    if not self.last_sync_drive or mod_time > self.last_sync_drive:
                        self.last_sync_drive = mod_time

            if nuevos > 0:
                logger.info(f"✅ [CacheWorker] {nuevos} archivos de Drive indexados/actualizados en LanceDB. Última mod: {self.last_sync_drive}")
            else:
                logger.debug("[CacheWorker] Drive está al día, no hay cambios.")
                
        except RuntimeError as e:
            logger.warning(f"[CacheWorker] Drive no configurado: {e}")
        except Exception as e:
            logger.error(f"[CacheWorker] Error en sync_drive: {e}")

cache_worker = CacheWorker(interval_seconds=600)
