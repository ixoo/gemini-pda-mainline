# Gemian Wi-Fi reference kernel

The [RE toolkit decision](RE_TOOLKIT.md) audits the current diagnostic
capabilities and explains why Kprobes is deferred for this 3.18 arm64 tree.

Status: six diagnostic Gemian revisions built and verified in changed boot2
sessions. Wi-Fi carrier and bounded native DMA observations are established;
mainline shared ownership and later packet DMA completion remain open.

The known-good Gemian 3.18 kernel brings up the MT6797 Wi-Fi hardware. Its
normal console output does not establish which CONSYS clock mode was selected
or whether the region-18/19/23 secure EMI protection requests succeeded. Those
are decision-changing inputs for the mainline shared-owner design. This
experiment builds a reusable Gemian reference kernel from public source commit
`59e00a9144d782e148332009a835b99c43382467`, the hash-pinned live Gemian
configuration, and the same pinned GCC 6.3 toolchain used by the established
Gemian Buildbox lane. The tracked [patch](patches/0001-diagnostic-record-Gemian-Wi-Fi-setup-decisions.patch)
records the co-clock argument at WMT initialization and CONSYS register
control, plus the arguments and raw secure-call result of selected EMI MPU
requests. It preserves the wrapper's return behavior and adds no register,
radio or firmware operation. Tracing is compiled in but disabled by default;
function and function-graph tracing may be enabled only during a later bounded
diagnostic session.

The first boot hypothesis is that the working Gemian stack will execute these
paths and provide an attributable clock-mode choice and EMI request/result
record. Unique evidence is one complete kernel log, the exact boot2 image
checksum, kernel release and changed boot ID, along with Wi-Fi link state.
If all records appear and Wi-Fi works, compare the recorded setup with the
mainline cold handoff before designing its owner. If Wi-Fi works but records
are absent, the compiled functions are not proved to be the active setup path;
use bounded function tracing or inspect the alternate caller. If the image
fails to boot or Wi-Fi regresses, preserve available evidence and return to the
known-good boot; do not repeat the same image without a new measurement. A
secure-call success establishes only the observed call result, not exclusive
ownership or a safe mainline power-on sequence.

Build only from a clean pushed project commit with
`./scripts/buildbox build-gemian-wifi-reference`, then fetch with
`./scripts/buildbox fetch-gemian-wifi-reference`. The validated bundle is
ignored under `artifacts/buildbox/<commit>/` and contains `Image.gz-dtb`,
`vmlinux`, `System.map`, final config, logs and SHA-256 inventory. The bundle
alone is not a boot image. A boot2 candidate requires separate offline Android
container assembly from the hash-pinned known-good Gemian boot image, exact
partition padding and review. Install only from verified Gemian through the
reviewed live-GPT boot2 guard and full readback, then shut down cleanly; the
owner selects boot2 physically. Primary boot is never a target.

Buildbox linked project commit `bf079c8be55e623b9fb5bc0e51a6a3feaed55f94`.
The [build receipt](results/build.json) pins the exact bundle inventory and
kernel field. The final config has function, function-graph and dynamic ftrace
enabled, with MTK default tracing disabled. The sole diagnostic is the same
69-section-mismatch modpost warning present in prior baseline builds. The
8.2 MiB kernel field contains release `3.18.41-gemini-wifi-ref+` and the
three diagnostic call sites are linked.

The [candidate recipe](build-candidate.py) reuses the hash-pinned Android-v0
assembler and known-good Gemian boot input, changing only the kernel field.
The [offline candidate receipt](results/candidate.json) records the unchanged
ramdisk checksum, 14,995,456-byte raw image and exact 16 MiB padded image.
The padded image SHA-256 is
`138e35e41fa12a3a0cdeca3660e42e291b5268814167c2857a7ad67cffe594b2`.
The private image stays ignored under `artifacts/gemian-wifi-reference/`.
The [installer preparation](prepare-installer.py) pins the reviewed guard and
installer derivation, the image inventory, and the expected predecessor
checksum. It generates a private shell script that rechecks the live GPT,
root/target device identity, power and full readback before clean shutdown.

## Device result

In known-good Gemian boot `b79541db-5e95-4a02-a32f-87fa18474b38`, the
live GPT identified inactive boot2. The installer confirmed a distinct root,
100% healthy battery and external power, and the expected predecessor checksum.
It wrote the padded image once, synced/flushed it, matched a full local stream
readback byte for byte, and shut down cleanly. The
[sanitized deployment receipt](results/deployment.json) records the exact
checksums; raw evidence stays ignored.

After the owner selected boot2, the LAN collector observed changed boot ID
`a690b7e2-a35e-4732-95c1-ab6b7af97c2f` and release
`3.18.41-gemini-wifi-ref+`. It preserved complete early and later kernel
logs. In this boot WMT initialized with `co_clock_type=0`; the CONSYS power-on
call received the same value. This is the source branch that requests VCN28
HW control and enables its regulator. The instrumented EMI calls reported
raw secure-call status zero for broad region 23, WMT region 19 and the four
observed WLAN region-18 requests (clear, policy, clear, policy). The observed
WLAN and WMT windows were the first and second 512 KiB of the 2 MiB CONSYS
reservation. `wlan0` reached carrier and Gemian was reachable over its LAN
address. The [runtime receipt](results/runtime-1.json) binds those facts to
the boot and retained private log checksums.

