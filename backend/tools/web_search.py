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

def _ddg_html_scraper(query: str) -> str:
    """Scrapes DDG HTML lite using httpx to avoid 403 Forbidden blocks."""
    import httpx
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        with httpx.Client(http2=True, timeout=10, follow_redirects=True) as client:
            res = client.get(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            html = res.text
            
        # Parse result snippets individually to filter out Ads
        results = []
        # Split HTML by result blocks
        blocks = re.split(r'class="result ', html)[1:]
        
        for block in blocks:
            # Ignore ads
            if "badge--ad" in block or "result--ad" in block:
                continue
                
            title_match = re.search(r'<h2 class="result__title">.*?<a[^>]*>(.*?)</a>', block, re.IGNORECASE | re.DOTALL)
            href_match = re.search(r'<h2 class="result__title">.*?<a[^>]*href="([^"]+)"', block, re.IGNORECASE | re.DOTALL)
            snippet_match = re.search(r'<a class="result__snippet[^>]*>(.*?)</a>', block, re.IGNORECASE | re.DOTALL)
            
            if title_match and snippet_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                body = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                url = href_match.group(1) if href_match else ""
                if url.startswith("//duckduckgo.com/l/?uddg="):
                    url = urllib.parse.unquote(url.split("uddg=")[1].split("&")[0])
                elif url.startswith("//"):
                    url = "https:" + url
                    
                results.append(f"### Fuente {len(results)+1}: [{title}]({url})\n{body}")
                
            if len(results) >= 3:
                break
                
        if results:
            # Get URL of the first source to generate preview
            first_url_match = re.search(r'\[.*?\]\((.*?)\)', results[0])
            first_url = first_url_match.group(1) if first_url_match else ""
            
            # Add strict instruction for the LLM to output the preview markdown
            prefix = ""
            if first_url:
                encoded_url = urllib.parse.quote(first_url)
                prefix = (
                    f"INSTRUCCIÓN OBLIGATORIA: Muestra la siguiente imagen de vista previa en tu respuesta: ![Vista previa del sitio](https://api.microlink.io/?url={encoded_url}&screenshot=true&meta=false&embed=screenshot.url)\n\n"
                    "CRÍTICO: Cuando menciones las fuentes o referencias de esta búsqueda, DEBES formatearlas como enlaces Markdown clicables (ej. [Nombre de la página](URL)). ¡NUNCA escribas la URL cruda!\n\n"
                )
            
            return prefix + "\n\n---\n\n".join(results)
        return _wiki_fallback(query)
    except Exception:
        return _wiki_fallback(query)

@tool
def web_search(query: str) -> str:
    """Busca en internet usando un buscador real y extrae el texto de las páginas web más relevantes.
    Úsala para obtener información textual y responder preguntas."""
    return _ddg_html_scraper(query)


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
    """Busca imágenes (fotos, diagramas, infografías) en la web.
    Usa ESTA herramienta (incluso en paralelo con web_search) siempre que el usuario te pida explícitamente que le muestres "una imagen", "fotos" o "diagramas" sobre un tema.
    SIEMPRE devuelve al menos una imagen — nunca devuelve vacío."""
    resultados = []
    query_en = _translate_query(query)  # English version for better DDG/Bing

    # ── Fuente 1: DuckDuckGo Images ──────────────────────────────
    for q_try in [query, query_en] if query_en != query else [query]:
        if resultados:
            break
        try:
            q_safe = urllib.parse.quote(q_try)
            ddg_url = f"https://duckduckgo.com/i.js?q={q_safe}&o=json&s=0&u=bing&f=,,,,,&l=us-en"
            req = urllib.request.Request(
                ddg_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://duckduckgo.com/',
                    'Accept': 'application/json',
                }
            )
            with urllib.request.urlopen(req, timeout=8) as res:
                data = json.loads(res.read())
            for item in data.get("results", []):
                img_url = item.get("image", "")
                title = item.get("title", query)[:60]
                if img_url and any(img_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                    resultados.append(f"![{title}]({img_url})")
                    if len(resultados) >= 2:
                        break
        except Exception:
            pass

    # ── Fuente 2: Bing Images scraper ────────────────────────────
    if not resultados:
        for q_try in [query_en, query] if query_en != query else [query]:
            if resultados:
                break
            try:
                q_safe = urllib.parse.quote(q_try)
                bing_url = f"https://www.bing.com/images/search?q={q_safe}&form=HDRSC2&first=1"
                req = urllib.request.Request(
                    bing_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}
                )
                with urllib.request.urlopen(req, timeout=8) as res:
                    html = res.read().decode('utf-8', errors='ignore')
                matches = re.findall(r'"murl":"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', html)
                for img_url in matches:
                    resultados.append(f"![{query}]({img_url})")
                    if len(resultados) >= 2:
                        break
            except Exception:
                pass

    # ── Fuente 3: Wikimedia Commons ──────────────────────────────
    if not resultados:
        for q_try in [query, query_en] if query_en != query else [query]:
            if resultados:
                break
            try:
                q_safe = urllib.parse.quote(q_try)
                wm_url = (
                    f"https://commons.wikimedia.org/w/api.php?action=query"
                    f"&generator=search&gsrsearch={q_safe}&gsrnamespace=6"
                    f"&prop=imageinfo&iiprop=url|mime&format=json&gsrlimit=15"
                )
                req = urllib.request.Request(wm_url, headers={'User-Agent': 'Jarvis/2.0 (Bot)'})
                with urllib.request.urlopen(req, timeout=8) as res:
                    data = json.loads(res.read())
                for page in data.get("query", {}).get("pages", {}).values():
                    title = page.get("title", "").replace("File:", "").split(".")[0]
                    img_info = page.get("imageinfo", [{}])[0]
                    img_url = img_info.get("url", "")
                    mime = img_info.get("mime", "")
                    if img_url and mime in ("image/jpeg", "image/png", "image/webp"):
                        proxy_url = f"/api/v1/proxy-image?url={urllib.parse.quote(img_url, safe='')}"
                        resultados.append(f"![{title}]({proxy_url})")
                        if len(resultados) >= 2:
                            break
            except Exception:
                pass

    # ── Fuente 4: Wikipedia article thumbnail (GARANTIZADO) ──────
    # La API de Wikipedia siempre devuelve la imagen principal del artículo.
    # Es open-access y nunca bloquea. Cubre CUALQUIER tema indexado.
    if not resultados:
        for q_try in [query_en, query] if query_en != query else [query]:
            try:
                q_safe = urllib.parse.quote(q_try.replace(" ", "_"))
                wp_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{q_safe}"
                req = urllib.request.Request(
                    wp_url,
                    headers={'User-Agent': 'Jarvis/2.0 (educational bot; contact via GitHub)'}
                )
                with urllib.request.urlopen(req, timeout=8) as res:
                    data = json.loads(res.read())
                thumbnail = data.get("thumbnail", {}).get("source", "")
                original = data.get("originalimage", {}).get("source", thumbnail)
                img_url = original or thumbnail
                if img_url:
                    title = data.get("title", query)
                    proxy_url = f"/api/v1/proxy-image?url={urllib.parse.quote(img_url, safe='')}"
                    resultados.append(f"![{title}]({proxy_url})")
                    break
            except Exception:
                pass

        # ── Fuente 5: Wikipedia en español (último recurso) ──────
        if not resultados:
            try:
                q_safe = urllib.parse.quote(query.replace(" ", "_"))
                wp_url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{q_safe}"
                req = urllib.request.Request(
                    wp_url,
                    headers={'User-Agent': 'Jarvis/2.0 (educational bot)'}
                )
                with urllib.request.urlopen(req, timeout=8) as res:
                    data = json.loads(res.read())
                thumbnail = data.get("thumbnail", {}).get("source", "")
                if thumbnail:
                    title = data.get("title", query)
                    proxy_url = f"/api/v1/proxy-image?url={urllib.parse.quote(thumbnail, safe='')}"
                    resultados.append(f"![{title}]({proxy_url})")
            except Exception:
                pass

    # Wrap all image URLs with our proxy-image endpoint to bypass strict browser Tracking Prevention and CORS
    final_resultados = []
    for line in resultados:
        # Match markdown images: ![Alt](URL)
        import re
        match = re.search(r'!\[([^\]]*)\]\((.*?)\)', line)
        if match:
            alt = match.group(1)
            raw_url = match.group(2)
            # Avoid double proxying
            if "/api/v1/proxy-image" not in raw_url:
                proxy_url = f"{_BACKEND_URL}/api/v1/proxy-image?url={urllib.parse.quote(raw_url, safe='')}"
                final_resultados.append(f"![{alt}]({proxy_url})")
            else:
                final_resultados.append(line)
        else:
            final_resultados.append(line)

    if not final_resultados:
        # This should almost never happen — only for very obscure queries
        return (
            f"No pude obtener una imagen visual para '{query}'. "
            f"Intenta con términos más simples o en inglés."
        )

    return (
        "IMÁGENES ENCONTRADAS. INSTRUCCIÓN CRÍTICA Y OBLIGATORIA: DEBES copiar y pegar EXACTAMENTE los siguientes enlaces Markdown en tu respuesta para que el usuario pueda ver las imágenes. NO los modifiques, NO escribas solo el título, DEBES incluir los corchetes y paréntesis tal cual (ej. ![Título](URL)).\n\n"
        + "\n\n".join(final_resultados)
    )


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
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
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
