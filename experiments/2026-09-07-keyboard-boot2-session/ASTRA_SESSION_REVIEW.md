# Keyboard session safety review

## State-machine repair 4: accept the frozen offline runner repair

Review time: `2026-09-07T22:24:56Z`. Decision: **accept this bounded
state-machine repair for offline tooling only**. `disconnect.py` hash:
`9595b06a4821cfe155f8539037724e10e9a0e8bfa1beead9a5b90b2bdb4959db`.
All four frozen source hashes match; companions are unchanged.

The runner now latches command completeness at marker observation, unregisters
and closes stdin, kills the client group, and stops the current event batch.
The returned `stdin_complete` is exclusively the latched value. The exact prior
stdout-before-stdin selector counterexample now returns false, retains the
marker, closes stdin and performs no post-marker write. Normal complete-input
and deterministic unread-input cases also pass their expected tests.

The runner still returns the early-marker result rather than raising for that
condition, so `perform()` retains the process record and reaches independent
export before rejecting the incomplete transport. Stream-completeness and empty
stderr checks remain required on the success path. No acceptance weakening
remains in this scoped ordering repair. The existing default-off gate and absent
private-baseline blocker are unchanged; no physical proof is claimed.

Tests actually run: six disconnect and six prerequisite tests (pass, including
generated shell syntax/ShellCheck), four frozen hash checks (match), exact
mocked selector-order regression (pass). No network, device or build actions;
monitor/capture suites were not rerun by this reviewer. Handoff reached.
This section supersedes the revision-3 rejection for the new frozen runner;
all physical admission limits in the earlier offline acceptance still apply.

## Post-acceptance hardening review 3: early-marker acceptance race

Review time: `2026-09-07T22:22:15Z`. Decision: **reject the new runner revision**
at a concrete acceptance weakening. Frozen `disconnect.py` hash:
`fa208999699cebbbb269fd721b972e8d56dd3d80b277dfb48100dafd993ba7ca`;
all four supplied hashes match. The previous accepted revision remains history,
not approval of this changed source.

The runner now kills on an early marker and returns instead of raising, which
allows the independent export to be attempted. However, `stdin_complete` is
computed from the final `sent` count rather than command completion **when the
marker was observed**. The loop continues processing selected stdin events
after the marker-triggered kill. A subsequent write can change the final count
and erase the evidence that the marker was early.

Deterministic host state-machine reproduction: use a selected-event batch with
stdout first (exact marker while `sent=0`), then writable stdin accepting the
remaining command. The mocked client returns SIGKILL termination and empty
remaining streams. The actual runner returns `stdin_complete=true`,
`marker_seen=true`, `client_signal=9`, `elapsed_milliseconds=0`,
`_stderr_empty=true`, `_streams_complete=true`, classification
`deliberate-client-disconnect`. These transport fields permit passage despite
the required command-before-marker ordering being false. This is a scheduling
counterexample, not an observed SSH or device result; SIGKILL invocation does
not itself establish that pipe writes cannot succeed until process termination.

Minimal repair: latch command completeness at marker observation, before the
kill, and use that immutable fact in acceptance. Stop/unregister stdin there so
no later selected write can improve the result. Preserve the existing early
marker output and independent export behavior. Next discriminating check: the
stdout-before-stdin event batch must remain non-passing even if a subsequent
write could otherwise finish the command; normal complete-before-marker must
still pass. No reviewer repair attempted; hand back this conflict immediately.

Tests actually run: six disconnect tests and six prerequisite tests pass;
four frozen hash checks match; deterministic selector-order counterexample
reproduces the weakened acceptance. No network, device or build actions. The
bounded stream prefix remains retained and the final success path checks both
internal stream facts, but those properties do not repair the ordering defect.
Private-baseline blocker and default-off gate remain unchanged. This section
supersedes the current acceptance below for the new runner revision only.

## Disconnect-tooling repair 2: accept offline tooling only

Review time: `2026-09-07T22:17:40Z`. Decision: **accept the frozen default-off
offline tool**, not a physical execution or session admission. All four frozen
source hashes match. `disconnect.py` is
`34c286bb92e326203ebf5cfebcf93d7561111467254686ba7a378322f0d3d952`;
the unchanged companion hashes and package identity are in the JSON record.

