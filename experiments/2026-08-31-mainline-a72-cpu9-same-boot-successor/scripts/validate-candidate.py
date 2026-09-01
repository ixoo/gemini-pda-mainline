#!/usr/bin/env python3
"""Source-pin and specialize the independent production CPU9 validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "0e646c153a74c33018141da7fe43353347f9f0dc06296ac9a72006f1e9acbf00"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/validate-candidate.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source validator changed")

text = SOURCE.read_text(encoding="utf-8")
extra = '''replacements = (
    ("a72-admission-live-trigger-candidate", "a72-cpu9-controller-candidate", 1),
    ("7.1.3-gemini-a72-admission-live", "7.1.3-gemini-cpu9-controller", 1),
    (''' + repr('''    provenance = json.loads(build_json)''') + ''', ''' + repr('''    provenance = json.loads(build_json)
    required_config = (
        b"CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP=y\\n",
        b"CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER=y\\n",
        b"CONFIG_MTK_MT6797_A72_CPU9_EXECUTOR=y\\n",
        b"CONFIG_MTK_MT6797_A72_CPU9_BINDER=y\\n",
        b"CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER=y\\n",
        b"CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y\\n",
    )
    require(all(symbol in config for symbol in required_config), "production CPU9 config changed")
    require(b"CONFIG_KUNIT=y\\n" not in config, "KUnit leaked into production config")
    for symbol in (
        b"CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER_KUNIT_TEST=y\\n",
        b"CONFIG_MTK_MT6797_A72_CPU9_EXECUTOR_KUNIT_TEST=y\\n",
        b"CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST=y\\n",
        b"CONFIG_MTK_MT6797_A72_CPU9_ADMISSION_CONTROLLER_KUNIT_TEST=y\\n",
    ):
        require(symbol not in config, "CPU9 KUnit suite leaked into production config")
    required_symbols = (
        b"gemini_cpu9_ledger_begin",
        b"mt6797_a72_cpu9_binder_prepare",
        b"mt6797_a72_cpu9_binder_diagnostic_snapshot",
        b"mt6797_a72_cpu9_admission_run",
    )
    require(all(symbol in system_map for symbol in required_symbols), "production CPU9 symbol changed")''') + ''', 1),
'''
if text.count("replacements = (\n") != 1:
    raise SystemExit("unsafe CPU9 candidate-validator derivation: replacement table changed")
text = text.replace("replacements = (\n", extra, 1)
replacements = (
    ("provenance/serviceability CPU8 candidate", "same-boot CPU9 production candidate", 1),
    ("RAW_SIZE = 6_948_864", "RAW_SIZE = 6_963_200", 1),
    ("KERNEL_SIZE = 4_872_077", "KERNEL_SIZE = 4_886_008", 1),
    ("1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa",
     "dd4b935862ce12d7bc2179aba3a81621ab4bdbcfdb069ad9977695a136315ef2", 1),
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a",
     "fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468", 1),
    ("68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c",
     "39074a71cd485c493f530a23858b9be1f37cdca5b35ca0c95f291357e8f62e08", 1),
    ("2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce",
     "01830c2f38773d501117501e22f55bb12f0c1740f1dac00a3a6993295684c364", 1),
    ("8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2",
     "603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b", 1),
    ("9b9118fd53b7b290803c52745b5fb8ab2559c0ba83765d30b6111d1bd01914d7",
     "3ffcd08ec15642de4470a00d7fdf495318741cfb0bce1c65d13f5bd80001d56b", 1),
    ("073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b",
     "0b2781ca1d8dcf195e7b3f786da0a0a6f2306a391f9bacb7da3f0448e4af7fb1", 1),
    ("45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda",
     "59f069542f20c63452eaa55bd4576def05f469bbf0886abf4536c7b6583b2a70", 1),
    ("388c099eaab6c4660db869fedf61e7e4b49c97de88b754c0dd407d4a88606f44",
     "f6a1ea0b96243207a1d8b6742fae2ecbfb87dda210320b5e214025a596db895a", 1),
    ("gemini-mt6797-a72-provenance-serviceability.boot.img",
     "gemini-mt6797-a72-cpu9-controller.boot.img", 1),
    ("5abde763316ab358d7f5cb1a3b6a461eb0a2ed99",
     "479f938f96bf34e49b3adef25b844d23d6fb2c4d", 1),
    ("68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a",
     "c1 9c 8f 40 26 e8 9f 8f 41 a 76 79 14 d5 e2 26 5c e5 24 2d fb 4c c2 5e e1 88 16 41 da f0 48 a3", 1),
    ("validation=a72-provenance-serviceability-independent",
     "validation=a72-cpu9-controller-independent", 1),
    (r'print("candidate_cpu8_request_paths=1")\n    print("cpu8_requests=0")',
     r'print("candidate_cpu8_request_paths=1")\n    print("candidate_cpu9_request_paths=1")\n    print("cpu8_requests_during_validation=0")\n    print("cpu9_requests_during_validation=0")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 candidate-validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "a72_cpu9_controller_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
