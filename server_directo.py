# server_directo.py
# Servidor HTTP que SÍ sirve ES modules correctamente.
# Usa brain_standalone.html — cerebro 3D puro sin build ni Vite.
import http.server, socketserver, os, webbrowser, mimetypes

PORT = 8765
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'public', 'brain_standalone.html')

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/javascript', '.mjs')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/wasm', '.wasm')

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        msg = fmt % args
        status = args[1] if len(args) > 1 else ''
        if status == '200':
            print(f"[OK] {msg}")
        elif status == '404':
            print(f"[404] {msg}")
        else:
            print(f"[{status}] {msg}")

    def guess_type(self, path):
        # Fix MIME type for ES modules
        if path.endswith('.js'):
            return 'application/javascript'
        if path.endswith('.mjs'):
            return 'application/javascript'
        return super().guess_type(path)

def main():
    if not os.path.exists(HTML_FILE):
        print(f"[X] ERROR: No se encontro {HTML_FILE}")
        return
    os.chdir(os.path.dirname(HTML_FILE))
    
    print("=" * 60)
    print("   JARVIS NEURAL BRAIN — Direct Server")
    print("=" * 60)
    print()
    print(f"[*] Servidor: http://localhost:{PORT}/")
    print(f"[*] Presiona Ctrl+C para detener.")
    print()
    
    webbrowser.open(f"http://localhost:{PORT}/")
    
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
            print("[*] Servidor detenido.")

if __name__ == "__main__":
    main()
