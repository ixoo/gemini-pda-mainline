# Native recovery witness — parser correction and supplemental assessment

Status: offline review proposal. No device connection, repeat request, new boot,
candidate change or readiness promotion is authorized. The original request
remains inconclusive and the original whole-session result remains
`recovered-with-baseline-incomplete`.

## Exact future parser correction

The existing hash-pinned reboot wrapper emits one announcement after the
collector's complete request frame and before invoking BusyBox reboot. The old
parser expected only the frame, so even an otherwise clean SSH disconnect with
the real wrapper output would fail. The corrected parser requires the exact
frame followed by that one exact announcement; missing, modified, duplicated,
truncated or extra output refuses. The immutable historical wrapper bytes were
read offline and their digest independently matched `REBOOT_SHA`; the expected
announcement was checked against those bytes. No wrapper or generated remote
recovery shell changes.

Transport requirements remain unchanged: complete stdin, exit status 255 and
no transport failure reason. An outer timeout, interruption, helper return or
other status cannot become `native-recovery-requested`. Applying the corrected
parser to the saved raw request passes the output comparison but still refuses
its outer timeout. Original phase/source snapshots and results are not edited.
A future admission must pin the new parser source; historical phase review must
continue using its recorded original source and manifest identities.

Focused fixtures reject missing or duplicate announcement, changed announcement,
wrong boot, wrong wrapper hash, truncated output and extra lines. Existing tests
continue to reject timeout, incomplete stdin, normal return and wrapper-return
status. All 47 session-step tests pass in 28.978 seconds, including prior snapshot
and incomplete-recovery anti-promotion cases. The host-shell fixture suite also
passes all 61 generated seal/recovery cases, with intercepted effects and no
actual target signal/reboot; temporary fixtures were removed. Generated remote
shell identities are unchanged. Target pidfd behavior was not retested.

## Supplemental proof from this session

The preserved evidence can support a separate, explicitly supplemental statement:

- A complete same-boot request frame and the exact pinned wrapper announcement
  were received after authenticated baseline checks and complete log preservation.
- The owner subsequently reported the known-good screen had returned.
- A separately admitted authenticated known-good probe confirmed Gemian with a
  boot identity distinct from both the preceding Gemian and mainline boots.

Together these establish a requested recovery followed by independently verified
known-good return. They do not establish the missing orderly SSH-disconnect
witness, the precise reboot instant, or by themselves exclude every intervening
physical action. The announcement precedes reboot invocation and is not itself
proof that reboot completed. A 255 status caused by the local timeout is not an
independent disconnect observation.

A coordinator could accept those combined observations as supplemental recovery
evidence without another boot, if the acceptance criterion explicitly permits
owner-confirmed return plus the independent changed-ID probe. Such a record must
pin the existing baseline/auth/log/request/confirmation manifests and original
source identities, retain the timed-out request result verbatim, and label the
combined conclusion separately from the automated classifier. It must not write
`native-recovery-requested` into the old phase or forge a passing session result.
No supplemental acceptance or dependent-experiment admission is made here.

The current strict criterion still leaves the baseline incomplete. Root review
must decide whether the available supplemental proof is sufficient for its next
admission, or whether an independently justified future recovery observation is
required. The parser correction alone cannot answer that policy/evidence choice.