Function and function-graph tracers are available, the active tracer remains
`nop`, and all three instrumented setup functions appear in ftrace's filterable
function list. This kernel is therefore available for later bounded tracing
without another build. The secure-call return codes do not resolve effective
EMI overlap arbitration, master-domain routing, or exclusive resource
ownership. The PDA currently remains in this diagnostic Gemian boot; mainline
Wi-Fi remains unsupported.

## Single-cycle trace protocol

The [bounded trace script](trace-cycle.sh) is pinned to the observed diagnostic
boot ID and release. Its hypothesis is that ConnMan's Wi-Fi disable/enable
will execute the WLAN stop/remove and probe/firmware paths, and may show whether
the shared CONSYS block powers down while Bluetooth remains enabled. The
unique observation is one private, timestamped function trace joined to this
boot's before/after kernel logs, command results and carrier transition. It
does not record DMA register arguments or prove all five firmware-lifetime
predicates from the [retained audit](../2026-09-07-mt6797-wifi-retained-lifetime-audit/README.md).

The script refuses a changed boot, absent initial carrier, another active
tracer/filter or a missing required function. It filters only fourteen setup,
firmware and teardown functions, uses a 128 KiB per-CPU ring, and restores the
original `nop` tracer, local clock, 7 KiB per-CPU buffer and tracing state.
Its effect budget is one ConnMan Wi-Fi disable and at most two enables, with
bounded waits; no firmware, calibration or register file is written directly.
It runs under systemd so loss of LAN SSH does not abort the re-enable. A
successful off/on trace can identify executed ordering for a later focused
observer. If the functions do not fire, CONSYS stays on, carrier does not
return, the trace overruns, or boot identity changes, mark the result limited
or inconclusive; do not replay the cycle. Preserve its private output before
any reviewed recovery. The script is single-use in this boot.

The [single-cycle result](results/trace-cycle-1.json) is limited. The systemd
job completed one disable and one enable in the same boot; carrier returned and
the active tracer was restored to `nop`. The appended kernel log contains only
the `wlan0` not-ready and ready transitions for this cycle, with no new WMT or
EMI setup lines. The filtered trace contained no function lines and had no
positive tracer control; its emptiness cannot prove those functions were not
called. ConnMan's technology toggle therefore did not establish the required
firmware load/shutdown lifetime. The private trace and full logs are retained
under ignored `artifacts/`. This cycle's effect and repeat budgets are
consumed; a different control path is needed for the next discriminator.
An independent [same-boot ftrace control](results/trace-selftest.json) later
recorded 84 `vfs_read` calls with the tracer restored afterward. This proves
that function tracing can record a known call in this kernel; it does not
retroactively make the ConnMan trace a complete negative witness.

## Direct WMT cycle candidate

The pinned vendor `wmt_chrdev_wifi.c` implements writes of `0` and `1` to
`/dev/wmtWifi` as `mtk_wcn_wmt_func_off(WMTDRV_TYPE_WIFI)` and
`mtk_wcn_wmt_func_on(WMTDRV_TYPE_WIFI)`. The off callback calls the registered
WLAN remove function; the on callback calls its probe function. Unlike the
ConnMan technology toggle, this is an explicit WLAN driver lifetime path.
The source also has an optional whole-chip assertion on failed requests, so
its effects and recovery need to be treated as a new test, not as a replay of
the ConnMan cycle.

The [direct WMT script](trace-wmt-cycle.sh) was a single-use candidate for this
same boot. Before any radio effect it checks the exact boot, live carrier,
power, character-device identity and trace state, then requires a positive
`vfs_read` function-tracer control. It filters `WIFI_write` and fourteen
selected lifecycle functions during one `0` write and at most two `1` writes.
It runs as a device-side systemd job, preserves private before/after logs and
trace, and restores ftrace. A complete successful callback/firmware trace
would inform the mainline owner design; missing callbacks, an empty trace,
device reset, or failed carrier restoration are refusal results. If LAN does
not return, the device-side result is preserved on the shared Gemian rootfs
for owner-operated known-good boot recovery.

The [result](results/trace-wmt-cycle-1.json) records one completed direct WMT
off/on cycle in the same diagnostic boot. Its in-job positive control captured
nine `vfs_read` calls; the bounded lifecycle trace captured 18 calls with no
overrun. `WIFI_write`, WMT Wi-Fi off, `wlanRemove`, and `wlanStop` preceded one
WMT Wi-Fi on, `wlanProbe`, `kalFirmwareOpen`, `kalFirmwareLoad`, four region-18
EMI wrapper/secure-call pairs, and `kalFirmwareClose`. All four new region-18
secure calls returned raw status zero. WMT logged Bluetooth on while Wi-Fi was
off, then both on. None of the selected CONSYS power or register-control
functions appeared in this positive-controlled trace. One enable restored
carrier and LAN SSH; the service exited successfully and ftrace returned to
`nop`. The complete logs and trace remain private under ignored `artifacts/`.

