#!/usr/bin/env python3
"""Exercise compiled MT6797 PSCI lifecycle-audit mutations."""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import struct
import sys
import tempfile

sys.dont_write_bytecode = True


BASE = 0xFFFF800080000000
BOOT = BASE + 0x100
CAN_DISABLE = BASE + 0x160
INIT = BASE + 0x180
PREPARE = BASE + 0x1C0
GENERIC_INIT = BASE + 0x200
GENERIC_PREPARE = BASE + 0x220
RATE_LIMIT = BASE + 0x300
PRINTK = BASE + 0x340
PSCI_CPU_ON = BASE + 0x380
PSCI_CPU_OFF = BASE + 0x3A0
GENERIC_DISABLE = BASE + 0x3C0
GENERIC_DIE = BASE + 0x3E0
GENERIC_KILL = BASE + 0x400
CUSTOM_OPS = BASE + 0x800
GENERIC_OPS = BASE + 0x850
PSCI_OPS = BASE + 0x8A0
OPS_NAME_ADDRESS = BASE + 0x900
BAD_NAME_ADDRESS = BASE + 0x940
PREPARE_FORMAT_ADDRESS = BASE + 0x980
RATE_STATE = BASE + 0x9E0
BOOT_FORMAT = BASE + 0xA00
RELA_START = BASE + 0x1000
IMAGE_SIZE = 0x2000

RET = 0xD65F03C0
NOP = 0xD503201F


