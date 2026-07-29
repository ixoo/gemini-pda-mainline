#!/usr/bin/env python3
"""Derive and run Curie's storage-inert LK assembler from exact Fermi."""

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


FERMI_DERIVER = (
    "experiments/2026-07-28-da9214-fermi/scripts/derive-candidate.py"
)
FERMI_DERIVER_SHA256 = (
    "82577a304377b86bd6b687504185e6c2c2ec371038a3545138468d380e052eee"
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


def load_fermi_deriver(repository: pathlib.Path) -> ModuleType:
    source = repository / FERMI_DERIVER
    data = read_regular(source, "source-pinned Fermi assembler deriver")
    if hashlib.sha256(data).hexdigest() != FERMI_DERIVER_SHA256:
        raise ValueError("source-pinned Fermi assembler deriver changed")
    spec = importlib.util.spec_from_file_location("curie_fermi_deriver", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Fermi assembler deriver")
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
        ("FERMI", "CURIE", 2),
        ("Fermi", "Curie", 8),
        ("fermi", "curie", 6),
        (
            "diagnostic=fixed-root-only-read-only-topology-fingerprint",
            "diagnostic=fixed-root-only-read-only-board-control-stability",
            1,
        ),
        (
            "native_policy=unforced-packed-fifo-two-pass-14-transfer-topology",
            "native_policy=unforced-packed-fifo-two-pass-14-transfer-board-state",
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
        raise ValueError("Curie assembler cannot restore exact Fermi foundation")
    required = {
        "candidate_curie": 1,
        "validate-package-curie.py": 1,
        "--name gemini-curie": 1,
        "candidate=Curie": 1,
        "diagnostic=fixed-root-only-read-only-board-control-stability": 1,
        "native_policy=unforced-packed-fifo-two-pass-14-transfer-board-state": 1,
        "adapter_retries=1,0,1-restored": 1,
        'script_dir=${CURIE_SCRIPT_DIR:?}': 1,
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
                f"derived Curie assembler contract changed for {token!r}"
            )
    for stale in (
        "candidate=Fermi",
        "candidate_fermi",
        "validate-package-fermi.py",
        "--name gemini-fermi",
        "orion-run-all",
        "fermi-run-native",
        "of=/dev/",
        "ssh ",
        "scp ",
        "reboot ",
        "shutdown ",
        "poweroff ",
    ):
        if stale in text:
            raise ValueError(
                f"derived Curie assembler retains forbidden token: {stale}"
            )
    return text


def main() -> int:
    scripts = pathlib.Path(__file__).resolve().parent
    repository = scripts.parents[2]
    try:
        fermi = load_fermi_deriver(repository)
        quasar = fermi.load_quasar_deriver(repository)
        vega_path = repository / quasar.VEGA_BUILDER
        vega_data = read_regular(vega_path, "source-pinned Vega assembler")
        if hashlib.sha256(vega_data).hexdigest() != quasar.VEGA_BUILDER_SHA256:
            raise ValueError("source-pinned Vega assembler changed")
        quasar_text = quasar.derive_text(vega_data.decode("utf-8", "strict"))
        fermi_text = fermi.derive_text(quasar_text)
        derived = derive_text(fermi_text)
        derived_sha256 = hashlib.sha256(derived.encode()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="curie-lk-assembler.") as raw:
            path = pathlib.Path(raw) / "build-candidate-curie.sh"
            path.write_text(derived, encoding="utf-8")
            path.chmod(0o700)
            result = subprocess.run(
                ["bash", os.fspath(path), *sys.argv[1:]],
                cwd=repository,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "CURIE_SCRIPT_DIR": os.fspath(scripts),
                    "CURIE_DERIVED_ASSEMBLER_SHA256": derived_sha256,
                },
                check=False,
            )
        return result.returncode
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
