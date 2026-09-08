# Candidate R disconnect-partial preservation work item

- **Outcome:** one default-off helper that can preserve the four fixed
  disconnect-proof files before separately reviewed recovery, without retrying
  or promoting the disconnect proof.
- **Owner and reviewer:** bounded implementation owner: disconnect-gate Luna
  implementer; integration owner: primary coordinator; hardware review: Astra.
- **Scope:** the implementer owns a small static ARM64 preservation helper and
  host fixtures under
  `../2026-09-05-owner-away-experiment-preparation/keyboard/`, plus the minimal
  userspace Buildbox routing changes needed to build and package that exact
  helper. The integration owner owns this contract, session/result
  documentation, admissions and live execution.
- **Model route:** Luna High for bounded implementation after Astra froze the
  hard hardware-preservation interface; Sol Medium coordinates integration.
- **Parent:** result revision
  `37a37a7866d39cc50b475fb37969c634ce07d6b4`; original admission
  `c14f6469-5c0a-4a83-9909-6789b3586c36`; boot
  `bbad1c49-ecdd-4f40-b1e0-c53f707106d1`; published enabled-binding SHA-256
  `47a1698639f3831e3da486b64e4b98c35653cb976a579b012ca2f40665904da4`.
- **Dependencies:** exact Candidate R manifest/current credentials, failed-attempt
  command and claim hashes, and a future one-use preservation admission. The
  original proof's two-connection budget is consumed and cannot be reused.
- **Frozen effects:** one future no-PTY SSH connection, zero retries, 30-second
  host deadline, 20-second remote deadline, command at most 32 KiB, stdout at
  most 512 KiB and stderr at most 16 KiB. The helper is disabled by default.
- **Remote contract:** authenticate and verify exact boot/candidate before reads;
  preserve only `observer.stdout` (98,304 bytes), `observer.stderr` (98,304),
  `monitor.status` (4,096) and `outer-exit` (16) below the fixed proof directory.
  Use per-stage/result framing, descriptor-backed regular-file identity checks,
  before/after metadata, bounded reads and independent treatment of missing,
  unsafe, changing, oversized or incomplete members. Preserve before a bounded
  512-process/4,096-descriptor/256-match sanitized diagnostic scan. Optionally
  report the hash-pinned reboot-helper identity; never invoke it. Recheck boot
  identity and emit a final completion marker.
- **Prohibited:** recursive or caller-selected remote paths, arbitrary process
  strings, device/FIFO/socket reads, opening descriptor targets, remote staging,
  signals, probe restart, evdev/VT access, console changes, logger consumption,
  storage writes, deletion, shutdown, reboot, original proof receipt or pass.
- **Validation:** fault tests for missing/partial/growing files, symlink/special
  types, descriptor identity changes, every stage failure, scan truncation,
  transport interruption and output ceilings. Scan failure must retain earlier
  exports. Tests must prove disabled/mismatched admissions refuse before claim,
  filesystem change or transport.
- **Stop/escalation:** stop before implementation if BusyBox cannot express the
  frozen descriptor checks without a new device helper. Stop after two repair
  failures, any scope change or ambiguous acceptance. Live execution is excluded.
- **Hardware:** none in this work item. Retrieval and recovery remain separate.
- **Handoff:** exact paths, source identities, focused tests, known limitations,
  and whether the exact future command is ready for hardware review.
- **Shell-only feasibility result:** blocked before code. Candidate R's
  verified BusyBox shell can open a file descriptor only through ordinary shell
  redirection; it cannot request `O_NOFOLLOW|O_NONBLOCK`. A symlink precheck is
  inherently raceable, while post-open metadata cannot prevent following a
  swapped symlink or blocking on a swapped FIFO. The frozen safe-open contract
  therefore requires a new reviewed device helper or must be abandoned. Astra
  selected a new helper for offline preparation rather than discarding
  potentially recoverable RAM evidence.
- **Helper addendum:** use a small independently reviewed static ARM64 binary,
  built twice on Buildbox from pinned source and tool inputs. It must open only
  the fixed four-file allowlist relative to verified directory descriptors with
  `O_NOFOLLOW|O_NONBLOCK`, reject unsupported behavior without fallback, emit
  bounded framing to stdout, and perform no signal, device-node, remote-write or
  recovery action. A later runner may deliver it only to a disjoint RAM-only
  path with exclusive creation and checksum verification; staging is retained.
