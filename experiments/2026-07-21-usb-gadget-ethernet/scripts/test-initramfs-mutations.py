#!/usr/bin/env python3
"""Require the Candidate AC initramfs validator to reject focused mutations."""

from __future__ import annotations

import argparse
from dataclasses import replace
import gzip
import importlib.util
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile


VALIDATOR_PATH = pathlib.Path(__file__).resolve().parent / "validate-initramfs.py"
MARKER_BYTES = b"GEMINI_USB_GADGET_ETHERNET_20260721_AC"
SPEC = importlib.util.spec_from_file_location("candidate_ac_validate_initramfs", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AC initramfs validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)
Member = VALIDATOR.Member
parse_newc = VALIDATOR.parse_newc
read_regular = VALIDATOR.read_regular


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
    compressed[9] = 3
    return bytes(compressed)


def validator_command(
    baseline: pathlib.Path,
    candidate: pathlib.Path,
    source_dir: pathlib.Path,
) -> list[str]:
    return [
        sys.executable,
        os.fspath(VALIDATOR_PATH),
        "--baseline",
        os.fspath(baseline),
        "--candidate",
        os.fspath(candidate),
        "--source-dir",
        os.fspath(source_dir),
    ]


def run_validator(
    baseline: pathlib.Path,
    candidate: pathlib.Path,
    source_dir: pathlib.Path,
    expected_status: int,
    expected_error: str | None = None,
) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        validator_command(baseline, candidate, source_dir),
        capture_output=True,
        check=False,
        env=environment,
    )
    if result.returncode != expected_status:
        raise RuntimeError(
            f"unexpected validator status {result.returncode}, expected {expected_status}\n"
            f"stdout={result.stdout.decode(errors='replace')}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )
    if expected_error is not None and expected_error not in result.stderr.decode(
        errors="replace"
    ):
        raise RuntimeError(
            f"validator rejected mutation for the wrong reason; expected {expected_error!r}\n"
            f"stderr={result.stderr.decode(errors='replace')}"
        )


def copy_sources(source: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    shutil.copytree(source, destination, copy_function=shutil.copy2)
    return destination


def write_candidate(path: pathlib.Path, members: dict[str, Member]) -> None:
    path.write_bytes(encode_newc(members))
    path.chmod(0o600)


def replace_member_and_source(
    clean_members: dict[str, Member],
    original_sources: pathlib.Path,
    temp: pathlib.Path,
    label: str,
    member_name: str,
    source_name: str,
    old: bytes,
    new: bytes,
) -> tuple[pathlib.Path, pathlib.Path]:
    member = clean_members[member_name]
    if old not in member.data:
        raise ValueError(f"mutation member token missing: {label}")
    members = dict(clean_members)
    members[member_name] = replace(member, data=member.data.replace(old, new))
    candidate = temp / f"{label}.img"
    write_candidate(candidate, members)
    sources = copy_sources(original_sources, temp / f"{label}-sources")
    source_path = sources / source_name
    source_data = source_path.read_bytes()
    if old not in source_data:
        raise ValueError(f"mutation source token missing: {label}")
    source_path.write_bytes(source_data.replace(old, new))
    return candidate, sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--source-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        run_validator(args.baseline, args.candidate, args.source_dir, 0)
        clean_members = parse_newc(read_regular(args.candidate, "Candidate AC initramfs"))
        with tempfile.TemporaryDirectory(prefix="candidate-ac-initramfs-mutations.") as raw:
            temp = pathlib.Path(raw)
            cases = 0

            def coherent_replace(
                label: str,
                member_name: str,
                source_name: str,
                old: bytes,
                new: bytes,
                expected_error: str,
            ) -> None:
                nonlocal cases
                candidate, sources = replace_member_and_source(
                    clean_members,
                    args.source_dir,
                    temp,
                    label,
                    member_name,
                    source_name,
                    old,
                    new,
                )
                run_validator(args.baseline, candidate, sources, 2, expected_error)
                cases += 1

            coherent_replace(
                "address",
                "bin/usb-net",
                "usb-net",
                b"10.15.19.82/24",
                b"10.15.19.83/24",
                "exact USB address command",
            )
            coherent_replace(
                "interface",
                "bin/usb-net",
                "usb-net",
                b"usb0",
                b"usb1",
                "bounded usb0 discovery loop",
            )
            coherent_replace(
                "port",
                "bin/usb-net",
                "usb-net",
                b"2323",
                b"2324",
                "exact persistent TCP shell listener",
            )
            coherent_replace(
                "marker",
                "bin/ac-record",
                "ac-record",
                MARKER_BYTES,
                b"GEMINI_USB_GADGET_ETHERNET_20260721_BAD",
                "AC recorder marker",
            )
            coherent_replace(
                "dispatch",
                "bin/usb-shell",
                "usb-shell",
                b"reboot is an alias for /bin/reboot",
                b"reboot is reboot",
                "absolute reboot alias expectation",
            )
            coherent_replace(
                "wait-bound",
                "bin/usb-net",
                "usb-net",
                b"readonly WAIT_SECONDS=30",
                b"readonly WAIT_SECONDS=31",
                "30-second USB wait bound",
            )
            coherent_replace(
                "listener-flags",
                "bin/usb-net",
                "usb-net",
                b"nc -ll -p 2323",
                b"nc -l -p 2323",
                "exact persistent TCP shell listener",
            )
            coherent_replace(
                "watchdog",
                "bin/usb-net",
                "usb-net",
                b"/bin/busybox nc -ll -p 2323 -e /bin/usb-shell",
                b"/dev/watchdog0\n/bin/busybox nc -ll -p 2323 -e /bin/usb-shell",
                "forbidden runtime path",
            )
            coherent_replace(
                "storage",
                "bin/usb-net",
                "usb-net",
                b"/bin/busybox nc -ll -p 2323 -e /bin/usb-shell",
                b"/dev/mmcblk0\n/bin/busybox nc -ll -p 2323 -e /bin/usb-shell",
                "forbidden runtime path",
            )
            coherent_replace(
                "automatic-reboot",
                "bin/usb-net",
                "usb-net",
                b"/bin/busybox nc -ll -p 2323 -e /bin/usb-shell",
                b"/bin/busybox reboot -n -f\n/bin/busybox nc -ll -p 2323 -e /bin/usb-shell",
                "automatic/background AC path",
            )

            extra_members = dict(clean_members)
            extra_members["unexpected"] = Member(
                stat.S_IFREG | 0o644, 0, 0, 1, 0, 0, 0, 0, 0, b"unexpected\n"
            )
            extra = temp / "extra-member.img"
            write_candidate(extra, extra_members)
            run_validator(args.baseline, extra, args.source_dir, 2, "archive inventory")
            cases += 1

            link_members = dict(clean_members)
            link = link_members["bin/nc"]
            link_members["bin/nc"] = replace(link, data=b"usb-shell")
            bad_link = temp / "symlink-target.img"
            write_candidate(bad_link, link_members)
            run_validator(args.baseline, bad_link, args.source_dir, 2, "BusyBox-link target")
            cases += 1

            inherited_members = dict(clean_members)
            inherited = inherited_members["bin/x-record"]
            inherited_members["bin/x-record"] = replace(
                inherited, data=inherited.data + b"# mutation\n"
            )
            bad_inherited = temp / "inherited-member.img"
            write_candidate(bad_inherited, inherited_members)
            run_validator(
                args.baseline,
                bad_inherited,
                args.source_dir,
                2,
                "inherited Candidate AB member changed",
            )
            cases += 1

        print(f"mutation_tests={cases}/{cases}")
        print("mutations=address,interface,port,marker,dispatch,wait-bound,listener-flags")
        print("mutations+=watchdog,storage,automatic-reboot,extra-member,symlink,inherited")
        print("validation=all-focused-mutations-rejected")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
