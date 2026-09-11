# Bootstrap failure diagnostics

Status: implemented and tested offline; the [second session](EXPORT_SESSION_2.md)
now binds the validated replacement filesystem and container, without deployment
or physical selection. The [first attempt](EXPORT_ATTEMPT_1.md) produced neither
a USB export nor an attributable startup failure. Console-only messages could
not discriminate startup refusal from an earlier boot failure.

## Existing logging path

The shell now mounts devtmpfs first, verifies `/dev/kmsg` is a character node
with major/minor `1:11` and no symlink, and opens it once as descriptor 3.
It records the next shell operation before performing it. After mounting proc,
records include the kernel boot UUID. The first record instead says `unknown`.
Each bind and read-only remount has its own fixed label. A caught shell failure
adds one stop record and parks; traps are disabled before that final record.
Failure to print the fallback console message also leaves the shell parked.

Python verifies that the inherited descriptor still identifies `1:11`, and
logs entry, passed preflight, snapshot/USB entry, waiting for the host, and
queued export. On a caught failure it logs the last fixed stage and `stopped`. Stages distinguish
session/source/input checks, each expected runtime field, process/network
isolation, capture layout/read, ACM ownership/node/configuration/open, host
request and snapshot send. They contain no observed field value, exception
message, firmware/calibration bytes, private hash or command-line contents.
Each Python record obtains and canonicalizes the current boot UUID.

There are at most 20 shell records, including the stop record, and eight Python
write attempts. Python consumes its budget before each attempt and never
retries a partial write. Current export control flow uses at most seven attempts
including a stop record. Each application record is at most 192 bytes; the
kernel adds its normal log prefix. A logging failure before preflight prevents
export and parks. Failure of the final stop log is swallowed so it cannot make
PID1 exit. No periodic log, reboot, console-level change or new daemon is added.

The prefix `<11>` requests LOG_USER at error severity. In the pinned native
source, `devkmsg_write()` sends this to `printk_emit()`. The registered pstore
console calls `pstore_simp_console_write()`, which selects the existing CONSOLE
backend and its `cprz` ring. The capture-mode PMSG snapshot and exclusion path
are separate. This uses ordinary kernel logging, not a new physical mapping,
reserved-memory slot, pmsg write, capture initializer or clear operation.

The source review used the prepared 46-patch tree bound by
[full-kernel-inputs.json](full-kernel-inputs.json):

| Source | SHA-256 |
| --- | --- |
| `kernel/printk/printk.c` | `6752cfe68485c45754aafc69d69a9dca89b5bac7760ce7ffa846f6204b60c754` |
| `drivers/char/mem.c` | `b693f13ce4edf0f0e5e3553ddf0d86fc779283c2ce6442972731cfbe31d45390` |
| `fs/pstore/platform.c` | `faff4a24ea2a298ba8fe267f04266665bc75e0241dc67718390708e587e73474` |
| `fs/pstore/ram.c` | `09761efea84dd9b9b8d398bf7171ebff901d2f5df6a8b649ecf0ec6a0e0c3f4f` |

## Validation and device boundary

Host tests passed: 16 startup cases and four bridge groups. The packaged ARM64
Python in an isolated RE-VM chroot also passed those checks and the ten serial
exchange cases. Tests cover exact error-stage selection, wrong log descriptor,
finite write budget, partial-write refusal, and parking after kernel-log and console failure
without proceeding to preflight or publishing private exception text. The
duplex bridge still performs exactly its existing three USB control writes;
its log sink and USB identities/controls are injected.

The actual updated BusyBox shell ran in an isolated RE-VM mount/PID namespace
using the preceding verified compact filesystem. The complete mount sequence
reached its Python boundary with 19 records. Injected sysfs and pstore mount
failures stopped at the correct stage with three and four records respectively.
The probe redirected descriptor 3 to its captured stdout, omitted console open
and SysRq write, and replaced the park loop with test exit 42. At the Python
boundary, the actual BusyBox `env` command launched the packaged Python with a
test entry that verified PID1, the inherited descriptor and cleared environment,
then exited zero. Thus it tested the shell and mounts without writing
the VM kernel log or operating a PDA. Extracted roots/namespaces were removed.
Shell syntax and ShellCheck passed. No kernel sources or configuration changed;
no kernel rebuild or hardware result is claimed.

A later session must bind the updated sources to a new UUID, filesystem and
verified container before deployment. The ordinary console ring can wrap,
log-level filtering can suppress records, and a hard failure before devtmpfs or
the log descriptor opens still has no new userspace record. An absent marker
therefore remains inconclusive. Preserve retained logs promptly after the
owner-approved recovery, without interpreting a timeout as restart approval.
A recovered marker must be joined to its boot UUID and exact deployment;
it identifies a reached stage, not successful hardware support or proof that
the next operation completed. The unchanged first image must not be repeated.
