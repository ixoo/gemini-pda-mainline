# One-shot mainline MT6797 WLAN firmware-start diagnostic

The [EMI-copy boot](../2026-09-28-mt6797-emi-copy-probe/results/runtime-1.json)
copied and read back both reserved-memory sections and sealed region 18. It
never submitted the two ordinary sections through the HIF, so firmware could
not run. This experiment connects the existing CONFIG/ACK/PDA and WIFI_START
transport to that retained, four-section image. It remains a diagnostic
profile, not a network driver or a claim of usable Wi-Fi.

[Patch 0045](../../patches/proposals/0045-soc-mediatek-probe-bounded-MT6797-WLAN-firmware-start.patch)
extends the same serialized, one-boot CONSYS owner behind
`mediatek,one-shot-firmware-start-probe`. The owner repeats the previously
accepted power, chip-ID, reset, HIF and region-18 admission sequence in the
**new** boot. It requires a full two-section EMI copy with byte readback and
matching final policy before the next operation. Under the held owner it
checks or requests HIF driver ownership once, refuses a nonempty reply queue
or pre-existing WLAN-ready bit, and seeds only the fresh INIT TC4/TC0
one-command credit pools. The immutable firmware plan supplies exactly two
ordinary sections; each gets a CONFIG with its validated destination,
encryption selector, key index and first-section reset bit, a matching
status-zero CMD_RESULT, then bounded PIO PDA chunks. Only after both sections
report complete submission does it send one WIFI_START with no address
override and poll WCIR for at most one second. There is no packet DMA,
calibration, scan, association or network interface. Powered resources,
firmware image, EMI mapping and HIF transaction are retained after any
uncertain effect until the reviewed reboot/recovery path.

The **one-boot hypothesis** is that this fresh mainline owner can receive two
successful CONFIG replies, submit all 14,832 ordinary bytes and observe
WCIR WLAN_READY after one START. The unique record joins exact boot2 full
checksum, changed boot ID, driver-own before/after, initial WRPLR/WCIR,
per-batch ordinary completion/status, START submission/readiness, complete
sealed kernel log, A53 regression and changed-boot Gemian Wi-Fi return.
Precondition refusal before CONFIG redirects ownership/queue investigation.
An absent/malformed/failed CONFIG reply or partial PDA result stops the
transaction without replay; its index and submitted byte count direct HIF
protocol diagnosis. START is forbidden on any incomplete image or failed
policy seal. A submitted START without WLAN_READY directs firmware execution,
encryption or EMI fetch diagnosis, not another identical boot. Readiness
permits subsequent command/event and standard wireless-interface work; it
does not itself make mainline Wi-Fi usable.

The new effect budget is one driver-own request if needed, two CONFIG
commands, at most eight PDA chunks totaling 14,832 payload bytes, one START
command and finite status polling. Each ordinary section has a one-second
transaction deadline; driver-own acquisition has at most 2,048 polls, and
START has a one-second deadline. No software deadline can cancel a stalled
MMIO access. A stopped/uncertain result holds the CONSYS state for native
recovery; it cannot authorize another submission, fresh credit seed,
automatic reset or replay. Raw logs, firmware and credentials stay ignored
under `artifacts/`.

The [first watch's USB-stage record](results/usb-stage-1.json) has a matching
full boot2 readback and clean shutdown. The Mac then observed preloader and
MediaTek 20ff, but no mainline USB route during the 900-second watch. Gemian
LAN SSH was unavailable at checks during and after the watch. There is no
mainline boot ID or kernel log, so
this watch does not answer the firmware-start hypothesis. The owner's physical
selection report, device screen state and live identity are needed before
attributing the stall or using the reviewed recovery path. Do not replay the
same image without a distinct
measurement.

In the next owner-confirmed boot2 selection, the gadget appeared but a macOS
`ifconfig -a` timeout stopped the host collector before device SSH. The
subsequent Gemian boot exposed a persistent-RAM record from the exact
firmware-start kernel release. Its [sanitized result](results/runtime-1.json)
shows driver ownership, two successful ordinary CONFIG/PDA sections totaling
14,832 bytes, and one successful START submission. A CPU7 NULL dereference
in delayed-work scheduling caused a fatal interrupt panic about 0.58 seconds
later. There was no WLAN-ready result, service regression or mainline Wi-Fi
claim. The raw pstore archive is retained privately. A disassembly joins the
NULL spin-lock argument to `pool_workqueue.pool`; it does not identify the
writer or prove that WLAN firmware caused the invalid pointer. The device
returned to a new carrier-up Gemian boot, and read-only boot2 hashing still
matched the candidate. Stop START testing and do not replay this image while
the crash and firmware-memory protection/ownership are unresolved.

Build only the clean pushed commit with
`KERNEL_PROFILE=mt6797-a53-wifi-firmware-start-probe ./scripts/build-kernel --backend buildbox`.
Validate the package, binding, built Gemini DTB, private RAM root and LK
container before a candidate is installed. Use the reviewed live-GPT guard,
predecessor and full-partition readback, then clean shutdown. The owner
selects boot2 physically only after the USB watcher is armed. The patch is
an internal experiment with synthetic, non-certifying authorship, not an
upstream submission.
