#!/usr/bin/env python3
"""Source-pin and specialize the independent READY-bound candidate validator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

SOURCE_SHA256 = "e91e78110870b355590dedb25528deaa1626f7e90947bcec6d7e996b1e22c895"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-atag-prerequisite/scripts/validate-candidate.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source validator changed")
try:
    package = Path(sys.argv[sys.argv.index("--package") + 1])
except (ValueError, IndexError):
    raise SystemExit("--package is required")
build = json.loads((package / "provenance/build.json").read_text(encoding="utf-8"))
expected_build = {
    "repository_commit": "5abde763316ab358d7f5cb1a3b6a461eb0a2ed99",
    "build_profile": "a72-admission-live-trigger-candidate",
    "kernel_release": "7.1.3-gemini-a72-admission-live",
    "config_inputs_sha256": "5968c24f1904c0559dea25480c41fbc7db49e822dc3600d1bdd7632330853f40",
    "source_sha256": "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc",
    "patchset_sha256": "b74e3ce223cef0fef1fda072ac9bc3d8d82bcb71ffb0a617b96cea31e266e4a4",
}
if any(build.get(key) != value for key, value in expected_build.items()):
    raise SystemExit("READY-bound package provenance changed")
a41 = json.loads((package / "provenance/a41-record.json").read_text(encoding="utf-8"))
if a41.get("digests", {}).get("config-inputs-sha256") != expected_build["config_inputs_sha256"]:
    raise SystemExit("A41 configuration-input identity changed")
if a41.get("target_cpus") != [8, 9] or a41.get("target_mpidrs") != [512, 513]:
    raise SystemExit("A41 target pair changed")
symbols = (package / "System.map").read_text(encoding="ascii")
for symbol in (
    "arm64_get_late_cpu_ready_token",
    "arm64_validate_late_cpu_preflight",
    "mt6797_a72_admission_add_cpu",
    "mt6797_a72_admission_trigger_run",
    "mt6797_a72_admission_run",
):
    if symbols.count(f" {symbol}\n") != 1:
        raise SystemExit(f"linked symbol changed: {symbol}")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("RAW_SIZE = 6_942_720", "RAW_SIZE = 6_948_864", 1),
    ("KERNEL_SIZE = 4_866_019", "KERNEL_SIZE = 4_871_165", 1),
    ("296ce7f4f1fc88fc04d4aa58bbb1317648149154", "5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", 1),
    ("58f47adde2079155fd56991f0d4271218c07a2124389fc7dc818febe4d2526f4", "68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", 1),
    ("0c4609d7cf35d40921202e064be03f1e245dd6ce41daefaa5380d98861ea2eba", "2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", 1),
    ("38b9ce8a49510403531778de774a50d2d8fa6cf27d236f1c9d72369b67164182", "073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", 1),
    ("7190b805ef72806c6fa9ed8f8c9f1896af678b5fb0eee17e81c909087ba07c9d", "45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", 1),
    ("6971ee829af37a8515331ddf293eb8007829dd5d52e4abaf81f12754b5da0fcd", "4c8cf8e05666919e261d1f09ae1b3194f6ba1e444d3ed1b52bc59321ff638d47", 1),
    ("fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7", 1),
    ("80f9be2b58437b6edfcb630bb78fe218e7a70b70dd32d3e8b819f7c3767327b3", "37ff44d6496d1ce8d4fc0cecb23d62c95a2a980e8c6c83a414399d260950045f", 1),
    ("config-restored ATAG-prerequisite candidate", "READY-bound CPU8 admission candidate", 1),
    ("gemini-mt6797-a72-admission-atag-prerequisite.boot.img", "gemini-mt6797-a72-ready-admission.boot.img", 1),
    ("validation=a72-admission-atag-prerequisite-independent", "validation=a72-ready-admission-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe READY-validator derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "a72_ready_admission_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
