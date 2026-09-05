# Read-only eMMC session packet

## Record and readiness

| Field | Value |
| --- | --- |
| Queue item | `emmc-readonly` |
| Parent | [Owner-away preparation](../README.md#emmc-readonly) |
| Preparation | `preparing`; protocol and host fixtures implemented |
| Device state | `unselected`; no physical access performed |
| Implementation scope | This directory only |
| Candidate | Unset; must be the authenticated A53 baseline's exact accepted candidate |
| Installer/receipt | Reuse that baseline's current guarded installer and immutable full-readback receipt |
| Reviewer/custodian | Unassigned; no custody or hardware admission inferred |

This packet is **not conditional-ready or ready**. Exact candidate, BusyBox,
observation-shell, independent log capture, authenticated transport/deadline,
serviceability and recovery identities remain missing. Its host fixtures are
useful implementation evidence, not substitutes for those gates. The
[queue](../../../project/experiment-queue.json) inventories readiness; the
[roadmap](../../../docs/ROADMAP.md) alone schedules work.

## Hypothesis and existing evidence

One software-visible read of the entire live-GPT-selected 16 MiB `boot2`
partition produces the exact installed candidate's padded checksum, without
targeted controller errors or loss of authenticated A53 serviceability.
It requests no mount, storage write, sysfs write, load, thermal observation,
clock/rail change or CPU8/9 admission.

The historical [AW observation](../../2026-07-25-emmc-development/results/candidate-aw-runtime-20260726.txt)
read precisely 16 MiB from live-resolved `boot2` and matched the padded image.
Its profile is historical-only and is **not** this packet's kernel foundation.
The later [PWRAP runtime](../../2026-09-04-mt6797-pwrap-reset-serviceability/results/runtime-attempt-1-pwrap-serviceable-20260904.txt)
enumerated one MMC card, 33 partitions and `122142720` 512-byte sectors;
CPU0–7 were online and CPU8/9 offline. The
[PWRAP recovery](../../2026-09-04-mt6797-pwrap-reset-serviceability/results/native-recovery-20260904.txt)
then completed one full 16 MiB `boot2` checksum and matched its installed
candidate. These observations justify the range and one-read count. They
provide no measured read latency: the 20-second deadline is a conservative
refusal limit chosen for this protocol, not an established performance result.

The PWRAP candidate's exact inputs are audited by the baseline owner. A matching
profile name, current package timestamp, AW configuration or V4 thermal result
cannot replace that audit. No new kernel/DT/config delta is requested here.

## Dependencies and attribution

Before physical admission, all of the following must refer to the exact frozen
authenticated baseline candidate and protocol:

1. The first baseline boot passed intended-key authentication, rejected-key
   authentication, separated console/log serviceability, CPU topology, PWRAP,
   supplies and MMC identity.
2. That boot returned to the known-good OS with a changed boot ID using the
   reviewed recovery path. Its recovery evidence is accepted, not just planned.
3. The baseline's package, composed DT, resolved config, initramfs, raw and
   padded container, BusyBox, observer, log-capture and installer digests are
   frozen; guarded installation and full-partition readback bind the selected
   padded checksum to the live label. Source rights are reviewed.
4. The custodian has admitted this specific single-read session, established
   stable power and a quiet RAM-only userspace, and bound a new mainline boot ID
   to that deployment receipt through the authenticated baseline interface.

The eMMC session uses one subsequent boot of the same candidate. The independent
new read observation makes this useful; boot-marker text does not. Keyboard is
independent and ten completed cold boots are not prerequisites. Sharing this
session with keyboard or Wi-Fi has no admission here; their ordering,
interference and combined budgets must first be reviewed explicitly.

The observer arguments are the accepted live mainline boot ID, exact release,
receipt's padded SHA-256 and candidate BusyBox SHA-256. Arguments and a complete
frame do not themselves prove deployment or authentication. The host must keep
the receipt, candidate inventory, capture transcript and dependency records
together and reject identities that disagree. No CID, serial, partition UUID,
card contents or credential is needed in the public record.

## Finite protocol and refusal boundary

| Resource | Frozen protocol limit |
| --- | --- |
| Physical selections | One admitted `boot2` selection for this packet |
| Target | The unique live GPT `PARTNAME=boot2` partition of the observed `mmcblk0` MMC card |
| Payload range | Partition-relative offset 0 through 16777215 inclusive |
| Requested payload | 32768 sectors, 16777216 bytes, one `dd` opening as input |
| Repeat allowance | Zero; failure, interruption and timeout consume the attempt |
| Read deadline | `timeout -s KILL 20`; no retry or deadline extension |
| Overall remote command | Required 40-second outer deadline in baseline authenticated capture, still unvalidated |
| RAM scratch | One fixed `/run/gemini-emmc-readonly` directory; two bounded kernel-log snapshots, digest/status only |
| Storage writes/mounts | Zero |
| CPU/load/thermal actions | Zero; CPU0–7 online, CPU8/9 offline throughout |
| Recovery | One baseline-reviewed recovery request; owner-assisted fallback only on its stated failure branch |

The 16 MiB budget counts bytes explicitly requested by this observer. Earlier
kernel probing/GPT enumeration and block-layer implementation reads are not
measured by it. Buffered reads may use cache; success is a software-visible
integrity observation, not proof of physical-media traffic, throughput, card
health or a stress result. There is no cache-dropping, direct-I/O, writeback,
flush or filesystem operation in the observer.

[`observe.sh`](observe.sh) checks live kernel/boot/BusyBox identity and CPU
topology; requires the init mount namespace, a RAM root, explicit tmpfs `/run`,
no block-backed mount anywhere, no active swap, and no target/parent holders.
It resolves the unique GPT label without assuming `p30`, matches device-node
major/minor to sysfs and class links, requires the known host/card/parent size,
and requires exactly 32768 target sectors within the parent. It repeats these
checks immediately before and after the read and refuses prior controller
errors. These observations do not lock mounts or protect against another root
process: the custodian must keep the session quiescent.

After preflight, an atomic fixed-name RAM directory consumes the invocation.
The trap removes only transient status, digest and log files; the directory and
`consumed` tombstone remain until reboot. A later invocation refuses that state.
Hard interruption may leave transient files there; they are small, private RAM
state and are **not** cleared to permit a retry. Once the host dispatches this
operation it must likewise preserve its attempt record and never dispatch it
again on reconnect. A reboot does not renew this experiment's consumed budget.

The device bytes flow directly from input-only `dd` to `sha256sum`, never into a
capture file or transcript. `dd` status travels separately; absent status,
short reads, nonzero status or wrong checksum cannot pass. A timeout cannot
guarantee that Linux kills a task stuck in uninterruptible I/O. At either
deadline the attempt is consumed, the host stops issuing commands, and the
custodian follows recovery instead of attempting more reads.

## Baseline interface needed before freeze

The RAM userspace must contain the exact validated `/bin/busybox` and support
`sh`, `cat`, `cut`, `grep`, `awk`, `find`, `readlink`, `stat`, `uname`, `sha256sum`,
`mkdir`, `rm`, `dmesg`, `timeout`, `dd` and `date` with the used options. The
host protocol must verify observer bytes before dispatch, pin SSH host and
intended user-key identities, use no password/netcat fallback, retain a private
attempt record before sending the command, enforce the 40-second overall
deadline, and stop without retry on authentication or transport failure.

The separate logger must preserve the complete relevant kernel messages before,
during and after the read and expose gaps, dropped records or overflow. The two
`dmesg` snapshot hashes and regex error count in this packet cannot prove log
continuity. Review that logger's exact record format and error classification
before declaring this packet prepared. Baseline serviceability observations
before and after must also show intact PWRAP/supplies/MMC, CPU topology, USB and
console. No new generic transport, installer or recovery framework is added.

Illustrative command shape, **not an admitted invocation**:

```sh
/bin/busybox timeout -s KILL 40 /bin/sh /run/reviewed/emmc-observe.sh \
  "$ACCEPTED_BOOT_ID" "$EXACT_KERNEL_RELEASE" \
  "$RECEIPT_PADDED_SHA256" "$CANDIDATE_BUSYBOX_SHA256"
```

The observer should be included in the candidate before its first baseline
boot, at the baseline owner's reviewed path; changing its bytes later
invalidates frozen candidate/protocol attribution. `/run/reviewed` above is
only an interface illustration, not a currently provisioned path.

## Capture, classification and recovery

Use the baseline's pinned authenticated capture to keep stdout and stderr
separate. The stdout frame contains only reviewed metadata, checksums and
counters. Keep transport logs, host credentials and any full raw kernel log in
an access-restricted Git-ignored experiment artifact directory until reviewed.
Publish only sanitized receipt identities, boot IDs, partition name/number,
range/count/deadline, digests, classifier outcome, errors and recovery result.
No new partition backup is made by this packet.

[`classify.py`](classify.py) rejects duplicate, missing, malformed, unknown,
prefixed and incomplete frames. Invoke it with identities independently obtained
from the accepted receipt and authenticated boot:

```sh
python3 experiments/2026-09-05-owner-away-experiment-preparation/emmc/classify.py \
  "$PRIVATE_CAPTURE" --boot-id "$ACCEPTED_BOOT_ID" \
  --kernel-release "$EXACT_KERNEL_RELEASE" --padded-sha256 "$RECEIPT_PADDED_SHA256" \
  --busybox-sha256 "$CANDIDATE_BUSYBOX_SHA256"
```

| Observation | Classification and decision |
| --- | --- |
| Guards refuse before reading | No transfer conclusion; inspect metadata/offline contract; no automatic retry |
| Nonzero read status, digest mismatch or targeted controller errors | Fail the bounded read claim; block dependent storage work and inspect preserved evidence |
| Interrupted frame, missing identity/log continuity, deadline, lost authentication or serviceability | Inconclusive; consume attempt, stop and recover |
| Exact digest, clean targeted messages, successful guards | `read-integrity-pass` only; require independent log and before/after serviceability acceptance |
| Above plus accepted independent logs/serviceability and changed-ID known-good recovery | Experiment pass for this one read/range/candidate only |

Recovery reuses the baseline's reviewed identity-bound procedure. This observer
does not reboot, power off or write a partition. Preserve the one read result
before requesting recovery, collect changed-ID known-good serviceability, and
record any changed behavior or need for owner intervention. This packet adds
no post-recovery partition checksum: a baseline recovery contract that needs
one must account for it separately before the combined session is admitted.
Failed or inconclusive recovery prevents this packet from passing.

## Owner session card — draft, not selected

After the prior baseline boot and its recovery have passed, the custodian will
identify the exact installed candidate and ask you to select `boot2` once using
the established physical key sequence. Leave the USB cable and stable power
connected. The baseline console should appear and the authenticated USB link
should become available. This test requires no typing or cable change; the
read observation has a 40-second command ceiling once it begins. Do not select
another queued experiment or repeat a failed attempt.

If the expected console or USB connection does not appear, or you see unusual
heat, charging behavior or a reset loop, stop. Follow the already reviewed
known-good recovery card supplied by the custodian. Total owner time and the
exact physical selection/recovery text remain unset until that baseline card
is validated; they must not be invented from this protocol's read deadline.

## Offline validation and remaining handoff

Run [`test_packet.py`](test_packet.py), Bash syntax and ShellCheck. The fixtures
transform only system-path literals into one managed temporary root and mock
BusyBox/hardware identity/read operations. They exercise the shell flow on the
host and always clean their temporary root. They do not run candidate AArch64
BusyBox or establish its timeout, applet, mount-namespace or kernel behavior.

The optional exact-app mode runs the outer and nested shell and ordinary
text/file/hash applets through the specified actual BusyBox and QEMU:

```sh
EMMC_TEST_BUSYBOX="$PINNED_BUSYBOX" EMMC_TEST_WORK_ROOT="$MANAGED_TEST_ROOT" \
  python3 experiments/2026-09-05-owner-away-experiment-preparation/emmc/test_packet.py
```

The work root must already exist; each test creates and cleans a private child.
`EMMC_TEST_QEMU` optionally selects the emulator (default `qemu-aarch64` on
PATH). `EMMC_TEST_BUSYBOX_SHA256` optionally requires an expected digest; the
actual binary digest is always reported. The candidate audit must independently
match that reported identity. Host mode remains the default when no binary is
supplied; its two real timeout tests are explicitly skipped.

Hardware `readlink`/`stat`/`uname`/`dmesg`, partition `dd`, and the observer's
20-second timeout effect stay mocked. Exact mode separately exercises the real
timeout applet with a harmless local BusyBox sleep and an invalid duration;
each runs in a fresh host process group with an independent four-second cleanup
deadline. This tests interruptible userspace behavior, not a blocked kernel MMC
operation. The dispatcher refuses non-fixture paths, symlink escapes, unknown
applets and changed nested shell/awk programs using explicit checks that remain
active under optimized Python. No hardware device path is passed to an applet.

Because the observer's transformed BusyBox path names that dispatcher, its
self-hash assertion covers the dispatcher. The actual BusyBox digest is a
separate test identity, not evidence that the unmodified device observer's
self-identity gate ran. QEMU applet tests remain distinct from complete
unmodified Linux observation-shell, authenticated transport and physical I/O
validation. No exact-mode result is claimed by adding this option.

Before changing readiness, record exact-file hashes and parent revision,
complete independent review, run equivalent success/refusal/interruption cases
with the exact candidate shell and applets on the authorized build environment,
and validate the baseline capture/deadline/log and recovery adapters. A local
kernel rebuild is neither needed nor authorized for these protocol-only files;
any changed candidate packaging remains with the baseline owner through
Buildbox. No device execution has occurred here.

Relevant candidate/protocol changes, withdrawn prerequisites, consumed attempt,
missing custody, or superseding results invalidate readiness. This does not
establish filesystem safety, persistent-root use, broad eMMC reliability,
suspend, permission to write storage, or the cumulative cold-boot release gate.
