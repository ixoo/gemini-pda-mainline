# Experiment: retained ram-console authority audit

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-21-mainline-retained-ram-console-authority-audit` |
| Status | completed source audit; production authority remains inconclusive |
| Subsystem | MediaTek retained preloader/LK ram-console and A34 reset provenance |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-21 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, production A34 provenance owner |

## Question or hypothesis

Can the exact retained ram-console layout be parsed strictly enough to expose
the current preloader reset-status word without accepting corrupted offsets,
and can that word, alone or with the raw TOPRGU snapshot and LK boot reason,
prove the fresh secure-platform epoch required by A34?

The source hypothesis has two independently falsifiable parts:

1. a pure bounds-checked parser is separable from physical mapping and reset
   classification; and
2. the public status semantics contain an independently attributable value or
   tuple that proves the secure payload was freshly loaded.

## Provenance and environment

- Repository input: signed and pushed commit
  `97d9a02ab58dc967d0683380dbe3da481ccf8885`.
- Planet LK: [`dguidipc/gemini-lk-android8`](https://github.com/dguidipc/gemini-lk-android8/tree/f4988d74bb70a0a15d7f362f412afba7e7fcda46)
  at `f4988d74bb70a0a15d7f362f412afba7e7fcda46`.
- Gemian kernel: [`gemian/gemini-linux-kernel-3.18`](https://github.com/gemian/gemini-linux-kernel-3.18/tree/d388d350cb2dda8f23b99be6fa5db9628896e87f)
  at `d388d350cb2dda8f23b99be6fa5db9628896e87f`.
- Mainline board description: canonical patch `0020`, which reserves
  `[0x44400000, 0x44410000)` as `no-map`.
- Prior independent observation: canonical patch `0303` preserves raw TOPRGU
  `WDT_STATUS` without interpreting it.
- Exact source hashes are recorded in
  [`results/source-provenance-20260821.txt`](results/source-provenance-20260821.txt).

No preloader source or complete preloader reset-status enum is present in the
audited public repositories. Search for the exact public structure and known
enum spellings found matching kernel/LK readers, but no independently pinned
preloader writer.

## Safety assessment

This was a read-only public-source audit. It did not access the Gemini, map its
retained memory, build a kernel, create a boot image, write boot2, reboot, or
change any CPU state. Temporary partial clones were outside the repository;
only source identities, structural facts, and conclusions are recorded here.

## Associated code

- [`results/source-provenance-20260821.txt`](results/source-provenance-20260821.txt)
  records exact public source identities and hashes.
- [`results/header-layout.tsv`](results/header-layout.tsv) freezes the common
  64-byte wire layout without copying source.
- [`results/authority-matrix.tsv`](results/authority-matrix.tsv) separates
  parseable observations from production authority.
- [`DESIGN.md`](DESIGN.md) specifies the selected pure-parser boundary.

The follow-on parser experiment is
[`../2026-08-21-mainline-mtk-ram-console-parser/`](../2026-08-21-mainline-mtk-ram-console-parser/).

## Procedure

1. Fetch each public repository and resolve the exact pinned commit.
2. Hash the MT6797 ram-console, target configuration, and boot-reason sources.
3. Compare field offsets and record chaining in LK and the vendor kernel.
4. Identify every public interpretation of the preloader `wdt_status` word.
5. Inspect the MT6797 project/platform build files for the optional full-PMIC
   reset define.
6. Compare the retained semantic word with LK command-line boot reason and the
   separately captured raw TOPRGU word.
7. Specify the minimum corruption checks required before reading four bytes at
   `off_pl`.
8. Decide separately whether parsing, mapping, classification, and A34
   lifecycle publication are justified.

## Observations

The pinned LK and Gemian kernel independently describe the same 64-byte wire
header: sixteen little-endian 32-bit words. They agree on signature
`0x43474244`, current preloader offset, prior-preloader offset and size, current
and prior LK offsets and size, total buffer size, Linux offset, and console
offset. LK's word 9 is named `dump_step`; the kernel includes that word in
padding, but all later fields remain at the same byte offsets.

The MT6797 LK pins the DRAM region to `0x44400000` with size `0x10000`. It
requires `off_pl == sizeof(header)` in its abnormal-boot path. It derives
`off_lk` from `off_lpl + ALIGN(sz_pl, 64)`, sets `sz_lk` to 64 bytes, derives
`off_llk`, and then derives `off_linux`. The current preloader record begins
with one 32-bit `wdt_status` word.

Neither audited implementation is strict enough to reuse as a mainline
parser. LK selects DRAM after only an SRAM-signature miss and does not first
validate the DRAM signature or every range before pointer arithmetic. The
vendor kernel checks some offsets against `sz_buffer` but does not exclude all
integer overflow, short records, or crossed ranges. It also has an old-format
fallback that reads one byte at fixed offset 12. The vendor driver then copies
the region and rewrites/clears later portions. A new observation path must not
inherit those compatibility or mutation behaviors.

The public LK names only these semantic values:

- normal boot: `0`;
- software watchdog: `2`;
- external-interrupt marker bit: `0x100`;
- system-reset marker bit: `0x200`; and
- optional full-PMIC reset bit: `0x800`.

The `0x800` interpretation is compiled only when `MTK_PMIC_FULL_RESET` is
defined. At the pinned public revision, the MT6797 platform rule leaves that
option commented and none of the public project makefiles enables it. A
private product overlay could differ, so this is evidence about the public
source build contract, not proof about the shipping binary.

LK's numeric/string boot reason is a different preloader-supplied object. It
distinguishes power key, USB, RTC, watchdog, bypass, tool, two-second reboot,
unknown, panic, reboot, and watchdog categories, but does not attest secure
payload loading. The ram-console status is also distinct from raw TOPRGU
`WDT_STATUS`; matching watchdog-like observations would be correlated reset
history, not independent proof of a fresh secure epoch.

The complete public preloader enum and writer ordering remain unavailable.
Unknown status bits therefore cannot be rejected as unsafe or promoted to
safe. Zero is especially ambiguous: LK treats it as a normal boot, not as a
cryptographic or electrical freshness assertion. Power-key or USB boot reason
likewise does not prove that DRAM and the secure payload crossed a cold power
boundary.

## Analysis

The first hypothesis is confirmed. A parser can operate on a caller-owned byte
copy, require the signature and exact buffer size, require `off_pl == 64`,
require a preloader record of at least four bytes, validate every aligned
addition without overflow, and require the exact two-preloader/two-LK prefix
chain before returning the complete raw current status. It needs no mapping,
MMIO, reset interpretation, or production caller.

The second hypothesis is rejected for the audited public inputs. The raw
TOPRGU word, preloader semantic status, and LK boot reason all describe the
reset/boot path. None says that the secure image was newly loaded, that its
private replay byte was initialized from the image, or that no retained secure
state survived. Combining correlated observations does not manufacture that
missing owner fact. The optional full-PMIC value is not active in the public
project configuration and has no pinned preloader writer contract here.

Physical mapping is a separate boundary. The board range is deliberately
reserved `no-map`; a later reader must bind the exact reservation, copy once
without modifying it, and prove its ordering relative to any writer. This
audit does not authorize such mapping.

## Conclusion

`confirmed` for a strict, hardware-free parser boundary at the exact public
revisions. `rejected` for treating any currently known ram-console status,
TOPRGU status, LK boot reason, or combination of them as sufficient fresh
secure-platform-epoch authority.

The A34 production owner remains CLOSED. CPU8/CPU9 vetoes and all provider,
transaction, P30, PSCI, and hardware exclusions remain unchanged.

## Follow-up

Implement and prove only the pure parser described in [`DESIGN.md`](DESIGN.md)
on Buildbox. After that, audit a separate immutable mapping/copy owner and seek
an independent secure-epoch attestation. Do not add a reset classifier, A34
caller, lifecycle publication, boot candidate, or device attempt from this
result.
