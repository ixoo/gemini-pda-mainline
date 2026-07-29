#!/usr/bin/env python3
"""Prove Orion's compiled and boot DT lineages carry one identical I2C6 contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import pathlib
import stat
import struct
import sys
from types import ModuleType

sys.dont_write_bytecode = True

import candidate_orion as co


COMPILED_DTB = pathlib.PurePosixPath("dtbs/mediatek/mt6797-gemini-pda.dtb")
I2C6 = "/i2c@1100e000"
HANDOFF = "/dvfsp-handoff@11015000"
INFRACFG = "/syscon@10001000"
SYSIRQ = "/interrupt-controller@10200620"
I2C6_PROPERTIES = {
    "compatible",
    "reg",
    "interrupts",
    "clocks",
    "clock-names",
    "clock-div",
    "#address-cells",
    "#size-cells",
    "status",
    "access-controllers",
}


class ContractError(ValueError):
    """A package, DT lineage, or resolved resource contract changed."""


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ContractError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def directory(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ContractError(f"{label} is missing or unsafe")


def verify_exact_cassini_package(package: pathlib.Path) -> pathlib.Path:
    directory(package, "exact Cassini package")
    if package.name != co.CASSINI_PACKAGE_DIR:
        raise ContractError("wrong pre-Orion Cassini package directory")
    manifest_path = package / "SHA256SUMS"
    manifest = regular(manifest_path, "Cassini package manifest")
    seen: set[str] = set()
    for line in manifest.decode("ascii").splitlines():
        if len(line) < 69 or line[64:68] != "  ./":
            raise ContractError("Cassini package checksum line is malformed")
        wanted = line[:64]
        relative = line[68:]
        pure = pathlib.PurePosixPath(relative)
        if (
            len(wanted) != 64
            or any(character not in "0123456789abcdef" for character in wanted)
            or not relative
            or pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != relative
            or relative in seen
        ):
            raise ContractError("Cassini package checksum entry is unsafe")
        seen.add(relative)
        member = package / relative
        regular(member, f"Cassini package member {relative}")
        if digest_path(member) != wanted:
            raise ContractError(f"Cassini package checksum failed: {relative}")

    actual: set[str] = set()
    for member in package.rglob("*"):
        relative = member.relative_to(package).as_posix()
        info = member.lstat()
        if member.is_symlink():
            raise ContractError(f"Cassini package contains symlink: {relative}")
        if stat.S_ISREG(info.st_mode):
            if relative != "SHA256SUMS":
                actual.add(relative)
        elif not stat.S_ISDIR(info.st_mode):
            raise ContractError(
                f"Cassini package contains special member: {relative}"
            )
    if actual != seen:
        raise ContractError("Cassini package manifest inventory is incomplete")

    compiled = package / COMPILED_DTB
    if digest_path(compiled) != co.CASSINI_COMPILED_DTB_SHA256:
        raise ContractError("exact pre-Orion compiled Gemini DT changed")
    provenance = json.loads(
        regular(package / "provenance/build.json", "Cassini build provenance")
    )
    if (
        not isinstance(provenance, dict)
        or "generated_utc" not in provenance
        or set(provenance).intersection(
            {"build_dir", "source_dir", "artifact_dir"}
        )
    ):
        raise ContractError("Cassini build provenance contract changed")
    del provenance["generated_utc"]
    normalized = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode()
    if hashlib.sha256(normalized).hexdigest() != co.CASSINI_PROVENANCE_SHA256:
        raise ContractError("normalized Cassini build provenance changed")

    root = pathlib.Path(__file__).resolve().parents[3]
    historical = (
        root
        / "experiments/2026-07-27-da9214-direct-address-cassini/scripts"
    )
    if digest_path(
        historical / "validate-package-cassini.py"
    ) != co.CASSINI_PACKAGE_VALIDATOR_SHA256:
        raise ContractError("source-pinned Cassini package validator changed")
    if digest_path(
        historical / "candidate_cassini.py"
    ) != co.CASSINI_PINS_SHA256:
        raise ContractError("source-pinned Cassini package pins changed")
    return compiled


def load_orion_dtb_validator() -> ModuleType:
    path = pathlib.Path(__file__).with_name("validate-orion-dtb.py")
    regular(path, "source-pinned Orion boot-DT validator")
    if digest_path(path) != co.ORION_DTB_VALIDATOR_SHA256:
        raise ContractError("source-pinned Orion boot-DT validator changed")
    spec = importlib.util.spec_from_file_location("orion_boot_dtb", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Orion boot-DT validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cells(raw: bytes, label: str) -> tuple[int, ...]:
    if len(raw) % 4:
        raise ContractError(f"{label} is not a whole number of cells")
    return tuple(
        struct.unpack_from(">I", raw, offset)[0]
        for offset in range(0, len(raw), 4)
    )


def phandle_map(tree: dict[str, dict[str, bytes]]) -> dict[int, str]:
    resolved: dict[int, str] = {}
    for path, properties in tree.items():
        values: list[int] = []
        for name in ("phandle", "linux,phandle"):
            if name in properties:
                parsed = cells(properties[name], f"{path}:{name}")
                if len(parsed) != 1:
                    raise ContractError(f"{path}:{name} is not one cell")
                values.append(parsed[0])
        if not values:
            continue
        if len(set(values)) != 1:
            raise ContractError(f"{path} has conflicting phandle aliases")
        handle = values[0]
        if not handle or handle in resolved:
            raise ContractError(f"invalid or duplicate phandle at {path}")
        resolved[handle] = path
    return resolved


def scalar_cell(
    tree: dict[str, dict[str, bytes]], path: str, name: str
) -> int:
    try:
        parsed = cells(tree[path][name], f"{path}:{name}")
    except KeyError as exc:
        raise ContractError(f"missing {path}:{name}") from exc
    if len(parsed) != 1:
        raise ContractError(f"{path}:{name} is not one cell")
    return parsed[0]


def resolve_phandle_array(
    tree: dict[str, dict[str, bytes]],
    node: str,
    name: str,
    provider_cells: str,
) -> tuple[tuple[str, tuple[int, ...]], ...]:
    handles = phandle_map(tree)
    values = cells(tree[node][name], f"{node}:{name}")
    index = 0
    result: list[tuple[str, tuple[int, ...]]] = []
    while index < len(values):
        provider = handles.get(values[index])
        if provider is None:
            raise ContractError(f"{node}:{name} has unresolved phandle")
        index += 1
        count = scalar_cell(tree, provider, provider_cells)
        if index + count > len(values):
            raise ContractError(f"{node}:{name} has truncated specifier")
        result.append((provider, values[index : index + count]))
        index += count
    if not result:
        raise ContractError(f"{node}:{name} is empty")
    return tuple(result)


def parent_paths(path: str) -> tuple[str, ...]:
    current = pathlib.PurePosixPath(path)
    result: list[str] = []
    while True:
        result.append(current.as_posix())
        if current.as_posix() == "/":
            break
        current = current.parent
    return tuple(result)


def resolved_interrupts(
    tree: dict[str, dict[str, bytes]], node: str
) -> tuple[str, tuple[tuple[int, ...], ...]]:
    handles = phandle_map(tree)
    parent_raw: bytes | None = None
    for path in parent_paths(node):
        parent_raw = tree[path].get("interrupt-parent")
        if parent_raw is not None:
            break
    if parent_raw is None:
        raise ContractError(f"{node} lacks an effective interrupt-parent")
    parent_cells = cells(parent_raw, f"{node}:effective interrupt-parent")
    if len(parent_cells) != 1 or parent_cells[0] not in handles:
        raise ContractError(f"{node} interrupt-parent is unresolved")
    provider = handles[parent_cells[0]]
    width = scalar_cell(tree, provider, "#interrupt-cells")
    values = cells(tree[node]["interrupts"], f"{node}:interrupts")
    if not width or len(values) % width:
        raise ContractError(f"{node}:interrupts has invalid specifier width")
    specs = tuple(
        values[index : index + width]
        for index in range(0, len(values), width)
    )
    return provider, specs


def require_compiled_delta(
    fdt: ModuleType,
    cassini_path: pathlib.Path,
    orion_path: pathlib.Path,
) -> tuple[dict[str, dict[str, bytes]], dict[str, dict[str, bytes]]]:
    regular(orion_path, "compiled Orion Gemini DT")
    cassini, cassini_reservations, cassini_boot_cpu = fdt.parse_fdt(cassini_path)
    orion, orion_reservations, orion_boot_cpu = fdt.parse_fdt(orion_path)
    if (
        orion_reservations != cassini_reservations
        or orion_boot_cpu != cassini_boot_cpu
    ):
        raise ContractError("compiled Orion changed FDT metadata")
    fdt.require_prop(
        cassini,
        I2C6,
        "compatible",
        fdt.string("mediatek,mt6797-i2c")
        + fdt.string("mediatek,mt6577-i2c"),
    )
    expected = copy.deepcopy(cassini)
    expected[I2C6]["compatible"] = fdt.string(co.I2C6_COMPATIBLE[0])
    if orion != expected:
        raise ContractError(
            "compiled Orion DT is not exact Cassini compiled DT plus "
            "only I2C6 compatible"
        )
    return cassini, orion


def require_cross_lineage_contract(
    fdt: ModuleType,
    compiled: dict[str, dict[str, bytes]],
    boot: dict[str, dict[str, bytes]],
) -> None:
    for label, tree in (("compiled", compiled), ("boot", boot)):
        fdt.require_prop(tree, "/", "#address-cells", fdt.cells(2))
        fdt.require_prop(tree, "/", "#size-cells", fdt.cells(2))
        fdt.require_prop(
            tree,
            HANDOFF,
            "compatible",
            fdt.string("mediatek,mt6797-dvfsp-handoff"),
        )
        fdt.require_prop(tree, HANDOFF, "status", fdt.string("okay"))
        fdt.require_prop(
            tree, HANDOFF, "#access-controller-cells", fdt.cells(0)
        )
        if I2C6 not in tree or set(tree[I2C6]) != I2C6_PROPERTIES:
            raise ContractError(f"{label} I2C6 property inventory changed")
        if any(path.startswith(I2C6 + "/") for path in tree):
            raise ContractError(f"{label} I2C6 is not childless")
        fdt.require_prop(
            tree, I2C6, "compatible", fdt.string(co.I2C6_COMPATIBLE[0])
        )
        fdt.require_prop(tree, I2C6, "status", fdt.string("okay"))
        fdt.require_prop(
            tree,
            I2C6,
            "reg",
            fdt.cells(
                0,
                0x1100E000,
                0,
                0x1000,
                0,
                0x11000500,
                0,
                0x80,
            ),
        )
        fdt.require_prop(tree, I2C6, "interrupts", fdt.cells(0, 0x58, 8))
        fdt.require_prop(
            tree, I2C6, "clock-names", fdt.string("main") + fdt.string("dma")
        )
        fdt.require_prop(tree, I2C6, "clock-div", fdt.cells(10))
        fdt.require_prop(tree, I2C6, "#address-cells", fdt.cells(1))
        fdt.require_prop(tree, I2C6, "#size-cells", fdt.cells(0))

    for name in I2C6_PROPERTIES - {"access-controllers", "clocks"}:
        if compiled[I2C6][name] != boot[I2C6][name]:
            raise ContractError(f"cross-lineage I2C6 {name} differs")

    compiled_access = resolve_phandle_array(
        compiled, I2C6, "access-controllers", "#access-controller-cells"
    )
    boot_access = resolve_phandle_array(
        boot, I2C6, "access-controllers", "#access-controller-cells"
    )
    if compiled_access != ((HANDOFF, ()),) or boot_access != compiled_access:
        raise ContractError("cross-lineage I2C6 access controller differs")

    compiled_clocks = resolve_phandle_array(
        compiled, I2C6, "clocks", "#clock-cells"
    )
    boot_clocks = resolve_phandle_array(boot, I2C6, "clocks", "#clock-cells")
    expected_clocks = ((INFRACFG, (0x36,)), (INFRACFG, (0x2E,)))
    if compiled_clocks != expected_clocks or boot_clocks != compiled_clocks:
        raise ContractError("cross-lineage I2C6 clock resources differ")

    compiled_irq = resolved_interrupts(compiled, I2C6)
    boot_irq = resolved_interrupts(boot, I2C6)
    expected_irq = (SYSIRQ, ((0, 0x58, 8),))
    if compiled_irq != expected_irq or boot_irq != compiled_irq:
        raise ContractError("cross-lineage I2C6 interrupt resource differs")


def validate(
    cassini_package: pathlib.Path,
    orion_package: pathlib.Path,
    hubble_dtb: pathlib.Path,
    derived_dtb: pathlib.Path,
) -> dict[str, str]:
    cassini_compiled = verify_exact_cassini_package(cassini_package)
    directory(orion_package, "Orion kernel package")
    orion_compiled = orion_package / COMPILED_DTB
    boot_validator = load_orion_dtb_validator()
    fdt = boot_validator.load_fdt_parser()
    _cassini_tree, orion_tree = require_compiled_delta(
        fdt, cassini_compiled, orion_compiled
    )
    boot_validator.validate(hubble_dtb, derived_dtb)
    boot_tree, _reservations, _boot_cpu = fdt.parse_fdt(derived_dtb)
    require_cross_lineage_contract(fdt, orion_tree, boot_tree)
    return {
        "cassini_normalized_provenance_sha256": co.CASSINI_PROVENANCE_SHA256,
        "cassini_compiled_dtb_sha256": digest_path(cassini_compiled),
        "orion_compiled_dtb_sha256": digest_path(orion_compiled),
        "hubble_dtb_sha256": digest_path(hubble_dtb),
        "orion_boot_dtb_sha256": digest_path(derived_dtb),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cassini-package", required=True, type=pathlib.Path)
    parser.add_argument("--orion-package", required=True, type=pathlib.Path)
    parser.add_argument("--hubble-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--derived-dtb", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        summary = validate(
            args.cassini_package.resolve(strict=True),
            args.orion_package.resolve(strict=True),
            args.hubble_dtb.resolve(strict=True),
            args.derived_dtb.resolve(strict=True),
        )
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        struct.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=orion-dual-exact-dtb-lineage")
    for key, value in summary.items():
        print(f"{key}={value}")
    print("compiled_delta=exact-cassini-compiled-plus-only-i2c6-compatible")
    print("boot_delta=exact-hubble-plus-only-i2c6-compatible")
    print("i2c6_node=/i2c@1100e000")
    print("i2c6_properties=exact-cross-lineage")
    print("i2c6_access_controller=/dvfsp-handoff@11015000")
    print("i2c6_clocks=/syscon@10001000:0x36,0x2e")
    print("i2c6_interrupt_parent=/interrupt-controller@10200620")
    print("i2c6_interrupt_specifier=0,0x58,8")
    print("i2c6=enabled-childless")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
