import os
import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from librarian import Librarian


class WikiWatcher(FileSystemEventHandler):
    def __init__(self, librarian: Librarian):
        self.librarian = librarian
        self._last_processed = {}
        self._debounce_seconds = 2

    def _should_process(self, path: str) -> bool:
        now = time.time()
        last = self._last_processed.get(path, 0)
        if now - last < self._debounce_seconds:
            return False
        self._last_processed[path] = now
        return True

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            if self._should_process(event.src_path):
                print(f"Watcher: File modified: {event.src_path}")
                self.librarian.ingest_source(Path(event.src_path))

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            if self._should_process(event.src_path):
                print(f"Watcher: New file detected: {event.src_path}")
                self.librarian.ingest_source(Path(event.src_path))


class KnowledgeSyncService:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.sources_path = self.base_path / "sources"
        self.librarian = Librarian(base_path)
        self.observer = Observer()

    def start(self):
        if not self.sources_path.exists():
            self.sources_path.mkdir(parents=True)

        event_handler = WikiWatcher(self.librarian)
        self.observer.schedule(event_handler, str(self.sources_path), recursive=True)
        self.observer.start()
        print(f"KnowledgeSyncService: Monitoring {self.sources_path}...")

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def sync_all(self):
        print("KnowledgeSyncService: Performing full sync...")
        sources = self.librarian.engine.get_all_sources()
        for source in sources:
            self.librarian.ingest_source(source)
        print(f"KnowledgeSyncService: Synced {len(sources)} files.")