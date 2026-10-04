from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .common import PipelineError, canonical_url, digest, json_text, utc_now


class State:
    def __init__(self, path: Path, dataset: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, metadata TEXT NOT NULL,
                body TEXT, body_hash TEXT, duplicate_of TEXT,
                fetch_attempts INTEGER NOT NULL DEFAULT 0, fetch_error TEXT, fetch_retryable INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS content_index ON records(body_hash);
            CREATE TABLE IF NOT EXISTS enrichments (
                record_id TEXT NOT NULL, signature TEXT NOT NULL, result TEXT,
                attempts INTEGER NOT NULL DEFAULT 0, error TEXT, retryable INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(record_id, signature)
            );
            CREATE TABLE IF NOT EXISTS revisions (
                record_id TEXT NOT NULL, revision INTEGER NOT NULL, changed_at TEXT NOT NULL,
                old_hash TEXT NOT NULL, new_hash TEXT NOT NULL, old_body TEXT NOT NULL, new_body TEXT NOT NULL,
                PRIMARY KEY(record_id, revision)
            );
            CREATE TABLE IF NOT EXISTS checkpoints (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        existing = self.db.execute("SELECT value FROM settings WHERE key='dataset'").fetchone()
        if existing and existing["value"] != dataset:
            self.close()
            raise PipelineError("workspace_dataset_mismatch")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO settings VALUES ('dataset', ?)", (dataset,))

    def close(self):
        self.db.close()

    def add(self, metadata):
        url = canonical_url(metadata["url"])
        record_id = digest(url)[:24]
        existing = self.db.execute("SELECT metadata FROM records WHERE id=?", (record_id,)).fetchone()
        origin = {key: metadata.get(key) for key in ("source_id", "source_name", "query", "discovery_provider", "url", "published_at")}
        if existing:
            merged = json.loads(existing["metadata"])
            if origin not in merged["sources"]:
                merged["sources"].append(origin)
                with self.db:
                    self.db.execute("UPDATE records SET metadata=? WHERE id=?", (json_text(merged), record_id))
                    duplicate = self.db.execute("SELECT duplicate_of FROM records WHERE id=?", (record_id,)).fetchone()["duplicate_of"]
                    if duplicate:
                        primary = self.db.execute("SELECT metadata FROM records WHERE id=?", (duplicate,)).fetchone()
                        primary_metadata = json.loads(primary["metadata"])
                        if origin not in primary_metadata["sources"]:
                            primary_metadata["sources"].append(origin)
                            self.db.execute("UPDATE records SET metadata=? WHERE id=?", (json_text(primary_metadata), duplicate))
            return False
        metadata = {**metadata, "url": url, "collected_at": utc_now(), "sources": [origin]}
        with self.db:
            self.db.execute("INSERT INTO records (id,url,metadata) VALUES (?,?,?)", (record_id, url, json_text(metadata)))
        return True

    def records(self):
        return self.db.execute("SELECT * FROM records ORDER BY rowid").fetchall()

    def fetched(self, record_id, body, metadata):
        content_hash = digest(" ".join(body.split()))
        previous = self.db.execute("SELECT body,body_hash FROM records WHERE id=?", (record_id,)).fetchone()
        metadata = {**metadata, "checked_at": utc_now()}
        with self.db:
            if previous["body"] is not None and previous["body_hash"] == content_hash:
                # Preserve exact excerpts and cached enrichment for whitespace-only changes.
                body = previous["body"]
            elif previous["body"] is not None:
                revision = self.db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM revisions WHERE record_id=?", (record_id,)).fetchone()[0]
                self.db.execute("INSERT INTO revisions VALUES (?,?,?,?,?,?,?)",
                                (record_id, revision, metadata["checked_at"], previous["body_hash"], content_hash, previous["body"], body))
                self.db.execute("DELETE FROM enrichments WHERE record_id=?", (record_id,))
            self.db.execute("UPDATE records SET body=?,body_hash=?,metadata=?,fetch_error=NULL,fetch_attempts=0,fetch_retryable=1 WHERE id=?",
                            (body, content_hash, json_text(metadata), record_id))
            # Recompute representatives so a refreshed primary or duplicate can diverge.
            representatives = {}
            for row in self.db.execute("SELECT id,body_hash FROM records ORDER BY rowid").fetchall():
                duplicate = representatives.get(row["body_hash"]) if row["body_hash"] else None
                self.db.execute("UPDATE records SET duplicate_of=? WHERE id=?", (duplicate, row["id"]))
                if row["body_hash"] and duplicate is None:
                    representatives[row["body_hash"]] = row["id"]
            duplicate = self.db.execute("SELECT duplicate_of FROM records WHERE id=?", (record_id,)).fetchone()[0]
            if duplicate:
                primary = self.db.execute("SELECT metadata FROM records WHERE id=?", (duplicate,)).fetchone()
                merged = json.loads(primary["metadata"])
                for origin in metadata["sources"]:
                    if origin not in merged["sources"]:
                        merged["sources"].append(origin)
                self.db.execute("UPDATE records SET metadata=? WHERE id=?", (json_text(merged), duplicate))
        return duplicate

    def changes(self):
        return [dict(row) for row in self.db.execute("SELECT * FROM revisions ORDER BY changed_at,record_id,revision")]

    def fetch_failure(self, record_id, error):
        with self.db:
            self.db.execute("UPDATE records SET fetch_attempts=fetch_attempts+1,fetch_error=?,fetch_retryable=? WHERE id=?", (error.code, int(error.retryable), record_id))

    def enriched(self, record_id, signature):
        return self.db.execute("SELECT * FROM enrichments WHERE record_id=? AND signature=?", (record_id, signature)).fetchone()

    def enrichment_result(self, record_id, signature, result):
        with self.db:
            self.db.execute("INSERT INTO enrichments (record_id,signature,result,attempts,error) VALUES (?,?,?,1,NULL) ON CONFLICT(record_id,signature) DO UPDATE SET result=excluded.result,error=NULL",
                            (record_id, signature, json_text(result)))

    def enrichment_failure(self, record_id, signature, error):
        with self.db:
            self.db.execute("INSERT INTO enrichments (record_id,signature,attempts,error,retryable) VALUES (?,?,1,?,?) ON CONFLICT(record_id,signature) DO UPDATE SET attempts=attempts+1,error=excluded.error,retryable=excluded.retryable",
                            (record_id, signature, error.code, int(error.retryable)))

    def checkpoint(self, key):
        row = self.db.execute("SELECT value FROM checkpoints WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_checkpoint(self, key, value):
        with self.db:
            self.db.execute("INSERT INTO checkpoints VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
