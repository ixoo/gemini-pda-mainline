# Explicit enabled capture producer — awaiting review/window

The third argument to [build-monitor.sh](build-monitor.sh) is now an explicit
`disabled` (default) or `capture` selection. The default still builds the refused
entry. `capture` compiles with `KEYBOARD_MONITOR_ENABLED=1`, retains the full
engine in both independently linked replicas, and publishes a distinct
`keyboard-capture-<manifest>` package containing `keyboard-monitor` and
`production_entry=enabled-admission-v1`. It keeps the existing static-AArch64,
no-interpreter/dependency, map, replica and 128 KiB size checks. Missing-argument
execution of the enabled entry must refuse without starting capture.

Both selections use one reconstruction of the pinned musl library and existing
managed cleanup. Enabled mode additionally runs:

1. The existing scaled monitor suite under ARM64 QEMU.
2. The runnable full-duration harmless fixture with actual signal/reap bounds,
   retaining stdout/stderr/status plus a source/binary-bound JSON result.
3. [test-disconnect.py](test-disconnect.py), using the exact retained original
   userspace package and ARM64 Dropbear under QEMU, disposable fixture keys and
   loopback no-PTY SSH. It waits for genuine harmless fixture output, terminates
   the sole client, and requires an independently returned nonzero monitor,
   retained private bytes and reaped child. The server keeps 60/360-second
   idle/maximum settings. No device, observer, VT, real key or personal endpoint
   is used. Its command shell is the builder account shell, not a claim that the
   entire candidate init has booted.

The disconnect test runs as PID 1 in a disposable user/PID/mount namespace. Its
exit kills remaining namespace descendants. Namespace setup failure refuses;
there is no host-wide process-group cleanup fallback. The existing fixture adds
only one harmless streaming-child mode and private PID/return records. Those
records are not an enabled production path.

The package records the complete runtime source identity, exact producer/test/
provisioning source hashes, resolved compiler/library/tool hashes and package
versions, enabled binary/map, all license notices, full-duration/disconnect
receipts and synthetic raw lifecycle evidence. `capture.prepare` now verifies
those packaged lifecycle receipts against their actual bytes and source hashes,
as well as the producer/runtime source identity. The original accepted disabled
package and size/full-engine receipts remain untouched.

## One proposed invocation after integration and admission

[CAPTURE_PRODUCER_DISPATCH.patch](CAPTURE_PRODUCER_DISPATCH.patch) is a focused
unapplied delta against integrated main `be52fe21`. It adds `--keyboard-capture`,
keeps the existing main/worker branch checks, dispatch locks and checked fetch,
and selects the distinct producer/publication kind. It does not undo the fresh
post-build remote-ref check. After applying that delta and publishing the
reviewed source revision, the proposed invocation from its clean main checkout is:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/buildbox_userspace.py --keyboard-capture --branch main
```

The producer needs the already retained original userspace package in the
managed userspace root; absence refuses instead of rebuilding or copying it.
Enabled mode's remote timeout target is 1,500 seconds within the existing
1,800-second dispatch target. These are termination targets, not claims of
hard cleanup for arbitrary kernel-stuck processes; the prior post-check policy
still applies. Full-duration/disconnect invocations have 260/45-second outer
targets. Failures stop publication and retain finite diagnostic logs.

Freeze the complete reviewed host/runtime source state before the build. A
later gate/helper/source change invalidates the packaged runtime identity; do
not waive that comparison or relabel an old package. Production host execution
remains off in this source handoff, and no filled physical admission is created.

## Offline checks

Producer and proposed dispatcher Python/shell syntax and ShellCheck pass;
invalid producer mode refuses before backend work. Twelve native monitor tests
and six capture tests pass after adding the fixture mode and packaged proof
checks. No ARM64 enabled build, full-duration run, namespace/disconnect execution,
backend connection, device connection or observer ran for this producer change.
