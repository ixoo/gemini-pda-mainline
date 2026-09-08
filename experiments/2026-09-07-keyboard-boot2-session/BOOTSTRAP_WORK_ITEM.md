# Candidate R preserver bootstrap work item

- **Outcome:** decide offline whether the accepted fixed preservation helper can
  be staged and launched through exactly two bounded no-PTY SSH exec requests,
  without stdin payload delivery, a detached watcher, an unowned descendant or
  ambiguous transition between requests. A negative result is complete work.
- **Parent:** consumed disconnect result revision
  `37a37a7866d39cc50b475fb37969c634ce07d6b4`; boot
  `bbad1c49-ecdd-4f40-b1e0-c53f707106d1`; candidate image
  `3290b867bc6cb2ecee42e6ca1436e1ae29613c074e7e45b3836ecb2905f3e07c`;
  candidate manifest
  `62440fdee9267e26d6f90148609a7c2551fdb9d6a9f603da03f891638c65180d`.
- **Accepted payload:** package `a3a0c30151d98f0751258b37e22c205c6b0592008977be6b93425acb0ff4efbc`;
  static AArch64 helper, 66,672 bytes, SHA-256
  `750169b008cae28fd6297f7a1567ad833022b521f17ee9c6c1e2ffa023c4f745`.
  The helper source and binary must not change.
- **Exact runtime inputs:** BusyBox 1.36.1 Ubuntu
  `1:1.36.1-6ubuntu3.1`, binary SHA-256
  `52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`,
  upstream archive
  `b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314`
  and Ubuntu delta
  `1c7d785cf1e1d5d09ddc22fe755e14327fb3799878a5d840fc611044ff05f022`;
  retained
  Dropbear release archive SHA-256
  `e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81`.
  Revalidate complete archive hashes before treating source as exact.
- **Route and ownership:** Sol Medium owns the source/lifecycle audit and a
  reasoned yes/no result. Luna Medium owns byte-exact command construction and
  host-only refusal fixtures from the frozen inputs. The primary coordinator
  owns this contract, private candidate input handling, integration and any
  shared/result files. Contributors are not alone in the worktree: preserve the
  existing `AGENTS.md` edit and do not revert or absorb another owner's work.
- **Lifecycle track:** establish from exact BusyBox ash/base64/xz and Dropbear
  server sources whether a fixed-file, sequential connection A creates any
  child the shell does not synchronously wait for; whether clean SSH command
  completion establishes exit/reap of that command shell and its synchronous
  applets; how disconnect and failed writes change that result; and which
  signal dispositions and mask the connection-B shell passes through `exec` to
  the helper. Distinguish source proof from inference. Do not generalize from a
  different shell, decoder or SSH server.
- **Construction track:** construct complete literal command A and command B
  from the exact accepted binary and private Candidate R manifest. A must carry
  the complete encoded payload in exec-command bytes, reproduce the inherited
  `identity_script` guard exactly (release, boot, CPU state, and the five
  boot-critical `init`, `bin/busybox`, `bin/reboot`, `bin/kmsg-capture` and
  `bin/kmsg-seal` member hashes), and verify RAM/executable-root conditions before an
  exclusive fixed stage, create fixed files with mode 0600 and no symlink
  acceptance, decode sequentially, verify exact byte count and SHA-256, set
  executable mode, and emit one strict receipt only after all checks pass. B
  must repeat identity/RAM/stage metadata/hash checks, require the exact A
  receipt as a local precondition, then replace its shell with the helper using
  `exec`. No command may read payload or control data from stdin.
- **Fixed ceilings:** each SSH exec command is at most 32,768 bytes; connection
  A and B each have a separately stated host deadline, remote pre-exec bound and
  stdout/stderr ceiling. The helper retains its internal 15-second monotonic
  deadline and output bounds. Count the exact UTF-8 command bytes, encoded
  payload bytes and all quoting/newlines. Record deterministic compression
  settings and hashes for the compressed and encoded forms.
- **Ordering and consumption:** this work does not create an admission. A future
  admission would allocate two new single-use connections. B is prohibited
  unless A produced the exact receipt, exited zero, both streams reached EOF,
  and the local client recorded unambiguous successful completion. Any A
  timeout, disconnect, nonzero status, framing error or uncertain completion
  consumes A, retains the stage and forbids B. Any B ambiguity retains all RAM
  state and is inconclusive. Zero retries.
