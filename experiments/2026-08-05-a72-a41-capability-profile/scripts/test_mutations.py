#!/usr/bin/env python3
"""Require a fixed adversarial mutation set to fail the A41 validator."""

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
SPEC = importlib.util.spec_from_file_location("a41_validate", SCRIPT_DIR / "validate.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load A41 validator")
VALIDATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATE
SPEC.loader.exec_module(VALIDATE)

REPO = SCRIPT_DIR.parents[2]
EXPECTED_MUTATION_COUNT = 43


class MutationFailure(RuntimeError):
    """The mutation harness itself or a negative test failed."""


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


def append(root: Path, relative: Path | str, text: str) -> None:
    path = root / relative
    path.write_text(path.read_text() + text)


def mutate_manifest(root: Path, callback: Callable[[dict], None]) -> None:
    path = root / VALIDATE.MANIFEST
    manifest = json.loads(path.read_text())
    callback(manifest)
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def copy_fixture(destination: Path) -> None:
    manifest = json.loads((REPO / VALIDATE.MANIFEST).read_text())
    profile = manifest["config"]["profiles"][VALIDATE.A41_PROFILE]
    files = {
        VALIDATE.MANIFEST,
        VALIDATE.CANONICAL_SERIES,
        VALIDATE.A41_SERIES,
        VALIDATE.PATCH_0092,
        VALIDATE.PATCH_0148,
        VALIDATE.PATCH_0149,
        Path("configs/gemini-smp8.fragment"),
        *map(Path, profile["fragments"]),
    }
    experiment = REPO / VALIDATE.EXPERIMENT_REL
    files.update(path.relative_to(REPO) for path in experiment.rglob("*") if path.is_file())
    for relative in files:
        source = REPO / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def delete_blocker_row(root: Path) -> None:
    replace(
        root,
        VALIDATE.EXPERIMENT_REL / "results/blockers.tsv",
        "14\tARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY\tmandatory_blocker\t"
        "current source implementation proof absent\n",
        "",
    )


def leak_fragment(root: Path) -> None:
    def mutate(manifest: dict) -> None:
        manifest["config"]["profiles"]["full"]["fragments"].append(
            str(VALIDATE.A41_FRAGMENT)
        )

    mutate_manifest(root, mutate)


def change_default(root: Path) -> None:
    mutate_manifest(
        root,
        lambda manifest: manifest["config"].__setitem__(
            "default_profile", VALIDATE.A41_PROFILE
        ),
    )


def change_selected_series(root: Path) -> None:
    mutate_manifest(
        root,
        lambda manifest: manifest["config"]["profiles"][VALIDATE.A41_PROFILE].__setitem__(
            "patch_series", str(VALIDATE.CANONICAL_SERIES)
        ),
    )


