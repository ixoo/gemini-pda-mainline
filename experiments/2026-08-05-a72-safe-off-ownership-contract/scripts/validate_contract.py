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
    "contract-defined",
}
EXPECTED_TIMEOUTS = {
    "C01": "same-critical-section-no-wait",
    "C02": "policy-drain-and-entry-observation-timeouts-unresolved",
    "C03": "synchronous-before-psci",
    "C04": "target-nonreturning;parent-check-at-C05",
    "C05": "10x10ms-affinity-polls",
    "C06": "cpu8-callback-timeout-unresolved",
    "C07": "per-owner-invariance-readback-timeouts-unresolved",
    "C08": "same-critical-section-after-C07",
    "L01": "same-critical-section-no-wait",
    "L02": "policy-drain-and-entry-observation-timeouts-unresolved",
    "L03": "synchronous-before-psci",
    "L04": "target-nonreturning;parent-check-at-L05",
    "L05": "10x10ms-affinity-polls",
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
    "C04": "retain-conservative-members-and-C02-shared-state;prohibit-retry;reset-only",
    "C05": "retain-conservative-members-and-C02-shared-state;prohibit-retry;reset-only",
    "C06": "retain-conservative-members-and-C02-shared-state;prohibit-retry;reset-only",
    "C07": "retain-exact-observed-shared-state-and-members;prohibit-retry;reset-only",
    "C08": "terminal-fault;no-retry;reset-only",
    "L01": "deny-cpu-off;no-hardware-change",
    "L02": "deny-cpu-off;release-only-owned-software-state;no-hardware-write",
    "L03": "deny-cpu-off;no-hardware-write",
    "L04": "retain-conservative-members-reference-and-L02-shared-state;prohibit-retry;reset-only",
    "L05": "retain-conservative-members-reference-and-L02-shared-state;prohibit-retry;reset-only",
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
    "C01": "c699b46873955974cc9fc90db8fc724491ea309a93dee46b164805ea58aa1b4c",
    "C02": "790aafedc11b81bb3b5f8c73eaa26ad0e0d3ae1ebfeebc2e01e240f22e6718d4",
    "C03": "e70f4e5eaf56c76fb33867895599577afe682e52ca5e23b9105935b3d4c0b1ae",
    "C04": "d0b49f5da8792fe62f0858421300fb1055725ba8f0a5c06068fd9a2fb45ec289",
    "C05": "b36140d03b1e6a0b300dfeee4fe51849d260ba1f99dd5c4a281eeeb3e4ad38e1",
    "C06": "cb4a7a55356101482f6ab54e9446f80449404d0ab419258928b06c353b8906bd",
    "C07": "d9f7f5b46f6ed919e0634dda1560babf3d53a39dc8ffa1e83b56f956b3d0a869",
    "C08": "9e559e8fbbeaf0ded09a125319965ce7898b2dd42f5714464ef871746805dc69",
    "L01": "155ddd12b449924e93ee4aa8e73e595a6505c161d27020ed70073f46ba819529",
    "L02": "894ca7d3b1b9202aca843e1faf4108d12eb2d2621735557ae9a76d0438a6a7b3",
    "L03": "61e33e3dde07e7c484dc8ea4b52b5608af2b7cde6762bda74c0b302e1069c015",
    "L04": "a96d8495174ac08eb82c473613e4da5f98b34b7afdbe65be31afaca35fc69656",
    "L05": "3dc693a6b99e70cc15a008ce989cd36edb1bbeb023f42a005bd8ae0f44c7a827",
    "L06": "e4c5935fcef85cf2adb4ae60ae78c621aff7178d57ce38665a3093edaa688ce7",
    "L07": "ac7c28714092ea33a0c6200e57facc5dcd37d31324d20425a55e8438d3a1c97f",
    "L08": "a97c1664b1fcf65bf528946d445795aa490c0b7cf4f1d5f65857781d2c9d2d53",
    "L09": "0cebd26adefd27abcc7ad6221b4d5eb3173aabfd84a7c31a7b537c15a4ce1358",
    "L10": "d4619a5d978d9b4b303c066e88edc198e7c48770d5b7d8107b956efb69464093",
    "L11": "d2a3cd7e4541dba802be2b97daceeacb015d34f58fca4354699492f4f9ab0743",
    "L12": "3d44bec90ac0c3db5089bf9ebb0aa423ca88aabbbb49b3ada3c257038e8ee0ce",
    "L13": "e74581d63c9ba5e9001ad144744d4029626e7de10b69468b0438e6be52e906e5",
    "L14": "beea736069a27aae45f24fa92b3fa37bddb4e54442bbcca48c6263af3b47ea8d",
}
EXPECTED_DISPOSITIONS = {
    "01": "forward-closed-off-ledger-open",
    "02": "closed-preiso-rollback",
    "03": "forward-closed-off-readback-open",
    "04": "closed-preiso-rollback",
    "05": "forward-closed-provider-release-open",
    "06": "closed-preiso-rollback",
    "07": "blocked-vsel-owner",
    "08": "blocked-postiso-owner",
    "09": "blocked-postiso-owner",
    "10": "forward-closed-off-owner-open",
    "11": "startup-closed-off-open",
    "12": "forward-closed-off-owner-open",
    "13": "startup-closed",
    "14": "blocked-failure-semantics",
    "15": "blocked-policy-owner",
    "16": "blocked-policy-owner",
    "17": "split-safe-off-open",
    "18": "startup-closed-off-open",
    "19": "blocked-resume-owner",
}
EXPECTED_RECONCILIATION_EVIDENCE = {
    "01": "experiments/2026-08-03-a72-scheduler-context/results/runtime-unpark-attempt-2-repeatability-pass-20260805.txt",
    "02": "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt",
    "03": "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt",
    "04": "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt",
    "05": "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt",
    "06": "experiments/2026-08-02-a72-pre-isolation-rollback-discriminator/results/runtime-2-20260802.txt",
    "07": "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt",
    "08": "experiments/2026-08-02-a72-one-way-cpu8-boundary/results/isolation-owner-audit-20260802.txt",
    "09": "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt",
    "10": "experiments/2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md",
    "11": "experiments/2026-08-03-a72-scheduler-context/results/runtime-unpark-attempt-2-repeatability-pass-20260805.txt",
    "12": "experiments/2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md",
    "13": "experiments/2026-08-03-a72-scheduler-context/results/runtime-unpark-attempt-2-repeatability-pass-20260805.txt",
    "14": "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt",
    "15": "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt",
    "16": "experiments/2026-07-22-a72-firmware-power-contract/results/a72-firmware-power-contract-prerequisites-20260722.md",
    "17": "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/runtime-first-natural-pair-20260802.txt",
    "18": "experiments/2026-08-03-a72-scheduler-context/results/runtime-unpark-attempt-2-repeatability-pass-20260805.txt",
    "19": "experiments/2026-08-02-a72-ownership-rollback-audit/results/ownership-matrix.tsv",
}
EXPECTED_RECONCILIATION_ROW_SHA256 = {
    "01": "573f98c77a0497c0e1c8504d1cb780d4b0471eb1a7944f8a2392c232c8e70c75",
    "02": "ba53e1b17babc53c1c60add44f2d297e2b9e9b20b0894ef8f8eafe22f43645c0",
    "03": "aa2b60af97cc141056bd717c59076dfe077d68738b782d6bd90a2dec1f9797e7",
    "04": "366d4146d3e51f6333f04d450b89d3bc31efe24f3e1203c9f58eeafecf32b5ab",
    "05": "d4adf58ca4467a8cb94e7c4e9fc1a460b0758d0458e6f32538bfa00976f85a84",
    "06": "e24b689cadd4a86bbf85fb3cb6f49cea5aad58a401fb41cf2538632f556e2c8a",
    "07": "f7b427c45dd4e2717ebcd918e52a36e2651bb413063252745908568decf0e016",
    "08": "dd89f80ec6d9367654b322db5f963c27a60810d121faa7d28f8a49fbd5b2a630",
    "09": "fadb0765b18e6271114d6b8222106b697d721092f842af60606c9f3037c7a0d4",
    "10": "23ebca9fbf6bfe516659b5671db3dcc20c65bbb090d61f2ee8ba936cfd7c6ee6",
    "11": "42b2b8fa3f4ed266b1371e02e0ca236bd23b3c3bc27d2bccfc6f925cdd367bc8",
    "12": "13fc68b0e5f25166129deffb4000cb9a0b4fd4619a5acf5e9ffee74500bba459",
    "13": "b3470c9c994b4f7c163153e06257e4c4ba45e33bf6c6369ffffcc56393739ff9",
    "14": "3e9cf1ff8723f18289c36545d701e429cb93a0a498e7629fa7fe5124e0bcb5f6",
    "15": "c4bb3b2ec9d16d0203dc2d64c0d12954cef9df99eb332d2a3b96a58908ec9cb9",
    "16": "b34386015d9dbeb7dcdb8747b7db96d4c839892ed0a9f8ade9a38063e0bd65f7",
    "17": "1aa04ac58d9795b9fb284b348c8c1c71e303282e6b0e2b6f4849bfd6b3300a9d",
    "18": "b12e2b51f316d73b1e5a6f3fe40be68a2cc128b69166642f87e9be8a94e74da2",
    "19": "f1e656258fe7072ef47c6e42adce7e1c98627ae87748e632efd460af50416131",
}
EVIDENCE_SHA256 = {
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
    require(by_id["C07"]["physical_writer"] == "none-observation",
            "CPU9 shared-state invariant gained a writer")
    require("cluster-off-notifier=not-entered" in by_id["C03"]["success_readback"],
            "CPU9 non-last notifier prohibition missing")
    require("cluster-off-notifier=entered" not in by_id["C03"]["success_readback"],
            "CPU9 notifier readback is contradictory")
    cpu9_secure_gate = (
        "secure-cpu9-off-callgraph=exact-attributed",
        "shared-write-set=empty",
        "per-core-effects-only",
    )
    for token in cpu9_secure_gate:
        require(token in by_id["C04"]["required_prestate"],
                f"CPU9 secure off audit missing {token}")

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
        "all-readbacks-owner-attributed",
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
            "CPU8 responsiveness gate precedes affinity OFF")
    require(int(by_id["C07"]["proof_order"]) <
            int(by_id["C08"]["proof_order"]),
            "CPU9 membership commits before invariance gates")
    final_cpu9_fields = (
        "cpu8=online",
        "cpu9=offline",
        "members=0x1",
        "provider-ref=1",
        "shared-state=bit-exact-C02-entry",
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
                f"last-user post-OFF attribution gate precedes affinity proof in {identifier}")
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
    for identifier in ("L09", "L10", "L11"):
        require(by_id[identifier]["requester"] == "unresolved-off-path-requester",
                f"unresolved off-path requester promoted in {identifier}")
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

    defined_ids = tuple(row["id"] for row in rows
                        if row["decision"] == "contract-defined")
    require(defined_ids == ("L05",), "blocking decision inventory changed")

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

    require(sum(row["current_disposition"] == "closed-preiso-rollback" for row in rows) == 3,
            "pre-isolation closure count changed")
    require(by_id["18"]["current_disposition"] == "startup-closed-off-open",
            "CPU9 startup evidence was promoted to CPU9-off")
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
        "cpu9_startup_closed_off_open=2",
        f"evidence_files={len(EVIDENCE_SHA256)}",
        "cpu9_off=BLOCKED",
        "last_a72_off=BLOCKED",
        "gate4=BLOCKED",
        "cpu_off_candidate_authorized=no",
        "build_authorized=no",
        "device_action=none",
        "next_action=exact-secure-cpu-off-owner-audit-and-membership-policy-suspend-notifier-contract",
    ]


def main() -> int:
    contract_rows = load_tsv(CONTRACT, CONTRACT_FIELDS)
    reconciliation_rows = load_tsv(RECONCILIATION, RECONCILIATION_FIELDS)
    validate_contract(contract_rows)
    validate_reconciliation(reconciliation_rows)
    validate_evidence()

    print("\n".join(validation_report(contract_rows, reconciliation_rows)))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as error:
        raise SystemExit(f"error: {error}") from error