The remove path also raised a new `cfg80211_netdev_notifier_call` warning from
`wlanNetUnregister`. In the exact diagnostic source, `net/wireless/core.c:1042`
warns when `wdev->current_bss` remains set during unregister, then releases
that BSS reference. The Wi-Fi technology was connected before the direct WMT
write, so this warning identifies an associated-interface removal case; it
does not by itself show a failed remove or a lasting kernel fault. The cycle
demonstrates the vendor WLAN callback and image
mapping/load helper order while Bluetooth retains the common block. It does
not prove successful firmware execution, DMA programming/idle, firmware-stop
completion, exclusive CONSYS ownership, or safe teardown; the function trace
contains no arguments or return values for those predicates. The direct WMT
effect budget is consumed. A future radio cycle should first establish a
separate, bounded disconnect state and a focused measurement for the missing
firmware-stop and DMA predicates.

## Stop-decision reference revision

The first direct WMT trace shows that `wlanRemove` executed, but function
tracing cannot distinguish a successful firmware stop from a skipped command,
fallback, or reset request. The selected vendor `wlanAdapterStop` returns its
initial success status even on these other paths. The separate
[stop-decision patch](patches/0002-diagnostic-record-Gemian-WLAN-stop-decisions.patch)
adds only diagnostic log fields for whether the power-control command was
attempted, its result, the reason the ready polling ended, the last WCIR read,
and the three existing worker-completion waits. The stop command remains one
call at its original gate, the three waits each remain one call in order, and
the native fallback loop is unchanged. A nonzero wait result is remaining
timeout ticks, not an independent proof of adapter or DMA idle.

The Buildbox recipe applies the setup and stop patches in order and gives this
revision release `3.18.41-gemini-wifi-ref2+`. The
[v2 Buildbox receipt](results/build-v2.json) pins its clean project commit,
source, toolchain, ordered patches and linked kernel. The only recorded build
diagnostic is the baseline 69-section-mismatch modpost warning. The
[v2 offline candidate](results/candidate-v2.json) uses the same verified
Gemian boot image, Android-v0 assembler and ramdisk as v1; only its kernel
field changes. An independent parse also found the appended DTB identical and
the header different only in kernel size and image ID; both images have zero
post-field padding. The private image and reviewed installer remain ignored.

The v2 boot hypothesis is that
the unchanged Gemian setup will still reach WLAN carrier and expose both new
diagnostic formats in the linked kernel. The unique first-boot observation is
the exact boot2 image/readback identity, changed boot ID, kernel release,
startup log and carrier state. If boot or carrier fails, preserve evidence and
return to known-good Gemian; do not retry the same image. If startup succeeds,
a separately bounded and recovery-ready off/on protocol can measure the stop
decision after explicitly clearing association. No radio cycle follows from
the build artifact alone. The v1 session and its private captures were
preserved. Before the v2 boot2 write, the device returned to known-good
primary Gemian so that boot2 was an inactive target for the reviewed GPT
guard and full readback.

The [v2 deployment receipt](results/deployment-v2.json) records a changed
primary Gemian boot, root on p29, inactive boot2 on p30, the exact v1
predecessor, three passing guard stages, full candidate readback, and a clean
shutdown. The device reported a healthy full battery and no external supply;
the reviewed power gate admitted this state. After the owner reported that
Gemian started, the armed one-shot LAN collector timed out without a
changed-boot SSH connection. The [attempt receipt](results/runtime-v2-attempt.json)
records this separately: neither the running kernel nor Wi-Fi state is yet
verified, so this is not a validated v2 boot or a Wi-Fi regression result.
The Mac later still saw one `0x0e8d:0x20ff` USB session without a network
interface; that identity also appears as an intermediate stage in earlier
project boots, but does not establish the stage here. The device remains
running pending screen-state and recovery-path inspection.

## Prepared v2 stop trace

The [single-use v2 script](trace-wmt-stop-v2.sh) is prepared but has **not**
been installed or run. Its SHA-256 is
`36908f13f0d4c164f23d10c4609a621810314e90b1da23b2f1bdb21052b9331c`.
It requires the exact v2 kernel release and a changed
boot ID observed by the host before any effect. Its hypothesis is that one
WMT Wi-Fi off/on cycle, after ConnMan has disconnected the associated
interface, will execute the new `wlanAdapterStop` decision record and three
worker waits without the prior associated-interface removal warning. Unique
evidence is the positive-controlled function trace joined to the before/after
kernel logs, stop/wait fields, carrier result and same-boot identity. A missing
function, failed tracer control, absent clean disconnect or changed identity
refuses before the WMT write. A completed cycle with no stop/wait record is a
limited result, not evidence of firmware quiescence.

