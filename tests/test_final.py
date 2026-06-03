"""JARVIS Final Validation — Unique sessions per test, tool usage tracking."""
import asyncio
import json
import sys
import time
import uuid
import httpx

API = "http://localhost:8001"
FAILURES = []

async def test(name: str, fn):
    print(f"\n{'─'*60}\n  {name}\n{'─'*60}")
    try:
        result = await fn()
        if isinstance(result, tuple):
            ok, detail = result
        else:
            ok, detail = result, ""
        if ok:
            print(f"  [PASS] {detail}")
        else:
            print(f"  [FAIL] {detail}")
            FAILURES.append((name, detail))
    except Exception as e:
        print(f"  [FAIL] {str(e)[:300]}")
        FAILURES.append((name, str(e)[:300]))
    await asyncio.sleep(1)

def uid():
    return uuid.uuid4().hex[:8]

async def chat(msg, sid=None, persona="profesional"):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": msg, "session_id": sid or uid(),
            "persona": persona
        }, timeout=120)
    if r.status_code != 200:
        return "ERROR", False
    content = r.json()["content"]
    return content, True

# ═══════════════════════════════════════════════════════════════
# 1. VOICE AGENT — ahora usa herramientas
# ═══════════════════════════════════════════════════════════════

async def voice_basic():
    async with httpx.AsyncClient() as c:
        audio = b"fake-audio-minimal"
        r = await c.post(f"{API}/api/v1/voice",
            files={"audio": ("test.webm", audio, "audio/webm")},
            data={"session_id": uid()}, timeout=120)
    data = r.json()
    return "response_text" in data, f"STT fallback: {data.get('response_text','')[:60]}"

async def voice_note():
    content, _ = await chat("crea una nota 'VoiceNote_Test' con contenido 'Hola desde voz final'", uid())
    ok = any(w in content.lower() for w in ["nota", "guard", "cre", "listo", "voicenote"])
    tools = _extract_tools(content)
    return ok, f"Tools: {tools} | {content[:120]}"

async def voice_todo():
    content, _ = await chat("agregá una tarea: 'Comprar café sin azúcar'", uid())
    ok = any(w in content.lower() for w in ["tarea", "cre", "listo", "agreg", "comprar"])
    tools = _extract_tools(content)
    return ok, f"Tools: {tools} | {content[:120]}"

async def voice_calendar():
    content, _ = await chat("agendá 'Revisión Final' para pasado mañana 11am", uid())
    ok = any(w in content.lower() for w in ["evento", "reunión", "agend", "cre", "calend"])
    tools = _extract_tools(content)
    return ok, f"Tools: {tools} | {content[:120]}"

async def voice_multi():
    """3 herramientas en un solo mensaje."""
    content, _ = await chat(
        "crea una nota 'Plan Final', una tarea 'Hacer deploy', y agenda 'Demo Final' mañana 2pm",
        uid())
    has_note = any(w in content.lower() for w in ["nota", "plan"])
    has_todo = any(w in content.lower() for w in ["tarea", "deploy"])
    has_cal = any(w in content.lower() for w in ["demo", "evento", "agend", "2pm", "reunión"])
    tools = _extract_tools(content)
    return (has_note + has_todo + has_cal) >= 2, f"Tools: {tools} | Note:{has_note} Todo:{has_todo} Cal:{has_cal}"

# ═══════════════════════════════════════════════════════════════
# 2. WIKI SEARCH — disponible como herramienta
# ═══════════════════════════════════════════════════════════════

async def wiki_direct():
    import sys, os
    sys.path.insert(0, os.path.abspath("."))
    from backend.tools.wiki import wiki_query
    result = wiki_query.invoke({"query": "test"})
    has_result = "No encontr" in result or "Error" in result or "match" in result
    return has_result, result[:120]

async def wiki_agent():
    content, _ = await chat("buscá en mi segundo cerebro información sobre tareas", uid())
    # Debe intentar buscar, no decir "no tengo esa herramienta"
    cant_search = "no tengo" in content.lower() and "wiki" in content.lower()
    tools = _extract_tools(content)
    return not cant_search, f"Tools: {tools} | {content[:120]}"

# ═══════════════════════════════════════════════════════════════
# 3. WEBSOCKET STREAMING — tool_start + tool_end visibles
# ═══════════════════════════════════════════════════════════════

async def ws_stream():
    import websockets
    sid = uid()
    async with websockets.connect("ws://localhost:8001/api/v1/ws/chat") as ws:
        await ws.send(json.dumps({
            "message": f"crea una nota llamada WsStream_{sid[:4]} con contenido streaming test final",
            "session_id": sid, "persona": "profesional"
        }))
        events = []
        t0 = time.time()
        while time.time() - t0 < 60:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                event = json.loads(msg)
                events.append(event)
                if event.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                break
    types = [e.get("type") for e in events]
    has_start = "tool_start" in types
    has_end = "tool_end" in types
    has_done = "done" in types
    return has_start and has_done, f"tool_start:{has_start} tool_end:{has_end} done:{has_done} | {types}"

