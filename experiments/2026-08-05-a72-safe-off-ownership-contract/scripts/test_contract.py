#!/usr/bin/env python3
"""Adversarial tests for the frozen A72 safe-off ownership contract."""

from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
from pathlib import Path
from typing import Callable


sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().with_name("validate_contract.py")
SPEC = importlib.util.spec_from_file_location("safe_off_contract_validator", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("error: cannot load contract validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
RESULT = VALIDATOR.EXPERIMENT / "results" / "contract-validation-20260805.txt"


def contract_rows() -> list[dict[str, str]]:
    return VALIDATOR.load_tsv(VALIDATOR.CONTRACT, VALIDATOR.CONTRACT_FIELDS)


def reconciliation_rows() -> list[dict[str, str]]:
    return VALIDATOR.load_tsv(
        VALIDATOR.RECONCILIATION, VALIDATOR.RECONCILIATION_FIELDS
    )


def mutate_row(rows: list[dict[str, str]], identifier: str, **changes: str) -> None:
    for row in rows:
        if row.get("id") == identifier or row.get("source_id") == identifier:
            row.update(changes)
            return
    raise AssertionError(f"missing mutation row {identifier}")


def expect_rejected(
    label: str, expected_error: str, action: Callable[[], None]
) -> None:
    try:
        action()
    except VALIDATOR.ContractError as error:
        if expected_error not in str(error):
            raise AssertionError(
                f"wrong rejection for {label}: expected {expected_error!r}, got {error!s}"
            ) from error
        return
    raise AssertionError(f"mutation accepted: {label}")


def check_contract_mutation(
    label: str,
    expected_error: str,
    mutator: Callable[[list[dict[str, str]]], None],
) -> None:
    rows = copy.deepcopy(contract_rows())
    mutator(rows)
    expect_rejected(
        label, expected_error, lambda: VALIDATOR.validate_contract(rows)
    )


def check_reconciliation_mutation(
    label: str,
    expected_error: str,
    mutator: Callable[[list[dict[str, str]]], None],
) -> None:
    rows = copy.deepcopy(reconciliation_rows())
    mutator(rows)
    expect_rejected(
        label, expected_error, lambda: VALIDATOR.validate_reconciliation(rows)
    )


def check_parser_mutation(label: str, expected_error: str, content: str) -> None:
    with tempfile.TemporaryDirectory(prefix="gemini-safe-off-contract-") as directory:
        path = Path(directory) / "mutated.tsv"
        path.write_text(content, encoding="utf-8")
        expect_rejected(
            label,
            expected_error,
            lambda: VALIDATOR.load_tsv(path, VALIDATOR.CONTRACT_FIELDS),
        )


def main() -> int:
    base_contract = contract_rows()
    base_reconciliation = reconciliation_rows()
    VALIDATOR.validate_contract(base_contract)
    VALIDATOR.validate_reconciliation(base_reconciliation)
    VALIDATOR.validate_evidence()
    base_report = VALIDATOR.validation_report(base_contract, base_reconciliation)
    VALIDATOR.validate_authorization(base_report)

    mutations: list[tuple[str, Callable[[], None]]] = []

    mutations.append(
        (
            "new-cpu-off-authorization",
            lambda: expect_rejected(
                "new-cpu-off-authorization",
                "blocking authorization markers changed",
                lambda: VALIDATOR.validate_authorization(
                    [
                        "cpu_off_candidate_authorized=yes"
                        if line == "cpu_off_candidate_authorized=no"
                        else line
                        for line in base_report
                    ]
                ),
            ),
        )
    )

    def add_contract(
        label: str,
        expected_error: str,
        mutator: Callable[[list[dict[str, str]]], None],
    ) -> None:
        mutations.append(
            (
                label,
                lambda: check_contract_mutation(label, expected_error, mutator),
            )
        )

    def add_reconciliation(
        label: str,
        expected_error: str,
        mutator: Callable[[list[dict[str, str]]], None],
    ) -> None:
        mutations.append(
            (
                label,
                lambda: check_reconciliation_mutation(
                    label, expected_error, mutator
                ),
            )
        )

    add_contract(
        "missing-boundary", "boundary inventory changed", lambda rows: rows.pop(0)
    )
    add_contract(
        "reordered-boundaries",
        "boundary inventory changed",
        lambda rows: rows.reverse(),
    )
    add_contract(
        "duplicate-boundary",
        "duplicate boundary",
        lambda rows: mutate_row(rows, "C02", boundary=rows[0]["boundary"]),
    )
    add_contract(
        "empty-prestate",
        "empty field in C01",
        lambda rows: mutate_row(rows, "C01", required_prestate=""),
    )
    add_contract(
        "empty-readback",
        "empty field in L09",
        lambda rows: mutate_row(rows, "L09", success_readback=""),
    )
    add_contract(
        "empty-timeout",
        "empty field in C05",
        lambda rows: mutate_row(rows, "C05", timeout=""),
    )
    add_contract(
        "invalid-decision",
        "invalid decision in C04",
        lambda rows: mutate_row(rows, "C04", decision="eligible"),
    )
    add_contract(
        "unresolved-owner-promoted",
        "unresolved owner promoted in L11",
        lambda rows: mutate_row(rows, "L11", decision="contract-defined"),
    )
    add_contract(
        "unresolved-timeout-promoted",
        "unresolved timeout promoted in C06",
        lambda rows: mutate_row(rows, "C06", decision="contract-defined"),
    )
    add_contract(
        "pre-psci-guessed-inverse",
        "pre-PSCI inverse changed in C02",
        lambda rows: mutate_row(rows, "C02", inverse="none-after-psci"),
    )
    add_contract(
        "post-psci-retry-inverse",
        "guessed post-PSCI inverse in C04",
        lambda rows: mutate_row(rows, "C04", inverse="retry-cpu-on"),
    )
    add_contract(
        "post-psci-optional-retry-response",
        "failure response changed in C04",
        lambda rows: mutate_row(
            rows,
            "C04",
            failure_response="retry-cpu-on;reset-only-optional",
        ),
    )
    add_contract(
        "cpu9-shared-dcm-write",
        "CPU9-off touches shared teardown in C07",
        lambda rows: mutate_row(rows, "C07", boundary="mp2-dcm-disable"),
    )
    add_contract(
        "cpu9-invariance-writer",
        "CPU9 shared-state invariant gained a writer",
        lambda rows: mutate_row(
            rows, "C07", physical_writer="linux-a72-state-machine"
        ),
    )
    add_contract(
        "cpu9-cluster-notifier-entry",
        "CPU9 non-last notifier prohibition missing",
        lambda rows: mutate_row(
            rows, "C03", success_readback="cluster-off-notifier=entered"
        ),
    )
    add_contract(
        "cpu9-contradictory-notifier",
        "CPU9 notifier readback is contradictory",
        lambda rows: mutate_row(
            rows,
            "C03",
            success_readback=(
                next(row for row in rows if row["id"] == "C03")["success_readback"]
                + ";cluster-off-notifier=entered"
            ),
        ),
    )
    target_source_tokens = (
        "preparation=exact-source-closed",
        "gic-deactivation=exact-source-closed",
        "cache-maintenance=exact-source-closed",
        "wfi-entry=exact-source-closed",
        "no-a72-mtcmos-teardown",
    )
    for token in target_source_tokens:
        add_contract(
            f"cpu9-target-source-missing-{token}",
            f"target CPU_OFF source path missing {token} in C04",
            lambda rows, token=token: mutate_row(
                rows,
                "C04",
                required_prestate=next(
                    row for row in rows if row["id"] == "C04"
                )["required_prestate"].replace(token, "removed", 1),
            ),
        )
    add_contract(
        "target-falsely-tears-down-mtcmos",
        "target CPU_OFF falsely gained MTCMOS teardown in C04",
        lambda rows: mutate_row(
            rows,
            "C04",
            success_readback=next(
                row for row in rows if row["id"] == "C04"
            )["success_readback"].replace(
                "no-a72-mtcmos-teardown", "a72-mtcmos-teardown=performed", 1
            ),
        ),
    )
    add_contract(
        "passive-affinity-info",
        "AFFINITY_INFO was made passive in C05",
        lambda rows: mutate_row(rows, "C05", physical_writer="none-observation"),
    )
    add_contract(
        "false-complete-affinity-timeout",
        "timeout changed in C05",
        lambda rows: mutate_row(rows, "C05", timeout="10x10ms-affinity-polls"),
    )
    add_contract(
        "replay-by-query-assumption",
        "AFFINITY_INFO replay control misattributed in C05",
        lambda rows: mutate_row(
            rows,
            "C05",
            required_prestate=next(
                row for row in rows if row["id"] == "C05"
            )["required_prestate"].replace(
                "hardware-replay-control=firmware-private-big_on-not-query-count",
                "hardware-replay-control=query-count",
                1,
            ),
        ),
    )
    cpu9_effect_tokens = (
        "cpu9-pwr-con-0x10006244=clear-bit2-then-bit0",
        "diagnostic-0x10222400=write-0x0000001b",
        "diagnostic-0x10222404=read-twice",
        "firmware-private-big_on-transition=0x3-to-0x1",
        "cluster-power-write-set=empty",
        "clock-write-set=empty",
        "cci-write-set=empty",
        "spm-shared-write-set=empty",
        "provider-write-set=empty",
    )
    for token in cpu9_effect_tokens:
        add_contract(
            f"cpu9-effect-missing-{token}",
            f"CPU9 power_off_big effect missing {token}",
            lambda rows, token=token: mutate_row(
                rows,
                "C05",
                success_readback=next(
                    row for row in rows if row["id"] == "C05"
                )["success_readback"].replace(token, "removed", 1),
            ),
        )
    add_contract(
        "false-empty-all-shared-write-set",
        "CPU9 secure-control writes were hidden by an empty shared set",
        lambda rows: mutate_row(
            rows,
            "C05",
            success_readback=(
                next(row for row in rows if row["id"] == "C05")["success_readback"]
                + ";all-shared-write-set=empty"
            ),
        ),
    )
    add_contract(
        "cpu9-cluster-effect",
        "CPU9 power_off_big effect missing cluster-power-write-set=empty",
        lambda rows: mutate_row(
            rows,
            "C05",
            success_readback=next(
                row for row in rows if row["id"] == "C05"
            )["success_readback"].replace(
                "cluster-power-write-set=empty",
                "cluster-power-write-set=teardown",
                1,
            ),
        ),
    )
    add_contract(
        "retained-cpu8-affinity-query",
        "retained CPU8 was queried through active AFFINITY_INFO",
        lambda rows: mutate_row(
            rows,
            "C05",
            success_readback=(
                next(row for row in rows if row["id"] == "C05")["success_readback"]
                + ";cpu8-affinity-info-level0=on"
            ),
        ),
    )
    add_contract(
        "already-off-cpu9-affinity-query",
        "already-off CPU9 was requeried through active AFFINITY_INFO",
        lambda rows: mutate_row(
            rows,
            "L05",
            success_readback=(
                next(row for row in rows if row["id"] == "L05")["success_readback"]
                + ";cpu9-affinity-info-level0=off"
            ),
        ),
    )

    last_core_effect_tokens = (
        "cpu8-pwr-con-0x10006240=clear-bit2-then-bit0",
        "firmware-private-big_on-transition=0x1-to-0x0",
        "cci-snoop-dvm=withdrawn",
        "cluster-snoop-control-0x10396000=exact-source-attributed",
        "internal-bus-protection-0x10001234=or-0x00000444",
        "b-mux-0x1001a270=clear-bit0",
        "b-pll-0x102224a0=clear-bit0",
        "spm-0x10006218=set-bit4-clear-bit2-then-bit0",
        "spm-0x10006290=or-0x2",
    )
    for token in last_core_effect_tokens:
        add_contract(
            f"last-core-effect-missing-{token}",
            f"last-core power_off_big effect missing {token}",
            lambda rows, token=token: mutate_row(
                rows,
                "L05",
                success_readback=next(
                    row for row in rows if row["id"] == "L05"
                )["success_readback"].replace(token, "removed", 1),
            ),
        )
    add_contract(
        "last-core-isolation-source-missing",
        "last-core isolation source attribution missing",
        lambda rows: mutate_row(
            rows,
            "L10",
            success_readback=next(
                row for row in rows if row["id"] == "L10"
            )["success_readback"].replace(
                "spm-0x10006290-source-operation=or-0x2", "removed", 1
            ),
        ),
    )
    add_contract(
        "responsiveness-before-affinity",
        "CPU8 responsiveness gate precedes active affinity teardown",
        lambda rows: mutate_row(rows, "C05", proof_order="6"),
    )
    add_contract(
        "membership-commit-before-invariance",
        "CPU9 membership commits before invariance gates",
        lambda rows: mutate_row(rows, "C08", proof_order="7"),
    )
    add_contract(
        "shared-teardown-before-affinity",
        "last-user post-query attribution gate precedes active teardown in L06",
        lambda rows: mutate_row(rows, "L05", proof_order="7"),
    )
    add_contract(
        "provider-promoted",
        "unimplemented writable provider was promoted",
        lambda rows: mutate_row(rows, "L13", decision="contract-defined"),
    )
    add_contract(
        "last-notifier-promoted",
        "last-user notifier owner was promoted",
        lambda rows: mutate_row(rows, "L03", decision="contract-defined"),
    )
    add_contract(
        "scenario-changed",
        "scenario proof order changed",
        lambda rows: mutate_row(rows, "C07", scenario="last-a72-off"),
    )

    entry_tokens = (
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
        "firmware-private-big_on-entry-proof=unresolved",
        "all-resource-readbacks-owner-attributed",
    )
    for token in entry_tokens:
        add_contract(
            f"cpu9-entry-missing-{token}",
            f"CPU9 entry snapshot missing {token}",
            lambda rows, token=token: mutate_row(
                rows,
                "C02",
                success_readback=next(
                    row for row in rows if row["id"] == "C02"
                )["success_readback"].replace(token, "removed", 1),
            ),
        )

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
        token = f"{field}=bit-exact-C02-entry"
        add_contract(
            f"cpu9-invariance-missing-{field}",
            f"CPU9 invariance missing {field}",
            lambda rows, token=token: mutate_row(
                rows,
                "C07",
                success_readback=next(
                    row for row in rows if row["id"] == "C07"
                )["success_readback"].replace(token, "removed", 1),
            ),
        )

    final_cpu9_tokens = (
        "cpu8=online",
        "cpu9=offline",
        "members=0x1",
        "firmware-private-big_on=0x1-source-attributed",
        "provider-ref=1",
        "shared-resource-state=bit-exact-C02-entry",
        "policy-admission=released",
        "suspend-admission=released",
        "transition-lock=released",
        "transaction=consumed",
        "cpu9-on-off-admission=closed-until-owned-transition",
    )
    for token in final_cpu9_tokens:
        add_contract(
            f"cpu9-terminal-missing-{token}",
            f"CPU9 terminal commit missing {token}",
            lambda rows, token=token: mutate_row(
                rows,
                "C08",
                success_readback=next(
                    row for row in rows if row["id"] == "C08"
                )["success_readback"].replace(token, "removed", 1),
            ),
        )

    provider_release_tokens = (
        "provider-ref=0",
        "buckb-enable=0",
        "page=0x80",
        "buckb-vsel=transaction-captured",
        "no-vsel-write",
    )
    for token in provider_release_tokens:
        add_contract(
            f"provider-release-missing-{token}",
            f"provider release missing {token}",
            lambda rows, token=token: mutate_row(
                rows,
                "L13",
                success_readback=next(
                    row for row in rows if row["id"] == "L13"
                )["success_readback"].replace(token, "removed", 1),
            ),
        )

    add_contract(
        "cpu9-suspend-interlock-not-held",
        "CPU9 suspend interlock was not held to final commit",
        lambda rows: mutate_row(
            rows,
            "C08",
            required_prestate=next(
                row for row in rows if row["id"] == "C08"
            )["required_prestate"].replace("suspend-admission=frozen", "removed", 1),
        ),
    )
    add_contract(
        "last-suspend-interlock-not-acquired",
        "last-user suspend interlock was not acquired",
        lambda rows: mutate_row(
            rows,
            "L02",
            success_readback=next(
                row for row in rows if row["id"] == "L02"
            )["success_readback"].replace("suspend-admission=frozen", "removed", 1),
        ),
    )
    add_contract(
        "last-suspend-interlock-not-held",
        "last-user suspend interlock was not held to final commit",
        lambda rows: mutate_row(
            rows,
            "L14",
            required_prestate=next(
                row for row in rows if row["id"] == "L14"
            )["required_prestate"].replace("suspend-admission=frozen", "removed", 1),
        ),
    )
    add_contract(
        "last-suspend-interlock-not-released",
        "last-user suspend interlock was not released",
        lambda rows: mutate_row(
            rows,
            "L14",
            success_readback=next(
                row for row in rows if row["id"] == "L14"
            )["success_readback"].replace("suspend-admission=released", "removed", 1),
        ),
    )
    add_contract(
        "last-transaction-not-consumed",
        "last-user transaction was not consumed",
        lambda rows: mutate_row(
            rows,
            "L14",
            success_readback=next(
                row for row in rows if row["id"] == "L14"
            )["success_readback"].replace("transaction=consumed", "removed", 1),
        ),
    )
    add_contract(
        "last-cpu-admission-not-closed",
        "last-user CPU admission was not closed",
        lambda rows: mutate_row(
            rows,
            "L14",
            success_readback=next(
                row for row in rows if row["id"] == "L14"
            )["success_readback"].replace(
                "cpu-on-off-admission=closed-until-owned-transition", "removed", 1
            ),
        ),
    )
    add_contract(
        "pll-off-assumed",
        "last-user secure state assumes PLL-off",
        lambda rows: mutate_row(
            rows,
            "L06",
            success_readback=next(
                row for row in rows if row["id"] == "L06"
            )["success_readback"].replace("pll-off-not-assumed", "pll=off", 1),
        ),
    )
    add_contract(
        "sram-requester-promoted",
        "unresolved SRAM requester was invented",
        lambda rows: mutate_row(
            rows, "L11", requester="linux-a72-state-machine-affinity-info"
        ),
    )
    add_contract(
        "weak-nonempty-prestate",
        "canonical contract row changed in C01",
        lambda rows: mutate_row(rows, "C01", required_prestate="lock-held"),
    )
    add_contract(
        "weak-nonempty-readback",
        "AFFINITY_INFO completion result missing in L05",
        lambda rows: mutate_row(
            rows, "L05", success_readback="cpu8-affinity-info-level0=off"
        ),
    )
    add_contract(
        "changed-evidence-narrative",
        "canonical contract row changed in C04",
        lambda rows: mutate_row(rows, "C04", evidence="generic-psci-exists"),
    )

    def swap_last_boundaries(rows: list[dict[str, str]]) -> None:
        l05 = next(row for row in rows if row["id"] == "L05")
        l06 = next(row for row in rows if row["id"] == "L06")
        l05["boundary"], l06["boundary"] = l06["boundary"], l05["boundary"]

    add_contract(
        "swapped-affinity-and-secure-boundaries",
        "AFFINITY_INFO teardown boundary missing in L05",
        swap_last_boundaries,
    )

    add_reconciliation(
        "missing-reconciliation",
        "reconciliation inventory changed",
        lambda rows: rows.pop(),
    )
    add_reconciliation(
        "preiso-reopened",
        "disposition changed in source row 06",
        lambda rows: mutate_row(
            rows, "06", current_disposition="blocked-postiso-owner"
        ),
    )
    add_reconciliation(
        "cpu9-off-falsely-closed",
        "disposition changed in source row 18",
        lambda rows: mutate_row(
            rows, "18", current_disposition="startup-and-off-closed"
        ),
    )
    add_reconciliation(
        "resume-owner-promoted",
        "disposition changed in source row 19",
        lambda rows: mutate_row(rows, "19", current_disposition="resume-closed"),
    )
    add_reconciliation(
        "absolute-evidence-substitution",
        "evidence path changed in source row 08",
        lambda rows: mutate_row(rows, "08", evidence_path="/private/evidence"),
    )
    add_reconciliation(
        "unrelated-existing-evidence",
        "evidence path changed in source row 18",
        lambda rows: mutate_row(rows, "18", evidence_path="docs/SAFETY.md"),
    )
    add_reconciliation(
        "duplicate-reconciliation-boundary",
        "duplicate reconciliation boundary",
        lambda rows: mutate_row(rows, "04", boundary=rows[0]["boundary"]),
    )
    add_reconciliation(
        "changed-reconciliation-narrative",
        "canonical reconciliation row changed in 10",
        lambda rows: mutate_row(rows, "10", remaining_gap="none"),
    )

    contract_lines = VALIDATOR.CONTRACT.read_text(encoding="utf-8").splitlines()
    extra_cell = "\n".join((contract_lines[0], contract_lines[1] + "\textra")) + "\n"
    mutations.append(
        (
            "extra-tsv-cell",
            lambda: check_parser_mutation(
                "extra-tsv-cell", "extra TSV cell", extra_cell
            ),
        )
    )
    untrimmed = "\n".join(
        (contract_lines[0], contract_lines[1].replace("C01\t", " C01\t", 1))
    ) + "\n"
    mutations.append(
        (
            "untrimmed-tsv-field",
            lambda: check_parser_mutation(
                "untrimmed-tsv-field", "untrimmed id", untrimmed
            ),
        )
    )

    for _, mutation in mutations:
        mutation()

    mutation_report = [
        "validation=a72-safe-off-contract-mutations",
        f"negative_mutations={len(mutations)}-rejected",
        "cpu_off_candidate_authorized=no",
        "result=pass",
    ]
    expected_transcript = "\n".join(
        base_report
        + mutation_report
    ) + "\n"
    actual_transcript = RESULT.read_text(encoding="utf-8")
    if actual_transcript != expected_transcript:
        raise AssertionError("saved validation transcript is stale")

    print("\n".join(mutation_report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
