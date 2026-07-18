# Experiment: online CPU1 behind the proven watchdog

## Record

| Field | Value |
| --- | --- |
| ID | `2026-07-18-cpu1-online-diagnostic` |
| Candidate | N |
| Status | Completed; first runtime decision oracle passed |
| Subsystem | ARM64 CPU hotplug, PSCI `CPU_ON`, first MT6797 Cortex-A53 secondary |
| Device variant | Current Gemini PDA unit; exact retail sub-variant not independently established |
| Date | 2026-07-18 |
| Investigator(s) | Project maintainers |
| Tracking issue | Not yet assigned |

## Question

With Candidate M's boot, no-IRQ watchdog, pstore, and fbcon behavior held
exact, can Linux online logical CPU1 through the standard ARM64/PSCI CPU-hotplug
path and remain observable until the proven watchdog returns to Gemian?

## Why this is the next gate

Candidate M completed the first fully observable mainline cycle on this unit.
Its retained console proves external `/init`, a working basic `mtk-wdt`, and a
31-second automatic reset; Gemian recovered the exact log and reported the
watchdog boot reason. That recovery boundary should be retained while the core
platform is widened one dependency at a time.

The exact embedded Candidate M configuration has `CONFIG_SMP=y`,
`CONFIG_HOTPLUG_CPU=y`, `CONFIG_ARM_PSCI_FW=y`, and `CONFIG_SYSFS=y`. Its forced
`maxcpus=1` limits boot-time bring-up, not later `cpu_up()`. The exact DTB has
ten PSCI/SMC CPUs; its intended first secondary is `/cpus/cpu@1`, MPIDR `0x1`,
and `arm,cortex-a53`. Candidate N separately requires the live Linux CPU1
device's `of_node` to resolve to that node. A successful write to CPU1's standard `online` control
returns only after the kernel's CPU-hotplug state machine completes, so this is
a direct PSCI/secondary-CPU result rather than a marker-only derivative.

The executable static check is
`scripts/validate-cpu1-foundation.py`. It reads the exact embedded config and
DTB; it has no device or write interface.

## Controlled delta

Candidate N derives from the exact hardware-tested Candidate M artifact. It
retains byte-for-byte:

- Linux 7.1.3 `Image.gz` and embedded configuration;
- forced `maxcpus=1`, `clk_ignore_unused`, console, and panic policy;
- Candidate M's appended DTB, including the no-IRQ watchdog and exact CPU/PSCI
  topology;
- Android-v0 addresses, page size, name, command line, canonical layout, and
  LK gzip-plus-appended-DTB contract; and
- the 31-second TOPRGU recovery policy and ramoops layout.

Only initramfs `/init` changes. It mounts devtmpfs, read-only procfs, and sysfs
with the one writable interface required by standard CPU hotplug. It then:

1. validates the live no-IRQ watchdog and live CPU1 Cortex-A53/PSCI nodes;
2. records `possible`, `present`, `online`, `offline`, the CPU1 device, its
   `of_node`, and filtered CPU/PSCI logs;
3. opens `/dev/watchdog0` and sends exactly one ownership-handoff ping;
4. requires CPU1 to exist, map to live `cpu@1`, expose a writable `online`
   control, and initially report offline;
5. emits a durable request-begin marker and writes `1` exactly once to
   `/sys/devices/system/cpu/cpu1/online`;
6. if the write returns, records its status and error text, the post-request
   masks, CPU1 state, filtered kernel lines, and two `/proc/stat` CPU1 samples;
   and
7. never offlines CPU1, retries the request, or pings the watchdog again.

If PSCI or secondary start blocks CPU0, the independently running TOPRGU timer
is already armed. No storage, framebuffer, network, raw memory, I2C, generic
reset command, or command shell is accessed.

## Decision oracle

| Attributable result | Decision |
| --- | --- |
| Precondition fails before the write, followed by watchdog return and retained pstore | Correct the exact live CPU enumeration or sysfs assumption; do not fall back to boot-time `maxcpus=2`. |
| `cpu1_request=begin` survives with no returned marker, followed by watchdog return | The request blocked inside CPU hotplug or PSCI. Audit the last durable CPU/PSCI boundary before another device cycle. |
| Request returns failure | Use the captured status/error and kernel lines to isolate policy, firmware denial, feature mismatch, or secondary timeout. Do not retry unchanged. |
| Request returns success, CPU1 is online, and its `/proc/stat` accounting advances | CPU1 completed the standard CPU-hotplug path and executed. Promote only the first secondary Cortex-A53 path; a changed follow-up may request the remaining A53s sequentially if it checkpoints and fail-stops after every core. |
| Automatic return plus surviving exact N `console-ramoops` | The M recovery channel remains valid with CPU1 online or with the captured failure boundary. |
| No automatic return or no exact N record | Treat as a recovery regression or unattributable selection. Stop platform widening and recover the exact partition/pstore state. |

No result from N establishes the remaining Cortex-A53 cores, either
Cortex-A72, CPU frequency scaling, idle states, storage, USB, UART, native
display, general userspace, suspend, or repeatability. Do not repeat N
unchanged after one attributable outcome.

## Reproducible build

The intended Linux/aarch64 VM invocation is:

```sh
DEV_VM_NAME=gemini-pda-build-recovery-20260717 \
  ./scripts/dev-vm run \
  /mnt/gemini-pda-mainline/experiments/2026-07-18-cpu1-online-diagnostic/scripts/build-cpu1-online-candidate.sh \
  --baseline /mnt/gemini-pda-mainline/artifacts/vm-export/boot-candidates/candidate-M-watchdog-registration-2bcb668e
```

