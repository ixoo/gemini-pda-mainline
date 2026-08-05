#!/usr/bin/env python3
"""Independent ABI 7 oracle for the Gemini A41 kernel-identity gate.

This module deliberately does not inspect kernel sources or import generated
constants.  It models the strict expected-DT record, the three independent
running identity producers, and the core-owned seal transition.  Identity
agreement can publish ``SEALED_IDENTITY`` only.  No API in this oracle can
provide target-local evidence or reach ``SEALED_RUNTIME``/``READY``.
"""

from __future__ import annotations

import hashlib
import hmac
import struct
import threading
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class OracleRejected(ValueError):
    """An input violates the frozen ABI 7 identity contract."""


DOMAIN_PREFIX = b"gemini-a41-runtime-binding-v1\0"
COMPATIBLE = "planet,gemini-a72-runtime-binding-v1"
SCHEMA_VERSION = 1
PROFILE_ID = "mt6797-a53-a72-a41-v7"
PROVENANCE_NODE_PATH = "/chosen/gemini-late-cpu-provenance"
PROVENANCE_NODE_NAME = "gemini-late-cpu-provenance"
TARGET_CPUS = (8, 9)
TARGET_MPIDRS = (0x200, 0x201)

IKCONFIG_START = b"IKCFG_ST"
IKCONFIG_END = b"IKCFG_ED"
GNU_BUILD_ID_TYPE = 3
GNU_BUILD_ID_SIZE = 20
SHA256_SIZE = 32
IKCONFIG_MAX_SIZE = 4 * 1024 * 1024
IKCONFIG_PLAIN_MAX_SIZE = 4 * IKCONFIG_MAX_SIZE
NOTE_BLOB_MAX_SIZE = 64 * 1024
ACTIVE_CONFIG_INPUTS_SHA256 = bytes.fromhex(
    "4dca4e50ab039fbc60593e86d20d02e7"
    "4e257dc6b5bb1afa94b38be6295b5203"
)

IDENTITY_PROPERTY_NAMES = (
    "expected-ikconfig-identity",
    "expected-gnu-build-id-identity",
    "expected-cmdline-identity",
)
PROVENANCE_PROPERTY_NAMES = (
    "upstream-source-sha256",
    "patch-series-sha256",
    "config-inputs-sha256",
    "resolved-config-sha256",
    "package-image-sha256",
    "build-provenance-sha256",
)
PROPERTY_ORDER = (
    "compatible",
    "schema-version",
    "profile-id",
    "target-cpus",
    "target-mpidrs",
    *IDENTITY_PROPERTY_NAMES,
    *PROVENANCE_PROPERTY_NAMES,
    "record-identity",
    "name",
)

_EXPECTED_PRODUCER_KIND = object()
_RUNNING_PRODUCER_KIND = object()
_SNAPSHOT_FACTORY_TOKEN = object()


class _ProducerToken:
    """Private per-product capability which cannot survive dataclass cloning."""

    __slots__ = ("__kind", "__product")

    def __init__(self, kind: object) -> None:
        self.__kind = kind
        self.__product: object | None = None

    def bind(self, product: object) -> None:
        if self.__product is not None:
            raise RuntimeError("producer token reused")
        self.__product = product

    def authenticates(self, product: object, kind: object) -> bool:
        return self.__kind is kind and self.__product is product


class IdentityKind(Enum):
    IKCONFIG = "ikconfig"
    GNU_BUILD_ID = "gnu-build-id"
    CMDLINE = "cmdline"


class Authority(Enum):
    EXPECTED_DT = "expected-dt"
    RUNNING_CORE = "running-core"


class SealState(Enum):
    OPEN = "OPEN"
    SEALED_EMPTY = "SEALED_EMPTY"
    SEALED_IDENTITY = "SEALED_IDENTITY"
    SEALED_RUNTIME = "SEALED_RUNTIME"
    FAULT = "FAULT"


