# Same-version Gemian pmsg witness design

## Parent and scope

The exact parent is the target-register capsule source with patchset SHA-256
`71ef281a...`. The child changes observation only. It does not reinterpret the
inconclusive prior runtime attempt and does not make pmsg a cross-version
mainline recovery path.

## Writer contract

`pstore_write_pmsg_kernel()` is callable only when `CONFIG_PSTORE_PMSG` is
enabled. It accepts a kernel buffer and a byte count, rejects null, zero, and
counts above 256, takes the existing `pmsg_lock`, and requires all of:

- non-null registered `psinfo`;
- non-null `write_buf`;
- non-null backend name; and
- exact backend name `ramoops`.

The helper calls `write_buf(PSTORE_TYPE_PMSG, ...)` once and returns the backend
status. It allocates no memory and has no retry, loop, physical address, erase,
or device control. Callers are fixed process-context sites and deliberately do
not alter parent control flow from the return value.

## Exact record sequence

Each record is a newline-terminated constant shorter than 256 bytes:

1. `gemini-a72-pmsg-v1 stage=entry parent=register-capsule`
2. `gemini-a72-pmsg-v1 stage=pre-scheduler parent=pair-v6-pass`
3. exactly one of:
   `gemini-a72-pmsg-v1 stage=pre-capsule result=pass` or
   `gemini-a72-pmsg-v1 stage=pre-capsule result=fault`

Entry is before `proc_create()` in the existing late initcall. Pre-scheduler is
inside the complete pair-v6 predicate immediately before
`mt6797_a72_sc_run()`. Pre-capsule follows computation of the unchanged pair-v7
predicate and precedes the unchanged pair-v7 console record and both unchanged
capsule emitters.

The existing console stream remains byte-for-byte schema compatible: no pmsg
record is printed to the console and pair-v6, pair-v7, phase, and capsule
format strings are untouched.

## Runtime classification

- ordered entry, pre-scheduler, and pre-capsule PASS plus valid capsules:
  classify the target-register result;
- ordered entry/pre-scheduler and pre-capsule FAULT: classify the inherited
  scheduler/capsule fault;
- entry or pre-scheduler without a terminal: localize execution before the
  pre-capsule boundary;
- terminal without pre-scheduler, duplicates, both terminal results, malformed
  records, or order violations: evidence corruption or mixed cycle;
- no pmsg witness after a confirmed changed cycle: pre-late-init,
  boot-selection/handoff, or pmsg retention failure, not a CPU result.

Console and USB may corroborate but cannot repair a malformed pmsg sequence.

## Build and physical gates

Generation must reconstruct the exact parent from public Git inputs, verify all
four parent file hashes, apply only the deterministic child, reverse it exactly,
and emit one patch. Buildbox must compare the child with that exact parent and
prove the config and inherited diagnostics identical.

Before any physical boot, a parser must validate raw binary pmsg while treating
all surrounding Android records as untrusted bytes. The installer remains
boot2-only, resolves the live GPT, performs full-partition readback, and shuts
down after success. Changed-cycle recovery remains primary; screen behavior is
non-classifying.
