#!/usr/bin/env python3
"""Audit Candidate AP's compiled provider/childless-I2C dependency boundary."""

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
HANDOFF_GET = "mt6797_dvfsp_handoff_get"
HANDOFF_REQUIRE_READY = "mt6797_dvfsp_handoff_require_ready"
HANDOFF_IS_READY_ATOMIC = "mt6797_dvfsp_handoff_is_ready_atomic"
HANDOFF_VALIDATE_CLOCK = "mt6797_dvfsp_handoff_validate_clock"
HANDOFF_VALIDATE_CLOCK_PM = "mt6797_dvfsp_handoff_validate_clock_pm"
I2C_PROBE = "mtk_i2c_probe"
I2C_INIT_HW = "mtk_i2c_init_hw"
I2C_DO_TRANSFER = "mtk_i2c_do_transfer"
I2C_TRANSFER = "mtk_i2c_transfer"
I2C_IRQ = "mtk_i2c_irq"
PROVIDER_PM = (
    "mt6797_dvfsp_handoff_suspend_late",
    "mt6797_dvfsp_handoff_resume_early",
)
I2C_PM = (
    "mtk_i2c_suspend_late",
    "mtk_i2c_resume_early",
    "mtk_i2c_suspend_noirq",
    "mtk_i2c_resume_noirq",
)
REQUIRED_IMAGE_MARKERS = (
    b"state=%s reason=%s initial_gate=%s supplier_bound=yes access_grant=%s ",
    b"suspend_checks=%d suspend_failures=%d resume_checks=%d ",
    b"pm_fault=%s consumer_ungated_checks=%d ",
    b"cleanup_attempts=%u cleanup_samples=%u cleanup_pcm_failures=%u ",
    b"cleanup_main_failures=%u cleanup_dma_invalid=%u cleanup_dma_gated=%u ",
    b"cleanup_selected=%u cleanup_result=%s ",
    b"attempts=%u samples=%u pcm_failures=%u main_failures=%u "
    b"dma_invalid=%u dma_gated=%u selected=%u result=%s\n",
    b"i=%02u main_valid=%d main=%08x dma_valid=%d dma=%08x\n",
    b"sample=%s timer=%08x/%08x con0=%08x con1=%08x ",
    b"dma_gate_valid=%u dma_gate=%08x",
    b"consumer_clock_check=held clocks=i2c-appm,ap-dma validation=passed ",
    b"consumer_clock_check=cleanup clocks=i2c-appm,ap-dma validation=passed ",
    b"GEMINI_MT6797_I2C6_GUARD handoff=ready ",
    b"probe_attempts=%d init_attempts=%d init_successes=%d ",
    b"runtime_pm_link=%d clock_domains=i2c-appm,ap-dma ",
    b"transfer_attempts=%d dma_starts=%d ",
    b"GEMINI_MT6797_I2C6_GUARD handoff=denied "
    b"probe_attempts=%d reason=supplier-not-ready\n",
)

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


def unique_normalized_symbol(symbols: list[Symbol], name: str) -> Symbol:
    matches = [symbol for symbol in symbols if normalize_symbol(symbol.name) == name]
    addresses = {symbol.address for symbol in matches}
    if len(addresses) != 1:
        raise ValueError(f"System.map does not contain one compiled {name}")
    return min(matches, key=lambda symbol: (symbol.name != name, symbol.name))


def audit_inlined_i2c_transfer(
    symbols: list[Symbol],
    transfer: Region,
    calls: list[tuple[int, str]],
) -> None:
    if (
        normalize_symbol(transfer.symbol.name) != I2C_TRANSFER
        or len(transfer.words) != 542
    ):
        raise ValueError("mtk_i2c_transfer compiled region geometry changed")
    if any(normalize_symbol(symbol.name) == I2C_DO_TRANSFER for symbol in symbols):
        raise ValueError(
            "mtk_i2c_do_transfer must remain fully inlined into mtk_i2c_transfer"
        )

    buffers = require_call_count(
        calls, "i2c_get_dma_safe_msg_buf", 4, I2C_TRANSFER
    )
    mappings = require_call_count(calls, "dma_map_single_attrs", 4, I2C_TRANSFER)
    writew = require_call_count(calls, "mtk_i2c_writew", 15, I2C_TRANSFER)
    wait = require_call_count(
        calls, "wait_for_completion_timeout", 1, I2C_TRANSFER
    )[0]
    reinitializations = require_call_count(
        calls, I2C_INIT_HW, 2, I2C_TRANSFER
    )
    paired_dma_order: list[int] = []
    for buffer_at, mapping_at in zip(buffers, mappings, strict=True):
        paired_dma_order.extend((buffer_at, mapping_at))
    require_ordered(
        [*paired_dma_order, wait, *reinitializations],
        f"{I2C_TRANSFER} fully-inlined body",
    )
    if writew[-1] <= wait:
        raise ValueError(
            "mtk_i2c_transfer compiled write/recovery geometry changed"
        )


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


