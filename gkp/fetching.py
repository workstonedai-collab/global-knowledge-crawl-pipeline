from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from .common import PipelineError, canonical_url, normalized_date


class HtmlDocument(HTMLParser):
    """Small HTML extractor; optional browser rendering still uses this parser."""

    IGNORE = {"script", "style", "noscript", "nav", "footer", "header", "svg", "template"}
    BLOCK = {"p", "div", "article", "section", "h1", "h2", "h3", "li", "br", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []
        self.title_depth = 0
        self.title_parts = []
        self.parts = []
        self.article_parts = []
        self.article_depth = 0
        self.links = []
        self.link = None
        self.published_at = None

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag in self.IGNORE:
            self.hidden.append(tag)
        if self.hidden:
            return
        if tag == "title":
            self.title_depth += 1
        if tag in {"article", "main"}:
            self.article_depth += 1
        if tag in self.BLOCK:
            self.parts.append("\n")
            if self.article_depth:
                self.article_parts.append("\n")
        if tag == "a" and attr.get("href"):
            self.link = {"href": attr["href"], "parts": []}
        if tag == "meta" and attr.get("property", attr.get("name", "")).lower() in {"article:published_time", "date", "datepublished"}:
            self.published_at = normalized_date(attr.get("content"))
        if tag == "time" and attr.get("datetime") and self.published_at is None:
            self.published_at = normalized_date(attr["datetime"])

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
            return
        if tag == "title":
            self.title_depth = max(0, self.title_depth - 1)
        if tag in {"article", "main"}:
            self.article_depth = max(0, self.article_depth - 1)
        if tag == "a" and self.link:
            self.links.append((self.link["href"], " ".join(self.link["parts"]).strip()))
            self.link = None
        if tag in self.BLOCK:
            self.parts.append("\n")
            self.article_parts.append("\n")

    def handle_data(self, text):
        if self.hidden:
            return
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return
        if self.title_depth:
            self.title_parts.append(text)
        else:
            self.parts.append(text + " ")
            if self.article_depth:
                self.article_parts.append(text + " ")
        if self.link:
            self.link["parts"].append(text)

    @property
    def title(self):
        return " ".join(self.title_parts).strip()

    @property
    def text(self):
        selected = self.article_parts if any(part.strip() for part in self.article_parts) else self.parts
        return re.sub(r"\n\s*\n+", "\n", "".join(selected)).strip()


def parse_html(raw: str) -> HtmlDocument:
    document = HtmlDocument()
    try:
        document.feed(raw)
        document.close()
    except Exception:
        raise PipelineError("invalid_html") from None
    return document


class Fetcher:
    def __init__(self, config, http):
        self.config, self.http = config, http
        self.robot_cache = {}

    def robots(self, url):
        if self.config.fetch.get("respect_robots", True) is False:
            return
        parts = urlsplit(url)
        root = parts.scheme + "://" + parts.netloc
        if root not in self.robot_cache:
            parser = RobotFileParser()
            try:
                text, _, _ = self.http.request(root + "/robots.txt")
                parser.parse(text.splitlines())
            except PipelineError as error:
                if error.code in {"http_404", "http_410"}:
                    parser.parse([])
                    parser.allow_all = True
                else:
                    raise PipelineError("robots_unavailable", error.retryable) from None
            self.robot_cache[root] = parser
        if not self.robot_cache[root].can_fetch("GlobalKnowledgePipeline", url):
            raise PipelineError("robots_disallowed")

    def read(self, url, fixture=None):
        if fixture:
            try:
                path = self.config.resolve(fixture)
                if path.stat().st_size > self.http.max_bytes:
                    raise PipelineError("fixture_too_large")
                return path.read_text(encoding="utf-8"), url, "text/html"
            except (OSError, UnicodeError):
                raise PipelineError("fixture_unreadable") from None
        self.robots(url)
        return self.http.request(url, redirects=True, guard=self.robots)

    def body(self, metadata):
        url = metadata["url"]
        fixtures = self.config.fetch.get("fixtures", {})
        fixture = fixtures.get(url)
        if fixture or self.config.fetch.get("provider", "http") == "http":
            raw, final_url, content_type = self.read(url, fixture)
        else:
            raw, final_url, content_type = self._browser(url)
        if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
            raise PipelineError("unsupported_document_type")
        if content_type == "text/plain":
            text, title, published = raw.strip(), metadata.get("title", ""), None
        else:
            doc = parse_html(raw)
            text, title, published = doc.text, doc.title, doc.published_at
        if len(text) < int(self.config.fetch.get("min_text_chars", 40)):
            raise PipelineError("body_too_short")
        metadata = {**metadata, "title": metadata.get("title") or title,
                    "published_at": metadata.get("published_at") or published,
                    "final_url": canonical_url(final_url)}
        metadata["freshness"] = "dated" if metadata["published_at"] else "unknown"
        return text, metadata

    def _browser(self, url):
        if self.config.offline:
            raise PipelineError("offline_network_blocked")
        self.http.validate(url)
        self.robots(url)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise PipelineError("browser_extra_required") from None
        # Rendering may make many subrequests: gate every network request.
        failures = []
        def route_request(route):
            try:
                target = route.request.url
                if not target.startswith(("http://", "https://")):
                    route.abort()
                    return
                self.http.validate(target)
                if route.request.is_navigation_request():
                    self.robots(target)
                self.http.budget.consume("http_requests")
                if route.request.resource_type in {"image", "font", "media"}:
                    route.abort()
                else:
                    route.continue_()
            except PipelineError as error:
                failures.append(error)
                route.abort()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page(service_workers="block", user_agent="GlobalKnowledgePipeline/0.1")
                    page.route("**/*", route_request)
                    response = page.goto(url, wait_until="domcontentloaded", timeout=self.http.timeout * 1000)
                    if failures:
                        raise failures[0]
                    if response is None or response.status >= 400:
                        raise PipelineError("browser_http_failed", True)
                    raw = page.content()
                    if len(raw.encode("utf-8")) > self.http.max_bytes:
                        raise PipelineError("response_too_large")
                    return raw, page.url, "text/html"
                finally:
                    browser.close()
        except PipelineError:
            raise
        except Exception:
            raise PipelineError("browser_failed", True) from None


def listing_items(raw, base_url, source):
    doc = parse_html(raw)
    seen = set()
    for href, title in doc.links:
        try:
            url = canonical_url(urljoin(base_url, href))
        except PipelineError:
            continue
        if url in seen or url == canonical_url(base_url):
            continue
        if not source.get("allow_external", False) and urlsplit(url).netloc != urlsplit(base_url).netloc:
            continue
        if source.get("include_pattern") and not re.search(source["include_pattern"], url):
            continue
        seen.add(url)
        yield {"url": url, "title": title}
