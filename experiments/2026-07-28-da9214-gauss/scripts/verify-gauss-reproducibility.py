#!/usr/bin/env python3
"""Verify two Gauss builds, binary deltas, and the 2x2 LK matrix offline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True


FERMI_VERIFIER = (
    "experiments/2026-07-28-da9214-fermi/"
    "scripts/verify-fermi-reproducibility.py"
)
FERMI_VERIFIER_SHA256 = (
    "11bbabe6f913dc93943e525f3587e1f1b2979ff5846f924c6edf19f5eb8ee4af"
)
GAUSS_CANDIDATE_MODULE_SHA256 = (
    "a4507861f0ed345715aa573c1604db57c95b5b9b08b27074eceb77d04daf200a"
)
GAUSS_PACKAGE_VALIDATOR_SHA256 = (
    "ad4eecf24f794b8b94a04408bdee5817220289650882448ba393bd76bca5a7bc"
)
GAUSS_BINARY_AUDITOR_SHA256 = (
    "4e9481ccb3243779c493392189a05deade71ab6acb5fefbd35307cd20330f137"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"verifier token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_fermi_verifier(repository: pathlib.Path) -> ModuleType:
    path = repository / FERMI_VERIFIER
    data = regular(path, "source-pinned Fermi reproducibility verifier")
    if hashlib.sha256(data).hexdigest() != FERMI_VERIFIER_SHA256:
        raise ValueError("source-pinned Fermi reproducibility verifier changed")
    spec = importlib.util.spec_from_file_location("gauss_fermi_verifier", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Fermi verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


def derive_source(source: str) -> str:
    text = source
    for old, new, count in (
        (
            '"""Verify two Fermi builds and their 2x2 LK assembly matrix '
            'offline."""',
            '"""Verify two Gauss builds and their 2x2 LK assembly matrix '
            'offline."""',
            1,
        ),
        ('("Vega", "Fermi", 25)', '("Vega", "Gauss", 25)', 1),
        ('("vega", "fermi", 7)', '("vega", "gauss", 7)', 1),
        ('SCRIPT_DIR / "candidate_fermi.py"', 'SCRIPT_DIR / "candidate_gauss.py"', 1),
        (
            'SCRIPT_DIR / "validate-package-fermi.py"',
            'SCRIPT_DIR / "validate-package-gauss.py"',
            1,
        ),
        (
            'CANDIDATE_MODULE_SHA256 = (\n'
            '    "3422bb29490f21f0410d4d45f521fc3ac89eff3679d117535c7b5dcf0cffe5e6"',
            'CANDIDATE_MODULE_SHA256 = (\n'
            f'    "{GAUSS_CANDIDATE_MODULE_SHA256}"',
            1,
        ),
        (
            'PACKAGE_VALIDATOR_SHA256 = (\n'
            '    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"',
            'PACKAGE_VALIDATOR_SHA256 = (\n'
            f'    "{GAUSS_PACKAGE_VALIDATOR_SHA256}"',
            1,
        ),
        ('"candidate=Fermi\\\\n"', '"candidate=Gauss\\\\n"', 1),
        (
            '"validation=fermi-two-build-2x2-reproducibility"',
            '"validation=gauss-two-build-2x2-reproducibility"',
            1,
        ),
        (
            '"Fermi verifier cannot restore exact Vega foundation"',
            '"Gauss verifier cannot restore exact Vega foundation"',
            1,
        ),
        (
            '"derived Fermi verifier contract changed for {token!r}"',
            '"derived Gauss verifier contract changed for {token!r}"',
            1,
        ),
        (
            '"derived Fermi verifier retained stale token: {stale}"',
            '"derived Gauss verifier retained stale token: {stale}"',
            1,
        ),
        (
            '"fermi_reproducibility_derived"',
            '"gauss_reproducibility_derived"',
            1,
        ),
    ):
        text = replace_exact(text, old, new, count)
    text = replace_exact(
        text,
        "    if restored != source:\n"
        '        raise ValueError("Gauss verifier cannot restore exact Vega '
        'foundation")\n'
        "    required = {",
        "    if restored != source:\n"
        '        raise ValueError("Gauss verifier cannot restore exact Vega '
        'foundation")\n'
        "    text = replace_exact(\n"
        "        text,\n"
        '        \'LK_EXPECTED_NAME = "gemini-gauss"\',\n'
        '        \'LK_EXPECTED_NAME = "gemini-fermi"\',\n'
        "        1,\n"
        "    )\n"
        "    required = {",
        1,
    )
    required = {
        'SCRIPT_DIR / "candidate_gauss.py"': 1,
        'SCRIPT_DIR / "validate-package-gauss.py"': 1,
        'LK_EXPECTED_NAME = "gemini-fermi"': 2,
        '"candidate=Gauss\\\\n"': 1,
        '"validation=gauss-two-build-2x2-reproducibility"': 1,
        GAUSS_CANDIDATE_MODULE_SHA256: 1,
        GAUSS_PACKAGE_VALIDATOR_SHA256: 1,
        "device_access=none": 1,
        "runtime_result=not-tested": 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(f"derived Gauss verifier changed for {token!r}")
    for forbidden in (
        "candidate_fermi.py",
        "validate-package-fermi.py",
        "candidate=Fermi",
        "validation=fermi-two-build-2x2-reproducibility",
    ):
        if forbidden in text:
            raise ValueError(f"derived Gauss verifier retained {forbidden!r}")
    return text


def load_implementation() -> ModuleType:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    fermi = load_fermi_verifier(repository)
    source_path = repository / fermi.QUASAR_VERIFIER
    source_data = regular(source_path, "source-pinned Quasar verifier")
    if hashlib.sha256(source_data).hexdigest() != fermi.QUASAR_VERIFIER_SHA256:
        raise ValueError("source-pinned Quasar reproducibility verifier changed")
    source = derive_source(fermi.derive_source(source_data.decode("utf-8", "strict")))
    name = "gauss_reproducibility_derived"
    module = ModuleType(name)
    module.__file__ = os.fspath(script)
    module.__package__ = ""
    sys.modules[name] = module
    try:
        exec(compile(source, os.fspath(script), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def load_binary_auditor() -> ModuleType:
    path = pathlib.Path(__file__).with_name("audit-gauss-binary.py")
    data = regular(path, "source-pinned Gauss binary auditor")
    if hashlib.sha256(data).hexdigest() != GAUSS_BINARY_AUDITOR_SHA256:
        raise ValueError("source-pinned Gauss binary auditor changed")
    spec = importlib.util.spec_from_file_location("gauss_repro_binary_audit", path)
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


_IMPL = load_implementation()
if (
    _IMPL.LK_EXPECTED_NAME != "gemini-fermi"
    or _IMPL.LK_EXPECTED_CMDLINE != "bootopt=64S3,32N2,64N2"
):
    raise ValueError("Gauss verifier changed Fermi's LK name or command line")

ContractError = _IMPL.ContractError
LK_EXPECTED_NAME = _IMPL.LK_EXPECTED_NAME
LK_EXPECTED_CMDLINE = _IMPL.LK_EXPECTED_CMDLINE


def validate_output(path: pathlib.Path) -> pathlib.Path:
    if (
        not path.name
        or path.name in {".", ".."}
        or path.exists()
        or path.is_symlink()
    ):
        raise ContractError("reproducibility-record output is invalid or exists")
    parent = path.parent.resolve(strict=True)
    info = parent.lstat()
    if parent.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ContractError("reproducibility-record output parent is unsafe")
    return parent / path.name


def write_output(path: pathlib.Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def verify(
    repository: pathlib.Path,
    packages: tuple[pathlib.Path, pathlib.Path],
    candidates: tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path],
    *,
    fermi_package: pathlib.Path,
    fermi_object: pathlib.Path,
    fermi_vmlinux: pathlib.Path,
    gauss_objects: tuple[pathlib.Path, pathlib.Path],
    gauss_vmlinuxes: tuple[pathlib.Path, pathlib.Path],
) -> bytes:
    base = _IMPL.verify(repository, packages, candidates)
    auditor = load_binary_auditor()
    audits = tuple(
        auditor.audit(
            fermi_package,
            packages[index],
            fermi_object=fermi_object,
            gauss_object=gauss_objects[index],
            fermi_vmlinux=fermi_vmlinux,
            gauss_vmlinux=gauss_vmlinuxes[index],
        )
        for index in range(2)
    )
    rendered = tuple(audit.render() for audit in audits)
    if rendered[0] != rendered[1]:
        raise ContractError("Gauss binary-audit build lanes differ")
    build = audits[0].build
    if build is None:
        raise ContractError("Gauss reproducibility lacks object/vmlinux audit")
    audit_sha256 = hashlib.sha256(rendered[0]).hexdigest()
    extra = (
        f"binary_auditor_sha256={GAUSS_BINARY_AUDITOR_SHA256}\n"
        f"binary_audit_sha256={audit_sha256}\n"
        f"fermi_image_sha256={audits[0].fermi_image_sha256}\n"
        f"gauss_image_sha256={audits[0].gauss_image_sha256}\n"
        f"fermi_object_sha256={build.fermi_object_sha256}\n"
        f"gauss_object_sha256={build.gauss_object_sha256}\n"
        f"fermi_vmlinux_sha256={build.fermi_vmlinux_sha256}\n"
        f"gauss_vmlinux_sha256={build.gauss_vmlinux_sha256}\n"
        "binary_delta=exact-five-source-deltas-plus-gnu-build-id\n"
        "lk_identity=exact-fermi-name-cmdline-dt-initramfs\n"
    ).encode("ascii")
    return base + extra


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--fermi-package", required=True, type=pathlib.Path)
    parser.add_argument("--fermi-object", required=True, type=pathlib.Path)
    parser.add_argument("--fermi-vmlinux", required=True, type=pathlib.Path)
    parser.add_argument("--package-a", required=True, type=pathlib.Path)
    parser.add_argument("--package-b", required=True, type=pathlib.Path)
    parser.add_argument("--gauss-object-a", required=True, type=pathlib.Path)
    parser.add_argument("--gauss-object-b", required=True, type=pathlib.Path)
    parser.add_argument("--gauss-vmlinux-a", required=True, type=pathlib.Path)
    parser.add_argument("--gauss-vmlinux-b", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-a-a", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-a-b", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-b-a", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-b-b", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        repository = args.repository.resolve(strict=True)
        packages = (
            args.package_a.resolve(strict=True),
            args.package_b.resolve(strict=True),
        )
        candidates = (
            args.candidate_a_a.resolve(strict=True),
            args.candidate_a_b.resolve(strict=True),
            args.candidate_b_a.resolve(strict=True),
            args.candidate_b_b.resolve(strict=True),
        )
        output = validate_output(args.output)
        record = verify(
            repository,
            packages,
            candidates,
            fermi_package=args.fermi_package.resolve(strict=True),
            fermi_object=args.fermi_object.resolve(strict=True),
            fermi_vmlinux=args.fermi_vmlinux.resolve(strict=True),
            gauss_objects=(
                args.gauss_object_a.resolve(strict=True),
                args.gauss_object_b.resolve(strict=True),
            ),
            gauss_vmlinuxes=(
                args.gauss_vmlinux_a.resolve(strict=True),
                args.gauss_vmlinux_b.resolve(strict=True),
            ),
        )
        write_output(output, record)
        print(record.decode("ascii"), end="")
        print(f"record_sha256={hashlib.sha256(record).hexdigest()}")
        print(f"output={output}")
        return 0
    except (
        ContractError,
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
