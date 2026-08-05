#!/usr/bin/env python3
"""Require ABI-5 fixture, source, and independent-oracle mutations to fail."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from dataclasses import replace as dataclass_replace
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
VALIDATOR_PATH = HERE / "validate.py"
SPEC = importlib.util.spec_from_file_location("a41_six_row_validate", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load six-row validator")
VALIDATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATE
SPEC.loader.exec_module(VALIDATE)


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise RuntimeError(f"mutation source is missing in {path.name}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def replace_all(path: Path, old: str, new: str, minimum: int = 1) -> None:
    text = path.read_text()
    if text.count(old) < minimum:
        raise RuntimeError(f"mutation sources are missing in {path.name}: {old!r}")
    path.write_text(text.replace(old, new))


def copy_repository_inputs(source: Path, target: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for directory in ("configs", "docs", "kernel", "patches"):
        shutil.copytree(source / directory, target / directory, ignore=ignore)
    child = target / VALIDATE.EXPERIMENT
    child.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / VALIDATE.EXPERIMENT, child, ignore=ignore)
    parent = target / VALIDATE.PARENT_VALIDATOR
    parent.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / VALIDATE.PARENT_VALIDATOR, parent)


def copy_source_inputs(source: Path, target: Path) -> None:
    for relative in VALIDATE.CHANGED_PATHS:
        source_path = source / relative
        target_path = target / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def expect_repository_failure(root: Path, mutation) -> None:
    mutation(root)
    try:
        VALIDATE.validate_repository(
            root, pin_hashes=False, skip_frozen_evidence=True
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
        return
    raise RuntimeError(f"unsafe repository mutation passed: {mutation.__name__}")


def expect_source_failure(root: Path, mutation, repo: Path) -> None:
    mutation(root)
    try:
        VALIDATE.validate_source_files(root, repo=repo)
    except (OSError, ValueError, RuntimeError):
        return
    raise RuntimeError(f"unsafe source mutation passed: {mutation.__name__}")


def mutate_manifest_profile_count(root: Path) -> None:
    path = root / VALIDATE.MANIFEST
    data = json.loads(path.read_text())
    del data["config"]["profiles"][VALIDATE.PROFILE]
    path.write_text(json.dumps(data, indent=2) + "\n")


def mutate_manifest_profile_series(root: Path) -> None:
    path = root / VALIDATE.MANIFEST
    data = json.loads(path.read_text())
    data["config"]["profiles"][VALIDATE.PROFILE]["patch_series"] = str(
        VALIDATE.PARENT_SERIES
    )
    path.write_text(json.dumps(data, indent=2) + "\n")


def mutate_manifest_profile_leak(root: Path) -> None:
    path = root / VALIDATE.MANIFEST
    data = json.loads(path.read_text())
    other = next(name for name in data["config"]["profiles"] if name != VALIDATE.PROFILE)
    data["config"]["profiles"][other]["patch_series"] = str(VALIDATE.SERIES)
    path.write_text(json.dumps(data, indent=2) + "\n")


def mutate_profile_fragment_setting(root: Path) -> None:
    replace_once(root / VALIDATE.FRAGMENT, "fixture-blocked", "fixture-open")


def mutate_selected_series_duplicate(root: Path) -> None:
    path = root / VALIDATE.SERIES
    tail = path.read_text().splitlines()[-1]
    path.write_text(path.read_text() + tail + "\n")


def mutate_selected_series_parent(root: Path) -> None:
    replace_once(root / VALIDATE.SERIES, "v7.1.3/0153-", "v7.1.3/0152-")


def mutate_canonical_series_order(root: Path) -> None:
    path = root / VALIDATE.CANONICAL_SERIES
    lines = path.read_text().splitlines()
    first = next(index for index, line in enumerate(lines) if "0153-" in line)
    second = next(index for index, line in enumerate(lines) if "0154-" in line)
    lines[first], lines[second] = lines[second], lines[first]
    path.write_text("\n".join(lines) + "\n")


def mutate_patch_source_commit(root: Path) -> None:
    replace_once(root / VALIDATE.PATCH, VALIDATE.SOURCE, "0" * 40)


def mutate_patch_author(root: Path) -> None:
    replace_once(root / VALIDATE.PATCH, "Gemini Mainline Project", "Unknown Author")


def mutate_patch_signoff(root: Path) -> None:
    replace_once(
        root / VALIDATE.PATCH,
        "submission-ready.\n",
        "submission-ready.\nSigned-off-by: X <x@invalid>\n",
    )


def mutate_fixture_census_state(root: Path) -> None:
    path = root / VALIDATE.EXPERIMENT / "results/six-row-fixture.tsv"
    replace_once(path, "\tPRESENT\tPRESENT\tPRESENT\t", "\tABSENT\tPRESENT\tPRESENT\t")


def mutate_fixture_census_required(root: Path) -> None:
    path = root / VALIDATE.EXPERIMENT / "results/six-row-fixture.tsv"
    replace_once(path, "\tyes\t", "\tno\t")


def mutate_implementation_claim(root: Path) -> None:
    path = root / VALIDATE.EXPERIMENT / "results/implementation.tsv"
    replace_once(path, "PARTIAL_SIX_ROW_FIXTURE_EVALUATOR", "COMPLETE")


def mutate_external_action(root: Path) -> None:
    path = root / VALIDATE.EXPERIMENT / "scripts/validate.py"
    path.write_text(path.read_text() + "\n# s" + "sh\n")


REPOSITORY_CASES = (
    mutate_manifest_profile_count,
    mutate_manifest_profile_series,
    mutate_manifest_profile_leak,
    mutate_profile_fragment_setting,
    mutate_selected_series_duplicate,
    mutate_selected_series_parent,
    mutate_canonical_series_order,
    mutate_patch_source_commit,
    mutate_patch_author,
    mutate_patch_signoff,
    mutate_fixture_census_state,
    mutate_fixture_census_required,
    mutate_implementation_claim,
    mutate_external_action,
)


def kernel_path(root: Path, name: str) -> Path:
    return root / "arch/arm64/kernel" / name


def source_commit_path_core(root: Path) -> None:
    replace_once(
        kernel_path(root, "late_cpu_profile.c"),
        "draft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_COMMIT_PATH;",
        "draft.evidence.blocker_mask |= 0;",
    )


def source_commit_path_profile(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        " ARM64_LATE_CPU_BLOCK_COMMIT_PATH)",
        " 0)",
    )


def source_commit_path_paired(root: Path) -> None:
    source_commit_path_core(root)
    source_commit_path_profile(root)


def source_fixture_runtime_origin(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "evidence->binding.origin = ARM64_LATE_CPU_BINDING_FIXTURE;",
        "evidence->binding.origin = ARM64_LATE_CPU_BINDING_RUNTIME;",
    )


def source_profile_early_success(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "mt6797_a72_validate_cap_plan(const struct arm64_late_cpu_plan *plan)\n{\n",
        "mt6797_a72_validate_cap_plan(const struct arm64_late_cpu_plan *plan)\n"
        "{\n\treturn 0;\n",
    )


def source_prepare_early_success(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "mt6797_a72_profile_prepare(struct arm64_late_cpu_evidence *evidence,\n"
        "\t\t\t   const struct cpumask *registered_targets)\n{\n",
        "mt6797_a72_profile_prepare(struct arm64_late_cpu_evidence *evidence,\n"
        "\t\t\t   const struct cpumask *registered_targets)\n"
        "{\n\treturn 0;\n",
    )


def source_identity_injection(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "/* Source-only fixture/expected evidence never publishes an identity. */",
        "plan->identity[0] = 1;",
    )


def source_boot_veto(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "return -EAGAIN;\n}\n\n#ifdef CONFIG_HOTPLUG_CPU",
        "return cpu_psci_ops.cpu_boot(cpu);\n}\n\n#ifdef CONFIG_HOTPLUG_CPU",
    )


def source_disable_veto(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n\treturn false;",
        "mt6797_psci_cpu_can_disable(unsigned int cpu)\n{\n\treturn true;",
    )


def source_classifier_target_collapse(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "&evidence->target_cap[target]",
        "&evidence->target_cap[0]",
    )


def source_v2_effect_target_collapse(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "&plan->evidence.target_cap[target],\n"
        "\t\t\t&plan->evidence.target_policy[target],\n"
        "\t\t\t&effects->target[target]);",
        "&plan->evidence.target_cap[0],\n"
        "\t\t\t&plan->evidence.target_policy[0],\n"
        "\t\t\t&effects->target[0]);",
    )


def source_bhb_effect_target_collapse(root: Path) -> None:
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "&plan->evidence.target_cap[target],\n"
        "\t\t\t&plan->evidence.target_policy[target], system_v2_state,\n"
        "\t\t\t&effects->target[target]);",
        "&plan->evidence.target_cap[0],\n"
        "\t\t\t&plan->evidence.target_policy[0], system_v2_state,\n"
        "\t\t\t&effects->target[0]);",
    )


def source_paired_ctr_producer_expectation(root: Path) -> None:
    path = kernel_path(root, "mt6797_psci.c")
    replace_all(path, "0x83338003", "0x83338007", 2)
    replace_all(path, "0x93338003", "0x93338007", 2)


def source_paired_v2_hyp_producer_expectation(root: Path) -> None:
    replace_once(
        kernel_path(root, "proton-pack.c"),
        "effects->spectre_v2_hyp_vector =\n"
        "\t\t\tARM64_LATE_CPU_HYP_VECTOR_SPECTRE_DIRECT;",
        "effects->spectre_v2_hyp_vector =\n"
        "\t\t\tARM64_LATE_CPU_HYP_VECTOR_DIRECT;",
    )
    replace_once(
        kernel_path(root, "mt6797_psci.c"),
        "effect->spectre_v2_hyp_vector ==\n"
        "\t\t       ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_DIRECT",
        "effect->spectre_v2_hyp_vector ==\n"
        "\t\t       ARM64_LATE_CPU_HYP_VECTOR_DIRECT",
    )
    path = kernel_path(root, "mt6797_psci.c")
    replace_once(
        path,
        "effect->bhb_hyp_vector ==\n"
        "\t\t       ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_DIRECT",
        "effect->bhb_hyp_vector ==\n"
        "\t\t       ARM64_LATE_CPU_HYP_VECTOR_INDIRECT",
    )
    replace_once(
        path,
        "effects->spectre_v2.hyp_vector !=\n"
        "\t\t    ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_DIRECT",
        "effects->spectre_v2.hyp_vector !=\n"
        "\t\t    ARM64_LATE_CPU_HYP_VECTOR_DIRECT",
    )
    replace_once(
        path,
        "effects->bhb.hyp_vector !=\n"
        "\t\t    ARM64_LATE_CPU_HYP_VECTOR_SPECTRE_DIRECT",
        "effects->bhb.hyp_vector !=\n"
        "\t\t    ARM64_LATE_CPU_HYP_VECTOR_INDIRECT",
    )


def source_paired_bhb_loop_producer_expectation(root: Path) -> None:
    proton = kernel_path(root, "proton-pack.c")
    replace_once(proton, "effects->bhb_matcher_loop_count = 8;",
                 "effects->bhb_matcher_loop_count = 11;")
    replace_once(proton, "Exact Cortex-A72 priority selects the k=8 loop before WA3",
                 "Exact Cortex-A72 priority selects the k=11 loop before WA3")
    replace_once(proton, "effects->bhb_loop_count = 8;",
                 "effects->bhb_loop_count = 11;")
    path = kernel_path(root, "mt6797_psci.c")
    replace_once(path, "effect->bhb_loop_count == 8", "effect->bhb_loop_count == 11")
    replace_once(path, "effect->bhb_matcher_loop_count == 8",
                 "effect->bhb_matcher_loop_count == 11")
    replace_once(path, "effects->bhb.loop_count != 8", "effects->bhb.loop_count != 11")
    replace_once(path, "effects->bhb.matcher_loop_count != 8",
                 "effects->bhb.matcher_loop_count != 11")


SOURCE_CASES = (
    source_commit_path_core,
    source_commit_path_profile,
    source_commit_path_paired,
    source_fixture_runtime_origin,
    source_profile_early_success,
    source_prepare_early_success,
    source_identity_injection,
    source_boot_veto,
    source_disable_veto,
    source_classifier_target_collapse,
    source_v2_effect_target_collapse,
    source_bhb_effect_target_collapse,
    source_paired_ctr_producer_expectation,
    source_paired_v2_hyp_producer_expectation,
    source_paired_bhb_loop_producer_expectation,
)


def rejected(action) -> bool:
    try:
        action()
    except VALIDATE.OracleRejected:
        return True
    return False


def oracle_cases() -> tuple[tuple[str, bool], ...]:
    t = VALIDATE.FIXTURE_TARGETS[0]
    p = VALIDATE.FIXTURE_POLICIES[0]
    s = VALIDATE.FIXTURE_SYSTEM
    legacy = dataclass_replace(t, pfr2=1 << 12, icc_idr0=1 << 8)
    direct = dataclass_replace(
        t, pfr0=1 << 24, icc_sre=1, gic_sre_usable=1,
        kernel_in_hyp=1, ich_source=VALIDATE.ICH_DIRECT,
        ich_vtr=VALIDATE.ICH_TDS,
    )
    hvc = dataclass_replace(direct, kernel_in_hyp=0, ich_source=VALIDATE.ICH_HVC)
    base = {"spectre_v2_hyp_vector": VALIDATE.HYP_SPECTRE_DIRECT}
    ctr_absent, _ = VALIDATE.derive_fixture_effects(
        system=dataclass_replace(s, ctr_sys=t.ctr)
    )
    v2_absent_target = dataclass_replace(t, wa1=VALIDATE.SMCCC_UNAFFECTED)
    v2_absent, _ = VALIDATE.derive_fixture_effects(
        targets=(v2_absent_target, v2_absent_target)
    )
    v4_absent_target = dataclass_replace(t, wa2=VALIDATE.SMCCC_NOT_REQUIRED)
    v4_absent, _ = VALIDATE.derive_fixture_effects(
        targets=(v4_absent_target, v4_absent_target)
    )
    bhb_absent_target = dataclass_replace(t, pfr0=3 << 56)
    bhb_absent, _ = VALIDATE.derive_fixture_effects(
        targets=(bhb_absent_target, bhb_absent_target)
    )
    cases = (
        ("oracle-gic-valid", VALIDATE.classify_gic(dataclass_replace(t, valid=t.valid & ~VALIDATE.GIC_VALID)) == VALIDATE.UNRESOLVED),
        ("oracle-gic-gcie", VALIDATE.classify_gic(dataclass_replace(legacy, pfr2=2 << 12)) == VALIDATE.UNRESOLVED),
        ("oracle-gic-legacy", VALIDATE.classify_gic(legacy) == VALIDATE.PRESENT),
        ("oracle-gic-sre-crosscheck", VALIDATE.classify_gic(dataclass_replace(t, gic_sre_usable=1)) == VALIDATE.UNRESOLVED),
        ("oracle-gic-result", VALIDATE.classify_gic(t, descriptor=False) == VALIDATE.UNRESOLVED),
        ("oracle-ich-hyp-valid", VALIDATE.classify_ich(dataclass_replace(t, valid=t.valid & ~VALIDATE.HYP_VALID)) == VALIDATE.UNRESOLVED),
        ("oracle-ich-none-payload", VALIDATE.classify_ich(dataclass_replace(t, ich_vtr=1)) == VALIDATE.UNRESOLVED),
        ("oracle-ich-direct-privilege", VALIDATE.classify_ich(dataclass_replace(direct, kernel_in_hyp=0)) == VALIDATE.UNRESOLVED),
        ("oracle-ich-direct-status", VALIDATE.classify_ich(dataclass_replace(direct, ich_status=-1)) == VALIDATE.UNRESOLVED),
        ("oracle-ich-direct-tds", VALIDATE.classify_ich(direct) == VALIDATE.PRESENT and VALIDATE.classify_ich(dataclass_replace(direct, ich_vtr=0)) == VALIDATE.ABSENT),
        ("oracle-ich-hvc-privilege", VALIDATE.classify_ich(dataclass_replace(hvc, kernel_in_hyp=1)) == VALIDATE.UNRESOLVED),
        ("oracle-ich-hvc-status", VALIDATE.classify_ich(dataclass_replace(hvc, ich_status=-7)) == VALIDATE.UNRESOLVED),
        ("oracle-ich-hvc-tds", VALIDATE.classify_ich(hvc) == VALIDATE.PRESENT and VALIDATE.classify_ich(dataclass_replace(hvc, ich_vtr=0)) == VALIDATE.ABSENT),
        ("oracle-ich-result", VALIDATE.classify_ich(t, descriptor=False) == VALIDATE.UNRESOLVED),
        ("oracle-ctr-valid", VALIDATE.classify_ctr(dataclass_replace(t, valid=t.valid & ~VALIDATE.CTR_VALID), s) == VALIDATE.UNRESOLVED),
        ("oracle-ctr-raw", VALIDATE.classify_ctr(dataclass_replace(t, ctr=t.ctr & ~VALIDATE.CTR_RES1, ctr_effective=t.ctr_effective & ~VALIDATE.CTR_RES1), s) == VALIDATE.UNRESOLVED),
        ("oracle-ctr-effective", VALIDATE.classify_ctr(dataclass_replace(t, ctr_effective=t.ctr), s) == VALIDATE.UNRESOLVED),
        ("oracle-ctr-system", VALIDATE.classify_ctr(t, dataclass_replace(s, ctr_sys=t.ctr)) == VALIDATE.ABSENT and not ctr_absent["ctr_mismatch.required"] and not ctr_absent["ctr_mismatch.target_mask"]),
        ("oracle-ctr-mask", VALIDATE.classify_ctr(t, dataclass_replace(s, ctr_strict_mask=s.ctr_strict_mask ^ 1)) == VALIDATE.UNRESOLVED),
        ("oracle-ctr-clidr", VALIDATE.classify_ctr(dataclass_replace(t, clidr=(1 << 24) | (1 << 21)), s) == VALIDATE.UNRESOLVED),
        ("oracle-ctr-result", VALIDATE.classify_ctr(t, s, descriptor=False) == VALIDATE.UNRESOLVED),
        ("oracle-v2-target-shape", VALIDATE.classify_v2(dataclass_replace(t, midr=0)) == VALIDATE.UNRESOLVED),
        ("oracle-v2-csv2", VALIDATE.classify_v2(dataclass_replace(t, pfr0=1 << 56)) == VALIDATE.ABSENT),
        ("oracle-v2-wa1-valid", VALIDATE.classify_v2(dataclass_replace(t, valid=t.valid & ~VALIDATE.WA1_VALID)) == VALIDATE.UNRESOLVED),
        ("oracle-v2-wa1-status", VALIDATE.classify_v2(dataclass_replace(t, wa1=-9)) == VALIDATE.UNRESOLVED),
        ("oracle-v2-hyp-vector", VALIDATE.evaluate_v2(dataclass_replace(t, hyp_available=0), p)["spectre_v2_hyp_vector"] == VALIDATE.HYP_DIRECT),
        ("oracle-v2-result", VALIDATE.classify_v2(t, descriptor=False) == VALIDATE.UNRESOLVED and not v2_absent["spectre_v2.required"] and not v2_absent["spectre_v2.target_mask"]),
        ("oracle-v4-target-shape", VALIDATE.classify_v4(dataclass_replace(t, midr=0)) == VALIDATE.UNRESOLVED),
        ("oracle-v4-ssbs", VALIDATE.evaluate_v4(dataclass_replace(t, pfr1=1 << 4), p)["spectre_v4_method"] == VALIDATE.V4_SSBS),
        ("oracle-v4-wa2-valid", VALIDATE.classify_v4(dataclass_replace(t, valid=t.valid & ~VALIDATE.WA2_VALID)) == VALIDATE.UNRESOLVED),
        ("oracle-v4-wa2-status", VALIDATE.classify_v4(dataclass_replace(t, wa2=-9)) == VALIDATE.UNRESOLVED),
        ("oracle-v4-alternative-gap", rejected(lambda: VALIDATE.evaluate_v4(dataclass_replace(t, pfr1=1 << 4), dataclass_replace(p, v4_policy=VALIDATE.V4_FORCE_OFF)))),
        ("oracle-v4-result", VALIDATE.classify_v4(t, descriptor=False) == VALIDATE.UNRESOLVED and not v4_absent["spectre_v4.required"] and not v4_absent["spectre_v4.target_mask"]),
        ("oracle-bhb-csv2", VALIDATE.classify_bhb(dataclass_replace(t, pfr0=3 << 56)) == VALIDATE.ABSENT),
        ("oracle-bhb-clearbhb", VALIDATE.evaluate_bhb(dataclass_replace(t, isar2=1 << 28), p, VALIDATE.MITIGATION_MITIGATED, base)["bhb_method"] == VALIDATE.BHB_INSTRUCTION),
        ("oracle-bhb-ecbhb", VALIDATE.evaluate_bhb(dataclass_replace(t, mmfr1=1 << 60), p, VALIDATE.MITIGATION_MITIGATED, base)["bhb_method"] == VALIDATE.BHB_HARDWARE),
        ("oracle-bhb-system-v2", VALIDATE.evaluate_bhb(t, p, VALIDATE.MITIGATION_VULNERABLE, base)["bhb_mitigation_state"] == VALIDATE.BHB_STATE_VULNERABLE),
        ("oracle-bhb-loop8", VALIDATE.evaluate_bhb(t, p, VALIDATE.MITIGATION_MITIGATED, base)["bhb_loop_count"] == 8),
        ("oracle-bhb-result", VALIDATE.classify_bhb(t, descriptor=False) == VALIDATE.UNRESOLVED and not bhb_absent["bhb.required"] and not bhb_absent["bhb.target_mask"]),
        ("oracle-asymmetric-classifier-index", VALIDATE.classify_six_rows(t) != VALIDATE.classify_six_rows(legacy)),
        ("oracle-asymmetric-v2-effect-index", rejected(lambda: VALIDATE.derive_fixture_effects((t, dataclass_replace(t, wa1=VALIDATE.SMCCC_NOT_SUPPORTED))))),
        ("oracle-asymmetric-v4-effect-index", rejected(lambda: VALIDATE.derive_fixture_effects((t, dataclass_replace(t, wa2=VALIDATE.SMCCC_NOT_SUPPORTED))))),
        ("oracle-asymmetric-bhb-effect-index", rejected(lambda: VALIDATE.derive_fixture_effects((t, dataclass_replace(t, isar2=1 << 28))))),
    )
    return cases


def run_typed_effect_mutations(root: Path) -> list[str]:
    path = root / VALIDATE.EXPERIMENT / "results/typed-effects.tsv"
    original = path.read_text()
    lines = original.splitlines()
    passed = []
    for index, name in enumerate(VALIDATE.TYPED_EFFECT_MUTATIONS, start=1):
        fields = lines[index].split("\t")
        fields[2] = "MUTATED"
        mutated = list(lines)
        mutated[index] = "\t".join(fields)
        path.write_text("\n".join(mutated) + "\n")
        try:
            VALIDATE.validate_tables(root)
        except (OSError, ValueError, RuntimeError):
            passed.append(name)
        else:
            raise RuntimeError(f"typed-effect mutation passed: {name}")
        finally:
            path.write_text(original)
    return passed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", "--repo-root", dest="repo", type=Path,
                        default=VALIDATE.default_repo())
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    source = args.source_root.resolve()
    if VALIDATE.run_git(source, ["rev-parse", "HEAD"]).strip() != VALIDATE.SOURCE:
        raise RuntimeError("source checkout is not at the pinned commit")

    print("validation=a41-six-row-fixture-mutations")
    passed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="gemini-a41-six-row-baseline-") as temporary:
        root = Path(temporary)
        copy_repository_inputs(repo, root)
        VALIDATE.validate_repository(
            root, pin_hashes=False, skip_frozen_evidence=True
        )
    with tempfile.TemporaryDirectory(prefix="gemini-a41-six-row-source-baseline-") as temporary:
        root = Path(temporary)
        copy_source_inputs(source, root)
        VALIDATE.validate_source_files(root, repo=repo)
    for mutation, name in zip(REPOSITORY_CASES, VALIDATE.REPOSITORY_MUTATIONS):
        with tempfile.TemporaryDirectory(prefix="gemini-a41-six-row-repo-") as temporary:
            root = Path(temporary)
            copy_repository_inputs(repo, root)
            expect_repository_failure(root, mutation)
        passed.append(name)
        print(f"PASS {name}")
    for mutation, name in zip(SOURCE_CASES, VALIDATE.SOURCE_MUTATIONS):
        with tempfile.TemporaryDirectory(prefix="gemini-a41-six-row-source-") as temporary:
            root = Path(temporary)
            copy_source_inputs(source, root)
            expect_source_failure(root, mutation, repo)
        passed.append(name)
        print(f"PASS {name}")
    for name, outcome in oracle_cases():
        if not outcome:
            raise RuntimeError(f"independent oracle mutation failed: {name}")
        passed.append(name)
        print(f"PASS {name}")
    with tempfile.TemporaryDirectory(prefix="gemini-a41-six-row-effects-") as temporary:
        root = Path(temporary)
        copy_repository_inputs(repo, root)
        for name in run_typed_effect_mutations(root):
            passed.append(name)
            print(f"PASS {name}")
    if tuple(passed) != VALIDATE.MUTATION_NAMES:
        raise RuntimeError("mutation inventory changed")
    print("network_accessed=no")
    print("build_invoked=no")
    print("device_accessed=no")
    print(f"RESULT PASS {len(passed)}/{len(VALIDATE.MUTATION_NAMES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