class Blocker(Enum):
    IDENTITY_NOT_SEALED = "identity-not-sealed"
    EXPECTED_RECORD_MISSING = "expected-record-missing"
    RUNNING_IDENTITIES_MISSING = "running-identities-missing"
    IDENTITY_MISMATCH = "identity-mismatch"
    PAIRED_ORACLE = "paired-oracle"
    INTERNAL_FAULT = "internal-fault"
    PROFILE_BINDING_REQUIRED = "profile-binding-required"
    PROFILE_BINDING_MISMATCH = "profile-binding-mismatch"
    TARGET_EVIDENCE_UNAVAILABLE = "target-evidence-unavailable"
    RUNTIME_EVIDENCE_UNAVAILABLE = "runtime-evidence-unavailable"
    COMMIT_PATH_UNAVAILABLE = "commit-path-unavailable"


_FUTURE_BLOCKERS = frozenset(
    {
        Blocker.TARGET_EVIDENCE_UNAVAILABLE,
        Blocker.RUNTIME_EVIDENCE_UNAVAILABLE,
        Blocker.COMMIT_PATH_UNAVAILABLE,
    }
)


@dataclass(frozen=True)
class RawProperty:
    """One raw DT property; tuples preserve order and duplicate names."""

    name: str
    value: bytes


@dataclass(frozen=True)
class RawNode:
    """One raw DT node; hierarchy and ordered properties remain explicit."""

    unit_name: str
    properties: tuple[RawProperty, ...]
    children: tuple["RawNode", ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "properties", tuple(self.properties))
        object.__setattr__(self, "children", tuple(self.children))


@dataclass(frozen=True)
class RecordFields:
    """The nine digest fields serialized before record-identity."""

    expected_ikconfig_identity: bytes
    expected_gnu_build_id_identity: bytes
    expected_cmdline_identity: bytes
    upstream_source_sha256: bytes
    patch_series_sha256: bytes
    config_inputs_sha256: bytes
    resolved_config_sha256: bytes
    package_image_sha256: bytes
    build_provenance_sha256: bytes

    def ordered(self) -> tuple[bytes, ...]:
        return (
            self.expected_ikconfig_identity,
            self.expected_gnu_build_id_identity,
            self.expected_cmdline_identity,
            self.upstream_source_sha256,
            self.patch_series_sha256,
            self.config_inputs_sha256,
            self.resolved_config_sha256,
            self.package_image_sha256,
            self.build_provenance_sha256,
        )


@dataclass(frozen=True)
class IdentityObservation:
    kind: IdentityKind
    digest: bytes
    authority: Authority
    source_token: str


@dataclass(frozen=True)
class IdentityTriplet:
    ikconfig: IdentityObservation
    gnu_build_id: IdentityObservation
    cmdline: IdentityObservation

    def ordered(self) -> tuple[IdentityObservation, ...]:
        return (self.ikconfig, self.gnu_build_id, self.cmdline)


@dataclass(frozen=True)
class ExpectedRecord:
    schema_version: int
    profile_id: str
    target_cpus: tuple[int, int]
    target_mpidrs: tuple[int, int]
    fields: RecordFields
    record_identity: bytes
    identities: IdentityTriplet
    source_token: str
    _producer_token: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class RunningIdentities:
    identities: IdentityTriplet
    source_token: str
    _producer_token: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class IdentityBinding:
    """Immutable binding constructed only by CoreOwner at seal time."""

    profile_id: str
    target_cpus: tuple[int, int]
    target_mpidrs: tuple[int, int]
    record_identity: bytes
    expected: IdentityTriplet
    running: IdentityTriplet


@dataclass(frozen=True, init=False)
class CoreSnapshot:
    state: SealState
    sealed: bool
    binding: IdentityBinding | None
    blockers: frozenset[Blocker]
    identity_complete: bool
    target_evidence_published: bool
    counts_as_runtime: bool
    production_ready: bool
    profile_bound: bool
    overlay_eligible: bool

    def __new__(cls, *_args: object, **_kwargs: object) -> "CoreSnapshot":
        raise TypeError("CoreSnapshot instances are owner-produced")

    @classmethod
    def _from_owner(
        cls,
        factory_token: object,
        *,
        state: SealState,
        binding: IdentityBinding | None,
        blockers: frozenset[Blocker],
        profile_bound: bool,
    ) -> "CoreSnapshot":
        if factory_token is not _SNAPSHOT_FACTORY_TOKEN:
            raise TypeError("CoreSnapshot instances are owner-produced")
        if state not in {
            SealState.OPEN,
            SealState.SEALED_EMPTY,
            SealState.SEALED_IDENTITY,
            SealState.FAULT,
        }:
            raise OracleRejected("snapshot-state")
        if (state is SealState.SEALED_IDENTITY) != (binding is not None):
            raise OracleRejected("snapshot-binding-polarity")
        if profile_bound and state is not SealState.SEALED_IDENTITY:
            raise OracleRejected("snapshot-profile-polarity")
        snapshot = object.__new__(cls)
        values = {
            "state": state,
            "sealed": state
            in {SealState.SEALED_EMPTY, SealState.SEALED_IDENTITY},
            "binding": binding,
            "blockers": blockers,
            "identity_complete": state is SealState.SEALED_IDENTITY,
            "target_evidence_published": False,
            "counts_as_runtime": False,
            "production_ready": False,
            "profile_bound": profile_bound,
            "overlay_eligible": profile_bound,
        }
        for name, value in values.items():
            object.__setattr__(snapshot, name, value)
        return snapshot