def normalized_region(
    image: bytes, symbols: list[Symbol], image_base: int, name: str
) -> Region:
    symbol = unique_normalized_symbol(symbols, name)
    later = sorted({item.address for item in symbols if item.address > symbol.address})
    if not later:
        raise ValueError(f"System.map has no end boundary after {name}")
    end = later[0]
    size = end - symbol.address
    offset = symbol.address - image_base
    if offset < 0 or size < 8 or size > 32768 or size % 4:
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


def call_indices(calls: list[tuple[int, str]], name: str) -> list[int]:
    return [index for index, called in calls if normalize_symbol(called) == name]


def require_call_count(
    calls: list[tuple[int, str]], name: str, count: int, context: str
) -> list[int]:
    indices = call_indices(calls, name)
    if len(indices) != count:
        raise ValueError(
            f"{context} compiled call count changed for {name}: {len(indices)}"
        )
    return indices


def require_ordered(indices: list[int], context: str) -> None:
    if indices != sorted(indices) or len(indices) != len(set(indices)):
        raise ValueError(f"{context} compiled call order changed")


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


def cfg_reachable(
    item: Region, start: int, target: int, forbidden: set[int]
) -> bool:
    pending = [start]
    visited: set[int] = set()
    while pending:
        index = pending.pop()
        if index == target:
            return True
        if (
            index in visited
            or index in forbidden
            or index < 0
            or index >= len(item.words)
        ):
            continue
        visited.add(index)
        if len(visited) > len(item.words):
            raise ValueError("compiled control-flow search exceeded function region")
        pending.extend(successors(item, index))
    return False


def require_cfg_sequence(item: Region, indices: list[int], context: str) -> None:
    if len(indices) != len(set(indices)):
        raise ValueError(f"{context} compiled CFG sequence is ambiguous")
    sites = set(indices)
    for current, following in zip(indices, indices[1:]):
        if not cfg_reachable(
            item,
            current + 1,
            following,
            sites - {current, following},
        ):
            raise ValueError(f"{context} compiled CFG sequence changed")


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


