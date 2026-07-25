#!/usr/bin/env python3
"""Validate one storage-inert Candidate AJ recovery/pstore evidence cycle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import os
import pathlib
import re
import stat
import sys
import tarfile
from dataclasses import dataclass
from types import ModuleType

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
EXPERIMENT = "2026-07-22-a72-reject-cpu8-request"
TARGET = "gemini@192.168.1.50"
IDENTITY_RELATIVE = "artifacts/credentials/gemini_ed25519"
RECOVERY_KERNEL = "3.18.41+"
RECOVERY_ARCH = "aarch64"
RECOVERY_ROOT = "/dev/mmcblk0p29"
CANDIDATE_AJ_SHA256 = "77f29772bafc070da6d0dda621136586348d2d1d1cf0c4cecec6b24800eee3c1"
RUNTIME_VALIDATOR_SHA256 = "e7ec6aa3d9d00fdec8c5d7669956c3c979c21bc228278bcc24d973ef85eff089"
NATIVE_VALIDATOR_SHA256 = "c9e5f2e0353cf20e61b93116ef214ad1eddb3459526f70378a326d675d6f7bbd"
AJ_RAW_SHA256 = "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8"
AJ_RAW_SIZE = "7380992"
AJ_ARTIFACT_MANIFEST_SHA256 = "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7"
AJ_PADDED_SHA256 = "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257"
AI_PADDED_SHA256 = "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
HEX256 = re.compile(r"[0-9a-f]{64}")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SAFE_MEMBER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")

CYCLE_KEYS = {
    "format_version", "experiment", "candidate_label", "target", "identity_relative",
    "ssh_batch_mode", "ssh_identities_only", "ssh_identity_agent",
    "ssh_strict_host_key_checking", "wait_seconds", "one_cycle_attempt",
    "disconnect_probe_failures_required", "pre_snapshot_confirmed",
    "disconnect_confirmed", "reconnect_confirmed", "post_snapshot_confirmed",
    "boot_id_changed", "initial_boot_id_sha256", "final_boot_id_sha256",
    "cycle_started_utc", "pre_snapshot_utc", "disconnect_observed_utc",
    "reconnect_observed_utc", "post_snapshot_utc", "cycle_started_epoch",
    "pre_snapshot_epoch", "disconnect_observed_epoch", "reconnect_observed_epoch",
    "post_snapshot_epoch", "installed_full_sha256_input", "installed_hash_basis",
    "installed_hash_reverified_during_recovery", "runtime_capture_planned",
    "runtime_companion_status", "runtime_companion_preserved",
    "runtime_source_mtime_epoch", "native_reboot_capture_planned",
    "native_reboot_companion_status", "native_reboot_companion_preserved",
    "native_reboot_source_mtime_epoch", "collector_reboot_command_issued",
    "external_reboot_evidence_status", "device_write_operations",
    "device_partition_reads", "remote_pstore_delete_operations",
    "raw_collect_device_pstore_primitive_used",
}
STATE_KEYS = {
    "capture_phase", "kernel", "architecture", "root_source", "boot_id_sha256",
    "pstore_directory",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_pinned(name: str, expected: str, module_name: str) -> ModuleType:
    path = SCRIPT_DIR / name
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"pinned source is absent or unsafe: {name}")
    if digest(path.read_bytes()) != expected:
        raise ValueError(f"pinned source identity changed: {name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load pinned source: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Evidence interpreters are pinned bottom-up.
AJ = load_pinned("candidate_aj.py", CANDIDATE_AJ_SHA256, "aj_recovery_identity")
RUNTIME = load_pinned(
    "validate-runtime.py", RUNTIME_VALIDATOR_SHA256, "aj_recovery_runtime"
)
NATIVE = load_pinned(
    "validate-native-reboot.py", NATIVE_VALIDATOR_SHA256, "aj_recovery_native"
)


@dataclass(frozen=True)
class Snapshot:
    state: dict[str, str]
    inventory: dict[str, tuple[str, int]]
    contents: dict[str, bytes]


@dataclass(frozen=True)
class Result:
    classification: str
    attribution: str
    candidate_boot_id: str
    native_reboot_subgate: str
    runtime_status: str
    native_status: str
    unique_files: int
    stale_files: int
    unique_lines: int
    cmdline_count: int
    cpu8_gate_count: int
    cpu8_failure_count: int
    restart_request_count: int
    restarting_system_count: int
    delta_lines: tuple[str, ...]


def require_private_directory(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{label} is not a non-symlink directory")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError(f"{label} mode is not 0700")


def read_regular(path: pathlib.Path, label: str, maximum: int = 4 * 1024 * 1024) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    if info.st_size > maximum:
        raise ValueError(f"{label} exceeds its size bound")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError(f"{label} mode is not 0600")
    return path.read_bytes()


def parse_env(data: bytes, label: str) -> dict[str, str]:
    text = data.decode("utf-8", errors="strict")
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result or "\x00" in value:
            raise ValueError(f"{label} is malformed or duplicated")
        result[key] = value
    return result


def canonical_integer(value: str, label: str, minimum: int = 0) -> int:
    if re.fullmatch(r"0|[1-9][0-9]*", value) is None:
        raise ValueError(f"{label} is not a canonical integer")
    number = int(value)
    if number < minimum:
        raise ValueError(f"{label} is below {minimum}")
    return number


def parse_inventory(data: bytes, label: str) -> dict[str, tuple[str, int]]:
    text = data.decode("ascii", errors="strict")
    result: dict[str, tuple[str, int]] = {}
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            raise ValueError(f"{label} is malformed")
        checksum, raw_size, name = fields
        if HEX256.fullmatch(checksum) is None or SAFE_MEMBER.fullmatch(name) is None or name in result:
            raise ValueError(f"{label} contains an unsafe or duplicate entry")
        result[name] = (checksum, canonical_integer(raw_size, f"{label} size"))
    return result


def validate_tar(data: bytes, expected: dict[str, tuple[str, int]], label: str) -> None:
    seen: dict[str, tuple[str, int]] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            if len(archive.getmembers()) > 65:
                raise ValueError(f"{label} has too many members")
            for member in archive.getmembers():
                if member.name in (".", "./") and member.isdir():
                    continue
                name = member.name.removeprefix("./")
                if not member.isfile() or SAFE_MEMBER.fullmatch(name) is None or name in seen or member.size > 2 * 1024 * 1024:
                    raise ValueError(f"{label} has an unsafe member")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"{label} has an unreadable member")
                content = stream.read(2 * 1024 * 1024 + 1)
                if len(content) != member.size:
                    raise ValueError(f"{label} member size changed")
                seen[name] = (digest(content), len(content))
    except (tarfile.TarError, OSError) as exc:
        raise ValueError(f"{label} is malformed") from exc
    if seen != expected:
        raise ValueError(f"{label} differs from its inventory")


def validate_snapshot(root: pathlib.Path, phase: str) -> Snapshot:
    require_private_directory(root, f"{phase} snapshot")
    expected_top = {"state.env", "pstore.tar", "pstore-members.txt", "pstore-inventory.tsv", "pstore"}
    if {entry.name for entry in os.scandir(root)} != expected_top:
        raise ValueError(f"{phase} snapshot inventory changed")
    state = parse_env(read_regular(root / "state.env", f"{phase} state"), f"{phase} state")
    if set(state) != STATE_KEYS:
        raise ValueError(f"{phase} state inventory changed")
    fixed = {
        "capture_phase": phase, "kernel": RECOVERY_KERNEL, "architecture": RECOVERY_ARCH,
        "root_source": RECOVERY_ROOT, "pstore_directory": "present",
    }
    for key, value in fixed.items():
        if state[key] != value:
            raise ValueError(f"{phase} recovery state changed: {key}")
    if HEX256.fullmatch(state["boot_id_sha256"]) is None:
        raise ValueError(f"{phase} boot ID checksum is malformed")
    inventory = parse_inventory(
        read_regular(root / "pstore-inventory.tsv", f"{phase} inventory"),
        f"{phase} inventory",
    )
    pstore = root / "pstore"
    require_private_directory(pstore, f"{phase} pstore")
    if {entry.name for entry in os.scandir(pstore)} != set(inventory):
        raise ValueError(f"{phase} extracted pstore inventory changed")
    contents: dict[str, bytes] = {}
    for name, expected in sorted(inventory.items()):
        content = read_regular(pstore / name, f"{phase} pstore {name}", 2 * 1024 * 1024)
        if (digest(content), len(content)) != expected:
            raise ValueError(f"{phase} pstore checksum inventory changed")
        contents[name] = content
    listed = read_regular(root / "pstore-members.txt", f"{phase} member list").decode("ascii", errors="strict").splitlines()
    names = [line.removeprefix("./") for line in listed if line not in (".", "./")]
    if len(names) != len(set(names)) or set(names) != set(inventory):
        raise ValueError(f"{phase} member list changed")
    validate_tar(read_regular(root / "pstore.tar", f"{phase} archive"), inventory, f"{phase} archive")
    return Snapshot(state, inventory, contents)


def normalized_kernel_line(line: bytes) -> bytes:
    value = line.strip()
    value = re.sub(rb"^<\d+>\s*", b"", value, count=1)
    value = re.sub(rb"^\[[^]\r\n]+\]\s*", b"", value, count=1)
    return value


def compare_pstore(pre: Snapshot, post: Snapshot) -> tuple[int, int, list[bytes], tuple[str, ...]]:
    pre_hashes = {checksum for checksum, _ in pre.inventory.values()}
    pre_lines = {normalized_kernel_line(line) for data in pre.contents.values() for line in data.splitlines()}
    unique_files = 0
    stale_files = 0
    unique_lines: list[bytes] = []
    delta: list[str] = []
    for name, (post_hash, post_size) in sorted(post.inventory.items()):
        before = pre.inventory.get(name)
        if before == (post_hash, post_size):
            relation = "unchanged-same-name"
            stale_files += 1
        elif post_hash in pre_hashes:
            relation = "stale-content-renamed"
            stale_files += 1
        else:
            relation = "unique-post-content"
            unique_files += 1
        delta.append(f"{relation}\t{name}\t{before[0] if before else 'absent'}\t{post_hash}\t{post_size}")
        if relation == "unique-post-content":
            for line in post.contents[name].splitlines():
                normalized = normalized_kernel_line(line)
                if normalized not in pre_lines:
                    unique_lines.append(normalized)
    for name, (pre_hash, pre_size) in sorted(pre.inventory.items()):
        if name not in post.inventory:
            delta.append(f"removed-after-cycle\t{name}\t{pre_hash}\tabsent\t{pre_size}")
    return unique_files, stale_files, unique_lines, tuple(delta)


def diagnostic_status(root: pathlib.Path, name: str, expected: str) -> None:
    text = read_regular(root / name, name, 64 * 1024).decode("utf-8", errors="strict")
    if not text or text.splitlines()[0] != f"status={expected}":
        raise ValueError(f"{name} status header changed")


def companion_conditions(
    root: pathlib.Path,
    cycle: dict[str, str],
    disconnect: int,
    reconnect: int,
) -> tuple[str, str, str, str]:
    runtime_status = cycle["runtime_companion_status"]
    native_status = cycle["native_reboot_companion_status"]
    if runtime_status not in {"valid", "invalid", "absent"} or native_status not in {"valid", "invalid", "absent"}:
        raise ValueError("companion status is malformed")
    diagnostic_status(root, "runtime-validation.txt", runtime_status)
    diagnostic_status(root, "native-reboot-validation.txt", native_status)

    runtime_path = root / "candidate-aj-runtime.txt"
    runtime_preserved = cycle["runtime_companion_preserved"]
    runtime_mtime_text = cycle["runtime_source_mtime_epoch"]
    runtime_text = ""
    runtime_boot_id = "unavailable"
    runtime_valid = False
    if runtime_preserved == "yes":
        runtime_data = read_regular(runtime_path, "Candidate AJ runtime companion", 2 * 1024 * 1024)
        runtime_mtime = canonical_integer(runtime_mtime_text, "runtime source mtime")
        if int(runtime_path.stat().st_mtime) != runtime_mtime:
            raise ValueError("preserved runtime mtime differs from the source record")
        try:
            runtime_text = runtime_data.decode("utf-8", errors="strict")
            RUNTIME.validate(runtime_text, AJ.PADDED_SHA256)
            identity = RUNTIME.key_values(RUNTIME.section(runtime_text, "IDENTITY"), "runtime identity")
            candidate = identity.get("boot_id", "")
            if UUID.fullmatch(candidate) is None:
                raise ValueError("runtime boot ID is malformed")
            runtime_valid = disconnect <= runtime_mtime <= reconnect
            if runtime_valid:
                runtime_boot_id = candidate
        except (OSError, UnicodeError, ValueError, KeyError, OverflowError):
            runtime_valid = False
    elif runtime_preserved == "no":
        if runtime_path.exists() or runtime_path.is_symlink() or runtime_mtime_text != "unavailable":
            raise ValueError("unpreserved runtime companion inventory changed")
    else:
        raise ValueError("runtime preservation state is malformed")
    expected_runtime_status = "valid" if runtime_valid else ("invalid" if runtime_preserved == "yes" or runtime_status == "invalid" else "absent")
    if runtime_status != expected_runtime_status:
        raise ValueError("runtime companion status does not match independent validation")

    native_path = root / "candidate-aj-native-reboot.txt"
    native_preserved = cycle["native_reboot_companion_preserved"]
    native_mtime_text = cycle["native_reboot_source_mtime_epoch"]
    native_valid = False
    if native_preserved == "yes":
        native_data = read_regular(native_path, "Candidate AJ native reboot companion", 2 * 1024 * 1024)
        native_mtime = canonical_integer(native_mtime_text, "native reboot source mtime")
        if int(native_path.stat().st_mtime) != native_mtime:
            raise ValueError("preserved native reboot mtime differs from the source record")
        try:
            native_text = native_data.decode("utf-8", errors="strict")
            if not runtime_valid:
                raise ValueError("native reboot companion lacks a valid runtime companion")
            native_boot_id = NATIVE.validate(native_text, runtime_text, AJ.PADDED_SHA256)
            if native_boot_id != runtime_boot_id:
                raise ValueError("native reboot boot ID differs from runtime")
            runtime_mtime = canonical_integer(runtime_mtime_text, "runtime source mtime")
            native_valid = runtime_mtime <= native_mtime <= reconnect
        except (OSError, UnicodeError, ValueError, KeyError, OverflowError):
            native_valid = False
    elif native_preserved == "no":
        if native_path.exists() or native_path.is_symlink() or native_mtime_text != "unavailable":
            raise ValueError("unpreserved native reboot companion inventory changed")
    else:
        raise ValueError("native reboot preservation state is malformed")
    expected_native_status = "valid" if native_valid else ("invalid" if native_preserved == "yes" or native_status == "invalid" else "absent")
    if native_status != expected_native_status:
        raise ValueError("native reboot companion status does not match independent validation")
    external = {"valid": "exact-validated-companion", "invalid": "invalid-companion", "absent": "absent"}[native_status]
    if cycle["external_reboot_evidence_status"] != external:
        raise ValueError("external reboot evidence status changed")
    return runtime_status, native_status, runtime_boot_id, runtime_text


def expected_derived(result: Result) -> str:
    candidate_sha = digest((result.candidate_boot_id + "\n").encode()) if result.candidate_boot_id != "unavailable" else "unavailable"
    values = (
        ("candidate_aj_attribution", result.attribution),
        ("classification", result.classification),
        ("candidate_boot_id", result.candidate_boot_id),
        ("candidate_boot_id_sha256", candidate_sha),
        ("runtime_companion_status", result.runtime_status),
        ("native_reboot_companion_status", result.native_status),
        ("native_reboot_subgate", result.native_reboot_subgate),
        ("exact_aj_cmdline_new_count", str(result.cmdline_count)),
        ("exact_cpu8_gate_new_count", str(result.cpu8_gate_count)),
        ("exact_cpu8_failure_new_count", str(result.cpu8_failure_count)),
        ("exact_restart_request_new_count", str(result.restart_request_count)),
        ("exact_restarting_system_new_count", str(result.restarting_system_count)),
    )
    return "".join(f"{key}={value}\n" for key, value in values)


def write_exclusive(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def validate_manifest(root: pathlib.Path) -> None:
    lines = read_regular(root / "SHA256SUMS", "recovery evidence manifest").decode("ascii", errors="strict").splitlines()
    manifest: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  \./(.+)", line)
        if match is None:
            raise ValueError("recovery evidence manifest is malformed")
        checksum, relative = match.groups()
        path = pathlib.PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or "." in path.parts or relative in manifest or path.name == "SHA256SUMS":
            raise ValueError("recovery evidence manifest path is unsafe or duplicated")
        manifest[relative] = checksum
    actual: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("recovery evidence contains a symlink")
        if path.is_file() and path.name != "SHA256SUMS":
            actual[path.relative_to(root).as_posix()] = digest(read_regular(path, "manifest member"))
    if manifest != actual:
        raise ValueError("recovery evidence manifest does not match the exact file tree")


def validate_evidence(
    root: pathlib.Path,
    expected_installed_full_sha256: str,
    *,
    allow_unfinalized: bool = False,
    write_derived: bool = False,
) -> Result:
    AJ.require_artifact_pins()
    identities = (
        AJ.RAW_SHA256, AJ.RAW_SIZE, AJ.ARTIFACT_MANIFEST_SHA256,
        AJ.PADDED_SHA256, AJ.AI_PADDED_SHA256,
    )
    if identities != (
        AJ_RAW_SHA256, AJ_RAW_SIZE, AJ_ARTIFACT_MANIFEST_SHA256,
        AJ_PADDED_SHA256, AI_PADDED_SHA256,
    ):
        raise ValueError("Candidate AJ/AI artifact identity set changed")
    if expected_installed_full_sha256 != AJ_PADDED_SHA256:
        raise ValueError("expected installed full-partition SHA-256 is not Candidate AJ")
    if root.is_symlink():
        raise ValueError("recovery evidence directory is a symlink")
    root = root.resolve(strict=True)
    require_private_directory(root, "recovery evidence directory")
    cycle = parse_env(read_regular(root / "cycle.env", "cycle record"), "cycle record")
    if set(cycle) != CYCLE_KEYS:
        raise ValueError("cycle record inventory changed")
    fixed = {
        "format_version": "2", "experiment": EXPERIMENT, "candidate_label": "AJ",
        "target": TARGET, "identity_relative": IDENTITY_RELATIVE, "ssh_batch_mode": "yes",
        "ssh_identities_only": "yes", "ssh_identity_agent": "none",
        "ssh_strict_host_key_checking": "yes", "one_cycle_attempt": "yes",
        "disconnect_probe_failures_required": "2", "pre_snapshot_confirmed": "yes",
        "disconnect_confirmed": "yes", "reconnect_confirmed": "yes",
        "post_snapshot_confirmed": "yes", "boot_id_changed": "yes",
        "installed_full_sha256_input": expected_installed_full_sha256,
        "installed_hash_basis": "caller-supplied-prior-full-partition-readback",
        "installed_hash_reverified_during_recovery": "no",
        "runtime_capture_planned": "yes", "native_reboot_capture_planned": "yes",
        "collector_reboot_command_issued": "no", "device_write_operations": "none",
        "device_partition_reads": "none", "remote_pstore_delete_operations": "none",
        "raw_collect_device_pstore_primitive_used": "no",
    }
    for key, value in fixed.items():
        if cycle[key] != value:
            raise ValueError(f"cycle contract changed: {key}")
    wait = canonical_integer(cycle["wait_seconds"], "cycle wait", 1200)
    if wait > 86400:
        raise ValueError("cycle wait exceeds one day")
    if HEX256.fullmatch(cycle["initial_boot_id_sha256"]) is None or HEX256.fullmatch(cycle["final_boot_id_sha256"]) is None or cycle["initial_boot_id_sha256"] == cycle["final_boot_id_sha256"]:
        raise ValueError("recovery boot ID checksum contract changed")
    for key in ("cycle_started_utc", "pre_snapshot_utc", "disconnect_observed_utc", "reconnect_observed_utc", "post_snapshot_utc"):
        if UTC.fullmatch(cycle[key]) is None:
            raise ValueError(f"cycle timestamp is malformed: {key}")
    epoch_keys = ("cycle_started_epoch", "pre_snapshot_epoch", "disconnect_observed_epoch", "reconnect_observed_epoch", "post_snapshot_epoch")
    epochs = [canonical_integer(cycle[key], key) for key in epoch_keys]
    if epochs != sorted(epochs):
        raise ValueError("cycle epochs are not monotonic")
    pre = validate_snapshot(root / "pre", "pre")
    post = validate_snapshot(root / "post", "post")
    if pre.state["boot_id_sha256"] != cycle["initial_boot_id_sha256"] or post.state["boot_id_sha256"] != cycle["final_boot_id_sha256"]:
        raise ValueError("snapshot boot ID does not match the cycle")
    runtime_status, native_status, candidate_boot_id, _ = companion_conditions(root, cycle, epochs[2], epochs[3])
    if candidate_boot_id != "unavailable":
        candidate_sha = digest((candidate_boot_id + "\n").encode())
        if candidate_sha in {cycle["initial_boot_id_sha256"], cycle["final_boot_id_sha256"]}:
            raise ValueError("candidate boot ID equals a recovery boot ID")

    unique_files, stale_files, unique_lines, delta_lines = compare_pstore(pre, post)
    signatures = (
        f"Kernel command line: {AJ.CMDLINE}".encode(),
        b"mt6797-psci: CPU8 boot rejected: A72 power sequence inactive",
        b"CPU8: failed to boot: -11",
        b"Candidate AB: kernel restart requested now (BusyBox reboot -n -f).",
        b"reboot: Restarting system",
    )
    counts = [unique_lines.count(signature) for signature in signatures]
    exact_triplet = counts[:3] == [1, 1, 1]
    if runtime_status == "valid":
        classification, attribution = "ATTRIBUTED", "exact-runtime-companion"
    elif exact_triplet:
        classification, attribution = "ATTRIBUTED_PARTIAL", "unique-exact-aj-pstore-signatures"
    else:
        classification, attribution = "INCONCLUSIVE", "absent"
    if native_status == "valid":
        native_subgate = "passed" if counts[3:] == [1, 1] else "incomplete"
    else:
        native_subgate = native_status
    result = Result(
        classification, attribution, candidate_boot_id, native_subgate,
        runtime_status, native_status, unique_files, stale_files, len(unique_lines),
        counts[0], counts[1], counts[2], counts[3], counts[4], delta_lines,
    )
    delta_text = "".join(line + "\n" for line in delta_lines)
    derived_text = expected_derived(result)
    if write_derived:
        if not allow_unfinalized:
            raise ValueError("--write-derived requires --allow-unfinalized")
        write_exclusive(root / "pstore-delta.tsv", delta_text)
        write_exclusive(root / "derived.env", derived_text)
    if read_regular(root / "pstore-delta.tsv", "pstore delta").decode("ascii", errors="strict") != delta_text:
        raise ValueError("pstore delta differs from pre/post content")
    if read_regular(root / "derived.env", "derived facts").decode("utf-8", errors="strict") != derived_text:
        raise ValueError("derived facts differ from independently derived results")

    expected_top = {
        "cycle.env", "pre", "post", "runtime-validation.txt",
        "native-reboot-validation.txt", "pstore-delta.tsv", "derived.env",
    }
    if cycle["runtime_companion_preserved"] == "yes":
        expected_top.add("candidate-aj-runtime.txt")
    if cycle["native_reboot_companion_preserved"] == "yes":
        expected_top.add("candidate-aj-native-reboot.txt")
    if not allow_unfinalized:
        expected_top |= {"validation.txt", "SHA256SUMS"}
    if {entry.name for entry in os.scandir(root)} != expected_top:
        raise ValueError("recovery evidence top-level inventory changed")
    if not allow_unfinalized:
        validation = read_regular(root / "validation.txt", "validation record").decode("utf-8", errors="strict")
        if f"classification={classification}\n" not in validation or f"native_reboot_subgate={native_subgate}\n" not in validation:
            raise ValueError("validation record result changed")
        validate_manifest(root)
    return result


def emit(result: Result) -> None:
    print("validation=candidate-aj-recovery-evidence")
    print("recovery_kernel=3.18.41+")
    print("recovery_root=/dev/mmcblk0p29")
    print("pre_disconnect_reconnect_post=confirmed")
    print("runtime_mtime_window=disconnect-through-reconnect")
    print(f"runtime_companion_status={result.runtime_status}")
    print(f"native_reboot_companion_status={result.native_status}")
    print(f"post_unique_content_files={result.unique_files}")
    print(f"post_stale_or_unchanged_files={result.stale_files}")
    print(f"post_lines_not_seen_pre={result.unique_lines}")
    print(f"exact_aj_cmdline_new_count={result.cmdline_count}")
    print(f"exact_cpu8_gate_new_count={result.cpu8_gate_count}")
    print(f"exact_cpu8_failure_new_count={result.cpu8_failure_count}")
    print(f"exact_restart_request_new_count={result.restart_request_count}")
    print(f"exact_restarting_system_new_count={result.restarting_system_count}")
    print(f"candidate_aj_attribution={result.attribution}")
    print(f"candidate_boot_id={result.candidate_boot_id}")
    print(f"native_reboot_subgate={result.native_reboot_subgate}")
    print(f"classification={result.classification}")
    print("collector_reboot_command_issued=no")
    print("device_partition_reads=none")
    print("device_write_operations=none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=pathlib.Path, required=True)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    parser.add_argument("--allow-unfinalized", action="store_true")
    parser.add_argument("--write-derived", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_evidence(
            args.evidence, args.expected_installed_full_sha256,
            allow_unfinalized=args.allow_unfinalized, write_derived=args.write_derived,
        )
        emit(result)
        return 0
    except (OSError, UnicodeError, ValueError, KeyError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