def load_module(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def branch(address: int, target: int, opcode: int) -> int:
    delta = target - address
    if delta % 4:
        raise ValueError("unaligned synthetic branch")
    return opcode | ((delta >> 2) & 0x03FFFFFF)


def conditional_branch(address: int, target: int, opcode: int = 0x54000000) -> int:
    delta = target - address
    if delta % 4:
        raise ValueError("unaligned synthetic conditional branch")
    return opcode | (((delta >> 2) & 0x7FFFF) << 5)


def compare_branch(
    address: int, target: int, register: int, *, nonzero: bool, is_64bit: bool
) -> int:
    opcode = 0x34000000
    if nonzero:
        opcode |= 0x01000000
    if is_64bit:
        opcode |= 0x80000000
    return conditional_branch(address, target, opcode) | register


def adrp(address: int, target: int, register: int) -> int:
    page_delta = ((target & ~0xFFF) - (address & ~0xFFF)) >> 12
    immediate = page_delta & 0x1FFFFF
    return (
        0x90000000
        | ((immediate & 0x3) << 29)
        | (((immediate >> 2) & 0x7FFFF) << 5)
        | register
    )


def add_x(register: int, immediate: int) -> int:
    if not 0 <= immediate <= 0xFFF:
        raise ValueError("synthetic ADD immediate is out of range")
    return 0x91000000 | (immediate << 10) | (register << 5) | register


def ldr_x(register: int, offset: int) -> int:
    if offset % 8 or not 0 <= offset <= 0x7FF8:
        raise ValueError("synthetic LDR offset is invalid")
    return 0xF9400000 | ((offset // 8) << 10) | (register << 5) | register


def replace(words: list[int], index: int, word: int) -> list[int]:
    changed = list(words)
    changed[index] = word
    return changed


def wrapper_words(auditor: object, start: int, slot: int) -> list[int]:
    return [
        auditor.PACIASP,
        adrp(start + 4, GENERIC_OPS + slot, 1),
        auditor.STP_FP_LR_16,
        auditor.MOV_FP_SP,
        ldr_x(1, (GENERIC_OPS + slot) & 0xFFF),
        auditor.BLR_X1,
        auditor.LDP_FP_LR_16,
        auditor.AUTIASP,
        RET,
    ]


def generic_prepare_words(auditor: object, *, slot: int | None = None) -> list[int]:
    slot = auditor.CPU_OPS_BOOT if slot is None else slot
    return [
        auditor.MOV_W1_W0,
        adrp(GENERIC_PREPARE + 4, PSCI_OPS + slot, 0),
        ldr_x(0, (PSCI_OPS + slot) & 0xFFF),
        compare_branch(
            GENERIC_PREPARE + 12,
            GENERIC_PREPARE + 56,
            0,
            nonzero=True,
            is_64bit=True,
        ),
        auditor.PACIASP,
        auditor.STP_FP_LR_16,
        adrp(GENERIC_PREPARE + 24, PREPARE_FORMAT_ADDRESS, 0),
        auditor.MOV_FP_SP,
        add_x(0, PREPARE_FORMAT_ADDRESS & 0xFFF),
        branch(GENERIC_PREPARE + 36, PRINTK, 0x94000000),
        auditor.RETURN_ENODEV,
        auditor.LDP_FP_LR_16,
        auditor.AUTIASP,
        RET,
        auditor.RETURN_ZERO,
        RET,
    ]


def boot_words(auditor: object) -> list[int]:
    return [
        auditor.PACIASP,
        auditor.STP_FP_LR_32,
        adrp(BOOT + 8, RATE_STATE, 0),
        auditor.MOV_FP_SP,
        add_x(0, RATE_STATE & 0xFFF),
        auditor.STR_X19_SP_16,
        0x2A0003F3,  # mov w19, w0
        branch(BOOT + 28, RATE_LIMIT, 0x94000000),
        compare_branch(
            BOOT + 32, BOOT + 52, 0, nonzero=False, is_64bit=False
        ),
        adrp(BOOT + 36, BOOT_FORMAT, 0),
        0x2A1303E1,  # mov w1, w19
        add_x(0, BOOT_FORMAT & 0xFFF),
        branch(BOOT + 48, PRINTK, 0x94000000),
        auditor.LDR_X19_SP_16,
        auditor.RETURN_EAGAIN,
        auditor.LDP_FP_LR_32,
        auditor.AUTIASP,
        RET,
    ]


def pack_addend(value: int) -> int:
    return value if value < 1 << 63 else value - (1 << 64)


def fixture(
    root: pathlib.Path,
    auditor: object,
    *,
    boot: list[int] | None = None,
    can_disable: list[int] | None = None,
    init: list[int] | None = None,
    prepare: list[int] | None = None,
    generic_init: list[int] | None = None,
    generic_prepare: list[int] | None = None,
    custom_targets: dict[int, int] | None = None,
    generic_targets: dict[int, int] | None = None,
    omit_relocations: set[int] | None = None,
    relocation_info: dict[int, int] | None = None,
    extra_relocations: list[tuple[int, int, int]] | None = None,
    raw_writes: list[tuple[int, bytes]] | None = None,
    sort_relocations: bool = True,
) -> tuple[pathlib.Path, pathlib.Path]:
    bodies = {
        BOOT: boot or boot_words(auditor),
        CAN_DISABLE: can_disable or [auditor.RETURN_ZERO, RET],
        INIT: init or wrapper_words(auditor, INIT, auditor.CPU_OPS_INIT),
        PREPARE: prepare
        or wrapper_words(auditor, PREPARE, auditor.CPU_OPS_PREPARE),
        GENERIC_INIT: generic_init or [auditor.RETURN_ZERO, RET],
        GENERIC_PREPARE: generic_prepare or generic_prepare_words(auditor),
    }
    image = bytearray(IMAGE_SIZE)
    image[
        auditor.IMAGE_MAGIC_OFFSET : auditor.IMAGE_MAGIC_OFFSET
        + len(auditor.IMAGE_MAGIC)
    ] = auditor.IMAGE_MAGIC
    for address, words in bodies.items():
        offset = address - BASE
        image[offset : offset + len(words) * 4] = struct.pack(
            f"<{len(words)}I", *words
        )
    image[
        OPS_NAME_ADDRESS - BASE : OPS_NAME_ADDRESS - BASE + len(auditor.OPS_NAME)
    ] = auditor.OPS_NAME
    image[BAD_NAME_ADDRESS - BASE : BAD_NAME_ADDRESS - BASE + 10] = b"wrong-ops\0"
    image[
        PREPARE_FORMAT_ADDRESS
        - BASE : PREPARE_FORMAT_ADDRESS
        - BASE
        + len(auditor.GENERIC_PREPARE_FORMAT)
    ] = auditor.GENERIC_PREPARE_FORMAT
    image[BOOT_FORMAT - BASE : BOOT_FORMAT - BASE + 33] = (
        b"CPU%u boot rejected: synthetic\n\0"
    )

    custom = {
        auditor.CPU_OPS_NAME: OPS_NAME_ADDRESS,
        auditor.CPU_OPS_INIT: INIT,
        auditor.CPU_OPS_PREPARE: PREPARE,
        auditor.CPU_OPS_BOOT: BOOT,
        auditor.CPU_OPS_CAN_DISABLE: CAN_DISABLE,
    }
    custom.update(custom_targets or {})
    generic = {
        auditor.CPU_OPS_INIT: GENERIC_INIT,
        auditor.CPU_OPS_PREPARE: GENERIC_PREPARE,
    }
    generic.update(generic_targets or {})
    omitted = omit_relocations or set()
    info_changes = relocation_info or {}
    relocations: list[tuple[int, int, int]] = []
    for slot, target in custom.items():
        offset = CUSTOM_OPS + slot
        if offset not in omitted:
            relocations.append(
                (offset, info_changes.get(offset, auditor.R_AARCH64_RELATIVE), target)
            )
    for slot, target in generic.items():
        offset = GENERIC_OPS + slot
        if offset not in omitted:
            relocations.append(
                (offset, info_changes.get(offset, auditor.R_AARCH64_RELATIVE), target)
            )
    relocations.extend(extra_relocations or [])
    if sort_relocations:
        relocations.sort(key=lambda record: record[0])
    else:
        relocations.reverse()
    relocation_bytes = b"".join(
        struct.pack("<QQq", offset, info, pack_addend(target))
        for offset, info, target in relocations
    )
    image[
        RELA_START - BASE : RELA_START - BASE + len(relocation_bytes)
    ] = relocation_bytes
    for address, data in raw_writes or []:
        offset = address - BASE
        image[offset : offset + len(data)] = data

    image_path = root / "Image"
    image_path.write_bytes(image)
    symbols = [
        (BASE, "T", "_text"),
        (BOOT, "t", auditor.FUNCTION),
        (BOOT + len(bodies[BOOT]) * 4, "t", "after_mt6797_psci_cpu_boot"),
        (CAN_DISABLE, "t", auditor.CAN_DISABLE_FUNCTION),
        (
            CAN_DISABLE + len(bodies[CAN_DISABLE]) * 4,
            "t",
            "after_mt6797_psci_cpu_can_disable",
        ),
        (INIT, "t", auditor.INIT_FUNCTION),
        (INIT + len(bodies[INIT]) * 4, "t", "after_mt6797_psci_cpu_init"),
        (PREPARE, "t", auditor.PREPARE_FUNCTION),
        (
            PREPARE + len(bodies[PREPARE]) * 4,
            "t",
            "after_mt6797_psci_cpu_prepare",
        ),
        (GENERIC_INIT, "T", auditor.GENERIC_INIT_FUNCTION),
        (
            GENERIC_INIT + len(bodies[GENERIC_INIT]) * 4,
            "T",
            "after_cpu_psci_cpu_init",
        ),
        (GENERIC_PREPARE, "T", auditor.GENERIC_PREPARE_FUNCTION),
        (
            GENERIC_PREPARE + len(bodies[GENERIC_PREPARE]) * 4,
            "T",
            "after_cpu_psci_cpu_prepare",
        ),
        (RATE_LIMIT, "T", "___ratelimit"),
        (PRINTK, "T", "_printk"),
        (PSCI_CPU_ON, "T", "psci_cpu_on"),
        (PSCI_CPU_OFF, "T", "psci_cpu_off"),
        (GENERIC_DISABLE, "T", "cpu_psci_cpu_disable"),
        (GENERIC_DIE, "T", "cpu_psci_cpu_die"),
        (GENERIC_KILL, "T", "cpu_psci_cpu_kill"),
        (CUSTOM_OPS, "d", auditor.OPS_SYMBOL),
        (GENERIC_OPS, "D", auditor.GENERIC_OPS_SYMBOL),
        (PSCI_OPS, "D", auditor.PSCI_OPS_SYMBOL),
        (OPS_NAME_ADDRESS, "r", "mt6797_psci_ops_name"),
        (BAD_NAME_ADDRESS, "r", "bad_ops_name"),
        (PREPARE_FORMAT_ADDRESS, "r", "cpu_psci_prepare_format"),
        (RATE_STATE, "d", "mt6797_boot_ratelimit_state"),
        (BOOT_FORMAT, "r", "mt6797_boot_format"),
        (RELA_START, "R", auditor.RELA_START_SYMBOL),
        (RELA_START + len(relocation_bytes), "R", auditor.RELA_END_SYMBOL),
    ]
    symbols.sort()
    system_map = root / "System.map"
    system_map.write_text(
        "".join(
            f"{address:016x} {kind} {name}\n" for address, kind, name in symbols
        ),
        encoding="ascii",
    )
    return image_path, system_map


def expect_rejected(
    auditor: object,
    root: pathlib.Path,
    diagnostic: str,
    **fixture_options: object,
) -> None:
    root.mkdir()
    image, system_map = fixture(root, auditor, **fixture_options)
    try:
        auditor.audit_kernel(image, system_map, objdump="synthetic")
    except ValueError as exc:
        if diagnostic not in str(exc):
            raise ValueError(
                f"mutation reached the wrong gate: expected {diagnostic!r}, got {exc!r}"
            ) from exc
        return
    raise ValueError("compiled-gate mutation unexpectedly passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    script = pathlib.Path(__file__).resolve().parent / "audit-mt6797-psci-cpu-boot.py"
    auditor = load_module(script, "gemini_ai_compiled_gate_auditor_tests")
    positive_boot = boot_words(auditor)
    positive_generic_prepare = generic_prepare_words(auditor)
    original_objdump = auditor.run_objdump
    auditor.run_objdump = lambda image, start, end, base, executable: (
        f"Disassembly of section .data:\n\n{start:x}:\tnop\n"
    )
    rejected = 0
    try:
        with tempfile.TemporaryDirectory(prefix="candidate-ai-gate-audit-tests-") as raw:
            work = pathlib.Path(raw)
            positive_root = work / "positive"
            positive_root.mkdir()
            image, system_map = fixture(positive_root, auditor)
            report = auditor.audit_kernel(image, system_map, objdump="synthetic")
            markers = (
                b"validation=mt6797-psci-cpu-boot-compiled-audit\n",
                b"lifecycle_validation=mt6797-psci-cpu-lifecycle-compiled-audit\n",
                b"compiled_cpu_ops_table=fail-closed\n",
                b"generic_ops_cpu_init_target=",
                b"generic_ops_cpu_prepare_target=",
                b"ops_postboot_callback=NULL\n",
                b"ops_disable_callback=NULL\n",
                b"ops_die_callback=NULL\n",
                b"ops_kill_callback=NULL\n",
                b"compiled_init_delegation=cpu_psci_cpu_init-only\n",
                b"compiled_prepare_delegation=cpu_psci_cpu_prepare-only\n",
                b"generic_prepare_cpu_on_invocation=absent\n",
                b"compiled_return_eagain=yes\n",
                b"resolved_calls=logging-only\n",
                b"compiled_can_disable_return=false\n",
                b"device_access=none\n",
                b"ops_raw_sha256=",
                b"init_wrapper_sha256=",
                b"prepare_wrapper_sha256=",
                b"generic_init_sha256=",
                b"generic_prepare_sha256=",
                b"function_sha256=",
                b"can_disable_sha256=",
                b"[bounded-objdump-cpu-boot]\n",
                b"[bounded-objdump-cpu-can-disable]\n",
                b"[bounded-objdump-cpu-init-wrapper]\n",
                b"[bounded-objdump-cpu-prepare-wrapper]\n",
                b"[bounded-objdump-generic-psci-init]\n",
                b"[bounded-objdump-generic-psci-prepare]\n",
            )
            for marker in markers:
                if marker not in report:
                    raise ValueError(f"positive audit report lacks {marker!r}")

            unsorted_root = work / "positive-unsorted-rela"
            unsorted_root.mkdir()
            unsorted_image, unsorted_map = fixture(
                unsorted_root, auditor, sort_relocations=False
            )
            auditor.audit_kernel(
                unsorted_image, unsorted_map, objdump="synthetic"
            )

            boot_cases: list[tuple[str, str, list[int]]] = [
                (
                    "boot-psci-call",
                    "non-logging target: psci_cpu_on",
                    replace(
                        positive_boot,
                        12,
                        branch(BOOT + 48, PSCI_CPU_ON, 0x94000000),
                    ),
                ),
                (
                    "boot-displaced-call",
                    "calls inside, not at, a symbol",
                    replace(
                        positive_boot,
                        7,
                        branch(BOOT + 28, RATE_LIMIT + 4, 0x94000000),
                    ),
                ),
                (
                    "boot-blr",
                    "indirect branch/call",
                    replace(positive_boot, 9, auditor.BLR_X1),
                ),
                (
                    "boot-br",
                    "indirect branch/call",
                    replace(positive_boot, 9, 0xD61F0020),
                ),
                (
                    "boot-external-branch",
                    "non-call branch outside",
                    replace(
                        positive_boot,
                        9,
                        branch(BOOT + 36, BASE + 0x700, 0x14000000),
                    ),
                ),
                (
                    "boot-svc",
                    "SVC/HVC/SMC or exception",
                    replace(positive_boot, 9, 0xD4000001),
                ),
                (
                    "boot-hvc",
                    "SVC/HVC/SMC or exception",
                    replace(positive_boot, 9, 0xD4000002),
                ),
                (
                    "boot-smc",
                    "SVC/HVC/SMC or exception",
                    replace(positive_boot, 9, 0xD4000003),
                ),
                (
                    "boot-brk",
                    "SVC/HVC/SMC or exception",
                    replace(positive_boot, 9, 0xD4200000),
                ),
                (
                    "boot-missing-eagain",
                    "compiled -EAGAIN",
                    replace(positive_boot, 14, auditor.RETURN_ZERO),
                ),
                (
                    "boot-ret-x0",
                    "non-X30 return",
                    replace(positive_boot, 9, 0xD65F0000),
                ),
                (
                    "boot-alternate-zero-path",
                    "reachable return other than -EAGAIN",
                    [
                        *positive_boot[:14],
                        conditional_branch(BOOT + 56, BOOT + 64),
                        auditor.RETURN_EAGAIN,
                        *positive_boot[15:],
                    ],
                ),
                (
                    "boot-cycle",
                    "reachable control-flow cycle",
                    replace(
                        positive_boot,
                        9,
                        branch(BOOT + 36, BOOT + 36, 0x14000000),
                    ),
                ),
                (
                    "boot-x30-clobber",
                    "writes X30",
                    replace(positive_boot, 9, 0x9100001E),
                ),
                (
                    "boot-sp-clobber",
                    "writes SP",
                    replace(positive_boot, 9, 0x910043FF),
                ),
                (
                    "boot-nonstack-store",
                    "non-stack memory access",
                    replace(positive_boot, 9, 0xF9000020),
                ),
                (
                    "boot-wfi",
                    "privileged or wait system instruction",
                    replace(positive_boot, 9, 0xD503207F),
                ),
                (
                    "boot-msr",
                    "privileged or wait system instruction",
                    replace(positive_boot, 9, 0xD5034FDF),
                ),
                (
                    "boot-skip-x19-restore",
                    "does not restore X19 on every return",
                    replace(
                        positive_boot,
                        8,
                        compare_branch(
                            BOOT + 32,
                            BOOT + 56,
                            0,
                            nonzero=False,
                            is_64bit=False,
                        ),
                    ),
                ),
                (
                    "boot-skip-stack-pop",
                    "invalid reachable PAC epilogue",
                    [
                        *positive_boot[:15],
                        branch(BOOT + 60, BOOT + 68, 0x14000000),
                        *positive_boot[15:],
                    ],
                ),
                (
                    "boot-extra-logging-call",
                    "exactly one rate-limit and one printk call",
                    [
                        *positive_boot[:13],
                        branch(BOOT + 52, RATE_LIMIT, 0x94000000),
                        *positive_boot[13:],
                    ],
                ),
            ]
            w0_after_eagain = [
                *positive_boot[:15],
                auditor.RETURN_ZERO,
                *positive_boot[15:],
            ]
            boot_cases.append(
                (
                    "boot-w0-after-eagain",
                    "reachable return other than -EAGAIN",
                    w0_after_eagain,
                )
            )
            for name, diagnostic, words in boot_cases:
                expect_rejected(
                    auditor, work / name, diagnostic, boot=words
                )
                rejected += 1

            leaf_cases = [
                (
                    "can-disable-true",
                    auditor.CAN_DISABLE_FUNCTION,
                    {"can_disable": [0x52800020, RET]},
                ),
                (
                    "can-disable-call",
                    auditor.CAN_DISABLE_FUNCTION,
                    {
                        "can_disable": [
                            branch(CAN_DISABLE, RATE_LIMIT, 0x94000000),
                            RET,
                        ]
                    },
                ),
                (
                    "can-disable-branch",
                    auditor.CAN_DISABLE_FUNCTION,
                    {
                        "can_disable": [
                            branch(CAN_DISABLE, CAN_DISABLE + 4, 0x14000000),
                            RET,
                        ]
                    },
                ),
                (
                    "can-disable-no-ret",
                    "constant-return leaf",
                    {"can_disable": [auditor.RETURN_ZERO, NOP]},
                ),
                (
                    "generic-init-true",
                    auditor.GENERIC_INIT_FUNCTION,
                    {"generic_init": [0x52800020, RET]},
                ),
                (
                    "generic-init-call",
                    auditor.GENERIC_INIT_FUNCTION,
                    {
                        "generic_init": [
                            branch(GENERIC_INIT, PSCI_CPU_ON, 0x94000000),
                            RET,
                        ]
                    },
                ),
            ]
            for name, diagnostic, options in leaf_cases:
                expect_rejected(auditor, work / name, diagnostic, **options)
                rejected += 1

            ops_cases: list[tuple[str, str, dict[str, object]]] = [
                (
                    "ops-wrong-init",
                    "relocation target changed",
                    {"custom_targets": {auditor.CPU_OPS_INIT: GENERIC_INIT}},
                ),
                (
                    "ops-wrong-prepare",
                    "relocation target changed",
                    {"custom_targets": {auditor.CPU_OPS_PREPARE: GENERIC_PREPARE}},
                ),
                (
                    "ops-wrong-boot",
                    "relocation target changed",
                    {"custom_targets": {auditor.CPU_OPS_BOOT: PSCI_CPU_ON}},
                ),
                (
                    "ops-wrong-can-disable",
                    "relocation target changed",
                    {"custom_targets": {auditor.CPU_OPS_CAN_DISABLE: GENERIC_DISABLE}},
                ),
                (
                    "ops-postboot-present",
                    "forbidden slot +0x20",
                    {
                        "extra_relocations": [
                            (
                                CUSTOM_OPS + auditor.CPU_OPS_POSTBOOT,
                                auditor.R_AARCH64_RELATIVE,
                                PSCI_CPU_ON,
                            )
                        ]
                    },
                ),
                (
                    "ops-disable-present",
                    "forbidden slot +0x30",
                    {
                        "extra_relocations": [
                            (
                                CUSTOM_OPS + auditor.CPU_OPS_DISABLE,
                                auditor.R_AARCH64_RELATIVE,
                                GENERIC_DISABLE,
                            )
                        ]
                    },
                ),
                (
                    "ops-die-present",
                    "forbidden slot +0x38",
                    {
                        "extra_relocations": [
                            (
                                CUSTOM_OPS + auditor.CPU_OPS_DIE,
                                auditor.R_AARCH64_RELATIVE,
                                GENERIC_DIE,
                            )
                        ]
                    },
                ),
                (
                    "ops-kill-present",
                    "forbidden slot +0x40",
                    {
                        "extra_relocations": [
                            (
                                CUSTOM_OPS + auditor.CPU_OPS_KILL,
                                auditor.R_AARCH64_RELATIVE,
                                GENERIC_KILL,
                            )
                        ]
                    },
                ),
                (
                    "ops-missing-boot",
                    "does not have exactly one relocation",
                    {"omit_relocations": {CUSTOM_OPS + auditor.CPU_OPS_BOOT}},
                ),
                (
                    "ops-duplicate-boot",
                    "does not have exactly one relocation",
                    {
                        "extra_relocations": [
                            (
                                CUSTOM_OPS + auditor.CPU_OPS_BOOT,
                                auditor.R_AARCH64_RELATIVE,
                                BOOT,
                            )
                        ]
                    },
                ),
                (
                    "ops-wrong-rela-type",
                    "not an R_AARCH64_RELATIVE",
                    {"relocation_info": {CUSTOM_OPS + auditor.CPU_OPS_BOOT: 0x101}},
                ),
                (
                    "ops-misaligned-rela",
                    "forbidden slot +0x19",
                    {
                        "extra_relocations": [
                            (
                                CUSTOM_OPS + auditor.CPU_OPS_BOOT + 1,
                                auditor.R_AARCH64_RELATIVE,
                                BOOT,
                            )
                        ]
                    },
                ),
                (
                    "ops-raw-nonzero",
                    "nonzero raw pointer",
                    {"raw_writes": [(CUSTOM_OPS + auditor.CPU_OPS_BOOT, b"\x01")]},
                ),
                (
                    "ops-wrong-name",
                    "string changed",
                    {"custom_targets": {auditor.CPU_OPS_NAME: BAD_NAME_ADDRESS}},
                ),
                (
                    "ops-name-wrong-rela-type",
                    "not an R_AARCH64_RELATIVE",
                    {"relocation_info": {CUSTOM_OPS + auditor.CPU_OPS_NAME: 0x101}},
                ),
                (
                    "generic-ops-wrong-init",
                    "relocation target changed",
                    {"generic_targets": {auditor.CPU_OPS_INIT: PSCI_CPU_ON}},
                ),
                (
                    "generic-ops-wrong-prepare",
                    "relocation target changed",
                    {"generic_targets": {auditor.CPU_OPS_PREPARE: PSCI_CPU_ON}},
                ),
                (
                    "generic-ops-missing-prepare",
                    "does not have exactly one relocation",
                    {"omit_relocations": {GENERIC_OPS + auditor.CPU_OPS_PREPARE}},
                ),
                (
                    "generic-ops-duplicate-init",
                    "does not have exactly one relocation",
                    {
                        "extra_relocations": [
                            (
                                GENERIC_OPS + auditor.CPU_OPS_INIT,
                                auditor.R_AARCH64_RELATIVE,
                                GENERIC_INIT,
                            )
                        ]
                    },
                ),
                (
                    "generic-ops-raw-nonzero",
                    "nonzero raw pointer",
                    {"raw_writes": [(GENERIC_OPS + auditor.CPU_OPS_INIT, b"\x01")]},
                ),
                (
                    "generic-ops-wrong-rela-type",
                    "not an R_AARCH64_RELATIVE",
                    {
                        "relocation_info": {
                            GENERIC_OPS + auditor.CPU_OPS_PREPARE: 0x101
                        }
                    },
                ),
            ]
            for name, diagnostic, options in ops_cases:
                expect_rejected(auditor, work / name, diagnostic, **options)
                rejected += 1

            wrapper_cases: list[tuple[str, str, dict[str, object]]] = [
                (
                    "init-wrapper-boot-slot",
                    "does not delegate",
                    {
                        "init": wrapper_words(
                            auditor, INIT, auditor.CPU_OPS_BOOT
                        )
                    },
                ),
                (
                    "prepare-wrapper-boot-slot",
                    "does not delegate",
                    {
                        "prepare": wrapper_words(
                            auditor, PREPARE, auditor.CPU_OPS_BOOT
                        )
                    },
                ),
                (
                    "init-wrapper-direct-call",
                    "delegation shape changed",
                    {
                        "init": replace(
                            wrapper_words(auditor, INIT, auditor.CPU_OPS_INIT),
                            5,
                            branch(INIT + 20, PSCI_CPU_ON, 0x94000000),
                        )
                    },
                ),
                (
                    "prepare-wrapper-wrong-register",
                    "delegation shape changed",
                    {
                        "prepare": replace(
                            wrapper_words(
                                auditor, PREPARE, auditor.CPU_OPS_PREPARE
                            ),
                            5,
                            0xD63F0000,
                        )
                    },
                ),
                (
                    "prepare-wrapper-exception",
                    "delegation shape changed",
                    {
                        "prepare": replace(
                            wrapper_words(
                                auditor, PREPARE, auditor.CPU_OPS_PREPARE
                            ),
                            5,
                            0xD4000002,
                        )
                    },
                ),
            ]
            for name, diagnostic, options in wrapper_cases:
                expect_rejected(auditor, work / name, diagnostic, **options)
                rejected += 1

            generic_cases: list[tuple[str, str, list[int]]] = [
                (
                    "generic-prepare-wrong-slot",
                    "does not only inspect psci_ops.cpu_on",
                    generic_prepare_words(
                        auditor, slot=auditor.CPU_OPS_POSTBOOT
                    ),
                ),
                (
                    "generic-prepare-indirect-call",
                    "indirect CPU_ON path",
                    replace(positive_generic_prepare, 8, 0xD63F0000),
                ),
                (
                    "generic-prepare-psci-call",
                    "non-printk target",
                    replace(
                        positive_generic_prepare,
                        9,
                        branch(GENERIC_PREPARE + 36, PSCI_CPU_ON, 0x94000000),
                    ),
                ),
                (
                    "generic-prepare-exception",
                    "exception instruction",
                    replace(positive_generic_prepare, 8, 0xD4000003),
                ),
                (
                    "generic-prepare-cycle",
                    "CPU_ON check branch changed",
                    replace(
                        positive_generic_prepare,
                        3,
                        branch(
                            GENERIC_PREPARE + 12,
                            GENERIC_PREPARE + 12,
                            0x14000000,
                        ),
                    ),
                ),
                (
                    "generic-prepare-32bit-pointer-check",
                    "CPU_ON check branch changed",
                    replace(
                        positive_generic_prepare,
                        3,
                        compare_branch(
                            GENERIC_PREPARE + 12,
                            GENERIC_PREPARE + 56,
                            0,
                            nonzero=True,
                            is_64bit=False,
                        ),
                    ),
                ),
                (
                    "generic-prepare-success-nonzero",
                    "compiled shape changed",
                    replace(positive_generic_prepare, 14, 0x52800020),
                ),
            ]
            for name, diagnostic, words in generic_cases:
                expect_rejected(
                    auditor,
                    work / name,
                    diagnostic,
                    generic_prepare=words,
                )
                rejected += 1
    finally:
        auditor.run_objdump = original_objdump

    expected = 61
    if rejected != expected:
        raise ValueError(f"expected {expected} rejected mutations, observed {rejected}")
    print("validation=mt6797-psci-cpu-lifecycle-compiled-audit-mutations")
    print("positive_compiled_fixture=passed")
    print("unsorted_rela_fixture=passed")
    print(f"mutations_rejected={rejected}")
    print("relocated_cpu_ops_table=audited")
    print("init_prepare_delegation=audited")
    print("generic_init_prepare_hardware_paths=audited")
    print("objdump_dependency=synthetic")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
