#!/usr/bin/env python3
"""Validate exact Candidate P plus the allowlisted Candidate V keyboard delta."""

from __future__ import annotations

import argparse
import copy
import hashlib
import pathlib
import struct
import subprocess
import sys
import tempfile


P_DTB_SHA256 = "c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379"
PACKAGE_DTB_SHA256 = "f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5"
PINCTRL = "/pinctrl@10005000"
I2C5_PINS = f"{PINCTRL}/i2c5-pins"
I2C5_BUS_PINS = f"{I2C5_PINS}/pins-bus"
KEYBOARD_PINS = f"{PINCTRL}/keyboard-soc-pins"
RESET_PINS = f"{KEYBOARD_PINS}/pins-reset"
IRQ_PINS = f"{KEYBOARD_PINS}/pins-irq"
I2C5 = "/i2c@1101c000"
AW = f"{I2C5}/gpio-expander@5b"
MATRIX = "/keyboard-matrix"
WATCHDOG = "/watchdog@10007000"
RAMOOPS = "/reserved-memory/ramoops@44410000"
OLD_RAMOOPS = "/reserved-memory/memory@44410000"
FRAMEBUFFER = "/chosen/framebuffer@7dfb0000"
P_AW_PHANDLE = 0x28
V_I2C5_PINS_PHANDLE = 0x2A
V_KEYBOARD_PINS_PHANDLE = 0x2B

FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cells(*values: int) -> bytes:
    return struct.pack(">" + "I" * len(values), *values)


def string(value: str) -> bytes:
    return value.encode("ascii") + b"\0"


def strings(*values: str) -> bytes:
    return b"".join(string(value) for value in values)


def align4(value: int) -> int:
    return (value + 3) & ~3


