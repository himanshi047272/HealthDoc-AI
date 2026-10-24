"""SQLite repository. Uses stdlib sqlite3 so it runs without extra packages."""
from __future__ import annotations
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, filename TEXT, stored_name TEXT, mime TEXT, kind TEXT,
 size_bytes INT, sha256 TEXT, status TEXT, error TEXT, page_count INT DEFAULT 0, chunk_count INT DEFAULT 0,
 ocr_pages INT DEFAULT 0, extractor TEXT, doc_type TEXT, doc_type_score REAL, is_demo INT DEFAULT 0,
 duration_ms INT, created_at REAL, updated_at REAL);
CREATE TABLE IF NOT EXISTS pages(doc_id TEXT, page_no INT, text TEXT, source TEXT, ocr_conf REAL, PRIMARY KEY(doc_id,page_no));
CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, doc_id TEXT, page_no INT, idx INT, text TEXT, source TEXT);
CREATE INDEX IF NOT EXISTS ix_chunks_doc ON chunks(doc_id);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, doc_id TEXT, status TEXT, stage TEXT, error TEXT, started_at REAL, finished_at REAL);
CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, created_at REAL);
CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, conv_id TEXT, role TEXT, content TEXT, mode TEXT, abstained INT,
 latency_ms REAL, doc_ids TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS citations(id TEXT PRIMARY KEY, message_id TEXT, n INT, doc_id TEXT, page_no INT, chunk_id TEXT, excerpt TEXT, valid INT);
