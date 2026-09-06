# WMT loader: fresh single-batch static attribution

## Result

The fresh v3 analysis establishes a local ioctl call at `0x12a4` using
`0x80047704`, matching the pinned vendor module-init command. It receives a
normalized scalar chip candidate. Cleanup at `0x125c` must return zero before
init is attempted. Init status selects logging, then is discarded; the ordinary
routine return instead comes from a later property_set call.

Five local predicates resolve conditionally. A mainline ABI/design remains
unresolved. Actual runtime values, libc conversion and process exit status
remain outside the claim; no program, device or ioctl was executed.

The [contract](WORK_ITEM.md) prospectively admits the entire routine
`[0xb10,0x14d0)` and exactly two literals. Parent is
`65f1b43333b727f0d5bbddf900cd38486a896e4d`; the
[accepted source predecessor](../2026-09-06-mt6797-connectivity-producer-source-attribution/README.md)
owns kernel command definitions and handler conditions. V1/v2 are excluded
chronology/selection only: every v3 identity, count and semantic finding was
rederived from the fresh v3 batch, not reused from their partial output.

## Exact method and counts

[inputs.json](inputs.json) pins logical binary `system/vendor/bin/wmt_loader`,
SHA-256 `446a1318e29c0515cde62c0a335ffb604adc0a955f990d009646e291330d11aa`,
and freshly observed ELF64 little-endian AArch64 metadata. The hash matched
before analysis. Source-predecessor files were freshly compared against the
frozen parent; inherited source identities and citations remain field-for-field.

One predeclared batch used six static children: hash, three version queries,
non-debug ELF headers/sections and one disassembly over the exact routine.
One in-memory controller read only the two literal intervals and derived
counts from that fresh disassembly. It checked mapping, instruction coverage
and exact NUL-terminated extents. There was no replay, added interval or second
batch. `DEBUGINFOD_URLS` was empty; no debug/unwind option, debug link, build ID,
symbol server or separate input was used. The RE shell is closed.

| Measurement | Result |
| --- | --- |
| Batch / controller / RE shell | 1 / 1 / 1 |
| Static child tools / permitted maximum | 6 / 8 |
| Disassemblies / replays | 1 / 0 |
| Routine code | 2496 bytes, 624 instructions |
| Basic blocks / direct call sites / ioctl sites | 108 / 62 / 14 |
| Exact literals | `[0x14d0,0x14df)`: 15 bytes; `[0x1510,0x152d)`: 29 bytes |
| Total selected code/literal bytes | 2540 |
| Static-analysis diagnostics / temporary files | 0 / 0 |

Basic blocks split at branch targets and after branch/return instructions;
calls do not split blocks. [analysis.json](analysis.json) retains complete
sanitized receipts, arguments, timestamps and counts. The approved launcher
emitted two host capability-check warnings before the controller; these are
recorded separately, not hidden in the zero static-tool diagnostic count.

## Six predicates

[verdicts.json](verdicts.json) gives exact address anchors, conditions, missing
edges and discriminators for each predicate.

| Predicate | Classification | Boundary |
| --- | --- | --- |
| Identity/open-to-fd | Resolved | Selected device path reaches open; stored descriptor feeds cleanup/init. Entry and runtime availability are unobserved. |
| Numeric init request/call | Resolved | `0x12a4`, request `0x80047704`; descriptor, candidate and cleanup gates apply. |
| Scalar argument origin | Resolved conditionally | Property or query-derived normalized low word, not a pointer or unconditional `0x6797`. |
| Local return behavior | Resolved | Cleanup gates init; init result only changes logging; a later property result supplies the routine return. |
| Command ordering | Resolved conditionally | Any selected autok precedes original-candidate cache set, normalization, cleanup and gated init. |
| Mainline ABI/design | Unresolved | Static vendor compatibility does not define a standard subsystem interface. |

The chip key is `persist.mtk.wcn.combo.chipid`. A hexadecimal parse supplies a
candidate whose low word is checked against recognized values. A missing or
unrecognized value triggers external-chip or SoC-query fallback. Accepted
`0x6797` passes through; candidate `0x0279` conditionally maps to `0x6797`.
The argument is zero-extended from a 32-bit register; the read-encoded request
does not make it a user pointer. Complete numeric/overflow validation and the
actual property/query value are not claimed.

Recognized MT6797 property/alias values skip autok. The `0x6630`/`0x6632`
property branch can perform a conditional external probe/autok sequence; its
probe can repeat up to ten attempts. The fallback external-query branch has a
second autok site, while SoC fallback skips it. Those earlier probe retries are
not cleanup or module-init retries. Autok status affects logging, not the later
init gate.

SET_CHIP_ID receives the original candidate before normalization. Cleanup and
init receive the normalized scalar. A cleanup nonzero result skips init; init
zero/nonzero branches both converge before descriptor close and later property
handling. Candidate `-1` takes an early local `-1` return. Otherwise the later
property_set at `0x13d8` supplies the routine return. The unrelated property
literals were not read. The routine is not called `main`: its startup caller
and external libc ioctl implementation are outside the admitted interval, so
their conversions and process status remain unresolved.

## Validation and handoff

[FREEZE.md](FREEZE.md) declares literal independent input, anchor, complete
receipt and verdict digests before [verify.py](verify.py) construction.
[VALIDATION.md](VALIDATION.md) records actual checks and exclusions.

Only identities, addresses, counts, two selected literals and independently
normalized prose/verifier code are retained. No raw binary, instruction listing,
function dump, decompiler output, strings corpus, database or private path is
retained. No redistribution, code reuse or vendor-ABI permission is inferred.

The single batch is consumed. Any later caller/libc attribution or mainline
interface design needs a separate item; this handoff starts no adjacent work.
No device, live-process, network, execution/emulation, ioctl or build occurred.
Only this v3 directory was edited by the analyst; the frozen contract and
concurrent work were preserved. Astra Medium owned the uncertainty. Sol Medium
independently accepted the complete v3 result on first review at 2026-09-06
19:49:57 UTC; the review-ready handoff was 19:44:37 UTC. The accepted pilot-03
measurement is in the workflow ledger. Observed start was 19:34:45 UTC. Credits
are unavailable.
