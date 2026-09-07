# First mapping delta captured; no admission

The one [Amendment 11](AMENDMENT-11.md) diagnostic successfully stopped after
its first validated mapping delta. Import event 16 requested `resource` from
`elftools.elf.elffile`; its after-delegation observer first saw the exact system
`resource` extension below. This establishes first observation and an exact
source join, not causation, component admissibility or usable pyelftools state.

## Identities and chronology

- Dispatch: `566d56d537acb218d34ffa88a039d9d2129426e6`; Astra Medium.
- All 34 controlling and 18 dependency hashes passed at the explicit
  [input paths](inputs.json) before execution.
- [Diagnostic source](mapping-diagnostic-v4.json) frozen
  `2026-09-07 03:59:41 UTC`; file SHA-256
  `1091f345b4713bd15aecd668fde85df5c82db000bbd4c636ba8b851d03e78bd7`;
  embedded source SHA-256
  `c11ee59ac7d402d1ca0c3382ac272410bca85803493702484110bfe00794d0ca`.
- One fresh `/usr/bin/python3.12 -I -S -B` invocation through the approved
  RE-VM shell: `2026-09-07T04:00:24.844487+00:00` to
  `2026-09-07T04:00:26.184507+00:00`.
- [Result receipt](mapping-diagnostic-result-v4.json), SHA-256
  `9ded854da37d87d2c4bdf8a3f4850b47d3dfac4e0d3a1125d90b3f0eaf482a8a`.
- Immutable canonical first-delta JSON SHA-256:
  `43a3612d6b1b5272528f0d8aa25d29ff8ed50f782f4d4ffa7e3ea1799e54fd67`.

## Exact bounded observation

The added file was
`/usr/lib/python3.12/lib-dynload/resource.cpython-312-aarch64-linux-gnu.so`,
68,288 bytes, SHA-256
`2e1deb71ff45f48040851b25eb46d106baacbcd1804641105dce48f8ed278e44`.
Its mode was `0644`; exact modification time is in the receipt. Four mapping
rows were recorded, with permissions/file offsets `r-xp/0x0`, `---p/0x3000`,
`r--p/0xf000`, and `rw-p/0x10000`. These are file offsets, not virtual addresses.
The file was absent from the immediately preceding global last-seen dictionary.

The first-observing event was a completed level-zero request for `resource`,
empty `fromlist`, caller `elftools.elf.elffile`, line 16, parent event 1.
The unique AST `Import` join is line 16, column 4, in the frozen installed
`/usr/lib/python3/dist-packages/elftools/elf/elffile.py`, 37,150 bytes, SHA-256
`457c93c8be327cbce2a86869aa40d9067f12f7c33052730f7e1cbcccb99b9b54`.
No source text or raw mapping addresses are published.

## Terminal and safety predicates

The warm proof passed with 194 baseline module objects, identical file-backed
dictionary and full pseudo rows, unchanged module identities and unchanged
native/prohibited counters. The run recorded 16 import events and 31 completed
observer intervals with zero observer import audit events. The 256-event cap
was unchanged.

The canonical record was frozen before the irreversible latch. The dedicated
payload-free signal propagated from the first observer through active-wrapper
unwinding. No later wrapper entry, loader-after-exec, outer return, observer
entry or main-after-import propagation path was observed. Those alternate latch
paths are source-enforced but were not runtime-exercised by this run.

All four final restoration checks passed: original import object, native-load
endpoint, finder list, and isolated path. The terminal count was 28 entered and
27 completed mapped modules; the interrupted import was intentionally not
required to finish. This is a successful diagnostic stop, not a completed
73-module package preflight or decoder qualification.

The receipt records one Capstone native request, zero optional requests, and
zero write, cache-write, network, process and private-read events. No engine,
method, callback, private analysis, device action or build occurred. No mapping
exception is granted. The RE shell was closed after the result; no capture file
or raw map was left behind by this diagnostic.

## Checks and handoff

Tests actually run: 52 exact dependency hashes; frozen-source hash and Python
syntax compilation before execution; the single guarded diagnostic; host
canonical-record digest, result identity, exact field/bound/privacy and terminal
predicate checks; relative Markdown-link checks; and `git diff --check`.
No alternate signal-path, restoration-failure or serializer-failure runtime
fixture was run, and there was no rerun against installed tools or another
binary.

Stop here. A later prospective review must decide whether this exact component
and import route belong in the frozen standard-library baseline/native closure.
Neither the mapping nor the interrupted module is admitted by this result.
The one private-analysis execution remains unused. Only this diagnostic's
three new files are handed off; every earlier artifact remains unchanged.
