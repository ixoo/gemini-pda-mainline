# One new eMMC read — supplemental-prerequisite preparation

This packet prepares one new measurement: read the entire live-GPT-selected
16 MiB logical boot2 once and compare its hash with the installed padded
candidate, while preserving authenticated A53 serviceability and a complete
independent controller log. It is not another baseline-parser test.

[`SESSION_PACKET.json`](SESSION_PACKET.json) pins the unchanged candidate, all
selected source bytes and independently reviewed prerequisite manifests. Its
explicit selector is `reviewed-supplemental`, accepted by the coordinator for
preparation. [`prerequisite.py`](prerequisite.py) also retains `original-strict`;
there is no fallback, automatic selector or rewriting of original evidence.
Both source closure and raw archive verification must pass the chosen path.
The original strict archive result remains incomplete.

The packet's `execute` entry point unconditionally refuses before any I/O,
regardless of arguments or file placement. The runtime fields remain unfilled.
The historical private launcher/completion drafts are not promoted, moved or
made callable by this packet. Their old path-based refusal is not substituted
for this unconditional gate. Later wiring must retain the disabled gate until
coordinator review explicitly accepts the whole runtime path; this document
cannot enable it.

## Concrete session and evidence

Reuse the currently installed authenticated candidate and validated deployment
receipt. No candidate rebuild or new deployment is requested. A future physical
boot is useful because it supplies an independent, exactly counted storage read
with before/after serviceability and full-log evidence. The owner and coordinator
must select/admit that new session; no physical action is requested now.

The existing [admission protocol](ADMISSION_HANDOFF.md) defines the exact three
observation connections and later completion phases. The prerequisite clause is
extended only by the explicit accepted supplemental selector. Its fixed sequence
and budgets remain:

1. New-boot authenticated preflight, within 45 seconds; reject a reused baseline
   or recovered boot identity, missing logger, changed members/topology or guards.
2. One input-only read of boot2 offsets 0–16777215, 32768 sectors, through the
   pinned existing observer. The inner read deadline is 20 seconds and transport
   ceiling 40 seconds. Require the installed padded checksum; no mount/write,
   extra read, benchmark or retry.
3. Same-boot postflight within 45 seconds. Failed/incomplete read stops the
   sequence instead of running postflight or repeating the read.
4. Separately admitted seal/export within the logger's original 600-second
   lifetime (30-second transport), requiring complete sequence-zero-through-seal
   coverage and no targeted controller errors for a final read claim.
5. Separately reviewed ordinary native recovery and owner-confirmed changed-ID
   known-good probe, 15 seconds each. Preserve any failure. The supplemental
   prerequisite is not blanket authorization to reinterpret a new recovery
   timeout; final recovery acceptance needs its own explicit reviewed criterion.

Pre/read/post alone can yield only `read-serviceability-only-pass`. A wrong
checksum or attributable controller error rejects this bounded read; timeout,
missing attribution/log coverage or interrupted transport is inconclusive.
Recovery and final admission distinctions remain in the existing protocol. New
custody, stable power, physical selection, host route, boot identity and owner
console observations must be actual facts; none is inferred from prerequisite
acceptance. No keyboard/radio/thermal test is combined with this session.

## Validation and handoff

Three focused fixture methods pass: explicit supplemental acceptance with strict
refusal/no fallback, changed source pin or missing log refusal, and unconditional
execution refusal before I/O even with execution-like arguments. The accepted
actual prerequisite was also reparsed offline through the selected path. Existing
observer/guard/body evidence retains its scope; no new live observation was run.

Coordinator review must decide the subsequent runtime wiring and admission.
This preparation does not change queue readiness or custody, enable eMMC,
connect to a device, deploy, reboot or request a backend build.
