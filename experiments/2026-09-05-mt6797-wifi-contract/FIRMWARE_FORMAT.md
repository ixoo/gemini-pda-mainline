# Bounded offline Wi-Fi firmware metadata inspection

The implemented inspector is
[`scripts/wifi_firmware.py`](scripts/wifi_firmware.py). It describes its
contract by default and opens no file. An explicit `--inspect FILE` opens one
ordinary local file and reports only its digest, size, structural counts,
lengths and fixed classification fields. It cannot load firmware, open a
device, issue an ioctl, control a radio, decrypt code, extract a section, or
write an output file.

Status on 2026-09-05 UTC: MT6797 gen3 `MTKE` inspection is implemented, with
the initial gen2 `MTKW` parser retained as an explicit comparison. All 55
synthetic tests pass; the subsequent private-file inspection is recorded below. A matching container is evidence about file structure, not proof
of the live kernel's selected loader, radio safety, redistribution rights or
mainline support.

The Wi-Fi workstream first ran the frozen MTKW-only inspector against the retained
private file in the RE VM: its recorded size and SHA-256 matched, but its
format was unsupported, correctly producing `inconclusive`. A separate
exact-digest-gated inspection reported the public format class `MTKE` without
emitting bytes. That result caused the source-selection audit below and the
MTKE implementation; it was not interpreted as corrupt or raw firmware.
The Wi-Fi workstream retains the private source snapshot and sanitized execution
receipts. The initial result does not count as an MTKE CRC/section validation.

The Wi-Fi workstream subsequently ran the reviewed MTKE revision in the RE VM.
The [sanitized receipt](results/firmware-mtke.json) confirms the exact retained
identity, matching CRC, four bounded sections, two encrypted HIF sections and
two disjoint EMI sections within the 512 KiB window. Reserved fields are zero.
The remaining 24 unreferenced bytes are counted only, with no inferred footer
meaning. This is a real private-file metadata result and no runtime loading
claim. The selected-gen2 inference is withdrawn; gen2 remains comparison
evidence only.

The owner has separately authorized use of the retained private firmware for
this work. Unresolved redistribution is a publication/distribution gate; it
does not block the authorized local inspection or independent source and host
test work. Technical loading prerequisites remain the proven format,
transport, memory and shared power/lifecycle contracts plus experiment
admission. This metadata tool does not satisfy those prerequisites itself.

## Selected board source: gen3, not the earlier gen2 assumption

