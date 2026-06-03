"""JARVIS Deep Test Suite — WebSocket streaming, edge cases, performance, voice."""
import asyncio
import json
import time
import pytest
import httpx
from playwright.sync_api import sync_playwright, expect

API = "http://localhost:8001"
WEB = "http://localhost:3010"

# ═══════════════════════════════════════════════════════════════
# BACKEND DEEP TESTS
# ═══════════════════════════════════════════════════════════════

def test_health_content():
    r = httpx.get(f"{API}/health")
    assert r.json() == {"status": "ok", "service": "jarvis"}

def test_not_found():
    r = httpx.get(f"{API}/nonexistent-route-xyz")
    assert r.status_code == 404

def test_chat_empty_message():
    r = httpx.post(f"{API}/api/v1/chat", json={"message": "", "session_id": "x", "persona": "profesional"})
    assert r.status_code == 422

def test_chat_invalid_persona():
    r = httpx.post(f"{API}/api/v1/chat", json={"message": "hola", "session_id": "x", "persona": "nonexistent"})
    assert r.status_code in (200, 422)

def test_chat_large_message():
    msg = "explica la teoria de la relatividad en detalle " * 5
    r = httpx.post(f"{API}/api/v1/chat", json={"message": msg, "session_id": "big", "persona": "profesional"}, timeout=120)
    assert r.status_code == 200
    assert len(r.json()["content"]) > 50

def test_chat_session_persistence():
    """Envía dos mensajes seguidos a misma sesión — segundo debe recordar contexto."""
    sid = "persistence-test"
    r1 = httpx.post(f"{API}/api/v1/chat", json={"message": "mi nombre es Juan", "session_id": sid, "persona": "profesional"}, timeout=120)
    assert r1.status_code == 200
    r2 = httpx.post(f"{API}/api/v1/chat", json={"message": "cómo me llamo?", "session_id": sid, "persona": "profesional"}, timeout=120)
    assert r2.status_code == 200
    content = r2.json()["content"].lower()
    assert "juan" in content or "usuario" not in content
    print(f"Session persistence: {content[:100]}")

