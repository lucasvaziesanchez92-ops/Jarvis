"""JARVIS AGENT PROFUNDO: Test de planeación multi-herramienta secuencial."""
import asyncio
import json
import time
from dataclasses import dataclass
import httpx

API = "http://localhost:8001"

@dataclass
class ToolCall:
    name: str

# ═══════════════════════════════════════════════════════════════════
# 1. TOOL AWARENESS — ¿Sabe qué herramientas tiene?
# ═══════════════════════════════════════════════════════════════════

async def test_tool_awareness_list():
    """Preguntar qué herramientas tiene disponibles — debe enumerarlas."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": "qué herramientas o funciones tenés disponibles?",
            "session_id": "tools-aware", "persona": "profesional"
        }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"].lower()
    assert any(k in content for k in ["nota", "crear", "gmail", "calend", "tarea", "wiki", "drive"]), \
        f"Agent unaware of tools: {content[:300]}"
    print(f"✓ Tool awareness: {content[:200]}")

async def test_tool_awareness_specific():
    """Preguntar si puede crear una nota — debe responder que sí."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": "podes crear notas?",
            "session_id": "tools-can", "persona": "profesional"
        }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"].lower()
    assert "sí" in content or "puedo" in content or "claro" in content, \
        f"Agent says it can't create notes: {content[:200]}"
    print(f"✓ Can create notes: {content[:200]}")

# ═══════════════════════════════════════════════════════════════════
# 2. SINGLE-TOOL VALIDATION — Cada herramienta individual responde correctamente
# ═══════════════════════════════════════════════════════════════════

async def test_single_create_note():
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": "crea una nota llamada 'Plan de negocio' con contenido 'Expandir a latam'",
            "session_id": "single-note", "persona": "profesional"
        }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"].lower()
    # Debe indicar éxito, no error
    assert "error" not in content.split()[:5]
    print(f"✓ Create note: {content[:200]}")

async def test_single_create_todo():
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": "agregá una tarea: Preparar presentación Q3",
            "session_id": "single-todo", "persona": "profesional"
        }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"].lower()
    assert "error" not in content.split()[:5]
    print(f"✓ Create todo: {content[:200]}")

async def test_single_calendar_event():
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": "agendá una reunión para pasado mañana a las 10am llamada 'Sprint review'",
            "session_id": "single-cal", "persona": "profesional"
        }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"].lower()
    assert "error" not in content.split()[:5]
    print(f"✓ Calendar: {content[:200]}")

async def test_wiki_search():
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": "buscá en el wiki información sobre programación",
            "session_id": "wiki-single", "persona": "profesional"
        }, timeout=120)
    assert r.status_code == 200
    content = r.json()["content"]
    print(f"✓ Wiki: {content[:200]}")

# ═══════════════════════════════════════════════════════════════════
# 3. MULTI-TOOL SEQUENTIAL — El AGENTE DEBE PLANEAR y ejecutar varios pasos
# ═══════════════════════════════════════════════════════════════════

async def test_multi_agenda_reunion_completa():
    """Workflow real: agendar reunión + crear nota con agenda + tomar tareas."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": (
                "Organizá una reunión de planificación para el próximo lunes a las 14hs. "
                "Creá una nota con los puntos de agenda: 1) Revisión de métricas 2) Nuevos features 3) Timeline. "
                "Y creá una tarea para preparar el slide deck."
            ),
            "session_id": "multi-agenda", "persona": "profesional"
        }, timeout=180)
    assert r.status_code == 200
    content = r.json()["content"]
    has_cal = any(w in content.lower() for w in ["evento", "reunión", "agend", "calend"])
    has_note = any(w in content.lower() for w in ["nota", "creé", "guardé"])
    has_todo = any(w in content.lower() for w in ["tarea", "tarea", "pendiente"])
    print(f"  Calendar: {has_cal} | Note: {has_note} | Todo: {has_todo}")
    print(f"  Full: {content[:400]}")
    # At least 2 of 3 should be attempted
    assert (has_cal + has_note + has_todo) >= 2, \
        f"Agent attempted only {has_cal + has_note + has_todo}/3 tools"

async def test_multi_notas_investigacion():
    """Investigar en wiki + crear notas con hallazgos."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": (
                "Buscá en mi segundo cerebro cualquier información sobre APIs REST. "
                "Después creá una nota resumiendo lo que encontraste."
            ),
            "session_id": "multi-wiki-note", "persona": "profesional"
        }, timeout=180)
    assert r.status_code == 200
    content = r.json()["content"]
    print(f"✓ Wiki+Note: {content[:400]}")

