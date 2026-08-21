# Clock-backend entry ledger

## Status

The predecessor probe/gate candidate produced an exact changed-cycle
`neither`: neither observer record survived and neither protected transport
was reached. The linked initcall order is clock backend, BigiDVFS backend, then
observer. This non-identical, zero-protected-call successor was generated,
manually reviewed, and admitted canonically as patch `0325`. Its first
Buildbox build failed closed before compilation because the base writer still
depended only on the disabled observer. Because the managed Buildbox source
correctly advanced through admitted patch `0325`, the correction is a narrow
follow-up `0326` against that exact source state. It broadens the hidden
dependency only to the clock backend that owns the new call sites. That
follow-up is now generated, manually reviewed, and admitted canonically; no
artifact from any rejected attempt is a boot candidate.

## Question

Does the exact serviceability kernel reach clock-backend driver registration
and the first operation of its probe when only that backend DT node is enabled?

## Hypothesis and unique evidence

The candidate keeps the exact kernel baseline, serviceability initramfs,
Gemini base DT, ramoops reservation, eight-A53 policy, two-write ceiling, and
all CPU/owner closures. Its derivative DT enables only the protected-clock
backend. It does not instantiate the observer, leaves the BigiDVFS backend
disabled, and makes zero protected calls.

Two fixed records reuse retained slots 173 and 174:

1. `driver-init`, immediately before clock-backend platform-driver
   registration;
2. `probe-enter`, as the first clock-backend probe operation.

Both use the exact Gemini compatibility, exact ramoops reservation and size,
`ramoops` compatibility, `no-map`, exact prefix, empty-slot, payload-before-
metadata, and full-readback gates. There is no clear, overwrite, or retry.

## Decision table

| Recovered evidence | Interpretation | Decision-changing next action |
| --- | --- | --- |
| neither | Clock driver init was not reached, or the shared safety/mapping/write path refused | Move to the last proven earlier init stage or split the shared safety predicates |
| `driver-init` only | Registration began, but matching/probe entry was not established | Audit platform-device population, registration return, and exact compatible matching |
| `driver-init` + `probe-enter`, no serviceable runtime | Clock probe began; failure is at or after its first operation | Split allocation, resource mapping, and clock acquisition without adding a protected read |
| both records plus exact serviceable runtime | Read-free clock-backend probe completed | Close this prerequisite and isolate BigiDVFS probe separately |
| malformed, duplicate, or foreign record | Attribution failed | Reject without boundary inference |

## Safety and build contract

- At most two short writes target only the same otherwise-unused retained-RAM
  zones under the standing diagnostic authorization.
- There is no protected read, secure call, MMIO read/write, clock enable,
  storage operation, CPU request, owner registration, retry, reset, reboot, or
  power operation in the new runtime path.
- The clock probe retains only its existing allocation, resource-map, clock-
  handle, lock-init, and driver-data operations.
- The base writer remains opt-in and is available only when either its
  historical observer or the new clock-backend call site is built in.
- Patch generation and compilation run only on Buildbox from a clean pushed
  commit and the integrity-verified managed source through canonical `0324`.
- The generated patch uses a synthetic, non-certifying experiment author with
  no DCO sign-off and is not submission-ready.

## Next action

Build the corrected isolated profile on Buildbox, then independently validate
an exact Android-v0/16 MiB candidate before any device action. Repository-wide
ordering remains in
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).

## Generation and admission

The first generation attempt failed closed on an exact include-order anchor;
the second passed semantic validation and byte-identical replay but strict
checkpatch rejected formatting. Both rejected attempts produced no admitted
patch. Exact pushed commit `178fb2f` then passed parent integrity, semantic and
patch validation, byte-identical replay, and strict checkpatch with 0 errors,
0 warnings, and 0 checks. Manual review confirmed one existing writer, two
call sites, one clock-only DT node, and no protected/secure call. The fetched
and admitted patch bytes are identical. See
[`results/generation-178fb2f.txt`](results/generation-178fb2f.txt).

The first build attempt at exact commit `922c0dd` rejected the profile before
compilation: `CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y` was not retained
because the experiment intentionally disables the observer required by patch
`0323`. This exposed a Kconfig dependency omitted from the original design,
not a source compile or hardware result. See
[`results/build-attempt-1-kconfig-rejected.txt`](results/build-attempt-1-kconfig-rejected.txt).

The first correction generator at exact commit `94e295d` also failed closed:
it expected the historical source state through `0324`, while the managed
Buildbox source had legitimately advanced through admitted patch `0325` during
the rejected build. Rather than reconstruct or copy a second source tree, the
correction is now generated as patch `0326` from exact source state
`ad988125...`. See
[`results/fix-generation-attempt-1-parent-state-rejected.txt`](results/fix-generation-attempt-1-parent-state-rejected.txt).

The next generator revision correctly matched that source-state marker and
Kconfig hash but mistakenly compared the marker with the separate full-tree
integrity digest. Exact commit `c9eff26` failed closed before creating an
artifact. The generator now pins both values independently; see
[`results/fix-generation-attempt-2-integrity-rejected.txt`](results/fix-generation-attempt-2-integrity-rejected.txt).

Exact commit `985f475` then passed the parent integrity, parent Kconfig, source
edit, and corrected Kconfig gates. Its patch-shape validator rejected the
generated subject because the validator accidentally omitted the word `make`
from the exact expected subject. No patch was admitted; the exact string check
is corrected in
[`results/fix-generation-attempt-3-subject-rejected.txt`](results/fix-generation-attempt-3-subject-rejected.txt).

Exact commit `395b1ed` repeated only that patch-shape rejection because
`git format-patch` folded the long RFC 2822 Subject header between `clock` and
`entry`. The semantic validators again passed. The generator now uses the
short exact subject `pstore: allow clock entry ledger without observer`, which
cannot fold under the formatter; see
[`results/fix-generation-attempt-4-folded-subject-rejected.txt`](results/fix-generation-attempt-4-folded-subject-rejected.txt).

Exact pushed commit `7bcdaa4` generated the one-file follow-up from source
state `ad988125...`. Parent and corrected Kconfig semantics, patch shape,
byte-identical replay, and strict checkpatch all passed. Manual review confirmed
one dependency-line replacement, no runtime-code delta, and byte-identical
fetched/admitted bytes. All 106 manifest profiles preserve canonical ordering;
the invariant self-test rejected all 8 mutations. See
[`results/fix-generation-7bcdaa4.txt`](results/fix-generation-7bcdaa4.txt).
