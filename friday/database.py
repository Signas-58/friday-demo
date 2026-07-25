import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "friday.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite tables for chat history and memories."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_call_id TEXT,
                name TEXT,
                timestamp TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                fact TEXT NOT NULL,
                timestamp TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()

def save_message(role: str, content: str, tool_call_id: str = None, name: str = None):
    """Save a chat message to history."""
    # Never save empty assistant content or raw system instructions to chat_history
    if not content and role == "assistant":
        return
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO chat_history (role, content, tool_call_id, name) VALUES (?, ?, ?, ?)",
            (role, content, tool_call_id, name)
        )
        conn.commit()

def get_chat_history(limit: int = 50):
    """Retrieve the recent message history log."""
    init_db()  # Safely ensure DB exists
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT role, content, tool_call_id, name FROM chat_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        # Return in chronological order
        messages = []
        for row in reversed(rows):
            msg = {"role": row["role"], "content": row["content"]}
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            if row["name"]:
                msg["name"] = row["name"]
            messages.append(msg)
        return messages

def clear_chat_history():
    """Purge all conversation logs from the database."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM chat_history")
        conn.commit()

def save_memory(key: str, fact: str) -> int:
    """Insert or update a user memory fact."""
    init_db()
    with get_db_connection() as conn:
        # Check if this exact fact exists under the key to avoid duplication
        cursor = conn.execute("SELECT id FROM user_memories WHERE key = ? AND fact = ?", (key, fact))
        row = cursor.fetchone()
        if row:
            return row["id"]
        
        cursor = conn.execute(
            "INSERT INTO user_memories (key, fact) VALUES (?, ?)",
            (key, fact)
        )
        conn.commit()
        return cursor.lastrowid

def list_memories():
    """Retrieve all saved user memories."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT id, key, fact FROM user_memories ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]

def delete_memory(memory_id: int) -> bool:
    """Delete a memory by id."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM user_memories WHERE id = ?", (memory_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_memories_prompt() -> str:
    """Format user memories as a text block for prompt injection."""
    memories = list_memories()
    if not memories:
        return ""
    
    lines = ["\n[Stored Memories regarding Tsakane]:"]
    for m in memories:
        lines.append(f"- ID {m['id']} | Category: {m['key']} | Fact: {m['fact']}")
    return "\n".join(lines)
