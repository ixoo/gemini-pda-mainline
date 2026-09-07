# A32: descriptor-metadata associations without returned target paths

Design parent and published transport: `a29d62e328a17c5aa72c549ae366df4df5be65ad`.
The experiment inputs/work item at that parent have SHA-256
`c8fab96b01a948c6e1b5a69ee7927942aa0bbd0e1fe3519077b3bf1bc3527f7d` and
`9be3e2f064048ac6b035df681b714616d01efe9d5c680bb336df0f9ec71dd0d7`.
The unrelated concurrent repository-policy edit is outside this dispatch and
is preserved; this is not a claim that the current whole worktree is clean.

Astra Medium `/root/runtime_identity_specialist` owns this descriptor/privacy
uncertainty and is prospective sole recovery custodian; Sol Medium reviews;
`/root` integrates and owns workflow measurement. This dispatch owns only
this amendment and minimal [WORK_ITEM.md](WORK_ITEM.md)/[inputs.json](inputs.json)
updates. It constructs no observer source, fixture, result or verifier and
performs no VM/private/device access, build, execution, commit or push.

## Supersession and rejected path-buffer route

[A31](AMENDMENT-31.md), SHA-256
`166dd21a1d92ab930e249980dd6dea98c7a2ea70424b2f609d6b56000aaee9d6`,
remains immutable. Its source-construction attempt stopped before any candidate
file or execution: the in-memory draft compiled at optimizations 0/1/2 and
rejected fourteen static mutations, but those checks did not prove its native
path-buffer allowance. A proposed Linux syscall PATH_MAX argument did not
establish a bound for CPython's libc getcwd call, whose wrapper/fallback was
not established. No runtime failure or libc behavior was measured. The draft
is not an accepted source candidate and must not be executed or repurposed as
one without a new construction/review freeze.

A32 supersedes only A31's observer cwd-name validation, returned cwd/fd-target
path comparison, and associated native path-buffer proof requirements. It
eliminates getcwd/getcwdb, readlink, realpath, path resolution helpers and all
returned target-path strings from the observer call graph. No libc research
or enlarged content/startup exception is necessary for this replacement.
Streaming entry names needed for bounded descriptor-relative acquisition are
not target-path discovery: they remain transient, never assembled into paths,
emitted, hashed, or retained after their immediate acquisition work.

The published `scripts/dev-vm` transport has SHA-256
`57c13556a452bfe8b80ad96c648907f88f0e60d38e9c02ca3fd6a0b357f5cc10`.
Keep A31's exact explicit-command interface, no-TTY/non-login startup,
literal argv, environment, stdin-only source transfer and version/help gate.
The transport's reviewed physical cd to its fixed existing startup directory
is a trusted prerequisite, not something this observer independently attests
by discovering a pathname. The observer opens only literal `..` from that
unchanged cwd with O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC and validates the
held root's fstat real-directory/owner metadata. It never changes cwd or lists
the startup payload. No alternate root or recovery of a root pathname is
allowed. A missing or untrusted transport prerequisite refuses before access.

All other A31 constraints remain: exact CPython 3.12.3 Linux invocation,
sys then audit hook then closed os/stat/time frozen/built-in import closure,
no filesystem opens during imports, sealed imports before observation,
interpreter metadata-only comparison and unverified historical digest,
trusted startup and /proc boundaries, and no security-sandbox/exact-syscall
claim. All A28/A29 source and prior evidence/pins remain unchanged. A29's
diagnostic budget stays consumed; every recovery outcome leaves its custody
unresolved. Publication does not admit a recovery access or observer spawn.

## Object identities and the sole procfs-follow exception

Root enumeration, matching-name rules, lstat/open/fstat identity validation,
ownership requirements and no-follow descriptor acquisition inherit A31.
For each of at most eight owned real matching directories, retain only a
bounded transient identity tuple (device, inode, file type, owner) and its
public observation-order index. For each exact stdout.raw/stderr.raw child,
the existing no-follow stat additionally supplies a private regular-file
identity tuple. Missing children retain the existing public absent/null
semantics; no identity is invented for them. No child file is opened or read.
Reject an observed zero link count as deleted/incomplete; use st_nlink only
as internal metadata, never a new public field. The finite scalar selection
and byte accounting, including st_nlink, must be frozen during construction.

