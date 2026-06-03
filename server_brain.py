# server_brain.py
# Servidor HTTP standalone para el cerebro 3D.
# NO depende del backend FastAPI. Solo sirve web/dist/ estaticamente.
# Uso: python server_brain.py

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8765
DIST_DIR = Path(__file__).parent / "web" / "dist"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def translate_path(self, path):
        # SPA routing: /brain → /brain.html
        if path == '/brain' or path == '/brain/':
            path = '/brain.html'
        if path == '/' or path == '':
            path = '/brain.html'
        return super().translate_path(path)

    def end_headers(self):
        # Permiso CORS para que funcione desde cualquier origen
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        # Logs coloreados
        msg = format % args
        if 'GET' in msg:
            print(f"[GET] {msg}")
        elif 'POST' in msg:
            print(f"[POST] {msg}")

def main():
    print("=" * 60)
    print("   JARVIS NEURAL BRAIN - Standalone Server")
    print("=" * 60)
    print()
    
    if not DIST_DIR.exists():
        print(f"[X] ERROR: No se encontro el directorio de build:")
        print(f"    {DIST_DIR}")
        print()
        print("[*] Ejecuta primero:")
        print("    cd web")
        print("    npm run build")
        return
    
    print(f"[*] Sirviendo desde: {DIST_DIR}")
    print(f"[*] URLs disponibles:")
    print(f"    http://localhost:{PORT}/           (Solo Cerebro)")
    print(f"    http://localhost:{PORT}/brain      (Solo Cerebro)")
    print(f"    http://localhost:{PORT}/brain.html (Solo Cerebro)")
    print(f"    http://localhost:{PORT}/index.html (App completa)")
    print()
    print(f"[*] Presiona Ctrl+C para detener.")
    print()
    
    # Abrir navegador
    webbrowser.open(f"http://localhost:{PORT}/brain.html")
    
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
            print("[*] Servidor detenido.")

if __name__ == "__main__":
    main()
