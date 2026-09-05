#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Small setup refusal and slow-transfer fixtures; no Debian inputs or guests."""
from concurrent.futures import ThreadPoolExecutor
import http.server
import importlib.util
import multiprocessing
import os
from pathlib import Path
import signal
import tempfile
import threading
import time
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("qemu_setup", Path(__file__).with_name("setup-qemu-debian.py"))
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class SlowServer(http.server.BaseHTTPRequestHandler):
    begun = threading.Event()

    def log_message(self, *_args):
        pass

    def do_GET(self):
        self.begun.set()
        if self.path == "/headers":
            try:
                for byte in b"HTTP/1.1 200 OK\r\nX-Slow: " + b"x" * 1000:
                    self.wfile.write(bytes((byte,)))
                    self.wfile.flush()
                    time.sleep(0.02)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        self.send_response(200)
        self.send_header("Content-Length", "100000")
        self.end_headers()
        self.begun.set()
        try:
            for _ in range(1000):
                self.wfile.write(b"x")
                self.wfile.flush()
                time.sleep(0.02)
        except (BrokenPipeError, ConnectionResetError):
            pass


def interrupted_fetch(package, directory):
    cancellation = threading.Event()
    def interrupted(_number, _frame):
        raise InterruptedError("synthetic SIGTERM")
    signal.signal(signal.SIGTERM, interrupted)
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        pool.submit(setup.fetch, package, Path(directory), cancellation, protocols="=http").result()
    except InterruptedError:
        pass
    finally:
        cancellation.set()
        pool.shutdown(wait=True, cancel_futures=True)


class SetupTests(unittest.TestCase):
    def test_link_traversal_is_rejected_before_normalization(self):
        inventory = {"a": {"kind": "directory"}, "a/link": {"kind": "link"},
                     "a/file": {"kind": "file"}, "ok": {"kind": "file"}}
        for target in ("/outside", "../../outside", "a/link/../ok", "a/file/../ok"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                setup.link_destination("output", target, False, inventory)
        self.assertEqual(setup.link_destination("output", "a/../ok", False, inventory), "ok")

    def test_unknown_and_unsupported_dependencies_refuse(self):
        for relation in ("missing", "known [arm64]", "known <!stage1>"):
            with self.assertRaises(ValueError):
                setup.check_dependencies(relation, {"known": "1"})
        setup.check_dependencies("missing | known:any", {"known": "1"})

    def test_foreign_architecture_does_not_satisfy_native_dependency(self):
        output = "library\tii \t1\tamd64\nlibrary\tii \t9\tarm64\ndata\tii \t1\tall\n"
        with mock.patch.object(setup, "run", return_value=output):
            self.assertEqual(setup.installed_versions(), {"library": "1", "data": "1"})

    def test_slow_continuous_transfer_deadline_and_sigterm(self):
        with mock.patch("socket.getfqdn", return_value="localhost"):
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SlowServer)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            package = {"package": "synthetic", "url": "http://127.0.0.1:%d/" % server.server_port,
                       "bytes": 100000, "sha256": "0" * 64}
            with tempfile.TemporaryDirectory(prefix="gemini-qemu-setup-test-") as directory:
                started = time.monotonic()
                with mock.patch.object(setup, "TRANSFER_SECONDS", 0.15), self.assertRaises((InterruptedError, ValueError)):
                    setup.fetch(package, Path(directory), threading.Event(), protocols="=http")
                self.assertLess(time.monotonic() - started, 1)
                Path(directory, "synthetic.partial").unlink()
                SlowServer.begun.clear()
                package["url"] += "headers"
                process = multiprocessing.get_context("spawn").Process(
                    target=interrupted_fetch, args=(package, directory))
                process.start()
                try:
                    self.assertTrue(SlowServer.begun.wait(3))
                    os.kill(process.pid, signal.SIGTERM)
                    process.join(2)
                    self.assertFalse(process.is_alive(), "worker ignored cancellation")
                    self.assertEqual(process.exitcode, 0)
                    self.assertFalse(Path(directory, "synthetic").exists())
                finally:
                    if process.is_alive():
                        process.kill()
                        process.join(2)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
