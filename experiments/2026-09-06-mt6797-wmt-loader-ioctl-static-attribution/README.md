# WMT loader static audit: stopped at tool-boundary conflict

This item is **not an accepted static-attribution result**. The admitted binary
matched its exact SHA-256 before analysis. During batch 1, however, `readelf -wf`
automatically attempted a separate debug-info lookup and reported a CRC
mismatch, then ignored that file. The lookup was outside the one-binary scope.
The already-submitted bounded disassembler command also completed in that same
batch. No batch 2 or further binary analysis was started.

## Escalation packet

- Evidence: logical input `system/vendor/bin/wmt_loader`, SHA-256
  `446a1318e29c0515cde62c0a335ffb604adc0a955f990d009646e291330d11aa`,
  matched the frozen contract. The unexpected separate-debug lookup produced
  a CRC warning; the private path and all raw tool output are excluded here.
- Attempts: one predeclared analysis batch, no repairs. It requested section
  metadata, unwind metadata, an exact device-path anchor and disassembly only
  in virtual-address interval `[0xb00, 0x1200)`. The three child tools completed;
  automatic debug lookup was not disabled in the unwind request. No new
  requests were submitted after the conflict was observed.
- Unresolved question: may the item restart with a static reader configuration
  that demonstrably disables separate-debug lookup, and how should the consumed
  batch and partial output be treated? No source or binary conclusion from the
  interrupted analysis is promoted to an accepted fact.
- Next discriminating check: under an explicit amended contract, establish a
  no-follow static-tool mode before reopening only the same hash-pinned binary.
  This item does not authorize that restart or another binary.

The RE shell was closed. There was no program execution/emulation, ioctl,
device access, live-process inspection, network retrieval, build, staging,
commit or push. No binary, strings corpus, complete function dump, decompiler
output, analysis database or temporary analysis file was retained. The frozen
[WORK_ITEM.md](WORK_ITEM.md) was not modified.

## Partial accounting and validation status

Observed start: 2026-09-06 19:12:33 UTC. Batch 1 declaration:
2026-09-06 19:13:48 UTC. One of two analysis batches consumed; batch 2 unused.
Preflight ran hash and file-identity checks plus disassembler/Python version
queries. The batch used one Python controller and three child-tool invocations
(two readelf, one objdump), plus in-memory exact-anchor matching. The displayed
interval contained a partial function region and eleven ioctl call sites;
no accepted function/control-flow classification or basic-block count was
completed before the stop. Block count is unavailable, not zero.

The installed disassembler reported GNU Binutils for Ubuntu 2.42; Python
reported 3.12.3. The retained binary was reported as stripped ELF64
little-endian AArch64. These are preflight observations, not execution proof.

Acceptance predicates, independent freezes, verifier/refusal tests and the
repository gate were not completed: the contract requires immediate stop on
scope conflict. This record is a sanitized escalation, not the requested
accepted result. Credits are unavailable. The coordinator owns the excluded
or amended-work measurement and any authorization to continue.
