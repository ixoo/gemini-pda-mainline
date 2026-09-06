#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one admitted TOPRGU restart observation; default is offline validation.

The executable owns the complete host sequence.  It starts the strict Gemian
recovery collector before asking the custodian to select boot2, permits one
candidate wrapper request, preserves pre-action RAM evidence, and never retries
after selection.  ``--execute`` and an exact interactive acknowledgement are
both required for the physical session.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import selectors
import shlex
import signal
import socket
import stat
import subprocess
import sys
import tarfile
import time

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
REPO = EXPERIMENT.parents[1]
sys.path.insert(0, str(HERE))
import session as S  # noqa: E402

BASELINE = REPO / "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts"
HISTORICAL = REPO / "experiments/2026-09-04-mt6797-pwrap-reset-serviceability/scripts"
COLLECTOR = REPO / "scripts/collect-device-pstore"
PINS = {
    BASELINE / "collect-baseline.py": "efbca1e464e04005d3b7d503742b426eb9f642140ec289c40bc43563852208cf",
    BASELINE / "session_steps.py": "762616bb386647e0a25addd36ad9dba2f6384ebde4858f89a806a32678fc60fc",
    HISTORICAL / "remote_observe.sh": "bfa7b11a355263f181285b12d99a07c1ca71ac6b8f13570730da7783937e9fe4",
    HISTORICAL / "classify_observation.py": "f628143d6a70fdda8c6da5171c69e91647a51eb3cb65fa1577d2487540cb1ca6",
    COLLECTOR: "9047084f3012aff47e23e56498d4bc0ae6f8fb7e4f15caec10abb6c15e9a9b3b",
}
RECOVERY_HOSTS = REPO / "artifacts/credentials/a53-recovery-known_hosts"
RECOVERY_HOSTS_SHA256 = "d43262bd1f9c76d02eb633900f5e5502e2342d6c1b41586a2d7e524a2293768f"
RECOVERY_KEY = REPO / "artifacts/credentials/gemini_ed25519"
CANDIDATE_CREDS = REPO / "artifacts/credentials/a53-auth"
TARGET = "root@10.15.19.82"
RECOVERY_TARGET = "gemini@192.168.1.50"
SELECT_PHRASE = "boot2-selected-once"
SELECTION_CHECKPOINT = "selection-consumed"
SELECTION_CHECKPOINT_BYTES = b"selection-consumed=true\n"
SHA = re.compile(r"[0-9a-f]{64}")
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def regular(path: Path, limit: int = 4 * 1024 * 1024, mode: int | None = None) -> bytes:
    info = path.lstat()
    require(not path.is_symlink() and stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
            info.st_size <= limit, "unsafe or oversized input: " + path.name)
    if mode is not None:
        require(stat.S_IMODE(info.st_mode) == mode and info.st_uid == os.getuid(),
                "private input metadata changed: " + path.name)
    return path.read_bytes()


def source_tools():
    for path, expected in PINS.items():
        require(digest(regular(path, 512 * 1024)) == expected,
                "reviewed session source changed: " + str(path.relative_to(REPO)))
    collect = runpy.run_path(str(BASELINE / "collect-baseline.py"))
    steps = runpy.run_path(str(BASELINE / "session_steps.py"))
    return collect, steps


def private_ignored(path: Path) -> None:
    require(path.is_relative_to(REPO / "artifacts"), "private input is outside artifacts")
    ignored = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", "--", str(path)],
                             check=False, timeout=5)
    require(ignored.returncode == 0, "private input is not Git-ignored")


def ssh_command(known_hosts: Path, key: Path) -> list[str]:
    options = ["BatchMode=yes", "IdentitiesOnly=yes", "IdentityAgent=none",
               "PreferredAuthentications=publickey", "PasswordAuthentication=no",
               "KbdInteractiveAuthentication=no", "NumberOfPasswordPrompts=0",
               "StrictHostKeyChecking=yes", "UserKnownHostsFile=" + str(known_hosts),
               "GlobalKnownHostsFile=/dev/null", "HostKeyAlgorithms=ssh-ed25519",
               "PubkeyAcceptedAlgorithms=ssh-ed25519", "UpdateHostKeys=no",
               "VerifyHostKeyDNS=no", "CanonicalizeHostname=no", "ProxyCommand=none",
               "ProxyJump=none", "ControlMaster=no", "ControlPath=none",
               "ControlPersist=no", "ClearAllForwardings=yes", "ForwardAgent=no",
               "ForwardX11=no", "ConnectionAttempts=1", "ConnectTimeout=10",
               "ServerAliveInterval=0", "LogLevel=ERROR", "EscapeChar=none"]
    return (["/usr/bin/ssh", "-F", "/dev/null", "-T", "-p", "22", "-i", str(key)] +
            [item for option in options for item in ("-o", option)] +
            [TARGET, "/bin/busybox sh -s"])


def recovery_command() -> list[str]:
    command = ssh_command(RECOVERY_HOSTS, RECOVERY_KEY)
    command[command.index(TARGET)] = RECOVERY_TARGET
    command[command.index("/bin/busybox sh -s")] = "sh -s"
    return command


