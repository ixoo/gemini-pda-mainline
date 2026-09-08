# Candidate R direct-exec deadline ownership work item

- **Outcome:** decide offline whether an already-present, hash-pinned Candidate
  R primitive can own a preservation launch deadline, or whether connection B
  can safely contain no preflight at all and immediately replace its shell with
  the already verified RAM-stage helper. A negative result is complete work.
- **Parent:** published bootstrap no-go commit
  `298356f8be33c7efc70e1a658da6f82978f93795` and
  [`results/candidate-r-bootstrap-feasibility.json`](results/candidate-r-bootstrap-feasibility.json).
  The consumed proof admission, exact boot/candidate identities and accepted
  helper/package identities remain unchanged.
- **Route and ownership:** Sol Medium owns cross-file/source reasoning. The
  primary coordinator owns this contract, result integration and any later
  scope decision. Astra Medium reviews process ownership and boot-attribution
  risk before any implementation. No implementer is assigned.
- **Primitive inventory:** inspect every executable regular file and script in
  the exact private Candidate R manifest, plus the exact BusyBox applet set and
  any hash-bound executable demonstrably retained in the current proof RAM
  stage. Match each candidate to source and exact binary identity. A usable
  primitive must begin a monotonic wall-clock deadline before its first
  potentially blocking operation, directly own the launched helper identity,
  and terminate and reap it on deadline, disconnect and all failure paths.
  Fixed-purpose programs do not become general supervisors by analogy.
- **Immediate-exec alternative:** evaluate a B command limited to shell signal
  reset followed immediately by `exec` of the fixed `/a53-p/helper`, with no
  `stat`, hash, command substitution, decoder, pipeline, receipt read or other
  remote preflight. Determine whether A's exact receipt, clean zero exit and
  both EOFs plus the exclusive root-owned RAM stage constitute a boot-specific
  unforgeable-enough capability for the next single-use connection. Prove from
  exact initramfs construction that `/a53-p` is absent from a fresh Candidate R
  root, rootfs is recreated across boot, and no admitted actor can create or
  replace it between A and B. Analyze boot change, reconnect, path replacement,
  `execve` failure/blocking, inherited signals/mask and Dropbear orphaning.
- **Required attribution:** do not silently remove the inherited B identity
  checks. State explicitly whether their replacement by the RAM-stage
  capability preserves or weakens candidate/boot attribution, and which local
  evidence is required immediately before B. A merely short command is not an
  acceptance result.
- **Acceptance:** either identify one exact already-present primitive satisfying
  every ownership/lifetime property, or prove that immediate exec preserves the
  same boot/candidate/stage binding and creates no pre-helper lifetime gap. The
  full specialist review must accept the exact reasoning. Otherwise return a
  stop/no-go.
- **Stop conditions:** stop on any need to change a binary, replace the consumed
  proof stage, clean remote state, add a connection, trust process names/PIDs,
  infer an empty signal mask, weaken custody, assume boot continuity, or treat
  Dropbear/host timeout as child termination. Any proposed helper/server change
  or relaxed attribution contract is a separately explicit owner decision.
- **Excluded:** tracked implementation, command generator, refusal fixture,
  Buildbox, device contact/SSH, admission UUID, live execution, input/VT access,
  recovery, reboot/shutdown, cleanup, commit or push by the worker.
- **Handoff:** exhaustive candidate table with exact identities and rejection
  reasons, direct-exec proof or counterexample, exact source locators, remaining
  uncertainty, and one specialist-ready yes/no recommendation.

## Offline result

The exact inventory closes this discriminator negatively. Candidate R's
initramfs is `b258a9a5dc894ecbd330005ecab841225b320a3c2b82abe725f3833c874d74cd`,
its 47-member manifest is
`62440fdee9267e26d6f90148609a7c2551fdb9d6a9f603da03f891638c65180d`,
and its construction source is revision `e9c028005b88ef8536ecb58c095e8d172253fa12`.
Every executable regular member was classified:

