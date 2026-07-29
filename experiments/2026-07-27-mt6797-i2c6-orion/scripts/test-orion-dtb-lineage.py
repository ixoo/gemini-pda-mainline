#!/usr/bin/env python3
"""Mutation tests for Orion's exact dual-DT-lineage proof."""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import struct
import tempfile
import unittest
from unittest import mock

import candidate_orion as co
import importlib.util


SCRIPT = pathlib.Path(__file__).with_name("validate-orion-dtb-lineage.py")
SPEC = importlib.util.spec_from_file_location("orion_lineage", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
lineage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lineage)
BOOT_SCRIPT = pathlib.Path(__file__).with_name("validate-orion-dtb.py")
BOOT_SPEC = importlib.util.spec_from_file_location("orion_boot_delta", BOOT_SCRIPT)
assert BOOT_SPEC is not None and BOOT_SPEC.loader is not None
boot_delta = importlib.util.module_from_spec(BOOT_SPEC)
BOOT_SPEC.loader.exec_module(boot_delta)


def cells(*values: int) -> bytes:
    return b"".join(struct.pack(">I", value) for value in values)


def string(value: str) -> bytes:
    return value.encode() + b"\0"


class FakeFDT:
    def __init__(self, trees: dict[pathlib.Path, dict[str, dict[str, bytes]]]):
        self.trees = trees

    @staticmethod
    def cells(*values: int) -> bytes:
        return cells(*values)

    @staticmethod
    def string(value: str) -> bytes:
        return string(value)

    @staticmethod
    def require_prop(tree, path, name, expected) -> None:
        if tree.get(path, {}).get(name) != expected:
            raise lineage.ContractError(f"wrong {path}:{name}")

    def parse_fdt(self, path):
        return copy.deepcopy(self.trees[path]), ((0, 0),), 0


def contract_tree(access_handle: int = 0x15) -> dict[str, dict[str, bytes]]:
    return {
        "/": {
            "interrupt-parent": cells(1),
            "#address-cells": cells(2),
            "#size-cells": cells(2),
        },
        lineage.I2C6: {
            "compatible": string(co.I2C6_COMPATIBLE[0]),
            "reg": cells(
                0, 0x1100E000, 0, 0x1000, 0, 0x11000500, 0, 0x80
            ),
            "interrupts": cells(0, 0x58, 8),
            "clocks": cells(3, 0x36, 3, 0x2E),
            "clock-names": string("main") + string("dma"),
            "clock-div": cells(10),
            "#address-cells": cells(1),
            "#size-cells": cells(0),
            "status": string("okay"),
            "access-controllers": cells(access_handle),
        },
        lineage.HANDOFF: {
            "phandle": cells(access_handle),
            "#access-controller-cells": cells(0),
            "compatible": string("mediatek,mt6797-dvfsp-handoff"),
            "status": string("okay"),
        },
        lineage.INFRACFG: {"phandle": cells(3), "#clock-cells": cells(1)},
        lineage.SYSIRQ: {"phandle": cells(1), "#interrupt-cells": cells(3)},
    }