- **Refusal fixtures:** prove wrong release/boot/member, non-RAM or noexec stage,
  preexisting stage/member, symlink or wrong metadata, truncated/corrupt
  encoding, decoder failure, wrong size/hash, malformed/duplicate receipt,
  nonzero/timeout/EOF ambiguity and command-over-ceiling all fail closed.
  Demonstrate that cleanup is never performed and B never launches after an A
  refusal. Fixtures must not contact the device or execute the ARM64 helper on
  the host.
- **Acceptance:** both complete commands fit; no unowned/lurking process remains
  after successful A; A's successful SSH completion is a defensible transition
  predicate; B's pre-exec work has a bounded lifetime; the exact launch chain
  leaves the helper with acceptable SIGPIPE disposition and signal mask; all
  refusal fixtures pass; and the hardware specialist accepts the frozen pair.
- **Stop conditions:** stop without implementation or live admission on source
  mismatch, any command over 32,768 bytes, heredoc/pipeline/background use,
  unbounded or unreaped child, reliance on host timeout as remote proof,
  uncertain signal inheritance, need to split the payload, change the helper,
  relax identity/RAM/stage checks, clean partial state, or add a third
  connection. Escalate any proposed scope change before editing a runner.
- **Excluded:** device contact, SSH, input/VT access, proof retry or promotion,
  recovery, reboot/shutdown, build, package change, admission UUID, live runner,
  staging cleanup, commit or push.
- **Handoff:** exact commands or an explicit impossibility result; byte/hash
  inventory; source locators and lifecycle argument; fixture commands/results;
  remaining uncertainty; and whether the pair is ready for Astra review. No
  later live action follows automatically.

## Offline result

The two-request design is **rejected before implementation**. The size question
closed positively but the lifecycle question did not:

- The accepted helper compresses to 22,672 bytes with
  `xz --check=crc32 -9e`, SHA-256
  `f2bae014740fd7bac4e67a237c8ef522b4b68fe4cc4fbdccf1138cc7a20cd083`.
  Its unwrapped Base64 is 30,232 bytes, SHA-256
  `e63743038aeb3f03627e06159010afbf4f5c8d16b9f6c6c887a92b1ba23bc6ae`.
  A complete measurement-only A form with the inherited five-member guard,
  fixed `/a53-p` stage, sequential decode, exclusive-output policy, verified
  helper and exact opaque receipt is 32,638 bytes, 130 bytes below the ceiling.
  Its SHA-256 is
  `731abfd578140dbc8e445414e9990171123f730947ad236f1402b74bf7630507`.
  These candidate command bytes are not retained or admitted because the
  independent lifecycle gate failed.
- Exact patched Ubuntu BusyBox source proves the frozen simple commands and
  command substitutions are synchronously waited and reaped. The relevant ash
  paths are `evalcommand`/`waitforjob` at `shell/ash.c:10567-10602`,
  `waitforjob`/`dowait`/`waitpid` at `5382-5422` and `4312-4482`, and
  command-substitution fork, pipe drain and wait at `6585-6708`. The selected
  Base64 and unxz decoders run in-process and the simple awk programs use no
  `system` or pipe operation.
- Exact Dropbear 2026.94 source proves that a received exact receipt, remote
  status zero, both stream EOFs and unambiguous local completion follow its
  `waitpid` of the direct A shell. It also resets SIGPIPE before the command
  shell, and `trap - PIPE; exec /a53-p/helper` would preserve the shell PID and
  give the helper default SIGPIPE.
- The same Dropbear source rejects the required lifetime claim. Its 60-second
  idle and 360-second session checks call connection cleanup. Channel cleanup
  closes pipe descriptors and forgets the child PID, but neither signals nor
  waits for a still-running command shell. Therefore a B shell stalled in any
  pre-exec check can survive the server/host connection deadline. The helper's
  15-second internal deadline starts only after `exec` and cannot cover that
  interval.

All BusyBox upstream, Ubuntu delta and Dropbear archive hashes revalidated;
all 23 Ubuntu patches applied for the source audit. The specialist accepted
the lifecycle finding as a stop/no-go. No refusal runner was implemented
because the frozen stop condition was already met. There was no device contact,
SSH, build, admission, helper execution, recovery or cleanup. The exact result
is
[`results/candidate-r-bootstrap-feasibility.json`](results/candidate-r-bootstrap-feasibility.json).

A separately assigned next discriminator may inspect the already-present,
hash-pinned Candidate R programs for a primitive that starts a deadline before
the first potentially blocking preflight operation and owns termination and
reaping through direct helper execution. A new supervisor, helper/server
change, extra connection or relaxed lifetime contract is outside this work
item and remains unadmitted.