| Exact members | Classification | Contract result |
| --- | --- | --- |
| `/init`, `/bin/admin-shell`, `/bin/console-status`, `/bin/emmc-observe`, `/bin/reboot`, `/bin/usb-auth`, `/bin/x-record` | Fixed scripts | No general launch deadline, child identity, termination and reap owner |
| `/bin/console-keymap-verify`, `/bin/console-unicode-mode`, `/bin/keyboard-observe`, `/bin/kmsg-capture`, `/bin/kmsg-seal` | Fixed-purpose native programs | No general helper execution or supervision interface |
| `/bin/dropbear` | Dropbear 2026.94, source archive `e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81` | Starts the command shell, but cleanup neither terminates nor reaps a stalled child |
| `/bin/busybox` | Ubuntu `1:1.36.1-6ubuntu3.1`, binary `52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933`, 270 exact applets | No applet meets all deadline, identity, termination and reap requirements |

The complete BusyBox applet table was inspected. The plausible supervisory
classes all fail independently: `timeout` uses a detached PID-based watcher
which does not reap the target; `start-stop-daemon` has no start deadline and
its retry policy is stop-only; `watch` loops through `system`; `run-parts`
waits sequentially but has no deadline or exact helper policy; and `setsid` is
only an exec wrapper. Shells and the other exec-capable applets (`env`,
`chroot`, `setpriv`, `time`, `xargs`, `find`, `awk`, service/init controls)
provide no qualifying combination. Source anchors are BusyBox
`coreutils/timeout.c`, `debianutils/start_stop_daemon.c`, `procps/watch.c`,
`debianutils/run_parts.c`, `util-linux/setsid.c` and `shell/ash.c` from the
hash-revalidated upstream archive
`b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314`
plus Ubuntu delta
`1c7d785cf1e1d5d09ddc22fe755e14327fb3799878a5d840fc611044ff05f022`.

The sole demonstrably retained proof-stage executable is the fixed-purpose
`/a53-keyboard-disconnect/probe`, 66,760 bytes with SHA-256
`560d00ab80040b90fead5d0a5b2672ed633f62599aa483ff0a33be0fa74d3681`.
It can launch only its compiled-in harmless fixture and cannot exec or supervise
the preserver. The accepted preserver remains 66,672 bytes with SHA-256
`750169b008cae28fd6297f7a1567ad833022b521f17ee9c6c1e2ffa023c4f745`;
its monotonic deadline begins inside `main`, after successful execution.

Immediate B as `trap - PIPE; exec /a53-p/helper` also fails the frozen
contract on three distinct boundaries:

1. `/a53-p` is absent from the exact initramfs and a fresh boot reconstructs
   the RAM rootfs. A's exact receipt, status zero and both EOFs therefore prove
   that stage at A completion, and a changed boot ordinarily fails closed.
   However, the host key repeats across boots and path presence under
   source-constrained custody is weaker evidence than B-time boot, candidate
   and member verification. Specialist review did not accept equivalence.
2. Shell startup and kernel `execve` occur before the helper's first instruction
   and deadline. If either stalls, Dropbear cleanup still provides no remote
   termination or reaping. Removing applet preflight shortens but does not
   eliminate the prohibited pre-helper lifetime gap.
3. Dropbear resets the SIGPIPE disposition but does not establish an empty
   signal mask. BusyBox ash's `trap - PIPE` changes disposition without
   unblocking signals, and the helper does not normalize its inherited mask.
   The contract explicitly forbids inferring an empty mask.

Astra accepted the audit as a **no-go under the current contract**. A helper
successor could normalize signal state at its first controlled instruction,
but that would not close shell startup or `execve`. Closing the launch gap
requires either a separately authorized already-running supervisor or an
explicit change making the lifetime guarantee begin at helper userspace entry;
RAM-stage attribution also needs an explicit decision. This is ready only for
Sol design scoping after that owner choice, not interface freeze or
implementation. The exact machine-readable result is
[`results/candidate-r-direct-exec-feasibility.json`](results/candidate-r-direct-exec-feasibility.json).
No runner, build, device contact, SSH, stage mutation, recovery or cleanup
occurred.
