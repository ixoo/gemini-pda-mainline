#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic stream/persistence checks, including a real local pseudo-terminal."""
import importlib.util
import io
import json
import os
from pathlib import Path
import pty
import stat
import tempfile
import threading
import tty
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'export', Path(__file__).with_name('capture-export.py'))
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)
BOOT = '00000000-0000-4000-8000-000000000001'
PREVIOUS = '00000000-0000-4000-8000-000000000002'
SESSION = 'ab' * 32
SNAPSHOT = bytes(range(256)) * 256


class Fragmented(io.BytesIO):
    def read(self, size=-1):
        return super().read(min(size, 17))

    def write(self, data):
        return super().write(data[:19])


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'export'
        frame = Fragmented()
        export.send_snapshot(frame, SNAPSHOT, BOOT, SESSION)
        self.frame = frame.getvalue()

    def receive(self, frame=None, **kwargs):
        return export.receive_snapshot(
            Fragmented(self.frame if frame is None else frame), self.output,
            kwargs.get('boot', PREVIOUS), kwargs.get('session', SESSION))

    def test_fragmented_roundtrip_and_private_files(self):
        result = self.receive()
        self.assertEqual((self.output / 'snapshot.raw').read_bytes(), SNAPSHOT)
        self.assertEqual(json.loads((self.output / 'receipt.json').read_text()), result)
        self.assertFalse(result['clearing_authorized'])
        for path, mode in ((self.output, 0o700), (self.output / 'snapshot.raw', 0o600),
                           (self.output / 'receipt.json', 0o600)):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)

    def test_identity_corruption_and_truncation_refuse_before_save(self):
        cases = [self.frame[:cut] for cut in (0, 1, export.HEADER.size - 1,
                                             export.HEADER.size, len(self.frame) - 1)]
        for offset in (0, 20, 52, 84, 88, len(self.frame) - 1):
            bad = bytearray(self.frame)
            bad[offset] ^= 1
            cases.append(bytes(bad))
        for frame in cases:
            with self.subTest(size=len(frame)), self.assertRaises(ValueError):
                self.receive(frame)
            self.assertFalse(self.output.exists())
        with self.assertRaises(ValueError):
            self.receive(boot=BOOT)
        with self.assertRaises(ValueError):
            self.receive(session='cd' * 32)

    def test_existing_output_and_symlink_preserved(self):
        self.output.mkdir()
        marker = self.output / 'unique-evidence'
        marker.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            self.receive()
        self.assertEqual(marker.read_bytes(), b'keep')
        link = self.root / 'link'
        link.symlink_to(self.output, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            export.receive_snapshot(io.BytesIO(self.frame), link, PREVIOUS, SESSION)
        self.assertEqual(marker.read_bytes(), b'keep')

    def test_public_parent_refused(self):
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private'):
            self.receive()
        self.assertFalse(self.output.exists())

    def test_destination_preflight_precedes_serial_open(self):
        self.output.mkdir()
        arguments = ['capture-export.py', '--serial', '/not-a-terminal',
                     '--previous-boot-id', PREVIOUS, '--session-sha256', SESSION, str(self.output)]
        with patch('sys.argv', arguments), patch.object(export.tty, 'setraw') as raw:
            with self.assertRaisesRegex(FileExistsError, 'snapshot output'):
                export.main()
            raw.assert_not_called()
        link = self.root / 'broken-link'
        link.symlink_to(self.root / 'absent')
        with self.assertRaises(FileExistsError):
            export.check_destination(link)

    def test_failed_sync_keeps_raw_and_reports_failure(self):
        with patch.object(export.os, 'fsync', side_effect=OSError('injected sync failure')):
            with self.assertRaises(OSError):
                self.receive()
        self.assertEqual((self.output / 'snapshot.raw').read_bytes(), SNAPSHOT)
        self.assertFalse((self.output / 'receipt.json').exists())
        with self.assertRaises(FileExistsError):
            self.receive()

    def test_sender_rejects_wrong_size_and_mutable_bytes(self):
        for snapshot in (SNAPSHOT[:-1], SNAPSHOT + b'x', bytearray(SNAPSHOT)):
            stream = io.BytesIO()
            with self.assertRaises(ValueError):
                export.send_snapshot(stream, snapshot, BOOT, SESSION)
            self.assertEqual(stream.getvalue(), b'')

    def test_request_rejects_same_boot_wrong_session_and_short_input(self):
        stream = io.BytesIO()
        export.request_snapshot(stream, PREVIOUS, SESSION)
        frame = stream.getvalue()
        export.await_request(Fragmented(frame), BOOT, SESSION)
        for bad in (frame[:-1], b'BAD!' + frame[4:]):
            with self.assertRaises(ValueError):
                export.await_request(Fragmented(bad), BOOT, SESSION)
        with self.assertRaises(ValueError):
            export.await_request(Fragmented(frame), PREVIOUS, SESSION)
        with self.assertRaises(ValueError):
            export.await_request(Fragmented(frame), BOOT, 'cd' * 32)

    def test_nonblocking_stream_deadline_and_disconnect(self):
        reader, writer = os.pipe()
        self.addCleanup(os.close, reader)
        os.set_blocking(reader, False)
        try:
            with self.assertRaises(TimeoutError):
                export.SerialStream(reader, 0.01).read(1)
        finally:
            os.close(writer)
        with self.assertRaises(ValueError):
            export.read_exact(export.SerialStream(reader, 1), 1)

    def test_real_pseudoterminal_transfer_without_ack(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        tty.setraw(slave)
        os.set_blocking(master, False)
        os.set_blocking(slave, False)
        errors = []

        def receive():
            try:
                stream = export.SerialStream(master, 2)
                export.request_snapshot(stream, PREVIOUS, SESSION)
                export.receive_snapshot(stream, self.output, PREVIOUS, SESSION)
            except Exception as error:
                errors.append(error)

        receiver = threading.Thread(target=receive, daemon=True)
        receiver.start()
        stream = export.SerialStream(slave, 2)
        export.await_request(stream, BOOT, SESSION)
        export.send_snapshot(stream, SNAPSHOT, BOOT, SESSION)
        receiver.join(timeout=5)
        self.assertFalse(receiver.is_alive(), 'receiver stalled')
        self.assertEqual(errors, [])
        self.assertEqual((self.output / 'snapshot.raw').read_bytes(), SNAPSHOT)
        os.set_blocking(slave, False)
        with self.assertRaises(BlockingIOError):
            os.read(slave, 1)


if __name__ == '__main__':
    unittest.main()
