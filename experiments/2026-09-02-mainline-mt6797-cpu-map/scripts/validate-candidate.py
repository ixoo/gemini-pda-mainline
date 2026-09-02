#!/usr/bin/env python3
"""Independently validate the exact MT6797 topology boot2 candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys


SOURCE_SHA256 = "17684507c202b40aa87ddc1df0a3f737d65af91da9a8e70ba1da5fbc52a93843"
COMPOSED_VALIDATOR_SHA256 = "40b8321c9734f2f21c050bf84e8716b5199570d4fa09de93ce3a3b6a32cc8350"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-completion-lock-repair-candidate.py"
)
COMPOSED_VALIDATOR = SCRIPT.with_name("validate-composed-dtb.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source completion-lock candidate validator changed")
if hashlib.sha256(COMPOSED_VALIDATOR.read_bytes()).hexdigest() != COMPOSED_VALIDATOR_SHA256:
    raise SystemExit("topology/provenance DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("CPU9 completion-path lock-repair container",
     "MT6797 4+4+2 topology container", 1),
    ("KERNEL_SIZE = 4_891_540", "KERNEL_SIZE = 4_892_100", 1),
    ("eba0aa21a2a650a64c0a3ba2b3d416932294eae2d257eb0e9b83b50df2335872",
     "7753563c80356b7b4822249a96c4baccf7d247bb9e9cf8747239e9292872d55c", 1),
    ("370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e",
     "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393", 1),
    ("2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9",
     "01c60771e1fc21c47a5a094482a555b286f8f5d046c009ba3e06d7e0212c6ac7", 1),
    ("29d47ed5d027d0787b583c196aff63e96d5a822b5137395dfc6607afefa33a2c",
     "1a393163e822c330ac9eefa00e873723b5d496fd7c48a10a16e5047df7aedfa1", 1),
    ("aae595e7884559d6f298a15c2a7f447c3b1b9c9f97d973ac8bc50169107bd128",
     "0d99f36e5e6b10e1743fe88cc6f59f357805ab287d58f5c2b57be3aac7311742", 1),
    ("f554c691007e26e2b8fb234320f291f10a33fdf0",
     "2e661e90a6b4d158400b4e5fe832d39f48abd10b", 1),
    ("38 61 52 0 ff 5c b4 b2 cb 41 f4 25 78 e3 e a1 aa ce 2f b0 2c d2 39 f0 e0 b9 fd 66 b7 e1 17 ad",
     "e3 9 96 b2 60 4d f0 7b 99 bf 6d 48 29 40 fa a ff 65 85 c8 6c e2 fd 7e d6 c4 2b 13 68 2c 58 65", 1),
    ("validation=a72-cpu9-completion-lock-repair-independent",
     "validation=a72-cpu9-topology-container-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe topology candidate validation derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "mt6797_cpu_map_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)

# The inherited validator proves the container and its package semantics.  Add
# the exact independent topology/provenance proof over the DT supplied to it.
arguments = sys.argv[1:]
def value(option: str) -> str:
    try:
        index = arguments.index(option)
        return arguments[index + 1]
    except (ValueError, IndexError):
        raise SystemExit(f"missing required argument for topology validation: {option}")

subprocess.run(
    [
        sys.executable,
        str(COMPOSED_VALIDATOR),
        "--serviceability-dtb",
        str(ROOT / "artifacts/mt6797-cpu-map-composition/topology-serviceability.dtb"),
        "--package-dtb",
        str(Path(value("--package")) / "dtbs/mediatek/mt6797-gemini-pda.dtb"),
        "--record-json",
        str(Path(value("--package")) / "provenance/a41-record.json"),
        "--candidate",
        value("--control-dtb"),
    ],
    check=True,
)
print("topology_validation=exact-4+4+2")
print("boot_candidate=true")
