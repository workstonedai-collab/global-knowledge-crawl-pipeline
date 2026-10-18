"""Exact retained-text receipts, separate from whitespace-normalized dedupe hashes."""
from urllib.parse import urlsplit, urlunsplit
from .common import digest


def text_receipt(record_id, body, metadata):
    parts = urlsplit(metadata.get('url', ''))
    # This export deliberately omits query strings, fragments and URL credentials.
    source = None
    if parts.scheme in ('http', 'https') and parts.hostname:
        host = '[' + parts.hostname + ']' if ':' in parts.hostname else parts.hostname
        if parts.port:
            host += ':' + str(parts.port)
        source = urlunsplit((parts.scheme, host, parts.path, '', ''))
    return {
        'schema_version': 1, 'record_id': record_id, 'source_url': source,
        'text_kind': 'retained_body', 'hash_rule': 'sha256-exact-utf8-v1',
        'sha256': digest(body) if body is not None else None,
        'utf8_bytes': len(body.encode('utf-8')) if body is not None else None,
        'checked_at': metadata.get('checked_at'),
    }