The effect budget is one ConnMan disable, one WMT off, one WMT on and one
ConnMan enable. The device-side exit handler attempts a WMT on only if off was
attempted and no on was attempted, and attempts ConnMan enable only if disabled
without an enable attempt. It always tries to restore the original `nop`
tracer. No WMT write is admitted until carrier is down and `iw` reports three
consecutive disconnected samples. Those observations reduce the known
`current_bss` warning case but do not prove cfg80211's internal reference is
clear. If the netdev or carrier does not return, preserve the private output
and use the reviewed known-good boot recovery path; do not replay the cycle.
The script's fixed output directory prevents a second use in the same rootfs.
At preparation time the PDA's release and boot ID were unverified, so this
protocol was not yet admitted for execution. The later verified boot and
cycle are recorded below.

## Verified v2 boot and stop cycle

In a changed primary Gemian boot `a4863e48-fed8-4d5b-b532-2fc1be4de150`,
the live inactive boot2 partition still matched the exact v2 candidate
checksum. After clean shutdown and owner selection of boot2, authenticated
Gemian LAN SSH reported changed boot ID
`7d372eb9-23ca-48af-91b3-8b5e9112c943`, release
`3.18.41-gemini-wifi-ref2+`, model `MT6797X` and `wlan0` carrier. The full
startup log was retained privately and pinned in the [v2 runtime receipt](results/runtime-v2.json).
This verifies the later v2 boot; it does not reinterpret the earlier
inconclusive boot attempt.

The previously prepared single-use script matched its tracked SHA-256 and
passed boot, power, Wi-Fi, tracer, function and utility preflights. It ran
under systemd so that transient LAN loss would not prevent its cleanup. Its
positive control traced nine `vfs_read` calls; the filtered trace recorded
one WMT Wi-Fi off and one on, WLAN remove/stop/adapter-stop, one power-control
command, WLAN probe and firmware-image helpers. The ring reported zero
overruns. ConnMan disconnected before WMT off, and carrier returned after
WMT on. The service exited zero in the same boot, with `nop`, local trace
clock and the original 7 KiB buffer restored. No new cfg80211 warning or
worker-wait timeout appeared. The [sanitized cycle receipt](results/trace-wmt-stop-v2-1.json)
pins the private logs and trace.

The new stop record reports `command_attempted=1`, `command_status=0`,
`reason=ready-clear`, poll index `1`, and final WCIR `0x00100279`. The three
worker waits each returned 300 remaining jiffies. This establishes that the
vendor path sent one accepted stop command, observed the ready bit clear, and
completed its HIF/RX/main worker waits in this cycle. It does **not** establish
firmware internal quiescence, positive AP-DMA idle before mapping release, or
coherent shared CONSYS off while Bluetooth remains active. The radio cycle's
single-use budget is consumed; do not replay it. A next observer needs a
distinct DMA-idle/endpoint-transition measurement rather than another copy
of this trace.

## Bounded DMA-path presence check

The [single-use function trace](trace-dma-presence-v2.sh) has SHA-256
`dcecacc3793503739786e80d04b95d1ba04cf434a019cbcdb5b3955a23e38919`.
The pinned selected AHB source enables DMA and exposes `kalDevPortRead`,
`kalDevPortWrite`, `HifPdmaConfig` and `HifPdmaStart` in the running v2
kernel's ftrace filter list. The hypothesis is that a single 4 KiB zero-data
reply over the existing authenticated Wi-Fi SSH link will execute at least
one `HifPdmaConfig` and `HifPdmaStart` call. A positive, non-overrun trace
would establish live packet DMA-path use in this boot, not register arguments,
transfer completion or DMA idle before unmap. An empty trace, missing positive
`vfs_read` control, overrun or changed boot is inconclusive and does not admit
a replay.

The exact effect budget is one 15-second filtered function trace and one
4 KiB zero-data SSH reply to the Mac, with no Wi-Fi control, added register read,
firmware request or external destination. The script requires the same v2
boot ID/release, carrier, idle tracer and default buffer/clock; it refuses
an occupied output directory. It runs under systemd with a 45-second outer
limit so its exit trap restores the `nop` tracer, all-function filter, local
clock, 7 KiB buffer and tracing state even if SSH disconnects. A later
instrumented kernel still needs typed native DMA register and idle-before-
unmap evidence; function tracing cannot supply those values.

The one admitted window completed in the same v2 boot. Exactly 4,096 zero
bytes reached the Mac over authenticated SSH. A positive `vfs_read` control
and 1,161 non-overrun function entries included 419 `kalDevPortRead`, 21
`kalDevPortWrite`, 72 `HifPdmaConfig` and 72 `HifPdmaStart` lines. The service
exited zero, carrier remained up, and the tracer, clock and buffer returned
to their prior state. The [sanitized presence receipt](results/trace-dma-presence-v2-1.json)
pins the private output. This demonstrates that the selected DMA config/start
path was active during a window containing the SSH reply; background Wi-Fi
traffic prevents attributing every call to that reply. It does not provide
programmed addresses, raw poll progression or idle-before-unmap evidence.
The one-window budget is consumed; do not replay it.

## Boot2 update preflight from the instrumented Gemian boot

