#!/usr/bin/env python3
"""Require focused A41 static-census safety mutations to fail validation."""

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

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
VALIDATOR_PATH = SCRIPT_DIR / "validate.py"
SPEC = importlib.util.spec_from_file_location("a41_static_census_validate", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load A41 static-census validator")
VALIDATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATE
SPEC.loader.exec_module(VALIDATE)

EXPECTED_MUTATION_COUNT = 22
PATCH_0092 = Path(
    "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
)
OTHER_PROFILE_SERIES = Path("patches/series-a72-reject-gate")


class MutationFailure(RuntimeError):
    """The mutation harness or a negative test failed."""


@dataclass(frozen=True)
class Mutation:
    name: str
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
        lambda manifest: manifest["config"]["profiles"][VALIDATE.PROFILE].__setitem__(
            "patch_series", str(VALIDATE.PARENT_SERIES)
        ),
    )


def break_other_profile_series(root: Path) -> None:
    entries = VALIDATE.series_entries((root / OTHER_PROFILE_SERIES).read_text())
    if len(entries) < 2:
        raise MutationFailure("independent profile series is too short")
    swap_lines(root, OTHER_PROFILE_SERIES, entries[0], entries[1])


def append_offline_command(root: Path) -> None:
    command = "cu" + "rl"
    append(
        root,
        VALIDATE.EXPERIMENT / "scripts/test_mutations.py",
        "\nimport subprocess\nsubprocess.run([\"" + command + "\"])\n",
    )


def add_unexpected_residue(root: Path) -> None:
    path = root / VALIDATE.EXPERIMENT / "results/unreviewed.txt"
    path.write_text("unexpected\n")


def mutations() -> list[Mutation]:
    patch = VALIDATE.PATCH
    selected = VALIDATE.SERIES
    census = VALIDATE.EXPERIMENT / "results/static-census.tsv"
    markers = VALIDATE.EXPERIMENT / "results/implementation.tsv"
    p151 = "v7.1.3/0151-arm64-split-late-CPU-evidence-from-commit-receipt.patch"
    p152 = str(patch.relative_to("patches"))
    return [
        Mutation(
            "patch-source-commit",
            lambda root: replace(root, patch, VALIDATE.SOURCE, "0" * 40),
        ),
        Mutation(
            "patch-subject",
            lambda root: replace(
                root,
                patch,
                "Subject: [PATCH] arm64: classify static MT6797 late-CPU capabilities",
                "Subject: [PATCH] arm64: enable MT6797 late CPUs",
            ),
        ),
        Mutation(
            "synthetic-signoff",
            lambda root: replace(
                root,
                patch,
                "This experiment-only change has no certifying sign-off",
                "Signed-off-by: Synthetic Author <noreply@invalid>\n\n"
                "This experiment-only change has no certifying sign-off",
            ),
        ),
        Mutation(
            "source-parent-identity",
            lambda root: replace(
                root, patch, "0xbf192fa874aea983", "0x0f192fa874aea983"
            ),
        ),
        Mutation(
            "config-input-identity",
            lambda root: replace(
                root, patch, "0x6fa24adaa512d804", "0x0fa24adaa512d804"
            ),
        ),
        Mutation(
            "selected-series-drop",
            lambda root: remove_line(root, selected, p152),
        ),
        Mutation(
            "selected-series-order",
            lambda root: swap_lines(root, selected, p151, p152),
        ),
        Mutation("manifest-series-selection", change_selected_series),
        Mutation("all-profile-series-order", break_other_profile_series),
        Mutation(
            "census-partition",
            lambda root: replace(
                root,
                census,
                "9\tARM64_HAS_AMU_EXTN\tPRESENT\t",
                "9\tARM64_HAS_AMU_EXTN\tABSENT\t",
            ),
        ),
        Mutation(
            "completion-claim",
            lambda root: replace(
                root, markers, "a41_complete\tno\t", "a41_complete\tyes\t"
            ),
        ),
        Mutation(
            "target-override-guard",
            lambda root: replace(
                root,
                patch,
                "+\tif (!cap || arm64_late_cpu_target_impl_override_active())",
                "+\tif (!cap)",
            ),
        ),
        Mutation(
            "kpti-force-guard",
            lambda root: replace(
                root, patch, "+\t\t    !__kpti_forced &&", "+\t\t    true &&"
            ),
        ),
        Mutation(
            "mandatory-blocker-mask",
            lambda root: replace(
                root,
                patch,
                "+\t    (evidence->blocker_mask & MT6797_A72_PROFILE_BLOCKERS) !=",
                "+\t    (evidence->blocker_mask & MT6797_A72_PROFILE_BLOCKERS) ==",
            ),
        ),
        Mutation(
            "target-method-empty",
            lambda root: replace(
                root,
                patch,
                "+\t\t    !mt6797_a72_target_method_empty(&evidence->target_method[i]))",
                "+\t\t    false)",
            ),
        ),
        Mutation(
            "partial-validator-eagain",
            lambda root: replace_between(
                root,
                patch,
                "mt6797_a72_validate_cap_plan",
                "static bool __init mt6797_a72_profile_config_gates_match",
                " \treturn -EAGAIN;",
                " \treturn 0;",
            ),
        ),
        Mutation(
            "plan-identity-write",
            lambda root: replace(
                root,
                patch,
                "+\t/* Expected-MIDR census only: observed MIDR_VALID proof is still absent. */",
                "+\tplan->identity[0] = 1;\n+\n"
                "+\t/* Expected-MIDR census only: observed MIDR_VALID proof is still absent. */",
            ),
        ),
        Mutation(
            "inherited-boot-veto",
            lambda root: replace_between(
                root,
                PATCH_0092,
                "+static int mt6797_psci_cpu_boot",
                "#ifdef CONFIG_HOTPLUG_CPU",
                "+\treturn -EAGAIN;",
                "+\treturn 0;",
            ),
        ),
        Mutation(
            "inherited-disable-veto",
            lambda root: replace_between(
                root,
                PATCH_0092,
                "+static bool mt6797_psci_cpu_can_disable",
                "+#endif",
                "+\treturn false;",
                "+\treturn true;",
            ),
        ),
        Mutation(
            "maxcpus-guard",
            lambda root: replace(
                root,
                Path("configs/gemini-smp8.fragment"),
                "maxcpus=8",
                "maxcpus=9",
                count=2,
            ),
        ),
        Mutation("external-action", append_offline_command),
        Mutation("unexpected-residue", add_unexpected_residue),
    ]


