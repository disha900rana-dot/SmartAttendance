import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "attendance.db"

@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            email TEXT,
            face_path TEXT NOT NULL,
            embedding BLOB NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            check_in_time TEXT NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Present',
            FOREIGN KEY(student_id) REFERENCES students(id),
            UNIQUE(student_id, attendance_date)
        );
        """)

def rows(query, params=()):
    with connection() as conn:
        return [dict(item) for item in conn.execute(query, params).fetchall()]

def row(query, params=()):
    with connection() as conn:
        result = conn.execute(query, params).fetchone()
        return dict(result) if result else None