The deployed process-identity mismatch is closed: generated command predicates
match the actual probe path and observer path, while executable predicates also
cover the probe's forked child and deleted executable names. Host execution of
the exact generated predicates passed six refusal cases and two controls. The
earlier `ignore`-mode correction remains intact.

The bounded source review establishes these offline properties:

- The first command delivers the fixture-only binary, uses `ignore`, and names
  no evdev/VT read path. The built-in child does not exec the keyboard observer.
- SSH is no-PTY with pinned authentication and no multiplexing. The runner
  requires the complete command to have entered client stdin before killing
  the local client group on an exact marker; semantic acceptance requires a
  marker-to-kill interval at most 100 ms and client SIGKILL termination.
- The remote wrapper retains outer exit after waiting for the monitor. The
  independent connection requires exit 2, scans bounded process/descriptor
  inventories and exports four bounded retained members. No remote evidence
  deletion is present. Local stream partials remain retained on refusal.
- Receipt publication follows raw-evidence verification, including exact
  retained bytes and the admitted terminal/reap lifecycle. Deadline,
  contradictory, incomplete or failed evidence is not a passing proof.
- Execution remains default-off before claims/transport. Source closure includes
  the tool, and the baseline dependency is checked before any later transport.

Tests actually run in this re-review: five disconnect tests (including generated
shell syntax and ShellCheck) and six prerequisite tests, all pass; four source
hash checks match; independent exact scan-predicate matrix passes. The owner's
reported monitor/capture suites were not rerun by this reviewer. No network,
device or build actions occurred. Tooling repair attempts reviewed: **2**.

Remaining physical uncertainty is intentional: actual Dropbear disconnect
delivery, child/monitor cleanup, inventory accessibility and resulting receipt
must be observed in a separately admitted exact-candidate run. The local marker
measurement is not itself a hardware liveness result. The exact private baseline
archive is still absent; published summaries do not replace it. Acceptance does
not authorize reconstructing that archive, enabling the gate, selecting a
candidate or admitting capture. Handoff reached. This section supersedes the
historical rejection decisions below.

## Disconnect-tooling repair 1: process inventory identity mismatch

Review time: `2026-09-07T22:14:42Z`. The mode repair closes the previous conflict:
`first_script()` now selects `ignore`, whose child ignores TERM and matches the
admitted HUP or forced-KILL outcomes. All four frozen source hashes match;
`disconnect.py` is now
`f7e9533816ca74e84bcca10b46f054389b1146780274bfa346523b3391099172`.

Decision: **reject at the first further concrete defect**. `export_script()`
rejects commands matching `*keyboard-disconnect-probe*|*keyboard-observe*`, but
the actual launched monitor command is
`/a53-keyboard-disconnect/probe /a53-keyboard-disconnect/run ignore`. Its forked
built-in child retains that argv as well. The process-name exclusion therefore
does not recognize the deployed probe it is intended to exclude. A host shell
test of the exact extracted `case` predicate with the exact launched command
returns success. The harmless child uses retained regular files, not evdev/VT,
so the descriptor filter is not a substitute for matching its process identity.

This does not assert that a process survived on hardware: retained outer-exit
and reaped-status checks are separate evidence. It establishes that the promised
independent process scan cannot enforce its surviving-probe rejection predicate.

Minimal repair: match the exact deployed probe/monitor identities, including the
built-in child retaining the monitor argv, rather than relying on the package
member basename. Add host refusal fixtures for those identities and a nonmatching
control. Next discriminating check: the exact current command must be rejected
by the generated scan. Stop here; later proof predicates remain unapproved.

Tests actually run: five disconnect tests and six prerequisite tests (pass),
four frozen hash checks (match), exact scan predicate reproduction (incorrect
acceptance confirmed). Tooling repair attempts reviewed: **1**. No device,
network or build actions; private-baseline blocker remains unchanged. This
section supersedes the current blocker below, preserving its history.

## Disconnect-tooling review: source/lifecycle conflict

Review time: `2026-09-07T22:10:57Z`. Decision: **reject offline tooling freeze
at the first concrete conflict**. This reviews the new default-off tool under
the work-item addendum, not another repair of the previously bounded verifier.
All four supplied source hashes matched; the exact hashes and package identity
are recorded in the companion JSON.

