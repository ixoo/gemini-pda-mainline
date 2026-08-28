#!/usr/bin/env python3
"""Source-pin and specialize the independent serviceable-candidate validator."""

from __future__ import annotations
import hashlib
from pathlib import Path
import sys

SOURCE_SHA256 = "2499666d9061ef8648af0a85821d98640e2b15b97917bad997e80cd64220bf49"
SCRIPT = Path(__file__).resolve(); ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-serviceability-restoration/scripts/validate-candidate.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source validator changed")
try:
    package = Path(sys.argv[sys.argv.index("--package") + 1])
except (ValueError, IndexError):
    raise SystemExit("--package is required")
config_bytes = (package / "kernel.config").read_bytes()
if b"CONFIG_NVMEM=y\n" not in config_bytes:
    raise SystemExit("NVMEM core is not built in")
if b"CONFIG_NVMEM_MTK_ATAG_DEVINFO=y\n" not in config_bytes:
    raise SystemExit("ATAG devinfo provider is not built in")
text = SOURCE.read_text(encoding="utf-8")
anchor = "replacements = (\n"
injected = '''replacements = (
    ("RAW_SIZE = 6_934_528", "RAW_SIZE = 6_942_720", 1),
    ("96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", "58f47adde2079155fd56991f0d4271218c07a2124389fc7dc818febe4d2526f4", 1),
    ("4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", "0c4609d7cf35d40921202e064be03f1e245dd6ce41daefaa5380d98861ea2eba", 1),
    ("265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", "9b9118fd53b7b290803c52745b5fb8ab2559c0ba83765d30b6111d1bd01914d7", 1),
    ("4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", "38b9ce8a49510403531778de774a50d2d8fa6cf27d236f1c9d72369b67164182", 1),
    ("c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", "7190b805ef72806c6fa9ed8f8c9f1896af678b5fb0eee17e81c909087ba07c9d", 1),
    ("c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "296ce7f4f1fc88fc04d4aa58bbb1317648149154", 1),
'''
if text.count(anchor) != 1:
    raise SystemExit("unsafe ATAG-validator derivation: replacement anchor changed")
text = text.replace(anchor, injected, 1)
replacements = (
    ("current full-admission DT serviceability restoration", "config-restored ATAG-prerequisite candidate", 1),
    ("KERNEL_SIZE = 4_857_732", "KERNEL_SIZE = 4_866_019", 1),
    ("b1ff92e8c21aff6b850ed5ac68854b06e0f2059719cb0d50f0924b22345c3e68", "6971ee829af37a8515331ddf293eb8007829dd5d52e4abaf81f12754b5da0fcd", 1),
    ("f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", 1),
    ("c23cab60a1c9e8cf5715410c2af90828bd01d19f63a75dc9e313726ceb0f92d8", "80f9be2b58437b6edfcb630bb78fe218e7a70b70dd32d3e8b819f7c3767327b3", 1),
    ("gemini-mt6797-a72-admission-serviceable.boot.img", "gemini-mt6797-a72-admission-atag-prerequisite.boot.img", 1),
    ("validation=a72-admission-serviceability-restoration-independent", "validation=a72-admission-atag-prerequisite-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe ATAG-validator wrapper derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "admission_atag_prerequisite_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
