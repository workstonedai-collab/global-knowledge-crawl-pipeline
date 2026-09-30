from __future__ import annotations

import ipaddress
import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .common import PipelineError, canonical_url, render


class Redirects(HTTPRedirectHandler):
    def __init__(self, client, allow: bool, guard=None):
        self.client, self.allow, self.guard = client, allow, guard

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not self.allow:
            raise PipelineError("api_redirect_blocked")
        self.client.validate(newurl)
        if self.guard:
            self.guard(newurl)
        self.client.budget.consume("http_requests")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpClient:
    def __init__(self, budget, *, offline=False, allow_private=False, timeout=20, max_bytes=2_000_000):
        self.budget = budget
        self.offline = offline
        self.allow_private = allow_private
        self.timeout = min(max(float(timeout), 1), 120)
        self.max_bytes = min(max(int(max_bytes), 1000), 10_000_000)

    def validate(self, url):
        canonical_url(url)
        if self.allow_private:
            return
        host = urlsplit(url).hostname
        try:
            addresses = socket.getaddrinfo(host, urlsplit(url).port or (443 if url.startswith("https:") else 80))
            if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
                raise PipelineError("private_address_blocked")
        except (socket.gaierror, OSError):
            raise PipelineError("dns_failed", True) from None

    def request(self, url, *, method="GET", payload=None, headers=None, redirects=False, guard=None):
        if self.offline:
            raise PipelineError("offline_network_blocked")
        self.validate(url)
        if method == "GET" and payload:
            parts = urlsplit(url)
            query = "&".join(filter(None, [parts.query, urlencode(payload, doseq=True)]))
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
        self.budget.consume("http_requests")
        request_headers = {"User-Agent": "GlobalKnowledgePipeline/0.1", **(headers or {})}
        body = None
        if method == "POST":
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        try:
            request = Request(url, data=body, method=method, headers=request_headers)
            with build_opener(Redirects(self, redirects, guard)).open(request, timeout=self.timeout) as response:
                raw = response.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    raise PipelineError("response_too_large")
                charset = response.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace"), response.geturl(), response.headers.get_content_type()
        except HTTPError as error:
            raise PipelineError("http_" + str(error.code), error.code in {408, 425, 429} or error.code >= 500) from None
        except (URLError, TimeoutError, OSError):
            raise PipelineError("network_failed", True) from None
        except (ValueError, LookupError):
            raise PipelineError("invalid_http_request") from None

    def json_request(self, service, context):
        headers = dict(service.get("headers", {}))
        env = service.get("credential_env")
        if env:
            credential = os.environ.get(env)
            if not credential:
                raise PipelineError("missing_credential_env")
            headers[service.get("auth_header", "Authorization")] = service.get("auth_prefix", "Bearer ") + credential
        payload = render(service.get("request", {}), context)
        text, _, _ = self.request(service["endpoint"], method=service.get("method", "POST").upper(), payload=payload, headers=headers)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise PipelineError("invalid_api_json", True) from None
