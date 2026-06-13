import os
import re

# 1. Update Brain Color
brain_path = "web-next/public/brain-standalone.html"
with open(brain_path, "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("color: 0xd0e8ff,", "color: 0xff88cc,")
html = html.replace("emissive: 0x2244aa,", "emissive: 0xaa2266,")
html = html.replace("roughness: 0.1,", "roughness: 0.15,")

with open(brain_path, "w", encoding="utf-8") as f:
    f.write(html)


# 2. Update file_extractor.py
extractor_path = "backend/core/file_extractor.py"
with open(extractor_path, "r", encoding="utf-8") as f:
    extractor = f.read()

new_extractor = """def _extract_image_with_groq_vision(data: bytes, filename: str) -> str:
    \"\"\"Use Gemini REST API to describe images.\"\"\"
    import base64
    import os
    import requests

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _extract_image_placeholder(filename)

    try:
        mime = "image/png"
        ext = filename.split(".")[-1].lower()
        if ext in ["jpg", "jpeg"]: mime = "image/jpeg"
        elif ext == "webp": mime = "image/webp"
        elif ext == "gif": mime = "image/gif"

        b64 = base64.b64encode(data).decode("ascii")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Describe esta imagen en detalle en español. Qué ves? Objetos, personas, texto, colores, composición, contexto. Sé conciso pero completo."},
                    {"inline_data": {"mime_type": mime, "data": b64}}
                ]
            }]
        }
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return f"[Análisis de {filename}]: {text}"
    except Exception as e:
        return f"[Error procesando imagen {filename} con Gemini: {e}]"
"""

extractor = re.sub(
    r'def _extract_image_with_groq_vision\(data: bytes, filename: str\) -> str:.*?except Exception as e:\s*return f"\[Error procesando imagen {filename} con Groq: {e}\]"\n*',
    new_extractor + "\n",
    extractor,
    flags=re.DOTALL
)

with open(extractor_path, "w", encoding="utf-8") as f:
    f.write(extractor)


# 3. Update google_suite.py
google_path = "backend/tools/google_suite.py"
with open(google_path, "r", encoding="utf-8") as f:
    google = f.read()

new_google_vision = """@tool
def analyze_drive_image(file_id: str) -> str:
    \"\"\"Analyze an image stored in Google Drive using Gemini Vision.
    Args: file_id: The Google Drive file ID of the image.
    Returns: A detailed visual description of the image.
    \"\"\"
    from backend.services.drive_service import download_file
    import base64
    import os
    import requests
    try:
        data, filename, mime = download_file(file_id)
        if not mime.startswith("image/"):
            return f"Error: El archivo {filename} no es una imagen (tipo: {mime})."
            
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return "Error: GEMINI_API_KEY no configurada."

        b64 = base64.b64encode(data).decode("ascii")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Describe esta imagen en detalle en español. Qué ves? Objetos, personas, texto, colores, composición, contexto. Sé conciso pero completo."},
                    {"inline_data": {"mime_type": mime, "data": b64}}
                ]
            }]
        }
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return f"[Análisis de {filename}]: {text}"
    except Exception as e:
        return f"[Error al analizar imagen con Gemini: {str(e)[:200]}]"
"""

google = re.sub(
    r'@tool\ndef analyze_drive_image\(file_id: str\) -> str:.*?except Exception as e:\s*return f"\[Error al analizar imagen {filename} con Groq Vision: \{str\(e\)\[:200\]\}\]"\n*',
    new_google_vision + "\n",
    google,
    flags=re.DOTALL
)

with open(google_path, "w", encoding="utf-8") as f:
    f.write(google)

print("Updates completed successfully.")
