# A29: one-run inventory diagnostic execution and result contract

Design parent: `4d9ac686d2f4d6a415ca3c0062d905bd1f5f6f0c`, clean and
equal to `origin/main`. This is a contract-only dispatch. The diagnostic
process budget is **unconsumed and unadmitted** until independent Sol Medium
review, publication and a separate explicit execution dispatch. Publication
alone does not start a process.

## Ownership and immutable inputs

Astra Medium `/root/runtime_identity_specialist` owns the collector/evidence
uncertainty and is the prospective **sole RE-VM custodian**. Sol Medium reviews;
`/root` integrates and records workflow measurement. Only this amendment,
[WORK_ITEM.md](WORK_ITEM.md) and [inputs.json](inputs.json) are owned now.
No VM, package, private, device, build, network, candidate execution, result,
verifier, shared-document, commit or push action occurs in this design turn.

[AMENDMENT-28.md](AMENDMENT-28.md) remains the immutable reproduction contract.
The published candidate was constructed separately; stale construction-time
"awaiting review" and authority fields inside its bytes are historical, not
execution permission. Do not change the source/container to refresh them.

| Frozen input | SHA-256 | Bytes where applicable |
| --- | --- | --- |
| Diagnostic container | f5ac57678dbc74bf36c5f11b3f45b72a12d8b156f3cf664f17bfb22ee39f700f | 502641 |
| UTF-8 embedded source | 4823099f6bd767a8e0a8e23e17aaddb744f1a8ab25da6ed1ce30d5f2500ae739 | 261137 |
| A28 | 4c31045693257876985a4fe52f4b3df82e67dc6b5e103b08e5c17241be5c7a96 | — |
| Design-parent inputs | dda058abb503b76b813a5d87ef3837b179c09540d3b83c92e6bf1fef1e6c9f8f | — |
| Design-parent work item | 8de4931e20ff0492b5d5d9d627d96688694dfd437e5561bdbac7a4ebea59b9e0 | — |

The candidate is [inventory-diagnostic-v1.json](inventory-diagnostic-v1.json).
Preserve its construction commit
`670b831b76225078aa3fa55b1accfe7ae9acae4a`, construction-input digest,
A28 design parent, mechanical V10 source digest and all inherited identity
objects. Do not confuse those historical bindings with the future execution
commit and its current input/work-item hashes. The latter are frozen at the
new published dispatch and recorded externally, avoiding self-hashes.

## Preflight and single collector

Before any RE-VM access, the custodian must receive an execution dispatch
naming the exact new published commit containing reviewed A29. Require clean
tracked/untracked/staged status and local `HEAD == origin/main == dispatch`;
check the exact origin URL is
`https://github.com/ixoo/gemini-pda-mainline.git` without fetching or pushing.
Verify all current controlling/dependency pins, A29, work item, candidate byte
length/hash, UTF-8 source length/hash, construction historical pins against
their named commits, and unchanged A28/V9/V10/method/freeze records.
Do not compare historical input/work-item pins to newly updated files.
Freeze the actual execution inputs digest before starting; no repair or
publication occurs under custody. Missing acceptance or a changed byte refuses.

Use only `./scripts/dev-vm re-shell`; no alternate guest entry, VM kernel
backend or private payload inspection. Its known startup directory is immutable
evidence: leave it without listing, reading or writing its contents.
Resolve the existing guest-owned `reverse-engineering` work root from the
known RE-shell location's parent, validate directory ownership/nonsymlink
identity, then create one fresh `inventory-diagnostic-a29.XXXXXX` child there
with `mktemp -d` and mode 0700. Record the exact private resolved path only
in custody notes. Never reuse a previous child's files or inspect old logs.
Check available host/guest space with filesystem metadata only; refuse if less
than 16 MiB is available for this sub-megabyte capture.

Immediately after child creation install EXIT/HUP/INT/TERM cleanup that owns
only this exact validated child, the new process group and its pipe descriptors.
It must close pipes, terminate/reap any still-owned diagnostic process, retain
unique capture bytes, and exit the RE shell. An empty never-started child may
be removed with `rmdir`. Once capture starts, do not delete its sole logs.
No recursive broad cleanup, wildcard target, previous-child cleanup or secure
erasure claim. Unexpected preexisting partial state is a refusal, not a rerun.

The collector creates exactly two regular nonsymlink files exclusively,
`stdout.raw` and `stderr.raw`, with mode 0600 under that child and umask 077.
No guest source/container/method file, third log, manifest or input copy.
A non-analysis supervisor may hold the public frozen source in memory and
manage pipes/clock/status; it must not import or probe candidate packages,
inspect installed identities, read private data, evaluate candidate code or
reimplement the child inventory. Its only child invocation is exactly:

