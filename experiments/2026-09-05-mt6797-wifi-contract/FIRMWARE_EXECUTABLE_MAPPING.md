# Bounded plaintext executable-mapping investigation

[The subsequent predecessor trace](FIRMWARE_NVRAM_PATH.md) finds a reachable
path candidate and an indirect call carrying the reference as an argument.
It supersedes the containing-path uncertainty below; caller/callee identity
and calibration semantics remain unproved.

The retained section 2 is a strong NDS32 code candidate at its container
destination. All of its linearly scanned instructions decoded without failure,
and independently reconstructed split-immediate constants point into section 3,
including NVRAM/EFUSE/EEPROM search spans. This advances the earlier
[literal-pointer investigation](FIRMWARE_CALIBRATION_BOUNDARY.md). It does not
identify a normal-command handler or resolve calibration precedence.

One entry-point hypothesis was tested against the first NVRAM reference
candidate. Its bounded control-flow graph did **not** reach that reference.
The hypothesis therefore cannot supply the containing function for this trace.
This slice stops at that result; it does not treat failure of that entry
heuristic as a contradiction of the stronger section-mapping evidence.

## Public mapping premises

At the existing Planet source pin, `wlanImageDividDownload` copies later
sections to the shared reservation at `destination & 0xfffff`. WMT programs
the reservation's upper address bits into the shared remap register and enables
the remap. These establish AP-side placement, not an independent statement of
the Wi-Fi CPU's entire virtual address map. The analysis uses each plaintext
section's full container destination as a **candidate firmware address** and
then checks internal instruction/address evidence against it. It does not use
the AP physical reservation as the firmware instruction address.
[Loader](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/wlan/gen3/common/wlan_lib.c#L818),
[WMT remapping](https://github.com/lineage-geminipda/android_kernel_planet_mt6797/blob/c5b0be85017ad0c599725e8273842efdbecdd88a/drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c#L1117).

The selected host START call disables address override. Its zero address is
therefore not an entry point for this analysis; see [WIFI_START.md](WIFI_START.md).
No reset-vector or boot-entry attribution is claimed.

## Decoder and structural evidence

The guest's Ghidra 12.1.2 NDS32 little-data-endian definition was used with
its big-endian instruction decoder. Data byte order remains an assumption:
the immediate/control-flow evidence here does not independently establish it.
No emulation, decryption, automatic whole-program analysis or device access ran.
`PseudoDisassembler` decoded from each section start, advancing by decoded
instruction length or two bytes on failure. The first pass capped each section
at 16384 attempts. Direct-flow counts below exclude unknown indirect targets.

| Section | Attempts | Decoded | Failed | Terminal instructions | Direct targets | Targets inside plaintext mappings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0, encrypted control | 2265 | 1805 | 460 | 4 | 349 | 0 |
| 1, encrypted control | 3480 | 2700 | 780 | 4 | 553 | 0 |
| 2, plaintext | 16384 | 16384 | 0 | 178 | 1698 | 1698 |
| 3, plaintext | 16384 | 7935 | 8449 | 1 | 1057 | 593 |

The encrypted byte populations were placed at artificial nonoverlapping
addresses solely as negative decoding controls. Their target-location counts
are not comparable evidence about their true execution addresses. An initial
control placement collided with a plaintext mapping and Ghidra refused it;
that run supplied no measurements. The corrected run produced the table.
Section 3's failures do not establish that it contains no code. Relative
branches staying in range cannot by themselves prove absolute placement.

## Independent address check and one anchored trace

An in-memory scan examined two-byte-aligned adjacent 32-bit instruction pairs
throughout section 2. It selected NDS32 `sethi` followed by `ori` or `addi`,
requiring the destination and source register to be the same register in the
pair. Arithmetic follows the installed decoder specification: a 20-bit
immediate shifted left 12, then OR with an unsigned 15-bit immediate or addition
of a signed 15-bit immediate, modulo 2^32. This is a narrow search, not a
general constant-propagation engine or proof of instruction boundaries.

There were 8728 pair candidates. Of their resulting full addresses, 3268 land
inside section 3's candidate extent; 12 land in the ten previously bounded
keyword spans (including their terminating NUL). A low-20-bit comparison yields
3283 extent hits and the same 12 keyword-span hits. Thus the full-address model
has substantial independent internal support, beyond relative branches and
the AP-side mask. These constants are reference candidates; they do not prove
that a string is consumed, that a branch executes, or that a command applies
calibration. No private addresses, bytes, span contents or disassembly are
published.

The single NVRAM-containing span has two pair candidates. For the first in
section order, a full section-2 linear decoding pass established that the pair
starts on a decoded instruction boundary; that full pass had zero decoding
failures. Direct call destinations within section 2 were collected as entry
candidates. The nearest such destination at or before the pair was selected
as one explicitly provisional containing-function hypothesis.

From that entry, a graph walk followed direct branches and fallthrough, without
entering callees, visiting each address once with a 4096-node cap. Its queue
exhausted after 68 nodes, with zero invalid decodes, one terminal instruction
and no node outside section 2. It did not visit the chosen pair. That precise
negative result rejects this containing-function hypothesis for the examined
direct-flow graph. It does not exclude an earlier entry, indirect transfer,
callee relationship or another reference. No further entry or handler search
was performed in this slice.

## Retention and interpretation

The existing immutable firmware identity was reused, with no new hash or
firmware export. Host and guest had approximately 86 and 87 GiB free before
analysis. Small headless projects, logs and scripts lived in guest-owned
temporary directories outside the immutable evidence tree. Cleanup traps were
installed immediately; all three run directories, including the refused run,
were removed. A final directory check found none remaining and the RE shell
was closed. No analysis database is retained.

The useful result is a supported candidate code mapping and an instruction-
aligned reference candidate, plus the rejected entry hypothesis. The remaining
unknown is the reference's containing executable path and its semantics, not
decoder availability or blanket encryption. This does not change the local
record policy, prove firmware/record pairing, identify command `0x48`, or add
a radio admission requirement. [NORMAL_COMMAND.md](NORMAL_COMMAND.md) retains
its host-side submission boundary; ordered work belongs to the roadmap.
