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

## Direct WMT cycle candidate

The pinned vendor `wmt_chrdev_wifi.c` implements writes of `0` and `1` to
`/dev/wmtWifi` as `mtk_wcn_wmt_func_off(WMTDRV_TYPE_WIFI)` and
`mtk_wcn_wmt_func_on(WMTDRV_TYPE_WIFI)`. The off callback calls the registered
WLAN remove function; the on callback calls its probe function. Unlike the
ConnMan technology toggle, this is an explicit WLAN driver lifetime path.
The source also has an optional whole-chip assertion on failed requests, so
its effects and recovery need to be treated as a new test, not as a replay of
the ConnMan cycle.

The [direct WMT script](trace-wmt-cycle.sh) is a single-use candidate for this
same boot. Before any radio effect it checks the exact boot, live carrier,
power, character-device identity and trace state, then requires a positive
`vfs_read` function-tracer control. It filters `WIFI_write` and fourteen
selected lifecycle functions during one `0` write and at most two `1` writes.
It runs as a device-side systemd job, preserves private before/after logs and
trace, and restores ftrace. A complete successful callback/firmware trace
would inform the mainline owner design; missing callbacks, an empty trace,
device reset, or failed carrier restoration are refusal results. If LAN does
not return, the device-side result is preserved on the shared Gemian rootfs
for owner-operated known-good boot recovery. This direct WMT cycle has not
been run; its effect budget is unspent.
