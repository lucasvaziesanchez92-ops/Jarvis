# PRD #3 — DATABASE/STORAGE: NEONDB SCHEMA
## Proyecto: JARVIS | Stack: PostgreSQL (NeonDB) + SQLAlchemy
### Versión: 1.0

---

## 1. VISIÓN DEL PRODUCTO

Jarvis necesita persistencia para: conversaciones (threads + messages), notas, tareas, eventos de calendario, y emails. El storage layer soporta dos backends: **SQLite** (desarrollo) y **PostgreSQL/NeonDB** (producción).

**Referencia directa de código:**
- `backend/storage/models.py` — Modelos unificados (Base, NoteModel, TodoModel, ThreadModel, MessageModel)
- `backend/storage/sqlite_store.py` — SqliteStore implementation
- `backend/storage/neon_store.py` — PostgresStore (NeonDB) implementation
- `backend/storage/__init__.py` — Factory `get_store()`

---

## 2. ARQUITECTURA DE STORAGE

### 2.1 Factory Pattern

```python
# backend/storage/__init__.py
def get_store():
    if settings.storage_type == "neon":
        from backend.storage.neon_store import PostgresStore
        return PostgresStore()
    else:
        from backend.storage.sqlite_store import SqliteStore
        return SqliteStore()
```

### 2.2 Backend Comparison

| Feature | SQLite | NeonDB (PostgreSQL) |
|---|---|---|
| Deployment | Local file | Cloud (neon.tech) |
| Concurrency | Limited | Full |
| SSL | N/A | Required |
| Connection pooling | N/A | QueuePool (10 conns) |
| Use case | Development | Production |

### 2.3 Current Status (from session context)

- `STORAGE_TYPE=neon` configured in `.env`
- Connection string: `postgresql://neondb_owner:npg_AoDS6vOE8wts@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`
- 4 tables exist in NeonDB: `notes`, `todos`, `threads`, `messages` — all empty (0 records)
- Missing tables: likely `email_message`, `chat`, `calendar_event` models exist but no DB tables

---

## 3. MODELOS DE DATOS

### 3.1 Base Class

```python
Base = declarative_base()
```

Todos los modelos heredan de `Base` y usan SQLAlchemy ORM.

### 3.2 Model: NoteModel

```python
class NoteModel(Base):
    __tablename__ = "notes"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)           # UUID string
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)          # Markdown content
    tags = Column(Text, default="[]")                # JSON array as string
    created_at = Column(DateTime, default=..., index=True)
    updated_at = Column(DateTime, default=..., onupdate=...)
    deleted_at = Column(DateTime, nullable=True)     # Soft delete
```

### 3.3 Model: TodoModel

```python
class TodoModel(Base):
    __tablename__ = "todos"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    text = Column(Text, nullable=False, index=True)  # Title/content of todo
    completed = Column(Boolean, default=False, index=True)
    priority = Column(String, default="medium", index=True)  # low/medium/high
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=..., index=True)
    deleted_at = Column(DateTime, nullable=True)     # Soft delete
```

### 3.4 Model: ThreadModel

```python
class ThreadModel(Base):
    __tablename__ = "threads"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    title = Column(String, nullable=True, index=True)
    status = Column(String, default="active")         # active/archived
    created_at = Column(DateTime, default=..., index=True)
    updated_at = Column(DateTime, default=..., onupdate=...)
    meta = Column(Text, nullable=True)                # JSON metadata
    deleted_at = Column(DateTime, nullable=True)     # Soft delete
```

### 3.5 Model: MessageModel

```python
class MessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index('ix_messages_thread_created', 'thread_id', 'created_at'),
    )

    id = Column(String, primary_key=True)
    thread_id = Column(String, nullable=False, index=True)  # FK → Thread
    role = Column(String, default="user")           # user/assistant/system
    content = Column(Text, nullable=False)
    meta = Column(Text, nullable=True)              # JSON (tool_calls, etc.)
    created_at = Column(DateTime, default=..., index=True)
```

**Índice compuesto:** `ix_messages_thread_created` para queries por thread + orden cronológico.

---

## 4. MISSING MODELS (NOT IN storage/models.py)

According to session context, these models exist but their tables were NOT created in NeonDB:

### 4.1 CalendarEventModel

Referenced in: `backend/models/calendar_event.py`