The owner clarified that a later boot2 image may be installed while the
instrumented Gemian kernel is running. A bounded read-only check in the
verified v2 boot resolved logical `boot2` to `/dev/mmcblk0p30`, with root on
`/dev/mmcblk0p29`. The reviewed device guard passed for target `179:30` and
root `179:29`; the full partition still matched the installed v2 image.
Battery presence, Good health and 100% capacity were observed. The
[sanitized preflight receipt](results/boot2-self-update-preflight.json) records
the exact boot identity and result. No write, shutdown or new boot occurred.

This establishes that a return to primary Gemian is not required solely to
make boot2 inactive in this session. It does not preapprove a future write:
that installer must resolve the live GPT and repeat all identity, mount,
power, candidate and full-readback checks at deployment time.

## V3 rail and clock outcome observer

The next [diagnostic patch](patches/0003-diagnostic-record-Gemian-CONSYS-power-outcomes.patch)
captures the existing VCN18/VCN28 regulator voltage and enable return values,
and the CONN clock-enable result in the common wrapper. It emits three bounded
records after the existing 20 ms settling delay. It adds no regulator,
register or radio operation and does not log inside the timed power sequence.
The pinned Gemian source for this wrapper has SHA-256
`0ec8e9c1594626d0b31f2d2623927d614f63af4437c16df838e10e11258663ce`.
The patch is an internal diagnostic archive, not an upstream submission.

The next boot hypothesis is that the working Gemian path returns zero for both
rail voltage/enable operations and CONN clock enable. Unique evidence is the
exact v3 boot2 image checksum, changed boot ID and release, complete startup
log with all three typed records, and observed Wi-Fi carrier. If the operations
return zero and Wi-Fi works, use those results when defining the mainline
provider's strict rail/clock error gates. A negative result or absent record
requires source-path diagnosis; a boot or Wi-Fi regression requires evidence
preservation and reviewed known-good recovery. Do not repeat the same image
without a decision-changing measurement. The record cannot prove achieved
VCN28 hardware-control mode, SPM key exclusivity, reset readback or EMI
arbitration.

The [v3 Buildbox receipt](results/build-v3.json) pins the clean pushed source,
ordered patches, linked kernel and package inventory. The sole build warning
is the same 69-section-mismatch count as v1 and v2. The
[v3 offline candidate](results/candidate-v3.json) was assembled from the
verified known-good Gemian boot container. Independent parsing found the v2
ramdisk and appended device tree byte-identical; the Android-v0 header changed
only in kernel size and image ID. The raw image is 14,995,456 bytes and the
exact 16 MiB boot2 image has SHA-256
`3e4663373b8b0519a06642ac5ddef4223f2a31b28aca8446bfbe2a59b6a456ea`.
The first installer preflight refused before writing because its historical
release gate allowed only primary Gemian. The [v3 installer derivation](prepare-installer.py)
now pins the exact verified v2 boot ID and release while retaining the live
GPT, root/target, power and full-readback gates. The
[deployment receipt](results/deployment-v3.json) records a guarded write to
inactive boot2, a matching full 16 MiB readback and clean shutdown. Physical
boot2 selection and changed-boot verification are still pending. The first
[one-shot LAN collector](results/runtime-v3-attempt.json) timed out without a
changed-boot SSH connection or confirmed physical selection. This establishes
no v3 boot or Wi-Fi result; rearm a fresh collector before the owner selects
boot2 later.

The [rearmed 30-minute LAN collector](results/runtime-v3-rearm-1.json)
also timed out without a changed-boot SSH connection. The owner was away
during this window and did not report a boot2 selection. This adds no v3
boot or Wi-Fi observation. Arm a fresh finite collector when the owner is
back and ready to select boot2 physically.

The owner later selected boot2 with a fresh collector armed. The
[v3 runtime receipt](results/runtime-v3-return-1.json) records a changed boot ID,
the expected diagnostic release, one complete set of power records in both
saved logs, and Wi-Fi carrier at two samples 25 seconds apart. VCN18 and VCN28
voltage/enable requests and CONN clock enable all returned zero; the source
branch used `co_clock_type=0` and requested VCN28. The early boot also logged
the 4G-mode branch. This satisfies the v3 request-outcome hypothesis for that
boot. It does not prove hardware-control mode, exclusive shared-resource
ownership, reset outcome or DMA idle. The unprivileged collector could not read
`/proc/cmdline`; kernel release and changed boot ID were captured separately.

## Retained 4G-mode observation

A [read-only reanalysis](results/4g-mode-reference.json) of the preserved
v1 and v2 boot logs found one `[EMI MPU] 4G mode` message in each exact,
verified boot and no opposite message. The pinned Gemian early-init source
emits that line after reading INFRACFG_AO bit 13 as set and assigning
`enable_4gb=1`. This resolves the boot-time selector observation for those
boots; it does not establish a stable selector during packet DMA, the v3
state, or the HIF ADDR2 bus-address translation. No device access occurred.

## V4 DMA idle outcome observer

