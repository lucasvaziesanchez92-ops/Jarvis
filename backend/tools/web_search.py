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
            snippet_match = re.search(r'<a class="result__snippet[^>]*>(.*?)</a>', block, re.IGNORECASE | re.DOTALL)
            
            if title_match and snippet_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                body = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                results.append(f"### Fuente {len(results)+1}: {title}\n\n{body}")
                
            if len(results) >= 3:
                break
                
        if results:
            return "\n\n---\n\n".join(results)
        return _wiki_fallback(query)
    except Exception:
        return _wiki_fallback(query)

@tool
def web_search(query: str) -> str:
    """Busca en internet usando un buscador real y extrae el contenido de las páginas web más relevantes.
    Úsala SIEMPRE que el usuario te pida buscar algo en internet, información externa o reciente."""
    return _ddg_html_scraper(query)
