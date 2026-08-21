#!/usr/bin/env python3
"""Validate the sanitized MT6797 A72 secure CPU-off attribution audit."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Iterable


EXPERIMENT = Path(__file__).resolve().parents[1]
README = EXPERIMENT / "README.md"
CALLGRAPH = EXPERIMENT / "results" / "callgraph.tsv"
EFFECTS = EXPERIMENT / "results" / "effect-inventory.tsv"
TRANSCRIPT = EXPERIMENT / "results" / "audit-validation-20260805.txt"
PAYLOAD_SHA256 = "2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3"
CALLGRAPH_SHA256 = "0007ba7868cbd68bb2a4ef6ad66240c7e00715e08934ca5d05ca482dfd464354"
EFFECTS_SHA256 = "85a877ca698a609ce3373c4dd829b027a3f6b6c52e4dfb3ba784a1011ab2fb67"
TRANSCRIPT_SHA256 = "6da8ad1883362b32fe7b8e2332f262ec8ebf195db09c91872a0ce59eda429af6"

CALLGRAPH_FIELDS = (
    "id", "stage", "function", "address", "caller", "gate", "semantic",
    "bounded", "replay_control",
)
EFFECT_FIELDS = (
    "id", "scenario", "order", "function", "code_range", "target",
    "action", "condition", "scope", "wait", "replay",
)
CALLGRAPH_IDS = tuple(f"CG{number:02d}" for number in range(1, 17))
EFFECT_IDS = tuple(f"EF{number:02d}" for number in range(1, 46))
LAST_CORE_UNBOUNDED = {
    "EF15", "EF17", "EF21", "EF24", "EF27", "EF29", "EF31", "EF38",
}
CPU9_UNBOUNDED = {"EF06", "EF08"}
CPU9_ACTIVE_SCOPE_ALLOWLIST = {
    "current-cpu",
    "private-firmware-state",
    "shared-diagnostic",
    "per-core-status",
    "per-core-power",
    "shared-diagnostic-and-private-firmware-state",
}


class AuditError(ValueError):
    """The sanitized audit violates a pinned attribution or safety invariant."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_tsv(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == fields, f"schema changed: {path.name}")
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            require(None not in row, f"extra TSV cell at {path.name}:{line_number}")
            for field in fields:
                value = row.get(field)
                require(value is not None and value != "",
                        f"empty {field} at {path.name}:{line_number}")
                require(value == value.strip(),
                        f"untrimmed {field} at {path.name}:{line_number}")
                require(not any(character in value for character in "\t\r\n"),
                        f"embedded TSV control at {path.name}:{line_number}")
            rows.append(row)  # type: ignore[arg-type]
    return rows


def row_map(rows: Iterable[dict[str, str]], key: str = "id") -> dict[str, dict[str, str]]:
    mapped: dict[str, dict[str, str]] = {}
    for row in rows:
        require(row[key] not in mapped, f"duplicate {key}: {row[key]}")
        mapped[row[key]] = row
    return mapped


def validate_callgraph(rows: list[dict[str, str]]) -> None:
    require(tuple(row["id"] for row in rows) == CALLGRAPH_IDS,
            "callgraph inventory changed")
    by_id = row_map(rows)

    require(by_id["CG06"]["function"] == "platform_affinst_off" and
            by_id["CG06"]["gate"] == "linear-id>7" and
            "skip-callback-cci-disable-and-disable-scu" in by_id["CG06"]["semantic"],
            "A72 target-side cluster skip changed")
    require(by_id["CG08"]["bounded"] == "nonreturning" and
            "infinite-post-off-wfi" in by_id["CG08"]["semantic"],
            "target CPU_OFF terminal WFI changed")

    active = by_id["CG10"]
    require(active["function"] == "psci_affinity_info" and
            active["address"] == "0x10c58c" and
            "active-query-dispatches-deferred-a72-hardware-off" == active["semantic"],
            "AFFINITY_INFO was made passive")
    require(active["gate"] == "[target-node+0x0a].bit0=1;linear-id>7",
            "AFFINITY_INFO active target gate changed")
    require(active["bounded"] == "unbounded-per-call",
            "AFFINITY_INFO was falsely bounded")
    require(active["replay_control"] == "private-big_on-bit-not-query",
            "query count replaced the private replay gate")

    replay = by_id["CG11"]
    require(replay["gate"] == "private-big_on&BIT(linear-id-8)" and
            replay["semantic"] == "hardware-teardown-skipped-after-target-bit-clear" and
            replay["replay_control"] == "private-big_on-bit",
            "hardware replay gate changed")

    retained = by_id["CG15"]
    require(retained["stage"] == "retained-cpu-observer-prohibited" and
            retained["replay_control"] == "forbidden-not-an-observer" and
            "retained-cpu8-wfi" in retained["semantic"],
            "retained CPU8 AFFINITY_INFO prohibition missing")
    require(by_id["CG16"]["stage"] == "already-off-observer-prohibited" and
            by_id["CG16"]["bounded"] == "not-an-independent-bound" and
            by_id["CG16"]["replay_control"] == "private-big_on-bit-required",
            "already-off AFFINITY_INFO was promoted to an independent oracle")


