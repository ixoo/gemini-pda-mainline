#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify frozen provisional metadata and exercise fail-closed mutations."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIGESTS = {
    "inputs.json": "cc93d3e9627e31a60d66ebcea8211104a47663313b0015a5390612624f50bf4b",
    "analysis.json": "18c4bf0b55a4cd00450b1eead755edf610e4050612191a3b7fdca968c4b36c12",
    "intervals.json": "30ab9bb53bff6c144ba75b390220f0c036e9cbe8730d2fcb7c562955a659f23d",
}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def validate(packet: dict, frozen: dict) -> None:
    inp, audit, spans = (packet[name] for name in DIGESTS)
    require(inp == frozen["inputs.json"], "input/tool/source identity drift")
    require(audit["state"] == "blocked-parser-scope-conflict", "scope stop removed")
    obs = audit["parser_observations"]
    require(obs["architecture_detector_called"] is True and
            obs["strict_no_classification_condition_met"] is False and
            obs["observations_admitted"] is False, "classification conflict hidden")
    require(all(value is False for value in audit["authority"].values()),
            "authority escalation")
    require(spans["state"] == "provisional-not-admitted" and
            spans["exact_function_end_claim"] is False, "interval promoted")
    require(len(spans["targets"]) == 4 and
            [r["name"] for r in spans["targets"]] == inp["targets"],
            "target inventory drift")
    region = spans["region"]
    lo, hi = int(region["start"], 16), int(region["end_exclusive"], 16)
    require(region["flags"] & 4 and region["flags_are_synthetic"] is True and
            hi - lo == region["size"], "region metadata drift")
    for row in spans["targets"]:
        start, end = int(row["address"], 16), int(row["next"]["address"], 16)
        require(row["matches"] == 1 and row["type"] == "T" and
                row["elf_address"] == row["address"], "target ambiguity/type/address")
        require(len(row["aliases"]) <= 4 and
                all(a["address"] == row["address"] for a in row["aliases"]),
                "alias boundary drift")
        require(lo <= int(row["previous"]["address"], 16) < start < end < hi and
                end - start == row["length"] and
                row["previous"]["index"] < row["index"] < row["next"]["index"],
                "non-monotonic/cross-region interval")
        require(row["admitted"] is False, "provisional result promoted")
    text = json.dumps(packet)
    require(not any(s in text for s in ("/home/", "/Users/", "PRIVATE KEY",
                                       "PRIVATE_PATH_SENTINEL")),
            "private material")
    require(packet == frozen, "frozen transformation/evidence drift")


def main() -> int:
    frozen = {}
    for name, expected in DIGESTS.items():
        raw = (HERE / name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected,
                "fixed file digest changed")
        frozen[name] = json.loads(raw)
    validate(copy.deepcopy(frozen), frozen)
    mutations = []

    def change(file: str, path: tuple, value: object) -> None:
        packet = copy.deepcopy(frozen)
        item = packet[file]
        for key in path[:-1]:
            item = item[key]
        item[path[-1]] = value
        mutations.append(packet)

    for key in ("analysis_parent", "dispatch_head"):
        change("inputs.json", (key,), "0" * 40)
    for group in ("predecessor", "kernel", "tool"):
        for key in frozen["inputs.json"][group]:
            change("inputs.json", (group, key), "drift")
    change("inputs.json", ("bounds", "kernel_tuples"), 2)
    change("inputs.json", ("bounds", "network"), True)
    for key in frozen["analysis.json"]["transformations"]:
        change("analysis.json", ("transformations", key, "behavior"), "invented")
    change("analysis.json", ("parser_observations", "architecture_detector_called"), False)
    change("analysis.json", ("parser_observations", "observations_admitted"), True)
    change("analysis.json", ("parser_observations", "strict_no_classification_condition_met"), True)
    for key in frozen["analysis.json"]["authority"]:
        change("analysis.json", ("authority", key), True)
    for key in frozen["analysis.json"]["predicates"]:
        change("analysis.json", ("predicates", key), "resolved")
    change("intervals.json", ("targets",), [])
    change("intervals.json", ("targets",), frozen["intervals.json"]["targets"] * 2)
    for key, value in (("matches", 2), ("type", "W"), ("elf_address", "0"),
                       ("aliases", [{"address": "0"}] * 5), ("admitted", True),
                       ("length", 0), ("index", 0)):
        change("intervals.json", ("targets", 0, key), value)
    change("intervals.json", ("targets", 0, "next", "address"), "0")
    change("intervals.json", ("targets", 0, "next", "address"), "ffffffffffffffff")
    change("intervals.json", ("region", "flags"), 3)
    change("intervals.json", ("region", "flags_are_synthetic"), False)
    change("intervals.json", ("exact_function_end_claim",), True)
    change("intervals.json", ("strength",), "strong because ELF GLOBAL")
    change("analysis.json", ("private_path",), "PRIVATE_PATH_SENTINEL")
    change("analysis.json", ("mutable_expected_digest",), "0" * 64)
    for packet in mutations:
        try:
            validate(packet, frozen)
        except (ValueError, TypeError, KeyError):
            continue
        raise ValueError("mutation accepted")
    print(f"provisional packet PASS; mutations={len(mutations)}; later-analysis=blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
