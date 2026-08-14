from __future__ import annotations
import sqlite3
from pathlib import Path
from threading import Lock

class PortalState:
    def __init__(self,path:Path):
        self.conn=sqlite3.connect(path,check_same_thread=False); self.conn.row_factory=sqlite3.Row; self.lock=Lock()
        self.conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS urls(url TEXT PRIMARY KEY,normalized_url TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',priority_score INTEGER NOT NULL,depth INTEGER NOT NULL,parent_url TEXT,anchor_text TEXT,discovered_from TEXT,reason TEXT,page_id TEXT,content_hash TEXT,crawl_time TEXT,discovered_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS portal_queue ON urls(status,priority_score DESC,depth,discovered_at);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,url TEXT UNIQUE,content_hash TEXT UNIQUE,simhash TEXT,title TEXT,markdown_path TEXT,crawl_time TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        """); self.conn.commit()
    def add(self,url,priority,depth,parent,anchor,source,stamp):
        with self.lock:
            cur=self.conn.execute("INSERT OR IGNORE INTO urls(url,normalized_url,priority_score,depth,parent_url,anchor_text,discovered_from,discovered_at) VALUES(?,?,?,?,?,?,?,?)",(url,url,priority,depth,parent,anchor,source,stamp)); self.conn.commit(); return cur.rowcount>0
    def claim(self):
        with self.lock:
            r=self.conn.execute("SELECT * FROM urls WHERE status='pending' ORDER BY priority_score DESC,depth,discovered_at LIMIT 1").fetchone()
            if not r:return None
            self.conn.execute("UPDATE urls SET status='processing' WHERE url=?",(r["url"],));self.conn.commit();return dict(r)
    def finish(self,url,status,stamp,reason="",page_id=None,digest=None):
        with self.lock:self.conn.execute("UPDATE urls SET status=?,reason=?,page_id=?,content_hash=?,crawl_time=? WHERE url=?",(status,reason,page_id,digest,stamp,url));self.conn.commit()
    def recover(self):
        with self.lock:self.conn.execute("UPDATE urls SET status='pending' WHERE status='processing'");self.conn.commit()
    def reprioritize(self,scorer):
        with self.lock:
            rows=self.conn.execute("SELECT url,anchor_text FROM urls WHERE status='pending'").fetchall()
            self.conn.executemany("UPDATE urls SET priority_score=? WHERE url=?",((scorer(r[0],r[1] or ""),r[0]) for r in rows));self.conn.commit()
    def next_id(self):
        with self.lock:
            row=self.conn.execute("SELECT value FROM settings WHERE key='next_id'").fetchone(); n=int(row[0]) if row else 1
            self.conn.execute("INSERT OR REPLACE INTO settings VALUES('next_id',?)",(str(n+1),));self.conn.commit();return f"PORTAL{n:06d}"
    def find_hash(self,d):return self.conn.execute("SELECT * FROM documents WHERE content_hash=?",(d,)).fetchone()
    def similar(self):return self.conn.execute("SELECT id,url,simhash FROM documents WHERE simhash IS NOT NULL").fetchall()
    def document(self,values):
        with self.lock:self.conn.execute("INSERT INTO documents(id,url,content_hash,simhash,title,markdown_path,crawl_time) VALUES(?,?,?,?,?,?,?)",values);self.conn.commit()
    def close(self):self.conn.commit();self.conn.close()
