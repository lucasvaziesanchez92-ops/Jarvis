import os
from dotenv import load_dotenv
from sync_service import KnowledgeSyncService
from librarian import Librarian

# Load env variables (OLLAMA_PROVIDER, OLLAMA_MODEL_ID, etc)
load_dotenv()

def main():
    print("--- Jarvis LLM-Wiki System Starting ---")
    
    # 1. Initialize the Sync Service (Librarian + Watcher)
    sync_service = KnowledgeSyncService(base_path="data")
    
    # 2. First-time sync: Process existing files in sources/
    sync_service.sync_all()
    
    # 3. Start background watcher for real-time updates
    sync_service.start()
    
    # 4. Interactive Loop for testing the "Second Brain"
    librarian = sync_service.librarian
    print("\nJarvis is now connected to your Obsidian Knowledge Base.")
    print("You can now ask questions based on your notes. (Type 'exit' to quit)\n")
    
    try:
        while True:
            query = input("User: ")
            if query.lower() in ['exit', 'quit']:
                break
                
            print("\nJarvis is thinking (consulting the wiki)...")
            response = librarian.query_knowledge(query)
            print(f"\nJarvis: {response}\n")
            print("-" * 50)
            
    except KeyboardInterrupt:
        pass
    finally:
        sync_service.stop()
        print("\nSystem shutdown. Bye!")

if __name__ == "__main__":
    main()
