#!/usr/bin/env python3
"""Derive and run Quasar's storage-inert LK assembler from exact Vega."""

from __future__ import annotations

import hashlib
import os
import pathlib
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


VEGA_BUILDER = (
    "experiments/2026-07-27-mt6797-i2c6-vega/"
    "scripts/build-candidate-vega.sh"
)
VEGA_BUILDER_SHA256 = (
    "a4ef4b49acec91096a33f756bdc64d803d60704b4b0148e45b0edb057208ec7b"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"assembler token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def derive_text(source: str) -> str:
    replacements = (
        ("Vega", "Quasar", 8),
        ("vega", "quasar", 6),
        (
            'script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"',
            'script_dir=${QUASAR_SCRIPT_DIR:?}',
            1,
        ),
        (
            "diagnostic=fixed-root-only-one-shot",
            "diagnostic=fixed-root-only-native-one-shot",
            1,
        ),
        (
            "mode_order=packed-fifo,packed-dma,aux-dma",
            "native_policy=unforced-packed-fifo-two-pass",
            1,
        ),
        (
            "adapter_retries=temporarily-zero-and-restored",
            "adapter_retries=1,0,1-restored",
            1,
        ),
        (
            "patch_series=$(value SERIES)\n"
            "boot_container=canonical-android-v0-lk-android8",
            "patch_series=$(value SERIES)\n"
            f"assembler_foundation_sha256={VEGA_BUILDER_SHA256}\n"
            "assembler_derived_sha256="
            "${QUASAR_DERIVED_ASSEMBLER_SHA256:?}\n"
            "boot_container=canonical-android-v0-lk-android8",
            1,
        ),
    )
    text = source
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)
    restored = text
    for old, new, count in reversed(replacements):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError("Quasar assembler cannot restore exact Vega foundation")
    validate_contract(text)
    return text


def validate_contract(text: str) -> None:
    required = {
        "candidate_quasar": 1,
        "validate-package-quasar.py": 1,
        "--name gemini-quasar": 1,
        "candidate=Quasar": 1,
        "diagnostic=fixed-root-only-native-one-shot": 1,
        "native_policy=unforced-packed-fifo-two-pass": 1,
        "adapter_retries=1,0,1-restored": 1,
        f"assembler_foundation_sha256={VEGA_BUILDER_SHA256}": 1,
        "assembler_derived_sha256="
        "${QUASAR_DERIVED_ASSEMBLER_SHA256:?}": 1,
        'script_dir=${QUASAR_SCRIPT_DIR:?}': 1,
        'python3 "$serializer"': 1,
        "--lk-android8": 1,
        'cmp -s "$stage/$BOOT_MEMBER" "$replica/$BOOT_MEMBER"': 1,
        'dd if=/dev/zero of="$padded" bs=16M count=1 status=none': 1,
        'dd if="$stage/$BOOT_MEMBER" of="$padded"': 1,
        "hardware_write=none": 1,
        "device_access=none": 1,
        "runtime_result=not-tested": 2,
    }
    for token, wanted in required.items():
        actual = text.count(token)
        if actual != wanted:
            raise ValueError(
                f"derived Quasar assembler count changed for {token!r}: "
                f"expected {wanted}, found {actual}"
            )
    forbidden = (
        "candidate=Vega",
        "candidate_vega",
        "validate-package-vega.py",
        "--name gemini-vega",
        "mode_order=packed-fifo,packed-dma,aux-dma",
        "of=/dev/",
        "ssh ",
        "scp ",
        "reboot ",
        "shutdown ",
        "poweroff ",
    )
    for token in forbidden:
        if token in text:
            raise ValueError(
                f"derived Quasar assembler retains forbidden token: {token}"
            )


def main() -> int:
    scripts = pathlib.Path(__file__).resolve().parent
    repository = scripts.parents[2]
    source_path = repository / VEGA_BUILDER
    try:
        source_data = read_regular(source_path, "source-pinned Vega assembler")
        if hashlib.sha256(source_data).hexdigest() != VEGA_BUILDER_SHA256:
            raise ValueError("source-pinned Vega assembler changed")
        source = source_data.decode("utf-8", "strict")
        derived = derive_text(source)
        derived_sha256 = hashlib.sha256(derived.encode()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="quasar-lk-assembler.") as raw:
            path = pathlib.Path(raw) / "build-candidate-quasar.sh"
            path.write_text(derived, encoding="utf-8")
            path.chmod(0o700)
            result = subprocess.run(
                ["bash", os.fspath(path), *sys.argv[1:]],
                cwd=repository,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "QUASAR_SCRIPT_DIR": os.fspath(scripts),
                    "QUASAR_DERIVED_ASSEMBLER_SHA256": derived_sha256,
                },
                check=False,
            )
        return result.returncode
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
