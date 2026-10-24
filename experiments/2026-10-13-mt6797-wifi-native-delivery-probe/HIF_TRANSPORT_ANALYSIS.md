# What is structurally wrong with the current approach: transport, rate and keep-alive

Analysis record, 2026-10-24. No device action. Sources: this driver's
`hif.c`, `hif_pio.h`, `join-commands.h` and `mac.c`; the vendor gen3 driver
in the public Gemian kernel tree (`drivers/misc/mediatek/connectivity/wlan/gen3`,
GPL-2.0, read-only); the sealed throughput logs of this experiment; the
96Boards-hosted MT6797 register table. Firmware behaviour is stated only
where the sealed logs show it.

## 1. The receive path is a word-at-a-time PIO poll; the vendor's is an interrupt, one aggregated DMA read per burst

What this driver does per received frame (`mt6797_hif_receive`): take the
HIF mutex, enter the window, read WRPLR (a setup write plus a data-word
read), issue one PIO transfer of the frame (a setup write, then one `readl`
of the CMD53 data register per 4 bytes: about 380 reads for a 1.5 KB frame),
run the guard read, optionally read WRPLR again, copy out. WRPLR reports one
length and the port returns one frame per read (register table: "at most 1
packet will return by the next RX port read"). The worker that does this
(`mt6797_mac_join_work`) also submits transmit frames, polls completion
status and sleeps between passes; there is no receive interrupt.

What the vendor driver does: the WLAN HIF interrupt (GIC SPI 283, level
low) wakes a thread; one read of the enhanced interrupt structure (112
bytes) returns WHISR, the per-queue transmit credit counts and, for each of
the two receive queues, the number of waiting frames and up to sixteen
lengths; the driver then issues one port read of the summed length into a
coalescing buffer (`nicRxSDIOAggReceiveRFBs`) and splits it. That read goes
through the AP DMA engine (`kalDevPortRead`: `use_dma = 1`,
`CONF_MTK_AHB_DMA = 1`, data ports WRDR0/WRDR1 and WTDR1 only; the PIO
`readl` loop is its fallback), with completion polled. So the vendor spends
about thirty CPU bus operations per burst of up to sixteen frames and lets
the DMA move the bytes; this driver spends about four hundred per frame on
the CPU.

The sealed logs match that arithmetic. The device-side receive rate per
chunk is 16–18 Mbit/s on the station tree and 10.5–14 on the trees since
pipelining, with device CPU idle at 77–79 % during receive; at 1,500-byte
frames that is 0.7–1.0 ms of worker time per frame, which is the PIO cost
plus the rest of the pass. Every segment is received once (netdev receive
packets 3,681–3,686 for 5 MiB in all four five-chunk runs), so nothing is
lost; the worker is simply the bottleneck, and the vendor control on the
same link (45 Mbit/s transmit, 38.5 receive on 2026-10-24) shows the air
is not.

The 16–18 → 11–12 drop since the pipelining boot is not explained by
anything in 0236 (its submission loop and its page budget are transmit-side
and cannot engage with one acknowledgment per pass; the budget is a host
ledger), nor by the bounded logging of 0243/0247. On a worker that is
already CPU-bound on PIO, any added per-pass or per-frame work (the later
patches' bookkeeping, two log records per transmitted acknowledgment at
340–410 acknowledgments per second, per-slot status handling) comes
straight out of receive time; which of them it is can only be measured, not
read. That measurement is cheap (per-pass receive count and read time
printed at data end) but it does not change the conclusion: the ceiling is
the transport, not the pass order.

## 2. Transmit is capped by the forced 6 Mbit/s rate, and the unforced rate fails for a reason upstream of the descriptor

Transmit per 1.5 KB frame costs about 380 PIO writes plus a status round
trip, but the measured ceiling is the air: at the fixed OFDM 6 Mbit/s every
frame takes about 4.2 ms, so 3.2–3.5 Mbit/s with four frames in flight is
close to that rate's goodput. Lifting it needs the firmware's rate
adaptation, and two boots showed that an unforced ordinary data frame is
never acknowledged (autorate: fixed-rate bit cleared; rate-2: the vendor's
exact data descriptor, zero rate word) while every forced frame is.

The host-side inputs have now been compared field by field with the
vendor's. The station record this driver sends (`mt6797_join_station_payload`,
124 bytes) lines up with the vendor's `CMD_UPDATE_STA_RECORD_T`: desired PHY
type set 8 (OFDM only), the non-HT rate set with 6 Mbit/s at bit 6 exactly
as the vendor's `RATE_SET_BIT_6M`, the BSS basic rate set, state 1 then 3,
WLAN index 1, broadcast index 2, legacy RTS policy, default fixed-rate code
0x4b, AMPDU disabled. The BSS info (`mt6797_join_bss_payload`) likewise:
rate sets, station index, fixed-rate code, non-HT basic PHY type index 3
and PHY type set 8. The vendor's post-association sequence is the same
three commands (`rlmProcessAssocRsp`, `nicUpdateBss`, station record state
3). What differs is content: this driver declares a non-QoS, non-HT station
(`ucIsQoS` 0, every HT/MCS/TX-rate-info field zero) to an access point
that is HT and WMM, where the vendor declares QoS and the HT capability
fields it parsed from the association response. Whether the firmware's rate
adaptation needs those, or initialises the station's rate table through a
path this legacy-only record never takes, cannot be settled from host
source; it is a firmware question. The practical next variable on the host
side is QoS: declare the station and BSS as QoS and send ordinary data as
QoS data with a TID, which is the vendor's normal case for any WMM access
point; HT declaration is the step after that and also changes the receive
side. Until then, forced 6 Mbit/s stays.

