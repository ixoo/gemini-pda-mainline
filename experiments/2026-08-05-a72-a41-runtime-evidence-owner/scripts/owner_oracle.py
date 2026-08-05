#!/usr/bin/env python3
"""Independent ownership oracle for the blocked A41 runtime-evidence step.

The oracle models provenance and sealing only.  It deliberately does not read
kernel sources, import implementation constants, or claim that a runtime
target provider exists.  A profile can submit NONE, FIXTURE, or RUNTIME
origin, but the private core record can currently seal only as empty.  A
complete fixture may still be evaluated separately; it never counts as runtime
evidence.  A profile-declared RUNTIME record remains blocked because no
architecture-owned target provider is present.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class OracleRejected(ValueError):
    """The profile submission violates the ownership contract."""


class Origin(Enum):
    """Origin claimed by the profile, not an architecture attestation."""

    NONE = "NONE"
    FIXTURE = "FIXTURE"
    RUNTIME = "RUNTIME"


class SealState(Enum):
    """Private architecture-core record lifecycle."""

    OPEN = "OPEN"
    SEALED_EMPTY = "SEALED_EMPTY"
    SEALED_RUNTIME = "SEALED_RUNTIME"
    FAULT = "FAULT"


class Blocker(Enum):
    """Fail-closed reasons returned for structurally valid submissions."""

    ORIGIN_NONE = "origin-none"
    FIXTURE_IS_NOT_RUNTIME = "fixture-is-not-runtime"
    PROFILE_RUNTIME_IS_UNATTESTED = "profile-runtime-is-unattested"
    RUNTIME_EVIDENCE_NOT_SEALED = "runtime-evidence-not-sealed"
    PRIVATE_RECORD_EMPTY = "private-record-empty"
    TARGET_PROVIDER_UNAVAILABLE = "target-provider-unavailable"


# This is an independent experiment contract, not a transcription loaded from
# C.  Values remain opaque because the ownership oracle verifies attribution,
# completeness, and immutability rather than capability semantics.
_REQUIRED_TARGET_FIELDS = frozenset(
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


def required_target_fields() -> frozenset[str]:
    """Return the immutable independent completeness contract."""

    return _REQUIRED_TARGET_FIELDS


@dataclass(frozen=True, order=True)
class TargetIdentity:
    """Actual logical-CPU and MPIDR identity observed for a target slot."""

    logical_cpu: int
    mpidr: int


@dataclass(frozen=True)
class EvidenceItem:
    """One opaque, present target-evidence field."""

    name: str
    value: str


@dataclass(frozen=True)
class TargetRecord:
    """One independently attributable target measurement."""

    slot: int
    actual_identity: TargetIdentity
    identity_pair: tuple[TargetIdentity, TargetIdentity]
    generation: str
    sample_id: str
    evidence: tuple[EvidenceItem, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity_pair", tuple(self.identity_pair))
        object.__setattr__(self, "evidence", tuple(self.evidence))


@dataclass(frozen=True)
class IdentityPairs:
    """Expected/running identity pairs which must agree field for field."""

    resolved_config: str
    running_config: str
    built_image: str
    running_image: str
    expected_cmdline: str
    running_cmdline: str

    def pairs(self) -> tuple[tuple[str, str, str], ...]:
        return (
            ("config", self.resolved_config, self.running_config),
            ("image", self.built_image, self.running_image),
            ("cmdline", self.expected_cmdline, self.running_cmdline),
        )


@dataclass(frozen=True)
class ProfileSubmission:
    """Untrusted profile input; notably, it contains no seal or provider."""

    origin: Origin
    generation: str | None = None
    identities: IdentityPairs | None = None
    records: tuple[TargetRecord, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))


@dataclass(frozen=True)
class CoreState:
    """Read-only snapshot of the core-owned private seal state."""

    state: SealState
    sealed: bool
    private_origin: Origin
    seal_identity: str | None


@dataclass(frozen=True)
class Verdict:
    """Ownership result; production_ready is false in every current branch."""

    origin: Origin
    seal_state: SealState
    structurally_valid: bool
    evaluated: bool
    sealed: bool
    counts_as_runtime: bool
    production_ready: bool
    blockers: frozenset[Blocker]
    evaluation_identity: str | None


@dataclass(frozen=True)
class _PrivateCoreRecord:
    """Private immutable state replaced only by the architecture owner."""

    state: SealState
    origin: Origin
    evidence_identity: str | None


class CoreOwner:
    """Architecture-owner model with no runtime-provider installation API."""

    __slots__ = (
        "__expected_targets",
        "__generation",
        "__runtime_record",
        "__profile_evaluation_identity",
    )

    def __init__(
        self,
        expected_targets: Iterable[TargetIdentity],
        generation: str,
    ) -> None:
        targets = tuple(expected_targets)
        if len(targets) != 2:
            raise OracleRejected("owner-target-count")
        if any(not isinstance(target, TargetIdentity) for target in targets):
            raise OracleRejected("owner-target-type")
        if len(set(targets)) != 2:
            raise OracleRejected("owner-target-identity-duplicate")
        if not isinstance(generation, str) or not generation:
            raise OracleRejected("owner-generation")

        self.__expected_targets = targets
        self.__generation = generation
        self.__runtime_record = _PrivateCoreRecord(
            state=SealState.OPEN,
            origin=Origin.NONE,
            evidence_identity=None,
        )
        self.__profile_evaluation_identity: str | None = None

    def snapshot(self) -> CoreState:
        """Expose seal status without exposing a writable seal handle."""

        record = self.__runtime_record
        return CoreState(
            state=record.state,
            sealed=record.state in {SealState.SEALED_EMPTY, SealState.SEALED_RUNTIME},
            private_origin=record.origin,
            seal_identity=record.evidence_identity,
        )

    def seal(self) -> CoreState:
        """Close the private producer window; current ABI has no producer."""

        if self.__runtime_record.state is not SealState.OPEN:
            self.__runtime_record = _PrivateCoreRecord(
                state=SealState.FAULT,
                origin=self.__runtime_record.origin,
                evidence_identity=self.__runtime_record.evidence_identity,
            )
            raise OracleRejected("post-seal-attempt")

        # No target provider or running-identity producer exists.  Therefore
        # the only reachable successful seal is explicitly SEALED_EMPTY.
        self.__runtime_record = _PrivateCoreRecord(
            state=SealState.SEALED_EMPTY,
            origin=Origin.NONE,
            evidence_identity=None,
        )
        return self.snapshot()

    def evaluate(self, submission: ProfileSubmission) -> Verdict:
        """Validate one profile submission and fail closed at the owner gate."""

        if not isinstance(submission, ProfileSubmission):
            raise OracleRejected("submission-type")
        if not isinstance(submission.origin, Origin):
            raise OracleRejected("origin-type")

        state = self.__runtime_record.state
        if state not in {SealState.SEALED_EMPTY, SealState.SEALED_RUNTIME}:
            return Verdict(
                origin=submission.origin,
                seal_state=state,
                structurally_valid=False,
                evaluated=False,
                sealed=False,
                counts_as_runtime=False,
                production_ready=False,
                blockers=frozenset(
                    {
                        Blocker.RUNTIME_EVIDENCE_NOT_SEALED,
                        Blocker.TARGET_PROVIDER_UNAVAILABLE,
                    }
                ),
                evaluation_identity=None,
            )

        if self.__profile_evaluation_identity is not None:
            raise OracleRejected("post-evaluation-submission")

        if submission.origin is Origin.NONE:
            if (
                submission.generation is not None
                or submission.identities is not None
                or submission.records
            ):
                raise OracleRejected("origin-none-with-evidence")
            return Verdict(
                origin=Origin.NONE,
                seal_state=state,
                structurally_valid=True,
                evaluated=False,
                sealed=True,
                counts_as_runtime=False,
                production_ready=False,
                blockers=frozenset(
                    {
                        Blocker.ORIGIN_NONE,
                        Blocker.PRIVATE_RECORD_EMPTY,
                        Blocker.TARGET_PROVIDER_UNAVAILABLE,
                    }
                ),
                evaluation_identity=None,
            )

        if submission.origin is Origin.RUNTIME:
            # A profile's origin label cannot substitute for a target provider.
            # There is intentionally no API in this milestone which can install
            # such a provider or mint a runtime seal.
            return Verdict(
                origin=Origin.RUNTIME,
                seal_state=state,
                structurally_valid=False,
                evaluated=False,
                sealed=True,
                counts_as_runtime=False,
                production_ready=False,
                blockers=frozenset(
                    {
                        Blocker.PROFILE_RUNTIME_IS_UNATTESTED,
                        Blocker.PRIVATE_RECORD_EMPTY,
                        Blocker.TARGET_PROVIDER_UNAVAILABLE,
                    }
                ),
                evaluation_identity=None,
            )

        canonical = self.__validate_complete(submission)
        evaluation_identity = hashlib.sha256(canonical).hexdigest()
        self.__profile_evaluation_identity = evaluation_identity
        return Verdict(
            origin=Origin.FIXTURE,
            seal_state=state,
            structurally_valid=True,
            evaluated=True,
            sealed=True,
            counts_as_runtime=False,
            production_ready=False,
            blockers=frozenset(
                {
                    Blocker.FIXTURE_IS_NOT_RUNTIME,
                    Blocker.PRIVATE_RECORD_EMPTY,
                    Blocker.TARGET_PROVIDER_UNAVAILABLE,
                }
            ),
            evaluation_identity=evaluation_identity,
        )

    def __validate_complete(self, submission: ProfileSubmission) -> bytes:
        if submission.generation != self.__generation:
            raise OracleRejected("submission-generation-drift")
        if not isinstance(submission.identities, IdentityPairs):
            raise OracleRejected("identity-pairs-missing")

        for label, expected, running in submission.identities.pairs():
            if (
                not isinstance(expected, str)
                or not isinstance(running, str)
                or not expected
                or not running
            ):
                raise OracleRejected(f"identity-pair-incomplete:{label}")
            if expected != running:
                raise OracleRejected(f"identity-pair-drift:{label}")

        records = submission.records
        if len(records) != 2:
            raise OracleRejected("target-record-count")
        if any(not isinstance(record, TargetRecord) for record in records):
            raise OracleRejected("target-record-type")
        if tuple(record.slot for record in records) != (0, 1):
            raise OracleRejected("target-record-slots")

        actual_identities = tuple(record.actual_identity for record in records)
        if len(set(actual_identities)) != 2:
            raise OracleRejected("duplicate-target-identity")

        sample_ids = tuple(record.sample_id for record in records)
        if any(not isinstance(sample_id, str) or not sample_id for sample_id in sample_ids):
            raise OracleRejected("target-sample-id")
        if len(set(sample_ids)) != 2:
            raise OracleRejected("paired-oracle")

        canonical_records: list[dict[str, object]] = []
        for slot, record in enumerate(records):
            if record.actual_identity != self.__expected_targets[slot]:
                raise OracleRejected(f"target-identity-mismatch:{slot}")
            if record.identity_pair != self.__expected_targets:
                raise OracleRejected(f"target-identity-pair-mismatch:{slot}")
            if record.generation != self.__generation:
                raise OracleRejected(f"target-generation-drift:{slot}")

            names: list[str] = []
            values: dict[str, str] = {}
            for item in record.evidence:
                if not isinstance(item, EvidenceItem):
                    raise OracleRejected(f"target-evidence-type:{slot}")
                if not isinstance(item.name, str) or not item.name:
                    raise OracleRejected(f"target-evidence-name:{slot}")
                if not isinstance(item.value, str) or not item.value:
                    raise OracleRejected(
                        f"target-evidence-value:{slot}:{item.name}"
                    )
                names.append(item.name)
                values[item.name] = item.value

            if len(names) != len(set(names)):
                raise OracleRejected(f"target-evidence-duplicate:{slot}")
            if set(names) != _REQUIRED_TARGET_FIELDS:
                missing = sorted(_REQUIRED_TARGET_FIELDS.difference(names))
                unexpected = sorted(set(names).difference(_REQUIRED_TARGET_FIELDS))
                detail = ",".join(missing) + "|" + ",".join(unexpected)
                raise OracleRejected(f"target-evidence-incomplete:{slot}:{detail}")

            canonical_records.append(
                {
                    "slot": slot,
                    "actual_identity": {
                        "logical_cpu": record.actual_identity.logical_cpu,
                        "mpidr": record.actual_identity.mpidr,
                    },
                    "identity_pair": [
                        {
                            "logical_cpu": identity.logical_cpu,
                            "mpidr": identity.mpidr,
                        }
                        for identity in record.identity_pair
                    ],
                    "generation": record.generation,
                    "sample_id": record.sample_id,
                    "evidence": {name: values[name] for name in sorted(values)},
                }
            )

        canonical = {
            "origin": submission.origin.value,
            "generation": submission.generation,
            "identities": {
                label: {"expected": expected, "running": running}
                for label, expected, running in submission.identities.pairs()
            },
            "records": canonical_records,
        }
        return json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
