#!/usr/bin/env python3
"""Independently validate the serviceability-corrected softtrace candidate."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "69046507a47f6170988d7592724e2ace07f359677af0ef9f90f5626bdd651f45"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT / "experiments/2026-08-28-mainline-a72-admission-trace-softfail/"
    "scripts/validate-candidate.py"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(SOURCE) != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
anchor = "replacements = (\n"
nodes_anchor = "    nodes = parse_dtb(dtb)\n"
nodes_replacement = '''    nodes = parse_dtb(dtb)
    serviceability_nodes = (
        "/usb@11271000",
        "/t-phy@11290000",
        "/t-phy@11290000/usb-phy@11290800",
        "/i2c@1101c000",
        "/i2c@1101c000/gpio-expander@5b",
        "/keyboard-matrix",
    )
    for node in serviceability_nodes:
        require(node in nodes and dt_string(nodes, node, "status") == "okay",
                f"serviceability node not enabled: {node}")
'''
provenance_anchor = '''    require("boot_candidate=pending-independent-validation\\n" in
            provenance.read_text(encoding="utf-8"),
            "builder provenance state changed")'''
provenance_replacement = '''    provenance_text = provenance.read_text(encoding="utf-8")
    require("boot_candidate=pending-independent-validation\\n" in provenance_text,
            "builder provenance state changed")
    require("experiment=2026-08-28-mainline-a72-admission-softtrace-serviceable\\n"
            in provenance_text, "builder experiment identity changed")
    require("dtb_sha256=1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c\\n"
            in provenance_text, "builder serviceability DT identity changed")'''
print_anchor = '    print("controller_nodes=1")\n'
print_replacement = '    print("controller_nodes=1")\n    print("serviceability_nodes=6")\n'
injected = (
    f"nodes_anchor = {nodes_anchor!r}\n"
    f"nodes_replacement = {nodes_replacement!r}\n"
    f"provenance_anchor = {provenance_anchor!r}\n"
    f"provenance_replacement = {provenance_replacement!r}\n"
    f"print_anchor = {print_anchor!r}\n"
    f"print_replacement = {print_replacement!r}\n"
    '''replacements = (
    ('DTB_SHA256 = "1bd6ce2ded2e1186503cb0d9d00107964ec27abc48062b9210e1935d38d60509"',
     'DTB_SHA256 = "1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c"', 1),
    ('dtb = package / "dtbs/mediatek/mt6797-gemini-pda-a72-admission.dtb"',
     'dtb = ROOT / "artifacts/a72-admission-serviceability-restoration-input/mt6797-gemini-pda-a72-admission-serviceable.dtb"', 1),
    (nodes_anchor, nodes_replacement, 1),
    (provenance_anchor, provenance_replacement, 1),
    (print_anchor, print_replacement, 1),
'''
)
if text.count(anchor) != 1:
    raise SystemExit("unsafe serviceable-softtrace validator: replacement anchor changed")
text = text.replace(anchor, injected, 1)
replacements = (
    ("9d1912aa3055d0835831a9376aec141329e5809fd833359f5baaeb6ad033fd40",
     "8dbc66427179b7468424ce6f81263132e90fb37264d46c4aeb650bad3a5678e7", 1),
    ("83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0",
     "df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60", 1),
    ("RAW_SIZE = 6_942_720", "RAW_SIZE = 6_944_768", 1),
    ("gemini-mt6797-a72-admission-softtrace.boot.img",
     "gemini-mt6797-a72-admission-softtrace-serviceable.boot.img", 1),
    ("candidate-a72-admission-softtrace-",
     "candidate-a72-admission-softtrace-serviceable-", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe serviceable-softtrace validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "serviceable_softtrace_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
