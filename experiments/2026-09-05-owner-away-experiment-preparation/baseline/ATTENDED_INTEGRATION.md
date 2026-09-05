# Attended baseline installation: integration assessment

Project Planning reviewed the private custodian receipts for the first attended
installation session. The frozen candidate has **not been written to boot2**.
Custody remains with A53 baseline and queued device tests. The owner clarified
that the device was still in Gemian; a subsequent explicitly authorized
read-only SSH check verified that state. Corrective preparation continues offline.

## Candidate and attempted installation

The raw candidate remains
`a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf`;
the 16 MiB padded image remains
`a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821`.
The kernel, DT, configuration and first-boot scope are unchanged.
[Preparation evidence](PREPARATION_RESULTS.md) and the [session protocol](SESSION.md)
remain the candidate and observation contracts. No baseline observation or
physical admission follows from this unsuccessful installation.

Initial preparation refused active swap before staging. Bounded read-only
inspection established one unused zram entry and ample memory, then examined
its startup ownership. The reviewed temporary deactivation passed. No vendor
startup helper was executed, and no swap format, size or persistent policy was
changed. The source-only [corrective proposal](SWAP_PREREQUISITE.md) records the
intended adjustment and restoration boundaries.

The unchanged derived installer, SHA-256
`c3621fbc7a037708b217551ede8f6ec5d9317529084f1876e784d195dcaa5b22`,
passed local candidate validation and its initial device guard, then returned
exit 2 during candidate upload. Its cleanup reported an unsafe staging path.
Source order and the retained streams place this refusal before invocation of
the guarded partition write. No write-phase, readback or shutdown receipt exists.
The disappearing staging file's cause is unresolved; session cleanup is a
hypothesis, not an established device fact. No unchanged upload retry is admitted.

## Cleanup and restoration

The separately admitted read-only reconciliation completed and found no file in
the exact candidate staging namespace and no matching open descriptor within
its bounded census. It deleted nothing. The synchronous installer and local
transport had exited. This supported a separately admitted restoration attempt.

That attempt returned exit 1 without a success marker. The subsequent read-only
reconciliation established the same backing device, configured size, zero swap
usage, original priority and utility hashes. The swap table reported its
canonical path rather than the original alias. Project Planning accepts the
observed restoration on backing-device identity; the original nonzero command
result remains preserved as an exact-spelling verifier refusal. No second
restoration or priority adjustment was performed. This describes the restoration observation; the later owner-authorized
verification below independently confirmed the same Gemian boot.

The custodian retains the immutable private receipts below its ignored
`artifacts/a53-authenticated/attended-install-1/` directory, including
`installer-execution-1`, `staging-reconciliation-1`, `temporary-zram-restore-1`
and `swap-restoration-reconciliation-1`. Raw startup material and authentication
inputs are not republished. The integrator inspected the saved outcomes and
relevant streams; it performed no device access.

## Independent correction review and current boundary

Project Planning reviewed the ten-file handoff through worker revision
`c747370c`, including the root-owned staging and pinned-trust changes from
`a6f9a7a4`. The earlier independent remote-shell run failed eight cases because
its ownership and command extraction fixtures still modeled the old transport.
The correction retains production guards and tests non-root ownership refusal;
it does not waive the staging gate. The [owning outcome](ATTENDED_OUTCOME.md)
records the correction and its limits.

The separate `owner-gemian-verification-1` private receipt completed with exit 0,
no stderr and no device mutations. Project Planning inspected its saved process,
classification and output: known-good release, unchanged boot identity,
authenticated sudo serviceability and the restored unused swap state were
observed. This resolves the ambiguous physical-boot report at that observation.
It does not imply continuing liveness or authorize replay of consumed actions.

Independent integration checks passed: 38 remote gate cases and 11 staging
cases in 4.119 seconds, nine host installer tests in 8.516 seconds, and six
swap-alias cases in 0.047 seconds. Changed shell sources passed Bash syntax and
ShellCheck; changed Python sources parsed successfully. These fixtures use
injected platform metadata and perform no device access. No kernel build was
needed for this host-tooling and evidence change.

The installer correction is accepted as host-tested preparation. The candidate
is unchanged; the corrected derived installer has its own deployment-2 evidence
identity. A finite retry handoff is being prepared, and no deployment occurs
from scheduled coordination. No Ready-for-boot2 request, successful installation
or new runtime support is claimed.
