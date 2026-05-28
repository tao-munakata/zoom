import sqlite3, os

DB_PATH = os.environ.get('DB_PATH', '/data/db/tasks.db')

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                zoom_url TEXT NOT NULL,
                meeting_id TEXT DEFAULT '',
                password TEXT DEFAULT '',
                start_at TEXT NOT NULL,
                end_at TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        # 既存DBへのカラム追加（初回のみ実行）
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN end_at TEXT DEFAULT ''")
        except Exception:
            pass

def create_task(title, zoom_url, meeting_id, password, start_at, end_at=''):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title,zoom_url,meeting_id,password,start_at,end_at) VALUES (?,?,?,?,?,?)",
            (title, zoom_url, meeting_id, password, start_at, end_at)
        )
        return cur.lastrowid

def get_all_tasks():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM tasks ORDER BY start_at DESC")]

def get_pending_tasks():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE status='pending'")]

def update_status(task_id, status):
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status=?,updated_at=datetime('now','localtime') WHERE id=?",
            (status, task_id)
        )

def delete_task(task_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