The [v4 diagnostic patch](patches/0004-diagnostic-record-Gemian-AHB-DMA-idle-outcomes.patch)
uses the pinned Gemian AHB source (`ahb.c` SHA-256
`d9b4e80fe98695284627e495ad640e39728ebe7df235df129f64d48e8a2e726b`).
The v2 runtime trace established that `HifPdmaConfig` and `HifPdmaStart`
run, but did not show the physical endpoints or whether the idle poll
returned zero before the DMA mapping was released. In each data-port RX
and TX path, this patch saves the return from the *existing*
`DmaPollStart` call and records the poll count and count-limit escape.
It logs the already computed source, destination, port and transfer size
once per direction after the path releases its DMA mapping. It adds no
DMA register read or transfer and leaves the existing timeout and
unmap behavior intact. A zero `idle_return` with `count_escape=0`
supports that this poll saw the channel EN bit clear; `count_escape=1`
means the path reached unmap without that assurance.
The source and destination are software configuration fields, not readback
of the DMA low-address or ADDR2 registers. In particular, a wide mapped
address here does not prove that its upper bits reached the engine.
In the [pinned `ahb_pdma.c`](../2026-09-07-mt6797-wifi-observer-feasibility/results/dma-hook-sources.json),
`HifPdmaStop` only masks the DMA interrupt:
its STOP write and internal enable poll are compiled out. The existing
`DmaPollStart` callback instead reads `AP_DMA_HIF_0_EN` and returns its
enable-bit state. The v4 record therefore witnesses the final enable read
and the loop's exit reason, not a successful hardware STOP command or
every transfer's lifetime. The [MT6797 register reference](https://www.96boards.org/documentation/consumer/mediatekx20/additional-docs/docs/MT6797_Register_Table_Part_1.pdf),
PDF pages 412–415, says EN clears after normal completion, STOP, FLUSH or
reset; a clear bit alone cannot distinguish them or prove full data delivery.
On normal exit, `idle_polls` equals the
callback count. On `count_escape=1`, the guard increments once more
without a callback, so the callback count is `idle_polls - 1`.

The records contain physical DMA addresses and belong in the ignored
private runtime capture. Publish only interpreted, sanitized facts.
The [v4 Buildbox receipt](results/build-v4.json) pins the clean pushed
source, ordered patches, linked kernel and checked package inventory.
Both new record strings are linked. The sole build warning is the same
69-section-mismatch count as v1–v3. The
[v4 offline candidate](results/candidate-v4.json) was assembled from the
verified known-good Gemian boot container. Independent
parsing found the v3 ramdisk and appended device tree byte-identical; the
Android-v0 header changed only in kernel size and image ID. The raw image
is 14,995,456 bytes and the padded 16 MiB image has SHA-256
`b1916ae329cdd6a7672a138d3d9673749279678d975255496fa411283ea9a886`.

After the validated [v3 runtime](results/runtime-v3-return-1.json), v4 is
selected for the next boot2 test. The [installer derivation](prepare-installer.py)
binds the reviewed guard to that exact v3 boot ID and release, v3 boot2
predecessor checksum, and v4 candidate checksum. Its generated private
installer SHA-256 is
`6146af35f8c8ee11c671ac5870188d3a99e63a98db5696fce42feb955d62c83e`.
The boot hypothesis is that a working Wi-Fi connection will exercise both
RX and TX data-port paths and record bounded idle-poll outcomes with their
computed endpoint fields. A changed boot ID, expected v4 release, Wi-Fi carrier,
and both records would support that narrow result. If boot identity or Wi-Fi
fails, preserve the finite capture and use the reviewed recovery path. If
either direction has no record, preserve the negative result and inspect
whether that path was exercised before changing instrumentation. A
`count_escape=1` would move investigation to the DMA lifetime and mapping
release; `count_escape=0` supports only a clear EN bit at the final read.
One record per direction cannot establish every transfer's ownership or
replace the native driver's full DMA sequencing.

The [v4 deployment receipt](results/deployment-v4.json) records the guarded
boot2 write, independent full-partition readback match, and clean shutdown.
The owner physically selects boot2 while a finite LAN collector is armed;
deployment alone is not a runtime result.

The owner selected boot2 with the one-shot LAN collector armed. The
[v4 runtime receipt](results/runtime-v4-return-1.json) binds a changed boot ID
to the expected release, complete early and late logs, and Wi-Fi carrier at
two samples 25 seconds apart. Both logs contain exactly one RX and one TX
record. Each first transfer's existing idle poll returned zero after one
read, without reaching the count-limit escape; no DMA timeout message was
found. The host-side fields contain mapped addresses below 4 GiB; the other
fields describe the configured HIF endpoint.
The records occurred just before the first Wi-Fi link event. They establish
the first startup transfers' final EN reads, not the idle result for later
SSH packet DMA. Neither the computed endpoints nor EN clearing proves the
actual low/ADDR2 register values, clean completion or delivery. The next
measurement distinguishes transfers made while carrier is reported from
these prelink startup records; packet attribution remains a separate gate.
The inherited warning and call-trace counts match v3; no new
DMA timeout or kernel panic was observed in this boot.

## V5 post-carrier DMA observer

