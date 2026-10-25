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
| `on=1`, block reads happening, `empty` every pass, `frames=0`: receive stalls with the mode correctly enabled | the block is not pollable on this firmware (the vendor reads it in its interrupt handler; if it is populated only on delivery, polling finds nothing) | revert to per-frame receive; the interrupt is the next variable |
| the `join credit` lines of the management frames missing, `credits=0` at data end | the block carried no TX release counts; the vendor reading of the enhanced block is wrong for this firmware | stop batching, keep per-frame receive |
| a credit still missing with `credits>0` | the merge of the block's counts into the TX status acquisition is wrong | fix the merge against the fixture before any further boot |

The mode across a rejoin: it is switched on once per HIF and the HIF lives
for the boot (`mac->hif` is set at probe; the firmware is started once and
never restarted inside a boot), so the enabled flag and the hardware state
agree across a teardown and a re-arm. A rejoin within one boot (the
AP-loss gate) inherits a fully configured receive mode, not a half one;
teardown does not revert it and has no reason to.

### Boot 1 of 0268 (2026-10-25): the join stopped at its credit wait; the block read had consumed the TX release counts

Build `9846b776`, boot2 `0037de60…` over `bf9bd805…`, mainline boot
`647b420a…`, returned to Gemian `1163163d…`, complete sealed log
(146,439 bytes). The mode took at the first receive (the second TX status
snapshot already reads `WHCR=0x00011000`: sixteen lengths, enhance bit),
and every exchange through the passive scan, the join grant, the peer
record and the authentication frame's response came through the batched
path. Then the authentication frame's page credit never arrived. In the
receive-DMA boot every management frame's `TX done` is followed by `join
credit: pages=1 remaining=0`; here `join TX done: pid=1 status=0` and `join
RX: subtype=11 status=0` are followed, 104 ms later, by `join stopped:
status=-110 first=0 submitted=0x800 debt=1 cleanup=0 branch=1` (branch 1 is
the worker's deadline check; the waiter was the credit wait,
`mt6797_mac_join_wait_credit`, mac.c). No data phase, no `HIF RX batch`
record, no row of the table reached: not a throughput data point, and
nothing about the receive ceiling follows from it. Display probe (not
evidence): framebuffer console bound, tty0 write ok, the indicator wrote.

Mechanism, from the vendor source before any guess. In enhanced mode the
block read of WHISR returns WHISR and the sixteen TX queue release counts
together (`ENHANCE_MODE_DATA_STRUCT_T`: `u4WHISR`, then the TQ counts), and
the vendor releases those counts into its TC accounting from the block
(`nicTxReleaseResource(prAdapter, &prSDIOCtrl->rTxInfo)`, nic_tx.c;
nic.c synthesises the TX-done bit from non-zero counts). The read consumes
them. Our credit path (`mt6797_hif_tx_status`, hif.c) still polled WHISR
and WTQCR0–7 directly, after the pass's receive had read the block, so it
saw zeros and the one-page debt stayed open to the 100 ms credit
deadline. The receive side of 0268 worked; its interaction with the credit
side was not covered by the fixture, which modelled receive only. 0267's
path (a refused command) was not exercised; its accounting is still
unverified on device.

Amended 0268 (same number; this boot of the earlier form is its record):
the counts the block carries are accumulated half-word by half-word and
merged into the next TX status acquisition (WHISR bits and WTQCR words,
the abnormal bits checked merged), with `credits=` in the data-end record
counting the blocks that carried any. With it the three measurement
protections: a count above sixteen is served as sixteen and drains next
pass, a length outside the frame bounds leaves that queue unread this
pass, a header that disagrees with its reported length drops that
aggregate (frames lost, the transport retransmits); each is counted in
`failures`, none poisons receive, and poison is reserved for a bus
failure, said so in the code. The fixture covers all of it (the clamp, the
bad length, the dropped aggregate with the other queue still served, the
credit merge and its clearing), strict checkpatch is clean. Boot 2 keeps
the headline, the band and the table above; the `join credit` lines of
the management frames are the first thing read.

**The page debt of a written command that times out** (`debt=1 cleanup=0`
on this boot). `cleanup=0` on branch 1 is by design: the lifetime
fail-stops without a cleanup submission when the credit wait times out,
because the page of a written command is the firmware's until a release
count returns, and the host must not reuse it. 0267 stays scoped to a
command refused before any write; it is not extended to this path. The
accounting has two layers: `join_page_debt` (mac.c) is the waiter's
bookkeeping, and the re-arm path zeroes it (`mt6797_mac_join_rearm`); the
page ledger itself is the HIF's normal transaction (`tc4_free`,
`tc4_pending_cpu/ffa`, normal_command.h), which re-arm does not touch, so a
page the firmware still owns stays debited there, a late release count is
reconciled against it, and nothing zeroes it short of a cold re-init. The
gap is between the layers: a release that arrives after re-arm, with the
waiter's debt already zero, reads as `join credit overflow` (-EPROTO) in
the guard and stops the new join; the ledger is right, the bookkeeping is
not. Contract, for the AP-loss gate (the boot that exercises exactly this
path): after a failed join and before the next, the accounting is
reconciled by a release count read into the ledger, or by the lifetime's
retirement with the ledger whole (`mt6797_hif_normal_idle`, hif.c:
`tc4_free == tc4_limit`, nothing pending), or by a re-init; never by
zeroing. The gate's predeclaration reads the ledger at the failed join's
stop and before the rejoin, and says whether a late credit was reconciled
or read as overflow ([lifecycle record](LIFECYCLE_RESULT.md)).

### Boot 2 of 0268 (2026-10-25): the credits came; the join guard refused at the second EAPOL message

Build `192c71ff`, boot2 `a9b89cfb…` over `0037de60…`, mainline boot
`9335c457…`, returned to Gemian `0b7f827b…`, complete sealed log
(150,285 bytes). The merge did what it was written for: every command and
frame's page credit returned (`join credit: pages=1 remaining=0` 0.8 ms
after the authentication frame, the association frame and the first EAPOL
message, where the register path had reported them only at `TX done`,
7–8 ms later), the join authenticated, associated, activated the station
(`state=3 lifetime=1`), received EAPOL message 1 and sent message 2
(`eapol sent: pid=3 pages=2`, credited, `TX done: pid=3 status=0`). Then,
172 µs after that `TX done`, `join stopped: status=-5 first=0
submitted=0x801 debt=0 cleanup=0 branch=2`. Branch 2 is the join guard
(`mt6797_mac_join_guard`, mac.c), which returned -EIO with the waiter's
debt at zero. No data phase, no `HIF RX batch` record: not a throughput
data point. Display probe (not evidence): framebuffer console bound, tty0
write ok, the indicator wrote.

Where -EIO can come from in that guard, from source: (a) the identity read
of WCIR (chip id 0x0279 with `WLAN_READY` bit 21) failing, that is the
firmware no longer ready; (b) the TX status acquisition refused by its own
admission (`mt6797_hif_tx_status`, runtime form: the normal phase must be
`NVRAM_SUBMITTED`, the baseline and the normal attempt made), which
returns -EIO without poisoning; (c) the abnormal bits of the merged WHISR
(bit 6 `ABNORMAL_INT`, bit 31 `D2H_SW_ASSERT_INFO_INT`), which poison;
(d) the ledger's reconcile refusing the counts (`mt6797_normal_reconcile`:
a count in a queue other than TQ1, TQ14 and TQ15, or a count above the
unmatched debt), which aborts the ledger with -EIO. The log cannot tell
them apart: the stop line carries the mac's first error (0), not the
HIF's, and nothing recorded the words. One candidate stands out from the
vendor source and this boot's own timing: the block reports the release
at the moment the firmware frees the page (0.8 ms after submission), the
register path reported it at `TX done`; if the firmware also reports a
count at completion (a page freed in two steps, or the same page twice),
the second count meets a debt of zero and (d) is exactly this symptom.
The vendor tolerates that: `nicTxCalculateResource` (nic_tx.c) clamps the
TX-done counts to the pages in use (`ucExtraTxDone`, the "extra TX done"
accounting), where our ledger refuses with an abort. This is a reading,
not a finding; boot 3 settles it.

What changed for boot 3, all offline: the guard records its refusal with
the words it saw (`join guard failed: ret= wcir= own= valid= whcr= whisr=
wtqcr0= wtqcr7= hif= pending_whisr= pending0= pending7= batch_failures=
credits=`), so (a) shows in `wcir`, (b) in `valid=0`, (c) in `whisr`, (d)
in `valid=0x3ff` with the counts in `wtqcr7`/`wtqcr0` and `hif=-5`. The
fixture now models both consumers of WHISR and the queue counts over one
clear-on-read hardware state: the credit path alone with the mode off
(unchanged behaviour), counts arriving between two block reads
(accumulated, not doubled), a block carrying no counts (`credits=` still),
and counts arriving while the credit path is mid-acquisition (added in
that one acquisition, nothing split or left pending); the merge-dependent
cases fail against a copy of the driver with the merge removed (checked:
the first of them aborts at its assertion). No driver behaviour changed
beyond the record line.

**Boot 3 reading, TX first.** The merge changes TX accounting, and its
failure mode is over-credit: more pages released than reserved raises the
in-flight depth, which looks like progress. So before the receive number
means anything: TX must sit in the 2.6–2.8 Mbit/s band (chunks seen up to
3.35 so far), `debt=0` at the stop line with `failures=0`, the byte caps
and the TCP verification intact. TX above 3.4 Mbit/s, or any non-zero
debt at the stop, stops the boot: the merge is over-releasing, the receive
number is held ungraded, and the next step is the accounting, not the
transport. A `join guard failed` line with `valid=0x3ff` and counts
against a zero debt is branch (d) above and goes the same way: the
accounting, with the vendor's clamp as the reference, before any further
boot. Only with TX in band and the debt whole do the receive rows of the
table apply.

**Reachability and ownership, answered from source** (two of the three
questions every predeclaration now carries; the third, for every register
the new code writes, what the vendor writes there or that it writes
nothing, was added after boot 3 and would have caught it: the vendor
writes WHCR once, at init, to the firmware's default). Reachability: the WHCR write is
`mt6797_hif_write32_locked(hif, 0x0c, …)` in `mt6797_hif_rx_batch_enable`,
reached from `mt6797_hif_receive` on the first receive once the firmware
is ready, the capability complete and the normal phase at
`CAP_RECEIVED`/`NVRAM_SUBMITTED`: the same admission every receive passes,
nothing earlier refuses it (boot 1 read back 0x00011000). The block read
(`mt6797_hif_rx_batch_block`: one setup word, 28 data-port reads of the
WHISR register) and the aggregated transfer (`mt6797_hif_data_transfer`,
ports 0x50/0x54, which `encode_command` admits for READ) reach the bus
with nothing consuming them first; the cache serve returns -EAGAIN with no
bus work when the cache is empty and no pass has armed a refill. The
guard record is a `dev_err` on the existing error path. Ownership: WHISR
(0x10) is clear-on-read in both forms, so `mt6797_hif_tx_status` (every
pass, and the two boot snapshots) now sees the register value OR-ed with
what the block consumed; `mt6797_hif_read32` admits only registers 0, 4
and 0x90 and never reads it. WTQCR0–7 (0x130–0x14c) are clear-on-read and
read only by `mt6797_hif_tx_status`, which now sees the register counts
plus the block-carried counts, half-word by half-word. WHCR (0x0c) is
read-modify-written once by the enable and read by `mt6797_hif_tx_status`
for its record (0x00011000 from then on); no other writer in the driver,
and the firmware-start path does not touch it. WRPLR (0x90) is read by the
per-frame path and `mt6797_hif_read32`; while the mode is on the per-frame
path is not entered and the block's lengths replace it. The data ports
0x50/0x54 are consumed by the aggregated read; the per-frame path would
consume the same FIFO and is not entered. The block's receive counts and
lengths describe what is queued and are re-reported until the port read
drains it (assumed from the vendor's model; a queue skipped for a bad
length is the case that tests it, and `failures=` reports it). What no
source answers is the timing of the TX release counts the firmware places
in the block against those it places in the registers: boot 2's open
question, and what the guard record is for.

### Boot 3 of 0268 (2026-10-25): the guard's words name the abnormal interrupt; the cause is our own WHCR write

Build `285d6aa3`, boot2 `490008d5…` over `a9b89cfb…`, mainline boot
`d3f812a9…`, returned to Gemian `4d65ad5c…`, complete sealed log
(150,250 bytes). Authenticated, associated, station activated, four
beacons delivered; then 416 ms in which no frame was delivered (beacons 5
to 8 are missing), and the guard record:

```
join guard failed: ret=-5 wcir=0x00300279 own=0x00000100 valid=0x3 whcr=0x00011000
  whisr=0x00000042 wtqcr0=0 wtqcr7=0 hif=-5 pending_whisr=0 pending0=0 pending7=0
  batch_failures=0 credits=2
