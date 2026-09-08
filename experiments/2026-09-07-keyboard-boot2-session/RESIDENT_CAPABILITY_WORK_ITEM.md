# Resident preservation supervisor capability-gate work item

- **Outcome:** implement and run hardware-free fixtures which prove or reject
  the frozen resident-supervisor Linux primitive assumptions on native Linux
  and static AArch64/QEMU. A negative result is complete work. Production
  supervisor, clients, candidate integration and live execution remain blocked.
- **Parent/interface:**
  [`RESIDENT_SUPERVISOR_DESIGN_WORK_ITEM.md`](RESIDENT_SUPERVISOR_DESIGN_WORK_ITEM.md)
  and its result at revision pending publication. Revision 1 is frozen; this
  task may expose a missing capability but may not silently redesign around it.
- **Route and ownership:** Luna High owns the bounded fixture implementation in
  the reusable keyboard directory and the minimal userspace Buildbox routing
  needed to run it. The primary coordinator owns this contract, result records
  and integration. Sol reviews cross-file/build routing; Astra reviews whether
  the exact evidence discharges the capability gate. The worker is not alone
  in the worktree and must not revert or absorb other edits.
- **Owned files:** add only
  `resident-capability-probe.c` and `test-resident-capabilities.py` below
  `experiments/2026-09-05-owner-away-experiment-preparation/keyboard/`; extend
  that directory's `build-monitor.sh` and `test-build-routing.py`; extend
  `baseline/scripts/buildbox_userspace.py` with one exact
  `keyboard-resident-capabilities` build/fetch kind. The primary owns all other
  files. Stop before changing an owned-file set.
- **Fixed build inputs:** current published repository revision; pinned musl
  1.2.6 archive and existing AArch64 compiler, linker and QEMU identities from
  `build-monitor.sh`; exact kernel config/System.map identities in the parent
  result. Build two byte-identical static AArch64 probe/fixture outputs. Retain
  source, tool, library, binary, log and scenario-matrix hashes plus licenses.
- **Transport fixtures:** use real `AF_UNIX/SOCK_SEQPACKET` and exact
  `recvmsg(MSG_DONTWAIT|MSG_CMSG_CLOEXEC)` behavior. Cover exact 192-byte record,
  zero-length record, short/long records, `MSG_TRUNC`, ancillary-FD/
  `MSG_CTRUNC`, half-close, full-close immediately after a valid record, blocked
  response, two records, concurrent clients and two-second preaccept expiry.
  Assert only the first exact nonzero record is valid input. Explicitly suppress
  SIGPIPE on every response send; client loss must yield transport LOST without
  terminating the server process.
- **Process fixtures:** exercise `memfd_create` with exact copy/mode/hash and all
  four required seals, then `execveat(AT_EMPTY_PATH)` with no fallback. Prove
  PDEATHSIG survives ordinary non-set-ID/no-capability memfd execution, including
  the parent-race recheck. Exercise `pidfd_open`, `waitid(P_PIDFD,...WNOWAIT)`,
  `pidfd_send_signal`, exact-PID `waitpid`, agreement of status, blocked/ignored
  TERM followed by KILL, unrelated-process survival and no PID/name signalling.
- **Signal and exec classification:** start from all-blocked, all-ignored and
  mixed inherited signals; prove the capsule's complete empty mask, default
  catchable dispositions and disabled altstack. Prove exec-error records,
  CLOEXEC EOF ambiguity, exact 98-byte helper-start witness, pre-exec death and
  LAUNCH_AMBIGUOUS classification. A forced parent death may prove only requested
  PDEATHSIG plus eventual observed exit/reap; no timeout alone may assert ceased.
- **RAM/ledger fixtures:** require header-only `/proc/swaps`; create and
  prefault the exact 16,384/524,288/16,384-byte MAP_SHARED tmpfs files; require
  aligned `atomic_is_lock_free(uint32_t)`; inject interruption before and after
  every claim/slot commit step; validate dual-slot generation/length/reserved/
  CRC32C/commit recovery and torn-latest fallback. Terminal classification must
  require an observed matching reap.
- **Matrix and attribution:** every required scenario runs once on native Linux
  and once under static AArch64/QEMU. Emit one bounded canonical JSON matrix
  with scenario, architecture, exact probe SHA-256, pass/fail/skip and reason.
  No required skip, duplicate or missing cell is accepted. Host orchestration
  failures cannot be recorded as semantic passes. Tests must leave no fixture
  process, socket, memfd reference or temporary file.
- **Buildbox scope:** add a package-only kind; do not build a kernel or candidate.
  The dispatcher must require a clean Git-fetched published revision and reuse
  existing locks, deadlines, managed staging and cleanup. A failed run retains
  only bounded diagnostics and admits no automatic retry.
- **Validation:** strict C warnings, Python compilation/unit tests, Bash syntax,
  ShellCheck, routing mutation/refusal tests, AArch64/static/no-interpreter
  checks, identical replicas, exact package inventory and repository whitespace
  checks. Local macOS may run orchestration/mutation tests but cannot substitute
  for either required Linux architecture.
- **Stop/escalation:** stop after two relevant repair attempts, any production
  implementation, fallback for a missing primitive, change to the frozen
  protocol/resource/lifecycle interface, unbounded wait, false finite-cessation
  claim, additional connection, device access, recovery, reboot/shutdown,
  keyboard/VT/evdev action, persistent storage or Candidate R mutation.
- **Handoff:** exact changed paths and hashes, focused local checks, package
  invocation, complete matrix expectation, known limitations and whether one
  exact Buildbox run is ready for Sol/Astra review. Do not commit or push.
