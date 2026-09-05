#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Synthetic commands and fake observations; no production transport input."""

import contextlib
import copy
import io
import json
import struct
import unittest
from unittest import mock

import wifi_init_session as session_model


def command(sequence=19, address=0x10203040):
    return struct.pack("<HHBBBBIII", 20, 0x8000, 1, 0xA0, 0, sequence,
                       address, 16, 0x80000000)


def response(sequence=19, status=0, diagnostics=bytes(16)):
    return struct.pack("<HHBB", 28, 0xE000, 1, sequence) + bytes(2) + bytes((status,)) + bytes(3) + diagnostics


class FakeClock:
    def __init__(self, tick=100):
        self.tick = tick

    def advance(self, ticks):
        self.tick += ticks


class FakeOwner:
    def __init__(self, epoch=0x1020304050607080):
        self.epoch = epoch
        self.ready = True

    def observation(self, clock):
        return {"now_tick": clock.tick, "owner_epoch": self.epoch,
                "owner_ready": self.ready}


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.owner = FakeOwner()
        self.session = session_model.InitSession(self.owner.epoch, 10)

    def context(self, **changes):
        context = self.owner.observation(self.clock)
        context.update(changes)
        return context

    def begin(self, sequence=19, packet=None, **context):
        return self.session.begin(command(sequence) if packet is None else packet,
                                  expected_sequence=sequence, **self.context(**context))

    def receive(self, packet=None, **context):
        return self.session.receive(response() if packet is None else packet,
                                    **self.context(**context))

    def poll(self, **context):
        return self.session.poll(**self.context(**context))

    def state(self):
        # Include the private clock floor and sequence set in refusal checks.
        return copy.deepcopy({name: getattr(self.session, name)
                              for name in self.session.__slots__})

    def unchanged_refusal(self, reason, operation):
        before = self.state()
        with self.assertRaisesRegex(session_model.Refusal, "^" + reason + "$"):
            operation()
        self.assertEqual(self.state(), before)

    def failed(self, snapshot, reason, started=1):
        self.assertEqual(snapshot["state"], "failed")
        self.assertEqual(snapshot["outcome"], reason)
        self.assertFalse(snapshot["command_pending"])
        self.assertEqual(snapshot["commands_started"], started)
        self.assertTrue(snapshot["recovery_required"])

    def test_success_serializes_distinct_commands_without_retaining_packets(self):
        self.assertEqual(self.begin()["state"], "pending")
        self.clock.advance(9)
        complete = self.receive()
        self.assertEqual(complete["state"], "idle")
        self.assertEqual(complete["outcome"], "source_contract_match")
        self.assertEqual(complete["commands_completed"], 1)
        self.begin(20)
        self.assertEqual(self.receive(response(20))["commands_completed"], 2)
        self.assertFalse(any(type(value) is bytes for value in self.state().values()))

    def test_busy_refusal_preserves_transaction_and_clock_floor(self):
        self.begin()
        self.clock.advance(8)
        self.unchanged_refusal("command_already_pending", lambda: self.begin(20))
        self.clock.tick = 101
        self.assertEqual(self.receive()["commands_completed"], 1)

    def test_equal_ticks_are_monotonic_and_accepted(self):
        self.begin()
        self.poll()
        self.assertEqual(self.receive()["state"], "idle")

    def test_poll_preserves_original_deadline(self):
        self.begin()
        for tick in (101, 105, 109):
            self.clock.tick = tick
            self.assertEqual(self.poll()["state"], "pending")
        self.clock.tick = 110
        self.failed(self.poll(), "timeout")

    def test_receive_at_or_after_exact_deadline_times_out(self):
        for tick in (110, 111, session_model.UINT64_MAX):
            with self.subTest(tick=tick):
                self.setUp()
                self.begin()
                self.clock.tick = tick
                self.failed(self.receive(), "timeout")

    def test_expiry_is_observed_before_busy_or_reply_decode(self):
        for operation in (lambda: self.begin(20, packet=b"bad"),
                          lambda: self.receive(b"bad")):
            self.setUp()
            self.begin()
            self.clock.advance(10)
            self.failed(operation(), "timeout")

    def test_late_ack_cannot_rearm_a_timed_out_session(self):
        self.begin()
        self.clock.advance(10)
        self.poll()
        self.unchanged_refusal("session_not_active", self.receive)
        self.unchanged_refusal("session_not_active", lambda: self.begin(20))

    def test_owner_loss_and_generation_change_poison_idle_and_pending(self):
        for pending in (False, True):
            for context, reason in (({"owner_ready": False}, "owner_not_ready"),
                                    ({"owner_epoch": self.owner.epoch + 1}, "owner_epoch_mismatch")):
                with self.subTest(pending=pending, reason=reason):
                    self.setUp()
                    if pending:
                        self.begin()
                    self.failed(self.poll(**context), reason, int(pending))

    def test_owner_failure_precedes_busy_and_unsolicited_refusal(self):
        self.begin()
        self.failed(self.begin(20, owner_ready=False), "owner_not_ready")
        self.setUp()
        self.failed(self.receive(owner_epoch=0), "owner_epoch_mismatch", 0)

    def test_changed_owner_cannot_attribute_an_otherwise_matching_ack(self):
        self.begin()
        self.owner.epoch += 1
        self.failed(self.receive(), "owner_epoch_mismatch")

    def test_clock_regression_poisoned_after_begin_poll_or_success(self):
        for setup in (self.begin, self.poll, lambda: (self.begin(), self.receive())):
            self.setUp()
            setup()
            started = self.session.snapshot()["commands_started"]
            self.clock.tick -= 1
            self.failed(self.poll(), "clock_regression", started)

    def test_clock_regression_precedes_busy_and_unsolicited_refusal(self):
        self.begin()
        self.failed(self.begin(20, now_tick=99), "clock_regression")
        self.setUp()
        self.poll()
        self.failed(self.receive(now_tick=99), "clock_regression", 0)

    def test_duplicate_idle_ack_is_refused_without_mutation(self):
        self.begin()
        self.receive()
        self.clock.advance(5)
        self.unchanged_refusal("unsolicited_response", self.receive)

    def test_old_ack_during_next_command_terminally_fails(self):
        self.begin()
        self.receive()
        self.begin(20)
        self.failed(self.receive(), "protocol_failure", 2)

    def test_every_malformed_response_length_terminally_fails(self):
        for packet in [response()[:size] for size in range(28)] + [response() + b"x"]:
            with self.subTest(size=len(packet)):
                self.setUp()
                self.begin()
                self.failed(self.receive(packet), "protocol_failure")

    def test_wrong_sequence_and_malformed_headers_fail_the_session(self):
        packets = [response(20)]
        for offset in (0, 3, 4):
            packet = bytearray(response())
            packet[offset] ^= 1
            packets.append(bytes(packet))
        for packet in packets:
            self.setUp()
            self.begin()
            self.failed(self.receive(packet), "protocol_failure")

    def test_all_nonzero_statuses_are_firmware_rejection_not_protocol_error(self):
        for status in range(1, 256):
            with self.subTest(status=status):
                self.setUp()
                self.begin()
                self.failed(self.receive(response(status=status)), "firmware_rejected")

    def test_advisory_reserved_and_diagnostic_fields_do_not_gate_or_escape(self):
        packet = bytearray(response(diagnostics=b"PRIVATE-DETAILS!"))
        packet[6:8], packet[9:12] = b"\xff\xff", b"\xff\xff\xff"
        self.begin()
        snapshot = self.receive(bytes(packet))
        self.assertEqual(snapshot["state"], "idle")
        self.assertNotIn("PRIVATE", json.dumps(snapshot))

    def test_each_sequence_including_zero_is_used_at_most_once_without_wrap(self):
        for sequence in range(256):
            self.begin(sequence)
            snapshot = self.receive(response(sequence))
            self.assertEqual(snapshot["commands_completed"], sequence + 1)
        for sequence in range(256):
            self.unchanged_refusal("sequence_already_used", lambda: self.begin(sequence))
        self.assertEqual(self.session.snapshot()["commands_started"], 256)

    def test_malformed_command_does_not_consume_sequence_or_clock_floor(self):
        self.poll()
        for packet in [command()[:size] for size in range(20)] + [command() + b"x"]:
            self.unchanged_refusal("logical_record_length_policy",
                                   lambda: self.begin(packet=packet, now_tick=109))
        self.unchanged_refusal("command_sequence_mismatch",
                               lambda: self.begin(packet=command(20), now_tick=109))
        self.assertEqual(self.begin()["commands_started"], 1)

    def test_deadline_overflow_refuses_without_mutation_then_valid_begin_works(self):
        self.unchanged_refusal("deadline_overflow",
                               lambda: self.begin(now_tick=session_model.UINT64_MAX - 9))
        self.assertEqual(self.begin()["state"], "pending")

    def test_deadline_at_uint64_max_is_valid_and_exclusive(self):
        self.clock.tick = session_model.UINT64_MAX - 10
        self.begin()
        self.clock.advance(9)
        self.assertEqual(self.poll()["state"], "pending")
        self.clock.advance(1)
        self.failed(self.poll(), "timeout")

    def test_constructor_uint64_boundaries_and_positive_timeout(self):
        for epoch in (0, session_model.UINT64_MAX):
            for timeout in (1, session_model.UINT64_MAX):
                session_model.InitSession(epoch, timeout)
        for invalid in (-1, 1 << 64, True, False, 1.0, None, "private"):
            with self.assertRaisesRegex(session_model.Refusal, "^invalid_owner_epoch$"):
                session_model.InitSession(invalid, 1)
            with self.assertRaisesRegex(session_model.Refusal, "^invalid_timeout_ticks$"):
                session_model.InitSession(0, invalid)
        with self.assertRaisesRegex(session_model.Refusal, "^invalid_timeout_ticks$"):
            session_model.InitSession(0, 0)

    def test_invalid_context_never_mutates_even_with_expiry_or_owner_loss(self):
        self.begin()
        operations = (self.begin, self.receive, self.poll)
        for key, reason, invalids in (
            ("now_tick", "invalid_now_tick", (-1, 1 << 64, True, None, "private", 1.0)),
            ("owner_epoch", "invalid_owner_epoch", (-1, 1 << 64, True, None, "private", 1.0)),
            ("owner_ready", "invalid_owner_ready", (0, 1, None, "private", 1.0)),
        ):
            for invalid in invalids:
                for operation in operations:
                    context = {"now_tick": 110, "owner_ready": False, key: invalid}
                    self.unchanged_refusal(reason, lambda: operation(**context))

    def test_invalid_packet_types_never_mutate_even_with_unsafe_context(self):
        class ByteSubclass(bytes):
            pass

        self.begin()
        for packet in (None, "private", 20, bytearray(command()), memoryview(command()), ByteSubclass(command())):
            self.unchanged_refusal("immutable_bytes_required", lambda: self.session.begin(
                packet, expected_sequence=19, **self.context(owner_ready=False)))
            self.unchanged_refusal("immutable_bytes_required", lambda: self.session.receive(
                packet, **self.context(now_tick=110)))

    def test_invalid_sequence_never_mutates_even_with_expired_transaction(self):
        self.begin()
        for sequence in (-1, 256, True, False, 1.0, None, "private"):
            self.unchanged_refusal("invalid_expected_sequence",
                                   lambda: self.session.begin(command(), expected_sequence=sequence,
                                                              **self.context(now_tick=110)))

    def test_transport_error_terminally_fails_idle_or_pending(self):
        for pending in (False, True):
            self.setUp()
            if pending:
                self.begin()
            self.failed(self.session.transport_error(), "transport_error", int(pending))
            self.unchanged_refusal("session_not_active", self.session.transport_error)

    def test_close_is_idempotent_and_preserves_failure_or_abandonment(self):
        for expected, recovery in (
            ("closed", False),
            ("closed_with_pending_command", True),
            ("transport_error", True),
        ):
            self.setUp()
            # Resolve methods on this iteration's object, not a prior session.
            if expected == "closed_with_pending_command":
                self.begin()
            elif expected == "transport_error":
                self.session.transport_error()
            closed = self.session.close()
            self.assertEqual(closed["state"], "closed")
            self.assertEqual(closed["outcome"], expected)
            self.assertEqual(closed["recovery_required"], recovery)
            self.assertEqual(self.session.close(), closed)
            for operation in (self.begin, self.receive, self.poll, self.session.transport_error):
                self.unchanged_refusal("session_not_active", operation)

    def test_failed_session_cannot_resume_after_corrected_owner_or_clock(self):
        self.begin()
        self.poll(owner_ready=False)
        for operation in (self.begin, self.receive, self.poll):
            self.unchanged_refusal("session_not_active", operation)
        self.assertTrue(self.session.close()["recovery_required"])

    def test_snapshot_is_detached_and_never_authorizes_replacement_or_hardware(self):
        snapshots = [self.session.snapshot(), self.begin(), self.receive(), self.session.close()]
        expected = {"state", "outcome", "command_pending", "commands_started", "commands_completed",
                    "recovery_required", "owner_evidence", "hardware_readiness", "transport_quiescence",
                    "runtime_protocol_match", "new_session_authorized", "file_access", "hardware_access",
                    "load_authorized", "transmit_authorized"}
        for snapshot in snapshots:
            self.assertEqual(set(snapshot), expected)
            for key in ("new_session_authorized", "file_access", "hardware_access",
                        "load_authorized", "transmit_authorized"):
                self.assertFalse(snapshot[key])
            self.assertEqual(snapshot["hardware_readiness"], "unproven")
            self.assertEqual(snapshot["transport_quiescence"], "unproven")
            self.assertNotIn(str(self.owner.epoch), json.dumps(snapshot))
            self.assertNotIn(str(0x10203040), json.dumps(snapshot))
            snapshot["state"] = "pending"
        self.assertEqual(self.session.snapshot()["state"], "closed")

    def test_fresh_epoch_is_consistency_only_and_cannot_detect_relabelled_reply(self):
        stale_reply = response()
        self.owner.epoch += 1
        self.session = session_model.InitSession(self.owner.epoch, 10)
        self.begin()
        snapshot = self.receive(stale_reply)
        self.assertEqual(snapshot["outcome"], "source_contract_match")
        self.assertEqual(snapshot["owner_evidence"], "caller_supplied_consistency_only")
        self.assertEqual(snapshot["runtime_protocol_match"], "unproven")
        self.assertFalse(snapshot["load_authorized"])

    def test_no_file_output_or_clock_access_and_cli_contract_only(self):
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch("builtins.open", side_effect=AssertionError("file access")), \
                mock.patch("time.monotonic", side_effect=AssertionError("clock access")), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.begin()
            self.poll()
            self.receive()
            self.session.close()
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(errors.getvalue(), "")
        for arguments, code in (([], 0), (["--inspect", "private-path\nprivate-data"], 2)):
            output = io.StringIO()
            with mock.patch("builtins.open", side_effect=AssertionError("file access")), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(session_model.main(arguments), code)
            self.assertNotIn("private", output.getvalue())
            decoded = json.loads(output.getvalue())
            self.assertEqual(decoded["status"], "contract_only" if code == 0 else "refused")


if __name__ == "__main__":
    unittest.main()
