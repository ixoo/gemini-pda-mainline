#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the frozen unresolved packet; never access an ELF or a device."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT_SHA = "89dd591276e93c58dee6f35a53eab3b8daa93dec565f71387a997adf1c3875a1"
ANALYSIS_SHA = "d08406c637cc19c943c761b302d7591eeb99a334cd03ac0fdf69fb084046cd70"
SYMBOLS = (
    ("do_connectivity_driver_init", "ffffffc0006e3a70"),
    ("do_wlan_drv_init", "ffffffc0006e3ed0"),
    ("mtk_wcn_wlan_gen3_init", "ffffffc0007415a0"),
    ("mtk_wcn_wlan_gen3_exit", "ffffffc000741898"),
)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def validate(inputs: dict, analysis: dict, frozen_inputs: dict,
             frozen_analysis: dict) -> None:
    require(inputs == frozen_inputs, "frozen input/source/repository identity changed")
    require(analysis["state"] == "unresolved-symbol-range-gate", "state promoted")
    require(len(analysis["symbols"]) == 4, "symbol inventory changed")
    for item, (name, address) in zip(analysis["symbols"], SYMBOLS, strict=True):
        require(item == {"name": name, "entries": 1, "address": address,
                         "size": 0, "type": "FUNC", "binding": "GLOBAL",
                         "visibility": "DEFAULT", "section_index": 1},
                "symbol reconstruction metadata changed")
    require(analysis["selected_functions"] == [] and
            analysis["function_bodies_inspected"] == 0 and
            analysis["whole_executable_branch_scans"] == 0 and
            analysis["whole_elf_xref_scans"] == 0, "unperformed analysis invented")
    for key in ("direct_exit_call_count", "direct_exit_callers",
                "address_taken_edges", "callback_registration_edges"):
        require(analysis[key] is None, "unknown observation promoted to edge/no-hit")
    require(all(value is False for value in analysis["authority"].values()),
            "authority promoted")
    require(analysis == frozen_analysis, "frozen evidence/conclusion changed")
    text = json.dumps({"inputs": inputs, "analysis": analysis})
    require(not any(token in text for token in ("/home/", "/Users/", "PRIVATE KEY")),
            "private material in public record")


def main() -> int:
    input_bytes = (HERE / "inputs.json").read_bytes()
    analysis_bytes = (HERE / "analysis.json").read_bytes()
    require(hashlib.sha256(input_bytes).hexdigest() == INPUT_SHA,
            "input digest changed; expected digest is code-pinned")
    require(hashlib.sha256(analysis_bytes).hexdigest() == ANALYSIS_SHA,
            "analysis digest changed; expected digest is code-pinned")
    inputs, analysis = json.loads(input_bytes), json.loads(analysis_bytes)
    validate(inputs, analysis, copy.deepcopy(inputs), copy.deepcopy(analysis))

    mutations = []

    def change(path: tuple, value: object, target: str = "analysis") -> None:
        pair = {"inputs": copy.deepcopy(inputs), "analysis": copy.deepcopy(analysis)}
        member = pair[target]
        for key in path[:-1]:
            member = member[key]
        member[path[-1]] = value
        mutations.append(pair)

    for key in ("repository_parent", "source_commit", "elf_sha256"):
        change((key,), "0" * len(inputs[key]), "inputs")
    change(("symbols",), analysis["symbols"] * 2)
    change(("symbols",), analysis["symbols"][:-1])
    for key, value in (("size", 4), ("binding", "WEAK"), ("type", "OBJECT"),
                       ("section_index", 2), ("address", "0"), ("entries", 2)):
        change(("symbols", 0, key), value)
    change(("containing_section", "flags"), "WA")
    change(("direct_exit_call_count",), 0)
    change(("direct_exit_callers",), [{"address": "0", "opcode": "B"}])
    change(("address_taken_edges",), [])
    change(("callback_registration_edges",), ["invented"])
    change(("selected_functions",), ["invented"] * 9)
    change(("whole_executable_branch_scans",), 1)
    change(("whole_elf_xref_scans",), 1)
    for key in analysis["predicates"]:
        change(("predicates", key), "resolved")
    for key in analysis["authority"]:
        change(("authority", key), True)
    change(("raw_evidence", "sha256"), "0" * 64)
    change(("raw_evidence", "label"), str(Path("/", "home", "private", "raw")))
    change(("mutable_expected_digest",), "0" * 64)
    for pair in mutations:
        try:
            validate(pair["inputs"], pair["analysis"], inputs, analysis)
        except (ValueError, KeyError, TypeError):
            continue
        raise ValueError("mutation accepted")
    print(f"unresolved packet: PASS; refusal mutations={len(mutations)}; "
          "binary semantic tests=not-run; teardown=unresolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
