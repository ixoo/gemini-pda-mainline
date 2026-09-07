# Pyelftools mapping-delta diagnostic amendment

This ninth prospective amendment resolves only the unidentified file-backed
mapping delta in [VALIDATION-V6-REFUSED.md](VALIDATION-V6-REFUSED.md). All
earlier contracts, bootstraps, refusals and diagnostics remain immutable.
`bootstrap-v6.json` and `VALIDATION-V6-REFUSED.md` are an explicit refusal pair.
V6 completed 73 unique mapped module bodies but stopped before engine use,
final closure, method freeze, callback or private access. The single private
analysis remains unused.

The refusal proves only that the guarded file-backed mapping dictionary changed
during the pyelftools import interval. It does not identify an added, removed
or changed file, a standard-library extension, a package native component or a
benign dependency. This amendment authorizes one no-private diagnostic that
retains the exact bounded mapping delta and import event that first observes
it. It grants no mapping/native exception and cannot proceed to method or
private analysis.

Before the diagnostic, pin and verify in [inputs.json](inputs.json) the exact
SHA-256 values of this amendment, the amended [WORK_ITEM.md](WORK_ITEM.md), all
earlier amendments, every earlier bootstrap/refusal record and the v1 mapping
diagnostic trio. Reject drift.

## Frozen diagnostic and reproduction

Create and freeze `mapping-diagnostic-v2.json` containing the complete
independently written source and embedded SHA-256 before first execution. Run
it exactly once with `/usr/bin/python3.12 -I -S -B` through the approved RE-VM
shell. The irreversible audit hook must precede metadata discovery and remain
active through exit.

Reproduce v6 through both exact package inventories, pre-import drift, the
77-entry terminal source map, the exact baseline/vDSO checks and successful
Capstone package import. Require the post-Capstone file-backed mapping identity
dictionary to satisfy the existing exact Capstone-system-native rules. Then
take that dictionary as the immutable diagnostic baseline. Do not instantiate
the engine, open the private ELF or invoke any callback.

Immediately before the single pyelftools import, wrap only the process-local
`builtins.__import__` object and retain its exact original identity. For every
import request while the wrapper is active, snapshot the already defined
strict mapping inventory before delegation and immediately after normal return
or exception. Maintain one global last-seen mapping dictionary so a nested
request that first observes a change owns that change and enclosing requests
cannot duplicate it. Restore the exact original import object after the one
top-level `from elftools.elf.elffile import ELFFile` completes or refuses.

For each first-observed mapping change, record only:

- monotonically increasing import-event index, requested module string,
  relative-import level, bounded `fromlist`, success/failure class and the
  requesting module's exact name when it is in the frozen package map, the
  predeclared standard-library set or is the exact frozen diagnostic harness
  `__main__`;
- added, removed and identity-changed component class; and
- for at most eight affected ordinary files, exact absolute canonical path
  beneath `/usr/lib` or `/usr/local/lib`, SHA-256, size, mode and mtime, plus
  mapping permissions and file offset for at most 32 affected mapping rows but
  no virtual address.

Refuse an unrecognized caller, unsafe/unbounded module or `fromlist` string,
relative/deleted/symlinked/nonregular path, component outside the installed
system roots, more than 256 import events, more than eight affected files or 32
affected mapping rows, an identity change without exact before/after
identities, or a mapping change not owned by one first-observing import event.
Package source imports remain
source-forced; ordinary import behavior is admitted only for the frozen
standard-library set. Record the exact frozen source identity and AST import
statement location matching any mapped package caller/request when uniquely
available; otherwise mark the static source join unresolved rather than infer
one.

After the pyelftools import interval, require all 73 entered mapped package
modules completed, no duplicate/unmapped source, exact vDSO stability, zero
write/cache/network/process/private events and no un-restored wrapper. Record
native-load audit events separately from file-backed map changes. Do not call a
mapping a library load merely because it appears, and do not call a Python
extension responsible unless the runtime import event and exact file identity
support that narrower classification.

Write only `mapping-diagnostic-result-v2.json` and
`MAPPING-DIAGNOSTIC-2.md`, with script/result hashes, UTC chronology, bounded
delta/events, aggregate package counts and `private_reads: 0`. No raw maps,
virtual addresses or private paths may be written. Stop after the diagnostic.
A later prospective reviewed amendment must decide whether the exact component
and import route belong in the frozen standard-library baseline/closure or
remain refused. No decoder engine, method freeze, private analysis,
acquisition, network, device action or build is admitted.
