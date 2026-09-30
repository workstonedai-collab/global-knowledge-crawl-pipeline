from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from .common import BudgetExceeded, PipelineError, digest, utc_now
from .config import Budget, Config
from .discovery import search_items, source_items
from .enrichment import Enricher
from .exports import export_records, write_json
from .fetching import Fetcher
from .http import HttpClient
from .state import State


@contextmanager
def workspace_lock(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    stream = (directory / ".run.lock").open("a+b")
    try:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if __import__("os").name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise PipelineError("workspace_already_running") from None
        yield
    finally:
        stream.close()


def run(config: Config, workspace: Path, *, retry_failed=False, retry_review=False, discover=True):
    with workspace_lock(workspace):
        state = State(workspace / "state.sqlite", config.dataset)
        try:
            return _run(config, workspace, state, retry_failed, retry_review, discover)
        finally:
            state.close()


def _run(config, workspace, state, retry_failed, retry_review, discover):
    started = utc_now()
    budget = Budget(config.limits)
    http = HttpClient(budget, offline=config.offline, allow_private=config.data.get("allow_private_network", False),
                      timeout=config.fetch.get("timeout_seconds", 20), max_bytes=config.fetch.get("max_response_bytes", 2_000_000))
    fetcher = Fetcher(config, http)
    enricher = Enricher(config, http, budget)
    errors = []
    stop_reason = None
    added = 0
    if retry_failed:
        with state.db:
            state.db.execute("UPDATE records SET fetch_attempts=0,fetch_error=NULL,fetch_retryable=1 WHERE body IS NULL")
            state.db.execute("DELETE FROM enrichments WHERE signature=? AND result IS NULL", (config.signature,))
    if retry_review:
        with state.db:
            # Keep validated results and earlier schema versions intact.
            for row in state.db.execute("SELECT record_id,result FROM enrichments WHERE signature=? AND result IS NOT NULL", (config.signature,)).fetchall():
                if json.loads(row["result"])["status"] == "needs_review":
                    state.db.execute("DELETE FROM enrichments WHERE record_id=? AND signature=?", (row["record_id"], config.signature))
    if discover:
        jobs = [("source:" + source["id"] + ":" + digest(source)[:16], "source", source) for source in config.sources]
        if config.search:
            jobs += [("search:" + digest({"service": config.search, "query": query})[:24], "search", query) for query in config.search["queries"]]
        for key, kind, value in jobs:
            since = state.checkpoint(key)
            if since:
                overlap = config.data.get("incremental_overlap_hours", 24)
                if type(overlap) not in {int, float} or overlap < 0:
                    raise PipelineError("invalid_incremental_overlap")
                since = (datetime.fromisoformat(since) - timedelta(hours=overlap)).isoformat()
            try:
                iterator = source_items(value, fetcher, since) if kind == "source" else search_items(config, http, budget, value, since)
                complete = True
                for metadata in iterator:
                    if added >= config.limits["max_items"]:
                        complete = False
                        stop_reason = "budget_items"
                        break
                    added += int(state.add(metadata))
                if complete:
                    # Advance only after discovery and candidate persistence succeed.
                    state.set_checkpoint(key, started)
                else:
                    break
            except BudgetExceeded as error:
                stop_reason = error.code
                break
            except PipelineError as error:
                errors.append({"stage": "discovery", "job": key, "code": error.code, "retryable": error.retryable})
    processed = 0
    for original in state.records():
        if original["duplicate_of"]:
            continue
        existing = state.enriched(original["id"], config.signature)
        if existing and existing["result"]:
            continue
        if original["body"] is None and (original["fetch_attempts"] >= config.limits["max_attempts"] or not original["fetch_retryable"]):
            continue
        if existing and (existing["attempts"] >= config.limits["max_attempts"] or not existing["retryable"]):
            continue
        if processed >= config.limits["max_items"]:
            stop_reason = stop_reason or "budget_items"
            break
        processed += 1
        metadata = json.loads(original["metadata"])
        body = original["body"]
        if body is None:
            try:
                body, metadata = fetcher.body(metadata)
                duplicate = state.fetched(original["id"], body, metadata)
                if duplicate:
                    continue
            except BudgetExceeded as error:
                stop_reason = error.code
                break
            except PipelineError as error:
                state.fetch_failure(original["id"], error)
                continue
        try:
            result = enricher.enrich(metadata, body)
            state.enrichment_result(original["id"], config.signature, result)
        except BudgetExceeded as error:
            stop_reason = error.code
            break
        except PipelineError as error:
            state.enrichment_failure(original["id"], config.signature, error)
    counts = export_records(state, config, workspace / "output")
    status = "paused" if stop_reason else "partial" if errors or counts["failed"] or counts["pending"] else "completed_with_review" if counts["needs_review"] else "completed"
    report = {"project": "Global Knowledge Crawl Pipeline (by GKN)", "version": "0.1.1", "dataset": config.dataset,
              "started_at": started, "finished_at": utc_now(), "status": status, "stop_reason": stop_reason,
              "new_candidates": added, "processed_this_run": processed, "counts": counts, "budget": budget.counts,
              "discovery_errors": errors, "offline": config.offline, "template_signature": config.signature,
              "token_accounting": "Conservative input-byte reservation plus output cap; reported usage is provider supplied, not a billing guarantee."}
    write_json(workspace / "output" / "run-report.json", report)
    return report


def export_only(config, workspace):
    with workspace_lock(workspace):
        state = State(workspace / "state.sqlite", config.dataset)
        try:
            return export_records(state, config, workspace / "output")
        finally:
            state.close()