def fields(raw: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.decode("ascii").splitlines():
        key, separator, value = line.partition("=")
        require(bool(separator) and bool(key) and key not in result and value == value.strip(),
                "malformed/duplicate runtime field")
        result[key] = value
    return result


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def mkdir_durable(path: Path, mode: int = 0o700, *, parents: bool = True) -> None:
    """Create private directories and publish each new entry to its parent."""
    missing = []
    cursor = path
    while True:
        try:
            info = cursor.lstat()
        except FileNotFoundError:
            missing.append(cursor)
            parent = cursor.parent
            require(parent != cursor, "managed directory has no existing ancestor")
            cursor = parent
            continue
        require(not cursor.is_symlink() and stat.S_ISDIR(info.st_mode),
                "managed directory is not a private directory")
        break
    require(parents or len(missing) <= 1, "managed directory parent is missing")
    if not missing:
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == mode,
                "managed directory privacy metadata changed")
    for directory in reversed(missing):
        directory.mkdir(mode=mode)
        directory.chmod(mode)
        created = directory.lstat()
        require(created.st_uid == os.getuid() and stat.S_IMODE(created.st_mode) == mode,
                "managed directory privacy metadata changed")
        sync_directory(directory)
        sync_directory(directory.parent)


def selection_consumed(attempt: Path) -> bool:
    """Return the conservative state of the durable physical-selection gate.

    The marker is considered opened only after its file and containing
    directory have been fsynced.  Once a marker is visible, malformed or
    unreadable marker contents are also treated as consumed: losing the
    marker's details must never turn a post-selection failure into a
    preselection repair.
    """
    marker = attempt / SELECTION_CHECKPOINT
    try:
        marker.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def persist_selection_checkpoint(attempt: Path) -> None:
    """Atomically persist and fsync the one-selection checkpoint."""
    marker = attempt / SELECTION_CHECKPOINT
    pending = attempt / ("." + SELECTION_CHECKPOINT + ".pending")
    require(not marker.exists() and not pending.exists(), "selection checkpoint already exists")
    write_new(pending, SELECTION_CHECKPOINT_BYTES)
    sync_directory(attempt)
    os.replace(pending, marker)
    try:
        sync_directory(attempt)
    except BaseException:
        # The prompt must not open unless the final directory entry was
        # successfully fsynced.  Best-effort rollback keeps a failed
        # preselection checkpoint outside the consumed state.
        try:
            marker.unlink()
        except BaseException:
            pass
        try:
            sync_directory(attempt)
        except BaseException:
            pass
        raise


def identity_script(candidate: dict, expected_boot: str | None = None) -> str:
    members = candidate["members"]
    expected = "" if expected_boot is None else f'[ "$boot" = "{expected_boot}" ] || exit 1\n'
    lines = ["BB=/bin/busybox", "set -eu", "export LC_ALL=C",
             f'[ "$($BB uname -r)" = "{S.RELEASE}" ] || exit 1',
             "boot=$($BB cat /proc/sys/kernel/random/boot_id)", expected.rstrip(),
             '[ "$($BB cat /run/a53/boot-id)" = "$boot" ] || exit 1']
    for name in ("init", "bin/busybox", "bin/reboot", "bin/kmsg-capture", "bin/kmsg-seal"):
        lines += [f'value=$($BB sha256sum /{name})',
                  f'[ "${{value%% *}}" = "{members[name]["sha256"]}" ] || exit 1']
    return "\n".join(line for line in lines if line) + "\n"


def preflight_script(candidate: dict, expected_boot: str | None = None) -> bytes:
    prefix = identity_script(candidate, expected_boot) + r'''
$BB printf '__TOPRGU_PREFLIGHT_BEGIN__\nboot_id=%s\n' "$boot"
$BB printf 'cpu_possible=%s\ncpu_present=%s\ncpu_online=%s\ncpu_offline=%s\n' \
  "$($BB cat /sys/devices/system/cpu/possible)" "$($BB cat /sys/devices/system/cpu/present)" \
  "$($BB cat /sys/devices/system/cpu/online)" "$($BB cat /sys/devices/system/cpu/offline)"
usb=$($BB ifconfig usb0 2>/dev/null | $BB grep -Ec 'inet (addr:)?10\.15\.19\.82([[:space:]]|$)')
$BB printf 'usb_ipv4_exact_count=%s\n' "$usb"
pid=$($BB cat /run/a53/kmsg-pid) || exit 1
case "$pid" in ''|*[!0-9]*) exit 1;; esac
$BB kill -0 "$pid" || exit 1
[ ! -e /run/a53/kmsg.status ] && [ ! -L /run/a53/kmsg.status ] || exit 1
[ ! -e /run/a53/kmsg-exit ] && [ ! -L /run/a53/kmsg-exit ] || exit 1
$BB printf 'logger_healthy=yes\n'
for pair in mem_address:0x44410000 mem_size:0xe0000 record_size:0x1000 console_size:0x10000 pmsg_size:0x20000 ftrace_size:0x1000 mem_type:0 ecc:0; do
  name=${pair%:*}; expected=${pair#*:}; actual=$($BB cat "/sys/module/ramoops/parameters/$name") || exit 1
  [ "$((actual))" -eq "$((expected))" ] || exit 1
done
$BB printf 'ramoops_exact=yes\n'
watchdog_processes=0
for item in /proc/[0-9]*/cmdline; do
  [ -r "$item" ] || continue
  case "$($BB tr '\000' ' ' <"$item")" in *watchdog*) watchdog_processes=$((watchdog_processes + 1));; esac
done
$BB printf 'userspace_watchdog_count=%s\n__TOPRGU_PREFLIGHT_END__\n' "$watchdog_processes"
'''
    return (prefix.encode("ascii") + regular(HISTORICAL / "remote_observe.sh", 65536) +
            b"\n/bin/busybox printf '__TOPRGU_SERVICEABILITY_DONE__\\n'\n")


