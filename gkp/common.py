from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class PipelineError(Exception):
    """A safe error code; raw provider responses never become log messages."""

    def __init__(self, code: str, retryable: bool = False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class BudgetExceeded(PipelineError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    data = value if isinstance(value, str) else json_text(value)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def canonical_url(value: str) -> str:
    try:
        parts = urlsplit(value.strip())
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError
        port = parts.port
        host = parts.hostname.lower()
        if ":" in host:
            host = "[" + host + "]"
        if port and not (parts.scheme == "http" and port == 80 or parts.scheme == "https" and port == 443):
            host += ":" + str(port)
        pairs = []
        for key, val in parse_qsl(parts.query, keep_blank_values=True):
            lowered = key.lower().replace("-", "_")
            if lowered in {"key", "api_key", "apikey", "token", "access_token", "password", "secret", "signature"}:
                raise PipelineError("credential_in_url")
            if not lowered.startswith("utm_") and lowered not in {"fbclid", "gclid", "mc_cid", "mc_eid"}:
                pairs.append((key, val))
        return urlunsplit((parts.scheme, host, parts.path or "/", urlencode(sorted(pairs)), ""))
    except (ValueError, AttributeError):
        raise PipelineError("invalid_source_url") from None


def normalized_date(value) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    if dt.tzinfo is None:
        # A date without a zone is not reliable enough for an incremental cutoff.
        return None
    return dt.astimezone(timezone.utc).isoformat()


def get_path(value, path: str, default=None):
    if not path:
        return value
    for component in path.split("."):
        if isinstance(value, dict):
            value = value.get(component, default)
        elif isinstance(value, list) and component.isdigit() and int(component) < len(value):
            value = value[int(component)]
        else:
            return default
    return value


def render(value, context: dict):
    """Whole-value $name placeholders preserve JSON types; no evaluation."""
    if isinstance(value, str) and value.startswith("$"):
        key = value[1:]
        if key not in context:
            raise PipelineError("unknown_request_placeholder")
        return context[key]
    if isinstance(value, list):
        return [render(item, context) for item in value]
    if isinstance(value, dict):
        return {key: render(item, context) for key, item in value.items()}
    return value


def approximate_tokens(text: str) -> int:
    # Conservative UTF-8 byte estimate, not a provider tokenizer or billing claim.
    return len(text.encode("utf-8")) + 32


def safe_cell(value):
    if isinstance(value, (dict, list)):
        value = json_text(value)
    if isinstance(value, str) and re.match(r"^[\s]*[=+@-]", value):
        return "'" + value
    return "" if value is None else value
