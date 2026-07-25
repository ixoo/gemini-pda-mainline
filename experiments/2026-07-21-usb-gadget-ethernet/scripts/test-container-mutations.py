#!/usr/bin/env python3
"""Prove coherent Candidate AC container mutations are rejected."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile

from ac_contract import AC_BOOT_FILE, AC_DTB_FILE, AC_INITRAMFS_FILE, digest_path


PAGE_SIZE = 2048


def run_validator(
    validator: pathlib.Path,
    artifact: pathlib.Path,
    baseline: pathlib.Path,
    expected_status: int,
) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            os.fspath(validator),
            "--artifact",
            os.fspath(artifact),
            "--baseline",
            os.fspath(baseline),
        ],
        check=False,
        capture_output=True,
        env=environment,
    )
    if completed.returncode != expected_status:
        raise ValueError(
            f"validator returned {completed.returncode}, expected {expected_status}: "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    if expected_status and b"error:" not in completed.stderr:
        raise ValueError("mutation rejection did not provide a fail-closed error")


def copy_artifact(source: pathlib.Path, parent: pathlib.Path, label: str) -> pathlib.Path:
    case = parent / label
    case.mkdir(mode=0o700)
    destination = case / source.name
    shutil.copytree(source, destination, copy_function=shutil.copy2)
    os.chmod(destination, 0o700)
    return destination


def flip(data: bytes, offset: int) -> bytes:
    if not 0 <= offset < len(data):
        raise ValueError("mutation offset is outside file")
    result = bytearray(data)
    result[offset] ^= 0x01
    return bytes(result)


def update_provenance(path: pathlib.Path, updates: dict[str, str]) -> None:
    output: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if not separator:
            raise ValueError("malformed provenance fixture")
        if key in updates:
            value = updates[key]
            seen.add(key)
        output.append(f"{key}={value}")
    if seen != set(updates):
        raise ValueError(f"provenance fixture lacks fields: {sorted(set(updates) - seen)}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def refresh_boot_id(boot_path: pathlib.Path) -> None:
    boot = bytearray(boot_path.read_bytes())
    fields = struct.unpack_from("<10I", boot, 8)
    kernel_size, _kernel_addr, ramdisk_size = fields[:3]
    second_size, page_size = fields[4], fields[7]
    if page_size != PAGE_SIZE or second_size:
        raise ValueError("unexpected Android-v0 fixture layout")
    kernel_offset = page_size
    kernel_end = kernel_offset + kernel_size
    ramdisk_offset = (kernel_end + page_size - 1) // page_size * page_size
    ramdisk_end = ramdisk_offset + ramdisk_size
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (boot[kernel_offset:kernel_end], boot[ramdisk_offset:ramdisk_end], b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    boot[576:596] = image_id.digest()
    boot_path.write_bytes(boot)


def update_boot_payload(
    artifact: pathlib.Path, member: str, payload_offset: int
) -> None:
    member_path = artifact / member
    member_data = member_path.read_bytes()
    index = len(member_data) // 2
    member_path.write_bytes(flip(member_data, index))

    boot_path = artifact / AC_BOOT_FILE
    boot = bytearray(boot_path.read_bytes())
    absolute = payload_offset + index
    boot[absolute] ^= 0x01
    boot_path.write_bytes(boot)
    refresh_boot_id(boot_path)


def rename_for_boot_hash(artifact: pathlib.Path) -> pathlib.Path:
    boot_hash = digest_path(artifact / AC_BOOT_FILE)
    destination = artifact.parent / f"candidate-AC-usb-gadget-ethernet-final-{boot_hash[:8]}"
    artifact.rename(destination)
    return destination


def rewrite_manifest(artifact: pathlib.Path) -> None:
    manifest = artifact / "SHA256SUMS"
    names: list[str] = []
    for entry in artifact.iterdir():
        if entry.name == "SHA256SUMS":
            continue
        if entry.is_symlink() or not entry.is_file():
            raise ValueError(f"unsafe mutation fixture member: {entry.name}")
        names.append(entry.name)
    data = "".join(
        f"{digest_path(artifact / name)}  ./{name}\n" for name in sorted(names)
    )
    manifest.write_text(data, encoding="ascii")


def refresh_dynamic_provenance(artifact: pathlib.Path, extra: dict[str, str]) -> None:
    boot_path = artifact / AC_BOOT_FILE
    updates = {
        "candidate_sha256": digest_path(boot_path),
        "candidate_size": str(boot_path.stat().st_size),
    }
    updates.update(extra)
    update_provenance(artifact / "provenance.txt", updates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if sys.platform != "linux" or os.uname().machine not in {"aarch64", "arm64"}:
            raise ValueError("container mutation tests require Linux aarch64")
        artifact = args.artifact.resolve(strict=True)
        baseline = args.baseline.resolve(strict=True)
        validator = pathlib.Path(__file__).resolve().parent / "validate-final-artifact.py"
        run_validator(validator, artifact, baseline, 0)

        with tempfile.TemporaryDirectory(prefix="candidate-ac-container-mutations.") as raw:
            root = pathlib.Path(raw)

            boot_mutant = copy_artifact(artifact, root, "boot")
            boot_path = boot_mutant / AC_BOOT_FILE
            boot = bytearray(boot_path.read_bytes())
            boot[48] ^= 0x01
            boot_path.write_bytes(boot)
            refresh_dynamic_provenance(boot_mutant, {})
            boot_mutant = rename_for_boot_hash(boot_mutant)
            rewrite_manifest(boot_mutant)
            run_validator(validator, boot_mutant, baseline, 2)

            kernel_mutant = copy_artifact(artifact, root, "kernel")
            update_boot_payload(kernel_mutant, "Image.gz", PAGE_SIZE)
            refresh_dynamic_provenance(
                kernel_mutant,
                {"candidate_image_gz_sha256": digest_path(kernel_mutant / "Image.gz")},
            )
            kernel_mutant = rename_for_boot_hash(kernel_mutant)
            rewrite_manifest(kernel_mutant)
            run_validator(validator, kernel_mutant, baseline, 2)

            dtb_mutant = copy_artifact(artifact, root, "dtb")
            image_size = (dtb_mutant / "Image.gz").stat().st_size
            update_boot_payload(dtb_mutant, AC_DTB_FILE, PAGE_SIZE + image_size)
            refresh_dynamic_provenance(
                dtb_mutant,
                {"candidate_dtb_sha256": digest_path(dtb_mutant / AC_DTB_FILE)},
            )
            dtb_mutant = rename_for_boot_hash(dtb_mutant)
            rewrite_manifest(dtb_mutant)
            run_validator(validator, dtb_mutant, baseline, 2)

            initramfs_mutant = copy_artifact(artifact, root, "initramfs")
            boot_data = (initramfs_mutant / AC_BOOT_FILE).read_bytes()
            kernel_size = struct.unpack_from("<I", boot_data, 8)[0]
            ramdisk_offset = (PAGE_SIZE + kernel_size + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE
            update_boot_payload(initramfs_mutant, AC_INITRAMFS_FILE, ramdisk_offset)
            refresh_dynamic_provenance(
                initramfs_mutant,
                {
                    "candidate_initramfs_sha256": digest_path(
                        initramfs_mutant / AC_INITRAMFS_FILE
                    )
                },
            )
            initramfs_mutant = rename_for_boot_hash(initramfs_mutant)
            rewrite_manifest(initramfs_mutant)
            run_validator(validator, initramfs_mutant, baseline, 2)

            extra_mutant = copy_artifact(artifact, root, "extra-member")
            unexpected = extra_mutant / "unexpected-member"
            unexpected.write_bytes(b"unexpected\n")
            os.chmod(unexpected, 0o600)
            rewrite_manifest(extra_mutant)
            run_validator(validator, extra_mutant, baseline, 2)

            provenance_mutant = copy_artifact(artifact, root, "provenance")
            with (provenance_mutant / "provenance.txt").open(
                "ab"
            ) as stream:
                stream.write(b"mutation=yes\n")
            rewrite_manifest(provenance_mutant)
            run_validator(validator, provenance_mutant, baseline, 2)

        print("validation=candidate-ac-container-mutations")
        print("original_artifact=PASS")
        print("boot_header_coherent_manifest_mutation=REJECTED")
        print("kernel_payload_coherent_boot_manifest_mutation=REJECTED")
        print("dtb_payload_coherent_boot_manifest_mutation=REJECTED")
        print("initramfs_payload_coherent_boot_manifest_mutation=REJECTED")
        print("extra_member_coherent_manifest_mutation=REJECTED")
        print("provenance_coherent_manifest_mutation=REJECTED")
        print("mutation_count=6")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    os.umask(0o077)
    raise SystemExit(main())
