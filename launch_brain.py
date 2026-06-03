import os, subprocess, sys, time, webbrowser

base = os.path.dirname(os.path.abspath(__file__))
web = os.path.join(base, 'web')

if not os.path.isdir(web):
    print("[X] ERROR: Run this script from the jarvis/ project root folder.")
    input("Press ENTER to exit...")
    sys.exit(1)

os.chdir(web)

# BUILD
brain_html = os.path.join('dist', 'brain.html')
if not os.path.exists(brain_html):
    print("[*] Building NeuralBrain... (takes ~10 seconds)")
    r = subprocess.run("npm run build", shell=True)
    if r.returncode != 0:
        print("[X] BUILD FAILED. Check errors above.")
        input("Press ENTER...")
        sys.exit(1)
else:
    print("[OK] Build found.")

# START Vite preview (the only server that properly serves ES modules)
print("[*] Starting server on http://localhost:8765/brain.html")
webbrowser.open("http://localhost:8765/brain.html")
print("[*] Press Ctrl+C to stop.")
print("")
try:
    subprocess.run("npx vite preview --port 8765 --host", shell=True)
except KeyboardInterrupt:
    print("")
    print("[*] Server stopped.")
