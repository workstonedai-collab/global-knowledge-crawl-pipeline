from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

from .common import PipelineError, get_path, normalized_date
from .config import read_document
from .fetching import listing_items, parse_html


def rss_items(raw: str):
    if "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        raise PipelineError("feed_dtd_blocked")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise PipelineError("invalid_feed") from None
    for entry in root.iter():
        if entry.tag.split("}")[-1] not in {"item", "entry"}:
            continue
        row = {}
        for child in entry:
            name = child.tag.split("}")[-1]
            text = "".join(child.itertext()).strip()
            if name == "title":
                row["title"] = text
            elif name == "link":
                if child.get("href") and child.get("rel", "alternate") == "alternate":
                    row["url"] = child.get("href")
                elif text:
                    row["url"] = text
            elif name in {"pubDate", "published", "date"} or name == "updated" and not row.get("published_at"):
                row["published_at"] = normalized_date(text)
            elif name in {"description", "summary", "content"}:
                row["snippet"] = parse_html(text).text if "<" in text else text
        if row.get("url"):
            yield row


def source_items(source, fetcher, since):
    if source["type"] == "url":
        items = [{"url": source["url"], "title": source.get("title", "")}]
    else:
        raw, final_url, _ = fetcher.read(source["url"], source.get("fixture"))
        items = rss_items(raw) if source["type"] == "rss" else listing_items(raw, final_url, source)
    keywords = [word.casefold() for word in source.get("keywords", [])]
    for item in items:
        item["url"] = urljoin(source["url"], item["url"])
        published = normalized_date(item.get("published_at"))
        if since and published and published < since:
            continue
        text = (item.get("title", "") + " " + item.get("snippet", "")).casefold()
        if keywords and not any(word in text for word in keywords):
            continue
        yield {**item, "published_at": published, "source_id": source["id"],
               "source_name": source.get("name", source["id"]), "query": None,
               "discovery_provider": source["type"], "freshness": "dated" if published else "unknown"}


def search_items(config, http, budget, query, since):
    service = config.search
    budget.consume("search_requests")
    if service["provider"] == "fixture":
        document = read_document(config.resolve(service["fixture"]))
        items = document.get(query, [])
    else:
        context = {"query": query, "since": since, "limit": config.limits["max_items"]}
        document = http.json_request(service, context)
        items = get_path(document, service.get("response", {}).get("items_path", "results"))
    if not isinstance(items, list):
        raise PipelineError("invalid_search_results", True)
    mapping = service.get("response", {}).get("fields", {"url": "url", "title": "title", "snippet": "snippet", "published_at": "published_at"})
    for item in items:
        if not isinstance(item, dict):
            raise PipelineError("invalid_search_item", True)
        fields = {name: get_path(item, path) for name, path in mapping.items()}
        if not isinstance(fields.get("url"), str):
            raise PipelineError("search_result_missing_url", True)
        for name in ("title", "snippet"):
            fields[name] = fields.get(name) or ""
            if not isinstance(fields[name], str):
                raise PipelineError("invalid_search_text", True)
        published = normalized_date(fields.get("published_at"))
        if since and published and published < since:
            continue
        yield {**fields, "published_at": published, "source_id": "search", "source_name": service.get("name", "keyword search"),
               "query": query, "discovery_provider": service["provider"], "freshness": "dated" if published else "unknown"}