async def test_multi_email_notas():
    """Revisar mail + tomar notas de lo importante."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": (
                "Revisá mis últimos 5 emails. Si encontrás algo urgente, "
                "creá una nota con los detalles."
            ),
            "session_id": "multi-mail-note", "persona": "profesional"
        }, timeout=180)
    assert r.status_code == 200
    content = r.json()["content"]
    print(f"✓ Mail+Note: {content[:400]}")

async def test_multi_calendar_todo_briefing():
    """Agendar evento + crear tareas preparatorias."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": (
                "Tengo una presentación importante el viernes a las 9am. "
                "Agendala y creá 3 tareas para prepararme: practicar slides, "
                "revisar datos, preparar backup plan."
            ),
            "session_id": "multi-cal-todo", "persona": "profesional"
        }, timeout=180)
    assert r.status_code == 200
    content = r.json()["content"]
    print(f"✓ Calendar+Todo: {content[:400]}")

# ═══════════════════════════════════════════════════════════════════
# 4. AGENT PLANNING — ¿Explica su plan o simplemente ejecuta?
# ═══════════════════════════════════════════════════════════════════

async def test_agent_explica_plan():
    """El agente debe poder explicar qué va a hacer antes de ejecutar."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": (
                "Necesito organizar mi semana: el lunes tengo que preparar una demo, "
                "el miércoles una reunión con inversores, y el viernes entregar un reporte. "
                "Qué herramientas vas a usar para ayudarme? Explícame tu plan."
            ),
            "session_id": "plan-explain", "persona": "profesional"
        }, timeout=180)
    assert r.status_code == 200
    content = r.json()["content"]
    # Should mention specific tools or actions
    tool_mentions = sum(1 for w in ["nota", "tarea", "calend", "agend", "evento", "recordatorio"] if w in content.lower())
    print(f"  Tool mentions in plan: {tool_mentions} — {content[:300]}")
    assert tool_mentions >= 2, "Agent didn't mention enough tools in plan"

async def test_agent_dependency_awareness():
    """Puede entender dependencias? 'Primero A, después B'."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/chat", json={
            "message": (
                "Primero buscá en el wiki si hay información sobre 'machine learning', "
                "y DESPUÉS (solo si encontraste algo) creá una nota con el resumen. "
                "Si no encontraste nada, decime que no hay información."
            ),
            "session_id": "dep-order", "persona": "profesional"
        }, timeout=180)
    assert r.status_code == 200
    content = r.json()["content"]
    print(f"✓ Dependency: {content[:400]}")

# ═══════════════════════════════════════════════════════════════════
# 5. STREAMING VISIBILITY — ¿El frontend ve el progreso?
# ═══════════════════════════════════════════════════════════════════

