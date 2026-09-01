#!/usr/bin/env python3
"""Independently validate the CPU9 configuration-identity repair container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6ad64ff391ad3573b4e6c16348dc3c4bb84de464f6330e3a9094c15c15fe749a"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("same-boot CPU9 production candidate",
     "CPU9 production configuration-identity repair candidate", 1),
    ("KERNEL_SIZE = 4_886_008", "KERNEL_SIZE = 4_886_009", 1),
    ("dd4b935862ce12d7bc2179aba3a81621ab4bdbcfdb069ad9977695a136315ef2",
     "e7ea9113a5288990ea54205339ea67b18056fcb4461b5dbecaf2ab45e96a1e15", 1),
    ("fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468",
     "118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562", 1),
    ("39074a71cd485c493f530a23858b9be1f37cdca5b35ca0c95f291357e8f62e08",
     "aee66bcce2413083638d64be3262aab1d3c92452814967d03d9a7a853c32761c", 1),
    ("01830c2f38773d501117501e22f55bb12f0c1740f1dac00a3a6993295684c364",
     "192a61b071a8c62ad976b058b53b93edfde0f3747ceefcece36309125edff2fe", 1),
    ("603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b",
     "ca7e95162c9e222d47991f6580682354cbb445d994a954950455ca5e6b9c80c3", 1),
    ("59f069542f20c63452eaa55bd4576def05f469bbf0886abf4536c7b6583b2a70",
     "a7732de1428e924187788fb2f971035f0beb4868feee6713bd10d9876e44265f", 1),
    ("f6a1ea0b96243207a1d8b6742fae2ecbfb87dda210320b5e214025a596db895a",
     "5f8b1722c664c81d9c168c388c1f80037ea4dc16369ca94d04081cf897fc1c93", 1),
    ("gemini-mt6797-a72-cpu9-controller.boot.img",
     "gemini-mt6797-a72-cpu9-config-identity-repair.boot.img", 1),
    ("479f938f96bf34e49b3adef25b844d23d6fb2c4d",
     "45582eea878418e64cacf5a67d9b0b92821a25ad", 1),
    ("c1 9c 8f 40 26 e8 9f 8f 41 a 76 79 14 d5 e2 26 5c e5 24 2d fb 4c c2 5e e1 88 16 41 da f0 48 a3",
     "51 bc d3 55 84 f2 e2 f7 ce 76 b1 4b 11 92 e7 a2 2a 42 23 43 53 e7 2d a7 f7 1f 3e 87 19 db 5b cb", 1),
    ("validation=a72-cpu9-controller-independent",
     "validation=a72-cpu9-config-identity-repair-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repaired CPU9 candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_repair_candidate_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
