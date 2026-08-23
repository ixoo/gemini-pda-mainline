#!/usr/bin/env python3
"""Source-pin and independently extend the Android-v0 candidate validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "41c2ed17f8df3ee56d55da7e64b33888838d9322bdde226c8707e6ef14273695"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    return text.replace(old, new)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    source = (
        repo_root
        / "experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry"
        / "scripts/test-candidate.py"
    )
    if not source.is_file() or source.is_symlink() or digest(source) != SOURCE_SHA256:
        raise SystemExit("source candidate validator is missing, unsafe, or changed")

    text = source.read_text(encoding="utf-8")
    replacements = (
        ("Independently validate the read-free first-dmesg clock-entry candidate.",
         "Independently validate the one-shot protected-clock candidate."),
        ("4_822_712", "4_821_077"),
        ("d8d98fccee89a77fd5a6bc1da3f55cb3d1366b60", "da8cad285d7c92d7dcd1d0cecc104d2f8908308a"),
        ("da921x-clock-entry-first-dmesg", "da921x-protected-clock-first-dmesg-call"),
        ("7.1.3-gemini-clock-entry-first-dmesg", "7.1.3-gemini-clock-one-read"),
        ("984acb29964a7e111da333d457d1bea48c6952cad2fd95c61b9bedf89d1d0c0e", "2a3a5507231d1a559ec0aa2b774cf2f2835347dd4cc55c677149edc93d251e77"),
        ("fd5e77c8194834b5da39f397bea2d4873ad8372e2802c8b6ec640518407b430e", "7e53cd8f5c1c0cd4b988e31cbccbd43a9d3c3d62b98052f87e57486d642ca544"),
        ("0a19f77a527e15997430311358e5ae499271eb03573cf6785b2dffdaf52427a7", "0a671868f7be2994d79f294c606f2defe47f6a71824db6d3e3eb2a5444367437"),
        ("df7f396405c06aca97b8ebe866bb86cd17459636a83affd8f35220d28c0af099", "e6cec0c9ae786c3578dcaf9ee790b7c9c8638e084aa9350ea5e928b06fba0a7c"),
        ("7e3e5c81e128b4a5b565fe47d8186b19b7c663f59b3ed266d95ed02d9a6e30bd", "77bef6f2d7e185bca8f14b448da1872ae79e357bfa5fded849da0c885259bf5e"),
        ("37a41e9dd67235e154f918e4f7db930dbbe8566448c6afd4f1a1de2e49b92f5e", "fdd17c87ecfac4f1ba786540f65f38f90c495cc0479df7e4a21d7c9a16a8f0f4"),
        ("7c1d5f69924a8280e36ff111b411c4fbecd32243e8d0da9e9f6f4b333a21e100", "31f72bcda3af4edb61d3fe18bcbaec50bef740e507b497ea617df5dd52ab772f"),
        ("251e792573bd9961d3f2b90563cff85d851c6502008d97e1ae502fbacda49b83", "d71c1f7e1102c8326f685f5df762de14153ba3cd204a2f9c16a865f068211573"),
        ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4", "3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6"),
        ("e19c8662b9e9f848bde83a9bd64e076b121c0bb6dcc43f9890404888e4b14243", "649175a1d5c80c6d7b44e8b3f009c157dc9f017dbbd746f047fb1075a60dc93a"),
        ("gemini-mt6797-clock-entry-first-dmesg.boot.img", "gemini-mt6797-protected-clock-first-dmesg.boot.img"),
        ("gemini-clock-entry-dtb-mutation.", "gemini-protected-clock-dtb-mutation."),
        ("gemini-clkfdm", "gemini-clk1read"),
        ("mainline-clock-backend-first-dmesg-candidate", "mainline-protected-clock-first-dmesg-candidate"),
    )
    for old, new in replacements:
        text = replace_exact(text, old, new)

    text = replace_exact(
        text,
        'BIGIDVFSP_BACKEND = "/dvfsp-bigidvfs-backend"\n',
        'BIGIDVFSP_BACKEND = "/dvfsp-bigidvfs-backend"\n'
        'OBSERVER = "/protected-readback-observer"\n',
    )

    old = '''    require(fdtget(dtb, CLOCK_BACKEND, "s", "status") == "okay",
            "clock backend is not enabled")
'''
    new = old + '''    require(fdtget(dtb, CLOCK_BACKEND, "s", "reg-names") == "mcumixed",
            "clock backend register owner changed")
    require(fdtget(dtb, CLOCK_BACKEND, "x", "reg") == "0 1001a000 0 1000",
            "clock backend resource changed")
    require(fdtget(dtb, CLOCK_BACKEND, "x", "access-controllers") == handoff,
            "clock backend handoff supplier changed")
'''
    text = replace_exact(text, old, new)

    old = '''    require(all("protected-readback" not in name for name in children(dtb, "/")),
            "protected-readback observer returned")
'''
    new = '''    require(OBSERVER.removeprefix("/") in children(dtb, "/"),
            "protected-readback observer is absent")
    require(fdtget(dtb, OBSERVER, "s", "compatible") ==
            "mediatek,mt6797-protected-readback-observer",
            "protected-readback observer compatible changed")
    require(fdtget(dtb, OBSERVER, "s", "status") == "okay",
            "protected-readback observer is disabled")
    clock_phandle = fdtget(dtb, CLOCK_BACKEND, "x", "phandle")
    bigidvfs_phandle = fdtget(dtb, BIGIDVFSP_BACKEND, "x", "phandle")
    require(fdtget(dtb, OBSERVER, "x", "mediatek,clock-backend") == clock_phandle,
            "observer clock phandle changed")
    require(fdtget(dtb, OBSERVER, "x", "mediatek,bigidvfs-backend") ==
            bigidvfs_phandle, "observer BigiDVFS phandle changed")
'''
    text = replace_exact(text, old, new)

    config_start = text.index("    for line in (\n", text.index("    config ="))
    config_end = text.index("    require(\"maxcpus=8\"", config_start)
    config_block = '''    for line in (
        "CONFIG_MODULES=y\\n",
        "CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y\\n",
        "CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y\\n",
        "CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER=y\\n",
        "CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION=y\\n",
        "# CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER is not set\\n",
        "# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set\\n",
        "# CONFIG_MTK_MT6797_A72_POWER is not set\\n",
        "# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set\\n",
        "# CONFIG_KUNIT is not set\\n",
        "CONFIG_LOCALVERSION=\\\"-gemini-clock-one-read\\\"\\n",
    ):
        require(config.count(line) == 1, f"configuration gate changed: {line!r}")
    for symbol in (
        "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION",
        "PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION",
        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",
        "PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION",
    ):
        require(f"CONFIG_{symbol}=y\\n" not in config,
                f"forbidden retained-write mode enabled: {symbol}")
'''
    text = text[:config_start] + config_block + text[config_end:]

    marker_start = text.index("    for marker in (\n", text.index("    image ="))
    marker_end = text.index("    system_map =", marker_start)
    marker_block = '''    for marker in (
        b"GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A checkpoint=before-clock slot=1 crc32=183854b2",
        b"GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A checkpoint=after-clock slot=2 crc32=d14b85aa",
        b"GEMINI_PROTECTED_READBACK_V1 clock ret=%d abi=%u generation=%llu muxsel=0x%08x ckdiv=0x%08x",
        b"GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=0 cpu_requests=0 owner_registration=0",
    ):
        require(image.count(marker) == 1, f"record or runtime marker changed: {marker!r}")
    for forbidden in (
        b"GEMINI_PROTECTED_READBACK_V1 bigidvfs ret=%d",
        b"GEMINI_CLOCK_BACKEND_FIRST_DMESG_V1 token=GCBF-20260823-A",
        b"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A",
        b"GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1",
        b"run-same-value-write-20260819-a",
        b"GAEL-20260816-A",
    ):
        require(forbidden not in image, f"forbidden Image token returned: {forbidden!r}")
'''
    text = text[:marker_start] + marker_block + text[marker_end:]

    symbols_start = text.index("    for required in (\n", text.index("    system_map ="))
    symbols_end = text.index("\n\n    require(args.dtb", symbols_start)
    symbols_block = '''    for required in (
        " T gemini_protected_readback_ledger_checkpoint\\n",
        " T mt6797_dvfsp_cspm_execute\\n",
        " T mt6797_dvfsp_clock_backend_read\\n",
        " T mt6797_bigidvfs_backend_read\\n",
        " t mt6797_readback_observer_probe\\n",
    ):
        require(system_map.count(required) == 1, f"required symbol changed: {required}")
    require("same_value" not in system_map.lower(), "forbidden same-value symbol returned")
'''
    text = text[:symbols_start] + symbols_block + text[symbols_end:]

    old = '''        ["-ts", CLOCK_BACKEND, "status", "disabled"],
        ["-ts", BIGIDVFSP_BACKEND, "status", "okay"],
'''
    new = '''        ["-ts", CLOCK_BACKEND, "status", "disabled"],
        ["-d", CLOCK_BACKEND, "access-controllers"],
        ["-ts", CLOCK_BACKEND, "reg-names", "mcumixed", "cspm"],
        ["-tx", CLOCK_BACKEND, "reg", "0", "1001a000", "0", "1000",
         "0", "11015000", "0", "1000"],
        ["-ts", BIGIDVFSP_BACKEND, "status", "okay"],
        ["-ts", OBSERVER, "status", "disabled"],
        ["-ts", OBSERVER, "compatible", "wrong,observer"],
        ["-d", OBSERVER, "mediatek,clock-backend"],
        ["-d", OBSERVER, "mediatek,bigidvfs-backend"],
'''
    text = replace_exact(text, old, new)

    old = '''        "control_dtb_source=runtime-proven-serviceability-plus-clock-status-okay",
        "retained_record_commits_expected=maximum-2",
        "protected_clock_reads_expected=0",
        "bigidvfs_reads_expected=0",
        "mapped_mmio_transactions_expected=0",
        "clock_enables_expected=0",
        "cpu8_cpu9_admission=closed",
        "boot_candidate=pending-independent-validation",
'''
    new = '''        "control_dtb_source=runtime-proven-serviceability-plus-single-owner-clock-and-clock-only-observer",
        "runtime_hypothesis=exactly-one-handoff-owned-protected-clock-snapshot-returns",
        "retained_record_commits_expected=maximum-2",
        "protected_clock_reads_expected=1",
        "bigidvfs_reads_expected=0",
        "protected_clock_caller_retries_expected=0",
        "cspm_transaction_semantics=one-bounded-handoff-owned-read-with-existing-semaphore-poll",
        "mapped_clock_mmio_read_snapshots_expected=1",
        "clock_enable_disable_pairs_expected=1",
        "secure_calls_expected=0",
        "cpu8_cpu9_admission=closed",
        "boot_candidate=pending-independent-validation",
'''
    text = replace_exact(text, old, new)

    old = '''    print("retained_record_commits_maximum=2")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("mapped_mmio_transactions=0")
    print("clock_enables=0")
'''
    new = '''    print("retained_record_commits_maximum=2")
    print("protected_clock_reads=1")
    print("bigidvfs_reads=0")
    print("protected_clock_caller_retries=0")
    print("mapped_clock_mmio_read_snapshots=1")
    print("clock_enable_disable_pairs=1")
    print("secure_calls=0")
'''
    text = replace_exact(text, old, new)

    with tempfile.TemporaryDirectory(prefix="gemini-protected-clock-validator.") as raw:
        derived = Path(raw) / "test-candidate.py"
        derived.write_text(text, encoding="utf-8")
        completed = subprocess.run([sys.executable, str(derived), *sys.argv[1:]], check=False)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
