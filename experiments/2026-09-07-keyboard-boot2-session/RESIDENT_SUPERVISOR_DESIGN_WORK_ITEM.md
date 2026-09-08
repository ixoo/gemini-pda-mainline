# Candidate successor resident preservation supervisor design work item

- **Outcome:** freeze, or reject with a precise discriminator, an offline
  architecture for a supervisor that is already running before authenticated
  USB administration and owns one future preservation-helper launch from
  request acceptance through terminal reap. This design supports a future
  candidate only; it cannot recover Candidate R's current RAM evidence.
- **Parent:** the published direct-exec no-go at revision
  `56501abf851ef9fdae1a02062939e75ed27b9fe3` and
  [`results/candidate-r-direct-exec-feasibility.json`](results/candidate-r-direct-exec-feasibility.json).
  The accepted 66,672-byte helper, its fixed four-file allowlist and all
  Candidate R evidence remain immutable inputs, not an implementation base.
- **Route and ownership:** Sol Medium owns cross-file design and interface
  reasoning. The primary coordinator owns this contract and integration.
  Astra Medium must accept lifetime, trigger, boot-attribution and recovery
  boundaries before any Luna implementation. No implementer is assigned.
- **Frozen safety objective:** after accepting one complete fixed request, the
  resident process starts a monotonic action deadline before `fork`/`execve`,
  directly owns the exact child identity, uses bounded nonblocking output,
  terminates and reaps the child on every deadline, transport-loss and failure
  path, and retains partial output in RAM. It must normalize and validate the
  child's signal mask/dispositions. PID names, process scans and Dropbear or
  host timeout are not ownership evidence.
- **No-effect trigger boundary:** an incomplete, malformed, duplicated or
  disconnected request must create no claim, launch no helper and change no
  evidence state. After a complete request is accepted, client disconnect must
  not cancel preservation. Define the smallest fixed local transport and
  request framing that proves this boundary without arbitrary paths, arguments,
  shell text or caller-selected identities. A pre-trigger SSH shell may not be
  treated as supervised; its inability to cause an effect before complete
  acceptance must make its lifetime irrelevant to the preservation claim.
- **Candidate integration:** use fixed initramfs paths and immutable package
  identities. Establish how `/init` starts the supervisor before `/bin/usb-auth`,
  how readiness is proven without a race, how BusyBox init owns/reaps it, and
  whether unexpected supervisor exit is terminal rather than automatically
  respawned. `/run` remains noexec and RAM-only. State exact changes needed to
  the candidate builder, manifest, validation and Buildbox package route, but
  do not implement them.
- **Attribution and one-shot state:** bind a future request to an exact boot,
  candidate, supervisor, helper and new preservation admission. Create at most
  one fixed RAM-only claim with exclusive semantics at the acceptance boundary.
  Define local receipt fields sufficient to distinguish refusal-before-effect,
  accepted/running, complete, deadline, child-exec failure and interrupted
  output without trusting booleans alone.
- **Scope discipline:** preserve only the existing four disconnect-proof files
  and the existing sanitized bounded process/descriptor scan. No evdev or VT
  access, keyboard capture, signal to unrelated processes, device-node access,
  storage write, cleanup, recovery, shutdown, reboot or proof promotion. Do not
  modify the accepted helper contract merely to absorb supervisor behavior.
- **Acceptance checks:** provide a complete state machine and process/descriptor
  ownership tree; exact trigger and output framing; deadline start/end rules;
  crash, disconnect, blocked-output, `fork`/`execve`, PID-reuse and init-parent
  failure analysis; candidate/build integration inventory; and a deterministic
  native plus ARM64/QEMU fixture matrix. Every action path must end with no live
  child and an attributable retained state. Astra must accept the design before
  an interface can be frozen.
- **Stop conditions:** stop on any need to contact Candidate R, discard or
  mutate its current RAM evidence, use an additional live connection, weaken
  boot/candidate attribution, make the supervisor remotely general-purpose,
  respawn after a consumed claim, write persistent storage, change the keyboard
  protocol, or assume an init/Dropbear behavior without exact-source proof.
