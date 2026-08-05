#!/usr/bin/env python3
"""Adversarially mutate the A41 immutable-plan archive and require rejection."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


sys.dont_write_bytecode = True


REPO = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = (
    REPO
    / "experiments/2026-08-05-a72-a41-immutable-plan/scripts/validate.py"
)
SPEC = importlib.util.spec_from_file_location("a41_immutable_validate", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load immutable-plan validator")
VALIDATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATE
SPEC.loader.exec_module(VALIDATE)


class MutationFailure(RuntimeError):
    """The mutation harness or a negative test failed."""


@dataclass(frozen=True)
class Mutation:
    name: str
    expected_error: str
    apply: Callable[[Path], None]


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


def replace_between(
    root: Path,
    relative: Path | str,
    start: str,
    end: str,
    old: str,
    new: str,
) -> None:
    path = root / relative
    text = path.read_text()
    begin = text.find(start)
    finish = text.find(end, begin + len(start))
    if begin < 0 or finish < 0:
        raise MutationFailure("{}: mutation range is missing".format(relative))
    section = text[begin:finish]
    if section.count(old) != 1:
        raise MutationFailure(
            "{}: ranged target count is {}".format(relative, section.count(old))
        )
    section = section.replace(old, new, 1)
    path.write_text(text[:begin] + section + text[finish:])


def append(root: Path, relative: Path | str, value: str) -> None:
    path = root / relative
    path.write_text(path.read_text() + value)


def remove_line(root: Path, relative: Path | str, exact: str) -> None:
    path = root / relative
    lines = path.read_text().splitlines()
    if lines.count(exact) != 1:
        raise MutationFailure("{}: exact line is not unique".format(relative))
    lines.remove(exact)
    path.write_text("\n".join(lines) + "\n")


def swap_lines(root: Path, relative: Path | str, first: str, second: str) -> None:
    path = root / relative
    lines = path.read_text().splitlines()
    if lines.count(first) != 1 or lines.count(second) != 1:
        raise MutationFailure("{}: swap lines are not unique".format(relative))
    left = lines.index(first)
    right = lines.index(second)
    lines[left], lines[right] = lines[right], lines[left]
    path.write_text("\n".join(lines) + "\n")


def mutate_manifest(root: Path, callback: Callable[[dict], None]) -> None:
    path = root / VALIDATE.MANIFEST
    manifest = json.loads(path.read_text())
    callback(manifest)
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def change_selected_series(root: Path) -> None:
    mutate_manifest(
        root,
        lambda manifest: manifest["config"]["profiles"][
            VALIDATE.PROFILE
        ].__setitem__("patch_series", str(VALIDATE.CANONICAL_SERIES)),
    )


def reorder_selected_fragments(root: Path) -> None:
    def change(manifest: dict) -> None:
        fragments = manifest["config"]["profiles"][VALIDATE.PROFILE]["fragments"]
        fragments[-1], fragments[-2] = fragments[-2], fragments[-1]

    mutate_manifest(root, change)


def leak_fragment(root: Path) -> None:
    mutate_manifest(
        root,
        lambda manifest: manifest["config"]["profiles"]["full"][
            "fragments"
        ].append(str(VALIDATE.SELECTED_FRAGMENT)),
    )


def break_other_profile_series(root: Path) -> None:
    manifest = json.loads((root / VALIDATE.MANIFEST).read_text())
    fallback = manifest.get("patch_series")
    excluded = {
        str(VALIDATE.CANONICAL_SERIES),
        str(VALIDATE.SELECTED_SERIES),
        str(VALIDATE.PREVIOUS_EXPERIMENT_REL),
    }
    for profile in manifest["config"]["profiles"].values():
        series = profile.get("patch_series", fallback)
        if series in excluded:
            continue
        path = root / series
        entries = [
            line for line in path.read_text().splitlines()
            if line and not line.startswith("#")
        ]
        if len(entries) >= 2:
            swap_lines(root, series, entries[0], entries[1])
            return
    raise MutationFailure("no independent profile series found")


def reorder_plan_publication(root: Path) -> None:
    path = root / VALIDATE.PATCH_0151
    text = path.read_text()
    first = "+\tlate_plan = draft;\n"
    second = (
        "+\tmemcpy(late_receipt.plan_identity, late_plan.identity,\n"
        "+\t       sizeof(late_receipt.plan_identity));\n"
    )
    if text.count(first) != 1 or text.count(second) != 1:
        raise MutationFailure("plan publication sequence is not unique")
    text = text.replace(first, "", 1)
    text = text.replace(second, second + first, 1)
    path.write_text(text)


def reorder_commit_call(root: Path) -> None:
    path = root / VALIDATE.PATCH_0151
    text = path.read_text()
    call = (
        "+\t/* Any late-target plan must commit before capability finalization. */\n"
        "+\tarm64_commit_late_cpu_profile();\n"
        "+\n"
    )
    update = " \tupdate_cpu_capabilities(SCOPE_SYSTEM);\n"
    if text.count(call) != 1 or text.count(update) != 1:
        raise MutationFailure("commit timing sequence is not unique")
    text = text.replace(call, "", 1)
    text = text.replace(update, update + call, 1)
    path.write_text(text)


def append_offline_command(root: Path) -> None:
    command = "cu" + "rl"
    append(
        root,
        VALIDATE.EXPERIMENT_REL / "scripts/test_mutations.py",
        "\nimport subprocess\nsubprocess.run([\"" + command + "\"])\n",
    )


def add_unexpected_residue(root: Path) -> None:
    path = root / VALIDATE.EXPERIMENT_REL / "results/unreviewed.txt"
    path.write_text("unexpected\n")


def mutations() -> list[Mutation]:
    patch = VALIDATE.PATCH_0151
    selected = VALIDATE.SELECTED_SERIES
    canonical = VALIDATE.CANONICAL_SERIES
    fragment = VALIDATE.SELECTED_FRAGMENT
    census = VALIDATE.EXPERIMENT_REL / "results/capability-census.tsv"
    unresolved = VALIDATE.EXPERIMENT_REL / "results/unresolved-effects.tsv"
    markers = VALIDATE.EXPERIMENT_REL / "results/implementation.tsv"
    p151 = str(VALIDATE.PATCH_0151.relative_to("patches"))
    p150 = str(VALIDATE.PATCH_0150.relative_to("patches"))
    return [
        Mutation(
            "patch_commit_identity",
            "patch commit identity changed",
            lambda root: replace(
                root, patch, VALIDATE.EXPECTED_PATCH_COMMIT,
                "0" * 40,
            ),
        ),
        Mutation(
            "patch_subject",
            "patch metadata",
            lambda root: replace(
                root, patch,
                "Subject: [PATCH] arm64: split late-CPU evidence from commit receipt",
                "Subject: [PATCH] arm64: enable late CPUs",
            ),
        ),
        Mutation(
            "synthetic_signoff",
            "synthetic sign-off",
            lambda root: replace(
                root, patch,
                "This experiment-only change has no certifying sign-off",
                "Signed-off-by: Synthetic Author <noreply@invalid>\n\n"
                "This experiment-only change has no certifying sign-off",
            ),
        ),
        Mutation(
            "patch_preimage",
            "patch pre/post image changed",
            lambda root: replace(root, patch, "index 45f7fa222..79446800e",
                                 "index 000000000..79446800e"),
        ),
        Mutation(
            "selected_series_drop",
            "selected series entry count changed",
            lambda root: remove_line(root, selected, p151),
        ),
        Mutation(
            "selected_series_reorder",
            "previous planner baseline failed",
            lambda root: swap_lines(root, selected, p150, p151),
        ),
        Mutation(
            "canonical_series_drop",
            "previous planner baseline failed",
            lambda root: remove_line(root, canonical, p151),
        ),
        Mutation(
            "another_profile_series_order",
            "previous planner baseline failed",
            break_other_profile_series,
        ),
        Mutation(
            "manifest_series_selection",
            "profile series selection changed",
            change_selected_series,
        ),
        Mutation(
            "manifest_fragment_order",
            "profile fragment order changed",
            reorder_selected_fragments,
        ),
        Mutation(
            "manifest_fragment_leak",
            "selected fragment leaked",
            leak_fragment,
        ),
        Mutation(
            "fragment_profile_disable",
            "selected fragment settings changed",
            lambda root: replace(
                root, fragment,
                "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=y",
                "CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE=n",
            ),
        ),
        Mutation(
            "fragment_localversion",
            "selected fragment settings changed",
            lambda root: replace(
                root, fragment,
                'CONFIG_LOCALVERSION="-gemini-a41-immutable-blocked"',
                'CONFIG_LOCALVERSION="-gemini-a41-live"',
            ),
        ),
        Mutation(
            "maxcpus_guard",
            "previous planner baseline failed",
            lambda root: replace(
                root, Path("configs/gemini-smp8.fragment"),
                "maxcpus=8", "maxcpus=9", count=2,
            ),
        ),
        Mutation(
            "config_digest_literal",
            "MT6797 fail-closed profile",
            lambda root: replace(
                root, patch, "0x91694455fdc12472", "0x01694455fdc12472",
            ),
        ),
        Mutation(
            "source_parent_literal",
            "MT6797 fail-closed profile",
            lambda root: replace(
                root, patch, "0xa1573b40b7b8f5a8", "0x01573b40b7b8f5a8",
            ),
        ),
        Mutation(
            "plan_abi",
            "ABI 3 header",
            lambda root: replace(
                root, patch,
                "+#define ARM64_LATE_CPU_PLAN_ABI\t\t3",
                "+#define ARM64_LATE_CPU_PLAN_ABI\t\t4",
            ),
        ),
        Mutation(
            "wa3_blocker_bit",
            "ABI WA3 blocker definition changed",
            lambda root: replace(
                root, patch,
                "+#define ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3\tBIT_ULL(15)",
                "+#define ARM64_LATE_CPU_BLOCK_FIRMWARE_WA3\tBIT_ULL(14)",
            ),
        ),
        Mutation(
            "wa3_cap_valid_bit",
            "target capability validity mask changed",
            lambda root: replace(
                root, patch,
                "+#define ARM64_LATE_CPU_TARGET_CAP_WA3_VALID\tBIT(7)",
                "+#define ARM64_LATE_CPU_TARGET_CAP_WA3_VALID\tBIT(6)",
            ),
        ),
        Mutation(
            "bhb_method_valid_bit",
            "target method validity mask changed",
            lambda root: replace(
                root, patch,
                "+#define ARM64_LATE_CPU_TARGET_METHOD_BHB_VALID\t\tBIT(3)",
                "+#define ARM64_LATE_CPU_TARGET_METHOD_BHB_VALID\t\tBIT(2)",
            ),
        ),
        Mutation(
            "aarch64_register_field",
            "AArch64 register field revidr is missing",
            lambda root: replace(root, patch, "+\tu64 revidr;",
                                 "+\tu64 omitted_revidr;"),
        ),
        Mutation(
            "aarch32_register_field",
            "AArch32 register field id_isar6 is missing",
            lambda root: replace(root, patch, "+\tu32 id_isar6;",
                                 "+\tu32 omitted_id_isar6;"),
        ),
        Mutation(
            "evidence_struct_definition",
            "missing C block struct arm64_late_cpu_evidence",
            lambda root: replace(
                root, patch,
                "+struct arm64_late_cpu_evidence {",
                "+struct arm64_late_cpu_partial_evidence {",
            ),
        ),
        Mutation(
            "receipt_commit_complete_field",
            "receipt schema",
            lambda root: replace(root, patch, "+\tu8 commit_complete;",
                                 "+\tu8 omitted_commit_complete;"),
        ),
        Mutation(
            "ready_evidence_identity_field",
            "READY token schema",
            lambda root: replace(
                root, patch,
                "+\tu64 evidence_identity[ARM64_LATE_CPU_ID_WORDS];",
                "+\tu64 omitted_evidence_identity[ARM64_LATE_CPU_ID_WORDS];",
            ),
        ),
        Mutation(
            "typed_effect_header_field",
            "typed effect schema",
            lambda root: replace(root, patch, "+\t\tu8 hyp_vector;",
                                 "+\t\tu8 omitted_hyp_vector;"),
        ),
        Mutation(
            "effect_comparison_field",
            "receipt effect comparison omits spectre_v2.callback",
            lambda root: replace(
                root, patch,
                "+\t       left->spectre_v2.callback == right->spectre_v2.callback &&",
                "+\t       true &&",
            ),
        ),
        Mutation(
            "effect_emptiness_field",
            "effect emptiness check omits spectre_v4.policy",
            lambda root: replace(
                root, patch,
                "+\t       !effects->spectre_v4.policy &&",
                "+\t       true &&",
            ),
        ),
        Mutation(
            "classifier_resolves_partial",
            "MT6797 fail-closed profile",
            lambda root: replace(
                root, patch,
                "+\treturn ARM64_LATE_CPU_CAP_UNRESOLVED;",
                "+\treturn ARM64_LATE_CPU_CAP_PRESENT;",
            ),
        ),
        Mutation(
            "profile_validator_success",
            "profile validator no longer rejects",
            lambda root: replace_between(
                root, patch,
                "mt6797_a72_validate_cap_plan",
                "static bool __init mt6797_a72_profile_config_gates_match",
                "+\treturn -EAGAIN;", "+\treturn 0;",
            ),
        ),
        Mutation(
            "profile_prepare_success",
            "profile preparation no longer rejects",
            lambda root: replace_between(
                root, patch,
                "mt6797_a72_profile_prepare",
                "static const struct arm64_late_cpu_profile",
                " \treturn -EAGAIN;", " \treturn 0;",
            ),
        ),
        Mutation(
            "plan_identity_guard",
            "prepare/freeze transaction",
            lambda root: replace(
                root, patch,
                "+\tif (!late_profile_plan_has_identity(&draft)) {",
                "+\tif (false) {",
            ),
        ),
        Mutation(
            "plan_publication_order",
            "prepare/freeze transaction",
            reorder_plan_publication,
        ),
        Mutation(
            "committed_state_publication",
            "COMMITTED publication became reachable",
            lambda root: replace(
                root, patch,
                "+\t\t\t  ARM64_LATE_CPU_PROFILE_PLAN_FROZEN);",
                "+\t\t\t  ARM64_LATE_CPU_PROFILE_COMMITTED);",
            ),
        ),
        Mutation(
            "blocked_commit_return",
            "architecture commit implementation",
            lambda root: replace(
                root, patch,
                "+\t    state == ARM64_LATE_CPU_PROFILE_BLOCKED)",
                "+\t    state == ARM64_LATE_CPU_PROFILE_READY)",
            ),
        ),
        Mutation(
            "commit_success",
            "core ABI 3 transaction",
            lambda root: replace(
                root, patch,
                '+\tpanic("late CPU profile commit implementation is unavailable");',
                "+\treturn;",
            ),
        ),
        Mutation(
            "commit_live_mutation",
            "commit completion gained a writer",
            lambda root: replace(
                root, patch,
                '+\tpanic("late CPU profile commit implementation is unavailable");',
                "+\tlate_receipt.commit_complete = 1;\n"
                '+\tpanic("late CPU profile commit implementation is unavailable");',
            ),
        ),
        Mutation(
            "receipt_effect_write",
            "receipt committed effects gained a writer",
            lambda root: replace(
                root, patch,
                '+\tpanic("late CPU profile commit implementation is unavailable");',
                "+\tlate_receipt.committed = late_plan.effects;\n"
                '+\tpanic("late CPU profile commit implementation is unavailable");',
            ),
        ),
        Mutation(
            "receipt_identity_check",
            "system verification lost bracketing identity checks",
            lambda root: replace(
                root, patch,
                "+\tif (!late_profile_receipt_identity_matches(&late_plan, &late_receipt))",
                "+\tif (false)",
            ),
        ),
        Mutation(
            "ready_release",
            "READY publication lost release-store",
            lambda root: replace(
                root, patch,
                "+\t/* Pairs with smp_load_acquire() in the READY-token accessor. */\n"
                "+\tsmp_store_release(&late_receipt.state,",
                "+\t/* READY publication incorrectly weakened. */\n"
                "+\tWRITE_ONCE(late_receipt.state,",
            ),
        ),
        Mutation(
            "ready_acquire",
            "core ABI 3 transaction",
            lambda root: replace(
                root, patch,
                "+\tif (smp_load_acquire(&late_receipt.state) !=",
                "+\tif (READ_ONCE(late_receipt.state) !=",
            ),
        ),
        Mutation(
            "ready_accessor_exposes_plan",
            "READY accessor",
            lambda root: replace(
                root, patch,
                "+\treturn &late_ready_token;",
                "+\treturn (void *)&late_plan;",
            ),
        ),
        Mutation(
            "commit_call_presence",
            "cpufeature ABI 3 boundary",
            lambda root: replace(
                root, patch,
                "+\tarm64_commit_late_cpu_profile();",
                "+\t/* commit call removed */",
            ),
        ),
        Mutation(
            "dynamic_bhb_autofill",
            "cpufeature ABI 3 boundary",
            lambda root: replace(
                root, patch,
                "+\t\t\t\t/* The exhaustive evaluator owns these typed effects. */",
                "+\t\t\t\tdraft->effects.bhb.required = 1;",
            ),
        ),
        Mutation(
            "census_partition",
            "capability census partition changed",
            lambda root: replace(
                root, census,
                "\tPRESENT\thas_amu returns true unconditionally",
                "\tABSENT\thas_amu returns true unconditionally",
            ),
        ),
        Mutation(
            "unresolved_slot_set",
            "unresolved-effect set changed",
            lambda root: replace(
                root, unresolved,
                "82\tARM64_SPECTRE_BHB", "83\tARM64_SPECTRE_BHB",
            ),
        ),
        Mutation(
            "completion_claim",
            "implementation markers changed",
            lambda root: replace(
                root, markers, "a41_complete\tno\t", "a41_complete\tyes\t",
            ),
        ),
        Mutation(
            "offline_network_command",
            "offline script contains a forbidden command",
            append_offline_command,
        ),
        Mutation(
            "boot_veto",
            "previous planner baseline failed",
            lambda root: replace_between(
                root, VALIDATE.PATCH_0092,
                "+static int mt6797_psci_cpu_boot",
                "#ifdef CONFIG_HOTPLUG_CPU",
                "+\treturn -EAGAIN;", "+\treturn 0;",
            ),
        ),
        Mutation(
            "disable_veto",
            "previous planner baseline failed",
            lambda root: replace_between(
                root, VALIDATE.PATCH_0092,
                "+static bool mt6797_psci_cpu_can_disable",
                "+#endif",
                "+\treturn false;", "+\treturn true;",
            ),
        ),
        Mutation(
            "build_authorization",
            "implementation markers changed",
            lambda root: replace(
                root, markers, "build_authorized\tno\t",
                "build_authorized\tyes\t",
            ),
        ),
        Mutation(
            "device_authorization",
            "implementation markers changed",
            lambda root: replace(
                root, markers, "device_action_authorized\tno\t",
                "device_action_authorized\tyes\t",
            ),
        ),
        Mutation(
            "bhb_state_from_loop",
            "BHB state/method separation",
            lambda root: replace(
                root, unresolved,
                "ABSENT iff target CSV2 field equals 3; otherwise PRESENT because A72 is not BHB-safe-listed",
                "PRESENT because loop k=8 was selected",
            ),
        ),
        Mutation(
            "unexpected_archive_residue",
            "unexpected experiment residue",
            add_unexpected_residue,
        ),
        Mutation(
            "personal_absolute_path",
            "personal absolute path entered archive",
            lambda root: append(
                root, VALIDATE.EXPERIMENT_REL / "README.md",
                "\n/" + "Users/example/private\n",
            ),
        ),
    ]


def copy_fixture(destination: Path) -> None:
    shutil.copytree(REPO / "patches", destination / "patches")
    shutil.copytree(REPO / "configs", destination / "configs")
    for relative in (
        VALIDATE.EXPERIMENT_REL,
        VALIDATE.PREVIOUS_EXPERIMENT_REL,
    ):
        shutil.copytree(REPO / relative, destination / relative)
    for relative in (
        VALIDATE.MANIFEST,
        Path("docs/ROADMAP.md"),
        Path("experiments/README.md"),
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / relative, target)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    cases = mutations()
    if len(cases) != VALIDATE.EXPECTED_MUTATION_COUNT:
        raise MutationFailure(
            "expected {} mutations, found {}".format(
                VALIDATE.EXPECTED_MUTATION_COUNT, len(cases)
            )
        )
    if len({case.name for case in cases}) != len(cases):
        raise MutationFailure("mutation names are duplicated")
    if args.list:
        for case in cases:
            print(case.name)
        return 0

    passed = 0
    for index, case in enumerate(cases, 1):
        with tempfile.TemporaryDirectory(
            prefix="gemini-a41-abi3-mutation-"
        ) as temporary:
            root = Path(temporary)
            copy_fixture(root)
            case.apply(root)
            try:
                VALIDATE.validate_repository(
                    root,
                    pin_hashes=False,
                    check_frozen_evidence=False,
                )
            except VALIDATE.ValidationError as error:
                if case.expected_error not in str(error):
                    raise MutationFailure(
                        "{} rejected for unexpected reason: {}".format(
                            case.name, error
                        )
                    ) from error
            else:
                raise MutationFailure(
                    "{} was incorrectly accepted".format(case.name)
                )
        passed += 1
        print("PASS mutation {:02d} {}".format(index, case.name))

    print("validator_sha256={}".format(VALIDATE.sha256_file(VALIDATOR_PATH)))
    print("mutation_suite_sha256={}".format(VALIDATE.sha256_file(Path(__file__))))
    print("python_version={}".format(sys.version.split()[0]))
    print("mutation_count={}".format(len(cases)))
    print("RESULT PASS {0}/{0}".format(passed))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, MutationFailure) as error:
        print("RESULT FAIL {}".format(error), file=sys.stderr)
        raise SystemExit(1)
