# A30: recovery-status-only metadata observation

Design parent: `3a0b3ec2666cde9b147d8c090db714cab7fc4f40`, clean and
equal to `origin/main`. Astra Medium `/root/runtime_identity_specialist`
owns this design and is prospective sole recovery custodian. Sol Medium
reviews; `/root` integrates and owns the workflow ledger. Current ownership
is this amendment and minimal [WORK_ITEM.md](WORK_ITEM.md)/[inputs.json](inputs.json)
updates only. No VM access or observation occurs in this design dispatch.

## Frozen failure and non-attribution boundary

The separately dispatched [A29](AMENDMENT-29.md) transport attempt at the
design-parent commit exited 1 and returned zero collector records. Host
transport stderr was 645 bytes, SHA-256
`d0847a45eceba5bd361c424ece087577656f01462b68af053e9a5d899824fdcb`.
Those raw host bytes were not retained and are unavailable. No guest retention
locator, PID/start identity, boot/session identity, raw receipt or child-exit
confirmation was returned. Guest process/file/directory existence is unknown.
The exited host RE-shell process proves no guest-process exit.

The diagnostic budget is irrevocably
`spawn_attempts=1, consumed=true, runs_remaining=0, rerun_admitted=false`.
No new diagnostic process, source feed, candidate/interpreter execution, package
inspection, method/private payload access or diagnostic-result construction is
permitted. A29's current frozen design-state fields remain historical; A30's
new state record records the consumed attempt without rewriting A29/source.

Design-parent hashes are: inputs
`a19b24915828c1673693a83316ce0527751688acba089ee0873fbbd8f17f4681`,
work item `0d6b9a727df2b527dcd360b6265760dbb3e6d3da26471f5a8cd6338f1b20f58d`,
A29 `c1ae9b73e4311c7e4b5790c9b4befeaeb24bb51ef49b4c7dc4cffa899d16d46c`.
Preserve all earlier controls, candidate/source identities and A28.
Future dispatch/input/amendment hashes are recorded externally after publication;
no document hashes itself.

Without an independent attempt identifier, prefix, ownership, mode, apparent
age, process name, cwd or descriptor association cannot uniquely attribute a
match to A29. The owner selected **status-only inventory**, not a termination
or custody-closure procedure. Every outcome leaves A29 custody unresolved.
Zero matches is absence within one bounded visible observation, not proof
that a guest child never started, exited, escaped the expected root or exists
in no other namespace. No observation refunds either budget.

## Admission, access budget and observer boundary

Require independent review, publication and one separate explicit status-only
dispatch naming its exact commit. Before access, verify clean tracked/staged/
untracked status, `HEAD == origin/main == dispatch`, exact origin URL
`https://github.com/ixoo/gemini-pda-mainline.git`, all current dependency/control
pins and the historical snapshots above, without fetch/push. A mismatch stops.

Use only `./scripts/dev-vm re-shell`, once, with the named custodian; no
alternate transport. Recovery access has its own limit 1. A positively proven
absence of any transport API/syscall attempt means attempts=0, consumed=false,
remaining=1. Any actual or uncertain transport call consumes it:
attempts=1, consumed=true, remaining=0, even if no guest shell started.
No automatic retry, reconnect, second view or diagnostic restart follows any
outcome, including ambiguous transport.

The observer may use shell builtins and existing native metadata utilities;
no Python, other programmable-language interpreter, candidate, package probe,
installation, network, new executable, build or source feed. The status shell
commands are observer plumbing, not diagnostic source. Keep them in memory;
create no guest file, directory, marker, log, source or evidence copy.
Do not write the installed environment or touch immutable payload contents.

On entry, use only cwd metadata to leave the known immutable startup directory
and validate its parent as the existing guest-owned nonsymlink
`reverse-engineering` root. Never list or descend into the startup payload.
Check ownership/nonsymlink identity of the selected root; missing, changed or
unavailable identity is refusal, not a substitute root. Preserve exact root,
matched basenames and any process handles privately in the custodian's
access-restricted working record, never in a public result.

The complete observation has a 30-second deadline and a 65536-byte private
in-memory metadata ceiling. The host controls only its newly launched observer
transport; a deadline closes its observation pipes and marks status incomplete.
It must not send a signal to a discovered guest process or process group, use
pkill/killall, reboot the VM, or assume a disconnected observer exited.
Normal observer-command exit is allowed; forced quiescence is not.
If observer exit cannot be confirmed, report recovery-access exit unconfirmed
and stop. No second access to check that condition.

## Bounded metadata inventory