All Planet source references below are pinned to
`c5b0be85017ad0c599725e8273842efdbecdd88a`. The board
`aeon6797_6m_n_defconfig` selects `CONFIG_MTK_COMBO_CHIP_CONSYS_6797=y`
and `CONFIG_MTK_COMBO_WIFI=y`. Connectivity Kconfig maps that choice to
`CONFIG_MTK_COMBO_CHIP="CONSYS_6797"`. The enclosing WLAN Makefile then
selects **gen3** and defines `MT6797`; other CONSYS selections use gen2.
This direct selection chain corrects the earlier gen2 assumption. A physical
device's historical kernel binary is not proven identical to this source
merely because its labels match.
[Board configuration](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/arch/arm64/configs/aeon6797_6m_n_defconfig#L247),
[Kconfig mapping](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/Kconfig#L144),
[WLAN selector](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/Makefile#L27).

The gen3 Makefile selects `os/linux/hif/ahb_sdioLike/` for MT6797. Its
objects include AHB, PDMA and SDIO-like bus helpers. The selected AHB glue
registers platform driver `mt-wifi`, consumes `wifi-dma` and directly maps
HIF/MCU/remap resources. It spells its compatible `mediatek,WIFI`, whereas
the older normalized live record spells `mediatek,wifi`; preserve these as
separate source and observation records. SDIO-like helper names do not prove
an enumerated physical SDIO function.
[Gen3 HIF selection](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/Makefile#L92),
[selected AHB driver](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c#L196).

## Source-established MT6797 MTKE format

The MT6797 branch of gen3 `wlan_lib.h` declares the `MTKE` signature and
the following little-endian layout. The inspector reads fields solely to
validate bounds and classify structure; it emits no addresses, selector
values, chip-info word or version values.

| Part | Source layout |
| --- | --- |
| Header: 24 bytes | Signature, CRC and count as 32-bit words; 16-bit major/minor numbers; 32-bit chip-info and reserved words |
| Each section: 16 bytes | 32-bit file offset; 8-bit key index and encryption selector; 16-bit reserved field; 32-bit length and destination |

[MT6797 declarations](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/wlan_lib.h#L348),
[MTKE signature](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/wlan_lib.h#L621).

The gen3 loader validates CRC over byte 8 through EOF. Its entire CRC table
was independently checked against reflected IEEE CRC32; initial/final
inversion matches the gen2 comparator. The selected configuration enables
divided download, acknowledgement and encryption support.
[CRC gate](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L421),
[gen3 configuration](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/config.h#L492).

The loader routes section indices 0 and 1 through HIF download configuration
and PDA packets. Nonzero encryption selectors enable hardware encryption
mode; the key-index field is masked to two bits. Later sections are copied
into a 512 KiB CONSYS EMI mapping after MPU changes. Their destination's low
20 bits select an offset, whose extent must fit that mapping. This is a
direct shared-RAM ownership dependency, not merely a common firmware name.
The source shows hardware download controls, not a requirement to decrypt
firmware on the host.
[Section routing and EMI copy](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L818),
[configuration controls](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L2401).

An invalid signature/CRC branch attempts whole-image download with fallback
settings. It is not evidence that the retained MTKE file uses a raw path.
The inspector refuses CRC errors and never follows a raw fallback; it also
never executes the HIF, DMA, MPU, memory-copy or firmware-start operations.
[Fallback source](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L442).

## Retained MTKW comparison format

The primary reference is Planet commit
`c5b0be85017ad0c599725e8273842efdbecdd88a`, below
`drivers/misc/mediatek/connectivity/wlan/gen2/`. The inspected source files
have explicit GPL version 2 notices. The inspector is independently written;
no vendor source, CRC table or firmware bytes are included.

The source's `wlan_lib.h` declares a 16-byte header with a signature, CRC,
section count and reserved word, followed by 16-byte section entries. Each
entry contains file offset, reserved word, length and destination address.
Its signature definition identifies `MTKW`. All represented values are
32-bit words; the inspector implements the little-endian format corresponding
to the observed ARM64 platform. Destination values are checked internally
but never emitted.
[Header and section declarations](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/include/wlan_lib.h#L296),
[signature](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/include/wlan_lib.h#L402).

The loader checks the signature and CRC over byte 8 through the end of the
file before using the section table. The source CRC has initial and final
inversion; its complete 256-entry table was compared in memory against the
reflected IEEE polynomial `0xedb88320`, with all entries matching. This
justifies Python's standard `zlib.crc32` for that field. The synthetic test
oracle uses an independently written bit-at-a-time calculation and the
published conventional `123456789` check vector, rather than calling the
production CRC routine.
[Loader check](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/common/wlan_lib.c#L378),
[CRC implementation](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/common/wlan_lib.c#L2310).

The Makefile defines `MT6628`; the configuration enables divided download
for that build selector, with download acknowledgements and encryption
enabled. This compile-time name is not a new silicon identification. The
loader constructs section-download commands, later starts Wi-Fi and polls
its ready state. This inspector performs none of those operations. Their
existence also means that a successfully parsed file is insufficient evidence
for a non-transmitting hardware test.
[Build selector](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/Makefile#L4),
[configuration](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/include/config.h#L483),
[download operation](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen2/common/wlan_lib.c#L1949).

Cyrozap's CC0
[SoC schema](https://github.com/cyrozap/mediatek-wifi-re/blob/bcbb3b914ce1292add14bffdee4f1e0a8af33500/mediatek_soc_wifi_firmware.ksy)
independently describes both layouts. The MTKE implementation is justified
by the selected gen3 source above; the CC0 schema is corroboration. The
`parse_mtkw` comparison function still refuses to reinterpret MTKE, while
the CLI dispatches only the two independently established formats. Other
signatures remain inconclusive and are not printed. There is no invented
footer parser: unreferenced bytes are counted, never interpreted or printed.

## Artifact identity and finite inspection policy

The CLI accepts structural interpretation only after both identities match
the [existing recorded inventory](../2026-07-12-connectivity-wmt-recovery/results/runtime-summary.txt):

- size: `411632` bytes;
- SHA-256: `a69383d74d829430487c39eef6b5e281b25f901595c903a632a10aa8631426dd`.

These values identify the previously observed `WIFI_RAM_CODE_6797`; the
coordinator separately classified it as MTKE. A different file produces only bounded
size/digest metadata and `artifact_identity_mismatch`. No CLI switch can
replace the trusted identity. The parser function accepts synthetic bytes
directly for host tests, but does not confer the CLI's artifact identity.

The local file limit is 1 MiB; the read loop requests at most that limit plus
one sentinel byte. Paths are limited to 4096 encoded bytes and 64 components,
with no symlink in any component and no empty, `.` or `..` component. A
regular-file metadata check precedes the read-only, no-follow open, and the
opened descriptor is checked again. Device, inode, mode, size and change
timestamps must agree before and after reading. File replacement, mutation,
oversize, missing safe-open flags or open/read errors produce fixed refusal
codes. The file must be a stable local private analysis input; this is a byte
budget, not a guarantee against a stalled filesystem or privileged concurrent
modification. It creates no temporary or persistent files.

The parser adds explicit inspection policy beyond the old loader's checks:

| Check | Classification |
| --- | --- |
| Truncated format-specific header or section table | Refused |
| Unknown format | Inconclusive; no raw signature output |
| CRC mismatch | Refused |
| Zero sections or more than 256 sections | Refused by finite inspection policy |
| Empty section, section crossing the table or file boundary | Refused by inspection policy |
| A 32-bit destination range overflow | Refused |
| Overlapping source ranges or destination ranges within a target address space | Refused by inspection policy; HIF and EMI are checked separately for MTKE |
| MTKE EMI extent beyond its 512 KiB mapping after the source's low-20-bit mask | Refused |
| Nonzero reserved word | Inconclusive; its meaning is unproven |
| Unreferenced bytes after accounting for table and sections | Counted only; no footer interpretation |
| Bounded, disjoint, CRC-consistent MTKW/MTKE structure | Structurally valid; no loading or runtime authorization |

The count limit is independent policy, not a hardware maximum. A one-section
MTKE structure can be counted but is not claimed to be complete executable
firmware. For MTKE, the inspector emits HIF/EMI section counts and the number
of HIF sections requesting encryption. A boolean reports whether the source
would mask high key-index bits, never the index or any key bytes. It follows
the source's nonzero-is-true encryption semantics rather than inventing a
0/1-only format requirement. EMI section encryption fields do not determine
the HIF encryption count because the selected source uses a different path.

These stricter policy refusals do not establish that a file is corrupt or
that the vendor loader would reject it. A new format or legitimate overlapping
layout needs another source audit and explicit parser revision, not relaxed
checks in response to a failing real image.

Output never includes path text, raw bytes, section offsets, destination
addresses, reserved values, strings, MAC addresses, firmware code or
calibration. Error messages contain fixed reason codes. `load_authorized`
remains false, `runtime_loader_applicability` remains unproven and
`redistribution_permission` remains unresolved even after structural success.

## Running and checking

From the repository root, describe the contract without reading firmware:

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/wifi_firmware.py
```

For a separately authorized private inspection, run in the established RE VM
against the existing private regular file:

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/wifi_firmware.py \
  --inspect /absolute/private/analysis/WIFI_RAM_CODE_6797
```

The placeholder is not a discovery instruction. Do not copy a file from the
device, download replacement firmware, or execute a firmware-loading tool to
satisfy this inspection. Use the existing verified private source identified by the owning experiment. Tool execution does not grant redistribution rights.

Exit codes are `0` for contract description or structural success, `2` for
refusal, and `3` for an inconclusive format/semantics result. Neither success
code is a radio or candidate-admission predicate.

Run hardware-free tests with:

```sh
python3 -B experiments/2026-09-05-mt6797-wifi-contract/scripts/test_wifi_firmware.py
```

The 55 synthetic tests pass. They cover an independent CRC oracle, all short
header lengths, format dispatch, truncation, corruption, section
count limits, range overflow, source/destination overlap, reserved semantics,
unreferenced bytes, exact-identity refusal, default no-open behavior, path
redaction, symlink components, simulated device-node metadata, FIFO and
directory refusal, oversized files, concurrent growth and the exact read
budget. MTKE tests additionally cover CRC coverage over all header fields,
first-two versus later section routing, separate HIF/EMI address spaces,
the last in-window byte, crossing the EMI bound, masked EMI aliases,
nonzero encryption semantics, key-index masking, ignored EMI flags and
suppression of addresses and header values. Temporary fixtures use a system temporary
root with immediate registered cleanup. No real firmware, device node read,
radio transaction or kernel build was part of the tests.

## Additional immutable source identities

Previously recorded hashes remain in [UPSTREAM.md](UPSTREAM.md). These files
were additionally inspected at the same Planet commit:

| File below gen2 | SHA-256 |
| --- | --- |
| `include/config.h` | `d414ff270c564151b218df39b47bd1dc89b2e1bda548a35137e95bb0db763ff2` |
| `include/nic_init_cmd_event.h` | `97b46a8fc76065724552b904bee9c1dd4784a5fc1820cfede757de0a68d0afe6` |

The command/event header was inspected to identify the later protocol audit
boundary; no command or ACK decoder is implemented here. The selected gen3
header below supersedes the gen2 header for that follow-up. Public definitions
alone do not establish transport framing observed on Gemini.

| Selected-source file | SHA-256 |
| --- | --- |
| `arch/arm64/configs/aeon6797_6m_n_defconfig` | `83f33ed07c17abe8dceaee64afd26de0cc970c0bae93681b68906636e21e883f` |
| `drivers/misc/mediatek/connectivity/Kconfig` | `2bbf3d81f3f2299feaecd8318ab99e92bebe9bc58704b1302355e4fb0193af9a` |
| `drivers/misc/mediatek/connectivity/wlan/Makefile` | `46185e00d63f9c29ee721781c9fd43b9f3e6f157f26d3610c60c63e00351fc33` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/Makefile` | `5e099f94e6c79593a9210b97096646d2d8e2b0ddd7110a8870519b3dd5c49204` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/include/wlan_lib.h` | `82680ed2fba541a751b63d01aa9d18b8414929e4e4eba74d44fe36d1c531172c` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c` | `56bf99536fcb96de5a5198943aec96c9efccb8af89261b29c62046e6560c422f` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/include/config.h` | `c773b8e5e07978d60565c2eeee976dae3e285ecb9152062fe3bb50b1358a1c32` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_init_cmd_event.h` | `46f8490382ae71485dfb4f106d9e53735ec66ef662b97a12810362309eae7a56` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb.c` | `d9b4e80fe98695284627e495ad640e39728ebe7df235df129f64d48e8a2e726b` |
| `drivers/misc/mediatek/connectivity/wlan/gen3/os/linux/hif/ahb_sdioLike/ahb_pdma.c` | `83c23a5582be2dcaa385359b7cd0f82af0ec9d6a4e102ea6faea57f59d75b480` |

## Next bounded implementation

The exact-file inspection is complete. Use its sanitized receipt to pin
section counts, CRC coverage and EMI extents in host fixtures, then specify
the gen3 DOWNLOAD_CONFIG/PDA/ACK packet contract from
[its exact command header](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/include/nic_init_cmd_event.h),
including sequence/status refusal and finite packet lengths. In parallel,
map the shared CONSYS EMI/remap/MPU lifetime into the common power/firmware
owner. None of that requires host-side firmware decryption or a device boot.
A working firmware loader still requires the active transport and resource
contracts and a separately admitted experiment.