```text
/usr/bin/python3.12 -I -S -B - inventory-diagnostic
```

Supply precisely the 261137 frozen UTF-8 source bytes to that child's stdin,
then EOF. No appended newline, wrapper, eval/exec trampoline, fixture, private
argument, method descriptor, side pipe or environment-based input. Source
transport is memory/pipe only; verify its hash/length before spawning, not by
executing it. Host extraction uses JSON parsing only, never candidate imports.
The supervisor itself and shell plumbing are collector machinery, not extra
diagnostic or interpreter-identity runs.

Use a clean child environment with only `PATH=/usr/bin:/bin`, `LC_ALL=C`,
`TZ=UTC`, `PYTHONDONTWRITEBYTECODE=1`, `DEBUGINFOD_URLS=` and
`PIP_NO_INDEX=1`. No LD/PYTHON injection variables, startup overrides,
proxy, credentials, downloads, network calls or debugger/plugin acquisition.
The unchanged source audit and isolated flags retain their original effect;
environment settings alone are not a network isolation guarantee. No security
sandbox or exact-syscall-bound claim is added to A28's inherited I/O.

Drain stdout and stderr concurrently through separate pipes to the two files;
do not merge them or run a command substitution that discards the exit status.
Bound the candidate lifetime, including stdin transfer and pipe draining, by
a monotonic 180-second deadline starting immediately before spawn. On deadline,
kill only its owned process group, close stdin, reap and retain captured bytes;
no grace extension or retry. If process exit cannot be confirmed, mark custody
unreleased, stop and escalate rather than claiming cleanup completion.
At most 524288 stdout bytes and 262144 stderr bytes may be retained. Crossing
either cap terminates the run as collector failure and records truncation;
hashes then identify captured prefixes, not complete streams. Do not silently
truncate and admit a receipt. These outer log caps do not change inherited
child read/discovery behavior.

Consume the sole process budget at any actual or uncertain spawn syscall/API
attempt, even if that attempt returns an error and no child starts. Set
spawn_attempts=1, consumed=true and runs_remaining=0. Set spawn_attempts=0
only when positively established that no spawn syscall/API call was attempted;
only that case is preflight-refused, consumed=false and runs_remaining=1.
Proof that no child started does not undo an attempted call. No second
process on refusal, exception, empty output, cap, timeout, transfer failure,
interruption or ambiguous status. A pre-spawn refusal is recorded separately
but never automatically retried. Do not restore an installed tool, update
packages, probe a file, inspect prior raw results or begin private analysis.

Before leaving custody, flush and close both files, record raw byte lengths,
SHA-256 values, truncation flags, child exit/signal/timeout and collector status,
and confirm child/supervisor/RE-shell exit. Hashing these new logs is allowed;
no post-failure installed-file reread or map snapshot is allowed.
Keep the raw logs privately in this exact mode-0700 child, preserving the sole
copy and its private retention locator. Transfer only the bounded prospective
public JSON envelope and sanitized collector facts to the host after privacy
inspection. Do not export raw stderr or raw logs. Release custody before host
result construction. An interruption preserves evidence and stops immediately.

## Exact child receipt and outcome classification

Accept stdout only when complete, ASCII JSON with a single object, no duplicate
keys, nonfinite numbers, second object or non-whitespace suffix. Its exact
outer keys are `canonical_receipt_sha256` and `receipt`. Verify the digest
over ASCII `json.dumps(receipt, sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False)` bytes, bounded at 262144.
The source's envelope may be larger than that canonical inner payload; do not
incorrectly apply the inner limit to raw stdout.

The child schema is version 10, mode `inventory-diagnostic`; exact top-level
receipt keys are the candidate's `output_schema.fields`. Recursively constrain
their reachable values from the frozen source's literal initializers and two
reachable stages. No arbitrary dictionary/string passthrough. Candidate
metadata's `hardware_support` and `runtime_acceptance` describe false authority;
they are not emitted child keys and must not be invented in the child receipt.
Record them in the host authority object instead.

Require empty stderr for an accepted child receipt. Any nonempty stderr remains
private and makes collector status `stderr-nonempty`; do not reinterpret,
quote or repair a traceback. Preserve even a valid-looking stdout receipt as
unaccepted evidence until review. Unknown keys, malformed/oversized JSON,
digest/schema mismatch, signal, cap or timeout cannot yield accepted child
localization.

