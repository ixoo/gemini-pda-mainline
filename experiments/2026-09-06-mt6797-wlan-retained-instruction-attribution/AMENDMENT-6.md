# Exact vDSO baseline-mapping amendment

This sixth prospective amendment resolves only the executable pseudo-mapping
classified by [MAPPING-DIAGNOSTIC.md](MAPPING-DIAGNOSTIC.md) and its hash-pinned
result. All earlier contracts, bootstraps, refusals and diagnostic files remain
immutable. The diagnostic granted no admission. No decoder has been imported
under an accepted preflight, no private ELF has been opened, and the single
private analysis remains unused.

The one authorized diagnostic reproduced both package inventories at the v4
baseline point and observed exactly one executable pseudo-file row: `[vdso]`,
`r-xp`, 4,096 bytes, file offset zero, device `0:0`, inode zero, multiplicity
one. Its two full in-process snapshots, including addresses, matched. Linux's
documented `/proc/PID/maps` interface identifies `[vdso]` as the virtual dynamic
shared object supplied by the kernel; see
<https://docs.kernel.org/filesystems/proc.html>. This supports only the narrow
baseline classification below, not trust in its code or a general pseudo-map
exception.

Before a replacement preflight, pin and verify in [inputs.json](inputs.json)
the exact SHA-256 values of this amendment, the amended
[WORK_ITEM.md](WORK_ITEM.md), all earlier amendments, every earlier
bootstrap/refusal record, and all three mapping-diagnostic files. Reject any
drift.

## Sole executable pseudo-map admission

Create a complete fresh mapping inventory immediately after importing the
frozen standard-library set and before package discovery. In the guarded
process, admit exactly one executable non-file-backed baseline row only when
all of these predicates hold simultaneously:

- pathname is exactly `[vdso]`;
- permissions are exactly `r-xp`;
- byte length is exactly 4,096;
- file offset is zero, device is `0:0`, inode is zero and multiplicity is one;
- it already exists in the interpreter/stdlib baseline before package
  inventories, decoder source execution or native-load wrapping; and
- its complete parsed row, including virtual address range, remains identical
  in the pre-import, post-Capstone-import, post-pyelftools-import and final
  mapping snapshots.

Do not open, copy, hash, parse, explicitly invoke, symbol-resolve or otherwise
inspect the vDSO bytes. Incidental interpreter or libc use is baseline process
behavior outside this method's observability and must not be attributed to a
decoder. Do not count the vDSO as a file-backed decoder/native
component, a newly mapped library, a package asset or satisfaction of any
`DT_NEEDED` entry. Record only the normalized tuple above and the four-snapshot
equality; do not publish or hash its address. Its admission means solely that
this pre-existing documented kernel virtual DSO does not make the guarded
file-backed native-closure check refuse.

Refuse every blank-name executable mapping, every executable bracketed label
other than exact `[vdso]`, a second executable pseudo row, any tuple or address
drift, or any vDSO row first appearing after the baseline. Continue to require
all ordinary executable mappings to have absolute canonical nonsymlink
file-backed identities and to satisfy the frozen baseline/new-native closure.
Nonexecutable pseudo/anonymous rows are not native components; compare their
complete parsed rows in process across the same four snapshots, publish only
bounded normalized counts, and refuse an unexpected executable transition.

## Replacement preflight and private-analysis gate

Create and freeze a distinct `bootstrap-v5.json` containing the complete
amended bootstrap and embedded SHA-256 before first execution. Run exactly one
fresh `/usr/bin/python3.12 -I -S -B` no-ELF preflight. It must reproduce both
complete direct-installed package identities, source-only module maps,
stat-only bytecode handling, inert-asset phases, pre-import drift, exact
Capstone optional/system-native route and `DT_NEEDED` closure, zero pyelftools
native requests, the exact vDSO rule above, final package/component drift and
named restoration. The audit hook precedes metadata discovery and remains
active through exit.

Only a complete successful v5 receipt may feed a frozen `method.json` that
contains the already complete analysis source. Only after that freeze may the
still-unused single private child open the exact retained ELF and perform the
original bounded instruction analysis. A failed v5 preflight creates only
`VALIDATION-V5-REFUSED.md` and stops. An accepted result uses
`VALIDATION-RESULT.md`; no earlier validation filename may be repurposed.

Refuse a mapping/parser ambiguity, tuple or chronology mismatch, generalization
from `[vdso]`, vDSO byte access, decoder/native/package drift, or any earlier
amendment refusal. No acquisition, network, device action or build is admitted.
The vDSO exception does not establish decoder safety, private-binary behavior,
runtime invocation or hardware support.
