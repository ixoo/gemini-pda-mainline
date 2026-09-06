#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pure one-attempt TOPRGU state machine and retained-pstore classifier."""
from __future__ import annotations

from dataclasses import dataclass, field
import re

RELEASE = "7.1.3-gemini-mt6797-toprgu-minimal-restart"
CONTRACT = "toprgu-minimal-restart-v1"
WRAPPER_CONTRACT = "busybox-reboot-n-f-v1"
USB_DEADLINE = 90
SSH_DEADLINE = 15
IDLE_MINIMUM = 45
RESET_GOOD = 5.0
RESET_TIMEOUT_START = 25.0
RESET_TIMEOUT_END = 40.0
REMOTE_COMMAND = b"/bin/reboot <expected-mainline-boot-id>\n"
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
SHA = re.compile(r"[0-9a-f]{64}")


class Refusal(ValueError):
    """A pre-selection gate failed; no physical budget was consumed."""


class Inconclusive(ValueError):
    """A post-selection gate failed; the one physical attempt is consumed."""


def require(ok: bool, reason: str, error=Refusal) -> None:
    if not ok:
        raise error(reason)


def marker_prefix(input_id: str, boot_id: str) -> str:
    require(SHA.fullmatch(input_id) is not None, "candidate input identity malformed")
    require(UUID.fullmatch(boot_id) is not None, "mainline boot ID malformed")
    return (f"GEMINI_TOPRGU_V1 contract={CONTRACT} wrapper={WRAPPER_CONTRACT} "
            f"candidate={RELEASE} input_id={input_id} boot_id={boot_id}")


def wrapper_command(boot_id: str) -> bytes:
    require(UUID.fullmatch(boot_id) is not None, "restart boot ID malformed")
    return ("/bin/reboot " + boot_id + "\n").encode("ascii")


def classify_pstore(records: dict[str, bytes], *, mainline_boot_id: str,
                    input_id: str, raw_sha256: str,
                    padded_sha256: str) -> dict[str, object]:
    """Require one attributable record with entry, request and kernel restart."""
    require(UUID.fullmatch(mainline_boot_id) is not None,
            "mainline boot ID malformed", Inconclusive)
    require(all(SHA.fullmatch(value) is not None for value in
                (input_id, raw_sha256, padded_sha256)),
            "candidate artifact identity malformed", Inconclusive)
    require(bool(records), "retained pstore is empty", Inconclusive)
    prefix = marker_prefix(input_id, mainline_boot_id).encode("ascii")
    carrying = [(name, raw) for name, raw in records.items() if prefix in raw]
    require(len(carrying) == 1,
            "candidate markers are missing or span multiple pstore records",
            Inconclusive)
    name, raw = carrying[0]
    entry = prefix + b" phase=entry"
    request = prefix + b" phase=request count=1"
    reboot = b"reboot: Restarting system"
    require(raw.count(entry) == raw.count(request) == raw.count(reboot) == 1,
            "durable marker multiplicity invalid", Inconclusive)
    entry_at, request_at, reboot_at = raw.index(entry), raw.index(request), raw.index(reboot)
    require(entry_at < request_at < reboot_at,
            "durable marker order invalid", Inconclusive)
    # A second record carrying a partial candidate token is stale/ambiguous too.
    token = ("input_id=" + input_id).encode("ascii")
    require(sum(token in item for item in records.values()) == 1,
            "candidate input identity is not unique in retained pstore",
            Inconclusive)
    return {"classification": "ordered-pstore-marker-chain",
            "pstore_record": name, "input_id": input_id,
            "raw_sha256": raw_sha256, "padded_sha256": padded_sha256,
            "entry_offset": entry_at, "request_offset": request_at,
            "kernel_restart_offset": reboot_at}


