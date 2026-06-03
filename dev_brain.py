import os, subprocess, sys, webbrowser

base = os.path.dirname(os.path.abspath(__file__))
web = os.path.join(base, 'web')

if not os.path.isdir(web):
    print("[X] ERROR: Ejecutar desde root del proyecto jarvis/")
    input("Press ENTER...")
    sys.exit(1)

os.chdir(web)

# Verificar node_modules
if not os.path.isdir("node_modules"):
    print("[!] Dependencias faltantes. Instalando...")
    subprocess.run("npm install", shell=True)

print("=" * 50)
print("  JARVIS NEURAL BRAIN")
print("  Dev Server (siempre funciona)")
print("=" * 50)
print()
print("[*] Iniciando Vite Dev Server...")
print("[*] URL: http://localhost:3000/brain.html")
print("[*] Espera 5-10 segundos y se abre Chrome.")
print("[*] Presiona Ctrl+C para detener.")
print()

webbrowser.open("http://localhost:3000/brain.html")

subprocess.run("npm run dev", shell=True)
