from backend.tools.web_search import web_search

def test_search():
    print("Testing Playwright Search...")
    result = web_search.invoke({"query": "Qué es el patrón Circuit Breaker"})
    print("\n--- Search Result ---")
    print(result[:1000]) # First 1000 chars

if __name__ == "__main__":
    test_search()
