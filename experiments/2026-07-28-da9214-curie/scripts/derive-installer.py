#!/usr/bin/env python3
"""Derive Curie's guarded boot2 installer from exact Fermi tooling."""

from __future__ import annotations

import hashlib
import pathlib
import stat
import sys

sys.dont_write_bytecode = True


FERMI_DERIVER = (
    "experiments/2026-07-28-da9214-fermi/scripts/derive-installer.py"
)
FERMI_DERIVER_SHA256 = (
    "aed6e8b17efe5cd5ea029977a0d17e83986e98ef091c7411b1569fb34470762b"
)
FERMI_RECORD_SHA256 = (
    "bddb4e126d87289b253872063713d12e61a36b088e551e61afc63534634a5fd6"
)
FERMI_VERIFIER_SHA256 = (
    "11bbabe6f913dc93943e525f3587e1f1b2979ff5846f924c6edf19f5eb8ee4af"
)
FERMI_CANDIDATE_MODULE_SHA256 = (
    "3422bb29490f21f0410d4d45f521fc3ac89eff3679d117535c7b5dcf0cffe5e6"
)
FERMI_PACKAGE_VALIDATOR_SHA256 = (
    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"
)
CURIE_VERIFIER_SHA256 = (
    "5e758c9e8f196ce7725d4330b923e294f7cf84f01d76f5f519cdc70ade0e13ee"
)
CURIE_CANDIDATE_MODULE_SHA256 = (
    "47494b3280f0e098a61469f03f6c91dfe887260719c0f144cccde4101dcea683"
)
CURIE_PACKAGE_VALIDATOR_SHA256 = (
    "1984c5bd7e63ce6cf88d9fb59d015567fb4051028bea53a473b6c14edcc5b04c"
)
FERMI_PADDED_SHA256 = (
    "0234c36c401aba7901f76a5ab8cc034d3d6038e132c9d9ad505e983119c69534"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def derive_source(source: str) -> str:
    text = source
    for old, new, count in (
        (
            FERMI_RECORD_SHA256,
            "ca3d70bf605e1397b49eaf7a7446b2573555dde067546b1adb5c9ef50ac7d748",
            1,
        ),
        (FERMI_VERIFIER_SHA256, CURIE_VERIFIER_SHA256, 1),
        (
            FERMI_CANDIDATE_MODULE_SHA256,
            CURIE_CANDIDATE_MODULE_SHA256,
            1,
        ),
        (
            FERMI_PACKAGE_VALIDATOR_SHA256,
            CURIE_PACKAGE_VALIDATOR_SHA256,
            1,
        ),
        ("FERMI", "CURIE", 5),
        ("Fermi", "Curie", 41),
        ("fermi", "curie", 13),
    ):
        text = replace_exact(text, old, new, count)

    text = replace_exact(
        text,
        'QUASAR_PADDED_SHA256 = (\n'
        '    "73fceae91606ebf831e503585406df1e2be997edc9fddff1bcae9ec718c91d78"\n'
        ")",
        "FERMI_PADDED_SHA256 = (\n"
        f'    "{FERMI_PADDED_SHA256}"\n'
        ")",
        1,
    )
    text = replace_exact(
        text,
        'fields["candidate_padded_sha256"] == QUASAR_PADDED_SHA256',
        'fields["candidate_padded_sha256"] == FERMI_PADDED_SHA256',
        1,
    )
    text = replace_exact(
        text,
        'f"{QUASAR_PADDED_SHA256}"',
        'f"{FERMI_PADDED_SHA256}"',
        2,
    )
    text = replace_exact(
        text,
        "expected_predecessor_sha256={QUASAR_PADDED_SHA256}",
        "expected_predecessor_sha256={FERMI_PADDED_SHA256}",
        1,
    )
    text = replace_exact(
        text,
        "EXPECTED_CURRENT_QUASAR_PADDED_SHA256",
        "EXPECTED_CURRENT_FERMI_PADDED_SHA256",
        5,
    )
    text = replace_exact(
        text,
        "Quasar-installed-readback-verified",
        "Fermi-installed-readback-verified",
        2,
    )
    text = replace_exact(
        text,
        "exact Quasar predecessor",
        "exact Fermi predecessor",
        1,
    )

    required = {
        "import candidate_curie as co": 1,
        "2026-07-28-da9214-curie/results/build-reproducibility.txt": 1,
        (
            'REPRODUCIBILITY_RECORD_SHA256 = '
            '"ca3d70bf605e1397b49eaf7a7446b2573555dde067546b1adb5c9ef50ac7d748"'
        ): 1,
        "scripts/verify-curie-reproducibility.py": 1,
        "scripts/candidate_curie.py": 1,
        "scripts/validate-package-curie.py": 1,
        CURIE_VERIFIER_SHA256: 1,
        CURIE_CANDIDATE_MODULE_SHA256: 1,
        CURIE_PACKAGE_VALIDATOR_SHA256: 1,
        f'    "{FERMI_PADDED_SHA256}"': 1,
        "EXPECTED_CURRENT_FERMI_PADDED_SHA256": 5,
        "Fermi-installed-readback-verified": 2,
        '"curie-two-build-2x2-reproducibility"': 1,
        "validation=curie-installer-derived": 1,
        "candidate_label=Curie": 1,
        "reboot_or_slot_selection=none": 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(
                f"derived Curie installer generator changed for {token!r}"
            )
    for stale in (
        "candidate_fermi.py",
        "validate-package-fermi.py",
        "verify-fermi-reproducibility.py",
        '"fermi-two-build-2x2-reproducibility"',
        "validation=fermi-installer-derived",
        FERMI_RECORD_SHA256,
        FERMI_VERIFIER_SHA256,
        FERMI_CANDIDATE_MODULE_SHA256,
        FERMI_PACKAGE_VALIDATOR_SHA256,
    ):
        if stale in text:
            raise ValueError(
                f"derived Curie installer generator retained {stale!r}"
            )
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    path = repository / FERMI_DERIVER
    data = regular(path, "source-pinned Fermi installer generator")
    if hashlib.sha256(data).hexdigest() != FERMI_DERIVER_SHA256:
        raise ValueError("source-pinned Fermi installer generator changed")
    return derive_source(data.decode("utf-8", "strict"))


exec(compile(load_source(), __file__, "exec"), globals(), globals())