def _require_bytes(value: object, label: str) -> bytes:
    if not isinstance(value, bytes):
        raise OracleRejected(f"{label}-type")
    return value


def _require_source_token(source_token: object) -> str:
    if not isinstance(source_token, str) or not source_token:
        raise OracleRejected("source-token")
    return source_token


def _require_digest(value: object, label: str) -> bytes:
    digest = _require_bytes(value, label)
    if len(digest) != SHA256_SIZE:
        raise OracleRejected(f"{label}-length")
    if not any(digest):
        raise OracleRejected(f"{label}-zero")
    return digest


def _be16(value: int, label: str) -> bytes:
    if not isinstance(value, int) or not 0 <= value <= 0xFFFF:
        raise OracleRejected(label)
    return struct.pack(">H", value)


def _be32(value: int, label: str) -> bytes:
    if not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
        raise OracleRejected(label)
    return struct.pack(">I", value)


def _be64(value: int, label: str) -> bytes:
    if not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise OracleRejected(label)
    return struct.pack(">Q", value)


def _domain_digest(tag: bytes, length_field: bytes, payload: bytes) -> bytes:
    return hashlib.sha256(DOMAIN_PREFIX + tag + length_field + payload).digest()


def _validate_ikconfig_gzip(payload: object) -> bytes:
    raw = _require_bytes(payload, "ikconfig")
    if not raw:
        raise OracleRejected("ikconfig-empty")
    if len(raw) > IKCONFIG_MAX_SIZE:
        raise OracleRejected("ikconfig-size")

    inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        plain = inflater.decompress(raw, IKCONFIG_PLAIN_MAX_SIZE + 1)
        if len(plain) > IKCONFIG_PLAIN_MAX_SIZE or inflater.unconsumed_tail:
            raise OracleRejected("ikconfig-expanded-size")
        plain += inflater.flush(IKCONFIG_PLAIN_MAX_SIZE + 1 - len(plain))
    except zlib.error as error:
        raise OracleRejected("ikconfig-gzip") from error

    if (
        len(plain) > IKCONFIG_PLAIN_MAX_SIZE
        or not inflater.eof
        or inflater.unused_data
        or inflater.unconsumed_tail
        or not plain
    ):
        raise OracleRejected("ikconfig-gzip")
    return raw


def extract_ikconfig_payload(image: object) -> bytes:
    """Extract one exact marker-bounded gzip payload from a finished Image."""

    raw_image = _require_bytes(image, "image")
    if raw_image.count(IKCONFIG_START) != 1 or raw_image.count(IKCONFIG_END) != 1:
        raise OracleRejected("ikconfig-marker-count")
    start = raw_image.find(IKCONFIG_START) + len(IKCONFIG_START)
    end = raw_image.find(IKCONFIG_END)
    if start > end:
        raise OracleRejected("ikconfig-marker-order")
    return _validate_ikconfig_gzip(raw_image[start:end])


def derive_ikconfig_identity(payload: object) -> bytes:
    raw = _validate_ikconfig_gzip(payload)
    return _domain_digest(b"ikconfig\0", _be64(len(raw), "ikconfig-length"), raw)


def derive_gnu_build_id_identity(build_id: object) -> bytes:
    raw = _require_bytes(build_id, "gnu-build-id")
    if len(raw) != GNU_BUILD_ID_SIZE:
        raise OracleRejected("gnu-build-id-length")
    if not any(raw):
        raise OracleRejected("gnu-build-id-zero")
    return _domain_digest(
        b"gnu-build-id\0",
        _be32(GNU_BUILD_ID_SIZE, "gnu-build-id-length"),
        raw,
    )