| Collector and child evidence | Host outcome | Consequence |
| --- | --- | --- |
| Complete valid receipt, empty stderr, exit 2, status refused, first stage initial-inventory | initial-inventory-reproduced | Record this run's frozen site or location-unresolved; stop |
| Same refusal, first stage startup | startup-refused | Not a reproduced inventory failure; stop |
| Complete valid receipt, empty stderr, exit 0, status initial-inventory-not-reproduced | initial-inventory-not-reproduced | Both reachable stages passed; stop before pre-entry |
| No valid receipt from otherwise completed transport, including early top-level exception | no-child-receipt | No child site, counts or cleanup invented |
| Transport/deadline/cap/status/schema/stderr conflict | collector-failure | Preserve facts; no accepted child conclusion |

A missing receipt takes `no-child-receipt` only when transport was complete,
not when timeout/truncation/disconnect obscures it. Empty stderr with normal
unexpected exit is a status conflict. Nonempty stderr without a receipt may
be recorded as the no-child-receipt reason when transport completed and exit
is nonzero; it is never a published traceback or inferred child failure site.

For reproduced/refused output, require first_failure equals the preserved
source shape, `failure_location == first_failure.location`, exactly one
refused reachable stage, all later stages not-evaluated, and no downstream
entry. Fixed IDs are exactly `initial-01` through `initial-09`, with the
helper/full line-column span from candidate `failure_localization.site_map`,
reason `unique-frozen-callsite` and frames_examined 1..64. They identify
the main inventory call, not the deepest helper operation or failed operand.
Unresolved output has only site_id, helper null, reason and frames_examined
0..64; reasons are `no-unique-frozen-callsite`, `traceback-frame-cap`,
`code-position-cap`, `capture-failure`. Never add a private path/role index
or per-helper label not emitted by this candidate.

For prefix passage, require null first_failure/failure_location, startup and
initial-inventory passed, all remaining outer/queue stages not-evaluated,
zero package/engine/resource/queue/method/callback/private entry and null tool
identity/analysis result. Check observed counters against source semantics,
not a fabricated successful-run total. Preserve empty restoration dictionaries
on untouched success and source-emitted not-applicable records on refusal;
do not mutate the receipt to make either look like performed restoration.

## Frozen host result and verifier ownership

After custody release, the same separately dispatched custodian may construct
only `inventory-diagnostic-result-v1.json`, `INVENTORY-DIAGNOSTIC.md`,
`verify-inventory-diagnostic.py` and authorized work-item/input state pins.
No such files are constructed now. Sol reviews the frozen result and verifier;
`/root` owns integration, ledger and shared state. No source repair follows
an outcome. Freeze result bytes/hash/UTC before writing the verifier.

The host result has exactly these keys, with no additional keys at any level:

- `schema_version`: integer 1; `kind`: "inventory-diagnostic-v1".
- `execution`: exact keys `design_parent_commit`, `dispatch_commit`,
  `inputs_sha256`, `work_item_sha256`, `amendment_28_sha256`,
  `amendment_29_sha256`, `container_sha256`, `container_bytes`,
  `source_sha256`, `source_bytes`, `argv`, `stdin`, `custodian`,
  `model`, `reasoning_effort`. Match the actual published dispatch;
  source-only stdin, exact argv, named custodian, gpt-6-astra/medium.
- `budget`: `limit` 1, `spawn_attempts` 0 or 1, `consumed` Boolean,
  `runs_remaining` 0 or 1, `rerun_admitted` false. The only allowed
  (spawn_attempts, consumed, runs_remaining) tuples are (0, false, 1) for
  preflight-refused with positively proven no spawn call, and (1, true, 0)
  for every other outcome. An actual or uncertain spawn call consumes,
  including a call that fails without creating a child. No-child-receipt,
  absence of a PID or proof of non-start cannot restore the budget.
