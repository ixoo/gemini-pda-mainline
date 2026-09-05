# Attended baseline installation: integration assessment

Project Planning reviewed the private custodian receipts for the first attended
installation session. The frozen candidate has **not been written to boot2**.
Custody remains with A53 baseline and queued device tests; all live actions are
paused after an owner report of a boot2 start in another task. The current boot
must be clarified rather than inferred from earlier Gemian observations.

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
restoration or priority adjustment was performed. This describes the last
verified Gemian state, not the device state after the later boot2-start report.

The custodian retains the immutable private receipts below its ignored
`artifacts/a53-authenticated/attended-install-1/` directory, including
`installer-execution-1`, `staging-reconciliation-1`, `temporary-zram-restore-1`
and `swap-restoration-reconciliation-1`. Raw startup material and authentication
inputs are not republished. The integrator inspected the saved outcomes and
relevant streams; it performed no device access.

## Current boundary

Offline corrective work covers root-owned temporary staging, explicitly pinned
Gemian SSH trust with host-key updates disabled, and canonical backing identity
in restoration checks. Those changes need independent review and a fresh
admission. Owner boot clarification comes before any resumed live action.
No Ready-for-boot2 request, new image installation or runtime support is claimed.
