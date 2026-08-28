#!/usr/bin/env python3
"""Source-pin and specialize the independent current-Image control validator."""

from __future__ import annotations
import hashlib
from pathlib import Path

SOURCE_SHA256 = "29b35ea8c07abcfa840e868a7b23075a49d1b0323f39faa0ffedb1e605f8ac96"
SCRIPT = Path(__file__).resolve(); ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-live-image-runtime-dt-control/scripts/validate-candidate.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source validator changed")
text = SOURCE.read_text(encoding="utf-8")
old_semantics = '''    require(dtb.count(b"mediatek,mt6797-a72-platform-state") == 1, "platform-state compatible changed")
    require(dtb.count(b"mediatek,mt6797-a72-platform-provider-clock-observer") == 1, "observer compatible changed")
    require(b"mt6797-a72-admission-controller" not in dtb and b"mt6797-a72-admission-binder" not in dtb, "admission node leaked into DT")'''
new_semantics = '''    require(dtb.count(b"mediatek,mt6797-a72-platform-state") == 1, "platform-state compatible changed")
    require(dtb.count(b"mediatek,mt6797-a72-admission-controller") == 1, "controller compatible changed")
    require(dtb.count(b"mediatek,mt6797-a72-binder") == 1, "binder compatible changed")
    require(b"mt6797-a72-platform-provider-clock-observer" not in dtb, "standalone observer leaked into DT")
    for node in ("/usb@11271000", "/t-phy@11290000", "/t-phy@11290000/usb-phy@11290800", "/i2c@1101c000", "/i2c@1101c000/gpio-expander@5b", "/keyboard-matrix"):
        result = subprocess.run(["fdtget", "-ts", str(args.control_dtb), node, "status"], check=True, capture_output=True, text=True)
        require(result.stdout.strip() == "okay", f"serviceability node is not enabled: {node}")'''
replacements = (
    ("current-Image/runtime-proven-DT control", "current full-admission DT serviceability restoration", 1),
    ("KERNEL_SIZE = 4_857_270", "KERNEL_SIZE = 4_857_732", 1),
    ("35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12", "b1ff92e8c21aff6b850ed5ac68854b06e0f2059719cb0d50f0924b22345c3e68", 1),
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", 1),
    ("90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", "1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c", 1),
    ("a029c258c19c96a234cb5cafe4c1bb35a36bac2beadbe8e2ea547da8870719d1", "c23cab60a1c9e8cf5715410c2af90828bd01d19f63a75dc9e313726ceb0f92d8", 1),
    ("gemini-mt6797-a72-live-image-runtime-dt-control.boot.img", "gemini-mt6797-a72-admission-serviceable.boot.img", 1),
    ('b"gemini-a72dtctl"', 'b"gemini-a72svc"', 1),
    (old_semantics, new_semantics, 1),
    ("validation=a72-live-image-runtime-dt-control-independent", "validation=a72-admission-serviceability-restoration-independent", 1),
    ('print("controller_nodes=0")', 'print("controller_nodes=1")', 1),
    ('print("binder_nodes=0")', 'print("binder_nodes=1")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe independent-validator derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "admission_serviceability_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
namespace["main"]()
