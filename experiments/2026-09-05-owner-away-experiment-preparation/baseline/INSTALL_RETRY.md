# Corrected installation retry — finite handoff

Status: offline preparation only. The last authorized read-only check verified
the unchanged known-good Gemian boot with swap restored and SSH serviceability.
It does not authorize another deactivation or installation. The coordinator owns
admission, shared queue state and the central physical-selection notification.
No live work is performed by this handoff or scheduled coordination.

## Exact frozen inputs

| Component | SHA256 |
| --- | --- |
| `scripts/install-boot2.py` entry point | `78f3ade3a410055269183cc81fe243f46db77b2127f120a9d1d3ea5b41d867d3` |
| `scripts/installer.py` corrected adapter | `ef9cf896f9b62b903b7d16176b5da40096e54cc839c5001fd2f5047638f72a6f` |
| Locally derived corrected installer | `fb62efa6fc74840698f6a2538963262d3949ee1678ee6d23fb7708654cd5ad8d` |
| `scripts/temporary-zram.sh` alias-aware adjustment | `128e0728a9b520a0bdfa676a0b67cc915e140fb9a545b53b543afa3a3256ad4a` |
| Unchanged raw boot candidate | `a25fe4cb907f4f3da2bf9f36fcf38b3fff7d8ba84adc37562fdcff2f1a422daf` |
| Exact padded candidate | `a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821` |
| Candidate manifest | `54b07f0c70e77fd1e34fde4fc1c929980f0d8c3410f0a97ce3f15ffec1a66179` |

Reuse the existing private candidate, validated foundation, userspace package,
credentials and recovery backup. Do not reconstruct or replace candidate bytes.
The derived installer digest is bound to the current private input paths; a
relocation that changes it requires review, not a silent pin update. The existing
candidate validator and pinned historical derivation inputs remain mandatory.

## Admission and consumed budgets

All earlier claims and receipts remain immutable. In particular, the consumed
installation attempt and its `deployment-1` evidence directory must not be
removed, reused or treated as an unspent budget. The nonzero restoration receipt
and subsequent accepted canonical-alias reconciliation remain distinct evidence.
See [the attended outcome](ATTENDED_OUTCOME.md).

A future coordinator admission may allocate only:

1. One separately claimed alias-aware `ACTION=deactivate`, with a 30-second
   transport ceiling and 65536/8192-byte private stdout/stderr caps. Use a new
   `temporary-zram-deactivate-2/` receipt. Review its result before proceeding.
2. One corrected installer execution, only after verified deactivation and
   separate installer admission, under `installer-execution-2/`; its unique
   deployment receipt is `a53-authenticated-baseline-deployment-2`. The existing
   entry point bounds deployment to 360 seconds, then termination/reaping to
   another 25 seconds. It is one installer invocation, containing the reviewed
   ordered SSH operations, not one SSH connection.
3. At most one `ACTION=restore` under `temporary-zram-restore-2/` on a confirmed
   abort with no staging or writers left, using the same 30-second and output
   caps. If the deactivation's built-in handled-abort restoration already ran,
   that consumes the restoration allowance; do not issue a second restoration.

No automatic retry, missing-fact probe, independent test, physical boot or
reboot is included. An indeterminate result consumes its claim and ends the
admitted sequence; any reconciliation requires explicit bounded admission.

## Required predicates and sequence

Before any admission, custody is exclusive, the owner has not selected another
boot, and no competing device or memory-heavy operation is in progress. Preserve
unique evidence and reuse the verified project recovery backup. The exact origin,
source pins, private permissions, known-host trust digest, candidate validation,
new receipt paths and available tmpfs space must pass the existing checks.

