# Keyboard capture and delivery: retained-observer decision

Status: bounded source and delivery review complete; minimum delta proposed.
No new target implementation, helper build, exact execution or device action
was performed for this decision. The selected baseline and first physical boot
remain unchanged. Actual keyboard metadata is a later runtime predicate and
does not prevent preparing the remaining host/target contracts offline.
The later [minimal monitor handoff](MONITOR.md) records the source-only
implementation, host tests and separately reviewable size/library proposal.

## Existing work to retain

The validated baseline userspace package already contains the static ARM64
`keyboard-observe` binary: 774,952 bytes, SHA-256
`51ef03def5461b2c13367906b3184a2dae14ca2f7ba7e835740be6a7268fa223`.
Its package manifest is
`dfeb746505b7ad01423e91e952e76620f845b048ae2e8c5cf8a311e0d4443e60`,
built from `e9c028005b88ef8536ecb58c095e8d172253fa12`. See the owning
[baseline preparation evidence](../baseline/PREPARATION_RESULTS.md).

| Retained source | SHA-256 |
| --- | --- |
| `keyboard-observe.c` | `f46eff614c6cfbabc2864148560636e7d26d9dfd693908d21f3284ae45c1bd8c` |
| `protocol.h` | `83b23042abdc90b26b4f880f4a926ddb8aa1701217719adf9e9ba68bb6d93455` |
| `protocol.json` | `5dd8b42b00a60041a9d5cb85f586ce639af6b62172a5488d8c0b73a0ed764306` |
| `classify.py` | `be55d4d816c4c0709bed44dd77057b404aa3baf15d23aa7be46e966c98aaefa9` |

The observer owns the 202-second guided sequence, per-window monotonic checks,
64-event/128-byte ceilings, dropped-event and held-key refusal, nonblocking
evdev/VT/stdout, exact device/VT/function-string/meta checks and attempts termios
restoration on normal exit and handled INT/TERM/HUP/PIPE. Full map verification
belongs to the launcher. It forks and executes no descendants.
Source-derived worst-case formatted stdout is conservatively 88,722 bytes,
including both possible footers, below 96 KiB. This is a source bound, not a
measured successful device capture. A cancellation after the last window is
not rechecked before the successful footer; external cancellation must still
withhold acceptance. Existing classifier framing and restoration evidence stay.

## Why existing BusyBox primitives do not close the lifecycle contract

The retained binary and corresponding Ubuntu source package are pinned in
[BUSYBOX_PROVENANCE.md](../baseline/BUSYBOX_PROVENANCE.md). This review matched
the official upstream and Ubuntu packaging archives against the retained source
descriptor (SHA-256
`ffbee3f0383ea5a3e77033c2bcc1978dc9ae00ff8c9d0a362ee32f6e84254be8`).
Archive bytes were inspected in memory; no source tree was installed or built.

The exact package source shows:

- `coreutils/timeout.c:50–62,101–152`: a detached watcher uses relative one-second
  sleeps, signals a numeric PID, emits no timeout/signal result and never waits
  for the observer. Its stdio is redirected, but extra inherited descriptors
  need not be closed by that daemonization path.
- `util-linux/setsid.c:57–81`: one path forks and returns success immediately.
- `shell/ash.c:4646–4740`: a trapped signal can end `wait` before child reaping.
- `coreutils/tee.c:93,114–120`: stdout is written before the named RAM file;
  default SIGPIPE and stalled forwarding can prevent that chunk's retention.

