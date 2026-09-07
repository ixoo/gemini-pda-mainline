# A31: source-frozen metadata observer replacing the A30 utility route

Design parent: `b35ffd6a63ae04add21d538870b359c342a74016`, clean and
equal to `origin/main`. Current input snapshot SHA-256
`aa9963fc23639090aeeeddbee8febe859e094671cfb01e7a92e5be4e4f510531`;
work-item snapshot SHA-256
`e88c390b4a84e52211b0cc4427861eac9eaafc4c8cacd8346a3576f4995ff70b`.

Astra Medium `/root/runtime_identity_specialist` owns this bounded-I/O
uncertainty; Sol Medium independently reviews; `/root` integrates and owns
workflow measurement. Only this amendment and minimal
[WORK_ITEM.md](WORK_ITEM.md)/[inputs.json](inputs.json) updates are owned now.
No observer source, guest access, execution, result/verifier, commit or push
occurs in this design dispatch.

## Supersession and immutable limits

[A30](AMENDMENT-30.md), SHA-256
`aed5e4cb8229ae8ddfedffe920b0064001568c5f77419e6d47705d13ae6ef11b`,
remains immutable historical design. Its command-preparation gate refused
before transport: no reviewed existing utility route established streaming,
count-all enumeration without materializing an unbounded list or statting
nonmatches. Output-capping a producer was not proof of those properties.
No recovery access was attempted.

A31 replaces only that unavailable utility/interpreter prohibition with one
small independently written, source-frozen observer. It is recovery plumbing,
not the A29 diagnostic candidate, a diagnostic retry, package experiment or
private-content analysis. A29's frozen transport failure and raw unavailability
remain exactly as recorded in A30. Its budget remains
`attempts=1, consumed=true, remaining=0, rerun_admitted=false`.
The separate recovery access/observer process is still unconsumed and
unadmitted. Every outcome leaves A29 custody unresolved, and no prefix,
descriptor association or process metadata uniquely attributes A29.

Retain all prior pins and the unchanged A28/A29 diagnostic source/container,
method and V9/V10 evidence. Neither file hashes nor private log contents are
inputs. A31 never authorizes signalling, terminating, deleting, closing another
process's descriptors, VM quiescence, radio/device/build/network activity or
further access.

## Exact invocation and truthful startup boundary

The current re-shell route is **unavailable for this observer**. At design
parent, scripts/dev-vm SHA-256 is
`8cb45d06a31abafcd887beb7bd0d385f169a0493c9e25c0209dd72dd08c163a9`.
Its re-shell arm calls start_vm (including limactl start), then limactl shell
without an explicit TTY option, then bash -lc and a guest-selected SHELL -l.
It forwards no command arguments. Login profiles can read/execute files, change
environment, produce output or perform history/other writes before Python.
Piped host stdin alone did not establish a noninteractive guest route.

A separately implemented, tested, independently reviewed and published
transport successor is a prerequisite **before observer source construction**.
Current design ownership does not include scripts. Its frozen interface is:

```text
./scripts/dev-vm re-shell -- /usr/bin/python3.12 -I -S -B - a29-recovery-status
```

Preserve zero-argument re-shell behavior exactly. With explicit -- and a
nonempty literal command vector, use limactl shell --tty=false with the
existing instance and --workdir=/tmp, followed directly by /bin/sh -c, never
the guest-selected SHELL, bash -lc, a login shell or an interactive flag.
Reject a missing command, extra arguments without the literal -- separator,
or a nonabsolute
command path before any VM call. No eval, joining command arguments into shell
source, argument splitting, environment-assignment command or alternate path.

