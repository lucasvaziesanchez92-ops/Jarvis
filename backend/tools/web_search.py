"""Web Agent PRO — Búsqueda y extracción real usando duckduckgo-search y Wikipedia."""
import asyncio
import urllib.request
import urllib.parse
import json
from langchain_core.tools import tool

try:
    from duckduckgo_search import AsyncDDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

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

@tool
async def web_search(query: str) -> str:
    """Busca en internet usando un buscador real y extrae el contenido de las páginas web más relevantes.
    Úsala SIEMPRE que el usuario te pida buscar algo en internet, información externa o reciente."""
    try:
        if not HAS_DDGS:
            return await asyncio.get_event_loop().run_in_executor(None, _wiki_fallback, query)
            
        results = await AsyncDDGS().text(query, max_results=3)
        if not results:
            return await asyncio.get_event_loop().run_in_executor(None, _wiki_fallback, query)
            
        final_report = []
        for i, res in enumerate(results):
            title = res.get("title", "Sin Título")
            href = res.get("href", "")
            body = res.get("body", "Sin extracto")
            final_report.append(f"### Fuente {i+1}: {title} ({href})\n\n{body}")
            
        return "\n\n---\n\n".join(final_report)
    except Exception:
        # DDGS blocked or errored -> use Wiki fallback
        return await asyncio.get_event_loop().run_in_executor(None, _wiki_fallback, query)