@dataclass
class Session:
    raw_sha256: str
    padded_sha256: str
    input_id: str
    wrapper_sha256: str
    deployment_boot_id: str
    selected: bool = False
    consumed: bool = False
    mainline_boot_id: str = ""
    state: str = "prepared"
    events: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        require(all(SHA.fullmatch(value) is not None for value in
                    (self.raw_sha256, self.padded_sha256, self.input_id,
                     self.wrapper_sha256)), "session SHA-256 binding malformed")
        require(UUID.fullmatch(self.deployment_boot_id) is not None,
                "deployment boot ID malformed")

    def _fail(self, reason: str) -> None:
        if self.selected:
            self.consumed = True
            self.state = "inconclusive"
            raise Inconclusive(reason)
        raise Refusal(reason)

    def select(self) -> None:
        require(not self.selected and not self.consumed,
                "selection already consumed")
        self.selected = True
        self.consumed = True
        self.state = "selected"
        self.events.append("selection=1")

    def bind_mainline(self, mainline_boot_id: str) -> None:
        require(self.state == "selected", "mainline identity bound in wrong state")
        if (UUID.fullmatch(mainline_boot_id) is None or
                mainline_boot_id == self.deployment_boot_id):
            self._fail("mainline boot identity invalid")
        self.mainline_boot_id = mainline_boot_id
        self.events.append("mainline_boot=bound")

    def preflight(self, checks: dict[str, bool], ssh_seconds: float) -> None:
        require(self.selected, "runtime preflight occurred before selection")
        required = {"raw_exact", "padded_exact", "input_id_exact",
                    "release_exact", "boot_id_exact", "usb_only",
                    "authenticated", "serviceable", "logger_healthy",
                    "ramoops_exact", "no_userspace_watchdog"}
        if (set(checks) != required or not all(value is True for value in checks.values()) or
                not isinstance(ssh_seconds, (int, float)) or isinstance(ssh_seconds, bool) or
                not 0 <= ssh_seconds <= SSH_DEADLINE):
            self._fail("runtime identity/auth/serviceability/logger preflight failed")
        self.state = "preflight-pass"
        self.events.append("preflight=pass")

    def stable_idle(self, elapsed_seconds: float, *, same_boot: bool,
                    identities_unchanged: bool, automatic_reset: bool) -> None:
        require(self.state == "preflight-pass", "stable idle observed in wrong state")
        if (not isinstance(elapsed_seconds, (int, float)) or isinstance(elapsed_seconds, bool) or
                elapsed_seconds < IDLE_MINIMUM or not same_boot or
                not identities_unchanged or automatic_reset):
            self._fail("stable idle proof failed")
        self.state = "idle-pass"
        self.events.append(f"stable_idle={elapsed_seconds:g}s")

    def preserve_log(self, classification: str, manifest_sha256: str) -> None:
        require(self.state == "idle-pass", "log preservation occurred in wrong state")
        if (classification != "complete-log-through-seal" or
                SHA.fullmatch(manifest_sha256) is None):
            self._fail("pre-action log preservation incomplete")
        self.state = "log-preserved"
        self.events.append("pre_action_log=sealed-and-preserved")

    def request(self, command: bytes) -> None:
        require(self.state == "log-preserved", "restart request not admitted")
        if command != wrapper_command(self.mainline_boot_id):
            self._fail("remote command not allowlisted")
        self.state = "requested"
        self.events.append("restart_request=1")

    def observe_reset(self, *, process_status: int, process_reason: str | None,
                      stdin_complete: bool, request_frame_exact: bool,
                      elapsed_seconds: float, disconnected: bool) -> None:
        require(self.state == "requested", "reset observed in wrong state")
        if (process_status != 255 or process_reason is not None or
                stdin_complete is not True or request_frame_exact is not True):
            self._fail("restart command returned or request transport was incomplete")
        if (not isinstance(elapsed_seconds, (int, float)) or isinstance(elapsed_seconds, bool) or
                not 0 <= elapsed_seconds <= RESET_GOOD or disconnected is not True):
            self._fail("reset/disconnect exceeded the five-second bound")
        self.state = "reset-observed"
        self.events.append(f"reset_disconnect={elapsed_seconds:g}s")

    def recover(self, recovered_boot_id: str, records: dict[str, bytes],
                *, recovery_kernel: str, recovery_arch: str,
                collector_complete: bool) -> dict[str, object]:
        require(self.state == "reset-observed", "recovery observed in wrong state")
        if (collector_complete is not True or recovery_kernel != "3.18.41+" or
                recovery_arch != "aarch64" or
                UUID.fullmatch(recovered_boot_id or "") is None or
                recovered_boot_id in (self.deployment_boot_id, self.mainline_boot_id)):
            self._fail("changed-ID known-good Gemian recovery missing")
        markers = classify_pstore(records, mainline_boot_id=self.mainline_boot_id,
                                  input_id=self.input_id,
                                  raw_sha256=self.raw_sha256,
                                  padded_sha256=self.padded_sha256)
        self.state = "pass"
        self.events.append("recovery=changed-id-gemian")
        return {"classification": "toprgu-minimal-restart-pass",
                "consumed": True, "events": list(self.events),
                "markers": markers, "recovered_boot_id": recovered_boot_id}


def classify_runtime(session: Session, *, mainline_boot_id: str,
                     usb_seconds: float, ssh_seconds: float,
                     checks: dict[str, bool], idle_seconds: float,
                     same_boot: bool, identities_unchanged: bool,
                     automatic_reset: bool, log_classification: str,
                     log_manifest_sha256: str, command: bytes,
                     process_status: int, process_reason: str | None,
                     stdin_complete: bool, request_frame_exact: bool,
                     disconnect_seconds: float, disconnected: bool,
                     recovered_boot_id: str, recovery_kernel: str,
                     recovery_arch: str, collector_complete: bool,
                     pstore_records: dict[str, bytes]) -> dict[str, object]:
    session.select()
    if (not isinstance(usb_seconds, (int, float)) or isinstance(usb_seconds, bool) or
            not 0 <= usb_seconds <= USB_DEADLINE):
        session._fail("USB interface deadline exceeded")
    session.bind_mainline(mainline_boot_id)
    session.preflight(checks, ssh_seconds)
    session.stable_idle(idle_seconds, same_boot=same_boot,
                        identities_unchanged=identities_unchanged,
                        automatic_reset=automatic_reset)
    session.preserve_log(log_classification, log_manifest_sha256)
    session.request(command)
    session.observe_reset(process_status=process_status,
                          process_reason=process_reason,
                          stdin_complete=stdin_complete,
                          request_frame_exact=request_frame_exact,
                          elapsed_seconds=disconnect_seconds,
                          disconnected=disconnected)
    return session.recover(recovered_boot_id, pstore_records,
                           recovery_kernel=recovery_kernel,
                           recovery_arch=recovery_arch,
                           collector_complete=collector_complete)
