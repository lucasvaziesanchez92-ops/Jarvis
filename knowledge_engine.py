import os
import re
from pathlib import Path
from typing import List, Dict, Any


class KnowledgeEngine:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.sources_path = self.base_path / "sources"
        self.wiki_path = self.base_path / "wiki"

        vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")
        if vault_path and Path(vault_path).exists():
            self.sources_path = Path(vault_path)

        self.sources_path.mkdir(parents=True, exist_ok=True)
        self.wiki_path.mkdir(parents=True, exist_ok=True)

    def get_all_sources(self) -> List[Path]:
        return list(self.sources_path.glob("**/*.md"))

    def read_file(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8")

    def semantic_chunk(self, text: str) -> List[Dict[str, Any]]:
        chunks = []
        pattern = r'(^#+\s+.*)'
        parts = re.split(pattern, text, flags=re.MULTILINE)

        current_header = "Introduction"
        for part in parts:
            if not part.strip():
                continue
            if part.startswith('#'):
                current_header = part.strip('#').strip()
            else:
                chunks.append({
                    "header": current_header,
                    "content": part.strip()
                })

        if not chunks and text.strip():
            chunks.append({"header": "General", "content": text.strip()})

        return chunks

    def extract_links(self, text: str) -> List[str]:
        return re.findall(r'\[\[(.*?)\]\]', text)

    def save_wiki_page(self, page_name: str, content: str):
        safe_name = re.sub(r'[<>:"/\\|?*]', '', page_name).strip()
        if not safe_name:
            return
        if safe_name.endswith('.md'):
            safe_name = safe_name[:-3]
        file_path = self.wiki_path / f"{safe_name}.md"
        file_path.write_text(content, encoding="utf-8")

    def update_log(self, entry: str):
        log_path = self.wiki_path / "log.md"
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n## [{date_str}] {entry}")

    def update_index(self, page_name: str, summary: str):
        index_path = self.wiki_path / "index.md"
        content = index_path.read_text(encoding="utf-8")

        clean_summary = summary.lstrip('#').strip()
        entry = f"- [[{page_name}]]: {clean_summary}"

        if f"[[{page_name}]]" in content:
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if f"[[{page_name}]]" in line:
                    new_lines.append(entry)
                else:
                    new_lines.append(line)
            content = "\n".join(new_lines)
        else:
            placeholder = "- No entities indexed yet."
            if placeholder in content:
                content = content.replace(placeholder, entry)
            elif "## Entities" in content:
                insert_pos = content.find("## Entities") + len("## Entities")
                content = content[:insert_pos] + "\n" + entry + content[insert_pos:]
            else:
                content += f"\n\n## Entities\n{entry}"

        index_path.write_text(content, encoding="utf-8")