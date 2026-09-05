# SPDX-License-Identifier: GPL-2.0-only
"""Only synthetic RAM and scripted callbacks; no firmware or hardware inputs."""

from dataclasses import FrozenInstanceError
import struct
import unittest
import zlib

from wifi_whole_image import (EmiLease, EmiOwner, OrdinaryTransport, Phase,
                              Protection, Refusal, Reservation, SecureFailure,
                              Session, WholeImage, check_status)

WINDOW = 512 * 1024


def fixture(count=4):
    image = bytearray(b"MTKE" + bytes(20))
    struct.pack_into("<I", image, 8, count)
    for index in range(count):
        destination = 0x1000 + index * 16 if index < 2 else 0xF0000000 + index * 16
        image += struct.pack("<IBBHII", 24 + 16 * count + index * 4,
                             7 if index == 0 else 0, index == 0, 0, 4, destination)
    image += b"".join(bytes([index + 1]) * 4 for index in range(count))
    struct.pack_into("<I", image, 4, zlib.crc32(image[8:]))
    return image


class MockLease(EmiLease):
    def __init__(self, session, events, statuses=(), fail=None):
        super().__init__(Reservation(0x80000000, 2 * WINDOW), session,
                         Protection(0, 1))  # Synthetic policies, no domain claim.
        self.events = events
        self.statuses = list(statuses)
        self.fail = fail
        self.memory = bytearray([0xAA]) * (2 * WINDOW)
        self.held = True
        self.copies = 0
        self.checks = 0

    def check_owned(self):
        self.checks += 1
        if not self.held or self.fail == f"check{self.checks}":
            raise Refusal("ownership_lost")

    def secure_set(self, function_id, start, inclusive_end, region_permission):
        self.events.append(("secure", function_id, start, inclusive_end, region_permission))
        return self.statuses.pop(0) if self.statuses else 0

    def copy(self, offset, data):
        self.copies += 1
        self.events.append(("copy", offset, data))
        self.memory[offset:offset + len(data)] = data  # Side effect before error.
        if self.fail == f"copy{self.copies}":
            raise Refusal("copy_failure")

    def visible(self):
        self.events.append(("visible",))
        if self.fail == "visible":
            raise Refusal("visibility_failure")



class MockOwner(EmiOwner):
    def __init__(self, events, statuses=(), fail=None):
        self.events = events
        self.statuses = statuses
        self.fail = fail
        self.lease = None

    def acquire(self, session):
        if self.lease is not None:
            raise Refusal("owner_already_claimed")
        self.events.append(("acquire",))
        self.lease = MockLease(session, self.events, self.statuses, self.fail)
        return self.lease


class MockOrdinary(OrdinaryTransport):
    def __init__(self, events, fail=None):
        self.events = events
        self.fail = fail
        self.count = 0
        self.session = None

    def submit(self, session, destination, data, encrypted, key_index):
        self.count += 1
        self.session = session
        self.events.append(("ordinary", destination, data, encrypted, key_index))
        if self.fail == f"ordinary{self.count}":
            raise Refusal("ordinary_failure")

    def start(self, session):
        assert session is self.session
        self.events.append(("start",))
        if self.fail == "start":
            raise Refusal("start_failure")


def setup(statuses=(), fail=None, image=None):
    events = []
    owner = MockOwner(events, statuses, fail)
    ordinary = MockOrdinary(events, fail)
    plan = WholeImage(fixture() if image is None else image, owner, ordinary)
    return plan, owner, ordinary, events


def finish(plan):
    while plan.phase in (Phase.NEW, Phase.SECTIONS):
        plan.step()