The /bin/sh -c script has only these operations: validate nonempty absolute
guest HOME, test the existing quoted HOME/reverse-engineering/gemini-vendor
directory, cd there with physical-directory semantics, and exec /usr/bin/env
-i with the six fixed environment assignments below and the literal "$@"
command vector. Supply a fixed innocuous $0 and command arguments as separate
argv elements. The script must not read stdin, so the observer receives the
original source pipe unchanged. Use an explicit env option terminator and an
absolute command path so command arguments cannot become env options or
assignments. Do not create files, redirect input through a shell heredoc,
consult SHELL, invoke a profile, install a trap or log command/source bytes.
The script's own errors use fixed sanitized codes, not HOME/command/path
interpolation; suppress native cd error text on its failure path. Native
transport/loader/exec diagnostics remain unaccepted private pipe data and
must not bypass the host output cap or privacy gate.

The host wrapper uses pipes for all three standard descriptors and requests
no local PTY. The successor explicitly requests Lima --tty=false; the observer
also refuses if any of descriptors 0/1/2 is a TTY. A trusted POSIX /bin/sh
invoked noninteractively with -c, without -l or -i, does not request login
profiles or interactive history. That behavior is a platform prerequisite,
not an attestation of a customized shell's internals. If the selected /bin/sh
does not satisfy it, refuse; no replacement shell or new transport fallback.

The /bin/sh process initially inherits the trusted guest launch environment:
env -i applies only when it execs the observer. Do not claim that it constrains
earlier dynamic-loader, Lima, VM startup, host-shell or guest-launch effects.
Those components can read configuration, load code, emit output or perform
their ordinary side effects before the observer hook. Even with no profile/
history invocation, the full transport is not metadata-only or a no-write/no-
package/no-private-effect sandbox. A hostile launch environment or modified
shell is outside the trust boundary, not something later env -i repairs.
Host wrappers must not themselves invoke a login/interactive shell or pass
BASH_ENV/ENV/exported-function injection variables to the host script launcher.

The owner supplied offline host observations: limactl version 2.2.0 and shell
help exposing global --tty with "Set to false for automation". These were not
remeasured by this design turn. The successor's explicit-command branch must
preflight the installed host CLI before start_vm: require exact version 2.2.0
and the supported --tty=false option from bounded local help output. Missing,
changed or inconclusive support refuses without VM access; no download/update.
Its implementation handoff records actual version/help evidence and the
reviewed successor script/test hashes. The zero-argument branch stays unchanged.

Future transport ownership is scripts/dev-vm and a focused host-only regression
test, with state pins owned by the integrator. Tests must stub limactl and the
guest command boundary: assert unchanged zero-argument argv; explicit --tty=false;
direct /bin/sh -c with no login/interactive flags; literal command/argument
preservation for spaces, quotes, dollars, semicolons and leading option-like
arguments after the absolute command; exact env -i assignments; unchanged
stdin bytes; no HOME/SHELL evaluation on the host; no profile/history command;
rejection before VM calls for malformed argv/version/help; sanitized errors;
and propagated exit status. Use bash -n, ShellCheck and focused normal/-O host
tests where Python is the test language. No test may contact a VM, execute
the observer/candidate or claim actual guest startup attestation. Publication
and a new observer-construction dispatch follow independent Sol review.

The sole future observer command passed through that successor is:

```text
/usr/bin/python3.12 -I -S -B - a29-recovery-status
```

Its stdin contains only the exact frozen observer UTF-8 source followed by EOF.
No path, PID, locator, diagnostic source, method or private argument/pipe.
Require exactly `sys.argv == ["-", "a29-recovery-status"]`, CPython 3.12.3
on Linux, and isolated/no-site/no-bytecode flags. No alternate mode or fallback.
At the env exec boundary, the child environment contains only PATH=/usr/bin:/bin, LC_ALL=C, TZ=UTC,
PYTHONDONTWRITEBYTECODE=1, DEBUGINFOD_URLS= and PIP_NO_INDEX=1.
This is not the environment of the preceding transport or /bin/sh startup,
nor an assertion that Python cannot adjust its own process environment.

