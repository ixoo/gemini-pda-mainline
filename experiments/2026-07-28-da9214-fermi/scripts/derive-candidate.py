#!/usr/bin/env python3
"""Derive and run Fermi's storage-inert LK assembler from exact Quasar."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
from types import ModuleType

sys.dont_write_bytecode = True


QUASAR_DERIVER = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/scripts/derive-candidate.py"
)
QUASAR_DERIVER_SHA256 = (
    "77cf4863ed1a2c49d832f19675da5e5fd075968648a313cb8666924a83d3ac2d"
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


def load_quasar_deriver(repository: pathlib.Path) -> ModuleType:
    source = repository / QUASAR_DERIVER
    data = read_regular(source, "source-pinned Quasar assembler deriver")
    if hashlib.sha256(data).hexdigest() != QUASAR_DERIVER_SHA256:
        raise ValueError("source-pinned Quasar assembler deriver changed")
    spec = importlib.util.spec_from_file_location("fermi_quasar_deriver", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Quasar assembler deriver")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


def derive_text(source: str) -> str:
    replacements = (
        ("QUASAR", "FERMI", 2),
        ("Quasar", "Fermi", 8),
        ("quasar", "fermi", 6),
        (
            "diagnostic=fixed-root-only-native-one-shot",
            "diagnostic=fixed-root-only-read-only-topology-fingerprint",
            1,
        ),
        (
            "native_policy=unforced-packed-fifo-two-pass",
            "native_policy=unforced-packed-fifo-two-pass-14-transfer-topology",
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
        raise ValueError("Fermi assembler cannot restore exact Quasar foundation")
    required = {
        "candidate_fermi": 1,
        "validate-package-fermi.py": 1,
        "--name gemini-fermi": 1,
        "candidate=Fermi": 1,
        "diagnostic=fixed-root-only-read-only-topology-fingerprint": 1,
        "native_policy=unforced-packed-fifo-two-pass-14-transfer-topology": 1,
        "adapter_retries=1,0,1-restored": 1,
        'script_dir=${FERMI_SCRIPT_DIR:?}': 1,
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
        if text.count(token) != wanted:
            raise ValueError(
                f"derived Fermi assembler contract changed for {token!r}"
            )
    for stale in (
        "candidate=Quasar",
        "candidate_quasar",
        "validate-package-quasar.py",
        "--name gemini-quasar",
        "orion-run-all",
        "quasar-run-native",
        "of=/dev/",
        "ssh ",
        "scp ",
        "reboot ",
        "shutdown ",
        "poweroff ",
    ):
        if stale in text:
            raise ValueError(
                f"derived Fermi assembler retains forbidden token: {stale}"
            )
    return text


def main() -> int:
    scripts = pathlib.Path(__file__).resolve().parent
    repository = scripts.parents[2]
    try:
        quasar = load_quasar_deriver(repository)
        vega_path = repository / quasar.VEGA_BUILDER
        vega_data = read_regular(vega_path, "source-pinned Vega assembler")
        if hashlib.sha256(vega_data).hexdigest() != quasar.VEGA_BUILDER_SHA256:
            raise ValueError("source-pinned Vega assembler changed")
        quasar_text = quasar.derive_text(vega_data.decode("utf-8", "strict"))
        derived = derive_text(quasar_text)
        derived_sha256 = hashlib.sha256(derived.encode()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="fermi-lk-assembler.") as raw:
            path = pathlib.Path(raw) / "build-candidate-fermi.sh"
            path.write_text(derived, encoding="utf-8")
            path.chmod(0o700)
            result = subprocess.run(
                ["bash", os.fspath(path), *sys.argv[1:]],
                cwd=repository,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "FERMI_SCRIPT_DIR": os.fspath(scripts),
                    "FERMI_DERIVED_ASSEMBLER_SHA256": derived_sha256,
                },
                check=False,
            )
        return result.returncode
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
