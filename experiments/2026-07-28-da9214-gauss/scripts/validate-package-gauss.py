#!/usr/bin/env python3
"""Validate Gauss's exact Fermi-identity package and linked binary delta."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True


FERMI_VALIDATOR = (
    "experiments/2026-07-28-da9214-fermi/scripts/validate-package-fermi.py"
)
FERMI_VALIDATOR_SHA256 = (
    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"
)
BINARY_AUDITOR_SHA256 = (
    "4e9481ccb3243779c493392189a05deade71ab6acb5fefbd35307cd20330f137"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"package-validator token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_fermi(repository: pathlib.Path) -> ModuleType:
    source = repository / FERMI_VALIDATOR
    data = read_regular(source, "source-pinned Fermi package validator")
    if hashlib.sha256(data).hexdigest() != FERMI_VALIDATOR_SHA256:
        raise ValueError("source-pinned Fermi package validator changed")
    sys.path.insert(0, str(source.parent))
    try:
        spec = importlib.util.spec_from_file_location(
            "gauss_fermi_package_validator", source
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load source-pinned Fermi validator")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(spec.name, None)
            raise
        return module
    finally:
        sys.path.remove(str(source.parent))


def derive_source(source: str) -> str:
    text = source
    for old, new, count in (
        (
            '"""Validate Candidate Fermi\'s exact kernel package and fail-closed DT."""',
            '"""Validate Candidate Gauss\'s exact Fermi-identity kernel package."""',
            1,
        ),
        ("import candidate_fermi as co", "import candidate_gauss as co", 1),
        ("co.FERMI_PATCH_SHA256S", "co.GAUSS_PATCH_SHA256S", 2),
        ("co.FERMI_PATCHES", "co.GAUSS_PATCHES", 3),
        ("co.FERMI_PATCH_SHA256", "co.GAUSS_PATCH_SHA256", 1),
        (
            '        b"Fermi",\n'
            '        b"addresses=0x69,0x68 passes=2 ",',
            '        b"Gauss",\n'
            '        b"addresses=0x69,0x68 passes=2 ",',
            1,
        ),
        (
            '        b"topology_mask=07 topology_expected=05 ",',
            '        b"d3_exact_mask=ff d3_exact_expected=1f ",',
            1,
        ),
        (
            "if len(entries) != 109 or tuple(entries[-7:]) != co.GAUSS_PATCHES:",
            "if len(entries) != 111 or tuple(entries[-9:]) != co.GAUSS_PATCHES:",
            1,
        ),
        ('print("validation=fermi-native-i2c6-kernel-package")',
         'print("validation=gauss-exact-d3-kernel-package")', 1),
        ('print("patch_count=109")', 'print("patch_count=111")', 1),
        (
            'print(f"fermi_patch_sha256={co.GAUSS_PATCH_SHA256}")',
            'print(f"gauss_patch_sha256={co.GAUSS_PATCH_SHA256}")',
            1,
        ),
        (
            'print("fermi_diagnostic=fixed-native-root-only-one-shot")',
            'print("gauss_diagnostic=fixed-exact-d3-root-only-one-shot")',
            1,
        ),
        (
            "if __name__ == \"__main__\":\n    raise SystemExit(main())",
            "if False:  # wrapper supplies the binary-audited CLI\n"
            "    raise SystemExit(main())",
            1,
        ),
    ):
        text = replace_exact(text, old, new, count)

    required = {
        "import candidate_gauss as co": 1,
        'CONFIG_LOCALVERSION="-gemini-fermi"': 1,
        "GEMINI_FERMI_20260728": 2,
        "CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y": 1,
        "mtk_i2c_fermi_fops": 1,
        "mtk_i2c_fermi_read": 1,
        "mtk_i2c_fermi_write": 1,
        "GEMINI_FERMI_NATIVE_DIAGNOSTIC state=ready": 1,
        "fermi-run-native": 1,
        'b"Gauss"': 1,
        "d3_exact_mask=ff d3_exact_expected=1f": 1,
        "tuple(entries[-9:]) != co.GAUSS_PATCHES": 1,
        'print("patch_count=111")': 1,
        "validation=gauss-exact-d3-kernel-package": 1,
        'print("da9214_provider=absent")': 1,
        'print("cpu8_cpu9=fail-closed-unrequested")': 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(
                f"derived Gauss package validator changed for {token!r}"
            )
    for stale in (
        "candidate_fermi",
        "topology_mask=07 topology_expected=05",
        'print("patch_count=109")',
        "validation=fermi-native-i2c6-kernel-package",
    ):
        if stale in text:
            raise ValueError(
                f"derived Gauss package validator retains stale token: {stale}"
            )
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    fermi = load_fermi(repository)
    return derive_source(fermi.load_source())


exec(compile(load_source(), __file__, "exec"), globals(), globals())


def load_binary_auditor() -> ModuleType:
    path = pathlib.Path(__file__).with_name("audit-gauss-binary.py")
    data = read_regular(path, "source-pinned Gauss binary auditor")
    if hashlib.sha256(data).hexdigest() != BINARY_AUDITOR_SHA256:
        raise ValueError("source-pinned Gauss binary auditor changed")
    spec = importlib.util.spec_from_file_location("gauss_package_binary_audit", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Gauss binary auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


def validate_with_fermi(
    repository: pathlib.Path,
    package: pathlib.Path,
    fermi_package: pathlib.Path,
    *,
    fermi_object: pathlib.Path,
    gauss_object: pathlib.Path,
    fermi_vmlinux: pathlib.Path,
    gauss_vmlinux: pathlib.Path,
):
    validate(repository, package)
    return load_binary_auditor().audit(
        fermi_package,
        package,
        fermi_object=fermi_object,
        gauss_object=gauss_object,
        fermi_vmlinux=fermi_vmlinux,
        gauss_vmlinux=gauss_vmlinux,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    parser.add_argument("--fermi-package", required=True, type=pathlib.Path)
    parser.add_argument("--fermi-object", required=True, type=pathlib.Path)
    parser.add_argument("--gauss-object", required=True, type=pathlib.Path)
    parser.add_argument("--fermi-vmlinux", required=True, type=pathlib.Path)
    parser.add_argument("--gauss-vmlinux", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        repository = args.repository.resolve(strict=True)
        package = args.package.resolve(strict=True)
        fermi_package = args.fermi_package.resolve(strict=True)
        fermi_object = args.fermi_object.resolve(strict=True)
        gauss_object = args.gauss_object.resolve(strict=True)
        fermi_vmlinux = args.fermi_vmlinux.resolve(strict=True)
        gauss_vmlinux = args.gauss_vmlinux.resolve(strict=True)
        binary_audit = validate_with_fermi(
            repository,
            package,
            fermi_package,
            fermi_object=fermi_object,
            gauss_object=gauss_object,
            fermi_vmlinux=fermi_vmlinux,
            gauss_vmlinux=gauss_vmlinux,
        )
        config = regular(package / "kernel.config", "kernel config")
        image = regular(package / "Image", "kernel Image")
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        gzip.BadGzipFile,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=gauss-exact-d3-kernel-package")
    print(f"profile={co.PROFILE}")
    print(f"patch_series={co.SERIES}")
    print("patch_count=111")
    print(f"gauss_patch_sha256={co.GAUSS_PATCH_SHA256}")
    print(f"config_sha256={digest(config)}")
    print(f"image_sha256={digest(image)}")
    print("kernel_identity=exact-fermi")
    print("lk_name=gemini-fermi")
    print("i2c6=mt6797-idvfs-childless")
    print("fermi_debugfs_identity=preserved")
    print("gauss_diagnostic=exact-d3-post-trigger-only")
    print("native_policy=unforced-packed-fifo")
    print("i2c_chardev=absent")
    print("da9214_provider=absent")
    print("cpu8_cpu9=fail-closed-unrequested")
    print(binary_audit.render().decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
