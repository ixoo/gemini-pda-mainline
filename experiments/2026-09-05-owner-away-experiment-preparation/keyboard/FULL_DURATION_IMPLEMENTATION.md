# Harmless duration package implementation — local review only

This implements the offline path proposed in
[FULL_DURATION_PROPOSAL.md](FULL_DURATION_PROPOSAL.md). No backend window has
been consumed. Capture's host gate and production monitor default remain off.
The original `monitor.c` and `monitor-fixture.c` bytes are unchanged.

## Assigned-window entry

After coordinator review, commit integration, publication and explicit assignment
of the userspace window, the dispatcher accepts:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/buildbox_userspace.py \
  --branch main --keyboard-duration
```

The mutually exclusive duration kind selects the shared reviewed musl preparation
in `build-monitor.sh`, then one fixture-only compile and one harmless `ignore`
run. It skips both monitor replicas, size checks and the scaled-test branch.
It uses the existing pinned compiler/linker and musl archive recipe, retaining
actual tool and library hashes and licenses. No installed musl copy is assumed.
The existing monitor build path remains the default for its callers.

The duration kind has its own staging, package, publication and fetch names.
A once-only per-revision attempt marker precedes the fixture phase; rerunning
that revision refuses and requires review, including after an interrupted run.
The package contains raw proof, its checksum manifest, the recomputed
classification, tool provenance, licenses and the enclosing package checksums.
Fetch retains the exact completed-log identity and clean/published revision
checks. It validates the exact duration inventory and binds the proof's source
hashes to Git bytes from the submitted revision, tool provenance and licenses.
A complete failed lifecycle can be fetched as a **failed** proof. Fetch success
alone is not timing acceptance; inspect `duration_classification` and the saved
classification. Malformed or incomplete packages refuse validation.

## Evidence and acceptance

`full-duration.py` records forwarded stdout/stderr, independently retained
observer stdout/stderr, raw monitor status, process result and elapsed time,
fixture bytes, and exact source/tool/library inputs. Files are created without
overwrite, fsynced and sealed before harness temporary-state cleanup. Cleanup
also requires the harness to finish with an observed terminal process; otherwise
both the proof and original stage remain. Fixture-only directories have no
automatic finalizers, so retained originals survive interpreter shutdown. The
classifier reparses saved bytes, checks exact inventory and checksums, rejects
source or fixture mismatches, and does not rely on a success message printed by
the process.

Pass requires the unique 202000 marker, identical forwarded/retained bytes,
empty stderr, expiry reason `deadline`, process exit 2, child SIGKILL, reaped 1,
identity lost 0, cancellation 0, both signal errors 0 and late 0. Measured TERM
must be 209000–210000 ms, KILL 213000–214000 ms, and reap between KILL and
215000 ms; the existing triggers and hard bounds are unchanged. The complete
observed harness interval must be at least 202 and less than 225 seconds.
Missing or malformed status, early signals, deadline misses, incomplete process
results or failed forwarding cannot pass. This is a harmless QEMU lifecycle
proof; it does not establish keyboard support or target disconnect behavior.

## Resource and failure accounting

The shared preparation checks 512 MiB available, serializes with the userspace
lock and reconstructs one musl installation in the managed stage. Phase limits
are: download 120 seconds, configure 120, library build 600, install 120;
configure/build/install have five-second kill escalation. The fixture compile
has 30 seconds, its run has 225 seconds, direct-child wait has one second and
pipe drains have finite byte/iteration limits. The enclosing Python phase has
300 seconds with five-second kill escalation. The remote duration wrapper has
1500 seconds plus ten-second kill escalation; local dispatch keeps its existing
1800-second timeout. Fetch remains a separate 180-second/32-MiB transfer.

These are process deadlines, not evidence that all descendants ceased. In
particular, an interrupted outer wrapper can outlive a separately created
fixture session. A wrapper timeout or failed cleanup needs backend process
review before another measurement; it never becomes a pass. A direct child
reap is distinguished from such an outer timeout in the raw process result.

Ordinary terminal runs with fully sealed replacement proof permit explicit
fixture cleanup. Only after that cleanup succeeds does the runner write the
fixed cleanup receipt. Any preservation error, incomplete run, timeout, missing
cleanup receipt or nonzero shell result retains the entire fixed stage in place,
including original fixture files and library/build data. No attempt is made to
move only an incomplete proof and delete its originals. Any retained duration
stage blocks automatic reuse even for a different revision; the coordinator must
review evidence and process state before cleanup. This retains at most the one
fixed stage and prevents accumulating repeated stages. Packaging or transfer
failures must be recovered from the existing exact package, not blindly rerun.
The retention diagnostic leaves descendant cessation explicitly unestablished.

## Local verification and remaining admission

Thirteen proof fixture methods cover valid synthetic evidence, control failures,
early/late/unordered times, missing/truncated/mutated data, source/binary drift,
incomplete process/forwarding, duplicate status, symlinks, overwrite refusal and
raw preservation before cleanup. Fault injection covers original-file reads,
first and partial writes, fsync and sealing failures. Tests also check uncertain
terminal state, garbage collection and interpreter-exit retention, shell timeout
and missing-receipt retention, and stale-stage refusal. They pass normally and with Python optimization.
Six dispatcher methods exercise all three kinds, main/worker branch rules,
fetch-only recovery and changed/empty remote-ref refusal with transport mocked.
Twelve native scaled monitor methods and six capture methods pass. Shell syntax
and ShellCheck pass. No production-duration execution or ARM64 compilation was
performed locally.

Capture still needs actual accepted prerequisite receipt binding and independent
exact Dropbear disconnect evidence before any enablement review. Neither capture
admission nor its execution gate is changed by this implementation. Work ordering
continues to belong to [the roadmap](../../../docs/ROADMAP.md).