class OrionDTLineageTests(unittest.TestCase):
    def assert_contract_rejected(self, mutate) -> None:
        compiled = contract_tree(0x15)
        boot = contract_tree(0x2C)
        mutate(compiled, boot)
        with self.assertRaises((lineage.ContractError, KeyError)):
            lineage.require_cross_lineage_contract(FakeFDT({}), compiled, boot)

    def test_positive_cross_lineage_contract(self) -> None:
        lineage.require_cross_lineage_contract(
            FakeFDT({}), contract_tree(0x15), contract_tree(0x2C)
        )

    def test_compiled_delta_exactly_one_property(self) -> None:
        cassini = contract_tree()
        cassini[lineage.I2C6]["compatible"] = (
            string("mediatek,mt6797-i2c") + string("mediatek,mt6577-i2c")
        )
        orion = copy.deepcopy(cassini)
        orion[lineage.I2C6]["compatible"] = string(co.I2C6_COMPATIBLE[0])
        with tempfile.TemporaryDirectory() as temporary:
            old = pathlib.Path(temporary) / "old.dtb"
            new = pathlib.Path(temporary) / "new.dtb"
            old.write_bytes(b"old")
            new.write_bytes(b"new")
            parser = FakeFDT({old: cassini, new: orion})
            lineage.require_compiled_delta(parser, old, new)
            changed = copy.deepcopy(orion)
            changed[lineage.I2C6]["unexpected"] = b""
            parser.trees[new] = changed
            with self.assertRaises(lineage.ContractError):
                lineage.require_compiled_delta(parser, old, new)

    def test_boot_delta_rejects_noncompatible_change(self) -> None:
        hubble = contract_tree(0x2C)
        hubble[lineage.I2C6]["compatible"] = (
            string("mediatek,mt6797-i2c") + string("mediatek,mt6577-i2c")
        )
        for cpu in ("/cpus/cpu@200", "/cpus/cpu@201"):
            hubble[cpu] = {"enable-method": string("mediatek,mt6797-psci")}
        candidate = copy.deepcopy(hubble)
        candidate[lineage.I2C6]["compatible"] = string(co.I2C6_COMPATIBLE[0])
        with tempfile.TemporaryDirectory() as temporary:
            old = pathlib.Path(temporary) / "hubble.dtb"
            new = pathlib.Path(temporary) / "orion.dtb"
            old.write_bytes(b"old")
            new.write_bytes(b"new")
            parser = FakeFDT({old: hubble, new: candidate})
            with mock.patch.object(
                boot_delta, "digest", return_value=co.HUBBLE_DTB_SHA256
            ), mock.patch.object(
                boot_delta, "load_fdt_parser", return_value=parser
            ):
                boot_delta.validate(old, new)
                changed = copy.deepcopy(candidate)
                changed["/"]["unexpected"] = b""
                parser.trees[new] = changed
                with self.assertRaises(ValueError):
                    boot_delta.validate(old, new)

    def test_package_positive_and_manifest_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = pathlib.Path(temporary) / co.CASSINI_PACKAGE_DIR
            dtb = package / lineage.COMPILED_DTB
            provenance = package / "provenance/build.json"
            dtb.parent.mkdir(parents=True)
            provenance.parent.mkdir(parents=True)
            dtb.write_bytes(b"exact baseline dt")
            value = {"schema": 1, "generated_utc": "not-pinned"}
            provenance.write_text(json.dumps(value) + "\n", encoding="utf-8")
            normalized = {"schema": 1}
            normalized_hash = hashlib.sha256(
                (json.dumps(normalized, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()

            def write_manifest(duplicate: bool = False) -> None:
                lines = []
                for member in (dtb, provenance):
                    relative = member.relative_to(package).as_posix()
                    digest = hashlib.sha256(member.read_bytes()).hexdigest()
                    lines.append(f"{digest}  ./{relative}\n")
                if duplicate:
                    lines.append(lines[0])
                (package / "SHA256SUMS").write_text("".join(lines), encoding="ascii")

            write_manifest()
            with mock.patch.object(
                co, "CASSINI_COMPILED_DTB_SHA256", hashlib.sha256(dtb.read_bytes()).hexdigest()
            ), mock.patch.object(
                co, "CASSINI_PROVENANCE_SHA256", normalized_hash
            ):
                self.assertEqual(lineage.verify_exact_cassini_package(package), dtb)
                dtb.write_bytes(b"mutated baseline dt")
                write_manifest()
                with self.assertRaises(lineage.ContractError):
                    lineage.verify_exact_cassini_package(package)
                dtb.write_bytes(b"exact baseline dt")
                write_manifest()
                extra = package / "unlisted"
                extra.write_bytes(b"x")
                with self.assertRaises(lineage.ContractError):
                    lineage.verify_exact_cassini_package(package)
                extra.unlink()
                write_manifest(duplicate=True)
                with self.assertRaises(lineage.ContractError):
                    lineage.verify_exact_cassini_package(package)
                write_manifest()
                value["changed"] = True
                provenance.write_text(json.dumps(value) + "\n", encoding="utf-8")
                write_manifest()
                with self.assertRaises(lineage.ContractError):
                    lineage.verify_exact_cassini_package(package)

    def test_status_child_and_property_inventory_rejected(self) -> None:
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "status", string("disabled")
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled.__setitem__(
                lineage.I2C6 + "/child@69", {"reg": cells(0x69)}
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "extra", b""
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled["/"].__setitem__(
                "#address-cells", cells(1)
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.HANDOFF].__setitem__(
                "status", string("disabled")
            )
        )

    def test_register_and_clock_names_rejected(self) -> None:
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "reg",
                cells(0, 0x1100E100, 0, 0x1000, 0, 0x11000500, 0, 0x80),
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "clock-names", string("dma") + string("main")
            )
        )

    def test_unresolved_and_duplicate_phandles_rejected(self) -> None:
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "access-controllers", cells(0x99)
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled.__setitem__(
                "/duplicate", {"phandle": cells(0x15)}
            )
        )

    def test_provider_width_and_truncation_rejected(self) -> None:
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.HANDOFF].__setitem__(
                "#access-controller-cells", cells(1)
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "clocks", cells(3)
            )
        )

    def test_access_provider_and_specifier_rejected(self) -> None:
        def wrong_provider(compiled, _boot):
            compiled["/wrong-access"] = {
                "phandle": cells(0x44),
                "#access-controller-cells": cells(0),
            }
            compiled[lineage.I2C6]["access-controllers"] = cells(0x44)

        self.assert_contract_rejected(wrong_provider)

        def wrong_spec(compiled, _boot):
            compiled[lineage.HANDOFF]["#access-controller-cells"] = cells(1)
            compiled[lineage.I2C6]["access-controllers"] = cells(0x15, 1)

        self.assert_contract_rejected(wrong_spec)

    def test_clock_provider_specifier_and_order_rejected(self) -> None:
        def wrong_provider(compiled, _boot):
            compiled["/wrong-clock"] = {
                "phandle": cells(0x55),
                "#clock-cells": cells(1),
            }
            compiled[lineage.I2C6]["clocks"] = cells(0x55, 0x36, 0x55, 0x2E)

        self.assert_contract_rejected(wrong_provider)
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "clocks", cells(3, 0x37, 3, 0x2E)
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "clocks", cells(3, 0x2E, 3, 0x36)
            )
        )

    def test_effective_irq_parent_and_specifier_rejected(self) -> None:
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled["/"].__setitem__(
                "interrupt-parent", cells(0x99)
            )
        )
        self.assert_contract_rejected(
            lambda compiled, _boot: compiled[lineage.I2C6].__setitem__(
                "interrupts", cells(0, 0x59, 8)
            )
        )


if __name__ == "__main__":
    unittest.main()