The expected interpreter record is the accepted V9 public identity:
path /usr/bin/python3.12, size 7845048, mode 0755, mtime_ns
1781873160000000000, historical SHA-256
`a7d56a8a764faf7bbf5c164055a48fd072be52287bdeb523a9e07b2042f4e7e1`.
The observer may compare only nonsymlink regular-file metadata at that exact
path after imports; it must not open/read/hash executable bytes. Its receipt
must say runtime_content_identity_verified=false. Matching metadata is not a
cryptographic identity attestation. The public historical digest remains a
construction binding, not a newly measured result.

**The whole Python process is not metadata-only.** Before stdin code installs
a hook, the OS/interpreter can load executable/shared-library/encoding/startup
bytes. The isolated flags remove site/user injection routes, not those reads.
No in-process observer can retroactively constrain or audit them. This is an
explicit trusted-startup boundary, not zero-read or exact-syscall provenance.
If runtime byte-identity attestation or absence of all startup reads is required,
stop: that requires another design, not an implicit content-read exception.

The exact explicit import order is `sys`, install audit hook, then `os`,
`stat`, `time`. Do not import json, hashlib, pathlib, subprocess, ctypes,
selectors, threading, importlib.metadata, site or package code. Serialize the
closed receipt with independently written fixed-schema formatting of bounded
integers, booleans, nulls and closed ASCII tokens; never serialize arbitrary
objects or exception messages.

Before helper imports, the hook permits import events only for sys, os, stat,
time, posix, posixpath, genericpath, abc, _abc and _collections_abc.
Permit exec events only for exact corresponding frozen-code filenames used
by that closure; no compile/eval/exec of other code. All filesystem open events
are denied during imports. After imports, require explicit helpers and newly
loaded dependencies to have the exact expected built-in/frozen origins and
names: sys/time/posix/_abc built-in; os/stat/posixpath/genericpath/abc/
_collections_abc frozen when present. Unexpected dependency, external source
module, extension-file load or open request refuses; never widen the whitelist.
Freeze the complete transitive import/exec event policy in the source review.
Already loaded startup modules are not newly verified by those checks.

Seal imports before observation. The source-first review must verify all audit
event names/argument shapes and the complete reachable call graph. Audit
callbacks may check fixed pending-operation state for expected open/scandir
events; audit open arguments alone do not bind dir_fd, and many metadata/read
operations have no complete Python audit coverage. Consequently trusted
descriptor wrappers, explicit callsite review, flags and caps enforce the
application boundary. Do not call this a Python/OS security sandbox.

## Descriptor-relative observation and I/O policy

After helper checks, acquire only:
(1) the known cwd parent root descriptor, (2) /proc directory descriptor,
(3) up to eight matching directory descriptors, (4) selected process-directory
descriptors and their exact stat metadata descriptor, and (5) corresponding
temporary fd-directory descriptors. No arbitrary absolute-path dispatch.

Validate cwd metadata without listing the immutable startup payload. Require
its exact final component gemini-vendor and parent component reverse-engineering.
Open `..` relative to that cwd with
O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC, then fstat and verify real directory
and observer ownership. Use this held descriptor for enumeration. No pathname
re-resolution for later descendant access. Opening a directory for enumeration
is allowed metadata I/O, not a regular-file content read. Do not chdir, create
a directory or modify the payload.

Open /proc with the same directory flags and require an owned-by-root real
directory with mode 0555. Trust the existing Linux /proc mount as the process
metadata interface; these checks do not attest filesystem type, mount topology
or kernel honesty. No mount-table read or new native call is admitted to claim
otherwise. A different root/type/mode refuses. Do not scan another proc mount
or namespace. Descriptor opens below it require numeric direct
entry names and the same no-follow directory flags. Native process metadata
is kernel-generated data, not a retained raw-log/private-payload input.

Use `os.scandir(root_fd)` as a streaming iterator. Do not convert it to list,
sort it, use recursive traversal or DirEntry.is_file/is_dir/stat on nonmatches.
Count every immediate name: examine at most 256, and consume only the 257th
as a cap sentinel. Accept only inventory-diagnostic-a29. plus six ASCII
alphanumeric characters. Prefix-like malformed names are a count-only anomaly.
The ninth matching candidate stops before its metadata is inspected.

