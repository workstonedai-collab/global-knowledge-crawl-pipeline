import hashlib
import unittest
from gkp.receipts import text_receipt


class ReceiptTests(unittest.TestCase):
    def test_exact_text_and_private_url_parts(self):
        body = 'Example\n\nUnicode: \u4e2d\u6587'
        receipt = text_receipt('sample', body, {'url': 'https://user:synthetic@example.org/post?token=fixture#part', 'checked_at': '2026-01-01T00:00:00Z'})
        self.assertEqual(receipt['sha256'], hashlib.sha256(body.encode()).hexdigest())
        self.assertEqual(receipt['utf8_bytes'], len(body.encode()))
        self.assertEqual(receipt['source_url'], 'https://example.org/post')
        self.assertNotIn('synthetic', str(receipt))
        self.assertNotIn('fetched_at', receipt)

    def test_missing_body_is_unknown_not_empty(self):
        self.assertIsNone(text_receipt('sample', None, {})['sha256'])
        self.assertIsNotNone(text_receipt('sample', '', {})['sha256'])