def parse_gnu_build_id_notes(note_blob: object) -> bytes:
    """Return the sole strict GNU build-ID from an arm64 LE note stream."""

    blob = _require_bytes(note_blob, "note-blob")
    if not blob or len(blob) > NOTE_BLOB_MAX_SIZE:
        raise OracleRejected("note-blob-size")
    offset = 0
    matches: list[bytes] = []

    while offset < len(blob):
        if len(blob) - offset < 12:
            raise OracleRejected("note-header-truncated")
        namesz, descsz, note_type = struct.unpack_from("<III", blob, offset)
        offset += 12

        name_end = offset + namesz
        name_aligned_end = offset + ((namesz + 3) & ~3)
        desc_end = name_aligned_end + descsz
        note_end = name_aligned_end + ((descsz + 3) & ~3)
        if (
            name_end > len(blob)
            or name_aligned_end > len(blob)
            or desc_end > len(blob)
            or note_end > len(blob)
        ):
            raise OracleRejected("note-bounds")

        name = blob[offset:name_end]
        descriptor = blob[name_aligned_end:desc_end]
        if note_type == GNU_BUILD_ID_TYPE and name == b"GNU\0":
            if descsz != GNU_BUILD_ID_SIZE:
                raise OracleRejected("gnu-build-id-length")
            if not any(descriptor):
                raise OracleRejected("gnu-build-id-zero")
            matches.append(descriptor)
        offset = note_end

    if len(matches) != 1:
        raise OracleRejected("gnu-build-id-count")
    return matches[0]


def derive_cmdline_identity(cmdline: object) -> bytes:
    raw = _require_bytes(cmdline, "cmdline")
    if not raw:
        raise OracleRejected("cmdline-empty")
    if b"\0" in raw:
        raise OracleRejected("cmdline-embedded-nul")
    return _domain_digest(b"cmdline\0", _be64(len(raw), "cmdline-length"), raw)


def serialize_record(
    fields: RecordFields,
    *,
    schema_version: int = SCHEMA_VERSION,
    profile_id: str = PROFILE_ID,
    target_cpus: tuple[int, ...] = TARGET_CPUS,
    target_mpidrs: tuple[int, ...] = TARGET_MPIDRS,
) -> bytes:
    """Serialize the record preimage with explicit widths and byte order."""

    if not isinstance(fields, RecordFields):
        raise OracleRejected("record-fields-type")
    if not isinstance(profile_id, str) or not profile_id:
        raise OracleRejected("profile-id")
    try:
        profile = profile_id.encode("ascii")
    except UnicodeEncodeError as error:
        raise OracleRejected("profile-id-encoding") from error
    if b"\0" in profile:
        raise OracleRejected("profile-id-nul")

    try:
        cpus = tuple(target_cpus)
        mpidrs = tuple(target_mpidrs)
    except TypeError as error:
        raise OracleRejected("target-collection") from error
    digests = tuple(
        _require_digest(value, f"record-field-{index}")
        for index, value in enumerate(fields.ordered())
    )

    return b"".join(
        (
            DOMAIN_PREFIX,
            b"record\0",
            _be32(schema_version, "schema-version"),
            _be16(len(profile), "profile-length"),
            profile,
            _be32(len(cpus), "target-cpu-count"),
            *(_be32(cpu, "target-cpu") for cpu in cpus),
            _be32(len(mpidrs), "target-mpidr-count"),
            *(_be64(mpidr, "target-mpidr") for mpidr in mpidrs),
            *digests,
        )
    )


def record_identity(fields: RecordFields, **record_parameters: object) -> bytes:
    return hashlib.sha256(serialize_record(fields, **record_parameters)).digest()


def _unit_base(unit_name: str) -> str:
    return unit_name.split("@", 1)[0]


def _compatible_contains(value: object, compatible: bytes) -> bool:
    if not isinstance(value, bytes):
        return False
    offset = 0
    while offset < len(value):
        end = value.find(b"\0", offset)
        if end < 0:
            return False
        if value[offset:end] == compatible:
            return True
        offset = end + 1
    return False