- **Handoff:** one recommended architecture, rejected alternatives, frozen
  interfaces and ownership, exact source anchors, remaining uncertainties,
  implementation ownership/files, focused acceptance tests and an Astra-ready
  yes/no recommendation. A negative result is complete offline work.

## Sol design candidate

Sol recommends one architecture for specialist review: a direct BusyBox-init
`once` child `/bin/a53-preservation-supervisor` owns one dormant pre-forked
launch capsule. The same capsule PID later executes the exact verified helper;
the supervisor never delegates deadline or reap ownership to Dropbear, a shell,
or a PID/name scan.

The successor `/init` no longer backgrounds `usb-auth`; it mounts and validates
the base system and then execs BusyBox init. The successor inittab contains
direct, no-shell `once` entries for the supervisor, `usb-auth`, and console
status. Exact patched BusyBox init starts `once` entries in file order without
waiting, makes each a direct PID-1 child, does not respawn them, and globally
reaps exited children. Order is not treated as readiness: before configuring
`usb0`, `usb-auth` runs a bounded fixed readiness client which connects to the
supervisor and verifies `SO_PEERCRED`, a live pidfd, UID 0, PPid 1, the
descriptor-backed peer executable and an exact READY identity frame. A stale
file or inittab order alone is never readiness. Supervisor death after readiness
makes later triggering fail before a claim and never causes respawn.

### Startup and dormant capsule

Before READY, the supervisor verifies its UID/parent, live boot/release/CPU and
RAM/noexec `/run` contract, then exclusively creates a per-boot instance
tombstone. It descriptor-opens, hashes and retains its fixed helper, client and
contract inputs. It precreates fixed mode-0600 bounded state, stdout and stderr
storage below a mode-0700 `/run/a53/preservation`, maps, prefaults and locks the
bounded pages, and creates all nonblocking socket, pipe, timer, signal and pidfd
resources.

The supervisor then forks exactly one capsule. The capsule sets and verifies
`PR_SET_PDEATHSIG(SIGKILL)` and parent identity; attaches `/dev/null` and the
precreated stdout/stderr pipes; closes all other descriptors except its private
activation input, CLOEXEC exec-status output and retained helper fd; establishes
cwd `/`, umask 077 and a fixed minimal environment; disables altstack; resets
every catchable disposition to default; clears the full signal mask; and
revalidates those invariants before emitting its fixed capsule-ready record.
It then blocks on one private activation byte. The supervisor exposes READY
only after that complete handshake. No evidence claim exists while the capsule
is dormant.

Pre-forking is the lifetime boundary: after acceptance the enforcing parent
never calls `fork`. It arms the action deadline before releasing the capsule,
owns that exact unreaped PID plus pidfd, and can terminate it if its later
`execveat(helper_fd, "", ..., AT_EMPTY_PATH)` stalls. The retained fd prevents
path replacement. A CLOEXEC status pipe distinguishes successful exec by EOF
from a fixed phase/errno failure. The helper has no process-creation path.

### Trigger and acceptance

The only trigger is a root-owned mode-0600 `AF_UNIX/SOCK_SEQPACKET` endpoint at
`/run/a53/preservation/control.sock`. A fixed static trigger client accepts no
arguments, stdin, path, operation or identity selection. It constructs one
fixed-size v1 request from the root-only candidate contract and live boot ID,
including magic/version/length, one candidate-created admission slot, exact
boot and component digests, zero reserved bytes, and a keyed authenticator. It
sends exactly one packet and shuts down its write side.

The supervisor requires UID-0 peer credentials, one exact untruncated packet,
no ancillary descriptors, exact field/authenticator equality, no second packet,
and EOF within a preaccept timeout. It drains and validates the entire connection
before deciding. Empty, short, long, malformed, duplicate, timed-out or
disconnected input affects connection-local memory only: the claim, capsule,
state and outputs remain byte-identical to READY. Thus a stalled pre-trigger
SSH shell has no preservation effect. One exact packet plus EOF is the proposed
atomic acceptance input; losing the response side after that point does not
cancel the action.