def parse_preflight(raw: bytes, stderr: bytes, process: dict, deployment_boot: str) -> str:
    require(not stderr and process["exit_status"] == 0 and process["reason"] is None and
            process["stdin_complete"] is True, "runtime SSH/preflight transport")
    begin, end = b"__TOPRGU_PREFLIGHT_BEGIN__\n", b"__TOPRGU_PREFLIGHT_END__\n"
    require(raw.count(begin) == raw.count(end) == 1 and raw.endswith(b"__TOPRGU_SERVICEABILITY_DONE__\n"),
            "runtime frame completeness")
    header = fields(raw.split(begin, 1)[1].split(end, 1)[0])
    require(set(header) == {"boot_id", "cpu_possible", "cpu_present", "cpu_online", "cpu_offline",
                            "usb_ipv4_exact_count", "logger_healthy", "ramoops_exact",
                            "userspace_watchdog_count"}, "runtime frame inventory")
    require(UUID.fullmatch(header["boot_id"]) is not None and header["boot_id"] != deployment_boot and
            [header[k] for k in ("cpu_possible", "cpu_present", "cpu_online", "cpu_offline")] ==
            ["0-9", "0-9", "0-7", "8-9"] and header["usb_ipv4_exact_count"] == "1" and
            header["logger_healthy"] == header["ramoops_exact"] == "yes" and
            header["userspace_watchdog_count"] == "0", "runtime identity/serviceability/logger preflight")
    classifier = runpy.run_path(str(HISTORICAL / "classify_observation.py"))
    classifier["classify"].__globals__["RELEASE"] = S.RELEASE
    observed = classifier["classify"](raw.decode("ascii"), deployment_boot)
    require(observed == header["boot_id"], "serviceability/mainline identity mismatch")
    return observed


def strict_collector_source() -> bytes:
    source = regular(COLLECTOR, 512 * 1024).decode("utf-8")
    old = "\t-o StrictHostKeyChecking=accept-new\n"
    require(source.count(old) == 1, "collector SSH anchor changed")
    options = ("\t-o StrictHostKeyChecking=yes\n"
               f"\t-o UserKnownHostsFile={shlex.quote(str(RECOVERY_HOSTS))}\n"
               "\t-o GlobalKnownHostsFile=/dev/null\n"
               "\t-o UpdateHostKeys=no\n\t-o VerifyHostKeyDNS=no\n"
               "\t-o CanonicalizeHostname=no\n\t-o ProxyCommand=none\n"
               "\t-o ProxyJump=none\n\t-o ControlMaster=no\n"
               "\t-o ClearAllForwardings=yes\n\t-o ForwardAgent=no\n\t-o ForwardX11=no\n")
    return source.replace(old, options).encode("utf-8")


