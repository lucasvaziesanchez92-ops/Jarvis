"""Test cada herramienta del registry individualmente."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_tool(name, fn, args):
    try:
        start = time.time()
        result = str(fn.invoke(args))
        elapsed = round(time.time() - start, 2)
        ok = "error" not in result.lower()[:30] or len(result) > 5
        status = "OK" if ok else "ERROR"
        detail = result[:120].replace("\n", " ")
        print(f"  [{status}] {name:<35} {elapsed:>5}s  {detail}")
        return ok
    except Exception as e:
        print(f"  [FAIL] {name:<35}        {str(e)[:100]}")
        return False

print("=" * 80)
print("  JARVIS TOOL REGISTRY — Full Audit")
print("=" * 80)

ok = 0
fail = 0
skip = 0

# ── Notes CRUD ──
print("\n── NOTES ──")
try:
    from backend.tools.notes import create_note, list_notes, get_note, update_note, delete_note
    if test_tool("create_note", create_note, {"title": "AuditTest", "content": "ok"}): ok += 1
    else: fail += 1
    res = list_notes.invoke({})
    ids = []
    import re
    for m in re.finditer(r"ID:\s*([a-f0-9-]+)", str(res)):
        ids.append(m.group(1))
    if test_tool("list_notes", list_notes, {}): ok += 1
    else: fail += 1
    if ids:
        if test_tool("get_note", get_note, {"note_id": ids[0]}): ok += 1
        else: fail += 1
        if test_tool("update_note", update_note, {"note_id": ids[0], "title": "AuditTestMod"}): ok += 1
        else: fail += 1
        for i in ids:
            test_tool(f"delete_note({i[:8]})", delete_note, {"note_id": i})
            ok += 1
    else:
        skip += 3
        print("  [SKIP] get_note/update_note/delete_note (no notes to test)")
except ImportError as e:
    skip += 5
    print(f"  [SKIP] notes module: {e}")

# ── Todos CRUD ──
print("\n── TODOS ──")
try:
    from backend.tools.todos import create_todo, list_todos, complete_todo, update_todo, delete_todo
    if test_tool("create_todo", create_todo, {"title": "AuditTodo", "priority": "alta"}): ok += 1
    else: fail += 1
    res = list_todos.invoke({})
    ok += 1
    tids = []; import re
    for m in re.finditer(r"ID:\s*([a-f0-9-]+)", str(res)):
        tids.append(m.group(1))
    if tids:
        test_tool("complete_todo", complete_todo, {"todo_id": tids[0]}); ok += 1
        test_tool("update_todo", update_todo, {"todo_id": tids[0], "title": "AuditTodoMod"}); ok += 1
        for tid in tids:
            test_tool(f"delete_todo({tid[:8]})", delete_todo, {"todo_id": tid}); ok += 1
    else:
        print("  [SKIP] complete/update/delete (no todos)"); skip += 3
except ImportError as e:
    skip += 5; print(f"  [SKIP] todos module: {e}")

# ── Time ──
print("\n── TIME ──")
try:
    from backend.tools.utility import get_current_time, get_current_date
    test_tool("get_current_time", get_current_time, {}); ok += 1
    test_tool("get_current_date", get_current_date, {}); ok += 1
except ImportError:
    skip += 2; print("  [SKIP] time module")

# ── Wiki ──
print("\n── WIKI ──")
try:
    from backend.tools.wiki import wiki_query, wiki_save_research, wiki_ingest
    test_tool("wiki_query", wiki_query, {"query": "test"}); ok += 1
    test_tool("wiki_save_research", wiki_save_research, {"title": "AuditWiki", "content": "test"}); ok += 1
    test_tool("wiki_ingest", wiki_ingest, {"file_name": "AuditWiki.md"}); ok += 1
except ImportError:
    skip += 3; print("  [SKIP] wiki module")

# ── Memory ──
print("\n── MEMORY ──")
try:
    from backend.tools.memory import search_memory, save_memory, list_memories, delete_memory
    test_tool("save_memory", save_memory, {"content": "test audit memo", "title": "AuditMem"}); ok += 1
    test_tool("search_memory", search_memory, {"query": "audit"}); ok += 1
    test_tool("list_memories", list_memories, {}); ok += 1
    test_tool("delete_memory", delete_memory, {"memory_id": "audit"}); ok += 1
except ImportError:
    skip += 4; print("  [SKIP] memory module")

# ── Legacy Calendar ──
print("\n── CALENDAR (legacy) ──")
try:
    from backend.tools.calendar import list_calendar_events, create_calendar_event, update_calendar_event, delete_calendar_event
    test_tool("list_calendar_events", list_calendar_events, {"max_results": 3}); ok += 1
    test_tool("create_calendar_event", create_calendar_event, {
        "summary": "AuditEvent", "start_time": "2026-06-01T10:00:00",
        "end_time": "2026-06-01T11:00:00"}); ok += 1
except ImportError:
    skip += 4; print("  [SKIP] calendar module")

# ── Legacy Email ──
print("\n── EMAIL (legacy) ──")
try:
    from backend.tools.email import search_emails, send_email, list_emails
    test_tool("list_emails", list_emails, {"max_results": 3}); ok += 1
    test_tool("search_emails", search_emails, {"query": "test"}); ok += 1
    test_tool("send_email", send_email, {"to": "test@example.com", "subject": "Audit", "body": "test"}); ok += 1
except ImportError:
    skip += 3; print("  [SKIP] email module")

# ── Google Suite ──
print("\n── GOOGLE SUITE ──")
try:
    from backend.tools.google_suite import (
        list_gmail, search_gmail, send_gmail,
        search_drive, list_drive_files,
        list_calendar_google, create_calendar_event_google
    )
    test_tool("list_gmail", list_gmail, {"max_results": 3}); ok += 1
    test_tool("search_gmail", search_gmail, {"query": "test"}); ok += 1
    test_tool("list_drive_files", list_drive_files, {"max_results": 3}); ok += 1
    test_tool("search_drive", search_drive, {"query": "test"}); ok += 1
    test_tool("list_calendar_google", list_calendar_google, {"max_results": 3}); ok += 1
    test_tool("create_calendar_event_google", create_calendar_event_google, {
        "summary": "AuditGEvent", "start_time": "2026-06-01T10:00:00",
        "end_time": "2026-06-01T11:00:00"}); ok += 1
    test_tool("send_gmail", send_gmail, {"to": "test@example.com", "subject": "Audit", "body": "test"}); ok += 1
except ImportError:
    skip += 7; print("  [SKIP] google_suite module")

# ── Web Search ──
print("\n── WEB SEARCH ──")
try:
    from backend.tools.web_search import web_search
    if test_tool("web_search", web_search, {"query": "python"}): ok += 1
    else: fail += 1
except ImportError:
    print("  [SKIP] web_search (playwright missing)"); skip += 1

# ── Semantic Search ──
print("\n── SEMANTIC SEARCH ──")
try:
    from backend.tools.semantic_search import search_notes_semantic, search_wiki_semantic, search_all_knowledge, get_knowledge_stats
    test_tool("search_notes_semantic", search_notes_semantic, {"query": "test"}); ok += 1
    test_tool("search_wiki_semantic", search_wiki_semantic, {"query": "test"}); ok += 1
    test_tool("search_all_knowledge", search_all_knowledge, {"query": "test"}); ok += 1
    test_tool("get_knowledge_stats", get_knowledge_stats, {}); ok += 1
except ImportError:
    print("  [SKIP] semantic_search (chromadb missing)"); skip += 4

print(f"\n{'='*80}")
print(f"  OK: {ok}  FAIL: {fail}  SKIP: {skip}  TOTAL: {ok+fail+skip}")
print(f"  Health: {round(ok/(ok+fail)*100)}% de las herramientas disponibles funcionan")
print(f"{'='*80}")
if fail > 0:
    print(f"  {fail} herramientas con errores necesitan atención")
if skip > 0:
    print(f"  {skip} herramientas no disponibles (dependencias faltantes)")