def _compatible_candidate(node: RawNode) -> bool:
    encoded = COMPATIBLE.encode("ascii")
    return any(
        isinstance(prop, RawProperty)
        and prop.name == "compatible"
        and _compatible_contains(prop.value, encoded)
        for prop in node.properties
    )


def _walk_tree(root: RawNode) -> tuple[RawNode, ...]:
    ordered: list[RawNode] = []
    seen: set[int] = set()
    stack: list[tuple[RawNode, bool]] = [(root, True)]

    while stack:
        node, is_root = stack.pop()
        if not isinstance(node, RawNode):
            raise OracleRejected("node-type")
        if id(node) in seen:
            raise OracleRejected("node-cycle-or-alias")
        seen.add(id(node))
        if not isinstance(node.unit_name, str):
            raise OracleRejected("node-name-type")
        if is_root:
            if node.unit_name != "":
                raise OracleRejected("root-name")
        elif (
            not node.unit_name
            or "/" in node.unit_name
            or "\0" in node.unit_name
        ):
            raise OracleRejected("node-name")
        if any(not isinstance(prop, RawProperty) for prop in node.properties):
            raise OracleRejected("property-type")
        if any(not isinstance(child, RawNode) for child in node.children):
            raise OracleRejected("child-type")
        ordered.append(node)
        stack.extend((child, False) for child in reversed(node.children))

    return tuple(ordered)


def parse_expected_record(
    nodes: Iterable[RawNode], *, source_token: str
) -> ExpectedRecord:
    """Parse exactly one strict expected-only ABI 7 DT provenance node."""

    token = _require_source_token(source_token)
    try:
        raw_nodes = tuple(nodes)
    except TypeError as error:
        raise OracleRejected("node-collection") from error
    if len(raw_nodes) != 1:
        raise OracleRejected("root-count")
    root = raw_nodes[0]
    all_nodes = _walk_tree(root)

    chosen_matches = tuple(
        child for child in root.children if _unit_base(child.unit_name) == "chosen"
    )
    if len(chosen_matches) != 1 or chosen_matches[0].unit_name != "chosen":
        raise OracleRejected("chosen-node")
    chosen = chosen_matches[0]

    provenance_name_matches = tuple(
        child
        for child in chosen.children
        if _unit_base(child.unit_name) == PROVENANCE_NODE_NAME
    )
    if (
        len(provenance_name_matches) != 1
        or provenance_name_matches[0].unit_name != PROVENANCE_NODE_NAME
    ):
        raise OracleRejected("provenance-node-path")
    node = provenance_name_matches[0]

    compatible_candidates = tuple(
        candidate for candidate in all_nodes if _compatible_candidate(candidate)
    )
    if (
        len(compatible_candidates) != 1
        or compatible_candidates[0] is not node
    ):
        raise OracleRejected("provenance-node-count")
    if node.children:
        raise OracleRejected("provenance-node-children")

    allowed = frozenset(PROPERTY_ORDER)
    values: dict[str, bytes] = {}
    for prop in node.properties:
        if not isinstance(prop.name, str) or not prop.name:
            raise OracleRejected("property-name")
        if prop.name.startswith("running-"):
            raise OracleRejected("running-property")
        if prop.name not in allowed:
            raise OracleRejected("unknown-property")
        if prop.name in values:
            raise OracleRejected("duplicate-property")
        values[prop.name] = _require_bytes(prop.value, prop.name)
    if frozenset(values) != allowed:
        raise OracleRejected("missing-property")

    if values["name"] != PROVENANCE_NODE_NAME.encode("ascii") + b"\0":
        raise OracleRejected("name")
    if values["compatible"] != COMPATIBLE.encode("ascii") + b"\0":
        raise OracleRejected("compatible")
    if values["schema-version"] != _be32(SCHEMA_VERSION, "schema-version"):
        raise OracleRejected("schema-version")
    if values["profile-id"] != PROFILE_ID.encode("ascii") + b"\0":
        raise OracleRejected("profile-id")
    if values["target-cpus"] != b"".join(
        _be32(cpu, "target-cpu") for cpu in TARGET_CPUS
    ):
        raise OracleRejected("target-cpus")
    if values["target-mpidrs"] != b"".join(
        _be64(mpidr, "target-mpidr") for mpidr in TARGET_MPIDRS
    ):
        raise OracleRejected("target-mpidrs")

    digest_values = {
        name: _require_digest(values[name], name)
        for name in (*IDENTITY_PROPERTY_NAMES, *PROVENANCE_PROPERTY_NAMES)
    }
    fields = RecordFields(
        expected_ikconfig_identity=digest_values["expected-ikconfig-identity"],
        expected_gnu_build_id_identity=digest_values[
            "expected-gnu-build-id-identity"
        ],
        expected_cmdline_identity=digest_values["expected-cmdline-identity"],
        upstream_source_sha256=digest_values["upstream-source-sha256"],
        patch_series_sha256=digest_values["patch-series-sha256"],
        config_inputs_sha256=digest_values["config-inputs-sha256"],
        resolved_config_sha256=digest_values["resolved-config-sha256"],
        package_image_sha256=digest_values["package-image-sha256"],
        build_provenance_sha256=digest_values["build-provenance-sha256"],
    )
    supplied_record_identity = _require_digest(
        values["record-identity"], "record-identity"
    )
    calculated_record_identity = record_identity(fields)
    if not hmac.compare_digest(supplied_record_identity, calculated_record_identity):
        raise OracleRejected("record-identity-mismatch")

    identities = IdentityTriplet(
        ikconfig=IdentityObservation(
            IdentityKind.IKCONFIG,
            fields.expected_ikconfig_identity,
            Authority.EXPECTED_DT,
            token,
        ),
        gnu_build_id=IdentityObservation(
            IdentityKind.GNU_BUILD_ID,
            fields.expected_gnu_build_id_identity,
            Authority.EXPECTED_DT,
            token,
        ),
        cmdline=IdentityObservation(
            IdentityKind.CMDLINE,
            fields.expected_cmdline_identity,
            Authority.EXPECTED_DT,
            token,
        ),
    )
    producer_token = _ProducerToken(_EXPECTED_PRODUCER_KIND)
    result = ExpectedRecord(
        schema_version=SCHEMA_VERSION,
        profile_id=PROFILE_ID,
        target_cpus=TARGET_CPUS,
        target_mpidrs=TARGET_MPIDRS,
        fields=fields,
        record_identity=supplied_record_identity,
        identities=identities,
        source_token=token,
        _producer_token=producer_token,
    )
    producer_token.bind(result)
    return result