After input validation the supervisor samples `CLOCK_MONOTONIC`, successfully
arms an absolute timerfd, then performs one aligned lock-free release CAS from
`EMPTY` to `CLAIMED_UNRECORDED`. That CAS is the sole acceptance/claim boundary.
The immutable preallocated header already contains boot, candidate, admission,
supervisor and helper identities, so a crash immediately afterward remains
attributable but nonterminal. Subsequent updates use two fixed ledger slots:
payload first and a generation/length/integrity commit word last. No state is
cleared, reset or reused.

### Action ownership and results

The state machine is:

`START -> READY -> CLAIMED -> ACCEPTED -> LAUNCHING -> RUNNING -> TERMINATING -> TERMINAL`

Startup mismatch yields no READY. Every preaccept refusal returns to READY with
unchanged retained state. After acceptance, the activation byte releases the
capsule. Exec-status EOF means running; a fixed error record or early capsule
exit means exec failure. The supervisor continuously drains helper pipes into
preallocated RAM, incrementally commits byte counts and hashes, and never lets
client backpressure delay lifecycle handling. Helper exit 0 or 2, signal,
output overflow, I/O fault and deadline each have distinct terminal enums.

The unchanged helper keeps its internal 15-second limit. The supervisor's outer
cutoff is 16 seconds from the preclaim sample, with TERM then KILL 250 ms later.
After KILL it performs only bounded drain and `waitpid` until the exact child is
reaped; scheduler or uninterruptible delay is recorded as an overrun, never as
proof of cessation. Catchable supervisor shutdown terminates and reaps the
child. Unexpected supervisor death triggers the capsule's already-established
PDEATHSIG; BusyBox init adopts/reaps it. In that forced-parent-death case the
last valid RAM ledger record remains accepted/nonterminal and inconclusive—no
synthetic final receipt. The instance tombstone and `once` policy prohibit a
replacement supervisor or second launch.

Helper stdout/stderr never point at SSH. The supervisor retains the listener,
accepted connection, signalfd, timerfd, child pidfd, activation/status/stream
pipe ends, directory descriptors and mapped state. The helper inherits only
stdin `/dev/null`, stdout/stderr and the required exec state. Nonblocking client
send failure marks transport lost while preservation continues.

Fixed bounded response frames are READY, REFUSED, ACCEPTED, STDOUT_CHUNK,
STDERR_CHUNK and FINAL. Each carries version, sequence, lengths, claim generation
and integrity. The final receipt binds admission, candidate-manifest lineage,
live boot, component hashes/sizes, request hash, claim generation, monotonic
times, exec phase/errno, wait status, termination method, deadline/overrun,
transport state, retained lengths/hashes and ledger integrity. Enumerated
results distinguish refusal-before-effect, accepted/running, complete,
helper-refusal, deadline, exec-failure, output-interrupted and accepted-
nonterminal. Missing, reordered, duplicated or corrupt frames are locally
inconclusive; response loss never changes an accepted request to refusal.

The generic Buildbox package contains no secret. A future private candidate
builder creates the fixed admission slot and root-only capability/contract,
then binds their digest to the final initramfs and external raw/padded image
manifest. Runtime self-verification supplies the live boot and member binding;
a same-process host preflight may additionally check release and critical
members before execing the fixed trigger. A reboot kills that process rather
than carrying a request to another boot.

### Proposed implementation ownership and checks

Reusable keyboard-route ownership would add `resident-preserver.c`,
`preservation-ready.c`, `preservation-trigger.c` and
`test-resident-preserver.py`; extend `build-monitor.sh` with exactly one
`keyboard-resident-preserver` package kind; and extend
`baseline/scripts/buildbox_userspace.py` plus `test-build-routing.py` for that
kind. A new successor experiment—not the closed Candidate R record—would own
its init, inittab, usb-auth, private-contract generator, candidate builder,
validator and mutations. It would add exactly the supervisor, two fixed clients,
unchanged accepted helper and private contract.

Every behavioral cell must pass once on native Linux and once as static AArch64
under pinned QEMU, with no required skip:

1. exact startup/normalization/identity reaches READY; every parent, boot,
   mount, file identity, ownership, mode, link or capsule mismatch does not;
