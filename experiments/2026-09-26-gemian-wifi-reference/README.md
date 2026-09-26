# Gemian Wi-Fi reference kernel

Status: Buildbox kernel and boot2 packaging validated; one changed-boot
diagnostic Gemian session confirmed Wi-Fi and available function tracing.

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
The device remains running pending screen-state and recovery-path inspection.
