"""Web Agent PRO — Búsqueda y extracción real sin deadlocks."""
import asyncio
import urllib.request
import urllib.parse
import json
import re
from langchain_core.tools import tool

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
                prefix = f"INSTRUCCIÓN OBLIGATORIA: Muestra la siguiente imagen de vista previa en tu respuesta: ![Vista previa del sitio](https://api.microlink.io/?url={encoded_url}&screenshot=true&meta=false&embed=screenshot.url)\n\n"
            
            return prefix + "\n\n---\n\n".join(results)
        return _wiki_fallback(query)
    except Exception:
        return _wiki_fallback(query)

@tool
def web_search(query: str) -> str:
    """Busca en internet usando un buscador real y extrae el contenido de las páginas web más relevantes.
    Úsala SIEMPRE que el usuario te pida buscar algo en internet, información externa o reciente."""
    return _ddg_html_scraper(query)


@tool
def buscar_imagenes_web(query: str) -> str:
    """Busca imágenes, diagramas o infografías en la web sobre un tema educativo, científico o visual.
    Utiliza esta herramienta cuando el usuario quiera VER imágenes o ilustraciones sobre un concepto."""
    try:
        url = "https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=" + urllib.parse.quote(query) + "&gsrnamespace=6&prop=imageinfo&iiprop=url|size|mime&format=json&gsrlimit=3"
        req = urllib.request.Request(url, headers={'User-Agent': 'Jarvis/2.0 (Bot)'})
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read())
        
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return f"No se encontraron imágenes para '{query}'."
            
        resultados = []
        for page in pages.values():
            title = page.get("title", "").replace("File:", "").split(".")[0]
            img_info = page.get("imageinfo", [{}])[0]
            url_img = img_info.get("url", "")
            if url_img:
                resultados.append(f"**[{title}]({url_img})**\n![{title}]({url_img})")
                
        if not resultados:
            return f"No se pudieron extraer las URLs de las imágenes para '{query}'."
            
        return "INSTRUCCIÓN OBLIGATORIA: Muestra estas imágenes en tu respuesta exactamente así en formato Markdown:\n\n" + "\n\n".join(resultados)
    except Exception as e:
        return f"Error buscando imágenes: {str(e)}"

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
