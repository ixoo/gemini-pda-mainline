#!/usr/bin/env python3
"""Validate the frozen A72 reference mapping and READY closure ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "gemini-mainline-a72-attestation-closure-v1"

FULL_REGISTER_IMAGE_FIELDS = {
    "ctr",
    "cntfrq",
    "dczid",
    "midr",
    "revidr",
    "aidr",
    "gmid",
    "smidr",
    "mpamidr",
    "id_aa64dfr0",
    "id_aa64dfr1",
    "id_aa64isar0",
    "id_aa64isar1",
    "id_aa64isar2",
    "id_aa64isar3",
    "id_aa64mmfr0",
    "id_aa64mmfr1",
    "id_aa64mmfr2",
    "id_aa64mmfr3",
    "id_aa64mmfr4",
    "id_aa64pfr0",
    "id_aa64pfr1",
    "id_aa64pfr2",
    "id_aa64zfr0",
    "id_aa64smfr0",
    "id_aa64fpfr0",
    "aarch32.id_dfr0",
    "aarch32.id_dfr1",
    "aarch32.id_isar0",
    "aarch32.id_isar1",
    "aarch32.id_isar2",
    "aarch32.id_isar3",
    "aarch32.id_isar4",
    "aarch32.id_isar5",
    "aarch32.id_isar6",
    "aarch32.id_mmfr0",
    "aarch32.id_mmfr1",
    "aarch32.id_mmfr2",
    "aarch32.id_mmfr3",
    "aarch32.id_mmfr4",
    "aarch32.id_mmfr5",
    "aarch32.id_pfr0",
    "aarch32.id_pfr1",
    "aarch32.id_pfr2",
    "aarch32.mvfr0",
    "aarch32.mvfr1",
    "aarch32.mvfr2",
}

EXPECTED_OBSERVED_FIELDS = [
    "ctr",
    "cntfrq",
    "dczid",
    "midr",
    "revidr",
    "id_aa64dfr0",
    "id_aa64isar0",
    "id_aa64isar1",
    "id_aa64mmfr0",
    "id_aa64mmfr1",
    "id_aa64pfr0",
    "id_aa64pfr1",
    "aarch32.id_isar0",
    "aarch32.id_isar1",
    "aarch32.id_isar2",
    "aarch32.id_isar3",
    "aarch32.id_isar4",
    "aarch32.id_isar5",
    "aarch32.id_mmfr0",
    "aarch32.id_mmfr1",
    "aarch32.id_mmfr2",
    "aarch32.id_mmfr3",
    "aarch32.id_pfr0",
    "aarch32.id_pfr1",
]

EXPECTED_UNMEASURED_FIELDS = [
    "aidr",
    "gmid",
    "smidr",
    "mpamidr",
    "id_aa64dfr1",
    "id_aa64isar2",
    "id_aa64isar3",
    "id_aa64mmfr2",
    "id_aa64mmfr3",
    "id_aa64mmfr4",
    "id_aa64pfr2",
    "id_aa64zfr0",
    "id_aa64smfr0",
    "id_aa64fpfr0",
    "aarch32.id_dfr0",
    "aarch32.id_dfr1",
    "aarch32.id_isar6",
    "aarch32.id_mmfr4",
    "aarch32.id_mmfr5",
    "aarch32.id_pfr2",
    "aarch32.mvfr0",
    "aarch32.mvfr1",
    "aarch32.mvfr2",
]

EXPECTED_TARGETS = {
    8: {
        "capsule_identity": "e35596c52bc8b40b",
        "mpidr": "0000000000000200",
    },
    9: {
        "capsule_identity": "600c5e2d6733661d",
        "mpidr": "0000000000000201",
    },
}

EXPECTED_TARGET_GROUPS = {
    "MIDR": ("complete", "missing", "early-target-entry-validator"),
    "ID_REGS": (
        "partial-24-of-47",
        "missing",
        "field-valid-expected-contract-and-entry-validator",
    ),
    "CTR": (
        "partial-ctr-and-clidr-no-effective-value",
        "missing",
        "arm64-cache-type-planner-and-entry-validator",
    ),
    "GIC": ("missing", "missing", "arm64-gic-current-boot-owner"),
    "HYP": ("missing", "missing", "arm64-el2-current-boot-owner"),
    "WA1": ("missing", "missing", "arm64-smccc-current-boot-owner"),
    "WA2": ("missing", "missing", "arm64-smccc-current-boot-owner"),
    "WA3": ("missing", "missing", "arm64-smccc-current-boot-owner"),
    "ASID": (
        "missing",
        "missing",
        "arm64-address-space-current-boot-owner",
    ),
    "GRANULE": (
        "missing",
        "missing",
        "arm64-address-space-current-boot-owner",
    ),
    "VA": ("missing", "missing", "arm64-address-space-current-boot-owner"),
}

EXPECTED_CURRENT_BOOT_GROUPS = {
    "runtime_binding": (
        "producer-exists-container-provenance-composition-required",
        "arm64-runtime-identity",
    ),
    "target_policy": (
        "missing",
        "arm64-current-command-line-and-firmware-policy",
    ),
    "system_capability": ("missing", "arm64-current-system-capability-owner"),
    "evidence_identity": ("missing", "arm64-core"),
    "plan_identity": ("missing", "arm64-core"),
    "architecture_commit": ("panic-stub", "arm64-core"),
    "system_verification": (
        "profile-callback-missing",
        "arm64-core-and-mt6797-profile",
    ),
    "alternatives_finalization": ("missing", "arm64-core"),
    "user_hwcap_finalization": (
        "profile-callback-missing",
        "arm64-core-and-mt6797-profile",
    ),
}

EXPECTED_STAGES = [
    ("bind-current-image", "arm64-core"),
    ("capture-current-system-policy", "arm64-core"),
    ("freeze-expected-target-contract", "arm64-core"),
    ("plan-capabilities-effects-and-hwcaps", "arm64-core"),
    ("mint-canonical-evidence-and-plan-identities", "arm64-core"),
    ("commit-architecture-effects", "arm64-core"),
    ("verify-system-and-alternatives", "arm64-core-and-mt6797-profile"),
    ("finalize-user-hwcaps", "arm64-core-and-mt6797-profile"),
    ("publish-ready", "arm64-core"),
    ("request-cpu8-once", "mt6797-admission-controller"),
    ("validate-current-cpu8-entry", "arm64-early-target-entry"),
    ("continue-ordinary-secondary-startup", "arm64-core"),
]

EXPECTED_FORBIDDEN_DESTINATIONS = [
    "observed_target_mpidr",
    "observed_target_midr",
    "observed_target_revidr",
    "runtime_target_cap",
    "runtime_target_policy",
    "runtime_system_cap",
]

EXPECTED_ENTRY_SOURCES = {
    "existing_order": [
        "check-local-cpu-capabilities",
        "cpuinfo-store-cpu",
        "notify-cpu-starting",
        "set-cpu-online",
    ],
    "new_order": [
        "check-local-cpu-capabilities",
        "cpuinfo-store-cpu",
        "validate-expected-target-contract",
        "notify-cpu-starting",
        "set-cpu-online",
    ],
    "cpuinfo_register_image": "existing-safe-or-feature-conditional-reader",
    "raw_ctr_and_clidr": "new-direct-entry-read-required",
    "standard_feature_mismatch": "existing-cpu-die-early",
    "expected_contract_mismatch": "new-park-before-notify-and-online",
}

PART_KEYS = {
    "core": {
        "abi",
        "fields",
        "valid",
        "error",
        "complete",
        "identity",
        "mpidr",
        "midr",
        "revidr",
        "cntfrq",
        "ctr",
        "dczid",
        "clidr",
    },
    "aa64": {
        "identity",
        "dfr0",
        "isar0",
        "isar1",
        "mmfr0",
        "mmfr1",
        "pfr0",
        "pfr1",
    },
    "a32isar": {
        "identity",
        "isar0",
        "isar1",
        "isar2",
        "isar3",
        "isar4",
        "isar5",
    },
    "a32mm": {
        "identity",
        "mmfr0",
        "mmfr1",
        "mmfr2",
        "mmfr3",
        "pfr0",
        "pfr1",
    },
}


class ValidationError(ValueError):
    """A frozen contract predicate did not hold."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_tokens(fragment: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for token in fragment.split():
        require("=" in token, f"malformed capsule token: {token}")
        key, value = token.split("=", 1)
        require(key not in tokens, f"duplicate capsule key: {key}")
        tokens[key] = value
    return tokens


