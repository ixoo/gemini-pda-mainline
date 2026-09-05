#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Small synthetic fixtures only; never access the pinned Buildbox archive."""
import fcntl
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
MODULE = importlib.util.spec_from_file_location("archive_adoption", HERE / "adopt-upstream-archive.py")
adoption = importlib.util.module_from_spec(MODULE)
sys.modules[MODULE.name] = adoption
MODULE.loader.exec_module(adoption)
DATA = b"synthetic public source archive\n" * 49152


def interrupted_child(spec, phase, connection):
    def event(name):
        if name == phase:
            connection.send(name)
            signal.pause()

    try:
        adoption.adopt(spec, execute=True, event=event)
    except InterruptedError:
        raise SystemExit(130)


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gemini-archive-adoption-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source_dir, self.cache, self.build = [self.root / p for p in ("source", "cache", "build")]
        for path in (self.source_dir, self.cache, self.build):
            path.mkdir(mode=0o700)
        self.source = self.source_dir / "source.tar.gz"
        self.final = self.cache / "archive.tar.gz"
        self.source.write_bytes(DATA)
        self.build_lock, self.acquire_lock = self.build / "build.lock", self.source_dir / ".acquire.lock"
        self.build_lock.touch(mode=0o600)
        self.acquire_lock.touch(mode=0o600)
        self.spec = adoption.Spec(self.source, self.final, self.build_lock, self.acquire_lock,
                                  len(DATA), hashlib.sha256(DATA).hexdigest())
        self.partial = self.cache / (".adopt-" + self.spec.sha256 + ".partial")
        self.receipt = self.cache / (self.final.name + ".adoption.json")
        self.receipt_partial = self.cache / (".adopt-" + self.spec.sha256 + ".receipt.partial")

    def run_adoption(self, **kwargs):
        return adoption.adopt(self.spec, **kwargs)

    def refuse(self, **kwargs):
        with self.assertRaises((ValueError, OSError)):
            self.run_adoption(execute=True, **kwargs)
        self.assertEqual(self.source.read_bytes(), DATA)

    def assert_complete(self):
        self.assertFalse(self.source.exists())
        self.assertEqual(self.final.read_bytes(), DATA)
        self.assertEqual(self.final.stat().st_nlink, 1)
        self.assertTrue(self.receipt.is_file())
        self.assertFalse(self.partial.exists())
        self.assertFalse(self.receipt_partial.exists())

    def test_default_has_no_filesystem_mutation(self):
        before = {str(p): (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns)
                  for p in self.root.rglob("*")}
        result = self.run_adoption()
        after = {str(p): (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns)
                 for p in self.root.rglob("*")}
        self.assertEqual(before, after)
        self.assertFalse(result["execute"])
        self.assertFalse(result["destination_present"])

    def test_migration_receipt_precedes_deletion_and_repeat_reuses(self):
        def event(name):
            if name == "receipt-durable":
                self.assertTrue(self.source.exists())
                self.assertEqual(self.final.read_bytes(), DATA)
                receipt = json.loads(self.receipt.read_text())
                self.assertEqual(receipt["source_identity"], adoption.identity(self.source.stat()))

        result = self.run_adoption(execute=True, event=event)
        self.assertEqual(result["state"], "adopted")
        self.assert_complete()
        inode = self.final.stat().st_ino
        original_receipt = self.receipt.read_bytes()
        self.run_adoption(execute=True)
        self.assertEqual(self.final.stat().st_ino, inode)
        self.assertEqual(self.receipt.read_bytes(), original_receipt)
        self.assert_complete()

    def test_existing_matching_destination_is_reused(self):
        self.final.write_bytes(DATA)
        inode = self.final.stat().st_ino
        self.run_adoption(execute=True)
        self.assertEqual(self.final.stat().st_ino, inode)
        self.assert_complete()

    def test_cross_filesystem_copy_when_linux_shm_is_available(self):
        shared = Path("/dev/shm")
        if (not shared.is_dir() or not os.access(shared, os.W_OK)
                or shared.stat().st_dev == self.source_dir.stat().st_dev):
            self.skipTest("requires a separate writable Linux /dev/shm filesystem")
        with tempfile.TemporaryDirectory(prefix="gemini-adoption-test-", dir=shared) as temporary:
            destination = Path(temporary) / self.final.name
            spec = adoption.Spec(self.source, destination, self.build_lock, self.acquire_lock,
                                 self.spec.size, self.spec.sha256)
            # The production 64 MiB reserve is excessive for this tiny tmpfs
            # fixture. No production CLI can change this module constant.
            with mock.patch.object(adoption, "HEADROOM", 1024):
                adoption.adopt(spec, execute=True)
            self.assertFalse(self.source.exists())
            self.assertEqual(destination.read_bytes(), DATA)
            self.assertEqual(destination.stat().st_nlink, 1)

    def test_existing_mismatch_is_never_replaced(self):
        self.final.write_bytes(b"wrong")
        self.refuse()
        self.assertEqual(self.final.read_bytes(), b"wrong")

    def test_source_digest_and_size_mismatch(self):
        for data in (b"wrong", b"x" * len(DATA)):
            with self.subTest(length=len(data)):
                self.source.write_bytes(data)
                with self.assertRaises(ValueError):
                    self.run_adoption(execute=True)
                self.assertEqual(self.source.read_bytes(), data)
                self.assertFalse(self.final.exists())

    def test_source_mutated_during_copy_is_preserved_and_partial_removed(self):
        def event(name):
            if name == "copy-chunk":
                self.source.write_bytes(b"x" * len(DATA))

        with self.assertRaises(ValueError):
            self.run_adoption(execute=True, event=event)
        self.assertTrue(self.source.exists())
        self.assertFalse(self.partial.exists())
        self.assertFalse(self.final.exists())

    def test_symlink_file_paths_and_parent_refuse(self):
        for path in (self.source, self.final, self.build_lock, self.acquire_lock,
                     self.partial, self.receipt, self.receipt_partial):
            with self.subTest(path=path.name):
                original = path.read_bytes() if path.exists() else None
                if path.exists():
                    path.unlink()
                path.symlink_to(self.root / "absent")
                with self.assertRaises((ValueError, OSError)):
                    self.run_adoption(execute=True)
                path.unlink()
                if original is not None:
                    path.write_bytes(original)
        moved = self.root / "moved-cache"
        self.cache.rename(moved)
        self.cache.symlink_to(moved, target_is_directory=True)
        self.refuse()

    def test_nonregular_source_refuses_without_blocking(self):
        self.source.unlink()
        os.mkfifo(self.source)
        with self.assertRaises(ValueError):
            self.run_adoption(execute=True)
        self.assertFalse(self.final.exists())

    def test_hardlinked_or_other_writable_source_refuses(self):
        extra = self.source_dir / "extra"
        os.link(self.source, extra)
        self.refuse()
        extra.unlink()
        self.source.chmod(0o666)
        self.refuse()

    def test_unsafe_parent_permissions_refuse(self):
        self.cache.chmod(0o777)
        self.refuse()

    def test_missing_lock_is_not_created(self):
        for lock in (self.build_lock, self.acquire_lock):
            lock.unlink()
            self.refuse()
            self.assertFalse(lock.exists())
            lock.touch(mode=0o600)

    def test_busy_locks_refuse_without_waiting(self):
        for lock in (self.build_lock, self.acquire_lock):
            with self.subTest(lock=lock.name), lock.open("rb") as stream:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.refuse()

    def test_build_lock_is_held_before_acquisition_lock(self):
        seen = []
        actual = adoption.fcntl.flock

        def flock(fd, flags):
            seen.append(os.fstat(fd).st_ino)
            actual(fd, flags)

        with mock.patch.object(adoption.fcntl, "flock", side_effect=flock):
            self.run_adoption()
        self.assertEqual(seen, [self.build_lock.stat().st_ino, self.acquire_lock.stat().st_ino])

    def test_no_space_refuses_before_partial(self):
        space = mock.Mock(f_bavail=1, f_frsize=1)
        with mock.patch.object(adoption.os, "fstatvfs", return_value=space):
            self.refuse()
        self.assertFalse(self.partial.exists())

    def test_write_and_sync_failure_preserve_original(self):
        for operation in ("write", "fsync"):
            with self.subTest(operation=operation):
                with mock.patch.object(adoption.os, operation, side_effect=OSError("injected I/O failure")):
                    self.refuse()
                self.assertFalse(self.partial.exists())
                self.assertFalse(self.final.exists())

    def test_stale_partial_inspection_and_recovery(self):
        self.partial.write_bytes(b"incomplete")
        self.partial.chmod(0o600)
        self.assertTrue(self.run_adoption()["stale_partial"])
        self.assertEqual(self.partial.read_bytes(), b"incomplete")
        self.run_adoption(execute=True)
        self.assert_complete()

    def test_unsafe_stale_partial_preserved(self):
        for path, data, mode in ((self.partial, b"x" * (len(DATA) + 1), 0o600),
                                 (self.partial, b"unknown", 0o644),
                                 (self.receipt_partial, b"x" * 16385, 0o600)):
            with self.subTest(path=path.name, mode=mode):
                path.write_bytes(data)
                path.chmod(mode)
                self.refuse()
                self.assertEqual(path.read_bytes(), data)
                path.unlink()

    def test_bad_receipt_preserves_both_archives(self):
        self.final.write_bytes(DATA)
        self.receipt.write_text("{}")
        self.refuse()
        self.assertEqual(self.final.read_bytes(), DATA)

    def test_source_absent_without_receipt_refuses(self):
        self.final.write_bytes(DATA)
        self.source.unlink()
        with self.assertRaises(ValueError):
            self.run_adoption(execute=True)
        self.assertEqual(self.final.read_bytes(), DATA)

    def test_receipt_failure_preserves_source_and_published_copy(self):
        def event(name):
            if name == "receipt-durable":
                self.receipt.write_text("{}")

        self.refuse(event=event)
        self.assertEqual(self.final.read_bytes(), DATA)

    def test_publish_collision_is_not_replaced(self):
        def event(name):
            if name == "copy-chunk":
                self.final.write_bytes(b"concurrent writer")

        self.refuse(event=event)
        self.assertEqual(self.final.read_bytes(), b"concurrent writer")
        self.assertFalse(self.partial.exists())

    def test_destination_mutation_before_source_removal_refuses(self):
        def event(name):
            if name == "receipt-durable":
                self.final.write_bytes(b"x" * len(DATA))

        self.refuse(event=event)

    def test_source_replacement_before_removal_refuses(self):
        def event(name):
            if name == "receipt-durable":
                replacement = self.source_dir / "replacement"
                replacement.write_bytes(DATA)
                replacement.replace(self.source)

        self.refuse(event=event)

    def test_all_signal_interruption_states_recover(self):
        phases = ("copy-chunk", "published-with-partial", "published",
                  "receipt-published-with-partial", "receipt-durable")
        for number in (signal.SIGTERM, signal.SIGKILL):
            for phase in phases:
                with self.subTest(signal=number, phase=phase):
                    self.source.write_bytes(DATA)
                    for path in self.cache.iterdir():
                        path.unlink()
                    context = multiprocessing.get_context("fork")
                    parent, child = context.Pipe()
                    process = context.Process(target=interrupted_child, args=(self.spec, phase, child))
                    process.start()
                    child.close()
                    try:
                        self.assertTrue(parent.poll(5), "child failed to reach phase")
                        self.assertEqual(parent.recv(), phase)
                        os.kill(process.pid, number)
                        process.join(5)
                        self.assertFalse(process.is_alive())
                        self.assertNotEqual(process.exitcode, 0)
                        self.assertEqual(self.source.read_bytes(), DATA)
                        self.run_adoption(execute=True)
                        self.assert_complete()
                    finally:
                        if process.is_alive():
                            process.kill()
                            process.join(5)
                        parent.close()

    def test_cli_cannot_override_paths_or_digest(self):
        for argument in ("--source", "--destination", "--sha256", "--home", "--test-root"):
            result = subprocess.run([sys.executable, str(HERE / "adopt-upstream-archive.py"),
                                     argument, str(self.root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments", result.stderr)
        with mock.patch.dict(os.environ, {"HOME": str(self.root)}):
            spec = adoption.production_spec()
        self.assertNotIn(self.root, spec.destination.parents)
        self.assertEqual(spec.sha256, adoption.SHA256)
        self.assertEqual(spec.size, adoption.SIZE)


if __name__ == "__main__":
    unittest.main()