Process enumeration, numeric direct-entry acquisition, owner check, comm
selection and the sole bounded generated `stat` read inherit A31. A selected
process always has a held no-follow process-directory descriptor. Only these
two additional callsite families may follow a link:

- `os.stat(b"cwd", dir_fd=process_fd, follow_symlinks=True)` obtains target
  metadata from the literal cwd entry of that held selected process.
- For a matching cwd only, open literal `fd` below that same process with
  A31's no-follow directory flags, validate its directory/owner metadata, and
  use `os.stat(slot, dir_fd=fd_directory_fd, follow_symlinks=True)` for the
  literal ASCII decimal slots 1 through 32, each at most once.

These are explicitly trusted Linux procfs symlink-follow operations for
metadata, not no-follow checks on the links themselves. No fd target or cwd
target is opened; no descriptor target is read, invoked, traversed, or used
as another lookup base. The native operation is descriptor-relative stat/
fstatat with a fixed basename and a fixed-size metadata result, not a returned
pathname. No arbitrary stat-follow wrapper or caller-supplied path is admitted.
Every other stat retains follow_symlinks=False and every open retains the
existing no-follow flags. The literal interpreter stat remains the only
existing absolute regular-file metadata route.

Compare cwd target device/inode/directory type to the observed matching
directory tuples and require the already selected owner to agree. A unique
tuple match is a protocol-compatible directory association only. Distinct
rows with the same directory identity are ambiguous: stop as unstable rather
than choosing the first row. For a nonmatching valid cwd, do not inspect fd
slots. For a matching cwd, compare each regular-file target's device/inode/
regular-file type and owner to the available stdout/stderr tuples. If both
raw names have the same identity, count only one slot association, never two.
Other valid targets are unknown associations, not content to inspect.
Keep these bounded counts internal; A31 adds no public fd-association fields.

Inaccessible, missing/disappearing or zero-link-count cwd/fd targets make the
observation incomplete; they must not be silently treated as nonmatching or
zero. In particular an ENOENT fd slot cannot distinguish an unused slot from
a race in this protocol, so it is incomplete, not an invented absence. This
conservative rule can prevent complete coverage even for an ordinary process
with fewer than 32 occupied slots. Do not add another probe or raise a cap to
resolve it. Absent named raw children observed by the initial no-follow stat
remain distinct from a failed procfs-follow observation.

Re-read only the same held selected process's generated stat once, as in A31,
and require identical PID/starttime before accepting its association count.
Do not reacquire by PID on failure. A detected type/owner/identity discrepancy,
exit, reuse or unavailable recheck is incomplete/unstable, without retry.
No PID, starttime, device/inode tuple, slot number or target locator may be
emitted, hashed or durably retained. Temporary PID/start values are required
only for the existing parser/recheck; discard them when that record ends.
Discard all transient identity tuples during cleanup. Public row indices
remain observation order, not resolvable mutation targets.

This does not lock process cwd/fds or filesystem objects. Stable PID/starttime
does not detect every chdir, close/reopen, unlink/relink, mount-namespace change,
or inode reuse between independent observations. Even equal device/inode/type
is not a durable object identity, namespace equivalence, unique A29 attribution,
proof of log custody/completeness, or permission to mutate. A visible detected
deletion/race is incomplete; undetected races remain an explicit limitation,
not an atomic-snapshot claim. Metadata operations request no content read or
filesystem mutation; their native implementation and normal system effects
are not an attested zero-effect sandbox. Stop construction if the selected
stat interface cannot provide this metadata-only, fixed-result application
boundary without broadening the admitted operations.

## Bounds, source review and closed records

