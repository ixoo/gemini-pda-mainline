# Wired one-read session — disabled pending final review

The tracked [launcher](collect-emmc.py) and [completion adapter](finish-emmc.py)
are source-only adaptations of the retained private drafts. The originals remain
unchanged private evidence. The complete runtime path now exists; no further
implementation or source relocation is needed to run the reviewed sequence after
explicit final enablement and actual session admission.

## Fixed dependency and execution boundary

Launcher admission adds exactly `prerequisite_selector` and
`prerequisite_phase_manifests`. `original-strict` requires null supplemental pins
and follows the unchanged strict verifier. `reviewed-supplemental` requires the
three exact prior manifest pins, runs the pinned supplemental verifier, then
reuses the original immutable snapshots to cross-bind candidate, deployment,
first/recovered boot IDs and admission. It retains the distinct supplemental
classification; there is no implicit fallback or rewritten baseline result.
Candidate/key preparation remains a separate validated local boundary.

All imported contracts, including selector, supplemental verifier, new recovery
parser and execution gate, are pinned in [source-pins.json](source-pins.json).
Launcher and completion admissions also bind their exact source identities.
The [session packet](SESSION_PACKET.json) records the currently disabled revision.
No private fallback source is loaded if tracked code is absent or changed.

Both CLI execution flags and callable dispatch paths invoke
[execution_gate.py](execution_gate.py). It raises unconditionally, before an
admission is read by a CLI or runtime context is used by dispatch. There is no
environment override. Tests replace the gate only inside fixtures that also
forbid process creation and replace every transport. Dry-run validates inputs
without consuming claims or making connections.

[ENABLEMENT.patch](ENABLEMENT.patch) is the exact unapplied final-review diff:
it changes the one gate to return, updates its source pin and the resulting
packet identities, and marks the packet enabled. It does not supply custody,
power, physical selection, a new boot or any admission. Applying it requires
coordinator review; this assignment has not applied it. Subsequent admissions
must bind the enabled identities, not the current disabled ones.

## Complete invocation and input contract

Use `collect-emmc.py --admission PRIVATE_JSON` for local validation and add
`--collect` only after final enablement and admission. The exact admission fields
are the launcher's `FIELDS`, fixed budgets are `BUDGETS`, and reviewed evidence
bindings are in SESSION_PACKET. Fill the new admission UUID and actual custody,
physical selection, power and handoff fields only from the coordinator's new
session. The candidate/deployment remain unchanged; no rebuild/reinstall is
part of this path.

One global observation claim is stored under the existing ignored
`emmc-readonly/attempt` root. Pre/read/post use the existing 45/40/45-second
transports and exact source-pinned scripts, live logger guards and one 16 MiB
input read. Source/prerequisite and host-key pins are rechecked before dispatch.
A second UUID cannot renew the consumed global attempt. Failure stops subsequent
observation phases and preserves the immutable raw record.

For completion, use `finish-emmc.py --admission PRIVATE_JSON`, adding `--execute`
only for the separately admitted phase. Its `ADMISSION_FIELDS` and `STEPS` define
exact fields and budgets. Bind the observation manifest, new boot, candidate,
source identity and owner/custody observations. Preserve-log requires stopped
observation transport; request-recovery requires a reverified preservation
manifest (or separately admitted explicit emergency fields). Confirm-recovery
requires actual owner return, pinned known-good trust and available prior phase
manifests. The existing 30/15/15-second budgets, full-log/controller-error checks,
changed-ID rules and incomplete-versus-complete result distinctions remain.

## New-session native recovery interpretation

[recovery_v2.py](recovery_v2.py) is used only by these new eMMC adapters. The
original baseline session source and closure are untouched. It requires the
complete expected same-boot request frame plus exactly one announcement emitted
by the pinned wrapper. Missing, duplicated, modified or extra output refuses.
Complete stdin, empty stderr, exit 255 and no transport failure reason remain mandatory;
timeouts and interruptions are not promoted. The remote recovery shell is the
unchanged original generator. A future timeout remains incomplete and requires
review; prerequisite supplemental acceptance does not waive this new phase.

## Validation and limits

The 17 launcher and 20 completion tests pass, normally and with Python optimized.
They exercise exact pre/read/post ordering, consumed claims, refusal, transport
failures, stored-result/snapshot substitution, late controller errors, partial
log preservation and independent recovery decisions. Two focused boundary tests
verify unconditional disablement and exact new wrapper output with timeout and
malformed-output refusals. The real accepted supplemental archive and retained
candidate cross-binding also pass offline through the wired launcher.

No actual device operation, kernel/backend build, candidate change or readiness
promotion occurred. Tests do not establish performance or hardware support.
Coordinator review of the exact enablement diff and actual new session facts is
the remaining execution gate; the runtime code itself is complete.

Coordinator stderr review correction: the completion adapter now explicitly
requires empty stderr before interpreting native-request success. A valid exact
stdout frame and exit255 with diagnostic stderr is inconclusive; raw stdout,
stderr, process and consumed claim remain preserved, and a second attempt refuses.
The completion suite now contains 21 cases. Updated completion/source packet
identities and the unapplied enablement diff include this correction.
