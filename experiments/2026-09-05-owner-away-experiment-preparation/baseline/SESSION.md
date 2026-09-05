# First authenticated A53 baseline session

Status: **first session completed; budgets consumed; no repeat selected**.
The [attended outcome](ATTENDED_OUTCOME.md#first-physical-baseline-session) records
the successful observation/authentication/logging and confirmed Gemian return,
with an inconclusive native-request transport witness. This preserved protocol
does not admit another boot. Project Planning alone sends the owner the
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
The [host readiness handoff](HOST_READINESS.md) records saved host policy,
current interface absence and the concrete remaining local preparation.

| Phase | Maximum actions and duration | Evidence and stop condition |
| --- | --- | --- |
| Physical selection | One owner selection | Exact installed candidate from guarded receipt; no automatic retry |
| Baseline observation | One SSH command, 45 seconds | Exact live init/userspace hashes, kernel config, CPU/PWRAP/MMC metadata, console/map and boot ID; no partition-content or thermal-value read |
| `auth-checks` | One wrong key, one wrong host pin, one fresh positive probe; 15 seconds each | Expected rejection text, nonzero SSH status, no remote stdout; fresh positive confirms the same boot and userspace; any failure stops this phase |
| `preserve-log` | One separately admitted SSH command, 30 seconds | At most one pidfd signal and 10 seconds waiting for exit; already terminal loggers receive no signal; 3 MiB stdout and 16 KiB stderr bounds |
| `request-recovery` | One separately admitted SSH command, 15 seconds | Ordinary recovery requires verified local log preservation; emergency recovery requires the exact exception fields below; same boot and inherited reboot wrapper, no sync or partition operation |
| Known-good confirmation | One separately admitted SSH command, 15 seconds | Owner confirms physical recovery/availability; exact Gemian release and a boot ID different from both predecessor and mainline |

The first observation's 128 KiB stdout/16 KiB stderr and each transport's fixed
outer deadline include termination/reaping. Authentication has at most 45 seconds
of network time plus 10 seconds for local disposable key creation. Preservation
has a separate admission and 30-second budget. The logger starts during init and has a 600-second absolute deadline
and 2 MiB cap. Start capture promptly after service appears; finish sealing well
before that deadline. Waiting for an owner is not permission to extend it. If
missed, preserve partial evidence, recover, and review before selecting a new
attempt. A failed authentication phase does not prevent a separately reviewed
preservation admission. A timeout or disconnect never starts an automatic export,
recovery command or another SSH connection. Review the saved evidence before
admitting another phase. No test automatically repeats on disconnect.

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

- `action`: `auth-checks`, `preserve-log`, `request-recovery` or `confirm-recovery`.
- `baseline_admission_id`, `baseline_manifest_sha256`,
  `candidate_manifest_sha256`, `finish_source_sha256`, `steps_source_sha256`:
  hashes/identity of the reviewed prior capture and current scripts.
- `custodian_role`, `custody_handoff_sha256`, `custody_exclusive: true`,
  `no_other_device_operations: true`: the current coordinator's handoff.
- `action_budgets`: exactly `{"rejected_key":1,"wrong_host":1,"positive_probe":1}`
  for `auth-checks`, `{"log_export":1}` for `preserve-log`,
  `{"native_reboot":1}` for `request-recovery`, or `{"known_good_probe":1}` for
  `confirm-recovery`. Booleans cannot stand in for numeric budgets.
- `owner_console_accepted`: the actual owner observation, never assumed.
- `physical_recovery_confirmed`: false except for the separately admitted
  known-good confirmation after owner recovery/availability.
- `known_good_known_hosts_sha256`: null except for confirmation, which pins
  the preverified private known-good host file.
- `auth_checks_manifest_sha256`, `log_export_manifest_sha256`,
  `native_request_manifest_sha256`: all null for authentication/preservation.
  Recovery requests pin only the preservation manifest, mandatory for ordinary
  recovery. Confirmation pins all available prior phase manifests; an absent
  phase has a null pin. Every supplied phase is checked offline against its
  original admission, baseline/candidate/source hashes, claim, exact fixed
  commands, process records, raw evidence and complete private inventory.
- `recovery_mode`: null except for `request-recovery`, where it is exactly
  `ordinary` or `emergency`.
- `emergency_reason`, `acknowledge_unique_ram_loss`: both null for ordinary
  recovery and all other phases. Emergency recovery requires acknowledgement
  exactly `true` and one reviewed reason from the table below. False, numeric
  substitutes, unspecified reasons and extra fields are refused.

| Emergency reason | Required circumstance and evidence |
| --- | --- |
| `log-export-unavailable` | No independently verifiable local export phase is available: it was unsafe/unavailable to attempt, or its recorded inventory/admission cannot be verified. Pin the consumed attempt's manifest when available; this does not admit a retry. |
| `log-preservation-incomplete` | A pinned, independently verified export exists but cannot preserve every available regular byte or confirm a terminal logger. Examples include transport truncation, read errors, changed files and a bounded prefix. |
| `immediate-safety-stop` | The custodian has observed a session stop condition requiring immediate recovery; preserving logs would delay that response. This exception does not waive fixed identity/host/RAM checks or authorize other commands. |

The emergency acknowledgement records that native recovery may destroy unique
RAM evidence. It is a narrow recovery admission, never a full-baseline pass or
permission to retry an export. If the fixed native command cannot safely run,
use the established physical recovery path. A known-good confirmation remains
available after missing or interrupted prior phases, but their missing/failed
proof cannot produce a complete-baseline pass. The confirmation has its own
owner availability assertion and one probe budget.

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

The preservation phase always retains bounded separated stdout/stderr and
the process outcome, including on parser or transport failure. It decodes every
available completed file block into the exact private names `kmsg.log`,
`kmsg.status`, `kmsg.status.partial`, and `kmsg-exit`. Unavailable files have empty
local placeholders; only their accompanying parsed state distinguishes absence
from an available empty file. Each result records file type, before/after size,
captured bytes/hash, read/encoding outcome, stability and truncation, plus logger
terminal state before export, signal attempts, transport completion and preservation completion.
Files, directories and the final checksum manifest are flushed locally before
the next phase can rely on them. The original RAM evidence is never deleted.

`preservation_complete` requires complete framing and transport, a terminal
logger confirmed before reading the log, a complete regular log, and successful unchanged, untruncated capture
of every present regular file. Missing auxiliary files remain explicitly missing;
symlinks, nonregular/unreadable files, read/encoding errors, changed snapshots,
unconfirmed terminal state and capped prefixes refuse ordinary recovery. A
complete export of an already exited failed/deadline logger can satisfy this
preservation condition while its baseline log classification stays inconclusive.
The terminal witness is a canonical exit code from a held, verified regular
`kmsg-exit` descriptor before any export file is read. Final status or an exit
code observed only after the log copy cannot establish preservation: the logger
could have appended records in between. That case requires emergency recovery
even when the later file blocks are otherwise complete.

Seal acceptance additionally requires the single signal in this attempt, the atomically published status,
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
added. Complete logs/authentication, ordinary recovery, owner console acceptance, original baseline
serviceability and confirmed recovery together produce
`first-authenticated-baseline-and-recovery-pass`.

Original observations and prior phases are parsed from retained, hash-verified
byte snapshots. Classification never reopens a previously checked evidence
file, and collector preparation inputs must match the admitted snapshot.
Ordinary native recovery requires the preservation proof to pass again
immediately before the command; local evidence changes stop it. Emergency
recovery remains available under the narrow fields above after authentication
or preservation failure when the original baseline identity was established.
Neither path retries another phase or automatically starts after a failed SSH
command. If baseline identity or
USB never became attributable, stop network actions and use the owner's
established physical known-good recovery path. Unusual heat, charging anomalies,
reset loops, changed recovery behavior or an unreadable screen stop the session.
Only Project Planning may then issue a revised physical action card. The owner
never has to infer readiness from a build completion or these preparation files.
