"""Web Agent PRO — Búsqueda y extracción real (Zero-Cost)."""
import asyncio
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from langchain_core.tools import tool

def _run_sync_search(query: str) -> str:
    def clean_html(html_content: bytes) -> str:
        soup = BeautifulSoup(html_content, "html.parser")
        for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
            s.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
        return "\n".join(lines[:50])

    try:
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            
        soup = BeautifulSoup(html, "html.parser")
        results = soup.select("a.result-url")
        
        urls = []
        for r in results:
            href = r.get("href")
            if href and href.startswith("http"):
                urls.append(href)
            if len(urls) >= 3:
                break
                
        if not urls:
            return f"No se encontraron resultados externos para '{query}'."
            
        final_report = []
        for i, u in enumerate(urls):
            try:
                req_page = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req_page, timeout=10) as res:
                    page_html = res.read()
                content = clean_html(page_html)
                final_report.append(f"### Fuente {i+1}: {u}\n\n{content}")
            except Exception as e:
                final_report.append(f"### Fuente {i+1}: {u}\n\nError al acceder: {str(e)}")
                
        return "\n\n---\n\n".join(final_report)
    except Exception as e:
        return f"Error crítico durante la navegación: {str(e)}"

@tool
async def web_search(query: str) -> str:
    """Busca en internet y extrae el contenido de las páginas web más relevantes.
    Úsala para investigación profunda sin APIs externas."""
    return await asyncio.get_event_loop().run_in_executor(None, _run_sync_search, query)
