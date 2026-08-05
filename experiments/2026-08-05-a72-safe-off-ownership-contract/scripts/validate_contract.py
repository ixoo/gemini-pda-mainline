#!/usr/bin/env python3
"""Validate the fail-closed MT6797 A72 safe-off ownership contract."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Iterable


EXPERIMENT = Path(__file__).resolve().parents[1]
REPOSITORY = Path(__file__).resolve().parents[3]
CONTRACT = EXPERIMENT / "results" / "safe-off-contract.tsv"
RECONCILIATION = EXPERIMENT / "results" / "evidence-reconciliation.tsv"

CONTRACT_FIELDS = (
    "id",
    "scenario",
    "proof_order",
    "boundary",
    "physical_writer",
    "requester",
    "required_prestate",
    "success_readback",
    "timeout",
    "inverse",
    "failure_response",
    "evidence",
    "decision",
)
RECONCILIATION_FIELDS = (
    "source_id",
    "boundary",
    "previous_status",
    "new_evidence",
    "current_disposition",
    "remaining_gap",
    "evidence_path",
)
CPU9_IDS = tuple(f"C{number:02d}" for number in range(1, 9))
LAST_IDS = tuple(f"L{number:02d}" for number in range(1, 15))
EXPECTED_IDS = CPU9_IDS + LAST_IDS
RECONCILIATION_IDS = tuple(f"{number:02d}" for number in range(1, 20))
DECISIONS = {
    "blocked-ledger",
    "blocked-observation",
    "blocked-owner",
    "blocked-owner-order",
    "blocked-policy-owner",
    "blocked-provider",
    "blocked-timeout",
    "contract-defined",
}
EXPECTED_TIMEOUTS = {
    "C01": "same-critical-section-no-wait",
    "C02": "policy-drain-and-entry-observation-timeouts-unresolved",
    "C03": "synchronous-before-psci",
    "C04": "target-source-path-nonreturning;parent-one-query-at-C05",
    "C05": "two-reachable-inner-waits-unbounded-no-call-bound",
    "C06": "cpu8-callback-timeout-unresolved",
    "C07": "per-owner-invariance-readback-timeouts-unresolved",
    "C08": "same-critical-section-after-C07",
    "L01": "same-critical-section-no-wait",
    "L02": "policy-drain-and-entry-observation-timeouts-unresolved",
    "L03": "synchronous-before-psci",
    "L04": "target-source-path-nonreturning;parent-one-query-at-L05",
    "L05": "eight-reachable-inner-waits-unbounded-no-call-bound",
    "L06": "secure-observer-timeout-unresolved",
    "L07": "idvfs-observer-timeout-unresolved",
    "L08": "dcm-observer-timeout-unresolved",
    "L09": "reset-observer-timeout-unresolved",
    "L10": "isolation-observer-timeout-unresolved",
    "L11": "sram-observer-timeout-unresolved",
    "L12": "secure-sentinel-observer-timeout-unresolved",
    "L13": "provider-timeout-unresolved",
    "L14": "same-critical-section-after-L13",
}
EXPECTED_FAILURE_RESPONSES = {
    "C01": "deny-cpu-off;no-hardware-change",
    "C02": "deny-cpu-off;release-only-owned-software-state;no-hardware-write",
    "C03": "deny-cpu-off;no-hardware-write",
    "C04": "retain-conservative-linux-members-and-C02-resource-state;prohibit-query-retry-after-fault;prohibit-cpu-retry;reset-only",
    "C05": "retain-conservative-linux-members-and-C02-resource-state;prohibit-query-retry-after-fault;prohibit-cpu-retry;reset-only",
    "C06": "retain-conservative-linux-members-and-C02-resource-state;prohibit-query-retry-after-fault;prohibit-cpu-retry;reset-only",
    "C07": "retain-exact-observed-resource-state-and-conservative-linux-members;prohibit-query-retry-after-fault;prohibit-cpu-retry;reset-only",
    "C08": "terminal-fault;no-retry;reset-only",
    "L01": "deny-cpu-off;no-hardware-change",
    "L02": "deny-cpu-off;release-only-owned-software-state;no-hardware-write",
    "L03": "deny-cpu-off;no-hardware-write",
    "L04": "retain-conservative-linux-members-reference-and-L02-resource-state;prohibit-query-retry-after-fault;prohibit-cpu-retry;reset-only",
    "L05": "retain-conservative-linux-members-reference-and-L02-resource-state;prohibit-query-retry-after-fault;prohibit-cpu-retry;reset-only",
    "L06": "no-further-shared-write;retain-exact-observed-state-and-reference;reset-only",
    "L07": "no-idvfs-compensation-or-guessed-write;retain-reference;reset-only",
    "L08": "no-dcm-compensation-or-guessed-write;retain-reference;reset-only",
    "L09": "no-reset-compensation-or-guessed-write;retain-reference;reset-only",
    "L10": "no-isolation-compensation-or-guessed-write;retain-reference;reset-only",
    "L11": "no-sram-compensation-or-guessed-write;retain-reference;reset-only",
    "L12": "retain-exact-observed-state-and-reference;reset-only",
    "L13": "record-exact-provider-and-rail-state;no-reenable-or-vsel-compensation;reset-only",
    "L14": "terminal-fault;no-retry;reset-only",
}
EXPECTED_CONTRACT_ROW_SHA256 = {
    "C01": "b7a6eb2b1dfbda2ecc7fb61aa9b39d0f1d2b1e71d98ac959b6b8fa2a364c872a",
    "C02": "0796ff38736ad86dd03dd4d2af79b0ff2f06a37ad83fd229194d61e855c81143",
    "C03": "8472aac206f4ff68a55f16637d3b65cabdb12c261cb80ef66eab915eed75f034",
    "C04": "dfffdf7aab3c62c5c410d40abf8e2cb078773710ec15d0e52b1541022b7a884e",
    "C05": "c384c8f11d316df650c2df2046c9634b8d32c5b4b78534b713d5bc3262827065",
    "C06": "91b9293524e9bb249c66c4693cfb39119dfc95af76f179124447a56f2dee7f27",
    "C07": "98f9bb1f9447459ae5e1187ab4fd182249e7d92e727f3f0f915709f626d46d13",
    "C08": "7ff003b827a13a8c4244547856bebb7fa08b7a491c083639ee3cca3dc08ca030",
    "L01": "b716e7344a507ccdfa47fb4d848c3dc105f370c486cc6406b4bef9bae3ee3cf0",
    "L02": "f0e07f933e846b9dd0c588a12dea28df31c3a20652f6076ec3d951b8e8532861",
    "L03": "e783a4bb8c8f3130d53baeb823d5d60bbbd78b5d4b7228d5451c67f77a86c55e",
    "L04": "a4e40af7c20d53476cbecc885bbf3afeea67482b800bbdae119a00fcf796101b",
    "L05": "fc3a4a484afcd0f1a0eca935f7f02fa506d908a26e2ca4021213c74f4137308b",
    "L06": "c3a85258a8696fa3722bddd6715c094a472f17db8bab0735d356e90f08053077",
    "L07": "ac7c28714092ea33a0c6200e57facc5dcd37d31324d20425a55e8438d3a1c97f",
    "L08": "a97c1664b1fcf65bf528946d445795aa490c0b7cf4f1d5f65857781d2c9d2d53",
    "L09": "62893fd8b068953ccd7ffa5ee24a730d35ec9ec8a8a5aa7b9de2337e78ba6aa2",
    "L10": "6fdd5234c15b3ee5730cea00281b07aede8547fef15d1f6a80f0f34cf9f63f31",
    "L11": "53e55ce26b571a51b585b1524b620a47dd0565be90718679b1c97a1234cacd70",
    "L12": "2fb8cd8802f6f6759742c8c96ce1c4b7aeafd077bb84a3d8ddc5bf57efd14d4c",
    "L13": "e74581d63c9ba5e9001ad144744d4029626e7de10b69468b0438e6be52e906e5",
    "L14": "a2c0bb61ddad93b9dfeebb3110a7ec0fc47a94df71b3b8fabd951f8d7cadd6b4",
}
EXPECTED_DISPOSITIONS = {
    "01": "forward-closed-off-ledgers-open",
    "02": "closed-preiso-and-last-off-source",
    "03": "forward-and-last-off-source-closed-readback-open",
    "04": "closed-preiso-rollback",
    "05": "forward-closed-provider-release-open",
    "06": "closed-preiso-rollback",
    "07": "blocked-vsel-owner",
    "08": "last-off-source-closed-failure-open",
    "09": "blocked-nonsecure-sram-owner",
    "10": "forward-and-last-off-source-closed-timeout-open",
    "11": "startup-and-off-source-closed-timeout-runtime-open",
    "12": "forward-and-last-off-source-closed-timeout-open",
    "13": "startup-closed",
    "14": "blocked-nonsecure-dcm-owner",
    "15": "blocked-policy-owner",
    "16": "blocked-policy-owner",
    "17": "split-safe-off-source-closed-contract-open",
    "18": "startup-and-off-source-closed-contract-open",
    "19": "blocked-resume-owner",
}
EXPECTED_RECONCILIATION_EVIDENCE = {
    "01": "experiments/2026-08-03-a72-scheduler-context/results/runtime-unpark-attempt-2-repeatability-pass-20260805.txt",
    "02": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "03": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "04": "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt",
    "05": "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt",
    "06": "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt",
    "07": "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt",
    "08": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "09": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "10": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "11": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "12": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "13": "experiments/2026-08-03-a72-scheduler-context/results/runtime-unpark-attempt-2-repeatability-pass-20260805.txt",
    "14": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "15": "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt",
    "16": "experiments/2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md",
    "17": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "18": "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv",
    "19": "experiments/2026-08-02-a72-ownership-rollback-audit/results/ownership-matrix.tsv",
}
EXPECTED_RECONCILIATION_ROW_SHA256 = {
    "01": "2636f8499e3a7398befd87a8a0cb2249c4ddcbffc973f01eca79d76c2c6f1c6c",
    "02": "63f0fc6225f59bb9b9839a2e501dabe39c772e2e4ce7e201e8b0ede856aa910e",
    "03": "0dbaac62db80af109f328e5b4f05703097dea7282060ad1492beefc64b027b5e",
    "04": "366d4146d3e51f6333f04d450b89d3bc31efe24f3e1203c9f58eeafecf32b5ab",
    "05": "d4adf58ca4467a8cb94e7c4e9fc1a460b0758d0458e6f32538bfa00976f85a84",
    "06": "e24b689cadd4a86bbf85fb3cb6f49cea5aad58a401fb41cf2538632f556e2c8a",
    "07": "f7b427c45dd4e2717ebcd918e52a36e2651bb413063252745908568decf0e016",
    "08": "ce8fc846b7832b860dd927ce1e54d3c0b30db6476158862b52009e5ca10039f0",
    "09": "34439fc8711b54a5fe005d683a2b8a70c0f031100e25fefbf5571970f559c3ec",
    "10": "77ac51cabc0741688d3dfeb0603dcd41cd871a945f444de195ae86f9b51e5e75",
    "11": "289d1188a6b825637d3196e88397baecc9222359000e7975a71419133815671f",
    "12": "f2a56349c5ce5765b36ac0a7f6f2a2e8754b0a4cabe00fa0cf3fb2dc93860f01",
    "13": "b3470c9c994b4f7c163153e06257e4c4ba45e33bf6c6369ffffcc56393739ff9",
    "14": "4a29548fe362b87054b1463e5a6f0220697cc0059a6a7a624725d21bd208dcd9",
    "15": "c4bb3b2ec9d16d0203dc2d64c0d12954cef9df99eb332d2a3b96a58908ec9cb9",
    "16": "b34386015d9dbeb7dcdb8747b7db96d4c839892ed0a9f8ade9a38063e0bd65f7",
    "17": "d072d7057d2dd3518244593752005c7d98937c7f1ffce6214e78711869577a27",
    "18": "b960f5a4581906fdc6a13529ca8affe20b2f6fafd397e83c39f4fa4366375332",
    "19": "f1e656258fe7072ef47c6e42adce7e1c98627ae87748e632efd460af50416131",
}
EVIDENCE_SHA256 = {
    "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/effect-inventory.tsv":
        "deaa6686582e6e3f2e3453ff626f14b2ec555d9be468ac2f67fb350e6eead8bc",
    "experiments/2026-08-05-a72-secure-cpu-off-attribution/results/audit-validation-20260805.txt":
        "6da8ad1883362b32fe7b8e2332f262ec8ebf195db09c91872a0ce59eda429af6",
    "experiments/2026-08-02-a72-ownership-rollback-audit/results/ownership-matrix.tsv":
        "5b483482f9727b3648b15df1b5a4e92ca513c6413a0e64380cd3419ff7d4e6a8",
    "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt":
        "1295291982ae539681fc817cebc894a6f7abb13484f000500e542caa861adaa4",
    "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt":
        "6db6ea41ba4689541cb504a0486c0a1b7249834ebdb8613f0e73b0bf56e808f5",
    "experiments/2026-08-03-a72-cpu9-terminal-attribution/results/runtime-attempt-2-pass-20260803.txt":
        "a90f82f514b1853be6feae1a4751e46bce00aa5b6fa1ae3a194f15b88eb999ac",
    "experiments/2026-08-03-a72-scheduler-context/results/runtime-unpark-attempt-2-repeatability-pass-20260805.txt":
        "6c0966228bb50fcc715c6734ce6e1804507743a820e07ce3e157d46e75fbf26c",
    "experiments/2026-08-02-a72-cpu8-held-online/results/source-order-audit-20260802.txt":
        "ce530fb74fe520d1899f94f64a2c4e2a0029699cb6dd91f7eaccb6d5f5e01a34",
    "experiments/2026-08-02-a72-one-way-cpu8-boundary/results/isolation-owner-audit-20260802.txt":
        "9f3bc3463f9785d4eb94bd3e0a7f6ad8e3e83069b1b77ec2fe182d5cd55021e0",
    "experiments/2026-08-03-a72-cpu9-cluster-reuse/patches/0001-diagnostic-start-CPU9-by-reusing-the-prepared-cluster.patch":
        "4d72f15e739b788c32397927c03f52e6c6adde15c65008dd686ca50f62ce0a76",
    "experiments/2026-08-02-a72-one-way-cpu8-boundary/patches/0003-diagnostic-run-one-way-CPU8-startup.patch":
        "d901475205f21494d9b64aaffe35a569fdb4f9f491289b3e3bd03e97b339a2ca",
    "experiments/2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md":
        "0ce33cb344876363b9c35e3c12e9adef9fc4357071cc3d35f667da9d76b6cd97",
    "experiments/2026-07-22-a72-firmware-power-contract/results/active-gemian-boot-binary-audit-20260726.txt":
        "c550de24db711c26b2426d061fcfba713de51b8b32c9959754e12fdbfef7c83a",
    "experiments/2026-07-22-a72-firmware-power-contract/results/active-gemian-kernel-reconciliation-20260723.txt":
        "709ae67b0e89c45828096837d6faee4f6f4e3b81e031c94ab6fd8d0b7b10577c",
}


class ContractError(ValueError):
    """The frozen contract or its evidence violates a safety invariant."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def load_tsv(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == fields, f"schema changed: {path}")
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            require(None not in row, f"extra TSV cell at {path}:{line_number}")
            for field in fields:
                value = row.get(field)
                require(value is not None, f"missing {field} at {path}:{line_number}")
                require(value == value.strip(),
                        f"untrimmed {field} at {path}:{line_number}")
                require(not any(character in value for character in "\t\r\n"),
                        f"embedded TSV control in {field} at {path}:{line_number}")
            rows.append(row)  # type: ignore[arg-type]
        return rows


