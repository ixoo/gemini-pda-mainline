# Executable pseudo-mapping diagnostic amendment

This fifth prospective amendment resolves only the unidentified baseline-map
stop in [VALIDATION-V4-REFUSED.md](VALIDATION-V4-REFUSED.md). All earlier
contracts, bootstraps and refusals remain immutable. `bootstrap-v4.json` and
`VALIDATION-V4-REFUSED.md` are an explicit refusal pair. No decoder was
imported, no private ELF was opened and the single private analysis remains
unused.

The v4 evidence proves both complete package inventories and their pre-import
drift checks passed, but proves only that the guarded process had at least one
executable mapping with an absent or bracketed name. It does not identify a
vDSO, a decoder mapping or an anonymous code region. This amendment authorizes
one no-private diagnostic to retain the minimum rejected-row classification;
it does not authorize any pseudo-mapping exception or resume decoder/private
analysis.

Before the diagnostic, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier amendments and every earlier bootstrap/refusal record. Reject any
drift.

## Frozen diagnostic

Create `mapping-diagnostic-v1.json` containing the complete independently
written diagnostic source and embedded SHA-256, and freeze it before first
execution. Run it exactly once using `/usr/bin/python3.12 -I -S -B` through the
approved RE-VM shell. Install the irreversible audit hook before metadata
discovery and keep it active through exit. Reproduce the exact identities and
inventory logic in immutable [bootstrap-v4.json](bootstrap-v4.json), including
both metadata/package inventories, source hashes, stat-only bytecode treatment,
inert-asset phases and one pre-import drift pass. The reproduction point is
immediately before v4's rejected baseline `maps()` classification. Do not
import Capstone or pyelftools, inspect another package or open the private ELF.

Import the complete standard-library set needed by the diagnostic before
taking an interpreter/stdlib mapping baseline. Thereafter require zero decoder
or package native-load requests and no new file-backed executable mapping while
the inventories run. This does not claim the interpreter/stdlib baseline has no
native mappings.

At the exact v4 baseline point, read `/proc/self/maps` twice consecutively.
Parse every row strictly and require exact in-process equality of the two full
parsed snapshots, including start and end virtual addresses. Then discard those
addresses without retaining or hashing either raw snapshot.

For rows whose pathname is absent, publish only class `name_absent`. For a
bracketed pathname, publish its exact label only when it is one of the closed
predeclared set `[vdso]`, `[vvar]`, `[vvar_vclock]`, `[vsyscall]`, `[heap]` or
`[stack]`. Publish every other bracketed name only as class
`bracketed_other`, its UTF-8 byte length capped at 256, and the SHA-256 of those
bytes; never publish its raw label. With that redacted name field, record only
the permission string, byte length computed from the address range,
hexadecimal file offset, device tuple, inode and whether executable permission
is present. Do not retain start/end addresses or ordinary file-backed pathname
rows.

Aggregate identical address-suppressed tuples with exact multiplicity. Record
total pseudo/anonymous rows and executable subset count, with at most 32 total
and eight executable rows; refuse overflow, malformed ranges, an overlength or
invalid UTF-8 bracketed label, a relative or deleted ordinary pathname, or any
difference between the two full parsed snapshots. A `name_absent` or
`bracketed_other` executable row remains a refusal candidate and gains no
admission from this diagnostic.

The diagnostic result goes in `mapping-diagnostic-result-v1.json` with exact
script/file hashes, UTC chronology, package aggregate counts, audit counters
and `private_reads: 0`. A short `MAPPING-DIAGNOSTIC.md` records what was and was
not established. Raw full maps content must not leave the guarded process or
be written anywhere.

## Decision boundary

This diagnostic may classify the rejected mapping but cannot admit it. Stop
after recording the bounded result. A separately reviewed prospective
amendment must decide whether each exact observed executable pseudo/anonymous
class is a stable kernel-provided mapping outside the file-backed native
closure or remains a refusal. Do not infer that a bracketed label is trustworthy
without its complete recorded permission/offset/device/inode/size tuple, and
never whitelist a blank-name executable mapping by default.

Refuse any decoder import, native load, private read, full-map publication,
unbounded row retention, mapping instability, unexpected file access, write,
network, subprocess, device operation or build. No result method freeze or
private analysis is permitted under this amendment.
