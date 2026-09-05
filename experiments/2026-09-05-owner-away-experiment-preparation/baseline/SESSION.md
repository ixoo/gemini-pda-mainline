# First authenticated A53 baseline session

Status: **preparing, unselected, no device admission**. This is an operator
protocol and handoff draft. Project Planning alone sends the owner the
“Ready for boot2 — action needed” card, after its selected candidate has a
verified guarded installation, full-partition readback and clean-shutdown
receipt and the queue is `waiting-owner-boot`. A userspace build, candidate
assembly or this document does not request a physical boot.

## Hypothesis and attributable outcomes

The exact [historical foundation](BASELINE_AUDIT.md), with only the reviewed
RAM userspace delta, supplies authenticated USB administration while tty1 stays
readable and complete kernel records are retained separately through an explicit
seal. CPU0–7 stay online; CPU8/9 remain present/offline. The new independent
observation path is key-authenticated SSH plus a sequence-checked RAM log,
replacing the inherited open shell and automatic input reader. Image, composed
DT and resolved configuration must remain byte-identical to the historical
runtime-proven package.

A console/auth regression rejects this userspace candidate. Missing USB,
partial output, missing early log records, a deadline, failed logger exit or
unconfirmed recovery is inconclusive and consumes its attempted action. It is
not evidence that the historical kernel stopped booting. A complete first
baseline and changed-ID known-good recovery permit independent keyboard and
read-only eMMC packets on subsequently admitted matching inputs; ten cold boots
are not their prerequisite. Their own launchers, contracts and budgets must
also pass review. Neither dependent packet runs during this first baseline.

## Exact preparation gates

The current candidate identity and build evidence belong in
[PREPARATION_RESULTS.md](PREPARATION_RESULTS.md). Before requesting admission,
validate the private candidate with `scripts/validate-candidate.py`, including
its exact inherited kernel/DT/config, complete initramfs member delta, static
ARM64 userspace, authentication options, exact-shell tests, private credentials,
LK header and 16 MiB zero padding. Credentials and the entire host-key-bearing
image stay under ignored access-restricted artifacts. Never attach them to Git
or a public issue.

The [installer](scripts/install-boot2.py) defaults to validation without SSH.
Its private generated adapter binds `candidate.json` and the padded digest,
uses the current shared device guard twice, resolves live GPT `boot2`, and
requires inactive target/root, stable power and complete readback. Secret image
staging is limited to the exact `/dev/shm` tmpfs with no active swap, verified
ownership/mode/size/hash and bounded cleanup. A matching partition is skipped.
No alternative partition, automatic reboot, new backup or persistent-root
staging is admitted. The installer finishes with clean shutdown; the owner
physically selects the candidate only on Project Planning's later card.

## First-boot action budget

No operation starts merely because a host or device becomes reachable.
Custody and explicit phase admission are recorded before transport begins.
The direct USB host interface must already have its reviewed `10.15.19.1/24`
configuration. The device binds only `usb0`, `10.15.19.82:22`; fixed private
host-key verification rejects a different endpoint. No DHCP, route changes or
network configuration are hidden in these capture commands.

| Phase | Maximum actions and duration | Evidence and stop condition |
| --- | --- | --- |
| Physical selection | One owner selection | Exact installed candidate from guarded receipt; no automatic retry |
| Baseline observation | One SSH command, 45 seconds | Exact live init/userspace hashes, kernel config, CPU/PWRAP/MMC metadata, console/map and boot ID; no partition-content or thermal-value read |
| Negative authentication | One wrong key, one wrong host pin; 15 seconds each | Expected rejection text, nonzero SSH status, no remote stdout |
| Fresh positive probe | One SSH command, 15 seconds | Same boot and exact relevant userspace after both refusals |
| Log seal/export | One SSH command, 30 seconds | At most 10 seconds waiting for logger exit; 3 MiB stdout and 16 KiB stderr bounds |
| Native recovery request | One SSH command, 15 seconds | Same boot, exact inherited reboot wrapper, one request; no sync or partition operation |
| Known-good confirmation | One separately admitted SSH command, 15 seconds | Owner confirms physical recovery/availability; exact Gemian release and a boot ID different from both predecessor and mainline |

The first observation's 128 KiB stdout/16 KiB stderr and each transport's fixed
outer deadline include termination/reaping. Authentication plus sealing is at
most 75 seconds of network time plus 10 seconds for local disposable key
creation. The logger starts during init and has a 600-second absolute deadline
and 2 MiB cap. Start capture promptly after service appears; finish sealing well
before that deadline. Waiting for an owner is not permission to extend it. If
missed, preserve partial evidence, recover, and review before selecting a new
attempt. No test automatically repeats on disconnect.

