#!/usr/bin/env python3
"""Exercise Candidate AH's component and Android-v0 validation boundaries."""

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


PAGE_SIZE = 2048
KERNEL_ADDR = 0x40200000
RAMDISK_ADDR = 0x45000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x44000000
NAME = "gemini-obs-L"
CMDLINE = "bootopt=64S3,32N2,64N2"
BOOT_MEMBER = "gemini-ad-contract-af-kernel-split.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-ad-contract-af-kernel-split.dtb"
INITRAMFS_MEMBER = "gemini-ad-contract-af-kernel-split-initramfs.img"


def align(value: int) -> int:
    return (value + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def serialize(
    image_gz: bytes,
    dtb: bytes,
    initramfs: bytes,
    *,
    name: str = NAME,
    cmdline: str = CMDLINE,
    kernel_addr: int = KERNEL_ADDR,
    ramdisk_addr: int = RAMDISK_ADDR,
    dt_size: int = 0,
) -> bytes:
    kernel = image_gz + dtb
    fields = (
        len(kernel),
        kernel_addr,
        len(initramfs),
        ramdisk_addr,
        0,
        SECOND_ADDR,
        TAGS_ADDR,
        PAGE_SIZE,
        dt_size,
        0,
    )
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, initramfs, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    header = bytearray(PAGE_SIZE)
    struct.pack_into("<8s10I", header, 0, b"ANDROID!", *fields)
    encoded_name = name.encode("ascii")
    encoded_cmdline = cmdline.encode("ascii")
    if len(encoded_name) >= 16 or len(encoded_cmdline) > 1536:
        raise ValueError("mutation string is too long")
    header[48:64] = encoded_name.ljust(16, b"\0")
    header[64:576] = encoded_cmdline[:512].ljust(512, b"\0")
    header[576:596] = image_id.digest()
    header[608:1632] = encoded_cmdline[512:].ljust(1024, b"\0")
    output = bytes(header) + kernel
    output += b"\0" * (align(len(output)) - len(output))
    output += initramfs
    output += b"\0" * (align(len(output)) - len(output))
    return output


def flip(data: bytes, offset: int | None = None) -> bytes:
    if not data:
        raise ValueError("cannot mutate an empty payload")
    index = len(data) // 2 if offset is None else offset
    output = bytearray(data)
    output[index] ^= 0x01
    return bytes(output)


def run(command: list[str], expect_success: bool) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if (result.returncode == 0) != expect_success:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"unexpected validator result ({result.returncode}): {detail}")
    if not expect_success and "error:" not in result.stderr:
        raise ValueError("mutation rejection did not provide a fail-closed diagnostic")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ah-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--af-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ag-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ad-artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        roots: dict[str, pathlib.Path] = {}
        for label, supplied in (
            ("AH", args.ah_artifact),
            ("AF", args.af_artifact),
            ("AG", args.ag_artifact),
            ("AD", args.ad_artifact),
        ):
            if supplied.is_symlink() or not supplied.is_dir():
                raise ValueError(f"unsafe {label} artifact path")
            roots[label] = supplied.resolve(strict=True)
        for command in ("fdtput", sys.executable):
            if shutil.which(command) is None:
                raise ValueError(f"required command missing: {command}")

        script_dir = pathlib.Path(__file__).resolve().parent
        validator = script_dir / "validate-boot.py"
        ah_boot = roots["AH"] / BOOT_MEMBER
        ah_image = roots["AH"] / "Image.gz"
        ah_dtb = roots["AH"] / DTB_MEMBER
        ah_initramfs = roots["AH"] / INITRAMFS_MEMBER
        af_boot = roots["AF"] / "gemini-a72-observer-initcall-diagnostic.boot.img"
        ag_boot = roots["AG"] / "gemini-simplefb-observation-restoration.boot.img"
        ad_boot = roots["AD"] / "gemini-smp8.boot.img"
        ad_dtb = roots["AD"] / "mt6797-gemini-pda-smp8.dtb"
        common = [
            sys.executable,
            os.fspath(validator),
            "--af-boot",
            os.fspath(af_boot),
            "--ag-boot",
            os.fspath(ag_boot),
            "--ad-boot",
            os.fspath(ad_boot),
            "--ad-dtb",
            os.fspath(ad_dtb),
        ]

        def validate_case(
            candidate: pathlib.Path,
            image: pathlib.Path,
            dtb: pathlib.Path,
            initramfs: pathlib.Path,
            expect_success: bool,
            prefix: list[str] | None = None,
        ) -> None:
            command = common if prefix is None else prefix
            run(
                [
                    *command,
                    "--candidate",
                    os.fspath(candidate),
                    "--image-gz",
                    os.fspath(image),
                    "--ah-dtb",
                    os.fspath(dtb),
                    "--initramfs",
                    os.fspath(initramfs),
                ],
                expect_success,
            )

        validate_case(ah_boot, ah_image, ah_dtb, ah_initramfs, True)
        image = ah_image.read_bytes()
        dtb = ah_dtb.read_bytes()
        initramfs = ah_initramfs.read_bytes()
        if serialize(image, dtb, initramfs) != ah_boot.read_bytes():
            raise ValueError("positive fixture is not the independently serialized image")

        with tempfile.TemporaryDirectory(prefix="candidate-ah-boot-mutations-") as raw:
            work = pathlib.Path(raw)
            rejected = 0

            def coherent_case(
                label: str,
                case_image: bytes = image,
                case_dtb: bytes = dtb,
                case_initramfs: bytes = initramfs,
                **header: object,
            ) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path]:
                case = work / label
                case.mkdir()
                image_path = case / "Image.gz"
                dtb_path = case / "candidate.dtb"
                initramfs_path = case / "initramfs.img"
                boot_path = case / "candidate.boot.img"
                image_path.write_bytes(case_image)
                dtb_path.write_bytes(case_dtb)
                initramfs_path.write_bytes(case_initramfs)
                boot_path.write_bytes(
                    serialize(case_image, case_dtb, case_initramfs, **header)
                )
                return boot_path, image_path, dtb_path, initramfs_path

            for label, kwargs in (
                ("image", {"case_image": flip(image)}),
                ("initramfs", {"case_initramfs": flip(initramfs)}),
                ("name", {"name": "gemini-obs-X"}),
                ("cmdline", {"cmdline": CMDLINE + " changed=1"}),
                ("kernel-address", {"kernel_addr": KERNEL_ADDR + PAGE_SIZE}),
                ("ramdisk-address", {"ramdisk_addr": RAMDISK_ADDR + PAGE_SIZE}),
                ("dt-size", {"dt_size": len(dtb)}),
            ):
                paths = coherent_case(label, **kwargs)
                validate_case(*paths, False)
                rejected += 1

            for label, path, prop, value in (
                ("cpu8-psci", "/cpus/cpu@200", "enable-method", "psci"),
                ("usb-disabled", "/usb@11271000", "status", "disabled"),
            ):
                case_dtb_path = work / f"{label}.dtb"
                shutil.copyfile(ah_dtb, case_dtb_path)
                run(
                    ["fdtput", "-t", "s", str(case_dtb_path), path, prop, value],
                    True,
                )
                paths = coherent_case(label, case_dtb=case_dtb_path.read_bytes())
                validate_case(*paths, False)
                rejected += 1

            corrupt_id = work / "corrupt-id.boot.img"
            corrupt_id.write_bytes(flip(ah_boot.read_bytes(), 576))
            validate_case(corrupt_id, ah_image, ah_dtb, ah_initramfs, False)
            rejected += 1

            trailing = work / "trailing.boot.img"
            trailing.write_bytes(ah_boot.read_bytes() + b"\0" * PAGE_SIZE)
            validate_case(trailing, ah_image, ah_dtb, ah_initramfs, False)
            rejected += 1

            bad_af = work / "bad-af.boot.img"
            bad_af.write_bytes(flip(af_boot.read_bytes(), 48))
            bad_common = common.copy()
            bad_common[bad_common.index(os.fspath(af_boot))] = os.fspath(bad_af)
            validate_case(
                ah_boot,
                ah_image,
                ah_dtb,
                ah_initramfs,
                False,
                prefix=bad_common,
            )
            rejected += 1

        print("validation=candidate-ah-boot-mutations")
        print("positive_fixture=accepted")
        print(f"mutations_rejected={rejected}-of-{rejected}")
        print("coherent_payload_and_dtb_mutations=rejected")
        print("android_v0_header_and_layout_mutations=rejected")
        print("device_access=none")
        return 0
    except (OSError, TypeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