`disconnect.py:first_script()` explicitly selects probe mode `wait`.
`monitor.c` restores default signal dispositions in the child, and
`monitor-fixture.c` ignores SIGTERM only in `ignore`/`late-signal` mode. Therefore
monitor-only cancellation with a still-live `wait` child can legitimately send
SIGTERM, reap signal 15 and retain `kill_ms=-1`. In contrast, the frozen
`prerequisites.py` accepts only signal 1 with no monitor signals, or signal 9
with ordered TERM/KILL. The first-connection source and accepted lifecycle
branches conflict. This is a source-supported possible branch, not a claim
about which signals the physical Dropbear session will deliver.

Discriminating host check: change the positive retained-status fixture to
`signal=15`, `kill_ms=-1`, retaining bounded `term_ms=10`, `reap_ms=100`, and
recompute both status hashes. The verifier refuses `disconnect parsed
lifecycle`. The five disconnect tests and six prerequisite tests pass but do
not cover this selected-mode outcome.

Minimal repair: explicitly align the selected harmless fixture mode and the
permitted lifecycle outcomes. Either preserve `wait` and validate its bounded
TERM-terminal branch, or deliberately choose a mode whose signal policy
matches the intended forced-kill proof. Review that choice against the existing
proof hypothesis; do not silently loosen signal checks. Add a source-consistent
selected-mode acceptance fixture and contradictory timing refusals. Next
discriminating check is host-only; no physical proof is needed to resolve this
contract conflict. No repair attempted by this reviewer.

The first-command source uses only the fixture probe, not the production evdev
observer, and the execution gate is default-off. Review stops at this conflict:
live-marker causality, process/descriptor exclusion, partial retention and
later execution are **not approved**. The exact private baseline archive remains
absent as documented in [the protocol](DISCONNECT_PROTOCOL.md); recovering it
or separately reviewing a fresh chain is still necessary before any admission.
No network, device, build, gate enablement or candidate reconstruction occurred.
This section supersedes the current decision below, while retaining the earlier
bounded lifecycle repair acceptance as history.

## Repair attempt 2: accept the bounded lifecycle repair

Re-review time: `2026-09-07T21:41:45Z`. The frozen uncommitted verifier repair
now closes both reviewed counterexamples. It requires retained digest-bound
members and checks canonical timing/count values, reason/cancel consistency,
signal outcome, sentinel handling, bounded TERM/KILL/reap ordering and member
byte counts. The exact `600/700/100` rehashed contradiction is refused.

Acceptance is **only for this frozen offline lifecycle-verifier contract**.
No conflicting evidence remains within that bounded re-review. This is not a
physical-session admission, proof of Dropbear disconnect behavior, or permission
to enable capture. The physical proof is still to be acquired and classified;
its absence is not a defect in this repair. The existing package integrity
finding remains scoped to the earlier built package, not the uncommitted host
verifier. Exact reviewed repair hashes are in the companion JSON record.

Tests actually run: prerequisite suite (6 tests, pass); independent fixture
checks of both accepted HUP-terminal and ordered TERM/KILL branches, and eight
rehashed refusals (over-bound/reversed timing, noncanonical numeric text,
over-bound reap, disallowed signal, reason/cancel contradiction and negative
stdout count), all pass. No device action or build. Repair attempts reviewed:
**2**. Handoff reached; the historical rejection sections below are superseded
by this bounded acceptance, without approving their deferred session predicates.

## Repair attempt 1: reject contradictory lifecycle evidence

Re-review time: `2026-09-07T21:39:52Z`. Reviewed the uncommitted bounded repair
on the source revision below. The original all-null preservation counterexample
is closed: seven bounded evidence files are now required, digest-bound and
partially parsed. All six prerequisite tests passed.

The first remaining concrete defect is that `term_ms` and `kill_ms` are required
status keys but their values are never parsed or checked. A direct host-only
mutation of the new positive fixture set `term_ms=600`, `kill_ms=700`,
`reap_ms=100`, `signal=9`, `late=0`, updated both affected status hashes, and was
accepted. This contradicts both event ordering and `monitor.c`, which sets
`late` when signal times exceed the scaled probe bounds. A digest-bound file is
not sufficient if contradictory decision-bearing contents pass classification.

Minimal repair: parse the signal timestamps and validate their permitted
sentinels, timing bounds, ordering against reap, and consistency with the emitted
lifecycle outcome, using the exact monitor source. Add the reproduced rehashed
contradiction as a refusal fixture. Next discriminating check: this mutation
must fail while source-consistent lifecycle fixtures pass. Do not merely tighten
the receipt booleans. No physical proof is required to resolve this host defect.