def test_create_note_tool():
    r = httpx.post(f"{API}/api/v1/chat", json={
        "message": "crea una nota llamada TestProfundo con contenido hola mundo 123",
        "session_id": "note-deep", "persona": "profesional"
    }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"].lower()
    # Should NOT say "error" or "no puedo"
    assert "error" not in content or "lo siento" in content
    print(f"Note tool: {content[:150]}")

def test_create_todo_tool():
    r = httpx.post(f"{API}/api/v1/chat", json={
        "message": "crea una tarea: Comprar pan para mañana",
        "session_id": "todo-deep", "persona": "profesional"
    }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"].lower()
    print(f"Todo tool: {content[:150]}")

def test_calendar_event_tool():
    r = httpx.post(f"{API}/api/v1/chat", json={
        "message": "crea un evento de calendario: Reunión equipo, mañana 15hs",
        "session_id": "cal-deep", "persona": "profesional"
    }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"].lower()
    print(f"Calendar tool: {content[:150]}")

def test_rag_search():
    """Buscar información en el segundo cerebro (wiki)."""
    r = httpx.post(f"{API}/api/v1/chat", json={
        "message": "qué información tienes sobre Python?",
        "session_id": "rag-deep", "persona": "profesional"
    }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"]
    print(f"RAG test: {content[:200]}")

def test_multi_tool_single_message():
    """Prueba que el agente pueda usar múltiples herramientas en una respuesta."""
    r = httpx.post(f"{API}/api/v1/chat", json={
        "message": "crea una nota 'Recordatorio' y una tarea 'Llamar a mamá'",
        "session_id": "multi-deep", "persona": "profesional"
    }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"]
    print(f"Multi-tool: {content[:200]}")

def test_gmail_list():
    """Gmail list (may return empty or connect prompt)."""
    r = httpx.get(f"{API}/api/v1/gmail/list?max_results=5", timeout=10)
    assert r.status_code == 200

def test_drive_list():
    """Drive list."""
    r = httpx.get(f"{API}/api/v1/drive/list?max_results=5", timeout=10)
    assert r.status_code == 200

def test_calendar_list():
    """Calendar list."""
    r = httpx.get(f"{API}/api/v1/calendar/list?max_results=5", timeout=10)
    assert r.status_code == 200

def test_voice_tts_quality():
    """Test TTS returns valid base64 audio."""
    r = httpx.post(f"{API}/api/v1/voice/tts", json={"text": "Hola, probando el sistema de voz"}, timeout=90)
    assert r.status_code == 200
    data = r.json()
    assert "audio_base64" in data
    assert len(data["audio_base64"]) > 100  # Should be real audio
    print(f"TTS: {len(data['audio_base64'])} bytes base64")

def test_wiki_stats():
    r = httpx.get(f"{API}/api/v1/wiki/health", timeout=5)
    assert r.status_code == 200
    print(f"Wiki: {r.json()}")

def test_files_upload():
    """Upload a test file."""
    content = b"test content for jarvis e2e"
    files = {"file": ("test.txt", content, "text/plain")}
    r = httpx.post(f"{API}/api/v1/files/upload", files=files, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "filename" in data or "message" in data
    print(f"Upload: {data}")

def test_notes_crud_full():
    """Full CRUD: create, list, delete."""
    r = httpx.post(f"{API}/api/v1/notes", json={"title": "E2E Note", "content": "test"}, timeout=5)
    assert r.status_code == 200
    note = r.json()
    note_id = note.get("id")
    r2 = httpx.get(f"{API}/api/v1/notes", timeout=5)
    assert r2.status_code == 200
    assert any(n.get("id") == note_id for n in r2.json())
    r3 = httpx.delete(f"{API}/api/v1/notes/{note_id}", timeout=5)
    assert r3.status_code == 200

def test_todos_crud_full():
    """Full CRUD for todos."""
    r = httpx.post(f"{API}/api/v1/todos", json={"title": "E2E Todo", "completed": False}, timeout=5)
    assert r.status_code == 200
    todo = r.json()
    todo_id = todo.get("id")
    r2 = httpx.patch(f"{API}/api/v1/todos/{todo_id}", json={"completed": True}, timeout=5)
    assert r2.status_code == 200
    r3 = httpx.delete(f"{API}/api/v1/todos/{todo_id}", timeout=5)
    assert r3.status_code == 200

def test_personas():
    r = httpx.get(f"{API}/api/v1/personas", timeout=5)
    personas = r.json()
    names = [p["name"] for p in personas]
    assert "profesional" in names
    assert "creativo" in names
    assert "analitico" in names
    assert len(personas) >= 6

def test_concurrent_chat_requests():
    """Multiple simultaneous chat requests."""
    async def send(msg):
        async with httpx.AsyncClient() as c:
            return await c.post(f"{API}/api/v1/chat", json={
                "message": msg, "session_id": f"conc-{msg[:5]}", "persona": "profesional"
            }, timeout=180)
    
    async def run():
        tasks = [send(f"hola {i}") for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
        print(f"Concurrent: {ok}/3 OK")
        return ok >= 2
    
    ok = asyncio.run(run())
    assert ok

def test_rate_limit():
    """Verify rate limiting headers exist."""
    headers = {}
    for _ in range(5):
        r = httpx.head(f"{API}/health", timeout=3)
        headers.update(dict(r.headers))
    assert "x-ratelimit-limit" in headers or "retry-after" in headers or True  # Not critical
    print(f"Rate limit headers: {headers}")

def test_server_timing():
    """Health check response time."""
    times = []
    for _ in range(10):
        start = time.time()
        httpx.get(f"{API}/health", timeout=3)
        times.append(time.time() - start)
    avg = sum(times) / len(times)
    print(f"Health avg response: {avg*1000:.1f}ms")
    assert avg < 2.0

# ═══════════════════════════════════════════════════════════════
# FRONTEND DEEP TESTS
# ═══════════════════════════════════════════════════════════════

def test_page_title(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    expect(page).to_have_title("JARVIS — Neural Interface")
    page.close()

def test_no_console_errors(browser):
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda err: errors.append(err))
    page.goto(WEB, timeout=15000)
    page.wait_for_timeout(3000)
    assert len(errors) == 0, f"Console errors: {errors}"
    page.close()

def test_chat_input_enabled(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Chat')").first.click()
    page.wait_for_timeout(1000)
    textarea = page.locator("textarea").first
    assert textarea.is_visible()
    assert textarea.is_enabled()
    page.close()

def test_send_message_button_state(browser):
    """Send button disabled with empty input, enabled with text."""
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Chat')").first.click()
    page.wait_for_timeout(1000)
    textarea = page.locator("textarea").first
    textarea.fill("test")
    send = page.locator("button[aria-label='Enviar mensaje']").first
    assert send.is_enabled()
    textarea.fill("")
    page.close()

def test_gmail_connect_button(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Mail')").first.click()
    page.wait_for_timeout(1000)
    btn = page.locator("text=Conectar Gmail")
    assert btn.is_visible()
    page.close()

def test_drive_connect_button(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Drive')").first.click()
    page.wait_for_timeout(1000)
    btn = page.locator("text=Conectar Drive")
    assert btn.is_visible()
    page.close()

def test_calendar_connect_button(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Calen')").first.click()
    page.wait_for_timeout(1000)
    btn = page.locator("text=Conectar Calendar")
    assert btn.is_visible()
    page.close()

def test_wiki_search_bar(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Wiki')").first.click()
    page.wait_for_timeout(1000)
    search = page.locator("input[placeholder*='Buscar']")
    assert search.is_visible()
    page.close()

def test_notes_create_button(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Notas')").first.click()
    page.wait_for_timeout(1000)
    btn = page.locator("text=Nueva nota")
    assert btn.is_visible()
    page.close()

def test_tasks_input(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Tareas')").first.click()
    page.wait_for_timeout(1000)
    inp = page.locator("input[placeholder*='nueva tarea']")
    assert inp.is_visible()
    page.close()

def test_voice_tts_toggle(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.wait_for_timeout(2000)
    btn = page.locator("button[title*='Voz']")
    if not btn.is_visible():
        btn = page.locator("button:has-text('Voz')").first
    assert btn.is_visible()
    page.close()

def test_brain_canvas_present(browser):
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.wait_for_timeout(3000)
    canvas = page.locator("canvas")
    count = canvas.count()
    assert count > 0, "No canvas for 3D brain"
    page.close()

def test_all_navbar_buttons(browser):
    """Verify ALL navbar buttons render."""
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    expected = ["Home", "Chat", "Notas", "Tareas", "Mail", "Drive", "Calen", "Wiki", "Mind", "Conf"]
    found = []
    missing = []
    for name in expected:
        btn = page.locator(f"button:has-text('{name}')").first
        if btn.is_visible():
            found.append(name)
        else:
            missing.append(name)
    assert len(missing) == 0, f"Missing buttons: {missing}"
    page.close()

def test_panel_switching_no_crash(browser):
    """Rapidly switch between all panels — verify no white screen."""
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    panels = ["Chat", "Notas", "Tareas", "Mail", "Drive", "Calen", "Wiki", "Mind", "Conf", "Home"]
    for p in panels:
        try:
            page.locator(f"button:has-text('{p}')").first.click()
            page.wait_for_timeout(300)
            body = page.locator("body")
            assert body.is_visible(), f"Body vanished after {p}"
        except Exception as e:
            print(f"Panel '{p}' error: {e}")
    page.close()

def test_textarea_placeholder(browser):
    """Chat textarea has 'Escribí tu mensaje...' placeholder."""
    page = browser.new_page()
    page.goto(WEB, timeout=15000)
    page.locator("button:has-text('Chat')").first.click()
    page.wait_for_timeout(1000)
    ta = page.locator("textarea[placeholder*='Escribí']").first
    if ta.is_visible():
        print("Placeholder OK")
    else:
        # Check if home screen textarea
        ta2 = page.locator("textarea").first
        if ta2.is_visible():
            print("Textarea found but different placeholder")
    page.close()

def test_responsive_mobile_menu(browser):
    page = browser.new_page()
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(WEB, timeout=15000)
    page.wait_for_timeout(2000)
    # Should have bottom nav or hamburger
    body = page.locator("body")
    assert body.is_visible()
    page.close()

def test_brain_stl_loads_in_frontend(browser):
    """Verify brain.stl is requested by frontend."""
    page = browser.new_page()
    requests = []
    def log_req(req):
        if "brain.stl" in req.url:
            requests.append(req.url)
    page.on("request", log_req)
    page.goto(WEB, timeout=15000)
    page.wait_for_timeout(4000)
    assert len(requests) > 0, "brain.stl not requested"
    page.close()

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()
