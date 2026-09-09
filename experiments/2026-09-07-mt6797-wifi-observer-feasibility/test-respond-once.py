#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""No-device tests of one command, metadata ordering and failure behavior."""

import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("responder", Path(__file__).with_name("respond-once.py"))
responder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(responder)


class ResponseTests(unittest.TestCase):
    def setUp(self):
        self.clock = 100
        self.records = [
            {"sequence": 1, "name": "ROMv3_patch_1_1_hdr.bin", "address_bytes_hex": "00000af0"},
            {"sequence": 2, "name": "ROMv3_patch_1_0_hdr.bin", "address_bytes_hex": "00000900"},
        ]
        self.ioctls = []
        self.fail_request = None
        self.expire_on_info = False
        for name, target, kwargs in (
            ("now", "time.monotonic_ns", {"side_effect": lambda: self.clock}),
            ("poll", "select.poll", {}),
            ("read", "os.read", {"return_value": b"srh_patch"}),
            ("write", "os.write", {"return_value": 2}),
            ("ioctl", "fcntl.ioctl", {"side_effect": self.ioctl_call}),
        ):
            module, attribute = target.split(".")
            mocker = patch.object(getattr(responder, module), attribute, **kwargs)
            setattr(self, name, mocker.start())
            self.addCleanup(mocker.stop)
        self.poll.return_value.poll.return_value = [(3, responder.select.POLLIN)]

    def ioctl_call(self, fd, request, value, *flags):
        self.assertEqual(fd, 3)
        self.ioctls.append((request, value, flags))
        if request == self.fail_request:
            raise OSError("injected publication failure")
        if request == responder.GET_CHIP_INFO:
            return 0x0279 if value == 0 else 0
        if request == responder.SET_PATCH_INFO and self.expire_on_info:
            self.clock = 1000
        return 0

    def serve(self):
        return responder.serve(3, 1000, self.records, 0x0279, 0)

    def test_ordered_publication_and_exact_reply(self):
        self.assertEqual(self.serve()["kernel_acceptance"], "requires capture")
        self.read.assert_called_once_with(3, 256)
        self.write.assert_called_once_with(3, b"ok")
        self.assertEqual([x[0] for x in self.ioctls], [responder.GET_CHIP_INFO] * 2 +
                         [responder.SET_PATCH_NUM] + [responder.SET_PATCH_INFO] * 2)
        self.assertEqual(self.ioctls[2][1], 2)
        for entry, sequence, address, name in (
            (self.ioctls[3], 1, b"\x00\x00\x0a\xf0", b"ROMv3_patch_1_1_hdr.bin"),
            (self.ioctls[4], 2, b"\x00\x00\x09\x00", b"ROMv3_patch_1_0_hdr.bin"),
        ):
            self.assertEqual(len(entry[1]), 264)
            self.assertEqual(struct.unpack("<I4s256s", entry[1]),
                             (sequence, address, name.ljust(256, b"\0")))
            self.assertEqual(entry[2], (True,))

    def test_unknown_command(self):
        self.read.return_value = b"srh_patch\n"
        with self.assertRaises(RuntimeError): self.serve()
        self.ioctl.assert_not_called()
        self.write.assert_not_called()

    def test_expired_before_poll(self):
        self.clock = 1000
        with self.assertRaises(TimeoutError): self.serve()
        self.poll.return_value.poll.assert_not_called()
        self.read.assert_not_called()

    def test_timeout_or_hangup(self):
        for events in ([], [(3, responder.select.POLLIN | responder.select.POLLHUP)]):
            self.poll.return_value.poll.return_value = events
            with self.assertRaises(RuntimeError): self.serve()
        self.read.assert_not_called()
        self.write.assert_not_called()

    def test_identity_refusal(self):
        for wrong in (0x1234, -1):
            self.ioctl.side_effect = None
            self.ioctl.return_value = wrong
            with self.assertRaises(RuntimeError): self.serve()
        self.write.assert_not_called()

    def test_publication_errors(self):
        for request in (responder.SET_PATCH_NUM, responder.SET_PATCH_INFO):
            self.fail_request = request
            with self.assertRaises(OSError): self.serve()
        self.write.assert_not_called()

    def test_version_mismatch(self):
        self.ioctl.side_effect = [0x0279, 0x0100]
        with self.assertRaises(RuntimeError): self.serve()
        self.assertEqual(self.ioctl.call_count, 2)
        self.write.assert_not_called()

    def test_nonzero_publication_result(self):
        self.ioctl.side_effect = [0x0279, 0, 1]
        with self.assertRaises(RuntimeError): self.serve()
        self.write.assert_not_called()

    def test_second_record_failure(self):
        self.ioctl.side_effect = [0x0279, 0, 0, 0, OSError("second record failed")]
        with self.assertRaises(OSError): self.serve()
        self.assertEqual(self.ioctl.call_count, 5)
        self.write.assert_not_called()

    def test_expiry_during_publication(self):
        self.expire_on_info = True
        with self.assertRaises(TimeoutError): self.serve()
        self.assertEqual(sum(x[0] == responder.SET_PATCH_INFO for x in self.ioctls), 1)
        self.write.assert_not_called()

    def test_short_reply_is_not_retried(self):
        self.write.return_value = 1
        with self.assertRaises(RuntimeError): self.serve()
        self.write.assert_called_once_with(3, b"ok")

    def test_expiry_during_reply_cannot_claim_acceptance(self):
        def delayed_reply(*args):
            self.clock = 1000
            return 2
        self.write.side_effect = delayed_reply
        with self.assertRaises(TimeoutError): self.serve()
        self.write.assert_called_once_with(3, b"ok")


if __name__ == "__main__":
    unittest.main()
