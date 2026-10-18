# D1: retain the existing SSH failure acquisition, unchanged C10 image

Predeclared after the [three-run C10 baseline](CCMP10_BASELINE.md). No new kernel
candidate or build. C10 SSH passed twice and failed once; C11's observer is not
required for an SSH failure. Failure-stage classification precedes driver changes
or longer sessions. GTK delivery, rekey, reuse and reconnect remain disabled.

## Hypothesis, observation and decision branches

Hypothesis: the failed exchange stops before an accepted server connection,
rather than completing TCP and failing KEX/auth. The sealed failed runs show
listener startup/termination without an accepted connection, but the client
stderr acquisition was discarded. This is insufficient to label TCP failure.

One bounded diagnostic retains stdout and stderr from the existing single Wi-Fi
SSH process, its return code or existing timeout, and host monotonic start/end.
Keep the exact command/options, ConnectTimeout, outer timeout, readiness checks,
boot/listener/lease/ACTIVE binding and guarded ACK. No verbosity option, extra
SSH call, ping, packet capture, ARP mutation, register read or firmware analysis.
Raw outputs can contain network identity and stay ignored/private, mode 0600.
Public results report only independently reviewed stage/status/counts/timing.

- A client `connect to host ... port ...` error establishes a TCP-connect failure
  (timeout/refusal/routing must be distinguished from the actual error). Select
  bounded host neighbor/ARP/TCP observation next to distinguish missing address
  resolution from SYN/reply loss; do not infer crypto rejection or patch the driver.
- A banner/KEX or host-key error establishes a later stage; correlate the sealed
  server events and checked RX/TX/credit chronology before selecting another test.
- An explicit authentication denial selects auth diagnosis. A valid SSH exchange
  with wrong boot/listener/lease/mode remains rejected, without ACK.
- Success or an unclassified error leaves the intermittent failure's exact stage
  unresolved. Record it as such; no automatic retry, timer extension or claim that
  the failure is fixed. Any further run requires a decision-changing observation.

After the stage is established, test the relevant path: legitimate frame rejection
at PN/crypto gates, TCP stalls/drops, RX or credit accounting. Existing C10 drop
counters bypass the checked path; unknown classes are not zero discards. Do not
attribute the SSH failure to withheld group traffic without evidence. Staged
60 s / 2 min / 10 min operation remains the next sustained milestone, not a reason
to extend an unexplained timeout.

## Scope and admission

Use the exact retained C10 candidate and original leaf/capture/session/recovery
workflow. A new host adapter selects only an output-retaining helper. That helper
calls the original actual-source state machine with an observing subprocess
runner. USB probe/ACK calls pass through unchanged. Only the Wi-Fi process's
stderr destination changes; stdout bytes returned to the original verifier are
unchanged. Output-file creation can affect host scheduling, so D1 is a diagnostic,
not a fourth unchanged baseline sample.

One custodian, new evidence root, fresh boot identity, one capture/session/helper
attempt, unchanged driver frame/byte/grant/wall/deadline gates, seal before reviewed
return and independently verify changed-boot Gemian. No re-arm or reconnect, so
another owner physical boot2 selection is required. Matching boot2 must not be
rewritten; retain full-readback/shutdown gates and stop at the physical handoff.
Do not execute D1 before focused actual-source tests, host preparation and a
reviewed handoff. This document specifies the observation, not a runtime result.

## Host implementation validation

The [session adapter](laptop-session-ccmp10-ssh-observe.py) replaces only the
owned helper executable path, preserving spawn options and parent ownership.
The [output observer](laptop-wifi-ssh-observe.py) pins and imports the original
CCMP and Phase-B helpers; it never decides whether to authenticate or ACK.
Seven [actual-source cases](tests/ssh-observation-test.py) pass locally: correct
identity/ACK, retained nonzero output without ACK, stale boot/mode/ACTIVE
rejection, closed-window rejection, existing timeout propagation, occupied
observation refusal and second-attempt refusal. These test host behavior only.
No kernel, firmware enforcement or D1 runtime result is claimed.

## D1 verified preparation — await physical selection

Published host input `4fe87eb8`, repository checks and seven actual-source tests
passed. Exact original C10 kernel input, image, candidate receipt, leaf, capture
and recovery sources remain unchanged. No Buildbox or local kernel compilation
was requested or performed. D1 is not a fourth unchanged baseline run.

Fresh known-good identity was independently verified as Gemian 3.18.41+/aarch64,
boot `38038581-a960-46ee-a6e3-06121192308e`. The original reviewed 603-line
installer is byte-identical under identity/path/hash substitutions only; Bash
syntax and ShellCheck passed. Derived shell SHA-256
`ba753a142c4d05b736568aad5f7bbac35ae651867aab82a04e12d690b2424f4b`.
Guard source remains
`0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf`.
One invocation verified C10 already matching, skipped the partition write,
and independently read back/byte-compared all 16 MiB against
`73e1ac21860e69f6e8f03fd3625022bd8d4c8e6f189c17ecc44d40f91066ed8d`.
Clean shutdown and unreachability confirmed; no automatic reboot or new backup.

The actual 925-byte deployment summary, SHA-256
`135e6d5d242bf2f0fc4cf8f2da2a1bcf89037202f75119f91089bb9de1a8d709`,
was seal-verified and copied byte-exact/mode 0600 into the new D1 session root.
Complete offline preparation through the new session adapter passed with helper
key/boot environment unset. An earlier offline invocation supplied an invalid
false-valued execution flag; argument parsing refused it before device action,
and its log is preserved. The corrected invocation omitted that flag. No
capture, helper, observation or execution claim exists; the session contains
only its deployment summary.

Required owner action: physically select boot2 with USB connected to the
custodian laptop and report startup. Stop until that action. Then verify the
fresh mainline identity and unchanged C10 installation provenance; execute one
original C10 capture and one D1 session, under all original limits. Include the
private observation directory in the pre-recovery seal, verify helper/device
quiescence, then perform the reviewed return and independent changed-boot Gemian
confirmation. Record any failure separately; do not retry silently.
