#!/usr/bin/env python3
"""Preserve and audit the compiled MT6797 PSCI reject lifecycle."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import pathlib
import re
import shutil
import stat
import struct
import subprocess
import sys
from dataclasses import dataclass

sys.dont_write_bytecode = True


FUNCTION = "mt6797_psci_cpu_boot"
INIT_FUNCTION = "mt6797_psci_cpu_init"
PREPARE_FUNCTION = "mt6797_psci_cpu_prepare"
CAN_DISABLE_FUNCTION = "mt6797_psci_cpu_can_disable"
OPS_SYMBOL = "mt6797_psci_ops"
GENERIC_OPS_SYMBOL = "cpu_psci_ops"
GENERIC_INIT_FUNCTION = "cpu_psci_cpu_init"
GENERIC_PREPARE_FUNCTION = "cpu_psci_cpu_prepare"
PSCI_OPS_SYMBOL = "psci_ops"
RELA_START_SYMBOL = "__pi_rela_start"
RELA_END_SYMBOL = "__pi_rela_end"

IMAGE_MAGIC_OFFSET = 0x38
IMAGE_MAGIC = b"ARM\x64"
MASK64 = (1 << 64) - 1
R_AARCH64_RELATIVE = 0x403
ELF64_RELA_SIZE = 24

CPU_OPS_SIZE = 0x48
CPU_OPS_NAME = 0x00
CPU_OPS_INIT = 0x08
CPU_OPS_PREPARE = 0x10
CPU_OPS_BOOT = 0x18
CPU_OPS_POSTBOOT = 0x20
CPU_OPS_CAN_DISABLE = 0x28
CPU_OPS_DISABLE = 0x30
CPU_OPS_DIE = 0x38
CPU_OPS_KILL = 0x40
OPS_NAME = b"mediatek,mt6797-psci\0"

RETURN_ZERO = 0x52800000
RETURN_EAGAIN = 0x12800140  # movn w0, #0xa; alias: mov w0, #-11
RETURN_ENODEV = 0x12800240  # movn w0, #0x12; alias: mov w0, #-19
RETURN_FALSE_WORDS = {RETURN_ZERO, 0x2A1F03E0}  # mov w0, #0 / mov w0, wzr
RET_X30 = 0xD65F03C0
PACIASP = 0xD503233F
AUTIASP = 0xD50323BF
NOP = 0xD503201F
BTI_C = 0xD503245F
INERT_HINT_WORDS = {NOP, BTI_C}

STP_FP_LR_16 = 0xA9BF7BFD
LDP_FP_LR_16 = 0xA8C17BFD
STP_FP_LR_32 = 0xA9BE7BFD
LDP_FP_LR_32 = 0xA8C27BFD
MOV_FP_SP = 0x910003FD
STR_X19_SP_16 = 0xF9000BF3
LDR_X19_SP_16 = 0xF9400BF3
BLR_X1 = 0xD63F0020
MOV_W1_W0 = 0x2A0003E1
GENERIC_PREPARE_FORMAT = b"\x013psci: no cpu_on method, not booting CPU%d\n\0"

SAFE_CALL_NAMES = {
    "___ratelimit",
    "__printk_ratelimit",
    "_printk",
    "printk",
}


@dataclass(frozen=True)
class Symbol:
    address: int
    kind: str
    name: str


@dataclass(frozen=True)
class FunctionRegion:
    symbol: Symbol
    end: int
    body: bytes
    words: tuple[int, ...]


@dataclass(frozen=True)
class Rela:
    offset: int
    info: int
    addend: int


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def parse_symbols(data: bytes) -> list[Symbol]:
    symbols: list[Symbol] = []
    for number, line in enumerate(data.decode("ascii").splitlines(), 1):
        match = re.fullmatch(r"([0-9A-Fa-f]+) ([A-Za-z?]) (\S+)", line)
        if match is None:
            raise ValueError(f"malformed System.map line {number}")
        symbols.append(Symbol(int(match.group(1), 16), match.group(2), match.group(3)))
    if not symbols or any(
        left.address > right.address for left, right in zip(symbols, symbols[1:])
    ):
        raise ValueError("System.map is empty or not address-sorted")
    return symbols


def unique_symbol(symbols: list[Symbol], name: str) -> Symbol:
    matches = [symbol for symbol in symbols if symbol.name == name]
    if len(matches) != 1:
        raise ValueError(f"System.map does not contain exactly one {name}")
    return matches[0]


def sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def branch_target(address: int, word: int, bits: int, shift: int = 2) -> int:
    immediate = (
        (word >> 5) & ((1 << bits) - 1)
        if bits < 26
        else word & ((1 << bits) - 1)
    )
    return address + (sign_extend(immediate, bits) << shift)


def adrp_target(address: int, word: int) -> int:
    if word & 0x9F000000 != 0x90000000:
        raise ValueError(f"instruction at 0x{address:x} is not ADRP")
    immediate = (((word >> 5) & 0x7FFFF) << 2) | ((word >> 29) & 0x3)
    return (address & ~0xFFF) + (sign_extend(immediate, 21) << 12)


def adrp_ldr_target(address: int, adrp: int, ldr: int, register: int) -> int:
    if adrp & 0x1F != register:
        raise ValueError("ADRP destination register changed")
    expected_ldr = 0xF9400000 | (register << 5) | register
    if ldr & 0xFFC003FF != expected_ldr:
        raise ValueError("LDR no longer uses the ADRP destination register")
    return adrp_target(address, adrp) + (((ldr >> 10) & 0xFFF) * 8)


def adrp_add_target(address: int, adrp: int, add: int, register: int) -> int:
    if adrp & 0x1F != register:
        raise ValueError("ADRP destination register changed")
    expected_add = 0x91000000 | (register << 5) | register
    if add & 0xFFC003FF != expected_add:
        raise ValueError("ADD no longer uses the ADRP destination register")
    immediate = (add >> 10) & 0xFFF
    if add & (1 << 22):
        immediate <<= 12
    return adrp_target(address, adrp) + immediate


def resolve_symbol(
    target: int, symbols: list[Symbol], addresses: list[int]
) -> tuple[str, int]:
    index = bisect.bisect_right(addresses, target) - 1
    if index < 0:
        raise ValueError(f"call target 0x{target:x} precedes all System.map symbols")
    symbol = symbols[index]
    return symbol.name, target - symbol.address


def normalize_symbol_name(name: str) -> str:
    base = name.removeprefix("__pi_")
    return re.sub(r"\.(?:isra|constprop|part)\.\d+$", "", base)


def call_name_is_safe(name: str) -> bool:
    return normalize_symbol_name(name) in SAFE_CALL_NAMES


def function_region(
    image: bytes,
    symbols: list[Symbol],
    image_base: int,
    name: str,
    *,
    minimum: int = 8,
    maximum: int = 4096,
) -> FunctionRegion:
    symbol = unique_symbol(symbols, name)
    later = sorted({item.address for item in symbols if item.address > symbol.address})
    if not later:
        raise ValueError(f"System.map has no end boundary after {name}")
    end = later[0]
    size = end - symbol.address
    offset = symbol.address - image_base
    if offset < 0 or size < minimum or size > maximum or size % 4:
        raise ValueError(f"unsafe or implausible {name} range")
    if offset + size > len(image):
        raise ValueError(f"{name} range falls outside the kernel Image")
    body = image[offset : offset + size]
    words = struct.unpack(f"<{len(body) // 4}I", body)
    return FunctionRegion(symbol, end, body, words)


def run_objdump(
    image: pathlib.Path, start: int, end: int, image_base: int, executable: str
) -> str:
    command = [
        executable,
        "-D",
        "-b",
        "binary",
        "-m",
        "aarch64",
        "--no-show-raw-insn",
        f"--adjust-vma=0x{image_base:x}",
        f"--start-address=0x{start:x}",
        f"--stop-address=0x{end:x}",
        str(image),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        diagnostic = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"objdump failed: {diagnostic}")
    marker = "Disassembly of section .data:"
    position = result.stdout.find(marker)
    if position < 0:
        raise ValueError("objdump did not emit a .data disassembly")
    output = result.stdout[position:].strip()
    if not re.search(rf"^\s*{start:x}:\s", output, re.MULTILINE):
        raise ValueError("objdump did not disassemble the function start")
    return output + "\n"


def parse_relocations(
    image: bytes, symbols: list[Symbol], image_base: int
) -> tuple[list[Rela], bytes]:
    start = unique_symbol(symbols, RELA_START_SYMBOL).address
    end = unique_symbol(symbols, RELA_END_SYMBOL).address
    start_offset = start - image_base
    end_offset = end - image_base
    if (
        start_offset < 0
        or end_offset <= start_offset
        or end_offset > len(image)
        or (end_offset - start_offset) % ELF64_RELA_SIZE
    ):
        raise ValueError("unsafe or malformed arm64 RELA range")
    raw = image[start_offset:end_offset]
    relocations = [
        Rela(offset, info, addend & MASK64)
        for offset, info, addend in struct.iter_unpack("<QQq", raw)
    ]
    return relocations, raw


def require_relocation(
    relocations: list[Rela], address: int, target: int, label: str
) -> Rela:
    matches = [relocation for relocation in relocations if relocation.offset == address]
    if len(matches) != 1:
        raise ValueError(f"{label} does not have exactly one relocation")
    relocation = matches[0]
    if relocation.info != R_AARCH64_RELATIVE:
        raise ValueError(f"{label} is not an R_AARCH64_RELATIVE relocation")
    if relocation.addend != target:
        raise ValueError(f"{label} relocation target changed")
    return relocation


def require_raw_zero(
    image: bytes, image_base: int, address: int, size: int, label: str
) -> None:
    offset = address - image_base
    if offset < 0 or offset + size > len(image):
        raise ValueError(f"{label} falls outside the kernel Image")
    if image[offset : offset + size] != bytes(size):
        raise ValueError(f"{label} contains a nonzero raw pointer or payload")


def require_image_string(
    image: bytes, image_base: int, address: int, expected: bytes, label: str
) -> None:
    offset = address - image_base
    if offset < 0 or offset + len(expected) > len(image):
        raise ValueError(f"{label} string falls outside the kernel Image")
    if image[offset : offset + len(expected)] != expected:
        raise ValueError(f"{label} string changed or is not NUL-terminated")


def audit_ops_tables(
    image: bytes,
    symbols: list[Symbol],
    image_base: int,
    relocations: list[Rela],
) -> list[tuple[int, int]]:
    ops = unique_symbol(symbols, OPS_SYMBOL)
    generic_ops = unique_symbol(symbols, GENERIC_OPS_SYMBOL)
    targets = {
        CPU_OPS_INIT: unique_symbol(symbols, INIT_FUNCTION).address,
        CPU_OPS_PREPARE: unique_symbol(symbols, PREPARE_FUNCTION).address,
        CPU_OPS_BOOT: unique_symbol(symbols, FUNCTION).address,
        CPU_OPS_CAN_DISABLE: unique_symbol(symbols, CAN_DISABLE_FUNCTION).address,
    }
    next_symbols = [
        symbol.address
        for symbol in symbols
        if ops.address < symbol.address < ops.address + CPU_OPS_SIZE
    ]
    if next_symbols:
        raise ValueError(f"{OPS_SYMBOL} overlaps another System.map symbol")
    require_raw_zero(image, image_base, ops.address, CPU_OPS_SIZE, OPS_SYMBOL)

    within_ops = [
        relocation
        for relocation in relocations
        if ops.address <= relocation.offset < ops.address + CPU_OPS_SIZE
    ]
    allowed_offsets = {CPU_OPS_NAME, *targets}
    unexpected = [
        relocation
        for relocation in within_ops
        if relocation.offset - ops.address not in allowed_offsets
    ]
    if unexpected:
        slot = unexpected[0].offset - ops.address
        raise ValueError(f"{OPS_SYMBOL} has a relocation in forbidden slot +0x{slot:02x}")

    name_relocations = [
        relocation
        for relocation in within_ops
        if relocation.offset == ops.address + CPU_OPS_NAME
    ]
    if len(name_relocations) != 1:
        raise ValueError(f"{OPS_SYMBOL}.name does not have exactly one relocation")
    name_relocation = name_relocations[0]
    if name_relocation.info != R_AARCH64_RELATIVE:
        raise ValueError(f"{OPS_SYMBOL}.name is not an R_AARCH64_RELATIVE relocation")
    require_image_string(
        image, image_base, name_relocation.addend, OPS_NAME, f"{OPS_SYMBOL}.name"
    )

    resolved: list[tuple[int, int]] = [(CPU_OPS_NAME, name_relocation.addend)]
    for slot, target in targets.items():
        relocation = require_relocation(
            relocations,
            ops.address + slot,
            target,
            f"{OPS_SYMBOL}+0x{slot:02x}",
        )
        resolved.append((slot, relocation.addend))

    for slot, name in (
        (CPU_OPS_POSTBOOT, "cpu_postboot"),
        (CPU_OPS_DISABLE, "cpu_disable"),
        (CPU_OPS_DIE, "cpu_die"),
        (CPU_OPS_KILL, "cpu_kill"),
    ):
        if any(relocation.offset == ops.address + slot for relocation in relocations):
            raise ValueError(f"{OPS_SYMBOL}.{name} callback is not NULL")

    for slot, target, name in (
        (CPU_OPS_INIT, unique_symbol(symbols, GENERIC_INIT_FUNCTION).address, "cpu_init"),
        (
            CPU_OPS_PREPARE,
            unique_symbol(symbols, GENERIC_PREPARE_FUNCTION).address,
            "cpu_prepare",
        ),
    ):
        require_raw_zero(
            image,
            image_base,
            generic_ops.address + slot,
            8,
            f"{GENERIC_OPS_SYMBOL}.{name}",
        )
        require_relocation(
            relocations,
            generic_ops.address + slot,
            target,
            f"{GENERIC_OPS_SYMBOL}.{name}",
        )
    return sorted(resolved)


def is_branch_register(word: int) -> bool:
    return word & 0xFE000000 == 0xD6000000


def is_exception_instruction(word: int) -> bool:
    return word & 0xFF000000 == 0xD4000000


def is_forbidden_system_instruction(word: int) -> bool:
    return word & 0xFF000000 == 0xD5000000 and word not in {
        PACIASP,
        AUTIASP,
        *INERT_HINT_WORDS,
    }


def is_load_store(word: int) -> bool:
    return word & 0x0A000000 == 0x08000000


def is_load_store_pair(word: int) -> bool:
    return word & 0x3A000000 == 0x28000000


def is_gpr_data_processing(word: int) -> bool:
    """Conservatively identify A64 integer data-processing destinations."""

    return (word >> 25) & 0xF in {0x5, 0x8, 0x9, 0xD}


def conditional_target(address: int, word: int) -> int | None:
    if word & 0xFF000000 == 0x54000000:  # B.cond / BC.cond imm19
        return branch_target(address, word, 19)
    if word & 0x7E000000 == 0x34000000:  # CBZ/CBNZ imm19
        return branch_target(address, word, 19)
    if word & 0x7E000000 == 0x36000000:  # TBZ/TBNZ imm14
        return branch_target(address, word, 14)
    return None


def successors(region: FunctionRegion, index: int) -> list[int]:
    word = region.words[index]
    address = region.symbol.address + index * 4
    opcode = word & 0xFC000000
    if word == RET_X30:
        return []
    if opcode == 0x14000000:  # B imm26
        return [(branch_target(address, word, 26) - region.symbol.address) // 4]
    target = conditional_target(address, word)
    if target is not None:
        return [index + 1, (target - region.symbol.address) // 4]
    return [index + 1]


def reachable_acyclic(region: FunctionRegion) -> set[int]:
    colors: dict[int, int] = {}

    def visit(index: int) -> None:
        if index < 0 or index >= len(region.words):
            raise ValueError(f"{region.symbol.name} has reachable fall-through outside its body")
        color = colors.get(index, 0)
        if color == 1:
            raise ValueError(f"{region.symbol.name} contains a reachable control-flow cycle")
        if color == 2:
            return
        colors[index] = 1
        for target in successors(region, index):
            visit(target)
        colors[index] = 2

    visit(0)
    return set(colors)


def writes_return_register(word: int, *, is_call: bool, is_flow: bool) -> bool:
    if is_call:
        return True
    if is_flow or word == RET_X30:
        return False
    if is_load_store_pair(word):
        if not word & (1 << 22):  # STP stores registers rather than writing them.
            return False
        return word & 0x1F == 0 or (word >> 10) & 0x1F == 0
    if is_load_store(word) and not word & (1 << 22):
        return False
    return word & 0x1F == 0


def audit_boot_frame(region: FunctionRegion) -> None:
    words = region.words
    if (
        len(words) < 8
        or words[0] != PACIASP
        or words[1] != STP_FP_LR_32
        or words[3] != MOV_FP_SP
        or tuple(words[-3:]) != (LDP_FP_LR_32, AUTIASP, RET_X30)
    ):
        raise ValueError(f"{FUNCTION} lacks its balanced PAC-protected stack frame")
    if words.count(PACIASP) != 1 or words.count(AUTIASP) != 1 or words.count(RET_X30) != 1:
        raise ValueError(f"{FUNCTION} has duplicate PAC or return control")
    if (
        words.count(STP_FP_LR_32) != 1
        or words.count(LDP_FP_LR_32) != 1
        or words.count(STR_X19_SP_16) != 1
        or words.count(LDR_X19_SP_16) != 1
        or words.index(STR_X19_SP_16) >= words.index(LDR_X19_SP_16)
    ):
        raise ValueError(f"{FUNCTION} lacks its unique X19 save/restore pair")

    allowed_memory = {
        STP_FP_LR_32,
        LDP_FP_LR_32,
        STR_X19_SP_16,
        LDR_X19_SP_16,
    }
    for index, word in enumerate(words):
        if is_load_store(word) and word not in allowed_memory:
            raise ValueError(f"{FUNCTION} contains non-stack memory access")
        if is_load_store_pair(word):
            mode = (word >> 23) & 0x3
            base = (word >> 5) & 0x1F
            if base == 31 and mode in (1, 3) and word not in (STP_FP_LR_32, LDP_FP_LR_32):
                raise ValueError(f"{FUNCTION} contains an unbalanced SP writeback")
            if word & (1 << 22) and (
                word & 0x1F == 30 or (word >> 10) & 0x1F == 30
            ) and word != LDP_FP_LR_32:
                raise ValueError(f"{FUNCTION} writes X30 outside its epilogue")
        if word & 0x1F == 30 and is_gpr_data_processing(word):
            raise ValueError(f"{FUNCTION} writes X30 outside its epilogue")
        if (
            word & 0x1F == 31
            and (word & 0x1F000000) in (0x11000000, 0x0B000000)
        ):
            raise ValueError(f"{FUNCTION} writes SP outside its prologue or epilogue")
        if index not in (0, len(words) - 2) and word in (PACIASP, AUTIASP):
            raise ValueError(f"{FUNCTION} changes pointer-authentication state internally")


def audit_boot(
    image: bytes, symbols: list[Symbol], image_base: int
) -> tuple[FunctionRegion, list[tuple[int, int, str, int]], list[int]]:
    region = function_region(image, symbols, image_base, FUNCTION, maximum=512)
    audit_boot_frame(region)
    symbol_addresses = [symbol.address for symbol in symbols]
    calls: list[tuple[int, int, str, int]] = []
    returns: list[int] = []
    external_branches: list[tuple[int, int]] = []

    for index, word in enumerate(region.words):
        address = region.symbol.address + index * 4
        opcode = word & 0xFC000000
        if is_exception_instruction(word):
            raise ValueError(f"{FUNCTION} contains an SVC/HVC/SMC or exception instruction")
        if is_forbidden_system_instruction(word):
            raise ValueError(f"{FUNCTION} contains a privileged or wait system instruction")
        if is_branch_register(word):
            if word == RET_X30:
                returns.append(address)
            else:
                raise ValueError(f"{FUNCTION} contains an indirect branch/call or non-X30 return")
            continue
        if opcode == 0x94000000:  # BL imm26
            target = branch_target(address, word, 26)
            name, displacement = resolve_symbol(target, symbols, symbol_addresses)
            calls.append((address, target, name, displacement))
        elif opcode == 0x14000000:  # B imm26
            target = branch_target(address, word, 26)
            if not region.symbol.address <= target < region.end:
                external_branches.append((address, target))
        else:
            target = conditional_target(address, word)
            if target is not None and not region.symbol.address <= target < region.end:
                external_branches.append((address, target))

    if external_branches:
        raise ValueError(f"{FUNCTION} contains a non-call branch outside its body")
    if not calls:
        raise ValueError(f"{FUNCTION} has no auditable logging calls")
    unsafe_calls = [name for _, _, name, _ in calls if not call_name_is_safe(name)]
    if unsafe_calls:
        raise ValueError(f"{FUNCTION} calls a non-logging target: {unsafe_calls[0]}")
    displaced_calls = [name for _, _, name, displacement in calls if displacement]
    if displaced_calls:
        raise ValueError(f"{FUNCTION} calls inside, not at, a symbol: {displaced_calls[0]}")
    normalized_names = [normalize_symbol_name(name) for _, _, name, _ in calls]
    rate_calls = [
        name for name in normalized_names if name in {"___ratelimit", "__printk_ratelimit"}
    ]
    printk_calls = [name for name in normalized_names if name in {"_printk", "printk"}]
    if len(calls) != 2 or len(rate_calls) != 1 or len(printk_calls) != 1:
        raise ValueError(
            f"{FUNCTION} does not contain exactly one rate-limit and one printk call"
        )
    if RETURN_EAGAIN not in region.words:
        raise ValueError(f"{FUNCTION} lacks the compiled -EAGAIN return value")
    if not returns:
        raise ValueError(f"{FUNCTION} lacks a return instruction")

    reachable = reachable_acyclic(region)
    unknown, eagain = 0, 1
    no_frame, pac_signed, frame_live, frame_popped, pac_authenticated = range(5)
    pending: list[tuple[int, int, int, bool, bool]] = [
        (0, unknown, no_frame, False, False)
    ]
    visited: set[tuple[int, int, int, bool, bool]] = set()
    reachable_returns: list[int] = []
    while pending:
        index, return_value, frame_state, x19_saved, x19_restored = pending.pop()
        state = (index, return_value, frame_state, x19_saved, x19_restored)
        if state in visited:
            continue
        visited.add(state)
        word = region.words[index]
        address = region.symbol.address + index * 4

        next_frame_state = frame_state
        if word == PACIASP:
            if frame_state != no_frame:
                raise ValueError(f"{FUNCTION} has an invalid reachable PAC state")
            next_frame_state = pac_signed
        elif word == STP_FP_LR_32:
            if frame_state != pac_signed:
                raise ValueError(f"{FUNCTION} has an invalid reachable stack prologue")
            next_frame_state = frame_live
        elif word == LDP_FP_LR_32:
            if frame_state != frame_live:
                raise ValueError(f"{FUNCTION} has an invalid reachable stack epilogue")
            next_frame_state = frame_popped
        elif word == AUTIASP:
            if frame_state != frame_popped:
                raise ValueError(f"{FUNCTION} has an invalid reachable PAC epilogue")
            next_frame_state = pac_authenticated

        next_x19_saved = x19_saved
        next_x19_restored = x19_restored
        if word == STR_X19_SP_16:
            if frame_state != frame_live or x19_saved:
                raise ValueError(f"{FUNCTION} has an invalid reachable X19 save")
            next_x19_saved = True
            next_x19_restored = False
        elif word == LDR_X19_SP_16:
            if not x19_saved:
                raise ValueError(f"{FUNCTION} restores X19 without a reachable save")
            next_x19_restored = True
        elif is_gpr_data_processing(word) and word & 0x1F == 19:
            if not x19_saved:
                raise ValueError(f"{FUNCTION} writes X19 before saving it")
            next_x19_restored = False

        if word == RET_X30:
            if next_frame_state != pac_authenticated:
                raise ValueError(
                    f"{FUNCTION} has a return without a balanced PAC/SP/X30 epilogue"
                )
            if not next_x19_saved or not next_x19_restored:
                raise ValueError(f"{FUNCTION} does not restore X19 on every return")
            if return_value != eagain:
                raise ValueError(f"{FUNCTION} has a reachable return other than -EAGAIN")
            reachable_returns.append(address)
            continue

        opcode = word & 0xFC000000
        flow = opcode == 0x14000000 or conditional_target(address, word) is not None
        call = opcode == 0x94000000
        if word == RETURN_EAGAIN:
            next_value = eagain
        elif writes_return_register(word, is_call=call, is_flow=flow):
            next_value = unknown
        else:
            next_value = return_value
        for target in successors(region, index):
            pending.append(
                (
                    target,
                    next_value,
                    next_frame_state,
                    next_x19_saved,
                    next_x19_restored,
                )
            )
    if not reachable_returns or not set(reachable_returns) <= {
        region.symbol.address + index * 4 for index in reachable
    }:
        raise ValueError(f"{FUNCTION} has no reachable direct return")
    return region, calls, sorted(set(reachable_returns))


def audit_constant_leaf(region: FunctionRegion, values: set[int], label: str) -> None:
    semantic = [word for word in region.words if word not in INERT_HINT_WORDS]
    if len(semantic) != 2 or semantic[0] not in values or semantic[1] != RET_X30:
        raise ValueError(f"{label} is not the required constant-return leaf")
    if any(is_load_store(word) or is_exception_instruction(word) for word in semantic):
        raise ValueError(f"{label} contains a memory or exception instruction")


def audit_wrapper(
    image: bytes,
    symbols: list[Symbol],
    image_base: int,
    name: str,
    slot: int,
) -> FunctionRegion:
    region = function_region(image, symbols, image_base, name, maximum=128)
    words = region.words
    expected_fixed = {
        0: PACIASP,
        2: STP_FP_LR_16,
        3: MOV_FP_SP,
        5: BLR_X1,
        6: LDP_FP_LR_16,
        7: AUTIASP,
        8: RET_X30,
    }
    if len(words) != 9 or any(words[index] != word for index, word in expected_fixed.items()):
        raise ValueError(f"{name} compiled delegation shape changed")
    generic_ops = unique_symbol(symbols, GENERIC_OPS_SYMBOL).address
    target = adrp_ldr_target(region.symbol.address + 4, words[1], words[4], 1)
    if target != generic_ops + slot:
        raise ValueError(f"{name} does not delegate through {GENERIC_OPS_SYMBOL}+0x{slot:02x}")
    return region


def audit_generic_prepare(
    image: bytes, symbols: list[Symbol], image_base: int
) -> FunctionRegion:
    region = function_region(
        image, symbols, image_base, GENERIC_PREPARE_FUNCTION, maximum=128
    )
    words = region.words
    for word in words:
        if is_branch_register(word) and word != RET_X30:
            raise ValueError(
                f"{GENERIC_PREPARE_FUNCTION} contains an indirect CPU_ON path"
            )
        if is_exception_instruction(word):
            raise ValueError(
                f"{GENERIC_PREPARE_FUNCTION} contains an exception instruction"
            )
    fixed = {
        0: MOV_W1_W0,
        4: PACIASP,
        5: STP_FP_LR_16,
        7: MOV_FP_SP,
        10: RETURN_ENODEV,
        11: LDP_FP_LR_16,
        12: AUTIASP,
        13: RET_X30,
        14: RETURN_ZERO,
        15: RET_X30,
    }
    if len(words) != 16 or any(words[index] != word for index, word in fixed.items()):
        raise ValueError(f"{GENERIC_PREPARE_FUNCTION} compiled shape changed")
    psci_ops = unique_symbol(symbols, PSCI_OPS_SYMBOL).address
    load_target = adrp_ldr_target(region.symbol.address + 4, words[1], words[2], 0)
    if load_target != psci_ops + CPU_OPS_BOOT:
        raise ValueError(f"{GENERIC_PREPARE_FUNCTION} does not only inspect psci_ops.cpu_on")
    branch = conditional_target(region.symbol.address + 12, words[3])
    if words[3] & 0xFF00001F != 0xB5000000 or branch != region.symbol.address + 56:
        raise ValueError(f"{GENERIC_PREPARE_FUNCTION} CPU_ON check branch changed")
    format_address = adrp_add_target(
        region.symbol.address + 24, words[6], words[8], 0
    )
    require_image_string(
        image,
        image_base,
        format_address,
        GENERIC_PREPARE_FORMAT,
        GENERIC_PREPARE_FUNCTION,
    )
    if words[9] & 0xFC000000 != 0x94000000:
        raise ValueError(f"{GENERIC_PREPARE_FUNCTION} logging call changed")
    call_target = branch_target(region.symbol.address + 36, words[9], 26)
    addresses = [symbol.address for symbol in symbols]
    call_name, displacement = resolve_symbol(call_target, symbols, addresses)
    if normalize_symbol_name(call_name) not in {"_printk", "printk"} or displacement:
        raise ValueError(f"{GENERIC_PREPARE_FUNCTION} calls a non-printk target")
    return region


def audit_kernel(
    image_path: pathlib.Path,
    system_map_path: pathlib.Path,
    *,
    objdump: str | None = None,
) -> bytes:
    image = read_regular(image_path, "kernel Image")
    system_map_data = read_regular(system_map_path, "System.map")
    if len(image) <= IMAGE_MAGIC_OFFSET + len(IMAGE_MAGIC):
        raise ValueError("kernel Image is too short")
    if image[IMAGE_MAGIC_OFFSET : IMAGE_MAGIC_OFFSET + len(IMAGE_MAGIC)] != IMAGE_MAGIC:
        raise ValueError("kernel Image lacks the arm64 Image magic")

    symbols = parse_symbols(system_map_data)
    image_base = unique_symbol(symbols, "_text").address
    relocations, relocation_bytes = parse_relocations(image, symbols, image_base)
    resolved_ops = audit_ops_tables(image, symbols, image_base, relocations)

    init_region = audit_wrapper(
        image, symbols, image_base, INIT_FUNCTION, CPU_OPS_INIT
    )
    prepare_region = audit_wrapper(
        image, symbols, image_base, PREPARE_FUNCTION, CPU_OPS_PREPARE
    )
    generic_init_region = function_region(
        image, symbols, image_base, GENERIC_INIT_FUNCTION, maximum=64
    )
    audit_constant_leaf(
        generic_init_region, {RETURN_ZERO}, GENERIC_INIT_FUNCTION
    )
    generic_prepare_region = audit_generic_prepare(image, symbols, image_base)
    boot_region, calls, reachable_returns = audit_boot(image, symbols, image_base)
    can_disable_region = function_region(
        image, symbols, image_base, CAN_DISABLE_FUNCTION, maximum=64
    )
    audit_constant_leaf(
        can_disable_region, RETURN_FALSE_WORDS, CAN_DISABLE_FUNCTION
    )

    executable = objdump
    if executable is None:
        executable = shutil.which("aarch64-linux-gnu-objdump") or shutil.which("objdump")
    if executable is None:
        raise ValueError("no AArch64-capable objdump is available")
    regions = (
        ("cpu-boot", boot_region),
        ("cpu-can-disable", can_disable_region),
        ("cpu-init-wrapper", init_region),
        ("cpu-prepare-wrapper", prepare_region),
        ("generic-psci-init", generic_init_region),
        ("generic-psci-prepare", generic_prepare_region),
    )
    disassemblies = {
        name: run_objdump(
            image_path,
            region.symbol.address,
            region.end,
            image_base,
            executable,
        )
        for name, region in regions
    }

    ops = unique_symbol(symbols, OPS_SYMBOL)
    generic_ops = unique_symbol(symbols, GENERIC_OPS_SYMBOL)
    generic_init = unique_symbol(symbols, GENERIC_INIT_FUNCTION)
    generic_prepare = unique_symbol(symbols, GENERIC_PREPARE_FUNCTION)
    ops_raw = image[
        ops.address - image_base : ops.address - image_base + CPU_OPS_SIZE
    ]
    report = [
        "validation=mt6797-psci-cpu-boot-compiled-audit\n",
        "lifecycle_validation=mt6797-psci-cpu-lifecycle-compiled-audit\n",
        f"image_sha256={digest_bytes(image)}\n",
        f"system_map_sha256={digest_bytes(system_map_data)}\n",
        "image_base_symbol=_text\n",
        f"image_base_address=0x{image_base:016x}\n",
        f"rela_start=0x{unique_symbol(symbols, RELA_START_SYMBOL).address:016x}\n",
        f"rela_end=0x{unique_symbol(symbols, RELA_END_SYMBOL).address:016x}\n",
        f"rela_count={len(relocations)}\n",
        f"rela_sha256={digest_bytes(relocation_bytes)}\n",
        f"ops_symbol={OPS_SYMBOL}\n",
        f"ops_address=0x{ops.address:016x}\n",
        f"ops_size={CPU_OPS_SIZE}\n",
        f"ops_raw_sha256={digest_bytes(ops_raw)}\n",
    ]
    for slot, target in resolved_ops:
        report.append(f"ops_slot_0x{slot:02x}=0x{target:016x}\n")
    report.extend(
        [
            "ops_postboot_callback=NULL\n",
            "ops_disable_callback=NULL\n",
            "ops_die_callback=NULL\n",
            "ops_kill_callback=NULL\n",
            "compiled_cpu_ops_table=fail-closed\n",
            f"generic_ops_symbol={GENERIC_OPS_SYMBOL}\n",
            f"generic_ops_address=0x{generic_ops.address:016x}\n",
            f"generic_ops_cpu_init_slot=0x{generic_ops.address + CPU_OPS_INIT:016x}\n",
            f"generic_ops_cpu_init_target=0x{generic_init.address:016x}\n",
            f"generic_ops_cpu_prepare_slot=0x{generic_ops.address + CPU_OPS_PREPARE:016x}\n",
            f"generic_ops_cpu_prepare_target=0x{generic_prepare.address:016x}\n",
        ]
    )
    for label, region in (
        ("init_wrapper", init_region),
        ("prepare_wrapper", prepare_region),
        ("generic_init", generic_init_region),
        ("generic_prepare", generic_prepare_region),
        ("function", boot_region),
        ("can_disable", can_disable_region),
    ):
        report.extend(
            [
                f"{label}_symbol={region.symbol.name}\n",
                f"{label}_start=0x{region.symbol.address:016x}\n",
                f"{label}_end=0x{region.end:016x}\n",
                f"{label}_size={len(region.body)}\n",
                f"{label}_sha256={digest_bytes(region.body)}\n",
            ]
        )
    report.extend(
        [
            "compiled_init_delegation=cpu_psci_cpu_init-only\n",
            "compiled_prepare_delegation=cpu_psci_cpu_prepare-only\n",
            "generic_init_hardware_access=absent\n",
            "generic_prepare_cpu_on_invocation=absent\n",
            f"direct_call_count={len(calls)}\n",
            f"reachable_eagain_return_count={len(reachable_returns)}\n",
        ]
    )
    for index, (address, target, name, displacement) in enumerate(calls):
        suffix = "" if displacement == 0 else f"+0x{displacement:x}"
        report.append(
            f"direct_call_{index}=0x{address:016x}->0x{target:016x}:{name}{suffix}\n"
        )
    report.extend(
        [
            "reachable_control_flow_cycles=0\n",
            "indirect_branch_or_call_count=0\n",
            "external_noncall_branch_count=0\n",
            "svc_hvc_smc_count=0\n",
            "privileged_or_wait_system_instruction_count=0\n",
            "nonstack_memory_access_count=0\n",
            "compiled_return_eagain=yes\n",
            "resolved_calls=logging-only\n",
            "psci_cpu_on_call=absent\n",
            "compiled_can_disable_return=false\n",
            "can_disable_calls_or_branches=absent\n",
            "psci_cpu_off_callback=absent\n",
            "hardware_transition_path=absent\n",
            "device_access=none\n",
        ]
    )
    for name, _ in regions:
        report.extend(
            [
                f"\n[bounded-objdump-{name}]\n",
                disassemblies[name],
            ]
        )
    return "".join(report).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=pathlib.Path, required=True)
    parser.add_argument("--system-map", type=pathlib.Path, required=True)
    parser.add_argument("--objdump")
    args = parser.parse_args()
    try:
        report = audit_kernel(
            args.image.resolve(strict=True),
            args.system_map.resolve(strict=True),
            objdump=args.objdump,
        )
        sys.stdout.buffer.write(report)
        return 0
    except (OSError, UnicodeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
