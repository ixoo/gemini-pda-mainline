#!/usr/bin/env python3
"""Synthetic mutation tests for AJ recovery classification and time binding."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import os
import pathlib
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True

PRE_BOOT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
POST_BOOT = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def load(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def private(path: pathlib.Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(0o600)


def text(path: pathlib.Path, value: str) -> None:
    private(path, value.encode())


def boot_digest(value: str) -> str:
    return digest((value + "\n").encode())


def snapshot(root: pathlib.Path, phase: str, boot_id: str, contents: dict[str, bytes]) -> None:
    directory = root / phase
    pstore = directory / "pstore"
    pstore.mkdir(parents=True, mode=0o700)
    directory.chmod(0o700)
    pstore.chmod(0o700)
    text(
        directory / "state.env",
        f"capture_phase={phase}\nkernel=3.18.41+\narchitecture=aarch64\n"
        f"root_source=/dev/mmcblk0p29\nboot_id_sha256={boot_digest(boot_id)}\n"
        "pstore_directory=present\n",
    )
    inventory: list[str] = []
    members: list[str] = []
    for name, data in sorted(contents.items()):
        private(pstore / name, data)
        inventory.append(f"{digest(data)}\t{len(data)}\t{name}\n")
        members.append(f"./{name}\n")
    text(directory / "pstore-inventory.tsv", "".join(inventory))
    text(directory / "pstore-members.txt", "".join(members))
    archive = directory / "pstore.tar"
    with tarfile.open(archive, "w", format=tarfile.USTAR_FORMAT) as handle:
        for name, data in sorted(contents.items()):
            member = tarfile.TarInfo(f"./{name}")
            member.mode = 0o600
            member.mtime = 0
            member.size = len(data)
            handle.addfile(member, io.BytesIO(data))
    archive.chmod(0o600)


def cycle(runtime_status: str, native_status: str, runtime_mtime: str, native_mtime: str) -> dict[str, str]:
    external = {"valid": "exact-validated-companion", "invalid": "invalid-companion", "absent": "absent"}[native_status]
    return {
        "format_version": "2", "experiment": "2026-07-22-a72-reject-cpu8-request",
        "candidate_label": "AJ", "target": "gemini@192.168.1.50",
        "identity_relative": "artifacts/credentials/gemini_ed25519",
        "ssh_batch_mode": "yes", "ssh_identities_only": "yes",
        "ssh_identity_agent": "none", "ssh_strict_host_key_checking": "yes",
        "wait_seconds": "1200", "one_cycle_attempt": "yes",
        "disconnect_probe_failures_required": "2", "pre_snapshot_confirmed": "yes",
        "disconnect_confirmed": "yes", "reconnect_confirmed": "yes",
        "post_snapshot_confirmed": "yes", "boot_id_changed": "yes",
        "initial_boot_id_sha256": boot_digest(PRE_BOOT),
        "final_boot_id_sha256": boot_digest(POST_BOOT),
        "cycle_started_utc": "2026-07-22T00:00:00Z",
        "pre_snapshot_utc": "2026-07-22T00:00:01Z",
        "disconnect_observed_utc": "2026-07-22T00:00:02Z",
        "reconnect_observed_utc": "2026-07-22T00:00:03Z",
        "post_snapshot_utc": "2026-07-22T00:00:04Z",
        "cycle_started_epoch": "100", "pre_snapshot_epoch": "101",
        "disconnect_observed_epoch": "102", "reconnect_observed_epoch": "103",
        "post_snapshot_epoch": "104",
        "installed_full_sha256_input": "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257",
        "installed_hash_basis": "caller-supplied-prior-full-partition-readback",
        "installed_hash_reverified_during_recovery": "no",
        "runtime_capture_planned": "yes", "runtime_companion_status": runtime_status,
        "runtime_companion_preserved": "no" if runtime_status == "absent" else "yes",
        "runtime_source_mtime_epoch": runtime_mtime,
        "native_reboot_capture_planned": "yes", "native_reboot_companion_status": native_status,
        "native_reboot_companion_preserved": "no" if native_status == "absent" else "yes",
        "native_reboot_source_mtime_epoch": native_mtime,
        "collector_reboot_command_issued": "no",
        "external_reboot_evidence_status": external,
        "device_write_operations": "none", "device_partition_reads": "none",
        "remote_pstore_delete_operations": "none",
        "raw_collect_device_pstore_primitive_used": "no",
    }


def make(
    root: pathlib.Path,
    validator: object,
    runtime_tests: object,
    native_tests: object,
    *,
    runtime_status: str,
    native_status: str = "absent",
    signatures: bool = True,
    duplicate_gate: bool = False,
    runtime_mtime: int = 102,
    native_mtime: int = 103,
) -> None:
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    pre = {"console-ramoops": b"old recovery record\n"}
    post_data = bytearray(b"old recovery record\n")
    if signatures:
        post_data.extend(f"Kernel command line: {validator.AJ.CMDLINE}\n".encode())
        post_data.extend(b"mt6797-psci: CPU8 boot rejected: A72 power sequence inactive\n")
        if duplicate_gate:
            post_data.extend(b"mt6797-psci: CPU8 boot rejected: A72 power sequence inactive\n")
        post_data.extend(b"CPU8: failed to boot: -11\n")
    if native_status == "valid":
        post_data.extend(b"Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n")
        post_data.extend(b"reboot: Restarting system\n")
    post = {"console-ramoops": bytes(post_data)}
    snapshot(root, "pre", PRE_BOOT, pre)
    snapshot(root, "post", POST_BOOT, post)
    recorded_native_mtime: int | str = native_mtime if native_status != "absent" else "unavailable"
    values = cycle(
        runtime_status,
        native_status,
        str(runtime_mtime) if runtime_status != "absent" else "unavailable",
        str(recorded_native_mtime),
    )
    text(root / "cycle.env", "".join(f"{key}={value}\n" for key, value in values.items()))
    text(root / "runtime-validation.txt", f"status={runtime_status}\nsynthetic=yes\n")
    text(root / "native-reboot-validation.txt", f"status={native_status}\nsynthetic=yes\n")
    runtime_text = ""
    if runtime_status != "absent":
        runtime_text = runtime_tests.fixture(validator.RUNTIME)
        if runtime_status == "invalid":
            runtime_text = runtime_text.replace(validator.RUNTIME.EXPECTED_CONFIG_SHA256, "0" * 64, 1)
        runtime_path = root / "candidate-aj-runtime.txt"
        text(runtime_path, runtime_text)
        os.utime(runtime_path, (runtime_mtime, runtime_mtime))
    if native_status != "absent":
        valid_runtime = runtime_tests.fixture(validator.RUNTIME)
        boot_id = validator.NATIVE.runtime_boot_id(valid_runtime, validator.AJ.PADDED_SHA256)
        native_text = native_tests.fixture(validator.NATIVE, valid_runtime, boot_id)
        native_path = root / "candidate-aj-native-reboot.txt"
        text(native_path, native_text)
        os.utime(native_path, (native_mtime, native_mtime))
    validator.validate_evidence(
        root, validator.AJ.PADDED_SHA256, allow_unfinalized=True, write_derived=True
    )


def finalize(validator: object, root: pathlib.Path) -> None:
    result = validator.validate_evidence(root, validator.AJ.PADDED_SHA256, allow_unfinalized=True)
    rendered = io.StringIO()
    with contextlib.redirect_stdout(rendered):
        validator.emit(result)
    text(root / "validation.txt", rendered.getvalue())
    records: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            records.append(f"{digest(path.read_bytes())}  ./{path.relative_to(root).as_posix()}\n")
    text(root / "SHA256SUMS", "".join(records))


def main() -> int:
    script_dir = pathlib.Path(__file__).resolve().parent
    validator = load(script_dir / "validate-recovery-evidence.py", "aj_recovery_test_validator")
    runtime_tests = load(script_dir / "test-runtime-validator.py", "aj_recovery_runtime_fixture")
    native_tests = load(script_dir / "test-native-reboot-validator.py", "aj_recovery_native_fixture")
    with tempfile.TemporaryDirectory(prefix="candidate-aj-recovery-test-") as temporary:
        base = pathlib.Path(temporary)
        partial = base / "partial"
        make(partial, validator, runtime_tests, native_tests, runtime_status="absent")
        result = validator.validate_evidence(partial, validator.AJ.PADDED_SHA256, allow_unfinalized=True)
        if result.classification != "ATTRIBUTED_PARTIAL" or result.attribution != "unique-exact-aj-pstore-signatures":
            raise ValueError("exact unique AJ pstore triplet did not produce ATTRIBUTED_PARTIAL")
        finalize(validator, partial)
        validator.validate_evidence(partial, validator.AJ.PADDED_SHA256)

        invalid = base / "invalid-runtime"
        make(invalid, validator, runtime_tests, native_tests, runtime_status="invalid")
        result = validator.validate_evidence(invalid, validator.AJ.PADDED_SHA256, allow_unfinalized=True)
        if result.classification != "ATTRIBUTED_PARTIAL":
            raise ValueError("invalid preserved runtime destroyed exact pstore partial attribution")

        duplicate = base / "duplicate-signature"
        make(duplicate, validator, runtime_tests, native_tests, runtime_status="absent", duplicate_gate=True)
        result = validator.validate_evidence(duplicate, validator.AJ.PADDED_SHA256, allow_unfinalized=True)
        if result.classification != "INCONCLUSIVE" or result.cpu8_gate_count != 2:
            raise ValueError("duplicated pstore signature incorrectly produced partial attribution")

        attributed = base / "attributed"
        make(attributed, validator, runtime_tests, native_tests, runtime_status="valid")
        result = validator.validate_evidence(attributed, validator.AJ.PADDED_SHA256, allow_unfinalized=True)
        if result.classification != "ATTRIBUTED":
            raise ValueError("exact runtime companion did not produce ATTRIBUTED")

        rebooted = base / "native-reboot"
        make(rebooted, validator, runtime_tests, native_tests, runtime_status="valid", native_status="valid")
        result = validator.validate_evidence(rebooted, validator.AJ.PADDED_SHA256, allow_unfinalized=True)
        if result.native_reboot_subgate != "passed":
            raise ValueError("exact external native reboot evidence did not pass its subgate")

        stale = base / "stale-runtime"
        try:
            make(stale, validator, runtime_tests, native_tests, runtime_status="valid", runtime_mtime=101)
        except (OSError, UnicodeError, ValueError, KeyError, OverflowError):
            pass
        else:
            raise ValueError("runtime mtime before observed disconnect unexpectedly passed")

        late_runtime = base / "late-runtime"
        try:
            make(late_runtime, validator, runtime_tests, native_tests, runtime_status="valid", runtime_mtime=104)
        except (OSError, UnicodeError, ValueError, KeyError, OverflowError):
            pass
        else:
            raise ValueError("runtime mtime at reconnect+1 unexpectedly passed")

        late_native = base / "late-native"
        try:
            make(
                late_native, validator, runtime_tests, native_tests,
                runtime_status="valid", native_status="valid", native_mtime=104,
            )
        except (OSError, UnicodeError, ValueError, KeyError, OverflowError):
            pass
        else:
            raise ValueError("native reboot mtime at reconnect+1 unexpectedly passed")

    print("validation=candidate-aj-recovery-evidence-mutations")
    print("runtime_window=disconnect-through-reconnect-only")
    print("missing_and_invalid_runtime=published-classifiable")
    print("unique_exact_aj_pstore_triplet=ATTRIBUTED_PARTIAL")
    print("duplicate_exact_signature=INCONCLUSIVE")
    print("external_native_reboot_subgate=separate-and-passed")
    print("collector_reboot_command_issued=no")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
