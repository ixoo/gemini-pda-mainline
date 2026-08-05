#!/usr/bin/env python3
"""Adversarial mutations for the A72 CPU-up source-closure contract."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Callable


VALIDATOR_PATH = Path(__file__).with_name("validate_contract.py")
SPEC = importlib.util.spec_from_file_location("a72_source_closure_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def expect_rejected(label: str, action: Callable[[], None], expected: str = "") -> None:
    try:
        action()
    except VALIDATOR.ContractError as error:
        if expected and expected not in str(error):
            raise AssertionError(
                f"wrong rejection for {label}: expected {expected!r}, got {error!s}"
            ) from error
        return
    raise AssertionError(f"mutation accepted: {label}")


def row(tables: dict[str, list[dict[str, str]]], table: str,
        identifier: str) -> dict[str, str]:
    return next(item for item in tables[table] if item["id"] == identifier)


def mutate_token(table: str, identifier: str, field: str, token: str) -> None:
    tables = copy.deepcopy(VALIDATOR.load_tables())
    target = row(tables, table, identifier)
    if token not in target[field]:
        raise AssertionError(f"test token absent: {table}/{identifier}.{field}: {token}")
    target[field] = target[field].replace(token, "MUTATED", 1)
    VALIDATOR.validate_tables(tables)


def mutate_source_hash(identifier: str) -> None:
    tables = copy.deepcopy(VALIDATOR.load_tables())
    row(tables, "source", identifier)["sha256"] = "0" * 64
    VALIDATOR.validate_tables(tables)


def mutate_config_value(identifier: str) -> None:
    tables = copy.deepcopy(VALIDATOR.load_tables())
    target = row(tables, "config", identifier)
    target["selected_value"] = "n" if target["selected_value"] == "y" else "y"
    VALIDATOR.validate_tables(tables)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--prepared-source-root", type=Path)
    parser.add_argument("--config", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(__import__("sys").argv[1:] if argv is None else argv)
    tables = VALIDATOR.load_tables()
    VALIDATOR.validate_tables(tables)
    VALIDATOR.validate_evidence(args.source_root, args.prepared_source_root, args.config)
    VALIDATOR.validate_documents()
    report = VALIDATOR.validation_report(tables)
    VALIDATOR.validate_authorization(report)
    VALIDATOR.validate_transcript(report)
    VALIDATOR.validate_optional_transcript()

    tests: list[tuple[str, Callable[[], None]]] = []

    def add(label: str, action: Callable[[], None], expected: str = "") -> None:
        tests.append((label, lambda label=label, action=action, expected=expected:
                      expect_rejected(label, action, expected)))

    # Raw table identity, schema, order, membership, and duplicate guards.
    for name, spec in VALIDATOR.TABLES.items():
        raw = spec["path"].read_bytes()
        add(f"identity-{name}",
            lambda name=name, raw=raw: VALIDATOR.validate_table_bytes(name, raw + b"\n"),
            "identity changed")

        fields = spec["fields"]
        malformed = raw.decode("utf-8").replace(fields[0], "mutated_id", 1).encode("utf-8")
        add(f"schema-{name}",
            lambda name=name, malformed=malformed:
            VALIDATOR.validate_table_bytes(name, malformed, check_identity=False),
            "schema changed")

        add(f"missing-row-{name}",
            lambda name=name: _validate_changed_tables(name, lambda rows: rows.pop()))
        add(f"reordered-{name}",
            lambda name=name: _validate_changed_tables(name, lambda rows: rows.reverse()))
        add(f"duplicate-{name}",
            lambda name=name: _validate_changed_tables(name, lambda rows: rows.append(copy.deepcopy(rows[-1]))))

    # Every pinned source/config identity is protected independently.
    for identifier in VALIDATOR.EXPECTED_SOURCE_HASHES:
        add(f"source-hash-{identifier}",
            lambda identifier=identifier: mutate_source_hash(identifier))
    for identifier in VALIDATOR.TABLES["config"]["ids"]:
        add(f"config-value-{identifier}",
            lambda identifier=identifier: mutate_config_value(identifier))

    # Every semantic phrase is an independent tripwire after identity is re-based.
    for table, identifier, field, token in VALIDATOR.SEMANTIC_TOKENS:
        add(f"semantic-{table}-{identifier}-{token}",
            lambda table=table, identifier=identifier, field=field, token=token:
            mutate_token(table, identifier, field, token))

    # Cross-row safety properties that do not reduce to one required phrase.
    add("deterministic-capability-class",
        lambda: _mutate_field("capability", "K01", "detection_basis",
                              lambda value: value.replace("deterministic", "conditional")))
    add("capability-veto-K02",
        lambda: _mutate_field("capability", "K02", "failure",
                              lambda value: value.replace("A26", "AXX")))
    for identifier in VALIDATOR.TABLES["early"]["ids"]:
        add(f"early-reset-only-{identifier}",
            lambda identifier=identifier: _mutate_field(
                "early", identifier, "terminal_result",
                lambda value: value.replace("reset", "ordinary-recovery", 1)))
        for token in ("CPU_OFF", "affinity", "query", "inverse", "retry",
                      "provider release", "membership commit"):
            add(f"early-forbidden-{identifier}-{token}",
                lambda identifier=identifier, token=token: _mutate_field(
                    "early", identifier, "forbidden",
                    lambda value, token=token: value.replace(token, "MUTATED", 1)))
    for identifier in VALIDATOR.TABLES["p32"]["ids"]:
        add(f"p32-reset-only-{identifier}",
            lambda identifier=identifier: _mutate_field(
                "p32", identifier, "recovery",
                lambda value: value.replace("reset", "ordinary-recovery", 1)))
        for token in ("CPU_OFF", "affinity", "query", "inverse", "retry",
                      "provider release", "membership commit", "HPS success",
                      "normal runtime continuation"):
            add(f"p32-forbidden-{identifier}-{token}",
                lambda identifier=identifier, token=token: _mutate_field(
                    "p32", identifier, "forbidden",
                    lambda value, token=token: value.replace(token, "MUTATED", 1)))
    add("callback-rollback-config",
        lambda: _mutate_field("callbacks", "H15", "selected_reachability",
                              lambda value: value.replace("=y", "=n")))
    add("callback-fallible-kthread",
        lambda: _mutate_field("callbacks", "H04", "closure_effect",
                              lambda value: value.replace("fallible", "nonfailing")))
    add("callback-fallible-cacheinfo",
        lambda: _mutate_field("callbacks", "H05", "closure_effect",
                              lambda value: value.replace("fallible", "nonfailing")))
    add("callback-absolute-dynamic-slot",
        lambda: _mutate_field("callbacks", "H06", "order_or_scope",
                              lambda value: value + " DYN+0"))

    # Document authorization, correction, index, and roadmap ownership.
    readme = VALIDATOR.README.read_text(encoding="utf-8")
    design = VALIDATOR.DESIGN.read_text(encoding="utf-8")
    membership_readme = (VALIDATOR.ROOT /
        "experiments/2026-08-05-a72-membership-admission-contract/README.md").read_text(encoding="utf-8")
    membership_design = (VALIDATOR.ROOT /
        "experiments/2026-08-05-a72-membership-admission-contract/DESIGN.md").read_text(encoding="utf-8")
    experiment_index = (VALIDATOR.ROOT / "experiments/README.md").read_text(encoding="utf-8")
    roadmap = (VALIDATOR.ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")

    for marker in VALIDATOR.MARKERS:
        add(f"readme-marker-{marker}",
            lambda marker=marker: VALIDATOR.validate_documents(
                readme=readme.replace(marker, "marker-removed", 1), design=design))
        add(f"design-marker-{marker}",
            lambda marker=marker: VALIDATOR.validate_documents(
                readme=readme, design=design.replace(marker, "marker-removed", 1)))

    add("readme-authorizes-cpu-on", lambda: VALIDATOR.validate_documents(
        readme=readme + "\ncpu_on_authorized=yes\n", design=design))
    add("design-authorizes-build", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design + "\nbuild_authorized=yes\n"))
    for phrase in VALIDATOR.FORBIDDEN_AUTHORIZATION_PROSE:
        add(f"readme-authorization-prose-{phrase}",
            lambda phrase=phrase: VALIDATOR.validate_documents(
                readme=readme + f"\n{phrase}.\n", design=design))
        add(f"design-authorization-prose-{phrase}",
            lambda phrase=phrase: VALIDATOR.validate_documents(
                readme=readme, design=design + f"\n{phrase}.\n"))
    add("membership-readme-correction", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design,
        membership_readme=membership_readme.replace(
            "Source-closure correction (2026-08-05)", "Correction removed", 1),
        membership_design=membership_design, experiment_index=experiment_index,
        roadmap=roadmap))
    add("membership-design-correction", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design, membership_readme=membership_readme,
        membership_design=membership_design.replace(
            "Source-closure correction (2026-08-05)", "Correction removed", 1),
        experiment_index=experiment_index, roadmap=roadmap))
    for token in VALIDATOR.MEMBERSHIP_README_TOKENS:
        add(f"membership-readme-token-{token}", lambda token=token:
            VALIDATOR.validate_documents(
                readme=readme, design=design,
                membership_readme=membership_readme.replace(token, "MUTATED"),
                membership_design=membership_design,
                experiment_index=experiment_index, roadmap=roadmap))
    for token in VALIDATOR.MEMBERSHIP_DESIGN_TOKENS:
        add(f"membership-design-token-{token}", lambda token=token:
            VALIDATOR.validate_documents(
                readme=readme, design=design, membership_readme=membership_readme,
                membership_design=membership_design.replace(token, "MUTATED"),
                experiment_index=experiment_index, roadmap=roadmap))
    add("membership-readme-notice-position", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design,
        membership_readme=membership_readme.replace("Current mechanism notice", "Old notice", 1),
        membership_design=membership_design, experiment_index=experiment_index,
        roadmap=roadmap))
    add("membership-design-notice-position", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design, membership_readme=membership_readme,
        membership_design=membership_design.replace("Current mechanism notice", "Old notice", 1),
        experiment_index=experiment_index, roadmap=roadmap))
    add("experiment-index-link", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design, membership_readme=membership_readme,
        membership_design=membership_design,
        experiment_index=experiment_index.replace(
            "2026-08-05-a72-cpu-up-source-closure", "source-closure-removed", 1),
        roadmap=roadmap))
    add("roadmap-a41", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design, membership_readme=membership_readme,
        membership_design=membership_design, experiment_index=experiment_index,
        roadmap=roadmap.replace("A41", "AXX")))
    roadmap_a41 = "1. Implement and mutation-test A41's pre-finalization profile owner"
    roadmap_p32 = "3. Complete A25 and implement P32A/D/F/X/R"
    add("roadmap-source-work-reordered", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design, membership_readme=membership_readme,
        membership_design=membership_design, experiment_index=experiment_index,
        roadmap=_swap_once(roadmap, roadmap_a41, roadmap_p32)), "reordered")
    add("roadmap-build-boundary-inverted", lambda: VALIDATOR.validate_documents(
        readme=readme, design=design, membership_readme=membership_readme,
        membership_design=membership_design, experiment_index=experiment_index,
        roadmap=roadmap.replace("does not\n   authorize a build", "does\n   authorize a build", 1)))
    add("experiment-duplicates-roadmap-order", lambda: VALIDATOR.validate_documents(
        readme=readme + "\nThe next implementation milestone is unsafe.\n", design=design),
        "duplicates ROADMAP ordering")

    # Optional inputs must be explicit, safe, and exact.
    add("relative-source-root", lambda: VALIDATOR.validate_source_root(Path("linux-7.1.3")),
        "absolute")
    add("relative-config", lambda: VALIDATOR.validate_config(Path("kernel.config")),
        "absolute")
    add("source-state-formula", lambda: VALIDATOR.validate_source_state(
        patchset_sha="0" * 64), "source-state identity changed")
    add("audited-source-composition", lambda: VALIDATOR.validate_official_file_composition({
        "arch/arm64/kernel/cpu_ops.c", "kernel/cpu.c"}),
        "file composition changed")
    add("relative-prepared-source-root", lambda: VALIDATOR.validate_prepared_source_root(
        Path("linux-7.1.3-prepared")), "absolute")
    first_patch = "patches/v7.1.3/0001-dt-bindings-reset-mediatek-add-MT6797-infracfg-reset.patch"
    first_patch_bytes = (VALIDATOR.ROOT / first_patch).read_bytes()
    add("non-0092-patch-content-drift", lambda: VALIDATOR.validate_patchset(
        {first_patch: first_patch_bytes + b"\n"}), "patchset content identity changed")

    optional_mutations = 0
    if args.source_root is not None:
        optional_mutations += 1
        add("valid-source-then-corruption", lambda: _copy_and_corrupt_root(
            args.source_root, VALIDATOR.SOURCE_ROOT_FILES, VALIDATOR.validate_source_root))
    if args.prepared_source_root is not None:
        optional_mutations += 1
        add("valid-prepared-source-then-corruption", lambda: _copy_and_corrupt_root(
            args.prepared_source_root, VALIDATOR.PREPARED_ROOT_FILES,
            VALIDATOR.validate_prepared_source_root, copy_marker=True))
    if args.config is not None:
        optional_mutations += 1
        add("valid-config-then-corruption", lambda: _copy_and_corrupt_config(args.config))

    # The report and frozen transcript cannot authorize or drift.
    for key, value in (
        ("implementation", "READY"),
        ("implementation_authorized", "yes"),
        ("cpu_on_authorized", "yes"),
        ("cpu_off_authorized", "yes"),
        ("build_authorized", "yes"),
        ("device_action_authorized", "yes"),
        ("device_action", "deploy"),
        ("current_cpu_boot_veto", "OPTIONAL"),
        ("result", "unsafe"),
    ):
        add(f"report-{key}-{value}",
            lambda key=key, value=value:
            VALIDATOR.validate_authorization(_replace_report(report, key, value)))

    transcript = VALIDATOR.TRANSCRIPT.read_text(encoding="utf-8")
    add("stale-transcript", lambda: VALIDATOR.validate_transcript(
        report, transcript.replace("result=pass", "result=stale", 1)))
    optional_transcript = VALIDATOR.OPTIONAL_TRANSCRIPT.read_text(encoding="utf-8")
    add("stale-optional-transcript", lambda: VALIDATOR.validate_optional_transcript(
        optional_transcript.replace("result=pass", "result=stale", 1)))

    expected_mutations = VALIDATOR.EXPECTED_NEGATIVE_MUTATIONS + optional_mutations
    if len(tests) != expected_mutations:
        raise AssertionError(
            f"mutation inventory changed: expected {expected_mutations}, "
            f"got {len(tests)}"
        )
    for label, action in tests:
        action()

    print("\n".join(VALIDATOR.mutation_report()))
    if optional_mutations:
        print(f"optional_evidence_mutations={optional_mutations}")
    return 0


def _validate_changed_tables(table: str, mutator: Callable[[list[dict[str, str]]], None]) -> None:
    tables = copy.deepcopy(VALIDATOR.load_tables())
    mutator(tables[table])
    VALIDATOR.validate_tables(tables)


def _mutate_field(table: str, identifier: str, field: str,
                  mutator: Callable[[str], str]) -> None:
    tables = copy.deepcopy(VALIDATOR.load_tables())
    target = row(tables, table, identifier)
    changed = mutator(target[field])
    if changed == target[field]:
        raise AssertionError(f"mutation target absent: {table}/{identifier}.{field}")
    target[field] = changed
    VALIDATOR.validate_tables(tables)


def _replace_report(report: list[str], key: str, value: str) -> list[str]:
    prefix = key + "="
    return [prefix + value if line.startswith(prefix) else line for line in report]


def _swap_once(text: str, first: str, second: str) -> str:
    if text.count(first) != 1 or text.count(second) != 1:
        raise AssertionError("swap markers are not unique")
    placeholder = "__A72_SOURCE_ORDER_SWAP__"
    return text.replace(first, placeholder, 1).replace(second, first, 1).replace(
        placeholder, second, 1)


def _copy_and_corrupt_root(source: Path, files: dict[str, str],
                           validator: Callable[[Path], None],
                           copy_marker: bool = False) -> None:
    with tempfile.TemporaryDirectory(prefix="a72-source-closure-") as temporary:
        root = Path(temporary)
        for relative in files.values():
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, destination)
        if copy_marker:
            shutil.copy2(source / ".gemini-source-state", root / ".gemini-source-state")
        first = root / next(iter(files.values()))
        first.write_bytes(first.read_bytes() + b"\n")
        validator(root)


def _copy_and_corrupt_config(config: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="a72-config-closure-") as temporary:
        copied = Path(temporary) / "kernel.config"
        shutil.copy2(config, copied)
        copied.write_bytes(copied.read_bytes() + b"\n")
        VALIDATOR.validate_config(copied)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, VALIDATOR.ContractError) as error:
        print(f"error: {error}", file=__import__("sys").stderr)
        raise SystemExit(1)
