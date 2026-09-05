#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Pure lifetime model for a future provider-owned gen3 command session.

This reference object is not thread-safe: a future shared provider must hold
one lock across each operation and its actual transport/ownership actions.
Caller-supplied epochs and readiness are consistency assertions, not leases,
authentication, hardware readiness, or proof that stale replies were drained.
No file, hardware, transport, clock, packet builder, retry or reset API exists.
"""

import json
import sys

import wifi_init_protocol as protocol


UINT64_MAX = (1 << 64) - 1
Refusal = protocol.Refusal


def _uint64(value, reason):
    if type(value) is not int or not 0 <= value <= UINT64_MAX:
        raise Refusal(reason)


class InitSession:
    """One finite sequence namespace and at most one pending command.

    Methods return a fresh sanitized snapshot, including terminal outcomes.
    Invalid API types and ordinary refusals raise a fixed Refusal without
    mutation. Valid unsafe context or pending expiry terminates the session
    before busy/unsolicited checks. Ordinary refusals do not advance the clock
    floor; accepted begin/receive/poll observations do. Ticks are caller-defined
    monotonic units, with no inferred source timeout or local clock access.

    Only scalar bookkeeping and a bounded sequence set are retained, never
    command/response bytes, addresses, diagnostics or decoded payloads.
    Closing a failed session preserves its failure and recovery requirement.
    A replacement session requires independent recovery/quiescence evidence;
    neither close nor a new epoch proves it. Callers can relabel stale bytes.
    """

    __slots__ = (
        "_owner_epoch", "_timeout_ticks", "_state", "_outcome", "_last_tick",
        "_used_sequences", "_pending_sequence", "_deadline", "_completed",
        "_recovery_required",
    )

    def __init__(self, owner_epoch, timeout_ticks):
        _uint64(owner_epoch, "invalid_owner_epoch")
        _uint64(timeout_ticks, "invalid_timeout_ticks")
        if timeout_ticks == 0:
            raise Refusal("invalid_timeout_ticks")
        self._owner_epoch = owner_epoch
        self._timeout_ticks = timeout_ticks
        self._state = "idle"
        self._outcome = "created"
        self._last_tick = None
        self._used_sequences = set()
        self._pending_sequence = None
        self._deadline = None
        self._completed = 0
        self._recovery_required = False

    def snapshot(self):
        """Return fixed metadata only; no epochs, sequences or tick values."""
        return {
            "state": self._state,
            "outcome": self._outcome,
            "command_pending": self._pending_sequence is not None,
            "commands_started": len(self._used_sequences),
            "commands_completed": self._completed,
            "recovery_required": self._recovery_required,
            "owner_evidence": "caller_supplied_consistency_only",
            "hardware_readiness": "unproven",
            "transport_quiescence": "unproven",
            "runtime_protocol_match": "unproven",
            "new_session_authorized": False,
            "file_access": False,
            "hardware_access": False,
            "load_authorized": False,
            "transmit_authorized": False,
        }

    @staticmethod
    def _context_types(now_tick, owner_epoch, owner_ready):
        _uint64(now_tick, "invalid_now_tick")
        _uint64(owner_epoch, "invalid_owner_epoch")
        if type(owner_ready) is not bool:
            raise Refusal("invalid_owner_ready")

    def _require_active(self):
        if self._state not in ("idle", "pending"):
            raise Refusal("session_not_active")

    def _fail(self, reason):
        self._state = "failed"
        self._outcome = reason
        self._pending_sequence = None
        self._deadline = None
        self._recovery_required = True
        return self.snapshot()

    def _observe(self, now_tick, owner_epoch, owner_ready):
        # Type checks precede this method. Safe observations alone do not
        # mutate the floor: the public operation must still be accepted.
        self._require_active()
        if not owner_ready:
            self._fail("owner_not_ready")
        elif owner_epoch != self._owner_epoch:
            self._fail("owner_epoch_mismatch")
        elif self._last_tick is not None and now_tick < self._last_tick:
            self._fail("clock_regression")
        elif self._deadline is not None and now_tick >= self._deadline:
            self._fail("timeout")
        return self._state != "failed"

    def begin(self, command, *, expected_sequence, now_tick, owner_epoch,
              owner_ready):
        """Admit one validated logical command; never send or retain it."""
        self._context_types(now_tick, owner_epoch, owner_ready)
        if type(command) is not bytes:
            raise Refusal("immutable_bytes_required")
        if type(expected_sequence) is not int or not 0 <= expected_sequence <= 255:
            raise Refusal("invalid_expected_sequence")
        if not self._observe(now_tick, owner_epoch, owner_ready):
            return self.snapshot()
        if self._state == "pending":
            raise Refusal("command_already_pending")

        protocol.decode_download_config(command, expected_sequence=expected_sequence)
        if expected_sequence in self._used_sequences:
            raise Refusal("sequence_already_used")
        if self._timeout_ticks > UINT64_MAX - now_tick:
            raise Refusal("deadline_overflow")

        self._used_sequences.add(expected_sequence)
        self._pending_sequence = expected_sequence
        self._deadline = now_tick + self._timeout_ticks
        self._last_tick = now_tick
        self._state = "pending"
        self._outcome = "command_pending"
        return self.snapshot()

    def receive(self, response, *, now_tick, owner_epoch, owner_ready):
        """Classify one reply within the pending command's finite lifetime."""
        self._context_types(now_tick, owner_epoch, owner_ready)
        if type(response) is not bytes:
            raise Refusal("immutable_bytes_required")
        if not self._observe(now_tick, owner_epoch, owner_ready):
            return self.snapshot()
        if self._state != "pending":
            raise Refusal("unsolicited_response")
        try:
            decoded = protocol.decode_command_result(
                response, expected_sequence=self._pending_sequence)
        except Refusal:
            return self._fail("protocol_failure")

        self._last_tick = now_tick
        if decoded["firmware_status_code"] != 0:
            return self._fail("firmware_rejected")
        self._pending_sequence = None
        self._deadline = None
        self._completed += 1
        self._state = "idle"
        self._outcome = "source_contract_match"
        return self.snapshot()

    def poll(self, *, now_tick, owner_epoch, owner_ready):
        """Apply a caller observation without waiting or accessing a clock."""
        self._context_types(now_tick, owner_epoch, owner_ready)
        if self._observe(now_tick, owner_epoch, owner_ready):
            self._last_tick = now_tick
        return self.snapshot()

    def transport_error(self):
        """Poison even an idle live session after a caller-reported error."""
        self._require_active()
        return self._fail("transport_error")

    def close(self):
        """Idempotent terminal teardown; does not drain or recover anything."""
        if self._state == "closed":
            return self.snapshot()
        if self._state == "pending":
            self._outcome = "closed_with_pending_command"
            self._recovery_required = True
        elif self._state == "idle":
            self._outcome = "closed"
        self._state = "closed"
        self._pending_sequence = None
        self._deadline = None
        return self.snapshot()


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        print(json.dumps({"status": "refused", "reason": "arguments_not_supported"}))
        return 2
    print(json.dumps({
        "status": "contract_only",
        "model": "mt6797_gen3_single_provider_init_session",
        "max_pending_commands": 1,
        "max_commands_per_session": 256,
        "clock": "caller_supplied_monotonic_ticks",
        "owner_evidence": "caller_supplied_consistency_only",
        "provider_lock_required": True,
        "file_access": False, "hardware_access": False,
        "transport_access": False, "clock_access": False,
        "retry_supported": False, "reset_supported": False,
        "load_authorized": False, "transmit_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
