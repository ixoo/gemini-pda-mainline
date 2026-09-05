# One production-duration harmless fixture — passed

The coordinator-admitted Buildbox attempt at source revision
`6d8c9b18420aeb0af14530a98aec1ef9979d2203` completed once and fetched the
validated duration package. There was no retry, repeated size build, kernel
build, native VM build, device access or production enablement.

[receipt.json](receipt.json) records the exact source, package, proof, fixture,
tool, raw-member and local build-log identities. The package identity is
`b8d5917b1f798f8d896caca76865f865b83b504a740326de7a0300f6fbc30fbd`;
the nested proof identity is
`bc165b390b04345eec23a2e6a0d2cc86bd193099b2cdb6bc64f0026e30480870`.
The package remains below the ignored Buildbox export tree identified in the
receipt; no binary or raw artifact is tracked here.

## Observed result

| Measurement | Observed | Required bound |
| --- | ---: | ---: |
| Observation marker | 202000 ms, once | 202000 ms |
| TERM | 209000 ms | 209000–210000 ms |
| KILL | 213001 ms | 213000–214000 ms |
| Child reap | 213021 ms | KILL through 215000 ms |
| Harness elapsed | 213.05312350800523 s | at least 202, less than 225 s |

The raw status has reason `deadline`, child signal 9, reaped 1, identity lost 0,
cancellation 0, both signal errors 0 and late 0. Expected process exit was 2;
its saved error is null. Forwarded and independently retained stdout match at
57 bytes, including the unique observation marker; stderr is empty. The saved
classification is `passed` with no failures. Local revalidation reparsed the
package checksums and raw proof and checked its source hashes against Git bytes
from the exact submitted revision. The coordinator independently read the
saved process/status and reparsed the proof against unchanged reviewed source
hashes, reporting the same pass and proof identity.

## Provenance and cleanup

The clean local checkout and published main ref matched the admitted revision.
Preflight found no active build/fixture process and no prior duration stage,
attempt or publication for that revision. Buildbox doctor passed; available
workspace space was 262 GiB, with approximately 86 GiB available on the host.
The remote build script required its exact clean Git revision before fixture
construction. The pinned musl source was reconstructed once, and the original
harmless fixture was compiled statically for ARM64 and run under QEMU. It did
not enter the disabled-monitor replica/size-build branch.

The dispatcher exited 0 after exact-package fetch and validation. A bounded
read-only postflight confirmed the remote checkout still clean at the submitted
revision, matching publication/package identities, the consumed attempt receipt,
and absence of the temporary duration stage. No duration process using that
stage path was observed in the postflight snapshot. The stage's temporary
library/build/fixture data was removed by the successful reviewed cleanup path;
the package remains retained. The worker separated from the shared main branch
before the coordinator resumed main changes.

## Interpretation

This is one full-duration lifecycle observation for the exact harmless ARM64
fixture and monitor engine source, including the forced-cleanup branch. It is
not a keyboard observation, a repeatability result, or a proof of Dropbear
transport-disconnect behavior. Capture remains disabled. Actual prerequisite
receipt validation and binding to any future enabled production package,
independent disconnect preservation evidence and owner/device admission still
require their own review. No capture admission follows automatically.

The [implementation handoff](../../FULL_DURATION_IMPLEMENTATION.md) describes
the route and failure-retention policy. This result changes the full-duration
prerequisite evidence only; work ordering stays in the
[roadmap](../../../../../docs/ROADMAP.md).

## Unfulfilled capture admission contract

The next preparation gap is a reviewed exact Dropbear no-PTY disconnect protocol
and receipt validator. It must pin the actual server build, shell and monitor
source/package contract; distinguish lost SSH transport from child termination;
and require independent preservation/reparse of retained files and attributable
terminal status after disconnect. Source inspection of channel pipes alone is
insufficient. No target disconnect test is assigned by this result.

In `capture.py`, `prepare` still validates the syntax of
`full_duration_receipt_sha256` and `disconnect_receipt_sha256` without opening
those prerequisite bytes. A future reviewed change must validate the immutable
actual proof packages and their outcomes, bind them to the admitted source,
protocol and production binary contract, and refuse absent, altered, failed or
inconclusive prerequisites before a claim or transport. This fixture hash cannot
be substituted for the hash of a future enabled production monitor. A fresh
baseline/source/custody admission is still required; the closed device session
is not reusable. The unconditional host gate remains in place throughout this
preparation. This identifies the remaining dependency, without assigning another
backend run or physical action.