```

The four sources, against that line and the two logs. (a) The identity
read: excluded, `wcir` carries chip id 0x0279 with `WLAN_READY` set and
the ownership bit is held. (b) The acquisition's admission: excluded,
`valid=0x3` says it read WHCR and WHISR, so it was admitted. (d) The
ledger's reconcile: excluded, the acquisition was refused before the
WTQCR reads (`valid` lacks their bits), the counts are zero and nothing
was pending; across boots 2 and 3 sixteen page credits returned, each
matching its reservation, no overflow line. (c) The abnormal bit: the one
left standing, and confirmed: `whisr=0x42` is `RX0_DONE_INT` with
`ABNORMAL_INT` (bit 6). Boot 2 stopped with the same status at the same
guard with its words unrecorded; it is read as the same event. `failures=0`
says every aggregate the host read split cleanly; the device, not the
split, raised the flag.

The cause, from the vendor source. Its SDIO init (`nicSDIOInit`, nic.c)
programs WHCR with the reported-length count field at 0 ("unlimited", the
field's documented range is 0–15 and a request of sixteen maps to 0) and
`RX_ENHANCE_MODE_EN` (bit 16) clear: the vendor build has
`CFG_SDIO_INTR_ENHANCE 1` (the 112-byte status read this proposal uses)
and `CFG_SDIO_RX_ENHANCE 0`. The firmware's default WHCR is that
configuration already (every boot's first TX status snapshot reads
`WHCR=0x00000000`). The earlier form of 0268 wrote 0x00011000: bit 16 and
a count of sixteen. Bit 16 is the RX enhancement, a mode the vendor's own
receive code describes and never runs on this chip: in it every
receive-port read returns the frames followed by four bytes of padding
and a fresh copy of the status block (nic_rx.c, the `kalMemCopy` after
the last frame of each aggregate, and the coalescing buffer sized for it),
which the host is expected to consume. Our aggregated reads never read
those 116 bytes. What exactly the device objected to is unread (WASR and
WASR2, which the vendor's abnormal handler reads before resetting the
chip, were not in the record); the mode mismatch is the one deviation from
the vendor's configuration on this path, and the stall before the flag
fits a FIFO carrying unread state behind every read. The proposal's
"vendor sequence" comment on the enable was wrong, and it was the kind of
claim the ownership question is for: WHCR's other writer is the firmware's
reset default, and we overwrote it.

On the owner's reading that OR-ing the block's WHISR into the polled
acquisition manufactured the edge: the record does not support that for
this boot. Bit 6 is a hardware event whichever read carried it, the
acquisition's own register read is part of the 0x42, and the vendor's
response to `ABNORMAL_INT` from either read is a chip reset, not a
dismissal. The rule itself is right and is now the code: in enhanced mode
the block is the single owner of WHISR and the TX counts; consumers derive
from it and never copy it. The counts are merged as additive data with the
TX-done bit they imply synthesised for the record (`synth=`), the block's
edge bits are not copied anywhere, and a block that carries bit 6 or bit
31 is its own recorded finding (`block_abnormal=` with the word, WASR and
WASR2 in the guard record) that fails the HIF, as the vendor resets the
chip for it. Dropping a block-carried abnormal would run the FIFO in a
state the firmware has declared bad; that is the explicit decision.

Amended 0268 for boot 4: WHCR is not written at all; the mode is confirmed
by reading (bit 16 clear, count 0–15) and refused otherwise. The unused
register-write helper is gone, so the proposal has no WHCR writer. The
guard record adds `synth=`, `wasr=`, `wasr2=`, `block_whisr=` and
`block_abnormal=`; the data-end record carries `block_abnormal=`. The
fixture covers the read-only confirmation, the uncopied WHISR beside the
synthesised bit, the block-carried abnormal (recorded, fatal), and the
join replay the owner asked for, at the ledger: the state-1 record's two
pages credited through the block, the authentication frame's page
credited through the registers, the second EAPOL message's two pages
through the block and its completion carrying no counts; the guard's
acquisition passes each with the synthesised bit where the block carried
the counts, and trips only on a genuine abnormal in the register. The
standing audit gains its third question, which this failure was: which
consumer's invariant now sees these values, and does it still mean what
it meant? For 0268: the reconcile sees the same counts earlier (at the
page's release rather than at `TX done`, 0.8 ms against 7–8 ms) and its
bounds held through sixteen credits; the acquisition's abnormal check now
sees the register alone, as it always did; the block's abnormal has its
own path.

**Boot budget (recorded before boot 4).** Boot 3 was the last diagnostic
boot for this transport, and its words named the source. Boot 4 is the
one measurement boot: TX first (the 2.6–2.8 band, `debt=0`, `failures=0`,
`on=1 whcr=0x00000000`, `block_abnormal=0`), then the receive rows of the
table. A guard refusal or a block-carried abnormal on boot 4 reverts
receive batching to the per-frame path (the option off in the lifecycle
fragment, the proposal kept) and moves the study to source, with the
interrupt and the block, and not to the device.

Reachability and ownership for boot 4, the delta: there is no WHCR write
to reach; the enable is one register read under the same admission as
before. WASR (0x20) and WASR2 (0xe0) are read only on the guard's failure
path, after the refusal, through `mt6797_hif_read32`, which admits them
without the deadline entry so a poisoned context can still be described;
the vendor's abnormal handler reads them once before its reset, whether
they clear on read is not stated, and nothing else in this driver reads
them. The merged counts' consumer is the reconcile, unchanged.

### Boot 4 of 0268 (2026-10-25): the measurement — the register work was not the receive cost either

Build `796d43bf`, boot2 `96e1f41e…` over `490008d5…`, mainline boot
`7aa0ea7c…`, returned to Gemian `ae210f69…`, complete sealed log
(1,696,642 bytes), five chunks each way, standard disconnect accepted.

TX first, as predeclared: 2.64 Mbit/s (chunks 3.10–3.22), inside the
2.6–2.8 band and under the 3.4 stop line; `debt=0` at the lifetime's end
(`join cleanup: stage=3 credits=returned slots=retired`, the cleanup
timing lines closing at `debt=0`); `failures=0`; the byte caps and the
TCP receipt intact (`all_pass True`). The merge is accepted: 21 page
credits over the join and the cleanup, each matched, no overflow line, no
guard record. 0267's path (a refused command) was not exercised; the
ordinary boot's accounting is whole.

Then the receive rows. `HIF RX batch: on=1 whcr=0x00000000 reads=137007
aggregates=5706 frames=12754 empty=131301 max=16 failures=0 credits=3647
block_abnormal=0x00000000`: the mode held for the boot without a WHCR
write, every frame of the data phase came through the block and the
aggregated reads (up to sixteen per block, 2.2 per aggregate on average,
96 % of the passes finding nothing), nothing was dropped, split wrongly or
flagged. Receive: 6.37 Mbit/s host-side (device-side chunks 8.5–12.2,
the last two below the 10.5–13 band), CPU idle 77.9 %; the pass census
6,125 passes/s at 0.030 frames per pass. That is the table's second row,
unchanged within the series' spread: with the per-frame length read, the
transfer setup and the status reads collapsed into one block read and one
aggregate per queue, the receive number did not move. The receive data
copy (DMA) was not the cost, and the per-frame register work was not the
cost.

What the same log says about where the cost is, read before the next
lever is chosen. The transmit completions per second across the data
phase run at 185–273 during the receive chunks and 377–556 during the
transmit chunks (`join TX done` lines, 4,035 completions, inter-completion
gap median 0.70 ms, p90 7.9 ms). During a TCP receive the device's
transmissions are the acknowledgements, one per two segments: 5 MiB in
6.58 s is about 545 segments/s and about 270 acknowledgements/s, which is
the transmit completion rate observed in those seconds. The receive
throughput of a TCP flow is window over round-trip time, and the
round-trip time here includes our transmit path's latency for each
acknowledgement (submit to completion, the 4–9 ms measured on the
transmit side since the yield boot), not the receive path's. So the
receive number may be clocked by the transmit path and would not move
with any receive-side lever, interrupt included; the three receive boots
that changed nothing (DMA, batching, the pass-rate cap) are consistent
with that and do not distinguish it. One measurement does: a receive
chunk that needs no acknowledgements (UDP, same host, same byte cap) or
the round-trip time from the device at rest; if the UDP receive clears
the TCP number by a wide margin, the receive ceiling is the transmit
latency and the interrupt is not the next step; if it does not, the
receive path itself holds and the interrupt is. That is a protocol change
to the measurement and the owner's call; the table's row says
"interrupt next" and it stands as written until then.

Retention (the owner's decision, 2026-10-25): 0268 measured neutral, and
the project's precedent for neutral is retirement (phase-pending, 0255,
0263, 0265). What it carries beyond the neutral number is a change to the
TX credit accounting on the path every remaining boot depends on, and an
admitted default should hold a number that justifies it; this one holds a
neutral with three receive chunks below the band. So the admission is
reverted: `CONFIG_MT6797_HIF_RX_BATCH` leaves the lifecycle and rate
fragments, the per-frame receive path is the admitted default again, and
the proposal stays in the series behind its option, with its fixtures,
for the boot that needs it (none is named; if a receive measurement later
needs the batched path to be readable, it is admitted when that boot is
staged). The series' receive levers are all measured: scheduling, depth,
DMA, batching, pass cap.

**What sets the 4–9 ms from submission to completion, from source (no
boot).** The driver learns a completion from the firmware: every data
descriptor requests a transmit-status report to the MCU with a PID
(`join-tx.h`: `d[20] = pid; d[21] = 2`, "TX status to MCU"), and the
firmware answers with a TX-done event that arrives through the receive
path (`join-events.h`, `mt6797_join_tx_done`; mac.c prints `join TX done`
from it). The worker sees that event on the pass after it lands, about
160–200 µs at the measured 5,000–6,000 passes/s; nothing in the driver
waits for a later credit event to declare the frame complete (the page
credit is separate accounting). So the 4–9 ms are spent between the HIF
write and the firmware's event, on the firmware side of the bus. The
vendor driver requests the MCU status report only for frames that carry a
completion handler (management, EAPOL: `nicTxFillDesc`, nic_tx.c, sets
the PID and `TXS_TO_MCU` under `if (prMsduInfo->pfTxDoneHandler)`), and
completes ordinary data on the page release counts alone; our descriptors
ask the MCU for a report on every data frame, which the vendor firmware
never does for data. Two things that answer cannot separate: whether the
frame goes to air late (queued behind the fixed-rate path or the per-frame
MCU report) or goes early and is reported late. The probe's round-trip
time is the measurement that separates them, because it does not depend
on when we learn of the completion. If the air transmission is late, the
lever is ours (no MCU report for data, completion on credits, as the
vendor does; then the rate); if only the report is late, the completion
latency does not clock receive and the acknowledgement reading above is
wrong. The inter-completion gap of 0.70 ms median says the firmware
pipelines frames; it does not say which of the two.

## 11. Receive probe (predeclared, 2026-10-25): is the receive number clocked by the transmit path?

A mechanism measurement, recorded beside the graded numbers and never
graded; the measurement protocol stays TCP for every graded number,
including the vendor comparison. One boot on the lifecycle tree with the
batching admission reverted (build `7ba78e08`: the per-frame receive path,
AP-DMA both directions, 0267, 0268 compiled out), the probe injected
host-side at prepare time
([`hosts/receive_probe.py`](hosts/receive_probe.py), guard
[`tests/receive-probe-test.py`](tests/receive-probe-test.py)). Three
readings in the same boot, because two cannot separate the first two
causes:

- **UDP receive, no return traffic.** Before the chunk loop, the device at
  rest: the laptop sends 1400-byte datagrams for one second at 10, 20 and
  30 Mbit/s to a closed UDP port on the device, each burst triggered by
  the device; the device kernel counts them in its UDP `NoPorts` counter
  (`/proc/net/snmp`), the laptop counts what it sent. Delivered rate and
  loss (sent minus counted; the device has no UDP receiver, so a sequence
  gap is not available) at each offered rate; the headline is the
  delivered rate at the highest offered rate with loss under one percent.
  Return traffic: the kernel's port-unreachable, rate-limited to one per
  second by default.
- **Round-trip time at rest.** One `ping -c3` from the device to the
  laptop before the chunks, the summary line.
- **The device's TCP receive window.** During each TCP receive chunk the
  laptop's send socket is sampled every 50 ms (macOS
  `TCP_CONNECTION_INFO`): the window the device advertises, the
  congestion window, the segment size and the TCP round-trip time. The
  device's receive buffer parameters are the kernel defaults (the
  initramfs sets none; `tcp_rmem` 4096/131072/6291456), not read on the
  device because the owned command has a 4096-byte bound (the probe's
  device block fits it with 33 bytes to spare); the advertised window is
  the measurement.

**Prediction.** If the acknowledgement latency is about 3.7 ms and one
acknowledgement covers two segments, a TCP receive runs at about
2 × MSS / latency = 2 × 1460 × 8 / 3.7 ms ≈ 6.3 Mbit/s, which is what the
series measures (6.4–7.5 host-side); the vendor's band would then follow
from a lower acknowledgement latency.

| Reading | Cause | Next |
|---|---|---|
| UDP far above 6.4 Mbit/s with loss under 1 %, RTT about 4 ms, window ample | the transmit path's completion latency clocks receive | the interrupt is not the next step; the shared limiter is TX completion latency (the MCU status report on every data frame, the fixed-rate path) |
| UDP far above 6.4, RTT well under 1 ms, window small | TCP flow control on the device, not transmit latency | fix the device's receive window and re-measure TCP before touching the transport |
| UDP near 6.4 (loss rising with the offered rate) | the receive path holds | the interrupt earns its risk after all |

The graded TCP numbers of this boot are read as every boot's: TX first
(the 2.6–2.8 band, `debt=0`), then receive, against the rx-dma row (the
same tree without 0268 admitted).

**The three questions.** Reachability: the probe writes nothing to the
device's registers and changes no driver code; its bus traffic is the
device's own `ping`, three `nc` connections to the laptop (the triggers)
and the kernel's handling of datagrams to a closed port; the device block
runs inside the owned PTY command before the chunk loop, after the
owner's identity checks, and the helper's own validators (idle policy,
receive sinks, the command bound) admit it with the flag on; with the flag
off the device script is byte-identical to the reviewed one (the guard
checks both). Ownership: the laptop socket option is read on the
laptop's own socket; the device's UDP counter is the kernel's, read twice
around each burst; neither is destructive and nothing else in the
measurement reads them. The third question: the probe writes no register,
and the vendor writes none for it.

**What it does not measure.** The RTT from `ping` and from the TCP samples
includes the AP and the laptop's own stack, so a 4 ms reading says the
loop is slow, not which half; the UDP reading is what assigns it to the
device's transmit side (receive moves freely without acknowledgements) or
to its receive side (receive does not move).

### Probe boot 1 (2026-10-25): the TCP samples came, the ping and the UDP bursts did not

Build `7ba78e08`, boot2 `cacce7a1…` over `96e1f41e…`, mainline boot
`07a5f5db…`, returned to Gemian `bc556eb9…`, complete sealed log
(1,629,872 bytes). Graded numbers (TCP, as every boot): TX 2.69 Mbit/s
(chunks 3.19–3.43, the 3.43 just above the band's 3.4 line on one chunk;
`debt=0`, 21 credits matched), receive 6.78 host-side (device-side chunks
10.1–12.5), the batching option compiled out (`on=0`, no block reads), the
rx-dma row reproduced on the reverted tree.

The probe itself ran half. The TCP samples are valid and are the first
reading of their kind: during every receive chunk the device's advertised
window sat between 64 KB (its floor at the chunk start) and 212–452 KB
(median 151–238 KB), the laptop's congestion window at 200–256 KB, the
segment size 1448, and the laptop-measured TCP round-trip time at a
median of 61–102 ms per chunk, with maxima of 113–203 ms. The window is
ample. The round-trip time during a receive is not 4 ms; it is a queue:
the laptop offers 20–24 Mbit/s in each burst, the device takes 10–12.5
Mbit/s, and the difference waits somewhere between the laptop's socket
and the device's stack for about a hundred milliseconds.

The ping and the three UDP bursts recorded nothing (`TP3_PING` empty,
`TP3_UDP n 0` three times, the laptop's trigger listener never accepted),
and the cause is this record's own injection: the probe's block was
inserted into the device script after the `HOST` and `BOOT` placeholders
had been substituted, so its `ping` and `nc` lines went to the literal
name `HOST` (the device has no resolver; `timeout 6` ended the ping, the
triggers failed to connect). The owner's rule applies to host-side code
as it does to the driver: the injection's reachability question was not
asked of the substitution order. Fixed: the block is inserted before the
substitutions; the guard now refuses a device script with an unbound
placeholder and checks that the probe lines carry the host; and the
trigger connection now yields a second round-trip reading at rest (the
laptop sends one byte and reads its kernel's RTT sample for that
connection), beside the ping. The kernel image is unchanged, so the re-run
is a same-image boot (the installer records `skipped-already-matching`
after its full readback and shuts down as before).

One more candidate for the table, from source. The driver registers twelve
legacy rates (1–54 Mbit/s, mac.c) and no HT capability, so the access
point's downlink to this station is legacy OFDM at the rate its own
control picks from that set; the device-side receive of 10–12.5 Mbit/s of
TCP payload is what 18–24 Mbit/s OFDM carries. The vendor control ran
with HT. If the UDP delivered rate tops out near the same 11–12 Mbit/s
with low loss at 30 Mbit/s offered, the ceiling is the access point's
rate to a legacy-only station, not our receive path and not the
acknowledgement clock; that reading goes to the table as a fourth row,
with the HT capability (and the station record's rate set) as the next
lever.

| Reading | Cause | Next |
|---|---|---|
| UDP delivered near 11–12 Mbit/s device-side whatever is offered, loss low below it and rising above it, TCP RTT at rest short | the access point's legacy downlink rate to a station that advertises no HT | advertise HT (and the matching station record) before any transport lever |

### Probe boot 2 (2026-10-25): a graded repeat; the probe ran disabled by the staging

Same image (`cacce7a1…`, the installer recorded `skipped-already-matching`
after its full readback), mainline boot `4627e5ea…`, returned to Gemian
`1172db3c…`, complete sealed log (1,499,754 bytes). Graded: TX 2.67
Mbit/s (chunks 3.16–3.40), receive 6.99 host-side (device-side 11.8–12.5),
`debt=0`, the third reading of the reverted tree in a row. The probe did
not run: the staging script for the re-run was derived from the first by a
name sweep that also renamed the probe's environment flag, so the prepare
step recorded `receive_probe: false` and the device script carried no
probe block (the receipt holds a disabled probe record). The staging now
asserts, before anything touches the device, that the plan says the probe
is on and that the device script the helper will send carries the host in
its probe lines; the staging scripts are host tooling outside the
repository and the lesson is recorded here because it cost a device
cycle: three cycles of this probe have been lost to the harness (the
unbound placeholder, the renamed flag), none to the driver. The TCP
samples of boot 1 stand; the ping and the UDP readings are still owed.

### Before probe boot 3: the two faults named, the gate on the rendered run, the queue

**Activation.** The run's environment set `TP_RECEIVE_PROBE2=1` while the
prepare step, the helper and the guard read `TP_RECEIVE_PROBE`, so the
plan recorded `receive_probe: false` and the probe never armed. The cause
was the staging script for the re-run, derived from the first by a name
sweep that also swept the flag. One name, `TP_RECEIVE_PROBE`, is read by
the prepare step, the helper, the guard and the preflight; nothing else
exists to be set by habit, and the preflight refuses an environment that
carries any other `TP_RECEIVE_*` name.

**Receive direction.** `rx_unicast=0 rx_group=0 rx_dropped=0` on the
data-end line while `tx_done=3513` and the receive chunks completed: no
leg was dead. The helper's own output has every receive chunk closing with
its full megabyte on the device (`TP2_PROGRESS direction=RX chunk=n
phase=end rc=0 bytes=1048576`, five times) and the interface counting
3,672 received packets over the receive direction; the laptop's send leg
and the device's listener both worked. The three counters are the dead
thing: they belong to the join worker's own data-delivery branch (mac.c,
the `mt6797_data_rx` path bounded by `MT6797_JOIN_DATA_RX_MAX`), which the
lifecycle tree never enters because received data has gone through the
runtime delivery path (`mt6797_ccmp_receive`, `ieee80211_rx_napi`) since
the single-arm consolidation; they have read zero on every boot of this
series, including the ones that moved five megabytes. The live path keeps
no count of delivered frames at all, so the data-end line is silent about
receive: that is the finding the owner's rule names (a silent leg is worse
than a failed one), and the next build adds the delivered-frame count to
the data-end record and drops the three dead counters from it (logging
only), alongside the received-rate record.

**The gate.** [`tests/probe-preflight.py`](tests/probe-preflight.py) reads
the rendered artefacts of a prepared run (the plan, the environment, the
helper the run will load, the device script it will send) and prints one
line per check: every feature flag in the plan agrees with the
environment and no stray flag exists; the rendered device script carries
the probe block, the receive listener, the transmit sender, both
directions and five chunks, each by anchor count, with no unbound
placeholder, within the command bound and admitted by the helper's own
validators; the helper writes the probe record and creates the trigger
under the same flag; offline, the UDP send leg paces on loopback, the
laptop's ping to its own address and the trigger connection each record a
round trip, a datagram arrives on a loopback socket, and a two-ended TCP
transfer runs through the helper's receive endpoint with its samples. Run
against boot 2's rendered run it refuses on seven lines (the stray flag,
the disabled plan, the three probe anchors, the endpoint without the probe,
the ping); the staging stops at a refusal before anything touches the
device.

**Probe boot 3 (boot A), what it must produce.** The device's advertised
window and the in-chunk TCP round-trip time as interval samples (every 50
ms, listed, not only a median); the laptop's ping to the device at rest
(before the owned command) and in-chunk (during the third receive chunk);
the device's ping to the laptop at rest and the trigger connections' TCP
round trips; the UDP delivered rate and loss at 10, 20 and 30 Mbit/s
offered. The pair of pings is the discriminator the 61–102 ms in-chunk
reading demands: slow only under load is a queue, slow at rest is policy
or path. The UDP reading separates the downlink from the acknowledgement
path, and the fourth row (the access point's legacy downlink rate to a
station that advertises no HT) stays in the table.

**The queue after it, as the owner set it.** Boot B: stop requesting the
MCU transmit-status report on ordinary data descriptors and complete those
frames on page credits, as the vendor does, management and security
keeping their reports; branches as predeclared (latency falls with TX up
and in-chunk RTT down confirms; RX rising with no receive-side change
confirms the acknowledgement clock in the same boot; latency unchanged
means data frames are not retired on credits the way the vendor's are);
two attempts, then the record. The next build also carries the
received-rate record, mirroring 0262 for received frames behind its own
option, once the source confirms the received-frame status carries the
rate. Boot C: the fixed-rate sweep on the data descriptor's rate code (6 →
54, 24 as the fallback), a transmit-side change that moves the receive
number proving the receive measurement a transmit property. Boot D: the
state-2 encoder attempt, one line of admission, one boot, the rate thread
closing on its result. The AP-loss gate stays independent of all of it.

**Absence ledger.** WHCR never written by the vendor beyond its init
default; WHISR never copied by a consumer; station state 2 never sent
through our refused encoder; and the MCU transmit-status report never
requested by the vendor for a plain data frame. Four instances; the third
question stays in every predeclaration.

### Probe boot 3 (2026-10-25): voided before the measurement; recovered through the reviewed path

Same image (`cacce7a1…`, installer `skipped-already-matching`), mainline
boot `d6563d2d…`. The join completed and the data window opened; the
measurement never started. The receipt names the helper's exception:
`measurement exceeds retained owner-observation bound`, the helper's own
check that the owned device command stays within 4096 bytes. The preflight
had passed that check at 4073 bytes with a 405-byte stand-in for the base
command; the run forms the base from the cohort's command with its ready
placeholder filled (433 bytes), so the real command was 4101 bytes and the
helper refused before any bus traffic. The leaf then waited for a
measurement that never came: the data phase ended by `connection-loss`
after 368 s when the host chain closed its stream, and the session host
refused export, seal and recovery together ("P2 remote owner not
confirmed quiescent"), leaving the device in mainline.

Recovery, through the reviewed path and separately from that refusal
(`preserve-and-return.py`, the station-2 precedent): live identity and the
RAM guard verified, the post-session quiescence proof passed (no owner
remained; nothing was killed), the full log sealed
(`complete-log-through-seal`), the native reboot requested (the first
request ended on the outer timeout with the SSH disconnect unconfirmed, the
second confirmed it), changed-ID Gemian `37bc58e9…` confirmed 15 s later.
The device never needed the owner's hands.

**Recovery unbundled from export.** The session host's refusal couples two
different preconditions: export and seal need quiescence, recovery needs
verified identity and the reviewed path. The cohort's refusal is sealed
and stays as it is; the unbundling lives in the watcher that starts the
run: the run has a wall clock of 300 s, and when it ends with the session
refused, failed or timed out while the device is still reachable on the USB
link, the watcher runs the reviewed preservation and return at once and
records the quiescence proof's outcome either way. A helper exception
therefore ends in a sealed log and a Gemian boot within minutes, not in a
stranded device. The sealed chain's own stream read is not bounded by this
(its sources are hash-pinned); the bound is the run's wall clock and the
measurement runner's 90 s timeout.

**The six fixes, in the owner's order.** The probe block runs after the
chunk loop, inside one subshell that cannot fail the run, every command in
it bounded. The trigger is `$BB timeout 5 $BB nc -w2 HOST 48003 </dev/null
2>/dev/null >/dev/null || true` (the redirections in that order because the
helper's receive validator reads the last sink of an `nc` line and admits
only `/dev/null`). A rate with no matching send is recorded `offered:
false`; the trigger records the connecting address and refuses nothing.
The measurement runner call carries a 90 s timeout. The sender paces by
sleeping; the in-chunk ping runs at 50 ms intervals (the laptop admits it
unprivileged). The counter window is 2.5 s. The device-side ping is gone
(the laptop's pings at rest and in-chunk replace it, and the block had to
lose 30 bytes to fit the real base): the block is 290 bytes quoted and the
rendered command 4029 bytes against the 4096 bound.

**The device block has an offline test.**
[`tests/probe-device-block-test.py`](tests/probe-device-block-test.py)
runs the block in a POSIX shell against a local trigger listener that sends
one second of datagrams to a closed port per trigger, on Linux with a
busybox binary; run in the development VM with the device's own busybox
(copied from the installed initramfs, 1.36.1), it emitted the three
`TP3_UDP` lines with counts equal to the listener's sends (363, 362, 366)
and exited in 7.6 s. The preflight now forms the base command exactly as
the run does and checks that the block follows the chunk loop. The
`TCP_CONNECTION_INFO` offsets stand (f[10] `snd_wnd`, f[11]
`snd_sbbytes`, f[13] `rttcur`, f[14] `srtt`, against `netinet/tcp.h`); the
field is relabelled the effective send window.

**Boot 4 predeclaration, the delta.** Readings as for boot 3 (window and
in-chunk RTT as interval samples, laptop pings at rest and in-chunk, trigger
round trips, UDP at three offered rates), with the device block after the
chunks. What a silent or refused run now produces: a bounded failure, the
run ending at its 300 s wall clock at the latest (the measurement runner at
90 s), the reviewed preservation and return following at once, the sealed
log and the Gemian boot id in the record; a void boot can no longer look
like boot 3.

### Probe boot 4 (2026-10-25, 11:39 UTC): the readings, graded correctly

Same image (`cacce7a1…`), mainline boot `2f327013…`, returned to Gemian
`1b6850a9…` through the harness's own path, complete sealed log
(1,686,335 bytes). The run's verdict line read `FAILED rc=1` and the
receipt `all_pass: false`; both are artefacts of the measurement
machinery, not of the driver's data path, and the readings stand as
measured:

| Reading | Value |
|---|---|
| TX, per chunk (host received) | 3.73–4.07 Mbit/s (aggregate 3.14 over 6.17 s) |
| RX, per chunk, device-side | 14.46–15.83 Mbit/s; host-side bursts 29.5–36.1; aggregate 7.78 |
| UDP offered 10 Mbit/s, no return traffic | 893 sent, 893 counted, delivered 10.01, loss 0 |
| UDP offered 20 Mbit/s | 1,786 sent, 1,786 counted, delivered 20.01, loss 0 |
| UDP offered 30 Mbit/s | sent by the laptop (third trigger accepted), the device line missing (below) |
| Round trip at rest, TCP (trigger connections) | 7, 8, 8 ms |
| Round trip at rest, ICMP (laptop to device) | 8.2 / 22.9 / 51.5 ms min/avg/max |
| Round trip in-chunk, ICMP (during receive chunk 3) | 12.9 / 56.3 / 97.6 ms |
| Round trip in-chunk, TCP samples per receive chunk (50 ms apart) | 9→132, 9→139, 8→95, 6→85, 8→65 ms |
| Effective send window (the device's advertised window as the sender sees it) | 64 KB at each chunk's start, 130–280 KB median, up to 497 KB |
| Congestion window, median | 200–256 KB; segment size 1448 |

**What voided the verdict, from the record.** The data phase ended by the
driver, `reason=native-diag`, 19.7 s after it began and before the host
had sent its disconnect, so the disconnect was never attempted
(`core_disconnect attempted=false`) and the receipt could not pass; the
owned device command was terminated with the data window, which is why
the third UDP line is missing and the leaf's verdict read failed. What
closed the data phase is a ceiling from the diagnostic era that still
sits in the lifecycle tree: with `CONFIG_MT6797_CCMP_60S_WINDOW` and
`CONFIG_MT6797_CCMP_CONNECTED_LIFETIME` the native-delivery diagnostic
ends its sample window when the CCMP path has queued
`MT6797_CCMP_DIAG_CHECKED_MAX` (8,192) frames (`mac.c`: `ccmp_queued >=
MT6797_CCMP_DIAG_CHECKED_MAX` sets `native_diag_sample_done`; the retire
budget of 750 ms then closes it and ends the data phase). Every boot of
the series finished its TCP chunks at 4,505–4,646 queued frames; this
boot's probe added 2,679 datagrams and the counter read exactly 8,192 at
the end (`ccmp-stable end: queued=8192`). The -5 at branch 8 that followed
is the teardown meeting a frame the closed window no longer admitted
(`native HIF refused: gate=header-length`, `teardown framing drop`), not a
fault of the data phase. Neither of the two harness fields the owner named
was in the verdict: the probe's exit status never reached it (`|| true`
already ended the block), and `known_size_complete` is recorded only, by
design unreachable for a one-second transmit chunk at a 1 MiB cap. Both
are fixed regardless: the block now ends with its own `TP3_RC=` line and
`true`, recorded as `probe_rc`, so it can decide nothing but itself; the
cap field is relabelled `byte_cap_reached` and a duration-relative floor
(`rate_floor_met`: at least 0.8 of the best chunk of that direction) is
recorded beside it, neither in the verdict. A rate the laptop offered with
no device line is recorded `offered: true, missing: true`, never as loss.
The ceiling itself is lifted for the measurement lifetime in the next
build (a proposal: the diagnostic's queued-frame ceiling becomes the
connected lifetime's, 32,768, under the lifecycle options), because at
15 Mbit/s a five-chunk receive alone approaches it.

**The receive question, answered.** UDP delivered 20 Mbit/s into the
device with zero loss and no return traffic, so the receive path is not
the ceiling and the interrupt is not the next step (table rows 1 and 3
resolved against row 3; row 4, the access point's legacy downlink rate,
is above 20 Mbit/s at least, so it is not the cap at the measured TCP
rates). TCP receive at 14.5–15.8 device-side while UDP carries 20 points
at the acknowledgement path, which is our transmit side: the 6 Mbit/s
fixed rate, the 4–9 ms per-frame completion, and a round trip of 7–8 ms
idle that rises to 40–130 ms under load as the queue builds. The next
lever is the one predeclared as boot B: stop requesting the MCU status
report on ordinary data descriptors and complete those frames on page
credits as the vendor does, the only change on the table that can move
the round trip, which is what the TCP number has been tracking.

**Re-baseline, and the comparison rule from now on.** The same image
produced TX 3.7–4.1 and RX 14.5–15.8 device-side in this session against
TX 3.2–3.4 and RX 8.5–12.5 at 02:00 (aggregates 3.14 against 2.67–2.69,
7.78 against 6.78–6.99). Session-to-session variance is about ±40 %, not
the ±5–7 % the records have assumed. From here: a driver change is judged
against the adjacent boot in the same session, or A/B inside one boot;
every "inside the band" in the records names the session it means or is
reworded as a within-session comparison; the noise floor in the
throughput series is corrected to this measured spread, with this pair as
the evidence. The console verdict reached the owner on the framebuffer in
seconds without SSH; once the status line and the cap field are out of
its way it is the trusted verdict at the device.

## 12. Boot B (predeclared, 2026-10-25): retire ordinary data on page credits

**The change.** 0272 (retired, in the history),
behind `CONFIG_MT6797_DATA_CREDIT_COMPLETION`: an ordinary data descriptor
goes out without a PID and without the MCU transmit-status report (bytes
20 and 21 of the descriptor stay zero), and the frame is retired at
submission; mac80211 is told it was transmitted without an acknowledgment
report (`IEEE80211_TX_STAT_NOACK_TRANSMITTED`, which its loss accounting
does not count); the TX-done event and the in-flight slot are not used for
it; the page credits of the TC1 pool stay the flow control, as they were.
Management and security frames keep their PID, their report and the
TX-done event. The data-end record counts the frames retired this way
(`credit_retired=`). The vendor sets the PID and the report together only
for frames with a completion handler (`nicTxFillDesc`) and retires plain
data on the page release counts; this is what the driver now does.

Three more things ride in the same build, none of them a data-path change:
0269 (reverted, in the history)
lifts the diagnostic's queued-frame ceiling to the admitted ceiling
(32,768), so the data window no longer closes under a probe beside the
chunks; [0270](../../patches/proposals/0270-wifi-mt6797-count-the-data-frames-delivered-to-mac80211-at-the-data-end.patch)
prints `rx_delivered=` (frames handed to mac80211) in place of the three
dead counters; [0271](../../patches/proposals/0271-wifi-mt6797-record-the-received-rate-word-logging-only.patch),
behind `CONFIG_MT6797_RX_RATE_RECORD`, counts the receive vector's
mode/rate of each queued data frame and prints the distinct values at the
data end (`RX rates: mode/rate=count …`): the rate the access point sends
toward this station. The lifecycle and rate fragments set both options.
Host fixture
[`tests/data-descriptor-test.c`](tests/data-descriptor-test.c)
(`tests/run-data-descriptor-test.py <kernel tree>`; it followed the
proposals that remained after boot B): the descriptor's rate bytes at the
default and at a profile's value, and the vector word after groups 4, 1
and 2, alone, absent, truncated. The descriptor-report variant's checks
went with 0272. Compiled with both options on and off;
strict checkpatch clean on all four.

**Comparison rule.** Within the session: boot B is read against the
adjacent boot of the current image in the same session, probe boot 4
(11:39 UTC: TX chunks 3.73–4.07, RX device-side 14.46–15.83, in-chunk TCP
round trip rising 9→139 ms, round trip at rest 7–8 ms). If the owner's
hands allow, a baseline boot of the current image immediately before B
replaces that reference; otherwise B is read against probe boot 4 and the
record says so.

**TX first, then the rest.** `debt=0` at the stop, no guard record, the
data phase ending by `disconnect`, `credit_retired` equal to the data
frames queued, `tx_done` counting them (retired at submission: that field
now means retired, and the per-frame `TX done` records exist only for
management and security frames). Then the reading:

| Reading (against probe boot 4, same session) | Cause | Next |
|---|---|---|
| TX per chunk up, in-chunk round trip down, UDP and TCP receive up without any receive-side change | the per-frame MCU report was the completion latency, and the acknowledgment clock is confirmed in the same boot | the fixed-rate sweep (boot C) on the faster completion path |
| TX up, round trip down, receive unchanged | the completion latency was transmit-only; the receive number has another clock | the sweep still; the receive clock is read from the RX rates line (the access point's rate) |
| TX and round trip unchanged | data frames are not retired on credits the way the vendor's are (the firmware still waits on something per frame, or the air transmission is the slow part) | one second attempt on this lever (the fixed-rate bit, then the rate code); then the record |
| the join fails, the debt is not zero, or `credit_retired` is below the frames queued | the retirement at submission is wrong in a way the fixture did not reach | revert the admission, keep the proposal, study from source |

Two attempts at this lever, then the record, as the owner set it.

**The three questions.** Reachability: the descriptor bytes are written by
`mt6797_join_tx_data_descriptor_report` (join-tx.h), reached from
`mt6797_hif_send_data_report` (hif.c) through
`mt6797_join_prepare_data_report` (join-submit.h); the PID rule is inverted
for the unreported form (PID 0 required) and the fixture covers both forms,
so nothing earlier refuses it; the frame reaches the bus by the same
transfer as before; the page accounting (`tc1_free`, `join_data_page_debt`)
is unchanged; the skb reaches mac80211 through the existing completed-data
queue outside the driver locks. Ownership: no new register is read or
written; the TX-done event path keeps its PIDs for reported frames; the
receive-vector word is read from the packet copy, non-destructively, and
the diagnostic ceiling is a constant. The third question: the vendor writes
PID and `TXS_TO_MCU` only for a frame with a completion handler and writes
neither for plain data; that absence is the fifth entry of the ledger
(WHCR never written beyond init, WHISR never copied, state 2 never sent
through a refused encoder, the MCU report never requested for plain data,
and now relied upon).

**What a void boot produces now.** The preflight reads the rendered run
before the install; the probe rides along (opt-in) and the lifted ceiling
keeps the data window open under it; a silent or refused run ends at the
watcher's 300 s wall clock at the latest and the reviewed preservation and
return follow at once.

### Boot B result (2026-10-25, 12:08 UTC): a regression; 0272 retired, 0269 reverted

Build `d8aa0d5f`, boot2 `276a6628…` over `cacce7a1…`, mainline boot
`b7a486c7…`, returned to Gemian `3b6d4978…` by the harness's own path
(session exit 1 after a clean receipt: `all_pass true`, disconnect
accepted, data phase 27.9 s ending by `disconnect`), complete sealed log
(173,080 bytes), preflight 25/25. The comparison is the same-session
adjacent pair, boot B against probe boot 4 (11:39), and is valid.

| | probe boot 4 (same image as the series) | boot B (0272 + 0269 admitted) |
|---|---|---|
| TX per chunk, host received | 3.73–4.07 Mbit/s (aggregate 3.14) | 3.13–3.76 (aggregate 3.07) |
| RX device-side per chunk | 14.46–15.83, every chunk at its byte cap | 11.34, 7.64, 1.46, 0.95, 1.19; four chunks ended by the device timeout |
| In-chunk TCP round trip | 6→139 ms | 8→438 ms |
| Round trip at rest (laptop ping / trigger TCP) | 8–51 ms / 7–8 ms | 67–177 ms / 33, 13, 6 ms |
| UDP delivered, loss | 10 and 20 Mbit/s, zero loss | 10: 608/893 (32 % lost); 20: 2,001/1,786 (late datagrams of the previous burst counted); 30: 2,434/2,679 (9 %) |
| data-end counters | — | `rx_delivered=8581 tx_queued=3000 tx_done=3000 tx_failed=0 tx_credits=22489 credit_retired=3000` |

No gain on the direction the lever targeted and a collapse on the one the
series cares about: the receive collapse appeared only with ordinary data
retired at submission. 0272 is retired with this boot as its
counter-evidence (out of the series and the fragments; the proposal is in
the history). 0269 is reverted as well: a queued-frame ceiling is runtime
behaviour, not logging, and it landed in the same boot, so this boot
cannot say which of the two starved receive. What probe boot 4 needed is
done differently by
[0274](../../patches/proposals/0274-wifi-mt6797-the-diagnostic-s-ceilings-stop-its-counts-not-the-window.patch):
the diagnostic's ceiling stays 8,192 and stops its own count (frames beyond
it are delivered and counted apart, `beyond=` on the ccmp-stable end line);
it never closes the data window or refuses delivery again.

**The safety reading.** `tx_failed=0`; the laptop's receive leg saw no
non-zero byte in any transmitted chunk (the helper's zero-payload check,
which raises on the first non-zero byte, passed on all five); `rx_delivered`
8,581 frames handed to mac80211. Retiring a buffer at submission while the
firmware may still own it is the change class that corrupts silently; that
check passing is the only evidence this boot holds that it did not, and the
regression is otherwise unattributed between the two admitted changes.

**The credit model, corrected before any second attempt.** The vendor does
not retire plain data at submission: it releases transmit resources on
the credit events the firmware reports (`nicTxReleaseResource` from the
block's counts, nic.c synthesising the done bit from non-zero counts),
which is what our `tx_credits` counter measures. 0272 retired the frame
when the bus write returned and used the credits only as flow control, so
nothing bounded the frames the firmware held for the air: the 1-page
acknowledgements of a receive went out as fast as credits came back
(0.8 ms), the firmware's queue grew, the in-chunk round trip reached 438
ms against the descriptor's 500 ms lifetime, and the receive collapsed. A
second attempt, if the lever gets one, is a descriptor with no PID and no
status report retired on credit arrival, never at submission, with an
instrument that survives retirement (the probe's in-chunk round trip, or a
timestamp taken before the retirement). The `tx_credits=22489` against
`credit_retired=3000` is pages against frames, from the code:
`join_data_credits` accumulates `tc1_released` pages and `credit_retired`
counted frames; 22,489 pages over 3,000 frames is 7.5 pages a frame, as
probe boot 4's 24,939 pages over 4,011 frames (6.2) with its different
mix of 12-page data frames and 1-page acknowledgements. Not a divergence.

**What stands from this boot.** The received-rate record read the access
point's downlink: `RX rates: mode/rate=count
1/9=90,1/11=297,1/13=438,1/8=706,1/12=6249,1/14=126,1/10=187,1/15=448`,
OFDM throughout, with index 12 (54 Mbit/s) on 6,249 of 8,541 frames and 48
Mbit/s on 706; the access point sends to this station mostly at 54. The
probe table's fourth row (a legacy downlink rate as the cap) is closed.
The second attempt at this lever is not spent now: under the broken
accounting TX still did not move, so the lever's expected gain is less
supported than when it was queued. The fixed-rate sweep goes ahead of it.


## 13. Boot C (predeclared, 2026-10-25): the fixed-rate sweep, 6 → 54 Mbit/s

**The change.** [0273](../../patches/proposals/0273-wifi-mt6797-make-the-data-descriptor-s-fixed-rate-code-a-build-option.patch)
puts the ordinary data descriptor's fixed rate code behind
`CONFIG_MT6797_DATA_FIXED_RATE_CODE` (default 0x4b, OFDM 6 Mbit/s, the
series' value); the lifecycle fragment sets 0x4c, OFDM 54 Mbit/s, the
largest remaining multiple and the rate the access point already uses
toward us. Management and security descriptors keep 6 Mbit/s. The first
data frame's record prints the code (`rate=0x4c`). Fallback if 54 fails:
0x49, 24 Mbit/s. The tree is otherwise the current admitted one (probe
boot 4's) with the two logging records (0270, 0271) and the ceiling fix
(0274); 0272 and 0269 are out. Host fixture
[`tests/data-descriptor-test.c`](tests/data-descriptor-test.c) checks the
descriptor's rate bytes at the default and at 0x4c and the vector word
helper; compiled at both values with the rate record on and off; checkpatch
clean.

**Comparison.** Same-session adjacent pair: boot C against the last boot of
the current admitted tree in its session; if more than the session has
passed since probe boot 4, the record says so and the comparison is
stated as cross-session with the ±40 % floor. The probe rides (in-chunk
round trip and the UDP legs are known good).

**TX first.** `debt=0`, no guard record, the data phase ending by
`disconnect`, `tx_failed` read before any rate claim: a fixed rate the
access point does not receive shows as unacknowledged frames (`TX done
status=3`, `txfail` ending the data phase) and sends the next boot to 24.

| Reading | Cause | Next |
|---|---|---|
| TX per chunk up by a multiple, in-chunk round trip down, receive up with no receive-side change | the per-frame cost was the air time at 6 Mbit/s and the receive number tracks the acknowledgement path, confirmed with no new mechanism | the state-2 attempt (boot D) on the faster tree; then the completion lever's corrected second attempt if still wanted |
| TX up, receive unchanged | the transmit per-frame cost fell but the receive clock is elsewhere | read the RX rates and the in-chunk round trip; the credit model's second attempt |
| TX unchanged at 54 (frames acknowledged) | the per-frame cost is not the air time: the firmware's fixed-rate path or the MCU report costs the 4–9 ms regardless of rate | the credit model's second attempt (retire on credit arrival) is the lever |
| frames unacknowledged, `txfail` | 54 is not received by the access point from this station at this power | the 24 Mbit/s fallback (0x49), same reading |

**The three questions.** Reachability: the rate bytes 26 and 27 are written
by `mt6797_join_tx_data_descriptor` (join-tx.h) from the option, reached by
the unchanged submission path; nothing earlier reads or refuses them (the
fixture checks both values). Ownership: no register; the firmware reads the
descriptor. What the vendor writes: for plain data the vendor writes no
fixed rate at all (its rate control runs from the station record's rate
table, which ours leaves empty, the branch-3 finding); the fixed-rate bit
with a code is the series' own path since the first data frame, now at a
different code. The ledger stands at five.

**Verification of 0274 on this boot.** With the probe's datagrams the
queued count would again cross 8,192: the ccmp-stable end line must show
the count saturated and `beyond>0` with the data phase ending by
`disconnect`, not `native-diag`.

### Boot C result (2026-10-25, 13:14 UTC): 54 Mbit/s acknowledged, transmit ×1.9, the log cut at the cap

Build `9ea1a37c`, boot2 `8cd36314…` over `276a6628…`, mainline boot
`61cda9bd…`, returned to Gemian `52ffff40…` by the session's own return
(changed-ID Gemian, recovery confirmed, two attempts, 15 s; the watcher's
unbundled recovery was not needed, the USB endpoint was down when the run
ended). Session classification `returned-with-incomplete-log`: the device
logger sealed at 2,097,147 bytes (`reason=byte-cap`, 27.5 s after its
start, 12,310 records, of them 5,134 `join TX done` and 5,129 `TX
completion timing` lines), so no data-end, RX-rates or ccmp-stable end
line exists and the receipt's `all_pass` is false on the log alone. The
measurement itself completed both directions.

**TX first.** The first data frame went out at `rate=0x4c`; 5,127
completions with status 0 and 5 with status 3 (`count=3`, scattered pids
34, 58, 73, 98, 116): 54 Mbit/s is received by the access point from this
station at this power. No guard record, no fault, no credit overflow, DMA
attached both ways. The 24 Mbit/s fallback is not needed.

| Direction | Boot C (13:14 UTC) | Probe boot 4 (11:39 UTC) | Boot B (12:08 UTC) |
|---|---|---|---|
| TX, host-received aggregate / chunks (Mbit/s) | 5.53 / 7.84, 6.64, 7.52, 7.70, 7.19 | 3.14 / 4.07, 3.74, 3.73, 3.87, 3.95 | 3.07 / 3.13–3.76 |
| RX, host-sent aggregate / device-side chunks (Mbit/s) | 7.19 / 17.48, 17.48, 18.24, 16.45, 17.12 (all `byte_cap`) | 7.78 / 14.46, 14.98, 15.25, 15.25, 15.83 | 3.50 / 11.3, 7.6, 1.5, 0.95, 1.2 |
| device idle TX / RX | 83.0 % / 76.5 % | 86.2 % / 78.3 % | 89.1 % / 88.5 % |
| in-chunk round trip (laptop ping, ms min/avg/max) | 9.2 / 34.8 / 50.9 | 12.9 / 56.3 / 97.6 | 70.3 / 103.7 / 150.8 |
| TCP receive `rttcur` max per chunk (ms) | 88, 70, 51, 60, 79 | 132, 139, 95, 85, 65 | 167–438 |
| UDP 10 / 20 / 30 Mbit/s | 893/893, zero loss / device line absent / absent | zero loss / zero loss / absent | 608/893, 2001/1786, 2434/2679 |

Boot C ran 66 minutes after boot B with the owner away between, so the
comparison is stated as cross-session with the ±40 % floor. TX per chunk
is ×1.9 the probe-4 chunks (6.64–7.84 against 3.73–4.07), beyond the
floor: real. Receive on the device side is +13 % (16.45–18.24 against
14.46–15.83), inside the floor: unchanged. The in-chunk round trip fell
by a third and the receive-direction `rttcur` samples fell with it, the
same direction as the transmit gain. The at-rest ping read 43/98/153 ms
(probe 4: 8/23/52; boot B: 67/122/177): the at-rest sample is not stable
across boots and is recorded, not read.

**Reading: the second row of §13.** TX up, receive unchanged. The
arithmetic: a 1,448-byte frame's air time fell from about 2.0 ms at
6 Mbit/s to about 0.3 ms at 54, and the per-frame cost (depth 4,
host-received rate) fell from about 3.0 ms to about 1.6 ms. Roughly 1.4 ms
of the per-frame cost was air time; about 1.6 ms per frame remains and
does not depend on the rate: at depth 4 that is a submit-to-completion of
about 6 ms per frame with the air time removed from it, the owner's
"4–9 ms" question in its remaining form (the MCU status report and its
collection, not the air). Receive did not follow the transmit gain beyond
the floor, so the receive number is not simply the acknowledgement path's
air time either; the RX-rates line that would say what the access point
sent is lost with the log. The next lever on transmit is the completion
path (the corrected second attempt: retire on credit arrival, with its
instrument); boot D (state 2) is independent and already approved.

**Two faults, named.** (1) *The log cap.* Two per-frame kernel records of
about 200 bytes each cost 2 MiB in 5,100 completions; at the 54 Mbit/s
rate the five-chunk measurement writes that many frames in the transmit
phase alone. The plan's own precedent (lifecycle-9) keeps the sealed
logger's 2 MiB contract and measures fewer chunks; boot D measures two
chunks per direction (the leaf's five-chunk loop text stays for the idle
validator and is narrowed after it, exactly as the lifecycle helper does;
the preflight takes the declared count). (2) *The probe's missing legs.*
The owned command ended during the 20 Mbit/s leg (`probe_rc` absent, the
disconnect never attempted) as it ended during probe 4's 30 Mbit/s leg.
With the log cut there is no data-end line to name the reason; the
queued-frame arithmetic (about 1,600 acknowledgements received in the
transmit phase, 3,620 data frames in the receive phase, 893 datagrams of
the first leg, then the second leg's 1,786) crosses 8,192 inside that leg,
and the review below shows 0274 as booted could not have kept the window
open there. Recorded as the probable cause, not verified by the log.

**Verification of 0274 on this boot: not possible, and by reading not
needed.** The review of the admitted tree (owner away, 2026-10-25) found
that 0274 removed one of three stops at the queued-frame ceiling: the
pre-read control step still asked the connected lifetime's budget step
(`mt6797_ccmp_diag_budget_step`), which stops at the same saturated count
(and at the total-frame and byte ceilings), closing the window through the
diagnostic's transition; and the per-frame admission asked it too, so
every frame beyond the ceiling was refused as `window_blocked` and the
`beyond=` count could never move. 0274 is amended in place
([0274 v2](../../patches/proposals/0274-wifi-mt6797-the-diagnostic-s-ceilings-stop-its-counts-not-the-window.patch)):
under the connected lifetime the budget step stops only on a missing
budget, the pre-read sample ceilings are the 60-second window's alone, the
count saturates and the frames beyond are delivered and counted apart.
A host fixture ([`tests/ccmp-budget-step-test.c`](tests/ccmp-budget-step-test.c),
run by `run-native-diag-test.py` with and without the connected lifetime)
pins both forms. Verification moves to boot D: if the queued count crosses
8,192 under two chunks and the probe, the ccmp-stable end line shows
`beyond>0` with the data phase ending by `disconnect`; if it does not
cross, the fixture is the evidence and the boot records "not exercised".

**Also from the review.** The rate series could not be applied past 0268:
0262 (the TX-done rate record) moved the Kconfig context 0268 expects, and
0273 rewrites the descriptor lines 0263 deleted; the repository checker
orders series but does not apply them. Both are retired and re-expressed
on the current tree as [0275](../../patches/proposals/0275-wifi-mt6797-record-the-data-phase-s-firmware-rate-words-as-a-histogram.patch)
(the same record, rebased) and [0276](../../patches/proposals/0276-wifi-mt6797-rate-code-0-sends-ordinary-data-without-a-fixed-rate.patch)
(rate code 0 is "no fixed rate at all", the vendor data form, one value of
0273's option); the state-2 record is [0277](../../patches/proposals/0277-wifi-mt6797-update-the-station-record-at-state-2-after-authentication.patch).
Both series were applied in order in the VM and the rate series' tree is
identical to the boot D branch. [0271](../../patches/proposals/0271-wifi-mt6797-record-the-received-rate-word-logging-only.patch)
is amended in place for its line buffer (96 bytes held eight entries only
at small counts). The descriptor fixture now covers rate code 0.

## 14. Boot D (predeclared, 2026-10-25): the state-2 station record, one boot

The rate thread's single informed attempt, approved by the owner after
the probe and the sweep; predeclared in the
[autorate record](TX_AUTORATE_RESULT.md#state-2-station-record-boot-second-attempt-predeclared-2026-10-25-the-encoder-admits-state-2)
where that thread lives. The tree is the rate series (the lifecycle tree
through 0274 v2, then 0275, 0276, 0277) on the rate profile (data without
a fixed rate, the received and transmitted rate records). Two chunks per
direction; the probe rides. The AP-loss gate stays independent.

### Boot D result (2026-10-25, 15:06 UTC): the state-2 record is accepted, the firmware selects 6 Mbit/s; the rate thread closes

Recorded in the [autorate record](TX_AUTORATE_RESULT.md#state-2-station-record-boot-second-attempt-result-2026-10-25-1506-utc--the-table-is-valid-the-selection-stays-at-6-mbits-the-rate-thread-closes).
For the transport thread: TX per chunk at the firmware's choice is the
fixed-6 baseline (3.8–4.0 Mbit/s), 45 % below the fixed 54 of boot C, so
0273 at 0x4c stays the data path; the two-chunk run kept the log complete
(972 KB) with all three probe legs and the disconnect; the queued count
(7,446) did not reach the 0274 ceiling. The transmit lever that remains
is the completion path: the corrected second attempt (retire on credit
arrival with its instrument) is drafted and compiled on a VM branch,
not admitted, pending the owner. The AP-loss gate follows.

## 15. Boot E (predeclared, 2026-10-25): the corrected credit model, read on both directions

**The position, now unambiguous.** About 1.5 ms of per-frame cost against
the vendor's about 0.26 ms. TX 7.4 Mbit/s at 54 where the air is 0.3 ms a
frame: the per-frame cost is the entire transmit limit. RX 15.8 Mbit/s
through TCP with one acknowledgement per 1.47 ms, the same number, while
the UDP legs prove the path carries 29 Mbit/s at 2 % loss (boot D). The
per-frame figures are derived (rate ÷ depth); the probe's `rttcur`
samples and the UDP counts are measured. One quantity limits both
directions; this boot is its first direct attack.

**The change.** [0278](../../patches/proposals/0278-wifi-mt6797-retire-ordinary-data-frames-on-credit-arrival.patch)
(`CONFIG_MT6797_DATA_CREDIT_RETIRE`): an ordinary data descriptor with no
PID and no MCU status report, retired when the TC1 page credits returned
since the frames submitted before it cover its own pages, in submission
order, never at submission; the depth-4 slot stays the in-flight bound
and the 750 ms slot deadline the backstop (an expired frame frees its host
PID and counts as failed); pages left over with no frame in flight are
dropped so a frame is never retired by credits that preceded it. The
instrument survives retirement: a submission timestamp read at the credit
event (four early `join data credit retire:` lines, then one line at the
data end: retired, expired, PID-pool faults, mean and maximum wait,
unmatched pages, deepest in-flight count), beside the probe's in-chunk
round trip. With it, [0275 v2](../../patches/proposals/0275-wifi-mt6797-record-the-data-phase-s-firmware-rate-words-as-a-histogram.patch)
(the firmware rate words as a per-phase histogram) and
[0279](../../patches/proposals/0279-wifi-mt6797-count-ordinary-data-completions-print-per-frame-lines-only-on-request.patch)
(ordinary data completions counted into a status/rate histogram and a
submit-to-completion latency histogram; per-frame lines only behind
`CONFIG_MT6797_TX_PER_FRAME_RECORD`, off), so five chunks fit the sealed
logger's cap at the 54 Mbit/s rate. The tree is the baseline (boot C's,
0273 at 0x4c) with those three; 0277 is not in it. Host fixtures:
[`tests/credit-retire-test.c`](tests/credit-retire-test.c) (the descriptor
without a report; slots retired in order as credits cover them, a
reported frame never by credits) and the descriptor fixture; compiled with
the options on and off; strict checkpatch clean apart from the series'
absent sign-off.

**Harness.** Five chunks per direction with aggregate logging; the probe
rides (in-chunk ping now keyed to the last chunk, its absence recorded);
the classifier takes the declared count. Comparison: boot C (same tree
without 0278) per chunk, cross-session with the ±40 % floor; the headline
is both directions in the same boot, TX chunks and RX device-side chunks,
with the UDP legs as the free ceiling probe.

**TX first.** `tx_failed`, `retire_expired` and `pid_faults` read before
any throughput claim; `debt=0`; the data phase ending by `disconnect`; the
laptop's zero-payload check on every transmitted chunk (a buffer retired
while the firmware still owns it is the change class that corrupts
silently); any RX chunk ended by `device_timeout` or any non-zero payload
reverts 0278 immediately, as boot B established.

| Reading | Cause | Next |
|---|---|---|
| per-frame cost down: TX and RX both up, the same-boot ratio of TX chunks and RX device chunks against boot C quoted | the MCU status report and its collection were the completion path's cost | the credit model is admitted; the next lever is fewer bus transactions per frame |
| cost flat: TX and RX at boot C's numbers, retire waits at the old completion latency | the credits are not the completion path; the firmware's own per-frame processing is the next reading | revert 0278 to a proposal; read the retire-wait histogram and the firmware's per-frame path (RE VM) |
| `retire_expired` > 0 with frames stalling to the slot deadline | the firmware's returned page count per frame is below the charged pages (the FIFO never covers the head) | revert; the page unit is the finding, read from the credit lines |
| any `device_timeout` receive chunk or a non-zero payload byte | the in-flight bound or the buffer ownership is wrong | revert immediately (boot B's rule) |

**The three questions.** Reachability: the descriptor bytes 20–21 and the
report flag through `mt6797_hif_send_data_report`; the retire path from
the pass guard's TC1 release accounting, which runs every pass; the drain
at the worker's status reporting. Ownership: the frame buffer is the
host's until retirement; the firmware owns the pages until it returns them
(the credit event), which is exactly when the frame is retired. What the
vendor writes: no PID and no report for plain data, resources released on
the page counts (`nicTxReleaseResource`), the frame freed after the bus
write (the host keeps no slot); ours keeps the slot until the credits
arrive, the stricter form. The ledger stands at eight.

**0274 v2 on this boot.** Five chunks and three probe legs cross 8,192
queued frames: the ccmp-stable end line must show `beyond>0` with the
data phase ending by `disconnect`; otherwise "not exercised".
