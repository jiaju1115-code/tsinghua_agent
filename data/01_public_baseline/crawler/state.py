from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock

class CrawlState:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = Lock()
        self.conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS urls (
          url TEXT PRIMARY KEY, depth INTEGER NOT NULL, parent_url TEXT,
          status TEXT NOT NULL DEFAULT 'pending', retries INTEGER NOT NULL DEFAULT 0,
          error TEXT, discovered_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_urls_status_depth ON urls(status, depth, discovered_at);
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, final_url TEXT, content_hash TEXT UNIQUE NOT NULL,
          title TEXT, markdown_path TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        self.conn.commit()
        columns={r[1] for r in self.conn.execute("PRAGMA table_info(urls)")}
        if "priority" not in columns:
            self.conn.execute("ALTER TABLE urls ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")
        doc_columns={r[1] for r in self.conn.execute("PRAGMA table_info(documents)")}
        if "simhash" not in doc_columns:
            self.conn.execute("ALTER TABLE documents ADD COLUMN simhash TEXT")
        self.conn.commit()

    def add_url(self, url, depth, parent, now, priority=0) -> bool:
        with self.lock:
            cur = self.conn.execute("INSERT OR IGNORE INTO urls(url,depth,parent_url,discovered_at,updated_at,priority) VALUES(?,?,?,?,?,?)", (url, depth, parent, now, now, priority))
            if cur.rowcount == 0:
                self.conn.execute("UPDATE urls SET priority=MAX(priority,?) WHERE url=? AND status='pending'",(priority,url))
            self.conn.commit(); return cur.rowcount > 0

    def claim(self):
        with self.lock:
            row = self.conn.execute("SELECT * FROM urls WHERE status='pending' ORDER BY priority DESC, depth, discovered_at LIMIT 1").fetchone()
            if not row: return None
            self.conn.execute("UPDATE urls SET status='processing' WHERE url=?", (row["url"],)); self.conn.commit()
            return dict(row)

    def finish(self, url, status, now, error=None, retries=None):
        with self.lock:
            if retries is None: self.conn.execute("UPDATE urls SET status=?,error=?,updated_at=? WHERE url=?", (status,error,now,url))
            else: self.conn.execute("UPDATE urls SET status=?,error=?,retries=?,updated_at=? WHERE url=?", (status,error,retries,now,url))
            self.conn.commit()

    def recover(self, retry_failed=False):
        with self.lock:
            self.conn.execute("UPDATE urls SET status='pending' WHERE status='processing'")
            if retry_failed: self.conn.execute("UPDATE urls SET status='pending',error=NULL WHERE status='failed'")
            self.conn.commit()

    def reprioritize(self, scorer):
        with self.lock:
            rows=self.conn.execute("SELECT url FROM urls WHERE status='pending'").fetchall()
            self.conn.executemany("UPDATE urls SET priority=? WHERE url=?",((scorer(r[0]),r[0]) for r in rows))
            self.conn.commit()

    def next_id(self) -> str:
        with self.lock:
            value = int((self.conn.execute("SELECT value FROM settings WHERE key='next_id'").fetchone() or ["1"])[0])
            self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('next_id',?)", (str(value+1),)); self.conn.commit()
            return f"THU{value:06d}"
    def setting(self,key,default=None):
        row=self.conn.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone();return row[0] if row else default
    def set_setting(self,key,value):
        with self.lock:self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(key,str(value)));self.conn.commit()

    def find_hash(self, digest): return self.conn.execute("SELECT * FROM documents WHERE content_hash=?", (digest,)).fetchone()
    def add_document(self, values, simhash=None):
        with self.lock:
            self.conn.execute("INSERT INTO documents(id,url,final_url,content_hash,title,markdown_path,created_at,simhash) VALUES(?,?,?,?,?,?,?,?)", (*values,simhash)); self.conn.commit()
    def similar_documents(self): return self.conn.execute("SELECT id,url,simhash FROM documents WHERE simhash IS NOT NULL").fetchall()
    def counts(self): return {r[0]: r[1] for r in self.conn.execute("SELECT status,count(*) FROM urls GROUP BY status")}
    def close(self): self.conn.commit(); self.conn.close()