def audit_kernel(
    image_path: pathlib.Path,
    system_map_path: pathlib.Path,
    *,
    expect_pm: bool = False,
) -> bytes:
    image = read_regular(image_path, "kernel Image")
    system_map_data = read_regular(system_map_path, "System.map")
    if image[IMAGE_MAGIC_OFFSET : IMAGE_MAGIC_OFFSET + len(IMAGE_MAGIC)] != IMAGE_MAGIC:
        raise ValueError("kernel Image lacks the arm64 Image magic")

    symbols = parse_symbols(system_map_data)
    image_base = unique_symbol(symbols, "_text").address
    required_symbols = (
        PROBE,
        LATE,
        DRIVER,
        DRIVER_INIT,
        HANDOFF_GET,
        HANDOFF_REQUIRE_READY,
        HANDOFF_IS_READY_ATOMIC,
        HANDOFF_VALIDATE_CLOCK,
        HANDOFF_VALIDATE_CLOCK_PM,
        I2C_PROBE,
        I2C_INIT_HW,
        I2C_TRANSFER,
        I2C_IRQ,
        "consumer_cleanup_show",
        "handoff_status_show",
        "mt6797_dvfsp_handoff_status_show",
    )
    # GCC may preserve the DEVICE_ATTR callback as either the short source
    # name or an object-prefixed local symbol. Require all fixed symbols first,
    # then accept exactly one of the two status callback spellings.
    for required in required_symbols[:-2]:
        unique_normalized_symbol(symbols, required)
    status_callbacks = [
        name
        for name in required_symbols[-2:]
        if any(normalize_symbol(item.name) == name for item in symbols)
    ]
    if len(status_callbacks) != 1:
        raise ValueError("compiled I2C handoff status callback is absent or ambiguous")
    if expect_pm:
        for required in PROVIDER_PM + I2C_PM:
            unique_normalized_symbol(symbols, required)
    if any("dvfsp_observer" in item.name for item in symbols):
        raise ValueError("compiled kernel still contains the old observer")
    if any(item.name == "mt6797_dvfsp_handoff_remove" for item in symbols):
        raise ValueError("compiled owner has a remove path")
    if any(
        item.name.startswith("mt6797_dvfsp_") and item.name.endswith("_store")
        for item in symbols
    ):
        raise ValueError("compiled owner exposes a writable sysfs callback")

    for marker in REQUIRED_IMAGE_MARKERS:
        if marker not in image:
            raise ValueError(f"compiled Image lacks AP format marker: {marker!r}")

    probe_region = normalized_region(image, symbols, image_base, PROBE)
    late_region = normalized_region(image, symbols, image_base, LATE)
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
        actual = sum(normalize_symbol(item) == name for item in probe_names)
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

    get_calls = calls_in(
        normalized_region(image, symbols, image_base, HANDOFF_GET), symbols
    )
    require_call_count(get_calls, "device_link_add", 1, HANDOFF_GET)
    require_call_count(get_calls, "of_count_phandle_with_args", 1, HANDOFF_GET)
    require_call_count(
        get_calls, "__of_parse_phandle_with_args", 1, HANDOFF_GET
    )
    require_call_count(get_calls, "of_find_device_by_node", 1, HANDOFF_GET)
    require_call_count(get_calls, "device_is_bound", 1, HANDOFF_GET)

    i2c_probe_region = normalized_region(image, symbols, image_base, I2C_PROBE)
    i2c_probe_calls = calls_in(i2c_probe_region, symbols)
    get_at = require_call_count(i2c_probe_calls, HANDOFF_GET, 1, I2C_PROBE)[0]
    ready_at = require_call_count(
        i2c_probe_calls, HANDOFF_REQUIRE_READY, 1, I2C_PROBE
    )[0]
    resource_call_prefixes = (
        "clk_",
        "devm_clk",
        "devm_platform_get_and_ioremap_resource",
        "devm_regulator",
        "devm_request_irq",
        "dma_",
        "i2c_add",
        "mtk_i2c_init_hw",
        "platform_get_irq",
    )
    premature = sorted(
        {
            name
            for index, name in i2c_probe_calls
            if index < ready_at
            and normalize_symbol(name).startswith(resource_call_prefixes)
        }
    )
    if premature:
        raise ValueError(
            "I2C probe touches a resource before readiness: " + premature[0]
        )
    ioremap_at = require_call_count(
        i2c_probe_calls,
        "devm_platform_get_and_ioremap_resource",
        2,
        I2C_PROBE,
    )
    init_at = require_call_count(i2c_probe_calls, I2C_INIT_HW, 1, I2C_PROBE)[0]
    validate_at = require_call_count(
        i2c_probe_calls, HANDOFF_VALIDATE_CLOCK, 2, I2C_PROBE
    )
    disable_at = require_call_count(
        i2c_probe_calls, "clk_bulk_disable", 1, I2C_PROBE
    )[0]
    add_adapter_at = require_call_count(
        i2c_probe_calls, "i2c_add_adapter", 1, I2C_PROBE
    )[0]
    add_group_at = require_call_count(
        i2c_probe_calls, "devm_device_add_group", 1, I2C_PROBE
    )[0]
    require_ordered([get_at, ready_at, *ioremap_at, init_at], I2C_PROBE)
    require_cfg_sequence(
        i2c_probe_region,
        [init_at, validate_at[0], disable_at, validate_at[1]],
        f"{I2C_PROBE} held-disable-cleanup",
    )
    require_ordered([add_adapter_at, add_group_at], I2C_PROBE)

    transfer_region = normalized_region(
        image, symbols, image_base, I2C_TRANSFER
    )
    transfer_calls = calls_in(transfer_region, symbols)
    transfer_ready_at = require_call_count(
        transfer_calls, HANDOFF_REQUIRE_READY, 1, I2C_TRANSFER
    )[0]
    regulator_enable = require_call_count(
        transfer_calls, "regulator_enable", 1, I2C_TRANSFER
    )[0]
    require_ordered([transfer_ready_at, regulator_enable], I2C_TRANSFER)
    audit_inlined_i2c_transfer(symbols, transfer_region, transfer_calls)

    pm_result = "disabled-config"
    if expect_pm:
        provider_suspend_calls = calls_in(
            normalized_region(image, symbols, image_base, PROVIDER_PM[0]), symbols
        )
        provider_resume_calls = calls_in(
            normalized_region(image, symbols, image_base, PROVIDER_PM[1]), symbols
        )
        if any(
            name in FORBIDDEN_CALL_NAMES
            for _, name in provider_suspend_calls + provider_resume_calls
        ):
            raise ValueError("compiled provider PM callback calls a forbidden path")

        i2c_suspend_calls = calls_in(
            normalized_region(image, symbols, image_base, I2C_PM[0]), symbols
        )
        i2c_resume_calls = calls_in(
            normalized_region(image, symbols, image_base, I2C_PM[1]), symbols
        )
        require_call_count(
            i2c_suspend_calls, HANDOFF_IS_READY_ATOMIC, 1, I2C_PM[0]
        )
        resume_ready_at = require_call_count(
            i2c_resume_calls, HANDOFF_IS_READY_ATOMIC, 1, I2C_PM[1]
        )[0]
        resume_enable_at = require_call_count(
            i2c_resume_calls, "clk_bulk_prepare_enable", 1, I2C_PM[1]
        )[0]
        resume_init_at = require_call_count(
            i2c_resume_calls, I2C_INIT_HW, 1, I2C_PM[1]
        )[0]
        resume_validate_at = require_call_count(
            i2c_resume_calls, HANDOFF_VALIDATE_CLOCK_PM, 2, I2C_PM[1]
        )
        resume_disable_at = require_call_count(
            i2c_resume_calls, "clk_bulk_disable", 1, I2C_PM[1]
        )[0]
        require_ordered(
            [
                resume_ready_at,
                resume_enable_at,
                resume_init_at,
                resume_validate_at[0],
                resume_disable_at,
                resume_validate_at[1],
            ],
            I2C_PM[1],
        )
        pm_result = "linked-call-order-plus-source-pinned-guards"

    lines = [
        "audit=mt6797-dvfsp-i2c6-consumer\n",
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
        "access_controller_exports=compiled\n",
        "access_controller_phandle_parser=compiled-inlined-wrapper-target\n",
        "pre_mmio_authorization_order=yes\n",
        "i2c_mmio_resources=two-after-ready\n",
        "consumer_clock_validation_order=compiled-cfg-held-disable-cleanup\n",
        "transfer_readiness_precedes_regulator_enable=yes\n",
        "explicit_device_link_add=compiled\n",
        "device_link_flags=autoremove-consumer-plus-pm-runtime-source-pinned\n",
        "explicit_add_clears_inferred=linux-7.1.3-source-pinned-core\n",
        "adapter_registration_precedes_status_publication=yes\n",
        "i2c_instrumentation_boundary_formats=compiled\n",
        "i2c_do_transfer_layout=fully-inlined-into-mtk_i2c_transfer\n",
        "i2c_transfer_region_words=542\n",
        "i2c_inlined_transfer_call_geometry=4-buffers-4-dma-maps-15-writew-1-wait-2-reinit\n",
        "instrumentation_sites=source-pinned-patch-contract\n",
        "cleanup_oracle=32-samples-31-intervals-all-valid-first-dma-gated-source-pinned\n",
        "read_only_dma_gate=infra1-0x094-bit18-source-pinned\n",
        "runtime_pm_link_publication=compiled\n",
        "protected_noirq_bypass=source-pinned-patch-contract\n",
        f"pm_callbacks={pm_result}\n",
        f"compiled_success_cfg_states={visited}\n",
        f"compiled_success_exit_paths={exits}\n",
    ]
    return "".join(lines).encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=pathlib.Path)
    parser.add_argument("--system-map", required=True, type=pathlib.Path)
    parser.add_argument(
        "--expect-pm",
        choices=("disabled", "linked"),
        default="disabled",
    )
    arguments = parser.parse_args()
    try:
        report = audit_kernel(
            arguments.image,
            arguments.system_map,
            expect_pm=arguments.expect_pm == "linked",
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