def mutations() -> list[Mutation]:
    p148 = VALIDATE.PATCH_0148
    p149 = VALIDATE.PATCH_0149
    p92 = VALIDATE.PATCH_0092
    selected = VALIDATE.A41_SERIES
    canonical = VALIDATE.CANONICAL_SERIES
    markers = VALIDATE.EXPERIMENT_REL / "results/implementation.tsv"
    blockers = VALIDATE.EXPERIMENT_REL / "results/blockers.tsv"
    readme = VALIDATE.EXPERIMENT_REL / "README.md"
    test_script = VALIDATE.EXPERIMENT_REL / "scripts/test_mutations.py"
    return [
        Mutation(
            "selected_patch_order",
            "A41 terminal patch order changed",
            lambda root: replace(
                root,
                selected,
                str(VALIDATE.PATCH_0148.relative_to("patches"))
                + "\n"
                + str(VALIDATE.PATCH_0149.relative_to("patches")),
                str(VALIDATE.PATCH_0149.relative_to("patches"))
                + "\n"
                + str(VALIDATE.PATCH_0148.relative_to("patches")),
            ),
        ),
        Mutation(
            "canonical_patch_order",
            "canonical A41 patch order changed",
            lambda root: replace(
                root,
                canonical,
                str(VALIDATE.PATCH_0148.relative_to("patches"))
                + "\n"
                + str(VALIDATE.PATCH_0149.relative_to("patches")),
                str(VALIDATE.PATCH_0149.relative_to("patches"))
                + "\n"
                + str(VALIDATE.PATCH_0148.relative_to("patches")),
            ),
        ),
        Mutation(
            "patch_preimage",
            "smp.c: preimage blob changed",
            lambda root: replace(root, p148, "index 1aa324104..", "index 000000000.."),
        ),
        Mutation(
            "lifecycle_order",
            "smp_cpus_done lifecycle",
            lambda root: replace(
                root,
                p148,
                "+\tarm64_prepare_late_cpu_profile();\n \tsetup_system_features();",
                " \tsetup_system_features();\n+\tarm64_prepare_late_cpu_profile();",
            ),
        ),
        Mutation("default_profile", "default profile changed", change_default),
        Mutation("profile_leak", "A41 fragment leaked into profile full", leak_fragment),
        Mutation(
            "fragment_extra_setting",
            "A41 fragment gained an unreviewed setting",
            lambda root: append(
                root,
                VALIDATE.A41_FRAGMENT,
                'CONFIG_CMDLINE="maxcpus=9"\n',
            ),
        ),
        Mutation(
            "kconfig_default_on",
            "A41 Kconfig option is not default-off",
            lambda root: replace(
                root,
                p149,
                '+\tbool "Fail-closed MT6797 late Cortex-A72 capability profile"\n',
                '+\tbool "Fail-closed MT6797 late Cortex-A72 capability profile"\n'
                "+\tdefault y\n",
            ),
        ),
        Mutation(
            "stale_config_input_identity",
            "A41 configuration identity: missing",
            lambda root: replace(root, p149, "0xef8a5a3fe57629be", "0x0000000000000000"),
        ),
        Mutation(
            "planned_capability_missing",
            "planned capability set/order changed",
            lambda root: replace(
                root,
                p149,
                "+\t__set_bit(ARM64_SPECTRE_BHB, draft->required_local_caps);\n",
                "",
            ),
        ),
        Mutation(
            "planned_capability_targets_live_state",
            "planned capability set/order changed",
            lambda root: replace(
                root,
                p149,
                "__set_bit(ARM64_SPECTRE_BHB, draft->required_local_caps)",
                "__set_bit(ARM64_SPECTRE_BHB, system_cpucaps)",
            ),
        ),
        Mutation(
            "bhb_method",
            "deterministic MT6797 plan: missing",
            lambda root: replace(
                root,
                p149,
                "draft->bhb_method = ARM64_LATE_CPU_BHB_LOOP",
                "draft->bhb_method = ARM64_LATE_CPU_BHB_FIRMWARE",
            ),
        ),
        Mutation(
            "bhb_loop_count",
            "deterministic MT6797 plan: missing",
            lambda root: replace(
                root,
                p149,
                "draft->bhb_loop_count = 8",
                "draft->bhb_loop_count = 7",
            ),
        ),
        Mutation(
            "mandatory_blocker_missing",
            "mandatory blocker set changed",
            lambda root: replace(
                root,
                p149,
                "+\t ARM64_LATE_CPU_BLOCK_FIRMWARE_WA1 |\t\t\t\t\\\n",
                "",
            ),
        ),
        Mutation(
            "blocker_table_row_missing",
            "blocker table is not exhaustive",
            delete_blocker_row,
        ),
        Mutation(
            "source_blocker_definition_missing",
            "source blocker set changed",
            lambda root: replace(
                root,
                p148,
                "+#define ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY",
                "+#define ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY_REMOVED",
            ),
        ),
        Mutation(
            "prepare_reports_success",
            "deterministic MT6797 plan: missing",
            lambda root: replace(root, p149, "+\treturn -EAGAIN;", "+\treturn 0;"),
        ),
        Mutation(
            "selected_system_commit",
            "selected profile gained a system commit",
            lambda root: replace(
                root,
                p149,
                "+\t.prepare = mt6797_a72_profile_prepare,\n",
                "+\t.prepare = mt6797_a72_profile_prepare,\n"
                "+\t.verify_system = mt6797_a72_profile_prepare,\n",
            ),
        ),
        Mutation(
            "cpu_on_delegate",
            "production mutation path added: cpu_psci_ops.cpu_boot(",
            lambda root: replace(
                root,
                p149,
                "+\t/* No system capability, alternative, vector, or HWCAP is changed. */",
                "+\tcpu_psci_ops.cpu_boot(8);\n"
                "+\t/* No system capability, alternative, vector, or HWCAP is changed. */",
            ),
        ),
        Mutation(
            "boot_veto",
            "0092 boot veto changed",
            lambda root: replace(root, p92, "+\treturn -EAGAIN;", "+\treturn 0;"),
        ),
        Mutation(
            "disable_veto",
            "0092 disable veto changed",
            lambda root: replace(root, p92, "+\treturn false;", "+\treturn true;"),
        ),
        Mutation(
            "independent_activation",
            "CPU0-independent profile activation",
            lambda root: replace(
                root,
                p149,
                "+\t\tmt6797_activate_a72_capability_profile();",
                "+\t\t/* activation removed */",
            ),
        ),
        Mutation(
            "complete_target_registration",
            "complete target registration: missing",
            lambda root: replace(
                root,
                p148,
                "cpumask_weight(&late_profile_targets)",
                "cpumask_weight_removed(&late_profile_targets)",
            ),
        ),
        Mutation(
            "prepare_full_profile_buffer_guard",
            "prepare core-owned identity guard: missing",
            lambda root: replace(
                root,
                p148,
                "memcmp(draft->profile_id, late_attestation.profile_id",
                "strcmp(draft->profile_id, late_attestation.profile_id",
            ),
        ),
        Mutation(
            "prepare_validate_before_copy",
            "prepare fail-closed transition",
            lambda root: replace(
                root,
                p148,
                "if (!late_profile_core_matches(&draft))",
                "if (false)",
            ),
        ),
        Mutation(
            "bounded_block_log",
            "bounded self-owned profile identity: missing",
            lambda root: replace(root, p148, 'pr_warn("%.*s blocked:', 'pr_warn("%s blocked:'),
        ),
        Mutation(
            "verify_elf_hwcap_immutable",
            "post-prepare immutable record guard: missing",
            lambda root: replace(
                root,
                p148,
                "before->expected_elf_hwcap",
                "before->e_hwcap",
                count=2,
            ),
        ),
        Mutation(
            "verify_compat_hwcap_immutable",
            "post-prepare immutable record guard: missing",
            lambda root: replace(
                root,
                p148,
                "before->expected_compat_hwcap == after->expected_compat_hwcap",
                "true",
            ),
        ),
        Mutation(
            "strict_caps_core_set",
            "system callback transaction",
            lambda root: replace(
                root,
                p148,
                "late_attestation.strict_caps_verified = 1",
                "late_attestation.strict_caps_verified = 0",
            ),
        ),
        Mutation(
            "strict_caps_ready_gate",
            "user callback transaction",
            lambda root: replace(
                root,
                p148,
                "!draft.strict_caps_verified || !draft.alternatives_finalized",
                "false || !draft.alternatives_finalized",
            ),
        ),
        Mutation(
            "const_system_callback",
            "const finalizer callbacks: missing",
            lambda root: replace(
                root,
                p148,
                "int (*verify_system)(const struct arm64_late_cpu_attestation *attestation)",
                "int (*verify_system)(struct arm64_late_cpu_attestation *attestation)",
            ),
        ),
        Mutation(
            "init_lifetime",
            "permanent profile pointer aliases freed init memory",
            lambda root: replace(
                root,
                p148,
                "static struct arm64_late_cpu_profile late_profile __initdata;",
                "static const struct arm64_late_cpu_profile *late_profile __ro_after_init;",
            ),
        ),
        Mutation(
            "source_parent_identity",
            "pre-A41 source parent identity: missing",
            lambda root: replace(root, p149, "0x2ef15df475d00e5a", "0x0000000000000000"),
        ),
        Mutation(
            "implementation_state_marker",
            "implementation claim boundary changed",
            lambda root: replace(
                root,
                markers,
                "implementation_state\tPARTIAL_FAIL_CLOSED",
                "implementation_state\tCOMPLETE",
            ),
        ),
        Mutation(
            "a41_complete_marker",
            "implementation claim boundary changed",
            lambda root: replace(root, markers, "a41_complete\tno", "a41_complete\tyes"),
        ),
        Mutation(
            "build_authorization_marker",
            "implementation claim boundary changed",
            lambda root: replace(root, markers, "build_authorized\tno", "build_authorized\tyes"),
        ),
        Mutation(
            "device_authorization_marker",
            "implementation claim boundary changed",
            lambda root: replace(
                root,
                markers,
                "device_action_authorized\tno",
                "device_action_authorized\tyes",
            ),
        ),
        Mutation(
            "claim_boundary_document",
            "experiment claim boundary: missing 'A41 remains incomplete'",
            lambda root: replace(root, readme, "A41 remains incomplete", "A41 is done"),
        ),
        Mutation(
            "unexpected_patch_path",
            "0149-arm64-mediatek-register-blocked-MT6797-A72-profile.patch: "
            "changed-path set differs",
            lambda root: append(
                root,
                p149,
                "\ndiff --git a/kernel/unsafe.c b/kernel/unsafe.c\n"
                "index 000000000..111111111 100644\n"
                "--- /dev/null\n+++ b/kernel/unsafe.c\n@@ -0,0 +1 @@\n+unsafe\n",
            ),
        ),
        Mutation(
            "selected_manifest_series",
            "A41 series selection changed",
            change_selected_series,
        ),
        Mutation(
            "selected_series_active_patch",
            "A41 series entry count changed",
            lambda root: append(
                root,
                selected,
                "v7.1.3/0093-soc-mediatek-enable-MT6797-A72-power-sequence.patch\n",
            ),
        ),
        Mutation(
            "blocker_disposition",
            "blocker table is not exhaustive",
            lambda root: replace(
                root,
                blockers,
                "2\tARM64_LATE_CPU_BLOCK_CONFIGURATION\tmandatory_blocker",
                "2\tARM64_LATE_CPU_BLOCK_CONFIGURATION\tconditional_guard",
            ),
        ),
        Mutation(
            "offline_boundary",
            "offline validator contains device/build action",
            lambda root: append(
                root,
                test_script,
                '\nsubprocess.run(["shut' + 'down"])\n',
            ),
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        raise MutationFailure("this test takes no arguments")
    try:
        baseline = VALIDATE.validate_repository(REPO, pin_hashes=True)
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
        with tempfile.TemporaryDirectory(prefix="gemini-a41-mutation-") as temporary:
            fixture = Path(temporary)
            try:
                copy_fixture(fixture)
                case.apply(fixture)
                VALIDATE.validate_repository(fixture, pin_hashes=False)
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

    print("baseline_static_checks={}".format(len(baseline)))
    print("mutation_count={}".format(len(cases)))
    print("RESULT PASS {}/{}".format(passed, len(cases)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