- **Implementation handoff:** helper source `5318a346...`, native/QEMU fixture
  `54e42b5b...`, build script `3c622b2e...`, dispatcher `6f907510...` and routing
  test `e810b3c6...`. Four native host fixture methods and seven routing methods
  pass; strict host compilation, Python compilation, Bash syntax, ShellCheck and
  whitespace checks pass. The integration review additionally covers full-size
  bounded output, invalid-mode and symlink ancestry refusal, format-truncation
  checks and consistent close-error classification.
- **State:** offline file-preservation component accepted. Buildbox produced
  two identical static AArch64 replicas, all four QEMU fixture methods passed,
  the fetched package inventory revalidated, and the specialist accepted the
  fixed helper without admitting delivery or execution. The exact result is
  [`results/candidate-r-preserver-preparation.json`](results/candidate-r-preserver-preparation.json).
  Device remains waiting; no live action is admitted.
- **Build attempts:** the first exact Buildbox dispatch refused locally because
  the published `main` commit was checked out on a differently named topic
  branch; revision `9e182d61...` repaired that host-only gate. The next dispatch
  reached the pinned compiler and musl build but exited 141 when a successful
  `nm | grep -q` check closed the large static-symbol pipe under `pipefail`.
  The focused repair writes bounded tool reports before matching them, avoiding
  success-induced SIGPIPE without weakening the static/AArch64 checks. A further
  Buildbox run compiled the helper and reached the QEMU fixtures, where the
  socket fixture failed with `EXDEV` while renaming a socket from `/tmp` into
  the workspace filesystem. Specialist escalation authorized one fixture-only
  repair and one exact rerun: bind the socket under the fixture directory by a
  short relative name, restore the working directory and close/remove only the
  fixture-owned socket. The helper source and semantics remain unchanged. Any
  further failure or broader repair requires immediate escalation.

## Helper-only successor boundary

The accepted helper is not admission-aware and its `stable=yes` field proves
only the checked before/after identity and size observations, not an atomic
snapshot. Specialist review rejected a shell-owned diagnostic/timeout tree:
killing an inner shell does not prove its helper or scan descendants terminate.
The combined delivery runner is therefore not ready for implementation.

One helper-only successor is frozen for Luna High implementation:

- Keep no arguments and the exact four fixed preservation paths. Preserve every
  member before scanning, and never let a scan failure suppress already-emitted
  preservation frames.
- Add the bounded sanitized process/descriptor scan to the same C process. It
  may visit at most 512 numeric process entries and 4,096 descriptor entries
  and report at most 256 fixed category matches. It must never open descriptor
  targets or print arbitrary command lines. Missing, inaccessible, changing or
  over-limit inventory is explicitly incomplete.
- The process may not fork, exec, create a session, signal another process,
  perform recovery, write remote files, open a device node or access a keyboard
  or VT. Existing descriptor-relative safe-open, ownership/mode/link, per-file
  and aggregate-output ceilings remain.
- Start one 15-second `CLOCK_MONOTONIC` deadline before preservation. Put stdout
  in nonblocking mode and route every output write through a deadline-aware
  poll/write loop. A blocked consumer, slow scan or expired deadline returns
  nonzero without signals; partial frames remain meaningful only as retained
  raw evidence and can never be promoted by a parser.
- Native and ARM64/QEMU fixtures must cover preservation retention across each
  scan failure, numeric-entry validation, malicious/truncated values, exact
  512/4,096/256 boundaries, overflow, deadline expiry and blocked stdout. Tests
  must also prove the source has no process-creation, execution or signaling
  path.

The enlarged binary receives a new exact size, hash and package identity; the
accepted 66,664-byte component remains historical input, not a delivery pin.
Stop after two relevant repair failures or any need to change the fixed paths,
effects, deadline, output semantics or scan ownership.

