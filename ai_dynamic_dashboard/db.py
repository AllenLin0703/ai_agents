"""SQLite 存储层 — 保存 metrics 和 alerts 历史"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "dashboard.db"


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS metrics (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        TEXT NOT NULL,
                source    TEXT NOT NULL,
                data      TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        TEXT NOT NULL,
                level     TEXT NOT NULL,
                message   TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def save_metric(self, source: str, data: dict):
        ts = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO metrics (ts, source, data) VALUES (?, ?, ?)",
            (ts, source, json.dumps(data, ensure_ascii=False)),
        )
        self.conn.commit()

    def save_alert(self, level: str, message: str):
        ts = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO alerts (ts, level, message) VALUES (?, ?, ?)",
            (ts, level, message),
        )
        self.conn.commit()

    def get_recent_metrics(self, limit: int = 10) -> dict:
        """返回各来源最新的 N 条记录"""
        result = {}
        for source in ("github", "social", "market", "system"):
            rows = self.conn.execute(
                "SELECT ts, data FROM metrics WHERE source=? ORDER BY id DESC LIMIT ?",
                (source, limit),
            ).fetchall()
            result[source] = [
                {"ts": r[0], **json.loads(r[1])} for r in rows
            ]
        return result

    def get_recent_alerts(self, limit: int = 20) -> list:
        rows = self.conn.execute(
            "SELECT ts, level, message FROM alerts ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"ts": r[0], "level": r[1], "message": r[2]} for r in rows]

    def close(self):
        self.conn.close()
