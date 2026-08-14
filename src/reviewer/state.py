import sqlite3
from pathlib import Path

class ReviewState:
    def __init__(self,path:Path):
        self.conn=sqlite3.connect(path);self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS reviews(id TEXT NOT NULL,content_hash TEXT NOT NULL,review_type TEXT NOT NULL,status TEXT NOT NULL,model TEXT NOT NULL,prompt_version TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,reviewed_at TEXT,recommended_action TEXT,error TEXT,PRIMARY KEY(id,content_hash,prompt_version,model,review_type));
        """);self.conn.commit()
    def ensure(self,candidate,review_type,model,prompt_version):
        self.conn.execute("INSERT OR IGNORE INTO reviews(id,content_hash,review_type,status,model,prompt_version) VALUES(?,?,?,'pending',?,?)",(candidate["id"],candidate["content_hash"],review_type,model,prompt_version));self.conn.commit()
    def status(self,candidate,review_type,model,prompt_version):
        return self.conn.execute("SELECT * FROM reviews WHERE id=? AND content_hash=? AND review_type=? AND model=? AND prompt_version=?",(candidate["id"],candidate["content_hash"],review_type,model,prompt_version)).fetchone()
    def processing(self,candidate,review_type,model,prompt_version):
        self.conn.execute("UPDATE reviews SET status='processing',attempts=attempts+1,error=NULL WHERE id=? AND content_hash=? AND review_type=? AND model=? AND prompt_version=?",(candidate["id"],candidate["content_hash"],review_type,model,prompt_version));self.conn.commit()
    def done(self,candidate,review_type,model,prompt_version,stamp,action):
        self.conn.execute("UPDATE reviews SET status='done',reviewed_at=?,recommended_action=?,error=NULL WHERE id=? AND content_hash=? AND review_type=? AND model=? AND prompt_version=?",(stamp,action,candidate["id"],candidate["content_hash"],review_type,model,prompt_version));self.conn.commit()
    def error(self,candidate,review_type,model,prompt_version,stamp,error):
        self.conn.execute("UPDATE reviews SET status='error',reviewed_at=?,error=? WHERE id=? AND content_hash=? AND review_type=? AND model=? AND prompt_version=?",(stamp,error,candidate["id"],candidate["content_hash"],review_type,model,prompt_version));self.conn.commit()
    def recover(self):self.conn.execute("UPDATE reviews SET status='pending' WHERE status='processing'");self.conn.commit()
    def counts(self):return self.conn.execute("SELECT review_type,status,count(*) n FROM reviews GROUP BY review_type,status").fetchall()
    def close(self):self.conn.commit();self.conn.close()

