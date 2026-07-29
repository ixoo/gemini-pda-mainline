#!/usr/bin/env python3
"""Derive Gauss's storage-inert assembler from the exact Fermi assembler."""

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


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_fermi_deriver(repository: pathlib.Path) -> ModuleType:
    path = repository / FERMI_DERIVER
    data = regular(path, "source-pinned Fermi assembler deriver")
    if hashlib.sha256(data).hexdigest() != FERMI_DERIVER_SHA256:
        raise ValueError("source-pinned Fermi assembler deriver changed")
    spec = importlib.util.spec_from_file_location("gauss_fermi_deriver", path)
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
    text = source
    replacements = (
        (
            "# Assemble storage-inert Candidate Fermi from a validated kernel "
            "package and",
            "# Assemble storage-inert Candidate Gauss from a validated kernel "
            "package and",
            1,
        ),
        (
            "usage: %s --package DIR --cassini-package DIR "
            "--hubble-artifact DIR --output-parent DIR",
            "usage: %s --package DIR --fermi-package DIR "
            "--fermi-object FILE --gauss-object FILE "
            "--fermi-vmlinux FILE --gauss-vmlinux FILE "
            "--cassini-package DIR --hubble-artifact DIR --output-parent DIR",
            1,
        ),
        (
            "package=\ncassini_package=",
            "package=\nfermi_package=\nfermi_object=\ngauss_object=\n"
            "fermi_vmlinux=\ngauss_vmlinux=\ncassini_package=",
            1,
        ),
        (
            "--package|--cassini-package|--hubble-artifact|--output-parent)",
            "--package|--fermi-package|--fermi-object|--gauss-object|"
            "--fermi-vmlinux|--gauss-vmlinux|--cassini-package|"
            "--hubble-artifact|--output-parent)",
            1,
        ),
        (
            "--package) package=$2 ;;\n"
            "\t\t--cassini-package) cassini_package=$2 ;;",
            "--package) package=$2 ;;\n"
            "\t\t--fermi-package) fermi_package=$2 ;;\n"
            "\t\t--fermi-object) fermi_object=$2 ;;\n"
            "\t\t--gauss-object) gauss_object=$2 ;;\n"
            "\t\t--fermi-vmlinux) fermi_vmlinux=$2 ;;\n"
            "\t\t--gauss-vmlinux) gauss_vmlinux=$2 ;;\n"
            "\t\t--cassini-package) cassini_package=$2 ;;",
            1,
        ),
        (
            '[[ -n "$package" && -n "$cassini_package" && '
            '-n "$hubble_artifact" && -n "$output_parent" ]] ||',
            '[[ -n "$package" && -n "$fermi_package" && '
            '-n "$fermi_object" && -n "$gauss_object" && '
            '-n "$fermi_vmlinux" && -n "$gauss_vmlinux" && '
            '-n "$cassini_package" && -n "$hubble_artifact" && '
            '-n "$output_parent" ]] ||',
            1,
        ),
        (
            'for directory in "$package" "$cassini_package" '
            '"$hubble_artifact" "$output_parent"; do',
            'for directory in "$package" "$fermi_package" "$cassini_package" '
            '"$hubble_artifact" "$output_parent"; do',
            1,
        ),
        (
            "done\nfor command in awk bash",
            'done\nfor build_file in "$fermi_object" "$gauss_object" '
            '"$fermi_vmlinux" "$gauss_vmlinux"; do\n'
            '\t[[ -f "$build_file" && ! -L "$build_file" && '
            '-s "$build_file" ]] ||\n'
            '\t\tdie "unsafe or missing build-audit input: $build_file"\n'
            "done\nfor command in awk bash",
            1,
        ),
        ("script_dir=${FERMI_SCRIPT_DIR:?}", "script_dir=${GAUSS_SCRIPT_DIR:?}", 1),
        (
            'package="$(cd -- "$package" && pwd -P)"\n'
            'cassini_package="$(cd -- "$cassini_package" && pwd -P)"',
            'package="$(cd -- "$package" && pwd -P)"\n'
            'fermi_package="$(cd -- "$fermi_package" && pwd -P)"\n'
            'cassini_package="$(cd -- "$cassini_package" && pwd -P)"',
            1,
        ),
        (
            '"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|\\\n'
            '"$cassini_package"',
            '"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|\\\n'
            '"$fermi_package"|"$fermi_package"/*|\\\n'
            '"$cassini_package"',
            1,
        ),
        ("import candidate_fermi as c", "import candidate_gauss as c", 1),
        (
            'package_validator="$script_dir/validate-package-fermi.py"',
            'package_validator="$script_dir/validate-package-gauss.py"',
            1,
        ),
        (
            'workdir="$(mktemp -d "$output_parent/.candidate-fermi.XXXXXX")"',
            'workdir="$(mktemp -d "$output_parent/.candidate-gauss.XXXXXX")"',
            1,
        ),
        (
            'python3 "$package_validator" --repository "$repo_root" '
            '--package "$package" \\\n'
            '\t>"$stage/package-validation.txt"',
            'python3 "$package_validator" --repository "$repo_root" '
            '--package "$package" \\\n'
            '\t--fermi-package "$fermi_package" '
            '--fermi-object "$fermi_object" \\\n'
            '\t--gauss-object "$gauss_object" '
            '--fermi-vmlinux "$fermi_vmlinux" \\\n'
            '\t--gauss-vmlinux "$gauss_vmlinux" '
            '>"$stage/package-validation.txt"',
            1,
        ),
        (
            "die 'independent Fermi DT derivations differ'",
            "die 'independent Gauss DT derivations differ'",
            1,
        ),
        (
            "die 'Fermi boot DT differs from exact Orion boot DT'",
            "die 'Gauss boot DT differs from exact Orion boot DT'",
            1,
        ),
        (
            "die 'independent Fermi Android-v0 assemblies differ'",
            "die 'independent Gauss Android-v0 assemblies differ'",
            1,
        ),
        ("die 'Fermi image does not fit boot2'", "die 'Gauss image does not fit boot2'", 1),
        ("candidate=Fermi", "candidate=Gauss", 1),
        (
            "assembler_foundation_sha256="
            "a4ef4b49acec91096a33f756bdc64d803d60704b4b0148e45b0edb057208ec7b",
            "assembler_foundation_sha256=${GAUSS_FERMI_ASSEMBLER_SHA256:?}",
            1,
        ),
        (
            "assembler_derived_sha256=${FERMI_DERIVED_ASSEMBLER_SHA256:?}",
            "assembler_derived_sha256=${GAUSS_DERIVED_ASSEMBLER_SHA256:?}",
            1,
        ),
        (
            "diagnostic=fixed-root-only-read-only-topology-fingerprint",
            "diagnostic=fixed-root-only-read-only-exact-d3-discriminator",
            1,
        ),
        (
            "native_policy=unforced-packed-fifo-two-pass-14-transfer-topology",
            "native_policy=unforced-packed-fifo-two-pass-14-transfer-exact-d3",
            1,
        ),
        ("die 'Fermi output inventory changed'", "die 'Gauss output inventory changed'", 1),
        ("die 'Fermi artifact manifest failed'", "die 'Gauss artifact manifest failed'", 1),
        (
            "validation=candidate-fermi-assembled",
            "validation=candidate-gauss-assembled",
            1,
        ),
    )
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)

    required = {
        "candidate_gauss": 1,
        "validate-package-gauss.py": 1,
        "--fermi-package": 4,
        "--fermi-object": 4,
        "--gauss-object": 4,
        "--fermi-vmlinux": 4,
        "--gauss-vmlinux": 4,
        "--name gemini-fermi": 1,
        "--expected-name gemini-fermi": 1,
        "candidate=Gauss": 1,
        "GEMINI_FERMI": 0,
        "diagnostic=fixed-root-only-read-only-exact-d3-discriminator": 1,
        "native_policy=unforced-packed-fifo-two-pass-14-transfer-exact-d3": 1,
        'script_dir=${GAUSS_SCRIPT_DIR:?}': 1,
        "hardware_write=none": 1,
        "device_access=none": 1,
        "runtime_result=not-tested": 2,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(f"derived Gauss assembler changed for {token!r}")
    for forbidden in (
        "candidate_fermi",
        "validate-package-fermi.py",
        "--name gemini-gauss",
        "--expected-name gemini-gauss",
        "candidate=Fermi",
        "of=/dev/",
        "ssh ",
        "scp ",
        "reboot ",
        "shutdown ",
        "poweroff ",
    ):
        if forbidden in text:
            raise ValueError(f"derived Gauss assembler retained {forbidden!r}")
    return text


def main() -> int:
    scripts = pathlib.Path(__file__).resolve().parent
    repository = scripts.parents[2]
    try:
        fermi = load_fermi_deriver(repository)
        quasar = fermi.load_quasar_deriver(repository)
        vega_path = repository / quasar.VEGA_BUILDER
        vega_data = regular(vega_path, "source-pinned Vega assembler")
        if hashlib.sha256(vega_data).hexdigest() != quasar.VEGA_BUILDER_SHA256:
            raise ValueError("source-pinned Vega assembler changed")
        quasar_text = quasar.derive_text(vega_data.decode("utf-8", "strict"))
        fermi_text = fermi.derive_text(quasar_text)
        derived = derive_text(fermi_text)
        fermi_sha256 = hashlib.sha256(fermi_text.encode()).hexdigest()
        derived_sha256 = hashlib.sha256(derived.encode()).hexdigest()
        with tempfile.TemporaryDirectory(prefix="gauss-lk-assembler.") as raw:
            path = pathlib.Path(raw) / "build-candidate-gauss.sh"
            path.write_text(derived, encoding="utf-8")
            path.chmod(0o700)
            result = subprocess.run(
                ["bash", os.fspath(path), *sys.argv[1:]],
                cwd=repository,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "GAUSS_SCRIPT_DIR": os.fspath(scripts),
                    "GAUSS_FERMI_ASSEMBLER_SHA256": fermi_sha256,
                    "GAUSS_DERIVED_ASSEMBLER_SHA256": derived_sha256,
                },
                check=False,
            )
        return result.returncode
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