The [v5 patch](patches/0005-diagnostic-record-Gemian-DMA-idle-after-WLAN-carrier.patch)
keeps v4's existing idle-poll fields and once-only bounds, but emits each
direction's record only when the WLAN netdev exists and reports carrier. It
reads software link state after the existing DMA unmap; it adds no radio,
transfer or DMA-register operation. This is a distinct observation because
both v4 records preceded the first link event. The pinned Gemian source sets
the WLAN netdev carrier off at creation, on for the media-connect indication,
and off for disconnect. Carrier can precede a later
link log or represent control traffic, so even a v5 record is not by itself
proof of SSH packet DMA.

The next boot hypothesis is that Wi-Fi remains functional and a bounded
post-carrier RX and TX transfer each reaches an idle poll with no count-limit
escape. Unique evidence is the exact v5 image checksum and changed boot ID,
the expected release, carrier samples, and the timestamped records compared
with the first link event. If both records appear after carrier and their
idle polls return zero, that supports only those two EN-clear observations.
If a record is absent despite carrier and authenticated traffic, inspect the
corresponding path and trigger timing before changing instrumentation. If
Wi-Fi or boot regresses, preserve the finite capture and use the reviewed
recovery path. An escape or nonzero final return moves investigation to DMA
lifetime and mapping release.

The [v5 Buildbox receipt](results/build-v5.json) pins a full link from clean
pushed commit `f514ea7a4bcd66be7f7ef8db921dcc251cdb55d3`. Its fetched
inventory passed checksum validation, both v5 record strings and the expected
release are linked, and the only warning retains the prior 69-section-mismatch
count. The [offline candidate](results/candidate-v5.json) contains the same
ramdisk and appended DTB bytes as v4; its Android-v0 header changes only in
kernel size and image ID. The exact padded 16 MiB image is
`cf9707c7b4259140f575568ddeec658065eae45bae2e4bd6811d5849a5df70ff`.
V5 is selected as the next distinct boot2 test. The
[installer derivation](prepare-installer.py) binds its private guarded script
to the observed v4 boot ID and release, the installed v4 predecessor checksum,
and the v5 candidate. The generated installer SHA-256 is
`2b1b5e3c7ba7d2664928334247710379a13dc47700cc7fa527471344bfe7a660`.
At that offline checkpoint, no v5 device write or boot had occurred.

The [v5 deployment receipt](results/deployment-v5.json) records the later
guarded boot2 write, independent full-partition readback match, and clean
shutdown. A finite LAN collector is armed for owner selection of boot2;
deployment alone does not establish a v5 runtime result.

The armed collector then observed a changed boot with the expected v5 release.
The [v5 runtime receipt](results/runtime-v5-return-1.json) pins complete early
and late logs and Wi-Fi carrier at two samples 25 seconds apart. The first
link-ready message occurred at 17.677420 seconds; the once-only TX and RX
records followed at 17.678089 and 17.678610 seconds. Each existing idle
poll read EN clear once, without a count-limit escape, before its DMA mapping
was released. Both mapped host-side addresses were below 4 GiB. No DMA
timeout or kernel panic was found, and the inherited warning/call-trace counts
match v4.

This resolves the narrow post-carrier idle question for those two transfers.
Their proximity to link-up leaves packet identity unresolved: they may be
control traffic and cannot prove the later SSH packet path or all DMA
lifetimes. The software carrier gate and computed endpoints do not read back
the DMA engine's low/ADDR2 registers, distinguish completion from STOP/FLUSH/
reset, or establish shared AP-DMA ownership for mainline. A future packet-DMA
test needs an attributable post-link trigger and a distinct, bounded record;
repeating this once-only image would not answer that question.

## V6 authenticated-window DMA observer

The [v6 patch](patches/0006-diagnostic-arm-Gemian-DMA-result-after-SSH-link.patch)
keeps the same carrier gate and existing DMA idle-poll fields, but adds a
root-only boolean diagnostic parameter, false by default. Each direction's
once-only record is eligible only after that software flag is set. It adds no
radio operation or DMA register read. This lets an authenticated SSH session
arm the observer after link-up and request one bounded 4 KiB zero-data reply;
it does not identify an individual packet within that window.

The next boot hypothesis is that the v6 kernel retains working Wi-Fi and the
post-trigger SSH window reaches one RX and one TX DMA poll without a count
escape. Before any trigger write, the host must verify the exact image and
changed boot ID, expected release, Wi-Fi carrier, a unique root-only parameter
path reading false, and no prior v6 records. The effect budget is one write
to that boolean and one bounded reply, followed by complete private log
capture; the once-only call sites bound output to two records. A missing
parameter, mismatched identity, preexisting record or absent carrier refuses
the write. A missing direction after the one window is a preserved negative
result, not permission to repeat the trigger. A boot or Wi-Fi regression uses
the reviewed recovery path after evidence preservation. Even positive records
directly prove only those final EN reads before unmap; the selected source path
may support a narrower control-flow inference. Low/ADDR2 register programming,
clean completion and exclusive shared-DMA ownership remain separate gates.
The [v6 Buildbox receipt](results/build-v6.json) pins a full kernel link from
clean pushed commit `250ef67905ab44ac587d400f556f964c793f8b2c`. The
validated bundle contains the root-only parameter and both v6 record strings;
its only diagnostic is the same 69-section-mismatch warning as v1–v5. The
[offline candidate](results/candidate-v6.json) pins the unchanged ramdisk and
appended DTB, a 14,995,456-byte raw Android-v0 image, and exact 16 MiB boot2
image with SHA-256
`f6218df7bc55b00218d2b9ac3e2cac61a1903486b753ff90bf51dcd1687eee7b`.
The generated installer is bound to the observed v5 Gemian boot and v5 boot2
predecessor. These receipts establish a prepared candidate, not v6 device
execution.

