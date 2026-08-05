#!/usr/bin/env python3
"""Adversarial tests for the independent A41 evidence-owner oracle."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import fields as dataclass_fields
from dataclasses import replace as dataclass_replace
from pathlib import Path

sys.dont_write_bytecode = True

ORACLE_PATH = Path(__file__).resolve().with_name("owner_oracle.py")
SPEC = importlib.util.spec_from_file_location("a41_owner_oracle", ORACLE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load owner oracle")
ORACLE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ORACLE
SPEC.loader.exec_module(ORACLE)


# The test owns this expected inventory independently so weakening the oracle's
# completeness set is observable.
EXPECTED_FIELDS = frozenset(
    {
        "midr-revidr",
        "aarch64-id-registers",
        "aarch32-id-registers",
        "ctr-clidr",
        "gic-local-interface",
        "hyp-ich",
        "firmware-wa1",
        "firmware-wa2",
        "firmware-wa3",
        "asid",
        "translation-granule",
        "va-range",
        "boot-capabilities",
        "system-capabilities",
        "native-hwcap",
        "compat-hwcap",
    }
)


class OwnerOracleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.targets = (
            ORACLE.TargetIdentity(logical_cpu=8, mpidr=0x200),
            ORACLE.TargetIdentity(logical_cpu=9, mpidr=0x201),
        )
        self.generation = "boot-generation-20260805"
        self.identities = ORACLE.IdentityPairs(
            resolved_config="config-a",
            running_config="config-a",
            built_image="image-a",
            running_image="image-a",
            expected_cmdline="cmdline-a",
            running_cmdline="cmdline-a",
        )

    def owner(self) -> ORACLE.CoreOwner:
        return ORACLE.CoreOwner(self.targets, self.generation)

    def sealed_owner(self) -> ORACLE.CoreOwner:
        owner = self.owner()
        state = owner.seal()
        self.assertEqual(state.state, ORACLE.SealState.SEALED_EMPTY)
        self.assertTrue(state.sealed)
        self.assertEqual(state.private_origin, ORACLE.Origin.NONE)
        self.assertIsNone(state.seal_identity)
        return owner

    def evidence(self) -> tuple[ORACLE.EvidenceItem, ...]:
        # Equal payload values are legal: record attribution, not incidental
        # register asymmetry, distinguishes the two targets.
        return tuple(
            ORACLE.EvidenceItem(name=name, value=f"opaque:{name}")
            for name in sorted(EXPECTED_FIELDS)
        )

    def record(
        self,
        slot: int,
        *,
        actual_identity: ORACLE.TargetIdentity | None = None,
        identity_pair: tuple[ORACLE.TargetIdentity, ORACLE.TargetIdentity] | None = None,
        generation: str | None = None,
        sample_id: str | None = None,
        evidence: tuple[ORACLE.EvidenceItem, ...] | None = None,
    ) -> ORACLE.TargetRecord:
        return ORACLE.TargetRecord(
            slot=slot,
            actual_identity=(
                actual_identity if actual_identity is not None else self.targets[slot]
            ),
            identity_pair=(identity_pair if identity_pair is not None else self.targets),
            generation=generation if generation is not None else self.generation,
            sample_id=sample_id if sample_id is not None else f"sample-{slot}",
            evidence=evidence if evidence is not None else self.evidence(),
        )

    def submission(
        self,
        origin: ORACLE.Origin = ORACLE.Origin.FIXTURE,
        *,
        records: tuple[ORACLE.TargetRecord, ...] | None = None,
        identities: ORACLE.IdentityPairs | None = None,
        generation: str | None = None,
    ) -> ORACLE.ProfileSubmission:
        return ORACLE.ProfileSubmission(
            origin=origin,
            generation=generation if generation is not None else self.generation,
            identities=identities if identities is not None else self.identities,
            records=(
                records
                if records is not None
                else (self.record(0), self.record(1))
            ),
        )

    def test_completeness_contract_is_independent_and_exact(self) -> None:
        self.assertEqual(ORACLE.required_target_fields(), EXPECTED_FIELDS)

    def test_core_starts_open_and_preseal_profile_is_blocked(self) -> None:
        owner = self.owner()
        self.assertEqual(owner.snapshot().state, ORACLE.SealState.OPEN)

        verdict = owner.evaluate(self.submission())
        self.assertEqual(verdict.seal_state, ORACLE.SealState.OPEN)
        self.assertFalse(verdict.structurally_valid)
        self.assertFalse(verdict.evaluated)
        self.assertFalse(verdict.sealed)
        self.assertFalse(verdict.counts_as_runtime)
        self.assertFalse(verdict.production_ready)
        self.assertEqual(
            verdict.blockers,
            frozenset(
                {
                    ORACLE.Blocker.RUNTIME_EVIDENCE_NOT_SEALED,
                    ORACLE.Blocker.TARGET_PROVIDER_UNAVAILABLE,
                }
            ),
        )

    def test_none_origin_is_blocked_by_sealed_empty_record(self) -> None:
        owner = self.sealed_owner()
        verdict = owner.evaluate(ORACLE.ProfileSubmission(ORACLE.Origin.NONE))
        self.assertEqual(verdict.seal_state, ORACLE.SealState.SEALED_EMPTY)
        self.assertTrue(verdict.structurally_valid)
        self.assertFalse(verdict.evaluated)
        self.assertTrue(verdict.sealed)
        self.assertFalse(verdict.counts_as_runtime)
        self.assertFalse(verdict.production_ready)
        self.assertEqual(
            verdict.blockers,
            frozenset(
                {
                    ORACLE.Blocker.ORIGIN_NONE,
                    ORACLE.Blocker.PRIVATE_RECORD_EMPTY,
                    ORACLE.Blocker.TARGET_PROVIDER_UNAVAILABLE,
                }
            ),
        )

    def test_none_origin_cannot_carry_evidence(self) -> None:
        claimed = self.submission(ORACLE.Origin.NONE)
        with self.assertRaisesRegex(ORACLE.OracleRejected, "origin-none-with-evidence"):
            self.sealed_owner().evaluate(claimed)

    def test_complete_fixture_evaluates_but_never_counts_runtime(self) -> None:
        owner = self.sealed_owner()
        verdict = owner.evaluate(self.submission())
        state = owner.snapshot()

        self.assertEqual(verdict.seal_state, ORACLE.SealState.SEALED_EMPTY)
        self.assertTrue(verdict.structurally_valid)
        self.assertTrue(verdict.evaluated)
        self.assertTrue(verdict.sealed)
        self.assertFalse(verdict.counts_as_runtime)
        self.assertFalse(verdict.production_ready)
        self.assertIsNotNone(verdict.evaluation_identity)
        self.assertEqual(state.state, ORACLE.SealState.SEALED_EMPTY)
        self.assertEqual(state.private_origin, ORACLE.Origin.NONE)
        self.assertIsNone(state.seal_identity)
        self.assertEqual(
            verdict.blockers,
            frozenset(
                {
                    ORACLE.Blocker.FIXTURE_IS_NOT_RUNTIME,
                    ORACLE.Blocker.PRIVATE_RECORD_EMPTY,
                    ORACLE.Blocker.TARGET_PROVIDER_UNAVAILABLE,
                }
            ),
        )

    def test_profile_declared_runtime_has_no_positive_path(self) -> None:
        owner = self.sealed_owner()
        verdict = owner.evaluate(self.submission(ORACLE.Origin.RUNTIME))

        self.assertEqual(verdict.seal_state, ORACLE.SealState.SEALED_EMPTY)
        self.assertFalse(verdict.structurally_valid)
        self.assertFalse(verdict.evaluated)
        self.assertTrue(verdict.sealed)
        self.assertFalse(verdict.counts_as_runtime)
        self.assertFalse(verdict.production_ready)
        self.assertTrue(owner.snapshot().sealed)
        self.assertEqual(owner.snapshot().private_origin, ORACLE.Origin.NONE)
        self.assertEqual(
            verdict.blockers,
            frozenset(
                {
                    ORACLE.Blocker.PROFILE_RUNTIME_IS_UNATTESTED,
                    ORACLE.Blocker.PRIVATE_RECORD_EMPTY,
                    ORACLE.Blocker.TARGET_PROVIDER_UNAVAILABLE,
                }
            ),
        )

    def test_no_profile_origin_can_reach_production(self) -> None:
        cases = (
            ORACLE.ProfileSubmission(ORACLE.Origin.NONE),
            self.submission(ORACLE.Origin.FIXTURE),
            self.submission(ORACLE.Origin.RUNTIME),
        )
        for submission in cases:
            with self.subTest(origin=submission.origin.value):
                owner = self.sealed_owner()
                verdict = owner.evaluate(submission)
                self.assertFalse(verdict.counts_as_runtime)
                self.assertFalse(verdict.production_ready)
                self.assertNotEqual(owner.snapshot().state, ORACLE.SealState.SEALED_RUNTIME)

    def test_both_target_records_are_required(self) -> None:
        incomplete = self.submission(records=(self.record(0),))
        with self.assertRaisesRegex(ORACLE.OracleRejected, "target-record-count"):
            self.sealed_owner().evaluate(incomplete)

    def test_every_target_field_is_required(self) -> None:
        items = self.evidence()[:-1]
        incomplete = self.submission(
            records=(self.record(0, evidence=items), self.record(1))
        )
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "target-evidence-incomplete:0"
        ):
            self.sealed_owner().evaluate(incomplete)

    def test_empty_duplicate_and_unexpected_evidence_are_rejected(self) -> None:
        base = self.evidence()
        cases = {
            "value": base[:-1]
            + (ORACLE.EvidenceItem(base[-1].name, ""),),
            "duplicate": base + (base[-1],),
            "incomplete": base[:-1]
            + (ORACLE.EvidenceItem("invented-field", "opaque"),),
        }
        for reason, items in cases.items():
            with self.subTest(reason=reason):
                submission = self.submission(
                    records=(self.record(0, evidence=items), self.record(1))
                )
                with self.assertRaisesRegex(
                    ORACLE.OracleRejected, f"target-evidence-{reason}:0"
                ):
                    self.sealed_owner().evaluate(submission)

    def test_duplicate_target_identity_is_rejected(self) -> None:
        duplicate = self.submission(
            records=(
                self.record(0),
                self.record(1, actual_identity=self.targets[0]),
            )
        )
        with self.assertRaisesRegex(ORACLE.OracleRejected, "duplicate-target-identity"):
            self.sealed_owner().evaluate(duplicate)

    def test_swapped_target_records_are_rejected(self) -> None:
        swapped = self.submission(
            records=(
                self.record(0, actual_identity=self.targets[1]),
                self.record(1, actual_identity=self.targets[0]),
            )
        )
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "target-identity-mismatch:0"
        ):
            self.sealed_owner().evaluate(swapped)

    def test_paired_oracle_sample_is_rejected(self) -> None:
        paired = self.submission(
            records=(
                self.record(0, sample_id="one-sample"),
                self.record(1, sample_id="one-sample"),
            )
        )
        with self.assertRaisesRegex(ORACLE.OracleRejected, "paired-oracle"):
            self.sealed_owner().evaluate(paired)

    def test_each_record_must_bind_the_ordered_identity_pair(self) -> None:
        reversed_pair = tuple(reversed(self.targets))
        disagreement = self.submission(
            records=(
                self.record(0),
                self.record(1, identity_pair=reversed_pair),
            )
        )
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "target-identity-pair-mismatch:1"
        ):
            self.sealed_owner().evaluate(disagreement)

    def test_target_generation_drift_is_rejected(self) -> None:
        drifted = self.submission(
            records=(
                self.record(0),
                self.record(1, generation="older-boot"),
            )
        )
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "target-generation-drift:1"
        ):
            self.sealed_owner().evaluate(drifted)

    def test_all_three_identity_pairs_must_agree(self) -> None:
        drifts = {
            "config": dataclass_replace(
                self.identities, running_config="config-b"
            ),
            "image": dataclass_replace(self.identities, running_image="image-b"),
            "cmdline": dataclass_replace(
                self.identities, running_cmdline="cmdline-b"
            ),
        }
        for label, identities in drifts.items():
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    ORACLE.OracleRejected, f"identity-pair-drift:{label}"
                ):
                    self.sealed_owner().evaluate(
                        self.submission(identities=identities)
                    )

    def test_identity_pairs_must_be_present_and_nonempty(self) -> None:
        missing = dataclass_replace(self.submission(), identities=None)
        with self.assertRaisesRegex(ORACLE.OracleRejected, "identity-pairs-missing"):
            self.sealed_owner().evaluate(missing)

        incomplete_identities = dataclass_replace(
            self.identities,
            running_config="",
        )
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "identity-pair-incomplete:config"
        ):
            self.sealed_owner().evaluate(
                self.submission(identities=incomplete_identities)
            )

    def test_submission_generation_drift_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "submission-generation-drift"
        ):
            self.sealed_owner().evaluate(self.submission(generation="older-boot"))

    def test_post_evaluation_replay_and_mutation_are_rejected(self) -> None:
        owner = self.sealed_owner()
        original = self.submission()
        owner.evaluate(original)
        sealed_state = owner.snapshot()

        with self.assertRaisesRegex(ORACLE.OracleRejected, "post-evaluation-submission"):
            owner.evaluate(original)

        changed_item = ORACLE.EvidenceItem(
            name=original.records[0].evidence[0].name,
            value="post-seal-drift",
        )
        changed_record = dataclass_replace(
            original.records[0],
            evidence=(changed_item,) + original.records[0].evidence[1:],
        )
        changed = dataclass_replace(
            original,
            records=(changed_record, original.records[1]),
        )
        with self.assertRaisesRegex(ORACLE.OracleRejected, "post-evaluation-submission"):
            owner.evaluate(changed)
        self.assertEqual(owner.snapshot(), sealed_state)

    def test_repeated_or_post_seal_attempt_faults_private_state(self) -> None:
        owner = self.sealed_owner()
        with self.assertRaisesRegex(ORACLE.OracleRejected, "post-seal-attempt"):
            owner.seal()

        self.assertEqual(owner.snapshot().state, ORACLE.SealState.FAULT)
        verdict = owner.evaluate(self.submission())
        self.assertEqual(verdict.seal_state, ORACLE.SealState.FAULT)
        self.assertFalse(verdict.evaluated)
        self.assertFalse(verdict.production_ready)
        self.assertIn(ORACLE.Blocker.RUNTIME_EVIDENCE_NOT_SEALED, verdict.blockers)

    def test_profile_has_no_seal_or_provider_control(self) -> None:
        profile_fields = {field.name for field in dataclass_fields(ORACLE.ProfileSubmission)}
        owner = self.owner()

        self.assertNotIn("seal", profile_fields)
        self.assertNotIn("provider", profile_fields)
        self.assertFalse(hasattr(owner, "set_seal"))
        self.assertFalse(hasattr(owner, "write_runtime_record"))
        self.assertFalse(hasattr(owner, "install_runtime_provider"))
        with self.assertRaises(TypeError):
            ORACLE.CoreOwner(self.targets, self.generation, seal="forged")

    def test_string_runtime_label_is_not_an_origin_attestation(self) -> None:
        forged = dataclass_replace(
            self.submission(ORACLE.Origin.RUNTIME),
            origin="RUNTIME",
        )
        with self.assertRaisesRegex(ORACLE.OracleRejected, "origin-type"):
            self.sealed_owner().evaluate(forged)


if __name__ == "__main__":
    unittest.main(verbosity=2)