For at most eight matches, lstat via `os.stat(name, dir_fd=root_fd,
follow_symlinks=False)`; require owned real directory before
`os.open(name, directory_flags, dir_fd=root_fd)`. Require the opened fstat
identity to match the prior device/inode/type/owner identity. A race or failure
is incomplete, not a retry. All child metadata uses the held directory fd,
so later pathname replacement cannot redirect the lookup.

Inspect only stdout.raw and stderr.raw with stat(..., dir_fd=match_fd,
follow_symlinks=False). Never open either file, even if it appears regular.
Record kind, owner-match, mode and regular-file size; content_sha256 is null.
No content read/hash, xattr, ACL, arbitrary child name, file traversal or
attempt to recover a child receipt. Close only the observer's own descriptors.

Enumerate /proc using one streaming scandir iterator, retaining no full list.
Count at most 1024 numeric process entries; the 1025th is a sentinel. Bound
all directory entries, including nonnumeric ones, at 2048 plus one sentinel.
Nonnumeric names receive no further observation. Count excess as process-cap.
For each numeric entry, open its directory with no-follow flags, fstat owner
and inspect only observer-owned entries; disappearance/inaccessibility makes
coverage incomplete, not proof of absence.

For an owner-matching process directory, open only the literal `stat` with
O_RDONLY|O_NOFOLLOW|O_CLOEXEC and dir_fd. Require a regular metadata node and
read at most 4096 bytes plus one overflow sentinel, then close. This is the
**sole regular-descriptor byte-read exception during observation**: bounded
kernel-generated /proc process metadata needed for comm/state/start identity.
No regular retained file, executable, library, log or payload bytes are read.
A proc stat implementation needing more bytes refuses; no second read to
complete an oversized record. Freeze a strict byte parser for PID, parenthesized
comm, state and field 22 starttime; reject malformed framing and unsupported
values. Keep private values internal; only comm equality to python3.12,
state class and consistency Booleans may influence public aggregates.

For at most sixteen python3.12 matches, readlink only cwd relative to the held
process fd. Compare internally to observed root/matching-directory paths,
without following the link. For matching cwd, open the exact fd directory
relative to the held process fd with directory flags and readlink only numeric
names 1..32. Count raw-file-path associations and unknown targets; never open
descriptor targets, read cmdline/environ/maps/stacks/memory or publish link
values. Re-read only the same held process's stat metadata once and require
the same PID/starttime. An exit/reuse/race is unstable, not a new PID lookup.

Individual name/link payloads are capped at 4096 bytes, each proc stat record
at 4096 plus its overflow sentinel. Reserve the maximum scratch allowance
before each operation; live retained metadata payload, scratch and receipt
buffers together may not exceed 65536 bytes. Increment a cumulative observed
metadata-byte counter, also limited to 65536; stop before an operation whose
maximum return allowance would exceed it. Discard nonmatching metadata
immediately. This cap may end process coverage before 1024 entries, which is
a legitimate incomplete observation, not grounds to raise it.

These are application payload/call bounds, not a 64-KiB Python RSS bound or
a claim about every libc/kernel buffer or syscall. In particular freeze the
scandir/readlink platform behavior and finite scratch accounting before source
acceptance; an unsupported interface is a construction refusal. Prohibit
unbounded read(), read_bytes(), read_text(), enumerate-to-list, raw exception
formatting and content-hash operations in the observation call graph.

## Receipt, privacy and deadline

Emit one bounded ASCII JSON object on stdout, at most 32768 bytes, followed
by one newline; stderr must be empty for a valid observer receipt.
Use fixed status/reason codes on caught failure and never print a traceback,
path, PID, source line, object representation or arbitrary error message.
An early unhandled failure produces no accepted receipt; do not repair/retry.