Repair attempts reviewed: **1**. Stop at this first defect; no broader session
approval is issued. The prior package integrity result below is retained without
rerunning a build or claiming the uncommitted verifier repair is in that package.
Tests actually run for this re-review: prerequisite suite (6 tests, pass),
rehashed impossible-timing counterexample (accepted, defect reproduced).
No device access, shared-file edit or build occurred. The initial review below
is historical; this section supersedes its current blocker and attempt count.

Review time: `2026-09-07T21:33:56Z`. Route: Astra Medium, named uncertainty:
disconnect/process ownership admission. Reviewed source revision:
`93e2b8526daa683c2ba848011fac757a398a13dd`.

## Decision: reject session admission at the first concrete defect

The semantic disconnect prerequisite accepts a passing receipt with **all four
preserved evidence members null**. In
[`prerequisites.py`](../2026-09-05-owner-away-experiment-preparation/keyboard/prerequisites.py),
`disconnect()` checks receipt identities and asserted booleans, but does not
open or classify exported monitor/process evidence. Thus neither the digest nor
the `passed` classification establishes deliberate transport loss while the
probe was alive, terminal/reaped processes, or preserved partial output.
`verify()` passes only the receipt bytes to this function, not evidence files.

This is reproduced by the existing positive fixture in
[`test-prerequisites.py`](../2026-09-05-owner-away-experiment-preparation/keyboard/test-prerequisites.py):
its `preservation.members` values are all null and it is accepted. Independently
calling `disconnect()` on that fixture with its actual receipt digest and toy
package pins also returned successfully. This is a host-only counterexample,
not a device result or a forged admitted session.

## Minimal repair and next discriminating check

Bind the passing disconnect classification to bounded, retained evidence files
and their verified hashes. Parse evidence sufficient to establish the exact
session/probe identity, deliberate disconnect while the child is live,
terminal/reap outcomes and bounded complete reader inventory. Preserve all
available partials independently of classification; absent/insufficient proof
must not become `passed` merely because nothing more was available. Add a
refusal fixture for the current all-null positive case and mutations for missing,
changed, stale or contradictory evidence. A source-root digest and asserted
booleans alone do not repair the evidence chain.

Next check: the current counterexample must fail before any claim or transport;
an independently constructed complete evidence fixture must pass, with every
decision-bearing file mutation refusing. Then return the frozen repair for
session-safety review. Repair attempts in this review: zero; stopped at the first
defect, as contracted.

## Package integrity: passes, separately from device readiness

The [enabled-build receipt](results/enabled-build/receipt.json) names package
`0baad6b85ae68770b783245e2f1dcd7eeb4ef40d93c19e0b30e1f89f8adc3065`.
The retained package passed `buildbox_userspace.py:check_package`: exact
inventory, SHA256SUMS identity, each member checksum/type and provenance revision.
All receipt-listed member hashes, the monitor byte count and six source-input
hashes against the exact Git revision also passed independent local checks.

- Monitor: `4363a7d61d818bc443d5cfd76455ac38fc2cea35178d44a2dc81c229ff97b67f`,
  66672 bytes.
- Probe: `560d00ab80040b90fead5d0a5b2672ed633f62599aa483ff0a33be0fa74d3681`.

The package records enabled production entry and identical replicas. Its QEMU
fixture results remain build evidence, not physical Dropbear, VT or evdev proof.
This reviewer did not rerun the build, remote publication checks or QEMU tests.

## Ordering and remaining risks

Harmless same-boot disconnect proof followed by validated-receipt capture is the
intended ordering, but is **not admitted** by this review. Capture remains
execution-disabled. Do not enable it based on this packet or treat package
integrity as a session approval.

Review of later admission predicates stops at this blocker. The harmless probe
uses scaled fixture timing, so any later protocol must prove transport loss
occurred before probe completion. It cannot itself demonstrate real observer
VT restoration or physical keyboard operation. Production timing, logger age,
exclusive VT/input ownership, same-boot binding, power and recovery still require
the final exact session review and attributable runtime evidence. No new
observation budget or device action is granted.

Tests actually run: prerequisite suite (3 tests, pass); direct all-null receipt
counterexample (accepted, defect reproduced); local package/inventory and
receipt/source identity checks (pass). No device access, boot, keyboard capture,
process-disconnect experiment, kernel build or support claim.