The helper-only implementation handoff is source
`184647a9ff7ba0e60159dd75b4836f944238b12302a90653ec46c5960abfaf55`
and fixture
`732c86fc1ba8a7191b8d1f0c2aea8b0f1151a62aa911711537e59030f9189ff7`.
Eleven host methods pass; the Linux device-number alias case is the sole macOS
skip and is mandatory on Buildbox. The first specialist review reproduced a
writable-output deadline bypass and executable-identity blind spot. Repair one
closed those plus descriptor ownership, sanitized identity and deterministic
blocked-output coverage, but left outer enumeration errno coupling and a
recognized dangling-input false completion. Final repair two made descriptor
metadata failure incomplete, isolated each outer `readdir`, and made match 257
an overflow after exact-limit 256. Final specialist source review found no
remaining relevant defect and admitted one exact Buildbox run only. Any new
failure is an escalation stop, not another repair authorization.

## Runner remains blocked

A future default-off runner needs a new preservation-admission UUID bound to
the consumed proof admission and exact boot, a disjoint retained RAM-only
exclusive stage, separately bounded raw-stdin payload framing and strict local
incremental retention. Before implementation it must also establish from the
exact retained BusyBox implementation that every timeout watcher and workload
has safe PID-reuse, termination and reaping behavior in normal, blocked-payload
and blocked-output cases. Otherwise it needs a separately designed supervisor.
Host timeout alone supplies no remote process-lifetime proof. No runner, live
delivery, probe restart, keyboard action, original proof receipt, success
promotion, cleanup, shutdown, reboot or recovery is admitted here.

## Fixture-only coverage escalation

The fetched successor package is internally valid, but it does not yet close
helper acceptance. Its eleven-test Linux log proves the portable device-number
alias case only through the native host helper; identity drift, exact scan
limits, truncated process data, executable identity, deadline and blocked
stdout also lack the contract-required ARM64/QEMU cells. Package integrity is
not evidence that an unexecuted architecture cell passed.

Astra therefore froze one separately scoped Luna High fixture repair. Only
`test-preserve-disconnect-native.py` and attributable result documentation are
owned. Helper source SHA-256
`184647a9ff7ba0e60159dd75b4836f944238b12302a90653ec46c5960abfaf55`
must not change. The fixture must parameterize identity drift, process limits,
descriptor and match boundaries, truncated process values, executable
identities and portable device aliases across native and explicit pinned-QEMU
ARM64 execution. It must compile equivalent native and ARM64 pause,
short-deadline and blocked-output variants, retain marker-driven race
synchronization, use a deterministic prefilled nonblocking output pipe for
both architectures, and verify preservation frames survive every scan refusal.

The result must include a bounded matrix naming scenario, architecture,
fixture-binary SHA-256, result and skip reason. Missing QEMU/compiler, any
required Linux skip or a missing required cell is failure. A macOS-native alias
skip is acceptable only when the Linux-native and ARM64/QEMU cells pass. Keep
the static forbidden-process-call scan against the unchanged helper source.

After focused offline review, commit and push the exact fixture change, then
run one exact Buildbox job. A test-only run is sufficient if existing routing
can produce attributable evidence without broader tooling changes. If the
reviewed package route must rebuild, the production helper must remain exactly
66,672 bytes with SHA-256
`750169b008cae28fd6297f7a1567ad833022b521f17ee9c6c1e2ffa023c4f745`;
record any successor package separately. The earlier two-repair helper-source
limit does not bar this explicit fixture correction, but no helper repair is
reopened. Stop on helper or production-binary drift, missing coverage, a
relevant test failure or need for broader tooling; there is no automatic
second run. Device delivery and live execution remain excluded.

The first escalated implementation revision, fixture SHA-256 `7f9a0c6a...`,
is rejected before publication: it reused emptied identity-drift inputs for the
second architecture, omitted complete preservation assertions on two scan
refusals, covered only the deleted executable spelling, and recorded process
exit before semantic assertions as if it were the matrix result. After the two
Luna attempts, Astra authorized one fresh fixture-only attempt by a different
Luna High implementer. This is an escalation disposition, not a resumed repair
loop, and does not admit Buildbox.