Do not emit or durably retain a private locator/PID mapping. Local variables
exist only for this process's comparisons and are discarded on exit.
Public row indices denote this observation's order only and are not resolvable
targets for mutation. A future owner-authorized target-identification design
would need its own evidence and access; these rows do not secretly grant it.
All discovered objects remain untouched. This explicitly replaces A30's proposed
private correspondence retention, avoiding both locator export and new files.

The host wrapper supplies the public frozen source in memory, captures pipes
concurrently and accepts at most 32769 stdout bytes and 4096 stderr bytes.
It must not echo either stream before fixed-schema/privacy validation.
Raw stderr remains unaccepted transient transport data, never a published
record or a claimed durable retained log. Record only presence/byte count and
whether capture completed; do not hash or publish its bytes. Public source
and host result hashing remain allowed publication operations, not guest
content observations.

Start one monotonic 30-second access deadline before the transport API call.
It includes connection, source transfer, process startup and observation.
The observer also checks its own monotonic deadline before every bounded
operation and loop step; it exits normally when its allowance is exhausted.
The host deadline closes only its newly owned pipes and records incomplete
status; no signal/termination of any discovered process or process group.
A blocked OS call can outlive the deadline: neither pipe closure nor host
transport exit proves observer exit. Preserve that uncertainty; no reconnect.
No claim of a hard kernel-enforced execution-time bound is made.

Cleanup closes only known descriptors owned by the observer and releases
its internal references. Never enumerate process descriptors for cleanup,
close another process's fd, delete state, restore tools or use signals.
A cleanup failure cannot replace the first failure or claim confirmed exit.
All outcomes keep A29 custody unresolved; observer exit confirmation concerns
only this new observer, not the missing A29 process.

## Budgets and staged construction/publication

One recovery transport and at most one observer spawn are permitted, only by a
new separately reviewed/published dispatch. Any actual or uncertain transport
attempt consumes the access budget. Any actual or uncertain observer spawn
attempt consumes its process budget, including failure without a child.
If transport failure obscures whether spawning occurred, conservatively mark
both consumed. A positively established pre-transport refusal leaves both
unconsumed. A confirmed pre-spawn guest refusal consumes access but not process;
it still never authorizes another access or attempt. Every terminal branch
has retry_admitted=false and leaves the diagnostic budget consumed.

Future bounded source construction owns `recovery-observer-v1.json` and
authorized state pins only. Freeze exact UTF-8 source/length/SHA-256, public
input snapshots, A30/A31 pins, imports/audit policy, descriptor operations,
caps, expected interpreter metadata and unverified historical digest, closed
receipt schema, authority and UTC. Store the complete container digest
externally in inputs.json; no self-hash. Construction cannot execute the
observer, guest probe, fixture or private parser.

Before publication, perform compile-only optimization 0/1/2, AST/literal
round-trips, unresolved-name checks and complete source-first callgraph/I/O
review. Enumerate every permitted open/stat/readlink/scandir/read/close route,
dir_fd provenance, flags, count/sentinel/byte limits, audit exception and
cleanup branch. Prove no forbidden package/content/write/hash/signal/exec/
subprocess route. Stop on an unsupported native interface; preserve the
explicit trusted-/proc rather than filesystem-type-attestation boundary.
Sol independently reviews the complete source before a separate one-access
dispatch. Publication alone consumes or admits neither budget.

After that separately admitted attempt, authorized host ownership is
`recovery-status-v1.json`, `RECOVERY-STATUS.md`,
`verify-recovery-status.py` and minimal work-item/input state pins.
Freeze result before verifier. Never create a final diagnostic result or
alter A29 source. Shared documents, hardware claims, ledger and publication
remain the integrator's responsibility.

The public observer receipt has exactly schema_version=1, mode
"a29-recovery-status", status, reason, root_complete, process_complete,
entries_examined, matches_observed, proc_entries_examined, processes_examined,
candidate_processes, compatible_processes, metadata_bytes, directories,
runtime_content_identity_verified=false, startup_reads_constrained=false,
pre_observer_effects_constrained=false, transport_startup_attested=false,
private_mapping_retained=false, cleanup_complete and a29_custody="unresolved".
Statuses are complete, refused or incomplete; reasons are none, runtime,
imports, audit, root-identity, proc-identity, directory-cap, match-cap,
process-cap, candidate-process-cap, byte-cap, metadata-unavailable, unstable,
deadline or cleanup. Complete requires reason none and both coverage flags true.
Counts are bounded integers or null when unavailable, never invented zeros.

