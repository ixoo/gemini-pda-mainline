#!/usr/bin/env python3
"""Source-pin and specialize the independent Android-v0/LK validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "29b35ea8c07abcfa840e868a7b23075a49d1b0323f39faa0ffedb1e605f8ac96"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
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
    require(dtb.count(b"planet,gemini-a72-runtime-binding-v1") == 1, "runtime provenance compatible changed")
    require(b"mt6797-a72-platform-provider-clock-observer" not in dtb, "standalone observer leaked into admission DT")
    for node in ("/usb@11271000", "/t-phy@11290000", "/t-phy@11290000/usb-phy@11290800", "/i2c@1101c000", "/i2c@1101c000/gpio-expander@5b", "/keyboard-matrix", "/dvfsp-clock-backend@1001a000", "/dvfsp-bigidvfs-backend"):
        result = subprocess.run(["fdtget", "-ts", str(args.control_dtb), node, "status"], check=True, capture_output=True, text=True)
        require(result.stdout.strip() == "okay", f"serviceability/admission node is not enabled: {node}")
    identity = subprocess.run(["fdtget", "-tbx", str(args.control_dtb), "/chosen/gemini-late-cpu-provenance", "record-identity"], check=True, capture_output=True, text=True)
    require(identity.stdout.strip() == "68 b8 64 d9 6a bb 58 fb 68 5f 41 45 82 7f fc c9 cc cc 37 2a 6c 26 95 ad d0 e1 44 98 ea 54 fc a", "runtime provenance identity changed")'''
replacements = (
    ("current-Image/runtime-proven-DT control", "provenance/serviceability CPU8 candidate", 1),
    ("RAW_SIZE = 6_934_528", "RAW_SIZE = 6_948_864", 1),
    ("KERNEL_SIZE = 4_857_270", "KERNEL_SIZE = 4_872_077", 1),
    ("35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12", "1921c30eba2e30da9d293d14efe3f2ac6e4f5a1aa6f633ea0567a21e987597fa", 1),
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", 1),
    ("96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", "68b04b4dc3a46cd61310678d2f772450dccf42087e64fa4902cb9f8439dd8d9c", 1),
    ("4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", "2b0ef4482e92d734385cfd794b49ed7cd65a4415731c7f9c3ee276fe603730ce", 1),
    ("90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", "8f87be2b5ef85c5eef7fd3a89f38488b1b14bdbed2d0031731ea07e7ce6e3bc2", 1),
    ("265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", "9b9118fd53b7b290803c52745b5fb8ab2559c0ba83765d30b6111d1bd01914d7", 1),
    ("4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", "073cf7b491e0ac3cf7925a3b2c73660554fd6597218a33e1655830eed59bda2b", 1),
    ("c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", "45b3dbeda5e3ff119e51d57c7e23dfef33d6ae9a9a6a493fbd5a5e9f58327bda", 1),
    ("a029c258c19c96a234cb5cafe4c1bb35a36bac2beadbe8e2ea547da8870719d1", "388c099eaab6c4660db869fedf61e7e4b49c97de88b754c0dd407d4a88606f44", 1),
    ("gemini-mt6797-a72-live-image-runtime-dt-control.boot.img", "gemini-mt6797-a72-provenance-serviceability.boot.img", 1),
    ('b"gemini-a72dtctl"', 'b"gemini-a72prov"', 1),
    ("c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "5abde763316ab358d7f5cb1a3b6a461eb0a2ed99", 1),
    (old_semantics, new_semantics, 1),
    ("validation=a72-live-image-runtime-dt-control-independent", "validation=a72-provenance-serviceability-independent", 1),
    ('print("controller_nodes=0")', 'print("controller_nodes=1")', 1),
    ('print("binder_nodes=0")', 'print("binder_nodes=1")', 1),
    ('print("cpu8_requests=0")', 'print("candidate_cpu8_request_paths=1")\n    print("cpu8_requests=0")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe candidate-validator derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": "a72_provenance_serviceability_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
namespace["main"]()