def derive_running_identities(
    *,
    ikconfig_gzip: bytes,
    note_blob: bytes,
    saved_command_line: bytes,
    saved_command_line_len: int,
    compiled_command_line: bytes,
    source_token: str,
) -> RunningIdentities:
    """Derive all running halves from architecture-owned byte sources."""

    token = _require_source_token(source_token)
    saved = _require_bytes(saved_command_line, "saved-command-line")
    compiled = _require_bytes(compiled_command_line, "compiled-command-line")
    if not isinstance(saved_command_line_len, int) or saved_command_line_len < 0:
        raise OracleRejected("saved-command-line-length")
    if len(saved) != saved_command_line_len + 1 or saved[-1:] != b"\0":
        raise OracleRejected("saved-command-line-storage")
    payload = saved[:saved_command_line_len]
    if b"\0" in payload:
        raise OracleRejected("saved-command-line-embedded-nul")
    if b"\0" in compiled:
        raise OracleRejected("compiled-command-line-nul")
    if payload != compiled:
        raise OracleRejected("forced-command-line-mismatch")

    build_id = parse_gnu_build_id_notes(note_blob)
    identities = IdentityTriplet(
        ikconfig=IdentityObservation(
            IdentityKind.IKCONFIG,
            derive_ikconfig_identity(ikconfig_gzip),
            Authority.RUNNING_CORE,
            token,
        ),
        gnu_build_id=IdentityObservation(
            IdentityKind.GNU_BUILD_ID,
            derive_gnu_build_id_identity(build_id),
            Authority.RUNNING_CORE,
            token,
        ),
        cmdline=IdentityObservation(
            IdentityKind.CMDLINE,
            derive_cmdline_identity(payload),
            Authority.RUNNING_CORE,
            token,
        ),
    )
    producer_token = _ProducerToken(_RUNNING_PRODUCER_KIND)
    result = RunningIdentities(
        identities=identities,
        source_token=token,
        _producer_token=producer_token,
    )
    producer_token.bind(result)
    return result


