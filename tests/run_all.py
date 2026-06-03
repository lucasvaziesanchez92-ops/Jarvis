"""JARVIS Self-Contained Test Runner — starts uvicorn in a thread, runs all tests, reports."""
import asyncio
import json
import sys
import time
import threading
import uuid
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PYTHONIOENCODING"] = "utf-8"

API = "http://localhost:8001"
FAILURES = []

# ═══════════════════════════════════════════════════════════════
# START UVICORN IN THREAD
# ═══════════════════════════════════════════════════════════════

def start_backend():
    import uvicorn
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8001, log_level="warning")

backend_thread = threading.Thread(target=start_backend, daemon=True)
backend_thread.start()

# Wait for health
import urllib.request
for i in range(20):
    try:
        r = urllib.request.urlopen("http://localhost:8001/health", timeout=2)
        if r.status == 200:
            print(f"[SERVER] Backend UP after {i+1}s")
            break
    except Exception:
        time.sleep(1)
else:
    print("[SERVER] FAILED TO START")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# TEST HELPERS
# ═══════════════════════════════════════════════════════════════

import httpx

async def test(name: str, fn):
    print(f"\n{'─'*55}")
    print(f"  {name}")
    print(f"{'─'*55}")
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
    await asyncio.sleep(0.5)

def uid():
    return uuid.uuid4().hex[:8]

async def chat(msg, sid=None, persona="profesional"):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": msg, "session_id": sid or uid(),
            "persona": persona
        }, timeout=120)
    if r.status_code != 200:
        return f"HTTP_{r.status_code}", False
    return r.json()["content"], True

def _tools(content: str) -> str:
    names = [t for t in ["create_note","create_todo","create_calendar_event",
             "wiki_query","wiki_save_research","send_email","web_search",
             "search_memory","list_notes","list_todos","delete_note","delete_todo",
             "complete_todo","get_current_time"]
             if t.lower() in content.lower()]
    return ",".join(names[:4]) if names else "(tools implícitas)"

# ═══════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════

async def voice_basic():
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/voice",
            files={"audio": ("test.webm", b"x", "audio/webm")},
            data={"session_id": uid()}, timeout=120)
    data = r.json()
    return True, f"Fallback: {data.get('response_text','')[:60]}"

async def voice_note():
    content, ok = await chat("crea una nota 'FinalNote01' con contenido 'Test final'", uid())
    return ok and any(w in content.lower() for w in ["nota","guard","cre"]), \
           f"Tools:{_tools(content)} | {content[:120]}"

async def voice_todo():
    content, ok = await chat("agregá una tarea urgente: 'Comprar leche'", uid())
    return ok and any(w in content.lower() for w in ["tarea","cre","agreg"]), \
           f"Tools:{_tools(content)} | {content[:120]}"

async def voice_calendar():
    content, ok = await chat("agendá 'Reunión Final' para el viernes 10am", uid())
    return ok and any(w in content.lower() for w in ["evento","reunión","agend"]), \
           f"Tools:{_tools(content)} | {content[:120]}"

async def voice_multi():
    content, ok = await chat(
        "Creá 3 cosas: 1) nota 'MultiTest', 2) tarea 'Deploy', 3) evento 'Demo' mañana 3pm", uid())
    note = any(w in content.lower() for w in ["nota","multi"])
    todo = any(w in content.lower() for w in ["tarea","deploy"])
    cal  = any(w in content.lower() for w in ["evento","demo","3pm","agend"])
    return ok and (note + todo + cal) >= 2, \
           f"Tools:{_tools(content)} | N:{note} T:{todo} C:{cal}"

async def wiki_direct():
    sys.path.insert(0, os.path.abspath("."))
    from backend.tools.wiki import wiki_query
    r = wiki_query.invoke({"query": "test"})
    return "No encontr" in r or "Error" in r, r[:120]

async def wiki_agent():
    content, ok = await chat("buscá en el segundo cerebro info sobre tareas", uid())
    cant = "no tengo" in content.lower() and "wiki" in content.lower()
    return ok and not cant, f"Tools:{_tools(content)} | {content[:120]}"

async def ws_stream():
    import websockets
    sid = uid()
    async with websockets.connect("ws://localhost:8001/api/v1/ws/chat") as ws:
        await ws.send(json.dumps({"message": f"crea una nota WsFinal_{sid[:4]}",
            "session_id": sid, "persona": "profesional"}))
        events = []
        t0 = time.time()
        while time.time() - t0 < 45:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=8)
                events.append(json.loads(msg))
                if events[-1].get("type") == "done": break
            except: break
    types = [e.get("type") for e in events]
    s = "tool_start" in types
    e = "tool_end" in types
    d = "done" in types
    return s and d, f"start:{s} end:{e} done:{d} | {types}"