2. the readiness client rejects stale, spoofed, replaced or dead peers and all
   timing races before network configuration;
3. every malformed, partial, duplicated, ancillary-FD, non-root, timed-out and
   precomplete-disconnect request leaves READY bytes unchanged and W dormant;
4. one exact frame plus EOF produces exactly one claim/activation under
   concurrent duplicates;
5. all-blocked/all-ignored/mixed inherited signals yield an empty capsule mask,
   default dispositions, disabled altstack and exact cwd/env/umask/fds;
6. exact fd-based exec succeeds; each injected exec failure and blocked exec is
   terminated and reaped with the correct record;
7. helper success, refusal, signal, one-pipe close, exact output limit,
   overflow, hang and ignored TERM preserve exact hashes and leave no child;
8. client loss before acceptance has no effect, while loss at/after acceptance
   cannot cancel or block retention and child cleanup;
9. supervisor catchable signals at each phase terminate/reap; forced death at
   each phase exercises PDEATHSIG, init-like adoption/reap and honest
   nonterminal classification;
10. pid substitution/reuse cannot redirect pidfd signalling and an unrelated
    process survives;
11. every pre/post claim and ledger fault yields EMPTY or one valid last
    generation, never false terminal success; torn newest state falls back;
12. response parser mutations reject missing, duplicate, reordered, malformed
    or corrupt frames and validate every exact result;
13. the original four files remain unchanged and forbidden syscall/path checks
    exclude evdev, VT, device, storage, reboot, shutdown and unrelated signals;
14. repeated/manual starts and simulated init re-entry cannot re-arm; inittab
    has no respawn; and Buildbox reproducibility, inventory, licensing,
    candidate composition and refusal mutations pass.

Rejected alternatives are per-request fork, self-exec of the supervisor,
shell/Dropbear/host timeout, path exec, daemonization/respawn, ready-file trust,
FIFO/TCP/datagram/signal triggers, caller-selected inputs, modifying the helper,
and a second SSH/export connection. Each loses a required identity, atomicity,
deadline or one-shot property.

Before implementation, Astra must accept four design boundaries: the dormant
pre-fork capsule as deadline-before-action; packet-plus-EOF as the acceptance
boundary; external final-image manifest mapping because an image cannot embed
its own hash; and forced-parent-death classification using PDEATHSIG plus PID-1
reap without fabricating a final receipt. The exact future kernel/config/libc
must also prove `SOCK_SEQPACKET`, `SO_PEERCRED`, timerfd/signalfd, pidfds,
`execveat(AT_EMPTY_PATH)`, `PR_SET_PDEATHSIG`, the bounded mlock budget and
lock-free aligned shared atomics. Missing support or any need for fallback is a
stop, not permission to weaken the design.

Sol recommends specialist design review, not implementation. No fixture, build,
candidate or device action has run. Candidate R remains powered on with its
current potentially unique RAM evidence untouched; this future design cannot
recover it.

## Specialist review 1 and design revision 1

Astra accepted the pre-fork architecture and external-manifest provenance
model in principle but rejected interface freeze. The original text conflated
transport loss with cancellation, treated exec-status EOF as positive evidence,
overstated PDEATHSIG cessation, left a mutable helper inode, and lacked exact
wire/resource/platform boundaries. The following revision supersedes those
conflicting details; unchanged architecture and exclusions above still apply.

### Revised commitment and failure semantics

The first single valid nonzero seqpacket is the complete protocol input. EOF is
not part of acceptance. The single-threaded supervisor retains at most one
control connection and calls `recvmsg` once with one 192-byte iovec,
`MSG_DONTWAIT|MSG_CMSG_CLOEXEC`, and no ancillary buffer. It accepts only when
the return is exactly 192, `MSG_TRUNC|MSG_CTRUNC` are clear,
`msg_controllen == 0`, `SO_PEERCRED` is UID 0, and all fields authenticate.
Return zero—including a zero-length seqpacket record—and shutdown without a
record are refusal-before-effect. The supervisor performs no second receive or
EOF check. Therefore a valid record followed immediately by half-close or full
close is accepted; that close can only remove the response channel.

