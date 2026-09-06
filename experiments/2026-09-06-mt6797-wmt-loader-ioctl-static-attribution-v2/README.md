# WMT loader ioctl static attribution, v2

## Review disposition

**Rejected as an accepted result.** Independent review found that batch 2
re-disassembled `[0xb10,0x1200)` for control-flow accounting even though the
frozen contract admitted only direct-edge-selected functions or literal/data
regions in that batch. The verifier froze the replay but did not establish its
contract admissibility. Therefore none of this v2 result is a durable hardware
or compatibility fact. The fresh [v3 audit](../2026-09-06-mt6797-wmt-loader-ioctl-static-attribution-v3/README.md)
prospectively admitted the complete routine in one batch, used no replay and
rederived every accepted conclusion from new output.

## Result

The exact retained `wmt_loader` has a direct local call to request
`0x80047704` at virtual address `0x12a4`, matching the pinned vendor
`COMBO_IOCTL_DO_MODULE_INIT` command. It supplies a scalar normalized chip
value. Cleanup request `0x80047705` at `0x125c` must return zero first.
The init result changes logging but is discarded before this routine returns.

This is static compatibility evidence, not runtime execution, successful
initialization, firmware activity, radio safety or a mainline ABI. Four
predicates resolve conditionally; full aggregate-to-process-result attribution
and a proposed mainline contract remain unresolved.

The [frozen contract](WORK_ITEM.md) selects parent
`65f1b43333b727f0d5bbddf900cd38486a896e4d`. The
[source predecessor](../2026-09-06-mt6797-connectivity-producer-source-attribution/README.md)
owns exact command definitions, kernel handler conditions and aggregate
semantics. This v2 run used fresh identity checks and fresh static output;
excluded v1 partial results were not reused.

## Identity and bounded method

[inputs.json](inputs.json) pins logical input `system/vendor/bin/wmt_loader`,
SHA-256 `446a1318e29c0515cde62c0a335ffb604adc0a955f990d009646e291330d11aa`,
10368 bytes, ELF64 little-endian AArch64. The exact hash matched before each
batch. The analysis used the RE VM, empty `DEBUGINFOD_URLS` and only the complete
predeclared non-debug arguments in [analysis.json](analysis.json). No tool
diagnostic or external-file evidence occurred. No debug/unwind option, debug
link or build ID was used; no program was executed, loaded or emulated.

The permitted first interval included the opening/data-flow region. The second
batch followed its direct continuation and chip-property literal, revisiting
the first routine segment solely for explicit closed-region CFG accounting.
The anonymous routine starts at `0xb10`; its process-entry caller is outside
the admitted regions. It is not silently labeled `main` from a stripped image.

| Accounting | Observed |
| --- | --- |
| Analysis batches | 2 of 2 |
| Static child-tool invocations | 8 of 14, including hash/version queries |
| In-memory Python controllers / RE shell sessions | 2 / 1 |
| Selected routine regions / basic blocks | 1 / 108 |
| Incidental preceding tail | 16 bytes, 4 instructions, 1 partial block; not used as caller evidence |
| Distinct ioctl call sites | 14 of 20 |
| Batch-2 regions / byte volume | 3 of 4 / 2525 of 4096 bytes |
| Disassembly volume / unique code bytes | 4288 / 2512 bytes |
| Selected literal bytes | 44 across two exact anchors |
| Diagnostics, temporary files, saved analysis state | 0 |

Calls do not split basic blocks in the recorded counting convention; branch
targets and branch/return fallthrough boundaries do. Repeated disassembly
counts toward byte/tool volume, not as additional distinct call sites.

## Six predicates

[verdicts.json](verdicts.json) supplies exact virtual-address semantic anchors,
conditions, missing edges and next discriminators for every predicate.

| Predicate | Result | Important boundary |
| --- | --- | --- |
| Identity and open-to-fd | Resolved | Exact `/dev/wmtdetect` literal reaches open; descriptor at `0x3008` feeds cleanup/init. Negative open results retry without a local attempt limit. |
| Init request/call | Resolved | `0x12a4`, numeric `0x80047704`; cleanup and descriptor gates remain conditions. |
| Third argument | Resolved conditionally | Property or kernel-query candidate, normalized then passed as scalar low 32 bits, not a pointer. |
| Aggregate-to-process result | Unresolved | Local logging/discard and later routine-return source are known; libc conversion and startup caller are not. |
| Cleanup/init/autok order | Resolved conditionally | Any selected autok occurs earlier; cleanup zero gates module init. |
| Mainline userspace contract | Unresolved | No standard-interface design or resource/error contract is supplied by this binary. |

### Chip argument

The direct property key is `persist.mtk.wcn.combo.chipid`. Its buffer is parsed
as hexadecimal; a nonzero property-read result and recognized low-word value
select the property path. Missing/unrecognized values use an external-chip or
SoC-query ioctl result instead. A recognized `0x6797` passes through; alias
`0x0279` becomes `0x6797` in the normalization at `0x1224`–`0x1230`. This is a
conditional constant mapping, not proof of an actual runtime argument.

The original candidate is first sent to SET_CHIP_ID before normalization.
Cleanup and init receive the normalized scalar, zero-extended by the 32-bit
register assignment. The command's read encoding does not make that scalar a
pointer. Full string, overflow and libc error validation are not established.

### Ordering and return loss

A recognized MT6797 property/alias skips autok. Recognized `0x6630`/`0x6632`
values use the conditional external-probe/autok branch; the fallback external
query uses a second autok site, whereas the fallback SoC query skips it.
Probe retries can occur before cleanup/init; they are not module-init retries.
Autok return affects logging, not the later init gate.

The common local order is original-candidate SET_CHIP_ID, normalization,
cleanup, then init only if cleanup returned zero. A cleanup error skips init.
Init zero and nonzero results select different logs and join before descriptor
close and later property handling. The later property_set call at `0x13d8`,
not the init aggregate, supplies the normal routine return. Candidate `-1`
takes a separate early `-1` return. Neither is promoted to process exit status:
the startup caller and separate libc ioctl implementation were not admitted.
The unrelated final property's name/value were deliberately not followed.

## Validation, rights and handoff

[FREEZE.md](FREEZE.md) contains literal independent canonical input, anchor,
complete analysis-receipt and complete verdict freezes declared before
[verify.py](verify.py) was constructed. [VALIDATION.md](VALIDATION.md) records
tests actually run and exclusions. The source predecessor's four file identities
and inherited tuples/citations are independently checked field-for-field.

Only sanitized identities, tool receipts, addresses, normalized semantics and
independently authored prose/verifier code are retained. No binary bytes,
instruction listings, complete function dump, strings corpus, decompiler output,
analysis database or private path is retained. This grants no reuse or
redistribution right for the private input or vendor ABI.

Both batches are closed and the RE shell is closed. The next discriminator
requires a separate caller/libc attribution or standard-interface-design item;
this handoff does not start one. No device, network, live process, ioctl,
Buildbox, build, staging, commit or push action occurred. Only this v2 directory
was edited; the frozen contract and concurrent work were preserved.

Astra Medium owned the uncertainty. Observed start was 2026-09-06 19:16:15 UTC.
The coordinator owns Sol Medium independent review and any pilot-03 acceptance
measurement. Credits are unavailable.