def prepare(candidate_dir: Path, deployment_path: Path, admission_path: Path, *,
            base_dtb: Path, foundation_initramfs: Path, userspace: Path,
            credentials: Path) -> dict:
    collect, steps = source_tools()
    for path in (candidate_dir, deployment_path, admission_path, base_dtb,
                 foundation_initramfs, userspace, credentials):
        private_ignored(path)
    validator = runpy.run_path(str(HERE / "validate-candidate.py"))
    validator["validate"](candidate_dir, base_dtb=base_dtb,
                          foundation_initramfs=foundation_initramfs,
                          userspace=userspace, credentials=credentials)
    manifest_raw = regular(candidate_dir / "candidate.json")
    candidate = json.loads(manifest_raw, object_pairs_hook=no_duplicates)
    admission_raw = regular(admission_path, 32768, 0o600)
    admission = json.loads(admission_raw, object_pairs_hook=no_duplicates)
    required = {"schema", "experiment", "action", "admission_id", "source_commit", "collector_initial_boot_id",
                "candidate_sha256", "candidate_manifest_sha256",
                "deployment_receipt_sha256", "expected_predecessor_sha256", "executor_sha256",
                "session_sha256", "candidate_validator_sha256", "deployment_parser_sha256",
                "session_packet_sha256", "collector_sha256", "recovery_known_hosts_sha256",
                "candidate_known_hosts_sha256", "candidate_admin_public_sha256", "custodian_role",
                "custody_exclusive", "observation_budget", "physical_selection_phrase_sha256"}
    require(set(admission) == required and admission["schema"] == 1 and
            admission["experiment"] == EXPERIMENT.name and admission["action"] == "one-toprgu-restart" and
            admission["custody_exclusive"] is True and admission["observation_budget"] == 1,
            "session admission inventory/scope")
    require(UUID.fullmatch(str(admission["admission_id"])) is not None and
            UUID.fullmatch(str(admission["collector_initial_boot_id"])) is not None and
            re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{0,63}", str(admission["custodian_role"])) is not None,
            "session admission/custodian identity")
    require(all(SHA.fullmatch(admission[k] or "") for k in required if k.endswith("sha256")),
            "session admission digest")
    runtime_pins = {
        "executor_sha256": digest(Path(__file__).read_bytes()),
        "session_sha256": digest(regular(HERE / "session.py", 512 * 1024)),
        "candidate_validator_sha256": digest(regular(HERE / "validate-candidate.py", 512 * 1024)),
        "deployment_parser_sha256": digest(regular(HERE / "deployment_receipt.py", 512 * 1024)),
        "session_packet_sha256": digest(regular(EXPERIMENT / "session-packet.json", 512 * 1024)),
        "collector_sha256": PINS[COLLECTOR],
        "recovery_known_hosts_sha256": RECOVERY_HOSTS_SHA256,
    }
    require(all(admission[key] == value for key, value in runtime_pins.items()),
            "session runtime source binding")
    require(admission["candidate_sha256"] == candidate["padded_sha256"] and
            candidate_dir.name == "candidate-" + candidate["padded_sha256"] and
            admission["candidate_manifest_sha256"] == digest(manifest_raw) and
            admission["physical_selection_phrase_sha256"] == digest((SELECT_PHRASE + "\n").encode()),
            "session admission identity")
    deployment_raw = regular(deployment_path, 32768, 0o600)
    require(digest(deployment_raw) == admission["deployment_receipt_sha256"], "deployment receipt identity")
    receipt = runpy.run_path(str(HERE / "deployment_receipt.py"))
    deployment_boot = receipt["receipt"](deployment_raw.decode("ascii"), candidate["padded_sha256"],
                                          digest(manifest_raw), admission["expected_predecessor_sha256"])
    require(UUID.fullmatch(deployment_boot) is not None, "deployment boot identity")
    require(admission["collector_initial_boot_id"] != deployment_boot,
            "collector initial boot must be the changed boot after deployment shutdown")
    require(digest(regular(RECOVERY_HOSTS, 16384, 0o600)) == RECOVERY_HOSTS_SHA256,
            "recovery host pin changed")
    regular(RECOVERY_KEY, 16384, 0o600)
    require(credentials == CANDIDATE_CREDS, "candidate credential bundle path changed")
    known = credentials / "known_hosts"
    key = credentials / "admin"
    known_raw = regular(known, 16384, 0o600); regular(key, 16384, 0o600)
    public = subprocess.run(["ssh-keygen", "-y", "-f", str(key)], check=True, timeout=10,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip() + b"\n"
    public_file = regular(credentials / "admin.pub", 16384, 0o600)
    require(admission["candidate_known_hosts_sha256"] == digest(known_raw) and
            admission["candidate_admin_public_sha256"] == digest(public_file) and
            public == public_file,
            "candidate SSH identity binding")
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.strip()
    origin_head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "refs/remotes/origin/main"],
                                 check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], check=True,
                           text=True, stdout=subprocess.PIPE).stdout
    origin = subprocess.run(["git", "-C", str(REPO), "remote", "get-url", "origin"], check=True,
                            text=True, stdout=subprocess.PIPE).stdout.strip()
    require(admission["source_commit"] == candidate["source_commit"] == head == origin_head and
            not dirty and origin == "https://github.com/ixoo/gemini-pda-mainline.git",
            "session source is not exact clean pushed origin/main")
    return {"candidate": candidate, "candidate_raw": manifest_raw, "admission": admission,
            "admission_raw": admission_raw, "deployment_raw": deployment_raw,
            "deployment_boot": deployment_boot, "collect": collect, "steps": steps,
            "known_hosts": known, "key": key}


def write_new(path: Path, data: bytes, mode: int = 0o600) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


def invoke(context: dict, root: Path, label: str, script: bytes, timeout: float) -> tuple[bytes, bytes, dict]:
    child = root / label
    child.mkdir(mode=0o700)
    write_new(child / "command.sh", script)
    process = context["collect"]["run_once"](ssh_command(context["known_hosts"], context["key"]),
                                               script, child, timeout,
                                               stdout_limit=3 * 1024 * 1024, stderr_limit=16384)
    write_new(child / "process.json", (json.dumps(process, sort_keys=True) + "\n").encode())
    return regular(child / "stdout.txt", 3 * 1024 * 1024), regular(child / "stderr.txt", 16384), process


def preserve_collector_after_failure(collector, collector_log, *, drained: bool = False,
                                     drain_state: dict[str, bool] | None = None) -> bool:
    """Drain and fsync collector output, converting every failure."""
    if drained:
        return True
    if drain_state is not None and drain_state.get("attempted", False):
        return drain_state.get("drained", False)
    if drain_state is not None:
        drain_state["attempted"] = True
    try:
        # Poll first for the explicit observer-state check, but communicate
        # even when the child has already exited so its buffered stdout is
        # drained exactly once.
        collector.poll()
        remaining, _ = collector.communicate(timeout=300)
        if drain_state is not None:
            drain_state["drained"] = True
        collector_log.write(remaining)
        collector_log.flush()
        os.fsync(collector_log.fileno())
        return True
    except BaseException as error:
        raise S.Inconclusive("post-selection recovery preservation failed: " + str(error)) from error