- `collector`: `status`, `started_utc`, `completed_utc`,
  `elapsed_seconds`, `deadline_seconds` 180, `child_exit_code`,
  `child_signal`, `timed_out`, `child_exit_confirmed`,
  `shell_exit_confirmed`, `custody_released`, `stdout`, `stderr`,
  `retention`. Status is complete, preflight-refused, spawn-uncertain,
  timeout, output-cap, transport-failure, status-conflict, invalid-receipt,
  stderr-nonempty or cleanup-unconfirmed. Exit code/signal are mutually
  exclusive integers or null; unavailable timing/status observations are null,
  never invented. Times are UTC, elapsed finite nonnegative.
  Each stream has exactly `bytes`, `sha256`, `truncated`, `complete`;
  Absent files use null bytes/hash and false complete/truncated; a created
  empty file instead has bytes 0 and the actual empty-file digest.
  Retention has exactly `created`, `location_role`, `directory_mode`,
  `file_mode`, `sole_copy_preserved` and `raw_exported`. For refusal before
  RE-VM/child/file creation, created=false, location_role/directory_mode/
  file_mode/sole_copy_preserved are null, and raw_exported=false. The same
  shape applies if only a never-started empty child was safely removed;
  created here means a retained capture directory exists at handoff, not
  that a temporary directory once existed. A retained child with at least
  one capture file uses created=true,
  location_role="private-re-vm-child", directory_mode="0700",
  file_mode="0600", sole_copy_preserved=true and raw_exported=false.
  Every actual or uncertain spawn attempt requires that retained-child shape;
  evidence loss is an escalation, not a fabricated successful retention.
  A preflight refusal after directory creation may use the retained-child
  shape when its directory and existing capture files are actually preserved.
  If an empty directory remains before any capture file was created, use
  created=true and the actual role/directory mode above, but file_mode and
  sole_copy_preserved null. This empty-directory shape is preflight-only;
  both capture files must exist before any spawn call. Never publish its path.
  Child_exit_confirmed and shell_exit_confirmed are null when the respective
  process/session was never created, true only after confirmed exit, and false
  when exit remains unconfirmed. Custody_released means no RE-VM custody is
  outstanding: true before any custody acquisition or after verified release,
  false while acquired custody or an owned process remains unresolved. Thus
  host-only preflight refusal has both exit-confirmed fields null and
  custody_released=true; it does not claim that a shell was opened or exited.
- `outcome`: one table token above, or `preflight-refused` before spawn.
- `child`: the validated original two-key envelope, or null for unaccepted/
  absent receipt. Do not publish arbitrary failed parser input here.
- `limitations`: exact Boolean true keys `current_run_only`,
  `historical_v10_site_unproved`, `compound_operand_unresolved`,
  `empty_inventory_not_zero_discovery`, `unmeasured_io_unavailable`,
  `no_general_sandbox_claim`. These are claim ceilings, not an assertion
  that every run encountered every limitation.
- `authority`: exact false Boolean keys `tool_environment_accepted`,
  `private_analysis_admitted`, `package_entry_admitted`,
  `engine_entry_admitted`, `method_entry_admitted`, `device_admitted`,
  `build_admitted`, `hardware_support`, `runtime_acceptance`.
- `frozen_utc`: result-freeze UTC after confirmed custody release.

For incomplete custody, defer result construction and hand off sanitized
collector facts; do not forge the final freeze. The prose record owns chronology,
closed reason explanation, raw hashes, actual checks and unresolved risks.
No raw exception strings, arbitrary paths, installed metadata, ASLR bases,
pointers, private bytes, source text, frame dictionaries or disassembly.
Uninstrumented I/O counts remain unavailable in prose, not added as zero fields.
No result restores the consumed V10 budget or admits later analysis.

The assert-free host verifier must check the exact result/source/control pins,
source-first chronology and A28 deltas without executing embedded source.
Recursively validate the child schema from AST/literal source and validate
cross-field semantics: first stage/site/span, outcomes versus exit/stderr,
counters/absence and untouched cleanup, monotonic budgets, capture completion,
privacy, custody release and false authority. Do not trust candidate metadata
alone where the emitted source differs.
Reject every budget/outcome tuple except the two rules above, including a
failed spawn call mislabeled preflight-refused or attempts=0. Require the
no-created-retention null shape for host-only refusal, retained-child shape
for every spawn attempt, and null exit observations for nonexistent sessions.
Reject invented modes, file hashes, preservation or exit claims before creation;
do not coerce null into false/true or interpret released custody as an exit
observation. Mutations must cover both host-only refusal and attempted-spawn
branches, including uncertain spawn and failed call with confirmed non-start.

Run normal and `-O` verification and mutations for all families: identity;
chronology/source delta; outcome/exit/stderr; site/span/unresolved shape;
historical/operand overclaim; unavailable counters/empty-inventory inference;
forbidden entry/authority; run budget; capture/hash/truncation; cleanup/custody;
privacy/extra keys. Recompute envelope hashes for semantic child mutations and
result digests where applicable so digest failure is not the sole rejection.
Record actual mutation counts, not prospective success. No candidate, guest,
package or private parser execution is a verifier test.

## Stop and handoff

Stop immediately on owner pause, conflicting evidence, unclear acceptance,
scope change or need for a second run; two failed repairs is an additional
ceiling, not two permitted executions. Preserve unique evidence and return
facts, attempts, unresolved question and next discriminating offline check.
A29's next handoff is design review/publication, not VM access. Design checks
cover exact pins/source schema/site bindings, links/privacy and diff scope;
runtime collector compatibility, reproduction and localization remain untested.
No hardware support is inferred. Credits are unavailable; the integrator
records actual route/timing/review measurements.
