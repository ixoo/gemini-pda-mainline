#!/usr/bin/env python3
"""Independently validate the production CPU9 progress-ledger container."""

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
     "CPU9 progress-ledger diagnostic candidate", 1),
    ("RAW_SIZE = 6_963_200", "RAW_SIZE = 6_965_248", 1),
    ("KERNEL_SIZE = 4_886_008", "KERNEL_SIZE = 4_886_744", 1),
    ("dd4b935862ce12d7bc2179aba3a81621ab4bdbcfdb069ad9977695a136315ef2",
     "85d3b591cdee4635cf0e5b889011459a4cb7e48f4ddd3ac2df0c20720e1c8833", 1),
    ("fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468",
     "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72", 1),
    ("39074a71cd485c493f530a23858b9be1f37cdca5b35ca0c95f291357e8f62e08",
     "c4e84c90a9843b8d5a7beaf8ce6c7874d1d8e972f14fa91a4e837800ecd0b5f6", 1),
    ("01830c2f38773d501117501e22f55bb12f0c1740f1dac00a3a6993295684c364",
     "4c4f43328c6c824045d118510183b1d7f2fdacd92ddeaf4f6b75a59ad76cf9b8", 1),
    ("603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b",
     "08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd", 1),
    ("3ffcd08ec15642de4470a00d7fdf495318741cfb0bce1c65d13f5bd80001d56b",
     "d450a5135a9689b40699273d09b74cadd873088317603d345ccc66cd25d027a8", 1),
    ("0b2781ca1d8dcf195e7b3f786da0a0a6f2306a391f9bacb7da3f0448e4af7fb1",
     "a657dd5c033d18b3d7638875e6603c6c9486fd9b13c2f9d9f4a9c60c82875534", 1),
    ("59f069542f20c63452eaa55bd4576def05f469bbf0886abf4536c7b6583b2a70",
     "e262795a456a933a16b0658edb699bb3ea444e04bfa842488cf04d794f545a28", 1),
    ("f6a1ea0b96243207a1d8b6742fae2ecbfb87dda210320b5e214025a596db895a",
     "e398c2b9156c31f02cb126be40204608b17f9df8a44a0f2268e05545d40448e2", 1),
    ("gemini-mt6797-a72-cpu9-controller.boot.img",
     "gemini-mt6797-a72-cpu9-progress.boot.img", 1),
    ("479f938f96bf34e49b3adef25b844d23d6fb2c4d",
     "630350185c9126f2c96be7295216c5ff1ee08c83", 1),
    ("c1 9c 8f 40 26 e8 9f 8f 41 a 76 79 14 d5 e2 26 5c e5 24 2d fb 4c c2 5e e1 88 16 41 da f0 48 a3",
     "ed 3a 4b f0 85 10 bd d5 c1 7 c1 10 18 3b 1c e9 85 df c5 59 4c 8a fa e5 4b df fe 0 6f b5 66 6", 1),
    ("a72-cpu9-controller-candidate", "a72-cpu9-progress-candidate", 1),
    ("7.1.3-gemini-cpu9-controller", "7.1.3-gemini-cpu9-progress", 1),
    ('b"CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER=y\\\\n",',
     'b"CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER=y\\\\n",\n        b"CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER=y\\\\n",\n        b\'CONFIG_LOCALVERSION="-gemini-cpu9-progress"\\\\n\',', 1),
    ('require(all(symbol in config for symbol in required_config), "production CPU9 config changed")',
     'require(all(symbol in config for symbol in required_config), "production CPU9 diagnostic config changed")\n    require(b"CONFIG_PSTORE_GEMINI_ADMISSION_TRACE=y\\\\n" not in config, "legacy admission trace leaked into diagnostic config")', 1),
    ('b"CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST=y\\\\n",',
     'b"CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST=y\\\\n",\n        b"CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER_KUNIT_TEST=y\\\\n",', 1),
    ('b"gemini_cpu9_ledger_begin",',
     'b"gemini_cpu9_ledger_begin",\n        b"gemini_cpu9_progress_begin",\n        b"gemini_cpu9_progress_checkpoint",', 1),
    ("validation=a72-cpu9-controller-independent",
     "validation=a72-cpu9-progress-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_progress_candidate_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
