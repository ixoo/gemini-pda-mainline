#!/usr/bin/env python3
"""Require decision-changing A41 planner mutations to fail validation."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("a41_planner_validate", SCRIPT_DIR / "validate.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load A41 planner validator")
VALIDATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATE
SPEC.loader.exec_module(VALIDATE)

REPO = SCRIPT_DIR.parents[2]
EXPECTED_MUTATION_COUNT = 69
SOURCE_FIXTURE_REL = Path("bounded-source-fixture")
CPU_ERRATA_FIXTURE = """
static const struct arm64_cpu_capabilities erratum_843419_list[] = {
    { .matches = is_affected_midr_range, },
    {},
};
static const struct arm64_cpu_capabilities qcom_erratum_1003_list[] = {
    { .matches = is_affected_midr_range, },
    {},
};
static const struct arm64_cpu_capabilities arm64_repeat_tlbi_list[] = {
    { .matches = is_affected_midr_range, },
    {},
};
static const struct midr_range erratum_speculative_at_list[] = {
    MIDR_ALL_VERSIONS(MIDR_CORTEX_A72),
    {},
};
static struct midr_range broken_aarch32_aes[] = {
    MIDR_ALL_VERSIONS(MIDR_CORTEX_A72),
    {},
};
const struct arm64_cpu_capabilities arm64_errata[] = {
    {
        .capability = ARM64_WORKAROUND_843419,
        .matches = cpucap_multi_entry_cap_matches,
        .match_list = erratum_843419_list,
    },
    {
        .capability = ARM64_WORKAROUND_QCOM_FALKOR_E1003,
        .matches = cpucap_multi_entry_cap_matches,
        .match_list = qcom_erratum_1003_list,
    },
    {
        .capability = ARM64_WORKAROUND_REPEAT_TLBI,
        .matches = cpucap_multi_entry_cap_matches,
        .match_list = arm64_repeat_tlbi_list,
    },
    {
        .capability = ARM64_WORKAROUND_SPECULATIVE_AT,
        ERRATA_MIDR_RANGE_LIST(erratum_speculative_at_list),
    },
    {
        .capability = ARM64_WORKAROUND_1742098,
        CAP_MIDR_RANGE_LIST(broken_aarch32_aes),
    },
    {},
};
""".lstrip()
CPUFEATURE_FIXTURE = """
static const struct arm64_cpu_capabilities arm64_features[] = {
    { .capability = ARM64_ALWAYS_SYSTEM, .matches = has_always, },
    {
        .capability = ARM64_HAS_NESTED_VIRT,
        .type = ARM64_CPUCAP_SYSTEM_FEATURE,
        .matches = has_nested_virt_support,
        .match_list = (const struct arm64_cpu_capabilities []){
            { .matches = has_cpuid_feature, },
            { .matches = has_cpuid_feature, },
            {},
        },
    },
    {},
};
""".lstrip()


class MutationFailure(RuntimeError):
    """The mutation harness itself or a negative test failed."""


@dataclass(frozen=True)
class Mutation:
    name: str
    expected_error: str
    apply: Callable[[Path], None]
    mode: str = "repository"


def replace(
    root: Path,
    relative: Path | str,
    old: str,
    new: str,
    *,
    count: int = 1,
) -> None:
    path = root / relative
    text = path.read_text()
    actual = text.count(old)
    if actual != count:
        raise MutationFailure(
            "{}: expected {} occurrence(s), found {}".format(relative, count, actual)
        )
    path.write_text(text.replace(old, new, count))


def replace_nth(
    root: Path,
    relative: Path | str,
    old: str,
    new: str,
    occurrence: int,
    *,
    total: int,
) -> None:
    path = root / relative
    text = path.read_text()
    if text.count(old) != total:
        raise MutationFailure(
            "{}: expected {} occurrence(s) of nth target".format(relative, total)
        )
    start = -1
    for _ in range(occurrence):
        start = text.find(old, start + 1)
    if start < 0:
        raise MutationFailure("{}: nth target is missing".format(relative))
    path.write_text(text[:start] + new + text[start + len(old) :])


def append(root: Path, relative: Path | str, text: str) -> None:
    path = root / relative
    path.write_text(path.read_text() + text)


def keep_first_line(root: Path, relative: Path | str) -> None:
    path = root / relative
    lines = path.read_text().splitlines()
    if not lines:
        raise MutationFailure("{}: cannot truncate an empty file".format(relative))
    path.write_text(lines[0] + "\n")


def mutate_manifest(root: Path, callback: Callable[[dict], None]) -> None:
    path = root / VALIDATE.MANIFEST
    manifest = json.loads(path.read_text())
    callback(manifest)
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def write_fixture_transcripts(root: Path) -> None:
    experiment = root / VALIDATE.EXPERIMENT_REL
    validator = experiment / "scripts/validate.py"
    suite = experiment / "scripts/test_mutations.py"
    offline_lines = [
        "PASS bounded-new-files",
        "PASS experiment-record",
        "PASS patch-identities",
        "PASS manifest-series",
        "PASS planner-source-contract",
        "PASS offline-boundary",
        "PASS sequential-source-application",
        "patch_0150_sha256=" + VALIDATE.EXPECTED_PATCH_SHA256[VALIDATE.PATCH_0150],
        "planner_series_sha256=" + VALIDATE.EXPECTED_PLANNER_SERIES_SHA256,
        "planner_patchset_sha256=" + VALIDATE.EXPECTED_PATCHSET_SHA256,
        "planner_source_state_sha256=" + VALIDATE.EXPECTED_SOURCE_STATE_SHA256,
        "source_parent_sha256=" + VALIDATE.EXPECTED_SOURCE_PARENT_SHA256,
        "config_inputs_sha256=" + VALIDATE.EXPECTED_CONFIG_INPUT_SHA256,
        "source_base_commit=" + VALIDATE.EXPECTED_BASE_COMMIT,
        "planner_source_commit=" + VALIDATE.EXPECTED_PATCH_COMMITS[VALIDATE.PATCH_0150],
        "planner_source_tree=" + VALIDATE.EXPECTED_PLANNER_SOURCE_TREE,
        "validator_sha256=" + VALIDATE.sha256_file(validator),
        "python_version=0.0.0",
        "git_version=git version fixture",
        "implementation_state=PARTIAL_READ_ONLY_PLANNER",
        "a41_complete=no",
        "build_authorized=no",
        "device_action_authorized=no",
        "RESULT PASS 7/7",
    ]
    (experiment / "results/offline-validation-20260805.txt").write_text(
        "\n".join(offline_lines) + "\n"
    )

    names = [case.name for case in mutations()]
    if len(names) != EXPECTED_MUTATION_COUNT or len(names) != len(set(names)):
        raise MutationFailure("cannot synthesize transcript for an invalid case set")
    mutation_lines = [
        "PASS mutation {:02d} {}".format(index, name)
        for index, name in enumerate(names, 1)
    ]
    mutation_lines.extend(
        [
            "validator_sha256=" + VALIDATE.sha256_file(validator),
            "mutation_suite_sha256=" + VALIDATE.sha256_file(suite),
            "python_version=0.0.0",
            "baseline_static_checks=6",
            "mutation_count={}".format(EXPECTED_MUTATION_COUNT),
            "RESULT PASS {0}/{0}".format(EXPECTED_MUTATION_COUNT),
        ]
    )
    (experiment / "results/mutation-validation-20260805.txt").write_text(
        "\n".join(mutation_lines) + "\n"
    )


def copy_fixture(destination: Path) -> None:
    """Copy only the bounded repository inputs consumed by validate_repository."""

    shutil.copytree(REPO / "patches", destination / "patches")
    shutil.copytree(REPO / "configs", destination / "configs")
    experiment = REPO / VALIDATE.EXPERIMENT_REL
    shutil.copytree(
        experiment,
        destination / VALIDATE.EXPERIMENT_REL,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for relative in (VALIDATE.MANIFEST, Path("docs/ROADMAP.md")):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / relative, target)
    source_fixture = destination / SOURCE_FIXTURE_REL
    source_fixture.mkdir()
    (source_fixture / "cpu_errata.c").write_text(CPU_ERRATA_FIXTURE)
    (source_fixture / "cpufeature.c").write_text(CPUFEATURE_FIXTURE)
    write_fixture_transcripts(destination)


def validate_source_fixture(root: Path) -> None:
    source_fixture = root / SOURCE_FIXTURE_REL
    VALIDATE.validate_capability_source_tables(
        (source_fixture / "cpu_errata.c").read_text(),
        (source_fixture / "cpufeature.c").read_text(),
    )


def change_default_profile(root: Path) -> None:
    mutate_manifest(
        root,
        lambda manifest: manifest["config"].__setitem__(
            "default_profile", VALIDATE.PLANNER_PROFILE
        ),
    )


def leak_planner_fragment(root: Path) -> None:
    mutate_manifest(
        root,
        lambda manifest: manifest["config"]["profiles"]["full"]["fragments"].append(
            str(VALIDATE.PLANNER_FRAGMENT)
        ),
    )


def change_planner_series(root: Path) -> None:
    mutate_manifest(
        root,
        lambda manifest: manifest["config"]["profiles"][
            VALIDATE.PLANNER_PROFILE
        ].__setitem__("patch_series", str(VALIDATE.CANONICAL_SERIES)),
    )


def break_another_profile_series(root: Path) -> None:
    manifest = json.loads((root / VALIDATE.MANIFEST).read_text())
    fallback = manifest["patch_series"]
    for profile in manifest["config"]["profiles"].values():
        series = profile.get("patch_series", fallback)
        if series not in (str(VALIDATE.CANONICAL_SERIES), str(VALIDATE.PLANNER_SERIES)):
            path = root / series
            lines = path.read_text().splitlines()
            active = [index for index, line in enumerate(lines) if line and not line.startswith("#")]
            if len(active) < 2:
                continue
            first, second = active[0], active[1]
            lines[first], lines[second] = lines[second], lines[first]
            path.write_text("\n".join(lines) + "\n")
            return
    raise MutationFailure("no non-planner profile series was available")


def mutations() -> list[Mutation]:
    p92 = VALIDATE.PATCH_0092
    p149 = VALIDATE.PATCH_0149
    p150 = VALIDATE.PATCH_0150
    selected = VALIDATE.PLANNER_SERIES
    canonical = VALIDATE.CANONICAL_SERIES
    experiment = VALIDATE.EXPERIMENT_REL
    markers = experiment / "results/implementation.tsv"
    blockers = experiment / "results/blockers.tsv"
    effects = experiment / "results/effects.tsv"
    classes = experiment / "results/capability-classes.tsv"
    design = experiment / "DESIGN.md"
    test_script = experiment / "scripts/test_mutations.py"
    offline_result = experiment / "results/offline-validation-20260805.txt"
    mutation_result = experiment / "results/mutation-validation-20260805.txt"
    p148_name = str(VALIDATE.PATCH_0148.relative_to("patches"))
    p149_name = str(p149.relative_to("patches"))
    p150_name = str(p150.relative_to("patches"))

    return [
        Mutation(
            "patch_commit_identity",
            "0150 source commit changed",
            lambda root: replace(
                root,
                p150,
                VALIDATE.EXPECTED_PATCH_COMMITS[p150],
                "0" * 40,
            ),
        ),
        Mutation(
            "patch_subject",
            "0150 subject changed",
            lambda root: replace(root, p150, "capability planner", "capability committer"),
        ),
        Mutation(
            "synthetic_signoff",
            "0150 experiment patch gained a sign-off",
            lambda root: replace(
                root,
                p150,
                "This experiment-only change has no certifying sign-off",
                "Signed-off-by: Synthetic Author <noreply@invalid>\n\n"
                "This experiment-only change has no certifying sign-off",
            ),
        ),
        Mutation(
            "unexpected_patch_path",
            "0150 changed-path set differs",
            lambda root: append(
                root,
                p150,
                "\ndiff --git a/kernel/unsafe.c b/kernel/unsafe.c\n"
                "index 000000000..111111111 100644\n"
                "--- /dev/null\n+++ b/kernel/unsafe.c\n@@ -0,0 +1 @@\n+unsafe\n",
            ),
        ),
        Mutation(
            "patch_preimage",
            "0150 preimage changed for arch/arm64/kernel/cpufeature.c",
            lambda root: replace(root, p150, "index 6d53bb15c..", "index 000000000.."),
        ),
        Mutation(
            "selected_patch_order",
            "planner terminal patch order changed",
            lambda root: replace(
                root,
                selected,
                p149_name + "\n" + p150_name,
                p150_name + "\n" + p149_name,
            ),
        ),
        Mutation(
            "canonical_patch_order",
            "canonical planner patch order changed",
            lambda root: replace(
                root,
                canonical,
                p149_name + "\n" + p150_name,
                p150_name + "\n" + p149_name,
            ),
        ),
        Mutation(
            "selected_duplicate",
            "planner series contains duplicate patches",
            lambda root: append(root, selected, p150_name + "\n"),
        ),
        Mutation("selected_manifest_series", "planner series selection changed", change_planner_series),
        Mutation(
            "other_profile_subsequence",
            "is not a canonical subsequence",
            break_another_profile_series,
        ),
        Mutation("default_profile", "default profile changed", change_default_profile),
        Mutation("profile_fragment_leak", "planner fragment leaked into profile full", leak_planner_fragment),
        Mutation(
            "planner_fragment_extra",
            "planner fragment gained an unreviewed setting",
            lambda root: append(root, VALIDATE.PLANNER_FRAGMENT, "CONFIG_ARM64_PSEUDO_NMI=y\n"),
        ),
        Mutation(
            "config_input_identity",
            "planner configuration-input identity changed",
            lambda root: append(root, "configs/gemini-handoff.fragment", "# identity drift\n"),
        ),
        Mutation(
            "tri_state_order",
            "capability tri-state order",
            lambda root: replace(
                root,
                p150,
                "+\tARM64_LATE_CPU_CAP_ABSENT,\n+\tARM64_LATE_CPU_CAP_PRESENT,",
                "+\tARM64_LATE_CPU_CAP_PRESENT,\n+\tARM64_LATE_CPU_CAP_ABSENT,",
            ),
        ),
        Mutation(
            "effect_definition_bit",
            "effect definitions changed",
            lambda root: replace(
                root,
                p150,
                "ARM64_LATE_CPU_EFFECT_SPEC_AT_FINALIZATION\tBIT_ULL(7)",
                "ARM64_LATE_CPU_EFFECT_SPEC_AT_FINALIZATION\tBIT_ULL(8)",
            ),
        ),
        Mutation(
            "descriptor_slot_guard",
            "descriptor structure guard",
            lambda root: replace(root, p150, "cap->capability != slot", "cap->capability == slot"),
        ),
        Mutation(
            "descriptor_composite_type",
            "descriptor exact composite types changed",
            lambda root: replace(
                root,
                p150,
                "+\tcase ARM64_CPUCAP_STRICT_BOOT_CPU_FEATURE:\n",
                "",
            ),
        ),
        Mutation(
            "descriptor_match_callback_guard",
            "descriptor structure guard",
            lambda root: replace(
                root,
                p150,
                "+\t    !arm64_late_cpu_cap_uses_multi_entry_match(cap)",
                "+\t    false",
            ),
        ),
        Mutation(
            "multi_entry_callback_identity",
            "exact multi-entry callback guard",
            lambda root: replace(
                root,
                p150,
                "return cap->matches == cpucap_multi_entry_cap_matches;",
                "return cap->matches != cpucap_multi_entry_cap_matches;",
            ),
        ),
        Mutation(
            "descriptor_match_bound",
            "descriptor structure guard",
            lambda root: replace_nth(
                root,
                p150,
                "+\tfor (i = 0; i < ARM64_NCAPS; i++, match++) {",
                "+\tfor (i = 0; i <= ARM64_NCAPS; i++, match++) {",
                1,
                total=2,
            ),
        ),
        Mutation(
            "live_match_callback",
            "live target match callback added",
            lambda root: replace(
                root,
                p150,
                "member_state = profile->classify_local_cap(cap, match, draft);",
                "member_state = match->matches(match, SCOPE_LOCAL_CPU);",
            ),
        ),
        Mutation(
            "canonical_or_present",
            "tri-state fail-closed classification",
            lambda root: replace(root, p150, "present = true;", "present = false;"),
        ),
        Mutation(
            "planner_canonical_bound",
            "planner canonical traversal",
            lambda root: replace(
                root,
                p150,
                "+\tfor (i = 0; i < ARM64_NCAPS; i++) {",
                "+\tfor (i = 0; i <= ARM64_NCAPS; i++) {",
            ),
        ),
        Mutation(
            "planner_finalization_guard",
            "planner canonical traversal",
            lambda root: replace(root, p150, "system_capabilities_finalized() ||", "false ||"),
        ),
        Mutation(
            "planner_always_system_guard",
            "planner canonical traversal",
            lambda root: replace(root, p150, "cpus_have_cap(ARM64_ALWAYS_SYSTEM) ||", "false ||"),
        ),
        Mutation(
            "classification_completeness",
            "planner canonical traversal",
            lambda root: replace(
                root,
                p150,
                "!bitmap_equal(draft->compiled_local_caps,",
                "bitmap_equal(draft->compiled_local_caps,",
            ),
        ),
        Mutation(
            "conflict_veto",
            "planner canonical traversal",
            lambda root: replace(
                root,
                p150,
                "!bitmap_empty(draft->conflicting_local_caps, ARM64_NCAPS)",
                "bitmap_empty(draft->conflicting_local_caps, ARM64_NCAPS)",
                count=2,
            ),
        ),
        Mutation(
            "planner_completion_flag",
            "planner canonical traversal",
            lambda root: replace(root, p150, "draft->local_caps_planned = 1", "draft->local_caps_planned = 0"),
        ),
        Mutation(
            "planner_effect_mapping",
            "planner effect mapping changed",
            lambda root: replace(
                root,
                p150,
                "+\t\t\t\t\tARM64_LATE_CPU_EFFECT_BHB_V2_DEPENDENCY;",
                "+\t\t\t\t\tARM64_LATE_CPU_EFFECT_BHB_ALTERNATIVE;",
            ),
        ),
        Mutation(
            "required_capability_allowlist",
            "required capability allowlist changed",
            lambda root: replace_nth(
                root,
                p150,
                "+\t\t\tcase ARM64_WORKAROUND_SPECULATIVE_AT:\n",
                "",
                2,
                total=2,
            ),
        ),
        Mutation(
            "target_bhb_k",
            "exact MT6797 target classifier",
            lambda root: replace(
                root,
                p150,
                "+\t\t    attestation->bhb_loop_count != 8)",
                "+\t\t    attestation->bhb_loop_count != 7)",
            ),
        ),
        Mutation(
            "midr_range_bound",
            "bounded exact MIDR classifier",
            lambda root: replace(
                root,
                p150,
                "+\tfor (i = 0; i < ARM64_NCAPS; i++, range++) {",
                "+\tfor (i = 0; i <= ARM64_NCAPS; i++, range++) {",
            ),
        ),
        Mutation(
            "exact_expected_caps",
            "exact expected capability set changed",
            lambda root: replace(
                root,
                p150,
                "+\t\tARM64_WORKAROUND_SPECULATIVE_AT,\n",
                "",
            ),
        ),
        Mutation(
            "exact_expected_effects",
            "exact expected effect set changed",
            lambda root: replace(
                root,
                p150,
                "+\t\tARM64_LATE_CPU_EFFECT_COMPAT_AES_CLEAR |\n",
                "",
            ),
        ),
        Mutation(
            "core_inventory_ownership",
            "core CAP_INVENTORY ownership",
            lambda root: replace(
                root,
                p150,
                "draft.blocker_mask |= ARM64_LATE_CPU_BLOCK_CAP_INVENTORY",
                "draft.blocker_mask &= ~ARM64_LATE_CPU_BLOCK_CAP_INVENTORY",
            ),
        ),
        Mutation(
            "disable_veto",
            "0092 disable veto changed",
            lambda root: replace(root, p92, "+\treturn false;", "+\treturn true;"),
        ),
        Mutation(
            "selected_commit_callback",
            "selected profile gained a production commit callback",
            lambda root: replace(
                root,
                p150,
                " \t.prepare = mt6797_a72_profile_prepare,\n",
                " \t.prepare = mt6797_a72_profile_prepare,\n"
                "+\t.commit = mt6797_a72_profile_prepare,\n",
            ),
        ),
        Mutation(
            "live_capability_write",
            "live capability mutation added",
            lambda root: replace(
                root,
                p150,
                "+\t\t__set_bit(i, draft->canonical_caps);",
                "+\t\t__set_bit(i, draft->canonical_caps);\n"
                "+\t\t__set_bit(i, system_cpu" + "caps);",
            ),
        ),
        Mutation(
            "completion_claim",
            "implementation claim boundary changed",
            lambda root: replace(root, markers, "a41_complete\tno", "a41_complete\tyes"),
        ),
        Mutation(
            "blocker_owner",
            "blocker table changed",
            lambda root: replace(
                root,
                blockers,
                "3\tARM64_LATE_CPU_BLOCK_CAP_INVENTORY\tcore\tblocked",
                "3\tARM64_LATE_CPU_BLOCK_CAP_INVENTORY\tprofile\tblocked",
            ),
        ),
        Mutation(
            "capability_scope",
            "capability class table changed",
            lambda root: replace(
                root,
                classes,
                "all surviving non-null cpucap_ptrs",
                "selected cpucap_ptrs",
            ),
        ),
        Mutation(
            "document_claim_boundary",
            "experiment claim boundary",
            lambda root: replace(root, design, "No such commit exists in patch 0150", "A commit exists in patch 0150"),
        ),
        Mutation(
            "offline_boundary",
            "offline validator contains build/device action",
            lambda root: append(
                root,
                test_script,
                '\nsubprocess.run(["shut' + 'down"])\n',
            ),
        ),
        Mutation(
            "planner_early_success",
            "planner gained an early success path",
            lambda root: replace(
                root,
                p150,
                "+\tif (!draft || !profile || !profile->classify_local_cap ||",
                "+\treturn 0;\n"
                "+\tif (!draft || !profile || !profile->classify_local_cap ||",
            ),
        ),
        Mutation(
            "canonical_slot_skip",
            "canonical planner traversal skip count changed",
            lambda root: replace(
                root,
                p150,
                "+\tfor (i = 0; i < ARM64_NCAPS; i++) {",
                "+\tfor (i = 0; i < ARM64_NCAPS; i++) {\n"
                "+\t\tif (!i)\n"
                "+\t\t\tcontinue;",
            ),
        ),
        Mutation(
            "match_member_skip",
            "match-member classification contains an unaudited skip",
            lambda root: replace(
                root,
                p150,
                "+\t\tenum arm64_late_cpu_cap_state member_state;",
                "+\t\tenum arm64_late_cpu_cap_state member_state;\n"
                "+\t\tif (!i)\n"
                "+\t\t\tcontinue;",
            ),
        ),
        Mutation(
            "direct_ready_publication",
            "0150 publishes READY state directly",
            lambda root: replace(
                root,
                p150,
                "+\tplan_ret = arm64_plan_late_cpu_capabilities(&draft, &late_profile);",
                "+\tdraft.state = ARM64_LATE_CPU_PROFILE_READY;\n"
                "+\tplan_ret = arm64_plan_late_cpu_capabilities(&draft, &late_profile);",
            ),
        ),
        Mutation(
            "profile_live_match_callback",
            "live target match callback added to selected profile",
            lambda root: replace(
                root,
                p150,
                "+\tswitch (cap->capability) {",
                "+\tmatch->matches(match, SCOPE_LOCAL_CPU);\n"
                "+\tswitch (cap->capability) {",
            ),
        ),
        Mutation(
            "mutation_harness_popen",
            "offline validator contains a dangerous process call",
            lambda root: append(root, test_script, '\nsubprocess.Popen(["make"])\n'),
        ),
        Mutation(
            "aliased_subprocess_popen",
            "offline validator contains an import alias",
            lambda root: append(
                root,
                experiment / "scripts/validate.py",
                '\nimport subprocess as sp\nsp.Popen(["make"])\n',
            ),
        ),
        Mutation(
            "effect_scope",
            "effects.tsv full rows changed",
            lambda root: replace(root, effects, "global max_bhb_k=8", "device write"),
        ),
        Mutation(
            "profile_early_success",
            "selected profile no longer has a sole fail-closed return",
            lambda root: replace(
                root,
                p149,
                "+\tmemcpy(draft->source_parent_identity, source_parent_identity,",
                "+\treturn 0;\n"
                "+\tmemcpy(draft->source_parent_identity, source_parent_identity,",
            ),
        ),
        Mutation(
            "boot_early_success",
            "0092 boot veto changed",
            lambda root: replace(
                root,
                p92,
                "+\tpr_warn_ratelimited(\"CPU%u boot rejected: A72 power sequence inactive\\n\",",
                "+\treturn 0;\n"
                "+\tpr_warn_ratelimited(\"CPU%u boot rejected: A72 power sequence inactive\\n\",",
            ),
        ),
        Mutation(
            "source_list_sentinel",
            "source list sentinel missing: erratum_843419_list",
            lambda root: replace(
                root,
                SOURCE_FIXTURE_REL / "cpu_errata.c",
                "static const struct arm64_cpu_capabilities erratum_843419_list[] = {\n"
                "    { .matches = is_affected_midr_range, },\n"
                "    {},\n"
                "};",
                "static const struct arm64_cpu_capabilities erratum_843419_list[] = {\n"
                "    { .matches = is_affected_midr_range, },\n"
                "};",
            ),
            mode="source_tables",
        ),
        Mutation(
            "source_list_binding",
            "source binding occurrence changed",
            lambda root: replace(
                root,
                SOURCE_FIXTURE_REL / "cpu_errata.c",
                ".match_list = erratum_843419_list,",
                ".match_list = erratum_843419_list_drift,",
            ),
            mode="source_tables",
        ),
        Mutation(
            "nested_match_list_sentinel",
            "source list sentinel missing: nested-virtualization match_list",
            lambda root: replace(
                root,
                SOURCE_FIXTURE_REL / "cpufeature.c",
                "            { .matches = has_cpuid_feature, },\n"
                "            {},\n"
                "        },",
                "            { .matches = has_cpuid_feature, },\n"
                "        },",
            ),
            mode="source_tables",
        ),
        Mutation(
            "git_push",
            "offline validator git command shape is not allowlisted",
            lambda root: append(
                root,
                experiment / "scripts/validate.py",
                '\nsubprocess.run(["git", "push"])\n',
            ),
        ),
        Mutation(
            "git_clean",
            "offline validator git command shape is not allowlisted",
            lambda root: append(
                root,
                experiment / "scripts/validate.py",
                '\nsubprocess.run(["git", "clean", "-fdx"])\n',
            ),
        ),
        Mutation(
            "git_reset",
            "offline validator git command shape is not allowlisted",
            lambda root: append(
                root,
                experiment / "scripts/validate.py",
                '\nsubprocess.run(["git", "reset", "--hard"])\n',
            ),
        ),
        Mutation(
            "modified_scan_omits_staged",
            "offline validator git command shape is not allowlisted",
            lambda root: replace(
                root,
                experiment / "scripts/validate.py",
                '                "HEAD",\n',
                '                "--cached",\n',
            ),
        ),
        Mutation(
            "planner_null_slot",
            "planner canonical traversal",
            lambda root: replace(
                root,
                p150,
                "+\t\tif (!cap)\n+\t\t\tcontinue;",
                "+\t\tif (!cap)\n+\t\t\tbreak;",
            ),
        ),
        Mutation(
            "profile_reports_success",
            "selected profile no longer has a sole fail-closed return",
            lambda root: replace(root, p149, "+\treturn -EAGAIN;", "+\treturn 0;"),
        ),
        Mutation(
            "boot_veto",
            "0092 boot veto changed",
            lambda root: replace(root, p92, "+\treturn -EAGAIN;", "+\treturn 0;"),
        ),
        Mutation(
            "effect_disposition",
            "effect table changed",
            lambda root: replace(root, effects, "\tplanned-only\n", "\tcommitted\n", count=8),
        ),
        Mutation(
            "frozen_offline_missing",
            "missing experiment file results/offline-validation-20260805.txt",
            lambda root: (root / offline_result).unlink(),
            mode="frozen_evidence",
        ),
        Mutation(
            "frozen_mutation_missing",
            "missing experiment file results/mutation-validation-20260805.txt",
            lambda root: (root / mutation_result).unlink(),
            mode="frozen_evidence",
        ),
        Mutation(
            "frozen_mutation_truncated",
            "frozen mutation transcript line count changed",
            lambda root: keep_first_line(root, mutation_result),
            mode="frozen_evidence",
        ),
        Mutation(
            "frozen_offline_extra_fail",
            "frozen offline transcript line count changed",
            lambda root: append(root, offline_result, "FAIL contradictory record\n"),
            mode="frozen_evidence",
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv or ())
    if arguments not in ([], ["--skip-frozen-evidence"]):
        raise MutationFailure("only --skip-frozen-evidence is accepted")
    skip_frozen_evidence = bool(arguments)
    try:
        baseline = VALIDATE.validate_repository(
            REPO,
            pin_hashes=True,
            check_frozen_evidence=not skip_frozen_evidence,
        )
        VALIDATE.validate_capability_source_tables(
            CPU_ERRATA_FIXTURE, CPUFEATURE_FIXTURE
        )
    except Exception as error:  # The baseline must be valid before negative tests.
        print("FAIL baseline {}".format(error), file=sys.stderr)
        return 1

    cases = mutations()
    if len(cases) != EXPECTED_MUTATION_COUNT:
        print(
            "FAIL mutation count {} != {}".format(len(cases), EXPECTED_MUTATION_COUNT),
            file=sys.stderr,
        )
        return 1
    if len({case.name for case in cases}) != len(cases):
        print("FAIL duplicate mutation name", file=sys.stderr)
        return 1

    passed = 0
    for index, case in enumerate(cases, 1):
        with tempfile.TemporaryDirectory(prefix="gemini-a41-planner-mutation-") as temporary:
            fixture = Path(temporary)
            try:
                copy_fixture(fixture)
                case.apply(fixture)
                if case.mode == "repository":
                    VALIDATE.validate_repository(
                        fixture,
                        pin_hashes=False,
                        check_frozen_evidence=False,
                    )
                elif case.mode == "source_tables":
                    validate_source_fixture(fixture)
                elif case.mode == "frozen_evidence":
                    VALIDATE.validate_repository(
                        fixture,
                        pin_hashes=False,
                        check_frozen_evidence=True,
                    )
                else:
                    raise MutationFailure("unknown mutation mode {}".format(case.mode))
            except VALIDATE.ValidationError as error:
                if case.expected_error not in str(error):
                    print(
                        "FAIL mutation {:02d} {}: wrong rejection: {}".format(
                            index, case.name, error
                        ),
                        file=sys.stderr,
                    )
                    return 1
                passed += 1
                print("PASS mutation {:02d} {}".format(index, case.name))
            except (OSError, ValueError, MutationFailure) as error:
                print(
                    "FAIL mutation {:02d} {}: harness error: {}".format(
                        index, case.name, error
                    ),
                    file=sys.stderr,
                )
                return 1
            else:
                print(
                    "FAIL mutation {:02d} {} was accepted".format(index, case.name),
                    file=sys.stderr,
                )
                return 1

    experiment = REPO / VALIDATE.EXPERIMENT_REL
    print("validator_sha256={}".format(VALIDATE.sha256_file(experiment / "scripts/validate.py")))
    print("mutation_suite_sha256={}".format(VALIDATE.sha256_file(Path(__file__))))
    print("python_version={}".format(sys.version.split()[0]))
    print("baseline_static_checks={}".format(len(baseline)))
    print("mutation_count={}".format(len(cases)))
    print("RESULT PASS {}/{}".format(passed, len(cases)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