async def test_ws_streaming_tool_visibility():
    """WebSocket debe mostrar tool_start/tool_end durante ejecución."""
    import websockets
    async with websockets.connect("ws://localhost:8001/api/v1/ws/chat") as ws:
        await ws.send(json.dumps({
            "message": "crea una nota llamada streaming-test con contenido prueba",
            "session_id": "ws-stream-test",
            "persona": "profesional"
        }))
        events = []
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    event = json.loads(msg)
                    events.append(event)
                    if event.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    break
        except Exception as e:
            print(f"WS error: {e}")

        types = [e.get("type") for e in events]
        has_tool_start = "tool_start" in types
        has_tool_end = "tool_end" in types
        has_token = "token" in types
        has_done = "done" in types

        print(f"  WS events: {types}")
        print(f"  tool_start: {has_tool_start} | tool_end: {has_tool_end} | token: {has_token} | done: {has_done}")
        assert has_tool_start, "No tool_start events!"
        assert has_tool_end, "No tool_end events!"
        assert has_done, "No done event!"

async def test_ws_streaming_multitool_visibility():
    """Multi-tool: el WS debe mostrar tool_start para cada herramienta."""
    import websockets
    async with websockets.connect("ws://localhost:8001/api/v1/ws/chat") as ws:
        await ws.send(json.dumps({
            "message": "crea una nota 'A' y una tarea 'B'",
            "session_id": "ws-multi-tool",
            "persona": "profesional"
        }))
        events = []
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=60)
                    event = json.loads(msg)
                    events.append(event)
                    if event.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    break
        except Exception as e:
            print(f"WS error: {e}")

        tool_events = [e for e in events if e.get("type") in ("tool_start", "tool_end")]
        tool_names = [e.get("tool_name") for e in tool_events if e.get("tool_name")]
        print(f"  Tool events: {len(tool_events)} — {tool_names}")
        # Should have at least 2 tool_start (note + todo)
        assert len(tool_events) >= 4, f"Expected >=4 tool events, got {len(tool_events)}"

# ═══════════════════════════════════════════════════════════════════
# 6. VOICE vs CHAT — Comparar comportamiento
# ═══════════════════════════════════════════════════════════════════

async def test_voice_no_tools():
    """Voice explicitamente NO usa herramientas. Verificar que responda bien igual."""
    # Esto es por diseño (voice.py:32) — verificamos que funcione
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{API}/api/v1/voice/tts", json={
            "text": "Hola, cómo estás hoy?"
        }, timeout=60)
    assert r.status_code == 200
    data = r.json()
    assert "audio_base64" in data
    assert len(data["audio_base64"]) > 100
    print(f"✓ Voice TTS: {len(data['audio_base64'])} bytes")

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

async def main():
    tests = {
        "Tool awareness list": test_tool_awareness_list,
        "Tool awareness specific": test_tool_awareness_specific,
        "Single create note": test_single_create_note,
        "Single create todo": test_single_create_todo,
        "Single calendar event": test_single_calendar_event,
        "Wiki search": test_wiki_search,
        "MULTI: Agenda reunión completa": test_multi_agenda_reunion_completa,
        "MULTI: Wiki + Notas": test_multi_notas_investigacion,
        "MULTI: Mail + Notas": test_multi_email_notas,
        "MULTI: Calendar + Todos": test_multi_calendar_todo_briefing,
        "Plan: Explica plan": test_agent_explica_plan,
        "Plan: Dependencias": test_agent_dependency_awareness,
        "WS: Tool visibility": test_ws_streaming_tool_visibility,
        "WS: Multi-tool visibility": test_ws_streaming_multitool_visibility,
        "Voice: No tools": test_voice_no_tools,
    }

    results = []
    for name, test in tests.items():
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")
        try:
            await test()
            results.append(("PASS", name))
            print(f"  ✅ PASS")
        except Exception as e:
            results.append(("FAIL", name))
            print(f"  ❌ FAIL: {e}")
        await asyncio.sleep(1)  # Rate limit

    print(f"\n{'='*60}")
    print(f"  RESULTADOS: {sum(1 for r in results if r[0]=='PASS')}/{len(results)}")
    print(f"{'='*60}")
    for status, name in results:
        print(f"  {'✅' if status == 'PASS' else '❌'} {name}")
    return results

if __name__ == "__main__":
    asyncio.run(main())
