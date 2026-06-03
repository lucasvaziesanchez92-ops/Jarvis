from backend.storage import get_store
import sqlalchemy as sa

store = get_store()
session = store.get_session()

tables = session.execute(sa.text(
    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
)).fetchall()

print('Tablas en NeonDB:', [t[0] for t in tables])

for t in ['notes', 'todos', 'threads', 'messages']:
    try:
        c = session.execute(sa.text(f'SELECT COUNT(*) FROM {t}')).fetchone()[0]
        print(f'  {t}: {c} registros')
    except:
        print(f'  {t}: sin datos o error')

session.close()
print()
print('Conexion a NeonDB: OK')