# First authenticated baseline observation

This is the contract for [collect-baseline.py](scripts/collect-baseline.py).
Preparation only: no physical device operation or hardware observation has run.
The result is deliberately `baseline-observation-only-pass`; authentication
negative tests, log sealing, owner console acceptance and attributable recovery
remain separately admitted and classified. A passing result cannot mark the
baseline or either conditional successor ready.

## Fixed inputs and custody

The collector has one target: `root@10.15.19.82`, port 22, through the prepared
USB administration path. It changes no host route or interface. The candidate
is selected by its admitted raw boot SHA-256 under
`artifacts/a53-authenticated/candidates/candidate-<sha256>/`; credentials are
only from `artifacts/credentials/a53-auth/`. Candidate and credential directories
must be owned by the caller and mode 0700. Read private files must be mode 0600,
regular, non-symlink files under ignored paths. No credential is copied into a
capture or committed. The exact `known_hosts` digest must match `candidate.json`,
and it must contain only the fixed target's Ed25519 identity. The matching
`authorized_keys` digest is checked against the candidate.

The source-pinned historical observer and classifier are reused. The active
[deployment receipt adapter](scripts/deployment_receipt.py) reuses the reviewed
V4 block-identity parser, retargeted to this experiment and additionally bound
to the exact candidate manifest. It validates the padded candidate/readback
identity, current guard identity, observed root/target device numbers, power,
shutdown, and disappearance. No V4 observation budget transfers to this packet.

The operator supplies a private mode-0600 admission JSON, containing exactly:

```json
{
  "schema": 1,
  "experiment": "a53-authenticated-baseline",
  "action": "first-baseline-observation",
  "admission_id": "<new UUID>",
  "candidate_sha256": "<raw boot.img SHA-256>",
  "candidate_manifest_sha256": "<candidate.json SHA-256>",
  "deployment_receipt_sha256": "<deployment-summary.txt SHA-256>",
  "collector_sha256": "<exact collect-baseline.py SHA-256>",
  "custodian_role": "<current assigned custodian role>",
  "custody_handoff_sha256": "<reviewed current custody handoff SHA-256>",
  "custody_exclusive": true,
  "physical_selection_confirmed": true,
  "no_other_device_operations": true,
  "observation_budget": 1
}
```

These are operator attestations, not a mechanism that obtains physical custody.
The custodian must review the referenced handoff and confirm actual physical
selection before writing this admission. The candidate's immutable
`physical_admission=false` construction record does not authorize collection;
the separately reviewed admission supplies that decision. One first-baseline
observation is allowed per admission. Minting another ID is not permission to
repeat a consumed observation or to bypass a failure.

## Invocation and finite effects

The default validates local inputs and emits a dry-run summary. It creates no
attempt and makes no network connection:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/collect-baseline.py \
  --admission PRIVATE_ADMISSION.json \
  --deployment-summary PRIVATE_DEPLOYMENT_SUMMARY.txt
```

Only after physical selection and custody admission, add `--collect` to that
exact invocation. There is no configurable remote command, address, SSH tool,
credential path, retry, or CLI time/stream override.

Before any network access the collector exclusively creates the private
`artifacts/a53-authenticated/attempts/<admission_id>/` directory and records a
consumed claim, input snapshots and the exact generated observation shell. An
existing directory, including an incomplete or empty one left by interruption,
refuses. Partial evidence is retained; the helper never clears or restarts an
attempt. Do not remove attempt records to recover an action budget.

There is one noninteractive SSH connection, no ambient user/system SSH config,
no agent, no password/keyboard-interactive authentication, no host-key learning,
no forwarding, no proxy and no connection multiplexing. The SSH process group
has one 45-second outer deadline, including termination and reaping. Collection
stops early on either 128 KiB stdout or 16 KiB stderr saturation. Pipes are
drained separately and written incrementally to mode-0600 files. Interruptions
and early transport exits are inconclusive; they consume the one attempt.

The fixed remote shell performs no mount, storage/partition-content read,
storage write, thermal-value acquisition, CPU change, keypress test, load,
logger stop, reboot or shutdown. It hashes the declared initramfs members,
BusyBox and native reboot helper; checks the live kernel configuration digest,
stable boot identity, CPU policy, console status, active tty1, absence of a
tty0/tty1 kernel console, and one matrix input device; and queries the already
loaded VT map using `console-keymap-verify --verify`. It never invokes the
Unicode mode setter, map loader or preflight loader. Historical automatic
keyboard/unauthenticated shell helpers must be absent.

Between the added pre/post frames, the historical
[PWRAP observer](../../2026-09-04-mt6797-pwrap-reset-serviceability/scripts/remote_observe.sh)
is embedded byte-for-byte and executed once. Its existing MMC/regulator/sysfs
metadata and thermal-zone enumeration are retained. Those are not partition
content reads or thermal-value reads. The strict host classifier checks the
exact historical field inventory, log framing and shared boot ID before calling
the original `classify` function. Missing, duplicate or trailing records cannot
be promoted by that older parser's more permissive envelope handling.

## Evidence and meaning

The private attempt contains `claim.json`, `remote-observe.sh`, `admission.json`,
`deployment-summary.txt`, `candidate.json`, `stdout.txt`, `stderr.txt`,
`result.json` and `SHA256SUMS`. Failures during early persistence may leave only
the claim or attempt directory; that still consumes the attempt. On ordinary
process failure the partial streams and result remain available. Checksums and
the source/recovery identities belong in the sanitized experiment handoff;
review raw stream contents before publication.

`baseline-observation-only-pass` requires the complete error-free authenticated
capture, exact live member/configuration checks, stable mainline boot ID distinct
from the deployment's recovery OS ID, and the original PWRAP serviceability
predicate. A complete historical negative result remains
`baseline-observation-rejected`. Lost transport, changed boot, framing errors,
unexpected stderr, missing witnesses, limits or interruption are inconclusive.

Identity is based on the verified deployment plus matching reported kernel,
configuration and initramfs members. This is not hostile-device remote
attestation or a direct measurement of the live Image bytes. Software console
status and active VT do not prove visible pixels or readability to the owner.
No cold-boot reliability, storage reliability, thermal protection, A72 or full
keyboard claim follows. Separate log sealing and recovery evidence must be
reviewed before admitting dependent packets.

## Offline checks and remaining gates

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/test-collect-baseline.py
```