The console acceptance is the owner's observation of a readable status screen
and absence of command interpretation. Software `console.status`, foreground
VT, map verification and zero kernel VT-console count supplement that observation;
they do not replace it. This first boot requests no typed input, extra load,
thermal samples, storage-content read or CPU8/9 admission.

## Operator commands and admission records

[`COLLECT_BASELINE.md`](COLLECT_BASELINE.md) owns the exact first-observation
admission schema and usage. A successful capture is only
`baseline-observation-only-pass`. Its immutable private directory records the
claim, deployment/candidate/admission copies, exact command, separated streams,
process result and checksum manifest. The claim is recorded before SSH.

The finishing helper is also offline by default:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/finish-baseline.py \
  --baseline-attempt "$PRIVATE_BASELINE_ATTEMPT" --admission "$PRIVATE_PHASE_ADMISSION"
```

Only the admitted custodian adds `--execute`. Each phase has one fixed directory
under ignored `artifacts/a53-authenticated/sessions/<baseline-admission-id>/`;
existing, failed or interrupted phases refuse another execution. The exact
phase admission has schema 1, experiment `a53-authenticated-baseline`, and:

- `action`: `auth-and-seal`, `request-recovery` or `confirm-recovery`.
- `baseline_admission_id`, `baseline_manifest_sha256`,
  `candidate_manifest_sha256`, `finish_source_sha256`, `steps_source_sha256`:
  hashes/identity of the reviewed prior capture and current scripts.
- `custodian_role`, `custody_handoff_sha256`, `custody_exclusive: true`,
  `no_other_device_operations: true`: the current coordinator's handoff.
- `action_budgets`: exactly the matching fixed dictionary in
  [`finish-baseline.py`](scripts/finish-baseline.py); booleans cannot stand in
  for numeric budgets.
- `owner_console_accepted`: the actual owner observation, never assumed.
- `physical_recovery_confirmed`: false except for the separately admitted
  known-good confirmation after owner recovery/availability.
- `known_good_known_hosts_sha256`, `auth_seal_manifest_sha256`,
  `native_request_manifest_sha256`: null for the first two actions. For
  confirmation, pin the preverified private known-good host file and available prior
  phase checksum manifests; an absent prior phase has a null manifest pin. A
  known-good probe remains available after interrupted request capture, but
  missing/failed request or authentication/log evidence cannot
  produce a complete-baseline pass.

The Gemian key remains `artifacts/credentials/gemini_ed25519`. Its reviewed host
pin must be prepared offline in private
`artifacts/credentials/a53-recovery-known_hosts`, for `192.168.1.50`. Do not learn
that key from an unauthenticated network scan. Strict host checking, disabled
agent/config/proxy forwarding, and one connection attempt apply to both hosts.
Raw transcripts and accidental owner input remain private pending field-by-field
sanitization. Publish only reviewed candidate/receipt hashes, boot IDs, bounded
counters and classifications.

## Sealing and recovery semantics

`kmsg-capture` exclusively creates its RAM log/status, requires sequence zero
and contiguous records, and marks every gap, overflow, limit and I/O error.
A separate fixed-path `kmsg-seal` opens a Linux pidfd, verifies that the referenced
process executes the installed logger, and signals through that process handle.
It never sends a signal by a reused numeric PID. Failure/unsupported pidfd means
refusal. Both seal and recovery claims first require a unique RAM root and
`/run` tmpfs, real private `/run/a53`, and no swap. They do not mount or repair
anything.

Seal acceptance requires complete transport, the atomically published status,
logger exit code zero, independent record/count/byte validation and the raw
log's hash. It proves coverage through the explicit seal, not messages created
later during recovery. A deadline or missing final status never counts as clean
logs. Injected syscall fixtures test control flow; they do not establish actual
Linux/device behavior. Physical evidence is still required.

The native recovery command uses the inherited hash-pinned `/bin/reboot`
wrapper, which invokes BusyBox `reboot -n -f`. The exact request frame followed
by SSH disconnect means only `native-recovery-requested`. It does not prove
that Gemian returned. One separately admitted known-good probe must show
`3.18.41+`, `aarch64` and a changed boot ID. No post-recovery partition read is
added. Complete logs/authentication, owner console acceptance, original baseline
serviceability and confirmed recovery together produce
`first-authenticated-baseline-and-recovery-pass`.

Recovery is still available after negative-authentication or log-seal failure
when the original baseline identity was established. If baseline identity or
USB never became attributable, stop network actions and use the owner's
established physical known-good recovery path. Unusual heat, charging anomalies,
reset loops, changed recovery behavior or an unreadable screen stop the session.
Only Project Planning may then issue a revised physical action card. The owner
never has to infer readiness from a build completion or these preparation files.