def validate_effects(rows: list[dict[str, str]]) -> None:
    require(tuple(row["id"] for row in rows) == EFFECT_IDS,
            "effect inventory changed")
    by_id = row_map(rows)

    require(by_id["EF05"]["target"] == "0x10222400;0x10222404" and
            by_id["EF05"]["action"] == "write-0x0000001b-and-read-twice",
            "CPU9 diagnostic effect changed")
    require(by_id["EF06"]["wait"] == "unbounded-no-timeout" and
            by_id["EF06"]["target"] == "0x10006178" and
            "0x00000800" in by_id["EF06"]["action"],
            "CPU9 WFI wait changed")
    require(by_id["EF07"]["target"] == "0x10006244" and
            by_id["EF07"]["action"] == "rmw-clear-bit2" and
            by_id["EF09"]["target"] == "0x10006244" and
            by_id["EF09"]["action"] == "rmw-clear-bit0",
            "CPU9 PWR_CON effect changed")
    require(by_id["EF08"]["target"] == "0x10006188" and
            by_id["EF08"]["wait"] == "unbounded-no-timeout" and
            "0x00000040" in by_id["EF08"]["action"],
            "CPU9 power acknowledgement changed")
    require(by_id["EF10"]["target"] == "private-big_on-ledger" and
            by_id["EF10"]["action"] == "clear-bit1" and
            by_id["EF10"]["replay"] == "prevents-hardware-replay",
            "CPU9 private membership/replay effect changed")
    require(by_id["EF11"]["action"] == "no-write" and
            by_id["EF11"]["scope"] == "cluster-shared-power-clock-cci-spm" and
            by_id["EF11"]["condition"] == "private-big_on!=0",
            "CPU9 retained branch gained a cluster effect")
    require(by_id["EF12"]["action"] == "proven-nonempty-write-subset" and
            by_id["EF12"]["target"] == "0x10222400;private-big_on-ledger" and
            by_id["EF12"]["replay"] == "not-empty",
            "CPU9 shared/private write subset was falsely made empty")

    cpu9_rows = [row for row in rows if row["scenario"] == "cpu9-off-cpu8-retained"]
    observed_cpu9_unbounded = {
        row["id"] for row in cpu9_rows if row["wait"] == "unbounded-no-timeout"
    }
    require(observed_cpu9_unbounded == CPU9_UNBOUNDED,
            "CPU9 retained unbounded-wait inventory changed")
    for row in cpu9_rows:
        if row["action"] != "no-write":
            require(row["scope"] in CPU9_ACTIVE_SCOPE_ALLOWLIST,
                    f"CPU9 retained row has a non-allowlisted effect scope: {row['id']}")

    require(by_id["EF20"]["function"] == "cci_disable" and
            by_id["EF21"]["wait"] == "unbounded-no-timeout",
            "last-core CCI withdrawal changed")
    require(by_id["EF24"]["target"] == "0x1039000c" and
            by_id["EF24"]["condition"] == "cci-change-pending" and
            by_id["EF24"]["scope"] == "cluster-cci-global-status-source-corroborated",
            "MP2 CCI global change-pending poll changed")
    require(by_id["EF22"]["target"] == "0x1022220c" and
            by_id["EF26"]["target"] == "0x1022220c" and
            by_id["EF22"]["action"] == by_id["EF26"]["action"] == "rmw-or-0x00000011",
            "unresolved shared-control writes changed")
    require(by_id["EF28"]["target"] == "0x10001234" and
            by_id["EF29"]["target"] == "0x1000123c" and
            by_id["EF29"]["wait"] == "unbounded-no-timeout",
            "cluster bus-protection effects changed")
    require(by_id["EF32"]["target"] == "0x1001a270" and
            by_id["EF32"]["action"] == "rmw-clear-bit0" and
            by_id["EF35"]["target"] == "0x102224a0" and
            by_id["EF35"]["action"] == "rmw-clear-bit0-and-store-readback",
            "B mux/PLL effects changed")
    require(by_id["EF36"]["target"] == by_id["EF37"]["target"] ==
            by_id["EF40"]["target"] == "0x10006218" and
            by_id["EF36"]["action"] == "rmw-set-bit4" and
            by_id["EF37"]["action"] == "rmw-clear-bit2" and
            by_id["EF40"]["action"] == "rmw-clear-bit0",
            "MP2 SPM power-control effects changed")
    require(by_id["EF39"]["target"] == "0x10006290" and
            by_id["EF39"]["action"] == "rmw-set-bit1-B_EXT_BUCK_ISO" and
            by_id["EF39"]["scope"] == "spm-external-buck-isolation",
            "last-core external-isolation write missing")

    for identifier, target, scope in (
        ("EF41", "0x10222274", "mp2-synchronous-dcm"),
        ("EF42", "0x102222b0;0x102222b4", "b-cluster-sram-ldo"),
        ("EF43", "external-regulator", "buckb-provider"),
    ):
        row = by_id[identifier]
        require(row["function"] == "audited-direct-last-core-callgraph" and
                row["target"] == target and row["scope"] == scope and
                row["wait"] == "absent" and row["replay"] == "no-secure-owner-attributed" and
                row["action"] in {"no-direct-write", "no-direct-access"},
                f"negative direct-callgraph finding changed in {identifier}")

    observed_unbounded = {
        row["id"] for row in rows
        if row["scenario"] == "last-a72-off" and row["wait"] == "unbounded-no-timeout"
    }
    require(observed_unbounded == LAST_CORE_UNBOUNDED,
            "last-core unbounded-wait inventory changed")
    require(by_id["EF44"]["target"] == "retained-online-cpu8" and
            by_id["EF44"]["action"] == "forbidden-query" and
            by_id["EF44"]["replay"] == "not-an-observer",
            "retained CPU8 query was permitted")
    require(by_id["EF45"]["action"] == "forbidden-independent-query" and
            by_id["EF45"]["replay"] == "private-gate-required",
            "already-off query was promoted to independent evidence")