Keep the same count/deadline ceilings: 256 root entries plus one sentinel,
eight matches plus the ninth-match sentinel, 2048 proc entries plus one
sentinel, 1024 numeric processes plus one sentinel, sixteen selected processes
plus one sentinel, and slots 1..32 only. Streaming scandir must not materialize
or sort a directory or inspect nonmatches. Each returned entry name remains
bounded at 4096 bytes; every generated proc stat read remains at most 4096
bytes plus its one overflow sentinel. No other regular-descriptor read exists.

Both cumulative observed metadata and live retained payload plus scratch and
receipt buffers remain capped at 65536 bytes; reserve the maximum before each
operation. Construction must declare finite fixed-width scalar/tuple and
scandir-name accounting, audit native-interface applicability, and reject
overflow/unsupported values. Removing target strings is not a claim about
Python RSS, allocator overhead, all libc/kernel buffers or every syscall.
No source acceptance may rely on the rejected getcwd/readlink allowance.
Keep the monotonic 30-second outer/inner deadlines, bounded concurrent pipe
capture, no reconnect/signals, observer-exit uncertainty, owned-fd-only cleanup
and cleanup-failure handling from A31. No deletion or custody closure follows.

Future source construction still owns only recovery-observer-v1.json and
authorized state pins, in a separate dispatch after A32 review/publication.
Freeze source UTF-8 bytes/length/hash, A30/A31/A32 and transport identities,
public input snapshots, exact imports/audit policy, all descriptor roles,
stat-follow exceptions, no-follow routes, tuple/cap accounting, receipt schema,
false authority and UTC. Store container hash externally without circularity.
Require compile-only 0/1/2, AST/literal round-trip, unresolved-name and complete
source-first callgraph/I/O checks without observer or fixture execution.

The audit hook must continue refusing unexpected events. Stat argument/dir_fd
policy is enforced by trusted role-specific source wrappers and callsite
review, not a claim that Python audit events completely expose fstatat.
Enumerate every reachable open/stat/fstat/scandir/read/close call and prove
that only the two procfs-follow families above can set follow_symlinks=True;
prove no getcwd/getcwdb/readlink/path-resolution/content/hash/write/package/
network/subprocess/signal route. Preserve A31's separate reviewed source
publication and single-access dispatch gates.

The observer receipt schema, status/reason vocabulary, null semantics, limits
and false authority fields remain exactly A31. Compatible process counts now
mean the bounded metadata association above, never pathname equality. Complete
still requires both coverage flags and no anomaly. Existing row stable means
only the declared matched-directory lstat/open/fstat consistency, not stability
of every target or an atomic snapshot. All content_sha256 fields stay null;
private_mapping_retained is false and a29_custody is unresolved in all branches.

The future host result retains A31's exact schema with one exhaustive addition:
`binding.amendment_32_sha256`. Keep the sole access.observer_exit_confirmed
field, stream caps, valid-receipt projection, exit/capture predicates and
no-target-selection decisions. No duplicate exit field, identity tuples,
path/PID mapping or new observational authority is admitted.

Future normal/-O assert-free verifier mutations must cover A32 binding and
chronology, banned path-return helpers, follow outside the two literal/role
families, missing no-follow flags, wrong descriptor origin, omitted device/
inode/type/owner comparison, duplicate-row ambiguity, absent/deleted/error
promotion to zero, missing process recheck, private tuple/PID/slot leakage,
cap/tuple-accounting changes and association-to-attribution promotion. Retain
all A31 mutation families. Semantic mutations must rebind enclosing public
hashes so digest failure is not the only test. No embedded source execution
or guest/private fixture is admitted by this design.

## Handoff

Host-only contract/pin/link/privacy/diff checks apply now; no runtime feasibility,
hardware support, transport/startup attestation or live-state result is claimed.
The next authorized boundary is independent design review and integrator
publication, then separately dispatched source construction. A29 is immutable
and consumed; recovery access and observer-process budgets each remain zero
attempts, unconsumed, one remaining and unadmitted, with no retry authorization.
Credits are unavailable; `/root` records the sanitized workflow measurement.