def _validate_triplet(
    triplet: IdentityTriplet,
    authority: Authority,
    source_token: str,
) -> bool:
    if not isinstance(triplet, IdentityTriplet):
        return False
    expected_kinds = (
        IdentityKind.IKCONFIG,
        IdentityKind.GNU_BUILD_ID,
        IdentityKind.CMDLINE,
    )
    for observation, kind in zip(triplet.ordered(), expected_kinds, strict=True):
        if (
            not isinstance(observation, IdentityObservation)
            or observation.kind is not kind
            or observation.authority is not authority
            or observation.source_token != source_token
        ):
            return False
        try:
            _require_digest(observation.digest, f"{kind.value}-identity")
        except OracleRejected:
            return False
    return True


def _producer_authenticates(
    token: object, product: object, kind: object
) -> bool:
    return isinstance(token, _ProducerToken) and token.authenticates(product, kind)


def _validate_expected_object(record: ExpectedRecord) -> bool:
    if not isinstance(record, ExpectedRecord):
        return False
    try:
        target_cpus = tuple(record.target_cpus)
        target_mpidrs = tuple(record.target_mpidrs)
    except TypeError:
        return False
    if (
        record.schema_version != SCHEMA_VERSION
        or record.profile_id != PROFILE_ID
        or target_cpus != TARGET_CPUS
        or target_mpidrs != TARGET_MPIDRS
        or not isinstance(record.fields, RecordFields)
        or not isinstance(record.source_token, str)
        or not record.source_token
        or not _producer_authenticates(
            record._producer_token, record, _EXPECTED_PRODUCER_KIND
        )
    ):
        return False
    try:
        expected_identity = record_identity(record.fields)
        _require_digest(record.record_identity, "record-identity")
    except (OracleRejected, TypeError):
        return False
    if not hmac.compare_digest(expected_identity, record.record_identity):
        return False
    if not _validate_triplet(
        record.identities, Authority.EXPECTED_DT, record.source_token
    ):
        return False
    return tuple(obs.digest for obs in record.identities.ordered()) == (
        record.fields.expected_ikconfig_identity,
        record.fields.expected_gnu_build_id_identity,
        record.fields.expected_cmdline_identity,
    )


def _validate_running_object(record: RunningIdentities) -> bool:
    return (
        isinstance(record, RunningIdentities)
        and isinstance(record.source_token, str)
        and bool(record.source_token)
        and _producer_authenticates(
            record._producer_token, record, _RUNNING_PRODUCER_KIND
        )
        and _validate_triplet(
            record.identities, Authority.RUNNING_CORE, record.source_token
        )
    )