def parse_capture(text: str) -> dict[int, dict[str, dict[str, str]]]:
    records: dict[int, dict[str, dict[str, str]]] = {8: {}, 9: {}}
    pattern = re.compile(
        r"^gemini-a72-regcap-v1 part=(core|aa64|a32isar|a32mm) "
        r"result=pass cpu=(8|9) (.+)$"
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        part = match.group(1)
        cpu = int(match.group(2))
        require(part not in records[cpu], f"duplicate cpu{cpu} {part} record")
        tokens = parse_tokens(match.group(3))
        require(set(tokens) == PART_KEYS[part], f"cpu{cpu} {part} schema changed")
        records[cpu][part] = tokens

    for cpu, parts in records.items():
        require(set(parts) == set(PART_KEYS), f"cpu{cpu} capsule parts incomplete")
        core = parts["core"]
        require(
            (core["abi"], core["fields"], core["valid"], core["error"], core["complete"])
            == ("1", "32", "0x1f", "0", "1"),
            f"cpu{cpu} core completion metadata changed",
        )
        identities = {part["identity"] for part in parts.values()}
        require(len(identities) == 1, f"cpu{cpu} capsule identities disagree")
    return records


def capture_registers(parts: dict[str, dict[str, str]]) -> dict[str, str]:
    core = parts["core"]
    aa64 = parts["aa64"]
    a32isar = parts["a32isar"]
    a32mm = parts["a32mm"]
    return {
        "ctr": core["ctr"],
        "cntfrq": core["cntfrq"],
        "dczid": core["dczid"],
        "midr": core["midr"],
        "revidr": core["revidr"],
        "id_aa64dfr0": aa64["dfr0"],
        "id_aa64isar0": aa64["isar0"],
        "id_aa64isar1": aa64["isar1"],
        "id_aa64mmfr0": aa64["mmfr0"],
        "id_aa64mmfr1": aa64["mmfr1"],
        "id_aa64pfr0": aa64["pfr0"],
        "id_aa64pfr1": aa64["pfr1"],
        **{f"aarch32.id_isar{i}": a32isar[f"isar{i}"] for i in range(6)},
        **{f"aarch32.id_mmfr{i}": a32mm[f"mmfr{i}"] for i in range(4)},
        "aarch32.id_pfr0": a32mm["pfr0"],
        "aarch32.id_pfr1": a32mm["pfr1"],
    }


def validate_document(document: dict[str, Any], capture_text: str) -> None:
    require(document.get("schema") == SCHEMA, "schema identity changed")
    require(document.get("plan_abi") == 7, "plan ABI changed")

    source = document.get("prepared_source", {})
    require(
        source.get("state")
        == "16b5e467943d87d5fedb162770a7e2229d5a40fed596eb54d9167abba15105ce",
        "prepared-source state changed",
    )
    for key, value in source.items():
        require(re.fullmatch(r"[0-9a-f]{64}", value) is not None, f"invalid {key}")

    reference = document.get("reference_capture", {})
    require(
        reference.get("role") == "prior-cycle-target-expectation-only",
        "reference role was promoted",
    )
    require(
        reference.get("may_populate_current_runtime_observation") is False,
        "prior-cycle evidence may populate current runtime observation",
    )
    observed = reference.get("register_image_observed_fields")
    unmeasured = reference.get("register_image_unmeasured_fields")
    require(observed == EXPECTED_OBSERVED_FIELDS, "observed register inventory changed")
    require(unmeasured == EXPECTED_UNMEASURED_FIELDS, "unmeasured inventory changed")
    require(set(observed).isdisjoint(unmeasured), "register inventories overlap")
    require(set(observed) | set(unmeasured) == FULL_REGISTER_IMAGE_FIELDS,
            "register image is not exactly partitioned")
    require(len(observed) == 24 and len(unmeasured) == 23,
            "register-image field counts changed")

    parsed = parse_capture(capture_text)
    targets = reference.get("targets")
    require(isinstance(targets, list) and len(targets) == 2, "target count changed")
    by_cpu: dict[int, dict[str, Any]] = {}
    for target in targets:
        cpu = target.get("cpu")
        require(cpu in EXPECTED_TARGETS and cpu not in by_cpu, "target CPU changed")
        by_cpu[cpu] = target
    require(set(by_cpu) == {8, 9}, "CPU8/CPU9 pair changed")

    for cpu in (8, 9):
        target = by_cpu[cpu]
        expected = EXPECTED_TARGETS[cpu]
        parts = parsed[cpu]
        core = parts["core"]
        require(target.get("capsule_identity") == expected["capsule_identity"],
                f"cpu{cpu} frozen identity changed")
        require(target.get("mpidr") == expected["mpidr"], f"cpu{cpu} MPIDR changed")
        require(target.get("clidr_el1") == "000000000a200023",
                f"cpu{cpu} CLIDR changed")
        require(core["identity"] == target["capsule_identity"],
                f"cpu{cpu} result identity mismatch")
        require(core["mpidr"] == target["mpidr"], f"cpu{cpu} result MPIDR mismatch")
        require(core["clidr"] == target["clidr_el1"],
                f"cpu{cpu} result CLIDR mismatch")
        registers = target.get("registers")
        require(isinstance(registers, dict), f"cpu{cpu} registers missing")
        require(list(registers) == EXPECTED_OBSERVED_FIELDS,
                f"cpu{cpu} named register order changed")
        require(registers == capture_registers(parts),
                f"cpu{cpu} frozen registers differ from result")

    shared8 = dict(by_cpu[8]["registers"])
    shared9 = dict(by_cpu[9]["registers"])
    require(shared8 == shared9, "CPU8/CPU9 shared register values disagree")

    mapping = document.get("abi7_mapping", {})
    groups = mapping.get("target_cap_groups", {})
    require(set(groups) == set(EXPECTED_TARGET_GROUPS), "target-cap groups changed")
    for name, expected in EXPECTED_TARGET_GROUPS.items():
        item = groups[name]
        require(
            (item.get("reference"), item.get("current_mainline"), item.get("owner"))
            == expected,
            f"{name} ownership/status changed",
        )
    require(groups["ID_REGS"]["reference"] == "partial-24-of-47",
            "partial ID registers were promoted to complete")

    current = mapping.get("current_boot_only_fields", {})
    require(set(current) == set(EXPECTED_CURRENT_BOOT_GROUPS),
            "current-boot owner groups changed")
    for name, expected in EXPECTED_CURRENT_BOOT_GROUPS.items():
        item = current[name]
        require((item.get("state"), item.get("owner")) == expected,
                f"{name} state/owner changed")
        require(item.get("fields"), f"{name} field inventory empty")

    contract = document.get("architecture_contract", {})
    require(
        contract.get("expected_target_schema") == "new-field-valid-schema-required",
        "expected-target schema requirement changed",
    )
    require(contract.get("forbidden_copy_destinations") == EXPECTED_FORBIDDEN_DESTINATIONS,
            "forbidden runtime-copy destinations changed")
    require(contract.get("entry_validation_sources") == EXPECTED_ENTRY_SOURCES,
            "entry validation source/order changed")
    stages = contract.get("stages")
    require(isinstance(stages, list) and len(stages) == len(EXPECTED_STAGES),
            "closure stage count changed")
    for index, (stage_id, owner) in enumerate(EXPECTED_STAGES, start=1):
        stage = stages[index - 1]
        require(stage.get("order") == index, f"closure order changed at {index}")
        require(stage.get("id") == stage_id, f"closure stage changed at {index}")
        require(stage.get("owner") == owner, f"closure owner changed for {stage_id}")
        require(stage.get("state"), f"closure state missing for {stage_id}")

    actions = contract.get("physical_actions", {})
    require(actions.get("cpu_request_before_ready") is False,
            "CPU request became possible before READY")
    require(actions.get("cpu8_request_count_max") == 1,
            "CPU8 request bound changed")
    require(actions.get("cpu9_request") is False, "CPU9 request became possible")
    require(actions.get("cpu_off") is False, "CPU_OFF became possible")
    require(actions.get("retry_count_max") == 0, "retry became possible")
    require(
        actions.get("entry_mismatch") == "refuse-before-ordinary-secondary-startup",
        "entry mismatch no longer fails closed",
    )


def validate_source_root(document: dict[str, Any], source_root: Path) -> None:
    expected = {
        "late_cpu_profile_header_sha256": Path("arch/arm64/include/asm/late_cpu_profile.h"),
        "late_cpu_profile_core_sha256": Path("arch/arm64/kernel/late_cpu_profile.c"),
        "mt6797_membership_sha256": Path("arch/arm64/kernel/mt6797_a72_membership.c"),
        "mt6797_psci_sha256": Path("arch/arm64/kernel/mt6797_psci.c"),
        "cpufeature_sha256": Path("arch/arm64/kernel/cpufeature.c"),
        "smp_sha256": Path("arch/arm64/kernel/smp.c"),
        "proton_pack_sha256": Path("arch/arm64/kernel/proton-pack.c"),
        "cpu_errata_sha256": Path("arch/arm64/kernel/cpu_errata.c"),
        "cpuinfo_sha256": Path("arch/arm64/kernel/cpuinfo.c"),
    }
    source = document["prepared_source"]
    for key, relative in expected.items():
        path = source_root / relative
        require(path.is_file(), f"prepared source missing {relative}")
        require(sha256_file(path) == source[key], f"prepared source changed: {relative}")

    header = (source_root / expected["late_cpu_profile_header_sha256"]).read_text()
    core = (source_root / expected["late_cpu_profile_core_sha256"]).read_text()
    cpuinfo = (source_root / expected["cpuinfo_sha256"]).read_text()
    smp = (source_root / expected["smp_sha256"]).read_text()
    require("#define ARM64_LATE_CPU_PLAN_ABI\t\t7" in header, "ABI-7 definition missing")
    require("panic(\"late CPU profile commit implementation is unavailable\")" in core,
            "commit panic-stub boundary changed")
    require("info->reg_id_aa64isar2 = read_cpuid(ID_AA64ISAR2_EL1);" in cpuinfo,
            "current-entry ISAR2 reader changed")
    require("info->reg_id_aa64pfr2 = read_cpuid(ID_AA64PFR2_EL1);" in cpuinfo,
            "current-entry PFR2 reader changed")
    require(smp.index("check_local_cpu_capabilities();") < smp.index("cpuinfo_store_cpu();") <
            smp.index("notify_cpu_starting(cpu);") < smp.index("set_cpu_online(cpu, true);"),
            "secondary-entry C ordering changed")


def default_paths() -> tuple[Path, Path]:
    experiment = Path(__file__).resolve().parents[1]
    repository = experiment.parents[1]
    ledger = experiment / "schema" / "attestation-ledger-v1.json"
    capture = repository / (
        "experiments/2026-08-28-a72-pmsg-witness/results/"
        "runtime-attempt-1-complete-pass-20260829.txt"
    )
    return ledger, capture


def main() -> int:
    default_ledger, default_capture = default_paths()
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=default_ledger)
    parser.add_argument("--capture", type=Path, default=default_capture)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()

    document = json.loads(args.ledger.read_text())
    capture_text = args.capture.read_text()
    validate_document(document, capture_text)
    if args.source_root is not None:
        validate_source_root(document, args.source_root)

    print("validation=mainline-a72-attestation-closure-v1-pass")
    print("targets=2")
    print("reference_register_image_fields=24")
    print("unmeasured_register_image_fields=23")
    print("target_local_values_per_cpu=26")
    print("abi7_target_groups=11")
    print("current_boot_owner_groups=9")
    print("closure_stages=12")
    print("unsafe_physical_actions=0")
    print("classification=prior-cycle-reference-only-ready-closure-incomplete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
