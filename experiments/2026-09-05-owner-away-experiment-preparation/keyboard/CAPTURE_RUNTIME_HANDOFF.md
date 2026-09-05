# Coherent keyboard capture source handoff — default off

[capture.py](capture.py) now connects preparation, exact enabled-package delivery,
fixed monitor invocation, independent raw export and existing observer
classification. [monitor.c](monitor.c) has the corresponding fixed-path entry,
compiled off unless `KEYBOARD_MONITOR_ENABLED=1` is explicitly selected. The host
execution gate also refuses before transport. The previously accepted disabled
package is not relabelled as enabled; its identity remains historical evidence.
No runtime contract has been filled with invented device values.

## Admission and execution

`prepare` reparses the accepted baseline/candidate closure through the existing
verifier, checks source identities, exact package/revision/binary bytes and
retained license bytes, and cross-binds the classifier's candidate/helper/source
and baseline result hashes. It requires a newly observed boot, actual owner and
custody facts, exact current event/devnum/capability/resource links, reviewed
metadata and separate full-duration/disconnect evidence pins. These external
review pins are admission inputs; a syntactically valid hash is not proof that
the referenced experiment passed. The coordinator must freeze them from reviewed
raw evidence before enabling the host gate.

Delivery is one claim and one connection, with exact readback of four private
files in an existing executable RAM root. Capture cannot start without the
matching successful local delivery receipt. It rechecks candidate/member hashes,
map readback, capabilities/resource links, foreground tty1, logger and CPU policy.
It scans bounded process/FD inventories for console workers, conflicting readers
and input/console device aliases; races or inaccessible entries refuse. Custody
must keep that exclusion valid throughout the observed interval.

The entry accepts only event/minor arguments and opens the fixed private parent;
no command/helper/path override is accepted. The monitor owns the existing
once-only capture directory and direct observer child. After it returns, the
shell exclusively retains its outer status and repeats the guards. A normal
transport result and the exact postflight marker are required; missing or failed
postflight cannot pass. No failure automatically starts export, recovery or a
second observation. Each action is invoked separately by the custodian.

All actions use the existing bounded SSH runner and private key/host checks.
The local mainline-only route prerequisite runs before a claim. Delivery is
30 seconds, capture including guards 240 seconds, private export 30 seconds.
Capture admission caps original boot age at 240 seconds; delivery and real owner
delays must fit before capture's age guard. A separate 30-second logger seal must
still fit the original 600-second lifetime. This is not a logger reset.

## Complete private preservation and classification

Export is independent of capture success and logger liveness. It exports the
four fixed files, in exact framing, under individual bounds: observer stdout,
observer stderr, monitor status and outer exit. Missing files are explicit,
allowing other unique bytes to be retained; malformed/truncated output refuses.
The remote source is never removed. The host retains raw transport bytes and
materializes every available keyboard file privately, including failed captures.

Assessment rechecks admissions/commands, process results, complete export
framing, forwarded-versus-retained bytes, exact normal monitor lifecycle and the
outer status. It requires a separately supplied actual owner completion record,
then constructs the existing classifier receipt from those checked witnesses.
A classifier pass is observation-only: complete controller-log preservation and
attributable recovery remain independently required for final keyboard acceptance.
Raw keyboard bytes and owner records remain private.

The CLI supports `prepare`, `delivery`, `capture`, `export`, and `assess`, with
explicit admission/package paths; assessment also takes the owner record path.
`--execute` always refuses in this reviewed-off source. No enablement patch or
filled production admission is supplied by this handoff.

## Runnable full-duration fixture and future enabled build

[full-duration.py](full-duration.py) reuses the existing fixture harness, including
WNOWAIT-held cleanup. Its fixture-only compile switch selects production timing;
the harmless child marks 202 seconds and ignores TERM, requiring measured TERM,
KILL and reap evidence. It emits the actual times and fails on any missed admitted
deadline; no scheduler tolerance silently converts a miss into acceptance.
The outer observation ceiling is 225 seconds, not a hard kernel cleanup promise.

