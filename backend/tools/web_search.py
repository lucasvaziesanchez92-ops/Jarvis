"""Web Agent PRO — Búsqueda y extracción real sin deadlocks."""
import asyncio
import os
import urllib.request
import urllib.parse
import json
import re
from langchain_core.tools import tool

_BACKEND_URL = os.getenv("BACKEND_PUBLIC_URL", "https://backend-production-cabf.up.railway.app")

def _wiki_fallback(query: str) -> str:
    try:
        url = "https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch=" + urllib.parse.quote(query) + "&utf8=&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Jarvis/2.0 (Bot)'})
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read())
        
        results = data.get('query', {}).get('search', [])
        if not results:
            return f"No se encontraron resultados externos para '{query}' en la web ni en Wikipedia."
            
        final_report = []
        for i, r in enumerate(results[:3]):
            title = r.get("title", "Sin título")
            snippet = r.get("snippet", "").replace("<span class=\"searchmatch\">", "**").replace("</span>", "**")
            final_report.append(f"### Fuente {i+1} (Wikipedia): {title}\n\n{snippet}...")
            
        return "\n\n---\n\n".join(final_report)
    except Exception as e:
        return f"Error crítico durante la búsqueda web: {str(e)}"

def _bing_html_scraper(query: str) -> str:
    """Scrapes Bing HTML using httpx since DDG Lite is now returning 202 Accepted blocks."""
    import httpx
    try:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
        with httpx.Client(http2=True, timeout=10, follow_redirects=True) as client:
            res = client.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
                }
            )
            html = res.text
            
        results = []
        blocks = re.findall(r'<li class="b_algo".*?>(.*?)</li>', html, re.IGNORECASE | re.DOTALL)
        
        for block in blocks:
            title_match = re.search(r'<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>', block, re.IGNORECASE | re.DOTALL)
            snippet_match = re.search(r'<div class="b_caption"><p[^>]*>(.*?)</p></div>', block, re.IGNORECASE | re.DOTALL)
            # A veces el snippet no está en b_caption p
            if not snippet_match:
                snippet_match = re.search(r'<div class="b_lineclamp[^>]*>(.*?)</div>', block, re.IGNORECASE | re.DOTALL)
                
            if title_match and snippet_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()
                body = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                url = title_match.group(1)
                
                # Ignorar links de videos o similares
                if not url.startswith("http"):
                    continue
                    
                results.append(f"### Fuente {len(results)+1}: [{title}]({url})\n{body}")
                
            if len(results) >= 3:
                break
                
        if results:
            first_url_match = re.search(r'\[.*?\]\((.*?)\)', results[0])
            first_url = first_url_match.group(1) if first_url_match else ""
            
            prefix = ""
            if first_url:
                encoded_url = urllib.parse.quote(first_url)
                prefix = (
                    f"INSTRUCCIÓN OBLIGATORIA: Muestra la siguiente imagen de vista previa en tu respuesta: ![Vista previa del sitio](https://api.microlink.io/?url={encoded_url}&screenshot=true&meta=false&embed=screenshot.url)\n\n"
                    "CRÍTICO: Cuando menciones las fuentes o referencias de esta búsqueda, DEBES formatearlas como enlaces Markdown clicables (ej. [Nombre de la página](URL)). ¡NUNCA escribas la URL cruda!\n\n"
                )
            
            return prefix + "\n\n---\n\n".join(results)
        return _wiki_fallback(query)
    except Exception as e:
        print(f"Bing scraper error: {e}")
        return _wiki_fallback(query)

@tool
def web_search(query: str) -> str:
    """Busca en internet usando un buscador real y extrae el texto de las páginas web más relevantes.
    Úsala para obtener información textual y responder preguntas."""
    return _bing_html_scraper(query)


# Spanish→English keyword map for better DDG/Bing results
_ES_EN = {
    "perro": "dog", "gato": "cat", "naranja": "orange", "negro": "black",
    "blanco": "white", "rojo": "red", "azul": "blue", "verde": "green",
    "auto": "car", "coche": "car", "avion": "airplane", "avión": "airplane",
    "ciudad": "city", "montaña": "mountain", "playa": "beach",
    "comida": "food", "persona": "person", "hombre": "man", "mujer": "woman",
}

def _translate_query(q: str) -> str:
    """Translate common Spanish words to English for better image search results."""
    words = q.lower().split()
    return " ".join(_ES_EN.get(w, w) for w in words)


