#!/usr/bin/env python3
"""Synthetic and mutation tests for Candidate AI recovery evidence."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import os
import pathlib
import shutil
import stat
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True


INSTALLED_SHA256 = (
    "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
)
PRE_BOOT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
POST_BOOT_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
CANDIDATE_BOOT_ID = "01234567-89ab-cdef-0123-456789abcdef"


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


def private_file(path: pathlib.Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(0o600)


def private_text(path: pathlib.Path, text: str) -> None:
    private_file(path, text.encode("utf-8"))


def boot_digest(boot_id: str) -> str:
    return digest((boot_id + "\n").encode())


def make_snapshot(root: pathlib.Path, phase: str, boot_id: str, files: dict[str, bytes]) -> None:
    snapshot = root / phase
    pstore = snapshot / "pstore"
    pstore.mkdir(parents=True, mode=0o700)
    snapshot.chmod(0o700)
    pstore.chmod(0o700)
    private_text(
        snapshot / "state.env",
        "".join(
            (
                f"capture_phase={phase}\n",
                "kernel=3.18.41+\n",
                "architecture=aarch64\n",
                "root_source=/dev/mmcblk0p29\n",
                f"boot_id_sha256={boot_digest(boot_id)}\n",
                "pstore_directory=present\n",
            )
        ),
    )
    inventory: list[str] = []
    members: list[str] = []
    for name, data in sorted(files.items()):
        private_file(pstore / name, data)
        inventory.append(f"{digest(data)}\t{len(data)}\t{name}\n")
        members.append(f"./{name}\n")
    private_text(snapshot / "pstore-inventory.tsv", "".join(inventory))
    private_text(snapshot / "pstore-members.txt", "".join(members))
    archive_path = snapshot / "pstore.tar"
    with tarfile.open(archive_path, "w", format=tarfile.USTAR_FORMAT) as archive:
        for name, data in sorted(files.items()):
            member = tarfile.TarInfo(f"./{name}")
            member.mode = 0o600
            member.size = len(data)
            member.mtime = 0
            archive.addfile(member, io.BytesIO(data))
    archive_path.chmod(0o600)


def cycle_values(runtime: bool) -> dict[str, str]:
    values = {
        "format_version": "1",
        "experiment": "2026-07-22-a72-reject-gate-kernel-split",
        "candidate_label": "AI",
        "target": "gemini@192.168.1.50",
        "identity_relative": "artifacts/credentials/gemini_ed25519",
        "ssh_batch_mode": "yes",
        "ssh_identities_only": "yes",
        "ssh_identity_agent": "none",
        "ssh_strict_host_key_checking": "yes",
        "wait_seconds": "1200",
        "one_cycle_attempt": "yes",
        "disconnect_probe_failures_required": "2",
        "pre_snapshot_confirmed": "yes",
        "disconnect_confirmed": "yes",
        "reconnect_confirmed": "yes",
        "post_snapshot_confirmed": "yes",
        "boot_id_changed": "yes",
        "initial_boot_id_sha256": boot_digest(PRE_BOOT_ID),
        "final_boot_id_sha256": boot_digest(POST_BOOT_ID),
        "cycle_started_utc": "2026-07-22T00:00:00Z",
        "pre_snapshot_utc": "2026-07-22T00:00:01Z",
        "disconnect_observed_utc": "2026-07-22T00:00:02Z",
        "reconnect_observed_utc": "2026-07-22T00:00:03Z",
        "post_snapshot_utc": "2026-07-22T00:00:04Z",
        "cycle_started_epoch": "100",
        "pre_snapshot_epoch": "101",
        "disconnect_observed_epoch": "102",
        "reconnect_observed_epoch": "103",
        "post_snapshot_epoch": "104",
        "installed_full_sha256_input": INSTALLED_SHA256,
        "installed_hash_basis": "caller-supplied-prior-full-partition-readback",
        "installed_hash_reverified_during_recovery": "no",
        "runtime_capture_requested": "yes" if runtime else "no",
        "runtime_source_mtime_epoch": "102" if runtime else "unavailable",
        "candidate_boot_id": CANDIDATE_BOOT_ID if runtime else "unavailable",
        "candidate_boot_id_sha256": (
            boot_digest(CANDIDATE_BOOT_ID) if runtime else "unavailable"
        ),
        "candidate_ai_attribution": "exact-runtime-companion" if runtime else "absent",
        "classification": "ATTRIBUTED" if runtime else "INCONCLUSIVE",
        "reboot_command_issued": "no",
        "device_write_operations": "none",
        "device_partition_reads": "none",
        "remote_pstore_delete_operations": "none",
        "raw_collect_device_pstore_primitive_used": "no",
    }
    return values


def write_cycle(root: pathlib.Path, values: dict[str, str]) -> None:
    private_text(root / "cycle.env", "".join(f"{key}={value}\n" for key, value in values.items()))


def write_delta(root: pathlib.Path, pre: dict[str, bytes], post: dict[str, bytes]) -> None:
    pre_inventory = {
        name: (digest(data), len(data)) for name, data in sorted(pre.items())
    }
    pre_hashes = {value[0] for value in pre_inventory.values()}
    lines: list[str] = []
    for name, data in sorted(post.items()):
        post_hash = digest(data)
        post_size = len(data)
        before = pre_inventory.get(name)
        if before == (post_hash, post_size):
            relation = "unchanged-same-name"
        elif post_hash in pre_hashes:
            relation = "stale-content-renamed"
        else:
            relation = "unique-post-content"
        pre_hash = before[0] if before is not None else "absent"
        lines.append(f"{relation}\t{name}\t{pre_hash}\t{post_hash}\t{post_size}\n")
    for name, (pre_hash, pre_size) in sorted(pre_inventory.items()):
        if name not in post:
            lines.append(f"removed-after-cycle\t{name}\t{pre_hash}\tabsent\t{pre_size}\n")
    private_text(root / "pstore-delta.tsv", "".join(lines))


def runtime_fixture(script_dir: pathlib.Path) -> str:
    runtime_validator = load(script_dir / "validate-runtime.py", "ai_runtime_for_recovery")
    runtime_tests = load(script_dir / "test-runtime-validator.py", "ai_runtime_fixture")
    return runtime_tests.fixture(runtime_validator)


def build_fixture(root: pathlib.Path, script_dir: pathlib.Path, *, runtime: bool) -> None:
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    stale = b"old retained record\n"
    old_console = b"GEMINI_OBSERVABILITY_20260717_L old pre-cycle lineage\n"
    new_console = old_console + (
        b"GEMINI_OBSERVABILITY_20260717_L new inherited lineage only\n"
        b"GEMINI_USB_GADGET_ETHERNET_20260721_AC inherited only\n"
        b"GEMINI_MT6797_KERNEL_RESTART_20260720_AB inherited only\n"
        b"Candidate AB: kernel restart requested now (BusyBox reboot -n -f).\n"
        b"reboot: Restarting system\n"
    )
    pre = {
        "console-ramoops": old_console,
        "dmesg-ramoops-0": stale,
    }
    post = {
        "console-ramoops": new_console,
        "dmesg-ramoops-0": stale,
        "dmesg-ramoops-1": stale,
    }
    make_snapshot(root, "pre", PRE_BOOT_ID, pre)
    make_snapshot(root, "post", POST_BOOT_ID, post)
    write_cycle(root, cycle_values(runtime))
    write_delta(root, pre, post)
    if runtime:
        private_text(root / "candidate-ai-runtime.txt", runtime_fixture(script_dir))
        private_text(
            root / "runtime-validation.txt",
            "validation=candidate-ai-runtime-attribution\n",
        )


def rewrite_env(path: pathlib.Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = 0
    output: list[str] = []
    for line in lines:
        if line.startswith(key + "="):
            output.append(f"{key}={value}")
            changed += 1
        else:
            output.append(line)
    if changed != 1:
        raise ValueError(f"fixture key is absent or duplicated: {key}")
    private_text(path, ("\n".join(output) + "\n"))


def expect_rejected(
    validator: object,
    root: pathlib.Path,
    expected_hash: str = INSTALLED_SHA256,
) -> None:
    try:
        validator.validate_evidence(root, expected_hash, allow_unfinalized=True)
    except (OSError, UnicodeError, ValueError, KeyError, OverflowError):
        return
    raise ValueError("recovery evidence mutation unexpectedly passed")


def finalize(validator: object, root: pathlib.Path) -> None:
    result = validator.validate_evidence(root, INSTALLED_SHA256, allow_unfinalized=True)
    rendered = io.StringIO()
    with contextlib.redirect_stdout(rendered):
        validator.emit(result)
    private_text(root / "validation.txt", rendered.getvalue())
    entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            entries.append(f"{digest(path.read_bytes())}  ./{path.relative_to(root).as_posix()}\n")
    private_text(root / "SHA256SUMS", "".join(entries))


def main() -> int:
    script_dir = pathlib.Path(__file__).resolve().parent
    validator = load(script_dir / "validate-recovery-evidence.py", "ai_recovery_validator")
    with tempfile.TemporaryDirectory(prefix="candidate-ai-recovery-validator-") as temporary:
        base = pathlib.Path(temporary)

        inconclusive = base / "inconclusive"
        build_fixture(inconclusive, script_dir, runtime=False)
        result = validator.validate_evidence(
            inconclusive, INSTALLED_SHA256, allow_unfinalized=True
        )
        if result.classification != "INCONCLUSIVE" or result.candidate_ai_attribution != "absent":
            raise ValueError("generic inherited markers incorrectly identified Candidate AI")
        if result.generic_lineage_token_lines < 3:
            raise ValueError("generic inherited marker fixture was not exercised")
        if result.post_unique_content_files != 1 or result.post_stale_or_unchanged_files != 2:
            raise ValueError("stale-content comparison fixture changed")
        if not result.restart_request_line_new or not result.restarting_system_line_new:
            raise ValueError("new orderly-restart fixture lines were not detected")
        finalize(validator, inconclusive)
        validator.validate_evidence(inconclusive, INSTALLED_SHA256)

        attributed = base / "attributed"
        build_fixture(attributed, script_dir, runtime=True)
        result = validator.validate_evidence(
            attributed, INSTALLED_SHA256, allow_unfinalized=True
        )
        if result.classification != "ATTRIBUTED" or result.candidate_boot_id != CANDIDATE_BOOT_ID:
            raise ValueError("exact Candidate AI runtime companion was not bound")
        finalize(validator, attributed)
        validator.validate_evidence(attributed, INSTALLED_SHA256)

        mutations = 0

        def mutation(name: str, runtime: bool = False) -> pathlib.Path:
            nonlocal mutations
            mutations += 1
            path = base / f"mutation-{mutations:02d}-{name}"
            build_fixture(path, script_dir, runtime=runtime)
            return path

        cases: list[pathlib.Path] = []
        path = mutation("wrong-installed-image")
        rewrite_env(path / "cycle.env", "installed_full_sha256_input", "b" * 64)
        expect_rejected(validator, path, "b" * 64)
        path = mutation("short-wait")
        rewrite_env(path / "cycle.env", "wait_seconds", "1199")
        cases.append(path)
        path = mutation("accept-new")
        rewrite_env(path / "cycle.env", "ssh_strict_host_key_checking", "accept-new")
        cases.append(path)
        path = mutation("wrong-target")
        rewrite_env(path / "cycle.env", "target", "gemini@example.invalid")
        cases.append(path)
        path = mutation("identity-agent")
        rewrite_env(path / "cycle.env", "ssh_identity_agent", "SSH_AUTH_SOCK")
        cases.append(path)
        path = mutation("same-boot")
        rewrite_env(path / "cycle.env", "final_boot_id_sha256", boot_digest(PRE_BOOT_ID))
        cases.append(path)
        path = mutation("boot-change-unconfirmed")
        rewrite_env(path / "cycle.env", "boot_id_changed", "no")
        cases.append(path)
        path = mutation("disconnect-unconfirmed")
        rewrite_env(path / "cycle.env", "disconnect_confirmed", "no")
        cases.append(path)
        path = mutation("reconnect-unconfirmed")
        rewrite_env(path / "cycle.env", "reconnect_confirmed", "no")
        cases.append(path)
        path = mutation("pre-unconfirmed")
        rewrite_env(path / "cycle.env", "pre_snapshot_confirmed", "no")
        cases.append(path)
        path = mutation("write-claimed")
        rewrite_env(path / "cycle.env", "device_write_operations", "one")
        cases.append(path)
        path = mutation("partition-read")
        rewrite_env(path / "cycle.env", "device_partition_reads", "boot2")
        cases.append(path)
        path = mutation("pstore-delete")
        rewrite_env(path / "cycle.env", "remote_pstore_delete_operations", "one")
        cases.append(path)
        path = mutation("reboot-command")
        rewrite_env(path / "cycle.env", "reboot_command_issued", "yes")
        cases.append(path)
        path = mutation("wrong-kernel")
        rewrite_env(path / "post/state.env", "kernel", "3.18.41")
        cases.append(path)
        path = mutation("wrong-root")
        rewrite_env(path / "post/state.env", "root_source", "/dev/mmcblk0p30")
        cases.append(path)
        path = mutation("wrong-phase")
        rewrite_env(path / "pre/state.env", "capture_phase", "post")
        cases.append(path)
        path = mutation("delta-tamper")
        private_text(path / "pstore-delta.tsv", "")
        cases.append(path)
        path = mutation("archive-tamper")
        private_file(path / "post/pstore.tar", b"not a tar archive\n")
        cases.append(path)
        path = mutation("private-mode")
        os.chmod(path / "pre/state.env", 0o644)
        cases.append(path)
        path = mutation("symlink")
        (path / "post/pstore/console-ramoops").unlink()
        (path / "post/pstore/console-ramoops").symlink_to("dmesg-ramoops-0")
        cases.append(path)
        path = mutation("runtime-missing", runtime=True)
        (path / "candidate-ai-runtime.txt").unlink()
        cases.append(path)
        path = mutation("runtime-invalid", runtime=True)
        runtime_path = path / "candidate-ai-runtime.txt"
        private_text(
            runtime_path,
            runtime_path.read_text(encoding="utf-8").replace(
                validator.load_runtime_validator(script_dir).EXPECTED_CONFIG_SHA256,
                "0" * 64,
                1,
            ),
        )
        cases.append(path)
        path = mutation("runtime-boot-id", runtime=True)
        rewrite_env(
            path / "cycle.env",
            "candidate_boot_id",
            "11234567-89ab-cdef-0123-456789abcdef",
        )
        cases.append(path)
        path = mutation("runtime-outside-cycle", runtime=True)
        rewrite_env(path / "cycle.env", "runtime_source_mtime_epoch", "99")
        cases.append(path)
        path = mutation("runtime-faked-classification")
        rewrite_env(path / "cycle.env", "runtime_capture_requested", "yes")
        rewrite_env(path / "cycle.env", "candidate_ai_attribution", "exact-runtime-companion")
        rewrite_env(path / "cycle.env", "classification", "ATTRIBUTED")
        cases.append(path)

        for path in cases:
            expect_rejected(validator, path)

    print("validation=candidate-ai-recovery-evidence-mutations")
    print("inconclusive_without_exact_ai_runtime=passed")
    print("generic_candidate_l_ac_ab_identity_weight=zero")
    print("exact_runtime_companion_boot_id_binding=passed")
    print("pre_post_inventory_content_comparison=passed")
    print("stale_renamed_content_not_unique=passed")
    print("private_modes=0700-directories-0600-files")
    print(f"mutations_rejected={mutations}")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