class WholeImageTests(unittest.TestCase):
    def test_full_image_literal_abi_order_and_confinement(self):
        plan, owner, ordinary, events = setup()
        with self.assertRaises(Refusal):
            plan.start()
        for count in range(1, 5):
            plan.step()
            self.assertEqual(plan.sections_complete, count)
            with self.assertRaises(Refusal):
                plan.start()
        self.assertNotIn(("visible",), events)
        plan.step()
        self.assertIs(plan.phase, Phase.READY)
        self.assertTrue(owner.lease.held)
        plan.start()
        self.assertIs(plan.phase, Phase.START_SUBMITTED)
        self.assertEqual(events, [
            ("acquire",),
            ("ordinary", 0x1000, b"\x01" * 4, True, 3),
            ("ordinary", 0x1010, b"\x02" * 4, False, 0),
            ("secure", 0x82000209, 0x80000000, 0x8007FFFF, 0x90000000),
            ("copy", 32, b"\x03" * 4), ("copy", 48, b"\x04" * 4),
            ("visible",),
            ("secure", 0x82000209, 0x80000000, 0x8007FFFF, 0x90000001),
            ("start",)])
        self.assertTrue(owner.lease.held)
        expected = bytearray([0xAA]) * (2 * WINDOW)
        expected[32:36] = b"\x03" * 4
        expected[48:52] = b"\x04" * 4
        self.assertEqual(owner.lease.memory, expected)
        with self.assertRaises(Refusal):
            plan.start()
        with self.assertRaises(Refusal):
            plan.step()

    def test_input_snapshot_and_frozen_section(self):
        image = fixture()
        plan, _, _, events = setup(image=image)
        image[:] = bytes(len(image))
        with self.assertRaises(FrozenInstanceError):
            plan._sections[0].destination = 0
        self.assertIsInstance(plan._sections, tuple)
        self.assertIsInstance(plan._sections[0].data, bytes)
        finish(plan)
        self.assertEqual(events[1][2], b"\x01" * 4)
        self.assertEqual(events[4], ("copy", 32, b"\x03" * 4))

    def test_each_declared_and_unknown_secure_status(self):
        check_status(0)
        for status in (-1, -2, -3, -4, -5, -(1 << 31), 1, (1 << 31) - 1):
            for stage in ("open", "restore"):
                with self.subTest(status=status, stage=stage):
                    plan, owner, _, events = setup([status, 0] if stage == "open" else [0, status])
                    with self.assertRaises(SecureFailure) as error:
                        finish(plan)
                    self.assertEqual(error.exception.status, status)
                    self.assertIs(plan.failure, error.exception)
                    self.assertIs(plan.phase, Phase.FAILED)
                    self.assertTrue(owner.lease.held)
                    self.assertEqual(sum(e[0] == "secure" for e in events), 2)
                    self.assertNotIn(("start",), events)
                    self.assertEqual(owner.lease.copies, 0 if stage == "open" else 2)
                    with self.assertRaises(Refusal):
                        plan.start()
                    with self.assertRaises(Refusal):
                        plan.step()

    def test_invalid_secure_result_representation(self):
        for value in (True, False, None, 0.0, "0", 1 << 31, -(1 << 31) - 1, 0xFFFFFFFF):
            with self.subTest(value=value), self.assertRaises(Refusal):
                check_status(value)

    def test_every_copy_and_visibility_failure_restores_without_start(self):
        for failure, completed_count in (("copy1", 2), ("copy2", 3), ("visible", 4)):
            with self.subTest(failure=failure):
                plan, owner, _, events = setup(fail=failure)
                with self.assertRaises(Refusal):
                    finish(plan)
                self.assertEqual(plan.sections_complete, completed_count)
                self.assertEqual(events[-1][0], "secure")
                self.assertEqual(events[-1][-1], 0x90000001)
                self.assertIs(plan.phase, Phase.FAILED)
                self.assertTrue(owner.lease.held)
                self.assertNotIn(("start",), events)
                self.assertNotIn(("release",), events)

    def test_primary_and_restore_failures_are_both_retained(self):
        plan, owner, _, events = setup([0, -4], "copy1")
        with self.assertRaisesRegex(Refusal, "copy_failure"):
            finish(plan)
        self.assertEqual(plan.restore_failure.status, -4)
        self.assertTrue(owner.lease.held)
        self.assertEqual(sum(e[0] == "secure" for e in events), 2)
        plan, _, _, _ = setup([-3, -1])
        with self.assertRaises(SecureFailure):
            finish(plan)
        self.assertEqual(plan.failure.status, -3)
        self.assertEqual(plan.restore_failure.status, -1)

    def test_ordinary_failures_stop_before_emi(self):
        for fail, count in (("ordinary1", 0), ("ordinary2", 1)):
            plan, owner, _, events = setup(fail=fail)
            with self.assertRaises(Refusal):
                finish(plan)
            self.assertEqual(plan.sections_complete, count)
            self.assertEqual(owner.lease.copies, 0)
            self.assertFalse(any(e[0] == "secure" for e in events))
            self.assertTrue(owner.lease.held)

    def test_start_failure_never_allows_second_start(self):
        for failure in ("start",):
            plan, _, _, events = setup(fail=failure)
            finish(plan)
            with self.assertRaises(Refusal):
                plan.start()
            with self.assertRaises(Refusal):
                plan.start()
            self.assertIs(plan.phase, Phase.FAILED)
            self.assertEqual(events.count(("start",)), 1)

    def test_owner_object_and_session_required(self):
        for owner in (True, False, None, object()):
            with self.assertRaises(Refusal):
                WholeImage(fixture(), owner, MockOrdinary([]))
        plan, owner, _, events = setup()
        owner.acquire = lambda session: True
        with self.assertRaisesRegex(Refusal, "missing_reservation_lease"):
            plan.step()
        self.assertEqual(events, [])
        plan, owner, _, _ = setup()
        owner.acquire = lambda session: MockLease(Session(), [])
        with self.assertRaisesRegex(Refusal, "owner_binding_changed"):
            plan.step()
        self.assertIs(plan.phase, Phase.FAILED)

    def test_shared_owner_cannot_be_claimed_twice(self):
        first, owner, ordinary, _ = setup()
        second = WholeImage(fixture(), owner, ordinary)
        first.step()
        with self.assertRaisesRegex(Refusal, "owner_already_claimed"):
            second.step()
        finish(first)

    def test_ownership_loss_or_binding_change_prevents_more_actions(self):
        for mutate in (lambda lease: setattr(lease, "held", False),
                       lambda lease: setattr(lease, "session", Session()),
                       lambda lease: setattr(lease, "reservation", Reservation(0x80000000, 2 * WINDOW))):
            plan, owner, _, events = setup()
            for _ in range(3):
                plan.step()
            mutate(owner.lease)
            count = len(events)
            with self.assertRaises(Refusal):
                plan.step()
            self.assertEqual(len(events), count)
            self.assertIsNotNone(plan.restore_failure)
            self.assertIs(plan.phase, Phase.FAILED)

    def test_loss_after_finalization_blocks_start(self):
        plan, owner, _, events = setup()
        finish(plan)
        owner.lease.held = False
        with self.assertRaises(Refusal):
            plan.start()
        self.assertNotIn(("start",), events)

    def test_reservation_overflow_window_edges_and_policy(self):
        for base, size in ((0, WINDOW), (-1, WINDOW), (1 << 32, WINDOW),
                           (0xFFFF0000, WINDOW), (1, WINDOW - 1), (True, WINDOW)):
            with self.subTest(base=base, size=size), self.assertRaises(Refusal):
                Reservation(base, size)
        r = Reservation((1 << 32) - WINDOW, WINDOW)
        self.assertEqual(r.span(WINDOW - 1, 1), (0xFFFFFFFF, 0xFFFFFFFF))
        for offset, length in ((-1, 1), (WINDOW, 1), (WINDOW + 1, 1),
                               (0, 0), (1, WINDOW), (1 << 64, 1), (0, 1 << 64)):
            with self.subTest(offset=offset, length=length), self.assertRaises(Refusal):
                r.span(offset, length)
        for value in (-1, 1 << 24, True):
            with self.assertRaises(Refusal):
                Protection(value, 0)

    def test_bad_images_refused_before_acquisition(self):
        for image in (b"", b"MTKW" + bytes(20), fixture()[:-1], bytes(1024 * 1024 + 1)):
            events = []
            with self.assertRaises(Refusal):
                WholeImage(image, MockOwner(events), MockOrdinary(events))
            self.assertEqual(events, [])
        for destination in (0xF0080000, 0xF007FFFE, 0xFFFFFFFF):
            image = fixture()
            struct.pack_into("<I", image, 24 + 16 * 2 + 12, destination)
            struct.pack_into("<I", image, 4, zlib.crc32(image[8:]))
            with self.assertRaises(Refusal):
                setup(image=image)

    def test_no_missing_or_extra_section_can_enable_start(self):
        for count in (1, 2, 3, 4, 8):
            plan, owner, _, events = setup(image=fixture(count))
            for _ in range(count):
                with self.assertRaises(Refusal):
                    plan.start()
                plan.step()
            self.assertEqual(plan.sections_complete, count)
            with self.assertRaises(Refusal):
                plan.start()
            plan.step()
            plan.start()
            self.assertEqual(owner.lease.copies, max(count - 2, 0))
            self.assertEqual(events.count(("start",)), 1)

    def test_every_ownership_check_failure_is_terminal(self):
        baseline, owner, _, _ = setup()
        finish(baseline)
        baseline.start()
        for check in range(1, owner.lease.checks + 1):
            with self.subTest(check=check):
                plan, _, _, events = setup(fail=f"check{check}")
                with self.assertRaises(Refusal):
                    finish(plan)
                    plan.start()
                self.assertIs(plan.phase, Phase.FAILED)
                starts = events.count(("start",))
                with self.assertRaises(Refusal):
                    plan.start()
                self.assertEqual(events.count(("start",)), starts)

    def test_nonvoid_provider_completion_cannot_advance(self):
        for method in ("check_owned", "copy", "visible"):
            plan, owner, _, events = setup()
            plan.step()
            setattr(owner.lease, method, lambda *args: True)
            with self.assertRaisesRegex(Refusal, "invalid_provider_completion"):
                finish(plan)
            self.assertIs(plan.phase, Phase.FAILED)
            self.assertNotIn(("start",), events)

    def test_interrupted_copy_is_terminal_and_attempts_restore(self):
        plan, owner, _, events = setup()
        plan.step()
        plan.step()
        def interrupted(*args):
            raise KeyboardInterrupt()
        owner.lease.copy = interrupted
        with self.assertRaises(KeyboardInterrupt):
            plan.step()
        self.assertIs(plan.phase, Phase.FAILED)
        self.assertEqual(events[-1][-1], 0x90000001)
        with self.assertRaises(Refusal):
            plan.start()

    def test_abort_before_during_and_after_emi(self):
        for steps in range(6):
            plan, owner, _, events = setup()
            for _ in range(steps):
                plan.step()
            plan.abort()
            self.assertIs(plan.phase, Phase.FAILED)
            with self.assertRaises(Refusal):
                plan.start()
            with self.assertRaises(Refusal):
                plan.step()
            if owner.lease:
                self.assertTrue(owner.lease.held)
            self.assertEqual(sum(e[0] == "secure" for e in events),
                             2 if steps >= 3 else 0)

    def test_reentrant_and_boolean_completion_refused(self):
        plan, owner, ordinary, events = setup()
        ordinary.submit = lambda *args: plan.start()
        with self.assertRaises(Refusal):
            plan.step()
        self.assertNotIn(("start",), events)
        plan, _, ordinary, _ = setup()
        ordinary.submit = lambda *args: True
        with self.assertRaisesRegex(Refusal, "invalid_provider_completion"):
            plan.step()
        self.assertEqual(plan.sections_complete, 0)


if __name__ == "__main__":
    unittest.main()
