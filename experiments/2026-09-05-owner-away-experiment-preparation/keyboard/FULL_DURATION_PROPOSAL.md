# Bounded full-duration fixture proposal — not admitted

This supplements [the capture handoff](CAPTURE_RUNTIME_HANDOFF.md). It proposes
one offline Buildbox measurement; it neither submits that measurement nor enables
capture. Work ordering remains in [the roadmap](../../../docs/ROADMAP.md).

## Exact scope and inputs

Use the current reviewed monitor and harmless `ignore` fixture, with
`MONITOR_FULL_DURATION` and static ARM64 compilation under QEMU. Run exactly one
202-second observation lifecycle. Do not invoke the current `keyboard-monitor`
dispatch route: it repeats the full size build. The accepted disabled package
from revision `75636670d933b9231f36fddf2ce876801568f64e`, package identity
`7eb7313217d0efe306b33a8bd7f90a4e782c7d0931ce71362b2de0ce8a33767f`,
is historical size evidence; it does not prove the changed monitor source.

Reuse the reviewed toolchain and pinned musl source recipe. The musl archive
SHA-256 is `d585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a`.
Do not assume a retained musl installation exists: the build recipe removes it.
A dedicated route must reconstruct that one library in managed temporary state,
then compile only the harmless fixture (the current harness additionally compiles
an unused disabled entry). Record actual compiler, linker, QEMU, library, license,
source and resulting fixture identities. Existing tool hashes are comparison
inputs, never substitutes for hashing the tools actually used.

## Changes required before assigning a backend window

1. Extend `full-duration.py` to persist bounded raw stdout, stderr, monitor status,
   process result and source/binary/tool identities before fixture cleanup,
   including failures. Preserve an immutable checksum manifest. Parse the saved
   bytes again for the final classification; a printed success JSON is insufficient.
2. Require the complete expected lifecycle: the 202000 observation marker,
   expiry reason `deadline`, exit 2, child SIGKILL, reaped 1, identity lost 0,
   cancellation 0, signal errors 0 and late 0. Require ordered measured times:
   TERM 209000–210000 ms, KILL 213000–214000 ms, and reap between KILL and
   215000 ms. Keep triggers 209000/213000 and hard bounds 210000/214000/215000.
   A timing miss remains a failed proof even if cleanup succeeds.
3. Add a fixture-only dispatcher route and exact package allowlist. Preserve the
   completed-log package identity, clean submitted commit and fresh remote-ref
   checks already used by the dispatcher. Pin the changed closure in the submitted
   revision and verify fetched bytes against its manifest. Do not relabel this
   package as an enabled production monitor or keyboard support result.
4. Add missing/malformed/truncated/mismatched and deadline-miss receipt fixtures.
   No repeat size measurement or live-device transport belongs in this route.

## Time, storage and cleanup accounting

The current harness allows two sequential 30-second compiles, a 225-second outer
observation window, a one-second child wait and bounded pipe drains. Thus 225
seconds is not the whole job budget. Library reconstruction, packaging and fetch
are additional phases requiring explicit finite limits in the proposed route;
its remote and host deadlines must cover these phases and cleanup. Do not claim
a hard wall-clock cleanup guarantee from a process timeout.

Check backend free space first. Use one managed temporary stage, register cleanup
immediately, and refuse or safely clean stale partial stages. Keep WNOWAIT-held
process identity through group cleanup. Preserve bounded failure evidence before
removing fixture/library staging on success or failure. Fetch only the validated
proof package into the ignored Buildbox export tree. No source-tree transfer,
extra Linux tree or retained duplicate build is required.

## Capture admission remains blocked

`capture.py` currently checks full-duration and disconnect receipt hash syntax;
it does not read and validate those proof bytes. Before enabling, preparation
must open actual immutable prerequisite receipts, verify their manifests and
successful classifications, and bind them to the exact monitor binary, source,
protocol and relevant runtime/transport contract. Missing, mismatched, failed or
inconclusive receipts must refuse before a claim or connection. Administrative
owner/custody pins similarly require actual reviewed evidence, not invented hash
strings. Exact Dropbear disconnect preservation remains an independent proof.

The integrated host execution gate stays disabled. The imported-helper mutation
fixture now expects the earlier `imported closure drift` refusal while retaining
its claim/transport sentinels. Six capture tests pass normally and with Python
optimization. No full-duration run, Buildbox submission, enabled ARM64 build,
production admission or device connection was performed for this proposal.

Source snapshot reviewed by this proposal (future implementation changes require
a new submitted closure):

- `monitor.c`: `eb74dc09f6086aa47a7520f323f18728ab232b338ed02056d5b26338db9e5047`
- `monitor-fixture.c`: `00b36d2f4c4b9cb9a65b6f8915eb973ce2c88f527e00dee1b53b058a64b2b1e4`
- `test-monitor.py`: `cbeafe1a6fb95738224991dbb28eeec74686d82e48c2a599328a270751dc0806`
- `full-duration.py`: `66c00445a7526e5af767c0e9cbb84d534111f1ca57f1e6d10fdd622ceb4e9a67`
