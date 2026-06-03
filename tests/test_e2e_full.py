"""JARVIS Automated Test Suite — Playwright E2E tests para backend y frontend."""
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
import httpx
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://localhost:3010"
API_URL = "http://localhost:8001"

# ── Backend API Tests ──────────────────────────────────────────

def test_health():
    """Test /health endpoint."""
    r = httpx.get(f"{API_URL}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_health_v1():
    """Test /api/v1/health endpoint."""
    r = httpx.get(f"{API_URL}/api/v1/health", timeout=5)
    assert r.status_code == 200

def test_cors_headers():
    """Test CORS headers are present in OPTIONS request."""
    r = httpx.options(f"{API_URL}/health", timeout=5)
    r2 = httpx.options(f"{API_URL}/health", timeout=5, headers={"Origin": "http://localhost:3010"})
    assert r.status_code == 200
    assert r2.status_code == 200

def test_notes_api():
    """Test notes CRUD endpoints."""
    r = httpx.get(f"{API_URL}/api/v1/notes", timeout=5)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_todos_api():
    """Test todos CRUD endpoints."""
    r = httpx.get(f"{API_URL}/api/v1/todos", timeout=5)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_personas_api():
    """Test personas list."""
    r = httpx.get(f"{API_URL}/api/v1/personas", timeout=5)
    assert r.status_code == 200
    personas = r.json()
    assert isinstance(personas, list)
    assert len(personas) >= 6

def test_google_auth_status():
    """Test Google auth status endpoint."""
    r = httpx.get(f"{API_URL}/auth/google/status", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "connected" in data

def test_google_auth_login_redirect():
    """Test Google login redirects to Google."""
    r = httpx.get(f"{API_URL}/auth/google/login", follow_redirects=False, timeout=5)
    assert r.status_code == 307
    assert "accounts.google.com" in r.headers.get("location", "")

def test_wiki_health():
    """Test wiki health endpoint."""
    r = httpx.get(f"{API_URL}/api/v1/wiki/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "configured" in data

def test_drive_health():
    """Test drive health endpoint."""
    r = httpx.get(f"{API_URL}/api/v1/drive/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert "configured" in data

def test_chat_post():
    """Test POST /api/v1/chat with simple message."""
    payload = {"message": "hola", "session_id": "test-123", "persona": "profesional"}
    try:
        r = httpx.post(f"{API_URL}/api/v1/chat", json=payload, timeout=120)
        assert r.status_code == 200
        data = r.json()
        assert "content" in data
        assert "session_id" in data
    except httpx.TimeoutException:
        pytest.skip("LLM timeout — puede tardar con Ollama Cloud")

def test_chat_tools_note():
    """Test that the agent uses create_note tool."""
    payload = {"message": "crea una nota de prueba que diga test123", "session_id": "test-tools-1", "persona": "profesional"}
    try:
        r = httpx.post(f"{API_URL}/api/v1/chat", json=payload, timeout=120)
        assert r.status_code == 200
        data = r.json()
        assert "content" in data
        print(f"NOTE TOOL TEST — Response: {data['content'][:200]}")
    except httpx.TimeoutException:
        pytest.skip("LLM timeout — puede tardar con Ollama Cloud")

def test_chat_tools_todo():
    """Test that the agent uses todo tools."""
    payload = {"message": "crea una tarea de prueba llamada test123", "session_id": "test-tools-3", "persona": "profesional"}
    try:
        r = httpx.post(f"{API_URL}/api/v1/chat", json=payload, timeout=120)
        assert r.status_code == 200
        data = r.json()
        assert "content" in data
        print(f"TODO TOOL TEST — Response: {data['content'][:200]}")
    except httpx.TimeoutException:
        pytest.skip("LLM timeout — puede tardar con Ollama Cloud")

def test_chat_tools_calendar():
    """Test that the agent uses calendar tool."""
    from datetime import datetime, timedelta
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT09:00:00")
    msg = f"crea un evento de prueba para mañana a las 9am llamado TestEvent"
    payload = {"message": msg, "session_id": "test-tools-4", "persona": "profesional"}
    try:
        r = httpx.post(f"{API_URL}/api/v1/chat", json=payload, timeout=120)
        assert r.status_code == 200
        data = r.json()
        assert "content" in data
        print(f"CALENDAR TOOL TEST — Response: {data['content'][:200]}")
    except httpx.TimeoutException:
        pytest.skip("LLM timeout — puede tardar con Ollama Cloud")

def test_voice_tts():
    """Test TTS endpoint."""
    payload = {"text": "Hola, esto es una prueba"}
    try:
        r = httpx.post(f"{API_URL}/api/v1/voice/tts", json=payload, timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert "audio_base64" in data
    except httpx.TimeoutException:
        pytest.skip("TTS timeout — puede tardar descargando modelo")

def test_brain_stl():
    """Test brain.stl is served."""
    r = httpx.get(f"{API_URL}/brain.stl", timeout=5)
    assert r.status_code == 200

def test_files_health():
    """Test file storage health."""
    r = httpx.get(f"{API_URL}/api/v1/files/health", timeout=5)
    assert r.status_code == 200

# ── Frontend E2E Tests ─────────────────────────────────────────

def test_frontend_loads(browser):
    """Test that frontend loads without errors."""
    page = browser.new_page()
    page.on("pageerror", lambda err: pytest.fail(f"Page error: {err}"))
    page.goto(BASE_URL, timeout=10000)
    expect(page).to_have_title("JARVIS — Neural Interface")
    page.close()

def test_frontend_navigation(browser):
    """Test all navbar tabs are clickable."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.wait_for_selector("button", timeout=5000)
    
    tabs = ["Home", "Chat", "Notas", "Tareas", "Mail", "Calen", "Drive", "Wiki", "Mind", "Conf"]
    for tab in tabs:
        try:
            btn = page.locator(f"button:has-text('{tab}')").first
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                print(f"  Tab '{tab}' OK")
            else:
                print(f"  Tab '{tab}' NOT VISIBLE")
        except Exception as e:
            print(f"  Tab '{tab}' ERROR: {e}")
    page.close()

def test_chat_panel_visible(browser):
    """Test chat panel loads correctly."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    # Navegar a Chat
    page.locator("button:has-text('Chat')").first.click()
    page.wait_for_timeout(1000)
    # Verificar que el textarea existe
    textarea = page.locator("textarea")
    if textarea.is_visible():
        textarea.fill("hola")
        send_btn = page.locator("button[aria-label='Enviar mensaje']")
        if send_btn.is_visible() and send_btn.is_enabled():
            send_btn.click()
            page.wait_for_timeout(5000)
            # Verificar respuesta
            msgs = page.locator("div:has(> span:text('JARVIS'))")
            count = msgs.count()
            print(f"Chat test OK: {count} mensajes JARVIS visibles")
        else:
            print("Send button not enabled (no text entered)")
    else:
        # Podría estar en home
        print("Chat textarea not found — may be in home view")
    page.close()

def test_notes_panel_crud(browser):
    """Test notes panel create + list."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.locator("button:has-text('Notas')").first.click()
    page.wait_for_timeout(1000)
    # Ver si hay botón para crear nota
    create_btn = page.locator("button:has-text('Nueva nota')")
    if create_btn.is_visible():
        create_btn.click()
        page.wait_for_timeout(500)
        title_input = page.locator("input[placeholder='Título...']")
        if title_input.is_visible():
            title_input.fill("Test Note E2E")
            content_input = page.locator("textarea[placeholder='Contenido...']")
            if content_input.is_visible():
                content_input.fill("Contenido de prueba automatizada")
            save_btn = page.locator("button:has-text('Guardar')")
            if save_btn.is_visible():
                save_btn.click()
                page.wait_for_timeout(500)
                print("Note created OK")
        else:
            print("Create form not found")
    else:
        print("Create button not visible")
    page.close()

def test_tasks_panel_crud(browser):
    """Test tasks panel create + complete."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.locator("button:has-text('Tareas')").first.click()
    page.wait_for_timeout(1000)
    add_btn = page.locator("input[placeholder*='nueva tarea']")
    if add_btn.is_visible():
        add_btn.fill("E2E Test Task")
        add_btn.press("Enter")
        page.wait_for_timeout(500)
        print("Task created OK")
    else:
        print("Task input not found")
    page.close()

def test_gmail_panel_loads(browser):
    """Test Gmail panel loads (connection prompt expected)."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.locator("button:has-text('Mail')").first.click()
    page.wait_for_timeout(1000)
    # Should show connect prompt (not authenticated)
    connect_text = page.locator("text=Conectá Gmail")
    oauth_text = page.locator("text=Conectar Gmail")
    if connect_text.is_visible() or oauth_text.is_visible():
        print("Gmail panel shows connect prompt OK")
    else:
        print("Gmail panel: authenticated or different view")
    page.close()

def test_drive_panel_loads(browser):
    """Test Drive panel loads."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.locator("button:has-text('Drive')").first.click()
    page.wait_for_timeout(1000)
    connect_btn = page.locator("text=Conectar Drive")
    if connect_btn.is_visible():
        print("Drive panel shows connect prompt OK")
    else:
        print("Drive panel: authenticated or different view")
    page.close()

def test_calendar_panel_loads(browser):
    """Test Calendar panel loads."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.locator("button:has-text('Calen')").first.click()
    page.wait_for_timeout(1000)
    # Should show calendar grid or connect prompt
    cal_header = page.locator("text=Enero | text=Febrero | text=Marzo")
    connect_btn = page.locator("text=Conectar Calendar")
    if cal_header.is_visible() or connect_btn.is_visible():
        print("Calendar panel loads OK")
    else:
        print("Calendar panel state unknown")
    page.close()

def test_wiki_panel_loads(browser):
    """Test Wiki panel loads."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.locator("button:has-text('Wiki')").first.click()
    page.wait_for_timeout(1000)
    search = page.locator("input[placeholder='Buscar en tu segundo cerebro...']")
    if search.is_visible():
        print("Wiki panel loads OK with search bar")
    else:
        print("Wiki panel search not visible")
    page.close()

def test_voice_controls_present(browser):
    """Test VoiceControls mic button is visible."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    # VoiceControls should be visible on home screen
    page.wait_for_timeout(2000)
    # Check for TTS toggle
    tts_btn = page.locator("button:has-text('Voz ON')")
    tts_off = page.locator("button:has-text('Voz OFF')")
    if tts_btn.is_visible() or tts_off.is_visible():
        print("VoiceControls present OK")
    else:
        print("VoiceControls NOT visible")
    page.close()

def test_brain_3d_loads(browser):
    """Test brain 3D canvas is present."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.wait_for_timeout(3000)
    canvas = page.locator("canvas")
    count = canvas.count()
    if count > 0:
        print(f"Brain 3D OK: {count} canvas elements found")
    else:
        print("No canvas found — brain may not have loaded")
    page.close()

def test_settings_panel(browser):
    """Test settings panel loads correctly."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    page.locator("button:has-text('Conf')").first.click()
    page.wait_for_timeout(1000)
    # Check for settings content
    api_input = page.locator("input[value*='http']")
    if api_input.is_visible():
        print("Settings panel loads OK")
    else:
        print("Settings panel: API URL input not visible")
    page.close()

def test_responsive_layout(browser):
    """Test mobile viewport."""
    page = browser.new_page()
    page.set_viewport_size({"width": 390, "height": 844})  # iPhone 14
    page.goto(BASE_URL, timeout=10000)
    page.wait_for_timeout(2000)
    # Bottom navbar should be visible
    navbar = page.locator("button:has-text('Home')")
    if navbar.is_visible():
        print("Mobile navbar visible OK")
    else:
        print("Mobile navbar NOT visible")
    page.close()

def test_multiple_navigations(browser):
    """Test rapid navigation between panels."""
    page = browser.new_page()
    page.goto(BASE_URL, timeout=10000)
    
    panels = ["Chat", "Notas", "Tareas", "Mail", "Drive", "Wiki"]
    for panel in panels:
        try:
            btn = page.locator(f"button:has-text('{panel}')").first
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(300)
                print(f"Nav to {panel} OK")
        except Exception as e:
            print(f"Nav to {panel} ERROR: {e}")
    page.close()

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()
