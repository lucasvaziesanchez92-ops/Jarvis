from pathlib import Path
import subprocess
import sys
import urllib.request
import urllib.error
import socket
import argparse

# ────────────────────────────────────────────────────────────
# JARVIS MOBILE LAUNCHER
# Descubre IP local, configura todo y levanta el stack
# ────────────────────────────────────────────────────────────

def get_local_ip():
    """Descubrir IP local para mobile."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except:
        return "127.0.0.1"

def verify_lm_studio(url: str = "http://127.0.0.1:1234/v1/models") > bool:
    """Verificar que LM Studio esté corriendo."""
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except urllib.error.URLError:
        return False
    except:
        return False

def verify_backend(url: str = "http://127.0.0.1:8000/health") > bool:
    """Verificar que el backend esté corriendo."""
    try:
        req = urllib.request.Request(url, method='GET')
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description="JARVIS Mobile Launcher")
    parser.add_argument("--api-url", type=str, default=None,
                        help="URL del backend (ej: http://192.168.1.100:8000)")
    parser.add_argument("--no-lm-studio", action="store_true",
                        help="No verificar LM Studio (para cloud)")
    parser.add_argument("--mobile-only", action="store_true",
                        help="Solo configurar, no levantar nada")
    args = parser.parse_args()

    # Directorio base
    base = Path(__file__).parent.resolve()
    env_file = base / ".env"
    web_next = base / "web-next"
    web_env = web_next / ".env.local"

    ip = get_local_ip()
    host_ip = ip if ip != "127.0.0.1" else "localhost"

    print("=" * 60)
    print("   JARVIS — Mobile Launcher (v2.0 FIX)")
    print("=" * 60)
    print()
    # 1. Verificar LM Studio
    if not args.no_lm_studio:
        if verify_lm_studio():
            print(f"  [OK] LM Studio:    http://127.0.0.1:1234")
        else:
            print(f"  [X]  LM Studio:    NO ENCONTRADO")
            print("       Asegurate de abrir LM Studio y cargar un modelo.")
            print("       O usa --no-lm-studio para saltar.")
            return 1
    else:
        print(f"  [i]  LM Studio:    skipped (--no-lm-studio)")

    # 2. Verificar entorno backend
    print(f"  [*]  IP Local:     {ip}")
    print(f"  [*]  Directorio:    {base}")

    # 3. Configurar .env del proyecto si hace falta
    provider = "lm_studio"
    lm_url = "http://127.0.0.1:1234/v1"
    if args.api_url and args.no_lm_studio:
        provider = "ollama"
        lm_url = args.api_url

    env_content = f"""# JARVIS Environment — Auto-configurado por launcher
LLM_PROVIDER={provider}
LM_STUDIO_BASE_URL={lm_url}
LM_STUDIO_MODEL=qwen/qwen2.5-vl-7b

API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["*"]
DATA_DIR=data
MAX_CONTEXT_MESSAGES=50
ENABLE_LANGSMITH=false

# URLs externas (desde el celular)
EXTERNAL_API_URL=http://{host_ip}:8000
EXTERNAL_WEB_URL=http://{host_ip}:3000
"""
    env_file.write_text(env_content, encoding="utf-8")
    print(f"  [OK] .env           → {env_file}")

    # 4. Configurar .env.local del frontend para conectarse al backend
    api_url = args.api_url or f"http://{host_ip}:8000"
    web_env_content = f"NEXT_PUBLIC_API_URL={api_url}\nNEXT_PUBLIC_WS_URL=ws://{host_ip}:8000"
    web_env.write_text(web_env_content, encoding="utf-8")
    print(f"  [OK] web .env.local → {web_env}")

    # 5. Verificar backend
    print()
    print("  [*]  Verificando backend...")
    if verify_backend(api_url + "/health"):
        print(f"  [OK] Backend:      {api_url}/health")
    elif verify_backend("http://127.0.0.1:8000/health"):
        print(f"  [OK] Backend:      http://127.0.0.1:8000/health")
    else:
        print(f"  [X]  Backend:      NO ENCONTRADO")
        print(f"       Levantalo con: python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000")
        print()

    # 6. Verificar node_modules
    print()
    print("  [*]  Verificando frontend...")
    if not (web_next / "node_modules").exists():
        print("       Instalando dependencias npm...")
        subprocess.run(["npm", "install"], cwd=web_next)

    # 7. Build del frontend (static export)
    print("       Buildando frontend (export estatico para mobile)...")
    build_result = subprocess.run(
        ["npm", "run", "build"],
        cwd=web_next,
        capture_output=True,
        text=True
    )
    if build_result.returncode != 0:
        print(f"  [X]  Build fallo:\n{build_result.stderr[-500:]}")
        return 1
    print(f"  [OK] Build:        web-next/.next/ (listo)")

    # 8. Instrucciones finales
    print()
    print("=" * 60)
    print("   ACCESO DESDE CELULAR (mismo WiFi)")
    print("=" * 60)
    print()
    print(f"   Navegador PC:  http://localhost:3000  (desktop)")
    print(f"   Celular:       http://{host_ip}:3000   (usar QR)")
    print()
    print("   Para modo DEBUG vertical:")
    print("   1. Abri Chrome")
    print("   2. F12 → Ctrl+Shift+M (modo dispositivo)")
    print("   3. Seleccionar iPhone SE 375x667")
    print()
    print("   O desde el celular real:")
    print("   1. Conectarse al MISMO WiFi que la PC")
    print("   2. Abrir Chrome → http://{host_ip}:3000")
    print()
    print("   QR Code: (copiar y generar en qr-code-generator.com)")
    print(f"   URL: http://{host_ip}:3000")
    print()
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