Pre-review the exact shell command sequence before the future access. Require
NUL-safe native streaming enumeration and bounded consumers; do not use a
shell glob, sorted listing, recursive traversal or an unbounded materialized
process/directory list. If the existing utilities cannot provide this bounded
route, refuse before observation rather than introducing an interpreter.
A stream/cap stop is incomplete, never a complete zero/one/multiple result.
These are observed-entry/byte/deadline bounds, not an exact filesystem syscall
trace or a general process-isolation claim.

Enumerate at most 256 immediate root entries, counting all names, not just
matches; the 257th entry stops as directory-cap. Do not stat nonmatches or
follow links. Select only names exactly matching
`inventory-diagnostic-a29.` plus six ASCII alphanumeric characters.
Treat malformed prefix-like names as a count-only anomaly and stop; do not
normalize, reinterpret or publish them. Preserve every matching object.
At most eight matching directory candidates may be examined; the ninth stops.
Zero/one/multiple is authoritative only for a fully completed enumeration.

For each selected entry, use lstat-equivalent metadata only: object kind,
owner-equals-observer Boolean and permission mode. Do not follow a symlink;
a symlink, non-directory or foreign-owned match is an anomaly and receives no
child inspection. For an owned real directory, inspect only the two exact
names `stdout.raw` and `stderr.raw` with no-follow metadata. Do not list
other contents. Record absent, regular, symlink, other or inaccessible; regular
files may report observed size/mode and owner-match. No open, read, tail, parse,
copy, content hash, xattr, ACL dump or raw-log output. If metadata changes
during the observation, record unstable and do not repeat it.

**File SHA-256 is unavailable:** it requires reading content and is forbidden
in this status-only scope. Every per-file content_sha256 is null. The earlier
host transport digest above is a frozen historical fact, not a recovered log
digest. Do not hash names, locators, PIDs or arbitrary metadata as a substitute
for content identity. Readable metadata never proves complete capture or
sole-copy preservation.

A single bounded process-metadata inventory may inspect at most 1024 visible
process records, with the 1025th stopping as process-cap. Select only records
owned by the observer UID with the native comm name `python3.12`.
Read only PID as a private temporary handle, UID equality, comm equality,
state class and start identity sufficient to detect handle reuse; no cmdline,
environ, maps, stacks, memory, executable content or full status dump.
For at most sixteen such records, inspect only cwd symlink metadata, and only
compare it to the already observed matching directory paths. Nonmatching cwd
records receive no further inspection. For matching cwd records, inspect
symlink metadata for descriptors 1 through 32 at most, counting links equal
to either observed raw-file path; do not open a descriptor or follow it to
content. Unknown targets become an aggregate count, never names or values.

Immediately recheck only the process start identity for that same handle;
a disappearance/reuse marks the row unstable, without a replacement process
lookup or retry. This is metadata consistency, not a liveness/exit guarantee.
An inaccessible cwd/start/descriptor record makes process coverage incomplete.
A matching cwd or raw-file descriptor is only **protocol-compatible
association**, not unique attribution, interpreter identity, diagnostic execution
or permission to signal that process. Keep reviewed-target candidates privately
for a possible separately authorized future design; never publish paths/PIDs,
start values or arbitrary process names. Never expand beyond these limits.

## Outcomes and decision boundary

The closed outcome tokens are:

- `preflight-refused`: no transport call attempted.
- `zero-matches`, `one-match`, `multiple-matches`: complete bounded root
  and process observation, counts 0, 1 or 2..8 respectively, no anomalies.
- `metadata-incomplete`: cap, deadline, permission, malformed name, symlink/
  ownership/type anomaly, racing identity or incomplete observer exit.
- `transport-failure`: transport error or missing/ambiguous status delivery.

Zero matches prevents selecting a directory target from this view. One match
provides one metadata-only candidate for future review, never ownership proof.
Multiple matches require explicit target disambiguation before any further
action. Compatible-process counts make the possible live-state risk visible;
zero compatible rows does not prove absence of a live child. Incomplete or
transport-failure results cannot select targets.

All branches preserve matches and report A29 custody unresolved. The next
decision belongs to the owner: retain unresolved status, supply an independent
attempt anchor, or authorize design of a broader, explicitly bounded quiescence
boundary against the privately retained candidate metadata. This observation
authorizes none of those actions automatically. It yields no final diagnostic
finding, valid child receipt, private-analysis admission or hardware claim.

## Future host records, schema and verification

