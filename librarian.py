import os
import re
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from knowledge_engine import KnowledgeEngine
from backend.config import settings
from backend.llm import get_llm


class Librarian:
    def __init__(self, base_path: str = "data"):
        self.engine = KnowledgeEngine(base_path)
        # Usamos el LLM centralizado en lugar de hardcodear Ollama
        self.llm = get_llm()
        self.schema_path = Path(base_path) / "schema.md"
        self._cached_schema = None

    def _get_system_prompt(self) -> str:
        if self._cached_schema is None:
            self._cached_schema = self.schema_path.read_text(encoding="utf-8")
        return (
            "You are the Librarian of a persistent Knowledge Wiki. Your goal is to maintain "
            "a compounding, interlinked collection of markdown files.\n\n"
            f"### WIKI SCHEMA & RULES:\n{self._cached_schema}\n\n"
            "Your task is to process new information and decide how it updates the existing wiki."
        )

    def _chat(self, prompt: str) -> str:
        # Usamos el LLM centralizado para mantener coherencia
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=prompt)
        ]
        response = self.llm.invoke(messages)
        return response.content

    def ingest_source(self, file_path: Path):
        print(f"Librarian: Ingesting {file_path.name}...")
        text = self.engine.read_file(file_path)

        prompt = (
            f"I have a new source document: {file_path.name}\n"
            f"Content:\n{text}\n\n"
            "Based on the Wiki Schema, identify:\n"
            "1. Key Entities to create or update.\n"
            "2. Core Concepts to refine.\n"
            "3. New Synthesis pages needed.\n\n"
            "For each item, output EXACTLY this format (no code blocks):\n\n"
            "CREATE [[PageName]]\n<markdown content>\n---\n\n"
            "or\n\n"
            "UPDATE [[PageName]]\n<markdown content to append>\n---\n\n"
            "Separate EVERY page with --- on its own line.\n"
            "Make sure every page uses [[wikilinks]] to connect related concepts."
        )

        analysis = self._chat(prompt)
        self._apply_wiki_updates(analysis)
        self.engine.update_log(f"ingest | {file_path.name} processed and wiki updated.")
        print(f"Librarian: Finished processing {file_path.name}.")

    def _apply_wiki_updates(self, analysis: str):
        updates = []

        blocks = re.split(r'\n---\n|\r\n---\r\n', analysis)
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            match = re.match(r'(CREATE|UPDATE)\s+\[\[(.*?)\]\]', block)
            if not match:
                continue

            action = match.group(1)
            page_name = match.group(2).strip()

            content_match = re.search(r'```(?:markdown|md)?\s*\n(.*?)```', block, re.DOTALL)
            if content_match:
                content = content_match.group(1).strip()
            else:
                after_header = block[match.end():]
                lines = after_header.strip().splitlines()
                clean_lines = [l for l in lines if l.strip() and l.strip() != '---']
                content = '\n'.join(clean_lines).strip()

            if content:
                updates.append((action, page_name, content))

        if not updates:
            self.engine.save_wiki_page("Unparsed_Synthesis", analysis)
            self.engine.update_index("Unparsed_Synthesis", "Raw synthesis from Librarian.")
            return

        for action, page_name, content in updates:
            safe_name = re.sub(r'[<>:"/\\|?*]', '', page_name).strip()
            if safe_name.endswith('.md'):
                safe_name = safe_name[:-3]
            if not safe_name:
                continue

            if safe_name in ('index', 'log'):
                continue

            if action == "CREATE":
                self.engine.save_wiki_page(safe_name, content)
                self._sync_wiki_to_vector(safe_name, content)
                for line in content.split('\n'):
                    line = line.strip().lstrip('#').strip()
                    if line and not line.startswith('```') and not line.startswith('|') and len(line) > 10:
                        self.engine.update_index(safe_name, line[:80])
                        break
            elif action == "UPDATE":
                page_path = self.engine.wiki_path / f"{safe_name}.md"
                if page_path.exists():
                    existing = page_path.read_text(encoding="utf-8")
                    self.engine.save_wiki_page(safe_name, existing + "\n\n" + content)
                else:
                    self.engine.save_wiki_page(safe_name, content)
                    for line in content.split('\n'):
                        line = line.strip().lstrip('#').strip()
                        if line and not line.startswith('```') and not line.startswith('|') and len(line) > 10:
                            self.engine.update_index(safe_name, line[:80])
                            break
                self._sync_wiki_to_vector(safe_name, content)

    def _sync_wiki_to_vector(self, page_name: str, content: str):
        """Sync wiki page to ChromaDB vector store. Non-blocking if Chroma fails."""
        try:
            from backend.service.vector_service import index_wiki_page
            index_wiki_page(page_name=page_name, content=content, source_file=f"wiki/{page_name}.md")
        except Exception as e:
            print(f"Librarian: Vector sync failed for wiki page {page_name}: {e}")

    def query_knowledge(self, query_text: str) -> str:
        """
        Versión de GRAFO: Identifica páginas relevantes, extrae su contenido 
        Y sus conexiones [[links]] para que el agente navegue por el cerebro.
        """
        index_path = self.engine.wiki_path / "index.md"
        if not index_path.exists():
            return "Wiki index not found. No knowledge available."
            
        index_content = index_path.read_text(encoding="utf-8")

        navigation_prompt = (
            f"User Query: {query_text}\n\n"
            f"Wiki Index:\n{index_content}\n\n"
            "Based on the index, which [[PageNames]] from the wiki are most relevant to answer this? "
            "Return only the list of page names, one per line, without brackets. If none, say 'NONE'."
        )
        
        nav_response = self._chat(navigation_prompt)
        pages_to_read = nav_response.strip().splitlines()

        collected_context = []
        all_found_links = set()

        for page in pages_to_read:
            page_name = page.strip().strip("[]")
            if page_name.upper() == "NONE" or not page_name:
                continue

            safe_name = re.sub(r'[<>:"/\\|?*]', '', page_name).strip()
            if safe_name.endswith('.md'):
                safe_name = safe_name[:-3]
            
            page_path = self.engine.wiki_path / f"{safe_name}.md"
            if page_path.exists():
                content = page_path.read_text(encoding='utf-8')
                # EXTRAER NODOS CONECTADOS
                links = re.findall(r'\[\[(.*?)\]\]', content)
                all_found_links.update(links)
                
                context_block = (
                    f"--- NODE: [[{page_name}]] ---\n"
                    f"{content}\n"
                    f"CONNECTED NODES: {', '.join([f'[[{l}]]' for l in links])}\n"
                )
                collected_context.append(context_block)

        if not collected_context:
            return "No specific wiki nodes were found for this query in the local brain."
            
        final_output = "\n\n".join(collected_context)
        
        # Añadimos una sugerencia de navegación si hay muchos links
        if all_found_links:
            suggestions = [l for l in all_found_links if l not in [p.strip().strip("[]") for p in pages_to_read]]
            if suggestions:
                final_output += f"\n\nSUGGESTED NODES TO EXPLORE: {', '.join([f'[[{s}]]' for s in suggestions[:5]])}"

        return final_output