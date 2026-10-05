"""
SQLite-backed drop-in for SessionRepository (MongoDB), used for local runs
when DB_TYPE=sqlite. Documents are stored as JSON; datetimes round-trip.
"""

import json
import sqlite3
import threading
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Optional

from config import Config
from repositories.RepositoryBase import RepositoryBase
from core.message_serializer import deserialize_messages


def _encode(obj):
    if isinstance(obj, datetime):
        return {"$dt": obj.isoformat()}
    return str(obj)


def _decode(d: dict):
    if set(d.keys()) == {"$dt"}:
        return datetime.fromisoformat(d["$dt"])
    return d


def _dumps(doc: dict) -> str:
    return json.dumps({k: v for k, v in doc.items() if k != "_id"}, default=_encode)


def _loads(raw: str) -> dict:
    return json.loads(raw, object_hook=_decode)


class SQLiteSessionRepository(RepositoryBase):
    def __init__(self, path: str = None):
        self.__path = path or Config.SQLITE_SESSION_DB_PATH
        self.__lock = threading.Lock()
        self.__conn = sqlite3.connect(self.__path, check_same_thread=False)
        self.__conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                user_email   TEXT,
                last_updated TEXT,
                doc          TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS session_messages (
                response_id TEXT PRIMARY KEY,
                session_id  TEXT,
                timestamp   TEXT,
                doc         TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_msg_session ON session_messages(session_id);
        """)

    # -------------------- helpers --------------------
    def _query(self, sql: str, params=()) -> list:
        with self.__lock:
            return self.__conn.execute(sql, params).fetchall()

    def _execute(self, sql: str, params=()) -> int:
        with self.__lock:
            cur = self.__conn.execute(sql, params)
            self.__conn.commit()
            return cur.rowcount

    def _save_session(self, doc: dict):
        last_updated = doc.get("last_updated") or datetime.utcnow()
        self._execute(
            "INSERT OR REPLACE INTO sessions (session_id, user_email, last_updated, doc) VALUES (?, ?, ?, ?)",
            (doc["session_id"], doc.get("user_email"), last_updated.isoformat(), _dumps(doc)),
        )

    def _save_message(self, doc: dict):
        ts = doc.get("timestamp") or datetime.utcnow()
        self._execute(
            "INSERT OR REPLACE INTO session_messages (response_id, session_id, timestamp, doc) VALUES (?, ?, ?, ?)",
            (doc.get("response_id"), doc.get("session_id"), ts.isoformat() if isinstance(ts, datetime) else str(ts), _dumps(doc)),
        )

    def _get_message(self, response_id: str) -> Optional[Dict]:
        rows = self._query("SELECT doc FROM session_messages WHERE response_id = ?", (response_id,))
        return _loads(rows[0][0]) if rows else None

    # -------------------- CRUD --------------------
    def create(self, data: dict) -> str:
        self._save_session(dict(data))
        return data["session_id"]

    def aggregate(self, pipeline):
        raise NotImplementedError("aggregate is not supported by the SQLite session store")

    def get_all(self, limit: int = 50) -> List[Dict]:
        return [_loads(r[0]) for r in self._query("SELECT doc FROM sessions LIMIT ?", (limit,))]

    def get_by_id(self, session_id: str) -> Optional[Dict]:
        if not session_id:
            return None
        rows = self._query("SELECT doc FROM sessions WHERE session_id = ?", (session_id,))
        return _loads(rows[0][0]) if rows else None

    def update(self, session_id: str, data: dict):
        session = self.get_by_id(session_id)
        if not session:
            return
        data = dict(data)
        data.pop("last_updated", None)
        session.update(data)
        session["last_updated"] = datetime.utcnow()
        self._save_session(session)

    def get_all_sessions(self, user_email, limit):
        rows = self._query(
            "SELECT doc FROM sessions WHERE user_email = ? AND last_updated >= ? ORDER BY last_updated DESC",
            (user_email, limit.isoformat()),
        )
        keys = ("session_id", "session_name", "module_name", "session_type", "last_updated")
        return [{k: d[k] for k in keys if k in d} for d in (_loads(r[0]) for r in rows)]

    def delete(self, session_id: str):
        self._execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        self._execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))

    # -------------------- Session Messages --------------------
    def add_message(self, message: dict):
        self._save_message(message)

    def get_messages(self, session_id: str) -> List[Dict]:
        rows = self._query("SELECT doc FROM session_messages WHERE session_id = ? ORDER BY timestamp", (session_id,))
        return [_loads(r[0]) for r in rows]

    def save_history(self, session_id: str, history: List[Dict]):
        self.update(session_id, {"chat_history": history})

    def load_history(self, session_id: str) -> List[Dict]:
        session = self.get_by_id(session_id)
        return deserialize_messages(session.get("chat_history", []) if session else [])

    def text_to_sql_messages(self, session_id: str):
        return self.get_messages(session_id)[:10]

    def update_message(self, response_id, update_data):
        msg = self._get_message(response_id)
        if msg:
            msg.update(update_data)
            self._save_message(msg)

    def _update_feedback(self, session_id, response_id, fields: dict):
        msg = self._get_message(response_id)
        if not msg or msg.get("session_id") != session_id:
            return SimpleNamespace(modified_count=0)
        msg.update(fields)
        self._save_message(msg)
        return SimpleNamespace(modified_count=1)

    def update_like_feedback(self, session_id, response_id, like):
        return self._update_feedback(session_id, response_id, {"like": like})

    def update_message_feedback(self, session_id, response_id, feedback):
        return self._update_feedback(session_id, response_id, {"feedback": feedback})

    # -------------------- Sync Queries --------------------
    def get_sessions_updated_since(self, since: datetime) -> List[Dict]:
        return [_loads(r[0]) for r in self._query("SELECT doc FROM sessions WHERE last_updated > ?", (since.isoformat(),))]

    def get_messages_since(self, since: datetime) -> List[Dict]:
        return [_loads(r[0]) for r in self._query("SELECT doc FROM session_messages WHERE timestamp > ?", (since.isoformat(),))]

    def get_all_sessions_full(self) -> List[Dict]:
        return [_loads(r[0]) for r in self._query("SELECT doc FROM sessions")]

    def get_all_messages_full(self) -> List[Dict]:
        return [_loads(r[0]) for r in self._query("SELECT doc FROM session_messages")]