def validate_readme(text: str) -> None:
    require(PAYLOAD_SHA256 in text, "private payload identity changed")
    for marker in (
        "cpu_off_authorized=no",
        "build_authorized=no",
        "device_action_authorized=no",
        "device_action=none",
    ):
        require(marker in text, f"authorization marker missing: {marker}")
    require("cpu_off_authorized=yes" not in text and
            "build_authorized=yes" not in text and
            "device_action_authorized=yes" not in text,
            "audit text grants authorization")
    require("not a passive observation" in text,
            "active AFFINITY_INFO conclusion missing")
    require("2026-08-21 correction" in text and
            "`0x1039000c`" in text and "`0x1039600c`" in text,
            "CCI address correction missing")
    require("Only the intended off target may be queried" in text and
            "Querying retained online CPU8" in text,
            "retained CPU8 observer prohibition missing")
    for forbidden in ("/Users/", "/home/", "artifacts/", "mmcblk", "tee1", "tee2"):
        require(forbidden not in text, f"private path or image name published: {forbidden}")


def main() -> int:
    callgraph = load_tsv(CALLGRAPH, CALLGRAPH_FIELDS)
    effects = load_tsv(EFFECTS, EFFECT_FIELDS)
    validate_callgraph(callgraph)
    validate_effects(effects)
    validate_readme(README.read_text(encoding="utf-8"))
    require(sha256(CALLGRAPH) == CALLGRAPH_SHA256, "callgraph canonical hash changed")
    require(sha256(EFFECTS) == EFFECTS_SHA256, "effect inventory canonical hash changed")
    require(sha256(TRANSCRIPT) == TRANSCRIPT_SHA256,
            "saved validation transcript changed")

    print("validation=a72-secure-cpu-off-attribution")
    print("result=PASS")
    print(f"payload_sha256={PAYLOAD_SHA256}")
    print(f"callgraph_rows={len(callgraph)}")
    print(f"callgraph_sha256={CALLGRAPH_SHA256}")
    print(f"effect_rows={len(effects)}")
    print(f"effect_inventory_sha256={EFFECTS_SHA256}")
    print(f"last_core_unbounded_waits={len(LAST_CORE_UNBOUNDED)}")
    print(f"cpu9_unbounded_waits={len(CPU9_UNBOUNDED)}")
    print("affinity_info=active-unbounded-target-only-not-independent-observer")
    print("cpu9_cluster_resource_effects=empty")
    print("cpu_off_authorized=no")
    print("build_authorized=no")
    print("device_action_authorized=no")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as error:
        raise SystemExit(f"error: {error}") from error
