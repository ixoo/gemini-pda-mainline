# Bootstrap failure diagnostics

Status: implemented and tested offline, then deployed for the
[second attempt](EXPORT_ATTEMPT_2.md). That boot produced neither USB export nor
recovered diagnostic markers; its kernel/startup stage remains inconclusive.
The [first attempt](EXPORT_ATTEMPT_1.md) also produced neither
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
use a separate zone, but share backend registration as described below.
This uses ordinary kernel logging, not a new physical mapping,
reserved-memory slot, pmsg write, capture initializer or clear operation.

The source review used the prepared 46-patch tree bound by
[full-kernel-inputs.json](full-kernel-inputs.json):

| Source | SHA-256 |
| --- | --- |
| `kernel/printk/printk.c` | `6752cfe68485c45754aafc69d69a9dca89b5bac7760ce7ffa846f6204b60c754` |
| `drivers/char/mem.c` | `b693f13ce4edf0f0e5e3553ddf0d86fc779283c2ce6442972731cfbe31d45390` |
| `fs/pstore/platform.c` | `faff4a24ea2a298ba8fe267f04266665bc75e0241dc67718390708e587e73474` |
| `fs/pstore/ram.c` | `09761efea84dd9b9b8d398bf7171ebff901d2f5df6a8b649ecf0ec6a0e0c3f4f` |

## Registration dependency and layout audit

After the second attempt, a source audit found that these markers depend on
successful capture-region setup. In the selected `fs/pstore/ram.c:675–811`,
`ramoops_probe()` checks the fixed capture layout, initializes the dump,
console, backup-console, ftrace and PMSG zones, then calls `pstore_register()`.
A capture mapping refusal therefore prevents the ordinary pstore console from
registering too. The console zone has already been initialized and its current
ring reset before PMSG mapping; failure cleanup frees the saved old-console
copy. Consequently a failed probe can leave no retained console message even
if the kernel reached this code. This is a source-derived failure path, not
evidence that the second attempt took it.

The selected configuration, SHA-256
`486392ac9152365891c50ffdee56be1b6ed1aed61d588aa66e29f966604202ff`,
and native parameter defaults satisfy the early layout guard without overrides:
base `0x44410000`, total size `0xe0000`, 4 KiB dump/ftrace sizes, 64 KiB
console/PMSG sizes, memory type zero and no ECC. The packaged command line
adds capture mode without changing these layout parameters. Applying the
unchanged native allocation formula gives these half-open ranges:

| Zone | Start | End, excluded |
| --- | --- | --- |
| 175 dump records | `0x44410000` | `0x444bf000` |
| Console | `0x444bf000` | `0x444cf000` |
| Backup console | `0x444cf000` | `0x444df000` |
| Ftrace | `0x444df000` | `0x444e0000` |
| PMSG | `0x444e0000` | `0x444f0000` |

Splitting the DT reservation into `0xd0000` plus the final `0x10000` PMSG
region does not change this configured allocation. Native
`ramoops_register_dummy()` takes its layout from parameters/configuration;
the MediaTek reservation callback only logs its range. The previously checked
[container](results/bootstrap-container-1.json) includes the split reservation
and PMSG `no-map` property. In the native source, the reserved-memory scanner
passes `no-map` to `memblock_remove()`, while ARM64 `pfn_valid()` queries
`memblock_is_memory()`. The capture mapper checks every page with `pfn_valid()`
before requesting the region and mapping it. Those source paths are consistent
with the intended exclusion; they do not establish the DT delivered by LK,
runtime reservation success, resource availability or successful mapping.

Additional source identities from the same prepared input tree are:

| Source | SHA-256 |
| --- | --- |
| `fs/pstore/ram_core.c` | `8a5a63163989901ec5dcccb374a77d572b81982fe5544025e090f4e00bcd0b10` |
| `arch/arm64/mm/init.c` | `55e7f3f8895da839bfb1b5ad5cc2efa0cd44b5b3ead3533453f5c56f2b76a7d0` |
| `drivers/of/fdt.c` | `3c9b23e038f9b58db3f7c428d598e14cba7fec2a8686691ead5c55e20623de41` |
| `arch/arm64/boot/dts/mt6797.dtsi` | `5e7809ca4ceb07c501a76b5c2f4d7d067ce11b092fa556b5893246831bd9330f` |

