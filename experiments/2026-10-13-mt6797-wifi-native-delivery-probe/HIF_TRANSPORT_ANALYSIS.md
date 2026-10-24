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

## 7. Conclusion: the transmit data copy is not the bottleneck

Boot 2 moved 3,712 data frames through AP-DMA channel 0 with zero
failures and changed neither direction (TX 2.69 against 2.62–2.76
Mbit/s, RX 7.04 against 6.91–6.99). That closes the transmit side of §1:
after 0236 removed the per-frame host cost, the bytes' path to the HIF is
not what limits transmit; the forced 6 Mbit/s descriptor rate is what
remains (§2), and the receive worker is a separate question (§1, measured
next against 7.0 host-side and about 12 device-side). The transmit
direction stays admitted in the lifecycle fragment: booted and
understood.

How to read a future log: the amended 0260 writes one of two records at
firmware start. `HIF DMA: attached=1 selector=… addr2=… tx=… rx=…` means
the channel is programmed and the `HIF DMA transfers` data-end record
counts what went through it; `HIF DMA: not attached: channel=… selector=…
clock=… tx=… rx=…` names which prerequisite was missing (the device-tree
resource, the EMI selector mapping, the AP-DMA clock, or neither direction
built). Boot 1 would have read `not attached: channel=0`. "Attached and
ineffective" is `attached=1` with a non-zero transfer count and unchanged
rates, which is what boot 2 is for transmit.

## 8. Receive-direction DMA boot (predeclared, 2026-10-24)

The pass-rate boot closed the last host-side explanation of the receive
level: the worker runs about five thousand passes a second and capping
its submissions changed nothing, so the receive ceiling is the polled read
itself, about 400 bus operations per frame. One build option changes:
`CONFIG_MT6797_HIF_DMA_RX=y` in the lifecycle fragment (the amended 0260
is already booted); the device tree is the package's service tree as on
the last three boots.

Measured against the baseline band: RX 7.0 Mbit/s host-side, about 12
device-side; TX 2.6–2.8. Expected: the attach record reads `tx=1 rx=1`;
`HIF DMA transfers` `rx` close to the number of received data frames
with `failures=0`; the received payloads intact (every chunk completes
by byte cap, the TCP stream verified by the harness). Branches: device-side
receive chunks above the 10.5–13 band → the byte moves were the cost and
the direction stays admitted, the next lever being the per-frame
WRPLR/status reads; unchanged with the DMA engaged → the byte moves are
not the cost and the poll structure (WRPLR read, guard, status) is, the
next step being the interrupt and the enhanced status read; `failures>0`,
a timeout, or corrupted receive data → stop the receive direction, keep
transmit, and read the address-extension semantics again.

Riding on this boot, opt-in and not evidence: the console progress
indicator ([`hosts/console_progress.py`](hosts/console_progress.py)). With
`TP_CONSOLE_PROGRESS=1` in the run environment the prepare step injects
into the reviewed leaf a six-line block (variant and boot, stage, cycle
and chunk, rate and elapsed time, link, verdict) rewritten in place on
`/dev/tty0` at the leaf's own markers (capture, join, data, teardown,
verdict), and the throughput helper's device script writes the chunk and
rate lines at its chunk markers; a few writes per second at most, nothing
to the kernel log, the first write error ends all writes, unset means no
change. The leaf reports `console_progress_lines=` at its end; the screen
is never graded and the command line is unchanged (`console=ttyS0`). The injection mechanism is guarded by
[`tests/console-progress-test.py`](tests/console-progress-test.py): every
leaf anchor occurs exactly once, the injected leaf is the reviewed leaf plus
exactly the known block, the flag off leaves it untouched, and the helper's
device script is the original plus exactly the cp() definition and its
chunk lines, flag on and off, with the helper's own safety validators
still passing.

## 9. Receive-direction DMA boot: result (2026-10-24) — engaged, intact, and not the ceiling

