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
    """Scrapes DDG HTML lite directly using urllib to avoid curl_cffi deadlocks."""
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode('utf-8', errors='ignore')
            
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
                    proxy_url = f"{_BACKEND_URL}/api/v1/proxy-image?url={urllib.parse.quote(img_url, safe='')}"
                    resultados.append(f"![{title}]({proxy_url})")
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
                    proxy_url = f"{_BACKEND_URL}/api/v1/proxy-image?url={urllib.parse.quote(img_url, safe='')}"
                    resultados.append(f"![{query}]({proxy_url})")
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
                        resultados.append(f"![{title}]({img_url})")
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
                    # Wikipedia images are open-access, no proxy needed
                    resultados.append(f"![{title}]({img_url})")
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
                    resultados.append(f"![{title}]({thumbnail})")
            except Exception:
                pass

    if not resultados:
        # This should almost never happen — only for very obscure queries
        return (
            f"No pude obtener una imagen visual para '{query}'. "
            f"Intenta con términos más simples o en inglés."
        )

    return (
        "CRITICO: Encontraste imágenes reales. DEBES copiar e incluir estos bloques Markdown EXACTAMENTE "
        "en tu respuesta final sin modificarlos. Una frase introductoria y luego las imágenes:\n\n"
        + "\n\n".join(resultados)
    )


@tool
def buscar_reversa_gratis(attachment_key: str) -> str:
    """Búsqueda inversa de imágenes en internet (Google Lens).
    Usa esta herramienta SIEMPRE que el usuario te pida buscar el origen de una imagen que subió, o analizar un screenshot/foto local buscando coincidencias en la web.
    Argumentos:
        attachment_key: La clave (key) del archivo adjunto subido por el usuario (suele venir en tu prompt junto al archivo).
    """
    import io
    import requests
    import re
    import json
    from backend.core.storage import download_bytes

    try:
        datos_binarios = download_bytes(attachment_key)
    except Exception as e:
        return f"Error al leer la imagen subida: {str(e)}"

    url_lens = "https://lens.google.com/v3/upload"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    archivo_virtual = io.BytesIO(datos_binarios)
    files = {
        "encoded_image": ("screenshot.jpg", archivo_virtual, "image/jpeg")
    }
    
    try:
        response = requests.post(url_lens, headers=headers, files=files, timeout=10)
        if response.status_code != 200:
            return f"Error al conectar con Google Lens: Status {response.status_code}"
            
        # Parse output using provided logic
        patron = r'AF_initDataCallback\s*\(\s*\{\s*key:\s*[\'"]ds:1[\'"].*?data:\s*(\[.+?\])\s*,\s*sideChannel:\s*\{'
        match = re.search(patron, response.text, re.DOTALL)
        if not match:
            return "No se encontraron coincidencias visuales (falló el parser de Lens)."
            
        data_raw = json.loads(match.group(1))
        
        try:
            coincidencias_visuales = data_raw[1][1][1][8][8][0][12]
        except (IndexError, TypeError):
            return "El formato de respuesta de Google Lens cambió. No se pudo extraer la lista visual."

        resultados_limpios = []
        for item in coincidencias_visuales:
            try:
                titulo = item[3]
                url_fuente = item[2]
                url_miniatura = item[0][0]
                nombre_sitio = item[1][0] if item[1] else "Fuente Web"
                
                resultados_limpios.append({
                    "titulo": f"[{nombre_sitio}] {titulo}",
                    "url_directa": url_fuente,
                    "url_imagen": url_miniatura
                })
            except (IndexError, TypeError):
                continue
                
        if not resultados_limpios:
            return "Lo siento, no encontré coincidencias visuales exactas para esta imagen en internet."
            
        md = "INSTRUCCIÓN OBLIGATORIA: Muestra exactamente los siguientes resultados de búsqueda inversa al usuario usando Markdown:\n\n### 🔍 Resultados de la Búsqueda Inversa:\n\n"
        for res in resultados_limpios[:5]:
            md += f"🔹 **[{res['titulo']}]({res['url_directa']})**\n"
            md += f"![vista_previa]({res['url_imagen']})\n\n"
            
        return md
        
    except Exception as e:
        return f"Error procesando la búsqueda visual inversa: {str(e)}"