## 3. The idle link dies because nothing keeps it alive

Connected and idle, the link is lost after about six minutes (boot 10:
no transmit completion in 361 s, then the firmware's loss report); under a
10 s probe cadence it held 600 s. The vendor relies on the firmware's own
keep-alive and sets the station record's keep-alive duration and option
only from the access point's BSS Max Idle Period element (`rlm.c`), zero
otherwise, exactly as this driver's record has them, so the record is not
the difference there either. Why the firmware keep-alive does not hold the
association here is the same firmware question as the rate: a
firmware-originated frame takes its rate from the station's rate table.
The host-side keep-alive (mac80211's null-data probe, admitted narrowly)
is a workaround with a stated cost until that is resolved.

## 4. The corrected approach

1. **Transport.** Replace the polled one-frame-per-read PIO receive path
   with the vendor's shape: the WLAN HIF interrupt (silicon-documented
   enable chain: WHIER, WHLPCR interrupt enable, the CONN wrapper gate),
   the enhanced interrupt structure for per-queue frame counts and
   lengths, one aggregated port read per queue, and the AP DMA engine
   (HIF channel 0 at the documented AP-DMA base, `INFRA_AP_DMA` clock
   shared with I2C) for the data ports in both directions. This driver
   already maps the HIF resource and the DMA facts are recorded in the
   hardware notes; the vendor's `ahb.c` / `ahb_pdma.c` are the reference.
   Expected: receive bounded by the air and the TCP stack, not the worker;
   transmit submission cost removed from the pass.
2. **Rate.** One host-side variable, QoS declaration with QoS data frames;
   in parallel the firmware-side question (what initialises the station's
   rate table) goes to the private reverse-engineering queue, since two
   descriptor variants have now excluded the descriptor.
3. **Keep-alive.** The narrow null-data admission as the workaround; a
   firmware answer may remove it.
4. **Order.** Transport first: it is the one change that moves both
   directions and removes the worker as the shared bottleneck that every
   later measurement (rate, lifecycle, loss) has been read through.

## 5. First transport proposals (2026-10-24)

Proposals 0258 (binding), 0259 (device tree) and 0260 (connectivity owner
and HIF) attach the Wi-Fi HIF's AP-DMA channel 0 and move data-port
transfers of at least 64 bytes through it, following the vendor's register
sequence with one coherent bounce buffer below 4 GiB and the
address-extension bits the vendor sets on every start; management,
security and command writes stay PIO; each direction is its own build
option. The lifecycle profile admits the transmit direction first, where a
wrong address can only send garbage, so the first boot establishes the
channel's addressing and programming on this device; the receive direction,
which carries the throughput question, follows in the next boot. The
host fixture [`tests/hif-dma-test.c`](tests/hif-dma-test.c)
(`tests/run-hif-dma-test.py <kernel tree>`) models the channel and checks
the setup word, the CON/SRC/DST/LEN programming, the extension bits in both
settings, the bounce copy in both directions with padding, the completion
acknowledgment and masking, the timeout path and the attach/free pairing.

## 6. Transmit-DMA boot 1 (2026-10-24): a composition defect, not a driver result

Build `9d276157` (0258–0260, `CONFIG_MT6797_HIF_DMA_TX=y`), candidate
`e838a5de…`, boot2 `42b6e52b…`, mainline boot `bc582fa7…`, returned to
Gemian `af1b8d18…`. The run completed the five-chunk protocol with a
complete sealed log, and reproduced the baseline: TX 2.62 Mbit/s, RX 6.91
Mbit/s host-side (device-side chunks 10.6–12.9 Mbit/s), TX status
histogram 3742 × 0 / 4 × 3. The DMA path never engaged: the log has no
attach record and the data-end record reads `HIF DMA transfers: tx=0 rx=0
poll_max=0 failures=0`. Cause: the candidate composer builds the boot
image from the parent candidate's `board.dtb`, not from the new build, so
the booted device tree had no `wifi-hif-dma` entry; the connectivity
owner found no channel and stayed on PIO. The predeclared expectations
were therefore not tested; nothing about the DMA programming is
established either way. Two defects are recorded: the composer's device
tree source, and the attach block in 0260, which logs nothing when a
prerequisite is missing (a line for the skipped case goes into the
receive-direction build).

**Device-tree provenance finding.** The `board.dtb` every Wi-Fi candidate
has booted since 2026-10-17 is one inherited composition artifact
(`25ab60f4…`, 28,671 bytes) that no kernel package on the host reproduces
(all 1,529 packaged MediaTek DTBs checked). Its `consys` node carries three
properties (`one-shot-wmt-common-init`, `one-shot-wmt-negotiate`,
`coex-antenna-mode`) that no device-tree patch in `patches/` sets, while the
series' own DTS selects `one-shot-wmt-identity-capture` instead and differs
in other nodes (CPU topology, A72 platform state, DVFSP handoff status,
simple framebuffer). The lifecycle results are therefore reproducible from
the candidate lineage, not from a fresh build of the series; reconciling the
DTS with the booted tree is an open item ([roadmap](../../docs/ROADMAP.md))
and must precede any boot from a freshly built device tree, which would
change several variables at once.

**Transmit-DMA boot 2 (staged).** Same package, same kernel and
configuration; the only change is the inherited device tree given the
channel (`reg` 0x11000080/0x80 and the name `wifi-hif-dma` inserted before
`afe`, by `fdtput`; `board.dtb` `25ab60f4…` → `87a637c7…`, 28,703 bytes,
nothing else differs in the decompiled tree). Candidate `ced3a0f3…`, boot2
`b9afec4d…` over `42b6e52b…`, written from Gemian `af1b8d18…`, full readback
verified, device shut down. Predeclaration unchanged from boot 1: the
attach record reads `attached=1 … tx=1 rx=0`; every ordinary data frame of
at least 64 bytes goes out by DMA (`tx` count close to the data-phase
`tx_done`) with `failures=0`; transmit and receive rates within the
baseline band (TX 2.6–2.8, RX device-side chunks 10.5–13). Branches: pass
→ receive direction next (one build option); `attached=0` → the selector or
clock prerequisite, read from the record; `failures>0` or `-ETIMEDOUT` →
address-extension semantics, try the extension bit off; data status 3 while
management frames complete → addressing wrong, stop the path.

**Transmit-DMA boot 2 (2026-10-24): passed.** Mainline boot `6227a6ba…`
(boot2 `b9afec4d…`), returned to Gemian `af51145e…`, complete sealed log
(9,543 records). Attach record `attached=1 selector=0x11403200 addr2=1
tx=1 rx=0`; data-end record `HIF DMA transfers: tx=3712 rx=0 poll_max=0
failures=0` against `tx_queued=3712 tx_done=3711 tx_failed=1`: every
ordinary data frame went out through the channel, the completion flag was
set before the first poll each time, and no transfer timed out. TX status
histogram 3716 × 0 / 1 × 3. Rates in the baseline band: TX 2.69 Mbit/s,
RX 7.04 host-side (device-side chunks 11.8–12.9), CPU idle 86.3 % / 79.5 %.
Established: the channel's addressing (host bounce buffer below 4 GiB
with the extension bit set as the selector says), the CON/SRC/DST/LEN
programming and the completion handling are right for the transmit
direction on this device. Not established: anything about receive, and
any throughput effect (transmit is air-bound at the fixed rate, receive
was still PIO). The attach block now also logs the skipped case (0260
amended: `HIF DMA: not attached: channel= selector= clock=`).

**Next: the receive direction.** One build option changes
(`CONFIG_MT6797_HIF_DMA_RX=y` in the lifecycle fragment, with the amended
0260); the composer takes the parent's device tree, which now carries the
channel. Predeclared: attach record `tx=1 rx=1`; `HIF DMA transfers`
`rx` close to the number of received data frames with `failures=0`;
device-side receive chunks above the 10.5–13 Mbit/s PIO band if the
worker's per-frame bus cost was the receive ceiling (the structural
claim), unchanged if the cost sits elsewhere in the pass; receive data
intact (the chunks complete by byte cap with the TCP stream verified by
the harness). Branches: `failures>0` or a timeout → stop the receive
direction, keep transmit; rates unchanged with DMA engaged → the receive
ceiling is the poll structure (WRPLR read, guard, status) rather than the
byte moves, and the next step is the interrupt and enhanced-status read.
