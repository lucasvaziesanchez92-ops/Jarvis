# Jarvis API Contract

Base URL: `http://localhost:8000`

## Health

```
GET /health
→ { "status": "ok", "service": "jarvis" }
```

## Chat

```
POST /chat
Body: { "message": str, "session_id": str, "user_id": str }
→ { "content": str, "session_id": str }

WS /ws/chat
Send: { "message": str, "session_id": str }
Recv: StreamChunk frames (see architecture.md)
```

## Notes

```
GET    /notes              → Note[]
POST   /notes              → Note (201)
GET    /notes/{id}         → Note
PUT    /notes/{id}         → Note
DELETE /notes/{id}         → 204
```

## Todos

```
GET    /todos              → Todo[]  (?show_completed=false)
POST   /todos              → Todo (201)
GET    /todos/{id}         → Todo
PATCH  /todos/{id}/complete → Todo
DELETE /todos/{id}         → 204
```

## Calendar

```
GET    /calendar           → CalendarEvent[]
POST   /calendar           → CalendarEvent (201)
GET    /calendar/{id}      → CalendarEvent
PUT    /calendar/{id}      → CalendarEvent
DELETE /calendar/{id}      → 204
```

## Email (requires Gmail credentials)

```
GET  /emails               → EmailSummary[]  (?label=INBOX&max=10)
GET  /emails/{message_id}  → EmailMessage
GET  /emails/search        → EmailSummary[]  (?q=query&max=10)
POST /emails/send          Body: { to, subject, body } → { result: str }
```

## Error format

```json
{ "detail": "Error message" }
```
HTTP status codes: `400` bad request, `404` not found, `503` service unavailable (Gmail not configured).