These locators refer to the exact
[upstream archive](https://archive.ubuntu.com/ubuntu/pool/main/b/busybox/busybox_1.36.1.orig.tar.bz2),
checked with the corresponding
[Ubuntu packaging archive](https://archive.ubuntu.com/ubuntu/pool/main/b/busybox/busybox_1.36.1-6ubuntu3.1.debian.tar.xz).
Packaging patches do not change those lifecycle properties. Source inspection
also identifies a possible PID-reuse race between liveness checks and later
numeric-PID signals; this is a structural inference, not a measured exploit.

Thus plain `timeout -s TERM -k 4 210` plus a shell/tee cannot establish the
existing TERM-by-210, KILL-by-214 and reap-by-215 evidence contract. A successful
timing example cannot repair absent identity or termination reporting. A broad
repeat of known-ineligible timeout fixtures is not a prerequisite for packet
preparation. Its detached watcher also escapes a group-only test runner;
any decision-changing future timeout experiment must first have independently
reviewed descendant containment, such as a disposable PID namespace.

The retained Dropbear no-PTY path supplies pipes (`svr-chansession.c:768–788`,
`dbutil.c:274–365`). Channel cleanup alone does not prove delivery of HUP or
observer reaping. This source was read from the retained release archive,
SHA-256 `e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81`.
Actual disconnect behavior remains an exact integration test, not an assumption.

## Minimum proposed target delta

Keep the retained observer and protocol unchanged. Narrow the existing private
supervisor proposal to one fixed observer child, direct RAM captures, bounded
forwarding and lifecycle status. Extending the observer with its own timer
would still leave no independent hard-termination/reaping witness and would
change a retained binary. A general process/descendant framework is unnecessary.

The minimal monitor must:

- Verify the separately admitted source/input contract and consume one fixed
  RAM claim before spawning; use exclusive private output files and no arbitrary
  command or helper path. Close unrelated inherited descriptors.
- Run only the exact `/bin/keyboard-observe --capture eventN 13 MINOR`. Preserve
  stdout/stderr directly in verified RAM. Bound regular files and status under
  the existing file-size policy; excess, short or incomplete evidence refuses.
- Forward only already-retained stdout, nonblockingly, often enough to carry
  the observer's genuine ten-second activity. Forwarding failure cancels the
  child, retains RAM evidence and withholds success. Add no keepalive, reconnect
  or replacement traffic to hide an inactive capture.
- Hold the direct child's identity through `waitid(WNOWAIT)` until signaling
  finishes, then reap it. Use one monotonic schedule and record actual TERM,
  KILL and reap times, cancellation and deadline violations. A late or unreaped
  child is inconclusive; no success is inferred from elapsed time alone.
- Require clean normal lifecycle, the existing restored footer, full transcript
  validation and postflight evidence together. Preserve raw failed captures
  before separately admitted recovery; the kmsg-only export cannot stand in for
  preservation of these additional private keyboard files.

The richer existing private supervisor source
`f43dad184bc5aab1728f753df5222df03271a2c759e8df4a602d3a9333957f02`
and its prior host fixtures remain historical preparation evidence. They do
not prove this proposed reduction or admit its production entry. No second
observer, metadata binary or general archive/diagnostic framework is proposed.

## Delivery is an explicit feasibility gate

The baseline init mounts `/run` with noexec. A later monitor would need a
separately reviewed executable RAM-rootfs location, verified from the actual
mount/resource state, with exclusive creation, exact input byte count,
cryptographic readback and
source/binary binding before use. No existing candidate member may be replaced.
The admission must bind the added runtime file independently of the unchanged
boot image and must preserve the baseline's authentication and candidate checks.
There is no mount change or current delivery permission in this proposal.

The exact BusyBox shell fixture measured `ulimit -f 1` as a 512-byte unit;
the configured inherited `ulimit -f 256` therefore implies a 128 KiB ceiling on
files grown by session descendants. It does not limit execution of the larger
observer already present in the initramfs. Conventionally linked retained glibc
helpers are 702,792 to 774,952 bytes, so small C source does not establish
deliverability. A monitor must fit that existing ceiling or receive a separately
reviewed policy/design
decision; the ceiling must not be raised silently. A small static/freestanding
build from pinned inputs is a possible approach, not a completed result. Binary
size, ABI, license, resource limits and exact execution must be checked in an
assigned build/test window before any runtime delivery contract is frozen.

The server's existing 60-second idle and 360-second maximum session limits stay.
The 202-second observation and all pre/post/preservation work must also fit the
original 600-second logger lifetime, including real owner delays. Offline action
ceilings do not establish remaining logger lifetime on an actual boot.

## Meaningful exact execution proposal

No following test has been run by this decision. Reuse retained binaries where
they answer the question; publish any changed minimal monitor and bounded
fixtures before an assigned Buildbox window. No unchanged candidate retest is
needed for these userspace checks.

| Test boundary | Useful result |
| --- | --- |
| Retained observer, malformed/noncanonical arguments; canonical arguments only with stdout already closed | Proves exact existing argument/FD refusal; opens no real input/VT device |
| New minimal monitor, one fixed harmless child | Proves exclusive claim, exact argv, direct retained bytes, status and normal reaping |
| Child ignores TERM, exits nonzero, or closes its output descriptors while remaining alive | Distinguishes forced/late/incomplete termination from a normal pass; output completion cannot replace waiting for the child |
| Timely and late INT/TERM/HUP/PIPE, including after apparent child completion | No cancellation may become a successful lifecycle result |
| Actual forwarding pipe closes or stalls | RAM capture survives; monitor cancels, bounds cleanup and records incomplete delivery |
| Inherited 128 KiB file limit and executable RAM fixture | Validates real binary delivery size, output/status limits and refusal paths without changing mounts |
| One full 202/210/214/215-second timing run after the reduced implementation passes bounded cases | Measures the final monotonic schedule and actual reap time, rather than only scaled host timing |

Successful evdev/VT capture and restoration require an explicitly isolated
compatible test environment or admitted device evidence. Argument/preflight
refusals do not prove those ioctls. Do not create real device nodes, access a
host VT or add a syscall-emulation framework merely to claim a positive test.

## Actual runtime predicates retained

Admission still needs the accepted first authenticated baseline and attributable
changed-ID recovery through the shared verifier, matching current deployment
and boot identity, exact event/devnum/capability bytes, reviewed matrix/AW9523
resource ancestry, foreground tty1 and map/meta policy, complete process/FD
reader exclusion, naturally exited console-status worker, exclusive custody,
stable power, and compatible session budgets. If available read-only interfaces
cannot prove a resource link, report it unresolved rather than inventing it.

The retained observer's checked preflight and complete footer can provide its
VT/Unicode/meta witness; a new metadata helper is not automatically required.
The current metadata/reader values remain unset. Raw owner input stays private;
only reviewed summaries may be published. The packet remains preparing and
unselected. Ordered work continues to belong solely to the project roadmap.