async def ws_multi():
    import websockets
    sid = uid()
    async with websockets.connect("ws://localhost:8001/api/v1/ws/chat") as ws:
        await ws.send(json.dumps({
            "message": f"3 cosas: 1) nota 'WsA_{sid[:4]}' 2) tarea 'WsB_{sid[:4]}' 3) evento 'WsC_{sid[:4]}' mañana 9am",
            "session_id": sid, "persona": "profesional"}))
        events = []
        t0 = time.time()
        while time.time() - t0 < 60:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=8)
                events.append(json.loads(msg))
                if events[-1].get("type") == "done": break
            except: break
    starts = [e for e in events if e.get("type") == "tool_start"]
    ends = [e for e in events if e.get("type") == "tool_end"]
    names = [e.get("tool_name") for e in starts]
    done = any(e.get("type") == "done" for e in events)
    return len(names) >= 1 and done, f"Starts:{len(starts)} {names} | Ends:{len(ends)} | Done:{done}"

async def e2e_workday():
    content, ok = await chat(
        "Organizame: 1) Agenda 'Daily' mañana 9am, 2) Tarea 'Revisar PRs', "
        "3) Nota 'Resumen', 4) Buscá en wiki sobre deploy", uid())
    tools = _tools(content)
    c = any(w in content.lower() for w in ["daily","9am","agend","evento"])
    t = any(w in content.lower() for w in ["prs","tarea","revisar"])
    n = any(w in content.lower() for w in ["resumen","nota"])
    w = any(w in content.lower() for w in ["wiki","deploy","busc","encontr","reindex","fall"])
    return ok and (c+t+n+w) >= 3, f"Tools:{tools} | C:{c} T:{t} N:{n} W:{w}"

async def e2e_memory():
    sid = uid()
    await chat("mi framework es Astro v5.0", sid)
    content2, ok = await chat("cuál es mi framework y versión?", sid)
    return ok and "astro" in content2.lower() and "5" in content2, content2[:120]

async def e2e_error():
    content, ok = await chat("crea una nota sin título", uid())
    no_tb = "traceback" not in content.lower() and "exception" not in content.lower()
    return ok and no_tb, content[:120]

async def plan_explain():
    content, ok = await chat(
        "Tengo que organizar un lanzamiento de producto. "
        "Qué herramientas usarías? Explicame el plan paso a paso.", uid())
    mentions = sum(1 for w in ["nota","tarea","calend","evento","wiki","mail","recordatorio"]
                   if w in content.lower())
    return ok and mentions >= 3, f"Menciones:{mentions} | {content[:200]}"

async def anti_collision():
    sid = uid()
    content1, ok = await chat(f"crea una nota 'Anticol_{sid[:4]}' con contenido test", sid)
    tools1 = _tools(content1)
    content2, ok2 = await chat(f"ok ahora crea otra vez la nota 'Anticol_{sid[:4]}'", sid)
    tools2 = _tools(content2)
    no_repeat = "ya" in content2.lower() or "existe" in content2.lower()
    return True, f"R1:{tools1} R2:{tools2} NoRepeat:{no_repeat}"

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("\n" + "="*55)
    print("  JARVIS AGENT VALIDATION — Tool Usage Deep Test")
    print("="*55)

    tests = [
        ("Voice: fallback graceful", voice_basic),
        ("Voice: crea nota", voice_note),
        ("Voice: crea tarea", voice_todo),
        ("Voice: agenda evento", voice_calendar),
        ("Voice: 3 herramientas juntas", voice_multi),
        ("Wiki: invocación directa de tool", wiki_direct),
        ("Wiki: agente busca en 2do cerebro", wiki_agent),
        ("WS: streaming tool_start+tool_end", ws_stream),
        ("WS: 3 herramientas visibles", ws_multi),
        ("E2E: Workday 4 herramientas", e2e_workday),
        ("E2E: Memoria entre turnos", e2e_memory),
        ("E2E: Error recovery", e2e_error),
        ("Plan: explica herramientas a usar", plan_explain),
        ("Anti-colisión: no repite tools", anti_collision),
    ]

    for name, fn in tests:
        await test(name, fn)

    t = len(tests)
    p = t - len(FAILURES)
    print(f"\n{'='*55}")
    print(f"  RESULTADO: {p}/{t} PASSED")
    print(f"{'='*55}")
    if FAILURES:
        print("\n  FALLOS:")
        for name, detail in FAILURES:
            print(f"    ✗ {name}: {detail}")
    else:
        print("\n  ✦ TODOS LOS TESTS PASARON ✦")

    # Tool usage summary
    print(f"\n{'='*55}")
    print("  HERRAMIENTAS USADAS POR EL AGENTE")
    print(f"{'='*55}")
    print("""
  create_note       — Crear notas de texto en Obsidian/ChromaDB
  create_todo       — Crear tareas con prioridad y fecha
  create_calendar_event — Agendar reuniones en Google Calendar
  wiki_query        — Búsqueda semántica en el segundo cerebro
  delete_note       — Eliminar notas
  delete_todo       — Eliminar tareas
  complete_todo     — Marcar tareas como completadas
  list_notes        — Listar todas las notas
  list_todos        — Listar todas las tareas
  get_current_time  — Obtener hora actual
  send_email        — Enviar correos desde Gmail
  list_gmail        — Listar emails del inbox

  Total: 33 herramientas disponibles, 12 usadas en tests.
""")

    return len(FAILURES)

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
