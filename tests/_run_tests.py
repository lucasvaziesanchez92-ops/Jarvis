"""JARVIS Test Runner — starts backend, waits, runs tests, reports."""
import subprocess
import sys
import time
import os

os.environ["PYTHONIOENCODING"] = "utf-8"

# Start backend as independent subprocess
backend = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.api.main:app",
     "--host", "127.0.0.1", "--port", "8001"],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
)

print(f"Backend PID: {backend.pid}")

# Wait for health
import urllib.request
for i in range(15):
    try:
        r = urllib.request.urlopen("http://localhost:8001/health", timeout=2)
        if r.status == 200:
            print(f"Backend UP after {(i+1)*2}s")
            break
    except Exception:
        time.sleep(2)
else:
    print("Backend FAILED to start")
    backend.terminate()
    sys.exit(1)

# Run tests
result = subprocess.run(
    [sys.executable, "-u", os.path.join(os.path.dirname(__file__), "test_final.py")],
    cwd=os.path.dirname(os.path.abspath(__file__)),
)

# Cleanup
backend.terminate()
backend.wait()
sys.exit(result.returncode)