def canonical_row_sha256(row: dict[str, str], fields: tuple[str, ...]) -> str:
    encoded = ("\t".join(row[field] for field in fields) + "\n").encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def row_map(rows: Iterable[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    mapped: dict[str, dict[str, str]] = {}
    for row in rows:
        require(row[key] not in mapped, f"duplicate {key}: {row[key]}")
        mapped[row[key]] = row
    return mapped


def validate_contract(rows: list[dict[str, str]]) -> None:
    require(tuple(row["id"] for row in rows) == EXPECTED_IDS, "boundary inventory changed")
    require(len({row["boundary"] for row in rows}) == len(rows), "duplicate boundary")
    by_id = row_map(rows, "id")

    for row in rows:
        require(all(row[field] for field in CONTRACT_FIELDS), f"empty field in {row['id']}")
        require(row["decision"] in DECISIONS, f"invalid decision in {row['id']}")
        require(row["proof_order"].isdigit(),
                f"non-numeric proof order in {row['id']}")
        require(row["timeout"] == EXPECTED_TIMEOUTS[row["id"]],
                f"timeout changed in {row['id']}")
        require(row["failure_response"] == EXPECTED_FAILURE_RESPONSES[row["id"]],
                f"failure response changed in {row['id']}")

    pre_psci = {"C01", "C02", "C03", "L01", "L02", "L03"}
    post_psci = set(EXPECTED_IDS) - pre_psci
    for identifier in pre_psci:
        row = by_id[identifier]
        require(row["inverse"].startswith("release-owned-"),
                f"pre-PSCI inverse changed in {identifier}")
        require(row["failure_response"].startswith("deny-cpu-off;"),
                f"pre-PSCI failure response changed in {identifier}")
        require("no-hardware" in row["failure_response"],
                f"pre-PSCI response permits a hardware write in {identifier}")
    for identifier in post_psci:
        row = by_id[identifier]
        require(row["inverse"] == "none-after-psci",
                f"guessed post-PSCI inverse in {identifier}")
        require("reset-only" in row["failure_response"],
                f"post-PSCI response lacks reset-only terminal in {identifier}")
        require("continue" not in row["failure_response"] and
                "optional" not in row["failure_response"] and
                "retry-cpu-on" not in row["failure_response"],
                f"post-PSCI response permits retry or continuation in {identifier}")

    forbidden_cpu9_boundaries = (
        "buckb-provider-reference-release",
        "cluster-and-cci-off",
        "dcm-disable",
        "isolation-final-state-attribution",
        "sram-final-state-attribution",
    )
    for identifier in CPU9_IDS:
        boundary = by_id[identifier]["boundary"]
        require(not any(token in boundary for token in forbidden_cpu9_boundaries),
                f"CPU9-off touches shared teardown in {identifier}")

    target_paths = {"C04": "cpu9", "L04": "cpu8"}
    for identifier, target in target_paths.items():
        row = by_id[identifier]
        require(row["physical_writer"] == "secure-psci-cpu-off-target-path",
                f"target CPU_OFF path writer changed in {identifier}")
        require(row["requester"] == "generic-arm64-psci",
                f"target CPU_OFF requester changed in {identifier}")
        require(row["decision"] == "contract-defined",
                f"source-closed target path was reopened in {identifier}")
        target_tokens = (
            f"target={target}",
            "preparation=exact-source-closed",
            "gic-deactivation=exact-source-closed",
            "cache-maintenance=exact-source-closed",
            "wfi-entry=exact-source-closed",
            "no-a72-mtcmos-teardown",
        )
        for token in target_tokens:
            require(token in row["required_prestate"],
                    f"target CPU_OFF source path missing {token} in {identifier}")
        require("no-a72-mtcmos-teardown" in row["success_readback"],
                f"target CPU_OFF falsely gained MTCMOS teardown in {identifier}")
        require("one-parent-affinity-query-attempt-required" in
                row["success_readback"],
                f"target CPU_OFF lost controlling-query handoff in {identifier}")

    active_queries = ("C05", "L05")
    for identifier in active_queries:
        row = by_id[identifier]
        require(row["physical_writer"].startswith("secure-power-off-big-"),
                f"AFFINITY_INFO was made passive in {identifier}")
        require(row["requester"] == "linux-a72-state-machine-affinity-info",
                f"AFFINITY_INFO requester changed in {identifier}")
        require("affinity-query-and-secure-power-off-big" in row["boundary"],
                f"AFFINITY_INFO teardown boundary missing in {identifier}")
        require("one-controlling-query-attempt" in row["required_prestate"],
                f"state-changing AFFINITY_INFO attempt count changed in {identifier}")
        require("hardware-replay-control=firmware-private-big_on-not-query-count" in
                row["required_prestate"],
                f"AFFINITY_INFO replay control misattributed in {identifier}")
        require("one-affinity-info-level0-call=off" in row["success_readback"],
                f"AFFINITY_INFO completion result missing in {identifier}")
        require(row["decision"] == "blocked-timeout",
                f"unbounded AFFINITY_INFO was promoted in {identifier}")
        require("unbounded" in row["timeout"] and
                "no-call-bound" in row["timeout"] and
                "10x10ms" not in row["timeout"],
                f"false complete AFFINITY_INFO timeout in {identifier}")
        require("prohibit-query-retry-after-fault" in row["failure_response"],
                f"AFFINITY_INFO failure permits a faulted retry in {identifier}")
    require(by_id["C05"]["timeout"].startswith("two-reachable-inner-waits"),
            "CPU9 retained secure wait count changed")
    require(by_id["L05"]["timeout"].startswith("eight-reachable-inner-waits"),
            "last-core secure wait count changed")

    cpu9_effects = (
        "cpu9-pwr-con-0x10006244=clear-bit2-then-bit0",
        "cpu8-pwr-con-write-set=empty",
        "diagnostic-0x10222400=write-0x0000001b",
        "diagnostic-0x10222404=read-twice",
        "firmware-private-big_on-transition=0x3-to-0x1",
        "cluster-power-write-set=empty",
        "clock-write-set=empty",
        "cci-write-set=empty",
        "spm-shared-write-set=empty",
        "provider-write-set=empty",
    )
    for token in cpu9_effects:
        require(token in by_id["C05"]["success_readback"],
                f"CPU9 power_off_big effect missing {token}")
    cpu9_effect_set = set(by_id["C05"]["success_readback"].split(";"))
    require("all-shared-write-set=empty" not in cpu9_effect_set and
            "shared-write-set=empty" not in cpu9_effect_set,
            "CPU9 secure-control writes were hidden by an empty shared set")
    require("cpu8-affinity-info" not in by_id["C05"]["success_readback"],
            "retained CPU8 was queried through active AFFINITY_INFO")
    require("retained-cpu8-proof-deferred-to-C06-non-psci-observation" in
            by_id["C05"]["success_readback"],
            "retained CPU8 proof did not defer to C06")

    require(by_id["C07"]["physical_writer"] == "none-observation",
            "CPU9 shared-state invariant gained a writer")
    require("C05-source-proof-is-not-runtime-invariance" in
            by_id["C07"]["required_prestate"],
            "CPU9 static effect proof replaced runtime invariance")
    require("all-runtime-readbacks-owner-attributed" in
            by_id["C07"]["success_readback"],
            "CPU9 runtime invariance lost independent ownership")
    require("cluster-off-notifier=not-entered" in by_id["C03"]["success_readback"],
            "CPU9 non-last notifier prohibition missing")
    require("cluster-off-notifier=entered" not in by_id["C03"]["success_readback"],
            "CPU9 notifier readback is contradictory")

    entry_fields = (
        "suspend-admission=frozen",
        "provider-ref=1",
        "page=0x80",
        "buckb-enable=1",
        "buckb-vsel=captured",
        "spm-reset=captured",
        "external-isolation=captured",
        "sram-registers=captured",
        "secure-sentinels=captured",
        "mp2-dcm=captured",
        "idvfs=captured",
        "b-clock=captured",
        "cci-clock=captured",
        "cci-admission=on",
        "firmware-private-big_on-entry-proof=unresolved",
        "all-resource-readbacks-owner-attributed",
    )
    for token in entry_fields:
        require(token in by_id["C02"]["success_readback"],
                f"CPU9 entry snapshot missing {token}")
    invariant_fields = (
        "provider-ref",
        "page",
        "buckb-enable",
        "buckb-vsel",
        "spm-reset",
        "external-isolation",
        "sram-registers",
        "secure-sentinels",
        "mp2-dcm",
        "idvfs",
        "b-clock",
        "cci-clock",
        "cci-admission",
    )
    for field in invariant_fields:
        require(f"{field}=bit-exact-C02-entry" in by_id["C07"]["success_readback"],
                f"CPU9 invariance missing {field}")

    require(int(by_id["C05"]["proof_order"]) <
            int(by_id["C06"]["proof_order"]),
            "CPU8 responsiveness gate precedes active affinity teardown")
    require(int(by_id["C07"]["proof_order"]) <
            int(by_id["C08"]["proof_order"]),
            "CPU9 membership commits before invariance gates")
    final_cpu9_fields = (
        "cpu8=online",
        "cpu9=offline",
        "members=0x1",
        "firmware-private-big_on=0x1-source-attributed",
        "provider-ref=1",
        "shared-resource-state=bit-exact-C02-entry",
        "policy-admission=released",
        "suspend-admission=released",
        "transition-lock=released",
        "transaction=consumed",
        "cpu9-on-off-admission=closed-until-owned-transition",
    )
    for token in final_cpu9_fields:
        require(token in by_id["C08"]["success_readback"],
                f"CPU9 terminal commit missing {token}")
    require("suspend-admission=frozen" in by_id["C08"]["required_prestate"],
            "CPU9 suspend interlock was not held to final commit")
    for identifier in tuple(f"L{number:02d}" for number in range(6, 14)):
        require(int(by_id["L05"]["proof_order"]) <
                int(by_id[identifier]["proof_order"]),
                f"last-user post-query attribution gate precedes active teardown in {identifier}")
    require("L05-source-proof-is-not-runtime-readback" in
            by_id["L06"]["required_prestate"],
            "last-core static source proof replaced runtime readback")

    last_core_effects = (
        "cpu8-pwr-con-0x10006240=clear-bit2-then-bit0",
        "firmware-private-big_on-transition=0x1-to-0x0",
        "cci-snoop-dvm=withdrawn",
        "shared-control-0x1022220c=or-0x11-twice-symbolic-unresolved",
        "cluster-snoop-control-0x10396000=exact-source-attributed",
        "internal-bus-protection-0x10001234=or-0x00000444",
        "b-mux-0x1001a270=clear-bit0",
        "b-pll-0x102224a0=clear-bit0",
        "spm-0x10006218=set-bit4-clear-bit2-then-bit0",
        "spm-0x10006290=or-0x2",
    )
    for token in last_core_effects:
        require(token in by_id["L05"]["success_readback"],
                f"last-core power_off_big effect missing {token}")
    require("cpu9-affinity-info" not in by_id["L05"]["success_readback"],
            "already-off CPU9 was requeried through active AFFINITY_INFO")
    require("prior-cpu9-off-proof-committed" in by_id["L05"]["required_prestate"] and
            "cpu9-proof-not-requeried" in by_id["L05"]["success_readback"],
            "last-core path lost committed CPU9-off proof")
    require("spm-0x10006218-source-writer=exact-attributed" in
            by_id["L09"]["success_readback"],
            "last-core SPM reset source attribution missing")
    require("spm-0x10006290-source-operation=or-0x2" in
            by_id["L10"]["success_readback"],
            "last-core isolation source attribution missing")
    require(by_id["L11"]["physical_writer"].startswith("unresolved") and
            "sram-write-absent-from-exact-secure-path" in
            by_id["L11"]["success_readback"],
            "unresolved SRAM writer was invented")
    require(int(by_id["L13"]["proof_order"]) >
            int(by_id["L12"]["proof_order"]),
            "BUCKB is not the final hardware release")
    require(by_id["L13"]["decision"] == "blocked-provider",
            "unimplemented writable provider was promoted")
    require(by_id["L03"]["decision"] == "blocked-owner",
            "last-user notifier owner was promoted")
    require("pll-off-not-assumed" in by_id["L06"]["success_readback"] and
            "pll=off" not in by_id["L06"]["success_readback"],
            "last-user secure state assumes PLL-off")
    require(by_id["L09"]["requester"] ==
            "linux-a72-state-machine-affinity-info" and
            by_id["L10"]["requester"] ==
            "linux-a72-state-machine-affinity-info",
            "attributed secure SPM requester changed")
    require(by_id["L11"]["requester"] == "unresolved-off-path-requester",
            "unresolved SRAM requester was invented")
    provider_release_fields = (
        "provider-ref=0",
        "buckb-enable=0",
        "page=0x80",
        "buckb-vsel=transaction-captured",
        "no-vsel-write",
    )
    for token in provider_release_fields:
        require(token in by_id["L13"]["success_readback"],
                f"provider release missing {token}")
    require("suspend-admission=frozen" in by_id["L02"]["success_readback"],
            "last-user suspend interlock was not acquired")
    require("suspend-admission=frozen" in by_id["L14"]["required_prestate"],
            "last-user suspend interlock was not held to final commit")
    require("suspend-admission=released" in by_id["L14"]["success_readback"],
            "last-user suspend interlock was not released")
    require("transaction=consumed" in by_id["L14"]["success_readback"],
            "last-user transaction was not consumed")
    require("cpu-on-off-admission=closed-until-owned-transition" in
            by_id["L14"]["success_readback"],
            "last-user CPU admission was not closed")
    require("firmware-private-big_on=0x0-source-attributed" in
            by_id["L14"]["success_readback"],
            "last-user private membership poststate missing")

    require(
        tuple((row["scenario"], int(row["proof_order"])) for row in rows) ==
        tuple(("cpu9-off-retain-cpu8", number) for number in range(1, 9)) +
        tuple(("last-a72-off", number) for number in range(1, 15)),
        "scenario proof order changed",
    )

    for row in rows:
        if row["physical_writer"].startswith("unresolved") or \
                row["requester"].startswith("unresolved"):
            require(row["decision"] in {
                "blocked-owner",
                "blocked-owner-order",
                "blocked-policy-owner",
            }, f"unresolved owner promoted in {row['id']}")
        if "unresolved" in row["timeout"]:
            require(row["decision"] != "contract-defined",
                    f"unresolved timeout promoted in {row['id']}")
        if row["decision"] == "blocked-timeout":
            require("unbounded" in row["timeout"],
                    f"timeout blocker lacks unbounded call in {row['id']}")

    defined_ids = tuple(row["id"] for row in rows
                        if row["decision"] == "contract-defined")
    require(defined_ids == ("C04", "L04"),
            "blocking decision inventory changed")

    for row in rows:
        require(
            canonical_row_sha256(row, CONTRACT_FIELDS) ==
            EXPECTED_CONTRACT_ROW_SHA256[row["id"]],
            f"canonical contract row changed in {row['id']}",
        )

    cpu9_blockers = sum(by_id[identifier]["decision"] != "contract-defined"
                        for identifier in CPU9_IDS)
    last_blockers = sum(by_id[identifier]["decision"] != "contract-defined"
                        for identifier in LAST_IDS)
    require(cpu9_blockers > 0 and last_blockers > 0,
            "CPU_OFF was silently made implementation-eligible")


def validate_reconciliation(rows: list[dict[str, str]]) -> None:
    require(tuple(row["source_id"] for row in rows) == RECONCILIATION_IDS,
            "reconciliation inventory changed")
    require(len({row["boundary"] for row in rows}) == len(rows),
            "duplicate reconciliation boundary")
    by_id = row_map(rows, "source_id")
    for row in rows:
        require(all(row[field] for field in RECONCILIATION_FIELDS),
                f"empty reconciliation field in {row['source_id']}")
        require(row["current_disposition"] == EXPECTED_DISPOSITIONS[row["source_id"]],
                f"disposition changed in source row {row['source_id']}")
        require(row["evidence_path"] ==
                EXPECTED_RECONCILIATION_EVIDENCE[row["source_id"]],
                f"evidence path changed in source row {row['source_id']}")
        require(row["evidence_path"] in EVIDENCE_SHA256,
                f"unpinned evidence in source row {row['source_id']}")
        evidence_path = Path(row["evidence_path"])
        require(not evidence_path.is_absolute() and ".." not in evidence_path.parts,
                f"unsafe evidence path in source row {row['source_id']}")
        candidate = REPOSITORY / evidence_path
        experiments_root = (REPOSITORY / "experiments").resolve()
        require(candidate.resolve().is_relative_to(experiments_root),
                f"evidence escapes experiments in source row {row['source_id']}")
        require(candidate.is_file(),
                f"missing evidence path in source row {row['source_id']}")
        require(
            canonical_row_sha256(row, RECONCILIATION_FIELDS) ==
            EXPECTED_RECONCILIATION_ROW_SHA256[row["source_id"]],
            f"canonical reconciliation row changed in {row['source_id']}",
        )

    require(sum(row["current_disposition"].startswith("closed-preiso")
                for row in rows) == 3,
            "pre-isolation closure count changed")
    require(by_id["18"]["current_disposition"] ==
            "startup-and-off-source-closed-contract-open",
            "CPU9 source attribution was promoted to implementable CPU9-off")
    require(by_id["19"]["current_disposition"] == "blocked-resume-owner",
            "suspend/resume ownership was promoted")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_evidence() -> None:
    for relative, expected in EVIDENCE_SHA256.items():
        path = REPOSITORY / relative
        require(path.is_file(), f"missing pinned evidence: {relative}")
        require(sha256(path) == expected, f"pinned evidence drift: {relative}")


def validation_report(
    contract_rows: list[dict[str, str]],
    reconciliation_rows: list[dict[str, str]],
) -> list[str]:
    defined = sum(row["decision"] == "contract-defined" for row in contract_rows)
    blocked = len(contract_rows) - defined
    return [
        "validation=a72-safe-off-ownership-contract",
        f"contract_boundaries={len(contract_rows)}",
        f"cpu9_off_boundaries={len(CPU9_IDS)}",
        f"last_a72_off_boundaries={len(LAST_IDS)}",
        f"contract_defined={defined}",
        f"blocked={blocked}",
        f"reconciliation_rows={len(reconciliation_rows)}",
        "closed_preiso_rows=3",
        "secure_target_paths_contract_defined=2",
        "active_affinity_timeout_blockers=2",
        f"evidence_files={len(EVIDENCE_SHA256)}",
        "cpu9_off=BLOCKED",
        "last_a72_off=BLOCKED",
        "gate4=BLOCKED",
        "cpu_off_candidate_authorized=no",
        "build_authorized=no",
        "device_action=none",
        "next_action=linux-private-membership-policy-suspend-notifier-timeout-and-observer-contract",
    ]


def validate_authorization(report: list[str]) -> None:
    required = {
        "cpu9_off=BLOCKED",
        "last_a72_off=BLOCKED",
        "gate4=BLOCKED",
        "cpu_off_candidate_authorized=no",
        "build_authorized=no",
        "device_action=none",
    }
    require(required.issubset(set(report)), "blocking authorization markers changed")
    require(not any(line.endswith("authorized=yes") for line in report),
            "new authorization was introduced")


def main() -> int:
    contract_rows = load_tsv(CONTRACT, CONTRACT_FIELDS)
    reconciliation_rows = load_tsv(RECONCILIATION, RECONCILIATION_FIELDS)
    validate_contract(contract_rows)
    validate_reconciliation(reconciliation_rows)
    validate_evidence()

    report = validation_report(contract_rows, reconciliation_rows)
    validate_authorization(report)
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as error:
        raise SystemExit(f"error: {error}") from error
