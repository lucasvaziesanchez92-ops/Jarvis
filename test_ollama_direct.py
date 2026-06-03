import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("OLLAMA_BASE_URL")
key = os.getenv("OLLAMA_API_KEY")
model = os.getenv("OLLAMA_MODEL_ID")

print(f"Probando conexión a: {url}")
print(f"Modelo: {model}")

# Prueba 1: Auth Bearer
headers = {"Authorization": f"Bearer {key}"}
try:
    resp = requests.post(f"{url}/chat", 
                         json={"model": model, "messages": [{"role": "user", "content": "hi"}], "stream": False},
                         headers=headers)
    print(f"Prueba 1 (Bearer): Status {resp.status_code}")
    if resp.status_code != 200:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"Error Prueba 1: {e}")

# Prueba 2: Sin Auth (por si acaso)
try:
    resp = requests.post(f"{url}/chat", 
                         json={"model": model, "messages": [{"role": "user", "content": "hi"}], "stream": False})
    print(f"Prueba 2 (No Auth): Status {resp.status_code}")
except Exception as e:
    print(f"Error Prueba 2: {e}")
