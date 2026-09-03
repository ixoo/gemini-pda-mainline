#!/usr/bin/env python3
"""Independently validate the physical CPU9-off/same-boot-restore container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "29b35ea8c07abcfa840e868a7b23075a49d1b0323f39faa0ffedb1e605f8ac96"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-28-mainline-a72-live-image-runtime-dt-control/"
    "scripts/validate-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source Android-v0/LK candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
old_semantics = '''require(dtb.count(b"mediatek,mt6797-a72-platform-state") == 1, "platform-state compatible changed")
    require(dtb.count(b"mediatek,mt6797-a72-platform-provider-clock-observer") == 1, "observer compatible changed")
    require(b"mt6797-a72-admission-controller" not in dtb and b"mt6797-a72-admission-binder" not in dtb, "admission node leaked into DT")'''
new_semantics = '''require(dtb.count(b"mediatek,mt6797-a72-platform-state") == 1, "platform-state compatible changed")
    require(dtb.count(b"mediatek,mt6797-a72-admission-controller") == 1, "admission controller changed")
    require(dtb.count(b"mediatek,mt6797-a72-binder") == 1, "admission binder changed")
    require(dtb.count(b"planet,gemini-a72-runtime-binding-v1") == 1, "runtime provenance changed")
    require(b"mediatek,mt6797-a72-platform-provider-clock-observer" not in dtb, "standalone observer leaked into DT")'''
replacements = (
    ("RAW_SIZE = 6_934_528", "RAW_SIZE = 6_981_632", 1),
    ("KERNEL_SIZE = 4_857_270", "KERNEL_SIZE = 4_904_733", 1),
    ("35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12", "482516ce51beb8d5a3df8baa59cdcba416e6b7ae18b08026cd7325fcf024b8e0", 1),
    ("c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab", "4b027c97c7f3cfc65ae7210a30724781bf58a321f8d51132c1413d501b75403b", 1),
    ("96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", "163a530aa6feb1c333fa1658be8b733d7cf0128decace9391c33bcd8f482e05e", 1),
    ("4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", "095ad19217599b56620dc1d6e3b50b312fbd523e226b837c261400fd1acdf9a6", 1),
    ("90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d", "f373dd190371b17b2b7bf123a945247b828c295dfee83c3d2844b1c5b16a609e", 1),
    ("265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", "a76237ab140491d0c11dd9560cf3eb11176476c910f0a5c889c70d1cf324e70a", 1),
    ("4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", "815838d4c27b7c2159ef73747e1aa5858794a58ccdcd2d394dee33d23c20f85f", 1),
    ("c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", "96984898f4baf3ab908586e25675c37eb77391611cb15c83af852446a305d321", 1),
    ("a029c258c19c96a234cb5cafe4c1bb35a36bac2beadbe8e2ea547da8870719d1", "b30c34cc56122e42261b551d6c6512ec6d0278ce9e08ab230bfddb379996ff1e", 1),
    ("gemini-mt6797-a72-live-image-runtime-dt-control.boot.img", "gemini-mt6797-a72-hotplug-physical.boot.img", 1),
    ('b"gemini-a72dtctl"', 'b"gemini-a72prov"', 1),
    ("c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "43349a53fda1ab1c7389ac0e6da2e89d131177bc", 1),
    ("a72-admission-live-trigger-candidate", "gemini-a72-hotplug-physical-candidate", 1),
    ("7.1.3-gemini-a72-admission-live", "7.1.3-gemini-a72-hotplug-physical", 1),
    (old_semantics, new_semantics, 1),
    ("validation=a72-live-image-runtime-dt-control-independent", "validation=a72-physical-hotplug-independent", 1),
    ("controller_nodes=0", "controller_nodes=1", 1),
    ("binder_nodes=0", "binder_nodes=1", 1),
    ("cpu8_requests=0", "physical_requests_during_validation=0", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe physical-hotplug candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_physical_hotplug_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
namespace["main"]()
