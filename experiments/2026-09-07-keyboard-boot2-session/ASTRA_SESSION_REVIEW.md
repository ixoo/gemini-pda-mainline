# Keyboard session safety review

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
