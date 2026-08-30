#!/usr/bin/env python3
"""Require representative unsafe expectation-activation mutations to fail."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile

import activation_edits
from validate_activation_source import ValidationError, validate


PROFILE = Path(activation_edits.PROFILE)


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"mutation anchor count changed: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


def prepare(source_root: Path, destination: Path) -> None:
    source = source_root / PROFILE
    target = destination / PROFILE
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    activation_edits.apply(destination)


def mutations() -> list[tuple[str, object]]:
    return [
        ("wrong-source-identity", lambda r: replace(
            r / PROFILE, "0x04bd7f060613719e", "0x14bd7f060613719e")),
        ("wrong-cpu8-capsule", lambda r: replace(
            r / PROFILE, "0xe35596c52bc8b40b", "0xe35596c52bc8b40a")),
        ("wrong-cpu9-capsule", lambda r: replace(
            r / PROFILE, "0x600c5e2d6733661d", "0x600c5e2d6733661c")),
        ("wrong-cpu9-mpidr", lambda r: replace(
            r / PROFILE, ".mpidr = { 0x200, 0x201 }",
            ".mpidr = { 0x200, 0x202 }")),
        ("partial-valid-mask", lambda r: replace(
            r / PROFILE, ".valid = ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK,",
            ".valid = ARM64_LATE_CPU_EXPECTED_PAIR_VALID_MASK & ~BIT_ULL(0),")),
        ("invent-id-register", lambda r: replace(
            r / PROFILE, ".id_aa64isar1 = 0x0000000000000000,",
            ".id_aa64isar1 = 0x0000000000000001,")),
        ("change-aarch32-register", lambda r: replace(
            r / PROFILE, ".id_mmfr3 = 0x02102211,",
            ".id_mmfr3 = 0x02102210,")),
        ("remove-attestation-blocker", lambda r: replace(
            r / PROFILE,
            "\t(ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |\t\t\t\\\n"
            "\t ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)",
            "\t(ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)")),
        ("restore-cache-blocker", lambda r: replace(
            r / PROFILE,
            "\t(ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |\t\t\t\\\n"
            "\t ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)",
            "\t(ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |\t\t\t\\\n"
            "\t ARM64_LATE_CPU_BLOCK_CACHE_TYPE |\t\t\t\t\\\n"
            "\t ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)")),
        ("remove-runtime-binding-gate", lambda r: replace(
            r / PROFILE,
            "\t    !mt6797_a72_binding_is_runtime(&evidence->binding) ||\n",
            "")),
        ("allow-current-target-cap", lambda r: replace(
            r / PROFILE,
            "\t\t    memchr_inv(&evidence->target_cap[target], 0,\n"
            "\t\t\t       sizeof(evidence->target_cap[target])) ||\n",
            "")),
        ("allow-observed-mpidr", lambda r: replace(
            r / PROFILE,
            "\t\tif (evidence->observed_target_mpidr[target] ||\n",
            "\t\tif (false ||\n")),
        ("accept-fixture-binding", lambda r: replace(
            r / PROFILE,
            "binding->origin == ARM64_LATE_CPU_BINDING_RUNTIME",
            "binding->origin == ARM64_LATE_CPU_BINDING_FIXTURE")),
        ("skip-system-evidence", lambda r: replace(
            r / PROFILE,
            "\t    !mt6797_a72_system_evidence_exact(&evidence->system_cap) ||\n",
            "")),
        ("allow-mitigations-off", lambda r: replace(
            r / PROFILE,
            "mt6797_a72_policy_evidence_exact(\n"
            "\tconst struct arm64_late_cpu_target_policy_evidence *policy)\n"
            "{\n"
            "\treturn policy->valid == ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK &&\n"
            "\t       policy->smccc_conduit == ARM64_LATE_CPU_SMCCC_SMC &&\n"
            "\t       !policy->mitigations_off && !policy->nospectre_v2 &&\n",
            "mt6797_a72_policy_evidence_exact(\n"
            "\tconst struct arm64_late_cpu_target_policy_evidence *policy)\n"
            "{\n"
            "\treturn policy->valid == ARM64_LATE_CPU_TARGET_POLICY_VALID_MASK &&\n"
            "\t       policy->smccc_conduit == ARM64_LATE_CPU_SMCCC_SMC &&\n"
            "\t       !policy->nospectre_v2 &&\n")),
        ("remove-policy-equality", lambda r: replace(
            r / PROFILE,
            "\treturn !memcmp(&evidence->target_policy[0],\n"
            "\t\t       &evidence->target_policy[1],\n"
            "\t\t       sizeof(evidence->target_policy[0]));\n",
            "\treturn true;\n")),
        ("restore-unresolved-spectre", lambda r: replace(
            r / PROFILE,
            "static const u16 mt6797_a72_present_caps[] __initconst = {\n"
            "\tARM64_HAS_AMU_EXTN,\n"
            "\tARM64_HW_DBM,\n"
            "\tARM64_MISMATCHED_CACHE_TYPE,\n"
            "\tARM64_SPECTRE_V2,\n"
            "\tARM64_SPECTRE_V4,",
            "static const u16 mt6797_a72_present_caps[] __initconst = {\n"
            "\tARM64_HAS_AMU_EXTN,\n"
            "\tARM64_HW_DBM,\n"
            "\tARM64_MISMATCHED_CACHE_TYPE,\n"
            "\tARM64_SPECTRE_V4,")),
        ("keep-planner-dormant", lambda r: replace(
            r / PROFILE,
            "#else\n"
            "\tif (!plan->local_caps_planned || !plan->effects_planned ||\n",
            "#else\n"
            "\tif (plan->local_caps_planned || !plan->effects_planned ||\n")),
        ("accept-empty-effects", lambda r: replace(
            r / PROFILE, "\t    mt6797_a72_effects_empty(&plan->effects) ||\n",
            "")),
        ("return-eagain", lambda r: replace(
            r / PROFILE,
            "\t/* The core owns canonical identities after this pure validation. */\n"
            "\treturn 0;\n",
            "\t/* The core owns canonical identities after this pure validation. */\n"
            "\treturn -EAGAIN;\n")),
        ("freeze-after-blocker", lambda r: replace(
            r / PROFILE,
            "#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
            "\tevidence->expected_pair = mt6797_a72_expected_pair;\n"
            "#endif\n"
            "\tevidence->blocker_mask = MT6797_A72_PROFILE_BLOCKERS;",
            "\tevidence->blocker_mask = MT6797_A72_PROFILE_BLOCKERS;\n"
            "#ifndef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE\n"
            "\tevidence->expected_pair = mt6797_a72_expected_pair;\n"
            "#endif")),
        ("publish-ready", lambda r: replace(
            r / PROFILE, "\t.prepare = mt6797_a72_profile_prepare,\n",
            "\t.prepare = mt6797_a72_profile_prepare,\n"
            "\t.finalize_user = mt6797_a72_profile_prepare, /* READY */\n")),
        ("add-cpu8-request", lambda r: replace(
            r / PROFILE,
            "\t/* No live system capability, alternative, vector, or HWCAP is changed. */\n",
            "\tcpu_up(8);\n"
            "\t/* No live system capability, alternative, vector, or HWCAP is changed. */\n")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    rejected = 0

    for name, mutate in mutations():
        with tempfile.TemporaryDirectory(prefix=f"a72-activation-{name}-") as tmp:
            root = Path(tmp)
            prepare(source_root, root)
            mutate(root)
            try:
                validate(root)
            except (OSError, ValueError, IndexError, ValidationError):
                rejected += 1
                continue
            raise SystemExit(f"unsafe mutation passed validation: {name}")

    print(f"rejected_mutations={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
