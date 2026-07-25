#!/usr/bin/env python3
"""Device-inert tests for Candidate AN's private live-FDT allowlist."""

from __future__ import annotations

import copy
import importlib.util
import pathlib
import struct
import sys
import unittest


sys.dont_write_bytecode = True

SOURCE = pathlib.Path(__file__).with_name("validate-live-fdt-delta.py")
SPEC = importlib.util.spec_from_file_location("candidate_an_live_fdt_delta", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AN live-FDT validator")
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


def delta_fixture() -> tuple[
    dict[str, dict[str, bytes]], dict[str, dict[str, bytes]]
]:
    artifact: dict[str, dict[str, bytes]] = {
        "/": {"model": b"artifact"},
        "/scp@10020000": {"status": b"disabled\0"},
        "/chosen": {},
        "/memory@40000000": {},
    }
    for path in VALIDATOR.EXPECTED_REMOVED_NODES:
        artifact[path] = {"placeholder": b""}
    live = copy.deepcopy(artifact)
    live["/"]["model"] = b"live"
    live["/scp@10020000"]["status"] = b"okay"
    for path, name in VALIDATOR.EXPECTED_ADDED_PROPERTIES:
        live[path][name] = b"x"
    for path in VALIDATOR.EXPECTED_ADDED_NODES:
        live[path] = {}
    for path in VALIDATOR.EXPECTED_REMOVED_NODES:
        del live[path]
    return artifact, live


def observer_fixture() -> tuple[
    dict[str, dict[str, bytes]], dict[str, dict[str, bytes]]
]:
    fdt = FakeFdt()
    artifact = {
        VALIDATOR.OBSERVER: {
            "compatible": fdt.string(
                "mediatek,mt6797-dvfsp-handoff-observer"
            ),
            "reg": fdt.cells(0, 0x11015000, 0, 0x1000),
        },
        VALIDATOR.I2C6: {"status": fdt.string("disabled")},
        VALIDATOR.CPU8: {
            "enable-method": fdt.string("mediatek,mt6797-psci")
        },
        VALIDATOR.CPU9: {
            "enable-method": fdt.string("mediatek,mt6797-psci")
        },
    }
    return artifact, copy.deepcopy(artifact)


class DeltaInventoryTests(unittest.TestCase):
    def test_exact_lk_inventory_is_accepted(self) -> None:
        artifact, live = delta_fixture()
        VALIDATOR.require_exact_delta(artifact, live)
        self.assertEqual(
            len(VALIDATOR.EXPECTED_ADDED_NODES)
            + len(VALIDATOR.EXPECTED_REMOVED_NODES)
            + len(VALIDATOR.EXPECTED_ADDED_PROPERTIES)
            + len(VALIDATOR.EXPECTED_CHANGED_PROPERTIES),
            37,
        )

    def test_unexpected_existing_property_is_rejected(self) -> None:
        artifact, live = delta_fixture()
        live["/chosen"]["unexpected"] = b"x"
        with self.assertRaises(ValueError):
            VALIDATOR.require_exact_delta(artifact, live)

    def test_unexpected_node_is_rejected(self) -> None:
        artifact, live = delta_fixture()
        live["/unexpected"] = {}
        with self.assertRaises(ValueError):
            VALIDATOR.require_exact_delta(artifact, live)


class ObserverContractTests(unittest.TestCase):
    def test_unchanged_fail_closed_contract_is_accepted(self) -> None:
        artifact, live = observer_fixture()
        VALIDATOR.require_observer_contract(FakeFdt(), artifact, live)

    def test_observer_property_mutation_is_rejected(self) -> None:
        artifact, live = observer_fixture()
        live[VALIDATOR.OBSERVER]["reg"] = FakeFdt.cells(
            0, 0x11015000, 0, 0x2000
        )
        with self.assertRaises(ValueError):
            VALIDATOR.require_observer_contract(FakeFdt(), artifact, live)

    def test_i2c6_child_is_rejected(self) -> None:
        artifact, live = observer_fixture()
        live[VALIDATOR.I2C6 + "/client@68"] = {}
        with self.assertRaises(ValueError):
            VALIDATOR.require_observer_contract(FakeFdt(), artifact, live)


class SensitiveShapeTests(unittest.TestCase):
    def test_private_string_validation_does_not_return_value(self) -> None:
        self.assertIsNone(VALIDATOR.cstring(b"REDACTED-FIXTURE\0", "serial"))
        with self.assertRaises(ValueError):
            VALIDATOR.cstring(b"unterminated", "serial")

    def test_region_rejects_zero_and_overflow(self) -> None:
        with self.assertRaises(ValueError):
            VALIDATOR.region(struct.pack(">4I", 0, 1, 0, 0), "zero")
        with self.assertRaises(ValueError):
            VALIDATOR.region(
                struct.pack(">4I", 0xFFFFFFFF, 0xFFFFFFF0, 0, 0x20),
                "overflow",
            )

    def test_source_does_not_embed_private_path_or_serial_value(self) -> None:
        source = SOURCE.read_text()
        self.assertNotIn("/private/tmp/", source)
        self.assertNotIn("serialno=", source)
        self.assertIn("device_unique_serial=validated-in-memory-not-emitted", source)


if __name__ == "__main__":
    unittest.main()
