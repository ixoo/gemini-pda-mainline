#!/usr/bin/env python3
"""Require Candidate AB validators to reject focused corruptions."""

from __future__ import annotations

import argparse
from dataclasses import replace
import gzip
import hashlib
import importlib.util
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile

from ab_contract import read_regular


_VALIDATOR_PATH = pathlib.Path(__file__).resolve().parent / "validate-initramfs.py"
_SPEC = importlib.util.spec_from_file_location("candidate_ab_validate_initramfs", _VALIDATOR_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AB initramfs validator")
_INITRAMFS_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _INITRAMFS_MODULE
_SPEC.loader.exec_module(_INITRAMFS_MODULE)
Member = _INITRAMFS_MODULE.Member
parse_newc = _INITRAMFS_MODULE.parse_newc


def run(command: list[str], expected: int) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, capture_output=True, check=False, env=environment)
    if result.returncode != expected:
        raise RuntimeError(
            f"unexpected status {result.returncode}, expected {expected}: {command}\n"
            f"stdout={result.stdout.decode(errors='replace')}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )


def flip(data: bytes, offset: int) -> bytes:
    result = bytearray(data)
    result[offset] ^= 0x01
    return bytes(result)


def pad4(data: bytearray) -> None:
    data.extend(b"\0" * ((-len(data)) & 3))


def encode_newc(members: dict[str, Member]) -> bytes:
    raw = bytearray()
    for inode, name in enumerate(sorted(members), 1):
        member = members[name]
        encoded_name = name.encode("utf-8") + b"\0"
        fields = (
            inode,
            member.mode,
            member.uid,
            member.gid,
            member.nlink,
            member.mtime,
            len(member.data),
            member.devmajor,
            member.devminor,
            member.rdevmajor,
            member.rdevminor,
            len(encoded_name),
            0,
        )
        raw.extend(b"070701" + b"".join(f"{value:08x}".encode("ascii") for value in fields))
        raw.extend(encoded_name)
        pad4(raw)
        raw.extend(member.data)
        pad4(raw)
    trailer = b"TRAILER!!!\0"
    fields = (len(members) + 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, len(trailer), 0)
    raw.extend(b"070701" + b"".join(f"{value:08x}".encode("ascii") for value in fields))
    raw.extend(trailer)
    pad4(raw)
    compressed = bytearray(gzip.compress(bytes(raw), compresslevel=9, mtime=0))
    compressed[9] = 3  # gzip -n on Linux records Unix as the originating OS.
    return bytes(compressed)


def write_manifest(artifact: pathlib.Path) -> None:
    lines: list[str] = []
    for path in sorted(artifact.iterdir(), key=lambda item: item.name):
        if path.name == "SHA256SUMS":
            continue
        if not path.is_file() or path.is_symlink():
            raise ValueError("mutation artifact contains non-regular entry")
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{checksum}  ./{path.name}\n")
    manifest = artifact / "SHA256SUMS"
    manifest.write_text("".join(lines), encoding="ascii")
    manifest.chmod(0o600)


def copy_artifact(source: pathlib.Path, parent: pathlib.Path, label: str) -> pathlib.Path:
    destination = parent / label / source.name
    destination.parent.mkdir(mode=0o700)
    shutil.copytree(source, destination, copy_function=shutil.copy2)
    destination.chmod(0o700)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    args = parser.parse_args()
    script_dir = pathlib.Path(__file__).resolve().parent
    experiment_dir = script_dir.parent
    python = sys.executable
    final_validator = script_dir / "validate-final-artifact.py"
    aa_validator = script_dir / "validate-aa-baseline.py"
    initramfs_validator = script_dir / "validate-initramfs.py"
    boot_validator = script_dir / "validate-boot.py"
    package_validator = script_dir / "validate-package.py"
    boot = args.artifact / "gemini-mt6797-kernel-restart.boot.img"
    initramfs = args.artifact / "gemini-mt6797-kernel-restart-initramfs.img"
    dtb = args.artifact / "mt6797-gemini-pda-kernel-restart.dtb"
    aa_initramfs = args.baseline / "gemini-keyboard-console-map-initramfs.img"
    final_command = [
        python,
        os.fspath(final_validator),
        "--artifact",
        os.fspath(args.artifact),
        "--baseline",
        os.fspath(args.baseline),
        "--package",
        os.fspath(args.package),
        "--manifest",
        os.fspath(args.manifest),
    ]
    try:
        run(final_command, 0)
        with tempfile.TemporaryDirectory(prefix="candidate-ab-mutations.") as raw_temp:
            temp = pathlib.Path(raw_temp)

            extra = copy_artifact(args.artifact, temp, "extra")
            (extra / "unexpected").write_text("unexpected\n", encoding="utf-8")
            run(final_command[:3] + [os.fspath(extra)] + final_command[4:], 2)

            manifest_mutation = copy_artifact(args.artifact, temp, "manifest")
            manifest_path = manifest_mutation / "SHA256SUMS"
            manifest_lines = manifest_path.read_bytes().splitlines(keepends=True)
            manifest_path.write_bytes(b"".join(reversed(manifest_lines)))
            run(final_command[:3] + [os.fspath(manifest_mutation)] + final_command[4:], 2)

            coherent_provenance = copy_artifact(args.artifact, temp, "coherent-provenance")
            provenance = coherent_provenance / "provenance.txt"
            provenance.write_bytes(provenance.read_bytes() + b"mutation=yes\n")
            write_manifest(coherent_provenance)
            run(final_command[:3] + [os.fspath(coherent_provenance)] + final_command[4:], 2)

            bad_baseline = temp / args.baseline.name
            shutil.copytree(args.baseline, bad_baseline, copy_function=shutil.copy2)
            bad_baseline.chmod(0o700)
            aa_manifest = bad_baseline / "SHA256SUMS"
            aa_manifest.write_bytes(flip(aa_manifest.read_bytes(), 0))
            run([python, os.fspath(aa_validator), "--artifact", os.fspath(bad_baseline)], 2)

            bad_boot = temp / "bad.boot.img"
            bad_boot.write_bytes(flip(read_regular(boot, "AB boot"), 4096))
            run(
                [
                    python,
                    os.fspath(boot_validator),
                    "--candidate",
                    os.fspath(bad_boot),
                    "--image",
                    os.fspath(args.package / "Image"),
                    "--image-gz",
                    os.fspath(args.artifact / "Image.gz"),
                    "--dtb",
                    os.fspath(dtb),
                    "--initramfs",
                    os.fspath(initramfs),
                ],
                2,
            )

            bad_initramfs = temp / "bad-initramfs.img"
            bad_initramfs.write_bytes(flip(read_regular(initramfs, "AB initramfs"), 32))
            run(
                [
                    python,
                    os.fspath(initramfs_validator),
                    "--baseline",
                    os.fspath(aa_initramfs),
                    "--candidate",
                    os.fspath(bad_initramfs),
                    "--source-dir",
                    os.fspath(experiment_dir / "initramfs"),
                ],
                2,
            )

            clean_members = parse_newc(read_regular(initramfs, "AB initramfs"))

            def semantic_mutation(
                label: str, member_name: str, suffix: bytes, source_name: str | None
            ) -> None:
                members = dict(clean_members)
                member = members[member_name]
                members[member_name] = replace(member, data=member.data + suffix)
                mutated = temp / f"{label}.img"
                mutated.write_bytes(encode_newc(members))
                source_dir = temp / f"{label}-sources"
                shutil.copytree(experiment_dir / "initramfs", source_dir)
                if source_name is not None:
                    source = source_dir / source_name
                    source.write_bytes(source.read_bytes() + suffix)
                run(
                    [
                        python,
                        os.fspath(initramfs_validator),
                        "--baseline",
                        os.fspath(aa_initramfs),
                        "--candidate",
                        os.fspath(mutated),
                        "--source-dir",
                        os.fspath(source_dir),
                    ],
                    2,
                )

            def semantic_replace(
                label: str,
                member_name: str,
                old: bytes,
                new: bytes,
                source_name: str,
            ) -> None:
                members = dict(clean_members)
                member = members[member_name]
                if member.data.count(old) != 1:
                    raise ValueError(f"mutation source token count changed: {label}")
                members[member_name] = replace(member, data=member.data.replace(old, new))
                mutated = temp / f"{label}.img"
                mutated.write_bytes(encode_newc(members))
                source_dir = temp / f"{label}-sources"
                shutil.copytree(experiment_dir / "initramfs", source_dir)
                source = source_dir / source_name
                source_data = source.read_bytes()
                if source_data.count(old) != 1:
                    raise ValueError(f"mutation tracked-source token count changed: {label}")
                source.write_bytes(source_data.replace(old, new))
                run(
                    [
                        python,
                        os.fspath(initramfs_validator),
                        "--baseline",
                        os.fspath(aa_initramfs),
                        "--candidate",
                        os.fspath(mutated),
                        "--source-dir",
                        os.fspath(source_dir),
                    ],
                    2,
                )

            semantic_mutation(
                "watchdog-access", "bin/reboot", b"\n/dev/watchdog0\n", "reboot"
            )
            semantic_mutation(
                "second-reboot",
                "bin/reboot",
                b"\n/bin/busybox reboot -n -f\n",
                "reboot",
            )
            semantic_mutation(
                "automatic-reboot",
                "init",
                b"\n/bin/busybox reboot -n -f\n",
                "init",
            )
            semantic_mutation(
                "keymap-byte", "etc/gemini-us.bkeymap", b"mutation", None
            )
            semantic_mutation("sync-path", "bin/reboot", b"\n/bin/busybox sync\n", "reboot")
            semantic_mutation("storage-path", "bin/reboot", b"\n/dev/mmcblk0\n", "reboot")
            semantic_replace(
                "fallback-path",
                "bin/reboot",
                b"/bin/busybox reboot -n -f\nstatus=$?",
                b"/bin/busybox reboot -n -f || /bin/busybox poweroff -f\nstatus=$?",
                "reboot",
            )
            semantic_replace(
                "reboot-flags",
                "bin/reboot",
                b"/bin/busybox reboot -n -f",
                b"/bin/busybox reboot -f",
                "reboot",
            )
            attribution = (
                b"/bin/x-record 'candidate=AB manual_reboot=requested trigger=bare-reboot "
                b"dispatch=absolute-wrapper method=busybox-reboot-no-sync-force "
                b"storage_access=none watchdog_userspace=none'\n"
            )
            invocation = b"/bin/busybox reboot -n -f\n"
            semantic_replace(
                "attribution-after-reboot",
                "bin/reboot",
                attribution + b"printf '%s\\n' 'Candidate AB: kernel restart requested now "
                b"(BusyBox reboot -n -f).'\n\n# Do not sync or inspect any filesystem: this is "
                b"an explicit forced reboot\n# request against the pinned BusyBox applet and "
                b"ordinary reboot(2) path.\n" + invocation,
                invocation + attribution + b"printf '%s\\n' 'Candidate AB: kernel restart "
                b"requested now (BusyBox reboot -n -f).'\n\n# Do not sync or inspect any "
                b"filesystem: this is an explicit forced reboot\n# request against the pinned "
                b"BusyBox applet and ordinary reboot(2) path.\n",
                "reboot",
            )

            semantic_mutation(
                "unicode-helper-substitution",
                "bin/console-unicode-mode",
                b"mutation",
                None,
            )
            semantic_mutation(
                "keymap-verifier-substitution",
                "bin/console-keymap-verify",
                b"mutation",
                None,
            )

            bad_dtb = temp / "bad.dtb"
            bad_dtb.write_bytes(flip(read_regular(dtb, "AB DTB"), 16))
            run(
                [
                    python,
                    os.fspath(boot_validator),
                    "--candidate",
                    os.fspath(boot),
                    "--image",
                    os.fspath(args.package / "Image"),
                    "--image-gz",
                    os.fspath(args.artifact / "Image.gz"),
                    "--dtb",
                    os.fspath(bad_dtb),
                    "--initramfs",
                    os.fspath(initramfs),
                ],
                2,
            )

            bad_image = temp / "bad-Image"
            bad_image.write_bytes(flip(read_regular(args.package / "Image", "AB Image"), 64))
            run(
                [
                    python,
                    os.fspath(boot_validator),
                    "--candidate",
                    os.fspath(boot),
                    "--image",
                    os.fspath(bad_image),
                    "--image-gz",
                    os.fspath(args.artifact / "Image.gz"),
                    "--dtb",
                    os.fspath(dtb),
                    "--initramfs",
                    os.fspath(initramfs),
                ],
                2,
            )

            boot_data = read_regular(boot, "AB boot")
            fields = struct.unpack_from("<10I", boot_data, 8)
            kernel_size, ramdisk_size, page_size = fields[0], fields[2], fields[7]
            kernel_end = page_size + kernel_size
            ramdisk_offset = (kernel_end + page_size - 1) // page_size * page_size

            bad_header = temp / "bad-header.boot.img"
            bad_header.write_bytes(flip(boot_data, 48))
            bad_ramdisk = temp / "bad-ramdisk.boot.img"
            bad_ramdisk.write_bytes(flip(boot_data, ramdisk_offset + ramdisk_size // 2))
            if ramdisk_offset <= kernel_end:
                raise ValueError("AB fixture unexpectedly lacks kernel padding")
            bad_padding = temp / "bad-padding.boot.img"
            bad_padding.write_bytes(flip(boot_data, kernel_end))
            for mutated in (bad_header, bad_ramdisk, bad_padding):
                run(
                    [
                        python,
                        os.fspath(boot_validator),
                        "--candidate",
                        os.fspath(mutated),
                        "--image",
                        os.fspath(args.package / "Image"),
                        "--image-gz",
                        os.fspath(args.artifact / "Image.gz"),
                        "--dtb",
                        os.fspath(dtb),
                        "--initramfs",
                        os.fspath(initramfs),
                    ],
                    2,
                )

            repo_root = args.manifest.resolve().parent.parent
            provenance_repo = temp / "repo-provenance"
            (provenance_repo / "kernel").mkdir(parents=True)
            (provenance_repo / "scripts").mkdir()
            shutil.copy2(args.manifest, provenance_repo / "kernel/manifest.json")
            shutil.copy2(repo_root / "scripts/kernel", provenance_repo / "scripts/kernel")
            shutil.copytree(repo_root / "patches", provenance_repo / "patches")
            shutil.copytree(repo_root / "configs", provenance_repo / "configs")
            patch = provenance_repo / "patches/v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch"
            original_patch = patch.read_bytes()
            patch.write_bytes(original_patch + b"mutation\n")
            run(
                [
                    python,
                    os.fspath(package_validator),
                    "--package",
                    os.fspath(args.package),
                    "--manifest",
                    os.fspath(provenance_repo / "kernel/manifest.json"),
                ],
                2,
            )
            patch.write_bytes(original_patch)
            config = provenance_repo / "configs/gemini-keyboard-manual-reboot.fragment"
            config.write_bytes(config.read_bytes() + b"# mutation\n")
            run(
                [
                    python,
                    os.fspath(package_validator),
                    "--package",
                    os.fspath(args.package),
                    "--manifest",
                    os.fspath(provenance_repo / "kernel/manifest.json"),
                ],
                2,
            )

            package_mutant = temp / args.package.name
            shutil.copytree(args.package, package_mutant, copy_function=shutil.copy2)
            build_json = package_mutant / "provenance/build.json"
            build_json.write_bytes(build_json.read_bytes() + b"\n")
            run(
                [
                    python,
                    os.fspath(package_validator),
                    "--package",
                    os.fspath(package_mutant),
                    "--manifest",
                    os.fspath(args.manifest),
                ],
                2,
            )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("clean_final_validation=PASS")
    print("final_inventory_mutation=REJECTED")
    print("final_manifest_mutation=REJECTED")
    print("coherent_provenance_mutation=REJECTED")
    print("aa_baseline_manifest_mutation=REJECTED")
    print("boot_kernel_mutation=REJECTED")
    print("initramfs_stream_mutation=REJECTED")
    print("initramfs_watchdog_access_mutation=REJECTED")
    print("initramfs_second_reboot_mutation=REJECTED")
    print("initramfs_automatic_reboot_mutation=REJECTED")
    print("initramfs_keymap_mutation=REJECTED")
    print("initramfs_sync_mutation=REJECTED")
    print("initramfs_storage_mutation=REJECTED")
    print("initramfs_fallback_mutation=REJECTED")
    print("initramfs_reboot_flags_mutation=REJECTED")
    print("initramfs_late_attribution_mutation=REJECTED")
    print("unicode_helper_substitution=REJECTED")
    print("keymap_verifier_substitution=REJECTED")
    print("dtb_substitution_mutation=REJECTED")
    print("image_substitution_mutation=REJECTED")
    print("android_header_mutation=REJECTED")
    print("android_ramdisk_mutation=REJECTED")
    print("android_padding_mutation=REJECTED")
    print("repository_patch_provenance_mutation=REJECTED")
    print("repository_config_provenance_mutation=REJECTED")
    print("package_build_provenance_mutation=REJECTED")
    print("mutations=25/25")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