class CoreOwner:
    """Private, one-shot owner which publishes only an identity binding."""

    __slots__ = (
        "__lock",
        "__state",
        "__expected",
        "__running",
        "__binding",
        "__blockers",
        "__profile_consumed",
        "__profile_bound",
    )

    def __init__(self) -> None:
        self.__lock = threading.Lock()
        self.__state = SealState.OPEN
        self.__expected: ExpectedRecord | None = None
        self.__running: RunningIdentities | None = None
        self.__binding: IdentityBinding | None = None
        self.__blockers = frozenset(
            {Blocker.IDENTITY_NOT_SEALED, *_FUTURE_BLOCKERS}
        )
        self.__profile_consumed = False
        self.__profile_bound = False

    def __snapshot_locked(self) -> CoreSnapshot:
        state = self.__state
        return CoreSnapshot._from_owner(
            _SNAPSHOT_FACTORY_TOKEN,
            state=state,
            binding=self.__binding,
            blockers=self.__blockers,
            profile_bound=self.__profile_bound,
        )

    def snapshot(self) -> CoreSnapshot:
        with self.__lock:
            return self.__snapshot_locked()

    def __fault_locked(self, reason: str) -> None:
        self.__expected = None
        self.__running = None
        self.__binding = None
        self.__profile_consumed = True
        self.__profile_bound = False
        self.__blockers = frozenset({Blocker.INTERNAL_FAULT, *_FUTURE_BLOCKERS})
        self.__state = SealState.FAULT
        raise OracleRejected(reason)

    def stage_expected(self, record: ExpectedRecord) -> None:
        with self.__lock:
            if self.__state is not SealState.OPEN:
                self.__fault_locked("post-seal-expected-stage")
            if self.__expected is not None:
                self.__fault_locked("duplicate-expected-stage")
            if not _validate_expected_object(record):
                self.__fault_locked("expected-record-invalid")
            self.__expected = record

    def stage_running(self, record: RunningIdentities) -> None:
        with self.__lock:
            if self.__state is not SealState.OPEN:
                self.__fault_locked("post-seal-running-stage")
            if self.__running is not None:
                self.__fault_locked("duplicate-running-stage")
            if not _validate_running_object(record):
                self.__fault_locked("running-identities-invalid")
            self.__running = record

    def seal(self) -> CoreSnapshot:
        with self.__lock:
            if self.__state is not SealState.OPEN:
                self.__fault_locked("repeat-seal")

            blockers = set(_FUTURE_BLOCKERS)
            if self.__expected is None:
                blockers.add(Blocker.EXPECTED_RECORD_MISSING)
            if self.__running is None:
                blockers.add(Blocker.RUNNING_IDENTITIES_MISSING)
            if self.__expected is None or self.__running is None:
                self.__binding = None
                self.__blockers = frozenset(blockers)
                self.__state = SealState.SEALED_EMPTY
                return self.__snapshot_locked()

            expected = self.__expected
            running = self.__running
            if expected.source_token == running.source_token:
                blockers.add(Blocker.PAIRED_ORACLE)
                self.__binding = None
                self.__blockers = frozenset(blockers)
                self.__state = SealState.SEALED_EMPTY
                return self.__snapshot_locked()

            if any(
                not hmac.compare_digest(want.digest, have.digest)
                for want, have in zip(
                    expected.identities.ordered(),
                    running.identities.ordered(),
                    strict=True,
                )
            ):
                blockers.add(Blocker.IDENTITY_MISMATCH)
                self.__binding = None
                self.__blockers = frozenset(blockers)
                self.__state = SealState.SEALED_EMPTY
                return self.__snapshot_locked()

            # Identity attribution remains separate from profile consumption.
            self.__binding = IdentityBinding(
                profile_id=expected.profile_id,
                target_cpus=expected.target_cpus,
                target_mpidrs=expected.target_mpidrs,
                record_identity=expected.record_identity,
                expected=expected.identities,
                running=running.identities,
            )
            blockers.add(Blocker.PROFILE_BINDING_REQUIRED)
            self.__blockers = frozenset(blockers)
            self.__state = SealState.SEALED_IDENTITY
            return self.__snapshot_locked()

    def consume_mt6797_profile(
        self,
        *,
        profile_id: str,
        target_cpus: tuple[int, ...],
        target_mpidrs: tuple[int, ...],
        config_inputs_sha256: bytes,
    ) -> CoreSnapshot:
        """Cross-bind a sealed identity to the exact active MT6797 profile."""

        with self.__lock:
            if self.__profile_consumed:
                self.__fault_locked("repeat-profile-consume")
            self.__profile_consumed = True

            try:
                cpus = tuple(target_cpus)
                mpidrs = tuple(target_mpidrs)
            except TypeError:
                cpus = ()
                mpidrs = ()
            expected = self.__expected
            matches = (
                self.__state is SealState.SEALED_IDENTITY
                and self.__binding is not None
                and expected is not None
                and profile_id == PROFILE_ID
                and cpus == TARGET_CPUS
                and mpidrs == TARGET_MPIDRS
                and isinstance(config_inputs_sha256, bytes)
                and hmac.compare_digest(
                    config_inputs_sha256, ACTIVE_CONFIG_INPUTS_SHA256
                )
                and hmac.compare_digest(
                    expected.fields.config_inputs_sha256,
                    ACTIVE_CONFIG_INPUTS_SHA256,
                )
            )
            blockers = set(self.__blockers)
            blockers.discard(Blocker.PROFILE_BINDING_REQUIRED)
            if matches:
                blockers.discard(Blocker.PROFILE_BINDING_MISMATCH)
                self.__profile_bound = True
            else:
                blockers.add(Blocker.PROFILE_BINDING_MISMATCH)
                self.__profile_bound = False
            self.__blockers = frozenset(blockers)
            return self.__snapshot_locked()