def cleanup_runtime(collector, collector_log, handlers: dict) -> None:
    """Best-effort cleanup that still reports every cleanup exception."""
    errors: list[BaseException] = []
    try:
        collector_log.close()
    except BaseException as error:
        errors.append(error)
    alive = True
    try:
        alive = collector.poll() is None
    except BaseException as error:
        errors.append(error)
    if alive:
        try:
            os.killpg(collector.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except BaseException as error:
            errors.append(error)
        try:
            collector.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(collector.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except BaseException as error:
                errors.append(error)
            try:
                collector.wait(timeout=5)
            except BaseException as error:
                errors.append(error)
        except BaseException as error:
            errors.append(error)
    for number, handler in handlers.items():
        try:
            signal.signal(number, handler)
        except BaseException as error:
            errors.append(error)
    if errors:
        raise errors[0]


def cleanup_after_execute(attempt: Path, collector, collector_log, handlers: dict) -> None:
    try:
        cleanup_runtime(collector, collector_log, handlers)
    except BaseException as error:
        if selection_consumed(attempt):
            raise S.Inconclusive("post-selection cleanup failed: " + str(error)) from error
        raise


def publish_attempt_result(attempt: Path, result: dict[str, object]) -> None:
    """Publish evidence inventory and result as one no-overwrite transaction."""
    result_path = attempt / "result.json"
    sums_path = attempt / "SHA256SUMS"
    pending_result = attempt / ".result.json.pending"
    pending_sums = attempt / ".SHA256SUMS.pending"
    require(not any(path.exists() for path in (result_path, sums_path, pending_result, pending_sums)),
            "attempt result transaction already exists")
    result_bytes = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    entries = []
    for path in sorted(attempt.rglob("*")):
        if not path.is_file() or path in (result_path, sums_path, pending_result, pending_sums):
            continue
        entries.append((path.relative_to(attempt).as_posix(), digest(regular(path, 4 * 1024 * 1024))))
    entries.append(("result.json", digest(result_bytes)))
    manifest = "".join(f"{checksum}  {name}\n" for name, checksum in sorted(entries))
    try:
        write_new(pending_result, result_bytes)
        write_new(pending_sums, manifest.encode())
        sync_directory(attempt)
        # Publish the complete inventory before exposing result.json.  A
        # failure here leaves no PASS result, only removable pending state.
        os.replace(pending_sums, sums_path)
        sync_directory(attempt)
        os.replace(pending_result, result_path)
        sync_directory(attempt)
    except BaseException:
        # This attempt is never retried.  Remove transaction fragments and
        # final files created by this invocation; any failed fsync remains a
        # conservative incomplete state rather than a successful result.
        for path in (pending_result, pending_sums, result_path, sums_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except BaseException:
                pass
        try:
            sync_directory(attempt)
        except BaseException:
            pass
        raise


def classify_failure(attempt: Path, error: BaseException) -> dict[str, object]:
    """Classify from the durable gate, never from the exception class."""
    consumed = selection_consumed(attempt)
    return {"classification": "inconclusive" if consumed else "refusal",
            "reason": str(error), "consumed": consumed,
            "next_action": ("preserve evidence and recover only; no retry" if consumed else
                            "repair preselection gate; a new admission is required")}


def recovery_preflight(context: dict, attempt: Path) -> None:
    child = attempt / "recovery-preflight"
    child.mkdir(mode=0o700)
    script = (b"set -eu\n"
              b"sudo -n true\n"
              b"printf 'kernel=%s\\narchitecture=%s\\nboot_id=%s\\n' "
              b"\"$(uname -r)\" \"$(uname -m)\" \"$(cat /proc/sys/kernel/random/boot_id)\"\n")
    write_new(child / "command.sh", script)
    process = context["collect"]["run_once"](recovery_command(), script, child, 15,
                                               stdout_limit=16384, stderr_limit=16384)
    write_new(child / "process.json", (json.dumps(process, sort_keys=True) + "\n").encode())
    raw = regular(child / "stdout.txt", 16384); error = regular(child / "stderr.txt", 16384)
    values = fields(raw)
    require(not error and process["exit_status"] == 0 and process["reason"] is None and
            process["stdin_complete"] is True and set(values) == {"kernel", "architecture", "boot_id"} and
            values["kernel"] == "3.18.41+" and values["architecture"] == "aarch64" and
            values["boot_id"] == context["admission"]["collector_initial_boot_id"],
            "strict changed-boot Gemian recovery preflight")
    sync_directory(child); sync_directory(attempt)


def wait_for_usb_port(deadline_seconds: float = S.USB_DEADLINE) -> float:
    start = time.monotonic()
    while time.monotonic() - start <= deadline_seconds:
        try:
            with socket.create_connection(("10.15.19.82", 22), timeout=0.5):
                return time.monotonic() - start
        except OSError:
            time.sleep(0.25)
    raise S.Inconclusive("USB SSH port did not appear before the 90-second deadline")


def disconnect_evidence(stdout: bytes, stderr: bytes, process: dict) -> bool:
    diagnostic = re.fullmatch(
        rb"(?:Connection to 10\.15\.19\.82 closed by remote host\.\r?\n|"
        rb"client_loop: send disconnect: Broken pipe\r?\n)?", stderr)
    return bool(not stdout and diagnostic is not None and process.get("exit_status") == 255 and
                process.get("reason") is None and process.get("stdin_complete") is True and
                isinstance(process.get("elapsed_seconds"), (int, float)) and
                not isinstance(process.get("elapsed_seconds"), bool) and
                0 <= process["elapsed_seconds"] <= S.RESET_GOOD)


def preserve_seal(attempt: Path, parsed: dict) -> str:
    phase = attempt / "pre-action-seal"
    exported = phase / "exported"
    exported.mkdir(mode=0o700)
    require(set(parsed["files"]) == {"kmsg.log", "kmsg.status", "kmsg-exit"},
            "sealed export inventory incomplete")
    for name, data in sorted(parsed["files"].items()):
        require(re.fullmatch(r"[A-Za-z0-9_.-]+", name) is not None, "unsafe exported log name")
        write_new(exported / name, data)
    write_new(phase / "classification.json",
              (json.dumps(parsed["result"], indent=2, sort_keys=True) + "\n").encode())
    manifest = "".join(digest(regular(path, 4 * 1024 * 1024)) + "  " +
                       path.relative_to(phase).as_posix() + "\n"
                       for path in sorted(phase.rglob("*")) if path.is_file())
    write_new(phase / "SHA256SUMS", manifest.encode())
    sync_directory(exported); sync_directory(phase); sync_directory(attempt)
    return digest(manifest.encode())


def preserved_seal_expectations(attempt: Path) -> list[tuple[str, int, str]]:
    """Return exact sealed file identities from the durable host export."""
    phase = attempt / "pre-action-seal"
    exported = phase / "exported"
    names = ("kmsg.log", "kmsg.status", "kmsg-exit")
    require({path.name for path in exported.iterdir()} == set(names),
            "sealed export inventory changed")
    listed: dict[str, str] = {}
    for line in regular(phase / "SHA256SUMS", 65536).decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)", line)
        require(match is not None, "sealed export checksum framing")
        checksum, relative = match.groups()
        require(relative not in listed, "duplicate sealed export checksum")
        listed[relative] = checksum
    result = []
    for name in names:
        data = regular(exported / name, 4 * 1024 * 1024, 0o600)
        checksum = digest(data)
        require(listed.get("exported/" + name) == checksum,
                "sealed export checksum changed: " + name)
        result.append((name, len(data), checksum))
    return result


def restart_script(candidate: dict, boot: str, attempt: Path) -> bytes:
    """Build the one SSH request that revalidates all sealed state then calls the wrapper."""
    require(UUID.fullmatch(boot) is not None, "restart boot identity malformed")
    expectations = preserved_seal_expectations(attempt)
    lines = [identity_script(candidate, boot),
             "# These hashes are read from the just-preserved, fsynced export.",
             "for pair in " + " ".join(f"'{name}|{size}|{checksum}'" for name, size, checksum in expectations) + "; do",
             "  name=${pair%%|*}; rest=${pair#*|}; size=${rest%%|*}; expected=${rest#*|}",
             "  [ -f \"/run/a53/$name\" ] && [ ! -L \"/run/a53/$name\" ] || exit 1",
             "  value=$($BB sha256sum \"/run/a53/$name\") || exit 1",
             "  [ \"${value%% *}\" = \"$expected\" ] || exit 1",
             "  [ \"$($BB stat -c '%s' \"/run/a53/$name\")\" = \"$size\" ] || exit 1",
             "done",
             "[ ! -e /run/a53/kmsg.status.partial ] && [ ! -L /run/a53/kmsg.status.partial ] || exit 1",
             "exec /bin/reboot \"$boot\"\n"]
    return "\n".join(lines).encode("ascii")


def validate_collector_capture(capture: Path, initial_boot: str,
                               recovered_boot: str) -> dict[str, bytes]:
    info = capture.lstat()
    require(not capture.is_symlink() and stat.S_ISDIR(info.st_mode) and
            stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.getuid(),
            "collector output directory metadata")
    sums = regular(capture / "SHA256SUMS", 65536, 0o600)
    listed: set[str] = set()
    for line in sums.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (\./[A-Za-z0-9_./+-]+)", line)
        require(match is not None, "collector checksum framing")
        expected, relative = match.groups(); relative = relative[2:]
        path = Path(relative)
        require(not path.is_absolute() and ".." not in path.parts and relative not in listed and
                relative != "SHA256SUMS", "collector checksum path/duplicate")
        listed.add(relative)
        require(digest(regular(capture / path, 4 * 1024 * 1024, 0o600)) == expected,
                "collector member checksum changed: " + relative)
    actual = {path.relative_to(capture).as_posix() for path in capture.rglob("*") if path.is_file()}
    require(actual == listed | {"SHA256SUMS"}, "collector inventory differs from checksum manifest")
    required = {"cycle.txt", "metadata.txt", "pstore.tar", "pstore-members.txt",
                "pstore-members-verbose.txt", "candidate-l-evidence.txt"}
    require(required <= listed and any(name.startswith("pstore/") for name in listed),
            "collector required inventory incomplete")
    cycle = fields(regular(capture / "cycle.txt", 16384, 0o600))
    cycle_keys = {"wait_for_cycle", "cycle_started_utc", "disconnect_observed_utc",
                  "reconnect_observed_utc", "initial_boot_id_sha256", "final_boot_id_sha256",
                  "boot_id_changed", "capture_kernel", "capture_arch", "expected_kernel",
                  "archive_pre_boot_id_sha256", "archive_post_boot_id_sha256"}
    require(set(cycle) == cycle_keys and cycle["wait_for_cycle"] == cycle["boot_id_changed"] == "yes" and
            cycle["capture_kernel"] == cycle["expected_kernel"] == "3.18.41+" and
            cycle["capture_arch"] == "aarch64", "collector cycle metadata")
    initial_hash = digest((initial_boot + "\n").encode())
    final_hash = digest((recovered_boot + "\n").encode())
    require(cycle["initial_boot_id_sha256"] == initial_hash and
            all(cycle[key] == final_hash for key in ("final_boot_id_sha256",
                "archive_pre_boot_id_sha256", "archive_post_boot_id_sha256")),
            "collector cycle boot identity binding")
    metadata = fields(regular(capture / "metadata.txt", 131072, 0o600))
    require(metadata.get("kernel") == "3.18.41+" and metadata.get("architecture") == "aarch64" and
            metadata.get("boot_id_sha256") == final_hash, "collector recovery metadata binding")
    archive_records: dict[str, bytes] = {}
    with tarfile.open(capture / "pstore.tar", "r:") as archive:
        for member in archive.getmembers():
            if member.name in (".", "./"):
                continue
            require(member.isfile() and re.fullmatch(r"\./[A-Za-z0-9][A-Za-z0-9._+-]*", member.name),
                    "unsafe collector pstore archive member")
            name = member.name[2:]
            require(name not in archive_records and member.size <= 4 * 1024 * 1024,
                    "duplicate/oversized pstore archive member")
            stream = archive.extractfile(member)
            require(stream is not None, "unreadable pstore archive member")
            archive_records[name] = stream.read()
    disk_records = {path.name: regular(path, 4 * 1024 * 1024, 0o600)
                    for path in sorted((capture / "pstore").iterdir())}
    require(archive_records == disk_records, "extracted pstore differs from captured archive")
    return disk_records


def execute(context: dict, attempt: Path) -> dict:
    require(sys.stdin.isatty(), "physical selection requires an interactive terminal")
    mkdir_durable(attempt, mode=0o700, parents=False)
    write_new(attempt / "admission.json", context["admission_raw"])
    write_new(attempt / "candidate.json", context["candidate_raw"])
    write_new(attempt / "deployment.txt", context["deployment_raw"])
    recovery_preflight(context, attempt)
    strict = strict_collector_source()
    collector_script = attempt / "strict-collector.sh"
    write_new(collector_script, strict, 0o700)
    capture = REPO / "artifacts/device-pstore" / ("toprgu-" + attempt.name)
    command = ["/bin/bash", str(collector_script), "--target", RECOVERY_TARGET,
               "--identity", str(RECOVERY_KEY), "--output", str(capture),
               "--wait-seconds", "300", "--wait-for-cycle", "--expected-kernel", "3.18.41+"]
    collector_fd = os.open(attempt / "collector.txt",
                           os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    collector_log = os.fdopen(collector_fd, "wb", buffering=0)
    collector = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 start_new_session=True)
    state = S.Session(context["candidate"]["raw_sha256"], context["candidate"]["padded_sha256"],
                      context["candidate"]["input_id"],
                      context["candidate"]["members"]["bin/reboot"]["sha256"],
                      context["deployment_boot"])
    handlers = {}
    def interrupted(number, _frame):
        raise InterruptedError("session interrupted by signal " + str(number))
    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        handlers[number] = signal.signal(number, interrupted)
    drain_state = {"attempted": False, "drained": False}
    try:
        armed = False
        deadline = time.monotonic() + 30
        selector = selectors.DefaultSelector(); selector.register(collector.stdout, selectors.EVENT_READ)
        while time.monotonic() < deadline and collector.poll() is None:
            for key, _ in selector.select(0.25):
                line = key.fileobj.readline()
                if line:
                    collector_log.write(line)
                    armed |= b"to remain disconnected across two probes" in line
            if armed: break
        selector.close()
        require(armed and collector.poll() is None, "strict recovery collector failed to arm")
        # This is the irreversible host-side checkpoint.  It is fully
        # fsynced before the prompt is displayed, so every later failure is
        # durably consumed even if the in-memory state or exception changes.
        persist_selection_checkpoint(attempt)
        print("Recovery collector armed. Physically select boot2 once, then type the exact acknowledgement.")
        # Opening the physical checkpoint makes an interruption ambiguous, so
        # conservatively consume the one-selection budget from this point.
        state.select()
        acknowledgement = input("selection> ")
        if acknowledgement != SELECT_PHRASE:
            raise S.Inconclusive("physical selection acknowledgement mismatch; selection status is ambiguous")
        usb_seconds = wait_for_usb_port()
        # Once TCP answers, this is the one admitted authenticated preflight.
        # Any authentication, identity, serviceability or logger failure is a
        # consumed inconclusive result; it is never treated as USB polling.
        out, err, process = invoke(context, attempt, "preflight", preflight_script(context["candidate"]),
                                   S.SSH_DEADLINE)
        try:
            boot = parse_preflight(out, err, process, context["deployment_boot"])
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            state._fail(str(error))
        state.bind_mainline(boot)
        checks = {name: True for name in ("raw_exact", "padded_exact", "input_id_exact", "release_exact",
                  "boot_id_exact", "usb_only", "authenticated", "serviceable", "logger_healthy",
                  "ramoops_exact", "no_userspace_watchdog")}
        state.preflight(checks, process["elapsed_seconds"])
        time.sleep(S.IDLE_MINIMUM)
        out, err, process = invoke(context, attempt, "idle-recheck", preflight_script(context["candidate"], boot), S.SSH_DEADLINE)
        require(parse_preflight(out, err, process, context["deployment_boot"]) == boot,
                "stable-idle identity changed")
        state.stable_idle(S.IDLE_MINIMUM, same_boot=True, identities_unchanged=True, automatic_reset=False)
        steps = context["steps"]
        steps["identity_script"].__globals__["RELEASE"] = S.RELEASE
        steps["identity_script"].__globals__["REBOOT_SHA"] = context["candidate"]["members"]["bin/reboot"]["sha256"]
        seal = steps["seal_script"](context["candidate"], boot)
        out, err, process = invoke(context, attempt, "pre-action-seal", seal, 30)
        parsed = steps["parse_log_export"](out, err, process)
        require(parsed["result"]["classification"] == "complete-log-through-seal" and
                parsed["result"]["preservation_complete"] is True, "pre-action log preservation incomplete")
        seal_manifest = preserve_seal(attempt, parsed)
        state.preserve_log("complete-log-through-seal", seal_manifest)
        state.request(S.wrapper_command(boot))
        restart = restart_script(context["candidate"], boot, attempt)
        out, err, process = invoke(context, attempt, "restart-request", restart, S.SSH_DEADLINE)
        disconnect_observed = disconnect_evidence(out, err, process)
        state.observe_reset(process_status=process["exit_status"], process_reason=process["reason"],
                            stdin_complete=process["stdin_complete"], request_frame_exact=disconnect_observed,
                            elapsed_seconds=process["elapsed_seconds"], disconnected=disconnect_observed)
        preserve_collector_after_failure(collector, collector_log, drain_state=drain_state)
        require(collector.returncode == 0 and capture.is_dir(), "recovery collector incomplete")
        probe_root = attempt / "recovery-probe"; probe_root.mkdir(mode=0o700)
        process = context["collect"]["run_once"](recovery_command(), steps["GEMIAN_PROBE"], probe_root, 15)
        write_new(probe_root / "process.json", (json.dumps(process, sort_keys=True) + "\n").encode())
        recovery_out = regular(probe_root / "stdout.txt", 16384); recovery_err = regular(probe_root / "stderr.txt", 16384)
        recovery = steps["parse_gemian"](recovery_out, recovery_err, process, context["deployment_boot"], boot)
        records = validate_collector_capture(capture, context["admission"]["collector_initial_boot_id"],
                                             recovery["boot_id"])
        return state.recover(recovery["boot_id"], records, recovery_kernel="3.18.41+",
                             recovery_arch="aarch64", collector_complete=True) | {"usb_seconds": round(usb_seconds, 3)}
    except BaseException as error:
        if selection_consumed(attempt):
            # No second mainline action is permitted.  Keep the observer alive
            # so the custodian can use only the reviewed physical recovery path
            # and the unique retained evidence can still be captured.
            print("Post-selection gate failed. Do not retry or issue another command; use the reviewed physical recovery path now.",
                  file=sys.stderr, flush=True)
            try:
                preserve_collector_after_failure(collector, collector_log, drain_state=drain_state)
            except BaseException as preservation_error:
                error = S.Inconclusive(str(error) + "; preservation failed: " + str(preservation_error))
            if not isinstance(error, S.Inconclusive):
                error = S.Inconclusive(str(error))
        raise error
    finally:
        cleanup_after_execute(attempt, collector, collector_log, handlers)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--deployment-receipt", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--base-dtb", type=Path, required=True)
    parser.add_argument("--foundation-initramfs", type=Path, required=True)
    parser.add_argument("--userspace", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    context = prepare(args.candidate.resolve(strict=True), args.deployment_receipt.resolve(strict=True),
                      args.admission.resolve(strict=True), base_dtb=args.base_dtb.resolve(strict=True),
                      foundation_initramfs=args.foundation_initramfs.resolve(strict=True),
                      userspace=args.userspace.resolve(strict=True),
                      credentials=args.credentials.resolve(strict=True))
    if not args.execute:
        result = {"classification": "session-dry-run", "device_action": "none",
                  "physical_selection": "not-requested", "candidate": context["candidate"]["padded_sha256"]}
    else:
        root = REPO / "artifacts/toprgu/sessions"
        mkdir_durable(root, mode=0o700, parents=True)
        attempt = root / context["admission"]["admission_id"]
        require(not attempt.exists() and not attempt.is_symlink(), "session attempt already exists; no retry")
        try:
            result = execute(context, attempt)
        except BaseException as error:
            result = classify_failure(attempt, error)
        if attempt.exists():
            try:
                publish_attempt_result(attempt, result)
            except BaseException as error:
                if selection_consumed(attempt):
                    result = classify_failure(attempt, error)
                else:
                    raise
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["classification"] in ("session-dry-run", "toprgu-minimal-restart-pass") else 3


if __name__ == "__main__":
    raise SystemExit(main())