**Expected fields:**
```python
id: UUID
title: str
description: str | None
start_time: datetime
end_time: datetime
location: str | None
created_at: datetime
updated_at: datetime
```

### 4.2 EmailMessageModel

Referenced in: `backend/models/email_message.py`

**Expected fields:**
```python
id: UUID
gmail_id: str | None
thread_id: str | None
from_address: str
to_address: list[str]
subject: str
body: str
body_html: str | None
received_at: datetime
created_at: datetime
```

### 4.3 ChatModel

Referenced in: `backend/models/chat.py`

**Expected fields:**
```python
id: UUID
session_id: str
status: str  # active/closed
created_at: datetime
updated_at: datetime
```

---

## 5. SOFT DELETE PATTERN

Todos los modelos principales tienen `deleted_at: datetime | None`.

- Si `deleted_at IS NOT NULL` → el registro está "borrado" pero persiste en DB
- Queries activas deben filtrar `deleted_at IS NULL`
- Permite auditoría y restauración

```python
# Ejemplo de soft delete en PostgresStore
def soft_delete(self, model_class, record_id: str) -> bool:
    session = self.get_session()
    record = session.query(model_class).filter(
        model_class.id == record_id,
        model_class.deleted_at.is_(None),
    ).first()
    if record:
        record.deleted_at = func.now()
        session.commit()
        return True
    return False
```

---

## 6. POSTGRES STORE (NEON) IMPLEMENTATION

### 6.1 Connection Pooling

```python
self.engine = create_engine(
    database_url,
    echo=False,
    poolclass=QueuePool,
    pool_size=10,        # 10 conexiones simultáneas
    max_overflow=20,     # +20 bajo demanda
    pool_timeout=30,
    pool_recycle=3600,  # reconectar cada hora
    connect_args={"connect_timeout": 15},
)
```

### 6.2 SSL Configuration

```python
# En neon_store.py, el connection string incluye ?sslmode=require
# No se necesita connect_args adicional para SSL — el driver lo maneja
```

### 6.3 Session Factory

```python
self.SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=self.engine,
)

def get_session(self) -> Session:
    return self.SessionLocal()
```

---

## 7. MIGRATIONS (Alembic)

### 7.1 Current Status

Alembic está configurado en `jarvis-next/alembic/`:

- `alembic.ini` existe
- `alembic/` directory con `env.py` y `script.py.mako`

### 7.2 Migration Commands

```bash
cd jarvis-next

# Crear nueva migración
alembic revision --autogenerate -m "add calendar events table"

# Aplicar migraciones
alembic upgrade head

# Ver estado
alembic current
alembic history
```

### 7.3 Needed Migrations

1. Create `calendar_events` table
2. Create `email_messages` table (si no existe)
3. Create `chats` table (si no existe)

---

## 8. ENVIRONMENT CONFIGURATION

### 8.1 .env for NeonDB

```env
STORAGE_TYPE=neon
DATABASE_URL=postgresql://neondb_owner:npg_xxx@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

### 8.2 .env for SQLite (development)

```env
STORAGE_TYPE=sqlite
DATA_DIR=data
```

---

## 9. MISSING: psycopg2 dependency

According to session context:
> `neon_store.py` needs `psycopg2` or `asyncpg` in requirements

Check `requirements.txt` to ensure `psycopg2-binary` is present.

---

## 10. IMPORTANT NOTES FROM SESSION

### 10.1 Python 3.14 Warning

> Python 3.14 compatibility warning with Pydantic V1

Solution: Pydantic V2 migration o usar `pydantic-settings` que ya está.

### 10.2 Path Requirement

> Python path must be run from `jarvis-next/` root for `.env` to load

El working directory debe ser `jarvis-next/` al ejecutar el backend.

### 10.3 Límite actual

Las tablas `notes`, `todos`, `threads`, `messages` están creadas y vacías. Faltan las demás.

---

## 11. PRÓXIMOS PASOS

1. [ ] Verificar que `psycopg2-binary` está en requirements.txt
2. [ ] Crear migración para `calendar_events`
3. [ ] Crear migración para `email_messages`
4. [ ] Crear migración para `chats`
5. [ ] Correr `alembic upgrade head` para crear todas las tablas
6. [ ] Crear script de seed data para testing
7. [ ] Verificar que `get_store()` factory funciona con `STORAGE_TYPE=neon`
8. [ ] Implementar connection health check en readiness probe