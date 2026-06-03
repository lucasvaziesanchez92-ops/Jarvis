
import os
import sys
from pathlib import Path

def check_env():
    print("--- Verificador de Entorno JARVIS ---")
    
    critical_paths = [
        "data",
        "data/wiki",
        "data/sources",
        "data/logs",
        "backend",
        "web-next"
    ]
    
    missing = []
    for p in critical_paths:
        if not Path(p).exists():
            missing.append(p)
    
    if missing:
        print(f"❌ Faltan carpetas críticas: {', '.join(missing)}")
    else:
        print("✅ Estructura de carpetas: OK")

    # Verificar .env
    if not Path(".env").exists():
        print("⚠️ Archivo .env no encontrado. Asegúrate de configurar tus API Keys.")
    else:
        print("✅ Archivo .env: Encontrado")

    # Verificar Base de Datos
    db_path = Path("data/jarvis.db")
    if not db_path.exists():
        print("⚠️ Base de datos 'data/jarvis.db' no encontrada. Se creará al iniciar.")
    else:
        print(f"✅ Base de datos: OK ({db_path.stat().st_size / 1024:.1f} KB)")

    # Verificar dependencias críticas
    try:
        import fastapi
        import langgraph
        # import playwright # No lo checamos así para no forzar ejecución
        print("✅ Dependencias Python básicas: OK")
    except ImportError as e:
        print(f"❌ Error de dependencias: {str(e)}")

    print("\n--- Todo listo para iniciar ---")
    print("Para iniciar el Backend: uvicorn backend.api.main:app --host 0.0.0.0 --port 8000")
    print("Para iniciar el Frontend: cd web-next && npm run dev")

if __name__ == "__main__":
    check_env()