def copy_fixture(destination: Path) -> None:
    """Copy only repository inputs consumed by the static-census validator."""

    shutil.copytree(REPO / "patches", destination / "patches")
    shutil.copytree(REPO / "configs", destination / "configs")
    shutil.copytree(
        REPO / VALIDATE.EXPERIMENT,
        destination / VALIDATE.EXPERIMENT,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for relative in (
        VALIDATE.MANIFEST,
        Path("docs/ROADMAP.md"),
        Path("experiments/README.md"),
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / relative, target)


def file_sha256(path: Path) -> str:
    return VALIDATE.sha256(path.read_bytes())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    cases = mutations()
    if len(cases) != EXPECTED_MUTATION_COUNT:
        raise MutationFailure(
            "expected {} mutations, found {}".format(
                EXPECTED_MUTATION_COUNT, len(cases)
            )
        )
    if len({case.name for case in cases}) != len(cases):
        raise MutationFailure("mutation names are duplicated")
    if args.list:
        for case in cases:
            print(case.name)
        return 0

    with tempfile.TemporaryDirectory(prefix="gemini-a41-static-baseline-") as temporary:
        baseline_root = Path(temporary)
        copy_fixture(baseline_root)
        baseline_checks = VALIDATE.validate_repository(
            baseline_root, pin_hashes=False, skip_frozen_evidence=True
        )
    print("PASS baseline")

    passed = 0
    for index, case in enumerate(cases, 1):
        with tempfile.TemporaryDirectory(
            prefix="gemini-a41-static-mutation-"
        ) as temporary:
            root = Path(temporary)
            copy_fixture(root)
            case.apply(root)
            try:
                VALIDATE.validate_repository(
                    root, pin_hashes=False, skip_frozen_evidence=True
                )
            except VALIDATE.ValidationError:
                pass
            else:
                raise MutationFailure("{} was incorrectly accepted".format(case.name))
        passed += 1
        print("PASS {} mutation={:02d}".format(case.name, index))

    print("validator_sha256={}".format(file_sha256(VALIDATOR_PATH)))
    print("mutation_suite_sha256={}".format(file_sha256(Path(__file__))))
    print("python_version={}".format(sys.version.split()[0]))
    print("baseline_static_checks={}".format(len(baseline_checks)))
    print("mutation_count={}".format(len(cases)))
    print("RESULT PASS {0}/{0}".format(passed))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, MutationFailure) as error:
        print("RESULT FAIL {}".format(error), file=sys.stderr)
        raise SystemExit(1)
