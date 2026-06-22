import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath('.'))

from backend.services.lancedb_cache import semantic_cache
from backend.agent.profiler import analizar_y_guardar_perfil

async def probar_memoria_permanente():
    print("[TEST] Inicializando entorno local de memoria...")
    
    # Simular que el usuario introduce datos clave en su comando de voz
    test_prompt = "Hola JARVIS, me llamo Carlos y estoy desarrollando un CRM empresarial con Next.js y Tailwind."
    print(f"[Usuario]: {test_prompt}")
    
    # Ejecutamos el extractor de perfil
    print("[TEST] Ejecutando extractor biográfico asíncrono...")
    await analizar_y_guardar_perfil(test_prompt)
    
    # Validar que los datos se hayan guardado físicamente en el disco duro de LanceDB
    print("\n[TEST] Consultando tabla 'user_profile_cache' en LanceDB...")
    hechos_recuperados = semantic_cache.obtener_perfil_completo()
    
    print(f"[Resultados encontrados en Base de Datos]: {len(hechos_recuperados)}")
    for h in hechos_recuperados:
        print(f"  - {h}")
        
    if len(hechos_recuperados) > 0:
        print("\n[TEST EXITOSO] JARVIS ahora recuerda quién eres de forma permanente.")
    else:
        print("\n[TEST FALLIDO] No se guardaron los hechos vectoriales.")

if __name__ == "__main__":
    asyncio.run(probar_memoria_permanente())
