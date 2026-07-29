#!/usr/bin/env python3
"""Strictly classify Gauss's exact-D3 debugfs result."""

from __future__ import annotations

import hashlib
import pathlib
import stat
import sys

sys.dont_write_bytecode = True


FERMI_VALIDATOR = (
    "experiments/2026-07-28-da9214-fermi/scripts/validate-fermi-result.py"
)
FERMI_VALIDATOR_SHA256 = (
    "546dd097a7497627351684759d60377f14b7b4aae1a869a5e1eafda767cde3a3"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"result-validator token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def derive_source(source: str) -> str:
    replacements = (
        (
            '"""Strictly classify Fermi\'s fixed legacy-topology debugfs result."""',
            '"""Strictly classify Gauss\'s exact-D3 debugfs result."""',
            1,
        ),
        (
            '    "topology_mask",\n'
            '    "topology_expected",',
            '    "d3_exact_mask",\n'
            '    "d3_exact_expected",',
            1,
        ),
        (
            "EXPECTED_FIELDS = "
            "(0xD9, 0xD0, 0xC0, 0x05, 0x00, 0x00, 0x00) * 2",
            "EXPECTED_FIELDS = "
            "(0xD9, 0xD0, 0xC0, 0x1F, 0x00, 0x00, 0x00) * 2",
            1,
        ),
        ('    "topology-stable",', '    "exact-d3-stable",', 1),
        (
            '            "signature=d9,d0,c0-twice",\n'
            '            "topology=(d3&07)==05-twice",\n'
            '            "stability=d3,5e,d9,da-full-byte-pair-equality",',
            '            f"observed_signature_passes="\n'
            '            f"{int(int(self.header[\'value_validated\']) >= 3) + int(int(self.header[\'value_validated\']) >= 10)}",\n'
            '            f"observed_d3_exact_validations="\n'
            '            f"{sum(sample[\'index\'] == \'3\' and sample[\'value_validated\'] == \'1\' for sample in self.samples)}",\n'
            '            f"observed_stability_pairs={self.header[\'stability_validated\']}",\n'
            '            "required_signature=d9,d0,c0-two-passes",\n'
            '            "required_d3=d3-exact-1f-two-passes",\n'
            '            "required_stability=d3,5e,d9,da-full-byte-pair-equality",',
            1,
        ),
        (
            '"expected_signature=d9,d0,c0 topology_register=d3 "\n'
            '        "topology_mask=07 topology_expected=05 "',
            '"expected_signature=d9,d0,c0 topology_register=d3 "\n'
            '        "d3_exact_mask=ff d3_exact_expected=1f "',
            1,
        ),
        (
            '        "topology_mask": "07",\n'
            '        "topology_expected": "05",',
            '        "d3_exact_mask": "ff",\n'
            '        "d3_exact_expected": "1f",',
            1,
        ),
        (
            "if index == 3 and value & 0x07 != 0x05:",
            "if index == 3 and value != 0x1F:",
            2,
        ),
        (
            'raise ResultError(f"Fermi sample {ordinal} topology changed")',
            'raise ResultError(\n'
            '                f"Fermi sample {ordinal} exact D3 changed"\n'
            "            )",
            1,
        ),
        (
            '"validation=fermi-topology-result"',
            '"validation=gauss-exact-d3-result"',
            1,
        ),
    )
    text = source
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)
    text = replace_exact(text, "Fermi", "Gauss", 52)
    text = replace_exact(text, "fermi", "gauss", 1)
    required = {
        "validation=gauss-exact-d3-result": 1,
        '"candidate": "Gauss"': 1,
        "candidate=Gauss state=ready": 1,
        '"topology_register"': 2,
        '"d3_exact_mask"': 2,
        '"d3_exact_expected"': 2,
        '"d3_exact_mask": "ff"': 1,
        '"d3_exact_expected": "1f"': 1,
        "topology_register=d3": 1,
        "d3_exact_mask=ff": 1,
        "d3_exact_expected=1f": 1,
        "(0xD9, 0xD0, 0xC0, 0x1F, 0x00, 0x00, 0x00) * 2": 1,
        '"exact-d3-stable"': 1,
        "value != 0x1F": 2,
        "observed_signature_passes=": 1,
        "observed_d3_exact_validations=": 1,
        "observed_stability_pairs=": 1,
        "required_signature=d9,d0,c0-two-passes": 1,
        "required_d3=d3-exact-1f-two-passes": 1,
        "required_stability=d3,5e,d9,da-full-byte-pair-equality": 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(
                f"derived Gauss result validator changed for {token!r}"
            )
    for stale in (
        "candidate=Fermi",
        '"candidate": "Fermi"',
        "validation=fermi-topology-result",
        '"topology_mask"',
        '"topology_expected"',
        "topology_mask=07",
        "topology_expected=05",
        "topology-stable",
        "signature=d9,d0,c0-twice",
    ):
        if stale in text:
            raise ValueError(
                f"derived Gauss result validator retains stale token: {stale}"
            )
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    path = repository / FERMI_VALIDATOR
    data = regular(path, "source-pinned Fermi result validator")
    if hashlib.sha256(data).hexdigest() != FERMI_VALIDATOR_SHA256:
        raise ValueError("source-pinned Fermi result validator changed")
    return derive_source(data.decode("utf-8", "strict"))


exec(compile(load_source(), __file__, "exec"), globals(), globals())