The [one-shot trigger](trigger-v6.py) runs only after a changed v6 boot is
captured by the private collector and Wi-Fi carrier is stable. It verifies the
pinned SSH identity and host trust, boot ID, release, parameter mode, initial
false value and absence of earlier v6 DMA records immediately before its sole
flag write. It saves the probe, reply, complete later logs and carrier samples
under ignored, owner-only `artifacts/`. A timeout or incomplete result is
preserved without a second write or reply. Each post-trigger read checks the
same boot ID before and after; the result requires carrier to remain present.
The 4 KiB reply is a bounded traffic window, not packet-level attribution.

The [v6 deployment receipt](results/deployment-v6.json) records a guarded
write from the verified v5 boot: boot2 was inactive, the v5 predecessor matched,
the full v6 partition readback matched the candidate, and Gemian shut down
cleanly. The subsequent [v6 runtime receipt](results/runtime-v6-return-1.json)
binds a changed boot, expected release, stable carrier and complete log chain
to one root-only trigger write and an exact 4 KiB SSH reply. No v6 DMA record
preceded the trigger. The first eligible TX and RX records appeared at 68.692
and 68.697 seconds after boot, long after link-ready at 17.902 seconds. Each
native idle poll saw EN clear on its first read before unmap, with no
count-limit escape. Carrier remained present at both post-trigger samples,
and warning/call-trace counts matched v5.

This later window removes the v5 ambiguity about records occurring immediately
at link-up. It does not attribute either transfer to the 4 KiB payload: the
authenticated SSH exchange and flag write also create traffic. The logged
endpoints are computed arguments rather than DMA-register readbacks. A further
source check of the exact [v6 build](results/build-v6.json) established that
`CONF_HIF_DMA_INT=0`, `CONF_HIF_CONNSYS_DBG=1` and `CONF_HIF_DMA_DBG=0` in
`os/linux/hif/ahb_sdioLike/include/hif.h`. In both `ahb.c` data-port paths,
the five-second `DmaPollIntr` timeout returns before the idle poll and log.
The records therefore imply that `HifPdmaPollIntr` read
`AP_DMA_HIF_0_INT_FLAG` bit 0 set before the driver acknowledged it, masked
the interrupt and read EN clear before unmap. This is a source-derived
inference, not an interrupt-register value captured in the log. The compiled
`HifPdmaStop` does not write STOP. A stale flag or an external STOP, FLUSH or
reset remains possible; flag-plus-EN does not prove data delivery. Shared
AP-DMA ownership, packet-level attribution and durable Wi-Fi behavior remain
open. The single-use v6 trigger budget is consumed; do not replay it in this
boot. A new kernel solely to log whether this interrupt poll succeeded would
repeat what the existing source path already establishes.

A separate [same-boot 4G/DMA join](results/4g-mode-v6-dma-join.json) found the
positive early 4G-mode branch in the retained v6 log. The pinned source sets
its file-static selector there and has no later writer. Both later mapped
host addresses were below 4 GiB, while the selected HIF start path issues
unconditional ADDR2 bit-32 set writes. This narrows the executing mode
assumption but does not resolve the FIFO bus alias or justify a mainline DMA
mask or address transformation.

## V7 VCN28 control readback candidate

The [v7 patch](patches/0007-diagnostic-sample-Gemian-VCN28-mode.patch)
adds one PMIC-wrap read of MT6351 `LDO_VCN28_CON0` (`0x0a0c`) after the
selected `co_clock_type=0` WMT on path requests VCN28 hardware control and
enables the regulator. An atomic claim limits the added transaction and log
to the first such path in a boot. The existing `pmic_read_interface()` uses
`pwrap_wacs2` with write flag zero and returns a transport status. The patch
records that status and the 16-bit read value without changing the vendor
return or adding a radio control, PMIC write or second boot-time probe.

The boot hypothesis is that the same path will run in a changed Gemian boot,
the read will succeed, bit 3 will reflect the requested control mode, and
Wi-Fi will still reach carrier. The value also exposes the source-clock mode
and enable selection fields (bits 7:5 and 13:11) at that instant; it does not
identify their external signal truth table or prove stable ownership. One
changed boot2 selection is the test budget. Require an exact built image,
guarded boot2 install, full readback and clean shutdown before owner selection.
Collect a complete startup log, changed boot ID, exact release, read status,
raw value and carrier. A read failure or absent log is inconclusive; a bit-3
mismatch redirects source/PMIC ownership analysis. A boot or Wi-Fi regression
requires preserved evidence and the reviewed Gemian recovery path. Do not
repeat an identical image after any of those results without a measurement
that would change the decision.
