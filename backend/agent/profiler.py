import re
import uuid
import asyncio
from loguru import logger
from backend.services.lancedb_cache import semantic_cache

# Utilizamos el LLM principal desde get_llm
from backend.llm import get_llm

# Filtro rápido para no gastar tokens si el usuario solo dice "hola" o "gracias"
PALABRAS_CLAVE_PERFIL = r"\b(llamo|nombre|trabajo|stack|programando|proyecto|desarrollando|correo|mail|vivo|ciudad|gusta|prefiero|soy|tengo)\b"

async def analizar_y_guardar_perfil(mensaje_usuario: str):
    """
    Analiza el mensaje en segundo plano para extraer hechos biográficos estables.
    """
    if not re.search(PALABRAS_CLAVE_PERFIL, mensaje_usuario.lower()):
        return # Filtro activado: No hay datos de identidad, terminamos en 0ms

    prompt_extractor = f"""
    Analiza el siguiente mensaje de un usuario e identifica si proporciona información personal o profesional ESTABLE sobre sí mismo (ej. su nombre, tecnologías que usa, proyectos actuales o preferencias).
    
    Mensaje: "{mensaje_usuario}"
    
    Instrucciones estrictas:
    1. Extrae la información como una lista de hechos atómicos en tercera persona. Ej: "El usuario se llama Carlos" o "El usuario programa en Next.js".
    2. Si el mensaje no contiene información persistente, responde únicamente con la palabra: VACIO.
    3. No inventes datos. Sé conciso.
    """
    
    try:
        # Llamada asíncrona desacoplada del pipeline principal usando el modelo de LLM configurado
        llm = get_llm()
        # ainvoke para llamarlo de forma asíncrona
        respuesta = await llm.ainvoke(prompt_extractor)
        contenido = respuesta.content.strip()
        
        # Eliminar bloques <think> si el modelo es tipo DeepSeek/Devstral
        contenido = re.sub(r'<think>.*?</think>', '', contenido, flags=re.DOTALL).strip()
        
        if "VACIO" in contenido.upper():
            return

        lineas = [linea.strip("- ").strip() for linea in contenido.split("\n") if linea.strip()]
        
        for hecho in lineas:
            if hecho:
                # Guardar el vector del hecho biográfico en LanceDB de forma permanente
                semantic_cache.guardar_hecho_perfil(
                    id_hecho=str(uuid.uuid4())[:8],
                    categoria="identidad",
                    hecho_limpio=hecho
                )
                logger.info(f"💾 [Memoria Permanente] Hecho guardado con éxito: {hecho}")
                
    except Exception as e:
        logger.warning(f"⚠️ [Profiler Error] No se pudo extraer el perfil: {e}")