Request v1 is exactly 192 bytes with big-endian integers: bytes 0--7 are
`A53PRV1\0`; 8--9 version 1; 10--11 fixed trigger opcode 1; 12--15 length 192;
16--31 admission UUID; 32--47 decoded boot UUID; 48--79 candidate-contract
SHA-256; 80--111 supervisor SHA-256; 112--143 helper SHA-256; 144--175
HMAC-SHA-256; and 176--191 zero. The MAC covers the fixed domain
`a53-preserve-trigger-v1\0`, bytes 0--143 and bytes 176--191.

During that dispatch the supervisor samples monotonic time, arms the absolute
timer, then release-CASes one aligned lock-free 32-bit claim from EMPTY to
CLAIMED before servicing hangup. The CAS—not socket receipt—is local commitment
of the already complete record. Concurrent connections are serialized; only
the first CAS activates the capsule. There is necessarily a crash interval
between socket receipt and a RAM claim: send-plus-close without ACCEPTED and
without a readable ledger is `outcome-unknown`, never proof of refusal or
acceptance, and the host one-use budget remains consumed. A requirement to make
network receipt and tmpfs state one transaction would reject this architecture.

After CLAIMED, disconnect, EPIPE, reset, blocked response or client death sets
transport LOST but never cancels the action. The supervisor proceeds until the
exact child is reaped or remains honestly nonterminal. No record is terminal
while the child lives. Catchable supervisor shutdown performs TERM/KILL/drain/
reap. Supervisor SIGKILL leaves the last accepted-nonterminal slot;
PDEATHSIG requests child death but does not prove or bound it, and PID 1 can
reap only after exit. An uninterruptible task may therefore remain nonterminal
without a finite bound; it can never be promoted as ceased or successful.

The 12-byte exec-error record contains magic `A53E`, version 1, phase EXECVEAT
and errno. A valid record proves returned exec failure; malformed/partial data
is ambiguous. CLOEXEC EOF proves only absence of that record. RUNNING requires
the exact first 98 helper stdout bytes through `__PRESERVE_HEADER_END__`; a
terminal child without valid error record or complete helper header is
LAUNCH_AMBIGUOUS. Complete helper classification still requires exact terminal
framing, output validation and wait status.

The supervisor sets SIGCHLD to default, rejects inherited ignore or
`SA_NOCLDWAIT`, installs its fixed dispositions, then blocks SIGCHLD, TERM, INT,
HUP and QUIT before signalfd and fork. It observes with
`waitid(P_PIDFD,...,WEXITED|WNOHANG|WNOWAIT)`, drains pipes, then calls
`waitpid(exact_pid,...)` exactly once and compares statuses. The capsule sets
PDEATHSIG, checks its recorded parent immediately and again before READY, and
rechecks PDEATHSIG. Its ordinary executable has no set-ID bits or file
capabilities; the fixture must prove PDEATHSIG survives exec.

### Sealed helper and fixed RAM ledger

A retained source fd was insufficient because it pinned an inode, not contents.
Before READY the supervisor creates a
`MFD_CLOEXEC|MFD_ALLOW_SEALING` memfd, copies exactly 66,672 verified helper
bytes, sets mode 0700, rewinds and rehashes, then applies and verifies
`F_SEAL_WRITE|F_SEAL_GROW|F_SEAL_SHRINK|F_SEAL_SEAL`. The capsule executes only
that fd with `execveat(AT_EMPTY_PATH)`. Memfd creation, sealing, content/mode
verification or executable policy failure is startup refusal; there is no inode
or path fallback.

There is no mlock assumption. Before READY the supervisor requires `/proc/swaps`
to contain only its header, allocates fixed tmpfs files with `posix_fallocate`,
maps them shared, writes/prefaults every page and reads them back:

| File | Bytes |
| --- | ---: |
| `state.bin` | 16,384 |
| `stdout.bin` | 524,288 |
| `stderr.bin` | 16,384 |
| **Total** | **557,056** |

