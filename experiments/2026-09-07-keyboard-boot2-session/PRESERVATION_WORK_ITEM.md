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
  `5d0d8618...`, build script `484412ff...`, dispatcher `209bb45f...` and routing
  test `e2fd75e1...`. Four native host fixture methods and six routing methods
  pass; strict host compilation, Python compilation, Bash syntax, ShellCheck and
  whitespace checks pass. The integration review additionally covers full-size
  bounded output, invalid-mode and symlink ancestry refusal, format-truncation
  checks and consistent close-error classification.
- **State:** waiting-build. The exact static AArch64 replicas and QEMU fixtures
  must pass on Buildbox before specialist review or any live admission. Device
  remains waiting; no live action is admitted.