### Retained LK and complete DT comparison

A subsequent RE-VM comparison checked every node and property in the appended
DTBs of the checksum-verified retained Gemian reference and selected kernel.
The reference has 875 nodes and 3,472 properties; the candidate has 876 and
3,474. The only differences are the smaller original pstore `reg` and the new
PMSG node's `reg` and empty `no-map`. All existing node/property ordering,
header memory-reservation entries and boot-CPU field are preserved.

| Appended DTB | Bytes | SHA-256 |
| --- | ---: | --- |
| Retained native reference | 130,745 | `9e26929563f7682d1f7545d6007f0092c7e085a4edbd6e7be0ac8eaa5159b2f9` |
| Selected export kernel | 130,833 | `f15b0840d7999a7c37b11017324de5c9f46d7d7f7b76b369aad337e453dc729f` |

The retained July LK binary, SHA-256
`75ec9f0ba97af9e68d964b304e0de809f9b4546982570bd16b2e7fe88823282c`,
was inspected as ARM Thumb at mapping base `0x45fffe00`. Its caller invokes
the memory sanity check at `0x46027164` and, on success, the reservation
appender at `0x46027268`. Function roles are inferred from source, strings
and control flow, not asserted debug symbols.

Within the check, the `reg` lookup at `0x46035502` advances to the next child
when absent, through `0x460356d4`. Present values are decoded as four 32-bit
big-endian cells and compared with the loader's reserved ranges. A conflict
can enter the infinite loop at `0x460356d2`. This check uses neither
`compatible` nor `no-map`; omitting `compatible` on the new PMSG node does not
itself trigger this path. The appender at `0x46033bfc` iterates the loader's
own reservation list and adds nodes/properties; it does not replace the
original pstore node in the inspected function.

This agrees with pinned
[mblock_v2.c](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/lib/mblock/mblock_v2.c)
lines 125–174 and 969–1113, SHA-256
`5712e8c35ec0e85e38339af4be5664a4bd8366785695bffb091746514183b004`,
and the caller in
[mt_boot.c](https://github.com/dguidipc/gemini-lk-android8/blob/f4988d74bb70a0a15d7f362f412afba7e7fcda46/lk/app/mt_boot/mt_boot.c)
lines 1718–1730, SHA-256
`9380b89d367770acf29f1c5b7f4856cc87bc4b64afd17aa9fa1fd621c213ecda`.
Both source identities were verified against downloads from that revision.

For an unchanged loader reservation list, splitting the same half-open range
cannot introduce an overlap that the original covering range did not already
have. That inference is limited to this check: changed boot allocations, other
DT callbacks, the actually installed LK and the DT delivered on the failed
boot remain unproved. No loader code was executed or changed.

The private audit uses pylibfdt to traverse ordered nodes/properties, verifies
both input digests and three compiled string references, and retains bounded
radare2 disassembly. Its SHA-256 is
`77e25303241da0d64afb00c6541b1dc4d7ba91c8af1583e4478761aa06f5646d`;
the principal disassembly digest is
`a171f1147ea457e0e6555503ea27127078b81599272628baea4854a3cd5e67aa`.
Raw DTBs, firmware and disassembly remain private.

This audit found no demonstrated layout repair and made no kernel, image or
device change. Keep the [known-good retention control](RETENTION_CONTROL.md)
as the next observation, pending its owner approval. Even a passing Gemian
control would leave candidate backend registration unproven; absent candidate
markers cannot establish failure before kernel entry or before PID1.

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

The second session bound these sources to a new UUID, filesystem and verified
container; its one physical attempt is consumed. The ordinary console ring can wrap,
log-level filtering can suppress records, and a hard failure before devtmpfs or
the log descriptor opens still has no new userspace record. An absent marker
therefore remains inconclusive. Preserve retained logs promptly after the
owner-approved recovery, without interpreting a timeout as restart approval.
A recovered marker must be joined to its boot UUID and exact deployment;
it identifies a reached stage, not successful hardware support or proof that
the next operation completed. The unchanged first image must not be repeated.