`state.bin` has one immutable identity page, one control page and two 4-KiB
ledger slots. The aligned control-page `_Atomic uint32_t` must report lock-free
before READY; only the single supervisor thread writes it. Each slot has a
32-byte header, at most 4,060 payload bytes and a commit word at offset 4,092.
The writer clears the inactive commit, writes payload/header/CRC32C, issues a
release fence and release-stores token `0xC01117ED` last. Recovery acquire-loads
both, validates all fixed fields, reserved bytes, length, generation and CRC,
then chooses the highest valid generation. A torn newest slot falls back to the
older valid slot. CLAIMED without a valid postclaim slot is
CLAIMED_UNRECORDED. Terminal state additionally requires `child_reaped=1` and
exact wait status. Output digests cover committed prefixes only.

Every response seqpacket is at most 4,096 bytes: a fixed 32-byte header and at
most 4,064 payload bytes. Its header binds magic/version/type/flags, payload
length, sequence, claim generation and CRC32C over fixed header bytes plus
payload. Stream payloads start with an 8-byte offset/length and carry at most
4,056 data bytes. One session permits at most 130 stdout frames, five stderr
frames, one fixed 48-byte ACCEPTED and one fixed 320-byte FINAL: at most 546,504
wire bytes. The event loop services signalfd, timerfd, pidfd, exec status,
stdout and stderr before client output; per iteration it drains at most 64 KiB
per child stream, sends at most four frames/16 KiB, receives once per ready
control fd and accepts once. Preaccept connection lifetime is two seconds; no
post-READY operation may block.

The separate readiness seqpacket socket is closed/unlinked after one successful
handshake. Its fixed client verifies peer credentials, live pidfd, PPid 1,
descriptor-opened peer executable and exact READY frame before `usb-auth`
configures the network. The existing kmsg capture background function and PID-1
ownership are unchanged.

### Exact platform evidence and remaining executable gate

The exact foundation configuration is 109,997 bytes with SHA-256
`194834d90eb2443f4b14ba8f2078ba16fe0c63f69088fcc8c063fe25af01c410`.
It has built-in UNIX sockets, signalfd, timerfd, shmem, memfd, procfs, futex,
POSIX/high-resolution timers, 64-bit ARM64 ELF and tmpfs. The exact 2,380,223-byte
System.map SHA-256 is
`07bf653ea74c2bae7e8747430d346b98aed850f3b24cf400a68db9612b6a7035`.
A read-only Buildbox recheck of that retained package found exact ARM64 syscall
symbols `pidfd_open`, `pidfd_send_signal`, `memfd_create`, `execveat`,
`signalfd4` and `timerfd_create`. Candidate R's admitted guards observed a
header-only `/proc/swaps`; the future candidate must re-establish this before
READY.

These build artifacts prove inclusion, not semantics. The pinned musl 1.2.6
archive remains
`d585fd3b613c66151fc3249e8ed44f77020cb5e6c1e635a616d3f9f82460512a`.
Before implementation admission, native Linux and static AArch64/QEMU fixtures
must prove the exact seqpacket rules (including zero-length, full close,
half-close and truncation), executable sealed memfd, PDEATHSIG across exec,
pidfd wait/signal, signal normalization, atomics/ledger, resource bounds and
every lifecycle failure. QEMU remains software evidence, not proof on Gemini.

### Specialist disposition

Astra accepted revision 1 for architecture and interface freeze. The CAS
commit boundary, postaccept disconnect continuation, honest nonterminal states,
positive 98-byte helper-start witness, sealed helper image and numerical
resource limits resolve the earlier design blockers. Production implementation
is not yet admitted: a fixture-only gate must first pass on native Linux and
static AArch64/QEMU. That gate must explicitly suppress SIGPIPE on supervisor
response writes and prove that forced parent death or uninterruptible execution
never produces a terminal/ceased classification without observed reap.

The exact design result is
[`results/candidate-successor-resident-supervisor-design.json`](results/candidate-successor-resident-supervisor-design.json).
The next bounded contract is
[`RESIDENT_CAPABILITY_WORK_ITEM.md`](RESIDENT_CAPABILITY_WORK_ITEM.md). Candidate
R and its current RAM state remain outside both offline tasks.
