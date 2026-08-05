#!/usr/bin/env python3
"""Validate the blocked A41 ABI-5 six-row fixture evaluator."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import (
    dataclass,
    fields as dataclass_fields,
    replace as dataclass_replace,
)
from pathlib import Path
from typing import Iterable, Mapping, Sequence

sys.dont_write_bytecode = True


EXPERIMENT = Path("experiments/2026-08-05-a72-a41-six-row-fixture")
PARENT_VALIDATOR = Path(
    "experiments/2026-08-05-a72-a41-static-census/scripts/validate.py"
)
PATCH = Path(
    "patches/v7.1.3/0154-arm64-evaluate-MT6797-late-CPU-fixture-evidence.patch"
)
PATCH_0092 = Path(
    "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
)
SERIES = Path("patches/series-a72-reject-gate-a41-six-row-fixture")
PARENT_SERIES = Path("patches/series-a72-reject-gate-a41-per-target-plan")
CANONICAL_SERIES = Path("patches/series")
FRAGMENT = Path("configs/gemini-a72-a41-six-row-fixture.fragment")
MANIFEST = Path("kernel/manifest.json")
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-six-row-fixture"
)

PATCH_SHA256 = "71908b62b275710223523102448b7fbcecb8cd557a2537259274f7986f7a3445"
SERIES_SHA256 = "8c76d1cef1ddd7f452ef7604d6b2581c56c13c1a982e3492e0d0c31f20d9e3da"
PATCHSET_SHA256 = "1247936c6f7ed6850434cd2a8402a53c9588444a608fa33e965a5f9bf445ed5e"
SOURCE_STATE_SHA256 = "2750c74f4c2c5c5ce0c07b90e57489fe6d412ec57fec7618b70a327623d5c058"
PARENT_SOURCE_STATE_SHA256 = (
    "78fcb018e5693cc258127ea6e2655319f55b80135c1230cb42fbf70c6d2e6deb"
)
CONFIG_SHA256 = "8ab011246184c5fff4885bdc38fef09d24cc31960235fb7640ea081505949815"
FIXTURE_SHA256 = "c41b8b84d68f9c0f05a9a047d319de9cfe8d41e8b792cb509ffa4be08341e887"
PARENT_VALIDATOR_SHA256 = (
    "a52019ee9021b507f91876ff22eeb1580108e7c18f4fb918c5b7f58bf058dfbd"
)
PARENT = "7fcc8ca433d2306d2e3d005289d6cf01dfbf0f4c"
PARENT_TREE = "47133d89119afe60e38057c8ac39840665a1f142"
SOURCE = "57d36fd59821b7de2fd81c938414e7f3c5a54229"
SOURCE_TREE = "253625b12d09411997e1877a58ffd843f417ad7d"
SOURCE_DIFF_SHA256 = "069ae9b8add4d197bf4c1de7bb0f874db91cd5129df9269aa30d6bf17a052199"
PROFILE_COUNT = 60
SERIES_ENTRY_COUNT = 96

CHANGED_PATHS = (
    "arch/arm64/Kconfig.platforms",
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/cpu_errata.c",
    "arch/arm64/kernel/cpufeature.c",
    "arch/arm64/kernel/late_cpu_profile.c",
    "arch/arm64/kernel/mt6797_psci.c",
    "arch/arm64/kernel/proton-pack.c",
)

EXPECTED_FRAGMENTS = (
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    str(FRAGMENT),
)

EXPECTED_EXPERIMENT_FILES = {
    "DESIGN.md",
    "README.md",
    "results/implementation.tsv",
    "results/kernel-static-review-20260805.txt",
    "results/mutation-validation-20260805.txt",
    "results/offline-validation-20260805.txt",
    "results/six-row-fixture.tsv",
    "results/typed-effects.tsv",
    "scripts/test_mutations.py",
    "scripts/validate.py",
}
FROZEN_TRANSCRIPTS = {
    "results/kernel-static-review-20260805.txt",
    "results/mutation-validation-20260805.txt",
    "results/offline-validation-20260805.txt",
}
FROZEN_FILE_SHA256 = {
    "README.md": "c584d414b921c8ea34389833f3f1e812cbcce58565c7b6aa327f0443ab85be8a",
    "DESIGN.md": "b896a6917b9401da86061bfd4864ab1dc7e300ab8ceb6f07b38b34afee43dee1",
    "results/implementation.tsv":
        "53a7e2cf7ee188b90b865f8184a35d90c74a256bbf8abe9ca5b684e6d0111fa0",
    "results/six-row-fixture.tsv":
        "2611b0e8905a66e6728d533bd0f186109617d6491ffe5e2bdd225626a6a7a2eb",
    "results/typed-effects.tsv":
        "c1ea74455ad8d28d06370820239d5df9e3d792cdaa11a341a04d6ee9ddd2fabc",
    "scripts/test_mutations.py":
        "94f36590c17d96ba88f766bc0519df6755df3dc15a54dffb11247a04c2b9961c",
}

REPOSITORY_CHECKS = (
    "experiment-inventory",
    "manifest-profile",
    "configuration-identity",
    "all-profile-series",
    "selected-series",
    "patch-provenance",
    "fixture-tables",
    "claim-boundary",
    "frozen-results",
)
SOURCE_CHECKS = (
    "source-identity",
    "patch-application",
    "six-row-source-contract",
    "typed-effect-source-contract",
    "fixture-provenance",
    "commit-path-blocker",
    "publication-vetoes",
    "static-tooling",
)
ORACLE_CHECKS = (
    "fixture-identity",
    "gic-ich-oracle",
    "ctr-oracle",
    "spectre-v2-v4-oracle",
    "spectre-bhb-oracle",
    "asymmetric-target-oracle",
    "typed-effects-oracle",
)


class ValidationError(RuntimeError):
    """A pinned offline invariant failed."""


class OracleRejected(ValueError):
    """The independent evaluator rejected incomplete or inconsistent input."""


def load_parent(repo: Path):
    """Load helpers only; never call the parent validator's main contract."""
    path = repo / PARENT_VALIDATOR
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_VALIDATOR_SHA256:
        raise ValidationError("parent helper identity changed")
    spec = importlib.util.spec_from_file_location("a41_static_helpers", path)
    if spec is None or spec.loader is None:
        raise ValidationError("cannot load static-census helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def config_hash(repo: Path, profile: Mapping[str, object]) -> str:
    lines = [f"profile={PROFILE}", f"base={profile['base']}"]
    for name in profile["fragments"]:
        relative = str(name)
        lines.append(f"{sha256((repo / relative).read_bytes())}  {relative}")
    return sha256(("\n".join(lines) + "\n").encode())


# Evidence validity bits deliberately mirror the ABI, but the oracle is not
# generated from or linked to the C implementation.
MIDR_VALID = 1 << 0
ID_REGS_VALID = 1 << 1
CTR_VALID = 1 << 2
GIC_VALID = 1 << 3
HYP_VALID = 1 << 4
WA1_VALID = 1 << 5
WA2_VALID = 1 << 6
WA3_VALID = 1 << 7
TARGET_VALID_MASK = (1 << 11) - 1
FIXTURE_TARGET_VALID = (
    MIDR_VALID | ID_REGS_VALID | CTR_VALID | GIC_VALID | HYP_VALID |
    WA1_VALID | WA2_VALID
)
SYSTEM_CTR_VALID = 1 << 0
SYSTEM_SSBS_VALID = 1 << 1
SYSTEM_EFFECTS_VALID = 1 << 2
SYSTEM_VALID_MASK = SYSTEM_CTR_VALID | SYSTEM_SSBS_VALID | SYSTEM_EFFECTS_VALID
POLICY_VALID_MASK = 0x7
TARGET_EFFECT_VALID_MASK = 0x7

MIDR_CORTEX_A72 = 0x410FD080
MIDR_CPU_MODEL_MASK = 0xFF0FFFF0
CTR_STRICT_MASK = 0xFFFFFFFFFFFF3FFF
CTR_IDC = 1 << 28
CTR_RES1 = 1 << 31
ICC_SRE = 1 << 0
ICH_TDS = 1 << 19
HVC_STUB_ERR = 0x0BADCA11
SMCCC_SUCCESS = 0
SMCCC_NOT_SUPPORTED = -1
SMCCC_NOT_REQUIRED = -2
SMCCC_UNAFFECTED = 1

UNRESOLVED = "UNRESOLVED"
ABSENT = "ABSENT"
PRESENT = "PRESENT"

MITIGATION_UNAFFECTED = "ARM64_LATE_CPU_MITIGATION_UNAFFECTED"
MITIGATION_MITIGATED = "ARM64_LATE_CPU_MITIGATION_MITIGATED"
MITIGATION_VULNERABLE = "ARM64_LATE_CPU_MITIGATION_VULNERABLE"
SMCCC_NONE = "ARM64_LATE_CPU_SMCCC_NONE"
SMCCC_SMC = "ARM64_LATE_CPU_SMCCC_SMC"
SMCCC_HVC = "ARM64_LATE_CPU_SMCCC_HVC"
V2_CALLBACK_NONE = "ARM64_LATE_CPU_V2_CALLBACK_NONE"
V2_CALLBACK_SMC = "ARM64_LATE_CPU_V2_CALLBACK_SMC"
V2_CALLBACK_HVC = "ARM64_LATE_CPU_V2_CALLBACK_HVC"
V4_NONE = "ARM64_LATE_CPU_V4_NONE"
V4_SSBS = "ARM64_LATE_CPU_V4_SSBS"
V4_FIRMWARE = "ARM64_LATE_CPU_V4_FIRMWARE"
V4_DYNAMIC = "ARM64_LATE_CPU_V4_POLICY_DYNAMIC"
V4_FORCE_ON = "ARM64_LATE_CPU_V4_POLICY_FORCE_ON"
V4_FORCE_OFF = "ARM64_LATE_CPU_V4_POLICY_FORCE_OFF"
BHB_NONE = "ARM64_LATE_CPU_BHB_NONE"
BHB_LOOP = "ARM64_LATE_CPU_BHB_LOOP"
BHB_FIRMWARE = "ARM64_LATE_CPU_BHB_FIRMWARE"
BHB_INSTRUCTION = "ARM64_LATE_CPU_BHB_INSTRUCTION"
BHB_HARDWARE = "ARM64_LATE_CPU_BHB_HARDWARE"
BHB_STATE_UNAFFECTED = "ARM64_LATE_CPU_BHB_STATE_UNAFFECTED"
BHB_STATE_MITIGATED = "ARM64_LATE_CPU_BHB_STATE_MITIGATED"
BHB_STATE_VULNERABLE = "ARM64_LATE_CPU_BHB_STATE_VULNERABLE"
BHB_VECTOR_NONE = "ARM64_LATE_CPU_BHB_VECTOR_NONE"
BHB_VECTOR_LOOP = "ARM64_LATE_CPU_BHB_VECTOR_LOOP"
BHB_VECTOR_CLEAR = "ARM64_LATE_CPU_BHB_VECTOR_CLEAR_INSN"
BHB_VECTOR_FIRMWARE = "ARM64_LATE_CPU_BHB_VECTOR_FIRMWARE"
HYP_DIRECT = "ARM64_LATE_CPU_HYP_VECTOR_DIRECT"
HYP_SPECTRE_DIRECT = "ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_DIRECT"
HYP_INDIRECT = "ARM64_LATE_CPU_HYP_VECTOR_INDIRECT"
HYP_SPECTRE_INDIRECT = "ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_INDIRECT"
ICH_NONE = "ARM64_LATE_CPU_ICH_VTR_NONE"
ICH_DIRECT = "ARM64_LATE_CPU_ICH_VTR_DIRECT"
ICH_HVC = "ARM64_LATE_CPU_ICH_VTR_HVC"

MITIGATION_ORDER = {
    MITIGATION_UNAFFECTED: 1,
    MITIGATION_MITIGATED: 2,
    MITIGATION_VULNERABLE: 3,
}


@dataclass(frozen=True)
class TargetEvidence:
    valid: int = FIXTURE_TARGET_VALID
    midr: int = MIDR_CORTEX_A72
    ctr: int = 0x83338003
    clidr: int = 0
    ctr_effective: int = 0x93338003
    pfr0: int = 0
    pfr1: int = 0
    pfr2: int = 0
    isar2: int = 0
    mmfr1: int = 0
    icc_sre: int = 0
    icc_idr0: int = 0
    ich_vtr: int = 0
    ich_status: int = 0
    wa1: int = SMCCC_SUCCESS
    wa2: int = SMCCC_SUCCESS
    wa3: int = 0
    hyp_available: int = 1
    kernel_in_hyp: int = 0
    gic_sre_usable: int = 0
    ich_source: str = ICH_NONE


@dataclass(frozen=True)
class TargetPolicy:
    valid: int = POLICY_VALID_MASK
    conduit: str = SMCCC_SMC
    mitigations_off: int = 0
    nospectre_v2: int = 0
    v4_policy: str = V4_DYNAMIC


@dataclass(frozen=True)
class SystemEvidence:
    valid: int = SYSTEM_VALID_MASK
    ctr_sys: int = 0xB4448004
    ctr_strict_mask: int = CTR_STRICT_MASK
    ssbs: int = 0
    v2_state: str = MITIGATION_UNAFFECTED
    v4_state: str = MITIGATION_UNAFFECTED
    bhb_state: str = BHB_STATE_UNAFFECTED
    bhb_matcher_loop_count: int = 0
    bhb_system_method: int = 0


FIXTURE_TARGETS = (TargetEvidence(), TargetEvidence())
FIXTURE_POLICIES = (TargetPolicy(), TargetPolicy())
FIXTURE_SYSTEM = SystemEvidence()


def _field(value: int, shift: int) -> int:
    return (value >> shift) & 0xF


def _target_shape_valid(target: TargetEvidence) -> bool:
    return (
        not target.valid & ~TARGET_VALID_MASK and
        target.valid & (MIDR_VALID | ID_REGS_VALID) ==
        (MIDR_VALID | ID_REGS_VALID) and
        target.midr & MIDR_CPU_MODEL_MASK == MIDR_CORTEX_A72 and
        (
            (not target.valid & HYP_VALID and not target.hyp_available and
             not target.kernel_in_hyp) or
            (target.valid & HYP_VALID and target.hyp_available in (0, 1) and
             target.kernel_in_hyp in (0, 1) and
             (not target.kernel_in_hyp or target.hyp_available))
        )
    )


def classify_gic(target: TargetEvidence, *, descriptor: bool = True) -> str:
    if not descriptor or target.valid & (ID_REGS_VALID | GIC_VALID) != (
        ID_REGS_VALID | GIC_VALID
    ):
        return UNRESOLVED
    gcie = _field(target.pfr2, 12)
    legacy = _field(target.icc_idr0, 8)
    if (
        gcie > 1 or legacy > 1 or target.gic_sre_usable not in (0, 1) or
        target.gic_sre_usable != bool(target.icc_sre & ICC_SRE)
    ):
        return UNRESOLVED
    return PRESENT if gcie and legacy else ABSENT


def classify_ich(target: TargetEvidence, *, descriptor: bool = True) -> str:
    if (
        not descriptor or not target.valid & HYP_VALID or
        target.hyp_available not in (0, 1) or
        target.kernel_in_hyp not in (0, 1) or
        (target.kernel_in_hyp and not target.hyp_available)
    ):
        return UNRESOLVED
    if not target.hyp_available:
        if target.ich_source != ICH_NONE or target.ich_status or target.ich_vtr:
            return UNRESOLVED
        return ABSENT
    legacy = classify_gic(target)
    if legacy == UNRESOLVED:
        return UNRESOLVED
    if legacy == PRESENT:
        if target.ich_source != ICH_NONE or target.ich_status or target.ich_vtr:
            return UNRESOLVED
        return PRESENT
    if not target.valid & MIDR_VALID or (
        target.midr & MIDR_CPU_MODEL_MASK
    ) != MIDR_CORTEX_A72:
        return UNRESOLVED
    gic = _field(target.pfr0, 24)
    if (
        gic == 2 or gic > 3 or target.gic_sre_usable not in (0, 1) or
        target.gic_sre_usable != bool(target.icc_sre & ICC_SRE)
    ):
        return UNRESOLVED
    if not gic or not target.gic_sre_usable:
        if target.ich_source != ICH_NONE or target.ich_status or target.ich_vtr:
            return UNRESOLVED
        return ABSENT
    if target.ich_source == ICH_DIRECT:
        if not target.kernel_in_hyp or target.ich_status:
            return UNRESOLVED
    elif target.ich_source == ICH_HVC:
        if target.kernel_in_hyp:
            return UNRESOLVED
        if target.ich_status == HVC_STUB_ERR:
            return UNRESOLVED if target.ich_vtr else ABSENT
        if target.ich_status:
            return UNRESOLVED
    else:
        return UNRESOLVED
    return PRESENT if target.ich_vtr & ICH_TDS else ABSENT


def _ctr_effective(raw: int, clidr: int) -> int:
    loc = (clidr >> 24) & 0x7
    louis = (clidr >> 21) & 0x7
    louu = (clidr >> 27) & 0x7
    if not raw & CTR_IDC and (not loc or (not louis and not louu)):
        return raw | CTR_IDC
    return raw


def classify_ctr(
    target: TargetEvidence,
    system: SystemEvidence,
    *,
    descriptor: bool = True,
) -> str:
    if (
        not descriptor or not target.valid & CTR_VALID or
        not system.valid & SYSTEM_CTR_VALID or
        system.valid & ~SYSTEM_VALID_MASK
    ):
        return UNRESOLVED
    if (
        system.ctr_strict_mask != CTR_STRICT_MASK or
        (target.ctr | target.ctr_effective | system.ctr_sys) >> 32 or
        not target.ctr & CTR_RES1 or not system.ctr_sys & CTR_RES1
    ):
        return UNRESOLVED
    effective = _ctr_effective(target.ctr, target.clidr)
    if target.ctr_effective != effective:
        return UNRESOLVED
    raw = target.ctr & system.ctr_strict_mask
    effective &= system.ctr_strict_mask
    system_value = system.ctr_sys & system.ctr_strict_mask
    return PRESENT if effective != system_value and raw != system_value else ABSENT


def _wa1_valid(status: int) -> bool:
    return status in (SMCCC_SUCCESS, SMCCC_UNAFFECTED, SMCCC_NOT_SUPPORTED)


def _wa2_valid(status: int) -> bool:
    return _wa1_valid(status) or status == SMCCC_NOT_REQUIRED


def classify_v2(target: TargetEvidence, *, descriptor: bool = True) -> str:
    if not descriptor or not _target_shape_valid(target):
        return UNRESOLVED
    csv2 = _field(target.pfr0, 56)
    if csv2 > 3:
        return UNRESOLVED
    if target.valid & WA1_VALID and not _wa1_valid(target.wa1):
        return UNRESOLVED
    if not target.valid & WA1_VALID and target.wa1:
        return UNRESOLVED
    if csv2:
        return ABSENT
    if not target.valid & WA1_VALID:
        return UNRESOLVED
    return ABSENT if target.wa1 == SMCCC_UNAFFECTED else PRESENT


def classify_v4(target: TargetEvidence, *, descriptor: bool = True) -> str:
    if not descriptor or not _target_shape_valid(target):
        return UNRESOLVED
    ssbs = _field(target.pfr1, 4)
    if ssbs > 2:
        return UNRESOLVED
    if target.valid & WA2_VALID and not _wa2_valid(target.wa2):
        return UNRESOLVED
    if not target.valid & WA2_VALID and target.wa2:
        return UNRESOLVED
    if ssbs:
        return PRESENT
    if not target.valid & WA2_VALID:
        return UNRESOLVED
    return ABSENT if target.wa2 in (SMCCC_UNAFFECTED, SMCCC_NOT_REQUIRED) else PRESENT


def classify_bhb(target: TargetEvidence, *, descriptor: bool = True) -> str:
    if not descriptor or not _target_shape_valid(target):
        return UNRESOLVED
    csv2 = _field(target.pfr0, 56)
    if csv2 > 3:
        return UNRESOLVED
    return ABSENT if csv2 == 3 else PRESENT


def classify_six_rows(
    target: TargetEvidence, system: SystemEvidence = FIXTURE_SYSTEM
) -> dict[str, str]:
    return {
        "ARM64_HAS_GICV5_LEGACY": classify_gic(target),
        "ARM64_HAS_ICH_HCR_EL2_TDIR": classify_ich(target),
        "ARM64_MISMATCHED_CACHE_TYPE": classify_ctr(target, system),
        "ARM64_SPECTRE_V2": classify_v2(target),
        "ARM64_SPECTRE_V4": classify_v4(target),
        "ARM64_SPECTRE_BHB": classify_bhb(target),
    }


def _policy_valid(policy: TargetPolicy) -> bool:
    return (
        policy.valid == POLICY_VALID_MASK and
        policy.conduit in (SMCCC_NONE, SMCCC_SMC, SMCCC_HVC) and
        policy.mitigations_off in (0, 1) and policy.nospectre_v2 in (0, 1) and
        policy.v4_policy in (V4_DYNAMIC, V4_FORCE_ON, V4_FORCE_OFF)
    )


def evaluate_v2(target: TargetEvidence, policy: TargetPolicy) -> dict[str, object]:
    if not _policy_valid(policy):
        raise OracleRejected("invalid-v2-policy")
    state = classify_v2(target)
    if state == UNRESOLVED:
        raise OracleRejected("unresolved-v2")
    result: dict[str, object] = {
        "spectre_v2_hyp_vector": HYP_DIRECT,
    }
    if state == ABSENT:
        result.update(
            spectre_v2_state=MITIGATION_UNAFFECTED,
            spectre_v2_conduit=SMCCC_NONE,
            spectre_v2_callback=V2_CALLBACK_NONE,
        )
        return result
    if target.wa1 != SMCCC_SUCCESS or policy.mitigations_off or policy.nospectre_v2:
        result.update(
            spectre_v2_state=MITIGATION_VULNERABLE,
            spectre_v2_conduit=SMCCC_NONE,
            spectre_v2_callback=V2_CALLBACK_NONE,
        )
        return result
    if not target.valid & HYP_VALID:
        raise OracleRejected("v2-hyp-evidence-missing")
    callbacks = {SMCCC_SMC: V2_CALLBACK_SMC, SMCCC_HVC: V2_CALLBACK_HVC}
    if policy.conduit not in callbacks:
        raise OracleRejected("v2-conduit-invalid")
    result.update(
        spectre_v2_state=MITIGATION_MITIGATED,
        spectre_v2_conduit=policy.conduit,
        spectre_v2_callback=callbacks[policy.conduit],
    )
    if target.hyp_available:
        result["spectre_v2_hyp_vector"] = HYP_SPECTRE_DIRECT
    return result


def evaluate_v4(target: TargetEvidence, policy: TargetPolicy) -> dict[str, object]:
    if not _policy_valid(policy):
        raise OracleRejected("invalid-v4-policy")
    state = classify_v4(target)
    if state == UNRESOLVED:
        raise OracleRejected("unresolved-v4")
    result: dict[str, object] = {
        "spectre_v4_policy": policy.v4_policy,
        "spectre_v4_callback_required": 0,
    }
    if state == ABSENT:
        result.update(
            spectre_v4_state=MITIGATION_UNAFFECTED,
            spectre_v4_method=V4_NONE,
            spectre_v4_conduit=SMCCC_NONE,
        )
        return result
    ssbs = _field(target.pfr1, 4)
    if ssbs:
        if policy.mitigations_off or policy.v4_policy == V4_FORCE_OFF:
            raise OracleRejected("v4-ssbs-policy-unrepresentable")
        result.update(
            spectre_v4_state=MITIGATION_MITIGATED,
            spectre_v4_method=V4_SSBS,
            spectre_v4_conduit=SMCCC_NONE,
        )
        return result
    if target.wa2 != SMCCC_SUCCESS:
        result.update(
            spectre_v4_state=MITIGATION_VULNERABLE,
            spectre_v4_method=V4_NONE,
            spectre_v4_conduit=SMCCC_NONE,
        )
        return result
    if policy.conduit not in (SMCCC_SMC, SMCCC_HVC):
        raise OracleRejected("v4-conduit-invalid")
    mitigation = (
        MITIGATION_VULNERABLE
        if policy.mitigations_off or policy.v4_policy == V4_FORCE_OFF
        else MITIGATION_MITIGATED
    )
    result.update(
        spectre_v4_state=mitigation,
        spectre_v4_method=V4_FIRMWARE,
        spectre_v4_conduit=policy.conduit,
    )
    if mitigation == MITIGATION_MITIGATED and policy.v4_policy == V4_DYNAMIC:
        result["spectre_v4_callback_required"] = 1
    return result


def evaluate_bhb(
    target: TargetEvidence,
    policy: TargetPolicy,
    system_v2_state: str,
    prior: Mapping[str, object],
    *,
    mitigation_configured: bool = True,
) -> dict[str, object]:
    if not _policy_valid(policy) or system_v2_state not in MITIGATION_ORDER:
        raise OracleRejected("invalid-bhb-input")
    state = classify_bhb(target)
    if state == UNRESOLVED:
        raise OracleRejected("unresolved-bhb")
    result: dict[str, object] = {
        "bhb_conduit": SMCCC_NONE,
        "bhb_vector_template": BHB_VECTOR_NONE,
        "bhb_hyp_vector": prior["spectre_v2_hyp_vector"],
        "bhb_v2_non_vulnerable": int(system_v2_state != MITIGATION_VULNERABLE),
        "bhb_loop_count": 0,
        "bhb_matcher_loop_count": 0,
    }
    if state == ABSENT:
        result.update(
            bhb_method=BHB_NONE,
            bhb_mitigation_state=BHB_STATE_UNAFFECTED,
        )
        return result
    clearbhb = _field(target.isar2, 28)
    ecbhb = _field(target.mmfr1, 60)
    if clearbhb > 1 or ecbhb > 1:
        raise OracleRejected("bhb-id-field-reserved")
    if not clearbhb:
        result["bhb_matcher_loop_count"] = 8
    if not result["bhb_v2_non_vulnerable"] or not mitigation_configured:
        result.update(
            bhb_method=BHB_NONE,
            bhb_mitigation_state=BHB_STATE_VULNERABLE,
        )
        return result
    if ecbhb:
        result["bhb_method"] = BHB_HARDWARE
    elif clearbhb:
        result.update(
            bhb_method=BHB_INSTRUCTION,
            bhb_vector_template=BHB_VECTOR_CLEAR,
        )
        if result["bhb_hyp_vector"] == HYP_DIRECT:
            result["bhb_hyp_vector"] = HYP_INDIRECT
    else:
        result.update(
            bhb_method=BHB_LOOP,
            bhb_loop_count=8,
            bhb_vector_template=BHB_VECTOR_LOOP,
        )
        if result["bhb_hyp_vector"] == HYP_DIRECT:
            result["bhb_hyp_vector"] = HYP_INDIRECT
    result["bhb_mitigation_state"] = BHB_STATE_MITIGATED
    return result


TARGET_EFFECT_FIELDS = (
    "valid",
    "spectre_v2_state",
    "spectre_v2_conduit",
    "spectre_v2_callback",
    "spectre_v2_hyp_vector",
    "spectre_v4_state",
    "spectre_v4_method",
    "spectre_v4_conduit",
    "spectre_v4_policy",
    "spectre_v4_callback_required",
    "bhb_method",
    "bhb_loop_count",
    "bhb_matcher_loop_count",
    "bhb_conduit",
    "bhb_mitigation_state",
    "bhb_vector_template",
    "bhb_hyp_vector",
    "bhb_v2_non_vulnerable",
)


def evaluate_target_effects(
    target: TargetEvidence,
    policy: TargetPolicy,
    system_v2_state: str,
) -> dict[str, object]:
    effect: dict[str, object] = {"valid": TARGET_EFFECT_VALID_MASK}
    effect.update(evaluate_v2(target, policy))
    effect.update(evaluate_v4(target, policy))
    effect.update(evaluate_bhb(target, policy, system_v2_state, effect))
    require(set(effect) == set(TARGET_EFFECT_FIELDS), "oracle target field set changed")
    return effect


AGGREGATE_EFFECT_FIELDS = (
    "ctr_mismatch.required",
    "ctr_mismatch.target_mask",
    "ctr_mismatch.trap_ctr_el0",
    "ctr_mismatch.alternative",
    "spectre_v2.required",
    "spectre_v2.target_mask",
    "spectre_v2.mitigation_state",
    "spectre_v2.conduit",
    "spectre_v2.callback",
    "spectre_v2.hyp_vector",
    "spectre_v2.alternative",
    "spectre_v4.required",
    "spectre_v4.target_mask",
    "spectre_v4.mitigation_state",
    "spectre_v4.method",
    "spectre_v4.conduit",
    "spectre_v4.policy",
    "spectre_v4.callback_required_mask",
    "spectre_v4.firmware_alternative",
    "bhb.required",
    "bhb.target_mask",
    "bhb.method",
    "bhb.loop_count",
    "bhb.matcher_loop_count",
    "bhb.conduit",
    "bhb.system_method",
    "bhb.mitigation_state",
    "bhb.vector_template",
    "bhb.hyp_vector",
    "bhb.alternative",
    "bhb.v2_non_vulnerable",
    "compat_aes_clear",
    "speculative_at_finalization",
)


def derive_fixture_effects(
    targets: Sequence[TargetEvidence] = FIXTURE_TARGETS,
    policies: Sequence[TargetPolicy] = FIXTURE_POLICIES,
    system: SystemEvidence = FIXTURE_SYSTEM,
) -> tuple[dict[str, object], tuple[dict[str, object], ...]]:
    if len(targets) != 2 or len(policies) != 2 or policies[0] != policies[1]:
        raise OracleRejected("target-count-or-policy-disagreement")
    if (
        system.valid != SYSTEM_VALID_MASK or system.ssbs not in (0, 1) or
        system.v2_state != MITIGATION_UNAFFECTED or
        system.v4_state != MITIGATION_UNAFFECTED or
        system.bhb_state != BHB_STATE_UNAFFECTED or
        system.bhb_matcher_loop_count or system.bhb_system_method
    ):
        raise OracleRejected("unsupported-system-baseline")
    six = tuple(classify_six_rows(target, system) for target in targets)
    for states in six:
        if UNRESOLVED in states.values():
            raise OracleRejected("unresolved-six-row-input")
    system_v2 = system.v2_state
    preliminary = []
    for target, policy in zip(targets, policies):
        partial = {"valid": TARGET_EFFECT_VALID_MASK}
        partial.update(evaluate_v2(target, policy))
        partial.update(evaluate_v4(target, policy))
        preliminary.append(partial)
        if MITIGATION_ORDER[partial["spectre_v2_state"]] > MITIGATION_ORDER[system_v2]:
            system_v2 = str(partial["spectre_v2_state"])
    per_target = []
    for target, policy, partial in zip(targets, policies, preliminary):
        effect = dict(partial)
        effect.update(evaluate_bhb(target, policy, system_v2, effect))
        require(set(effect) == set(TARGET_EFFECT_FIELDS), "oracle field set changed")
        per_target.append(effect)

    def target_mask(symbol: str) -> int:
        return sum(
            1 << index for index, states in enumerate(six)
            if states[symbol] == PRESENT
        )

    ctr_mask = target_mask("ARM64_MISMATCHED_CACHE_TYPE")
    v2_mask = target_mask("ARM64_SPECTRE_V2")
    v4_mask = target_mask("ARM64_SPECTRE_V4")
    bhb_mask = target_mask("ARM64_SPECTRE_BHB")

    def first_and_require_equal(mask: int, fields: Sequence[str]) -> int | None:
        selected = [index for index in range(2) if mask & (1 << index)]
        if not selected:
            return None
        first_index = selected[0]
        for index in selected[1:]:
            if any(
                per_target[first_index][field] != per_target[index][field]
                for field in fields
            ):
                raise OracleRejected("required-target-effect-disagreement")
        return first_index

    first_v2 = first_and_require_equal(v2_mask, (
        "spectre_v2_state", "spectre_v2_conduit", "spectre_v2_callback",
        "spectre_v2_hyp_vector",
    ))
    first_v4 = first_and_require_equal(v4_mask, (
        "spectre_v4_state", "spectre_v4_method", "spectre_v4_conduit",
        "spectre_v4_policy",
    ))
    first_bhb = first_and_require_equal(bhb_mask, (
        "bhb_method", "bhb_loop_count", "bhb_conduit",
        "bhb_mitigation_state", "bhb_vector_template", "bhb_hyp_vector",
        "bhb_v2_non_vulnerable",
    ))
    callback_mask = sum(
        1 << index
        for index, effect in enumerate(per_target)
        if effect["spectre_v4_callback_required"]
    )
    matcher = max([
        system.bhb_matcher_loop_count,
        *(int(effect["bhb_matcher_loop_count"])
          for index, effect in enumerate(per_target)
          if bhb_mask & (1 << index)),
    ])
    method_bits = {
        BHB_NONE: 0,
        BHB_LOOP: 1 << 0,
        BHB_FIRMWARE: 1 << 1,
        BHB_HARDWARE: 1 << 2,
        BHB_INSTRUCTION: 1 << 3,
    }
    aggregate: dict[str, object] = {
        field: 0 for field in AGGREGATE_EFFECT_FIELDS
    }
    aggregate.update({
        "ctr_mismatch.required": int(bool(ctr_mask)),
        "ctr_mismatch.target_mask": ctr_mask,
        "spectre_v2.required": int(bool(v2_mask)),
        "spectre_v2.target_mask": v2_mask,
        "spectre_v4.required": int(bool(v4_mask)),
        "spectre_v4.target_mask": v4_mask,
        "spectre_v4.callback_required_mask": callback_mask,
        "bhb.required": int(bool(bhb_mask)),
        "bhb.target_mask": bhb_mask,
        "compat_aes_clear": 1,
        "speculative_at_finalization": 1,
    })
    if ctr_mask:
        aggregate.update({
            "ctr_mismatch.trap_ctr_el0": 1,
            "ctr_mismatch.alternative": 1,
        })
    if first_v2 is not None:
        first = per_target[first_v2]
        aggregate.update({
            "spectre_v2.mitigation_state": first["spectre_v2_state"],
            "spectre_v2.conduit": first["spectre_v2_conduit"],
            "spectre_v2.callback": first["spectre_v2_callback"],
            "spectre_v2.hyp_vector": first["spectre_v2_hyp_vector"],
            "spectre_v2.alternative": 1,
        })
    if first_v4 is not None:
        first = per_target[first_v4]
        aggregate.update({
            "spectre_v4.mitigation_state": first["spectre_v4_state"],
            "spectre_v4.method": first["spectre_v4_method"],
            "spectre_v4.conduit": first["spectre_v4_conduit"],
            "spectre_v4.policy": first["spectre_v4_policy"],
            "spectre_v4.firmware_alternative": int(
                not system.ssbs and not policies[0].mitigations_off and
                policies[0].v4_policy == V4_DYNAMIC
            ),
        })
    if first_bhb is not None:
        first = per_target[first_bhb]
        aggregate.update({
            "bhb.method": first["bhb_method"],
            "bhb.loop_count": first["bhb_loop_count"],
            "bhb.matcher_loop_count": matcher,
            "bhb.conduit": first["bhb_conduit"],
            "bhb.system_method": system.bhb_system_method |
            method_bits[str(first["bhb_method"])],
            "bhb.mitigation_state": first["bhb_mitigation_state"],
            "bhb.vector_template": first["bhb_vector_template"],
            "bhb.hyp_vector": first["bhb_hyp_vector"],
            "bhb.alternative": 1,
            "bhb.v2_non_vulnerable": first["bhb_v2_non_vulnerable"],
        })
    require(set(aggregate) == set(AGGREGATE_EFFECT_FIELDS),
            "oracle aggregate field set changed")
    return aggregate, tuple(per_target)


def _canonical_enum(value: str, values: Mapping[str, str], scope: str) -> str:
    try:
        return values[value]
    except KeyError as error:
        raise OracleRejected(f"{scope}-enum-unrepresentable") from error


def fixture_material(
    targets: Sequence[TargetEvidence] = FIXTURE_TARGETS,
    policies: Sequence[TargetPolicy] = FIXTURE_POLICIES,
    system: SystemEvidence = FIXTURE_SYSTEM,
) -> bytes:
    if len(targets) != 2 or len(policies) != 2:
        raise OracleRejected("fixture-identity-target-count")
    target_lines = []
    for index, (target, policy) in enumerate(zip(targets, policies)):
        ich_source = _canonical_enum(target.ich_source, {
            ICH_NONE: "NONE", ICH_DIRECT: "DIRECT", ICH_HVC: "HVC",
        }, "ich-source")
        conduit = _canonical_enum(policy.conduit, {
            SMCCC_NONE: "NONE", SMCCC_SMC: "SMC", SMCCC_HVC: "HVC",
        }, "conduit")
        v4_policy = _canonical_enum(policy.v4_policy, {
            V4_DYNAMIC: "DYNAMIC", V4_FORCE_ON: "FORCE_ON",
            V4_FORCE_OFF: "FORCE_OFF",
        }, "v4-policy")
        target_lines.append(
            f"target{index}=cpu:{8 + index},mpidr:0x{0x200 + index:x},"
            f"midr:0x{target.midr:x},revidr:0,valid:0x{target.valid:x},"
            f"ctr:0x{target.ctr:x},clidr:{target.clidr},"
            f"ctr_effective:0x{target.ctr_effective:x},pfr0:{target.pfr0},"
            f"pfr1:{target.pfr1},pfr2:{target.pfr2},isar2:{target.isar2},"
            f"mmfr1:{target.mmfr1},icc_sre:{target.icc_sre},"
            f"icc_idr0:{target.icc_idr0},ich_vtr:{target.ich_vtr},"
            f"ich_status:{target.ich_status},wa1:{target.wa1},wa2:{target.wa2},"
            f"wa3:{target.wa3},hyp:{target.hyp_available},"
            f"kernel_in_hyp:{target.kernel_in_hyp},gic_sre:{target.gic_sre_usable},"
            f"ich_source:{ich_source},policy_valid:0x{policy.valid:x},"
            f"conduit:{conduit},mitigations_off:{policy.mitigations_off},"
            f"nospectre_v2:{policy.nospectre_v2},v4_policy:{v4_policy}"
        )
    mitigation_names = {
        MITIGATION_UNAFFECTED: "UNAFFECTED",
        MITIGATION_MITIGATED: "MITIGATED",
        MITIGATION_VULNERABLE: "VULNERABLE",
    }
    bhb_names = {
        BHB_STATE_UNAFFECTED: "UNAFFECTED",
        BHB_STATE_MITIGATED: "MITIGATED",
        BHB_STATE_VULNERABLE: "VULNERABLE",
    }
    text = "\n".join((
        "fixture=mt6797-a72-six-row-v1",
        "abi=5",
        "origin=FIXTURE",
        *target_lines,
        f"system=valid:0x{system.valid:x},ctr:0x{system.ctr_sys:x},"
        f"strict_mask:0x{system.ctr_strict_mask:x},ssbs:{system.ssbs},"
        f"v2_state:{_canonical_enum(system.v2_state, mitigation_names, 'v2-state')},"
        f"v4_state:{_canonical_enum(system.v4_state, mitigation_names, 'v4-state')},"
        f"bhb_state:{_canonical_enum(system.bhb_state, bhb_names, 'bhb-state')},"
        f"bhb_matcher_loop_count:{system.bhb_matcher_loop_count},"
        f"bhb_system_method:{system.bhb_system_method}",
    )) + "\n"
    return text.encode()


def fixture_identity_is_field_sensitive() -> bool:
    baseline = sha256(fixture_material())
    groups = (
        (TargetEvidence, FIXTURE_TARGETS[0], "targets"),
        (TargetPolicy, FIXTURE_POLICIES[0], "policies"),
        (SystemEvidence, FIXTURE_SYSTEM, "system"),
    )
    for record_type, record, group in groups:
        for field in dataclass_fields(record_type):
            value = getattr(record, field.name)
            mutated = value + 1 if isinstance(value, int) else value + "-MUTATED"
            changed = dataclass_replace(record, **{field.name: mutated})
            try:
                if group == "targets":
                    material = fixture_material((changed, FIXTURE_TARGETS[1]))
                elif group == "policies":
                    material = fixture_material(
                        policies=(changed, FIXTURE_POLICIES[1])
                    )
                else:
                    material = fixture_material(system=changed)
            except OracleRejected:
                continue
            if sha256(material) == baseline:
                return False
    return True


def value_text(value: object, field: str) -> str:
    if field.endswith("_mask"):
        return f"0x{int(value):x}"
    if field == "bhb.system_method":
        return f"0x{int(value):x}"
    return str(value)


def expected_typed_effect_rows() -> list[tuple[str, str, str]]:
    aggregate, targets = derive_fixture_effects()
    rows = [
        ("aggregate", field, value_text(aggregate[field], field))
        for field in AGGREGATE_EFFECT_FIELDS
    ]
    for target, effect in enumerate(targets):
        rows.extend(
            (f"target{target}", field, value_text(effect[field], field))
            for field in TARGET_EFFECT_FIELDS
        )
    return rows


REQUIRED_CAPS = {
    "ARM64_MISMATCHED_CACHE_TYPE",
    "ARM64_SPECTRE_V2",
    "ARM64_SPECTRE_V4",
    "ARM64_SPECTRE_BHB",
    "ARM64_WORKAROUND_1742098",
    "ARM64_WORKAROUND_SPECULATIVE_AT",
}
DYNAMIC_PRESENT = {
    "ARM64_MISMATCHED_CACHE_TYPE",
    "ARM64_SPECTRE_V2",
    "ARM64_SPECTRE_V4",
    "ARM64_SPECTRE_BHB",
}
DYNAMIC_ABSENT = {
    "ARM64_HAS_GICV5_LEGACY",
    "ARM64_HAS_ICH_HCR_EL2_TDIR",
}


IMPLEMENTATION_MARKERS = {
    "implementation_state": "PARTIAL_SIX_ROW_FIXTURE_EVALUATOR",
    "a41_complete": "no",
    "plan_abi": "5",
    "evidence_origin": "FIXTURE",
    "fixture_capability_rows": "40",
    "fixture_present_count": "8",
    "fixture_absent_count": "32",
    "fixture_required_count": "6",
    "local_caps_planned": "1",
    "effects_planned": "1",
    "effect_plan_complete": "yes",
    "runtime_binding_complete": "no",
    "profile_validate_plan": "-EAGAIN",
    "profile_prepare": "-EAGAIN",
    "plan_identity": "unavailable",
    "commit_path": "unavailable",
    "plan_frozen_reachable": "no",
    "committed_reachable": "no",
    "ready_reachable": "no",
    "cpu_boot_veto": "-EAGAIN",
    "cpu_disable_veto": "false",
    "maxcpus": "8",
    "build_authorized": "no",
    "device_action_authorized": "no",
    "boot_candidate": "false",
    "hardware_support_claim": "none",
}


def _read_tsv(path: Path, fields: Sequence[str]) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require(reader.fieldnames == list(fields), f"{path.name}: header changed")
        rows = list(reader)
    for row in rows:
        require(None not in row and all(value is not None for value in row.values()),
                f"{path.name}: malformed row")
    return rows


def validate_tables(repo: Path) -> None:
    parent = load_parent(repo)
    census_path = repo / EXPERIMENT / "results/six-row-fixture.tsv"
    rows = _read_tsv(census_path, (
        "slot", "symbol", "target0_state", "target1_state",
        "aggregate_state", "required", "basis",
    ))
    require(len(rows) == 40, "fixture census is not exactly 40 rows")
    expected_slots = sorted(parent.ALL)
    require([int(row["slot"]) for row in rows] == expected_slots,
            "fixture census slot order changed")
    present_count = 0
    absent_count = 0
    required_count = 0
    for row, slot in zip(rows, expected_slots):
        symbol = parent.ALL[slot]
        require(row["symbol"] == symbol, f"slot {slot}: symbol changed")
        state = PRESENT if symbol in set(parent.PRESENT.values()) | DYNAMIC_PRESENT else ABSENT
        require(symbol not in set(parent.UNRESOLVED.values()) -
                DYNAMIC_PRESENT - DYNAMIC_ABSENT,
                f"slot {slot}: unexpected unresolved capability")
        require((row["target0_state"], row["target1_state"],
                 row["aggregate_state"]) == (state, state, state),
                f"slot {slot}: fixture state changed")
        required = "yes" if symbol in REQUIRED_CAPS else "no"
        require(row["required"] == required, f"slot {slot}: required bit changed")
        require(bool(row["basis"].strip()), f"slot {slot}: basis is empty")
        present_count += state == PRESENT
        absent_count += state == ABSENT
        required_count += required == "yes"
    require((present_count, absent_count, required_count) == (8, 32, 6),
            "fixture census totals changed")

    effects_path = repo / EXPERIMENT / "results/typed-effects.tsv"
    effect_rows = _read_tsv(effects_path, ("scope", "field", "value", "basis"))
    expected = expected_typed_effect_rows()
    actual = [(row["scope"], row["field"], row["value"]) for row in effect_rows]
    require(actual == expected, "typed-effect rows or values changed")
    require(all(row["basis"].strip() for row in effect_rows),
            "typed-effect basis is empty")
    require(len(effect_rows) == 69, "typed-effect table is not exactly 69 rows")

    implementation = _read_tsv(
        repo / EXPERIMENT / "results/implementation.tsv",
        ("key", "value", "evidence"),
    )
    require(len(implementation) == len(IMPLEMENTATION_MARKERS),
            "implementation marker count changed")
    actual_markers = {row["key"]: row["value"] for row in implementation}
    require(actual_markers == IMPLEMENTATION_MARKERS,
            "implementation claim boundary changed")
    require(all(row["evidence"].strip() for row in implementation),
            "implementation evidence is empty")


def _expect_rejected(action, scope: str) -> None:
    try:
        action()
    except OracleRejected:
        return
    raise ValidationError(f"oracle accepted {scope}")


def validate_oracle() -> list[str]:
    require(sha256(fixture_material()) == FIXTURE_SHA256,
            "fixture canonical identity changed")
    require(fixture_identity_is_field_sensitive(),
            "fixture identity ignores a dataclass field")
    expected_six = {
        "ARM64_HAS_GICV5_LEGACY": ABSENT,
        "ARM64_HAS_ICH_HCR_EL2_TDIR": ABSENT,
        "ARM64_MISMATCHED_CACHE_TYPE": PRESENT,
        "ARM64_SPECTRE_V2": PRESENT,
        "ARM64_SPECTRE_V4": PRESENT,
        "ARM64_SPECTRE_BHB": PRESENT,
    }
    require(all(classify_six_rows(target) == expected_six for target in FIXTURE_TARGETS),
            "fixture six-row result changed")

    legacy = dataclass_replace(
        FIXTURE_TARGETS[0], pfr2=1 << 12, icc_idr0=1 << 8,
    )
    require(classify_gic(legacy) == PRESENT and classify_ich(legacy) == PRESENT,
            "legacy GIC/ICH path changed")
    require(
        classify_gic(dataclass_replace(
            FIXTURE_TARGETS[0], pfr2=1 << 12
        )) == ABSENT and
        classify_gic(dataclass_replace(
            FIXTURE_TARGETS[0], icc_idr0=1 << 8
        )) == ABSENT,
        "GIC GCIE/legacy conjunction changed",
    )
    require(classify_gic(dataclass_replace(legacy, pfr2=2 << 12)) == UNRESOLVED,
            "reserved GCIE was accepted")
    direct = dataclass_replace(
        FIXTURE_TARGETS[0], pfr0=1 << 24, icc_sre=ICC_SRE,
        gic_sre_usable=1, kernel_in_hyp=1, ich_source=ICH_DIRECT,
        ich_vtr=ICH_TDS,
    )
    require(classify_ich(direct) == PRESENT,
            "direct ICH TDS path changed")
    require(classify_ich(dataclass_replace(direct, ich_vtr=0)) == ABSENT,
            "direct ICH no-TDS path changed")
    require(classify_ich(dataclass_replace(direct, kernel_in_hyp=0)) == UNRESOLVED,
            "direct ICH privilege cross-check changed")
    hvc = dataclass_replace(
        direct, kernel_in_hyp=0, ich_source=ICH_HVC,
    )
    require(classify_ich(hvc) == PRESENT,
            "HVC ICH TDS path changed")
    require(classify_ich(dataclass_replace(hvc, ich_vtr=0)) == ABSENT,
            "HVC ICH no-TDS path changed")
    require(classify_ich(dataclass_replace(
        hvc, ich_vtr=0, ich_status=HVC_STUB_ERR
    )) == ABSENT, "HVC-stub unavailable path changed")
    require(classify_ich(dataclass_replace(
        hvc, ich_status=HVC_STUB_ERR
    )) == UNRESOLVED, "HVC-stub nonzero VTR was accepted")
    no_hyp = dataclass_replace(FIXTURE_TARGETS[0], hyp_available=0)
    require(classify_ich(no_hyp) == ABSENT,
            "no-hyp ICH NONE path changed")
    require(classify_ich(dataclass_replace(no_hyp, ich_vtr=1)) == UNRESOLVED,
            "no-hyp ICH payload was accepted")

    fixture = FIXTURE_TARGETS[0]
    require(classify_ctr(fixture, FIXTURE_SYSTEM) == PRESENT,
            "fixture CTR result changed")
    require(classify_ctr(fixture, dataclass_replace(
        FIXTURE_SYSTEM, ctr_sys=fixture.ctr
    )) == ABSENT, "CTR raw-match result changed")
    require(classify_ctr(fixture, dataclass_replace(
        FIXTURE_SYSTEM, ctr_sys=fixture.ctr_effective
    )) == ABSENT, "CTR effective-match result changed")
    ctr_absent, _ = derive_fixture_effects(
        system=dataclass_replace(FIXTURE_SYSTEM, ctr_sys=fixture.ctr)
    )
    require(
        all(not ctr_absent[field] for field in (
            "ctr_mismatch.required", "ctr_mismatch.target_mask",
            "ctr_mismatch.trap_ctr_el0", "ctr_mismatch.alternative",
        )),
        "symmetric-ABSENT CTR aggregate stayed required",
    )
    require(classify_ctr(fixture, dataclass_replace(
        FIXTURE_SYSTEM, ctr_strict_mask=CTR_STRICT_MASK ^ 1
    )) == UNRESOLVED, "noncanonical CTR mask was accepted")
    require(classify_ctr(dataclass_replace(
        fixture, ctr_effective=fixture.ctr
    ), FIXTURE_SYSTEM) == UNRESOLVED, "inconsistent effective CTR was accepted")
    require(classify_ctr(dataclass_replace(
        fixture, ctr=fixture.ctr & ~CTR_RES1,
        ctr_effective=fixture.ctr_effective & ~CTR_RES1,
    ), FIXTURE_SYSTEM) == UNRESOLVED, "CTR RES1 violation was accepted")

    require(classify_v2(fixture) == PRESENT and classify_v4(fixture) == PRESENT,
            "fixture v2/v4 classification changed")
    require(classify_v2(dataclass_replace(fixture, pfr0=1 << 56)) == ABSENT,
            "CSV2 v2 result changed")
    require(classify_v2(dataclass_replace(fixture, wa1=SMCCC_UNAFFECTED)) == ABSENT,
            "WA1 unaffected result changed")
    v2_absent_target = dataclass_replace(fixture, wa1=SMCCC_UNAFFECTED)
    v2_absent, _ = derive_fixture_effects(
        targets=(v2_absent_target, v2_absent_target)
    )
    require(
        all(not v2_absent[field] for field in (
            "spectre_v2.required", "spectre_v2.target_mask",
            "spectre_v2.mitigation_state", "spectre_v2.conduit",
            "spectre_v2.callback", "spectre_v2.hyp_vector",
            "spectre_v2.alternative",
        )),
        "symmetric-ABSENT v2 aggregate stayed required",
    )
    require(classify_v2(dataclass_replace(fixture, wa1=-9)) == UNRESOLVED,
            "unknown WA1 status was accepted")
    require(classify_v4(dataclass_replace(fixture, pfr1=1 << 4)) == PRESENT,
            "SSBS v4 result changed")
    require(classify_v4(dataclass_replace(fixture, wa2=SMCCC_NOT_REQUIRED)) == ABSENT,
            "WA2 not-required result changed")
    v4_absent_target = dataclass_replace(fixture, wa2=SMCCC_NOT_REQUIRED)
    v4_absent, _ = derive_fixture_effects(
        targets=(v4_absent_target, v4_absent_target)
    )
    require(
        all(not v4_absent[field] for field in (
            "spectre_v4.required", "spectre_v4.target_mask",
            "spectre_v4.mitigation_state", "spectre_v4.method",
            "spectre_v4.conduit", "spectre_v4.policy",
            "spectre_v4.callback_required_mask",
            "spectre_v4.firmware_alternative",
        )),
        "symmetric-ABSENT v4 aggregate stayed required",
    )
    require(classify_v4(dataclass_replace(fixture, wa2=-9)) == UNRESOLVED,
            "unknown WA2 status was accepted")
    v2 = evaluate_v2(fixture, FIXTURE_POLICIES[0])
    require(v2["spectre_v2_hyp_vector"] == HYP_SPECTRE_DIRECT and
            v2["spectre_v2_callback"] == V2_CALLBACK_SMC,
            "fixture v2 effect changed")
    require(evaluate_v2(
        dataclass_replace(fixture, hyp_available=0), FIXTURE_POLICIES[0]
    )["spectre_v2_hyp_vector"] == HYP_DIRECT,
            "v2 no-hyp vector changed")
    require(evaluate_v2(fixture, dataclass_replace(
        FIXTURE_POLICIES[0], conduit=SMCCC_HVC
    ))["spectre_v2_callback"] == V2_CALLBACK_HVC,
            "v2 HVC callback changed")
    ssbs_target = dataclass_replace(fixture, pfr1=1 << 4)
    require(evaluate_v4(ssbs_target, FIXTURE_POLICIES[0])[
        "spectre_v4_method"
    ] == V4_SSBS, "v4 SSBS method changed")
    _expect_rejected(
        lambda: evaluate_v4(ssbs_target, dataclass_replace(
            FIXTURE_POLICIES[0], v4_policy=V4_FORCE_OFF
        )),
        "SSBS plus force-off policy",
    )
    require(evaluate_v4(fixture, FIXTURE_POLICIES[0])[
        "spectre_v4_callback_required"
    ] == 1, "v4 dynamic callback changed")
    require(evaluate_v4(fixture, dataclass_replace(
        FIXTURE_POLICIES[0], v4_policy=V4_FORCE_ON
    ))["spectre_v4_callback_required"] == 0,
            "v4 force-on callback changed")

    base_effect = {"spectre_v2_hyp_vector": HYP_SPECTRE_DIRECT}
    bhb = evaluate_bhb(
        fixture, FIXTURE_POLICIES[0], MITIGATION_MITIGATED, base_effect,
    )
    require(
        bhb["bhb_method"] == BHB_LOOP and bhb["bhb_loop_count"] == 8 and
        bhb["bhb_matcher_loop_count"] == 8 and
        bhb["bhb_hyp_vector"] == HYP_SPECTRE_DIRECT,
        "exact A72 loop-8 BHB result changed",
    )
    clear = evaluate_bhb(
        dataclass_replace(fixture, isar2=1 << 28), FIXTURE_POLICIES[0],
        MITIGATION_MITIGATED, base_effect,
    )
    require(clear["bhb_method"] == BHB_INSTRUCTION and
            clear["bhb_matcher_loop_count"] == 0,
            "ClearBHB priority changed")
    hardware = evaluate_bhb(
        dataclass_replace(fixture, mmfr1=1 << 60), FIXTURE_POLICIES[0],
        MITIGATION_MITIGATED, base_effect,
    )
    require(hardware["bhb_method"] == BHB_HARDWARE,
            "ECBHB priority changed")
    hardware_over_clear = evaluate_bhb(
        dataclass_replace(fixture, isar2=1 << 28, mmfr1=1 << 60),
        FIXTURE_POLICIES[0], MITIGATION_MITIGATED, base_effect,
    )
    require(
        hardware_over_clear["bhb_method"] == BHB_HARDWARE and
        hardware_over_clear["bhb_matcher_loop_count"] == 0,
        "ECBHB-over-ClearBHB priority changed",
    )
    require(evaluate_bhb(
        dataclass_replace(fixture, pfr0=3 << 56), FIXTURE_POLICIES[0],
        MITIGATION_MITIGATED, base_effect,
    )["bhb_mitigation_state"] == BHB_STATE_UNAFFECTED,
            "CSV2.3 BHB result changed")
    bhb_absent_target = dataclass_replace(fixture, pfr0=3 << 56)
    bhb_absent, _ = derive_fixture_effects(
        targets=(bhb_absent_target, bhb_absent_target)
    )
    require(
        all(not bhb_absent[field] for field in (
            "bhb.required", "bhb.target_mask", "bhb.method",
            "bhb.loop_count", "bhb.matcher_loop_count", "bhb.conduit",
            "bhb.system_method", "bhb.mitigation_state",
            "bhb.vector_template", "bhb.hyp_vector", "bhb.alternative",
            "bhb.v2_non_vulnerable",
        )),
        "symmetric-ABSENT BHB aggregate stayed required",
    )
    require(evaluate_bhb(
        fixture, FIXTURE_POLICIES[0], MITIGATION_VULNERABLE, base_effect,
    )["bhb_mitigation_state"] == BHB_STATE_VULNERABLE,
            "vulnerable-v2 BHB gate changed")
    _expect_rejected(
        lambda: evaluate_bhb(
            dataclass_replace(fixture, isar2=2 << 28), FIXTURE_POLICIES[0],
            MITIGATION_MITIGATED, base_effect,
        ),
        "reserved ClearBHB field",
    )

    asymmetric_gic = dataclass_replace(
        fixture, pfr2=1 << 12, icc_idr0=1 << 8,
    )
    require(classify_six_rows(fixture) != classify_six_rows(asymmetric_gic),
            "asymmetric classifier fixture does not distinguish targets")
    _expect_rejected(
        lambda: derive_fixture_effects((
            fixture, dataclass_replace(fixture, wa1=SMCCC_NOT_SUPPORTED),
        )),
        "collapsed v2 effect target",
    )
    _expect_rejected(
        lambda: derive_fixture_effects((
            fixture, dataclass_replace(fixture, wa2=SMCCC_NOT_SUPPORTED),
        )),
        "collapsed v4 effect target",
    )
    _expect_rejected(
        lambda: derive_fixture_effects((
            fixture, dataclass_replace(fixture, isar2=1 << 28),
        )),
        "collapsed BHB effect target",
    )

    aggregate, targets = derive_fixture_effects()
    require(len(aggregate) == 33 and all(len(target) == 18 for target in targets),
            "typed effect field count changed")
    require(len(expected_typed_effect_rows()) == 69,
            "typed effect row count changed")
    return list(ORACLE_CHECKS)


def validate_inventory(repo: Path, *, skip_frozen_evidence: bool) -> None:
    root = repo / EXPERIMENT
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    required = EXPECTED_EXPERIMENT_FILES - FROZEN_TRANSCRIPTS
    if skip_frozen_evidence:
        require(required <= actual <= EXPECTED_EXPERIMENT_FILES,
                "experiment inventory changed")
    else:
        require(actual == EXPECTED_EXPERIMENT_FILES,
                "frozen experiment inventory changed")
    forbidden_commands = tuple(
        word for word in (
            "cu" + "rl", "wg" + "et", "s" + "sh", "sc" + "p",
            "rsy" + "nc", "nc" + "at", "so" + "cat",
            "build" + "-kernel", "dev" + "-vm",
        )
    )
    command_pattern = re.compile(
        r"(?<![A-Za-z0-9_])(?:" +
        "|".join(map(re.escape, forbidden_commands)) +
        r")(?![A-Za-z0-9_])"
    )
    for relative in actual:
        path = root / relative
        require(path.is_file() and not path.is_symlink(),
                f"experiment path is unsafe: {relative}")
        text = path.read_text()
        require(("/" + "Users/") not in text,
                f"experiment exposes a personal host path: {relative}")
        require(("arti" + "facts/") not in text,
                f"experiment refers to private artifacts: {relative}")
        require(not any(line.endswith((" ", "\t")) for line in text.splitlines()),
                f"experiment has trailing whitespace: {relative}")
        if relative.startswith("scripts/"):
            require(command_pattern.search(text) is None,
                    f"experiment script contains an external action: {relative}")
    for relative, digest in FROZEN_FILE_SHA256.items():
        require(sha256((root / relative).read_bytes()) == digest,
                f"frozen experiment file changed: {relative}")


REPOSITORY_MUTATIONS = (
    "manifest-profile-count",
    "manifest-profile-series",
    "manifest-profile-leak",
    "profile-fragment-setting",
    "selected-series-duplicate",
    "selected-series-parent",
    "canonical-series-order",
    "patch-source-commit",
    "patch-author",
    "patch-signoff",
    "fixture-census-state",
    "fixture-census-required",
    "implementation-claim",
    "external-action",
)
SOURCE_MUTATIONS = (
    "source-commit-path-core",
    "source-commit-path-profile",
    "source-commit-path-paired",
    "source-fixture-runtime-origin",
    "source-profile-early-success",
    "source-prepare-early-success",
    "source-identity-injection",
    "source-boot-veto",
    "source-disable-veto",
    "source-classifier-target-collapse",
    "source-v2-effect-target-collapse",
    "source-bhb-effect-target-collapse",
    "source-paired-ctr-producer-expectation",
    "source-paired-v2-hyp-producer-expectation",
    "source-paired-bhb-loop-producer-expectation",
)
ORACLE_MUTATIONS = (
    "oracle-gic-valid",
    "oracle-gic-gcie",
    "oracle-gic-legacy",
    "oracle-gic-sre-crosscheck",
    "oracle-gic-result",
    "oracle-ich-hyp-valid",
    "oracle-ich-none-payload",
    "oracle-ich-direct-privilege",
    "oracle-ich-direct-status",
    "oracle-ich-direct-tds",
    "oracle-ich-hvc-privilege",
    "oracle-ich-hvc-status",
    "oracle-ich-hvc-tds",
    "oracle-ich-result",
    "oracle-ctr-valid",
    "oracle-ctr-raw",
    "oracle-ctr-effective",
    "oracle-ctr-system",
    "oracle-ctr-mask",
    "oracle-ctr-clidr",
    "oracle-ctr-result",
    "oracle-v2-target-shape",
    "oracle-v2-csv2",
    "oracle-v2-wa1-valid",
    "oracle-v2-wa1-status",
    "oracle-v2-hyp-vector",
    "oracle-v2-result",
    "oracle-v4-target-shape",
    "oracle-v4-ssbs",
    "oracle-v4-wa2-valid",
    "oracle-v4-wa2-status",
    "oracle-v4-alternative-gap",
    "oracle-v4-result",
    "oracle-bhb-csv2",
    "oracle-bhb-clearbhb",
    "oracle-bhb-ecbhb",
    "oracle-bhb-system-v2",
    "oracle-bhb-loop8",
    "oracle-bhb-result",
    "oracle-asymmetric-classifier-index",
    "oracle-asymmetric-v2-effect-index",
    "oracle-asymmetric-v4-effect-index",
    "oracle-asymmetric-bhb-effect-index",
)
TYPED_EFFECT_MUTATIONS = tuple(
    "typed-effect-" + scope + "-" + field.replace("_", "-").replace(".", "-")
    for scope, fields in (
        ("aggregate", AGGREGATE_EFFECT_FIELDS),
        ("target0", TARGET_EFFECT_FIELDS),
        ("target1", TARGET_EFFECT_FIELDS),
    )
    for field in fields
)
MUTATION_NAMES = (
    *REPOSITORY_MUTATIONS,
    *SOURCE_MUTATIONS,
    *ORACLE_MUTATIONS,
    *TYPED_EFFECT_MUTATIONS,
)


def offline_result_lines() -> list[str]:
    checks = (*REPOSITORY_CHECKS, *SOURCE_CHECKS, *ORACLE_CHECKS)
    return [
        "validation=a41-six-row-fixture-offline",
        *(f"PASS {check}" for check in checks),
        f"patch_sha256={PATCH_SHA256}",
        f"series_sha256={SERIES_SHA256}",
        f"patchset_sha256={PATCHSET_SHA256}",
        f"source_state_sha256={SOURCE_STATE_SHA256}",
        f"config_sha256={CONFIG_SHA256}",
        f"fixture_sha256={FIXTURE_SHA256}",
        "fixture_capabilities=40:8-present:32-absent:6-required",
        "typed_effect_fields=33-aggregate:18-target0:18-target1",
        "implementation_state=PARTIAL_SIX_ROW_FIXTURE_EVALUATOR",
        "a41_complete=no",
        "network_accessed=no",
        "build_invoked=no",
        "device_accessed=no",
        "build_authorized=no",
        "device_action_authorized=no",
        f"RESULT PASS {len(checks)}/{len(checks)}",
    ]


def mutation_result_lines() -> list[str]:
    return [
        "validation=a41-six-row-fixture-mutations",
        *(f"PASS {name}" for name in MUTATION_NAMES),
        "network_accessed=no",
        "build_invoked=no",
        "device_accessed=no",
        f"RESULT PASS {len(MUTATION_NAMES)}/{len(MUTATION_NAMES)}",
    ]


def static_result_lines() -> list[str]:
    return [
        "validation=a41-six-row-fixture-kernel-static-review",
        f"source_parent={PARENT}",
        f"source_commit={SOURCE}",
        f"source_tree={SOURCE_TREE}",
        f"source_diff_sha256={SOURCE_DIFF_SHA256}",
        f"format_patch_sha256={PATCH_SHA256}",
        "git_diff_check=PASS",
        "checkincludes=PASS",
        "checkpatch_errors=0",
        "checkpatch_warnings=0",
        "strict_checkpatch_errors=0",
        "strict_checkpatch_warnings=0",
        "strict_checkpatch_checks=100",
        "strict_checkpatch_types=OPEN_ENDED_LINE",
        "python_syntax=PASS",
        "native_build_invoked=no",
        "buildbox_build_invoked=no",
        "network_accessed=no",
        "device_accessed=no",
        "RESULT PASS",
    ]


def validate_frozen_results(repo: Path, *, skip_frozen_evidence: bool) -> bool:
    results = repo / EXPERIMENT / "results"
    offline = results / "offline-validation-20260805.txt"
    mutations = results / "mutation-validation-20260805.txt"
    static = results / "kernel-static-review-20260805.txt"
    if skip_frozen_evidence and not all(
        path.exists() for path in (offline, mutations, static)
    ):
        return False
    require(offline.read_text().splitlines() == offline_result_lines(),
            "offline result is not exact validator stdout")
    require(mutations.read_text().splitlines() == mutation_result_lines(),
            "mutation result is not exact suite stdout")
    require(static.read_text().splitlines() == static_result_lines(),
            "kernel static result is not exact ordered evidence")
    return True


def validate_repository(
    repo: Path,
    *,
    pin_hashes: bool = True,
    skip_frozen_evidence: bool = False,
) -> list[str]:
    repo = repo.resolve()
    parent = load_parent(repo)
    validate_inventory(repo, skip_frozen_evidence=skip_frozen_evidence)
    validate_tables(repo)
    validate_oracle()

    manifest = json.loads((repo / MANIFEST).read_text())
    profiles = manifest["config"]["profiles"]
    require(len(profiles) == PROFILE_COUNT, "manifest profile count changed")
    require(PROFILE in profiles, "six-row fixture profile is missing")
    profile = profiles[PROFILE]
    require(profile.get("base") == "defconfig", "profile base changed")
    require(profile.get("patch_series") == str(SERIES), "profile series changed")
    require(tuple(profile.get("fragments", ())) == EXPECTED_FRAGMENTS,
            "profile fragment order changed")
    for name, candidate in profiles.items():
        if name == PROFILE:
            continue
        require(candidate.get("patch_series") != str(SERIES),
                f"fixture series leaked into profile {name}")
        require(str(FRAGMENT) not in candidate.get("fragments", ()),
                f"fixture fragment leaked into profile {name}")
    assignments = [
        line.strip()
        for line in (repo / FRAGMENT).read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(assignments == [
        "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
        "CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE=y",
        'CONFIG_LOCALVERSION="-gemini-a41-fixture-blocked"',
    ], "fixture fragment gained an unreviewed setting")
    require("maxcpus=8" in (repo / "configs/gemini-smp8.fragment").read_text(),
            "inherited maxcpus=8 changed")
    require(config_hash(repo, profile) == CONFIG_SHA256,
            "configuration-input identity changed")

    canonical = parent.series_entries((repo / CANONICAL_SERIES).read_text())
    selected = parent.series_entries((repo / SERIES).read_text())
    parent_selected = parent.series_entries((repo / PARENT_SERIES).read_text())
    parent.validate_all_profile_series(repo, manifest, canonical)
    require(len(selected) == SERIES_ENTRY_COUNT, "selected series count changed")
    require(selected[:-1] == parent_selected, "parent series prefix changed")
    require(selected[-1] == str(PATCH.relative_to("patches")),
            "patch 0154 is not the selected tail")
    require(parent.is_subsequence(selected, canonical),
            "selected series is not canonical order")
    if pin_hashes:
        require(parent.file_sha256(repo / SERIES) == SERIES_SHA256,
                "selected series identity changed")
        require(parent.patchset_hash(repo, SERIES) == PATCHSET_SHA256,
                "patchset identity changed")
        require(parent.source_state_hash(repo, SERIES) == SOURCE_STATE_SHA256,
                "source-state identity changed")
        require(parent.source_state_hash(repo, PARENT_SERIES) ==
                PARENT_SOURCE_STATE_SHA256, "parent source state changed")

    patch = (repo / PATCH).read_text()
    source_match = re.match(r"From ([0-9a-f]{40}) ", patch)
    require(source_match is not None and source_match.group(1) == SOURCE,
            "patch source commit changed")
    header = patch.split("\n---\n", 1)[0]
    parent.tokens(header, [
        "From: Gemini Mainline Project <noreply@invalid>",
        "Subject: [PATCH] arm64: evaluate MT6797 late-CPU fixture evidence",
        "This experiment-only change has no certifying sign-off and is not\n"
        "submission-ready.",
    ], "patch metadata")
    require("Signed-off-by:" not in patch, "synthetic patch gained a sign-off")
    sections = parent.patch_sections(patch)
    require(tuple(sections) == CHANGED_PATHS, "patch changed-path set changed")
    if pin_hashes:
        require(parent.file_sha256(repo / PATCH) == PATCH_SHA256,
                "format-patch identity changed")
    additions = parent.added_lines(patch)
    for forbidden in (
        "cpu_psci_ops.cpu_boot(cpu)",
        "apply_alternatives",
        "system_capabilities_finalized =",
        "late_receipt.state = ARM64_LATE_CPU_PROFILE_READY",
        "plan->identity[0] =",
        "draft->identity[0] =",
    ):
        require(forbidden not in additions,
                f"patch adds forbidden publication path {forbidden}")
    parent.tokens(additions, [
        "ARM64_LATE_CPU_BLOCK_COMMIT_PATH",
        "ARM64_LATE_CPU_BINDING_FIXTURE",
        "return -EAGAIN;",
    ], "patch safety boundary")
    inherited = (repo / PATCH_0092).read_text()
    inherited_mt = parent.patch_postimage(
        parent.patch_sections(inherited)["arch/arm64/kernel/mt6797_psci.c"]
    )
    boot = parent.function(inherited_mt, "mt6797_psci_cpu_boot")
    disable = parent.function(inherited_mt, "mt6797_psci_cpu_can_disable")
    require("return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot,
            "inherited boot veto changed")
    require("return false;" in disable, "inherited disable veto changed")
    require("PARTIAL_SIX_ROW_FIXTURE_EVALUATOR" in
            (repo / EXPERIMENT / "README.md").read_text(),
            "experiment claim is missing")
    frozen_checked = validate_frozen_results(
        repo, skip_frozen_evidence=skip_frozen_evidence
    )
    checks = list(REPOSITORY_CHECKS[:-1])
    if frozen_checked:
        checks.append(REPOSITORY_CHECKS[-1])
    return checks


def _struct_body(text: str, name: str) -> str:
    match = re.search(
        rf"struct\s+{re.escape(name)}\s*\{{(.*?)\n\}};", text, re.S
    )
    require(match is not None, f"missing struct {name}")
    return match.group(1)


def _require_tokens(text: str, tokens: Iterable[str], scope: str) -> None:
    for token in tokens:
        require(token in text, f"{scope}: missing {token!r}")


def validate_source_files(root: Path, *, repo: Path | None = None) -> None:
    repo = (repo or default_repo()).resolve()
    parent = load_parent(repo)
    kconfig = (root / CHANGED_PATHS[0]).read_text()
    header = (root / CHANGED_PATHS[1]).read_text()
    errata = (root / CHANGED_PATHS[2]).read_text()
    core = (root / CHANGED_PATHS[3]).read_text()
    lifecycle = (root / CHANGED_PATHS[4]).read_text()
    mt = (root / CHANGED_PATHS[5]).read_text()
    proton = (root / CHANGED_PATHS[6]).read_text()

    fixture_kconfig = re.search(
        r"config ARM64_MT6797_A72_FIXTURE_EVIDENCE\n(.*?)(?=\nconfig |\Z)",
        kconfig,
        re.S,
    )
    require(fixture_kconfig is not None, "fixture Kconfig is missing")
    _require_tokens(fixture_kconfig.group(1), [
        "depends on ARM64_MT6797_A72_CAPABILITY_PROFILE",
        "default n",
        "source validation only",
        "neither describes hardware nor enables a CPU boot path",
    ], "fixture Kconfig")

    _require_tokens(header, [
        "#define ARM64_LATE_CPU_PLAN_ABI\t\t5",
        "ARM64_LATE_CPU_BLOCK_COMMIT_PATH\t\tBIT_ULL(19)",
        "ARM64_LATE_CPU_BHB_NONE",
        "ARM64_LATE_CPU_BHB_STATE_UNAFFECTED",
        "ARM64_LATE_CPU_BHB_STATE_VULNERABLE",
        "ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_DIRECT",
        "ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_INDIRECT",
        "ARM64_LATE_CPU_ICH_VTR_NONE",
        "ARM64_LATE_CPU_ICH_VTR_DIRECT",
        "ARM64_LATE_CPU_ICH_VTR_HVC",
        "u8 kernel_in_hyp_mode;",
        "u8 ssbs;",
        "u8 bhb_matcher_loop_count;",
        "u8 bhb_system_method;",
        "u8 local_caps_planned;",
        "u8 effects_planned;",
        "(*derive_effects)(const struct arm64_late_cpu_plan *plan,",
    ], "ABI-5 schema")
    target_struct = _struct_body(header, "arm64_late_cpu_target_effect_plan")
    for field in TARGET_EFFECT_FIELDS:
        require(re.search(rf"\b{re.escape(field)}\s*;", target_struct) is not None,
                f"target effect schema lost {field}")
    aggregate_struct = _struct_body(header, "arm64_late_cpu_effect_plan")
    for token in (
        "callback_required_mask", "matcher_loop_count", "conduit",
        "hyp_vector", "target[ARM64_LATE_CPU_MAX_TARGETS]",
    ):
        require(token in aggregate_struct,
                f"aggregate effect schema lost {token}")

    compiled = tuple(parent.ALL[slot] for slot in sorted(parent.ALL))
    present_symbols = set(parent.PRESENT.values()) | DYNAMIC_PRESENT
    absent_symbols = set(parent.ABSENT.values()) | DYNAMIC_ABSENT
    require(parent.array_symbols(mt, "mt6797_a72_compiled_caps") == compiled,
            "compiled 40-row capability set changed")
    require(parent.array_symbols(mt, "mt6797_a72_present_caps") ==
            tuple(parent.ALL[slot] for slot in sorted(parent.ALL)
                  if parent.ALL[slot] in present_symbols),
            "fixture present capability set changed")
    require(parent.array_symbols(mt, "mt6797_a72_early_caps") ==
            ("ARM64_HAS_AMU_EXTN", "ARM64_HW_DBM"),
            "fixture early capability set changed")
    require(parent.array_symbols(mt, "mt6797_a72_unresolved_caps") ==
            tuple(parent.ALL[slot] for slot in sorted(parent.UNRESOLVED)),
            "production unresolved capability set changed")
    require(parent.array_symbols(mt, "mt6797_a72_absent_caps") ==
            tuple(parent.ALL[slot] for slot in sorted(parent.ALL)
                  if parent.ALL[slot] in absent_symbols),
            "fixture absent capability set changed")
    require(parent.array_symbols(mt, "mt6797_a72_required_caps") ==
            tuple(parent.ALL[slot] for slot in sorted(parent.ALL)
                  if parent.ALL[slot] in REQUIRED_CAPS),
            "fixture required capability set changed")

    gic = parent.function(core, "arm64_late_cpu_gicv5_legacy_state")
    ich = parent.function(core, "arm64_late_cpu_ich_hcr_tdir_state")
    gic_evidence = parent.function(core, "late_cpu_gicv5_legacy_evidence_state")
    _require_tokens(gic + gic_evidence, [
        "late_cpu_gic_descriptor_valid(cap, match)",
        "ARM64_LATE_CPU_TARGET_CAP_ID_REGS_VALID",
        "ARM64_LATE_CPU_TARGET_CAP_GIC_VALID",
        "ID_AA64PFR2_EL1_GCIE_SHIFT",
        "ICC_IDR0_EL1_GCIE_LEGACY_SHIFT",
        "gcie > 1", "legacy > 1", "target->gic_sre_usable !=",
        "gcie && legacy",
    ], "GIC oracle boundary")
    _require_tokens(ich, [
        "late_cpu_ich_descriptor_valid(cap, match)",
        "ARM64_LATE_CPU_TARGET_CAP_HYP_VALID",
        "target->kernel_in_hyp_mode && !target->hyp_available",
        "ARM64_LATE_CPU_ICH_VTR_NONE",
        "ARM64_LATE_CPU_ICH_VTR_DIRECT",
        "ARM64_LATE_CPU_ICH_VTR_HVC",
        "target->kernel_in_hyp_mode",
        "HVC_STUB_ERR",
        "ICH_VTR_EL2_TDS",
    ], "ICH oracle boundary")

    ctr = parent.function(errata, "arm64_late_cpu_cache_type_state")
    _require_tokens(ctr, [
        "cap->capability != ARM64_MISMATCHED_CACHE_TYPE",
        "system->valid & ~ARM64_LATE_CPU_SYSTEM_CAP_VALID_MASK",
        "mask != ~GENMASK_ULL(15, 14)",
        "~GENMASK_ULL(31, 0)",
        "!(raw & BIT(31))", "!(system->ctr_sys_val & BIT(31))",
        "CLIDR_LOC(target->clidr_el1)",
        "target->ctr_effective != effective",
        "effective != sys && raw != sys",
    ], "CTR oracle boundary")

    v2_state = parent.function(proton, "late_cpu_a72_spectre_v2_evidence_state")
    v4_state = parent.function(proton, "late_cpu_a72_spectre_v4_evidence_state")
    bhb_state = parent.function(proton, "late_cpu_a72_spectre_bhb_evidence_state")
    _require_tokens(v2_state, [
        "ID_AA64PFR0_EL1_CSV2_SHIFT", "csv2 > 3",
        "ARM64_LATE_CPU_TARGET_CAP_WA1_VALID",
        "late_cpu_wa1_status_valid", "SMCCC_ARCH_WORKAROUND_RET_UNAFFECTED",
    ], "Spectre-v2 predicate")
    _require_tokens(v4_state, [
        "ID_AA64PFR1_EL1_SSBS_SHIFT", "ssbs > 2",
        "ARM64_LATE_CPU_TARGET_CAP_WA2_VALID",
        "late_cpu_wa2_status_valid", "SMCCC_RET_NOT_REQUIRED",
    ], "Spectre-v4 predicate")
    _require_tokens(bhb_state, [
        "ID_AA64PFR0_EL1_CSV2_SHIFT", "csv2 > 3", "csv2 == 3",
    ], "Spectre-BHB predicate")
    _require_tokens(proton, [
        "status == SMCCC_RET_SUCCESS",
        "status == SMCCC_ARCH_WORKAROUND_RET_UNAFFECTED",
        "status == SMCCC_RET_NOT_SUPPORTED",
        "status == SMCCC_RET_NOT_REQUIRED",
    ], "named SMCCC status domain")

    v2_effect = parent.function(proton, "late_cpu_v2_effect")
    v4_effect = parent.function(proton, "late_cpu_v4_effect")
    bhb_effect = parent.function(proton, "arm64_late_cpu_a72_bhb_effect")
    _require_tokens(v2_effect, [
        "ARM64_LATE_CPU_HYP_VECTOR_DIRECT",
        "ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_DIRECT",
        "ARM64_LATE_CPU_V2_CALLBACK_SMC",
        "ARM64_LATE_CPU_V2_CALLBACK_HVC",
        "policy->mitigations_off || policy->nospectre_v2",
    ], "Spectre-v2 effects")
    _require_tokens(v4_effect, [
        "ARM64_LATE_CPU_V4_SSBS", "ARM64_LATE_CPU_V4_FIRMWARE",
        "ARM64_LATE_CPU_V4_POLICY_FORCE_OFF", "return -EOPNOTSUPP;",
        "spectre_v4_callback_required = 1",
    ], "Spectre-v4 effects")
    _require_tokens(bhb_effect, [
        "ID_AA64ISAR2_EL1_CLRBHB_SHIFT",
        "ID_AA64MMFR1_EL1_ECBHB_SHIFT",
        "effects->bhb_matcher_loop_count = 8",
        "ARM64_LATE_CPU_BHB_HARDWARE",
        "ARM64_LATE_CPU_BHB_INSTRUCTION",
        "Exact Cortex-A72 priority selects the k=8 loop before WA3",
        "effects->bhb_loop_count = 8",
        "ARM64_LATE_CPU_BHB_VECTOR_LOOP",
    ], "Spectre-BHB effects")

    classifier = parent.function(mt, "mt6797_a72_classify_local_cap")
    require(classifier.count("&evidence->target_cap[target]") == 6,
            "six-row classifier collapsed or changed target indexing")
    _require_tokens(classifier, [
        "evidence->target_cpu[target] != 8 + target",
        "evidence->expected_target_mpidr[target] != 0x200 + target",
        "evidence->expected_target_midr[target] != MIDR_CORTEX_A72",
        "arm64_late_cpu_gicv5_legacy_state",
        "arm64_late_cpu_ich_hcr_tdir_state",
        "arm64_late_cpu_cache_type_state",
        "arm64_late_cpu_a72_spectre_v2_state",
        "arm64_late_cpu_a72_spectre_v4_state",
        "arm64_late_cpu_a72_spectre_bhb_state",
    ], "six-row classifier")
    planner = parent.function(core, "arm64_plan_late_cpu_capabilities")
    _require_tokens(planner, [
        "classify_late_cpu_cap(cap, draft, profile, target,",
        "draft->target[target].classified_local_caps",
        "draft->target[target].local_caps",
        "if (!all_classified)",
        "draft->local_caps_planned = 1",
    ], "per-target classifier loop")

    derive = parent.function(mt, "mt6797_a72_derive_effects")
    require(derive.count("&plan->evidence.target_cap[target]") == 2 and
            derive.count("&plan->evidence.target_policy[target]") == 2,
            "effect evaluator collapsed or changed target indexing")
    _require_tokens(derive, [
        "arm64_late_cpu_a72_spectre_v2_v4_effects",
        "arm64_late_cpu_a72_bhb_effect",
        "effects->target[target].spectre_v2_state > system_v2_state",
        "mt6797_a72_v2_effect_equal",
        "mt6797_a72_v4_effect_equal",
        "mt6797_a72_bhb_effect_equal",
        "effects->spectre_v4.callback_required_mask |= BIT(target)",
        "effects->bhb.matcher_loop_count =",
        "effects->compat_aes_clear =",
        "effects->speculative_at_finalization =",
    ], "typed-effect aggregation")

    core_effect_validator = parent.function(core, "validate_late_cpu_effect_plan")
    _require_tokens(core_effect_validator, [
        "late_cpu_v2_target_effect_valid",
        "late_cpu_v4_target_effect_valid",
        "late_cpu_bhb_target_effect_valid",
        "effects->spectre_v4.callback_required_mask != callback_mask",
        "effects->bhb.matcher_loop_count != matcher_loop_count",
        "late_cpu_bhb_system_method(effects->bhb.method)",
    ], "core typed-effect validator")
    effect_planner = parent.function(core, "arm64_plan_late_cpu_effects")
    require(effect_planner.index("profile->derive_effects") <
            effect_planner.index("validate_late_cpu_effect_plan") <
            effect_planner.index("draft->effects = effects"),
            "scratch effect validation order changed")

    fixture_target_exact = parent.function(mt, "mt6797_a72_fixture_target_effect_exact")
    lifecycle_target_equal = parent.function(lifecycle, "late_profile_target_effects_match")
    for field in TARGET_EFFECT_FIELDS:
        require(f"effect->{field}" in fixture_target_exact,
                f"fixture exact check lost target field {field}")
        require(f"left->{field}" in lifecycle_target_equal,
                f"lifecycle copy check lost target field {field}")
    fixture_effects_exact = parent.function(mt, "mt6797_a72_fixture_effects_exact")
    lifecycle_effects_equal = parent.function(lifecycle, "late_profile_effects_match")
    for field in AGGREGATE_EFFECT_FIELDS:
        c_field = field.replace(".", ".")
        require(f"effects->{c_field}" in fixture_effects_exact,
                f"fixture exact check lost aggregate field {field}")
        require(f"left->{c_field}" in lifecycle_effects_equal,
                f"lifecycle copy check lost aggregate field {field}")

    fixture_target = parent.function(mt, "mt6797_a72_fixture_target_exact")
    fixture_registers = parent.function(mt, "mt6797_a72_fixture_registers_exact")
    fixture_evidence = parent.function(mt, "mt6797_a72_evidence_is_fixture")
    populate = parent.function(mt, "mt6797_a72_populate_fixture")
    _require_tokens(fixture_target + fixture_registers + fixture_evidence + populate, [
        "0x83338003", "0x93338003", "0xb4448004",
        "~GENMASK_ULL(15, 14)", "ARM64_LATE_CPU_BINDING_FIXTURE",
        "ARM64_LATE_CPU_ICH_VTR_NONE", "SMCCC_RET_SUCCESS",
        "ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK",
        "ARM64_LATE_CPU_SMCCC_SMC", "ARM64_LATE_CPU_V4_POLICY_DYNAMIC",
        "target_cap->hyp_available = 1",
        "target_cap->kernel_in_hyp_mode = 0",
    ], "fixture evidence bytes")
    _require_tokens(mt, [
        "0x78fcb018e5693cc2", "0x42fbf70c6d2e6deb",
        "0x8ab011246184c5ff", "0x40ea081505949815",
        "0xc41b8b84d68f9c0f", "0x9ffa4be08341e887",
        '"mt6797-a53-a72-a41-v5"',
    ], "fixture identities")

    validator = parent.function(mt, "mt6797_a72_validate_cap_plan")
    prepare = parent.function(mt, "mt6797_a72_profile_prepare")
    require("return 0;" not in validator and
            validator.rstrip().endswith("return -EAGAIN;\n}"),
            "fixture profile validator gained a success path")
    require("return 0;" not in prepare and
            prepare.rstrip().endswith("return -EAGAIN;\n}"),
            "fixture profile prepare gained a success path")
    require("plan->identity[i]" in validator and
            re.search(r"(?:plan|draft)->identity\s*\[[^]]+\]\s*=", mt) is None,
            "fixture path injects a plan identity")
    _require_tokens(mt, [
        "ARM64_LATE_CPU_BLOCK_CONFIGURATION",
        "ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY",
        "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA1",
        "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA2",
        "ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3",
        "ARM64_LATE_CPU_BLOCK_ID_REGISTERS",
        "ARM64_LATE_CPU_BLOCK_CACHE_TYPE",
        "ARM64_LATE_CPU_BLOCK_ASID",
        "ARM64_LATE_CPU_BLOCK_GRANULE",
        "ARM64_LATE_CPU_BLOCK_VA_MODE",
        "ARM64_LATE_CPU_BLOCK_GIC",
        "ARM64_LATE_CPU_BLOCK_HWCAP",
        "ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS",
        "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
        "ARM64_LATE_CPU_BLOCK_COMMIT_PATH",
    ], "profile safety blockers")

    lifecycle_prepare = parent.function(lifecycle, "arm64_prepare_late_cpu_profile")
    commit = parent.function(lifecycle, "arm64_commit_late_cpu_profile")
    _require_tokens(lifecycle_prepare, [
        "draft.evidence.blocker_mask |=\n\t\t\tARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
        "draft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_COMMIT_PATH",
        "if (ret || plan_ret || effect_ret || validate_ret ||",
        "draft.evidence.blocker_mask)",
        "!draft.local_caps_planned || !draft.effects_planned",
    ], "core fail-closed preparation")
    _require_tokens(commit, [
        'panic("late CPU profile commit implementation is unavailable")',
        "state != ARM64_LATE_CPU_PROFILE_PLAN_FROZEN",
        "!late_plan.local_caps_planned", "!late_plan.effects_planned",
    ], "unavailable commit path")
    boot = parent.function(mt, "mt6797_psci_cpu_boot")
    disable = parent.function(mt, "mt6797_psci_cpu_can_disable")
    require("return -EAGAIN;" in boot and "cpu_psci_ops.cpu_boot" not in boot,
            "source boot veto changed")
    require("return false;" in disable, "source disable veto changed")


def run_git(root: Path, args: Sequence[str], *, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
    )
    error = result.stderr.decode() if binary else result.stderr
    require(result.returncode == 0,
            f"git {args[0]} failed: {error.strip()}")
    return result.stdout


def validate_source_application(repo: Path, source_root: Path) -> None:
    repo = repo.resolve()
    source_root = source_root.resolve()
    parent = load_parent(repo)
    require((source_root / ".git").exists(),
            "source root is not a Git repository")
    require(run_git(source_root, ["rev-parse", f"{PARENT}^{{tree}}"] ).strip() ==
            PARENT_TREE, "source parent tree changed")
    require(run_git(source_root, ["rev-parse", f"{SOURCE}^{{tree}}"] ).strip() ==
            SOURCE_TREE, "source result tree changed")
    require(run_git(source_root, ["rev-parse", f"{SOURCE}^"]).strip() == PARENT,
            "source commit parent changed")
    require(run_git(source_root, ["rev-parse", "HEAD"]).strip() == SOURCE,
            "source checkout is not at the pinned commit")
    require(not run_git(source_root, ["status", "--porcelain"]).strip(),
            "source checkout is not clean")
    require(not run_git(source_root, ["diff", "--check", f"{PARENT}..{SOURCE}"]).strip(),
            "source diff has whitespace errors")
    diff = run_git(source_root, ["diff", f"{PARENT}..{SOURCE}"], binary=True)
    require(sha256(diff) == SOURCE_DIFF_SHA256, "source diff identity changed")
    changed = run_git(source_root, ["diff", "--name-only", f"{PARENT}..{SOURCE}"])
    require(tuple(changed.splitlines()) == CHANGED_PATHS,
            "source changed-path set changed")

    checkpatch = subprocess.run(
        [
            str(source_root / "scripts/checkpatch.pl"), "--no-tree",
            "--show-types", "--ignore=MISSING_SIGN_OFF",
            str((repo / PATCH).resolve()),
        ],
        cwd=source_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(checkpatch.returncode == 0 and
            re.search(r"total: 0 errors, 0 warnings", checkpatch.stdout),
            "format-patch checkpatch failed")
    strict_checkpatch = subprocess.run(
        [
            str(source_root / "scripts/checkpatch.pl"), "--strict", "--no-tree",
            "--show-types", "--ignore=MISSING_SIGN_OFF",
            str((repo / PATCH).resolve()),
        ],
        cwd=source_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        strict_checkpatch.returncode == 1 and
        "total: 0 errors, 0 warnings, 100 checks" in strict_checkpatch.stdout and
        strict_checkpatch.stdout.count("CHECK:OPEN_ENDED_LINE:") == 100 and
        not re.search(r"^CHECK:(?!OPEN_ENDED_LINE:)",
                      strict_checkpatch.stdout, re.MULTILINE),
        "strict checkpatch signal changed",
    )
    include_paths = [path for path in CHANGED_PATHS if path.endswith((".c", ".h"))]
    checkincludes = subprocess.run(
        [str(source_root / "scripts/checkincludes.pl"), *include_paths],
        cwd=source_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(checkincludes.returncode == 0 and
            "No duplicate includes found." in checkincludes.stdout,
            "duplicate-include check failed")
    for script in (repo / EXPERIMENT / "scripts").glob("*.py"):
        compile(script.read_text(), str(script), "exec")

    patch_text = (repo / PATCH).read_text()
    sections = parent.patch_sections(patch_text)
    with tempfile.TemporaryDirectory(prefix="gemini-a41-six-row-apply-") as temporary:
        scratch = Path(temporary)
        for path, section in sections.items():
            index = re.search(r"^index ([0-9a-f]+)\.\.([0-9a-f]+)", section, re.M)
            require(index is not None, f"{path}: patch index is missing")
            parent_blob = run_git(
                source_root, ["show", f"{PARENT}:{path}"], binary=True
            )
            parent_oid = run_git(
                source_root, ["rev-parse", f"{PARENT}:{path}"]
            ).strip()
            require(parent_oid.startswith(index.group(1)),
                    f"{path}: patch preimage changed")
            target = scratch / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(parent_blob)
        command = [
            "git", "apply", "--whitespace=error-all", str((repo / PATCH).resolve())
        ]
        check = subprocess.run(
            [*command[:2], "--check", *command[2:]],
            cwd=scratch,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(check.returncode == 0,
                f"patch application check failed: {check.stderr.strip()}")
        applied = subprocess.run(
            command,
            cwd=scratch,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(applied.returncode == 0,
                f"patch application failed: {applied.stderr.strip()}")
        for path in sections:
            expected = run_git(
                source_root, ["show", f"{SOURCE}:{path}"], binary=True
            )
            require((scratch / path).read_bytes() == expected,
                    f"{path}: applied postimage differs from source commit")
        validate_source_files(scratch, repo=repo)


def default_repo() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", "--repo-root", dest="repo", type=Path,
                        default=default_repo())
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--skip-frozen-evidence", action="store_true")
    args = parser.parse_args(argv)
    print("validation=a41-six-row-fixture-offline")
    try:
        checks = validate_repository(
            args.repo,
            skip_frozen_evidence=args.skip_frozen_evidence,
        )
        validate_source_application(args.repo, args.source_root)
        checks.extend(SOURCE_CHECKS)
        checks.extend(validate_oracle())
    except (
        OSError, ValueError, RuntimeError, json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    for check in checks:
        print(f"PASS {check}")
    print(f"patch_sha256={PATCH_SHA256}")
    print(f"series_sha256={SERIES_SHA256}")
    print(f"patchset_sha256={PATCHSET_SHA256}")
    print(f"source_state_sha256={SOURCE_STATE_SHA256}")
    print(f"config_sha256={CONFIG_SHA256}")
    print(f"fixture_sha256={FIXTURE_SHA256}")
    print("fixture_capabilities=40:8-present:32-absent:6-required")
    print("typed_effect_fields=33-aggregate:18-target0:18-target1")
    print("implementation_state=PARTIAL_SIX_ROW_FIXTURE_EVALUATOR")
    print("a41_complete=no")
    print("network_accessed=no")
    print("build_invoked=no")
    print("device_accessed=no")
    print("build_authorized=no")
    print("device_action_authorized=no")
    print(f"RESULT PASS {len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