Only after the status attempt ends may a separately dispatched worker construct
`recovery-status-v1.json`, `RECOVERY-STATUS.md`,
`verify-recovery-status.py` and minimal authorized work-item/input state pins.
These files are not created now. A recovery status record may truthfully retain
unconfirmed access exit; it is not A29's prohibited final diagnostic result.
No `inventory-diagnostic-result-v1.json` or diagnostic verifier is authorized.
Freeze result bytes/hash/UTC before writing its assert-free host verifier.
Sol independently reviews; `/root` integrates and owns shared/ledger edits.

The result has exactly these keys, with no extra keys recursively:

- `schema_version`: integer 1; `kind`: "a29-recovery-status-only".
- `binding`: exact keys `design_parent_commit`, `dispatch_commit`,
  `inputs_sha256`, `work_item_sha256`, `amendment_29_sha256`,
  `amendment_30_sha256`, `custodian`, `model`, `reasoning_effort`;
  actual published identities, named custodian, gpt-6-astra/medium.
- `diagnostic_budget`: exact keys `attempts` 1, `consumed` true,
  `remaining` 0, `rerun_admitted` false.
- `recovery_budget`: same four keys; only (0,false,1,false) for
  preflight-refused or (1,true,0,false) for every other outcome.
- `access`: exact keys `started_utc`, `completed_utc`,
  `deadline_seconds` 30, `transport_exit_code`, `observer_exit_confirmed`.
  Unobserved times/exit are null; UTC strings and integer exit codes only.
  Observer exit is null for never-started/unknown, true only when confirmed.
- `outcome`: one closed token above; `reason`: one of none, preflight,
  directory-cap, match-cap, process-cap, candidate-process-cap, byte-cap,
  deadline, root-identity, name-anomaly, object-anomaly, metadata-unavailable,
  unstable, access-exit-unconfirmed, transport. For complete outcomes use none.
- `observation`: exact keys `root_complete`, `process_complete`,
  `entries_examined`, `matches_observed`, `processes_examined`,
  `compatible_processes`, `directories`. Completeness fields are Boolean;
  counts are bounded integers or null if unavailable, never invented zeros.
  Directories is an array of at most eight sanitized rows, empty if none
  observed. Each has `index` (1-based observation order, not a locator),
  `kind` (directory/symlink/other/inaccessible), `owner_matches`
  (Boolean/null), `mode` (four octal digits/null), `files`,
  `compatible_process_count` (0..16/null), `stable` (Boolean/null).
  Files has exactly stdout and stderr, each with `kind`
  (absent/regular/symlink/other/inaccessible/not-inspected), `owner_matches`,
  `mode`, `size` (nonnegative integer/null), `content_sha256` null.
  Only observed regular-file sizes/modes may be nonnull; uninspected or absent
  values are null. No file bytes or arbitrary strings.
- `custody`: exact `a29_state` "unresolved", `unique_attribution` false,
  `closure_claimed` false, `mutation_performed` false.
- `decision`: zero-matches -> "no-target-in-visible-view", one-match ->
  "single-compatible-target-needs-independent-review", multiple-matches ->
  "target-disambiguation-required", all other outcomes -> "no-target-selection".
- `authority`: exact false keys `termination`, `deletion`,
  `content_read`, `diagnostic_rerun`, `private_analysis`, `device`,
  `build`, `hardware_support`.
- `frozen_utc`: actual host result freeze time after access returned or was
  declared interrupted; never implies guest exit.

The prose record states actual checks, observation limits, raw unavailability,
unresolved custody and the next owner decision. Keep the private correspondence
between sanitized row indices and candidate paths/process handles out of Git.
No raw logs, process IDs, locators, private paths or status text are published.

Normal and `-O` verifier runs must actively validate exact pins, source-first
chronology, closed schema/types, count caps, completeness/outcome/decision
links, both budgets, null-versus-zero observations, forbidden hashes/content,
process association without attribution, custody always unresolved, false
authority, privacy and no extra keys. Mutate every listed family, including
zero/one/multiple, truncated views promoted to complete, nonexistent metadata
invented, attempted access refunded and prefix-only termination/closure.
Rebind generic result digests for semantic mutations; generic hash failure
alone is insufficient. No guest/candidate/interpreter run is a verifier test.

## Current handoff

Validate pins, historical snapshots, closed caps/schema/budgets, links/privacy
and diff scope using host-only static checks. No observation implementation
or runtime compatibility is claimed. Stop on scope ambiguity or an unavailable
bounded native metadata route; do not substitute a broader scanner.
Design review/publication/new dispatch remains the next handoff. Credits are
unavailable; the integration owner records actual route and review measurements.
