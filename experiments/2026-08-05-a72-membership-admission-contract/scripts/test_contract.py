#!/usr/bin/env python3
"""Adversarial mutation tests for the A72 membership/admission contract."""

from __future__ import annotations

import copy
import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().with_name("validate_contract.py")
SPEC = importlib.util.spec_from_file_location("membership_contract_validator", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("error: cannot load membership contract validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def rows_for(kind: str) -> list[dict[str, str]]:
    path, fields, _, _ = TABLES[kind]
    return VALIDATOR.load_tsv(path, fields)


TABLES = {
    "phase": (VALIDATOR.PHASE, VALIDATOR.PHASE_FIELDS, VALIDATOR.validate_phase,
              VALIDATOR.EXPECTED_PHASE_ROW_SHA256),
    "membership": (VALIDATOR.MEMBERSHIP, VALIDATOR.MEMBERSHIP_FIELDS,
                   VALIDATOR.validate_membership,
                   VALIDATOR.EXPECTED_MEMBERSHIP_ROW_SHA256),
    "provider": (VALIDATOR.PROVIDER, VALIDATOR.PROVIDER_FIELDS,
                 VALIDATOR.validate_provider, VALIDATOR.EXPECTED_PROVIDER_ROW_SHA256),
    "admission": (VALIDATOR.ADMISSION, VALIDATOR.ADMISSION_FIELDS,
                  VALIDATOR.validate_admission, VALIDATOR.EXPECTED_ADMISSION_ROW_SHA256),
}


def row(rows: list[dict[str, str]], identifier: str) -> dict[str, str]:
    return next(item for item in rows if item["id"] == identifier)


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


def with_rehashed_row(
    kind: str, identifier: str, mutator: Callable[[dict[str, str]], None],
    action: Callable[[list[dict[str, str]]], None] | None = None,
) -> None:
    _, fields, validator, expected_hashes = TABLES[kind]
    rows = copy.deepcopy(rows_for(kind))
    changed = row(rows, identifier)
    mutator(changed)
    original = expected_hashes[identifier]
    expected_hashes[identifier] = VALIDATOR.canonical_row_sha256(changed, fields)
    try:
        (validator if action is None else action)(rows)
    finally:
        expected_hashes[identifier] = original


def token_mutation(kind: str, identifier: str, field: str, token: str) -> None:
    def mutate(item: dict[str, str]) -> None:
        if token not in item[field]:
            raise AssertionError(f"test token absent: {kind}/{identifier}.{field}: {token}")
        item[field] = item[field].replace(token, "MUTATED", 1)

    with_rehashed_row(kind, identifier, mutate)


def main() -> int:
    phase = rows_for("phase")
    membership = rows_for("membership")
    provider = rows_for("provider")
    admission = rows_for("admission")
    VALIDATOR.validate_phase(phase)
    VALIDATOR.validate_membership(membership)
    VALIDATOR.validate_provider(provider)
    VALIDATOR.validate_admission(admission)
    VALIDATOR.validate_documents()
    VALIDATOR.validate_evidence()
    report = VALIDATOR.validation_report(phase, membership, provider, admission)
    VALIDATOR.validate_authorization(report)
    VALIDATOR.validate_transcript(report)

    tests: list[tuple[str, Callable[[], None]]] = []

    # Every canonical row has an identity guard independent of the semantic checks.
    for kind, (_, _, validator, _) in TABLES.items():
        for canonical in rows_for(kind):
            identifier = canonical["id"]
            tests.append((
                f"{kind}-row-identity-{identifier}",
                lambda kind=kind, identifier=identifier, validator=validator: expect_rejected(
                    f"{kind}-row-identity-{identifier}",
                    lambda: _row_identity_mutation(kind, identifier, validator),
                ),
            ))

    semantic_tokens = (
        # Phase ordering, one-shot, effect, call-budget, terminal, and reset invariants.
        ("phase", "P01", "token_rule", "P31-same-request-cpu8-up-attempt=consumed"),
        ("phase", "P01", "token_rule", "cpu8-preparation-attempt=one-unconsumed"),
        ("phase", "P02", "token_rule", "before-remaining-A28-prestate-checks"),
        ("phase", "P03", "token_rule", "A31-private-entry-big_on=0x3"),
        ("phase", "P04", "token_rule", "provider-release-attempt=one-unconsumed"),
        ("phase", "P05", "token_rule", "A32-no-cpuhp-provider-or-hardware-effect=pass"),
        ("phase", "P06", "token_rule", "A38-operation-attempt-remains-consumed-until-A34-reset"),
        ("phase", "P07", "allowed_effect", "publish-OFF_COMMITTED-immediately-before"),
        ("phase", "P08", "token_rule", "affinity-level=0"),
        ("phase", "P10", "token_rule", "A33-final-requested-cpuhp-state-and-online-mask"),
        ("phase", "P11", "token_rule", "A38-exact-operation-attempt-remains-consumed"),
        ("phase", "P13", "members_rule", "present-possible-restored"),
        ("phase", "P13", "members_rule", "nonaliased-mpidr-0x200-0x201"),
        ("phase", "P17", "allowed_effect", "no-provider-or-hardware-effect"),
        ("phase", "P19", "token_rule", "every-M02-post-full-bringup-callback-IPI-identity-online-accounting-hit-count"),
        ("phase", "P19", "token_rule", "provider-A33-final-schedule-or-reschedule-failure-is-terminal"),
        ("phase", "P19", "allowed_effect", "no-P10-before-all-M02-proofs-and-sample3"),
        ("phase", "P20", "token_rule", "A40-private-branch-proof-fresh"),
        ("phase", "P20", "token_rule", "A29-concurrency-or-entry-proof=pass"),
        ("phase", "P24", "allowed_effect", "two-argument-psci_ops.cpu_on"),
        ("phase", "P27", "allowed_effect", "BPLL"),
        ("phase", "P28", "allowed_effect", "wait-240us"),
        ("phase", "P29", "allowed_effect", "no-residual-effect"),
        ("phase", "P30", "token_rule", "CPU_STUCK_IN_KERNEL"),
        ("phase", "P30", "allowed_effect", "target-custom-cpu_die"),
        ("phase", "P30", "allowed_effect", "controller-custom-cpu_kill"),
        ("phase", "P31", "token_rule", "observer-capture-window=open"),
        ("phase", "P31", "token_rule", "no-other-predecessor-state-check-before-consumption"),
        ("phase", "P31", "token_rule", "no-generation-or-token-allocated"),
        ("phase", "P31", "token_rule", "later-A36-operation-specific-predecessor-checks=pending"),
        ("phase", "P31", "failure_route", "A28-mismatch-deny-IDLE-without-token"),
        ("phase", "P32", "token_rule", "target-cpu_die-up-token-guard=pass"),
        ("phase", "P32", "token_rule", "controller-cpu_kill-up-token-fault-guard=pass"),
        ("phase", "P32", "allowed_effect", "prevents-CPU_OFF"),
        ("phase", "P32", "allowed_effect", "prevents-affinity"),
        ("phase", "P32", "allowed_effect", "A30-cpuhp-online-mask-divergence"),
        # Membership commit proof and delayed-work lifecycle.
        ("membership", "M01", "commit_gate", "P27-preprovider"),
        ("membership", "M01", "commit_gate", "P28-postprovider"),
        ("membership", "M01", "provider_sequence", "origin-M01-generation"),
        ("membership", "M02", "commit_gate", "P15-secondary-completion"),
        ("membership", "M02", "commit_gate", "after-P15-full-generic-callbacks-complete"),
        ("membership", "M02", "commit_gate", "then-initial-static-delayed-work-schedule=pass"),
        ("membership", "M02", "commit_gate", "then-sample1-about-1s=pass"),
        ("membership", "M02", "commit_gate", "then-reschedule1=pass"),
        ("membership", "M02", "commit_gate", "then-sample2-about-6s=pass"),
        ("membership", "M02", "commit_gate", "then-reschedule2=pass"),
        ("membership", "M02", "commit_gate", "then-sample3-about-10s=pass"),
        ("membership", "M02", "commit_gate", "P10-forbidden-before-sample3-and-all-M02-proofs"),
        ("membership", "M02", "failure_rule", "every-post-full-bringup-callback-IPI-identity-online-accounting-hit-count"),
        ("membership", "M02", "failure_rule", "provider-A33-final-schedule-or-reschedule-failure-enters-P19-FAULT"),
        ("membership", "M02", "failure_rule", "no-runtime-inverse-or-retry"),
        ("membership", "M03", "commit_gate", "A40-private-branch-proof-fresh"),
        ("membership", "M03", "commit_gate", "PWR_CON-and-power-ack=OFF"),
        ("membership", "M03", "commit_gate", "safe-off-C07"),
        ("membership", "M04", "commit_gate", "A40-private-branch-proof-fresh"),
        ("membership", "M04", "commit_gate", "safe-off-L06-through-L13"),
        ("membership", "M04", "provider_sequence", "consume-exact-durable-reference-id"),
        # Provider identity and one-shot synchronous calls.
        ("provider", "R01", "proof", "consume-provider-acquire-attempt-before"),
        ("provider", "R01", "required_context", "P27-preprovider-preparation=complete"),
        ("provider", "R02", "proof", "1ms-settle"),
        ("provider", "R02", "proof", "BUCKB-enabled-page=0x80"),
        ("provider", "R02", "proof", "inherited-VSEL-exact-readback"),
        ("provider", "R02", "proof", "durable-held-reference-id"),
        ("provider", "R03", "proof", "P29-exact-preisolation-rollback-required-before-P21"),
        ("provider", "R04", "proof", "retained-across-transaction-generations"),
        ("provider", "R05", "required_context", "L06-through-L12"),
        ("provider", "R05", "proof", "consume-provider-release-attempt-before"),
        ("provider", "R06", "required_context", "released-reference-id=exact-published-durable-id"),
        ("provider", "R07", "proof", "regulator_is_enabled-is-not-reference-proof"),
        ("provider", "R08", "proof", "provider-state-not-cleared-at-runtime"),
        # Admission, callback, lock, private freshness, and veto blockers.
        ("admission", "A01", "required_context", "CPUHP_OFFLINE"),
        ("admission", "A02", "rule", "deny-tasks_frozen-not-zero"),
        ("admission", "A03", "rule", "never-acquire-a72_transition_lock"),
        ("admission", "A04", "ordering", "priority-strictly-above-gemian-vendor-priority-zero"),
        ("admission", "A05", "ordering", "M01-or-M02-commit-before-HPS-increment"),
        ("admission", "A07", "rule", "all-CPUHVFS-actions-no-op"),
        ("admission", "A08", "required_context", "before-and-after-CPUHP_TEARDOWN_CPU"),
        ("admission", "A09", "required_context", "A40-private-branch-proof-fresh-through-query=pass"),
        ("admission", "A09", "rule", "consume-query-budget-before-call"),
        ("admission", "A09", "rule", "one-level-0-active-affinity-info"),
        ("admission", "A10", "rule", "forbidden-retained-or-nontarget-query"),
        ("admission", "A11", "rule", "no-repeat"),
        ("admission", "A12", "failure", "DEAD-is-not-CPU_OFF-WFI-or-physical-off-proof"),
        ("admission", "A13", "ordering", "unbounded-first-smc"),
        ("admission", "A14", "ordering", "every-applicable-phase-membership-provider-admission-and-lock-row"),
        ("admission", "A14", "ordering", "no-enumerated-subset-can-relax-veto"),
        ("admission", "A16", "rule", "kill-result-not-propagated-to-_cpu_down"),
        ("admission", "A18", "required_context", "provider-not-NONE"),
        ("admission", "A19", "rule", "void-10-second-sync-timeout"),
        ("admission", "A21", "rule", "must-not-acquire-a72_transition_lock"),
        ("admission", "A22", "required_context", "CPUHP_ONLINE"),
        ("admission", "A23", "ordering", "all-startup-cpuhp-callbacks"),
        ("admission", "A24", "rule", "always-deny-unowned-unattested-or-frozen"),
        ("admission", "A25", "required_context", "every-can_rollback_cpu-teardown-branch"),
        ("admission", "A26", "rule", "every-applicable-phase-membership-provider-admission-and-lock-row"),
        ("admission", "A26", "rule", "no-enumerated-subset-can-relax-veto"),
        ("admission", "A26", "rule", "P32"),
        ("admission", "A26", "rule", "R07"),
        ("admission", "A27", "rule", "target-losing-P07-CAS-must-not-issue-CPU_OFF"),
        ("admission", "A28", "rule", "only-generic-entry-invariant"),
        ("admission", "A28", "rule", "operation-specific-predecessor-state-is-later-A36"),
        ("admission", "A28", "ordering", "A28-pass-before-P01-P04-token-and-freeze"),
        ("admission", "A28", "failure", "A36-mismatch-uses-P05-P06"),
        ("admission", "A29", "rule", "concurrent-SMC-lock-deadlock-proof"),
        ("admission", "A30", "rule", "terminal-divergent-state-through-P32"),
        ("admission", "A31", "rule", "arm-A40-complete-writer-caller-exclusion"),
        ("admission", "A32", "rule", "every-failure-after-any-executed-or-uncertain-effect-enters-P23-FAULT"),
        ("admission", "A33", "rule", "generic-return-alone-insufficient"),
        ("admission", "A34", "rule", "present-and-possible-restored"),
        ("admission", "A34", "rule", "cpu_logical_map(cpu8)=0x200"),
        ("admission", "A34", "rule", "cpu_logical_map(cpu9)=0x201"),
        ("admission", "A35", "rule", "do-not-claim-internal-present-mask-immutability"),
        ("admission", "A36", "ordering", "A28-pass-before-P01-P02-token-and-FROZEN"),
        ("admission", "A36", "failure", "A36-failure-before-P17-P18-uses-P05-P06"),
        ("admission", "A37", "rule", "route-P32-terminal-FAULT"),
        ("admission", "A38", "rule", "before-generic-A28-state-mapping-checks"),
        ("admission", "A38", "rule", "A36-predecessor-checks-run-after-P01-P02-token-and-FROZEN-before-P17-P18"),
        ("admission", "A38", "lock_rule", "never-held-across-A36-register-readback"),
        ("admission", "A39", "rule", "bypasses-cpu_can_disable-and-optional-cpu_disable"),
        ("admission", "A39", "rule", "CPU_STUCK_IN_KERNEL-for-52-bit-VA"),
        ("admission", "A40", "rule", "complete-source-and-runtime-private-big_on-writer-caller-inventory"),
        ("admission", "A40", "rule", "non-SMC-reader"),
        ("admission", "A40", "rule", "independent-A29-equivalent-concurrent-SMC-lock-deadlock-proof"),
        ("admission", "A40", "failure", "P23-after-any-executed-or-uncertain-pre-P07-effect"),
        ("admission", "L07", "rule", "never-held-across-sleep"),
        ("admission", "L08", "rule", "release-before-public-cpu_up-or-cpu_down"),
    )
    for kind, identifier, field, token in semantic_tokens:
        label = f"semantic-{kind}-{identifier}-{token}"
        tests.append((
            label,
            lambda kind=kind, identifier=identifier, field=field, token=token,
                   label=label: expect_rejected(
                       label, lambda: token_mutation(kind, identifier, field, token)
                   ),
        ))

    tests.extend(_structural_tests(report))

    if len(tests) != VALIDATOR.EXPECTED_NEGATIVE_MUTATIONS:
        raise AssertionError(
            f"mutation inventory changed: expected {VALIDATOR.EXPECTED_NEGATIVE_MUTATIONS}, "
            f"got {len(tests)}"
        )
    for label, action in tests:
        action()

    print("\n".join(VALIDATOR.mutation_report()))
    return 0


def _row_identity_mutation(
    kind: str, identifier: str, validator: Callable[[list[dict[str, str]]], None]
) -> None:
    rows = copy.deepcopy(rows_for(kind))
    changed = row(rows, identifier)
    field = {
        "phase": "event", "membership": "private_big_on_rule",
        "provider": "event", "admission": "owner",
    }[kind]
    changed[field] += ";identity-mutation"
    validator(rows)


def _structural_tests(report: list[str]) -> list[tuple[str, Callable[[], None]]]:
    tests: list[tuple[str, Callable[[], None]]] = []

    def add(label: str, action: Callable[[], None]) -> None:
        tests.append((label, lambda label=label, action=action: expect_rejected(label, action)))

    add("missing-phase", lambda: VALIDATOR.validate_phase(rows_for("phase")[:-1]))
    add("reordered-phase", lambda: VALIDATOR.validate_phase(list(reversed(rows_for("phase")))))

    def private_in_members() -> None:
        with_rehashed_row("phase", "P03", lambda item: item.update(
            members_rule=item["members_rule"] + ";big_on=members"
        ))
    add("private-ledger-in-members-rule", private_in_members)

    def membership_0x2() -> None:
        with_rehashed_row("membership", "M02", lambda item: item.update(post_members="0x2"))
    add("cpu9-only-membership", membership_0x2)

    def duplicate_acquire() -> None:
        with_rehashed_row("provider", "R03", lambda item: item.update(
            from_state="NONE", to_state="ACQUIRE_INFLIGHT"
        ))
    add("duplicate-provider-acquire", duplicate_acquire)

    def held_across_readback() -> None:
        with_rehashed_row("admission", "L07", lambda item: item.update(
            rule=item["rule"] + ";held-across-readback"
        ))
    add("leaf-held-across-readback", held_across_readback)

    readme = VALIDATOR.README.read_text(encoding="utf-8")
    design = VALIDATOR.DESIGN.read_text(encoding="utf-8")
    add("readme-duplicate-authorization", lambda: VALIDATOR.validate_documents(
        readme + "\nimplementation_authorized=yes\n", design
    ))
    add("design-duplicate-authorization", lambda: VALIDATOR.validate_documents(
        readme, design + "\ncpu_off_authorized=yes\n"
    ))
    add("readme-loses-p32", lambda: VALIDATOR.validate_documents(
        readme.replace("P32", "PXX"), design
    ))
    add("design-loses-a40", lambda: VALIDATOR.validate_documents(
        readme, design.replace("A40 must prove that the\nbranch value remains fresh",
                               "freshness omitted")
    ))
    add("design-authorizes-cpu-on", lambda: VALIDATOR.validate_documents(
        readme, design + "\nCPU_ON is authorized.\n"
    ))

    for provenance_hash in VALIDATOR.README_PROVENANCE_SHA256:
        add(
            f"readme-provenance-{provenance_hash[:12]}",
            lambda provenance_hash=provenance_hash: VALIDATOR.validate_documents(
                readme.replace(provenance_hash, "f" * 64, 1), design
            ),
        )

    for source_identity in VALIDATOR.README_SOURCE_IDENTITIES:
        add(
            f"readme-source-identity-{source_identity[-12:]}",
            lambda source_identity=source_identity: VALIDATOR.validate_documents(
                readme.replace(source_identity, "mutated-source-identity", 1), design
            ),
        )

    source_audit = next(key for key in VALIDATOR.EVIDENCE_SHA256
                        if key.endswith("source-order-audit-20260805.txt") and
                        "membership-admission" in key)
    def evidence_hash() -> None:
        original = VALIDATOR.EVIDENCE_SHA256[source_audit]
        VALIDATOR.EVIDENCE_SHA256[source_audit] = "0" * 64
        try:
            VALIDATOR.validate_evidence()
        finally:
            VALIDATOR.EVIDENCE_SHA256[source_audit] = original
    add("source-audit-hash", evidence_hash)

    cpu9_design = next(key for key in VALIDATOR.EVIDENCE_SHA256
                       if key.endswith("a72-cpu9-cluster-reuse/DESIGN.md"))
    def predecessor_hash() -> None:
        original = VALIDATOR.EVIDENCE_SHA256[cpu9_design]
        VALIDATOR.EVIDENCE_SHA256[cpu9_design] = "0" * 64
        try:
            VALIDATOR.validate_evidence()
        finally:
            VALIDATOR.EVIDENCE_SHA256[cpu9_design] = original
    add("cpu9-predecessor-hash", predecessor_hash)

    transcript = VALIDATOR.TRANSCRIPT.read_text(encoding="utf-8")
    add("stale-transcript", lambda: VALIDATOR.validate_transcript(
        report, transcript.replace("result=pass", "result=stale", 1)
    ))

    for key, value in (
        ("implementation", "READY"), ("implementation_authorized", "yes"),
        ("cpu_off_authorized", "yes"), ("build_authorized", "yes"),
        ("device_action_authorized", "yes"), ("device_action", "deploy"),
        ("current_cpu_boot_veto", "OPTIONAL"),
        ("current_cpu_disable_veto", "OPTIONAL"),
        ("all_applicable_contract_rows_for_veto_relaxation", "OPTIONAL"),
    ):
        add(f"report-{key}-{value}", lambda key=key, value=value:
            VALIDATOR.validate_authorization(report + [f"{key}={value}"]))
    return tests


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, VALIDATOR.ContractError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
