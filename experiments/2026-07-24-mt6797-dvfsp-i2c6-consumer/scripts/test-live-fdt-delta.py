#!/usr/bin/env python3
"""Device-inert tests for Candidate AP's private live-FDT allowlist."""

from __future__ import annotations

import copy
import importlib.util
import pathlib
import struct
import sys
import unittest


sys.dont_write_bytecode = True

SOURCE = pathlib.Path(__file__).with_name("validate-live-fdt-delta.py")
SPEC = importlib.util.spec_from_file_location("candidate_ap_live_fdt_delta", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AP live-FDT validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class FakeFdt:
    @staticmethod
    def string(value: str) -> bytes:
        return value.encode("ascii") + b"\0"

    @staticmethod
    def cells(*values: int) -> bytes:
        return struct.pack(">" + "I" * len(values), *values)

    @staticmethod
    def require_prop(
        tree: dict[str, dict[str, bytes]],
        path: str,
        name: str,
        value: bytes,
    ) -> None:
        if tree.get(path, {}).get(name) != value:
            raise ValueError(f"unexpected {path}:{name}")


class FakeCommon:
    @staticmethod
    def cstring(value: bytes, label: str) -> None:
        if (
            not value
            or not value.endswith(b"\0")
            or value.count(b"\0") != 1
            or any(byte < 0x20 or byte > 0x7E for byte in value[:-1])
        ):
            raise ValueError(f"{label} is not one printable string")


def handoff_fixture() -> tuple[
    dict[str, dict[str, bytes]],
    dict[str, dict[str, bytes]],
]:
    fdt = FakeFdt()
    artifact = {
        VALIDATOR.HANDOFF: {
            "compatible": fdt.string("mediatek,mt6797-dvfsp-handoff"),
            "reg": fdt.cells(0, 0x11015000, 0, 0x1000),
            "clocks": fdt.cells(0x3, 0x36),
            "clock-names": fdt.string("i2c"),
            "mediatek,infracfg": fdt.cells(0x3),
            "status": fdt.string("okay"),
            "#access-controller-cells": fdt.cells(0),
            "phandle": fdt.cells(0x2C),
        },
        VALIDATOR.INFRACFG: {
            "compatible": (
                fdt.string("mediatek,mt6797-infracfg")
                + fdt.string("syscon")
            ),
            "phandle": fdt.cells(0x3),
        },
        VALIDATOR.I2C6: {
            "status": fdt.string("okay"),
            "access-controllers": fdt.cells(0x2C),
        },
        VALIDATOR.CPU8: {
            "enable-method": fdt.string("mediatek,mt6797-psci"),
        },
        VALIDATOR.CPU9: {
            "enable-method": fdt.string("mediatek,mt6797-psci"),
        },
    }
    return artifact, copy.deepcopy(artifact)


class HandoffContractTests(unittest.TestCase):
    def test_exact_fail_closed_contract_is_accepted(self) -> None:
        artifact, live = handoff_fixture()
        VALIDATOR.require_handoff_contract(FakeFdt(), artifact, live)

    def test_every_handoff_property_mutation_is_rejected(self) -> None:
        artifact, live = handoff_fixture()
        for name in artifact[VALIDATOR.HANDOFF]:
            with self.subTest(name=name):
                mutated = copy.deepcopy(live)
                mutated[VALIDATOR.HANDOFF][name] += b"\xff"
                with self.assertRaises(ValueError):
                    VALIDATOR.require_handoff_contract(
                        FakeFdt(),
                        artifact,
                        mutated,
                    )

    def test_wrong_i2c_appm_clock_is_rejected(self) -> None:
        artifact, live = handoff_fixture()
        live[VALIDATOR.HANDOFF]["clocks"] = FakeFdt.cells(0x3, 0x37)
        with self.assertRaises(ValueError):
            VALIDATOR.require_handoff_contract(FakeFdt(), artifact, live)

    def test_infracfg_phandle_resolution_is_exact(self) -> None:
        artifact, live = handoff_fixture()
        cases = []

        wrong_compatible = copy.deepcopy(live)
        wrong_compatible[VALIDATOR.INFRACFG]["compatible"] = FakeFdt.string(
            "syscon"
        )
        cases.append(wrong_compatible)

        wrong_phandle = copy.deepcopy(live)
        wrong_phandle[VALIDATOR.INFRACFG]["phandle"] = FakeFdt.cells(0x4)
        cases.append(wrong_phandle)

        duplicate_phandle = copy.deepcopy(live)
        duplicate_phandle["/unexpected-provider"] = {
            "phandle": FakeFdt.cells(0x3),
        }
        cases.append(duplicate_phandle)

        for mutated in cases:
            with self.subTest():
                with self.assertRaises(ValueError):
                    VALIDATOR.require_handoff_contract(
                        FakeFdt(),
                        artifact,
                        mutated,
                    )

    def test_i2c6_child_and_forbidden_nodes_are_rejected(self) -> None:
        artifact, live = handoff_fixture()
        forbidden = (
            VALIDATOR.I2C6 + "/client@68",
            VALIDATOR.OBSERVER,
            VALIDATOR.DA9214,
            VALIDATOR.A72_POWER,
            VALIDATOR.LEGACY_DVFSP,
        )
        for path in forbidden:
            with self.subTest(path=path):
                mutated = copy.deepcopy(live)
                mutated[path] = {}
                with self.assertRaises(ValueError):
                    VALIDATOR.require_handoff_contract(
                        FakeFdt(),
                        artifact,
                        mutated,
                    )

    def test_access_controller_reference_must_resolve_exactly(self) -> None:
        artifact, live = handoff_fixture()
        mutations = []
        wrong_reference = copy.deepcopy(live)
        wrong_reference[VALIDATOR.I2C6]["access-controllers"] = FakeFdt.cells(0x2B)
        mutations.append(wrong_reference)
        wrong_cells = copy.deepcopy(live)
        wrong_cells[VALIDATOR.HANDOFF]["#access-controller-cells"] = FakeFdt.cells(1)
        mutations.append(wrong_cells)
        duplicate = copy.deepcopy(live)
        duplicate["/unexpected-controller"] = {"phandle": FakeFdt.cells(0x2C)}
        mutations.append(duplicate)
        for mutated in mutations:
            with self.subTest():
                with self.assertRaises(ValueError):
                    VALIDATOR.require_handoff_contract(
                        FakeFdt(), artifact, mutated
                    )

    def test_cpu_rejecting_method_mutation_is_rejected(self) -> None:
        artifact, live = handoff_fixture()
        live[VALIDATOR.CPU8]["enable-method"] = FakeFdt.string("psci")
        with self.assertRaises(ValueError):
            VALIDATOR.require_handoff_contract(FakeFdt(), artifact, live)


class DynamicShapeTests(unittest.TestCase):
    @staticmethod
    def atag_cmdline(payload: bytes) -> bytes:
        raw = struct.pack("<2I", 0, VALIDATOR.ATAG_CMDLINE_TAG) + payload
        raw += b"\0" * (-len(raw) % 4)
        return struct.pack("<I", len(raw) // 4) + raw[4:]

    def fixture(self) -> dict[str, dict[str, bytes]]:
        return {
            "/chosen": {
                "atag,cmdline": self.atag_cmdline(b"a\0"),
                "bootargs": b"a\0",
            }
        }

    def test_bounded_printable_cmdlines_are_accepted(self) -> None:
        live = self.fixture()
        live["/chosen"]["atag,cmdline"] = self.atag_cmdline(
            b"x" * (VALIDATOR.ATAG_CMDLINE_MAX_LENGTH - 9) + b"\0"
        )
        for name, maximum in VALIDATOR.DYNAMIC_CMDLINE_MAX_LENGTHS.items():
            live["/chosen"][name] = b"x" * (maximum - 1) + b"\0"
        VALIDATOR.require_dynamic_cmdline_shapes(FakeCommon(), live)

    def test_atag_cmdline_and_bootargs_must_match(self) -> None:
        live = self.fixture()
        live["/chosen"]["bootargs"] = b"b\0"
        with self.assertRaises(ValueError):
            VALIDATOR.require_dynamic_cmdline_shapes(FakeCommon(), live)

    def test_malformed_or_oversized_cmdlines_are_rejected(self) -> None:
        cases = (
            b"unterminated",
            b"two\0strings\0",
            b"x" * VALIDATOR.DYNAMIC_CMDLINE_MAX_LENGTHS["bootargs"] + b"\0",
        )
        for value in cases:
            with self.subTest(value_length=len(value)):
                live = self.fixture()
                live["/chosen"]["bootargs"] = value
                with self.assertRaises(ValueError):
                    VALIDATOR.require_dynamic_cmdline_shapes(FakeCommon(), live)

    def test_malformed_atag_cmdline_is_rejected(self) -> None:
        cases = (
            b"too-short",
            struct.pack("<2I", 4, VALIDATOR.ATAG_CMDLINE_TAG) + b"x\0\0\0",
            struct.pack("<2I", 3, 0xDEADBEEF) + b"x\0\0\0",
            struct.pack("<2I", 3, VALIDATOR.ATAG_CMDLINE_TAG) + b"xxxx",
        )
        for value in cases:
            with self.subTest(value_length=len(value)):
                live = self.fixture()
                live["/chosen"]["atag,cmdline"] = value
                with self.assertRaises(ValueError):
                    VALIDATOR.require_dynamic_cmdline_shapes(FakeCommon(), live)


class SourcePinTests(unittest.TestCase):
    def test_common_delta_inventory_and_source_pins(self) -> None:
        _, common, _ = VALIDATOR.load_inputs()
        entries = (
            len(common.EXPECTED_ADDED_NODES)
            + len(common.EXPECTED_REMOVED_NODES)
            + len(common.EXPECTED_ADDED_PROPERTIES)
            + len(common.EXPECTED_CHANGED_PROPERTIES)
        )
        self.assertEqual(entries, 37)
        self.assertEqual(
            VALIDATOR.EXPECTED_LIVE_FDT_SHA256,
            "7b00d5eee94307d9f78e48ea0d3aeaf7081e54ffae98e89168596f6ee4e4d6a7",
        )
        self.assertEqual(
            VALIDATOR.EXPECTED_LIVE_FDT_SIZE,
            52655,
        )

    def test_source_does_not_embed_private_path_or_serial_value(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("/private/tmp/", source)
        self.assertNotIn("serialno=", source)
        self.assertIn(
            "device_unique_serial=validated-in-memory-not-emitted",
            source,
        )


if __name__ == "__main__":
    unittest.main()
