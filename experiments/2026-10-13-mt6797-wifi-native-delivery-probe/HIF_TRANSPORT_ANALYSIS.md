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
