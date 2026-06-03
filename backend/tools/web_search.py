"""Web Agent PRO — Búsqueda y extracción real mediante Playwright (Zero-Cost)."""
from langchain_core.tools import tool
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import random

def clean_html(html_content: str) -> str:
    """Limpia el HTML para extraer solo el texto relevante."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Eliminar elementos innecesarios
    for script_or_style in soup(["script", "style", "nav", "footer", "header", "aside"]):
        script_or_style.decompose()
        
    # Obtener texto y limpiar espacios
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
    return "\n".join(lines[:50]) # Limitar a las primeras 50 líneas significativas

@tool
def web_search(query: str) -> str:
    """Busca en internet usando un navegador real (Playwright).
    Navega por los resultados, extrae el contenido de las páginas y retorna un resumen técnico.
    Úsala para investigación profunda sin APIs externas."""
    
    print(f"WebAgent: Iniciando búsqueda para '{query}'...")
    
    with sync_playwright() as p:
        # Lanzamos el navegador
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 1. Buscar en DuckDuckGo Lite (Puro HTML, muy fiable para scraping)
            search_url = f"https://duckduckgo.com/lite/?q={query.replace(' ', '+')}"
            page.goto(search_url, wait_until="load", timeout=20000)
            
            # 2. Extraer los links de los resultados
            # En Lite, los resultados están en tablas o celdas con la clase .result-link
            links = page.query_selector_all("a.result-link")
            urls = [link.get_attribute("href") for link in links[:3] if link.get_attribute("href")]
            
            if not urls:
                # Intento alternativo por si las clases cambian
                all_links = page.query_selector_all("a")
                urls = []
                for link in all_links:
                    href = link.get_attribute("href")
                    # Filtramos links de navegación de DDG
                    if href and href.startswith("http") and "duckduckgo.com" not in href:
                        urls.append(href)
                    if len(urls) >= 3:
                        break
            
            if not urls:
                return f"No se encontraron resultados externos para '{query}'."
            
            final_report = []
            
            # 3. Visitar cada URL y extraer contenido
            for i, url in enumerate(urls):
                print(f"WebAgent: Extrayendo contenido de {url}...")
                try:
                    page.goto(url, wait_until="load", timeout=10000)
                    time.sleep(random.uniform(1, 2)) # Evitar detección
                    
                    content = clean_html(page.content())
                    final_report.append(f"### Fuente {i+1}: {url}\n\n{content}")
                except Exception as e:
                    final_report.append(f"### Fuente {i+1}: {url}\n\nError al acceder: {str(e)}")
            
            return "\n\n---\n\n".join(final_report)
            
        except Exception as e:
            return f"Error crítico durante la navegación: {str(e)}"
        finally:
            browser.close()