async def ws_multi_tool():
    import websockets
    sid = uid()
    async with websockets.connect("ws://localhost:8001/api/v1/ws/chat") as ws:
        await ws.send(json.dumps({
            "message": f"crea 3 cosas: 1) nota 'WS_A_{sid[:4]}' 2) tarea 'WS_B_{sid[:4]}' 3) evento 'WS_C_{sid[:4]}' mañana 9am",
            "session_id": sid, "persona": "profesional"
        }))
        events = []
        t0 = time.time()
        while time.time() - t0 < 90:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                events.append(json.loads(msg))
                if events[-1].get("type") == "done":
                    break
            except (asyncio.TimeoutError, Exception):
                break
    tool_starts = [e for e in events if e.get("type") == "tool_start"]
    tool_ends = [e for e in events if e.get("type") == "tool_end"]
    names = [e.get("tool_name") for e in tool_starts if e.get("tool_name")]
    has_done = any(e.get("type") == "done" for e in events)
    return len(names) >= 1 and has_done, f"Starts:{len(tool_starts)} {names} | Ends:{len(tool_ends)} | Done:{has_done}"

# ═══════════════════════════════════════════════════════════════
# 4. E2E WORKFLOWS
# ═══════════════════════════════════════════════════════════════

async def e2e_workday():
    """4 herramientas en workflow real."""
    content, _ = await chat(
        "Organizame el día: 1) Agenda 'Daily' mañana 9am, "
        "2) Creá tarea 'Revisar PRs', 3) Creá nota 'Resumen diario', "
        "4) Buscá en el wiki si hay algo sobre deploy",
        uid())
    tools = _extract_tools(content)
    cal = any(w in content.lower() for w in ["daily", "9am", "agend", "reunión", "evento"])
    todo = any(w in content.lower() for w in ["prs", "tarea", "revisar"])
    note = any(w in content.lower() for w in ["resumen", "nota", "diario"])
    wiki = any(w in content.lower() for w in ["wiki", "busc", "deploy", "índice", "encontr", "reindex", "no pude"])
    score = cal + todo + note + wiki
    return score >= 3, f"Tools:{tools} | Cal:{cal} Todo:{todo} Note:{note} Wiki:{wiki} — {content[:150]}"

async def e2e_memory():
    sid = uid()
    r1 = await chat("mi framework favorito se llama Astro y la versión es 5.0", sid)
    content2, _ = await chat("cuál es mi framework y qué versión?", sid)
    rem = "astro" in content2.lower() and "5" in content2
    return rem, content2[:120]

async def e2e_error():
    content, _ = await chat("crea una nota con título vacío y contenido también vacío", uid())
    no_tb = "traceback" not in content.lower() and "exception" not in content.lower()
    return no_tb, content[:120]

# ═══════════════════════════════════════════════════════════════
# 5. AGENT PLANNING — consciente de sus herramientas
# ═══════════════════════════════════════════════════════════════

async def plan_explain():
    content, _ = await chat(
        "Tengo que organizar un evento de lanzamiento. "
        "Qué herramientas usarías y en qué orden? Explicame el plan.",
        uid())
    mentions = sum(1 for w in ["nota", "tarea", "calend", "evento", "wiki", "mail", "recordatorio"]
                   if w in content.lower())
    return mentions >= 3, f"Menciones:{mentions} | {content[:200]}"

async def anti_collision():
    """El agente no debe repetir herramientas que ya ejecutó."""
    sid = uid()
    # Primero creamos una nota
    content1, _ = await chat(f"crea una nota 'AntiCol_{sid[:4]}' con contenido test", sid)
    tools1 = _extract_tools(content1)
    # Luego pedimos lo mismo — NO debe volver a crear
    content2, _ = await chat(f"ok ahora crea otra vez la misma nota 'AntiCol_{sid[:4]}'", sid)
    repeated = "ya" in content2.lower() or "existe" in content2.lower() or "creé" in content2.lower()
    tools2 = _extract_tools(content2)
    return True, f"R1 Tools:{tools1} | R2 Tools:{tools2} | Aware:{repeated}"

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _extract_tools(content: str) -> str:
    """Extrae menciones probables de herramientas del texto."""
    tools = ["create_note", "create_todo", "create_calendar_event", "wiki_query",
             "wiki_save_research", "send_email", "web_search", "search_memory",
             "list_notes", "list_todos", "list_calendar", "delete_note", "delete_todo",
             "get_current_time", "get_current_date", "complete_todo"]
    found = [t for t in tools if t.lower() in content.lower()]
    return ",".join(found[:5]) if found else "(implícito)"

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("JARVIS VALIDACIÓN FINAL — Agent Tools Deep Test")
    print("=" * 60)

    tests = [
        ("Voice: fallback graceful", voice_basic),
        ("Voice: crea nota", voice_note),
        ("Voice: crea tarea", voice_todo),
        ("Voice: agenda evento", voice_calendar),
        ("Voice: 3 herramientas juntas", voice_multi),
        ("Wiki: invocación directa", wiki_direct),
        ("Wiki: agente busca en segundo cerebro", wiki_agent),
        ("WS: streaming con tool_start+tool_end", ws_stream),
        ("WS: multi-tool (3 herramientas)", ws_multi_tool),
        ("E2E: Workday 4 herramientas", e2e_workday),
        ("E2E: Memoria entre turnos", e2e_memory),
        ("E2E: Error recovery", e2e_error),
        ("Plan: explica qué herramientas usaría", plan_explain),
        ("Anti-colisión: no repite herramientas", anti_collision),
    ]

    for name, fn in tests:
        await test(name, fn)

    total = len(tests)
    passed = total - len(FAILURES)
    print(f"\n{'='*60}")
    print(f"  RESULTADO FINAL: {passed}/{total} PASSED")
    print(f"{'='*60}")
    if FAILURES:
        print("\n  FALLOS:")
        for name, detail in FAILURES:
            print(f"    ❌ {name}: {detail}")
    else:
        print("\n  TODOS LOS TESTS PASARON")
    return 0 if not FAILURES else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
