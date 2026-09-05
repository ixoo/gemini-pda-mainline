#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Failure fixtures for input integrity, HTTP errors and bounded downloads."""
import hashlib
import io
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch
import urllib.error

API = runpy.run_path(str(Path(__file__).with_name('audit-inputs.py')))
URL = 'https://raw.githubusercontent.com/example/project/pinned/file'
ENTRY = {'url': URL, 'path': 'file', 'bytes': 3,
         'sha256': hashlib.sha256(b'abc').hexdigest()}


class Response(io.BytesIO):
    status = 200
    url = URL


class Integrity(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(API['verify'](ENTRY, b'abc'), 'abc')

    def test_truncated(self):
        with self.assertRaises(ValueError):
            API['verify'](ENTRY, b'ab')

    def test_same_size_mutation(self):
        with self.assertRaises(ValueError):
            API['verify'](ENTRY, b'abd')

    def test_http_error_is_not_absence_evidence(self):
        with patch('urllib.request.urlopen', side_effect=urllib.error.HTTPError(
                URL, 404, 'missing', {}, None)):
            with self.assertRaises(urllib.error.HTTPError):
                API['fetch'](ENTRY)

    def test_redirect(self):
        response = Response(b'abc')
        response.url = URL + '/other'
        with patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ValueError):
                API['fetch'](ENTRY)

    def test_non_success(self):
        response = Response(b'abc')
        response.status = 206
        with patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ValueError):
                API['fetch'](ENTRY)

    def test_download_bound(self):
        response = Response(b'x' * (API['LIMIT'] + 10))
        with patch.object(response, 'read', wraps=response.read) as read:
            with patch('urllib.request.urlopen', return_value=response):
                with self.assertRaises(ValueError):
                    API['fetch'](ENTRY)
            read.assert_called_once_with(API['LIMIT'] + 1)


if __name__ == '__main__':
    unittest.main()