Build `fdf4c6b1`, boot2 `51faa318…` over `695a8f88…`, mainline boot
`17c16b91…`, returned to Gemian `84dfc8eb…`, complete sealed log, five
chunks each way, all pass. Attach record `attached=1 selector=0x11403200
addr2=1 tx=1 rx=1`; data-end record `HIF DMA transfers: tx=3870 rx=8510
poll_max=0 failures=0`: every data frame out and every received packet in
went through the channel, the completion flag set before the first poll,
no timeout, and every receive chunk completed by byte cap with the TCP
stream verified. Rates: TX 2.63 Mbit/s (chunks 2.98–3.35), RX 6.67
host-side (device-side chunks 9.6–11.8), CPU idle 85.9 % / 81.0 %
(receive idle up from 78–79 %), status histogram 3874 × 0 / 1 × 3, census
5,114 passes per second.

Branch 2 of §8: unchanged with the DMA engaged. The byte moves were not
the receive cost; what remains per received frame is the poll structure,
the WRPLR read, the guard and the status reads around each transfer, which
is where the vendor's interrupt and enhanced-status read (§1) differ from
this driver. That is the next transport step, predeclared when its turn
comes: one interrupt-driven receive with the enhanced status block read
once per burst, measured against 6.7–7.5 host-side and 10–13 device-side.

Retention: both DMA directions stay admitted. Throughput is unchanged
within the run-to-run spread (the lowest receive chunk, 9.64 Mbit/s, sits
below the earlier 10.0 floor by one chunk's noise; the aggregate 6.67 is
inside 6.67–7.54 seen since the equivalence boots), zero transfers failed
over 12,380 moves, receive CPU idle rose two to three points, and the path
is the vendor's. The counter is kept: a lower receive chunk appeared once;
if the next two boots repeat it, the receive direction is re-examined.

Console indicator, not evidence: the leaf reported
`console_progress_lines=30 console_progress_dead=0`, five stage blocks of
six lines written to the frame-buffer console with no write error; the
helper's chunk lines are written from its own shell and are not counted.

## 10. Receive batching boot (predeclared, 2026-10-25)

What is left per received frame after the DMA boots is register work: the
length register read, the transfer setup, the guard and the status reads,
with the worker making five thousand passes a second (a notice latency of
about 200 µs, so the interrupt is not the first lever).
[0268](../../patches/proposals/0268-wifi-mt6797-receive-by-the-enhanced-status-block-and-aggregated-reads.patch)
does what the vendor's receive path does, by polling: once per worker pass
one 112-byte read of the enhanced status block from the WHISR register
(the receive queues' frame counts and up to sixteen lengths each), then
one aggregated data-port transfer per non-empty queue, split by the
reported lengths with the same header check as before and served from
that cache; the worker loop is unchanged, a pass that finds the cache
empty reads the block once, and the mode is switched on in WHCR
(sixteen lengths, the enhance bit) at the first receive and read back.
The vendor reads that block in its interrupt handler, but the block is a
register read it also polls elsewhere, so no interrupt is needed and
nothing in the queue reorders. Host fixture:
[`tests/hif-rx-batch-test.c`](tests/hif-rx-batch-test.c)
(`tests/run-hif-rx-batch-test.py <kernel tree>`): the enable and
read-back, the block, two aggregates split into three frames served in
block order, -EAGAIN on the empty cache without bus work, one block read
per pass, and the refusals (a count over sixteen, a header that disagrees
with its length). The census (0264) stays.

Single variable against the receive-DMA boot:
`CONFIG_MT6797_HIF_RX_BATCH=y` in the lifecycle fragment; the page-release
fix 0267 is in the same build and its accounting is read on this boot
(the failure path itself stays unexercised unless a join fails). Headline:
device-side receive chunks and host-side receive rate beside the new
`HIF RX batch` data-end record (`on`, WHCR before and after, block reads,
aggregates, frames, empty reads, failures).

| Outcome | Reading | Next |
|---|---|---|
| device-side receive chunks above the 10.5–13 band, or host-side above 8 Mbit/s | the per-frame reads were the cost | keep the batching; move the TX status reads into the same block |
| unchanged (RX about 7 host-side, 11–13 device-side), `on=1`, frames counted, zero failures | the register work was not the cost either; the worker's notice latency and scheduling remain | the interrupt earns its risk next |
| `on=0` (WHCR did not take the bits), or `failures>0`, or frames lost | the mode or the aggregate framing is not what the vendor source says for this firmware | stop batching, keep per-frame receive, read the firmware side |