@tool
def buscar_imagenes_web(query: str) -> str:
    """Busca im?genes (fotos, diagramas, infograf?as) en la web.
    Usa ESTA herramienta (incluso en paralelo con web_search) siempre que el usuario te pida expl?citamente que le muestres "una imagen", "fotos" o "diagramas" sobre un tema.
    SIEMPRE devuelve al menos una imagen ? nunca devuelve vac?o."""
    import urllib.request, urllib.parse, json
    resultados = []
    
    # 1. DuckDuckGo Search Package (Robusto, mejores resultados web)
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            ddg_results = list(ddgs.images(query, max_results=3))
            for item in ddg_results:
                img_url = item.get("image", "")
                title = item.get("title", query)[:60].replace("[", "").replace("]", "")
                if img_url:
                    resultados.append(f"![{title}]({img_url})")
                    if len(resultados) >= 2:
                        break
    except Exception:
        pass

    # 2. Wikipedia Commons (Respaldo)
    if not resultados:
        try:
            q_safe = urllib.parse.quote(query)
            wm_url = (
                f"https://commons.wikimedia.org/w/api.php?action=query"
                f"&generator=search&gsrsearch={q_safe}&gsrnamespace=6"
                f"&prop=imageinfo&iiprop=url|mime&format=json&gsrlimit=5"
            )
            req = urllib.request.Request(wm_url, headers={'User-Agent': 'Jarvis/2.0 (Bot)'})
            with urllib.request.urlopen(req, timeout=8) as res:
                data = json.loads(res.read())
            for page in data.get("query", {}).get("pages", {}).values():
                title = page.get("title", "").replace("File:", "").split(".")[0].replace("[", "").replace("]", "")
                img_info = page.get("imageinfo", [{}])[0]
                img_url = img_info.get("url", "")
                mime = img_info.get("mime", "")
                if img_url and mime in ("image/jpeg", "image/png", "image/webp"):
                    resultados.append(f"![{title}]({img_url})")
                    if len(resultados) >= 2:
                        break
        except Exception:
            pass

    if not resultados:
        return "NO SE ENCONTRARON IM?GENES REALES. Informa al usuario que la b?squeda de im?genes web no arroj? resultados v?lidos y no intentes inventar la imagen."
        
    res_text = "IM?GENES ENCONTRADAS. INSTRUCCI?N CR?TICA Y OBLIGATORIA: DEBES copiar y pegar EXACTAMENTE los siguientes enlaces Markdown en tu respuesta para que el usuario pueda ver las im?genes. NO los modifiques, NO escribas solo el t?tulo, DEBES incluir los corchetes y par?ntesis tal cual (ej. ![T?tulo](URL)).\n\n"
    res_text += "\n".join(resultados)
    return res_text

@tool
def buscar_reversa_gratis(attachment_key: str) -> str:
    """Analiza una imagen que subió el usuario usando visión artificial (Gemini Vision).
    Identifica qué es el objeto/persona/lugar y busca información sobre él en internet.
    Usa esta herramienta SIEMPRE que el usuario suba una foto y pida analizarla, identificarla o buscar su precio.
    Args:
        attachment_key: La clave del archivo adjunto tal como viene en el contexto del mensaje.
    """
    import base64
    import os
    import requests
    from backend.core.storage import download_bytes

    # ── Paso 1: Descargar la imagen del storage ──────────────────
    try:
        image_bytes = download_bytes(attachment_key)
    except Exception as e:
        return f"No pude acceder a la imagen subida. Error: {e}"

    if len(image_bytes) < 100:
        return "La imagen recibida está vacía o corrupta."

    # ── Paso 2: Identificar con Gemini Vision ────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "GEMINI_API_KEY no configurada. No puedo analizar la imagen."

    b64 = base64.b64encode(image_bytes).decode("ascii")
    # Detect mime type from magic bytes
    mime = "image/jpeg"
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        mime = "image/png"
    elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        mime = "image/webp"

    vision_payload = {
        "contents": [{
            "parts": [
                {"text": (
                    "Analiza esta imagen con detalle. Responde en español:\n"
                    "1. ¿Qué objeto, producto, persona o lugar aparece en la imagen?\n"
                    "2. Describe sus características principales (marca, modelo, color, estado si aplica).\n"
                    "3. ¿Qué palabras clave usarías para buscar este artículo en Google?\n"
                    "Sé específico y conciso."
                )},
                {"inline_data": {"mime_type": mime, "data": b64}}
            ]
        }]
    }

    import time
    description = ""
    for attempt in range(3):
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
                json=vision_payload,
                timeout=25,
            )
            resp.raise_for_status()
            vision_result = resp.json()
            description = vision_result["candidates"][0]["content"]["parts"][0]["text"]
            break
        except requests.exceptions.HTTPError as e:
            if resp.status_code in (429, 503) and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return f"Error al analizar la imagen con visión artificial: {e}"
        except Exception as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return f"Error al analizar la imagen con visión artificial: {e}"

    # ── Paso 3: Buscar en web con la descripción ─────────────────
    # Extract search keywords from vision result (last line of the response)
    lines = [l.strip() for l in description.split("\n") if l.strip()]
    search_query = lines[-1] if lines else description[:80]
    # Clean up common prefixes
    for prefix in ("3.", "Keywords:", "Palabras clave:", "Búsqueda:"):
        search_query = search_query.replace(prefix, "").strip()

    web_info = ""
    try:
        web_info = _ddg_html_scraper(f"{search_query} precio comprar")
        if len(web_info) > 1500:
            web_info = web_info[:1500] + "..."
    except Exception:
        pass

    result = (
        f"**Análisis de la imagen:**\n{description}\n\n"
        f"**Información encontrada en internet:**\n{web_info if web_info else 'No se encontró información adicional.'}"
    )
    return result