The builder requires a clean repository, the exact Candidate M file set and
manifest, Linux/aarch64, and source epoch zero. It validates the embedded
config, CPU1/PSCI DT contract, initramfs-only archive delta, complete
Android-v0 delta, canonical IDs, addresses, capacity, and checksums. It has no
hardware or flashing interface and writes only guest-owned build artifacts.

## Attended procedure

This procedure was executed once for the exact candidate whose independent
builds and logical-`boot2` write/readback are recorded below. The result was
attributable, so unchanged N repetition is closed.

1. Keep external power connected and start the cycle-aware private collector
   from known-good Gemian:

   ```sh
   ./scripts/collect-device-pstore \
     --target gemini@192.168.1.50 \
     --wait-for-cycle --ask-sudo-password \
     --output artifacts/device-pstore/candidate-N-runtime-1
   ```

2. Select the verified logical `boot2` once with the silver button. Do not
   press power during the first 120 seconds. Record visible N lines and whether
   the return is automatic.
3. Verify the private capture manifest and inspect `pstore/console-ramoops`
   for the exact N marker. The collector's current
   `candidate-l-evidence.txt` is a legacy L-specific parser and must not be
   used to infer N-marker absence.
4. Apply the first matching oracle row. Do not select the same image again
   unless a changed measurement can alter the next decision.

## Safety boundary

The only hardware-directed userspace mutation is one standard CPU-hotplug
write targeting logical CPU1. The live DT and sysfs mapping must identify it
as the first Cortex-A53 and initially offline. The watchdog is armed before the
request and is not pinged afterward. A failed precondition after arming records
the reason and waits for the same recovery reset; a failure before a usable
watchdog enters a static hold and may require the known-good power-key path.
Primary `boot`, `boot3`, storage, firmware, NVRAM, GPT, and preloader are out of
scope.

## Associated code

- `initramfs/init`
- `scripts/build-initramfs.sh`
- `scripts/validate-initramfs-delta.sh`
- `scripts/validate-cpu1-foundation.py`
- `scripts/validate-boot-delta.py`
- `scripts/build-cpu1-online-candidate.sh`
- Candidate M source and runtime evidence in
  `../2026-07-18-watchdog-registration-diagnostic/`

## Result

Two clean aarch64 VM builds from repository revision
`7cdb4b994075fa009ae5a52a0b35fe038df4b650` are recursively byte-for-byte
identical, and both complete manifests verify. The raw Android-v0 image is
6,524,928 bytes with SHA-256
`43aea71224f6261001ff00904b30dae29063334172a2f6b0163b424a84c0e3aa`.
The exact Candidate M kernel segment, DTB, embedded configuration, LK addresses,
name, command line, and layout are unchanged; the only payload delta is
initramfs `/init`. All foundation, archive-delta, container-delta, syntax, and
ShellCheck gates pass. The private host export is
`artifacts/vm-export/boot-candidates/candidate-N-cpu1-online-7cdb4b99/`.

The raw image was zero-padded to the exact 16 MiB target size and written only
to live-resolved logical `boot2` while Gemian remained on `mmcblk0p29`. AC was
online and the battery was 100%, Full, and Good. A fresh mode-0600 full backup
matched the prior Candidate M partition checksum. The write was synchronized,
block-cache flushed, and independently read back to a mode-0600 local file;
the complete target and local readback both match padded SHA-256
`a5cc12372ece5e50364a88bc0bf4401ff092e335281352b062ed0ad229fbb7bf`.
No other partition was targeted and no reboot or shutdown was performed.

On its one attended selection, retained `console-ramoops` established the exact
N marker and live CPU1-to-`cpu@1` mapping. The standard CPU-hotplug write
returned success: CPU1 initialized its GICv3 redistributor, booted as MPIDR
`0x1` / MIDR `0x410fd034` (Cortex-A53), changed the global online mask from
`0` to `0-1`, and advanced its `/proc/stat` accounting between two samples.
CPU1 remained online through the last complete 25-second wait marker. The
owner saw the same success on fbcon, and the already armed watchdog returned
the device to Gemian automatically without a power press or other help.

Gemian then reported `wdt_by_pass_pwk`, `powerup_reason=reboot`, and boot reason
4. Its two PMIC watchdog-reboot fields were zero, unlike Candidate M's value
of one; retain that difference as a reset-propagation question rather than
using those fields alone to reject the exact TOPRGU trace and automatic return.
This passes N's decision oracle only for the first secondary Cortex-A53. It
does not establish repeatability, boot-time SMP, any other core, CPU stress,
coherency, DVFS, idle, or thermal behavior. Do not repeat unchanged N.

With this recovery loop proven, the next candidate may request CPU1 through
CPU7 sequentially rather than spending one manual cycle per A53. It must emit
a durable begin/return/mask and execution checkpoint after each core, stop on
the first failure, and leave CPU8–9 (the Cortex-A72 pair) untouched. The last
surviving checkpoint supplies the failure boundary; bisect only a grouped
dependency that remains ambiguous.

See `results/final-build-reproduction-20260718.txt`,
`results/boot2-write-candidate-n-20260718.txt`, and the sanitized
`results/runtime-candidate-n-attempt-1-20260718.txt`.