CREATE TABLE IF NOT EXISTS searches(id TEXT PRIMARY KEY, kind TEXT, latency_ms REAL, n_results INT, created_at REAL);
CREATE TABLE IF NOT EXISTS eval_runs(id TEXT PRIMARY KEY, created_at REAL, metrics TEXT, results TEXT);
"""

SORTABLE = {"created_at", "filename", "page_count", "status", "size_bytes"}


def new_id() -> str:
    return uuid.uuid4().hex[:16]



   
class Store:
    def __init__(self, path):
        self.path = str(path)
        self._lock = threading.RLock()

        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(
            self.path,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.version = 0

    def close(self):
        with self._lock:
            if self.conn is not None:
                self.conn.close()
                self.conn = None

    def q(self, sql, args=(), one=False):
        with self._lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            rows = [dict(r) for r in cur.fetchall()] if cur.description else []

        return (rows[0] if rows else None) if one else rows


    # documents
    def add_document(self, **f) -> dict:
        now = time.time()
        d = dict(id=new_id(), status="uploaded", error=None, created_at=now, updated_at=now, is_demo=0)
        d.update(f)
        self.q(f"INSERT INTO documents({','.join(d)}) VALUES({','.join('?' * len(d))})", tuple(d.values()))
        return self.get_document(d["id"])

    def get_document(self, doc_id):
        return self.q("SELECT * FROM documents WHERE id=?", (doc_id,), one=True)

    def update_document(self, doc_id, **f):
        f["updated_at"] = time.time()
        sets = ",".join(f"{k}=?" for k in f)
        self.q(f"UPDATE documents SET {sets} WHERE id=?", (*f.values(), doc_id))

    def find_by_hash(self, sha):
        return self.q("SELECT * FROM documents WHERE sha256=?", (sha,), one=True)

    def list_documents(self, q=None, status=None, kind=None, doc_type=None, sort="created_at", order="desc", page=1, page_size=20):
        where, args = [], []
        if q:
            where.append("filename LIKE ?"); args.append(f"%{q}%")
        for col, val in (("status", status), ("kind", kind), ("doc_type", doc_type)):
            if val:
                where.append(f"{col}=?"); args.append(val)
        w = f"WHERE {' AND '.join(where)}" if where else ""
        sort = sort if sort in SORTABLE else "created_at"
        order = "ASC" if str(order).lower() == "asc" else "DESC"
        total = self.q(f"SELECT COUNT(*) c FROM documents {w}", tuple(args), one=True)["c"]
        rows = self.q(f"SELECT * FROM documents {w} ORDER BY {sort} {order} LIMIT ? OFFSET ?",
                      (*args, page_size, (page - 1) * page_size))
        return rows, total

    def delete_document(self, doc_id):
        for t in ("pages", "chunks", "jobs"):
            self.q(f"DELETE FROM {t} WHERE doc_id=?", (doc_id,))
        self.q("DELETE FROM citations WHERE doc_id=?", (doc_id,))
        self.q("DELETE FROM documents WHERE id=?", (doc_id,))
        self.version += 1

    # pages / chunks
    def replace_pages(self, doc_id, pages):
        self.q("DELETE FROM pages WHERE doc_id=?", (doc_id,))
        with self._lock:
            self.conn.executemany("INSERT INTO pages VALUES(?,?,?,?,?)",
                                  [(doc_id, p["page_no"], p["text"], p["source"], p.get("ocr_conf")) for p in pages])
            self.conn.commit()

    def get_pages(self, doc_id):
        return self.q("SELECT * FROM pages WHERE doc_id=? ORDER BY page_no", (doc_id,))

    def replace_chunks(self, doc_id, chunks):
        self.q("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        with self._lock:
            self.conn.executemany("INSERT INTO chunks VALUES(?,?,?,?,?,?)",
                                  [(c["id"], doc_id, c["page_no"], c["idx"], c["text"], c["source"]) for c in chunks])
            self.conn.commit()
        self.version += 1

    def get_chunks(self, ready_only=True):
        sql = "SELECT c.* FROM chunks c JOIN documents d ON d.id=c.doc_id"
        if ready_only:
            sql += " WHERE d.status='ready'"
        return self.q(sql + " ORDER BY c.doc_id, c.page_no, c.idx")

    # jobs
    def create_job(self, doc_id):
        j = new_id()
        self.q("INSERT INTO jobs VALUES(?,?,?,?,?,?,?)", (j, doc_id, "running", "queued", None, time.time(), None))
        return j

    def update_job(self, job_id, **f):
        sets = ",".join(f"{k}=?" for k in f)
        self.q(f"UPDATE jobs SET {sets} WHERE id=?", (*f.values(), job_id))

    def latest_job(self, doc_id):
        return self.q("SELECT * FROM jobs WHERE doc_id=? ORDER BY started_at DESC LIMIT 1", (doc_id,), one=True)

    # chat
    def add_conversation(self):
        c = new_id(); self.q("INSERT INTO conversations VALUES(?,?)", (c, time.time())); return c

    def conversation_exists(self, cid):
        return self.q("SELECT 1 x FROM conversations WHERE id=?", (cid,), one=True) is not None

    def add_message(self, conv_id, role, content, mode=None, abstained=0, latency_ms=None, doc_ids=None):
        m = new_id()
        self.q("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)",
               (m, conv_id, role, content, mode, int(abstained), latency_ms, json.dumps(doc_ids or []), time.time()))
        return m

    def add_citations(self, message_id, cites):
        for c in cites:
            self.q("INSERT INTO citations VALUES(?,?,?,?,?,?,?,?)", (new_id(), message_id, c["n"], c["document_id"],
                   c["page_no"], c["chunk_id"], c["excerpt"], int(c["valid"])))

    def get_messages(self, conv_id):
        msgs = self.q("SELECT * FROM messages WHERE conv_id=? ORDER BY created_at, rowid", (conv_id,))
        for m in msgs:
            m["citations"] = self.q(
                "SELECT c.n, c.doc_id document_id, d.filename, c.page_no, c.chunk_id, c.excerpt, c.valid FROM citations c "
                "LEFT JOIN documents d ON d.id=c.doc_id WHERE c.message_id=? ORDER BY c.n", (m["id"],))
        return msgs

    # metrics
    def log_search(self, kind, latency_ms, n):
        self.q("INSERT INTO searches VALUES(?,?,?,?,?)", (new_id(), kind, latency_ms, n, time.time()))

    def add_eval_run(self, metrics, results):
        r = new_id()
        self.q("INSERT INTO eval_runs VALUES(?,?,?,?)", (r, time.time(), json.dumps(metrics), json.dumps(results)))
        return r

    def latest_eval_run(self):
        r = self.q("SELECT * FROM eval_runs ORDER BY created_at DESC LIMIT 1", one=True)
        if r:
            r["metrics"], r["results"] = json.loads(r["metrics"]), json.loads(r["results"])
        return r
