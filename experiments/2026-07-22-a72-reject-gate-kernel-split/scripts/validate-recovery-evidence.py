#!/usr/bin/env python3
"""Validate one read-only Candidate AI recovery/pstore evidence cycle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import pathlib
import re
import stat
import sys
import tarfile
from dataclasses import dataclass

sys.dont_write_bytecode = True


EXPERIMENT = "2026-07-22-a72-reject-gate-kernel-split"
TARGET = "gemini@192.168.1.50"
IDENTITY_RELATIVE = "artifacts/credentials/gemini_ed25519"
RECOVERY_KERNEL = "3.18.41+"
RECOVERY_ARCH = "aarch64"
RECOVERY_ROOT = "/dev/mmcblk0p29"
EXPECTED_INSTALLED_FULL_SHA256 = (
    "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
)
RUNTIME_VALIDATOR_SHA256 = (
    "a1ca2a1a7a33eda0f9f52bbee8d964f3ed3004566183792f2eb4f446cffb1e38"
)
HEX256 = re.compile(r"[0-9a-f]{64}")
UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
SAFE_MEMBER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")
UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")

GENERIC_LINEAGE_TOKENS = (
    b"GEMINI_OBSERVABILITY_20260717_L",
    b"GEMINI_USB_GADGET_ETHERNET_20260721_AC",
    b"GEMINI_MT6797_KERNEL_RESTART_20260720_AB",
    b"7.1.3-gemini-observability-L",
)

CYCLE_KEYS = {
    "format_version",
    "experiment",
    "candidate_label",
    "target",
    "identity_relative",
    "ssh_batch_mode",
    "ssh_identities_only",
    "ssh_identity_agent",
    "ssh_strict_host_key_checking",
    "wait_seconds",
    "one_cycle_attempt",
    "disconnect_probe_failures_required",
    "pre_snapshot_confirmed",
    "disconnect_confirmed",
    "reconnect_confirmed",
    "post_snapshot_confirmed",
    "boot_id_changed",
    "initial_boot_id_sha256",
    "final_boot_id_sha256",
    "cycle_started_utc",
    "pre_snapshot_utc",
    "disconnect_observed_utc",
    "reconnect_observed_utc",
    "post_snapshot_utc",
    "cycle_started_epoch",
    "pre_snapshot_epoch",
    "disconnect_observed_epoch",
    "reconnect_observed_epoch",
    "post_snapshot_epoch",
    "installed_full_sha256_input",
    "installed_hash_basis",
    "installed_hash_reverified_during_recovery",
    "runtime_capture_requested",
    "runtime_source_mtime_epoch",
    "candidate_boot_id",
    "candidate_boot_id_sha256",
    "candidate_ai_attribution",
    "classification",
    "reboot_command_issued",
    "device_write_operations",
    "device_partition_reads",
    "remote_pstore_delete_operations",
    "raw_collect_device_pstore_primitive_used",
}

STATE_KEYS = {
    "capture_phase",
    "kernel",
    "architecture",
    "root_source",
    "boot_id_sha256",
    "pstore_directory",
}


@dataclass(frozen=True)
class Snapshot:
    state: dict[str, str]
    inventory: dict[str, tuple[str, int]]
    contents: dict[str, bytes]


@dataclass(frozen=True)
class ValidationResult:
    classification: str
    candidate_ai_attribution: str
    candidate_boot_id: str
    post_unique_content_files: int
    post_stale_or_unchanged_files: int
    post_lines_not_seen_pre: int
    generic_lineage_token_lines: int
    restart_request_line_new: bool
    restarting_system_line_new: bool
    delta_lines: tuple[str, ...]


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str, maximum: int = 4 * 1024 * 1024) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError(f"{label} is absent") from exc
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError(f"{label} is not a regular non-symlink file")
    if info.st_size > maximum:
        raise ValueError(f"{label} exceeds its size bound")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError(f"{label} mode is not 0600")
    return path.read_bytes()


def require_private_directory(path: pathlib.Path, label: str) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError(f"{label} is absent") from exc
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink():
        raise ValueError(f"{label} is not a non-symlink directory")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError(f"{label} mode is not 0700")


def parse_env(data: bytes, label: str) -> dict[str, str]:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not UTF-8") from exc
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result or "\x00" in value:
            raise ValueError(f"{label} is malformed or duplicated")
        result[key] = value
    return result


def parse_positive_integer(value: str, label: str, *, minimum: int = 0) -> int:
    if re.fullmatch(r"0|[1-9][0-9]*", value) is None:
        raise ValueError(f"{label} is not a canonical integer")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{label} is below {minimum}")
    return result


def load_runtime_validator(script_dir: pathlib.Path) -> object:
    path = script_dir / "validate-runtime.py"
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError("Candidate AI runtime validator is absent") from exc
    if path.is_symlink() or digest_bytes(data) != RUNTIME_VALIDATOR_SHA256:
        raise ValueError("Candidate AI runtime validator source identity changed")
    spec = importlib.util.spec_from_file_location("gemini_ai_recovery_runtime", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load Candidate AI runtime validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory_from_contents(contents: dict[str, bytes]) -> dict[str, tuple[str, int]]:
    return {
        name: (digest_bytes(data), len(data)) for name, data in sorted(contents.items())
    }


def parse_inventory(data: bytes, label: str) -> dict[str, tuple[str, int]]:
    try:
        text = data.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not ASCII") from exc
    result: dict[str, tuple[str, int]] = {}
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            raise ValueError(f"{label} is malformed")
        checksum, raw_size, name = fields
        if (
            HEX256.fullmatch(checksum) is None
            or SAFE_MEMBER.fullmatch(name) is None
            or name in result
        ):
            raise ValueError(f"{label} has an unsafe or duplicate entry")
        result[name] = (
            checksum,
            parse_positive_integer(raw_size, f"{label} size"),
        )
    return result


def validate_tar(
    data: bytes, expected: dict[str, tuple[str, int]], label: str
) -> None:
    import io

    seen: dict[str, tuple[str, int]] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) > 65:
                raise ValueError(f"{label} has too many members")
            for member in members:
                if member.name in (".", "./") and member.isdir():
                    continue
                name = member.name.removeprefix("./")
                if (
                    not member.isfile()
                    or SAFE_MEMBER.fullmatch(name) is None
                    or name in seen
                    or member.size > 2 * 1024 * 1024
                ):
                    raise ValueError(f"{label} has an unsafe member")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"{label} member is unreadable")
                member_data = stream.read(2 * 1024 * 1024 + 1)
                if len(member_data) != member.size:
                    raise ValueError(f"{label} member size changed")
                seen[name] = (digest_bytes(member_data), len(member_data))
    except (tarfile.TarError, OSError) as exc:
        raise ValueError(f"{label} is malformed") from exc
    if seen != expected:
        raise ValueError(f"{label} content differs from the extracted inventory")


def validate_snapshot(root: pathlib.Path, phase: str) -> Snapshot:
    require_private_directory(root, f"{phase} snapshot")
    expected_top = {
        "state.env",
        "pstore.tar",
        "pstore-members.txt",
        "pstore-inventory.tsv",
        "pstore",
    }
    actual_top = {entry.name for entry in os.scandir(root)}
    if actual_top != expected_top:
        raise ValueError(f"{phase} snapshot inventory changed")

    state = parse_env(read_regular(root / "state.env", f"{phase} state"), f"{phase} state")
    if set(state) != STATE_KEYS:
        raise ValueError(f"{phase} state inventory changed")
    expected_state = {
        "capture_phase": phase,
        "kernel": RECOVERY_KERNEL,
        "architecture": RECOVERY_ARCH,
        "root_source": RECOVERY_ROOT,
        "pstore_directory": "present",
    }
    for key, value in expected_state.items():
        if state[key] != value:
            raise ValueError(f"{phase} recovery state changed: {key}")
    if HEX256.fullmatch(state["boot_id_sha256"]) is None:
        raise ValueError(f"{phase} boot ID checksum is malformed")

    inventory = parse_inventory(
        read_regular(root / "pstore-inventory.tsv", f"{phase} inventory"),
        f"{phase} inventory",
    )
    pstore = root / "pstore"
    require_private_directory(pstore, f"{phase} extracted pstore")
    actual_members = {entry.name for entry in os.scandir(pstore)}
    if actual_members != set(inventory):
        raise ValueError(f"{phase} extracted pstore inventory changed")
    contents: dict[str, bytes] = {}
    for name in sorted(inventory):
        data = read_regular(pstore / name, f"{phase} pstore {name}", 2 * 1024 * 1024)
        contents[name] = data
    if inventory_from_contents(contents) != inventory:
        raise ValueError(f"{phase} pstore checksum inventory changed")

    members_data = read_regular(root / "pstore-members.txt", f"{phase} member list")
    try:
        raw_listed = [
            line.removeprefix("./")
            for line in members_data.decode("ascii", errors="strict").splitlines()
            if line not in (".", "./")
        ]
    except UnicodeDecodeError as exc:
        raise ValueError(f"{phase} member list is not ASCII") from exc
    listed = set(raw_listed)
    if (
        len(raw_listed) != len(listed)
        or listed != set(inventory)
        or any(SAFE_MEMBER.fullmatch(name) is None for name in listed)
    ):
        raise ValueError(f"{phase} member list changed")
    validate_tar(
        read_regular(root / "pstore.tar", f"{phase} pstore archive"),
        inventory,
        f"{phase} pstore archive",
    )
    return Snapshot(state=state, inventory=inventory, contents=contents)


def parse_manifest(root: pathlib.Path) -> dict[str, str]:
    data = read_regular(root / "SHA256SUMS", "recovery evidence manifest")
    try:
        text = data.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("recovery evidence manifest is not ASCII") from exc
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (\./.+)", line)
        if match is None:
            raise ValueError("recovery evidence manifest is malformed")
        checksum, relative = match.groups()
        path = pathlib.PurePosixPath(relative.removeprefix("./"))
        normalized = path.as_posix()
        if (
            path.is_absolute()
            or ".." in path.parts
            or "." in path.parts
            or normalized in result
            or path.name == "SHA256SUMS"
        ):
            raise ValueError("recovery evidence manifest path is unsafe or duplicated")
        result[normalized] = checksum
    return result


def validate_manifest(root: pathlib.Path) -> None:
    manifest = parse_manifest(root)
    actual: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError("recovery evidence contains a symlink")
        if path.is_file() and relative != "SHA256SUMS":
            data = read_regular(path, f"manifest member {relative}")
            actual[relative] = digest_bytes(data)
    if manifest != actual:
        raise ValueError("recovery evidence manifest does not match the exact file tree")


def extract_runtime_boot_id(runtime_validator: object, text: str) -> str:
    identity = runtime_validator.key_values(
        runtime_validator.section(text, "IDENTITY"), "runtime identity"
    )
    boot_id = identity.get("boot_id", "")
    if UUID.fullmatch(boot_id) is None:
        raise ValueError("Candidate AI runtime boot ID is malformed")
    return boot_id


def compare_pstore(pre: Snapshot, post: Snapshot) -> tuple[
    int, int, int, int, bool, bool, tuple[str, ...]
]:
    pre_hashes = {checksum for checksum, _ in pre.inventory.values()}
    pre_lines = {line for data in pre.contents.values() for line in data.splitlines()}
    unique_files = 0
    stale_files = 0
    delta: list[str] = []
    unique_lines: list[bytes] = []
    for name, (post_hash, post_size) in sorted(post.inventory.items()):
        pre_same = pre.inventory.get(name)
        if pre_same == (post_hash, post_size):
            relation = "unchanged-same-name"
            stale_files += 1
        elif post_hash in pre_hashes:
            relation = "stale-content-renamed"
            stale_files += 1
        else:
            relation = "unique-post-content"
            unique_files += 1
        pre_hash = pre_same[0] if pre_same is not None else "absent"
        delta.append(f"{relation}\t{name}\t{pre_hash}\t{post_hash}\t{post_size}")
        if relation == "unique-post-content":
            unique_lines.extend(
                line for line in post.contents[name].splitlines() if line not in pre_lines
            )
    for name, (pre_hash, pre_size) in sorted(pre.inventory.items()):
        if name not in post.inventory:
            delta.append(f"removed-after-cycle\t{name}\t{pre_hash}\tabsent\t{pre_size}")

    generic_lines = sum(
        1 for line in unique_lines if any(token in line for token in GENERIC_LINEAGE_TOKENS)
    )
    request = any(
        b"Candidate AB: kernel restart requested now (BusyBox reboot -n -f)." in line
        for line in unique_lines
    )
    restarting = any(b"reboot: Restarting system" in line for line in unique_lines)
    return (
        unique_files,
        stale_files,
        len(unique_lines),
        generic_lines,
        request,
        restarting,
        tuple(delta),
    )


def validate_evidence(
    root: pathlib.Path,
    expected_installed_full_sha256: str,
    *,
    allow_unfinalized: bool = False,
    write_delta: bool = False,
) -> ValidationResult:
    if HEX256.fullmatch(expected_installed_full_sha256) is None:
        raise ValueError("expected installed full-partition SHA-256 is malformed")
    if expected_installed_full_sha256 != EXPECTED_INSTALLED_FULL_SHA256:
        raise ValueError("expected installed full-partition SHA-256 is not Candidate AI")
    if root.is_symlink():
        raise ValueError("recovery evidence directory is a symlink")
    root = root.resolve(strict=True)
    require_private_directory(root, "recovery evidence directory")

    cycle = parse_env(read_regular(root / "cycle.env", "cycle record"), "cycle record")
    if set(cycle) != CYCLE_KEYS:
        raise ValueError("cycle record inventory changed")
    expected_cycle = {
        "format_version": "1",
        "experiment": EXPERIMENT,
        "candidate_label": "AI",
        "target": TARGET,
        "identity_relative": IDENTITY_RELATIVE,
        "ssh_batch_mode": "yes",
        "ssh_identities_only": "yes",
        "ssh_identity_agent": "none",
        "ssh_strict_host_key_checking": "yes",
        "one_cycle_attempt": "yes",
        "disconnect_probe_failures_required": "2",
        "pre_snapshot_confirmed": "yes",
        "disconnect_confirmed": "yes",
        "reconnect_confirmed": "yes",
        "post_snapshot_confirmed": "yes",
        "boot_id_changed": "yes",
        "installed_full_sha256_input": expected_installed_full_sha256,
        "installed_hash_basis": "caller-supplied-prior-full-partition-readback",
        "installed_hash_reverified_during_recovery": "no",
        "reboot_command_issued": "no",
        "device_write_operations": "none",
        "device_partition_reads": "none",
        "remote_pstore_delete_operations": "none",
        "raw_collect_device_pstore_primitive_used": "no",
    }
    for key, value in expected_cycle.items():
        if cycle[key] != value:
            raise ValueError(f"cycle contract changed: {key}")
    wait_seconds = parse_positive_integer(cycle["wait_seconds"], "cycle wait", minimum=1200)
    if wait_seconds > 86400:
        raise ValueError("cycle wait exceeds the one-day bound")
    if HEX256.fullmatch(cycle["initial_boot_id_sha256"]) is None or HEX256.fullmatch(
        cycle["final_boot_id_sha256"]
    ) is None:
        raise ValueError("recovery boot ID checksum is malformed")
    if cycle["initial_boot_id_sha256"] == cycle["final_boot_id_sha256"]:
        raise ValueError("recovery boot ID did not change")
    for key in (
        "cycle_started_utc",
        "pre_snapshot_utc",
        "disconnect_observed_utc",
        "reconnect_observed_utc",
        "post_snapshot_utc",
    ):
        if UTC.fullmatch(cycle[key]) is None:
            raise ValueError(f"cycle timestamp is malformed: {key}")
    epochs = [
        parse_positive_integer(cycle[key], key)
        for key in (
            "cycle_started_epoch",
            "pre_snapshot_epoch",
            "disconnect_observed_epoch",
            "reconnect_observed_epoch",
            "post_snapshot_epoch",
        )
    ]
    if epochs != sorted(epochs):
        raise ValueError("cycle epochs are not monotonic")

    pre = validate_snapshot(root / "pre", "pre")
    post = validate_snapshot(root / "post", "post")
    if pre.state["boot_id_sha256"] != cycle["initial_boot_id_sha256"]:
        raise ValueError("pre snapshot is not bound to the initial recovery boot")
    if post.state["boot_id_sha256"] != cycle["final_boot_id_sha256"]:
        raise ValueError("post snapshot is not bound to the final recovery boot")

    runtime_requested = cycle["runtime_capture_requested"]
    if runtime_requested not in ("yes", "no"):
        raise ValueError("runtime-capture request state is malformed")
    runtime_path = root / "candidate-ai-runtime.txt"
    runtime_validation_path = root / "runtime-validation.txt"
    if runtime_requested == "yes":
        runtime_data = read_regular(runtime_path, "Candidate AI runtime companion", 2 * 1024 * 1024)
        runtime_validation = read_regular(
            runtime_validation_path, "Candidate AI runtime validation"
        ).decode("utf-8", errors="strict")
        if "validation=candidate-ai-runtime-attribution\n" not in runtime_validation:
            raise ValueError("Candidate AI runtime validation record is absent")
        runtime_validator = load_runtime_validator(pathlib.Path(__file__).resolve().parent)
        runtime_text = runtime_data.decode("utf-8", errors="strict")
        runtime_validator.validate(runtime_text, expected_installed_full_sha256)
        candidate_boot_id = extract_runtime_boot_id(runtime_validator, runtime_text)
        if cycle["candidate_boot_id"] != candidate_boot_id:
            raise ValueError("cycle record changed the exact Candidate AI boot ID")
        candidate_boot_id_sha256 = digest_bytes((candidate_boot_id + "\n").encode())
        if cycle["candidate_boot_id_sha256"] != candidate_boot_id_sha256:
            raise ValueError("cycle record changed the Candidate AI boot ID checksum")
        if candidate_boot_id_sha256 in {
            cycle["initial_boot_id_sha256"],
            cycle["final_boot_id_sha256"],
        }:
            raise ValueError("candidate boot ID equals a recovery boot ID")
        runtime_mtime = parse_positive_integer(
            cycle["runtime_source_mtime_epoch"], "runtime source mtime"
        )
        if not epochs[1] <= runtime_mtime <= epochs[3] + 1:
            raise ValueError("runtime companion was not created during the observed cycle")
        if cycle["candidate_ai_attribution"] != "exact-runtime-companion":
            raise ValueError("exact Candidate AI attribution state changed")
        if cycle["classification"] != "ATTRIBUTED":
            raise ValueError("attributed recovery classification changed")
        attribution = "exact-runtime-companion"
        classification = "ATTRIBUTED"
    else:
        if runtime_path.exists() or runtime_path.is_symlink() or runtime_validation_path.exists():
            raise ValueError("unexpected runtime companion exists")
        if (
            cycle["runtime_source_mtime_epoch"] != "unavailable"
            or cycle["candidate_boot_id"] != "unavailable"
            or cycle["candidate_boot_id_sha256"] != "unavailable"
            or cycle["candidate_ai_attribution"] != "absent"
            or cycle["classification"] != "INCONCLUSIVE"
        ):
            raise ValueError("no-runtime recovery classification changed")
        candidate_boot_id = "unavailable"
        attribution = "absent"
        classification = "INCONCLUSIVE"

    (
        unique_files,
        stale_files,
        unique_lines,
        generic_lines,
        restart_request,
        restarting_system,
        delta_lines,
    ) = compare_pstore(pre, post)

    delta_path = root / "pstore-delta.tsv"
    expected_delta = "".join(line + "\n" for line in delta_lines)
    if write_delta:
        if not allow_unfinalized:
            raise ValueError("--write-delta requires --allow-unfinalized")
        if delta_path.exists() or delta_path.is_symlink():
            raise ValueError("refusing to overwrite pstore delta")
        descriptor = os.open(delta_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="ascii", newline="") as stream:
                stream.write(expected_delta)
        except BaseException:
            try:
                delta_path.unlink()
            except OSError:
                pass
            raise

    expected_top = {"cycle.env", "pre", "post", "pstore-delta.tsv"}
    if runtime_requested == "yes":
        expected_top |= {"candidate-ai-runtime.txt", "runtime-validation.txt"}
    if not allow_unfinalized:
        expected_top |= {"validation.txt", "SHA256SUMS"}
    actual_top = {entry.name for entry in os.scandir(root)}
    if actual_top != expected_top:
        raise ValueError("recovery evidence top-level inventory changed")
    delta_data = read_regular(root / "pstore-delta.tsv", "pstore delta").decode(
        "ascii", errors="strict"
    )
    if delta_data != expected_delta:
        raise ValueError("pstore delta record differs from pre/post content")
    if not allow_unfinalized:
        validation_text = read_regular(root / "validation.txt", "validation record").decode(
            "utf-8", errors="strict"
        )
        if f"classification={classification}\n" not in validation_text:
            raise ValueError("validation record classification changed")
        validate_manifest(root)

    return ValidationResult(
        classification=classification,
        candidate_ai_attribution=attribution,
        candidate_boot_id=candidate_boot_id,
        post_unique_content_files=unique_files,
        post_stale_or_unchanged_files=stale_files,
        post_lines_not_seen_pre=unique_lines,
        generic_lineage_token_lines=generic_lines,
        restart_request_line_new=restart_request,
        restarting_system_line_new=restarting_system,
        delta_lines=delta_lines,
    )


def emit(result: ValidationResult) -> None:
    print("validation=candidate-ai-recovery-evidence")
    print("recovery_kernel=3.18.41+")
    print("recovery_root=/dev/mmcblk0p29")
    print("pre_snapshot=confirmed")
    print("disconnect=confirmed")
    print("reconnect=confirmed")
    print("recovery_boot_id_changed=yes")
    print("pstore_pre_post_content_comparison=passed")
    print(f"post_unique_content_files={result.post_unique_content_files}")
    print(f"post_stale_or_unchanged_files={result.post_stale_or_unchanged_files}")
    print(f"post_lines_not_seen_pre={result.post_lines_not_seen_pre}")
    print(f"generic_lineage_token_lines={result.generic_lineage_token_lines}")
    print("generic_candidate_l_ac_ab_identity_weight=zero")
    print(
        "new_inherited_ab_restart_request_line="
        + ("present" if result.restart_request_line_new else "absent")
    )
    print(
        "new_kernel_restarting_system_line="
        + ("present" if result.restarting_system_line_new else "absent")
    )
    print(f"candidate_ai_attribution={result.candidate_ai_attribution}")
    print(f"candidate_boot_id={result.candidate_boot_id}")
    print(f"classification={result.classification}")
    print("remote_pstore_deletion=none")
    print("reboot_command=none")
    print("device_write_operations=none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=pathlib.Path, required=True)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    parser.add_argument("--allow-unfinalized", action="store_true")
    parser.add_argument("--write-delta", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_evidence(
            args.evidence,
            args.expected_installed_full_sha256,
            allow_unfinalized=args.allow_unfinalized,
            write_delta=args.write_delta,
        )
        emit(result)
        return 0
    except (OSError, UnicodeError, ValueError, KeyError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