The deactivation must freshly match the privately recorded Gemian boot, release,
architecture, init mount namespace, exact configured backing, utility hashes,
one unused swap entry and memory margin. Run those identity/active predicates
twice two seconds apart, then again immediately before the deactivation command.
Every sample must independently satisfy the unchanged zero-usage and memory
gates; no historical sample substitutes for a fresh one. Only the original and canonical
spellings resolving to that same backing are accepted. Its successful receipt
must show no active swap and preserved identity/memory. A changed boot or record
refuses; do not assume the earlier read-only observation is still current.

The corrected installer independently captures and retains its initial boot
identity, then requires it unchanged throughout its guards. No physical boot
selection is permitted between the admitted prerequisite and installation; the
coordinator must compare the resulting identity with the prerequisite receipt.
The existing entry point does not accept an externally supplied expected boot ID.

The ordered installer behavior is unchanged except for the reviewed root-owned
staging and pinned SSH trust:

- Validate candidate and sources locally; resolve logical boot2 from live GPT;
  require exact identity, inactive/unmounted target, size, writable state,
  stable power, no swap and unchanged known-good root.
- Record predecessor checksum. If already matching, skip upload/write and still
  complete the required validation, readback and shutdown evidence.
- Otherwise prepare one root-owned mode-0600 file on the exact tmpfs, stream the
  padded candidate through sudo, and revalidate file identity/size. Retain the
  exact candidate hash and fresh device/power/no-swap guards before writing.
- Write only the resolved boot2 target, sync and flush, require its full-partition
  checksum, clean staging, then perform independent full readback comparison.
- Validate the deployment receipt, request clean poweroff, and record the bounded
  shutdown/reachability result. Do not reboot or physically select boot2.

Only the coordinator issues a Ready-for-boot2 card after reviewing the complete
receipt. The first subsequent physical boot remains the authenticated A53
baseline only: unchanged kernel/DT/config, CPU0–7, attributable USB/log evidence.
Passing baseline/recovery permits separately admitted dependent tests; regression
rejects the candidate; missing or incomplete evidence is inconclusive.

## Abort and stop conditions

The [swap corrective protocol](SWAP_PREREQUISITE.md) remains authoritative.
A failure before deactivation changes nothing. A confirmed deactivation followed
by abort requires the one reviewed restoration, preserving format/configuration
and default priority. Confirm cleanup and absence of credential-bearing stage
writers before restoration; a cleanup error, timeout, missing framing, ambiguous
write, remaining stage or open descriptor stops the sequence for reconciliation.
Do not run restoration concurrently with an unresolved operation.

Canonical spelling alone is not a restoration failure when the reviewed
alias-aware verifier confirms the same backing and record. Any other changed
identity, unexpected usage/priority, serviceability loss, power anomaly or changed
boot stops the sequence. Do not reset/format zram, invoke vendor helpers, change
services, weaken a gate, substitute another partition or issue another toggle.
A failed readback or shutdown must never become a Ready notification.

Validation for these executable revisions is recorded in the attended outcome:
38 actual remote gate cases, 11 stage cases, nine host installer tests and six
alias fixture cases passed. This document adds no executable behavior. No retry
has run and no hardware support claim is promoted.

The sampling correction passes eight inert sequence cases: exact two-sample /
two-second wait / immediate-check ordering, plus refusal at each identity/active
gate or the wait. No refused sequence reaches the inert mutation marker. The
six alias cases also pass (two methods, 0.052 seconds); Bash syntax and ShellCheck
pass. These fixtures execute only the extracted predicate/sequence, never a
device command. The correction does not itself consume or admit a live action.

## Integration review and first action

Project Planning accepted the corrected staging source and this finite retry
protocol during direct continuation of the owner's request for regular device
tests. It independently reproduced all eight sampling-sequence and six alias
cases in 0.053 seconds; Bash syntax and ShellCheck passed. The sampling source
identity in the table above is unchanged by integration.

Only the one prerequisite deactivation is initially admitted. The custodian
must return its immutable outcome for review before the installer is admitted.
This is not a physical boot request or evidence that boot2 has been written.
All failure and restoration limits above remain in force.