The 29 tests use temporary fake SSH executables and synthetic candidate/receipt
files. They open no network socket. They cover local gates, claim-before-process,
consumed-attempt refusal, both stream limits, timeout and SIGTERM preservation,
early exit, exact source embedding, frame corruption, console/map failures and
original classifier rejection. The generated shell passes host Bash syntax.
Temporary fixtures are removed on success/failure under the managed temporary
root (`GEMINI_TEST_WORK_ROOT` may explicitly select another root).

These fixtures do not execute the observation against the exact candidate's
BusyBox, Linux ioctls or live sysfs. The exact-BusyBox observation-shell fixture
and independent review remain required before conditional readiness. The
candidate package, deployment, first boot, visual console and later completion
phases still have their own gates. All device execution remains unselected here.

The internal `run_once` helper is shared with the separate fixed completion
phases. Those callers may supply their reviewed fixed stream ceilings; each
must establish its own exclusive immutable claim and admission before invoking
it. This internal composition point does not add a configurable user-facing
runner or authorize an extra connection.

The separate [session shell harness](scripts/test-session-shell.py) checks the
generated sealing and recovery scripts without target effects. Its exact source
pins must match before any fixture executes. The 61 cases cover identity and RAM
guards before the remote claim, duplicate and descendant mounts, symlinks,
existing claims, pre-exited failure/gap/cap/deadline/partial status, logger
refusal/timeout/failure, late termination, malformed exit records, replaced or
vanished files, malformed log evidence, and
the native helper unexpectedly returning. Every signal-helper/reboot call is
intercepted; direct numeric `kill` is refused. Ten deliberate proxy misuse cases
also prove the effect guards remain active with Python optimization both off
and on. The default uses the host shell:

```sh
PYTHONOPTIMIZE=1 python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/test-session-shell.py
```

For a separately selected exact userspace artifact, add `--busybox FILE --qemu
PROGRAM --work-root MANAGED_ROOT`. That mode executes the exact ARM64 BusyBox
shell and safe applets under QEMU; fixture-owned identity/status data and every
device effect remain intercepted. Neither mode proves Linux pidfd behavior,
logger/device operation, or a successful physical recovery. The single JSON
result distinguishes host-shell from exact-BusyBox execution and includes the
generated source digests and optimization level.

## Failed logger evidence export

The fixed `seal_script` now emits the strict `gemini-log-export-v2` envelope.
An already-published final status or exit file consumes the export claim but
causes no new signal. Otherwise the identified pidfd helper is invoked once,
followed by at most ten one-second waits. Failure or timeout still reaches the
bounded export. Nothing restarts the logger or repeats a consumed claim.

The envelope contains `kmsg.log` (at most 2 MiB), `kmsg.status`,
`kmsg.status.partial` and `kmsg-exit` (at most 8192 bytes each). It records missing,
symlink, nonregular, changed and unreadable paths without reading their contents.
For a regular file the exporter opens a held descriptor, checks its device/inode
against the non-symlink source before reading, and records sizes and identity
stability around the read. It streams a bounded prefix through base64 and records
read/encoding status and truncation. Only small read-status receipts are written
inside the exclusive RAM claim; no second multi-megabyte log file is created.

`parse_log_export` returns raw captured file bytes separately from its JSON
classification. Complete earlier file blocks remain available if a later block
or transport fails. The caller must retain the original stdout, stderr and
process record even when the parser cannot recover a file block. A failed or
pre-exited logger remains `log-export-inconclusive`, including when all its
evidence has been preserved.

`preservation_complete` requires a complete error-free transport and envelope,
a verified canonical exit record held and read before the first exported file,
a complete regular log, and every available file captured
without errors, changes or truncation. This is an evidence-retention predicate,
not baseline acceptance. `complete-log-through-seal` additionally requires this
attempt's successful explicit seal, the same earlier termination witness,
exact zero exit, absent partial status, and
the original strict final-status/contiguous-record predicate. The `parse_seal`
compatibility entry point returns its original tuple only for that complete
pass. Old seal envelopes are rejected.

A terminal status that appears after the log was read cannot prove that the
captured bytes include the final tail. The `terminal_before_export` header must
therefore be true for either complete preservation or acceptance. A final status
without an earlier valid exit file still has its bytes exported, but remains
insufficient for ordinary recovery admission.
