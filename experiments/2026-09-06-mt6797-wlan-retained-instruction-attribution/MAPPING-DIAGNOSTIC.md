# Mapping diagnostic v1 — classified, not admitted

The one authorized diagnostic observed thirteen anonymous/pseudo-file rows,
including exactly one executable row: label `[vdso]`, permissions `r-xp`,
length 4,096 bytes, file offset `0x0`, device `0:0`, inode `0`, multiplicity one.
There was no executable `name_absent` or `bracketed_other` row in this process.
The complete address-suppressed multiplicities are in
[mapping-diagnostic-result-v1.json](mapping-diagnostic-result-v1.json).

This identifies the observed label and tuple, not its trustworthiness or
stability across processes. It grants no mapping exception. A separately
reviewed prospective decision is required before any replacement decoder
preflight. No decoder import, native package load, method freeze or private
instruction analysis occurred; the single private-analysis budget is unused.

## Chronology and identities

- Clean dispatch: `517fa080acd64e7a8b5eec25f13a510b329ff191`.
- All fifteen controlling and eighteen dependency hashes passed.
- [Diagnostic source](mapping-diagnostic-v1.json) frozen:
  `2026-09-07T02:54:28Z`.
- Execution started: `2026-09-07T02:54:52.084948+00:00`.
- Execution completed: `2026-09-07T02:54:52.135401+00:00`.
- Diagnostic file SHA-256:
  `8ebc7f226817e49786b0fde42e8980c0b7f17255637e500203e3984eaad32ad4`.
- Embedded source SHA-256:
  `29c8d2a902c268f70eb354b58d9c48299440568a34be77a63d54452ef5e3cbb8`.
- Result SHA-256:
  `ae2146baefd5669dc46b1ce9f79392c6f93f5fdb8c4d992ed0a72a346769e352`.

## Checks and limits

The audit hook preceded metadata discovery and remained active until exit.
The complete diagnostic standard-library set was imported before the initial
interpreter/stdlib mapping baseline. V4's two independent package inventories
and pre-import drift pass were reproduced before its rejected `maps()` point.
No new file-backed executable mapping appeared relative to that baseline.

Capstone had 67 entries, including 25 sources, 14 inert assets and 25 stat-only
bytecode files. Pyelftools had 117 entries, including 52 sources, no inert
assets and 52 stat-only bytecode files. Their direct-installed-tree provenance
remains separate; neither is promoted to RECORD or package-manager provenance.
Inert opens occurred only during initial inventory and pre-import drift.
Bytecode was never opened or hashed.

The two complete parsed snapshots, including virtual addresses, compared equal
in memory. Raw snapshots and addresses were neither published nor hashed, and
were discarded in the process. Ordinary file-backed rows were not retained in
the result. The twelve distinct normalized tuples account for thirteen rows.
All reported write/cache/network/process/native/optional counters were zero.

Tests actually run: thirty-three frozen hash comparisons, diagnostic source
digest and syntax checks, exactly one isolated diagnostic, and host result
checks for file pins, tuple fields, closed labels, multiplicities, caps and
guard counters. No mutation suite or normal/optimized instruction-result
verifier ran; neither belongs to this diagnostic handoff. `git diff --check`
passed. No device, network, acquisition, build, commit or push occurred.

Only the three named diagnostic files were added. The RE shell was closed;
no private capture files or raw mapping residue were created. Historical
contracts and evidence remain unchanged. Work stops at this diagnostic handoff.
