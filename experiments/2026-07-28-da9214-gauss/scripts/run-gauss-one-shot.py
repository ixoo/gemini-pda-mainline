#!/usr/bin/env python3
"""Run Gauss's exact-D3 diagnostic once through Fermi's USB endpoint."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True


FERMI_RUNNER = (
    "experiments/2026-07-28-da9214-fermi/scripts/run-fermi-one-shot.py"
)
FERMI_RUNNER_SHA256 = (
    "e391f02ff5cc99296e1508e4a7b5bc4211c025a1e65f7f7a85adc6caa6fe7e11"
)
GAUSS_PACKAGE_VALIDATOR_SHA256 = (
    "ad4eecf24f794b8b94a04408bdee5817220289650882448ba393bd76bca5a7bc"
)
GAUSS_RESULT_VALIDATOR_SHA256 = (
    "d3cd1a1eaa284f99391f926f31165c50813c6b0811a070591635e703cf99f734"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"runner token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_fermi_runner(repository: pathlib.Path) -> ModuleType:
    path = repository / FERMI_RUNNER
    data = regular(path, "source-pinned Fermi one-shot runner")
    if hashlib.sha256(data).hexdigest() != FERMI_RUNNER_SHA256:
        raise ValueError("source-pinned Fermi one-shot runner changed")
    spec = importlib.util.spec_from_file_location("gauss_fermi_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Fermi runner")
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
            '"""Run Fermi\'s fixed native-path diagnostic once and preserve '
            'evidence."""',
            '"""Run Gauss\'s exact-D3 diagnostic once through Fermi\'s '
            'endpoint."""',
            1,
        ),
        (
            'PACKAGE_VALIDATOR_SHA256 = (\n'
            '    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"',
            'PACKAGE_VALIDATOR_SHA256 = (\n'
            f'    "{GAUSS_PACKAGE_VALIDATOR_SHA256}"',
            1,
        ),
        (
            'RESULT_VALIDATOR_SHA256 = (\n'
            '    "546dd097a7497627351684759d60377f14b7b4aae1a869a5e1eafda767cde3a3"',
            'RESULT_VALIDATOR_SHA256 = (\n'
            f'    "{GAUSS_RESULT_VALIDATOR_SHA256}"',
            1,
        ),
        (
            '    if restored != source:\n'
            '        raise RunnerError("Fermi runner cannot restore exact '
            'Vega foundation")\n'
            "    required = {",
            '    if restored != source:\n'
            '        raise RunnerError("Fermi runner cannot restore exact '
            'Vega foundation")\n'
            "    text = replace_exact(\n"
            "        text,\n"
            '        "import candidate_fermi as co",\n'
            '        "import candidate_gauss as co",\n'
            "        1,\n"
            "    )\n"
            "    text = replace_exact(\n"
            "        text,\n"
            '        \'"validate-package-fermi.py"\',\n'
            '        \'"validate-package-gauss.py"\',\n'
            "        1,\n"
            "    )\n"
            "    required = {",
            1,
        ),
        (
            '"import candidate_fermi as co": 1,',
            '"import candidate_gauss as co": 1,',
            1,
        ),
        (
            '\'"validate-package-fermi.py"\': 1,',
            '\'"validate-package-gauss.py"\': 1,',
            1,
        ),
        (
            '        "candidate_vega",\n'
            '        "validate-package-vega.py",',
            '        "candidate_vega",\n'
            '        "candidate_fermi",\n'
            '        "validate-package-vega.py",\n'
            '        "validate-package-fermi.py",',
            1,
        ),
        (
            'pathlib.Path(__file__).with_name("validate-fermi-result.py")',
            'pathlib.Path(__file__).with_name("validate-gauss-result.py")',
            1,
        ),
        ('"Fermi result validator"', '"Gauss result validator"', 1),
        (
            '"fermi_result_validator_runtime"',
            '"gauss_result_validator_runtime"',
            1,
        ),
        (
            '"validation=fermi-runtime-one-shot"',
            '"validation=gauss-runtime-one-shot"',
            1,
        ),
        (
            '"validation=fermi-exact-serviceability-gated-one-shot"',
            '"validation=gauss-exact-d3-serviceability-gated-one-shot"',
            1,
        ),
    ):
        text = replace_exact(text, old, new, count)
    required = {
        "import candidate_gauss as co": 2,
        '"validate-package-gauss.py"': 2,
        '"validate-gauss-result.py"': 1,
        'KERNEL_RELEASE = "7.1.3-gemini-fermi"': 1,
        "GEMINI_FERMI_20260728": 2,
        "fermi-run-native": 3,
        "guard_path=/run/fermi-run-all.invoked": 1,
        "debugfs_root=/run/fermi-debugfs": 1,
        "validation=gauss-runtime-one-shot": 1,
        "validation=gauss-exact-d3-serviceability-gated-one-shot": 1,
        GAUSS_PACKAGE_VALIDATOR_SHA256: 1,
        GAUSS_RESULT_VALIDATOR_SHA256: 1,
        "post_capture=unconditional-even-after-negative-write": 2,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(f"derived Gauss runner changed for {token!r}")
    for forbidden in (
        "candidate_quasar",
        "validate-package-quasar.py",
        "validate-quasar-result.py",
        "gemini-gauss",
        "GEMINI_GAUSS",
        "gauss-run-native",
    ):
        if forbidden in text:
            raise ValueError(f"derived Gauss runner retained {forbidden!r}")
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    fermi = load_fermi_runner(repository)
    return derive_source(fermi.load_source())


exec(compile(load_source(), __file__, "exec"), globals(), globals())
