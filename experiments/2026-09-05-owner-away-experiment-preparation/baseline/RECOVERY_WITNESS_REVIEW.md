# Supplemental recovery verification with original archive closure

The coordinator accepted the limited supplemental criterion: authenticated
baseline/authentication/complete log, exact same-boot request frame and pinned
wrapper announcement, owner-observed return, and independent changed-ID Gemian.
This permits preparation of dependent tests; it does not admit their execution.
The original request remains inconclusive and the original whole-session result
remains `recovered-with-baseline-incomplete`.

## Original source retained

The attempted in-place wrapper-output parser correction would invalidate the
original seven-file source closure and phase admission hashes. It is withdrawn:
`session_steps.py` and its tests are restored byte-for-byte to their original
versions. No original source pins, admissions, manifests or results are changed.
The original strict aggregate verifier still refuses the actual archive with
`native request/SSH disconnect unconfirmed`.

A future parser revision must use a separately versioned execution/verification
path while retaining this original closure. Repointing historical admissions or
repinning their source hashes is not a migration strategy. No future parser or
new device protocol is introduced here.

## Narrow separate verifier

[`supplemental_recovery.py`](scripts/supplemental_recovery.py) pins the original
aggregate verifier itself, which validates the original seven-file source closure
before importing any original evidence-processing helpers. It uses their exact
inventory, private-file, manifest, snapshot, command, claim, admission, baseline,
authentication, log and known-good parsers. It never calls a transport or opens
candidate images or credentials.

The caller must supply independently reviewed candidate/baseline/confirmation
and all three prior-phase manifest identities. The supplemental verifier requires:

- Original raw baseline and authentication reparsing to pass, complete log
  preservation and exact ordinary-recovery admission/command identities.
- The exact complete same-boot recovery frame followed by the one exact
  announcement of the hash-pinned wrapper; no extra, missing or changed bytes.
- Complete stdin, empty stderr, exit 255, the exact `outer-timeout` reason and
  elapsed time in the original 14–15-second termination window. Arbitrary
  timeouts, interruptions, early failures and successful requests are outside
  this narrow supplemental case.
- The unchanged stored inconclusive request result and original parser refusal.
- Both owner console acceptance and physical-return observation in the bound
  confirmation admission, all matching prior manifests, exact known-good probe,
  clean confirmation process and a boot ID different from both earlier boots.
- The unchanged final incomplete-baseline result and a final source/inventory
  recheck. The original full-eligibility predicate must remain false.

Only then does it return
`supplemental-authenticated-baseline-recovery-verified`, with the original
classifications preserved, `orderly_ssh_disconnect_proven=false` and
`dependent_admission=false`. This is a separate evidence result, never an original
whole-session pass. The announcement precedes reboot invocation; the combined
proof establishes requested recovery followed by independently verified return,
not the missing SSH-disconnect witness or exact reboot instant.

## Validation and actual archive demonstration

Four synthetic test methods exercise a valid distinct supplemental proof and
refuse changed output, wrong boot, malformed/truncated announcement, arbitrary
transport reasons/status/timing, incomplete stdin, missing owner observation,
failed confirmation, incomplete authentication/log evidence, changed source
bindings and independently pinned manifest mismatches. Semantically mutated
fixtures refresh their manifests so refusal is not merely a checksum mismatch.
The tests pass in 0.527 seconds. All 24 original aggregate tests also pass in 1.354 seconds; no archive fixture
rewrites production evidence.

On the actual immutable session, an offline read using the coordinator-reviewed
bindings independently demonstrated both results: original strict aggregate
refusal and the distinct supplemental verification. These outputs are stored
separately from the original attempt/session under the private attended archive's
`supplemental-offline-review/`. No device connection, repeat boot, candidate
change, eMMC enablement or readiness promotion occurred. The coordinator owns
any subsequent preparation or admission decision.
