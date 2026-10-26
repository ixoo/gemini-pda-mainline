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
| `retire_expired` > 0 with frames stalling to the slot deadline | a frame the credits never cover (this branch did not occur; the charge and release units are the same 128-byte page on both sides, reconciled in the result) | revert; read the credit lines |
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

### Boot E result (2026-10-25, 15:38 UTC): the credit model is the completion path for transmit; receive did not follow

Build `c6fa0edc` (lifecycle profile: 0273 at 0x4c, 0275 v2, 0276, 0278
credit retire, 0279 per-frame lines off), boot2 `528d1d1d…` over
`df7d6e65…`, mainline boot `21c301dc…`, returned to Gemian `239967b1…`
(changed-ID Gemian, recovery confirmed, 15 s); session
`ram-service-regression-pass`, log complete through the seal (172,693
bytes, 2,126 records, five chunks per direction: the aggregate records
hold five chunks at 54 Mbit/s with a tenth of the cap used), receipt
`all_pass`, disconnect accepted, data phase 22.8 s ending by
`disconnect`; the classifier read the declared count (`chunks_declared=5`,
`measurement_censored=false`). Its `throughput_baseline_pass` is false
on this boot as on every boot of this series since probe boot 4 (its
`gtk_counters_consistent` gate, from the connected-lifetime trial's
classifier, has been false since boot B); the series grades on the
receipt and the sealed log, never on that gate, and the gate is noted
here as classifier debt, not a device finding.

**TX first, and the revert rule.** `tx_failed=0`; the credit model's own
line: `retired=5637 expired=0 pid_faults=0 wait_avg_us=3477
wait_max_us=14337 left_pages=0 inflight_max=4`; no expired slot, no
PID-pool fault, no unmatched page; `debt=0`, no guard record, 21 credit
lines, no overflow. Every receive chunk ended at its byte cap (no
`device_timeout`) and the laptop's zero-payload check passed on all five
transmitted chunks (the helper raises on the first non-zero byte and the
receipt is `all_pass`). The revert rule was not triggered. The first data
frame: `rate=0x4c report=0`; no TX done line and no per-frame completion
line for ordinary data (0279); the five completions in the log are
management and security frames.

| Direction | Boot E (15:38 UTC, credit retire) | Boot C (13:14 UTC, same tree without 0278) |
|---|---|---|
| TX chunks (Mbit/s) / ended by | **floor** 9.23, 9.18, 9.46, 9.20, 9.25 / all `byte_cap` at 0.89–0.91 s (1 MiB; a rate over a window holding slow start, not a measured steady rate) | 6.64–7.84 / `duration` |
| TX aggregate, host received | 7.74 | 5.53 |
| RX device-side chunks (Mbit/s) | **floor** 18.64, 19.97, 17.85, 17.85, 18.64 (all `byte_cap` in 0.42–0.47 s) | **floor** 16.45–18.24 (`byte_cap` in 0.46–0.51 s) |
| RX aggregate, host sent | 13.53 | 7.19 |
| device idle TX / RX | 89.1 % / 86.4 % | 83.0 % / 76.5 % |
| UDP 10 / 20 / 30 Mbit/s | 893/893, 1786/1786, 2679/2679: zero loss on all three | zero loss / cut / cut |
| in-chunk ping (ms min/avg/max), keyed to the last chunk | 4.9 / 28.7 / 41.4 | 9.2 / 34.8 / 50.9 |
| TCP receive `rttcur` max per chunk (ms) | 76, 83, 62, 80, 57 | 88, 70, 51, 60, 79 |
| at-rest ping (ms) | 254 / 309 / 364 | 43 / 98 / 153 |
| ccmp-stable end | `queued=8192 beyond=3304` | lost with the log |

**Reading.** Transmit: the per-frame cost is down and the credits are the
completion path. The measured evidence is the instrument: 5,637 frames
retired on credit arrival with a mean wait of 3.48 ms and a maximum of
14.3 ms at four in flight, against the ~6 ms submit-to-completion derived
for the status-report path; and every transmit chunk reached its 1 MiB cap
in 0.9 s where boot C's ran their full second. The throughput number
itself is censored by the harness: the 1 MiB-per-chunk cap, set for the
6 Mbit/s era, now binds at 9.2–9.5 Mbit/s, so boot E's TX figure is a
floor, inside the ±40 % cross-session floor against boot C only because
the cap cut it (derived from the retire wait at depth 4, the path can
carry about 13 Mbit/s before the next limit). Receive: 17.9–20.0 against
16.5–18.2, inside the floor; the acknowledgement frames took the same
cheaper path and the receive number did not follow. So the first row's
condition holds on transmit and not on receive: the transmit completion
path was the transmit limit, and the receive limit is not the transmit
completion path. What the receive data say: UDP carries 30 Mbit/s with
zero loss on all three legs (2,679 datagrams a second received and
delivered: about 0.37 ms a frame on the receive path), so the receive
path is not the limit either; TCP receive at 18.6 Mbit/s runs with an
in-chunk round trip of 29 ms mean and `rttcur` up to 83 ms over a window
of 64–380 KB, which is the sender pacing on a long round trip, not a
device ceiling on frames. Where the 29 ms sits (the device's receive
buffering and acknowledgement timing, or the air) is the next receive
question; it is not the HIF per-frame cost.

**Page accounting, reconciled (owner, 2026-10-25).** `tx_credits=49276`
against `retired=5637` is not a per-frame page figure: the data phase
carried about 3,620 data frames at 13 pages each (28-byte descriptor plus
a 1,514-byte Ethernet frame, 128-byte pages) and about 1,810
acknowledgement frames at 1 page, 48,870 pages against the 49,276
observed, a 0.8 % match. Both sides count the same unit: the vendor's
`NIC_TX_PAGE_SIZE` is 128 and ours is `(28 + len + 127) / 128`
(0123, 0278). The charge and the return are identical units; no unit
question remains, and no length sweep is queued (it would re-measure what
the source says).

**The vendor's resource contract, sourced (gen3 `nic_tx.c`).**
`nicTxAcquireResource` charges the frame's page count against the
queue's free-page count without blocking (busy when short);
`nicTxPollingResource` reads the released counts (WTSR) and sleeps the
polling delay between reads when the pool is empty;
`nicTxReleaseResource` adds the released counts to the free-page pool
and derives a free-buffer count as pages divided by the maximum pages
per frame (`NIC_TX_MAX_PAGE_PER_FRAME`, whose size constant the header
marks "for development only"); the derived count is nonetheless read by
the queue manager's quota adjustment (`qmAdjustTcQuotasMthread`,
`que_mgt.c`) to spread the per-queue budgets, though admission itself is
the page count. The polling delay is 50 ms
(`NIC_TX_RESOURCE_POLLING_DELAY_MSEC`), with 256 polls the timeout, not
5 ms. There is no per-frame FIFO on the vendor side: plain data is freed
after the bus write and the pool is the whole contract. Our FIFO (the frame kept
until the credits that cover it arrive, in submission order) is the
stricter form of the same contract. The two questions that remain for
firmware reverse engineering are the trigger of the released count (DMA
completion, acknowledgement, or retry exhaustion) and over-return under
aggregation; both matter only once depth 12 and, later, A-MPDU exist.

**Dispositions.** 0278 is admitted (it is the lifecycle tree's data path
from this boot). 0274 v2 is verified on hardware: the queued count
saturated at 8,192 with 3,304 frames beyond it delivered and counted, the
window open to the host's disconnect. 0279 and 0275 v2 did their job: a
five-chunk boot at the fixed 54 rate sealed at 173 KB. The in-chunk ping
keyed to the last chunk reported. The at-rest ping keeps rising boot over
boot (23, 98, 122, 222, 309 ms avg): recorded, the power-save answer stands.

**Harness, before the next transmit measurement.** `byte_cap_per_chunk`
(1 MiB, "1 s or 1 MiB per chunk") is part of the reviewed finite protocol
and now censors transmit; the next measurement needs the cap raised (4 MiB
per 1 s chunk keeps the duration the bound up to 33 Mbit/s) with the plan,
the installer review's protocol record and the leaf's `MAX_BYTES` changed
together, the owner's call. Until then boot E's transmit number is a floor.

**Next.** Transmit: fewer bus transactions per frame (the next lever named
in §15's table). Receive: the 29 ms round trip under load, read from the
device side. The AP-loss gate stays independent and needs no new
mechanism; it runs over the boot-E image.

## 16. Boots F and G (predeclared, 2026-10-25): the depth, one variable each

**The position.** With ordinary data retired on credit arrival, the
in-flight depth is the only bound on the frames the firmware holds for
the air, and the host ledger admits 52 pages (four frames of 13) where
the vendor's default budget for the queue is 468 pages (36 frames): the
ledger uses about 11 % of the budget. The forecast is arithmetic on boot
E's mean wait, not a guess, and it predeclares its own correction: the
wait rises with depth (more frames queue behind each credit), so each
result is read against the wait it measured, never against 3.48 ms flat.

| depth | ledger pages | predicted frames/s at 3.5 ms | implied |
|---|---|---|---|
| 4 (boot E) | 52 | 1,143 | 13 Mbit/s (measured as a 9.3 floor under the 1 MiB cap) |
| 8 (boot F) | 104 | 2,286 | 26 Mbit/s |
| 12 (boot G) | 156 | 3,429 | air-limited at 54 Mbit/s |

**The change.** [0280](../../patches/proposals/0280-wifi-mt6797-make-the-data-depth-a-build-option-with-the-TC1-ledger-derived-from-it.patch)
makes the depth (`CONFIG_MT6797_CCMP_TX_DEPTH`, 1–16) a build option
with the pages the host ledger admits derived from it, 13 a frame, so a
build cannot carry one depth with another depth's ledger (owner's
refinement); nothing changes at the default. Boot F: depth 8, 104 pages.
Boot G: depth 12, 156 pages, exposed only through the sweep profiles. One variable per boot, five chunks,
the probe riding, boot B's revert rule standing (any receive chunk ended
by `device_timeout` or any non-zero payload reverts the boot's change).
The tree is otherwise the baseline with 0278.

**Harness.** The per-chunk byte cap is raised from 1 MiB to 4 MiB for
these boots (plan, review record and the laptop's sender together; the
device side is bounded by the laptop), so a 1 s chunk is the bound up to
33 Mbit/s; the compose, validator and review records take the declared
depth and ledger. Both changes are declared in the run's plan.

**TX first.** `tx_failed`, `retire_expired`, `pid_faults`, `left_pages`
and the zero-payload check before any throughput claim; `inflight_max`
must reach the depth or the depth was not exercised.

| Reading | Cause | Next |
|---|---|---|
| frames/s up with the wait rising less than proportionally; TX and RX device chunks quoted as the same-boot pair | the depth was the bound; the credit path scales | the next depth, then the air: a higher legacy rate against HT, decided on the depth-12 numbers |
| frames/s flat with the wait rising in proportion | the firmware's per-frame processing is the bound, not the host depth | stop the depth sweep; the firmware's per-frame path (RE VM) |
| `retire_expired` > 0 or `pid_faults` > 0 | the FIFO or the pool does not hold at this depth | revert to the previous depth; read the credit lines |
| any `device_timeout` receive chunk or a non-zero payload | the bound or the ownership is wrong at this depth | revert immediately |

**The three questions.** Reachability: the depth sizes the slot array and
the per-pass submission count; the ledger pages are the admit call at
HIF activation, reached on every boot. Ownership: the host ledger's own
figures, 6.6 kB of accounting at 52 pages against the vendor's 468-page
(60 kB) budget, with about 18 kB of extra socket buffers at depth 12: the
constraint being lifted was never RAM but a conservation habit; the
firmware's budget is 468 pages. What the vendor writes: 468
pages, 36 frames, by default; no per-frame FIFO. The ledger stands at
nine. After the air becomes the limit, the choice between a higher
legacy rate and HT is made on the depth-12 numbers, not before them.

### Boot F result (2026-10-25, 16:13 UTC): depth 8 did not move transmit; the slots are half empty, the limit is upstream of the driver

Build `4a6c3785` (lifecycle profile, depth 8 with the 104-page ledger
derived), boot2 `78bc8d58…` over `528d1d1d…`, mainline boot `d54083d8…`,
returned to Gemian `ccba9a97…` (changed-ID Gemian, recovery confirmed,
three attempts); session `ram-service-regression-pass`, log complete
through the seal (173,864 bytes), receipt `all_pass`, disconnect accepted,
data phase 41.2 s ending by `disconnect`. The steady-state protocol ran
for the first time: 4 MiB or 3 s per chunk, five chunks each way. The
watcher was started by hand 13 s after the owner's boot reached the USB
endpoint (the staged watcher file lacked its executable bit, a staging
fault now fixed); the cold logger admitted the start and the run is whole.

**TX first, and the revert rule.** `tx_failed=0`; `retired=19041
expired=0 pid_faults=0 wait_avg_us=4473 wait_max_us=32323 left_pages=0
inflight_max=8`: the depth was exercised to its limit, no expiry, no
fault, no unmatched page; `debt=0`, no guard record, 21 credit lines, no
overflow; the zero-payload check passed on all five transmitted chunks.
One receive chunk (the fifth) reads `ended_by=device_timeout`, the
literal trigger of boot B's revert rule, and it is not boot B's failure:
the device's 3 s bound (`timeout 3`, exit 143) fired before the laptop's
3 s duration, a race between two equal bounds in the new protocol, with
3,353,568 bytes received and the laptop's final-half send rate at 42
Mbit/s; the receive direction did not collapse (the other four chunks at
their 4 MiB cap in 1.7–2.5 s, UDP at 30 Mbit/s with zero loss,
`rx_delivered=27158`). The protocol is corrected (the device's bound is
now one second past the laptop's duration) and the rule stands; this
boot's change is reverted for a different reason, below.

| | Boot F (depth 8; 4 MiB or 3 s) | Boot E (depth 4; 1 MiB or 1 s) |
|---|---|---|
| TX chunks, whole (Mbit/s) / ended by | 9.24, 9.15, 1.91, 9.25, 9.36 / all `duration` (3.0 s, 3.4–3.5 MB) | floor 9.18–9.46 / `byte_cap` at 0.91 s |
| TX chunks, final half (Mbit/s) | 9.09, 8.85, 0.72, 9.24, 9.05 | — |
| RX device-side chunks, whole (Mbit/s) / ended by | 13.70, 15.98, 18.75, 20.09, 8.88 / `byte_cap` in 1.7–2.5 s, the fifth at the device's bound | floor 17.9–20.0 / `byte_cap` in 0.45 s |
| RX laptop-side final half (Mbit/s; the sender's buffer fill, not the device's receive) | 28, 56, 45, 64, 42 | — |
| credit retire: mean / max wait, in flight max | 4.47 ms / 32.3 ms, 8 | 3.48 ms / 14.3 ms, 4 |
| TCP receive `rttcur` max per chunk (ms) / window max | 626, 288, 306, 291, 318 / 2.0 MB | 76–83 / 0.4 MB |
| in-chunk ping (ms min/avg/max) | 4.6 / 48.2 / 95.0 | 4.9 / 28.7 / 41.4 |
| at-rest ping (ms) | 3.9 / 26.3 / 63.9 | 254 / 309 / 364 |
| UDP 10 / 20 / 30 Mbit/s | zero loss on all three | zero loss on all three |
| ccmp-stable end | `queued=8192 beyond=18927` | `beyond=3304` |

**Reading (corrected the same day: the first reading named the sender's
TCP; the owner's arithmetic names the firmware).** Frames per second are
flat: 9.2 Mbit/s steady at depth 8 against boot E's 9.2 floor at depth
4, now measured over full 3 s chunks, so the number is a rate, not a
floor; the wait rose 3.48 → 4.47 ms and `inflight_max` 4 → 8. The
pipeline is not saturated by the host: 8 slots at 4.47 ms would admit
about 1,790 frames a second, and 794 arrive. Depth 12 would read a wait
of about 5.5 ms and the same rate. **Depth 8: no change, the service
rate is fixed.** The quantity that decides it is the service time, wait
divided by mean occupancy (Little's law): 3.48 ms over 2.8 frames at
depth 4 and 4.47 ms over 3.6 frames at depth 8 are both 1.24 ms a frame,
a serial service whose utilisation at 794 frames a second is 0.99. The
limiter, with the evidence that excludes everything else: the host's DMA
attached and carried every frame (`tx=1` attached, no failure, no DMA
poll ceiling) with the CPU 90 % idle; the air at 54 Mbit/s costs 0.225 ms
for a 1,518-byte frame, 5.6× less than the 1.25 ms observed, and the
access point receives at that rate (5 unacknowledged of 5,132 on boot C);
the credits are collected in every pass (216,858 passes, 0.088
submissions each); the wait grows with the depth while the rate does
not, a fixed service rate behind a longer queue. **Corrected again (owner, after boot H's chunk): depth 8 neutral, the
offer rate is the limit; the mechanism is not yet identified.** The
firmware reading above does not survive the depth comparison: a
service-limited pipeline with eight admitted would have carried the
wait from 3.48 ms to about 6.96 ms, and it went to 4.47; the mean in
flight never approached 8, and the worker's census (0.088 submissions a
pass over 216,858 passes) says the driver's queue was empty most of the
time. The frames are not being offered at the depth the driver permits.
The service-time derivation (wait over occupancy, 1.24 ms at both
depths) measures the per-frame latency when few are in flight; it is a
ceiling only if the firmware serves serially, which is the unproven
step. What is proven: the air is not the limit (boot H's sampled frames
all left at 0x4c with status 0, 0.225 ms of air against 1.25 ms
observed), the host's DMA and CPU are not, and the depth is not. Whether
"the driver can only do 9" or "TCP is pacing it at 9" is decided by a
transmit probe without acknowledgement pacing and by the device's own
TCP state during the chunks (§18), not by more depth.

**Dispositions.** Boot G (depth 12) is cancelled and the boot spent
elsewhere (§17); the lifecycle fragment returns to depth 4 (0280 stays
the option); the §16 forecast is retired as written (it assumed the slots
would fill). 0274 v2 held again (`beyond=18927`). The steady-state
protocol is adopted with its bound race fixed; boot F's whole-chunk
transmit numbers are the first steady-state rates in the series.

**Next.** If the per-frame cost is real and inside the firmware, the way
past 9.25 Mbit/s is fewer firmware transactions per byte (A-MSDU or
A-MPDU: HT capability, QoS data with TIDs and, for A-MPDU, a block-ack
session), a project, not a boot. **It is not opened on the current
evidence**: aggregation addresses a per-frame cost, and a per-frame cost
has not been established. The sampled status report (§17) and the
transmit probe with the device's TCP state (§18) decide it in one boot;
if they say TCP-paced, HT could not move the number it would be opened
for. The firmware question (software CCMP in the transmit path) is
answered in the private memo: no AES tables in either image, the cost,
whatever it is, is not encryption.

## 17. Stalls, named; and boot H (predeclared, 2026-10-25): the sampled status report

**Stalls, a named object.** Transmit chunk 3 of boot F ran at 1.91 Mbit/s
for its whole 3 s (716,336 bytes; final half 0.72 Mbit/s) between device
clock 40.94 s and 43.95 s, while the chunks on either side ran at 9.2;
receive chunk 5 of boot F received 3,353,568 bytes between 59.20 s and
62.22 s, its laptop-side final half at 42 Mbit/s and its whole at 8.9,
so its first half carried almost nothing, before the device's bound cut
it. The same phenomenon appeared at longer intervals before: boot D's
second receive chunk (10.4 against 15.8), boot C's first transmit chunks
below the later ones. These are not the series' rate; they cost real
throughput and they would confound an aggregation reading left inside
the chunk averages. From here every result quotes its stall-free chunks
beside the whole-run rate, and each stall is recorded here with its
device-clock start and end, its direction and its bytes. The mechanism
(a TCP retransmission timeout after an air loss that the completion
report cannot name, or a receive-path pause) is a separate question; the
sampled report below gives the first instrument that can name an air
loss on a data frame.

**Boot H: the sampled MCU status report ([0281](../../patches/proposals/0281-wifi-mt6797-request-the-MCU-status-report-for-one-ordinary-data-frame-in-N.patch), predeclared).** Retiring
on credits removed both instruments that identified a data frame's rate
and its submit-to-completion time (the histograms read `n=0`). Restore
them by sampling, not by restoring their cost: request the MCU status
report for one ordinary data frame in 64, the vendor's own asymmetry (it
requests reports only where it has a handler), keeping the credit-retire
path for the 63 others. The sampled frame keeps its place in the credit
FIFO (its pages are matched in order like every other frame) and its
slot until the report arrives, which supplies the rate word, the status
and the latency sample into the existing histograms (0275 v2, 0279) at
1/64 of the per-frame cost; the credit accounting stays exact. One
variable, five steady-state chunks, the probe riding, the stall ledger
kept.

| Reading | Cause | Next |
|---|---|---|
| the sampled rate word is 0x4c throughout, status 0 | the air is exonerated: the firmware's per-frame cost is the limit at the fixed rate | aggregation (HT) is the throughput lever; the RE question decides how much it buys |
| the firmware downshifts below 54 on some samples | the air is part of the answer | the rate is a lever beside aggregation: read the downshift against the stalls |
| sampled status 3 clustered at the stalls | air losses the credit path hid, costing TCP timeouts | name the stalls as air losses; the firmware's retry count is the next read |
| samples missing or unowned | the sampling path or the pool disagrees with the credit path | revert 0281; the fixture is wrong |

**The RE question, answered (private memo, 2026-10-25).** Neither
retained firmware image (the ROM and the RAM code) holds an AES S-box,
inverse S-box, T-table or round-constant table, so a table-driven
software AES is excluded; the key material installed by the key command
goes to the MAC's per-station key table, which the hardware reads. The
firmware's ~1.25 ms a frame is not encryption but its per-transaction
work around a data frame (descriptor, station and key lookup, queueing,
page and status bookkeeping). A-MSDU divides that work by the aggregate
size and fits this cost exactly; A-MPDU buys air time, not firmware time;
no per-frame rate change moves it. Host fixture for 0281:
[`tests/credit-retire-test.c`](tests/credit-retire-test.c) (a sampled
frame covered in order and held for its report; a report before coverage
leaves a placeholder; placeholders occupy entries for the room check).

**Reachability, ownership, the vendor.** The sample is chosen at
submission (every 64th ordinary data frame carries a PID and the report
flag); the report arrives on the receive path as today's management
reports do; the vendor requests the report exactly this way for frames
with a handler. The ledger stands at ten.

### Boot H, first run (2026-10-25, 16:37 UTC): void for the series on a harness fault; the sampled report works

Build `a1aa339a` (depth 4, credit retire, one report in 64), boot2
`0f1ca6cf…` over `78bc8d58…`, mainline boot `aa1af0f7…`, returned to
Gemian `00c816df…` (recovery confirmed); session
`ram-service-regression-pass`, log complete through the seal (172,800
bytes). The measurement ended after the first transmit chunk: the device
bound of 4 s that fixed boot F's race made the laptop close a transmit
chunk first, and the device's `nc` then exits 1 on the closed pipe, which
the leaf's exit-code rule read as a fault (exit 38); the leaf ended, the
host's disconnect ended the data phase at 8.9 s (`reason=disconnect`,
`tx_failed=0`), the receive direction and the probe never ran, receipt
`all_pass=false`. A harness fault, not a device finding: the transmit leg
now accepts that close as the chunk's normal end (receive sees a plain
EOF), and the run is repeated on the same image.

**What the one chunk and the instrument did yield (provisional, not a
series row).** TX chunk 1: 9.48 Mbit/s over 3.0 s (final half 9.46), the
steady rate again. The sampled status report worked exactly as
predeclared: `samples=39 reports=39` of 2,484 frames retired (one in 64),
no expiry, no PID-pool fault, no unowned completion, `left_pages=0`; the
rate histogram `0/0x004c=39` (every sample sent at 54 Mbit/s, status 0,
first and last 0x4c), the completion-latency histogram `n=39`: 37 in
[4, 8) ms, one in [8, 16), one under 1 ms, maximum 14.9 ms, against the
credit-retire mean wait of 3.59 ms. **Proven by the chunk:** every sampled data frame left at 0x4c with status
0, so the air (0.225 ms a frame at 54 Mbit/s against the 1.25 ms
observed) is exonerated at the fixed rate, and the one-in-64 report costs
nothing (39 reports of about 2,500 frames). Also recorded, the first
direct evidence of what the access point chooses toward this station in
one phase: `RX rates 1/12=1286, 1/8=227, 1/13=80, 1/11=41, 1/9=4` (78 %
at 54 Mbit/s, 14 % at 48). **Not proven:** that the firmware's per-frame
processing is the limit; the depth comparison does not support it (the
boot F record's third reading), and this chunk cannot say whether the
driver can only do 9 or TCP paces it at 9. **The fault, named:** a run
that ends after one chunk without recording a reason is the silent-leg
class again (an endpoint reported `completed=false, errors=0`, the
receive direction had no chunks, the classifier read `fault=false` with
`measurement_censored=true`); an endpoint that stops now records why and
the session fails with that reason attached (§18). Boot H is recorded as
one valid transmit chunk with the receive direction lost to a harness
stop, not as a measurement.

## 18. Boot H, second run (predeclared, 2026-10-25): the transmit probe and the device's TCP state

**The question.** The transmit number is 9.2 Mbit/s at depth 4 and 8 with
the air, the host and the depth excluded; what remains is "the driver
and firmware can only do 9" against "TCP paces it at 9". Two instruments
decide it in one boot, neither a driver change.

**The transmit probe.** The mirror of the receive probe that proved 30
Mbit/s: the device offers 10, 20 and 30 Mbit/s toward the laptop with
1,400-byte payloads, timed on the device, the arrivals counted on the
laptop. The device's BusyBox has no UDP sender (`nc` is TCP-only, no
`socat`), so the leg is ICMP echo: `ping -s 1400 -i <interval> -c N`,
893, 1,786 and 2,679 requests at intervals of 1.12, 0.56 and 0.37 ms,
each leg about a second; the laptop answers every request (its replies
are the count, taken on the device as "received", and the receive path
has carried 30 Mbit/s with zero loss on three boots, so a missing reply
is a lost request), and the offered rate is the device's own clock
around the leg. The return traffic is the one deviation from the owner's
specification (no return traffic) and is declared; the receive UDP legs
step aside this boot to keep the device command under its 4,096-byte
bound (they stand on three boots), the leaf's comment lines are stripped
at render and the console indicator (not evidence) is left out of this
run for the same reason ([`hosts/transmit_probe.py`](hosts/transmit_probe.py);
the early-stop record is [`hosts/early_stop.py`](hosts/early_stop.py)).

**The device's TCP state.** One line per transmit chunk, sampled 1.5 s
into the chunk from `/proc/net/tcp` for the socket to the laptop's
transmit port: the congestion window, the slow-start threshold, the
retransmit-queue count and the transmit queue; and the device's TCP
retransmission count (`/proc/net/snmp`, `RetransSegs`) before and after
the transmit phase. It discriminates the same question from the other
side and makes the answer unambiguous when both agree.

**The silent early stop, fixed.** An endpoint that stops before its last
chunk records why (`stopped: after_chunk, reason`), the measurement
carries `early_stop` with the device's exit code, and the classifier's
fault reason names it; a run that ends after one chunk can no longer
read as censored with no fault.

| TX probe result | Cause | Next |
|---|---|---|
| about 20 Mbit/s or better | the driver and firmware are not the limit; the TCP send window is | the transmit number becomes a TCP question: socket buffers, large segments, or a protocol without acknowledgement pacing |
| about 9 Mbit/s, matching TCP | the per-frame cost is real and inside the firmware | aggregation (HT with block-ack) is the throughput project |
| between | both contribute | read the device's congestion window before choosing |

The cwnd line reads the same table from the other side: a window pinned
near the bandwidth-delay product of 9 Mbit/s over the in-chunk round trip
says TCP; a window far above it with the queue empty says the driver.
The run otherwise repeats boot H's first run on the same image (the
sampled status report, 0281), five steady-state chunks with the transmit
leg's close accepted, the stall ledger kept.

### Boot H, second run (2026-10-25, 17:06 UTC): stopped after one chunk again, this time with its reason recorded; the first congestion-window sample