During an assigned userspace window, reconstruct the one pinned musl library
using the existing build recipe, then run before that recipe's cleanup:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/keyboard/full-duration.py \
  --compiler "$stage/musl-install/bin/musl-gcc" \
  --qemu "$(command -v qemu-aarch64-static)" --work-root "$stage/full-duration-fixtures"
```

Use a separate fixture work directory. This run builds only the harmless fixture
and disabled entry; it does not repeat the accepted size-only build. An eventual
enabled binary is a meaningful new output: link the same full-engine recipe with
`-DKEYBOARD_MONITOR_ENABLED=1`, retain two replicas/map/static-ELF checks and the
existing size ceiling, and publish it as `keyboard-monitor` with manifest
`production_entry=enabled-admission-v1`. All source/tool/library/license identities
must be retained. The current dispatcher/build default remains disabled; no
backend run or dispatcher edit is included here. Exact Dropbear disconnect
validation remains a required independent admission result.

## Checks performed and limits

Eleven native monitor methods pass after entry/fixture wiring. Five raw capture
fixtures pass: complete classifier integration, partial preservation, diagnostic
refusal, malformed export and default-off before I/O. All generated delivery,
capture and export shells pass syntax and ShellCheck (SC2016 excluded for awk
field expressions). Enabled entry and full-duration fixture compile natively;
neither was executed. No ARM64 enabled build, full-duration run, exact target
shell execution, live metadata proof, capture/export or device action occurred.


## Focused coordinator corrections after the initial handoff

The admission source identity now includes the eMMC launcher's own identity,
its exact selected source-pins inventory, the original baseline verifier's
transitive pinned members, and direct host-route/package-verifier sources.
Preparation and pre-effect checks reject drift in any of those inputs. A fixture
mutates an imported host helper and verifies refusal before claims or transport.
The fixed baseline source closure itself is not modified.

Signal trigger targets now precede the unchanged measured upper bounds:
TERM triggers at 209 seconds and must be measured by 210; KILL triggers at 213
and must be measured by 214. The original 202-second observation interval and
215-second final upper bound remain. One second of finite scheduling headroom
is reserved before each signal bound; it is not extra tolerance after a run.
Early cancellation may shorten cleanup, while scheduled expiry retains the
original final bound. Signal timestamps are sampled after the syscall returns.
Actual upper-bound misses still mark the lifecycle late and refuse acceptance.

Scaled fixtures use 280/360 ms triggers with unchanged 300/380 ms signal bounds
and 500 ms final bound. Normal forced cleanup stays within those bounds; a
fixture-only 40 ms pre-TERM delay crosses the hard bound and is explicitly
recorded late despite successful reaping. Twelve native monitor methods and six
capture/refusal methods pass; the latter also pass under optimized Python.
The first closure fixture run exposed source files being treated as private
mode-0600 evidence; reads now explicitly use the existing regular-source mode
while retaining type/symlink/size checks. No backend/full-duration/device run was
performed. The original accepted package, size and full-engine receipts remain
unchanged and are not relabelled as evidence for these changed source bytes.

## Coordinator integration review

The coordinator reviewed the coherent capture implementation from `6b409fbd`
and its closure/timing corrections from `a1d9ea30`. Independent execution of
six capture tests and twelve native monitor tests passed. Initial fixture
invocations lacked filesystem access to the worker temporary directory; after
authorized access, both suites passed without source changes. The mutation
fixture rejects changed imported helper bytes before a claim or transport, and
the delayed-signal fixture retains a late result despite successful reaping.

The integrated host gate and default monitor entry remain disabled. Existing
disabled ARM64 package receipts do not validate these changed source bytes.
Enabled ARM64 construction, full-duration timing, disconnect preservation and
authenticated device execution remain untested by this integration.

The integrated-tree capture and monitor suites also passed (6 and 12 tests).
The repository publication gate passed across 192 profiles with unchanged
grandfathered metadata debt of 37. Python syntax, local document links and
seven-file sensitive-text review passed. Linux-only artifact provenance remains
deferred to CI; no kernel, ARM64 userspace or device build/test was run here.
