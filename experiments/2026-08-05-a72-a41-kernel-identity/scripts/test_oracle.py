#!/usr/bin/env python3
"""Frozen-vector and bounded adversarial tests for the ABI 7 oracle."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import struct
import sys
import threading
import unittest
from dataclasses import replace
from pathlib import Path

sys.dont_write_bytecode = True

ORACLE_PATH = Path(__file__).resolve().with_name("oracle.py")
SPEC = importlib.util.spec_from_file_location("a41_kernel_identity_oracle", ORACLE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load kernel-identity oracle")
ORACLE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ORACLE
SPEC.loader.exec_module(ORACLE)


# These values are intentionally independent of constants in oracle.py.
EXPECTED_PATH = "/chosen/gemini-late-cpu-provenance"
EXPECTED_COMPATIBLE = b"planet,gemini-a72-runtime-binding-v1\0"
EXPECTED_PROFILE = b"mt6797-a53-a72-a41-v7\0"
EXPECTED_ACTIVE_CONFIG_INPUTS = bytes.fromhex(
    "4dca4e50ab039fbc60593e86d20d02e7"
    "4e257dc6b5bb1afa94b38be6295b5203"
)
EXPECTED_PROPERTY_ORDER = (
    "compatible",
    "schema-version",
    "profile-id",
    "target-cpus",
    "target-mpidrs",
    "expected-ikconfig-identity",
    "expected-gnu-build-id-identity",
    "expected-cmdline-identity",
    "upstream-source-sha256",
    "patch-series-sha256",
    "config-inputs-sha256",
    "resolved-config-sha256",
    "package-image-sha256",
    "build-provenance-sha256",
    "record-identity",
    "name",
)

FROZEN_IKCONFIG_PLAIN = b"CONFIG_A41_ORACLE=y\n# CONFIG_UNUSED is not set\n"
FROZEN_IKCONFIG_GZIP = bytes.fromhex(
    "1f8b08000000000002ff73f6f773f3748f7734318cf70f7274f671b5ade45256"
    "70868886fa8506bbba2864162be4e5972814a796700100cb6ad3122f000000"
)
FROZEN_BUILD_ID = bytes(range(1, 21))
FROZEN_CMDLINE = b"console=ttyS0,921600n8 maxcpus=8"

FROZEN_IKCONFIG_ID = bytes.fromhex(
    "45af0d935ff7d7432fd91115f0f1c7b0fa091a5e8594f1e926da9960c980cbc6"
)
FROZEN_BUILD_ID_ID = bytes.fromhex(
    "23799cbe8b04eb0df824422f5c5fd7ecc6609a753a51598af110a5839b7b5f4b"
)
FROZEN_CMDLINE_ID = bytes.fromhex(
    "e4017e7921f7599ea9f5626d67a7fb199cc0a22d028ab4352aed1ca7de25bf06"
)
FROZEN_PROVENANCE = (
    bytes.fromhex("0f88a502f36c79355da57a912aac70747f2f484e1c8a20cb5f34f712fb9649e0"),
    bytes.fromhex("c313fb17c218708dc05eaf03981ad267013f2bfd3775b0178c5dcaef67ed3415"),
    bytes.fromhex("53bbe19a5f2ef655c9a4bd91a50334a5a935434ca2f39ba11300d78896a6ce14"),
    bytes.fromhex("5ac6d48dedc51f671110b07a531e822128c91cdac44c249a677a45321f64955d"),
    bytes.fromhex("7d02d231f60f4f812c8dbdc4c13f5ada49efa10338e87bac1559c5e75a7a7ec8"),
    bytes.fromhex("824cf8b9ca8210437e5fdf9f1a6aa6e2d3eddbce6211c6229289ff6762456624"),
)
FROZEN_RECORD_ID = bytes.fromhex(
    "acef213ee86902f149a0ad6efbbc706905538a5d1ed411182ae8ec9a1d71e078"
)
FROZEN_RECORD = bytes.fromhex(
    "67656d696e692d6134312d72756e74696d652d62696e64696e672d763100"
    "7265636f7264000000000100156d74363739372d6135332d6137322d613431"
    "2d763700000002000000080000000900000002000000000000020000000000"
    "0000020145af0d935ff7d7432fd91115f0f1c7b0fa091a5e8594f1e926da99"
    "60c980cbc623799cbe8b04eb0df824422f5c5fd7ecc6609a753a51598af110a"
    "5839b7b5f4be4017e7921f7599ea9f5626d67a7fb199cc0a22d028ab4352ae"
    "d1ca7de25bf060f88a502f36c79355da57a912aac70747f2f484e1c8a20cb5"
    "f34f712fb9649e0c313fb17c218708dc05eaf03981ad267013f2bfd3775b017"
    "8c5dcaef67ed341553bbe19a5f2ef655c9a4bd91a50334a5a935434ca2f39ba"
    "11300d78896a6ce145ac6d48dedc51f671110b07a531e822128c91cdac44c249"
    "a677a45321f64955d7d02d231f60f4f812c8dbdc4c13f5ada49efa10338e87b"
    "ac1559c5e75a7a7ec8824cf8b9ca8210437e5fdf9f1a6aa6e2d3eddbce6211"
    "c6229289ff6762456624"
)


def frozen_fields() -> ORACLE.RecordFields:
    return ORACLE.RecordFields(
        FROZEN_IKCONFIG_ID,
        FROZEN_BUILD_ID_ID,
        FROZEN_CMDLINE_ID,
        *FROZEN_PROVENANCE,
    )


def note(owner: bytes, descriptor: bytes, note_type: int) -> bytes:
    """Build one independently encoded little-endian ELF note."""

    return b"".join(
        (
            struct.pack("<III", len(owner), len(descriptor), note_type),
            owner,
            b"\0" * ((-len(owner)) % 4),
            descriptor,
            b"\0" * ((-len(descriptor)) % 4),
        )
    )


FROZEN_BUILD_NOTE = note(b"GNU\0", FROZEN_BUILD_ID, 3)
UNRELATED_NOTE = note(b"TEST", b"abc", 7)


def property_values(fields: ORACLE.RecordFields | None = None) -> dict[str, bytes]:
    selected = fields if fields is not None else frozen_fields()
    return {
        "name": b"gemini-late-cpu-provenance\0",
        "compatible": EXPECTED_COMPATIBLE,
        "schema-version": b"\0\0\0\1",
        "profile-id": EXPECTED_PROFILE,
        "target-cpus": bytes.fromhex("0000000800000009"),
        "target-mpidrs": bytes.fromhex("00000000000002000000000000000201"),
        "expected-ikconfig-identity": selected.expected_ikconfig_identity,
        "expected-gnu-build-id-identity": selected.expected_gnu_build_id_identity,
        "expected-cmdline-identity": selected.expected_cmdline_identity,
        "upstream-source-sha256": selected.upstream_source_sha256,
        "patch-series-sha256": selected.patch_series_sha256,
        "config-inputs-sha256": selected.config_inputs_sha256,
        "resolved-config-sha256": selected.resolved_config_sha256,
        "package-image-sha256": selected.package_image_sha256,
        "build-provenance-sha256": selected.build_provenance_sha256,
        "record-identity": hashlib.sha256(ORACLE.serialize_record(selected)).digest(),
    }


def raw_node(
    *,
    fields: ORACLE.RecordFields | None = None,
    unit_name: str = "gemini-late-cpu-provenance",
    properties: tuple[ORACLE.RawProperty, ...] | None = None,
    children: tuple[ORACLE.RawNode, ...] = (),
) -> ORACLE.RawNode:
    values = property_values(fields)
    selected = properties
    if selected is None:
        selected = tuple(
            ORACLE.RawProperty(name, values[name]) for name in EXPECTED_PROPERTY_ORDER
        )
    return ORACLE.RawNode(unit_name, selected, children)


def raw_tree(
    *,
    fields: ORACLE.RecordFields | None = None,
    provenance: ORACLE.RawNode | None = None,
    root_name: str = "",
    chosen_name: str = "chosen",
    chosen_extra: tuple[ORACLE.RawNode, ...] = (),
    root_extra: tuple[ORACLE.RawNode, ...] = (),
) -> ORACLE.RawNode:
    selected = provenance if provenance is not None else raw_node(fields=fields)
    chosen = ORACLE.RawNode(chosen_name, (), (selected, *chosen_extra))
    return ORACLE.RawNode(root_name, (), (chosen, *root_extra))


def expected_record(
    fields: ORACLE.RecordFields | None = None,
    *,
    source_token: str = "dt:validated-package",
) -> ORACLE.ExpectedRecord:
    return ORACLE.parse_expected_record(
        (raw_tree(fields=fields),), source_token=source_token
    )


def running_record(
    *,
    ikconfig: bytes = FROZEN_IKCONFIG_GZIP,
    notes: bytes = FROZEN_BUILD_NOTE,
    saved: bytes = FROZEN_CMDLINE + b"\0",
    saved_len: int = len(FROZEN_CMDLINE),
    compiled: bytes = FROZEN_CMDLINE,
    source_token: str = "core:running-kernel",
) -> ORACLE.RunningIdentities:
    return ORACLE.derive_running_identities(
        ikconfig_gzip=ikconfig,
        note_blob=notes,
        saved_command_line=saved,
        saved_command_line_len=saved_len,
        compiled_command_line=compiled,
        source_token=source_token,
    )


class KernelIdentityOracleTest(unittest.TestCase):
    def assert_rejected(self, reason: str, operation: object) -> None:
        with self.assertRaisesRegex(ORACLE.OracleRejected, reason):
            operation()  # type: ignore[operator]

    def test_frozen_domain_vectors(self) -> None:
        self.assertEqual(
            ORACLE.ACTIVE_CONFIG_INPUTS_SHA256,
            EXPECTED_ACTIVE_CONFIG_INPUTS,
        )
        self.assertEqual(
            ORACLE.derive_ikconfig_identity(FROZEN_IKCONFIG_GZIP),
            FROZEN_IKCONFIG_ID,
        )
        self.assertEqual(
            ORACLE.derive_gnu_build_id_identity(FROZEN_BUILD_ID),
            FROZEN_BUILD_ID_ID,
        )
        self.assertEqual(
            ORACLE.derive_cmdline_identity(FROZEN_CMDLINE), FROZEN_CMDLINE_ID
        )

    def test_frozen_record_bytes_length_and_identity(self) -> None:
        serialized = ORACLE.serialize_record(frozen_fields())
        self.assertEqual(serialized, FROZEN_RECORD)
        self.assertEqual(len(serialized), 384)
        self.assertEqual(hashlib.sha256(serialized).digest(), FROZEN_RECORD_ID)
        self.assertEqual(ORACLE.record_identity(frozen_fields()), FROZEN_RECORD_ID)

    def test_exact_expected_record_parses(self) -> None:
        properties = raw_node().properties
        self.assertEqual(len(properties), 16)
        self.assertEqual(properties[-1].name, "name")
        self.assertEqual(
            properties[-1].value, b"gemini-late-cpu-provenance\0"
        )
        parsed = expected_record()
        self.assertEqual(parsed.profile_id, "mt6797-a53-a72-a41-v7")
        self.assertEqual(parsed.target_cpus, (8, 9))
        self.assertEqual(parsed.target_mpidrs, (0x200, 0x201))
        self.assertEqual(parsed.record_identity, FROZEN_RECORD_ID)
        self.assertEqual(
            tuple(item.authority for item in parsed.identities.ordered()),
            (ORACLE.Authority.EXPECTED_DT,) * 3,
        )

    def test_running_sources_derive_the_frozen_triplet(self) -> None:
        running = running_record()
        self.assertEqual(
            tuple(item.digest for item in running.identities.ordered()),
            (FROZEN_IKCONFIG_ID, FROZEN_BUILD_ID_ID, FROZEN_CMDLINE_ID),
        )
        self.assertEqual(
            tuple(item.authority for item in running.identities.ordered()),
            (ORACLE.Authority.RUNNING_CORE,) * 3,
        )

    def test_complete_pairs_publish_only_sealed_identity(self) -> None:
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected_record())
        owner.stage_running(running_record())
        self.assertEqual(owner.snapshot().state, ORACLE.SealState.OPEN)
        self.assertIsNone(owner.snapshot().binding)

        result = owner.seal()
        self.assertEqual(result.state, ORACLE.SealState.SEALED_IDENTITY)
        self.assertTrue(result.sealed)
        self.assertTrue(result.identity_complete)
        self.assertIsNotNone(result.binding)
        self.assertEqual(result.binding.record_identity, FROZEN_RECORD_ID)

    def test_sealed_identity_never_implies_runtime_or_ready(self) -> None:
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected_record())
        owner.stage_running(running_record())
        result = owner.seal()
        self.assertFalse(result.target_evidence_published)
        self.assertFalse(result.counts_as_runtime)
        self.assertFalse(result.production_ready)
        self.assertNotEqual(result.state, ORACLE.SealState.SEALED_RUNTIME)
        self.assertEqual(
            result.blockers,
            frozenset(
                {
                    ORACLE.Blocker.PROFILE_BINDING_REQUIRED,
                    ORACLE.Blocker.TARGET_EVIDENCE_UNAVAILABLE,
                    ORACLE.Blocker.RUNTIME_EVIDENCE_UNAVAILABLE,
                    ORACLE.Blocker.COMMIT_PATH_UNAVAILABLE,
                }
            ),
        )

    def test_missing_expected_or_running_half_seals_empty(self) -> None:
        cases = ("both", "expected", "running")
        for case in cases:
            with self.subTest(case=case):
                owner = ORACLE.CoreOwner()
                if case == "expected":
                    owner.stage_expected(expected_record())
                elif case == "running":
                    owner.stage_running(running_record())
                result = owner.seal()
                self.assertEqual(result.state, ORACLE.SealState.SEALED_EMPTY)
                self.assertIsNone(result.binding)
                self.assertFalse(result.identity_complete)
                if case != "expected":
                    self.assertIn(
                        ORACLE.Blocker.EXPECTED_RECORD_MISSING, result.blockers
                    )
                if case != "running":
                    self.assertIn(
                        ORACLE.Blocker.RUNNING_IDENTITIES_MISSING, result.blockers
                    )

    def test_each_identity_pair_mismatch_seals_empty(self) -> None:
        names = (
            "expected_ikconfig_identity",
            "expected_gnu_build_id_identity",
            "expected_cmdline_identity",
        )
        for name in names:
            with self.subTest(field=name):
                fields = replace(frozen_fields(), **{name: b"\xa5" * 32})
                owner = ORACLE.CoreOwner()
                owner.stage_expected(expected_record(fields))
                owner.stage_running(running_record())
                result = owner.seal()
                self.assertEqual(result.state, ORACLE.SealState.SEALED_EMPTY)
                self.assertIsNone(result.binding)
                self.assertIn(ORACLE.Blocker.IDENTITY_MISMATCH, result.blockers)

    def test_same_source_token_is_a_paired_oracle(self) -> None:
        token = "one-source-for-both-halves"
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected_record(source_token=token))
        owner.stage_running(running_record(source_token=token))
        result = owner.seal()
        self.assertEqual(result.state, ORACLE.SealState.SEALED_EMPTY)
        self.assertIn(ORACLE.Blocker.PAIRED_ORACLE, result.blockers)
        self.assertIsNone(result.binding)

    def test_expected_authority_cannot_be_substituted_as_running(self) -> None:
        valid = running_record()
        substituted_observation = replace(
            valid.identities.ikconfig, authority=ORACLE.Authority.EXPECTED_DT
        )
        substituted = replace(
            valid,
            identities=replace(valid.identities, ikconfig=substituted_observation),
        )
        owner = ORACLE.CoreOwner()
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "running-identities-invalid"
        ):
            owner.stage_running(substituted)
        result = owner.snapshot()
        self.assertEqual(result.state, ORACLE.SealState.FAULT)
        self.assertIsNone(result.binding)
        self.assertIn(ORACLE.Blocker.INTERNAL_FAULT, result.blockers)

    def test_root_chosen_and_provenance_hierarchy_is_exact(self) -> None:
        chosen = ORACLE.RawNode("chosen", (), (raw_node(),))
        nested = ORACLE.RawNode(
            "",
            (),
            (
                ORACLE.RawNode(
                    "chosen",
                    (),
                    (ORACLE.RawNode("container", (), (raw_node(),)),),
                ),
            ),
        )
        cases = {
            "absent-root": (),
            "duplicate-root": (raw_tree(), raw_tree()),
            "wrong-root-name": (raw_tree(root_name="root"),),
            "missing-chosen": (ORACLE.RawNode("", (), ()),),
            "chosen-unit-address": (raw_tree(chosen_name="chosen@0"),),
            "duplicate-chosen": (
                raw_tree(root_extra=(ORACLE.RawNode("chosen", (), ()),)),
            ),
            "provenance-unit-address": (
                raw_tree(
                    provenance=raw_node(
                        unit_name="gemini-late-cpu-provenance@0"
                    )
                ),
            ),
            "duplicate-provenance-name": (
                raw_tree(chosen_extra=(raw_node(),)),
            ),
            "direct-provenance-unit-alias": (
                raw_tree(
                    chosen_extra=(
                        ORACLE.RawNode(
                            "gemini-late-cpu-provenance@0", (), ()
                        ),
                    )
                ),
            ),
            "nested-provenance": (nested,),
            "root-node-alias": (ORACLE.RawNode("", (), (chosen, chosen)),),
        }
        for case, roots in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(ORACLE.OracleRejected):
                    ORACLE.parse_expected_record(roots, source_token="dt:test")

    def test_provenance_node_rejects_every_child(self) -> None:
        child = ORACLE.RawNode("harmless", (), ())
        tree = raw_tree(provenance=raw_node(children=(child,)))
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "provenance-node-children"
        ):
            ORACLE.parse_expected_record((tree,), source_token="dt:test")

    def test_recursive_compatible_string_list_alias_is_a_second_candidate(self) -> None:
        alias = ORACLE.RawNode(
            "alias",
            (
                ORACLE.RawProperty(
                    "compatible", b"test,first\0" + EXPECTED_COMPATIBLE
                ),
            ),
        )
        soc = ORACLE.RawNode("soc", (), (alias,))
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "provenance-node-count"
        ):
            ORACLE.parse_expected_record(
                (raw_tree(root_extra=(soc,)),), source_token="dt:test"
            )

    def test_unrelated_hierarchical_nodes_do_not_hide_exact_node(self) -> None:
        unrelated = ORACLE.RawNode(
            "serial@0", (ORACLE.RawProperty("compatible", b"test,uart\0"),)
        )
        soc = ORACLE.RawNode("soc", (), (unrelated,))
        parsed = ORACLE.parse_expected_record(
            (raw_tree(root_extra=(soc,)),), source_token="dt:test"
        )
        self.assertEqual(parsed.record_identity, FROZEN_RECORD_ID)

    def test_name_only_provenance_lookalike_elsewhere_is_unrelated(self) -> None:
        lookalikes = (
            ORACLE.RawNode("gemini-late-cpu-provenance", (), ()),
            ORACLE.RawNode("gemini-late-cpu-provenance@0", (), ()),
        )
        soc = ORACLE.RawNode("soc", (), lookalikes)
        parsed = ORACLE.parse_expected_record(
            (raw_tree(root_extra=(soc,)),), source_token="dt:test"
        )
        self.assertEqual(parsed.record_identity, FROZEN_RECORD_ID)

    def test_every_required_property_is_required(self) -> None:
        canonical = raw_node().properties
        for missing in EXPECTED_PROPERTY_ORDER:
            with self.subTest(missing=missing):
                properties = tuple(prop for prop in canonical if prop.name != missing)
                reason = (
                    "provenance-node-count"
                    if missing == "compatible"
                    else "missing-property"
                )
                with self.assertRaisesRegex(ORACLE.OracleRejected, reason):
                    ORACLE.parse_expected_record(
                        (raw_tree(provenance=raw_node(properties=properties)),),
                        source_token="dt:test",
                    )

    def test_every_property_duplicate_is_rejected_at_varied_positions(self) -> None:
        canonical = raw_node().properties
        for index, duplicate in enumerate(canonical):
            insert_at = (index * 7 + 3) % (len(canonical) + 1)
            properties = (
                canonical[:insert_at]
                + (duplicate,)
                + canonical[insert_at:]
            )
            with self.subTest(name=duplicate.name, insert_at=insert_at):
                with self.assertRaisesRegex(
                    ORACLE.OracleRejected, "duplicate-property"
                ):
                    ORACLE.parse_expected_record(
                        (raw_tree(provenance=raw_node(properties=properties)),),
                        source_token="dt:test",
                    )

    def test_unknown_and_running_properties_are_rejected(self) -> None:
        canonical = raw_node().properties
        cases = {
            "unknown": (
                canonical + (ORACLE.RawProperty("unexpected-attestation", b"x"),),
                "unknown-property",
            ),
            "running": (
                canonical
                + (
                    ORACLE.RawProperty(
                        "running-ikconfig-identity", b"\x01" * 32
                    ),
                ),
                "running-property",
            ),
        }
        for case, (properties, reason) in cases.items():
            with self.subTest(case=case):
                with self.assertRaisesRegex(ORACLE.OracleRejected, reason):
                    ORACLE.parse_expected_record(
                        (raw_tree(provenance=raw_node(properties=properties)),),
                        source_token="dt:test",
                    )

    def test_property_order_is_not_semantic(self) -> None:
        canonical = raw_node().properties
        variants = (
            tuple(reversed(canonical)),
            canonical[5:] + canonical[:5],
            canonical[::2] + canonical[1::2],
        )
        for properties in variants:
            with self.subTest(order=tuple(prop.name for prop in properties)):
                parsed = ORACLE.parse_expected_record(
                    (raw_tree(provenance=raw_node(properties=properties)),),
                    source_token="dt:test",
                )
                self.assertEqual(parsed.record_identity, FROZEN_RECORD_ID)

    def test_string_encodings_are_exact(self) -> None:
        cases = {
            "compatible-no-nul": ("compatible", EXPECTED_COMPATIBLE[:-1]),
            "compatible-extra": ("compatible", EXPECTED_COMPATIBLE + b"x\0"),
            "profile-no-nul": ("profile-id", EXPECTED_PROFILE[:-1]),
            "profile-old": ("profile-id", b"mt6797-a53-a72-a41-v6\0"),
            "name-no-nul": (
                "name",
                b"gemini-late-cpu-provenance",
            ),
            "name-wrong": ("name", b"gemini-late-cpu-provenancf\0"),
        }
        for case, (name, value) in cases.items():
            with self.subTest(case=case):
                props = tuple(
                    ORACLE.RawProperty(
                        prop.name, value if prop.name == name else prop.value
                    )
                    for prop in raw_node().properties
                )
                with self.assertRaises(ORACLE.OracleRejected):
                    ORACLE.parse_expected_record(
                        (raw_tree(provenance=raw_node(properties=props)),),
                        source_token="dt:test",
                    )

    def test_schema_cpu_and_mpidr_encodings_are_exact(self) -> None:
        cases = {
            "schema-value": ("schema-version", bytes.fromhex("00000002")),
            "schema-width": ("schema-version", b"\x01"),
            "cpu-order": ("target-cpus", bytes.fromhex("0000000900000008")),
            "cpu-count": ("target-cpus", bytes.fromhex("00000008")),
            "cpu-little": ("target-cpus", bytes.fromhex("0800000009000000")),
            "mpidr-order": (
                "target-mpidrs",
                bytes.fromhex("00000000000002010000000000000200"),
            ),
            "mpidr-width": ("target-mpidrs", bytes.fromhex("0000020000000201")),
            "mpidr-little": (
                "target-mpidrs",
                bytes.fromhex("00020000000000000102000000000000"),
            ),
        }
        for case, (name, value) in cases.items():
            with self.subTest(case=case):
                props = tuple(
                    ORACLE.RawProperty(
                        prop.name, value if prop.name == name else prop.value
                    )
                    for prop in raw_node().properties
                )
                with self.assertRaises(ORACLE.OracleRejected):
                    ORACLE.parse_expected_record(
                        (raw_tree(provenance=raw_node(properties=props)),),
                        source_token="dt:test",
                    )

    def test_every_digest_rejects_short_long_and_zero_values(self) -> None:
        digest_names = EXPECTED_PROPERTY_ORDER[5:-1]
        mutations = (b"\x01" * 31, b"\x01" * 33, b"\0" * 32)
        for name in digest_names:
            for value in mutations:
                with self.subTest(name=name, length=len(value), zero=not any(value)):
                    props = tuple(
                        ORACLE.RawProperty(
                            prop.name, value if prop.name == name else prop.value
                        )
                        for prop in raw_node().properties
                    )
                    with self.assertRaises(ORACLE.OracleRejected):
                        ORACLE.parse_expected_record(
                            (raw_tree(provenance=raw_node(properties=props)),),
                            source_token="dt:test",
                        )

    def test_record_identity_detects_field_drift(self) -> None:
        props = tuple(
            ORACLE.RawProperty(
                prop.name,
                (bytes([prop.value[0] ^ 1]) + prop.value[1:])
                if prop.name == "patch-series-sha256"
                else prop.value,
            )
            for prop in raw_node().properties
        )
        with self.assertRaisesRegex(ORACLE.OracleRejected, "record-identity-mismatch"):
            ORACLE.parse_expected_record(
                (raw_tree(provenance=raw_node(properties=props)),),
                source_token="dt:test",
            )

    def test_recomputed_record_does_not_allow_unknown_property(self) -> None:
        properties = raw_node().properties + (
            ORACLE.RawProperty("unknown-but-hashed-elsewhere", b"\x01" * 32),
        )
        with self.assertRaisesRegex(ORACLE.OracleRejected, "unknown-property"):
            ORACLE.parse_expected_record(
                (raw_tree(provenance=raw_node(properties=properties)),),
                source_token="dt:test",
            )

    def test_record_serialization_is_sensitive_to_order_and_metadata(self) -> None:
        fields = frozen_fields()
        swapped = replace(
            fields,
            expected_ikconfig_identity=fields.expected_gnu_build_id_identity,
            expected_gnu_build_id_identity=fields.expected_ikconfig_identity,
        )
        variants = (
            ORACLE.serialize_record(swapped),
            ORACLE.serialize_record(fields, schema_version=2),
            ORACLE.serialize_record(fields, profile_id="mt6797-a53-a72-a41-v6"),
            ORACLE.serialize_record(fields, target_cpus=(9, 8)),
            ORACLE.serialize_record(fields, target_mpidrs=(0x201, 0x200)),
        )
        for variant in variants:
            with self.subTest(prefix=variant[:16].hex()):
                self.assertNotEqual(variant, FROZEN_RECORD)
                self.assertNotEqual(hashlib.sha256(variant).digest(), FROZEN_RECORD_ID)

    def test_domains_and_length_widths_are_distinct(self) -> None:
        prefix = b"gemini-a41-runtime-binding-v1\0"
        wrong_tag = hashlib.sha256(
            prefix
            + b"ikconfig\0"
            + struct.pack(">Q", len(FROZEN_CMDLINE))
            + FROZEN_CMDLINE
        ).digest()
        little_length = hashlib.sha256(
            prefix
            + b"cmdline\0"
            + struct.pack("<Q", len(FROZEN_CMDLINE))
            + FROZEN_CMDLINE
        ).digest()
        missing_prefix_nul = hashlib.sha256(
            prefix[:-1]
            + b"cmdline\0"
            + struct.pack(">Q", len(FROZEN_CMDLINE))
            + FROZEN_CMDLINE
        ).digest()
        self.assertNotEqual(wrong_tag, FROZEN_CMDLINE_ID)
        self.assertNotEqual(little_length, FROZEN_CMDLINE_ID)
        self.assertNotEqual(missing_prefix_nul, FROZEN_CMDLINE_ID)

    def test_ikconfig_extraction_requires_unique_ordered_markers(self) -> None:
        image = b"head" + b"IKCFG_ST" + FROZEN_IKCONFIG_GZIP + b"IKCFG_ED" + b"tail"
        self.assertEqual(ORACLE.extract_ikconfig_payload(image), FROZEN_IKCONFIG_GZIP)
        bad_images = (
            FROZEN_IKCONFIG_GZIP,
            b"IKCFG_ST" + image,
            image + b"IKCFG_ED",
            b"IKCFG_ED" + FROZEN_IKCONFIG_GZIP + b"IKCFG_ST",
        )
        for bad in bad_images:
            with self.subTest(size=len(bad)):
                with self.assertRaises(ORACLE.OracleRejected):
                    ORACLE.extract_ikconfig_payload(bad)

    def test_malformed_empty_truncated_and_trailing_ikconfig_are_rejected(self) -> None:
        cases = (
            b"",
            b"not-gzip",
            FROZEN_IKCONFIG_GZIP[:-1],
            FROZEN_IKCONFIG_GZIP + b"trailing",
        )
        for payload in cases:
            with self.subTest(size=len(payload)):
                with self.assertRaises(ORACLE.OracleRejected):
                    ORACLE.derive_ikconfig_identity(payload)

    def test_ikconfig_bounds_concatenation_crc_and_expansion_are_rejected(self) -> None:
        corrupt_crc = bytearray(FROZEN_IKCONFIG_GZIP)
        corrupt_crc[-1] ^= 1
        cases = {
            "compressed-bound": b"x" * (ORACLE.IKCONFIG_MAX_SIZE + 1),
            "concatenated-members": FROZEN_IKCONFIG_GZIP * 2,
            "empty-member": gzip.compress(b"", mtime=0),
            "corrupt-crc": bytes(corrupt_crc),
            "expansion-bound": gzip.compress(
                b"A" * (ORACLE.IKCONFIG_PLAIN_MAX_SIZE + 1), mtime=0
            ),
        }
        for case, payload in cases.items():
            with self.subTest(case=case, size=len(payload)):
                with self.assertRaises(ORACLE.OracleRejected):
                    ORACLE.derive_ikconfig_identity(payload)

    def test_recompressed_ikconfig_is_not_the_same_identity(self) -> None:
        recompressed = gzip.compress(FROZEN_IKCONFIG_PLAIN, compresslevel=1, mtime=1)
        self.assertNotEqual(recompressed, FROZEN_IKCONFIG_GZIP)
        self.assertNotEqual(
            ORACLE.derive_ikconfig_identity(recompressed), FROZEN_IKCONFIG_ID
        )

    def test_strict_build_id_allows_well_formed_unrelated_notes(self) -> None:
        stream = UNRELATED_NOTE + FROZEN_BUILD_NOTE + UNRELATED_NOTE
        self.assertEqual(ORACLE.parse_gnu_build_id_notes(stream), FROZEN_BUILD_ID)

    def test_build_id_count_length_zero_and_malformed_notes_are_rejected(self) -> None:
        cases = {
            "missing": UNRELATED_NOTE,
            "duplicate": FROZEN_BUILD_NOTE + FROZEN_BUILD_NOTE,
            "short-id": note(b"GNU\0", FROZEN_BUILD_ID[:-1], 3),
            "long-id": note(b"GNU\0", FROZEN_BUILD_ID + b"x", 3),
            "zero-id": note(b"GNU\0", b"\0" * 20, 3),
            "header-truncated": b"\x04\0",
            "body-truncated": FROZEN_BUILD_NOTE[:-1],
            "malformed-tail": FROZEN_BUILD_NOTE + b"x",
            "big-endian-header": struct.pack(">III", 4, 20, 3)
            + b"GNU\0"
            + FROZEN_BUILD_ID,
        }
        for case, stream in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(ORACLE.OracleRejected):
                    ORACLE.parse_gnu_build_id_notes(stream)

    def test_build_id_bounds_overflow_and_padding_truncation_are_rejected(self) -> None:
        name_padding = note(b"XYZ", b"", 7)
        descriptor_padding = note(b"TEST", b"abc", 7)
        cases = {
            "note-bound": b"\0" * (ORACLE.NOTE_BLOB_MAX_SIZE + 1),
            "name-align-overflow": struct.pack("<III", 0xFFFFFFFF, 0, 3),
            "descriptor-align-overflow": struct.pack(
                "<III", 0, 0xFFFFFFFF, 3
            ),
            "name-total-overflow": struct.pack(
                "<III", 0xFFFFFFFC, 0, 3
            ),
            "descriptor-total-overflow": struct.pack(
                "<III", 0, 0xFFFFFFFC, 3
            ),
            "name-padding-truncated": FROZEN_BUILD_NOTE + name_padding[:-1],
            "descriptor-padding-truncated": (
                FROZEN_BUILD_NOTE + descriptor_padding[:-1]
            ),
        }
        for case, stream in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(ORACLE.OracleRejected):
                    ORACLE.parse_gnu_build_id_notes(stream)

    def test_nonexact_gnu_owner_is_unrelated_not_a_second_build_id(self) -> None:
        stream = (
            note(b"GNU", FROZEN_BUILD_ID, 3)
            + note(b"GNU\0extra", FROZEN_BUILD_ID, 3)
            + FROZEN_BUILD_NOTE
        )
        self.assertEqual(ORACLE.parse_gnu_build_id_notes(stream), FROZEN_BUILD_ID)

    def test_command_line_storage_and_force_policy_are_exact(self) -> None:
        self.assertEqual(
            running_record().identities.cmdline.digest,
            FROZEN_CMDLINE_ID,
        )
        cases = {
            "no-terminal-nul": (FROZEN_CMDLINE, len(FROZEN_CMDLINE), FROZEN_CMDLINE),
            "length-includes-nul": (
                FROZEN_CMDLINE + b"\0",
                len(FROZEN_CMDLINE) + 1,
                FROZEN_CMDLINE,
            ),
            "embedded-nul": (
                FROZEN_CMDLINE[:7] + b"\0" + FROZEN_CMDLINE[8:] + b"\0",
                len(FROZEN_CMDLINE),
                FROZEN_CMDLINE,
            ),
            "compiled-nul": (
                FROZEN_CMDLINE + b"\0",
                len(FROZEN_CMDLINE),
                FROZEN_CMDLINE + b"\0",
            ),
        }
        for case, (saved, saved_len, compiled) in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(ORACLE.OracleRejected):
                    running_record(saved=saved, saved_len=saved_len, compiled=compiled)

    def test_command_line_whitespace_order_and_bootconfig_drift_fail(
        self,
    ) -> None:
        variants = (
            FROZEN_CMDLINE + b" ",
            b"maxcpus=8 console=ttyS0,921600n8",
            FROZEN_CMDLINE[:-1],
            b"bootconfig.option=1 " + FROZEN_CMDLINE,
        )
        for saved_payload in variants:
            with self.subTest(saved=saved_payload):
                with self.assertRaisesRegex(
                    ORACLE.OracleRejected, "forced-command-line-mismatch"
                ):
                    running_record(
                        saved=saved_payload + b"\0",
                        saved_len=len(saved_payload),
                        compiled=FROZEN_CMDLINE,
                    )

    def test_raw_resolved_config_hash_cannot_substitute_for_ikconfig(self) -> None:
        raw_config_digest = hashlib.sha256(FROZEN_IKCONFIG_PLAIN).digest()
        self.assertNotEqual(raw_config_digest, FROZEN_IKCONFIG_ID)
        fields = replace(
            frozen_fields(), expected_ikconfig_identity=raw_config_digest
        )
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected_record(fields))
        owner.stage_running(running_record())
        result = owner.seal()
        self.assertEqual(result.state, ORACLE.SealState.SEALED_EMPTY)
        self.assertIn(ORACLE.Blocker.IDENTITY_MISMATCH, result.blockers)

    def test_failed_parse_cannot_publish_a_partial_binding(self) -> None:
        owner = ORACLE.CoreOwner()
        malformed = raw_node(properties=raw_node().properties[:-1])
        with self.assertRaises(ORACLE.OracleRejected):
            owner.stage_expected(
                ORACLE.parse_expected_record(
                    (raw_tree(provenance=malformed),), source_token="dt:test"
                )
            )
        owner.stage_running(running_record())
        result = owner.seal()
        self.assertEqual(result.state, ORACLE.SealState.SEALED_EMPTY)
        self.assertIsNone(result.binding)
        self.assertIn(ORACLE.Blocker.EXPECTED_RECORD_MISSING, result.blockers)

    def test_duplicate_expected_and_running_stage_fault_and_clear(self) -> None:
        cases = ("expected", "running")
        for case in cases:
            with self.subTest(case=case):
                owner = ORACLE.CoreOwner()
                if case == "expected":
                    owner.stage_expected(expected_record())
                    operation = lambda: owner.stage_expected(
                        expected_record(source_token="dt:second")
                    )
                else:
                    owner.stage_running(running_record())
                    operation = lambda: owner.stage_running(
                        running_record(source_token="core:second")
                    )
                with self.assertRaisesRegex(
                    ORACLE.OracleRejected, f"duplicate-{case}-stage"
                ):
                    operation()
                state = owner.snapshot()
                self.assertEqual(state.state, ORACLE.SealState.FAULT)
                self.assertIsNone(state.binding)
                self.assertIn(ORACLE.Blocker.INTERNAL_FAULT, state.blockers)

    def test_invalid_expected_and_running_objects_fault(self) -> None:
        invalid_expected = replace(expected_record(), _producer_token=object())
        invalid_running = replace(running_record(), _producer_token=object())
        cases = (
            (
                "expected",
                invalid_expected,
                lambda owner, value: owner.stage_expected(value),
            ),
            (
                "running",
                invalid_running,
                lambda owner, value: owner.stage_running(value),
            ),
        )
        for case, value, operation in cases:
            with self.subTest(case=case):
                owner = ORACLE.CoreOwner()
                with self.assertRaisesRegex(
                    ORACLE.OracleRejected, f"{case}-.+-invalid"
                ):
                    operation(owner, value)
                state = owner.snapshot()
                self.assertEqual(state.state, ORACLE.SealState.FAULT)
                self.assertIsNone(state.binding)

    def test_direct_label_forgery_is_not_a_running_producer(self) -> None:
        expected = expected_record()
        source_token = "forged:labels-only"
        forged_triplet = ORACLE.IdentityTriplet(
            *(
                replace(
                    observation,
                    authority=ORACLE.Authority.RUNNING_CORE,
                    source_token=source_token,
                )
                for observation in expected.identities.ordered()
            )
        )
        forged = ORACLE.RunningIdentities(
            forged_triplet, source_token, object()
        )
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected)
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "running-identities-invalid"
        ):
            owner.stage_running(forged)
        self.assertEqual(owner.snapshot().state, ORACLE.SealState.FAULT)

    def test_public_snapshot_construction_is_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "owner-produced"):
            ORACLE.CoreSnapshot()
        with self.assertRaisesRegex(TypeError, "owner-produced"):
            ORACLE.CoreSnapshot(
                ORACLE.SealState.SEALED_RUNTIME,
                True,
                None,
                frozenset(),
                True,
                True,
                True,
                True,
                True,
                True,
            )
        with self.assertRaisesRegex(TypeError, "owner-produced"):
            ORACLE.CoreSnapshot._from_owner(
                object(),
                state=ORACLE.SealState.SEALED_RUNTIME,
                binding=None,
                blockers=frozenset(),
                profile_bound=True,
            )

    def test_mt6797_profile_cross_bind_is_explicit_and_identity_only(self) -> None:
        fields = replace(
            frozen_fields(),
            config_inputs_sha256=EXPECTED_ACTIVE_CONFIG_INPUTS,
        )
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected_record(fields))
        owner.stage_running(running_record())
        sealed = owner.seal()
        self.assertEqual(sealed.state, ORACLE.SealState.SEALED_IDENTITY)
        self.assertFalse(sealed.profile_bound)
        self.assertFalse(sealed.overlay_eligible)
        self.assertIn(ORACLE.Blocker.PROFILE_BINDING_REQUIRED, sealed.blockers)

        bound = owner.consume_mt6797_profile(
            profile_id="mt6797-a53-a72-a41-v7",
            target_cpus=(8, 9),
            target_mpidrs=(0x200, 0x201),
            config_inputs_sha256=EXPECTED_ACTIVE_CONFIG_INPUTS,
        )
        self.assertEqual(bound.state, ORACLE.SealState.SEALED_IDENTITY)
        self.assertTrue(bound.profile_bound)
        self.assertTrue(bound.overlay_eligible)
        self.assertFalse(bound.target_evidence_published)
        self.assertFalse(bound.counts_as_runtime)
        self.assertFalse(bound.production_ready)
        self.assertNotEqual(bound.state, ORACLE.SealState.SEALED_RUNTIME)
        self.assertNotIn(ORACLE.Blocker.PROFILE_BINDING_REQUIRED, bound.blockers)

    def test_each_mt6797_cross_bind_mismatch_blocks_overlay(self) -> None:
        active_fields = replace(
            frozen_fields(),
            config_inputs_sha256=EXPECTED_ACTIVE_CONFIG_INPUTS,
        )
        cases = {
            "profile": {
                "profile_id": "mt6797-a53-a72-a41-v6",
            },
            "cpus": {"target_cpus": (9, 8)},
            "mpidrs": {"target_mpidrs": (0x201, 0x200)},
            "supplied-config": {"config_inputs_sha256": b"\xa5" * 32},
            "record-config": {},
        }
        for case, overrides in cases.items():
            with self.subTest(case=case):
                fields = frozen_fields() if case == "record-config" else active_fields
                owner = ORACLE.CoreOwner()
                owner.stage_expected(expected_record(fields))
                owner.stage_running(running_record())
                owner.seal()
                arguments = {
                    "profile_id": "mt6797-a53-a72-a41-v7",
                    "target_cpus": (8, 9),
                    "target_mpidrs": (0x200, 0x201),
                    "config_inputs_sha256": EXPECTED_ACTIVE_CONFIG_INPUTS,
                }
                arguments.update(overrides)
                state = owner.consume_mt6797_profile(**arguments)
                self.assertEqual(state.state, ORACLE.SealState.SEALED_IDENTITY)
                self.assertFalse(state.profile_bound)
                self.assertFalse(state.overlay_eligible)
                self.assertIn(
                    ORACLE.Blocker.PROFILE_BINDING_MISMATCH, state.blockers
                )
                self.assertFalse(state.production_ready)

    def test_repeat_profile_consumption_faults_and_clears_binding(self) -> None:
        fields = replace(
            frozen_fields(),
            config_inputs_sha256=EXPECTED_ACTIVE_CONFIG_INPUTS,
        )
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected_record(fields))
        owner.stage_running(running_record())
        owner.seal()
        arguments = {
            "profile_id": "mt6797-a53-a72-a41-v7",
            "target_cpus": (8, 9),
            "target_mpidrs": (0x200, 0x201),
            "config_inputs_sha256": EXPECTED_ACTIVE_CONFIG_INPUTS,
        }
        self.assertTrue(owner.consume_mt6797_profile(**arguments).profile_bound)
        with self.assertRaisesRegex(
            ORACLE.OracleRejected, "repeat-profile-consume"
        ):
            owner.consume_mt6797_profile(**arguments)
        state = owner.snapshot()
        self.assertEqual(state.state, ORACLE.SealState.FAULT)
        self.assertIsNone(state.binding)
        self.assertFalse(state.profile_bound)
        self.assertFalse(state.overlay_eligible)

    def test_snapshot_is_coherent_while_seal_races_readers(self) -> None:
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected_record())
        owner.stage_running(running_record())
        barrier = threading.Barrier(5)
        results: list[ORACLE.CoreSnapshot] = []
        results_lock = threading.Lock()

        def reader() -> None:
            barrier.wait()
            local = [owner.snapshot() for _ in range(500)]
            with results_lock:
                results.extend(local)

        readers = [threading.Thread(target=reader) for _ in range(4)]
        for thread in readers:
            thread.start()
        barrier.wait()
        owner.seal()
        for thread in readers:
            thread.join()

        self.assertTrue(results)
        for snapshot in results:
            if snapshot.state is ORACLE.SealState.OPEN:
                self.assertIsNone(snapshot.binding)
                self.assertIn(
                    ORACLE.Blocker.IDENTITY_NOT_SEALED, snapshot.blockers
                )
            elif snapshot.state is ORACLE.SealState.SEALED_IDENTITY:
                self.assertIsNotNone(snapshot.binding)
                self.assertIn(
                    ORACLE.Blocker.PROFILE_BINDING_REQUIRED, snapshot.blockers
                )
            else:
                self.fail(f"mixed or unexpected snapshot: {snapshot.state}")

    def test_post_seal_expected_and_running_stage_fault_and_clear(self) -> None:
        for case in ("expected", "running"):
            with self.subTest(case=case):
                owner = ORACLE.CoreOwner()
                owner.stage_expected(expected_record())
                owner.stage_running(running_record())
                self.assertEqual(
                    owner.seal().state, ORACLE.SealState.SEALED_IDENTITY
                )
                if case == "expected":
                    operation = lambda: owner.stage_expected(expected_record())
                else:
                    operation = lambda: owner.stage_running(running_record())
                with self.assertRaisesRegex(
                    ORACLE.OracleRejected, f"post-seal-{case}-stage"
                ):
                    operation()
                state = owner.snapshot()
                self.assertEqual(state.state, ORACLE.SealState.FAULT)
                self.assertIsNone(state.binding)
                self.assertIn(ORACLE.Blocker.INTERNAL_FAULT, state.blockers)
                self.assertFalse(state.production_ready)

    def test_repeat_seal_faults_and_never_reaches_runtime(self) -> None:
        owner = ORACLE.CoreOwner()
        owner.stage_expected(expected_record())
        owner.stage_running(running_record())
        owner.seal()
        with self.assertRaisesRegex(ORACLE.OracleRejected, "repeat-seal"):
            owner.seal()
        state = owner.snapshot()
        self.assertEqual(state.state, ORACLE.SealState.FAULT)
        self.assertNotEqual(state.state, ORACLE.SealState.SEALED_RUNTIME)
        self.assertFalse(state.counts_as_runtime)
        self.assertFalse(state.production_ready)


if __name__ == "__main__":
    unittest.main(verbosity=2)