Same image (`0f1ca6cf…`, the installer's full readback matched), mainline
boot `ea148dcb…`, returned to Gemian `d70ab8f1…`; session
`ram-service-regression-pass`, log complete (177,340 bytes). The run
stopped after the first transmit chunk once more: the device's `nc` ended
the chunk the laptop closed with SIGPIPE (exit 141), not the exit 1 the
transmit leg had been taught to accept, and the leaf exited 38 again. The
early-stop record did its job: the measurement carries `early_stop` with
both endpoints' reasons ("TX: cancelled while waiting for the device to
open chunk 2; RX: cancelled while waiting for the device to open chunk
1") and `device_chunk_exits TX: [141]`, so the stop is named in the
receipt and the classifier, not inferred. The transmit leg now accepts
141 as well; the third run follows on the same image.

**The first congestion-window sample.** 1.5 s into transmit chunk 1 (9.19
Mbit/s whole, 9.42 final half) the device's socket to the laptop read
`cwnd=7 ssthresh=5`, retransmit queue empty: a window of seven segments
(10 KB) in congestion avoidance, which at 9.2 Mbit/s is a round trip of
about 9 ms as the device's TCP sees it, and a slow-start threshold of five
says the window was cut by loss or by a retransmission timeout before
this sample. One sample, provisional: it reads as the first row of §18's
table from the TCP side (the device's TCP is pacing transmit at its
window over the completion latency), and the third run's five samples
and echo legs decide it.

### Boot H, third run (2026-10-25, 17:14 UTC): whole; the transmit limit is the driver's own drops, not the air, not the depth, and TCP holds a six-segment window because of them

Same image (`0f1ca6cf…`, the installer's full readback matched), mainline
boot `7a95b0c6…`, returned to Gemian `0550b47c…` (recovery confirmed);
session `ram-service-regression-pass`, log complete (172,256 bytes); both
directions complete, five steady-state chunks each, the echo legs and
five congestion-window samples; data phase 37.8 s ending by `disconnect`.
The receipt reads `all_pass=false` only because the laptop's own rule
still demanded exit 0/124/143 on every chunk where the transmit leg now
ends on the laptop's close (1 or 141): a verdict artefact, corrected in
the protocol; the measurement is whole.

**TX first.** `tx_failed=0`; `retired=23512 expired=0 pid_faults=0
wait_avg_us=3073 wait_max_us=15377 left_pages=0 inflight_max=4
samples=373 reports=373`; no guard record, no overflow, the zero-payload
check passed; `ccmp-stable end: queued=8192 beyond=18083` (0274 v2 held
again). The interface counters: `tx_errors=0 tx_dropped=0` on both
phases.

| | Boot H run 3 (depth 4, sampled report, steady-state chunks) |
|---|---|
| TX chunks, whole / final half (Mbit/s) | 9.19, 9.28, 9.35, 9.72, 9.73 / 9.17, 9.16, 9.41, 9.81, 9.47 (all `duration`, 3.0 s; no stall) |
| TX aggregate, host received | 8.95 |
| RX device-side chunks, whole (Mbit/s) | 20.34, 20.21, 14.46, 20.21, 19.62 (4 MiB in 1.65–2.32 s; chunk 3 the slow one) |
| RX aggregate, host sent | 17.07 |
| device idle TX / RX | 89.6 % / 86.7 % |
| sampled status reports | 373 of 23,512 (one in 63): all `0/0x004c`, first and last 0x4c; latency 42 under 1 ms, 78 in [1, 2), 25 in [2, 4), 199 in [4, 8), 29 in [8, 16), max 10.0 ms |
| device TCP state 1.5 s into each TX chunk | `cwnd=6 ssthresh=5`, `6/5`, `6/5`, `6/6`, `6/6`; retransmit queue empty each time |
| device TCP `RetransSegs` across the TX phase | 0 → 451 (1.9 % of 23,885 segments) |
| echo legs, device to laptop, 1,400-byte payloads | offered 4.83 Mbit/s: 885 of 893 replied (0.9 % lost); offered 9.48: 1,263 of 1,786 (29 %); offered 13.96: 1,218 of 2,679 (54 %); delivered 4.79, 6.70, 6.34 Mbit/s |
| in-chunk ping / at rest (ms min/avg/max) | 10.3 / 44.6 / 85.4 and 9.7 / 37.0 / 78.1 |
| TCP receive `rttcur` max per chunk (ms) / window max | 324, 300, 348, 331, 300 / 2.5 MB |
| AP downlink (RX rates) | 1/12=25486, 1/8=656, 1/11=124, 1/13=5, 1/9=4 (97 % at 54 Mbit/s) |

**Reading, against §18's table.** The echo legs could not offer 10, 20
and 30: BusyBox `ping` paced its requests at about 2.3 ms whatever the
interval asked (offered 4.8, 9.5 and 14.0 Mbit/s), a limitation of the
device-side tool, declared. What they do show is decisive with the TCP
state beside them: at 4.8 Mbit/s offered the path delivers 4.8 with under
1 % loss; at 9.5 and 14 offered it delivers 6.7 and 6.3 with 29 % and
54 % lost, so the transmit path loses what is offered above roughly
800–1,000 frames a second rather than queueing it. TCP sees the same
thing from inside: 451 retransmissions in the transmit phase and a
congestion window pinned at six segments (8.7 KB) with the slow-start
threshold at five or six on all five samples, which at 9.2–9.7 Mbit/s is
a round trip of about 7.3 ms as the device's TCP measures it. The window
never grows because every probe above the drain rate costs a loss. The
373 sampled status reports, all acknowledged at 0x4c, say those losses
are not on the air (at a 1.9 % loss rate the chance of 373 clean samples
is below one in a thousand), and the interface counters count no drop:
the loss is between the socket and the firmware, invisible to every
counter. The source names it: the driver's data admission is a bounded
queue (`MT6797_JOIN_DATA_TX_QUEUE` frames, 8 × 1,550 bytes), and a frame
that arrives when the queue is full is freed unsent
(`ieee80211_free_txskb` at the end of the transmit entry) with no
`ieee80211_stop_queues` anywhere in the driver: there is no backpressure
toward mac80211, so TCP's bursts above the drain rate are dropped
silently, reported to no one, and recovered by TCP's retransmission with
its window halved. The vendor stops the network queue at a per-queue
threshold and wakes it (`netif_stop_subqueue` / `netif_wake_subqueue`,
`gl_kal.c`). So: the middle row of the table (both contribute), read
with the window: the driver drains about 800–1,000 frames a second and
drops the excess; TCP, losing 2 %, holds a six-segment window and paces
at 9.2–9.7 Mbit/s; the per-frame drain cost (about 1.1–1.25 ms a frame
for 1,448-byte frames) is real and upstream of the air, and the drops are
a defect of their own that costs the retransmissions, the small window
and the stalls. HT is not opened on this: the first change is
backpressure (§19), after which the transmit number reads the drain rate
without loss and the drain itself becomes the question.

**Transmit-path loss, the first figure.** Beside the receive path's UDP
figure (30 Mbit/s offered, zero loss, three boots), the transmit path
now has its own: 0.9 % lost at 4.8 Mbit/s offered, 29 % at 9.5 and 54 %
at 14.0 (1,400-byte echo requests, the pacing of BusyBox `ping` at about
2.3 ms declared). The loss begins at the drain rate, not at an air
rate: the sampled reports show the air acknowledging every frame it is
given, and the drop sits in the driver's admission above about 800–
1,000 frames a second.

**Stalls.** None on transmit this run; receive chunk 3 (14.46 against
19.6–20.3, 2.32 s to its cap) is the one slow chunk and is recorded in
the ledger (§17).

## 19. Boot I (predeclared, 2026-10-25): backpressure toward mac80211, one variable

**The change.** [0282](../../patches/proposals/0282-wifi-mt6797-stop-mac80211-s-queues-while-the-data-queue-is-nearly-full-with-the-queue-bound-its-own-option.patch)
(`CONFIG_MT6797_TX_BACKPRESSURE`): when the driver's data queue reaches
its bound (eight frames, 12,400 bytes) the transmit entry stops
mac80211's queues instead of letting the next frame arrive to be freed
unsent; the worker wakes them once the queue has drained to half; the
data-phase end, the discard of the queue at teardown and the rearm wake
them so nothing stays stopped. Frames that still arrive while stopped
are counted (`tx_dropped=`) and the data-end line reports the stops, the
wakes and the drops. The vendor's form of the same thing is the
per-queue stop threshold with a wake (`gl_kal.c`). Nothing changes with
the option off.

**The expectation, honestly (owner, 2026-10-25).** Backpressure converts
drops into queueing; it does not raise the drain rate. The arithmetic
bounds the result: 1,150 frames a second at depth 4 with a 3.48 ms wait,
1,790 at depth 8 with 4.47 ms, that is 13 to 20 Mbit/s; removing 451
retransmissions out of about 3,600 frames a chunk is worth about a tenth
of the goodput, and the rest comes from TCP's window recovering. So: loss
to zero, the rate to 10–20 Mbit/s, not a multiple. The single most
informative number is not the rate but whether the drain rate moved at
all between boot H and boot I: `wait_avg`, `inflight_max`, the stops and
the wakes are quoted beside the rate.

**Why 0235's verdict does not apply.** 0235 held the mac80211 queue and
was retired for measuring worse; 0282 does the same thing. At that time
the pipeline submitted one frame per pass, so holding the queue could
only add latency; now the queue is eight deep, credits retire
asynchronously, and holding it is the only way to keep frames that would
otherwise be freed unsent.

**The drop counter.** `tx_failed=0` through 451 retransmissions is this
boot's instrumentation lesson: a frame freed unsent is invisible to every
counter the driver has. 0282's `dropped_full` counts every ordinary data
frame the transmit entry frees unsent inside an open data phase, stopped
or not, so the data-end record can never again show zero drops while the
stack retransmits; it is the number that says whether backpressure holds
or leaks.

**Harness.** The same run as boot H's third: five steady-state chunks,
the sampled report, the echo legs, the TCP state per chunk, the
retransmission count; the laptop's verdict accepts the transmit leg's
closes.

**TX first.** `tx_failed`, `retire_expired`, `pid_faults`, `dropped_full`
(expected 0 with the queues stopped in time), the zero-payload check;
any receive `device_timeout` or non-zero payload reverts, as boot B
established.

| Reading | Cause | Next |
|---|---|---|
| steady TX 12–20 Mbit/s, zero loss, retransmissions near zero | the drops were masking the drain rate | the drain rate is now the limit: the per-frame cost, then aggregation |
| steady TX about 9.3 Mbit/s, zero loss, stops high, `inflight_max` 8 throughout (4 at this depth) | the 1.1 ms per frame is real and the drops never inflated it | aggregation (HT) is the only lever left on transmit |
| TX up but RX down, or any `device_timeout` | the stop/wake path starves the receive side | revert, as boot B established |

**What opens HT.** HT is opened when a boot shows zero-loss transmit at
the drain rate with a per-frame cost that only aggregation can amortise;
boot I is the boot that decides whether that is now true. It is not
reopened on instinct before.

**The three questions.** Reachability: the stop at the transmit entry's
admission, the wake in the worker's dequeue and at every path that
empties the queue. Ownership: mac80211's queue state is the host's;
nothing is written to the device. What the vendor writes: a network
queue stop at a packet threshold and a wake when drained. The ledger
stands at eleven.

### Boot I result (2026-10-25, 17:33 UTC): the mechanism works, the queue discipline does not

Build `b02ddb84` (boot H's tree with 0282), boot2 `d589c647…` over
`0f1ca6cf…`, mainline boot `bf3cebdf…`, returned to Gemian `fa957e17…`
(recovery confirmed); session `ram-service-regression-pass`, log complete
(174,970 bytes), receipt `all_pass` (the laptop's rule now accepts the
transmit leg's closes), both directions complete, no early stop.

**TX first.** `tx_failed=0`, `retired=16214 expired=0 pid_faults=0
left_pages=0`, 257 samples with 257 reports all at `0/0x004c`; the
backpressure record: `stops=2223 wakes=2223 dropped_full=0 stopped=0`,
so mac80211's queues were stopped and woken 2,223 times in 16,471 frames
(every seventh frame) and no frame was freed unsent. The zero-payload
check passed.

| | Boot I (0282 on) | Boot H run 3 (same tree, 0282 off) |
|---|---|---|
| TX chunks, whole / final half (Mbit/s) | 2.46, 3.69, 3.69, 4.02, 3.80 / 3.81, 4.59, 3.91, 4.03, 3.30 | 9.19–9.73 / 9.16–9.81 |
| TX aggregate | 3.34 | 8.95 |
| RX device-side chunks (Mbit/s) / ended by | 17.66, 19.17, 7.55, 19.28, 13.42 / chunk 3 `device_timeout` (3.78 MB at the device's 4 s bound, final half 58, a stall at its start) | 14.5–20.3 / all `byte_cap` |
| device TCP state per TX chunk (cwnd / ssthresh) | 2/16, 12/11, 19/14, 1/15 (retransmit queue 1: a timeout), 22/11 | 6/5, 6/5, 6/5, 6/6, 6/6 |
| `RetransSegs` across the TX phase | 0 → 549 (3.3 % of 16,471) | 0 → 451 (1.9 %) |
| credit-retire wait mean / max, in flight max | 2.84 ms / 15.2 ms, 4 | 3.07 ms / 15.4 ms, 4 |
| completion latency (257 samples) | 13 under 1 ms, 72 in [1, 2), 31 in [2, 4), 95 in [4, 8), 46 in [8, 16), max 10.5 ms | 42, 78, 25, 199, 29 of 373 |
| echo legs | the first leg 893 of 893 at 9.35 Mbit/s offered, zero loss; the second and third did not run to their summary | 0.9 % / 29 % / 54 % |
| in-chunk ping / at rest (ms min/avg/max) | 6.1 / 43.1 / 66.4 and 70.0 / 125.2 / 180.3 | 10.3 / 44.6 / 85.4 and 9.7 / 37.0 / 78.1 |

**Reading (owner, 2026-10-25): a mechanism success and a configuration
regression.** `stops=2223 wakes=2223 dropped_full=0 stopped=0`,
`tx_failed=0`, `expired=0`: the intent is achieved and nothing was freed
unsent. And transmit fell from 9.19–9.73 to 2.46–4.02 Mbit/s per chunk
(aggregate 8.95 → 3.34) while the credit-retire wait fell to 2.84 ms with
`inflight_max=4`. The cause is in the counters, not the throughput: 2,223
stops over a 35.7 s phase is a stop and a wake every 16 ms, and four in
flight over 2.84 ms allows about 1,400 frames a second against about 345
delivered. The stop/wake cycle is the limiter: the queue bound (eight)
and the in-flight depth (four) are the same order, so the queue
oscillates at the worker's pass cadence and mac80211 is re-scheduled
before it can refill. The 549 retransmissions and the window swinging
from 1 to 22 are what TCP does to a path whose service stops every 16
ms; they are not the air (257 clean samples) and not drops
(`dropped_full=0`). 0282 is kept and its thresholds fixed (§20); the
series does not return to silent drops as the fallback: the old
behaviour bought throughput by losing frames and paying 451
retransmissions behind a `tx_failed=0`, and the drop counter stays in
the data-end record permanently so that can never be invisible again.

**Stalls.** Receive chunk 3 ended at the device's bound (`device_timeout`,
3,782,176 bytes in 4.01 s, 7.55 Mbit/s whole against 17.7–19.3 on chunks
1, 2, 4 and 5, the laptop's final half at 58), the third appearance of
the same intermittent receive stall; transmit chunk 1 ran at 2.46 against
3.7–4.0. Both go to the stall ledger (§17) with their device-clock
positions taken from the leaf's progress lines, and any transmit reading
quotes its stall-free chunks beside the whole run.

## 20. Boot J (predeclared, 2026-10-25): backpressure with the queue decoupled from the depth

**The change.** 0282 amended in place
([v2](../../patches/proposals/0282-wifi-mt6797-stop-mac80211-s-queues-while-the-data-queue-is-nearly-full-with-the-queue-bound-its-own-option.patch)):
the data queue's bound becomes its own option
(`CONFIG_MT6797_DATA_TX_QUEUE_FRAMES`, default 64 frames, 100 kB of
pageable memory, eight without the option), the stop mark is seven
eighths of the bound (56) and the wake mark half (32), so the stop and
wake cycle runs about 100 ms apart at the measured drain rate rather
than every 16 ms; the record keeps the stops, the wakes and the drops and
adds the queue's high-water mark against its bound. One variable, the
same run as boots H and I (five steady-state chunks, the sampled report,
the echo legs, the TCP state per chunk, the retransmission count).

**The expectation.** Stops in the low tens a second, `dropped_full=0`,
transmit back at or above 9.25 Mbit/s with no retransmissions on the
device's socket. Quoted beside the rate: `wait_avg`, `inflight_max`, the
stops, the wakes and the high-water mark.

| Reading | Cause | Next |
|---|---|---|
| TX back at about 9.3 Mbit/s with zero loss and retransmissions near zero | the drain rate is confirmed as the limit | aggregation (HT) is the only remaining transmit lever; it opens on this evidence |
| TX above 12 with zero loss | the retransmissions were part of the cost and the true drain rate is higher | the drain rate, measured now without loss, is the next number to understand |
| stops still in the hundreds a second, or TX still throttled | the marks are still coupled to the pass cadence | widen the bound again before reading anything else |
| retransmissions persist with `dropped_full=0` | the retransmissions are not drops: the device's TCP timers against a late acknowledgement | the device's `TcpExt` counters (loss probes, spurious timeouts, DSACKs) before and after the transmit phase |
| any receive `device_timeout` or non-zero payload | the stop/wake path starves the receive side | revert to the previous bound, as boot B established |

The three questions: reachability, the same stop and wake sites with the
marks moved; ownership, mac80211's queue state is the host's; the vendor,
a per-queue packet threshold with a wake. The ledger stands at twelve.

### Boot J result (2026-10-25, 17:53 UTC): transmit above 12 with zero loss; the retransmissions were part of the cost

Build `e51cb584` (boot I's tree with 0282 v2, queue bound 64, stop 56,
wake 32), boot2 `5e19a3c6…` over `d589c647…`, mainline boot `50c9d80a…`,
returned to Gemian `3722770b…` (recovery confirmed, live identity checked
afterwards); session `ram-service-regression-pass`, log complete (176,635
bytes), receipt `all_pass`, both directions complete, no early stop. The
controller's `session_exit=1` is the same exit boots H (run 3) and I
recorded with a complete log and a passing receipt.

**TX first.** `tx_failed=0`, `retired=25630 expired=0 pid_faults=0
left_pages=0`, 406 samples with 406 reports all at `0/0x004c`; the
backpressure record: `stops=156 wakes=156 dropped_full=0 stopped=0
high_water=56 bound=64`: the queue reached its stop mark and never its
bound, and no frame was freed unsent. The zero-payload check passed and
no receive chunk reached the device's bound.

| | Boot J (bound 64) | Boot I (bound 8) | Boot H run 3 (no backpressure) |
|---|---|---|---|
| TX chunks, whole / final half (Mbit/s) | 16.61, 16.70, 15.51, 15.96, 16.50 / 16.64, 16.60, 15.22, 16.09, 16.55 (all `byte_cap`: floors) | 2.46–4.02 / 3.30–4.59 | 9.19–9.73 / 9.16–9.81 |
| TX aggregate | 15.02 | 3.34 | 8.95 |
| RX device-side chunks (Mbit/s) / ended by | 19.17, 18.54, 18.85, 18.54, 19.62 / all `byte_cap` | 7.55–19.28 / one `device_timeout` | 14.5–20.3 / all `byte_cap` |
| stops / wakes / `dropped_full` | 156 / 156 / 0 (at most 14 a second over the 11.3 s transmit phase) | 2,223 / 2,223 / 0 | — (frames freed unsent) |
| device TCP state per TX chunk (cwnd / ssthresh) | 65/64, 71/63, 58/49, 86/53, 95/77, retransmit queue 0 throughout | 2/16 … 22/11 | 6/5 … 6/6 |
| `RetransSegs` across the TX phase | 0 → 6 (0.04 % of 14,550 transmitted) | 0 → 549 | 0 → 451 |
| credit-retire wait mean / max, in flight max | 2.86 ms / 14.5 ms, 4 | 2.84 ms / 15.2 ms, 4 | 3.07 ms / 15.4 ms, 4 |
| completion latency (406 samples) | 25 under 1 ms, 70 in [1, 2), 76 in [2, 4), 144 in [4, 8), 91 in [8, 16), max 13.6 ms | 13, 72, 31, 95, 46 of 257 | 42, 78, 25, 199, 29 of 373 |
| echo legs | the first leg 892 of 893 (4.81 Mbit/s offered by the device tool's pacing); the second and third did not run to their summary, as in boot I | 893 of 893; two without summary | 0.9 % / 29 % / 54 % loss |
| in-chunk ping / at rest (ms min/avg/max) | 17.2 / 36.1 / 47.7 and 31.4 / 86.3 / 141.0 | 6.1 / 43.1 / 66.4 and 70.0 / 125.2 / 180.3 | 10.3 / 44.6 / 85.4 and 9.7 / 37.0 / 78.1 |

**Reading, against §20's table as predeclared: the second branch, and
the configuration fix that released the mechanism (owner, 2026-10-25).**
Transmit at 15.51–16.70 Mbit/s per chunk (aggregate 15.02) against boot
H run 3's 9.19–9.73 and boot I's 2.46–4.02, with `dropped_full=0`,
`tx_failed=0`, `expired=0`, `left_pages=0`, 406 of 406 sampled frames at
`0x4c` status 0 and six retransmissions in 14,550 segments: above 12 with
zero loss. Backpressure was never wrong; the queue bound was. The same
stop and wake sites with the hysteresis moved (stop near full at 56,
wake at half at 32) turned boot I's 2,223 cycles into 156 over the 29.2 s
data phase (at most 14 a second in the 11.3 s transmit phase), the queue
peaked at its stop mark (`high_water=56` of `bound=64`) and never at its
bound, and TCP's window opened (cwnd 58–95 against boot H's 6). The
retransmissions of boots H and I were part of the cost: the drain rate
boot H implied (800–1,000 frames a second) was the rate TCP allowed a
lossy path, not the driver's. Cross-session against boot I (+350 %) and
boot H run 3 (+68 % aggregate, ×1.7 per chunk), both outside the ±40 %
floor; every transmit chunk ended on its byte cap in about 2.1 s, so the
chunk rates are floors.

Not taken: the first branch (HT opens on transmit at about 9.3), the
third (stops in the hundreds), the fourth (retransmissions persisting)
and the fifth (no receive `device_timeout`, no non-zero payload; the
bound stays). HT/aggregation stays closed: its condition was written for
the drain rate confirmed at 9.3, and the pipeline, not the drain rate, is
now the bound.

**The saturation arithmetic, which now predicts.** With ordinary data
retired on credit arrival the transmit ceiling is the depth over the mean
credit-retire wait: 4 ÷ 2.864 ms = 1,397 frames a second, 16.2 Mbit/s at
1,448 bytes of TCP payload a frame, against 16.5 measured on the chunks'
final halves (15.2–16.6) and 1,285 frames a second over the whole phase
(14,550 in 11.32 s of device clock, 3.7 of 4 in flight on average). The
pipeline is saturated. The wait itself fell at the same depth: 3.48 ms on
boot E and 3.07 ms on boot H run 3 (frames freed unsent), 2.84 ms on boot
I and 2.86 ms on boot J (none freed), and the same 2.84–2.86 ms at 3.3
and at 15 Mbit/s, so it is the per-frame service time, not queueing in
the driver. The silent drops were inflating the credit wait: the earlier
"about 1.25 ms a frame" (rate ÷ depth on boots F and H) was a starved
pipe, not the service time (0.72 ms a frame at depth 4). From here the
forecast rule is depth ÷ `wait_avg`, read against the wait each boot
measures. Boot F's neutral depth-8 result (3.6 of 8 in flight, 4.47 ms)
was measured with frames freed unsent and does not carry to this tree.

**Stalls.** None: transmit chunks within 7 % of each other (15.51–16.70),
receive chunks within 6 % (18.54–19.62), all ended on the byte cap. No
entry for the §17 ledger.

**Which queue the acknowledgements take (from source, no boot; the
owner's receive-stall hypothesis).** Two kinds of acknowledgement are in
play and they answer differently.

- The 802.11 link-layer ACK is a control frame the MAC sends a SIFS after
  each received frame. It never reaches the host: mac80211 does not build
  it, the driver's `.tx` accepts only protected To-DS data, the two
  control-port EAPOL frames and an allowed management set (anything else
  is freed unsent), and its filter passes no control frames up. It does
  not share the data queue; that part of the hypothesis is dropped.
- The TCP acknowledgements the device sends while it receives are
  ordinary protected data frames, and they share everything with transmit
  data: the driver registers one mac80211 queue (`hw->queues = 1` with
  the station join), so all access categories are one queue; they enter
  the same `join_queue` under the same bound; the stop is
  `ieee80211_stop_queues()` on every queue at once; and they take the
  same four-frame in-flight window and the same credit retire. A stopped
  or full data queue therefore holds or (before backpressure) frees the
  receive path's acknowledgements, which is a mechanism by which a
  transmit-queue defect stalls the peer's sending.

The hypothesis stands on its second half: in this tree the receive
path's TCP acknowledgements have no path around the data queue. It is
consistent with the record (boot I's stall with a chattering
eight-frame queue; boot J's none with a deep one; the earlier stalls on
boots C, D and F, when a full eight-frame queue freed frames unsent,
acknowledgements included) and not proven: the data-end record counts
stops and drops for the whole data phase, not by direction, so no boot
yet shows a stop or a drop inside a stalled receive chunk. The structural
fix it points at is a path for acknowledgements and control that the
data queue cannot stop: a separate queue (or a separate traffic class,
as the vendor's four-queue resource model provides) for small frames and
pure TCP acknowledgements. That needs mac80211 queues beyond the one
registered (or a driver-side priority queue) and is not yet a proposal.
One further observation from the same read: the management and EAPOL
admission refuses any frame while the shared queue holds three or more,
so with a 64-frame data queue a management frame sent during a busy
data phase is freed unsent; no such frame is sent on this path today.

## 21. Boot K (predeclared, 2026-10-25): depth 8 on boot J's tree

**The change.** `CONFIG_MT6797_CCMP_TX_DEPTH=8` on boot J's tree (the
TC1 ledger derives to 104 pages, 0280), with the same 64-frame queue,
stop 56 and wake 32. One driver variable against boot J.

**The harness.** The chunk byte cap rises from 4 MiB to 16 MiB with the
3 s duration kept (plan, review record, the laptop's sender and the
device's `dd`). At 16.5 Mbit/s a chunk filled 4 MiB in 2.0 s, inside
the duration; at a predicted 32 Mbit/s it would fill in 1.05 s and at
the air limit in under 0.9 s, censoring again exactly where the change
is largest. At 16 MiB the duration binds below about 45 Mbit/s, so every
chunk measures steady state. Boot J's chunk rates were floors under the
old cap; boot K's are not, so the comparison reads boot K's chunks
against boot J's final halves.

**The expectation (depth ÷ `wait_avg`).** Read `wait_avg` first.

| `wait_avg` at depth 8 | forecast frames/s | forecast TX Mbit/s |
|---|---|---|
| 2.9 ms (unchanged) | 2,760 | 32 |
| 3.6 ms | 2,220 | 26 |
| 4.5 ms (boot F's) | 1,780 | 21 |
| 5.0 ms | 1,600 | 18.5 |

| Reading | Cause | Next |
|---|---|---|
| TX 26–32 Mbit/s with `wait_avg` near 2.9–3.6 ms, stops in boot J's order (hundreds, not thousands), `high_water` near 64, `dropped_full=0` | the depth was the bound; the pipeline scales | the rule holds; the air is the next limit to look for |
| TX below 26 with `wait_avg` risen toward 5 ms and the rule still matching | the firmware's per-frame service time grows with the frames it holds | a different answer: the firmware's per-frame path, not the host depth |
| TX far below the rule at the measured wait | something other than the window binds (the air, the queue's refill, the peer) | read `inflight_max`, the in-flight mean and the stops before anything else |
| TX above about 35 Mbit/s | the air at the fixed 54 Mbit/s rate becomes visible as a limit | the rate (54 Mbit/s) rather than the pipeline is the next question |
| `expired` > 0, `pid_faults` > 0, `left_pages` > 0 or `dropped_full` > 0 | the FIFO, the pool or the queue does not hold at this depth | revert to depth 4; read the credit lines |
| any receive `device_timeout` or non-zero payload | the depth starves the receive side | revert to depth 4, as boot B established |

Receive is expected unchanged or better. `inflight_max` must reach 8 or
the depth was not exercised.

**The receive stall: watched, not reproduced.** No boot is spent on a
reproduction. If no receive stall appears in boot K and the run after it,
both with the deep queue, the attribution is recorded as "consistent
with the shared-queue hypothesis, not proven". A stall that does appear
goes to the §17 ledger with its device-clock position and the stops and
drops beside it.

The three questions: reachability, the depth sizes the slot array and
the per-pass submission count and the ledger is admitted at HIF
activation on every boot; ownership, the host ledger's figures (104 of
the firmware's 468-page budget); the vendor, the same budget the vendor
allots this queue.

### Boot K result (2026-10-25, 18:10 UTC): transmit +27 % on the rule; the revert row fired on receive, confounded by the harness

Build `5a3e577d` (boot J's tree at depth 8, ledger 104), boot2
`5f5a187c…` over `5e19a3c6…`, mainline boot `7f208322…`, returned to
Gemian `4a464713…` (recovery confirmed, live identity checked
afterwards); session `ram-service-regression-pass`, log complete
(174,327 bytes), receipt `all_pass`, both directions complete, no early
stop; the controller's `session_exit=1` is the same exit as boots H
(run 3), I and J.

**TX first.** `tx_failed=0`, `retired=51117 expired=0 pid_faults=0
left_pages=0 inflight_max=8` (the depth was exercised), 811 samples with
811 reports all at `0/0x004c`; `stops=564 wakes=564 dropped_full=0
stopped=0 high_water=56 bound=64`. The zero-payload check passed.

| | Boot K (depth 8) | Boot J (depth 4) |
|---|---|---|
| TX chunks, whole / final half (Mbit/s) | 20.99, 20.89, 20.89, 20.87, 21.16 / 21.05, 20.68, 21.27, 21.12, 21.00 (all ended by the 3 s duration: steady state) | 15.51–16.70 / 15.22–16.64 (byte-capped at 4 MiB: floors) |
| TX aggregate | 19.87 | 15.02 |
| credit-retire wait mean / max, in flight max | 4.26 ms / 22.5 ms, 8 | 2.86 ms / 14.5 ms, 4 |
| rule (depth ÷ wait) / measured frames a second | 1,877 (21.7 Mbit/s) / 1,725 over the phase (27,531 in 15.96 s; 7.4 of 8 in flight) | 1,397 (16.2) / 1,285 |
| stops / wakes / `dropped_full`, high water | 564 / 564 / 0 over the 43.3 s data phase, 56 of 64 | 156 / 156 / 0, 56 of 64 |
| device TCP state per TX chunk (cwnd / ssthresh) | 110/46, 90/83, 118/99, 116/90, 110/58, retransmit queue 0 | 58–95 |
| `RetransSegs` across the TX phase | 0 → 4 | 0 → 6 |
| completion latency (811 samples) | 22 under 1 ms, 84 in [1, 2), 212 in [2, 4), 316 in [4, 8), 176 in [8, 16), 1 in [16, 32), max 16.2 ms | 25, 70, 76, 144, 91 of 406 |
| RX device-side chunks (Mbit/s) / ended by | 19.55, 19.80, 11.70, 19.41, 15.97 / `peer_eof`, `peer_eof`, **`device_timeout`**, `peer_eof`, **`device_timeout`** | 18.54–19.62 / all `byte_cap` |
| echo legs | the first leg 893 of 893 at 9.09 Mbit/s offered; the second and third without summary, as in boots I and J | 892 of 893 at 4.81 |
| in-chunk ping / at rest (ms min/avg/max) | 9.9 / 53.6 / 102.0 and 43.5 / 98.6 / 153.6 | 17.2 / 36.1 / 47.7 and 31.4 / 86.3 / 141.0 |

**Transmit, against §21: the second row.** 20.9–21.2 Mbit/s per chunk,
steady to 2 %, +27 % on boot J's chunks within the session (boot J's
were floors, so the gain is at most that) with zero loss and four
retransmissions. The wait rose from 2.86 to 4.26 ms (×1.49 for ×2 the
depth) and the rule, read at the measured wait, predicted 21.7 Mbit/s
against 21.0: the rule holds, and the forecast table's 4.5 ms row (21)
is where the boot landed. The pipeline is still saturated (7.4 of 8 in
flight), and the per-frame service time fell from 0.72 to 0.53 ms, so
holding more frames helps the firmware less than in proportion: the
second row's reading, the firmware's per-frame path rather than the host
depth, is the transmit limit's next question. Stops stayed in the
hundreds and the queue at its stop mark, as predicted. The air (above
about 35) is not yet visible.

**Receive: the revert row fired.** Two receive chunks ended on the
device's 4 s bound. The rule is applied as written: the lifecycle
fragment returns to depth 4. The attribution to the depth is not
established, because the harness changed in the same boot (a confound
the staging should have caught):

- With the 16 MiB cap, receive chunks are bound by the laptop's 3 s
  duration for the first time; before, they ended on the 4 MiB cap in
  about 1.8 s. The laptop writes at 23–26 Mbit/s into a send window of
  up to 1.8 MB with round trips of 300–370 ms, and the device keeps
  receiving that queue after the laptop's close: the three whole chunks
  ended on `peer_eof` 3.62–3.82 s after their start, 0.2–0.4 s inside
  the device's bound. The device's one-second margin was set for a
  transmit race (boot F) and is now raced by the receive drain.
- Chunk 5 (device clock 48.46–52.47 s, 8,006,568 bytes, 15.97 Mbit/s)
  is that race: about 0.96 MB the laptop had sent was still in flight
  when the bound fired.
- Chunk 3 (40.48–44.49 s, 5,865,848 bytes, 11.70 Mbit/s, against about
  9.7 MB sent) is the intermittent receive stall again, its fourth
  appearance; it would have stalled under any bound.

**Stall ledger (§17).** Receive chunk 3 of boot K, device clock 40.48 s
to 44.49 s, 5,865,848 bytes, ended on the device's bound; receive chunk 5,
48.46 s to 52.47 s, 8,006,568 bytes, a drain cut by the bound rather
than a stall. The stall appeared with the deep queue (high water 56,
nothing freed unsent), so §21's watch does not record the shared-queue
attribution as consistent: either the stall is not the data queue, or
the queue stopped inside the stalled chunk, which the whole-phase stop
counter cannot show.

**The transmit ceiling of the current design (owner, 2026-10-25; a
two-point fit).** Boots J and K fix the credit-retire wait as a line in
the depth: wait ≈ 1.465 ms + 0.350 ms × depth (2.864 ms at 4, 4.263 ms at
8). Throughput is depth ÷ wait, so it rises toward 1 ÷ 0.350 ms = 2,859
frames a second, 33.1 Mbit/s at 1,448 bytes of TCP payload a frame:

| depth | wait (model) | frames a second | TX Mbit/s |
|---|---|---|---|
| 4 | 2.86 ms | 1,397 | 16.2 (boot J: 16.5 final halves) |
| 8 | 4.26 ms | 1,877 | 21.7 (boot K: 21.0) |
| 12 | 5.66 ms | 2,119 | 24.6 |
| 16 | 7.06 ms | 2,266 | 26.2 |
| ∞ | — | 2,859 | 33.1 |

About 33 Mbit/s is also the order of the air ceiling at a fixed 54
Mbit/s rate once each frame's contention, preamble and acknowledgement
are paid (an estimate, not measured on this device): depth and air run
out in the same place, and nothing above about 33 Mbit/s is reachable in
this design without HT aggregation. That is the number at which HT stops
being a project and becomes the only option. The fit has two points and
no degrees of freedom; depth 12 is its test. (The owner's brief quoted
21.2 Mbit/s for depth 8; 8 ÷ 4.263 ms is 1,877 frames a second, 21.7 at
1,448 bytes, the same frame size that gives boot J's 16.2.)

**How a receive chunk ends.** `peer_eof`: the laptop stopped sending at
its 3 s duration and closed, and the device read end-of-stream after
draining what was still in flight (3.62–3.82 s on boot K): the normal
end of a duration-bound chunk. `device_timeout`: the device's own bound
(`timeout 4`, exit 143) fired before end-of-stream: a stall, or (boot K's
chunk 5) a drain longer than the one-second margin. `byte_cap`: the cap
was reached first (every chunk through boot J). Only `device_timeout`
can be a stall, and since boot K it is not always one.

**What would change the decision.** Separating the two causes needs the
device's receive bound past the drain (or the receive chunk ended by
bytes the laptop counts, not by the device's clock) and the stops and
drops split by direction; with those, depth 8 on the same image either
keeps its receive or shows the depth starving it. Not staged: the next
boot is the owner's decision.

**The revert re-read (owner, 2026-10-25).** Boot K's revert fired on a
receive artefact under a transmit change: the depth is a transmit
variable, the timeouts were on the receive path, and the safety counters
(`expired`, `pid_faults`, `left_pages`, `dropped_full`, `tx_failed`) were
all zero. The rule is amended: a timeout reverts a change on its own
path, or when the safety counters show loss. Depth 8 is restored.

## 22. Boot L (predeclared, 2026-10-25): depth 8 again, measured over the send window, with the queue's time series

**No driver variable.** Boot K's tree (depth 8, ledger 104, the 64-frame
queue) with three instruments and no behavioural change, so the boot
answers four questions at once: does transmit reproduce about 20.9 Mbit/s;
what is the clean receive rate with the drain excluded; was boot K's
receive chunk 3 a stall or a drain artefact; and does the queue ever stop
while the device receives. An acknowledgement-split boot is not staged
before those four answers exist: it would be a change aimed at a
mechanism the same boot can rule out.

**The receive bound and the drain.** The device's bound on both legs
moves from 4 s to 6 s for the 3 s send ([steady_state_chunks.py](hosts/steady_state_chunks.py)).
The owner asked for the device to time the laptop's close; it cannot: the
end of stream reaches it behind the very drain being measured. The
laptop's socket can, on one clock ([drain_accounting.py](hosts/drain_accounting.py)):
at the close it reads the bytes not yet acknowledged (`snd_sbbytes`),
so the bytes the device had acknowledged by the close are the sent bytes
less that backlog, and it polls until the backlog is empty (up to 2.5 s)
to time the drain. The receive chunk's rate is the acknowledged bytes over
the send window; the drain is recorded beside it with its bytes and
duration, never as a rate; the device's own count and exit stay in the
record. With the bound past any drain, `peer_eof` against
`device_timeout` stops being a proxy, and only a stall can leave a
shortfall. The acknowledged count trails the device's receipt by the
acknowledgement's own delay, so the rate is a slight underestimate, the
same in every chunk.

**The queue's time series and the receive gaps.** [0283](../../patches/proposals/0283-wifi-mt6797-record-a-per-second-backpressure-series-and-receive-gaps.patch)
(`CONFIG_MT6797_DATA_PHASE_SERIES`, logging only) prints, per second of
the data phase, the stops, the wakes, the queue's high-water mark, the
kilobytes delivered and the data frames queued, with the phase's start on
the kernel clock; the run's `TP1_<DIR>_START_NS` markers are on the same
clock and align it offline. The driver does not know the leaf's phases,
so it records time, not a phase split. It also records each gap of more
than 200 ms between delivered data frames (at most 32): its start, its
duration, the bytes delivered before it and in the 200 ms after it, the
data frames queued (the device's acknowledgements, in a receive chunk)
and retired during it, and the queue length, frames in flight, credit
pages and stop state when it ended. Gaps at chunk boundaries are expected
and are discarded by the alignment.

**The verdict.** Every steady-state run since boot H failed the verdict on
gates written for earlier protocols while its data was whole. The
throughput verdict ([throughput_verdict.py](hosts/throughput_verdict.py),
the same change in [classify-throughput.py](classify-throughput.py))
keeps the receipt, the verified boot, healthy cleanup, the key sequence,
no fault and the declared chunk count, and replaces the stale gates: no
native ciphertext reached the core with the counters monotone (for the
512-frame and 1 MiB ceilings of `counts_ok` and the 60 s GTK budget of
`gtk_counters_consistent`); each chunk inside the device's declared bound
plus 0.5 s (for the 1 s protocol's 1.5 s); and the credit-retire end
record as the ownership proof (nothing expired, no PID fault, no pages
left, no failed transmit) where ordinary data carries no PID (for the
depth-four PID trace). Read against boots J and K's records it passes
every gate but timing, which their receipts could not declare.

**The expectations.**

| Question | Expectation | If not |
|---|---|---|
| transmit | 20.9 Mbit/s ± noise at a wait near 4.26 ms, stops in the hundreds, `dropped_full=0` | a cross-boot difference larger than boot J to K's needs its own reading before anything else |
| clean receive rate | about 19.5 Mbit/s over the send window on every stall-free chunk, the drain 0.5–1 s and complete | a drain longer than 2.5 s is recorded incomplete and read as a stall |
| boot K's chunk 3 | no `device_timeout`; a shortfall appears only with a receive gap inside the chunk | a shortfall without a gap: the accounting is wrong, not the path |
| the queue during receive | **zero stops and zero wakes in every second of the receive phase**: the queue holds only the device's TCP acknowledgements, a few hundred a second against a bound of 64, so it can reach its stop mark only if the acknowledgement path stalls on its own | the acknowledgement split is justified, and the series and the gap records say where |

If the queue never stops during receive and a receive gap still appears,
the shared queue is excluded as the stall's cause with evidence, and the
gap record (acknowledgements queued and retired, in flight, pages)
names what the path was doing. If no stall appears in this run and the
next with the deep queue, the attribution is recorded as "consistent
with the shared-queue hypothesis, not proven".

The three questions: reachability, the series and the gaps are updated
at the same admission, wake and delivery sites the counters already use;
ownership, all of it is the host's own state, read and printed at the
data end; the vendor, no counterpart (logging only).

### Boot L result (2026-10-25, 18:37 UTC): the queue never stopped during receive; transmit did not reproduce; the acknowledgements lag

Build `7fddd16f` (boot K's tree at depth 8 with 0283), boot2 `c0f4a6f1…`
over `5f5a187c…`, mainline boot `176270e2…`, returned to Gemian
`9721fff5…` (recovery confirmed, live identity checked afterwards);
session `ram-service-regression-pass`, log complete (185,244 bytes),
receipt `all_pass`, both directions complete, no early stop. The
controller's `session_exit` is 0 for the first time in the steady-state
series: the amended verdict passed every gate (receipt, verified boot,
timing inside 6.5 s, healthy cleanup, no native ciphertext, key
sequence, no fault, credit-retire ownership).

**Alignment.** The series' start (`started_ns=14480161923`) plus the data
phase's 44,004 ms lands within 5 ms of the series line's own kernel
timestamp, and the leaf's markers are on the same clock: second 18
holds the change from transmit (ended 33.05 s) to receive (started
33.20 s), second 37 holds the receive end (52.30 s).

**The four answers.**

| Question | Expectation (§22) | Boot L |
|---|---|---|
| transmit | about 20.9 Mbit/s at a wait near 4.26 ms | **not reproduced**: chunks 17.25, 18.65, 18.72, 15.50, 17.38 (final halves 16.45–19.07), aggregate 16.15; wait 4.67 ms, 8 in flight at most, 6.6 on average (23,142 frames in 16.29 s); the rule at the measured wait predicts 19.9; `RetransSegs` 0 → 96 against boot K's 4, `dropped_full=0`, `tx_failed=0`, `expired=0`, 697 of 697 samples at `0x4c` status 0 |
| clean receive rate | about 19.5 Mbit/s over the send window, the drain 0.5–1 s and complete | device-side 19.63, 20.45, 16.80, 21.18, 21.11 Mbit/s; every drain complete (0.14–1.02 s), every chunk `peer_eof`, no `device_timeout` |
| boot K's chunk 3 | no `device_timeout`; a shortfall only with a receive gap | no timeout and no receive gap over 200 ms anywhere in the receive phase; chunk 3 is again the slow one (16.80 device-side over 4.08 s), as a dip in the per-second series (2,031 and 1,694 KiB in its first and last seconds against 2,400–2,970), not a silence |
| the queue during receive | zero stops and zero wakes in every receive second | **zero stops and zero wakes in all 18 whole receive seconds**, high water 9–30 against the stop mark of 56; the stops (94) are all in the transmit seconds and in the echo leg after receive (21 in second 40) |

**The acknowledgement split is excluded as the receive mechanism.** The
queue holds only the device's acknowledgements while it receives
(429–1,578 frames queued a second) and never reached its stop mark, so
data backpressure delayed no acknowledgement in this run. A separate
stop/wake domain for acknowledgements would have changed nothing here.

**The send-window rate measures the acknowledgements, not the receipt.**
Receive chunk 5: the laptop had 5,368,528 bytes acknowledged at its
close and 3,022,552 still unacknowledged, and the whole backlog was
acknowledged 142 ms later; the device counted all 8,391,080 bytes over
3.18 s. Three megabytes cannot cross the air in 142 ms, so most of the
backlog had already arrived and its acknowledgements had not yet reached
the laptop: about a second's worth of received data unacknowledged, then
acknowledged in one burst (an inference from the byte counts and the
air rate; no per-frame timing exists). Chunks 1, 2 and 4 drained at the
air's pace (1.5–1.9 MB over 0.57–0.85 s), chunk 3 likewise (2.66 MB over
1.02 s). So the owner's rate basis (bytes acknowledged by the close over
the send window: 20.28, 20.48, 15.74, 21.44, 14.31) reads the
acknowledgement path's lag as a receive shortfall; with every drain
complete and no timeout, the device's own count over its own span is
the clean receive rate. The lag is real and is not the driver's queue
(no stop, high water 10–30 at depth 8); where it accumulates (the
device's TCP, the in-flight window, or the uplink) this run cannot say.

**Transmit at depth 8 is a band, about 19 ± 2 Mbit/s (owner, 2026-10-25).**
Two boots with the same configuration and different waits gave boot
K's 20.87–21.16 per chunk at 4.26 ms and boot L's 15.50–18.72 (mean
17.5) at 4.67 ms. The record carries the band, not the better sample;
boot K's number stands as its upper sample. The model's prediction at
boot L's wait, 8 ÷ 4.67 ms = 1,713 frames a second or 19.8 Mbit/s, falls
inside the band, though boot L itself ran below it (6.6 of 8 in flight
on average), with 96 retransmissions where boot K had 4 and one
transmit-path stall: a 203 ms stretch from 27.41 s (transmit chunk 4,
the slowest at 15.50) with nothing arriving from the laptop while 8
frames were in flight and 29 queued, and only 9 retired against 45
queued. The pipeline stopped retiring, so the firmware or the air held
the frames. The completion latency shifted up (291 samples in [8, 16)
ms against 176) and the round trip at rest rose (64–172 ms against
43–154): a session difference, inside the ±40 % floor, with no driver
variable and nothing in the logging that costs more than a clock read
per frame.

**The intermittent receive stall is withdrawn (owner, 2026-10-25).**
Boot L ran the receive phase with the drain excluded and found no
receive silence: of the fifteen gaps over 200 ms the driver recorded,
four fall before the transmit phase (14.49–16.24 s, the data phase
opening) and ten after the receive phase (53.5–58.4 s, the echo legs and
the idle tail), all but one with an empty data path (queue 1, nothing in
flight, nothing queued or retired; the exception, 54.44 s, is inside the
second echo leg with 271 frames queued and 8 in flight), and one inside
the transmit window (the 203 ms transmit stall above); none falls inside
the receive window (33.20–52.30 s). The chunk shortfalls were two different things, and
neither is a receive-path stall:

- **The acknowledgement timing.** Chunk 5's shortfall (14.31 Mbit/s on
  the acknowledged bytes) is the split between in flight and
  acknowledged at the laptop's close: 3.02 MB unacknowledged, all of it
  acknowledged in 142 ms, which is a burst of delayed acknowledgements,
  not a wire rate. On the device's own count the chunk ran at 21.11.
- **The chunk boundary.** Chunk 3 (16.80 device-side over 4.08 s) is
  normal in its interior (the three whole seconds inside it: 2,776, 2,548
  and 2,381 KiB, 19.5–22.7 Mbit/s); its shortfall is in its first 0.39 s
  and its last 0.69 s, the new connection's start and the long drain,
  which together carried about 664 KiB.

So three boots attributed a chunk-boundary and acknowledgement-batching
effect to the receive path: boot I's chunk 3 (`device_timeout` at the
4 MiB cap), boot K's chunks 3 and 5 (on the device's 4 s bound with the
drain racing it) and the dips quoted since boot F. What made them
believable, kept so that neither belief returns: every one was a chunk
total read against a bound, with no record inside the chunk; the
device's bound sat one second past the laptop's duration, inside the
drain; and the rate basis mixed the laptop's view with the device's.
The earlier shortfalls on the device's own count (boot I's 3.78 MB in
4.01 s, boot K's 5.87 MB) were real slow chunks, but no record inside
them exists, so they name no mechanism and are not evidence of a
receive-path stall; boot L, the first run instrumented inside the
chunk, found no receive silence at all. The
acknowledgement-split hypothesis is withdrawn on the same evidence and
on boot L's series: zero stops in every receive second, high water at
most 30 against the stop mark of 56, and no receive gap at all.

**Measuring receive from now on (owner, 2026-10-25).** The device knows
when the bytes arrived; the laptop knows when they were acknowledged,
and the difference is the device's acknowledgement batching. The
primary receive rate is the device's received bytes over its own span
(the leaf's start and end markers, 10 ms resolution; the start includes
the connection's opening, about one round trip); the secondary is the
bytes acknowledged by the laptop's close over the send window, reported
as the TCP flow's view with the unacknowledged amount stated. Both are
reported per chunk and never averaged across the two bases. Boot L by
both: device 19.63, 20.45, 16.80, 21.18, 21.11; flow 20.28, 20.48, 15.74,
21.44, 14.31 (unacknowledged at the close 1.91, 1.57, 2.66, 1.49, 3.02 MB).

**The gap record, corrected before it is believed again.** Two defects
in 0283's receive gaps: `rx_bytes_before` was cumulative while
`rx_bytes_after` was a delta, so the pair could not be read as one
window; and gaps were recorded across the whole data phase, where idle
is expected. 0283 v2 logs both as deltas (the bytes in the 200–400 ms
before the gap, with that window's length, and in the 200 ms after it),
and the throughput record keeps only the gaps between a direction's
start and end markers, counting the others; the driver does not know
the leaf's phases, so the windowing is applied where the markers are.
A gap kept in the record is a stall by construction.

## 23. Boot M (predeclared, 2026-10-25): depth 12, once, then stop

**The change.** `CONFIG_MT6797_CCMP_TX_DEPTH=12` (the TC1 ledger derives
to 156 pages of the firmware's 468) on boot L's tree; everything else as
boot L (the 64-frame queue, the 16 MiB or 3 s chunks, the 6 s device
bound, the drain accounting, 0283's series with the gap record as v2,
the amended verdict). One variable against boot L.

**The expectation, from the two-point model.** wait ≈ 1.465 ms + 0.350
ms × 12 = 5.66 ms, so 12 ÷ 5.66 ms = 2,119 frames a second, 24.6 Mbit/s.
Read `wait_avg` first, and read transmit against the rule at the wait
the boot measures, since depth 8 gave 17.5 to 20.9 across two sessions:

| Reading | Cause | Next |
|---|---|---|
| `wait_avg` under the model (below about 5.4 ms) with transmit on the rule | the wait grows less than linearly; the asymptote is above 33 Mbit/s | one more depth step is worth considering |
| `wait_avg` near 5.66 ms, transmit near the rule | the model holds; the remaining depth gains are worth less than the session noise | depth is spent; the 54 Mbit/s air is the wall, and above it only HT |
| transmit well under the rule at the measured wait | the window is not what binds at this depth (the air, the firmware's queue) | read the in-flight mean, the transmit gaps and the latency before anything else |
| `expired`, `pid_faults`, `left_pages`, `dropped_full` or `tx_failed` non-zero | the pool or the queue does not hold at this depth | revert to depth 8 (the amended rule: safety counters show loss) |
| a transmit-path timeout | the depth fails on its own path | revert to depth 8 |

Receive is not this change's path: a receive timeout does not revert it
(the amended rule), and receive is read on the device's count with the
TCP flow's view beside it. `inflight_max` must reach 12 or the depth was
not exercised. After this boot the depth sweep stops whatever it shows,
except on the first row.

The three questions: reachability, the depth sizes the slot array and
the per-pass submission count, and the ledger is admitted at HIF
activation; ownership, 156 of the firmware's 468 pages, the host
ledger's own figures; the vendor, within the vendor's budget for the
queue.

### Boot M result (2026-10-25, 18:53 UTC): depth 12 on the model; the depth sweep stops; a receive slowdown the silence rule cannot see

Build `faea70e6` (boot L's tree at depth 12, ledger 156, 0283 v2),
boot2 `7a9a40e8…` over `c0f4a6f1…`, mainline boot `9baa00b0…`, returned
to Gemian `38cd7be3…` (recovery confirmed, live identity checked
afterwards); session `ram-service-regression-pass`, log complete
(184,282 bytes), receipt `all_pass`, verdict passed (`session_exit=0`),
no early stop.

**Transmit, against §23: the second row; the sweep stops.** Chunks
23.01, 22.91, 22.73, 22.85, 24.06 Mbit/s (final halves 22.44–24.63),
aggregate 21.87; `wait_avg` 5.459 ms with `inflight_max=12` (the depth
exercised) and 10.4 in flight on average (30,388 frames in 15.99 s);
`expired=0`, `pid_faults=0`, `left_pages=0`, `dropped_full=0`,
`tx_failed=0`, 836 of 836 samples at `0x4c` status 0, one retransmission
(cwnd 116–156). The wait came in 3.6 % under the model's 5.66 ms, short
of the first row's mark (5.4 ms); transmit ran 6 % under the model's
24.6 and 10 % under the rule at the measured wait (25.5). Within the
session noise the model holds: depth 4 → 8 → 12 gave 16.2, 19 ± 2 and
23 Mbit/s, the waits 2.86, 4.26–4.67 and 5.46 ms. A least-squares line
through the three depths (boots J, K and L averaged, M) gives wait ≈
1.67 ms + 0.324 ms × depth, an asymptote of 3,083 frames a second, 35.7
Mbit/s: the same wall as the two-point 33.1 within the depth-8 spread.
The remaining depth gains (about 1.5 Mbit/s from 12 to 16 on either
fit) are below the session noise, so the depth sweep stops here, as
predeclared; depth 12 stays in the lifecycle fragment (no safety counter
moved, no transmit timeout). Stops ran at about 45 a second in the
transmit seconds (693 in all), the queue at its stop mark, as at depth 8.

**Receive.** Device-side chunks 16.87, 20.13, 18.81, 19.01, 9.54 Mbit/s,
every chunk `peer_eof`, every drain complete (0.56–1.73 s), no timeout;
zero stops and wakes in all 20 whole receive seconds, high water 4–12;
no gap over 200 ms inside either measurement window (six outside). The
TCP flow's view (15.63, 17.42, 14.24, 15.02, 5.41, with 2.65–4.19 MB
unacknowledged at each close) trails the device's count in every chunk,
the acknowledgement lag boot L showed.

**A receive slowdown the silence rule cannot see.** Chunk 5 (51.17–55.22
s) ran at 9.54 Mbit/s on the device's own count, and the laptop itself
sent only 4.83 MB in its 3 s (12.9 Mbit/s against 22.9–26.8 in chunks
1–4): the sender slowed. The per-second series puts it in one second,
53.30–54.30 s, with 218 KiB delivered (1.8 Mbit/s) and 85 frames queued
for transmit, between seconds of 1,994 and 1,347 KiB; frames kept
arriving at intervals under 200 ms, so no gap was recorded. The data
queue held at most 12 frames and never stopped, so it is not the
acknowledgement path's queue, and the split stays withdrawn. It is a
real receive slowdown on the device's count, which boot L's withdrawal
of "the receive stall" did not cover: that withdrawal holds for
silences and for the chunk totals it re-read, not for this. The
sender's slowing is consistent with loss recovery on the laptop's side
(an inference: the laptop's own retransmissions are not recorded; the
device's netdev `rx_dropped` rose by 8 during the receive phase). The
silence rule misses a trickle; a per-second floor (for example a second
under a quarter of its chunk's median) would catch it.

**Stalls (§17).** Receive chunk 5 of boot M, the second at 53.30–54.30 s,
218 KiB, the sender at 12.9 Mbit/s over the chunk; no transmit stall.

**The air ceiling, corrected downward (owner, 2026-10-25).** At a fixed
54 Mbit/s a 1,518-byte frame costs about 386 µs of air once the
preamble, SIFS, the acknowledgement, DIFS and the average backoff are
paid (225 µs of payload; about 20, 16, 30, 34 and 68 µs of the rest),
so the air carries about 2,590 frames a second, about 30 Mbit/s of TCP
goodput, not the 33 the record carried. The three-depth fit's asymptote
(35.7) lies above it, so the air, not the window, is the wall. At 23
Mbit/s transmit runs at 77 % of the air ceiling; every further depth
step buys at most a few percent. That is the number that decides HT.

**Receive, read on the device's clock (correcting the owner's brief).**
The brief quoted "device-side final halves" of 29.3, 33.8, 28.1, 21.3
and 0 Mbit/s as the steady receive capacity. Those figures are the
laptop's: in the receive direction the laptop is the sender, and its
final half is the rate it wrote into its own socket, which runs ahead
of delivery while its send buffer fills. The device's own per-second
count, the only delivery measure inside a chunk, never reached them:
no whole receive second of boot M carried more than 2,857 KiB (23.4
Mbit/s), none of boot L's more than 2,972 (24.3). Slow start is
short against the 3 s window (the device's advertised window opens from
64 KB and the round trip starts near 7 ms). So receive stays quoted on
the device's count: 17–20 Mbit/s per chunk, up to about 23–24 in its
best whole seconds; UDP's 29 (boot D) is what the path carried without
TCP. The series row keeps the device's figure as primary.

**Boot M's chunk 5, re-read.** Not "the last two seconds empty": the two
seconds carried 218 KiB and then 1,347 KiB (the drain). The laptop
wrote nothing in its last 1.5 s (no final-half figure), and the device's
advertised window, at the last sample, was open at 2.18 MB; but the
laptop sampled the window only after a successful send, so the stall
itself has no samples. The driver delivered frames throughout. The
stream slowed with the link live; [§24](#24-boot-n-predeclared-2026-10-25-depth-16-and-the-receive-streams-state)
instruments the stream.

## 24. Boot N (predeclared, 2026-10-25): depth 16, and the receive stream's state

**The change.** `CONFIG_MT6797_CCMP_TX_DEPTH=16` (the TC1 ledger derives
to 208 of the firmware's 468 pages) on boot M's tree: one driver
variable, worth running only because it is one line. With it, the
receive stream's state is recorded on both ends
([receive_stream.py](hosts/receive_stream.py), no driver change): the
device's advertised window every 50 ms from the laptop's socket,
whatever the send did, with the chunk-relative time and the laptop's
unacknowledged backlog; the bytes waiting in the device's receive
socket (`rx_queue` from `/proc/net/tcp`) every 0.5 s; and the frames the
driver delivers, already in 0283's per-second series. Recorded, not
gated: the stream-stall check joins the receipt only once it can be
computed unambiguously.

**Transmit expectation.** The three-depth fit gives a wait of 1.668 +
0.324 × 16 = 6.86 ms, 2,332 frames a second, 27.0 Mbit/s; the two-point
model 26.2; the air ceiling about 30. Expect 25–26 Mbit/s, with the wait
read first:

| Reading | Cause | Next |
|---|---|---|
| transmit 25–26 at a wait near 6.9 ms | the window still binds, the air close behind | depth is finished; HT is the project |
| transmit flat near 23 with the wait rising past 7 ms | the air binds (frames wait for airtime, not for the window) | depth 12 is the setting; HT is the project |
| safety counters non-zero or a transmit timeout | the pool or the queue does not hold at 16 | revert to depth 12 |

**Receive: the stream's three readings.**

| Reading | Cause | Consequence |
|---|---|---|
| the device's window closes to zero while frames keep arriving | the receiving application (`nc` into `wc`) cannot consume at the arrival rate | a measurement artefact: drain faster or use a bigger receive buffer |
| the window stays open and the frames a second fall | the access point stopped sending to this station | a link event, and its own investigation |
| frames a second stay high but the socket's queue and the window do not move | the stack is not consuming what the driver delivers | ours, and worth a boot |

A chunk without a slowdown reads nothing; the readings apply only to a
second below a quarter of its chunk's median on the device's count.

The three questions: reachability, the depth sizes the slot array and
the per-pass submission count; ownership, 208 of the firmware's 468
pages; the vendor, within the vendor's budget for the queue. The stream
samples read only the device's own `/proc/net/tcp` and the laptop's
own socket.

### Boot N result (2026-10-25, 19:10 UTC): depth 16 is flat, the air binds; depth 12 is the setting; the receive stream read on both ends

Build `e13b2a90` (boot M's tree at depth 16, ledger 208, with the
receive stream's state), boot2 `95f81866…` over `7a9a40e8…`, mainline
boot `f81c66aa…`, returned to Gemian `a8d4e94f…` (recovery confirmed,
live identity checked afterwards); session `ram-service-regression-pass`,
log complete (183,989 bytes), both directions complete, no early stop.
The receipt read `all_pass=false` on one field: the transmit
direction's pipeline exit was 141, its last chunk's normal close when
the laptop ends the chunk first, which the per-chunk rule has accepted
since boot H and the direction-level rule did not (earlier runs' last
transmit chunks happened to exit 0). The data is whole; the
direction-level rule now accepts the same transmit closes
([steady_state_chunks.py](hosts/steady_state_chunks.py)). Every other
verdict gate passed.

**Transmit, against §24: the second row.** Chunks 23.33, 23.44, 23.36,
23.77, 23.24 Mbit/s (final halves 23.32–24.21), aggregate 22.20; wait
6.571 ms with `inflight_max=16`, 12.7 in flight on average (30,793
frames in 15.98 s, 1,927 a second against boot M's 1,900); nothing
expired, faulted, left or freed unsent, `tx_failed=0`, 857 of 857
samples at `0x4c` status 0, three retransmissions. A third more depth
and a fifth more wait gave 1.4 % more frames: the extra frames wait for
airtime, not for the window. The rule at the measured wait (28.2) is no
longer what binds; the air is: 1,927 data frames a second at about 386
µs each fill about 74 % of every second before the laptop's own
acknowledgements on the same channel. Transmit on the legacy rate has
reached its wall at about 23.5 Mbit/s (78 % of the 30 Mbit/s ceiling).
Depth 12 is the setting; the fragment returns to it. Depth is finished;
HT is the project ([scope](HT_PROJECT_SCOPE.md)).

**Receive.** Device-side chunks 20.10, 17.73, 20.47, 15.39, 20.97 Mbit/s,
every chunk `peer_eof`, every drain complete (0.54–1.87 s), no timeout;
zero stops in all 20 receive seconds (high water 9–16). The stream on
both ends, against §24's readings:

- **The receiving application.** The device's socket held 847,824 bytes
  unread at one 0.5 s sample of chunk 2 and 1,927,384 at one of chunk 5,
  zero at every other sample: `nc` into `wc` falls behind at moments.
  The advertised window never closed (its least, after opening, was 2.1
  MB), so the application's lag did not throttle the stream: the first
  reading does not apply.
- **The link.** Chunk 4 (45.18–50.12 s, 15.39 Mbit/s, the slow one)
  holds the only two receive gaps inside a measurement window: 368 ms
  from 49.41 s (550 KB in the 219 ms before it, 66 bytes in the 200 ms
  after) and 271 ms from 49.78 s, both in the chunk's drain after the
  laptop's close, with the device's socket empty, nothing in flight on
  the device, the queue at 1 and the advertised window open at 6.7 MB.
  Frames stopped arriving with the window open and the device idle: the
  second reading, a link-side event. Whether the access point held the
  frames or the laptop stopped sending (its retransmission timer with
  4.19 MB unacknowledged at the close) the record cannot tell: the
  laptop's own retransmissions are not sampled.
- **The stack.** No sample shows the driver delivering while the socket
  queue and the window stand still: the third reading does not occur.

The receive slowdowns are link-side and in the drain, not the driver's
and not the application's. The next instrument, if it is wanted, is the
laptop's retransmitted bytes from the same socket samples.

**Stalls (§17).** Receive chunk 4 of boot N, 49.41–50.05 s, two silences
(368 and 271 ms) in the drain, window open, socket empty.

**The owner's reading of boot N (2026-10-25).** The depth sweep ends
here. Against depth 12, depth 16 gave 1.7 % more transmit for a third
more frames in flight; depth 12 is the best value, and the transmit
design's ceiling on the fixed 54 Mbit/s rate is about 23.4 Mbit/s, 78 %
of the air's 30. No further host-side depth, queue or accounting change
can move it: the air binds, and only a faster or aggregated PHY (HT)
does.

**The receive final half, withdrawn.** Boot N's receive "final halves"
include 49.4 Mbit/s, which a legacy 54 Mbit/s association cannot
carry: the figure is the laptop's write rate into its own socket, which
runs in bursts as delayed acknowledgements free its buffer, not a
delivery rate. The reading of boot M's 28–34 Mbit/s as receive capacity
is withdrawn with it (the record had already declined to adopt it). The
receive record keeps the figure only as `host_write_final_half_Mbit_s`.
Receive is quoted as the device's whole-window rate, about 19 Mbit/s
delivered over TCP; the path's capacity of about 30 Mbit/s stands on the
UDP probe alone (boot D). A device-side final half would need the
leaf's progress inside a chunk, and the device command has 18 bytes of
its 4,096 left; 0283's per-second series is the device-side figure
inside a chunk.

**The verdict, named.** Boot N's `session_exit=1` came from one receipt
field, the transmit direction's pipeline exit (fixed, above). Every gate
the verdict applies now reads the run's own declarations (the device
bound for timing, the credit-retire record for ownership; the sample
ceilings, the 1 s chunk bound and the PID trace are no longer gates),
and a failed verdict names itself: the receipt lists the checks that
cleared `all_pass` and the verdict lists the failed gates with their
phase (`verdict_failed`). Re-run on boot N's record it reads
`classifier:receipt_all_pass` (its receipt predates the list). The
receipt's own checks (quiescence, the core disconnect, completeness,
chunk exits, the netdev counters) are data-path checks and stay gates;
`byte_cap_reached`, `duration_pass` and `connected_lifetime_trial_pass`
are retained fields that gate nothing.

**HT needs WMM: the host-only probe cannot leave the data path alone
(from source, 2026-10-25).** The cheapest decisive experiment the owner
proposed (advertise HT, carry the HT capability element in the
association, change nothing on the data path) cannot be built on
mac80211: `ieee80211_determine_our_sta_mode` limits a station to legacy
when WMM is not in use ("WMM/QoS not supported, limiting to legacy"),
and WMM needs at least four hardware queues and a `conf_tx` operation;
the driver registers one queue and no `conf_tx`. With WMM in use,
mac80211 sends QoS data (subtype 8, a 26-byte header with the QoS
control field), which the transmit admission refuses (it accepts
non-QoS protected data, 0x4108, only), and the association admission
refuses the WMM element as well as the HT capability. So the smallest
HT association is HT advertisement, WMM (four queues, `conf_tx`, the
element admitted) and QoS data in the transmit admission and its
Ethernet II conversion together: [the scope](HT_PROJECT_SCOPE.md) is
re-ordered accordingly. Whether the access point speaks HT to this
device is already answered by the vendor's own driver: 45.1 Mbit/s of
transmit through the same access point (vendor control 2) is above the
legacy ceiling and needs HT.

## 25. Boot O (predeclared, 2026-10-25): WMM and QoS data at the legacy rate, a de-risking step whose success is that nothing moves

**Why.** Every route past the 30 Mbit/s legacy air needs QoS data with
TIDs: A-MPDU requires it and block-ack is per TID, and mac80211
negotiates HT only with WMM. The driver refused WMM by design (the
association admission refused its element; one queue; non-QoS data
with TID 0 fixed). This boot carries WMM and QoS data at a rate that
already works, so the framing's risks are isolated from the rate change
that follows. **It has no throughput expectation**: without an HT
capability mac80211 starts no block-ack session, and
`ampdu_action` refuses one anyway, so QoS framing alone changes nothing
measurable. Any throughput move is a warning, not a win: it would mean
something else changed with the framing.

**The change, one variable.**
[0284](../../patches/proposals/0284-wifi-mt6797-negotiate-WMM-and-carry-data-as-QoS-data-at-the-legacy-rate.patch)
(`CONFIG_MT6797_WMM_QOS_DATA`) on boot M's tree (depth 12, the 64-frame
queue, 0283):

- four mac80211 queues, a `conf_tx` operation (the access point's EDCA
  parameters recorded; no WMM parameter command, so the firmware keeps
  its defaults), `ampdu_action` refusing block-ack;
- the association admits one WMM information element with QoS info 0
  (no U-APSD); when the access point answers with its WMM parameter
  element the BSS info declares `ucIsQBSS` (byte 42) and the station
  record `ucIsQoS` (byte 18), as the vendor does for a WMM access point;
- transmit: QoS data with QoS control 0 (TID 0, AC_BE, the TC1 queue the
  descriptor already names) and the control-port EAPOL frames with their
  own TID, converted to Ethernet II from the 26-byte header; QoS data
  with any other TID is refused and counted; the descriptor, the fixed
  0x4c rate, the ledger and the depth are unchanged;
- receive: QoS data with QoS control 0, and QoS EAPOL-Key on both the
  translated and the native layout, with the 26-byte header rebuilt for
  mac80211.

**Where the risks actually sit (from source).** The owner's brief placed
the CCMP AAD of the 26-byte header on the host. It is not there: the
host hands the firmware Ethernet II and receives decrypted, translated
802.3, so the firmware builds the 802.11 header and computes the AAD on
both paths. The host's risks are admission and framing; the AAD is the
firmware's, triggered by the station record's QoS declaration. A third
risk the brief did not name: with WMM the access point is likely to
send the four-way handshake's EAPOL-Key frames as QoS data, which the
EAPOL gate refused; 0284 admits them, and the handshake is the first
thing this boot tests.

**Success is "nothing moved".**

| Reading | Required |
|---|---|
| WMM | `join WMM: requested=1 accepted=1`; four `WMM params` lines (one per access category) |
| join, both lifetimes, ledger | unchanged: the handshake completes, `expired=0`, `pid_faults=0`, `left_pages=0`, `dropped_full=0`, `tx_failed=0` |
| framing | `data qos:` `tx_qos` carries the data and `tx_nonqos` near 0, `tx_tid_refused=0`; `rx_qos` carries the receive, `rx_refused_qos=0` |
| TX per chunk | about 23 Mbit/s (depth 12's band), five full-duration chunks |
| RX device-side | about 19 Mbit/s |
| rate samples | 697–857 sampled reports, all at `0x4c` status 0 |
| CCMP | no decrypt or replay failure on either path: no receive refusals beyond boot M's background, no transmit stall with the air acknowledging |
| frame counts | delivered ≈ received, no unexplained drops |
| verdict | `session_exit=0`; if not, `verdict_failed` names the check |

**The failure modes, named in advance.**

| Reading | Cause | Next |
|---|---|---|
| the join stops at the handshake, the EAPOL trace reads `frame-control`, `native-layout` or `llc` | the access point's QoS EAPOL-Key in a shape the gate does not take | read the trace's descriptor bytes; nothing else changed |
| `requested=1 accepted=0`, `tx_qos=0` | the access point ignored our WMM element or answered without its parameters; mac80211 stays non-QoS | the association record shows whether the element was carried; the boot is a no-op, not a failure |
| `rx_refused_qos` climbing with `rx_qos=0` | the firmware's receive descriptor for QoS data differs from the non-QoS shape the check fixes, or the firmware's decryption of QoS frames fails (the AAD on receive) | read one refused descriptor; the check, not the key |
| transmit stalls (TCP retransmitting, chunks near zero) while the sampled reports read status 0 | the air acknowledges our QoS frames but the access point discards them: the firmware's AAD for the QoS header on transmit | revert the station record's `ucIsQoS` first (the transmit framing follows it) |
| `tx_tid_refused` > 0 | mac80211 classified ordinary data off TID 0 | the classification, not the path; data on other TIDs is the next step's work |

The three questions: reachability, the same admission, conversion and
receive-check sites the non-QoS path uses, and the BSS and station
records already sent after association; ownership, the QoS declaration
is the host's own record fields; the vendor, `ucIsQoS`/`ucIsQBSS` set
for a WMM access point and QoS data with TID 0 in TC1 (public gen3
`CMD_UPDATE_STA_RECORD_T`/`CMD_SET_BSS_INFO`).

**After it, each one boot.** HT capability advertisement (the 54 Mbit/s
descriptor kept, the received-rate record read for HT modes: does this
access point send HT to this station); then the station record's PHY
and MCS fields so the firmware can transmit at MCS; then block-ack and
A-MPDU, where the throughput appears ([scope](HT_PROJECT_SCOPE.md)).

**Housekeeping already done.** The verdict reads the run's declarations
and names its failures (`verdict_failed`), and the transmit direction's
normal 141 close is accepted (boot N); the receive final half is out of
the record as a delivery figure (`host_write_final_half_Mbit_s` only).

### Boot O result (2026-10-25, 19:38 UTC): the access point accepted WMM; the four-way handshake timed out; the kernel record was lost; 0284 reverted

Build `1882d5d3` (0284 on boot M's tree), boot2 `8c813def…` over boot
N's `95f81866…`, mainline boot `00ad695e…`; the owner restarted the
device by hand into Gemian `27f35470…` (live identity checked). The
boot is **void for the measurement and a failure on its own path**: no
data phase was reached.

**What the retained evidence shows (the supplicant's own log and the
leaf's progress, laptop side).** The association carried our WMM
element and the access point answered with its parameters (the
supplicant: "Valid WMM association, WMM AC is enabled", U-APSD queues
0). The supplicant then waited for EAPOL-Key message 1 and received
none; ten seconds after the association the access point
deauthenticated the station with reason 15 (4WAY_HANDSHAKE_TIMEOUT).
The leaf waited for its one record for the rest of the run's 300 s wall
clock and the run ended on it (exit 124).

**What it does not show.** The kernel record, which holds the EAPOL
gate's trace for every EAPOL-shaped frame (`EAPOL admission: ...
verdict=... predicate=...`), was not exported: the session refuses to
seal the log while the owned supplicant is still alive
("owned supplicant not confirmed quiesced (supplicant_processes=1);
refusing seal and recovery"), and the reviewed preservation and return
refused on the same post-session quiescence proof (exit 62), as they
are designed to; nothing kills a device process. The owner restarted
the device; the ramoops console did not survive (the read-only pstore
capture from Gemian found no entries). So three causes cannot be
separated:

- the access point's message 1 arrived as QoS data in a shape the new
  EAPOL gate refused (on the translated or the native layout);
- the firmware did not deliver it once the station record declared QoS
  (or delivered it where the receive path does not look);
- the access point did not send it.

**Against §25: the first named failure mode.** The handshake stopped,
nothing else changed; the rule applies: a change that fails on its own
path reverts. The lifecycle fragment drops `CONFIG_MT6797_WMM_QOS_DATA`
(boot M's tree again, depth 12); 0284 stays a proposal. The WMM half is
answered: this access point accepts our WMM element and returns its
parameters.

**The harness gap this exposed.** A join that fails leaves the
supplicant alive, and with it alive neither the session's seal nor the
reviewed return proceeds: the evidence that explains a failed join is
exactly the evidence that is lost. Before another join-path change is
booted, either the leaf must end its own supplicant when the join fails
(so the quiescence proof passes and the seal and return run), or the
kernel record must be exported on a path that does not need it. That is
a change to the reviewed preservation tooling and is the owner's call.

**Separating the causes, when the gap is closed.** The cheapest
discriminating boot keeps WMM and the QoS EAPOL gate but leaves the
station record and BSS info non-QoS (`ucIsQoS`/`ucIsQBSS` 0): if the
handshake then completes, the firmware's QoS declaration was what
stopped message 1; if it still times out, the gate's trace names the
refused shape.

**The gap closed (owner-reviewed, 2026-10-25).**
[join_failure_exit.py](hosts/join_failure_exit.py) adds one literal
replacement to prepare's leaf derivation: while the leaf waits for the
data phase's record, and only then, the wait ends at once when the
supplicant's own log shows the join has ended (a deauthentication or
disconnection notification, or auto-connect disabled; in boots L, M and
N these appear only after the connection, at the lifetime's end), or
after 90 s without the data phase. The cycle then breaks as any
data-phase fault does, the leaf quiesces its supplicant and exits, the
host seals the kernel record and the reviewed return runs. Tested
offline ([join-failure-exit-test.py](tests/join-failure-exit-test.py));
the seal and the return on a real failed join remain to be shown by the
next boot that fails one. Every staged boot from here applies it.

**The positive result, stated plainly (owner, 2026-10-25).** This access
point negotiates WMM with this station: it accepted our WMM information
element and returned its EDCA parameter set in the association response.
That is the first HT prerequisite confirmed, independent of the
handshake's failure; WMM is required for 802.11n, so in practice the
access point is 11n-capable (an inference, consistent with the vendor
driver's 45.1 Mbit/s through it).

**Why ramoops did not survive.** The layout was not the cause: boot O's
live device tree carries `ramoops@44410000` (`0xe0000`, records
`0x1000`, console `0x10000`, ftrace `0x1000`, pmsg `0x20000`), which puts
the console zone at `[0x444bf000, 0x444cf000)`, exactly Gemian's primary
console zone, the cross-version layout the
[Gemian baseline](../../docs/hardware/gemini-gemian-baseline.md#exact-active-ramoops-layout)
records. The reset path was: Gemian came up with `boot_reason=0` and
`androidboot.bootreason=power_key`, a cold power-on. Retention is
established only across warm resets; the owner's power-key restart was
the only way out of a hung session, and it destroys the console it was
meant to read. So the kernel record must leave the device over USB
before any restart, and a warm path (the reviewed native reboot) keeps
the ramoops copy as a second line.

**The evidence gap, closed in two layers.** The leaf ends a failed
join's data-phase wait itself ([join_failure_exit.py](hosts/join_failure_exit.py)).
Behind it, [failure_preservation.py](hosts/failure_preservation.py):

- in the session, when the C2 wrapper refuses on quiescence, the owned
  supplicant is stopped (every `wpa_supplicant`, TERM, then KILL after
  5 s, the sets before and after recorded), the C2 supplicant count and
  the leaf's quiescence record are re-run under new labels, and either
  both pass and the C2 cycles export and the reviewed seal proceed to
  the reviewed return, or the kernel record is exported through the
  reviewed seal script, kept privately, and the return refused as
  before;
- in the watcher's preservation and return, the owned processes its
  proof names (`wpa_supplicant`, `nc`, `dhcpcd`, `udhcpc`) are stopped
  the same way and the sealed log exported whatever their state; the
  quiescence proof is then required before the native reboot.

The RAM-wiping reboot still needs quiescence; the export no longer does.
Tested offline ([failure-preservation-test.py](tests/failure-preservation-test.py))
and the stop script against real processes on Linux (a plain process
stopped by TERM, one ignoring TERM stopped by KILL at 5.6 s, an
unrelated process left running).

**The receive path for a QoS EAPOL-Key, read from source (owner's
item).** 0284's gate admits the AP's clear EAPOL-Key as QoS data on
both layouts as written: the translated layout with the QoS frame
control from group 4, its QoS control copied into a rebuilt 34-byte
header for mac80211 (A-MSDU refused); the native layout with the
descriptor's header length 26 and the LLC at 26, passed through as
received. So the source does not refuse the 26-byte layout as such, and
does not exclude any of boot O's three causes on its own: the gate
still fixes descriptor fields measured only on non-QoS frames (format
byte 1, MSDU format 0, the translated header length 14, the padding
flag) and the BSS tag (15 before the BSS command completes, 1 after the
station activation), any of which can refuse a QoS frame, and in the
stable-epoch receive path a refused pre-key frame is traced and skipped,
not fatal, which is exactly boot O's silence. The existing trace (every
pre-key data descriptor up to 64, verdict and predicate) held the
answer; 0284 v2 adds the header it read.

## 26. Boot P (predeclared, 2026-10-25): the discriminating boot, WMM on and the records non-QoS, instrumented

**The change, one variable against boot O.**
[0284 v2](../../patches/proposals/0284-wifi-mt6797-negotiate-WMM-and-carry-data-as-QoS-data-at-the-legacy-rate.patch):
`CONFIG_MT6797_WMM_QOS_DATA=y` with `CONFIG_MT6797_WMM_QOS_RECORDS`
off: WMM negotiated and the host's QoS admission as in boot O, the BSS
info and the station record left non-QoS (`ucIsQBSS`, `ucIsQoS` 0), as
in every working boot. The instrument: for every pre-key data frame the
gate examines, an `EAPOL header:` line with the verdict and refusing
predicate, the descriptor's header-length field, the frame control, the
QoS control, the EtherType and the BSS tag; the candidate recognizer
also knows the native 26-byte layout. No fix rides along: the boot
names the cause, and its fix is its own single change.

**The reading.**

| Observation | Cause | Next |
|---|---|---|
| an EAPOL-Key (`ethertype=0x888e`) arrives as QoS (QoS frame control, or `hl=26`) and is refused, the predicate named | the gate does not take that layout or field | admit it as its own change, records still non-QoS, and re-run |
| it arrives (QoS or not) and is admitted, and the handshake completes | with the records non-QoS the downlink works: in boot O the records' QoS declaration stopped message 1 in the firmware | the records' declaration is the next question, its own boot |
| it arrives and is admitted, and the handshake still fails | message 1 got through; the failure is later, our message 2 as QoS data on the uplink or the AP refusing it | the uplink QoS EAPOL framing gets the record |
| no EAPOL-shaped frame in the trace at all | message 1 never reached the host even with the records non-QoS | the firmware's receive under WMM, or the access point not sending; not the gate |

The owner's brief read the last row as "the AP never sent it because
our EAPOL-Key reply was rejected"; message 1 comes before any reply, so
a missing message 1 cannot be caused by our message 2.

If the handshake completes, the rest of §25's "nothing moved" table
applies (transmit about 23, receive about 19, the samples at `0x4c`
status 0, no refusals, the verdict green). Either way the kernel record
now reaches the laptop: on a failed join through the leaf's exit and
the seal, and behind it through the session's stop or export and the
watcher's export-before-proof.

### Boot P result (2026-10-25, 20:30 UTC): the access point sends EAPOL-Key on TID 6; the gate refused it at descriptor byte 9; the evidence survived

Build `c65b5937` (0284 v2, WMM on, records non-QoS), boot2 `48bec39b…`
over boot O's `8c813def…`, mainline boot `7e90a7c2…`, returned to Gemian
`86417b2f…` by the session's own reviewed return (recovery confirmed,
live identity checked afterwards); session `ram-service-regression-pass`,
log complete through the seal (174,307 bytes). The verdict was red, as a
failed join must be, and named itself: no received bytes, no core
disconnect, and the classifier gates that follow from them.

**The cause, as the trace states it.** The association carried WMM
(`requested=1 accepted=1 records_qos=0`, four parameter sets). The access
point then sent EAPOL-Key message 1 four times (trace ordinals 1, 3, 14
and 22), each a QoS data frame on TID 6 (AC_VO) that the firmware
translated to Ethernet: `translated=1 hl=14 fc=0x0288 qos=0x0006
ethertype=0x888e bss=1`. Every descriptor field matches the non-WMM
baseline's message 1 (boots L and N: format `0xce`, byte 8 `0x01`,
prefix `0xc000`, 147 bytes) except one: descriptor byte 9 read `0x06`
where the baseline reads `0x00`, and the gate refused all four at it
(`predicate=rxd-byte9`, the check that byte 9 is zero). Byte 9 carries
the frame's TID in its low nibble (it equals the QoS TID on all four;
its high nibble is the cipher, `0x40` for the CCMP data the data path
admits). The other 19 traced frames were protected non-QoS data refused
at byte 4 (`fc=0x4208`/`0x6208`), not the handshake. The supplicant
received nothing and the join ended.

**Boot O's three causes, attributed.** Boot O ran the same gate on the
same access point, so its silent handshake was this refusal: the AP sent
message 1, the firmware delivered it, the gate refused it at byte 9. The
records' QoS declaration (boot O's other difference) is not implicated.

**The evidence fix worked.** The join failed and the kernel record
survived with the trace intact: the leaf saw the supplicant's end of
join 5 s into its data-phase wait (`join_failure_exit reason=supplicant`),
quiesced its supplicant (count 0, quiescence record clean), the session
sealed the log and ran the reviewed return. The session's second layer
(stop, re-check, or export before refusing) was not needed.

**Against §26: the first row.** The EAPOL-Key arrives as QoS and is
refused, the predicate named; next, admit it as its own change, the
records still non-QoS, and re-run.

**The measurement freeze for the HT chain (owner, 2026-10-25).** From
boot Q, the fix of boot P, the instrument is frozen until the HT chain
is complete: the chunk protocol (5 chunks each way, 16 MiB or 3 s, the
device bound 6 s, the drain recorded to 2.5 s), the verdict's gates
(throughput_verdict.py as of `c65b5937`, with the transmit close rule),
the receive basis (the device's count primary, the TCP flow beside it),
the receive-gap windows (inside each direction's markers), the receive
stream and per-second series as recorded, and the two failure-
preservation layers. Any change to these is a freeze break: named,
approved by the owner and recorded before the boot that carries it.

## 27. Boot Q (predeclared, 2026-10-25): the QoS EAPOL-Key admitted, our EAPOL on TID 6, records still non-QoS

**The change.** Three proposals on boot P's tree, the records still
non-QoS:

- [0286](../../patches/proposals/0286-wifi-mt6797-admit-the-access-point-s-QoS-EAPOL-Key-whatever-its-TID.patch):
  with WMM the EAPOL gate admits any TID in descriptor byte 9's low
  nibble, on both layouts, and keeps the cipher nibble required zero for
  a clear EAPOL-Key; the delivery line records the admitted TID. Every
  other predicate is unchanged; the protected frames refused at byte 4
  stay refused, so the record shows how narrow the widening is.
- [0287](../../patches/proposals/0287-wifi-mt6797-send-the-control-port-s-EAPOL-on-TID-6-with-WMM.patch):
  our own EAPOL frames carry TID 6 (AC_VO) in the security descriptor
  (byte 6, bits 4-6), the TID the access point uses. **The queue,
  confirmed from source:** the descriptor names its queue explicitly in
  byte 3 (`0x88`: the MCU port, TC4, the pool the ledger already
  provisions for security frames; public gen3 `TX_DESC_QUEUE_INDEX` bits
  3-6 and `TX_DESC_PORT_INDEX` bit 7), so the TID does not select the
  queue and a TID 6 submission cannot vanish into an unprovisioned
  traffic class; nothing was rerouted or provisioned. Note: the vendor's
  security-frame path redirects these frames to TID 0
  (`nicTxComposeSecurityFrameDesc`), and with the station record
  non-QoS the firmware builds a non-QoS header, so on this boot the TID
  is unlikely to reach the air at all.
- [0285](../../patches/proposals/0285-wifi-mt6797-never-skip-a-refused-pre-key-frame-without-a-record.patch)
  (logging only): a refused pre-key frame always leaves a record, with
  refusals on their own bound of 64 and the header line independent of
  configuration.

**Success is a completed four-way handshake and nothing else moved.**

| Reading | Required |
|---|---|
| handshake | the AP's EAPOL-Key admitted (`join eapol delivered: ... tid=6`), the four messages in the supplicant's phrase counts, keys installed |
| association, lifetimes, ledger | unchanged: `requested=1 accepted=1 records_qos=0`, `expired=0`, `pid_faults=0`, `left_pages=0`, `dropped_full=0`, `tx_failed=0` |
| rate | the sampled reports all at `0x4c` status 0 |
| TX / RX | about 23 Mbit/s per chunk / about 19 device-side |
| refusals | only the protected frames at byte 4, no `rxd-byte9` |
| verdict | `session_exit=0`, or `verdict_failed` naming the check |

| Reading | Cause | Next |
|---|---|---|
| the handshake completes and nothing else moved | the gate was the downlink's only obstacle | boot R: the records' QoS declaration, its own variable |
| the AP's EAPOL-Key is admitted but the handshake stops after message 2 | our message 2 (TID 6, non-QoS records) is not accepted by the access point | revert 0287 (the vendor's TID 0) as its own change before anything else |
| a refusal at another predicate | a second field differs for QoS frames | named by 0285's record; admit it as its own change |

After boot R, HT capability advertisement is the next step.

### Boot Q result (2026-10-25, 20:43 UTC): the four-way handshake completes under WMM; DHCP then failed, the access point's QoS replies refused at the receive check

Build `65679190` (0285-0287, records non-QoS), boot2 `13703a41…` over
boot P's `48bec39b…`, mainline boot `c7f9b018…`, returned to Gemian
`8afdfec0…` by the session's own reviewed return (recovery confirmed,
live identity checked afterwards); log complete through the seal
(184,711 bytes); verdict red and named (no received bytes, no core
disconnect, timing).

**The handshake: §27's first goal met.** The access point's EAPOL-Key
arrived on TID 6 as in boot P; the first message 1 was refused at
`bss-interval` (the BSS-tag timing rule, exactly as on the non-WMM
baseline), and messages 1 and 3 were then admitted and delivered
(`join eapol delivered: ... tid=6`); no frame was refused at byte 9; the
only other refusals were protected frames at byte 4. The supplicant
logged each of the four messages once, installed the PTK and the GTK,
completed the key negotiation and connected: our messages 2 and 4 (TID 6
in the descriptor, TC4, non-QoS records) were accepted by the access
point. The association and the ledger were unchanged
(`requested=1 accepted=1 records_qos=0`; `expired=0`, `pid_faults=0`,
`left_pages=0`, `dropped_full=0`, `tx_failed=0`).

**Then DHCP failed and the leaf ended the lifetime.** The data phase
opened (12.5 s, then the leaf's own disconnect, reason 3 locally
generated): `dhcp_exit=1 dhcp_bound=0`, the data checks failed, and no
measurement ran. The QoS counters: `tx_qos=4 tx_nonqos=0` (four DHCP
discovers, carried by mac80211 as QoS data and converted), `rx_qos=0
rx_nonqos=40 rx_refused=45 rx_refused_qos=4`. Four QoS frames came back
and all four were refused by the CCMP receive check, none delivered: the
access point's DHCP replies, one per discover (an inference from the
counts; the post-key receive check records no per-frame refusal, 0285
covers the pre-key gate only). The check fixes descriptor byte 9 at
`0x40` (the cipher and TID 0) and the QoS control at 0, so a reply on any
TID other than 0 is refused by construction: the same class of field as
boot P's EAPOL refusal, on the data path.

**Against §27.** The handshake row is met; nothing else could be read
because no data flowed. The next change must name the data path's
refusing field before it is widened: a per-frame record for the CCMP
receive check's refusals (the predicate, frame control, QoS control and
descriptor byte 9), logging only, the way 0285 does for the pre-key gate.
The likely fix after it is the data-path counterpart of 0286 (byte 9's
low nibble and the QoS control's TID admitted, the cipher still
required CCMP), each its own boot; boot R (the records' QoS declaration)
waits behind them.

**Boot Q's target met, in the owner's terms (2026-10-25).** `wmm_requested=1
wmm_accepted=1 ac_params=8`; the EAPOL-Key admitted on both messages
(`qos=0x0006 ethertype=0x888e`, the body valid); the pairwise and group
keys installed; `tx_qos=4 tx_nonqos=0 tx_tid_refused=0`, which also
settles the queue question: QoS uplink frames reach the provisioned
queue and none are refused. The handshake defect of boot O is closed.
The DHCP failure is the downlink QoS data admission, not the handshake:
the access point sends data as QoS because WMM is negotiated, and no QoS
data frame was delivered (`rx_qos=0`) while 40 non-QoS frames were.
One correction to the counts: 0284 took `rx_refused` before the group
check ran, so the 45 includes group frames that check then delivered;
`rx_qos=0` still shows that all four QoS frames were refused by both
checks. 0288 counts a refusal only when both have refused.

## 28. Boot R (predeclared, 2026-10-25): QoS data admitted at the receive checks, one variable

**The change.**
[0289](../../patches/proposals/0289-wifi-mt6797-admit-QoS-data-on-any-TID-at-the-receive-checks.patch):
with WMM, both the pairwise and the group receive check admit a QoS data
frame on any TID whose QoS control holds only that TID (normal
acknowledgment, no A-MSDU, no EOSP) and agrees with descriptor byte 9's
low nibble; the cipher nibble is still required CCMP; non-QoS frames keep
TID 0. The firmware decrypts and translates the frame to Ethernet, which
the host delivers as before: the translated layout is the only one the
firmware delivers for data, QoS or not, so a native QoS data frame stays
refused and named. The records' QoS declaration stays off; the 0x4c
descriptor, the depth (12) and the ledger are untouched. Riding along,
logging only:
[0288](../../patches/proposals/0288-wifi-mt6797-name-every-data-frame-both-receive-checks-refuse.patch)
names every frame both checks refuse (the first 64 of a lifetime): the
descriptor bytes and group set, the frame control, QoS control and HT
control, the PN's order against the receive context, and the first field
that differs; refusals are counted only when both checks refuse. The
owner's rule: a refusal that is not named has already cost three boots.
The C fixtures for both checks pass unchanged (the non-WMM path,
sanitizers on).

| Reading | Required |
|---|---|
| `rx_qos > 0` and `rx_refused_qos` → 0 | the admission is the change, and it worked |
| DHCP binds, `cycles_completed=1` | the data path is restored |
| TX about 23, RX about 19, rate `0x4c`, ledger exact | nothing else moved |
| `rx_refused` beside `rx_qos`, every refusal named (`data rx refused: field=...`) | what is still refused, and why |
| any MIC or decrypt failure | the 26-byte AAD (the firmware's, on the receive side), and stop |

| Reading | Cause | Next |
|---|---|---|
| QoS frames refused at `field=pn` | the access point's PNs arrive out of order across TIDs; the receive context keeps one strict counter for all of them | a per-TID replay counter, its own change |
| QoS frames refused at another field | a second difference for QoS data | named by 0288; its own change |
| DHCP binds and the measurement runs | the downlink is restored at the legacy rate | boot S: the records' QoS declaration, then HT capability |

**After it, the chain as scoped.** The station record's QoS declaration
(firmware side) as its own variable, then HT capability advertisement,
then the station record's PHY and MCS fields, then block-ack.

### Boot R result (2026-10-25, 20:55 UTC): QoS receive admission works and DHCP binds; two named blockers, and the measurement's SSH never connected

Build `1af78599` (0288, 0289, records non-QoS), boot2 `45c802cd…` over
boot Q's `13703a41…`, mainline boot `c747596b…`, returned to Gemian
`bcd86356…` by the watcher's reviewed preservation and return (recovery
confirmed); kernel log complete through the seal (216,421 bytes). The
session refused its export and seal, so no graded receipt was written
(the seal gap, below).

**§28's target met.** `rx_qos=22 rx_refused_qos=0`: no QoS frame was
refused. DHCP bound at the leaf (`dhcp_exit=0 dhcp_bound=1
dhcp_prefix=24 lease_written=1`), dropbear was ready and three pings went
out and came back. The data phase ran 291.8 s and ended on the leaf's
disconnect: `tx_queued=14 tx_done=14 tx_failed=0`, `rx_delivered=1165`,
ledger exact (`expired=0 pid_faults=0 left_pages=0 dropped_full=0`),
association unchanged (`requested=1 accepted=1 records_qos=0`), no MIC
or decrypt failure. The measurement did not run: the laptop's SSH over
Wi-Fi never connected (`connect to host ... port 22: Operation timed
out`, exit 255, no byte).

**Two blockers, both named.**

1. *Transmit:* `tx_tid_refused=19` against `tx_qos=14`. 0284 refused any
   QoS control other than 0 and only counted it, so these frames are not
   named individually. Mainline's RFC 8325 mapping puts AF21 on TID 3
   and CS3 on TID 4, for example, and a refusal of anything mac80211
   classified off TID 0 fits pings passing while SSH did not. That is a
   fit, not a measurement.
2. *Receive:* 15 frames refused by both checks (0288), all on the
   broadcast entry (`wlan=2`). 14 at `field=prefix`: status `0xc200`,
   142 bytes, `p4=0x48 p6=0xce p9=0x40`, group-4 frame control
   `0x6208` or `0x4208` (non-QoS data, FromDS, Protected, More Data on
   ten), `pn=greater`. One at `field=packet-type` (`0xe004`, 442 bytes:
   not a data descriptor). No receive refusal was QoS.

**The `0xc200` decode (the owner's, checked against the pinned source).**
In the pinned gen3 `nic_rx.h` (`59e00a91`), descriptor bytes 10–11 are
`u2StatusFlag`. Bit 9 is `RX_STATUS_LLC_MIS`, and bits 14 and 15 are
`RX_STATUS_AMPDU_SUB_FRAME` and `RX_STATUS_AMPDU_FORMAT`, so
`0xc200 = 0xc000 | LLC_MIS`. The descriptor bytes give broadcast match
with key id 1, a translated 14-byte header with the 2-byte offset, TID 0
and CCMP. This is the group LLC-mismatch class that `data-rx.h` already
decodes from runtime 30, there with the type word `0x002e`.

**One correction: these are not the DHCP replies.** Three readings
disagree:

- DHCP bound in this boot.
- Each frame is 142 bytes: a 16-byte base, 64 bytes of groups 1–4 and the
  2-byte offset leave 60 bytes. That is a 14-byte header and 46 bytes,
  the size of a minimum Ethernet frame. A DHCP reply carries at least
  300 bytes of BOOTP.
- The class's earlier record carried `0x002e` in the type word, an 802.3
  length of 46 rather than an EtherType: an 802.2 LLC frame that the
  hardware could not translate to Ethernet II.

The pinned vendor data path also drops a frame with this bit as an error
(`nic_rx.c`: `RXS_DW2_RX_nERR_BITMAP` `0x07F8` covers bit 9; it logs
`LLC_MIS_ERR` and drops). Its receive path never reads
`RX_STATUS_ETH_TYPE_OFFSET`. Boot S therefore discards the class as the
vendor does, naming each frame's type or length word, rather than
admitting it. If that word comes back at `0x0600` or above (an
EtherType), this inference is wrong and admission is the next boot's
change.

**The packet numbers (security).** The group check keeps one strict
counter and admits a frame only when its PN is greater. `pn=greater`
means each of the 14 would have advanced that counter: they are not
replays, so nothing about them needs a replay check relaxed. Discarding
them leaves the counter unchanged. The per-TID concern is real on the
pairwise side. A receiver keeps one replay counter per TID because a
transmitter's frames on different TIDs can be reordered against each
other, while the pairwise check keeps one counter for all TIDs. That
would appear as `field=pn pn=lower` on unicast QoS frames; boot R has
none. If it appears, a per-TID pairwise counter is its own change, named
as security-relevant: each TID stays strictly ordered, and no PN at or
below that TID's last is ever accepted.

**The vendor's transmit routing (`nic_tx.h`, `nic_tx.c`, `que_mgt.c`
at `59e00a91`).**

- `NET_TC_NON_STAREC_NON_QOS_INDEX` exists ("BMC/non-associated
  frame"). In station mode, however, `qmDetermineStaRecIndex` sends every
  frame, group destinations included, through the access point's station
  record. `STA_REC_INDEX_BMCAST` and its TC5 are for IBSS and
  access-point operation.
- With a QoS station record, the TC follows the TID's access category
  (`aucTid2ACI`; `arNetwork2TcResource`: BE→TC1, BK→TC0, VI→TC2,
  VO→TC3). With a non-QoS record, one TID-0 template on TC5 serves every
  TID.
- `nicTxFillMsduInfo` moves DHCP and ARP to UP 6 (VO) at the lowest
  fixed rate.

Our record is non-QoS, so the descriptor's TID 0 already matches the
vendor. We stay on TC1, the queue of every earlier boot: moving to TC5 is
a resource-pool change and its own variable.

**The seal gap, diagnosed and fixed (host).** The halt did satisfy the
device's quiescence (the watcher's owned-stop found only the supplicant,
then nothing). The refusal came from the laptop's helper, in two layers:

1. *A crash in the boot N naming loop.* The failure-naming loop that
   `throughput_verdict.py` added for boot N evaluates
   `direction['bytes'] > 0`. With no measurement, receive `bytes` is
   `None`, so the helper raised `TypeError` after the USB remote-owner
   scan had already run. Its catch-all then wrote "helper exception;
   remote ownership not confirmed" over that result. The retained gate
   short-circuits; the naming loop did not. The loop is now total over a
   measurement that never ran.
2. *A check that could not pass.* Without the device's `TP1_OWNER_PID`,
   the helper forces the owner scan to fail (`owners=1`), because it
   cannot check the owner's process group. A connection that never
   opened never prints that PID. `unreached_stream.py` lets the tagged
   scan stand unmodified only when the retained SSH observation proves
   the TCP connect failed: exit 255, no timeout, no stdout, and stderr
   exactly one `ssh: connect to host ... port 22:` failure line. The
   record names the case (`ssh_unreached`). Any other missing PID still
   fails.

Against boot R's retained observation the predicate is true; against
boots K–N, whose SSH connected, it is false. Tests:
`tests/unreached-stream-test.py`.

## 29. Boot S (predeclared, 2026-10-25): the data path under WMM, two admissions, every refusal named

**The changes, one declared boot (the owner's order).**

- [0290](../../patches/proposals/0290-wifi-mt6797-discard-the-group-LLC-mismatch-class-as-the-vendor-does-and-name-status-bits.patch)
  (receive): the CCMP path recognises the group LLC-mismatch class with
  the existing `data-rx.h` decoder and discards it as the vendor does.
  It is never delivered, the group PN is unchanged, and the first eight
  are named with the type or length word (`join data LLC mismatch
  discarded: ... type=`). Every refusal record also names the status
  bits that differ from `0xc000` (`status=llc-mis`, and so on).
- [0291](../../patches/proposals/0291-wifi-mt6797-transmit-QoS-data-on-any-TID-each-refusal-named.patch)
  (transmit): QoS data is admitted on any TID 0–7 with normal
  acknowledgment, no A-MSDU and no EOSP, and counted per TID
  (`tx_tid=`). The descriptor stays TID 0 on TC1, the vendor's non-QoS
  template. Any other QoS control is refused, counted and named
  (`data tx refused: tid= ac= qos= group= type= tos=`).
- Host, failure handling only: `unreached_stream.py` and the total
  naming loop. The measurement protocol is unchanged (the HT-chain
  freeze).
- Unchanged: the records non-QoS, depth 12, rate `0x4c`, the ledger.
  No replay check is relaxed.

| Reading | Required |
|---|---|
| `tx_tid_refused=0`, `tx_tid=` showing the TIDs in use | the transmit admission is the change |
| `rx_refused` 0 apart from named non-data descriptors; `rx_llc_mis` equal to the former `0xc200` refusals, each with `type=` | the receive class is named and handled as the vendor does |
| DHCP binds, the measurement's SSH connects, `cycles_completed=1`, a graded `ccmp-session-result.json` | the data path is restored and measured |
| no throughput expectation; ledger exact; no MIC or decrypt failure; `pn=` refusals none | nothing else moved |

| Reading | Cause | Next |
|---|---|---|
| `type=` at `0x0600` or above on the discarded class | they carry an EtherType: §28's inference wrong | admit the class, its own change |
| `field=pn pn=lower` on unicast QoS frames | the AP's TIDs reorder against one pairwise counter | a per-TID pairwise replay counter, its own named security change |
| `data tx refused` with a non-zero ack policy or another bit | a second transmit difference | named; its own change |
| SSH still unreached with both counters at 0 | the cause is not the admissions | the receipt now grades it; the next diagnostic reads the device's own TCP view |
| the measurement runs | the data path under WMM at the legacy rate | boot T: the station record's QoS declaration, which brings the TID into the descriptor and the TC by access category (the vendor's QoS template) |

### Boot S result (2026-10-25, 21:32 UTC): the data path under WMM is restored and measured; both predictions held; the per-TID replay branch opened

Build `349f8165` (0290, 0291, records non-QoS), boot2 `f7cdcf2f…` over
boot R's `45c802cd…`, mainline boot `dfe35b8e…`, returned to Gemian
`566c4f7e…` by the session's own reviewed return (live identity checked
afterwards); log complete through the seal (197,281 bytes). The first
graded receipt of the HT chain: `session_exit=0`, `all_pass=True`,
`verdict_failed=[]`, `throughput_baseline_pass=True`, the core disconnect
accepted. The seal-gap fixes were not exercised (the SSH connected).

**§29's admissions.**

- *Transmit:* `tx_tid_refused=0`, `tx_qos=48784`,
  `tx_tid=48581/0/0/203/0/0/0/0`. mac80211 used TID 0 and TID 3. TID 3
  is AF21, the marking on the measurement's SSH control session, so a
  refusal of anything off TID 0 is what stopped boot R's SSH. That
  refusal is now measured, not only fitted.
- *Receive:* `rx_qos=38884 rx_nonqos=145`. `rx_llc_mis=2`, both
  `type=0x002e bytes=46 fc=0x6208 keyid=1`: an 802.3 length, not an
  EtherType. §28's inference held: these are 802.2 LLC frames, not DHCP,
  and discarding them as the vendor does lost nothing. DHCP bound, the
  pings were answered, the measurement's SSH connected and
  `cycles_completed=1`.
- *Ledger exact:* `expired=0 pid_faults=0 left_pages=0
  dropped_full=0 tx_failed=0`, every sampled report at `0x4c`, no MIC or
  decrypt failure.

**The open row: `field=pn pn=lower`, 12 unicast frames (§29's second
branch): a per-TID packet-number mismatch, a correctness defect.**

All 12 came on the pairwise entry (`wlan=1`) with status `0xc000`
(`status=none`) and CCMP:

- ten on TID 0 (`qos=0x0000`, `fc=0x4288`, 1,524–1,596 bytes, three of
  them with Retry: `fc=0x4a88`);
- two on TID 5 (`qos=0x0005`, `p9=0x45`, 148 bytes).

CCMP keeps a PN per TID, while the driver kept one counter across all
TIDs. Once TID 3 and TID 5 carried traffic, a TID 0 frame below the
counter they had advanced looked like a replay. Under WMM that
predicate drops legitimate frames and holds the anti-replay invariant in
the wrong shape. 12 of 38,896 unicast frames is not a throughput limit,
but each costs a TCP retransmission. Under HT these TIDs become the
population where A-MPDU sub-frames and block-ack sessions appear, all
of them per TID.

The fix is
[0292](../../patches/proposals/0292-wifi-mt6797-keep-one-CCMP-replay-counter-per-TID.patch),
its own change, predeclared as security-relevant in §30.

**Throughput: WMM cost no measurable throughput.**

- *Transmit:* 17.17 Mbit/s over five chunks (22.6, 18.9, 16.3, 15.0,
  19.6). The variance is one fixed-rate TCP congestion episode, not the
  QoS framing. The device's own TCP state places it in chunk 3
  (`cwnd 84 ssthresh 64`, against 128/102 in chunk 1 and 187/107 in
  chunk 2), and the device's retransmissions rose from 1 to 7 across the
  transmit direction. The driver dropped nothing (`dropped_full=0`,
  `tx_failed=0`), and the firmware side held boot M's pace (credit-retire
  wait 5.37 ms against 5.46, 12 in flight). The chunks either side of the
  episode run at boot M's level: chunk 1 at 22.6 with final half 23.6,
  and chunk 5's final half 23.7, against boot M's 22.7–24.1.
- *Receive:* 17.64 Mbit/s (chunks 14.6–21.2), within boot M's 16.9–20.1
  at the same depth.

The QoS framing is therefore not a suspect in later comparisons; a
transmit dip is read against the TCP state first.

**The vendor's status masks beside ours (`nic_rx.h`, `59e00a91`).**

| Mask | Value | Rule |
|---|---|---|
| `RXS_DW2_RX_nERR_BITMAP` | `0x07F8` | bits 3–10 must be zero; contains `RX_STATUS_LLC_MIS` (bit 9), so the vendor drops this class |
| `RXS_DW2_AMPDU_nERR_BITMAP` | `0xFFBF` | all bits except bit 6 must be zero: a frame inside a block-ack session |
| `RXS_DW2_RX_nDATA_BITMAP` | `0x3000` | must equal `0x2000` for a non-data frame |
| ours | `== 0xc000` | exact |

Our predicate is stricter than any single vendor mask: it requires
both A-MPDU bits set and every other bit clear. That suits a station
without block-ack. Once HT frames arrive with other status bits set,
each one is refused and named (0290's `status=`), not silently
admitted. Widening the predicate then follows the vendor masks bit by
bit, never wholesale.

**The rate codes, from source.** `wlan_def.h` (`59e00a91`, lines 51–98):
`TX_MODE_OFDM 0x40`, `TX_MODE_HT_MM 0x80`, OFDM codes 6M `0xB`, 9M `0xF`,
12M `0xA`, 18M `0xE`, 24M `0x9`, 36M `0xD`, 48M `0x8`, 54M `0xC`, MCS7
`0x7`. So `0x4b` is 6 Mbit/s, `0x4c` is 54 Mbit/s and `0x87` is HT MCS7,
as the records have said. Boot S's downlink histogram (mode 1, OFDM)
decodes as 54 M ×38,446, 48 M ×429, 6 M ×145, 36 M ×5, 24 M ×4.

**Against §29.** Rows 1–3 met; row 4 met except the `pn=` refusals,
which are §30's change. Boot S met its purpose: the WMM data path works
(`tx_qos=48784 tx_nonqos=0 tx_tid_refused=0`, `rx_qos=38884`, DHCP, SSH,
the full five-chunk measurement, a clean verdict). Three confirmations:

- TID 3 carried 203 frames, which explains boot R's SSH failure;
- the LLC-mismatch frames are 46-byte 802.3 length frames
  (`type=0x002e`), and discarding them was right;
- the transmit variance is a TCP congestion episode, not the QoS framing.

## 30. Boot T (predeclared, 2026-10-25): one CCMP replay counter per TID, a security-relevant change

**The change.**
[0292](../../patches/proposals/0292-wifi-mt6797-keep-one-CCMP-replay-counter-per-TID.patch)
is security-relevant and declared as such. Both the pairwise and the
group context keep eight replay counters, indexed from descriptor byte
9's TID nibble (`ucTidSecMode` bits 0–3), the same per-TID keying as the
vendor's receive state (`aucRxBaTable[ucTID]`, `CFG_RX_MAX_BA_TID_NUM 8`)
and mac80211's `rx_pn[tid]`.

- TID 0's counter is the existing field; a non-QoS data frame shares it,
  as in mac80211. TIDs 1–7 are new.
- A frame is checked against its own TID's counter and advances only that
  one.
- Each counter is seeded at key installation from mac80211's receive
  sequence for that TID, and cleared with the context exactly where the
  single counter was.
- *Not relaxed:* every counter stays strict, and nothing at or below a
  TID's last PN is accepted. A QoS TID of 8 or more (TSPEC, never
  negotiated) is now refused.
- The refusal record names the frame's TID and the counter that refused
  it (`tid= counter=pairwise|group`).

New offline fixture `tests/ccmp-tid-pn-test.c` (ASan and UBSan): boot S's
case is admitted (TID 3 ahead, then a TID 0 frame above its own counter).
Equal and lower PNs are refused on the same TID, non-QoS frames share
TID 0, and TSPEC TIDs and a QoS/descriptor TID disagreement are refused,
in both contexts. The frozen PTK and GTK fixtures pass unchanged.

**Riding along, host and not graded: the probe's dead legs.** Since boot
H, `transmit_probe.py` has replaced the device's UDP trigger with the
echo legs. The laptop's trigger thread still waited for three connections
that never came (`completed: false`, `udp: []`, every run). The 20 and
30 Mbit/s echo legs ended early with no summary in boots M, N and S
(stderr discarded). Both are removed: the trigger is created with no
rates (its laptop pings remain), and the record says `udp_legs:
retired`. The 10 Mbit/s echo leg, which has recorded zero loss every
time, stays, and now keeps its own error line. The device command
shrinks by about 21 bytes against its 4,096-byte bound. Boot S rendered
4,091 bytes at the longest laptop address, a 5-byte margin, so the stage
now renders the command before installing and refuses above the bound.

Unchanged: WMM data, the records non-QoS, depth 12, rate `0x4c`, the
ledger, the measurement protocol.

| Reading | Required |
|---|---|
| no `field=pn pn=lower` on unicast QoS frames; `rx_refused_qos` → 0 | per-TID counters are the fix |
| any remaining `pn=` refusal names its TID and counter, and is `equal` or a Retry frame | a genuine duplicate, refused as it must be |
| DHCP, SSH, five chunks, a clean verdict; ledger exact; no MIC failure | nothing else moved |
| TCP retransmissions (`tcp_retrans_segs`) at or below boot S's 6 | one cause of retransmission removed (recorded, not graded) |

| Reading | Cause | Next |
|---|---|---|
| `pn=lower` on a TID without Retry | the access point reorders within one TID, or the seed is wrong | read the seed and the record before anything else |
| refusals at a new field or status bit | another layout difference | named; its own change |
| clean | the anti-replay invariant now has the per-TID shape HT needs | HT, the cheap route first (HT scope) |

### Boot T result (2026-10-25, 21:53 UTC): per-TID replay counters remove every receive refusal; the anti-replay invariant has the shape HT needs

Build `42307a6a` (0292 and the probe repair, records non-QoS), boot2
`c7f650a8…` over boot S's `f7cdcf2f…`, mainline boot `efaa1099…`,
returned to Gemian `bafaa65c…` by the session's own reviewed return
(live identity checked afterwards); log complete through the seal
(187,451 bytes). Graded receipt: `session_exit=0`, `all_pass=True`,
`verdict_failed=[]`, the core disconnect accepted. The device command
rendered at 4,074 of 4,096 bytes.

**§30's change: met.**

- `rx_refused=0 rx_refused_qos=0`, with `rx_qos=42198 rx_nonqos=186`.
  No frame was refused at any field, so not one `pn=` refusal remains,
  genuine duplicate or otherwise. Boot S's twelve were the single counter
  across TIDs.
- Transmit: `tx_tid_refused=0`, `tx_tid=49528/0/0/168/0/0/0/1` (TID 3
  for the SSH control session, one frame on TID 7).
- `rx_llc_mis=0`: no LLC-mismatch frame this run.
- Ledger exact (`expired=0 pid_faults=0 left_pages=0 dropped_full=0
  tx_failed=0`), retire wait 5.53 ms, 12 in flight, every sampled report
  at `0x4c`, no MIC or decrypt failure.

**Throughput (recorded; no expectation declared).**

- *Transmit:* 20.86 Mbit/s with every chunk at 21.7–22.3, a steadier run
  than boot S's 15.0–22.6, close to boot M's 22.7–24.1.
- *Receive:* 16.38 Mbit/s, chunks 18.7, 10.4, 20.0, 18.8, 20.0. The
  chunk-2 dip had no receive refusal and an empty device receive queue,
  and the laptop's own send rate fell with it (17.2 against 22.9–24.2 on
  the other chunks). The flow slowed at the sender, not at a drop in this
  driver. A single-chunk dip of this size is in boot M's record too
  (chunk 5 at 9.5).
- *§30's recorded row, not met:* device TCP retransmissions went from 0
  to 9 across the transmit direction, against boot S's 1 to 7. The
  per-TID counters removed the receive refusals, not the transmit
  direction's own retransmissions. That is the air, recorded and not
  graded.

**The probe.** The UDP legs are recorded as retired, and the laptop's
trigger thread now completes (`completed: true`). The one echo leg
delivered 892 of 893 at 4.8 Mbit/s offered: the device took 2.07 s
to pace 893 requests, against 1.08 s in boot S, so this run's leg ran at
half its nominal rate. That is recorded as a probe reading, not as
transmit capacity.

**Boot T completes the WMM/QoS step (owner, 2026-10-25).** Across 49,697
transmit and 42,198 receive QoS frames: `rx_refused=0 rx_refused_qos=0
rx_llc_mis=0 tx_tid_refused=0`, with TIDs 0, 3 and 7 exercised.
Transmit ran 21.71–22.26 per chunk (aggregate 20.86) against boot S's
15.0–22.6 (17.17). Across boots S and T the QoS framing is cleared: with
the same framing, transmit returned to boot M's level, so the framing was
never the cause.

**What boot S's transmit variance was not: the PN drops.** The proposed
attribution, that boot S's transmit variance was the twelve per-TID PN
drops and their TCP consequences, does not survive the timing.

- On the device's clock, boot S's transmit direction ran 17.24–33.51 s
  and its receive direction 33.54–53.43 s.
- The twelve refusals are stamped 34.59–55.39 s: every one fell after
  the transmit direction had ended, ten of them in the receive
  direction's data frames.
- They cost receive retransmissions, not the transmit dip.

Boot S's transmit dip was a congestion episode of its own (chunk 3:
`cwnd 84 ssthresh 64`). Boot T's steadier transmit is the same
fixed-rate link on another run, not the PN change.

**The residual loss source, and the fixed-rate trade.** Nothing is
refused any more, yet boot T's transmit direction retransmitted 9
segments, and `ssthresh` fell to 24 in chunk 4. At a fixed 54 Mbit/s
there is no rate adaptation: a dip in the channel costs frames at that
rate, and TCP backs off. That is the standing trade of the fixed-rate
decision (0273), and it bounds both directions' variance.

A fixed HT MCS trades less margin for more air time: MCS7 needs a
cleaner channel than 54 Mbit/s OFDM. So the HT steps should predict
more loss exposure, not less, unless rate adaptation comes with them.

**Against §30.** The change is met: the per-TID counters are the fix,
and nothing at or below a TID's last PN is accepted. The anti-replay
invariant now has the per-TID shape that block-ack needs. Next, per the
owner's sequence, is HT on the cheap route (HT scope): HT capability
advertised with WMM, the fixed `0x4c` descriptor and the records kept,
and the receive rate record read for HT modes, watching the receive
refusals for a change of shape.

## 31. Boot U (predeclared, 2026-10-25): HT capability advertised, the descriptor unchanged

**The change.**
[0293](../../patches/proposals/0293-wifi-mt6797-advertise-HT-on-5-GHz-with-the-data-rate-still-fixed.patch)
(`MT6797_HT_CAPABILITY`, set in the lifecycle fragment) is the cheap HT
entry, capabilities only.

- *Advertised on 5 GHz:* HT20, one stream, MCS 0–7. No short guard
  interval, greenfield, STBC, LDPC or 40 MHz. The smallest A-MPDU window
  (8 KiB, 8 µs spacing), SM power save disabled.
- *Admission:* the association request admits exactly that HT
  capability element (mac80211 sets the SM power save bits itself), and
  the join channel is admitted at HT20 as well as 20 MHz non-HT. Before
  0293 the admission refused any HT element and any HT width.
- *Recorded:* `join HT: requested= accepted=`, accepted when the
  response carries the access point's HT operation element.
- *Unchanged:* the fixed `0x4c` data descriptor, the station record's
  legacy PHY, the records non-QoS, depth 12, the ledger, the measurement
  protocol. Block-ack stays refused: `ampdu_action` returns
  `-EOPNOTSUPP`, so mac80211 declines any ADDBA request, and the
  driver's management admission does not transmit action frames in any
  case.

Success is that nothing moves:

| Reading | Required |
|---|---|
| `join HT: requested=1 accepted=1`, association and both lifetimes as before | HT negotiated |
| `rx_refused=0`, no status bit beyond `0xc000`, ledger exact | nothing else moved |
| TX about 22, RX about 18, a clean verdict | the measurement unchanged |
| the receive rate record (`RX rates: mode/rate=`) | **the reading that matters** |

| Reading | Cause | Next |
|---|---|---|
| mode 2 (HT) frames in the receive rate record | the access point sends HT toward this station | the fixed-MCS descriptor (`TX_MODE_HT_MM \| MCS7` = `0x87` in the existing fixed-rate field) as the next single variable |
| only mode 1 (OFDM) | the access point stays legacy toward this station | HT buys nothing here; the throughput work ends at about 22/18, recorded as such |
| `rx_refused` non-zero, new status bits, or more than one A-MPDU sub-frame per buffer | the access point aggregates toward a station that cannot receive it | **stop**: name each before any throughput claim; that is the boundary between "HT is available" and "HT is available and we cannot receive it" |
| `join frame element refused` or `join channel refused` | the admission does not match what mac80211 built | the record names the element or width; correct the admission |

The fixed-rate trade (boot T) applies: the HT steps should predict more
loss exposure at a fixed MCS, not less.

### Boot U result (2026-10-25, 22:09 UTC): the access point uses HT toward this station at the top MCS, and our receive path takes it unchanged

Build `625c1eb3` (0293, records non-QoS), boot2 `a227cbd5…` over boot
T's `c7f650a8…`, mainline boot `23568a50…`, returned to Gemian
`5356f352…` by the session's own reviewed return (live identity checked
afterwards); log complete through the seal (187,145 bytes). The receipt
was whole (`all_pass=True`, five chunks each way, the core disconnect
accepted). The verdict failed on one gate, `classifier:ownership`, for
`tx_failed=2`, explained below.

**HT is available, and received.**

- `join HT: requested=1 accepted=1`.
- The receive rate record: mode 2 (HT) MCS7 ×27,538, MCS6 ×9,846,
  MCS5 ×718 and MCS4 ×4, with the legacy 6 Mbit/s ×130 the
  management and group frames.
- Zero refusals on 38,106 QoS frames, almost all of them HT
  (`rx_refused=0 rx_refused_qos=0`, no status bit beyond `0xc000`,
  `rx_llc_mis=1` with `type=0x002e` as before). No action frame was
  recorded either way.

This access point will use HT toward this station and chooses the top
MCS, and our receive path accepts HT frames unchanged: the QoS, TID and
per-TID replay work generalises. §31's stop boundary was not reached.

**The two failed transmits are air losses.** The sampled transmit
reports show `0/0x004c=747,3/0x004c=2`. Status 3 is
`TX_RESULT_MPDU_ERROR` in the vendor's `wlan_lib.h` (`59e00a91`): a
frame unacknowledged after its retries, at the fixed 54 Mbit/s.
`expired=0 pid_faults=0 left_pages=0`. The old gate folded `tx_failed`
into the ownership proof, so an air loss read as an ownership failure.
The flags `counts_ok`, `duration_pass` and `connected_lifetime_trial_pass`
were false in boots S and T too, whose verdicts passed: they were never
gates, and they did not fail this run. Fixed on the host (below).

**Throughput, against boot T's 20.86 / 16.38 and §31's "nothing moved".**

- *Transmit:* 19.2 Mbit/s (chunks 19.3–20.9).
- *Receive:* 13.72 Mbit/s (chunks 18.6, 18.1, 9.4, 18.4, 8.9).
- The device's TCP retransmissions across the transmit direction rose
  to 32 (boots S and T: 6 and 9), and `cwnd` fell as low as 22.
- In both receive dips the laptop's own send rate fell with the device's
  (16.0 and 11.8 against 22–23.5 on the other chunks), with no
  refusal.

So "nothing moved" was not met in rate or loss. From one run this cannot
be split between the channel and the access point's HT behaviour; it is
recorded, not attributed. The binding limit is plain all the same: the
access point offers about 65–72 Mbit/s of air and the device takes 18
at best.

## 32. Boot V (predeclared, 2026-10-25): receive batching re-admitted on boot U's tree

**The change.** `CONFIG_MT6797_HIF_RX_BATCH=y` in the lifecycle fragment,
with [0268](../../patches/proposals/0268-wifi-mt6797-receive-by-the-enhanced-status-block-and-aggregated-reads.patch)
unchanged and still in the series. Once per pass it reads the enhanced
status block, then reads each queue's frames in one aggregated
data-port transfer. When it was measured (boot 4 of 0268) it was
neutral, and correctly retired. Its own record said the receive number
was then plausibly clocked by the transmit path's acknowledgement
latency, so no receive lever could move it. Boot U changes that
condition: the access point now delivers MCS7 and our receive side is
the binding limit. Everything else is boot U's tree: HT advertised, the
descriptor at `0x4c`, the records non-QoS, depth 12, the ledger. The
probe's UDP legs stay retired.

**Riding along, host only: the verdict no longer lies about air
losses.** `throughput_verdict.py` splits a failed transmit out of
`ownership` into its own gate, `tx_delivery`. When every failed frame is
accounted for by status-3 (`MPDU_ERROR`) entries in the sampled report
histogram, the gate passes and the count is a named warning
(`verdict_warnings: tx_air_losses=N`). Any other status, or failures the
histogram does not explain, fail `classifier:tx_delivery`.
`ownership` keeps its proof (one record, retired > 0, nothing expired,
no PID fault, no pages left). The cohort's legacy flags are listed by
name in `retained_not_gated`.

Re-classified offline, boot U's own evidence passes with
`tx_air_losses=2`, and boot T is unchanged. A synthetic status 5, and an
unexplained count, both fail `tx_delivery`. Fixture:
`tests/throughput-classifier-test.py`.

| Reading | Cause | Next |
|---|---|---|
| RX rises toward 25–30 with TX unchanged | the per-frame register work was the ingest limit, exposed only now | keep it; the receive side is then within a factor of 2 of the access point |
| RX unchanged | ingest is elsewhere: the polled loop's cadence or the firmware's ring | the interrupt becomes the next question, with a reason at last |
| any refusal, or any `device_timeout` receive chunk | the batching interacts with HT frames | revert, as boot B established |
| the credit ledger not whole (`expired`, `pid_faults`, `left_pages`) | the block read's TX credit merge (boot 1 of 0268) on today's credit-retire path | revert; the merge is the suspect |

Quoted beside the receive rate: the device-side rate, the refusal
counters, `HIF RX batch:` (reads, aggregates, frames, max, failures),
the receive rate record, and the transmit side's `tx_air_losses`.

**After it, the fixed HT MCS for transmit (boot W, not yet
predeclared).** One constant, `CONFIG_MT6797_DATA_FIXED_RATE_CODE=0x87`
(`TX_MODE_HT_MM | MCS7`), in the descriptor's existing fixed-rate field.
The access point proves MCS7 works in this channel. Payload air time for
a 1,536-byte frame drops from 227.6 µs at 54 Mbit/s to 189 µs at MCS7
with the long guard interval we advertise (65 Mbit/s). The owner's
169 µs is MCS7 with the short guard interval (72.2 Mbit/s), which is not
advertised. Expect about +15–18 % on transmit before per-frame overhead.
A fixed MCS trades margin for rate, so losses should rise, not fall,
until rate adaptation exists.

### Boot V result (2026-10-25, 22:25 UTC): batching lifts receive modestly and transmit with it; ingest is still bound elsewhere; one correct replay refusal

Build `1246fc2d` (`HIF_RX_BATCH` re-admitted on boot U's tree), boot2
`c06ff1ae…` over boot U's `a227cbd5…`, mainline boot `81266691…`,
returned to Gemian `885a03ed…` by the session's own reviewed return (live
identity checked afterwards); log complete through the seal (193,192
bytes). Clean verdict: `session_exit=0`, `all_pass=True`,
`verdict_failed=[]`, no warning, every gate true (`tx_delivery`
included).

**The batching worked.** `HIF RX batch: on=1 whcr=0x00000000
reads=535990 aggregates=20994 frames=43914 empty=514996 max=16
failures=0 credits=51230 block_abnormal=0x00000000`: every frame came
through the status block and the aggregated reads, about 2.1 per
aggregate and up to 16. The ledger is exact: `expired=0 pid_faults=0
left_pages=0 dropped_full=0 tx_failed=0`, sampled reports 797 of 797 at
status 0, retire wait 5.16 ms, 12 in flight. No receive chunk ended by
`device_timeout`. The downlink is HT: MCS7 ×42,055 of 42,069 QoS frames.

**Against §32's rows.**

| | Boot T (no HT) | Boot U (HT) | Boot V (HT + batch) |
|---|---|---|---|
| RX aggregate | 16.38 | 13.72 | **18.22** |
| RX chunks | 18.7, 10.4, 20.0, 18.8, 20.0 | 18.6, 18.1, 9.4, 18.4, 8.9 | 22.1, 19.5, 22.3, 10.1, 20.6 |
| TX aggregate (chunks) | 20.86 (21.7–22.3) | 19.2 (19.3–20.9) | **22.01** (22.3–24.1) |
| device TCP retransmissions, TX | 9 | 32 | 4 |
| receive refusals | 0 | 0 | 1 (`pn=equal`, Retry) |

- *Receive* rose on its good chunks, from 18.1–18.6 to 19.5–22.3, about
  +15 %. It did not rise toward 25–30, so the result sits nearer the
  "RX unchanged" row than the first.
- The device was 85.6 % idle during receive, so the CPU is not the
  ingest limit. The single dip (chunk 4, 10.1) came with the laptop's
  own send rate falling to 11.8 and an empty device receive queue: the
  flow slowed at the sender, as in boots T and U.
- The per-frame register work was part of the cost, and no longer the
  binding part. Ingest is elsewhere: the polled loop's cadence or the
  firmware's ring. The interrupt is the next receive question, now with
  a reason.
- *Transmit* also rose, to 22.01 with every chunk at 22.3–24.1, with 4
  retransmissions. That is an inference, not measured: with one status
  block read per pass in place of per-frame reads, the worker returns to
  the transmit queue sooner.

**Owner, 2026-10-25: the re-admission paid; 0268 stays admitted.** RX
13.72 → 18.22 aggregate (clean chunks 18.1–18.6 → 19.5–22.3), TX 19.20 →
22.01 with no transmit change, 42,055 MCS7 frames through the block
read. Two lessons, stated once so later boots are read correctly:

- *A "neutral" retirement records a condition, not a property.* 0268
  measured neutral while the acknowledgement clock capped receive at
  about 19. That was the condition; it was not a property of the
  batching. This is the second retirement overturned when the condition
  changed.
- *Transmit and receive share one worker.* A receive-side change moves
  transmit: here the transmit chunks rose by 2–3 Mbit/s with nothing on
  the transmit path changed. Later boots attribute a transmit move to a
  receive change, or the reverse, only after this.

`empty=514996` of `reads=535990`: 96 % of block reads find nothing. The
remaining receive cost is the pass cadence, not the block read.

**The one refusal: the literal trigger of §32's third row, and a correct
refusal.** `field=pn ... fc=0x4a88 qos=0x0000 pn=equal tid=0
counter=pairwise`, 148 bytes. The Retry bit is set and the PN equals the
TID-0 counter: a retransmission of a frame already delivered. The
replay check must refuse it, and §30 predicted this row ("equal, or a
Retry frame: a genuine duplicate, refused as it must be"). It names its
TID and counter, has `status=none`, and is no aggregation artefact. So
the row's literal condition is met while its cause, the batching
interacting with HT frames, is not. Boot B's precedent (line 1727)
recorded a literal trigger of this kind as "not boot B's failure". The
owner kept the admission. Also recorded:
`rx_llc_mis=3`, all `type=0x002e`.

## 33. Boot W (predeclared, 2026-10-25): the fixed HT MCS7 on transmit, one constant

**The change.** `CONFIG_MT6797_DATA_FIXED_RATE_CODE=0x87`
(`TX_MODE_HT_MM | MCS7`, `wlan_def.h`) in the lifecycle fragment, written
into the descriptor's existing fixed-rate field
(`TX_DESC_FIXDE_RATE_MASK`, bits 2–13: `0x87 << 2 = 0x021c`). The
guard-interval and LDPC bits stay clear (the long guard interval we
advertise). The option's range stopped at `0x4f`, so `0x87` would have
been refused by the configuration and silently replaced by the 6 Mbit/s
default.
[0294](../../patches/proposals/0294-wifi-mt6797-admit-an-HT-rate-code-as-the-fixed-data-rate.patch)
widens the range to the vendor's 8-bit codes and documents the HT mode;
no code changes. Management and security frames keep OFDM 6 Mbit/s.
Everything else is boot V's tree: batching on, HT advertised, the
records non-QoS (the station record's PHY stays legacy), depth 12, the
ledger.

**The prediction.** The access point sends MCS7 to us on 42,055 of
42,069 frames, so the channel supports it in that direction.

- *Air time:* payload air time for a 1,536-byte frame goes from 227.6 µs
  at 54 Mbit/s to 189 µs at MCS7 with the long guard interval
  (65 Mbit/s). The owner's 169 µs is MCS7 with the short guard interval
  (72.2 Mbit/s), not configured here.
- *Transmit:* about +15–18 % before per-frame overhead, so toward 25 from
  boot V's 22.
- *Losses:* a fixed MCS trades margin for rate, so losses and
  retransmissions should rise slightly. That is not a regression, and
  the verdict's `tx_air_losses` warning is where it should appear.

| Reading | Cause | Next |
|---|---|---|
| sampled reports at rate `0x87`, status 0; TX toward 25 | the firmware sends HT on the legacy station record | the receive decision below |
| reports at `0x87` with many status-3 frames, TX down | MCS7 has no margin on the uplink at this range | a lower fixed MCS (6 or 5) as its own boot, or adaptation |
| every data frame status 3, or the reported rate stays `0x4c` | the firmware will not send HT to a station record declared legacy | the station record's PHY and MCS fields (HT scope item 4) |
| any receive refusal, ledger not whole beyond air losses | the change reached past the transmit rate | stop and name it |

**Then one decision, not a queue: the interrupt or the air-rate
levers.** With batching in place, the remaining receive cost is the poll
cadence (96 % of block reads empty) against an access point willing to
send at 65–72 Mbit/s. The choice is made on one criterion, which one
moves the binding constraint:

- *If receive ingest stays flat while transmit rises:* the receive answer
  is the interrupt, the vendor's own shape (ISR → status block →
  aggregated DMA). It removes the pass cadence.
- *If receive tracks the air rate once transmit is faster:* the air-rate
  levers come first, because they are cheaper. Short guard interval
  (`SGI_20`, about 11 %) and 40 MHz are fields in paths we already
  write.

### Boot W result (2026-10-25, 22:44 UTC): the firmware sends HT MCS7 on a legacy station record with no loss, but transmit hardly moves: the per-frame cycle binds, not the air

Build `43f4fa20` (0294, `DATA_FIXED_RATE_CODE=0x87`, batching and HT on,
records non-QoS), boot2 `0b0e2e01…` over boot V's `c06ff1ae…`, mainline
boot `2bcf0d02…`, returned to Gemian `dd7fd353…` by the session's own
reviewed return (live identity checked afterwards); log complete through
the seal (189,447 bytes). Clean verdict: `session_exit=0`,
`all_pass=True`, `verdict_failed=[]`, no warning.

**The descriptor change took, with no loss.** `join data TX: first ...
rate=0x87`; sampled reports `0/0x0087=830` of 830: every sampled data
frame was sent at HT MCS7 and acknowledged. The firmware sends HT on a
station record that still declares legacy PHY. There were no air losses
(`tx_failed=0`, no `tx_air_losses` warning) and 4 TCP retransmissions.
Ledger exact: `expired=0 pid_faults=0 left_pages=0 dropped_full=0`. No
receive refusal (`rx_refused=0`), and the downlink is MCS7 on 44,360 of
44,541 QoS frames. Batching `failures=0`, with 96 % of block reads empty
again (536,612 of 560,659).

| | Boot V (54 Mbit/s OFDM) | Boot W (HT MCS7) |
|---|---|---|
| TX aggregate (chunks) | 22.01 (22.3–24.1) | 22.58 (23.5–24.2) |
| credit-retire wait, in flight | 5.16 ms, 12 | 5.20 ms, 12 |
| RX aggregate (chunks) | 18.22 (22.1, 19.5, 22.3, 10.1, 20.6) | 19.97 (22.6, 20.4, 17.8, 21.9, 22.4) |
| device idle TX / RX | 81.1 / 85.6 % | 80.9 / 84.8 % |
| TCP retransmissions, air losses | 4, 0 | 4, 0 |

**Against §33's prediction: not met, and the reason is measured.**
Transmit rose 2.6 %, not 15–18 %. The credit-retire wait did not move
(5.16 → 5.20 ms at 12 in flight): each frame costs about 433 µs of the
host-and-firmware cycle (5.2 ms over 12), against 189 µs of air at MCS7
and 227.6 µs at 54 Mbit/s. Shortening the air time could not shorten the
cycle. Transmit is bound by the per-frame retire cycle, as the depth
model said (asymptote about 33–36 Mbit/s), not by the air. Receive rose
to 19.97 with no dip. Its good chunks (20.4–22.6) sit with boot V's
(19.5–22.3): one run, read as unchanged.

**The decision §33 asked for: the interrupt, not the air-rate levers.**
The criterion was which lever moves the binding constraint.

- *Transmit:* a 17 % cut in air time moved transmit by 2.6 %, so short
  guard interval (about 11 % less air) and 40 MHz cannot move it either.
- *Receive:* the downlink already arrives at MCS7, about 65 Mbit/s of
  air, while we take 20 with the device 85 % idle and 96 % of block reads
  empty. Receive is bound by the poll cadence, not the air.

Both directions are bound by the polled host cycle, which is what the
interrupt (the vendor's ISR → status block → aggregated DMA) removes. The
air-rate levers stay unused and cheap, for after it. The fixed MCS7
stays: no loss, transmit and receive no worse, and it keeps air time free
for the downlink.

**Boot W, the owner's reading (2026-10-25): the service-time arithmetic,
the air-rate levers retired, and the two couplings.**

*The arithmetic, which decides the next project.*

| Quantity | Value | Source |
|---|---|---|
| air at MCS7 (long GI), 1,518 bytes | 0.19 ms (0.17 at short GI); 0.22 at 54 Mbit/s | 1,518 × 8 ÷ 65, ÷ 72.2, ÷ 54 |
| transmit service time per frame | 0.43 ms | credit-retire wait 5.2 ms ÷ 12 in flight (the owner's 0.46 rounds the same) |
| transmit, per TCP segment | 0.51 ms | 22.58 Mbit/s ÷ (1,448 × 8) = 1,949 segments/s |
| receive, per TCP segment | 0.58 ms | 19.97 Mbit/s = 1,724 segments/s, arriving in aggregated bursts |
| the vendor through the same firmware | 0.26 ms | 45 Mbit/s = 3,885 segments/s |

- The air is about a third of our transmit service time, which is why a
  17–20 % air reduction produced 2.6 %.
- Receive shows the same per-frame cost while the access point sends
  aggregated bursts (2.1 frames per block read, up to 16), so the cost
  is per frame, not per aggregate.
- Subtracting air time, the vendor's firmware work is about 0.09 ms a
  frame against our 0.28 ms (the owner's estimate).

*40 MHz and short guard interval are retired as throughput levers.* Both
only shrink the air component, which is now the smaller part of the
service time. They are recorded as "air-only, low value" and leave the
HT queue, so they do not return as candidates.

*The two couplings, read before any result that moves both directions is
called a side effect.*

- **Shared worker:** a receive-side change moves transmit. Boot V
  batching moved transmit from 19.2 (boot U) and 20.86 (boot T) to
  22.01, with no transmit change.
- **Shared medium:** a transmit-side change can move receive, because
  shorter transmit air time frees the medium for the access point's
  downlink. Boot W shows it only weakly. Receive's aggregate rose 10 %
  (18.22 → 19.97), but the mean of boot V's four undisturbed chunks
  (21.1) equals boot W's five (21.0): most of the aggregate gain is boot
  V's single dip not recurring. The coupling is plausible and recorded;
  boot W does not measure its size.

*The next project: firmware aggregation (HT scope).* What the record
already shows:

- Our descriptor leaves block-ack enabled. Byte 11 is the vendor's
  `ucPowerOffset`: bit 7 fixed rate, bit 5 `TX_DESC_BA_DISABLE`; ours is
  `0x80`, so BA-disable is clear.
- What declares nothing is the station record: no QoS (`ucIsQoS`, the
  existing `WMM_QOS_RECORDS` option, kept off since boot P), legacy PHY
  (`ucDesiredPhyTypeSet`), and no MCS set, HT capability or A-MPDU
  parameters (`ucMcsSet`, `aucRxMcsBitmask`, `u2HtCapInfo`,
  `ucAmpduParam` in `CMD_UPDATE_STA_RECORD`).

## 34. Boot X (predeclared, 2026-10-25): the records' QoS and HT declaration, a compatibility step whose success is that nothing moves

**Purpose, in one line.** The BSS's `ucIsQBSS` and the station's
`ucIsQoS` (and the records' HT fields) gate nothing observed yet: boots
S–W carried QoS data both ways with them off, with zero refusals and HT
rates. Their consumer is the firmware's QoS and aggregation machinery,
which only block-ack exercises. This boot isolates the declaration from
the aggregation after it, so a later block-ack failure cannot be
attributed to the records.

**The change.** `CONFIG_MT6797_WMM_QOS_RECORDS=y` (off since boot P) and
[0295](../../patches/proposals/0295-wifi-mt6797-declare-the-access-point-s-HT-in-the-post-association-records.patch)
`CONFIG_MT6797_HT_RECORDS=y` in the lifecycle fragment, on boot W's tree.
The fields follow the vendor structures (`nic_cmd_event.h`, `59e00a91`).
Only the post-association records change, the ones the vendor AIS path
also sends after association. The state-1 record before association
stays legacy.

| Record field (byte) | Sent | Value |
|---|---|---|
| BSS `ucIsQBSS` (42) | yes | 1 (WMM accepted) |
| BSS `ucPhyTypeSet` (55) | yes | `0x18`, OFDM \| HT |
| BSS `u2OperationalRateSet`, `u2BSSBasicRateSet` (44, 46) | unchanged | as the join establishes |
| BSS RLM `ucHtProtectMode` (73) | yes | the operating mode of the AP's HT information 2 (`ENUM_HT_PROTECT_MODE` values) |
| BSS RLM `u2HtOpInfo3`, `u2HtOpInfo2`, `ucHtOpInfo1` (76, 78, 80) | yes | from the AP's HT operation element, in the association response |
| BSS RLM `ucRfSco`, `ucGfOperationMode`, `ucTxRifsMode` (71, 74, 75) | left at 0 | HT20 at the fixed channel |
| BSS `ucUseShortPreamble`, `ucUseShortSlotTime`, `ucNonHTBasicPhyType` (81, 82, 52) | unchanged | |
| STA `ucIsQoS` (18) | yes | 1 |
| STA `ucDesiredPhyTypeSet` (13) | yes | `0x18`, OFDM \| HT |
| STA `ucMcsSet`, `ucSupMcs32`, `aucRxMcsBitmask[10]` (21, 22, 24–33) | yes | from the peer's HT MCS set, in the association response |
| STA `u2HtCapInfo`, `u2HtExtendedCap` (40, 42) | yes | from the peer's HT capability element |
| STA `u2RxHighestSupportedRate`, `u4TxRateInfo`, `u4TxBeamformingCap`, `ucAselCap` (34, 36, 44, 49) | left at 0 | today's values |
| STA `ucAmpduParam` (48) | left at 0 | benign |
| STA `ucTxAmpdu`, `ucRxAmpdu` (76, 77) | unchanged | 1, block-ack disabled |
| STA `u2HwDefaultFixedRateCode` (74), the data descriptor | unchanged | `0x4b` for management; data at `0x87` |

One record line names every declared value as sent (`join HT records:
declared= sta_phy= mcs= mcs32= cap= ext= bss_phy= protect= op1= op2=
op3=`). The next boot inherits it as its baseline.

**Success is that nothing moved, read on the queue mapping, not the
rate.**

| Reading | Required |
|---|---|
| association, both lifetimes, `join HT records: declared=1` | the records accepted |
| ledger | unchanged: `debt=0`, `left_pages=0`, `expired=0`, `dropped_full=0`, `tx_failed=0` or air losses only |
| TC mapping | every QoS submission still on the provisioned TC1 |
| refusals | `rx_refused=0`, `tx_tid_refused=0` |
| TX / RX | about 22.6 / 20 Mbit/s |
| rate samples | still `0x0087` (the descriptor's fixed MCS is unchanged by the record) |

How the TC mapping is read: the host names the queue in each descriptor
(byte 3: queue index 1, TC1) and the firmware returns page credits per
queue. No per-TC line exists, so a firmware remap to an unprovisioned TC
(the vendor's model has four AC TCs; we have pages for one) shows as
credits that do not return: `expired` or `left_pages` non-zero,
`tx_credits` short of the submissions, or the backpressure left stopped.

| Reading | Cause | Next |
|---|---|---|
| nothing moved | the declaration is compatible | the block-ack boot, inheriting this baseline |
| credits stop returning, a queue starves | the firmware maps QoS frames away from TC1 once the station is QoS | **the finding worth having before block-ack**: the TC per access category (the vendor's `arNetwork2TcResource`) becomes its own change |
| the association or a record refused | a field or its encoding is wrong | the record line names the values; correct the field |
| rate samples leave `0x0087` | the record overrides the descriptor's fixed rate | name it; the rate source is then the record |

**Then the block-ack boot (not yet predeclared).** Block-ack enabled in
the station record, with several frames submitted per aggregate window.
The measurement is the service time; throughput is a consequence. If
`wait_avg ÷ depth` falls below about 0.2 ms, the firmware is amortising
its per-frame work and transmit can pass 30. If it stays near 0.43 ms,
its cost is per MPDU and about 23 Mbit/s is the real ceiling.

### Boot X result (2026-10-25, 23:13 UTC): the records' QoS and HT declaration is compatible; nothing the declaration could move moved

Build `a34cff21` (`WMM_QOS_RECORDS` and 0295 `HT_RECORDS` on boot W's
tree), boot2 `9b74c622…` over boot W's `0b0e2e01…`, mainline boot
`393a0c99…`, returned to Gemian `0c2f26a4…` by the session's own
reviewed return (live identity checked afterwards); log complete through
the seal (187,581 bytes). Verdict passed: `session_exit=0`,
`all_pass=True`, `verdict_failed=[]`, one warning `tx_air_losses=3`.

**The declaration, as sent.** `join WMM: ... records_qos=1`;
`join HT records: declared=1 sta_phy=0x18 mcs=0xff mcs32=0 cap=0x09ef
ext=0x0000 bss_phy=0x18 protect=2 op1=0x07 op2=0x0006 op3=0x0000 ampdu=0
ba=disabled`. The firmware accepted both records, and the join and both
lifetimes ran as before. The baseline the block-ack boot inherits, read
from the access point's elements:

- `cap=0x09ef`: LDPC, 40 MHz, SM power save disabled, short GI 20 and 40,
  TX STBC, one RX STBC stream, 7,935-byte A-MSDU, no greenfield.
- `protect=2` and `op2=0x0006`: HT operating mode 2 (a 20 MHz
  protection mode) with non-greenfield stations present.
- `op1=0x07`: the access point runs a 40 MHz BSS with its secondary
  channel below. We declare HT20 (`ucRfSco` left 0), consistent with
  40 MHz retired as a lever.

**Against §34's table: met.**

| Reading | Boot X |
|---|---|
| association, lifetimes | as before |
| ledger | `expired=0 pid_faults=0 left_pages=0 dropped_full=0`; `tx_failed=3`, all sampled status 3 at `0x0087` (air losses, the warning) |
| TC mapping | every credit returned: 48,727 retired, `tx_done` + `tx_failed` = `tx_queued` (49,497 + 3 = 49,500), backpressure never left stopped (`stopped=0`), TC4 reconciliation as in every boot |
| refusals | `rx_refused=0`, `tx_tid_refused=0` |
| rate samples | `0/0x0087=770, 3/0x0087=3`: the record did not override the descriptor's fixed MCS |
| TX / RX | 21.27 (chunks 23.4, 23.9, 23.8, 20.0, 21.2) / 18.94 (13.8, then 21.2, 20.2, 21.6, 21.8) |

Throughput sits within the series' run-to-run spread around boot W's
22.58 / 19.97. Transmit's first three chunks match boot W, and its last
two came with 16 TCP retransmissions and `ssthresh` down to 34: air,
the fixed-rate trade, three sampled losses. Receive's one low chunk had
the laptop's own send rate falling with it (14.8), as in earlier boots;
the other four match boot W. Nothing the declaration could move moved.

**Owner, 2026-10-25: boot X passed its purpose and missed its
criterion; the two halves are recorded separately.**

- *Passed: the steady state is unchanged.* Transmit chunks 1–3 match
  boot W (23.4–23.9 against 23.5–24.2), and receive chunks 2–5 are
  slightly better. `rx_refused=0`, `tx_tid_refused=0`, the ledger exact.
  The queue mapping is intact: 49,500 QoS frames all landed on the
  provisioned TC1. The declared risk, the firmware wanting per-AC
  traffic classes we have no pages for, did not materialise.
- *Missed: §34's "nothing moved" criterion on losses.* Transmit chunks 4
  and 5 ran at 20.0 and 21.2 against 23.8–24.1, retransmissions rose from
  4 to 16, and `tx_failed` from 0 to 3. That is an unexplained loss
  episode in the second half, not a throughput regression: the steady
  state is unchanged.
- *Read together with it:* three of 773 sampled transmit reports carry
  status 3 (`MPDU_ERROR`) at MCS7, where boot W had none of 830. Small,
  but the first retry-limit failures the fixed MCS has produced. They
  are kept beside the loss episode, not read separately.

**The declaration stays, and is named as a suspect.** It is the
prerequisite for the aggregation that follows and cost nothing
structural. If the block-ack boot disappoints, the first thing to split
is the declaration itself: the QoS bits alone against the HT fields
(`u2HtOpInfo1..3`, `ucHtProtectMode`). Those are the only part of it
that can change framing and protection behaviour.

**Next: the block-ack boot (to be predeclared).** It inherits this
baseline. Block-ack is enabled in the station record
(`ucTxAmpdu`/`ucRxAmpdu`, the A-MPDU parameters), with several frames
submitted per aggregate window, read as service time per frame:

| `wait_avg ÷ depth` | Meaning |
|---|---|
| falls below about 0.2 ms | the firmware is amortising its per-frame work; transmit can pass 30 |
| stays near 0.43–0.46 ms | its cost is per MPDU; about 23 Mbit/s is the real ceiling, and the vendor's 45 comes from something else, worth one source read |
| retransmissions climb with boot X's second-half signature | the declaration's HT fields, not the aggregation | split the declaration (above) |

Boot X's figure is 0.46 ms (5.49 ms ÷ 12).

## 35. Boot Y (predeclared, 2026-10-25): transmit aggregation in the firmware, read as service time

**Where the differentiation stands (owner, 2026-10-25).** Everything else
is at parity with the vendor and is not re-litigated: WMM, QoS framing,
HT capability, per-TID replay, TID routing, the records' QoS and HT
declaration, both directions clean. One structural gap remains. Our
per-frame service is about 0.46 ms against 0.17–0.19 ms of air; the
vendor's 45 Mbit/s through the same firmware implies about 0.26 ms end
to end and 0.09 ms of firmware work per frame. Two differences in how
the vendor transmits explain it, each now read from source:

- *Firmware-side A-MPDU.* The vendor build keeps block-ack in the
  firmware (`config.h`: `CFG_M0VE_BA_TO_DRIVER 0`). Its station record
  enables A-MPDU (`cnm_mem.c`: `ucTxAmpdu` and `ucRxAmpdu` =
  `FEATURE_OPT_IN_COMMAND(AmpduTx/AmpduRx)`, `FEATURE_ENABLED` by
  default, so 2; `ucTxBaSize` and `ucRxBaSize` 64; `ucAmpduParam` the
  peer's). The host handles only the receive block-ack events
  (`EVENT_ID_RX_ADDBA/DELBA`) for its reordering. Transmit block-ack
  needs no host event.
- *Submission batching (the second suspect, owner's item 3, answered).*
  The vendor hands the firmware a burst per transfer, not one frame per
  command. With MT6797's `CFG_SDIO_TX_AGG 1` and
  `CFG_SDIO_TX_AGG_LIMIT 0`, `nicTxMsduQueue` copies every queued MSDU
  (descriptor and frame, 4-byte aligned) into one coalescing buffer of up
  to 968 pages, then issues one `HAL_WRITE_TX_PORT` for the whole queue.
  On this AHB part one `kalDevPortWrite` is one SDIO-gen3 command in
  block mode, a single transfer (DMA to `MCR_WTDR1`) carrying every frame.
  Ours writes one descriptor and one DMA transfer per frame. That is a
  host-side lever for the same per-frame difference, cheaper than any
  firmware question.

**The queue, in this order.**

1. Transmit aggregation (this boot), read as service time.
2. Submission batching (several frames per transfer), if aggregation
   leaves the per-frame cost near 0.46 ms.
3. Interrupt-driven receive, if receive stays near 20 against an access
   point sending at MCS7. Boot V showed the block read worth about a
   third; the residual is the pass cadence.
4. Only then short guard interval, then 40 MHz: both scale the air, a
   third of the cost.

Rate adaptation (parked on an unanswered firmware question) and power
save (an idle and latency item) stay off the throughput queue.

**The change.**
[0296](../../patches/proposals/0296-wifi-mt6797-let-the-firmware-aggregate-transmit-to-an-HT-access-point.patch)
(`CONFIG_MT6797_TX_AMPDU=y` in the lifecycle fragment, on boot X's tree):
in the state-3 station record that declares the access point's HT,

- `ucTxAmpdu` (76) = 2, `FEATURE_OPT_CMD_ENABLED`, where boot X sent 1
  (DISABLED);
- `ucTxBaSize` (92) = 64, the vendor's window;
- `ucAmpduParam` (48) = the peer's A-MPDU parameters from its HT
  capability, where boot X sent 0.

Receive A-MPDU stays disabled (`ucRxAmpdu` 1, `ucRxBaSize` 0). A
receive session would need host reordering, and admission of status
words with the A-MPDU bits clear (the vendor's `RXS_DW2_AMPDU_nERR`
path), its own change. Host submission is unchanged: one frame per
transfer, 12 in flight, so an aggregate can hold at most what the
firmware has queued (up to 12). The record line names the values
(`ampdu= tx_ampdu=2 tx_ba=64 rx_ampdu=1`).

**The reading: service time first, throughput a consequence.**

| `wait_avg ÷ depth` | Meaning | Next |
|---|---|---|
| falls below about 0.2 ms | the firmware amortises its per-frame work across the aggregate | aggregation is the lever; raise the depth (the aggregate's upper bound) and read transmit past 30 |
| stays near 0.46 ms | the firmware's cost is per MPDU, **or no aggregate formed** | submission batching (queue item 2) |
| retransmissions climb with boot X's second-half signature | the declaration's HT fields, not the aggregation | split the declaration: the QoS bits alone against the HT fields |
| any receive refusal, credits not returning, a stuck queue | the session changed more than the transmit path | stop and name it |

**One limitation, stated before the boot.** The transmit-done event
carries `ucTxCount` and `ucFlag`, and the source gives neither an
aggregation meaning. So a result near 0.46 ms cannot by itself
distinguish "the firmware's cost is per MPDU" from "the firmware formed
no aggregate" (no session established, or a fixed-rate descriptor kept
out of aggregation). Either way the next lever is the same, submission
batching, which needs no firmware answer.

### Boot Y result (2026-10-25, 23:35 UTC): firmware transmit aggregation reports every frame delivered while TCP sees loss; the stream collapsed; §35's stop row

Build `70df93c9` (0296, `TX_AMPDU` on boot X's tree), boot2 `2d09ef9d…`
over boot X's `9b74c622…`, mainline boot `03459830…`, returned to Gemian
`84fe607a…` by the session's own reviewed return (live identity checked
afterwards); log complete through the seal (197,649 bytes). Verdict
failed: `session_exit=1`, the receipt not whole, `classifier:timing`. The
failure is named below; no throughput is claimed.

**The change took.** `join HT records: declared=1 ... ampdu=0x1b
tx_ampdu=2 tx_ba=64 rx_ampdu=1`: the firmware accepted the station record
with transmit A-MPDU enabled, the 64-frame window, and the peer's A-MPDU
parameters `0x1b` (64 KiB maximum A-MPDU, 8 µs density). The join and
association ran as before.

**What happened.**

- The transmit direction's first chunk delivered 3,108,432 bytes to the
  laptop in 3 s: 8.28 Mbit/s against about 23.5 in boots W and X.
- 1.5 s into it, the device's TCP sender stood at `cwnd 1 ssthresh 7`
  (`TP4_TCP 1 1 7`): repeated retransmission timeouts.
- The measurement's SSH control session then ended (exit 255 about 22 s
  after it started, no stderr, 479 bytes of output). The second
  transmit chunk and every receive chunk never opened (`early_stop:
  cancelled while waiting for the device to open chunk 2 / chunk 1`).
- The data phase ran to the leaf's own disconnect: 41.6 s, 2,372 frames
  queued.

**What the firmware and the driver said meanwhile.**

- `tx_done=2372 tx_failed=0`; the sampled reports `0/0x0087=37` of 37,
  every one status 0 at MCS7.
- The credits whole: `retired=2335 expired=0 pid_faults=0 left_pages=0`,
  `dropped_full=0`, backpressure never left stopped.
- No transmit refusal (`tx_tid=2319/0/0/53/...`).
- One receive refusal, the 442-byte software-frame class of boot R
  (`field=packet-type prefix=0xe004 status=cipher-mismatch+data
  wlan=2`), not a data frame. `rx_qos=179` (MCS7), `rx_llc_mis=16`.

**Reading.** With firmware transmit aggregation, the firmware reports
frames as delivered (status 0) that the peer does not deliver to the
laptop: TCP collapses while the driver's ledger stays whole. This is the
first boot in the series where the transmit status and end-to-end
delivery disagree. The ledger's own checks cannot see it; the receipt
and the TCP state do.

Candidates, not measured and not distinguished by this record:

- the access point's block-ack reorder buffer holding or dropping the
  aggregated frames: the sequence numbers the firmware assigns against
  the session's starting sequence, or a BlockAckReq the firmware does not
  send;
- the fixed-rate descriptor (`0x87`) on frames inside an A-MPDU;
- the session on the SSH control session's TID 3 failing separately
  from TID 0.

The service-time reading is not meaningful on a stream that collapsed
(wait 4.81 ms over 12, from 2,372 frames).

**§35's row.** "Credits not returning, a stuck queue → stop and name
it": the credits returned, but the end-to-end stream stalled, which is
the condition the row exists for. So the boot stops here. Transmit
aggregation is withdrawn from the admitted profile until its failure is
understood: `CONFIG_MT6797_TX_AMPDU` leaves the lifecycle fragment, and
0296 stays in the series behind its option. The next lever in the
owner's queue needs no firmware answer: submission batching (several
frames per transfer, the vendor's `CFG_SDIO_TX_AGG`). Whether
aggregation returns, and with which read first (the firmware's block-ack
sequence handling, or a fixed-rate exclusion), is the owner's decision.

**Boot Y, the owner's classification (2026-10-25): a regression, with the
class of cause.**

- *The evidence.* 2,372 transmit frames in 41.6 s (about 57 a second
  against about 1,200 in boots W and X), 371 frames delivered, one chunk
  at 8.28 Mbit/s, then the disconnect. Meanwhile the host pipeline was
  healthy: `expired=0 pid_faults=0 left_pages=0`, `inflight_max=12`,
  `wait_avg=4.81 ms`.
- *The class of cause.* Both directions starved with the association
  intact. That is an aggregation state the peer does not share, not a
  host or ledger fault.
- *Kept as a permanent instrument:* `join HT records:` (`declared`,
  `sta_phy`, `mcs`, `cap`, `ampdu`, `tx_ampdu`, `tx_ba`, `rx_ampdu`), the
  record an aggregation boot is read by.
- *Reverted:* `CONFIG_MT6797_TX_AMPDU` leaves the fragment. 0296 stays a
  proposal, with this boot as its counter-evidence.

**The block-ack control path, read from the vendor source before any
further aggregation attempt (`59e00a91`).**

1. *Does the host send an ADDBA acceptance or per-TID control for the
   firmware to aggregate?* No. With `CFG_M0VE_BA_TO_DRIVER 0`, no host
   path sends one. `CMD_ID_TX_AMPDU` (`wlanoidSetTxAmpdu`) and
   `CMD_ID_ADDBA_REJECT` (`wlanoidSetAddbaReject`) are set-OIDs, and
   neither has a caller in the connect or initialisation path. The only
   host input per station is the station record (`ucTxAmpdu`,
   `ucRxAmpdu`, `ucTxBaSize`, `ucRxBaSize`, `ucAmpduParam`).
   `CMD_ID_RESET_BA_SCOREBOARD` belongs to the moved-to-driver build.
2. *What must the host do on `EVENT_ID_RX_ADDBA`?* Create a receive
   reorder entry for the event's TID, with its starting sequence and
   window (`qmHandleEventRxAddBa` → `qmAddRxBaEntry`), and reorder that
   TID's frames until `EVENT_ID_RX_DELBA`. It is a receive event only. In
   boot Y none was emitted: the join path refuses and logs any
   unrecognised control event (`join control event refused`), and the
   log has none. That is consistent with `ucRxAmpdu` declared disabled.
3. *Is `CMD_ID_ADDBA_REJECT` needed once per TID, and what does the
   firmware assume without it?* It is one global flag
   (`CMD_ADDBA_REJECT_T { fgEnable }`), not per TID, and the vendor's
   normal path never sends it. What the firmware assumes without it is
   in the firmware, not in the source.

So no answer is "the host must send it": the source shows no host step
missing from boot Y. The failure lies in the firmware's transmit
block-ack behaviour toward this access point. One consequence for the
next attempt: with block-ack in the firmware, the vendor gives the host
no transmit block-ack event, only the receive ones. A per-TID transmit
session record (requested, established, rejected, window) has no host
input defined in the source. A future aggregation boot can show the
receive events and the service time; the transmit session itself would
need a firmware query or an air capture, each its own question.

**A precondition and a stop rule for every aggregation boot (the
predeclaration lacked both).**

- *Precondition:* the link carries the previous boot's volume. The
  graded table assumes a working link.
- *Stop rule:* if transmit frames per second fall below about half the
  previous boot's (here 57 against about 1,200), stop, revert, and do not
  grade throughput.

Boot Y spent 41 seconds carrying 2,372 frames and never reached the
measurement it was predeclared for.

**Two declaration suspects, checked against the pinned source (owner,
2026-10-25): neither holds.**

- *The PHY type sets are OFDM | HT, not HT | VHT.* At `59e00a91`,
  `wlan_def.h`'s `ENUM_PHY_TYPE_INDEX_T` is HR/DSSS 0, ERP 1, ERP-P2P 2,
  OFDM 3, HT 4, VHT 5, so `PHY_TYPE_BIT_OFDM` = `BIT(3)` = `0x08`,
  `PHY_TYPE_BIT_HT` = `0x10`, `PHY_TYPE_BIT_VHT` = `0x20`, and
  `PHY_TYPE_SET_802_11AN` = OFDM | HT = `0x18`. The declared `sta_phy`
  and `bss_phy` of `0x18` are therefore exactly the vendor's 802.11an set,
  in the vendor's bit assignment. The legacy `0x08` that boots A–W ran on
  is `PHY_TYPE_BIT_OFDM`, and `ucNonHTBasicPhyType = 3` is
  `PHY_TYPE_OFDM_INDEX`. A layout without the ERP-P2P entry (OFDM `0x04`,
  HT `0x08`, VHT `0x10`) is not this pin. No correction is needed.
- *`ampdu=0x1b` is the peer's own A-MPDU parameters, not a constant.*
  The driver copies the access point's HT capability element body from
  its association response (`mac.c`, `join_ht_peer_cap`) and writes byte
  2 of it into `ucAmpduParam` (`hif.c`). The record line prints that same
  byte. The vendor fills it the same way (`prStaRec->ucAmpduParam =
  rHtCap.ucAmpduParamsInfo`). `0x1b` decodes as maximum A-MPDU exponent
  3 (64 KiB) and minimum start spacing 6 (8 µs). Our own advertised value
  would be `0x18` (8 KiB, 8 µs), so the declared value cannot be ours.

## 36. Boot Z (predeclared, 2026-10-25): aggregation declared as in boot Y, one frame in flight, the discriminator

**Purpose.** Separate "the declaration breaks framing" from "the
aggregate breaks delivery" for the price of one boot. The PHY sets and
the A-MPDU parameters are correct as declared, so the remaining split is
whether one frame at a time survives the transmit block-ack state.

**The change.** On boot Y's tree, the lifecycle fragment sets
`CONFIG_MT6797_TX_AMPDU=y` again (the declaration exactly as boot Y:
`ucTxAmpdu` 2, `ucTxBaSize` 64, the peer's `ucAmpduParam` `0x1b`, receive
A-MPDU disabled) and `CONFIG_MT6797_CCMP_TX_DEPTH=1`: one frame in
flight, the depth pins at their depth-one ledger. Nothing else changes:
HT, the records, `0x87`, batching on.

**Precondition and stop rule (§35's, scaled to depth one).** The depth
model (wait ≈ 1.465 + 0.350 × depth ms, the depth sweep's fit) predicts a retire
wait of about 1.8 ms at depth one, so about 550 frames a second. If
transmit frames per second fall below about 275, the boot stops,
`TX_AMPDU` is reverted, and no throughput is graded. The receipt is
read only for delivery and acknowledgement, not rate.

| Reading | Cause | Next |
|---|---|---|
| frames delivered and acknowledged at about the depth-one rate, TX rate `0x87`, TCP healthy | the declaration is harmless; boot Y's aggregate itself is malformed or unagreed | read the A-MPDU construction: the delimiter, the per-MPDU PN, and the session's starting sequence against the access point's reorder window |
| even one frame at a time is not delivered (TCP collapses, status 0 reported) | the declaration alone breaks framing | read what `ucTxAmpdu`/`ucTxBaSize`/`ucAmpduParam` change in the firmware's frame build, against the association response's HT capability |
| transmit below about 275 frames/s | the stop rule | stop, revert, do not grade |

Also recorded: the `join HT records:` line, the sampled transmit status,
the device's TCP state, and any receive refusal or control event.

### Boot Z result (2026-10-25, 23:51 UTC): the declaration is harmless at depth one; the aggregate is what goes undelivered; the lifetime then stopped on missing transmit reports

Build `f62f9e45` (`TX_AMPDU` as in boot Y, `CCMP_TX_DEPTH=1`), boot2
`f775c477…` over boot Y's `2d09ef9d…`, mainline boot `d25cb9fc…`,
returned to Gemian `3885482b…` by the session's own reviewed return
(`changed-ID-Gemian`, two attempts, recovery confirmed; live identity
checked afterwards); log complete through the seal (188,283 bytes).
Verdict failed (`session_exit=1`). The receipt and the lifetime are
named below.

**The discriminator's first branch (owner, 2026-10-25).** The declaration
was exactly boot Y's (`join HT records: ... ampdu=0x1b tx_ampdu=2
tx_ba=64 rx_ampdu=1`), with one frame in flight.

- All five transmit chunks completed at 10.19, 9.40, 10.36, 10.19 and
  9.60 Mbit/s.
- The device's TCP stayed healthy: `cwnd` 56, 50, 65, 43, 62 against boot
  Y's collapse to 1, with retransmissions rising from 2 to 5.
- 22,295 frames were queued in 29.6 s, about 750 a second, above the
  depth model's 550 and far above the 275 stop line.
- The transmit status is 0 at `0x0087` on 22,229 of 22,239 reports, the
  other 10 being air losses (status 3).
- Zero refusals (`rx_refused=0`); `rx_llc_mis=7`, all `type=0x002e`.

So the station record's QoS, HT and A-MPDU declaration does not break
framing. The fault is in the aggregate, or in the block-ack agreement
the access point honours. Boot Y stays the counter-evidence for the
aggregate itself.

**The receive half, and why the lifetime ended: not a harness
truncation.** Receive chunks 1 and 2 ran at 13.1 and 13.2 Mbit/s, chunk
3 at zero, chunks 4 and 5 never opened. The driver stopped the lifetime:
`join stopped: status=0 first=0 submitted=0x801 debt=0 cleanup=0
branch=4` (at error level), then `connection loss report:
source=terminal`, which ended the data phase at 29.6 s
(`reason=disconnect`) and with it the measurement's SSH session (exit
255). Before the stop, six receive gaps of 300–620 ms show transmit
stalled with frames waiting and nothing submitted: `queue=38–53
inflight=0 pages=0 stopped=1`.

At depth one the driver does not retire on credits (`retired=0
samples=0`): each frame waits for its own transmit-done report. 22,295
frames were queued against 22,239 reports (22,229 done, 10 failed), so
56 reports never arrived. The last record before the stop is a frame in
flight still awaiting its report (`CCMP completion observation:
inflight=1 pid=68`). Under the transmit block-ack declaration, the
firmware's per-frame transmit status is therefore incomplete. That
stalls a depth-one pipeline and ended this lifetime. It is a finding
about the aggregation state, recorded with boot Y's, not a receive
result: the receive numbers 13.1/13.2/0 are not to be read as a receive
regression.

**The cost model this boot gives, and the ceiling (owner, 2026-10-25).**

| Depth | Frames/s | Source |
|---|---|---|
| 1 | about 750–820 (unloaded round trip about 1.2 ms a frame) | boot Z |
| 12 | about 1,890 | boots M, W |
| 16 | about 1,970 | boot N |

The firmware saturates at about 1,950 frames a second, about 23.6 Mbit/s,
which is why depths 12 and 16 measured the same. `wait_avg ÷ depth`
understates the fixed round trip and is read as a lower bound on the
service time. About 23 Mbit/s is the measured ceiling of the design
without aggregation; in the owner's reading, no further depth, queue or
batching change will move it.

**Aggregation is parked behind firmware visibility.** Three boots (Y, Z,
and boot X's declaration) went into aggregation with no measured gain.
The remaining question lives inside the firmware, not in the host's
records: does it ever establish a transmit block-ack session for this
TID, and why does it report success for aggregates the peer never
delivered? It is scoped as one bounded firmware question, answered in the
private analysis environment with these runs' evidence as its premise.
No further boot goes to record bisects unless that read says the host is
involved. `CONFIG_MT6797_TX_AMPDU` leaves the fragment again, and the
depth returns to 12.

**Next: the receive interrupt (to be scoped and predeclared).** Receive
has a measured third behind the batching (boot V) and an access point
delivering MCS7, and its remaining cost is named: the poll cadence (96 %
of block reads empty, about 5,000 passes a second). The vendor's shape
(ISR → status block read → aggregated DMA) is one step from ours, the
last lever with no unknown mechanism. The predeclaration reads the
device-side receive rate and frames per second, not the aggregate. The
UDP probe stays retired. Any refusal, `device_timeout`, or a transmit
regression beyond the noise band reverts immediately, as boot B
established.

## 37. The receive interrupt, scoped (2026-10-25): the vendor's shape, ours, and the smallest bridge

**The vendor's shape (`59e00a91`).**

- *The line.* The vendor device tree gives the WLAN HIF a line of its
  own: `wifi@180f0000` (the same window as our `wifi-hif`),
  `interrupts = <GIC_SPI 283 IRQ_TYPE_LEVEL_LOW>`. `ahb.c` maps it from
  that node and calls `request_irq(irq, HifAhbISR, flags)`.
- *The ISR.* `HifAhbISR` touches no HIF register. It counts, masks the
  line (`__disable_irq()`), sets `GLUE_FLAG_INT_BIT` and wakes the HIF
  thread.
- *The thread.* It runs `nicProcessIST`: up to `u4HifIstLoopCount`
  (`CFG_IST_LOOP_COUNT`, 1 or 32 by build) passes of read-status-then-
  handle. The status is the enhanced block in an `CFG_SDIO_INTR_ENHANCE`
  build, the same 112-byte block 0268 reads. Then `nicEnableInterrupt`
  re-arms: `WHLPCR` (`0x04`) `INT_EN_SET` (bit 0), then `__enable_irq()`.
- *The sources.* `WHIER` (`0x14`) is programmed to `WHIER_DEFAULT`: RX0
  done (bit 1), RX1 done (bit 2), TX done (bit 0), abnormal (bit 6), and
  the firmware's software interrupts (bits 8–31). `WHISR` (`0x10`)
  carries the same bits. `WHLPCR` `INT_EN_CLR` (bit 1) disables.

**Ours today.**

- *No interrupt at all.* The mac80211 driver is registered on the consys
  device (`mt6797_mac_register(dev, owner->fw_hif, ...)`). The consys
  node's single interrupt is SPI 130 through `mediatek,mt6797-sysirq`,
  the WMT/BTIF line, and the consys probe requires exactly that one
  (`of_irq_count == 1`, SPI 130). The WLAN HIF's SPI 283 is not
  described anywhere in our device tree. The `wifi` child
  (`mediatek,mt6797-wlan`) carries no interrupt and is disabled.
- *The cadence, from `join-pump.h` at `CONFIG_HZ=250`.* With nothing
  pending (no transmit queued, in flight or owed), the worker re-queues
  after 20 ms, which is 5 jiffies. Pending without progress, it makes 32
  immediate passes, then sleeps 1 ms, which rounds to one 4 ms jiffy.
  Frames that arrive while the transmit side is idle or stalled wait up
  to 4–20 ms before any pass reads them. Otherwise the worker spins:
  about 10,000 passes a second, 96 % of block reads empty (boots V–X).

**The smallest bridge: the interrupt as a wake source, the poll kept as
the safety net.**

1. *Device tree:* `interrupts = <GIC_SPI 283 IRQ_TYPE_LEVEL_LOW>` on
   the `wifi` child node, through the same sysirq parent. The consys
   node and its single-interrupt check stay as they are.
2. *Consys:* parse the child's interrupt (`of_irq_get` on the child) and
   pass it to `mt6797_mac_register`. A missing interrupt keeps today's
   polled behaviour.
3. *HIF:* a locked 32-bit write for `WHIER` and `WHLPCR`, through the
   same command-setup path the reads use. At the data phase's opening,
   `WHIER = WHIER_DEFAULT` and `WHLPCR = INT_EN_SET`, each read back and
   recorded. At its end, `WHLPCR = INT_EN_CLR`.
4. *mac80211 driver:* `request_irq` with a hard handler that, like the
   vendor's, touches no HIF register: `disable_irq_nosync`, count, and
   `mod_delayed_work(join_work, 0)`. At the end of each pass the worker
   re-enables the line if it had been masked, the vendor's
   `nicEnableInterrupt` point. `WHISR` is read-cleared by the passes
   already in place (the block read, or the transmit status read).
5. *Unchanged:* the pump's delays stay as the fallback, so a missed
   interrupt costs today's latency, never a stall. Batching, the
   ledger, depth 12, `0x87`, HT and the records stay too, and transmit
   aggregation stays off.
6. *Records:* interrupts taken, worker wakes they caused, wakes that
   found work, `WHIER` and `WHLPCR` before and after, passes a second,
   empty block reads.

**Risks named before the code.**

- *An interrupt storm.* The line is level-low; the hard handler masks it
  before returning, so a storm is bounded to one wake per pass.
- *Concurrent HIF access.* No HIF register is touched in hard-interrupt
  context; every access stays in the serialized worker.
- *Ownership.* The interrupt is armed only in the data phase, under
  driver ownership, and cleared before the lifetime's cleanup.
- *Unbalanced enable.* One flag set by the handler and cleared by the
  worker's single `enable_irq`.
- *Two unknowns, measured by the boot itself:* whether the firmware
  already left `WHIER`/`INT_EN` armed (the before values), and whether
  SPI 283 fires at all on this board (the interrupt count).

## 38. Boot AA (predeclared, 2026-10-25, to be implemented after review): the receive interrupt as a wake source

**Implemented (owner-reviewed, 2026-10-25).**

- [0297](../../patches/proposals/0297-dt-bindings-soc-mediatek-mt6797-consys-allow-the-WLAN-HIF-interrupt.patch):
  the binding allows one optional interrupt on the `wifi` child.
- [0298](../../patches/proposals/0298-arm64-dts-mediatek-gemini-describe-the-WLAN-HIF-interrupt.patch):
  the Gemini device tree describes SPI 283, level low, through sysirq;
  compiled `<0x00 0x11b 0x08>`, with the consys node's SPI 130
  unchanged.
- [0299](../../patches/proposals/0299-wifi-mt6797-arm-and-disarm-the-HIF-interrupt-sources.patch):
  `MT6797_HIF_RX_IRQ`; the locked function-1 register write and
  `mt6797_hif_set_interrupt()` (`WHLPCR` `INT_EN_SET`/`INT_EN_CLR`, both
  registers read before and after). Owner, before the build: only TX
  done, RX0 done and RX1 done are armed, `WHIER = 0x00000007`. The
  vendor's `WHIER_DEFAULT` adds the abnormal source and the firmware's
  software interrupts, conditions the poll already catches, and the
  abnormal source is what poisoned the HIF in boot 3 of 0268.
- [0300](../../patches/proposals/0300-wifi-mt6797-wake-the-worker-on-the-WLAN-HIF-interrupt.patch):
  consys hands the child's interrupt to the client, which requests it
  masked. The hard handler masks the line and re-queues the worker. The
  worker arms, re-arms and disarms at the end of its pass. The pump's
  delays stay.

Built warning-free at W=1 with the option off and on; checkpatch,
`dt_binding_check` and `CHECK_DTBS` clean for these changes.

*Arming happens once per data phase, not once per boot.*
`hif_irq_arm_tried` is cleared at every data phase's opening, beside
the per-lifetime counters (`taken`, `rearmed`). So the interrupt is live
in every lifetime's data phase, including the three lifetimes of the
access-point-loss gate. "Wakes that
found work" is read from the batch counters (empty against total block
reads), beside interrupts taken and the pass census. The lifecycle
fragment sets `CONFIG_MT6797_HIF_RX_IRQ=y` on boot X's admitted profile.

**The change.** §37's bridge, behind `CONFIG_MT6797_HIF_RX_IRQ` in the
lifecycle fragment, on boot X's admitted profile (batching, HT, the
records, `0x87`, depth 12; no transmit aggregation). It touches the
device tree's `wifi` child, the consys owner, the HIF register writes
and the mac80211 worker.

**The reading: the device-side receive rate and frames per second, not
the aggregate.**

**The prediction, corrected by the owner (2026-10-25): this boot tests
the line, not the throughput.** The pump's delays are unchanged, so the
worker still polls at full rate. It still performs about 12,500 block
reads a second with 96 % empty, the cost §37 identified. The interrupt
adds at most about 200 µs of wake latency against a 600 µs per-frame
service. No throughput change is expected.

| Reading | Meaning |
|---|---|
| `HIF interrupt armed: status=0 whier=…>0x00000007 whlpcr=…>…` (INT_EN set) and `taken > 0` | the line fires on this board: **the boot's real result** |
| `taken = 0` with a clean data phase | the firmware did not assert it, or the enable path is incomplete: record both register pairs and stop; do not chase it in the same session |
| any regression in refusals, refusals per TID, the ledger, or frames per second | arming perturbs the path: revert |
| arm or disarm `status != 0`, or a mask-count warning from the interrupt core | the register path or the enable/disable accounting is wrong |

`taken`, `rearmed` and the pass census are quoted separately. With the
poll unchanged, the empty-read ratio will look identical to boot X's,
and that must not be read as "the interrupt did nothing".

The UDP probe stays retired. The precondition and stop rule of §35 apply
in their general form: the link carries boot X's volume (about 1,200
frames a second in transmit), or the boot stops and nothing is graded.

**A fragment defect caught before staging (2026-10-26).** The first
build of boot AA carried `CONFIG_MT6797_TX_AMPDU=y`. Withdrawing
aggregation after boot Y deleted the fragment line, and 0296's option
defaults to `y`, so the deletion re-enabled it. No boot ran with it
unintentionally: boot Z set it on purpose, and nothing was built from
the fragment in between. The fragment now says `# CONFIG_MT6797_TX_AMPDU
is not set` explicitly, and the build's config is checked for it before
staging. That package was not staged.

### Boot AA result (2026-10-26, 00:28 UTC): the interrupt arms cleanly and never fires; §38's `taken = 0` row; stopped there

Build `348be4c6` (0297–0300, `HIF_RX_IRQ` with `WHIER` `0x00000007`,
transmit aggregation off, boot X's profile), boot2 `6f24c213…` over boot
Z's `f775c477…`, mainline boot `600b600e…`, returned to Gemian
`9a690b5a…` by the session's own reviewed return (live identity checked
afterwards); log complete through the seal (189,496 bytes). Clean
verdict: `session_exit=0`, `all_pass=True`, `verdict_failed=[]`, no
warning.

**The line.**

- Attached: `one-shot WLAN HIF interrupt attached: irq=218 status=0` (SPI
  283 mapped through sysirq).
- Armed at the data phase's opening: `status=0
  whier=0x00000000>0x00000007 whlpcr=0x00000100>0x00000101`. The firmware
  had left every source disarmed, the write armed TX, RX0 and RX1 done,
  and the enable bit now reads set.
- Disarmed at its end: `status=0 taken=0 rearmed=0
  whlpcr=0x00000101>0x00000100`.
- **No interrupt was taken** in a 44.3 s data phase that received 45,673
  frames and completed 52,739 transmits. No interrupt-core warning
  (unbalanced enable, spurious or unhandled interrupt) appears in the
  log.

**Nothing else moved.** `rx_refused=0`, `tx_tid_refused=0`, the ledger
exact (`expired=0 pid_faults=0 left_pages=0 dropped_full=0
tx_failed=0`), sampled reports 824 of 824 at status 0 and `0x0087`. About
1,191 transmit frames a second (52,739 in 44.3 s), as in boot X. TX
22.16 (chunks 23.6, 24.3, 20.9, 24.2, 24.0), RX 16.22 (19.7, 21.6, 10.1,
20.9, 14.0, the laptop's own send rate falling in both dips), within
the series' spread. As predicted with the poll unchanged, the pass census
(526,017 passes in 44.3 s) and the empty-read ratio (499,834 of 530,073
block reads, 94 %) are as before. That says nothing about the
interrupt, which was never taken.

**Against §38's table: the `taken = 0` row.** "The firmware did not assert
it, or the enable path is incomplete": both register pairs are recorded
above, and the line is not chased in this session. Candidates for the
later, bounded look:

- the continuous poll read-clears `WHISR` (in the block read) before the
  level reaches the interrupt controller;
- a further gate between the HIF and the AP's interrupt controller (a
  CONSYS or infra mask the vendor sets elsewhere);
- the line itself: SPI 283 and its polarity through sysirq on this
  board.

Boot AB (§39) depends on the line firing and waits on that look. The
option stays in the profile, harmless as measured; whether it stays, or
leaves until the line is understood, is the owner's call.

**Owner, 2026-10-26: the driver half works, the source half does not.**
`irq=218`, `whier 0x0>0x7`, `whlpcr 0x100>0x101`, disarmed cleanly,
`taken=0 rearmed=0`, zero refusals, the ledger exact. Arming and
disarming perturb nothing: transmit at 22.16 (chunks to 24.28) is within
the series' best. Boot W's 22.58 remains the highest aggregate. So the
patches cost nothing when they do nothing, which matters when a gain is
later attributed.

**The missing register: the wrapper's line mask at `0x200`.** The
vendor's `sdio.h` defines `__disable_irq()` as `writel(0x01, base +
0x200)` and `__enable_irq()` as `writel(0, base + 0x200)`.
`nicEnableInterrupt` calls `__enable_irq()` right after `WHLPCR
INT_EN_SET`, and the ISR calls `__disable_irq()`, the one raw write its
top half makes. The vendor also brackets every register access in
`sdio_bus_driver.c` with the pair, which our handler does not need
because it touches no register. Neither 0299 nor 0300 writes `0x200`, so
the line was most likely masked at the wrapper.

[0301](../../patches/proposals/0301-wifi-mt6797-also-unmask-the-HIF-wrapper-s-interrupt-line.patch)
adds exactly that to the arm and disarm paths. Arm writes `0x200 = 0`
after `INT_EN_SET`; disarm writes `0x200 = 0x01` before `INT_EN_CLR`.
Each is read back and recorded as `mask=before>after` on the `armed` and
`disarmed` lines. No other change. Built warning-free at W=1 with the
option off and on; checkpatch clean but for the policy `Signed-off-by`.

### Boot AA2 (predeclared, 2026-10-26): boot AA with the wrapper unmasked

The same profile as boot AA plus 0301.

| Reading | Meaning | Next |
|---|---|---|
| `mask=0x00000001>0x00000000` (or already 0), `taken > 0`, `rearmed > 0`, no change in refusals, ledger or rates | the line fires and is re-armed: the interrupt is a real wake source | boot AB (§39) proves it usable |
| `taken = 0` with the wrapper unmasked | the poll's read-clear: the block read clears `WHISR` about 12,500 times a second (499,834 of 530,073 empty in boot AA) before the line is latched | the next step is not another register but boot AB's design change: while armed, the receive poll runs only on a wake plus a slow (about 10 ms) fallback. That is also where the 15–25 % receive gain lives, so both outcomes converge on the same change |
| arm or disarm `status != 0`, a mask-count warning, or any regression in refusals, ledger or frames per second | the wrapper write perturbs the path | revert |

### Boot AA2 result (2026-10-26, 00:38 UTC): void, the join failed before the data phase; the interrupt never reached its arming point

Build `82717df4` (boot AA plus 0301), boot2 `561e2025…` over boot AA's
`6f24c213…`, mainline boot `3399b0a9…`, returned to Gemian `27ee846e…` by
the session's own reviewed return (live identity checked afterwards);
log complete through the seal (148,778 bytes). Verdict failed: no data
phase, so nothing was measured.

**What happened.**

- The authentication exchange completed (`join TX: subtype=11`, done
  status 0; `join RX: subtype=11 status=0`).
- Our association request was sent and acknowledged (`join TX:
  subtype=0 pid=2`, done status 0).
- No association response was received. The access point's first
  EAPOL-Key frame then arrived and was refused at `predicate=association`
  (`bss=15 activated=0 bss_configured=0`), and the join stopped: `join
  stopped: status=-95 first=-95 ... branch=1`. mac80211 retried the
  association once and aborted when the driver had stopped.
- The access point evidently accepted the association, since it began
  the four-way handshake; our receive path never saw its response.

This is the first such join failure in the series: no earlier boot's
log carries `predicate=association` or a `-95` stop.

**Not attributable to 0301 or the interrupt.** The interrupt was
attached masked at registration (`attached: irq=218 status=0`) and is
armed only at the data phase's opening, which this lifetime never
reached. There is no `armed` line, and the wrapper mask at `0x200` was
never written. The boot is void for §38's question; the same image
answers it on a re-run.

**What boot AA2 found in the driver (owner, 2026-10-26, checked against
the source).** The `-95` stop came from `mt6797_mac_mgd_prepare_tx`
(0136). Its admission requires `!(mac->join_seen & BIT(subtype))`, and
`mt6797_mac_tx` (0129) sets that bit when it queues the frame. So
mac80211's association retry ("try 2/3") failed the predicate, set
`first_error = -EOPNOTSUPP` and `closing = true`, and the worker stopped
before the retry was queued: there is no second association request in
the log. The lost association response is a normal radio event, one in
the 94 retained logs; the defect is that the driver permits one
association attempt where mac80211 permits three. It is fixed as its own
change before the reconnect gate (below).

### Boot AA3 (predeclared, 2026-10-26): §38 re-run on the unchanged image

The same image as boot AA2 (`561e2025…`, build `82717df4`), no build.
The reviewed installer reads boot2's full partition first. It reports
`skipped-already-matching` if boot2 still holds the image, and writes
and reads it back otherwise. The branches are §38's, as written:

| Reading | Next |
|---|---|
| `mask=0x…1>0x…0` with `taken > 0` (and `rearmed > 0`), no change in refusals, ledger or rates | boot AA4 (§39) as written: capture the receive gain |
| `taken = 0` with the wrapper unmasked | the poll's read-clear is the suspect: boot AA4 changes purpose (below) |
| arm or disarm `status != 0`, a mask-count warning, or any regression | revert |
| the join fails before the data phase again | void again; the bounded-retry change comes first |

### Boot AA3 result (2026-10-26, 00:49 UTC): the wrapper was never masked; the line stays silent; §38's second row

Mainline boot `ee702c23…`, build `82717df4`. Boot2 was verified, not
written: the installer read the full partition as `561e2025…` and
reported `skipped-already-matching`. Graded `all_pass`, with
`verdict_failed` empty. The session's reviewed return reached Gemian
`cfbcce3f…`.

**The interrupt.**

```
HIF interrupt armed:    irq=218 status=0 whier=0x00000000>0x00000007 whlpcr=0x00000100>0x00000101 mask=0x00000000>0x00000000
HIF interrupt disarmed: irq=218 status=0 taken=0 rearmed=0 whlpcr=0x00000101>0x00000100 mask=0x00000000>0x00000001
```

- *Observed:* the wrapper line mask at `0x200` already reads 0 before
  0301's arm write, and the disarm write of `0x01` reads back as 1. The
  register is live and writable. It was unmasked at arm time.
- *Observed:* `taken=0` across a 41.6 s data phase, with WHIER `0x7`,
  WHLPCR `INT_EN` set and the wrapper unmasked.
- *Result (the negative that matters):* the wrapper mask was never the
  cause, and the three device-side enables are not sufficient. 0301's
  arm write changes nothing on this firmware state.
- *Withdrawn inference (owner correction, 2026-10-26):* this record first
  named the poll's read-clear as the remaining suspect. That cannot
  explain the boot. The block read clears only the firmware's software
  interrupts and the own-back interrupt. The three enabled sources (TX
  done, RX0 done, RX1 done) are read-only: receive-done follows the
  length FIFO's occupancy and falls only when the queue is read down.
  So every source we armed stayed asserted from the firmware's write
  until our drain. At 12,438 passes a second that is up to about 80 µs,
  on each of the 22,090 reads that found frames. WHIER `0x7`, WHLPCR
  bit 0 reading back 1 and the wrapper mask at 0 held all 22,090 times,
  and the interrupt controller delivered none of them.
- *Open:* whether the line reaches SPI 283 at all (level low through the
  sysirq inverter). Boot AA4 (§39) reads the controller's pending state
  to decide it.

**The rest, against boot AA.** Nothing regressed.

| | Boot AA | Boot AA3 |
|---|---|---|
| TX aggregate (chunks) | 22.16 (20.9–24.3) | 22.57 (21.8–24.9) |
| RX aggregate | 16.22 | 20.48 |
| RX device chunks | 19.67, 21.61, 10.12, 20.94, 13.96 | 22.45, 22.62, 22.96, 21.38, 17.95 |
| block reads, empty | 530,073, 94.3 % | 521,463, 95.8 % |
| passes/s | — | 12,438 |
| transmit `expired`/`pid_faults`/`left_pages` | 0/0/0 | 0/0/0 |
| sampled status 3 (air loss) | 0 | 2 of 779 (warning `tx_air_losses=2`) |
| receive refusals | 0 | 16, all `pn=equal` Retry |

- The receive rise matches boot V's good chunks (19.5–22.3). Boot AA's
  low aggregate came from two sender-side dips, not the interrupt; the
  image is the same. This is noise between runs, not a gain.
- The 16 refusals are one shape: `fc=0x4a88`, Retry set, the PN equal
  to the TID-0 pairwise counter. They are retransmissions of frames
  already delivered, refused as they must be (boot V's single refusal
  had the same shape). No other field was refused. `rx_llc_mis=13`.

**The join, for the next patch.** The association response arrived at
14.20 s. The first EAPOL-Key was refused at `predicate=bss-interval`
24 ms later (`activated=0 bss_configured=0`) and admitted only on the
access point's retransmission at 15.22 s, a 996 ms stall. That is the
same sequence and the same 996 ms as boot AA, now on two consecutive
clean boots. The early-M1 change below is predicted to remove it.

**The branches, read honestly.**

- *First row, not taken:* it needed `mask=0x…1>0x…0`, and the mask never
  read 1.
- *Third row, not taken:* the rates rose, and the 16 refusals are Retry
  duplicates with the PN equal, correct refusals rather than a
  regression.
- *Second row, taken:* `taken=0` with the wrapper unmasked. Its planned
  follow-up, the slow poll as a read-clear test, rested on the withdrawn
  inference. It is replaced by the controller-side probe (§39, owner,
  2026-10-26).

**The measured design ceiling without aggregation (owner, 2026-10-26).**
TX 22.6 and RX 20.5 Mbit/s aggregate, both on the fixed HT MCS7 rate
with the depth-12 pump. This is the best pair in the series.


## 39. Boot AA4 (predeclared, 2026-10-26): the HIF line at the interrupt controller

The slow-poll boot first declared here is held. Its premise, that the
block read clears the sources, is withdrawn (§38, boot AA3). One probe
decides the question that remains: does the HIF output reach SPI 283?

**The change (0303, with 0302).** Nothing in the poll changes. While
the interrupt is armed, the driver reads the controller's pending state
of the line with `irq_get_irqchip_state(…, IRQCHIP_STATE_PENDING, …)`
right after each status block read and before the queues it names are
read. It samples every block that names frames and one in 64 of the
others. The disarmed line prints `pending=<set>/<samples>` for blocks
with frames, `idle_pending=` for the others, and `probe_errors=`. For a
level-sensitive SPI the pending state of this SoC's GICv3 follows the
input line, so this observes the line, not our handler. 0302 removes
0301's disarm write (the vendor's disable path never writes the
wrapper mask), keeps `mask=` on both lines as the record, and adds
`whier=` to the disarmed line, so a firmware clear of WHIER during the
data phase would show. The join changes (0304, 0305) are not in this
boot.

| Reading | Meaning | Next |
|---|---|---|
| `pending > 0` with `taken = 0` | the input asserts and is not delivered: the fault is on our side of the distributor (descriptor mask state, CPU interface, priority) | inspect the irq descriptor and the `enable_irq` accounting; the HIF side is right |
| `pending = 0` over ≥ 20,000 sampled blocks that named frames | the HIF output does not reach SPI 283 | stop the poll work; the line is misrouted or gated outside the four known gates; answer it offline before any further interrupt patch |
| `taken > 0` | contradicts AA3 | record it and re-open §38 |
| `probe_errors > 0` with no samples | the controller does not report the state | the boot does not decide; record it |

The rest is read against boot AA3: transmit and receive rates, refusals
and the transmit ledger. A regression beyond the noise band means the
probe is not free, and it is removed.

### Boot AA4 result (2026-10-26, 01:09 UTC): the probe is inert; the line reading is uninformative

Mainline boot `73487b02…`, build `0c803c25`, boot2 `fc08179f…` (written
over `561e2025…` and read back in full). Graded `all_pass`, with
`verdict_failed` empty. The session's reviewed return reached Gemian
`129a25b3…`.

```
HIF interrupt armed:    irq=218 status=0 whier=0x00000000>0x00000007 whlpcr=0x00000100>0x00000101 mask=0x00000000>0x00000000
HIF interrupt disarmed: irq=218 status=0 taken=0 rearmed=0 pending=0/30980 idle_pending=0/7651 probe_errors=0 whier=0x00000007>0x00000007 whlpcr=0x00000101>0x00000100 mask=0x00000000>0x00000000
```

- *Observed:* the controller's pending state of SPI 283 read 0 on all
  30,980 frame-bearing samples and all 7,651 idle samples. No sample
  failed.
- *Observed:* WHIER was still `0x7` at disarm, so the firmware did not
  clear it during the 42.9 s data phase. WHLPCR INT_EN read 1 until the
  disarm, and the wrapper mask stayed 0, untouched by 0302's disarm.
- *Withdrawn (owner, 2026-10-26):* the first version of this note
  concluded "the line never reaches the controller". With WHIER `0x7`
  armed the line could not assert (§41: the done bits do not drive the
  host line here). The probe also sampled after the status block read,
  which acknowledges the sources. So `pending=0/30980` is uninformative,
  not a negative. The Gemian reading (§41) supersedes it.
- *Established:* 0302 works (the mask is untouched on disarm, and
  `whier=0x7>0x7`). The firmware never clears WHIER during the data
  phase. The probe is free: no change in rates, ledger or refusals.

**Branch: none taken.** The data-path conclusions stand: TX 22.58 and
RX 20.46, with no regression.

**The rest, against boot AA3.** Nothing regressed, so the probe is free.

| | Boot AA3 | Boot AA4 |
|---|---|---|
| TX aggregate (chunks) | 22.57 (21.8–24.9) | 22.58 (21.8–25.3) |
| RX aggregate (device chunks) | 20.48 (17.95–22.96) | 20.46 (21.03–21.69) |
| block reads, empty | 521,463, 95.8 % | 524,465, 94.1 % |
| passes/s | 12,438 | 12,139 |
| transmit `expired`/`pid_faults`/`left_pages` | 0/0/0 | 0/0/0 |
| sampled status 3 (air loss) | 2 of 779 | 0 of 829 |
| receive refusals | 16, `pn=equal` Retry | 1, `field=packet-type` |

The one refusal is boot R's 442-byte software-frame class
(`prefix=0xe004 status=cipher-mismatch+data`, `wlan=2`), not a data
frame; boot Y recorded it too. It is not a probe effect. The first EAPOL-Key again waited about one
second for the access point's retransmission. The fix, 0305, was
deliberately not in this boot.

## 40. The working system's interrupt registers (Gemian, 2026-10-26): unverified

**Status (owner, 2026-10-26): the register claim is not established.**
The Gemian values below were read through the direct aperture at
`0x180f0000`. That aperture is the HIF's command interface, not a
mirror of the MCR registers:

- `0x180f0008` returned `0x00010000`, `0x00020000`, `0x00030000`,
  `0x00040000` and `0x00050000` on successive reads, a counter that
  advances by `0x10000` per access.
- `0x180f0000` held `0x90000804`: the command setup for register 4
  (WHLPCR), length 4.
- `0x180f0004` held `0x101`, the last data word (INT_EN_SET with
  FW_OWN_REQ).

So "WHIER `0x1e00`" and "WHCR `0xa07f0000`" are leftovers of the last
transactions, not register values, and no decision rests on them. The
interrupt counts from `/proc/interrupts` and the vendor DT stand.
Those aperture accesses are also what restarted the device twice:
while the firmware owns the HIF, the host may touch only the
ownership, interrupt-enable and bus-status class of registers, and
anything else raises an abnormal interrupt, on which the vendor resets
the chip. **No further Gemian register reads.**

The original record follows, kept for the history.


Owner reading on Gemian (vendor kernel 3.18.41+, WLAN-GEN3), read-only
(`/proc/interrupts`, the device tree, `devmem` reads of the direct
aperture):

- *The line is live on this board.* `315: … GICv3 315 AHB_SLAVE_HIF`
  takes about 70 interrupts a second at idle.
- *Routing and polarity are ours.* The vendor DT's `wifi@180f0000` has
  `interrupts = <0 0x11b 0x8>` (SPI 283, level-low) and
  `reg = <0x180f0000 0x1100>`, identical to 0298.
- *The registers,* stable over six samples:

| Register | Gemian | Ours, armed (AA–AA4) |
|---|---|---|
| WHLPCR (`0x180f0004`) | `0x00000101` | `0x00000101` |
| wrapper line mask (`0x180f0200`) | `0x00000000` | `0x00000000` |
| WHIER (`0x180f0014`) | `0x00001e00` | `0x00000007` |
| WHCR | `0xa07f0000` | `0x00000000` |

**As first recorded (superseded above): the armed mask.** `0x1e00` enables WHISR bits 9–12, the
firmware's device-to-host software interrupts, and none of the RX0,
RX1 or TX done bits. On this configuration the firmware notifies the
host through software interrupts, and the done bits do not drive the
host line. With `0x7` armed, every gate we knew of was open and the line
still could not assert. That is what boots AA, AA3 and AA4 measured.
The wrapper mask, the read-clear and the SPI number were never the
cause. §37 chose `0x7` by keeping only the done bits of the vendor's
`WHIER_DEFAULT` and dropping its software bits. Those dropped bits were
the host line's source.

WHCR is the one other difference: Gemian runs RX-enhance (bit 16) with
a length count set. It is held for the case below where the line still
does not fire.

## 41. Boot AA5 (predeclared, 2026-10-26): WHIER 0x1e00, the probe both sides of the status read, and the join changes

**The interrupt half.**

- *0306:* arm WHIER `0x00001e00`. The handler still only masks and
  wakes. The worker's block read still clears WHISR's software bits, so
  no per-bit dispatch is added.
- *0302 is kept:* no disarm write of the mask, and `whier=` on both
  lines.
- *0303 (reworked):* reads the pending state of SPI 283 immediately
  before each status block read, and after it before the drain. Each
  sample is classified by that block's frame counts. The disarmed line
  prints `pending_before= pending_after= idle_before= probe_errors=`.
  With the right mask, `pending_before` confirms that the assertion
  precedes our drain. The sample after the read follows the
  acknowledgement, so it can only read 0, whatever the line does.

| Reading | Meaning | Next |
|---|---|---|
| `taken > 0` and `rearmed > 0` in the data phase, `whier=0x00001e00>0x00001e00`, rates, ledger and refusals unchanged | the line works; the mask was the defect | the slow poll: while armed, poll receive only on a wake plus a ~10 ms fallback; predict +15–25 % receive |
| `taken = 0` with `whier=0x1e00>0x1e00` | one difference remains: WHCR (Gemian `0xa07f0000`, ours `0x00000000`) | compare the two modes before any further poll work |
| a storm (`taken` far above the passes) | the software bits re-assert faster than the drain | the handler already masks; record it and disarm |

**The join half (0304, 0305; owner, 2026-10-26).** The probe was inert
in boot AA4, so one boot can carry these without losing attribution. A
join failure would be 0304's or 0305's, and the interrupt half reads
independently of the join. The roughly one-second EAPOL stall appeared
in boots AA, AA3 and AA4, every clean boot since the join changes were
written.

- *Predicted:* the first EAPOL-Key is admitted on the station tag
  (`bss=1`) within 10 ms of the association response, instead of
  996 ms later on the retransmission.
- *Unchanged:* `join_eapol_seen < 2`, the key handshake, refusals and
  rates.
- *Read only if it occurs:* the `join prepare:` lines record each
  authentication and association admission. A second association
  attempt is admitted only if a response is lost.
- *Revert:* any join failure, handshake change or refusal attributable
  to 0304 or 0305 reverts that patch.

The rates are read against boots AA3 and AA4, where the ceiling stands
at TX ≈ 22.6 and RX ≈ 20.5 Mbit/s aggregate. One coupling is
predeclared: a working line changes worker wake timing on the shared
worker, so a transmit move in this boot is read with the interrupt
half, not the join half.

### Boot AA5 result (2026-10-26, 01:28 UTC): early M1 works; the lifetime stopped at 6.1 s (-90 in the receive batch); the probe is no longer inert; the interrupt half is void

Mainline boot `8ec5ee88…`, build `3a2d28b8`, boot2 `345753c1…` (written
over `fc08179f…` and read back in full). The session failed
(`session_exit=1`). Its own reviewed return reached Gemian `8dbc2cc3…`
with the log sealed complete (171,203 bytes).

**The join half: as predicted, except the 10 ms figure.**

- One authentication and one association attempt (`join prepare:
  … admitted=1` twice), so 0304's retry was not needed.
- The first EAPOL-Key was admitted on `bss=1` before the activation
  (`activated=0 bss_configured=0 seen=0`) and delivered. Message 3
  followed (`seen=1`, activated).
- The association response arrived at 14.9506 s and message 1 at
  14.9751 s: 24.5 ms. That is its arrival time, the same 24 ms after
  which boots AA, AA3 and AA4 refused it. The 996 ms wait for the
  retransmission is gone. The predeclared "within 10 ms" was the wrong
  figure: the access point sends message 1 about 24 ms after its
  response.

**The interrupt half: void.**

- Armed: `whier=0x00000000>0x00001e00 whlpcr=0x00000100>0x00000101
  mask=0>0`. 0306's value reads back.
- Disarmed: `status=-5`, after the lifetime had failed, so its register
  fields are the zeroed record and not readings. `taken=0 rearmed=0`.
- `pending_before=0/721`, `pending_after=0/721`, `idle_before=0/33919`,
  `probe_errors=0`.
- *Inconclusive (owner, 2026-10-26):* 721 frame-bearing samples are 721
  opportunities, not the 20,000 the table needs. This is not "the mask
  is not the defect". The arm is verified (`whier 0x0→0x1e00`). The
  disarm's `status=-5`, with every field 0, is the HIF already closing
  after the lifetime stop, not evidence that WHIER was cleared.

**The stop.** `join stopped: status=-90 … branch=4`, 6,098 ms into the
data phase, with `CCMP receive observation: port=0 … status=-90` and
`RX batch: … failures=1`.

- *The source:* `-EMSGSIZE` on the receive path can come only from
  `mt6797_hif_transfer_size()`, on the batch's aggregated port read.
  The size check passes per-frame lengths up to 2,352 and at most 16
  frames, but the buffer is exactly 16 × 2,356 = 37,696 bytes. A block
  transfer rounds up to 512-byte blocks, so any aggregate over 37,376
  bytes becomes 37,888 and is refused as a bus failure, which poisons
  the HIF.
- *The trigger:* reaching that needs an average above 2,336 bytes per
  frame over 16 frames. That is implausible for 1,500-byte MSDUs. The
  likely trigger is one block with an out-of-range count (the single
  counted failure, clamped to 16) and lengths that are not real.
  Whether 0306's software interrupts make such a block possible is not
  shown.
- *Defect regardless of trigger:* the bound is the driver's. The comment
  that "only a bus failure is returned" is wrong for this case.
- *Not a repeating wedge:* the receive caller increments
  `rx_batch_failures` on the fill's own error before it poisons
  (`if (error) { hif->rx_batch_failures++; goto poison; }`). So
  `failures=1` is the terminal `-90` itself, and no `i < n` skip
  occurred: a skipped queue would have counted again on each pass. One
  block was refused once, and that refusal poisoned the HIF. The
  receive observation's repeated `-90` is the poisoned state's return
  value. The fix is the buffer bound (0307): every aggregate the length
  and count checks admit then transfers, and its frames are verified
  against their lengths as before. Sizing refusals are unreachable
  after it, so no worker-side relaxation is needed.

**The probe is no longer free.**

- *Observed:* 34,640 worker passes in 6.1 s (5,680/s) against boot AA4's
  12,139/s. Every pass took one "before" read. TX chunk 1 ran at
  12.86 Mbit/s against boot AA4's 25.20.
- *Inference, not separated:* AA4 sampled about 900 times a second and
  its pass rate fell 2.4 % from AA3, which suggests about 27 µs per
  `irq_get_irqchip_state()` call. One call per pass plausibly explains
  much of the 94 µs added per pass. 0306 (the firmware's software
  interrupts) cannot be excluded from one boot.

**What stands (owner, 2026-10-26).** 0304 and 0305 are validated and
kept. The first EAPOL-Key was admitted 24 ms after the association
response, the pairwise key followed at 15.1025 s, and there was no
stall: the 996 ms seen in boots AA, AA3 and AA4 is gone. 0304 was not
exercised (one attempt each). 0306's WHIER value arms and reads back.
The interrupt reading and the rates are open.

**The live lead: the firmware's HIF mode (owner, 2026-10-26).** On
Gemian the HIF line takes about 9 interrupts a second at idle and about
8,310 a second while receiving 20 MB (about 80 Mbit/s): one per frame or
small burst. So the software interrupts are the data notification. Ours
raised none with the same mask, so the remaining difference is the
firmware-side configuration. §40's held case is now the case: Gemian's
WHCR reads `0xa07f0000`, ours `0x00000000`.

*Offline, the pinned public vendor source.*

- Its WHCR writes are these. `nicSDIOInit` clears the length count
  (`WHCR_MAX_HIF_RX_LEN_NUM`, bits 8–13) and sets it to
  `SDIO_MAXIMUM_RX_LEN_NUM`. It clears RX-enhance (bit 16), because
  `CFG_SDIO_RX_ENHANCE` is 0. `nicRxInitialize` sets the count to
  `CFG_SDIO_MAX_RX_AGG_NUM` (0). At the end of `wlanAdapterStart`, after
  firmware ready, `HAL_SET_INTR_STATUS_READ_CLEAR` clears
  `W_INT_CLR_CTRL` (bit 1) and `HAL_SET_MAILBOX_READ_CLEAR(FALSE)`
  clears `RECV_MAILBOX_RD_CLR_EN` (bit 2). Then `nicEnableInterrupt`
  runs.
- On a WHCR that reads 0, every one of those writes is a no-op, and none
  sets bits 16–22, 29 or 31. As published, the driver does not produce
  `0xa07f0000`.
- So those bits are set by the firmware, by a vendor build that differs
  from the pinned source, or they are not the mt6630 fields at all on
  this AHB HIF.
- One cheap discriminator before any mode change: our WHCR is read
  through the indirect function-1 path, and Gemian's through the direct
  aperture at `0x180f000c`. Reading both views on our side shows
  whether the two numbers are comparable.

**The throughput consequence (owner, 2026-10-26).** With the vendor's
mask, the receive path is interrupt-driven at roughly one interrupt per
frame: about 2,000 a second at our rates. So the wake-versus-poll
question becomes worth measuring, but only after the line fires.

**The probe's cost, for the next boot.** AA5's per-pass "before" read
coincided with the pass rate halving (5,680/s against 12,139/s). If the
probe is kept at that cadence, the next boot's rates are read against
that cost, not against AA3 and AA4.

## 42. Boot AA6 (predeclared, 2026-10-26): the mask taken out of the unknowns

**Why not `0x1e00` (owner, 2026-10-26).** WHISR in the retained logs has
read only `0x0`, `0x2`, `0x3` and once `0x42` (ABNORMAL with RX0 done,
at rxbatch3's guard failure). No bit at or above 8, and so no
device-to-host software interrupt, has been set in any of our sessions,
so `0x1e00` enables sources this firmware never raises. Conversely,
with `0x7` armed the enabled bits were set (`0x2`, `0x3`) for 40 s and
the line still never fired. The defect is not a bit choice we can see.

**The change.**

- *0308:* arm the vendor's `WHIER_DEFAULT` (`0xffffff47`) with ABNORMAL
  (bit 6) and the firmware-assert software interrupt (bit 31) withheld.
  The block read fails the HIF on either, and neither is a
  notification: `0xffffff47 & ~(BIT(6) | BIT(31)) = 0x7fffff07`. The
  value first given, `0xbfffff07`, clears bit 30 rather than bit 31
  and would have armed the firmware-assert source.
- *0309:* the pending-state read now runs before one block read in
  eight, classified by that block's frame counts, so the pass rate
  stays near boot AA4's. The sample after the read is gone. The first
  take prints `first take: taken= whisr=` with the WHISR word of the
  block read in the pass the interrupt woke. The disarmed line prints
  the last block's `whisr=` beside the counts.
- *Also in this boot:* 0307 (the batch bound) and 0304–0305 (validated).

| Reading | Meaning | Next |
|---|---|---|
| `taken > 0`, with `whisr` at the first take naming the source bit | the line works and the source is identified | the poll-on-wake work, with only that bit enabled |
| `taken = 0` over ≥ 10,000 frame-bearing samples while WHISR shows `0x2`/`0x3` | an enabled bit is set and the line still does not assert | the output path or the firmware's HIF mode, never another mask; this boot closes the mask question |
| a storm | the full mask re-asserts faster than the drain | the handler masks; record it and disarm |
| the lifetime stops in the receive batch again | 0307 did not cover the cause | void |

The rates are read against boots AA3 and AA4.

**Offline item (owner, 2026-10-26).** ABNORMAL is what a host access to
a register outside the firmware-ownership whitelist raises, and the
block read touches WHCR, WHISR and the WTQCRs. So check whether any of
our status reads can run while the firmware owns the HIF. That would be
a self-inflicted abnormal path that the block read then treats as fatal.

- *What is known so far:* `hif.c` never writes the WHLPCR ownership
  bits, and every arm line read WHLPCR `0x100` (driver-own) at the start
  of the data phase, so data-phase status reads run under driver
  ownership.
- *Open:* where rxbatch3's single `0x42` happened, relative to
  ownership.

### Boot AA6 result (2026-10-26, 01:52 UTC): void again on -90 in the receive batch; the cause is the transfer-size rounding, not the buffer

Mainline boot `df1db510…`, build `4496c9b6`, boot2 `ccb73bae…` (written
over `345753c1…` and read back in full). The first stage attempt was
refused before any device action, because the preceding Gemian boot
had changed to `88a02dda…` after the aperture-read restarts. It was
re-derived with that pin. The session failed (`session_exit=1`). Its
own reviewed return reached Gemian `34cabf67…` with the log sealed
complete (174,384 bytes).

**The row taken: the fourth.** The lifetime stopped in the receive
batch again: `join stopped: status=-90 … branch=4` at 29.11 s,
15.15 s into the data phase, with `CCMP receive observation: port=0 …
status=-90` and `RX batch: … failures=1`. Transmit had completed its
five chunks (22.79, 22.39, 21.59, 20.96, then 0.04 at the stop). The
receive direction never opened its first chunk. Void, as
predeclared.

**The cause, found offline, and 0307's diagnosis corrected.** 0307 was
right that the buffer could not hold a block-rounded maximum aggregate,
but that was not what stopped these boots. `mt6797_hif_transfer_size()`
chose block mode on the four-byte-rounded size and only then rounded a
byte-mode receive to eight bytes. A DMA receive of 505–508 bytes
therefore became a byte-mode command of 512, above the 511 the count
field holds, and was refused with `-EMSGSIZE`. The batch's aggregates
are multiples of four, so the one failing size below 512 is 508: a
single frame of 501–504 bytes, or several summing to it.

- *Shown on the host:* the actual helper, swept over every payload up
  to 37,696 bytes at the 37,888-byte capacity, refuses exactly 505–508
  on receive and nothing else (`tests/run-transfer-size-test.py`).
- *Inference:* both stops were a 508-byte aggregate. The log keeps no
  block, so the size itself is not recorded.
- *Not shown:* why only AA5 and AA6 met it. No earlier session stopped
  with `-90`, though DMA receive and batching ran in every boot since V.
  The armed software-interrupt bits (0306, 0308) are new in exactly
  these two boots, and a firmware that then posts other packets would
  fit, but nothing here shows it.

0310 rounds a receive to eight bytes before the mode is chosen, so
505–508 bytes moves as one 512-byte block. Every other size keeps its
transfer. It is an inference that the device tolerates a 512-byte block
read for a 508-byte queue: the driver already reads padded whole blocks
for every receive of 512 bytes or more.

**The interrupt half: inconclusive again, now with the pass rate
restored.**

- Armed: `whier=0x00000000>0x7fffff07 whlpcr=0x00000100>0x00000101
  mask=0>0`. 0308's value reads back.
- Disarmed (`status=-5`, after the stop): `taken=0 rearmed=0`, last
  block `whisr=0x00000002` (RX0 done), `pending_before=0/456`,
  `idle_before=0/23716`, `probe_errors=0`. 456 frame-bearing samples is
  short of the 10,000 the table needs.
- *Observed:* the worker ran 193,373 passes in 15.15 s, 12,763/s, with
  the probe at one read in eight. AA5's 5,680/s was the per-pass probe,
  not its stop. The rates are comparable with boots AA3 and AA4 again:
  TX chunks 22.79–20.96 Mbit/s.

**The join half again as validated.** One authentication and one
association attempt. The first EAPOL-Key was admitted on `bss=1` before
the activation, 24.2 ms after the association response
(13.7706 → 13.7949 s), with no stall. One receive refusal, boot R's
442-byte software-frame class.

**The interrupt conclusion (owner, 2026-10-26): decisive for what it
excludes.**

- *The run:* `whier=0x7fffff07`, every bit the vendor default allows,
  with an enabled source set at the driver's own read
  (`whisr=0x00000002`), WHLPCR INT_EN set and the wrapper mask at 0.
- *The reading:* `pending_before=0/456`, `idle_before=0/23716` and
  `taken=0` over 15 s. The pending state follows a level SPI and
  latches for an edge, so the line never asserted once.
- *What the conclusion rests on (owner, 2026-10-26):* 456 frame-bearing
  samples is short of the 10,000 the table asked for. So the mask
  conclusion rests on the state at disarm, `whisr=0x00000002` with
  every legal bit armed and `taken=0`, not on the sample count. The
  arming order (below) is the untested half.
- *Excluded:* the mask, the wrapper mask, the arming order, the
  read-clear race and SPI 283.
- *What remains:* the HIF's output is not driven, on our side or by the
  firmware, in this run.

The interrupt experiment is retired from the profile:
`CONFIG_MT6797_HIF_RX_IRQ` is off. 0297–0303, 0306, 0308 and 0309 stay
in the series as diagnostics that cost nothing while the option is off.
The receive engine remains the poll.

**Where the enable lives: two candidates, both offline.**

- *Host side (the pinned public vendor source).* The vendor opens the
  WLAN function as an SDIO function behind the AHB bridge before it
  reads the chip ID: `glBusInit` calls `sdio_open()`, which runs three
  steps.
  - `ahb_sdio_enable_func`: CCCR `0x02` I/O enable `|= 1 << 1`, then
    waits for CCCR `0x03` I/O ready.
  - `sdio_set_block_size`: 512.
  - `ahb_sdio_claim_irq`: CCCR `0x04` (`SDIO_CCCR_IENx`) `|= (1 << 1)
    | 1`, function 1 and the master interrupt enable.

  The CCCR accesses are command-52 function-0 transactions (setup word
  at offset 0: data in bits 0–7, register address from bit 9, function
  0, the write flag in bit 31; the data at offset 4). Our driver makes
  no function-0 access at all: no I/O enable and no interrupt enable.
  On SDIO a function's interrupt reaches the host only with both
  `IENx` bits set. This is a concrete write the vendor makes and we do
  not, between bus open and `nicEnableInterrupt`. The vendor source
  has no other wrapper write besides `0x200`, which `__disable_irq` and
  `__enable_irq` write around every command transaction.

  *This is the AHB variant's code, checked against the pinned tree
  (owner query, 2026-10-26).* The owner read `sdio_bus_driver.c` as the
  real-SDIO build's. The gen3 Makefile selects
  `HIF_DIR := os/linux/hif/ahb_sdioLike/` for `WLAN_CHIP_ID MT6797`,
  and builds `$(HIF_DIR)ahb.o $(HIF_DIR)ahb_pdma.o
  $(HIF_DIR)sdio_bus_driver.o`. `ahb_sdioLike/ahb.c` calls
  `sdio_open()` under `#if defined(MT6797)` (line 354, in the bus
  init, before the chip-ID read), and `sdio_open()` in
  `ahb_sdioLike/sdio_bus_driver.c` writes `SDIO_CCCR_IENx` (line 443).
  The function-0 writes are made by the variant this board runs, and
  the lead stands.
- *Host side, the order (owner, 2026-10-26).* `nicInitializeAdapter()`
  writes `WHIER = WHIER_DEFAULT` (`nic/nic.c:680`), called early in
  `wlanAdapterStart` (`common/wlan_lib.c:374`), long before
  `nicEnableInterrupt`. Our only WHIER write is at the data-phase arm,
  about four seconds after the firmware boots. That ordering difference
  is untested. AA7 has the option off, so it needs its own boot.
- *The DMA engine's interrupt (owner lead, checked).* The AHB variant
  can register a second, level-low line for AP-DMA completion
  (`request_irq(MT_GDMA2_IRQ_ID, HifDmaISR, IRQF_TRIGGER_LOW, "AHB_DMA",
  …)`). In the pinned build it sits under `#if (CONF_HIF_DMA_INT == 1)`,
  and `ahb_sdioLike/include/hif.h` defines `CONF_HIF_DMA_INT 0`. The
  vendor polls DMA completion as we do. Recorded so it is not
  rediscovered as a difference.
- *Firmware side (owner).* The retained firmware's log strings name a
  host-interrupt mask of its own (`HIF INT MASK TO HOST TX/RX[%u/%u]`,
  with `HIF_ISR`, `HIF_IER`, `MAIL` and `SW_INT_CNT`). Which register or
  command feeds it is the firmware question, answered with the binary
  in the RE VM and the register table.
- *The test, when one register is named:* a single write in the arming
  path and one boot, read as §42. The CCCR `IENx` read alone, recorded
  at arm before any write, already says whether the host-side enable
  is 0.

## 43. Boot AA7 (predeclared, 2026-10-26): the receive fix, with the interrupt option off

The AA6 tree plus 0310 (receive rounding) and 0311 (a refused batch
transfer names itself), with `CONFIG_MT6797_HIF_RX_IRQ` off. The
interrupt code and the probe are compiled out. 0304–0305 and 0307 stay
in.

| Reading | Meaning | Next |
|---|---|---|
| the run completes both directions with no `-90`, rates as boots AA3/AA4 | 0310 is the fix | the reconnect gate |
| `-90` recurs, and the `RX batch refused:` line names a 505–508-byte aggregate | 0310 did not take effect | read the build |
| `-90` recurs with any other size or site | another transfer refuses; the line names it | fix that site |
| `failures > 0` or a header mismatch on a 505–508-byte aggregate, no `-90` | the device objects to a 512-byte block read for a 508-byte queue (owner, 2026-10-26): the driver had only ever issued block reads for 512 bytes or more | revisit 0310's mode choice |

On a clean run the batch line also records `max_bytes`, the largest
aggregate, and `window_505_508`, the count of aggregates of 505–508
bytes. These confirm whether the window is reachable-but-rare rather
than assumed (owner, 2026-10-26).

**The discriminator (owner, 2026-10-26).** The two boots that died this
way are the two with the probe before the block read. Boot AA4's probe
sat after it and ran 42 s clean. With the option off, that variable is
gone:

- `-90` without the probe places the cause in the data path;
- no `-90` leaves the pre-read probe inside the fill implicated, as
  well as 0310's fix.

The two cannot be separated in one clean boot. A clean AA7 is
consistent with both, so it closes the receive stop, not the
attribution.

### Boot AA7 result (2026-10-26, 02:10 UTC): clean; 0310's window was reached once and passed; the receive stop is closed

Mainline boot `f4666284…`, build `7eeb2c26`, boot2 `e4783dff…` (written
over `ccb73bae…` and read back in full). Graded `all_pass`, with
`verdict_failed` empty. The session's reviewed return reached Gemian
`fea5bf2d…` with the log sealed complete (187,930 bytes).

**The receive batch.**

```
HIF RX batch: on=1 whcr=0x00000000 reads=474225 aggregates=24500 frames=37750 empty=449725 max=16 max_bytes=25600 window_505_508=1 failures=0 credits=49730
```

- *Observed:* no `-90` and no `RX batch refused:` line, with
  `failures=0` over 24,500 aggregates.
- *Observed:* one aggregate of 505–508 bytes. Before 0310 that size was
  refused with `-EMSGSIZE` and stopped the lifetime. Here it moved as
  one 512-byte block, and no failure or header mismatch was counted. So
  the device accepts the block read (§43's added row did not occur).
- *Observed:* the largest aggregate was 25,600 bytes. 0307's bound was
  never approached, which is what a correct bound change looks like
  when the cause is elsewhere.
- *The discriminator, resolved in 0310's favour (owner, 2026-10-26).*
  §43's caveat, that the probe and the fix cannot be separated, no
  longer stands. The exact size 0310 makes safe occurred once in 43 s
  and transferred as a 512-byte block, with the interrupt code
  compiled out. So the fault was size-specific, and the size occurs
  harmlessly now. One occurrence per roughly 40 s matches AA5 stopping
  6 s into its data phase and AA6 at 15 s. It was present in every
  boot, and earlier boots happened not to meet it.
- *Permanent instruments:* 0310, 0311 and the `max_bytes` and
  `window_505_508` counters stay. Each data phase gives one number for
  whether and how often the window recurs, at no cost when it does not.

**Branch taken: the first row.** 0310 is the fix. The receive stop is
closed.

**The rates: below boots AA3/AA4, not attributed to the change.**

| | Boot AA4 | Boot AA7 |
|---|---|---|
| TX aggregate (chunks) | 22.58 (25.20, 25.17, 25.26, 21.93, 21.81) | 17.94 (7.88, 19.04, 22.88, 22.95, 22.45) |
| RX aggregate (device chunks) | 20.46 (21.03–21.69) | 15.42 (12.65, 15.38, 16.99, 21.75, 14.49) |
| device TCP retransmissions, TX | 8 | 444 |
| sampled transmit status 3 (air loss) | 0 of 829 | 0 of 733 |
| passes/s | 12,139 | 11,016 |
| transmit `expired`/`pid_faults`/`left_pages` | 0/0/0 | 0/0/0 |

- *Transmit:* the loss is in chunks 1–2. Chunks 3–5 ran at 22.45–22.95,
  AA4's band. The firmware reported every sampled frame delivered
  (status 0), so the 444 retransmissions are end-to-end losses with no
  air-loss signature at the radio.
- *Receive:* the dips came with an empty device receive queue, and with
  the laptop's own send rate low in the same chunks (host 15.21, 17.31,
  21.73, 25.01, 21.88). The flow slowed at the sender, as boots T, U
  and V recorded.
- *Inference:* nothing in this boot's changes acts on these frames.
  0310 alters one aggregate size, 0311 only records, and the interrupt
  code is compiled out. The run reads as path variance.
- *Stated plainly (owner, 2026-10-26):* AA7 is 17.94 TX (7.88 on chunk
  1, then 19.0–23.0) and 15.42 RX. AA3 and AA4 were 22.6/20.5 and AA
  was 22.2/16.2. Its first transmit chunk is a third of its last four,
  so it is not "rates as AA3/AA4". No cold start is established that
  would justify excluding chunk 1: AA4's chunk 1 was 25.2. So the
  ceiling statement becomes a best case with a typical band. Best case:
  TX 22.6 and RX 20.5 Mbit/s aggregate (AA3, AA4). Typical band over
  the clean HT-MCS7 depth-12 runs (AA, AA3, AA4, AA7): TX 17.9–22.6 and
  RX 15.4–20.5.
- *Informational flags:* `counts_ok`, `duration_pass` and
  `connected_lifetime_trial_pass` read false on this clean run, as on
  every clean run since boot S. They are retained fields from earlier
  protocols, not gates (`retained_not_gated` in the verdict), and
  `verdict_gates` were all true. A pass is not a failure because they
  are false.

**The join, a third time.** One authentication and one association
attempt. The first EAPOL-Key arrived with the association response (it
was admitted 0.12 ms later, in the same pass) and was admitted on
`bss=1` before the activation. One receive refusal, boot R's 442-byte
software-frame class.

## 44. The reconnect gate (predeclared, 2026-10-26): the access point's own loss on the AA7 image

The only user-facing path untested since the WMM rewrite. It costs no
new mechanism, and it is the first boot that can exercise 0304's retry
admission under real loss (owner, 2026-10-26).

**The run.** The lifecycle harness of the
[AP-loss gate](LIFECYCLE_RESULT.md#ap-loss-gate-result-2026-10-25-1548-utc--three-lifetimes-the-loss-was-the-access-points-own-inactivity-disassociation-reported-as-reason-4-and-the-station-rejoined-within-2-s-of-its-rearm):
three supplicant-driven lifetimes, one chunk per direction. Cycle 2 is
kept connected under the harness's light periodic probes until the
access point's own inactivity disassociation (about six minutes; no
owner action). Cycle 3 must rejoin. The image is boot AA7's
(`e4783dff…`, build `7eeb2c26`), which boot2 already holds, so the
installer should report `skipped-already-matching`. The candidate is
composed through the AA7 chain, whose composer and validator know the
current image. Only the measurement harness is the lifecycle one.

**Predicted.**

- The loss is reported (`connection loss report: source=monitor
  reason=4 class=air`). The driver ends the data phase with
  `connection-loss`, runs the three-stage cleanup with credits
  returned and slots retired, removes both keys and re-arms
  (`lifetime=2`). Cycle 3 scans, joins, completes the handshake and
  DHCP, and its data phase opens with its probes answered. The log is
  complete through the seal.
- The ledger is clean across the loss: every lifetime ends with
  `expired=0 pid_faults=0 left_pages=0`. There is no `join stopped`,
  no `-90`, and `window_505_508` is still counted, in each lifetime.
- *Reconnect time,* now that the one-second EAPOL stall is gone. In the
  AP-loss gate the loss report (386.695 s) was followed by the rearm
  (386.827 s), the association response (388.531 s), message 1 refused
  24 ms later and delivered only at 389.559 s, and the group key's
  credit (389.635 s). That is 2.94 s from loss to group key, 1.10 s of
  it from association response to group key. Predicted here: about
  0.1 s from association response to group key, and about 1.9–2.0 s
  from loss to group key, roughly a second less.
- *A lost management frame on the rejoin* must be absorbed by 0304's
  second attempt (`join prepare: … assoc_attempts=1 admitted=1`)
  rather than stopping the join, the property boot AA2 showed missing.
  This is read only if it occurs.

| Reading | Meaning | Next |
|---|---|---|
| the loss, the rearm and the rejoin as predicted, the ledger clean, reconnect about a second faster | the reconnect path holds on the WMM/HT tree, and early M1 shortens it | the WHIER-order boot (§45) |
| no loss within the harness's wait | the access point kept the station (its timer, or the probes) | record it; the gate is not tested |
| loss but no rejoin, or a `join stopped` on the rejoin | read the rejoin's scan, prepare and join records | fix that site before anything else |
| `-90` or a refused batch transfer | 0310/0311 did not cover a case | void; the refusal line names it |

**Result (2026-10-26, 02:25 UTC): the first row.** The access point's
own loss (`reason=4`), the rearm and the rejoin. The ledger was clean
across the loss, with no `-90`, and `window_505_508` was counted in
every lifetime. The loss report to the group key took 1.97 s, against
the AP-loss gate's 2.94 s. The full record is in
[the lifecycle result](LIFECYCLE_RESULT.md#reconnect-gate-result-2026-10-26-0225-utc--the-access-points-own-loss-on-the-wmmht-tree-rejoin-with-keys-197-s-after-the-loss-report-about-a-second-faster-than-the-ap-loss-gate).
The session's `session_exit=1` is the lifecycle classifier's two-cycle
default; regraded with the pinned cycles, it passes. 0304's retry was
not exercised.

## 45. The WHIER-order boot (predeclared, 2026-10-26; after §44): one variable

The interrupt option is re-enabled for this boot only. WHIER is written
`0xffffff47` (the vendor `WHIER_DEFAULT`) in the start path before the
firmware boots, in the vendor's `nicInitializeAdapter` order. The
data-phase arm is unchanged.

- *Predicted:* `taken > 0`, if the firmware's own host-interrupt mask is
  set at its initialization from the WHIER it finds.
- *If `taken = 0` again:* the ordering is not it either, and the
  firmware's mask is set by an initialization command. That is a
  question for the RE VM and the firmware image, not for a boot.

The patch is written and shown for review after §44 runs. The AHB
variant's CCCR `IENx` lead (§42) stays recorded; it is not this boot's
variable.