def cstring(data: bytes, offset: int, limit: int) -> tuple[str, int]:
    end = data.find(b"\0", offset, limit)
    if end < 0:
        raise ValueError("unterminated FDT string")
    try:
        value = data[offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("non-ASCII FDT name") from exc
    return value, end + 1


def parse_fdt(
    path: pathlib.Path,
) -> tuple[dict[str, dict[str, bytes]], tuple[tuple[int, int], ...], int]:
    data = path.read_bytes()
    if len(data) < 40:
        raise ValueError(f"{path}: truncated FDT header")
    fields = struct.unpack_from(">10I", data)
    (
        magic,
        total,
        off_struct,
        off_strings,
        off_reserve,
        version,
        last,
        boot_cpu,
        size_strings,
        size_struct,
    ) = fields
    if magic != FDT_MAGIC or total != len(data) or total < 40:
        raise ValueError(f"{path}: invalid FDT header")
    if not 16 <= last <= version <= 17:
        raise ValueError(f"{path}: unsupported FDT version")
    if off_struct + size_struct > total or off_strings + size_strings > total:
        raise ValueError(f"{path}: FDT block exceeds total size")
    if off_reserve < 40 or off_reserve % 8:
        raise ValueError(f"{path}: invalid reservation-map offset")

    reservations: list[tuple[int, int]] = []
    reserve_pos = off_reserve
    reserve_limit = min(
        offset for offset in (off_struct, off_strings, total) if offset >= off_reserve
    )
    while reserve_pos + 16 <= reserve_limit:
        address, size = struct.unpack_from(">2Q", data, reserve_pos)
        reserve_pos += 16
        if address == 0 and size == 0:
            break
        reservations.append((address, size))
    else:
        raise ValueError(f"{path}: unterminated reservation map")

    tree: dict[str, dict[str, bytes]] = {}
    stack: list[str] = []
    pos = off_struct
    struct_end = off_struct + size_struct
    strings_end = off_strings + size_strings
    saw_end = False
    while pos + 4 <= struct_end:
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == FDT_BEGIN_NODE:
            name, pos = cstring(data, pos, struct_end)
            pos = align4(pos)
            if not stack:
                if name:
                    raise ValueError(f"{path}: root node has a name")
                node_path = "/"
            else:
                node_path = stack[-1].rstrip("/") + "/" + name
            if node_path in tree:
                raise ValueError(f"{path}: duplicate node {node_path}")
            tree[node_path] = {}
            stack.append(node_path)
        elif token == FDT_END_NODE:
            if not stack:
                raise ValueError(f"{path}: unmatched FDT_END_NODE")
            stack.pop()
        elif token == FDT_PROP:
            if not stack or pos + 8 > struct_end:
                raise ValueError(f"{path}: malformed FDT property")
            length, name_offset = struct.unpack_from(">2I", data, pos)
            pos += 8
            if pos + length > struct_end or name_offset >= size_strings:
                raise ValueError(f"{path}: property exceeds FDT block")
            name, _ = cstring(data, off_strings + name_offset, strings_end)
            if name in tree[stack[-1]]:
                raise ValueError(f"{path}: duplicate property {stack[-1]}:{name}")
            tree[stack[-1]][name] = data[pos : pos + length]
            pos = align4(pos + length)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            if stack or pos != struct_end:
                raise ValueError(f"{path}: malformed FDT end")
            saw_end = True
            break
        else:
            raise ValueError(f"{path}: unknown FDT token {token}")
    if not saw_end:
        raise ValueError(f"{path}: missing FDT_END")
    return tree, tuple(reservations), boot_cpu


def require_prop(
    tree: dict[str, dict[str, bytes]], node: str, prop: str, expected: bytes
) -> None:
    if node not in tree or tree[node].get(prop) != expected:
        raise ValueError(f"unexpected or missing property {node}:{prop}")


def phandle_map(tree: dict[str, dict[str, bytes]]) -> dict[int, str]:
    handles: dict[int, str] = {}
    for node, props in tree.items():
        values = []
        for name in ("phandle", "linux,phandle"):
            if name not in props:
                continue
            raw = props[name]
            if len(raw) != 4:
                raise ValueError(f"invalid {node}:{name} width")
            values.append(struct.unpack(">I", raw)[0])
        if len(set(values)) > 1:
            raise ValueError(f"conflicting phandle aliases at {node}")
        if not values:
            continue
        value = values[0]
        if value == 0:
            raise ValueError(f"zero phandle at {node}")
        if value in handles and handles[value] != node:
            raise ValueError(
                f"duplicate phandle 0x{value:x}: {handles[value]} and {node}"
            )
        handles[value] = node
    return handles


def require_p_contract(tree: dict[str, dict[str, bytes]]) -> None:
    if OLD_RAMOOPS in tree:
        raise ValueError("Candidate P contains the obsolete ramoops reservation")
    expected_ramoops = {
        "compatible": string("ramoops"),
        "reg": cells(0, 0x44410000, 0, 0xE0000),
        "record-size": cells(0x1000),
        "console-size": cells(0x10000),
        "ftrace-size": cells(0x1000),
        "pmsg-size": cells(0x20000),
        "mem-type": cells(0),
        "no-map": b"",
    }
    if tree.get(RAMOOPS) != expected_ramoops:
        raise ValueError("Candidate P ramoops contract is not exact")
    expected_framebuffer = {
        "compatible": string("simple-framebuffer"),
        "reg": cells(0, 0x7DFB0000, 0, 0x01F90000),
        "width": cells(1080),
        "height": cells(2160),
        "stride": cells(4352),
        "format": string("a8r8g8b8"),
        "clocks": cells(3, 45, 6, 6),
    }
    if tree.get(FRAMEBUFFER) != expected_framebuffer:
        raise ValueError("Candidate P loader simplefb contract is not exact")
    require_prop(
        tree,
        WATCHDOG,
        "compatible",
        strings("mediatek,mt6797-wdt", "mediatek,mt6589-wdt"),
    )
    require_prop(tree, WATCHDOG, "reg", cells(0, 0x10007000, 0, 0x100))
    if "interrupts" in tree[WATCHDOG]:
        raise ValueError("Candidate P watchdog unexpectedly has an interrupt")
    for node in (I2C5, AW, MATRIX):
        require_prop(tree, node, "status", string("disabled"))
    require_prop(tree, AW, "phandle", cells(P_AW_PHANDLE))
    handles = phandle_map(tree)
    if max(handles) != 0x29 or handles.get(0x29) != f"{PINCTRL}/hall-pins":
        raise ValueError("Candidate P global phandle boundary is not exact")
    if KEYBOARD_PINS in tree or "phandle" in tree[I2C5_PINS]:
        raise ValueError("Candidate P unexpectedly contains corrected keyboard pins")


def require_oracle_contract(tree: dict[str, dict[str, bytes]]) -> None:
    for node in (I2C5, AW, MATRIX):
        require_prop(tree, node, "status", string("disabled"))
    pio_phandle = tree[PINCTRL].get("phandle")
    aw_phandle = tree[AW].get("phandle")
    i2c5_pins_phandle = tree[I2C5_PINS].get("phandle")
    keyboard_pins_phandle = tree[KEYBOARD_PINS].get("phandle")
    for label, value in (
        ("pio", pio_phandle),
        ("AW", aw_phandle),
        ("i2c5 pins", i2c5_pins_phandle),
        ("keyboard pins", keyboard_pins_phandle),
    ):
        if value is None or len(value) != 4:
            raise ValueError(f"oracle {label} phandle is invalid")
    require_prop(tree, I2C5, "pinctrl-names", string("default"))
    require_prop(tree, I2C5, "pinctrl-0", i2c5_pins_phandle)
    require_prop(tree, I2C5_BUS_PINS, "pinmux", cells(0xF001, 0xF101))
    require_prop(tree, AW, "pinctrl-names", string("default"))
    require_prop(tree, AW, "pinctrl-0", keyboard_pins_phandle)
    require_prop(tree, AW, "interrupt-parent", pio_phandle)
    require_prop(tree, AW, "interrupts", cells(10, 8))
    require_prop(tree, AW, "gpio-ranges", aw_phandle + cells(0, 0, 16))
    require_prop(tree, AW, "reset-gpios", pio_phandle + cells(58, 0))
    if tree.get(KEYBOARD_PINS) != {"phandle": keyboard_pins_phandle}:
        raise ValueError("oracle keyboard pin group has unexpected properties")
    if tree.get(RESET_PINS) != {"pinmux": cells(0x3A00), "output-high": b""}:
        raise ValueError("oracle reset pin contract is not exact")
    if tree.get(IRQ_PINS) != {"pinmux": cells(0x5701)}:
        raise ValueError("oracle GPIO87/EINT10 pin contract is not exact")
    for prop in ("gpio-activelow", "drive-inactive-cols"):
        require_prop(tree, MATRIX, prop, b"")


def expected_tree(p_tree: dict[str, dict[str, bytes]]) -> dict[str, dict[str, bytes]]:
    expected = copy.deepcopy(p_tree)
    expected[I2C5_PINS]["phandle"] = cells(V_I2C5_PINS_PHANDLE)
    expected[KEYBOARD_PINS] = {"phandle": cells(V_KEYBOARD_PINS_PHANDLE)}
    expected[RESET_PINS] = {"pinmux": cells(0x3A00), "output-high": b""}
    expected[IRQ_PINS] = {"pinmux": cells(0x5701)}

    expected[I2C5]["status"] = string("okay")
    expected[I2C5]["pinctrl-names"] = string("default")
    expected[I2C5]["pinctrl-0"] = cells(V_I2C5_PINS_PHANDLE)
    expected[I2C5]["clock-frequency"] = cells(400000)

    expected[AW]["status"] = string("okay")
    expected[AW]["pinctrl-names"] = string("default")
    expected[AW]["pinctrl-0"] = cells(V_KEYBOARD_PINS_PHANDLE)
    expected[AW]["gpio-ranges"] = cells(P_AW_PHANDLE, 0, 0, 16)
    for prop in (
        "interrupt-parent",
        "interrupts",
        "interrupt-controller",
        "#interrupt-cells",
    ):
        expected[AW].pop(prop)

    expected[MATRIX]["status"] = string("okay")
    expected[MATRIX]["poll-interval"] = cells(20)
    expected[MATRIX]["col-scan-delay-us"] = cells(2)
    if "debounce-delay-ms" in expected[MATRIX]:
        raise ValueError("Candidate P unexpectedly has matrix debounce-delay-ms")
    return expected


def compare_trees(
    expected: dict[str, dict[str, bytes]], actual: dict[str, dict[str, bytes]]
) -> None:
    if actual == expected:
        return
    details: list[str] = []
    for node in sorted(set(expected) | set(actual)):
        if node not in expected:
            details.append(f"unexpected node {node}")
            continue
        if node not in actual:
            details.append(f"missing node {node}")
            continue
        for prop in sorted(set(expected[node]) | set(actual[node])):
            if prop not in expected[node]:
                details.append(f"unexpected property {node}:{prop}")
            elif prop not in actual[node]:
                details.append(f"missing property {node}:{prop}")
            elif expected[node][prop] != actual[node][prop]:
                details.append(f"changed property {node}:{prop}")
    raise ValueError("DTB delta is not exact P plus keyboard allowlist: " + "; ".join(details[:24]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-p", type=pathlib.Path, required=True)
    parser.add_argument("--package-oracle", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        p_dtb = args.baseline_p.resolve(strict=True)
        oracle = args.package_oracle.resolve(strict=True)
        candidate = args.candidate.resolve(strict=True)
        if digest(p_dtb) != P_DTB_SHA256:
            raise ValueError("baseline is not exact Candidate P DTB")
        if digest(oracle) != PACKAGE_DTB_SHA256:
            raise ValueError("package DTB is not the exact keyboard oracle")

        p_tree, p_reservations, p_boot_cpu = parse_fdt(p_dtb)
        oracle_tree, _, _ = parse_fdt(oracle)
        candidate_tree, candidate_reservations, candidate_boot_cpu = parse_fdt(candidate)
        require_p_contract(p_tree)
        require_oracle_contract(oracle_tree)
        candidate_handles = phandle_map(candidate_tree)
        if (
            max(candidate_handles) != V_KEYBOARD_PINS_PHANDLE
            or candidate_handles.get(V_I2C5_PINS_PHANDLE) != I2C5_PINS
            or candidate_handles.get(V_KEYBOARD_PINS_PHANDLE) != KEYBOARD_PINS
        ):
            raise ValueError("Candidate V fresh phandle allocation is not exact and unique")
        if candidate_reservations != p_reservations:
            raise ValueError("Candidate P reservation map changed")
        if candidate_boot_cpu != p_boot_cpu:
            raise ValueError("Candidate P boot_cpuid_phys changed")
        compare_trees(expected_tree(p_tree), candidate_tree)

        script_dir = pathlib.Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as directory:
            rebuilt = pathlib.Path(directory) / "expected-v.dtb"
            subprocess.run(
                [
                    "bash",
                    str(script_dir / "build-keyboard-watchdog-dtb.sh"),
                    str(p_dtb),
                    str(oracle),
                    str(rebuilt),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            if rebuilt.read_bytes() != candidate.read_bytes():
                raise ValueError("candidate is not the deterministic P-based DTB transform")

        print("validation=candidate-v-dtb-delta")
        print(f"baseline_p_dtb_sha256={P_DTB_SHA256}")
        print(f"package_oracle_dtb_sha256={PACKAGE_DTB_SHA256}")
        print(f"candidate_dtb_sha256={digest(candidate)}")
        print("base=candidate-P-exact")
        print("keyboard_oracle=corrected-package-only")
        print("keyboard_delta=i2c5-pins,aw9523-resources,polling-activation")
        print("watchdog_delta=none-already-no-irq-in-P")
        print("simplefb=exact-P-retained")
        print("ramoops=exact-P-retained")
        print("all_unrelated_p_nodes_and_properties=byte-exact-semantics")
        print("deterministic_transform=byte-identical-reconstruction")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, struct.error, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