Directory/file rows inherit A30's exact closed sanitized field/type schema.
All file content_sha256 values remain null. No state/start/PID/path/descriptor
number or private correspondence field may be added. Unknown targets contribute
only to bounded source-frozen aggregate counters if declared in that schema;
the initial version emits no new such fields.

The host result retains A30's exact kind/schema, binding, diagnostic_budget,
access, outcome/reason, observation, custody, decision, authority and frozen_utc
fields, with these exhaustive schema changes: add amendment_31_sha256,
transport_commit, transport_script_sha256, observer_container_sha256 and
observer_source_sha256 to binding; replace
recovery_budget with recovery_access_budget and observer_process_budget
(each attempts/consumed/remaining/rerun_admitted); add observer_receipt
(the validated object above or null) and transport with exactly stdout_bytes,
stderr_bytes, capture_complete, runtime_identity_verified=false,
pre_observer_effects_constrained=false and transport_startup_attested=false.
Stream byte counts are integers in 0..32769 and 0..4096 respectively, or null
if unavailable; null is not an observed zero. Capture_complete is Boolean and
true only when both streams ended within caps without truncation/deadline or
transport ambiguity. The remaining three transport fields are literal false.
access.observer_exit_confirmed is the **sole exit-confirmation field**: true
only with confirmed observer exit, false when a started observer's exit remains
unconfirmed, null for never-started or unknown start. Do not add a transport
copy. A transport exit code, complete capture or a valid receipt alone is not
observer-exit confirmation. Complete zero/one/multiple outcomes require true
observer exit, complete capture, zero stderr bytes and a valid complete receipt.
Unconfirmed/unknown observer exit cannot produce those outcomes; use
metadata-incomplete/access-exit-unconfirmed or transport-failure/transport as
appropriate. Preflight-refused has null exit confirmation and null stream
counts, false capture_complete and null observer_receipt. In every branch
A29 custody remains unresolved, independently of the new observer's exit.
The historical kind string remains a29-recovery-status-only, not a diagnostic
identity. Add observer-refused to outcome, always no-target-selection;
its reason is the observer's closed reason. Otherwise A30 outcomes/decisions
remain, with caps/races mapped to metadata-incomplete. Require exact cross-field
projection between a valid receipt and observation, not an independent invented
summary. Missing/invalid receipt cannot support a complete outcome.

Normal and -O verifier runs actively check hashes/pins and source-first
chronology including transport publication before observer construction,
exact noninteractive transport argv/environment boundary and false startup
attestation/effect fields, sole typed access exit field and all outcome links,
imports/startup limitations, runtime metadata versus unverified
content identity, descriptor-relative/no-follow callsites, proc-stat-only
read exception, every cap/sentinel, closed schema/null semantics, result
projection, access/process budget tuples, timeout/exit uncertainty, cleanup,
no retained private mapping, unresolved A29 custody and false authority.
Mutate every family; rebind public envelope/result hashes for semantic
mutations so generic digest rejection is not the sole check. Never execute
embedded observer/diagnostic source or use guest/private fixtures.

## Handoff and unresolved risks

Current checks are host-only design pin/snapshot/schema/link/privacy/diff
checks. They do not establish executable observer feasibility, installed
interpreter content identity, frozen-import availability, procfs attestation
or exact syscall/resource bounds. Construction must resolve those interfaces
without expanding the content/startup exceptions above, or refuse.

No source or execution budget is consumed now. Handoff is Sol design review
and integrator publication, then separate transport implementation/review/
publication, then separately dispatched observer construction. Credits
are unavailable; the integrator owns the sanitized workflow measurement.
