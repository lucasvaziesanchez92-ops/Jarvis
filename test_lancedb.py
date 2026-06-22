import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from backend.services.lancedb_cache import semantic_cache

def test_lancedb():
    print("Iniciando prueba de LanceDB...")
    
    # 1. Guardar documento de prueba
    semantic_cache.guardar_en_cache(
        categoria="drive",
        id_doc="12345",
        titulo="Factura de Servicios Diciembre 2023",
        contenido="Esta es la factura del servicio de luz y agua.",
        link="https://drive.google.com/test",
        timestamp="2023-12-01T12:00:00"
    )
    print("✅ Documento guardado en caché.")
    
    # 2. Buscar similitud (Cache Hit esperado)
    print("🔍 Buscando 'factura de luz'...")
    resultados = semantic_cache.buscar_similitud("drive", "factura de luz")
    
    if resultados:
        print(f"✅ Cache Hit! Resultados: {resultados}")
    else:
        print("❌ Fallo: No se encontraron resultados.")
        
    # 3. Buscar algo irrelevante (Cache Miss esperado)
    print("🔍 Buscando 'receta de pastel'...")
    resultados_miss = semantic_cache.buscar_similitud("drive", "receta de pastel", umbral=0.7)
    
    if not resultados_miss:
        print("✅ Cache Miss esperado funcionó (sin falsos positivos).")
    else:
        print(f"❌ Fallo: Falsos positivos detectados: {resultados_miss}")
        
if __name__ == '__main__':
    test_lancedb()
