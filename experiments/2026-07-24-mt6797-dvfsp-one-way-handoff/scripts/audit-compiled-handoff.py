#!/usr/bin/env python3
"""Audit the compiled Candidate AO one-way handoff boundary."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import stat
import struct
import sys
from dataclasses import dataclass


sys.dont_write_bytecode = True

IMAGE_MAGIC_OFFSET = 0x38
IMAGE_MAGIC = b"ARM\x64"
PROBE = "mt6797_dvfsp_handoff_probe"
LATE = "mt6797_dvfsp_late_work"
DRIVER = "mt6797_dvfsp_handoff_driver"
DRIVER_INIT = "mt6797_dvfsp_handoff_driver_init"

FORBIDDEN_CALL_NAMES = {
    "clk_set_rate",
    "clk_set_parent",
    "devm_clk_get_enabled",
    "i2c_transfer",
    "i2c_smbus_xfer",
    "kernel_restart",
    "regmap_write",
    "regmap_update_bits",
    "regulator_disable",
    "regulator_enable",
    "regulator_set_voltage",
    "writel",
}


@dataclass(frozen=True)
class Symbol:
    address: int
    kind: str
    name: str


@dataclass(frozen=True)
class Region:
    symbol: Symbol
    end: int
    words: tuple[int, ...]


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_symbols(data: bytes) -> list[Symbol]:
    symbols: list[Symbol] = []
    previous = -1
    for number, line in enumerate(data.decode("ascii").splitlines(), 1):
        match = re.fullmatch(r"([0-9A-Fa-f]+) ([A-Za-z?]) (\S+)", line)
        if match is None:
            raise ValueError(f"malformed System.map line {number}")
        symbol = Symbol(int(match.group(1), 16), match.group(2), match.group(3))
        if symbol.address < previous:
            raise ValueError("System.map is not address-sorted")
        previous = symbol.address
        symbols.append(symbol)
    if not symbols:
        raise ValueError("System.map is empty")
    return symbols


def unique_symbol(symbols: list[Symbol], name: str) -> Symbol:
    matches = [symbol for symbol in symbols if symbol.name == name]
    if len(matches) != 1:
        raise ValueError(f"System.map does not contain exactly one {name}")
    return matches[0]


def normalize_symbol(name: str) -> str:
    base = name.removeprefix("__pi_")
    return re.sub(r"\.(?:isra|constprop|part)\.\d+$", "", base)


def sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def branch_target(address: int, word: int, bits: int) -> int:
    if bits == 26:
        immediate = word & ((1 << 26) - 1)
    else:
        immediate = (word >> 5) & ((1 << bits) - 1)
    return address + (sign_extend(immediate, bits) << 2)


def region(
    image: bytes, symbols: list[Symbol], image_base: int, name: str
) -> Region:
    symbol = unique_symbol(symbols, name)
    later = sorted({item.address for item in symbols if item.address > symbol.address})
    if not later:
        raise ValueError(f"System.map has no end boundary after {name}")
    end = later[0]
    size = end - symbol.address
    offset = symbol.address - image_base
    if offset < 0 or size < 8 or size > 16384 or size % 4:
        raise ValueError(f"unsafe or implausible {name} region")
    if offset + size > len(image):
        raise ValueError(f"{name} falls outside the kernel Image")
    words = struct.unpack(f"<{size // 4}I", image[offset : offset + size])
    return Region(symbol, end, words)


def exact_symbol_at(symbols: list[Symbol], address: int) -> str:
    names = [normalize_symbol(item.name) for item in symbols if item.address == address]
    if not names:
        raise ValueError(f"call target 0x{address:x} has no exact System.map symbol")
    preferred = [name for name in names if not name.startswith("__")]
    return sorted(preferred or names)[0]


def calls_in(item: Region, symbols: list[Symbol]) -> list[tuple[int, str]]:
    calls: list[tuple[int, str]] = []
    for index, word in enumerate(item.words):
        if word & 0xFC000000 != 0x94000000:
            continue
        address = item.symbol.address + index * 4
        target = branch_target(address, word, 26)
        calls.append((index, exact_symbol_at(symbols, target)))
    return calls


def conditional_target(address: int, word: int) -> int | None:
    if word & 0xFF000010 == 0x54000000:
        return branch_target(address, word, 19)
    if word & 0x7E000000 == 0x34000000:
        return branch_target(address, word, 19)
    if word & 0x7E000000 == 0x36000000:
        return branch_target(address, word, 14)
    return None


def successors(item: Region, index: int) -> list[int]:
    word = item.words[index]
    address = item.symbol.address + index * 4
    if word == 0xD65F03C0:
        return []
    if word & 0xFC000000 == 0x14000000:
        target = branch_target(address, word, 26)
        if target < item.symbol.address or target >= item.end:
            return []
        return [(target - item.symbol.address) // 4]
    target = conditional_target(address, word)
    if target is not None:
        result = [index + 1]
        if item.symbol.address <= target < item.end:
            result.append((target - item.symbol.address) // 4)
        return result
    return [index + 1] if index + 1 < len(item.words) else []


def audit_success_balance(
    probe: Region, probe_calls: list[tuple[int, str]]
) -> tuple[int, int]:
    enable_indices = [index for index, name in probe_calls if name == "clk_enable"]
    if len(enable_indices) != 1:
        raise ValueError("probe does not contain exactly one clk_enable call")
    enable_index = enable_indices[0]
    branch_index = enable_index + 1
    if branch_index >= len(probe.words):
        raise ValueError("clk_enable call has no success/failure branch")
    branch = probe.words[branch_index]
    if branch & 0x7F00001F != 0x35000000:
        raise ValueError("clk_enable result is not checked by CBNZ w0")

    call_by_index = {index: name for index, name in probe_calls}
    pending = [(branch_index + 1, 0, 0)]
    visited: set[tuple[int, int, int]] = set()
    exits: list[tuple[int, int]] = []
    while pending:
        index, disables, unprepares = pending.pop()
        state = (index, disables, unprepares)
        if state in visited:
            continue
        visited.add(state)
        if len(visited) > 20000:
            raise ValueError("compiled success path is cyclic or oversized")
        if index < 0 or index >= len(probe.words):
            exits.append((disables, unprepares))
            continue

        call = call_by_index.get(index)
        if call == "clk_enable":
            raise ValueError("successful handoff path enables the clock twice")
        if call == "clk_disable":
            disables += 1
        elif call == "clk_unprepare":
            unprepares += 1

        next_indices = successors(probe, index)
        if not next_indices:
            exits.append((disables, unprepares))
            continue
        for next_index in next_indices:
            pending.append((next_index, disables, unprepares))

    if not exits or any(item != (1, 1) for item in exits):
        raise ValueError(
            "not every compiled clk_enable success path has one disable/unprepare"
        )
    return len(visited), len(exits)


def audit_kernel(image_path: pathlib.Path, system_map_path: pathlib.Path) -> bytes:
    image = read_regular(image_path, "kernel Image")
    system_map_data = read_regular(system_map_path, "System.map")
    if image[IMAGE_MAGIC_OFFSET : IMAGE_MAGIC_OFFSET + len(IMAGE_MAGIC)] != IMAGE_MAGIC:
        raise ValueError("kernel Image lacks the arm64 Image magic")

    symbols = parse_symbols(system_map_data)
    image_base = unique_symbol(symbols, "_text").address
    for required in (PROBE, LATE, DRIVER, DRIVER_INIT):
        unique_symbol(symbols, required)
    if any("dvfsp_observer" in item.name for item in symbols):
        raise ValueError("compiled kernel still contains the old observer")
    if any(item.name == "mt6797_dvfsp_handoff_remove" for item in symbols):
        raise ValueError("compiled owner has a remove path")
    if any(
        item.name.startswith("mt6797_dvfsp_") and item.name.endswith("_store")
        for item in symbols
    ):
        raise ValueError("compiled owner exposes a writable sysfs callback")

    probe_region = region(image, symbols, image_base, PROBE)
    late_region = region(image, symbols, image_base, LATE)
    probe_calls = calls_in(probe_region, symbols)
    late_calls = calls_in(late_region, symbols)
    probe_names = [name for _, name in probe_calls]
    late_names = [name for _, name in late_calls]

    required_counts = {
        "clk_prepare": 1,
        "clk_enable": 1,
        "clk_disable": 1,
        "clk_unprepare": 2,
        "queue_delayed_work_on": 1,
    }
    for name, expected in required_counts.items():
        actual = probe_names.count(name)
        if actual != expected:
            raise ValueError(
                f"compiled probe call count changed for {name}: {actual}"
            )

    if any(name.startswith("clk_") for name in late_names):
        raise ValueError("late worker mutates a clock")
    all_owner_calls = set(probe_names) | set(late_names)
    forbidden = sorted(
        name
        for name in all_owner_calls
        if name in FORBIDDEN_CALL_NAMES
        or name.startswith("i2c_")
        or name.startswith("regulator_")
        or name.startswith("psci_")
    )
    if forbidden:
        raise ValueError(f"compiled owner calls forbidden control path: {forbidden[0]}")

    visited, exits = audit_success_balance(probe_region, probe_calls)
    lines = [
        "audit=mt6797-dvfsp-one-way-handoff\n",
        f"image_sha256={digest(image)}\n",
        f"system_map_sha256={digest(system_map_data)}\n",
        "probe_present=yes\n",
        "clk_prepare_enable_calls=1\n",
        "clk_disable_unprepare_calls=1\n",
        "every_successful_enable_balanced=yes\n",
        "late_worker_clock_mutation=absent\n",
        "direct_mmio_write=absent\n",
        "regmap_write_or_update=absent\n",
        "i2c_regulator_cpu_control_calls=absent\n",
        "restart_unpause_userspace_api=absent\n",
        "remove_or_unbind_path=absent\n",
        f"compiled_success_cfg_states={visited}\n",
        f"compiled_success_exit_paths={exits}\n",
    ]
    return "".join(lines).encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=pathlib.Path)
    parser.add_argument("--system-map", required=True, type=pathlib.Path)
    arguments = parser.parse_args()
    try:
        report = audit_kernel(arguments.image, arguments.system_map)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