Each identity-drift architecture case must reset and repopulate inputs, use a
bounded explicit marker wait, and reap its child in `finally` before removing
files. Snapshot and compare all four exact payloads, regular states, successful
read metadata and stability after every completed-preservation scan refusal.
Test exact and deleted executable spellings as distinct native and ARM64 cases
with independent executable/deleted/command-line counters. Matrix `pass` may
be appended only after semantic assertions; failures are recorded and
propagated. Required cells occur exactly once and must pass; duplicates,
missing cells, failures and required skips reject acceptance, while cleanup
still runs. Focused negative fixtures must prove those matrix refusals. A pair
of consecutive native variants may prove state isolation only when labeled
non-ARM; it cannot stand in for the later real QEMU evidence. Any further
relevant defect, helper drift or scope expansion stops at a new escalation.

The separately escalated Luna revision `7fcf2248...` was also rejected before
publication because unittest-object/string comparison could label failed cases
as passing, matrix-validation failure bypassed diagnostic cleanup, and its
local isolation check did not exercise two delayed drift variants. Astra then
authorized one final coordinator-owned fixture correction. The resulting
fixture is
`790a46a4478e588b508270f07bd32870dcaac330e4a1ed08a58399cadd860285`;
the helper remains `184647a9...`. Fifteen native methods pass with the one
expected macOS device-alias skip. Assertion, ordinary-exception and real nested
subtest failures now produce failed matrix cells while retaining the original
failure; matrix validation always attempts bounded diagnostics and cleanup;
and two distinct delayed native binaries both pass the shared drift
orchestration. Final specialist source review admits commit/push and one exact
Buildbox run. That run must contain exactly one passing, unskipped native and
ARM64/QEMU cell for each of the 13 required scenarios (26 cells total), and the
rebuilt production helper must remain exactly 66,672 bytes with SHA-256
`750169b008cae28fd6297f7a1567ad833022b521f17ee9c6c1e2ffa023c4f745`.
Any failure or identity drift stops without another build or repair.

The single Buildbox run at revision `70637c2f...` passed and produced package
identity `a3a0c301...`. All nine indexed files revalidate. The production
helper remains the required 66,672-byte static AArch64 binary with SHA-256
`750169b0...`; the retained log reports 15 tests, no skips, and 48 unique
passing matrix cells. All 26 required native/ARM64 cells occur exactly once
with no skip reason. Stdout/stderr buffering placed the unittest summary
between the intact JSON line and its end marker; independent parsing and the
specialist both accepted the single 8,800-byte JSON array. Preserve the
checksummed log unchanged. The exact successor result is
[`results/candidate-r-preserver-scan-preparation.json`](results/candidate-r-preserver-scan-preparation.json).
This closes offline helper preparation only.

## Exec-command bootstrap feasibility

The fixed helper still has no admitted delivery runner. Source review of the
exact retained BusyBox rejected its detached `timeout` watcher for PID
identity, termination and reaping ownership. A proposed supervisor can own its
helper child after it starts, but receiving the supervisor over standard input
would recreate the unresolved blocked-input lifetime before supervision begins.
The next discriminator is therefore a complete bootstrap carried in the SSH
exec-command request, with no payload read from the network stream.

Offline revalidation of Ubuntu's exact retained BusyBox package and binary
confirmed `base64`, `sha256sum`, `xz`, `unxz`, `gzip`, `gunzip`, `printf`,
`chmod`, `mkdir`, `stat` and `awk` applets. The accepted 66,672-byte helper is
22,672 bytes under deterministic `xz --check=crc32 -9e`, but 30,233 bytes once
base64 encoded; gzip plus base64 is 35,165 bytes. Thus the helper alone only
barely fits the 32 KiB exec-command ceiling and does not establish room for the
mandatory boot/admission checks, exclusive RAM staging, checksum verification
and transition. No supervisor exists in Candidate R and no static supervisor
size has been established.

Runner design remains blocked at that bootstrap boundary. A safe future design
must first prove an exact complete encoded-size budget and a fixed decoder/
exclusive-stage/`exec` sequence using only already-received command bytes. If a
supervisor is used, it must replace the shell, keep its sole helper child
identity until reap, use nonblocking bounded pipes and monotonic deadlines, and
preserve staging and partial evidence on disconnect or failure. No stdin
delivery, detached watcher, process-name signal, cleanup, recovery, proof
promotion, live connection or device action is admitted by this measurement.
