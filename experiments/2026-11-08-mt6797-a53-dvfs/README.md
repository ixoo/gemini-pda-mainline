# Experiment: A53 voltage scaling, CCI and boot integration on MT6797

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-08-mt6797-a53-dvfs` |
| Status | `running`: V0-V3 passed on the station; V4 stopped on a kernel BUG (required OPPs, 2026-11-08), nothing written; fixed in `0673`/`0674`, which need a new image; boot gate stays off |
| Subsystem | DA9214 BUCKA/BUCKB, VSRAM_L LDO, MCUMIXED PLLs incl. CCI, cpufreq-dt, mtk-cci-devfreq, energy model |
| Device variant | Named Gemini PDA development unit, mainline station on boot2 |
| Date(s) | 2026-11-08 |
| Investigator(s) | Julien Etienne; Claude (analysis, code) |
| Tracking issue | none |

## Question or hypothesis

The [A53 cpufreq experiment](../2026-11-07-mt6797-a53-cpufreq/README.md) scales
CPU0-7 at the firmware's fixed 1.00 V. Can the clusters run the whole vendor
range instead, 221-1547 MHz on CPU0-3 and 325-2002 MHz on CPU4-7, with VPROC1
and VSRAM_L set for each point in the vendor's order and the CCI following
the faster cluster? Can all of it then load at boot behind a gate?

The hypothesis is yes. It fails if a voltage or selector readback differs from
the request, if VSRAM_L is ever below VPROC1, if a measured clock is off, if a
hash differs, if a driver faults, or if the CCI does not follow the clusters.

## What this builds

Patches, in series order (`patches/series` and `patches/series-a53-station`):

| Patch | Change |
| --- | --- |
| [`0656`](../../patches/proposals/0656-clk-mediatek-mt6797-mcusys-let-the-clusters-reach-th.patch) | The clock driver limits each cluster to the top of the vendor table (1547 and 2002 MHz) instead of its boot rate. It refuses a post-divider change unless the old or the new rate is at least 1092 MHz (MAINPLL), so the rail always supports the 2 us bridge |
| [`0657`](../../patches/proposals/0657-dt-bindings-clock-mediatek-add-the-MT6797-CCI-PLL-in.patch), [`0658`](../../patches/proposals/0658-clk-mediatek-mt6797-mcusys-add-the-CCI-PLL.patch) | The CCI PLL (ARMPLL2, CON1 `0x1001a224`, mux bits 7:6, divider bits 19:15, MCU FHCTL channel 2), up to 988 MHz, as Gemian's `mt_cpufreq.c` drives it (`hopping_id = MCU_FH_PLL2`) |
| [`0659`](../../patches/proposals/0659-regulator-da9213-legacy-let-consumers-set-the-buck-v.patch) | A writable build of the legacy DA921x provider. BUCKA and BUCKB voltages from a `regulators` node, set by one read-modify-write of `0xd7`/`0xd9` with a read back, waiting 1 us per 10 mV (at least 25 us). No enable or disable operation, so BUCKB's enable bit stays with the A72 module. The probe checks identity only |
| [`0660`](../../patches/proposals/0660-dt-bindings-regulator-add-the-MediaTek-MT6797-CPU-SR.patch), [`0661`](../../patches/proposals/0661-regulator-add-the-MediaTek-MT6797-CPU-SRAM-LDO.patch) | VSRAM_L as one regulator over the eight INFRACFG_AO LDOs, writing the vendor's selector pattern into `CPULDO_CTRL_1`/`_2`. It sets only selectors 3-15 (900-1200 mV), refuses to probe unless all eight LDOs are enabled and on one selector, and never switches them |
| [`0662`](../../patches/proposals/0662-soc-mediatek-add-an-MT6797-CPU-rail-and-SRAM-LDO-cou.patch) | A built-in regulator coupler: VSRAM_L = clamp(VPROC1 + 10 mV, its DT minimum, 1.2 V), raised before VPROC1 and lowered after it |
| [`0663`](../../patches/proposals/0663-PM-devfreq-mtk-cci-make-the-intermediate-clock-optio.patch)-[`0665`](../../patches/proposals/0665-PM-devfreq-mtk-cci-add-MT6797.patch) | mtk-cci-devfreq with an optional intermediate clock (the MT6797 CCI PLL changes rate glitch-free itself) and an MT6797 entry; the passive governor follows cpufreq |
| [`0666`](../../patches/proposals/0666-arm64-dts-mediatek-gemini-station-scale-the-A53-volt.patch) | `mt6797-gemini-pda-station-dvfs.dts`: the station-a72 tree with the DA9214 on the legacy driver (BUCKA `vproc1` 770-1200 mV, BUCKB `vproc-big` 800-1200 mV, unused), VSRAM_L coupled to it, the full LL/L/CCI tables and `cpu-supply` |
| [`0673`](../../patches/proposals/0673-PM-devfreq-passive-leave-out-CPUs-that-have-no-OPPs.patch) | After D1: the passive devfreq governor skips a CPU with no OPPs (the A72s), instead of deferring forever or failing every update |
| [`0674`](../../patches/proposals/0674-arm64-dts-mediatek-gemini-station-let-the-CCI-follow.patch) | After D1: no required-opps, so the CCI follows by interpolation; VSRAM_L floor 1.10 V, the firmware's own boot value |
| [`0675`](../../patches/proposals/0675-cpufreq-dt-set-the-OPP-of-a-CPU-with-a-supply-at-ini.patch) | After D1, found in review: cpufreq-dt sets each regulated policy's OPP at init. Otherwise CPU0-3, booting at the listed 897 MHz, would hold no voltage request on the shared VPROC1 until their first change, and CPU4-7 could lower the rail under them. CPU4-7's move off the unlisted 1274 MHz also happens here, where it can fail cleanly, instead of in the core's `BUG_ON()` path. Module only |
| [`0677`](../../patches/proposals/0677-PM-devfreq-mtk-cci-set-the-rate-of-the-OPP-it-picked.patch) | After D2 V7: mtk-cci-devfreq passes the devfreq flags and sets the rate of the OPP it picked, so an interpolated request rounds up to a CCI point for both clock and voltage. It used to take the voltage of the point below and set the raw rate. Module only |
| [`0680`](../../patches/proposals/0680-arm64-dts-mediatek-gemini-station-power-allocator-co.patch) | After D3 V9: power-allocator cooling. CPU0-7 get `dynamic-power-coefficient` (78 and 129) for an energy model; a 75 C passive control trip carries both clusters and the GPU; 100 ms passive polling; 1.5 W `sustainable-power`. Needs a new image |
| [`0682`](../../patches/proposals/0682-PM-devfreq-mtk-cci-drop-the-voltage-request-when-it-.patch) | After D3 item 3: mtk-cci-devfreq gives up its voltage request on a failed probe and in `remove()`. A deferred probe used to leave VSRAM_L at 1.20 V (and, by inference, VPROC1 at the CCI's top point), because putting a regulator consumer does not settle the rail again. Module only |
| [`0687`](../../patches/proposals/0687-arm64-dts-mediatek-gemini-station-weight-the-LL-clus.patch) | After the weighted V9p: the soc-thermal control maps carry `contribution` 4096 for LL and 1024 for L and the GPU, the weights that run tested at run time. Device tree; next non-V11 image |
| [`0726`](../../patches/proposals/0726-PM-devfreq-mtk-cci-restore-the-boot-voltage-instead-.patch) | Fixes `0682`: a request of 0 to INT_MAX is clamped to VPROC1's 770 mV floor, not dropped. With no CPU policy (station-work-102 and -103), that put the rail under the boot rates and hard-hung the SoC. A failed probe now restores the voltage found at probe, and `remove()` leaves the request alone. Module only |
| [`0728`](../../patches/proposals/0728-arm64-dts-mediatek-gemini-station-give-the-A53-OPPs-.patch) | The A53 OPPs declare a 500 us clock latency instead of 100 us. A VPROC1 change alone averaged 336 us on the station, and schedutil's rate limit (1.5 times the latency) was 204 us. On station-work-105 at idle the clusters changed 6 times/s and the CCI 4 times/s, so this corrects the description; it is not a power fix. Device tree; next image |
| [`0749`](../../patches/proposals/0749-regulator-da9213-legacy-answer-VPROC1-reads-from-the.patch) | VPROC1 reads come from the last write that read back correctly, not from I2C6. A rail change drops from six transfers to three, and a request that leaves the rail alone needs none. Each write still reads the register first and refuses with `changed behind the driver` if it differs. BUCKB still reads the chip. Module only |

Profile `mt6797-a53-station-dvfs`: the `mt6797-a53-station-a72` fragments plus
[`gemini-a53-station-dvfs.fragment`](../../configs/gemini-a53-station-dvfs.fragment).
New drivers are modules (`da9213-legacy-regulator`, `mt6797-vsram-regulator`,
`clk-mt6797-mcusys`, `cpufreq-dt`, `mtk-cci-devfreq`). Only the coupler is
built in, because regulator couplers must register before any regulator. The
default governor in this profile is `userspace`, so loading cpufreq-dt does
not start scaling by itself. The DTB is `mt6797-gemini-pda-station-dvfs.dtb`.

Candidate after D1 (compile-checked on Buildbox, not run): commit `ee974aa1`,
job `ee974aa122e8508bee209ecd69979e6c92dd5a8d-mt6797-a53-station-dvfs-m1`,
package `linux-7.1.3-gemini-6986c6161c3e9c0c89b0133646a937a29c8a23f18af720cfd1a74278a4733c51`.
The modules are byte-identical to D1's; the image (passive governor) and the
DTB (no required-opps, VSRAM_L floor 1.10 V) are new:

| File | SHA-256 |
| --- | --- |
| `Image.gz` | `0a772f96217b0f0df21b9c8f2245ce793216b51c19a14a45b40747cd4f001ee2` |
| `mt6797-gemini-pda-station-dvfs.dtb` | `dbb17e52fa5642041c97e6bc2d498c2c83d458e82f3ec58520423f21364a79f0` |
| `kernel.config` | `ffbe2b615a1c7c5b34f136c8285e966d824e28fdc9472af7cdbc0eb4d9b253fa` |
| `da9213-legacy-regulator.ko` | `760d7a63f1d5e6c6cd7caed1bb39bf0e71d4f7b39d26edbd98984d2667bd01e8` |
| `mt6797-vsram-regulator.ko` | `efc041d2b3552b305f91f6ed6f5042ed4824bffc65914fb346503a193c847959` |
| `clk-mt6797-mcusys.ko` | `f5c53ff9466ef9c78160b0ac040d9b595c4ca8c2633b24303840454170fc0fd6` |
| `cpufreq-dt.ko` | `f558be9bfe9f82f31c5245fbba52d54ac3584fbfee98ebbb25f6582425dddba5` |
| `mtk-cci-devfreq.ko` | `2f8edde688670cecf795eb1b40560409ec7b03d227fce5c26ed4483f10e5aadd` |

D2, composed by the custodian as `station-work-93` and not yet flashed: built from
commit `4a1c6f22` (which includes 0673-0676), job
`4a1c6f22e8b762582691c6369dc05d4b02bfacde-mt6797-a53-station-dvfs-m1`, package
`ec8cb8e7…`, config `ffbe2b61…`, `Image.gz` `4d79ccc96ac4ce5a…`, board DTB
after `station-dt.sh` `8c59eff2…` (no required-opps), initramfs `1ebb2ced…`,
boot2 `ed088a5a07e869663fbb77449d3a901834a60d49ac602a67b6d026bed870dead`.
Compared with D1's modules, `cpufreq-dt.ko` (`7e86b951…`, 0675),
`gemini-lid.ko` and `snd-soc-mt6797-afe.ko` changed; the other DVFS modules did not.
The run uses `tools/v-test.sh` at sha256 `bf763922…`. At V4, a "failed to set
the initial OPP" line counts as a stop.

D2 with 0677, for the V7-V9 rerun, compile-checked on Buildbox but not run:
commit `3e338a46`, job
`3e338a464cff131c0b4132f6941040ac6a2c0b14-mt6797-a53-station-dvfs-m1`, package
`linux-7.1.3-gemini-03a493e96015f6fcce56a6c4b1b765f1ce8d08352f8a5a62a83d7a98c032e9ca`.
Only `mtk-cci-devfreq.ko` differs from the `4a1c6f22` package
(`90b5722757d492614657e727daca338887693a668a137a1da6df61d52a319dbe`); the
image, DTBs, config and every other module are byte-identical. It replaces the
module on the D2 station, with no new image.

Candidate after D3 (0680), compile-checked on Buildbox, not run: commit `1768fe04`,
job `1768fe04b7ca814ba382c7c0ba1e58760e7c88ad-mt6797-a53-station-dvfs-m1`, package
`linux-7.1.3-gemini-695c71d4e7170e8c30d381576c7218d5caa78ef4506f1ca42c2194c526cd8237`.
`Image.gz` `56a0a2dfd1e6f9dbbadf058bfdf6a602d6ece8dea0d391404f3f9e91b8baa81f`,
`mt6797-gemini-pda-station-dvfs.dtb`
`72a485eac5d86d18f05181ae61a7b4c8a62ea1101c3b3fc60f0848e1b2e2f29b`, config
`ffbe2b61…` unchanged. Against the `3e338a46` package the image changes with the
series (`0678`, `0679` from other sessions), and of the modules only
`mt6797-spm-sleep.ko` changes; every DVFS module is identical.

Station init: the [station `init`](../2026-10-30-mainline-dev-station/initramfs/init)
loads whichever of those five modules the image carries, in that order, and
then sets every policy to schedutil. If the tree has the CCI but the driver did
not bind (a deferred probe still loads), it unloads the CCI and cpufreq-dt
while the policies hold their first point and reports `failed-cci-unbound`. It runs only when
`/mnt/data/cpufreq-at-boot` exists, after the A72 block, and with the same
unfinished-load marker as the display. Nothing creates that file; the
custodian creates it after the heat soak (V9).

Energy model: `capacity-dmips-mhz` for all ten CPUs comes from the A72
station tree, from the all-cores session's per-MHz measurements
([all cores](../2026-11-01-mt6797-all-cores/README.md)). Since `0680`,
`dynamic-power-coefficient` is 78 for CPU0-3 and 129 for CPU4-7, fitted to the
vendor's per-core dynamic power for each operating point at its base voltage
(mW = C × MHz × mV² / 10⁹); every point is within 11 % of the fit. With it
cpufreq-dt registers an energy model and both clusters can be power-allocator
actors. V10 can check the fit against this unit.

Thermal: since `0680` the `soc-thermal` zone also has a 75 C passive control
trip, the vendor's adaptive CPU budget target, with both clusters and the GPU
on it, 100 ms passive polling and a 1.5 W first `sustainable-power`. The 58 C
trip is the allocator's switch-on point. No device tree property picks a
zone's governor: the station init (and V8/V9) set `power_allocator` on the
zone, which refuses to bind, leaving step-wise, unless every device on the
control trip has an energy model. Set it only while the zone is below 58 C,
because the allocator does not touch the 58 C step-wise instances.

### Voltages

Each point's VPROC1 is the higher of:

- the vendor base table for this unit's speed bin (SB/0119,
  [CPU clusters section 4.3](../../docs/hardware/mt6797-cpu-clusters.md#43-vendor-base-table-for-the-selected-speed-bin));
- this unit's EEM-calibrated value from its Gemian capture
  ([section 4.2](../../docs/hardware/mt6797-cpu-clusters.md#42-live-per-opp-voltage-table))
  plus the 62.5 mV that the vendor adds at or below 33 C, where the station
  runs.

The result is capped at the vendor's 1.2 V `MAX_VPROC_VOLT` and rounded up to
the DA9214's 10 mV step. It is never below what Gemian would apply on this unit
at room temperature, and never below the uncalibrated table. Because the EEM
column is per unit, the tree is for this unit only.

VSRAM_L follows the vendor rule from `set_cur_volt_extbuck()`, VPROC1 + 10 mV
rounded up to the LDO's 25 mV step, but never below 1.10 V (`0674`) and
never above 1.2 V. The vendor's own range starts at 1.0 V. The firmware leaves
1.10 V with VPROC1 at 1.00 V (D1 V0-V2), so 1.10 V is the lowest value seen
running.

| LL MHz | VCO MHz | post-div | divider | PCW | Base mV | EEM mV | +62.5 | Set mV | VPROC1 sel | VSRAM_L mV (sel) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1547 | 1547 | /1 | /1 | `0x0ee000` | 1200 | 1170 | 1232.5 | 1200 | `0x5a` | 1200 (`15`) |
| 1495 | 1495 | /1 | /1 | `0x0e6000` | 1190 | 1150 | 1212.5 | 1200 | `0x5a` | 1200 (`15`) |
| 1443 | 1443 | /1 | /1 | `0x0de000` | 1170 | 1140 | 1202.5 | 1200 | `0x5a` | 1200 (`15`) |
| 1391 | 1391 | /1 | /1 | `0x0d6000` | 1150 | 1110 | 1172.5 | 1180 | `0x58` | 1200 (`15`) |
| 1339 | 1339 | /1 | /1 | `0x0ce000` | 1140 | 1090 | 1152.5 | 1160 | `0x56` | 1175 (`14`) |
| 1274 | 1274 | /1 | /1 | `0x0c4000` | 1130 | 1070 | 1132.5 | 1140 | `0x54` | 1150 (`13`) |
| 1222 | 1222 | /1 | /1 | `0x0bc000` | 1100 | 1050 | 1112.5 | 1120 | `0x52` | 1150 (`13`) |
| 1118 | 1118 | /1 | /1 | `0x0ac000` | 1070 | 1000 | 1062.5 | 1070 | `0x4d` | 1100 (`11`) |
| 1014 | 2028 | /2 | /1 | `0x138000` | 1040 | 960 | 1022.5 | 1040 | `0x4a` | 1100 (`11`) |
| 897 | 1794 | /2 | /1 | `0x114000` | 1000 | 920 | 982.5 | 1000 | `0x46` | 1100 (`11`) |
| 806 | 1612 | /2 | /1 | `0x0f8000` | 970 | 880 | 942.5 | 970 | `0x43` | 1100 (`11`) |
| 715 | 1430 | /2 | /1 | `0x0dc000` | 940 | 840 | 902.5 | 940 | `0x40` | 1100 (`11`) |
| 624 | 1248 | /2 | /1 | `0x0c0000` | 900 | 810 | 872.5 | 900 | `0x3c` | 1100 (`11`) |
| 481 | 1924 | /2 | /2 | `0x128000` | 850 | 800 | 862.5 | 870 | `0x39` | 1100 (`11`) |
| 338 | 1352 | /2 | /2 | `0x0d0000` | 800 | 790 | 852.5 | 860 | `0x38` | 1100 (`11`) |
| 221 | 1768 | /2 | /4 | `0x110000` | 770 | 770 | 832.5 | 840 | `0x36` | 1100 (`11`) |

| L MHz | VCO MHz | post-div | divider | PCW | Base mV | EEM mV | +62.5 | Set mV | VPROC1 sel | VSRAM_L mV (sel) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2002 | 2002 | /1 | /1 | `0x134000` | 1200 | 1170 | 1232.5 | 1200 | `0x5a` | 1200 (`15`) |
| 1950 | 1950 | /1 | /1 | `0x12c000` | 1190 | 1150 | 1212.5 | 1200 | `0x5a` | 1200 (`15`) |
| 1885 | 1885 | /1 | /1 | `0x122000` | 1170 | 1120 | 1182.5 | 1190 | `0x59` | 1200 (`15`) |
| 1820 | 1820 | /1 | /1 | `0x118000` | 1150 | 1100 | 1162.5 | 1170 | `0x57` | 1200 (`15`) |
| 1755 | 1755 | /1 | /1 | `0x10e000` | 1140 | 1090 | 1152.5 | 1160 | `0x56` | 1175 (`14`) |
| 1703 | 1703 | /1 | /1 | `0x106000` | 1130 | 1060 | 1122.5 | 1130 | `0x53` | 1150 (`13`) |
| 1625 | 1625 | /1 | /1 | `0x0fa000` | 1100 | 1040 | 1102.5 | 1110 | `0x51` | 1125 (`12`) |
| 1495 | 1495 | /1 | /1 | `0x0e6000` | 1070 | 1000 | 1062.5 | 1070 | `0x4d` | 1100 (`11`) |
| 1352 | 1352 | /1 | /1 | `0x0d0000` | 1040 | 950 | 1012.5 | 1040 | `0x4a` | 1100 (`11`) |
| 1209 | 1209 | /1 | /1 | `0x0ba000` | 1000 | 900 | 962.5 | 1000 | `0x46` | 1100 (`11`) |
| 1092 | 1092 | /1 | /1 | `0x0a8000` | 970 | 850 | 912.5 | 970 | `0x43` | 1100 (`11`) |
| 962 | 1924 | /2 | /1 | `0x128000` | 940 | 820 | 882.5 | 940 | `0x40` | 1100 (`11`) |
| 832 | 1664 | /2 | /1 | `0x100000` | 900 | 790 | 852.5 | 900 | `0x3c` | 1100 (`11`) |
| 650 | 1300 | /2 | /1 | `0x0c8000` | 850 | 790 | 852.5 | 860 | `0x38` | 1100 (`11`) |
| 468 | 1872 | /2 | /2 | `0x120000` | 800 | 790 | 852.5 | 860 | `0x38` | 1100 (`11`) |
| 325 | 1300 | /2 | /2 | `0x0c8000` | 770 | 770 | 832.5 | 840 | `0x36` | 1100 (`11`) |

| CCI MHz | VCO MHz | post-div | divider | PCW | Base mV | EEM mV | +62.5 | Set mV | VPROC1 sel | VSRAM_L mV (sel) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 988 | 1976 | /2 | /1 | `0x130000` | 1200 | 1160 | 1222.5 | 1200 | `0x5a` | 1200 (`15`) |
| 975 | 1950 | /2 | /1 | `0x12c000` | 1190 | 1150 | 1212.5 | 1200 | `0x5a` | 1200 (`15`) |
| 936 | 1872 | /2 | /1 | `0x120000` | 1170 | 1130 | 1192.5 | 1200 | `0x5a` | 1200 (`15`) |
| 910 | 1820 | /2 | /1 | `0x118000` | 1150 | 1120 | 1182.5 | 1190 | `0x59` | 1200 (`15`) |
| 884 | 1768 | /2 | /1 | `0x110000` | 1140 | 1100 | 1162.5 | 1170 | `0x57` | 1200 (`15`) |
| 845 | 1690 | /2 | /1 | `0x104000` | 1130 | 1080 | 1142.5 | 1150 | `0x55` | 1175 (`14`) |
| 819 | 1638 | /2 | /1 | `0x0fc000` | 1100 | 1070 | 1132.5 | 1140 | `0x54` | 1150 (`13`) |
| 754 | 1508 | /2 | /1 | `0x0e8000` | 1070 | 1030 | 1092.5 | 1100 | `0x50` | 1125 (`12`) |
| 676 | 1352 | /2 | /1 | `0x0d0000` | 1040 | 990 | 1052.5 | 1060 | `0x4c` | 1100 (`11`) |
| 611 | 1222 | /2 | /1 | `0x0bc000` | 1000 | 950 | 1012.5 | 1020 | `0x48` | 1100 (`11`) |
| 533 | 1066 | /2 | /1 | `0x0a4000` | 970 | 900 | 962.5 | 970 | `0x43` | 1100 (`11`) |
| 481 | 1924 | /2 | /2 | `0x128000` | 940 | 870 | 932.5 | 940 | `0x40` | 1100 (`11`) |
| 416 | 1664 | /2 | /2 | `0x100000` | 900 | 840 | 902.5 | 910 | `0x3d` | 1100 (`11`) |
| 325 | 1300 | /2 | /2 | `0x0c8000` | 850 | 820 | 882.5 | 890 | `0x3b` | 1100 (`11`) |
| 234 | 1872 | /2 | /4 | `0x120000` | 800 | 790 | 852.5 | 860 | `0x38` | 1100 (`11`) |

The CCI's 169 MHz point is left out: the firmware leaves its sync DCM divider at
3, which needs at least 210 MHz (A53 cpufreq
[A1](../2026-11-07-mt6797-a53-cpufreq/README.md#a1)). The CCI follows the
clusters through the passive governor. Each cluster's place in its own range
maps onto 234-988 MHz, and the faster cluster wins. VPROC1 is shared, so the
rail is the highest of the three consumers' requests. The CCI asks for the
voltage of its own point, so the mapping changes performance only, never
the CCI's voltage margin.

### Open question: VSRAM_L below VPROC1 0.97 V

Gemian's manual path clamps VSRAM_L to at least 1.0 V but also asserts that it
is at most 30 mV above VPROC1, so that path would `BUG()` below VPROC1 0.97 V.
On the live unit those points run through the CSPM PCM firmware instead, whose
VSRAM_L choice there is not known. This tree keeps VSRAM_L at 1.10 V below that
point, up to 260 mV above VPROC1 at 221 MHz. The MediaTek upstream coupler
likewise ignores the spread while the SRAM sits at its floor. Test V0g measures
what Gemian's PCM actually sets. If it sets VSRAM_L lower, the floor and the
low points are revisited before V5.

## Safety assessment

V0 and V1 are read-only. From V2 on the tests write regulators and
registers, listed below. Recovery: the boot2 image is the only flash change;
the standing boot2, power-off, physical selection and Gemian recovery rules
apply. No protected partition is touched.

### Writes for owner approval

Approved separately per item; the custodian's request is not that approval.

**At boot (V1):** one `flash-boot2` write of the new image. Nothing else; no
module loads.

**V2 (regulator modules):** none expected. The DA921x probe reads its 4
identity registers twice (page2 `0x05`, `0x06`, `0x47`, primary `0xd3`). The
VSRAM_L probe reads `0x10001f98`/`f9c`/`fa0`. The regulator core writes a
voltage only if one is outside its constraints. V1 checks it is not, and a
value outside them stops the test before V2.

**V3 (clock module):** items 1-5 of the A53 cpufreq record
([writes](../2026-11-07-mt6797-a53-cpufreq/README.md#writes-for-owner-approval)),
now also for FHCTL channel 2 at probe: `CLK_CON` `0x1001af04` bit 2 ← 1,
`RST_CON` `0x1001af08` bit 2 ← 0 then 1, and `CFG` `0x1001af5c`, `UPDNLMT`
`0x1001af60` and `DDS` `0x1001af64` ← 0.

**V4-V9 (frequency and voltage changes):**

1. DA9214 `0x68` register `0xd7` (VPROC1), bits 6:0 ← selector `0x36`-`0x5a`
   (840-1200 mV) from the table above; bit 7 kept. One two-byte I2C6 write
   per change, read back. `0xd9` (VPROC2) and `0x5e` are not written: BUCKB
   has no consumer.
2. INFRACFG_AO `0x10001f9c` and `0x10001fa0` (VSRAM_L) ← selector × `0x01010101`,
   selector 11-15 (1100-1200 mV). `0x10001f98` is not written.
3. MCUMIXED, as A53 cpufreq items 1-8, for all three PLLs and every PCW in the
   tables above:
   - CON1 `0x1001a204` (LL), `0x1001a214` (L), `0x1001a224` (CCI);
   - FHCTL `DVFS` `0x1001af40`/`0x1001af54`/`0x1001af68`, `HP_EN` bits 0-2,
     `CFG`, `DDS`, `SLOPE0`;
   - divider fields of `0x1001a274` (bits 9:5, 14:10, 19:15) ← 8, 10 or 11;
   - for an LL or L post-divider change: TOPCKGEN `0x10000104` bits 5:4 and the
     mux field of `0x1001a270` through MAINPLL.

   CCI's post-divider is /2 at every point, so it never takes the bridge.
4. On loading `mtk-cci-devfreq`: VPROC1 to the CCI table's top voltage (1.2 V)
   and VSRAM_L to 1.2 V, which upstream's driver does at probe. The passive
   governor then sets the CCI point.
5. V8 writes the `soc-thermal` zone's `emul_temp` (77000, then 0), as A53
   cpufreq t7. V8 and V9 write `power_allocator` to the zone's `policy`; the
   station init does the same once the boot gate is open.
6. V7's schedutil phase, V8 and V9 write tracefs control files and
   `trace_marker` (owner-approved for D3). V9p also enables four thermal
   events: `thermal_power_allocator`, `thermal_power_allocator_pid`,
   `thermal_power_cpu_limit` and `thermal_temperature`.
7. V9p with `IPA_GAINS` writes those PID files of the `soc-thermal` zone
   after the policy write (which resets them): `k_po`, `k_pu`, `k_i`, `k_d`,
   `integral_cutoff`. The script refuses any other name and reads each back.
   With `IPA_WEIGHTS` it also writes every `cdevN_weight` of the zone (the
   listed cooling-device type's value, 1024 for the others) and reads each back.
8. Withdrawn. `0700` added a second CSPM write, `0x11015448`. `0e90a668` removed
   it: `0x11015440`, `0x444` and `0x448` are master ports 0-2 of the same
   semaphore 3, so holding port 0 (item 2) already excludes the firmware's A72
   path. With `0700` on station-work-101, every MCUMIXED transaction timed out.
   Images from `0e90a668` on write only `0x11015440`.
9. V12b writes the global schedutil tunable
   `/sys/devices/system/cpu/cpufreq/schedutil/rate_limit_us` (there is no
   per-policy copy with `cpufreq-dt`): 2000, then 5000, then back to the value
   read at the start (804 with `0728`).

No PMIC (MT6351), BUCKB, `0x5e`, VSRAM_B, A72 or secure call, and no write
outside the lists above.

### Limits

- VPROC1 770-1200 mV by constraint, 840-1200 mV in the tables; VSRAM_L
  1100-1200 mV; VSRAM_L never below VPROC1.
- CPU0-3 221-1547 MHz, CPU4-7 325-2002 MHz, CCI 234-988 MHz.
- SoC temperature: stop above 80 C. The power allocator, from 58 C, holds
  the zone near 75 C; 95 C hot, 110 C critical and the 117 C hardware reset stay armed.
- Load runs are bounded (15 s in V7, 10 min in V9) and the battery stays on
  the charger except in V10.

### Stop conditions

Stop at the first of these, keep the kernel log and the stage output, and do
not retry:

- a module that refuses to load or a driver that does not bind; any kernel line
  with `fault`, `failed`, `error`, `behind the driver`, `did not hold`,
  `not granted`, `refusing`, an Oops, a `BUG` or a `WARNING` from these drivers
  (the A72 `cpufreq_dt: failed to find data for cpu8/9` lines excepted);
- a regulator readback other than the requested voltage, or VSRAM_L below
  VPROC1 at any read;
- debugfs `faulted=1` on the clock driver;
- a measured clock more than 5 % from the requested one;
- a hash differing from the reference: power off, since a wrong result may
  mean corrupted state;
- the SoC above 80 C;
- the station unreachable for 60 s, or a hang: the owner long-presses power,
  and the next boot is unchanged (the init gate is off).

## Device tests, in order

The stages are scripted in [`tools/v-test.sh`](tools/v-test.sh), written by the
device custodian; the expected rail per point and the V4/V7 checks were
added after D1. Every fixed point checks the hardware VPROC1 and VSRAM_L
against the table and the coupler rule. After D3 the schedutil phases (V7's
load phase, V8 and V9) no longer pair separate sysfs and I2C reads, which
cannot be taken at one instant while the governor moves. They check only
what any single read must satisfy (VPROC1 770-1200 mV, each VSRAM_L word one
selector at 1100-1200 mV). Each of those phases is traced instead:
`clk_set_rate`, `regulator_set_voltage` and their `_complete` events stream
through [`tools/v-trace-check.awk`](tools/v-trace-check.awk). The phase starts
from fixed points, which seed the check. While a change is in flight, a clock
counts at the higher of its old and new rate, and a rail at the lower of its
old and requested voltage. At every event VPROC1 must cover the table voltage
of all three PLLs, and VSRAM_L must be at or above VPROC1 and 1100 mV. Every
PLL target must be a table point. A violation, a lost event or a ring-buffer
overrun stops the stage. `v7s` reruns V7's schedutil phase alone.

Each is one call; the custodian folds them into the test plan. "Read" means a
`devmem` read of a 32-bit word; DA9214 reads use `i2cget -fy 6 0x68 REG` (or
the regulator sysfs once bound). Run V0 on the current station image before
building anything on it.

| Test | Boot | What it does | Expected | Writes |
| --- | --- | --- | --- | --- |
| V0 | current station | Read `0x10001f98`, `0x10001f9c`, `0x10001fa0` and DA9214 `0xd7`, `0x5d`, `0xd9` | `CTRL_0` low byte `0xff`; `CTRL_1` = `CTRL_2` = code × `0x01010101` with code 11-15 (1.10-1.2 V); `0xd7` = `0x46` (1.00 V); VSRAM_L ≥ 1.10 V, so V2 writes nothing | none |
| V0g (optional, recommended) | Gemian | With the vendor `userspace` policy pin LL at 221 MHz and L at 325 MHz, then at 897/1209 MHz; at each, read `0x10001f9c` and CSPM `SW_RSV3`-`6` (`0x11015614`-`0x11015620`, `V_CURR`/`VS_CURR`) | The PCM's VPROC1 and VSRAM_L codes at the low and middle points; decides the 1.0 V floor question | none (read-only Gemian inspection) |
| V1 | new image, profile `mt6797-a53-station-dvfs`, DTB `station-dvfs` | A53 cpufreq t0 plus the V0 reads | As V0; cpufreq empty; all CPU0-7 online (blanking off) | boot2 |
| V2 | V1 | `insmod da9213-legacy-regulator.ko`, then `mt6797-vsram-regulator.ko`; read `/sys/class/regulator/*/{name,microvolts}` and `regulator_summary` | `DA9214 legacy direct-address identity matched; voltages are writable`; vproc1 1000000, vproc-big 1000000, vsram_l = V0 value; no write (selectors unchanged) | none |
| V3 | V1 | `insmod clk-mt6797-mcusys.ko`; debugfs `registers` | Three PLL lines: LL 897, L 1274 MHz, CCI ≈ 629.5 MHz, each "up to" 1547/2002/988 MHz; `faulted=0` | V3 list |
| V4 | V1 | `insmod cpufreq-dt.ko` (userspace) | policy0 0-3 221-1547 MHz, policy4 4-7 325-2002 MHz; L moves from its unlisted 1274 to 1352 MHz: VSRAM_L stays 1100, VPROC1 1040 mV, then the clock; LL stays at 897 MHz/1000 mV. A failure here is the core's `BUG_ON()` for an unlisted frequency: power off | V4-V9 items 1-3 |
| V5 | V1 | CPU0-3 sweep: every LL point down then up, then 221↔1547 jumps; at each, measure CPU1 and CPU3, hash, read vproc1 and vsram_l | Clocks within 5 %, hashes equal, readbacks exactly the table, VSRAM_L ≥ VPROC1 | items 1-3 |
| V6 | V1 | CPU4-7 the same, 325-2002 MHz, including both post-divider crossings | As V5 | items 1-3 |
| V7 | V1 | `insmod mtk-cci-devfreq.ko`; step LL and L and read the devfreq `cur_freq` and the CCI PLL line; then schedutil on both, 10 s idle, 15 s of 8-CPU load, 10 s idle | CCI = the higher of the two clusters' places mapped onto 234-988 MHz, rounded to a CCI point; schedutil idles low and loads high; all load hashes equal; transitions counted | items 1-4 |
| V8 | V1 | Cooling: `power_allocator` on the zone, emulate 77 C (above the control trip), then release | At least one policy's `scaling_max_freq` drops within 10 s; both come back | item 5 |
| V9 | V1 | Heat soak from below 45 C: `power_allocator` on the zone, 10 min of 8-CPU load under schedutil, sampling every 10 s the SoC temperature, both policies' frequencies, vproc1, vsram_l and hashes | The allocator settles the SoC near 75 C and below 80 C; no hash difference. Pass opens the boot gate | items 1-3, 5 |
| V9p | V1, cold | V9 with the allocator's budget, PID terms, CPU limits and zone temperature traced, raw trace kept in `/tmp/v9p-trace.txt`; `IPA_GAINS="k_po=60 k_pu=60 k_i=10 integral_cutoff=3000"` sets the tuned gains, `IPA_WEIGHTS="cpufreq-cpu0=4096"` the cooling weights | Defaults: the trace shows why the caps swing (below). Tuned: mean near 75 C, below 77 C, no poll-to-poll swing | items 1-3, 5-7 |
| V10 | V1 | Energy model: on battery, per cluster, one busy CPU pinned at each point for 10 s, the rest idle; record the fuel gauge's average `current_now` and `voltage_now` against an idle baseline | Power per point for `dynamic-power-coefficient` (mW = C × MHz × mV² / 10⁹) and the capacity ratio from a fixed workload's time per MHz | items 1-3 |
| V11 | new boot, same image | Create `/mnt/data/cpufreq-at-boot`; power off; owner selects boot2 | Station status `cpufreq=loaded,da9213-legacy-regulator,mt6797-vsram-regulator,clk-mt6797-mcusys,cpufreq-dt,mtk-cci-devfreq`; schedutil on both policies | items 1-4 at boot |
| V12a | station image with schedutil at boot | Switch cost under video: 20 s of the station-work-112 mpv H.264 1080p playback with `sched_switch` (filtered to `sugov*`), `clk_set_rate` and `regulator_set_voltage` traced; before and after, both policies' `stats/total_trans`, the CCI's `trans_stat` total, `/proc/interrupts` (I2C6 line), the clock debugfs `registers`, mpv's dropped frames and, once, `energy_model/cpu{0,4}/ps:*/inefficient`. [`tools/v-switch-cost.awk`](tools/v-switch-cost.awk) reads the trace | Per sugov thread: changes/s, wall and CPU time per change, PLL and rail sets per change, CPU share | item 6 |
| V12b | as V12a | V12a again at `rate_limit_us` 2000 and 5000, then restore | Fewer changes/s and less sugov CPU, with no more dropped frames | items 6, 9 |
| V12c | first image with `0749` | V12a again | Rail sets cost three I2C6 transfers each, and I2C6 interrupts per change fall | item 6 |
| V12d | as V12c | 20 s of the V12c playback with `perf record -g -t $(pgrep -x sugov:0)`; `perf report --no-children --stdio`, plus the same report with `--children` | Where the remaining CPU time per change goes: PLL polling, regulator core and coupler, I2C path or OPP | item 6 |

After a pass: record support, fill the energy model, and decide with the owner
whether the station's default image moves to this profile.

### Interactions

- **A72s.** Load `mt6797-a72.ko` before the clock module, as agreed with the
  all-cores session and as the init does. Bringing the A72s up while A53 rates
  can change is not covered; for a later A72 hotplug, hold both policies on
  `userspace` at a fixed point. BUCKB has no consumer here. The A72 module
  keeps writing `0x5e` itself, and a later A72 voltage consumer belongs to the
  all-cores work.
- **Arch root.** The init copies the image's modules into the Arch root. If
  that root's udev can resolve their aliases, it could load the clock and
  cpufreq modules without the gate. Before shipping these modules in an image
  that hands over to Arch, check that the root has no `modules.alias` for them
  or blacklists them.

## Observations

**V0 (2026-11-08), passed.** Run by the device custodian, owner-approved, on the
station RAM root: boot `52f4c5fd-c191-4955-9277-42bc774ea4c1`, release
`7.1.3-gemini-a53-station`, boot2 `6c0fd742…` (station-work-91). Reads only:
`0x10001f98` = `0x000000FF`, `0x10001f9c` = `0x10001fa0` = `0x0B0B0B0B` (code
11 in every byte), DA9214 `0xd7` = `0x46` (1.00 V), `0x5d` = `0x01`, `0xd9` =
`0x46`. Every V0 expectation holds; no stop condition.

**V1-V4 (2026-11-08), stopped at V4 on a kernel BUG.** Run by the device custodian,
owner-approved, on image D1 (`station-work-92`, boot2 `09ae90fd…`, from this profile at
`980309cf`), station RAM root, boot `e79a664d-e06a-4c3e-a39f-57fe2100e5e5`, cable in, A72
module not loaded. The kernel was already tainted W by an unrelated keyboard warning after
an earlier s2idle cycle on this boot.

- **V1 passed:** CPU0/3 at 896/894 MHz and CPU4/7 at 1271 MHz; DA9214 `0xd7` `0x46`
  (1000 mV), VSRAM words `0x0B0B0B0B` (1100 mV); SoC 34.3 C.
- **V2 passed:** "DA9214 legacy direct-address identity matched; voltages are writable",
  VSRAM_L "selector 11 (1100000 uV)"; sysfs vproc1 and vproc-big 1000000, vsram_l 1100000,
  equal to the hardware. No write.
- **V3 passed:** sync DCM `0x00070707`; PLL0 897 MHz (up to 1547), PLL1 1274 MHz (up to
  2002), PLL2 630 MHz (up to 988); `faulted=0`.
- **V4 stopped:** `insmod cpufreq-dt` logged "cpu cpu4: Failed to set required opps: -16",
  then "__target_index: Failed to change cpu frequency: -16", then `kernel BUG at
  drivers/cpufreq/cpufreq.c:1528` in `cpufreq_online` (insmod, CPU4), followed by a
  `kernel/context_tracking.c:107` warning in CPU4's idle loop. VPROC1, VSRAM_L and all three
  PLLs then read unchanged: no write had been made. `poweroff -f` hung after it, so the owner
  forced the power off. Inference: policy4 starts at the unlisted 1274 MHz, the core must
  move it to a listed point, and that point's required OPP (the CCI link) cannot be set while
  `mtk-cci-devfreq` is not loaded. The init's load order would hit the same BUG, so the boot
  gate stays off.

**V1-V7 (2026-11-08), stopped at V7 on an interpolated CCI rate.** Run by the device
custodian, owner-approved, on image D2 (`station-work-93`, boot2 `ed088a5a…`, from this
profile at `4a1c6f22`), boot `bb910b05…`, script `tools/v-test.sh` `bf763922…`.

- **V1-V3 passed:** VSRAM_L 1100 mV (code 11), providers and clocks as on D1.
- **V4 passed, as predicted for 0675:** "Running at unlisted initial frequency: 1274000
  kHz, changing to: 1352000 kHz"; policy0 897000, policy4 1352000; DA9214 `0xd7` `0x4a`
  (1040 mV), VSRAM_L 1100 mV; measured 894 and 1350 MHz.
- **V5-V6 passed:** all 34 points on each cluster, with rails as tabled; SoC at most 32 C.
- **V7 stopped:** `mtk-cci-devfreq` probed without deferring, governor passive.
  LL 221000 with L 325000 gave CCI 234 MHz and VPROC1 860 mV; LL 897000 with L 325000 gave
  CCI 611 MHz and 1020 mV; both as expected. LL 221000 with L 1209000 gave devfreq
  `cur_freq` 626080000 and PLL2 624999755 Hz, which is not a CCI point, with VPROC1 1020 mV
  (the 611 MHz point's voltage). devfreq logged "Couldn't update frequency transition
  information" three times. The CCI ran about 2.5 % above its voltage's point until the
  power-off at the stop.

**V1-V7 (2026-11-08), stopped in V7's schedutil phase on a sampling race.** Run by
the device custodian, owner-approved, on image D3 (`station-work-94`, from `5ed802b4`,
`mtk-cci-devfreq.ko` `90b57227…` with 0677), boot `d7f02aca…`.

- **V1-V6 passed again.**
- **V7's fixed pairs passed, the CCI now on table points with the PLL equal to
  `cur_freq`:** 221/325 MHz gave CCI 234 MHz at 860 mV; 897/325, 611 at 1020; 221/1209,
  676 at 1060 (D2: 626.08); 1547/2002, 988 with VPROC1 1200 and VSRAM_L 1200 mV
  (`0x0F0F0F0F`); 897/1209, 676 at 1060. No "Couldn't update" line.
- **Schedutil:** idle 1014000/325000 kHz with CCI 754 MHz; under 8-CPU load
  1443000/1885000 kHz with CCI 936 MHz. Then `volts` stopped on "vproc1 sysfs 1190000
  != hw 1200 mV". No kernel warning, taint 0.
- **Afterwards, by hand:** with schedutil running, two sysfs reads around one I2C read
  differed (1140 and 1170 mV), and one row paired hardware 940 mV with frequencies that
  need 1100 mV. At fixed userspace points (897000/1209000, CCI 676) sysfs gave 1060000 and
  the hardware `0x4c`, three times in a row. Inference: the separate reads are each a process apart in
  shell time while the rail moves within milliseconds, so the stop says nothing about
  ordering. The script now traces the schedutil phases instead.

**V1-V9 (2026-11-09), stopped at V9 on the 80 C limit.** Run by the device custodian,
owner-approved, on D3, boot `6dbf6d59…`, scripts from `d9e52a18`.

- **V1-V7 passed.** V7's traced schedutil phase: 28,884 events, 0 violations, no
  overrun. Idle 221/1625 MHz with CCI 819 MHz; under load 1495/1950 MHz with CCI 975.
  10 s after the load policy0 still read 1495 MHz and the CCI 988 MHz; policy4 was back at
  1352.
- **V8 passed:** emulated 62 C capped both policies one step (1495/1950 MHz), then
  released; 0 violations.
- **V9 stopped:** started warm (64 C at t+10 s, after V5-V8 back to back). The 58 C
  step-wise trip held the clusters only one to three steps down: the caps swung between
  1391/1820 and 1339/1755 MHz every 10 s while the SoC rose about 1 C per 10 s to 80.1 C.
  No fault, taint 0. Afterwards both cooling devices read 0/15 and the SoC 34 C.
- Two setup slips, not DVFS results: debugfs unmounted (V3 rerun after removing the
  clock module), and the backlight policy took CPU1-7 offline at console blank during V5
  (V5 rerun). The script now checks both.

station-work-95 (`1768fe04`, with `0680`), boot `f49ed0bf…`, cable in; the custodian's
record is in [the CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md):

- **V1-V9 passed in one run.** V7: 14,492 traced events, 0 violations; idle
  1014/1352 MHz with the CCI at 754, load 1495/1950 with the CCI at 975. V8: the
  emulated 77 C capped both policies to 221/325 MHz within 5 s and released at 0.
- **V9 under `power_allocator`** (sustainable power 1500): from 34.5 C the SoC read
  67.7 C after 10 s, then stayed between 62.7 and 75.4 C, a 70.1 C mean over the 10 s
  samples; it never reached 80. The caps moved between the top points and as low as
  338/468 MHz from one sample to the next, with VPROC1 between 890 and 1200 mV. 158,882
  traced events (26,380 VPROC1 sets in 600 s), 0 violations, no overrun, hashes equal.
  After the load the SoC fell to 42.8 C. No fault, taint 0.
- **V9p with the default gains passed** (same boot, owner-approved trace events): k_po 90,
  k_pu 180, k_i 18, k_d 0, integral_cutoff 0. From 27.5 C, 64.9 C at t+10 s, then
  63.2-75.6 C, 40.7 C at the end. 204,274 events, 0 violations, 29,182 VPROC1 sets,
  hashes equal. The trace has 5,671 PID updates, one per 105 ms. Per 50 s window:

  | Window | Mean / min / max SoC | Mean budget | Integral term | Polls with a >4 C jump |
  | --- | --- | --- | --- | --- |
  | 0-50 s | 70.5 / 59.5 / 74.5 C | 2.00 W | 0 | 0 % |
  | 100-150 s | 71.7 / 65.7 / 76.1 C | 1.42 W | -0.73 W | 87 % |
  | 300-350 s | 69.7 / 62.9 / 75.3 C | 1.31 W | -1.10 W | 100 % |
  | 550-600 s | 68.8 / 59.7 / 75.3 C | 1.22 W | -1.35 W | 99 % |

  From about 100 s on, the reading alternates every poll between about 65 and 75 C, and
  the caps alternate between the top points and about 715-806/962-1092 MHz. The next poll's reading
  rises about 5.8 C for each watt granted to the clusters (fit over 150-540 s). With the
  budget steady at full power, the reading moved 0.2 C (s.d.) from poll to poll.

station-work-96 (`0681`-`0683`, init `3891147c`), boot `53187f71…`, cable in, `v-test.sh`
`dd6c7e18`; the custodian's record is in the CPU power test plan:

- **V1-V8 passed** (V7 16,039 and V8 3,030 traced events, 0 violations).
- **V9p with k_po 60, k_pu 60, k_i 10, integral_cutoff 3000** (read back; k_d 0,
  sustainable power 1500) passed: 151,872 events, 0 violations, 20,445 VPROC1 sets, hashes
  equal. The 10 s samples from t+50 to t+530 s averaged 75.0 C (71.0-77.1 C; 70.2 C and
  63.2-75.6 C with the defaults). Per poll, 9.7 % of readings were above 77 C, the highest
  79.5 C, and the reading moved 3.0 C (s.d.) from poll to poll (9.3 C with the defaults).
- From about 50 s the LL cap sat at 221 MHz (briefly 338) while the L cap moved between
  1092 and 2002 MHz. Hashes per CPU: CPU0-3 1,021-1,041 and CPU4-7 3,641-3,724, 18,922 in
  all, against 2,515-2,553, 2,784-2,810 and 21,347 with the defaults: 11 % less work at a
  5 C higher temperature.
- The budget fell from 1.10 W (100-200 s) to 0.80 W (500-600 s), with the integral at
  -0.45 to -0.76 W; the LL request at 221 MHz was 35-42 mW, the L request 0.76-1.07 W.

## Analysis

### V1-V4 on D1

V0-V3 match the design: the providers bind without writing, and the
clock driver reads all three PLLs, CCI included.

V4 failed in the OPP core, before any write. CPU4-7 boot at 1274 MHz, which
the L table does not list. The cpufreq core moves them at once to the next
listed point, 1352 MHz, and calls `BUG_ON()` if that fails. The CPU points
carried required-opps to CCI points, and any table with required-opps gets
a `required_devs` array (`drivers/opp/of.c`). While the CCI table does not
exist yet, `_set_required_opps()` returns `-EBUSY` for lazy linking.
mtk-cci-devfreq cannot load first, because its passive governor needs the
policies. Worse, that governor also waits for a policy on every possible CPU,
and fails updates for an online CPU without one. CPU8-9 never get a policy,
so the CCI device could never have probed here, in any order. The custodian's
inference was right; the second blocker sat behind it.

Both fixes need a new image: the OPP core and the governor are built in,
and the tree changes.

- `0674` drops the required-opps. The passive governor interpolates each
  cluster's place in its range onto the CCI's, and the faster cluster wins.
  The CCI requests its own point's voltage, so this is as safe as the index
  mapping. The CCI still follows only the VPROC1 clusters, as the vendor's
  does.
- `0673` makes the passive governor skip a CPU with no OPPs.
- `0674` also raises the VSRAM_L floor to 1.10 V, where the firmware left it
  at VPROC1 1.00 V, 90 mV above the vendor kernel's +10 mV rule. The coupler
  no longer lowers VSRAM_L below a state the firmware ran.

The forced first change in V4 stays: if VPROC1 cannot be set then, the core
still hits its `BUG_ON()`. That is upstream behaviour for an unlisted boot
frequency, and the test treats it as a stop. With 0675 this move now happens
in cpufreq-dt's init, where a failure only stops the policy from registering.

### V7 on D2

Interpolation makes the passive governor ask for rates between CCI points.
`mtk_ccifreq_target()` looked up the point at or below the request
(`devfreq_recommended_opp()` with a fixed flag of 1), took that point's voltage,
and then set the clock to the raw request. Upstream boards follow through
required-opps, so every request there is a point and the mismatch never shows.
`0677` passes the devfreq flags and lets the lookup round `*freq` to the point
it returns, as the other devfreq drivers do. Normal updates carry no
least-upper-bound flag, so the request rounds up, and the clock, the voltage and
devfreq's record all name the same point. For the V7 case that is 676 MHz at
that point's voltage. The change is in the `mtk-cci-devfreq` module only;
`tools/v-test.sh` already expects table points and needs no change.

### V9 on D3

Step-wise steps a cooling device up only while the trend is rising and down
while it is falling. The SoC sensor's reading jitters by more than the
heating per 1 s poll, so the trend flips nearly every poll and the state
random-walks around one to three steps instead of accumulating. That is
step-wise working as designed with one trip and a slow, noisy rise; it holds
no temperature.

The vendor does not use trips for this either: its adaptive CPU cooler runs a
power budget toward a 75 C junction target from 58 C. The upstream
equivalent is the power allocator, which needs an energy model for each CPU
cooling device. The vendor's own per-core dynamic-power table fits
`P = C × f × V²` closely per cluster, so `0680` takes the coefficients from
it rather than waiting for V10, and adds the 75 C control trip. The 1.5 W
sustainable power only seeds the controller's gains. V9's trace of the
allocator, if needed, would show the granted power to tune it.

### V9 on station-work-95

The power allocator does what step-wise could not: it held the SoC under the
75 C target with all eight CPUs loaded. It does it badly, though. The budget
swings from full to nearly nothing within seconds, the clusters spend the run
jumping between the top and bottom of their tables, and the mean sits about
5 C below the target. Power scales with V², so alternating between 1.2 V and
0.9 V costs more energy for the same work than holding a middle point.

The estimated constants, from the 58 C switch-on trip, the 75 C control trip
and 1.5 W, are k_pu = 2 × 1500 / 17 ≈ 176 mW/C, k_po ≈ 88 mW/C and
k_i ≈ 18 mW/C per 100 ms poll (sysfs shows them as 180, 90 and 18).

V9p shows both suspected causes, working together:

- **The integral only winds down.** With `integral_cutoff` 0 it integrates only
  above 75 C, so every overshoot lowers the budget for good: -1.35 W by the end,
  and the mean fell from 73.4 to 68.8 C.
- **That puts the loop on the wrong gain.** The sensor answers within one poll,
  at about 5.8 C/W. Below the target, the error uses k_pu: 176 mW/C × 5.8 C/W ≈ 1.0,
  so each poll's correction overturns the last one, and the reading flips about
  10 C every poll. Above the target, k_po gives about 0.5. The more the integral
  drags the mean below 75 C, the more of the time the loop runs on k_pu.

A two-part plant fitted to the trace reproduces the default run: 5.8 C/W
within a poll, plus 28 C/W with a 13.6 s time constant, from 27.5 C. It gives a
68.0 C mean, swings every poll and 1.20 W. In that model:

| Gains (k_po / k_pu / k_i / integral_cutoff) | Mean / max SoC | Mean budget | Poll-to-poll s.d. |
| --- | --- | --- | --- |
| 90 / 180 / 18 / 0 (default) | 68.0 / 74.5 C | 1.20 W | 11.5 C |
| 90 / 180 / 18 / 3000 | 75.0 / 76.3 C | 1.41 W | 0.7 C |
| 60 / 60 / 10 / 3000 | 75.0 / 75.8 C | 1.41 W | 0.35 C |
| 120 / 120 / 10 / 3000 | 75.0 / 76.0 C | 1.41 W | 0.5 C |

The proposal is 60 / 60 / 10 / 3000: a fast-loop gain of about 0.35 on either
side of the target. The integral now also runs from 72 C up, so it unwinds below
the target. The model puts the SoC at the 75 C target with about 15 % more
power for the CPUs. The model leaves out the operating-point steps and the GPU,
so V9p with these gains is the test. If they hold, the station init writes them
after `power_allocator`.

### V9p on station-work-96: one cluster starves

The tuned gains fixed the loop: the mean sits on the 75 C target and the
poll-to-poll swing dropped from 9.3 to 3.0 C. The split between the clusters
went wrong instead. The allocator divides the budget in proportion to each
actor's requested power. cpufreq cooling computes that request at the
*current*, already capped, frequency, and then grants the highest point whose
power fits, rounding down. Once LL is at 221 MHz it requests about 40 mW, gets
about the same, and its next point (338 MHz) needs 1.6 times that, so it never
climbs out. Either cluster can end up trapped. With the defaults, every other
poll gave full power and reset both requests, which hid this.

LL and L are both A53 clusters, so a MHz is worth the same on either, and the
energy model makes LL far cheaper per MHz: 112 µW/MHz at its 1547 MHz top, against
129-186 µW/MHz for L from 1209 MHz up. At about 0.95 W for the CPUs, the dynamic-power
optimum is LL 1118 / L 1092 MHz (8,840 MHz in all). LL at its top with L at 650 MHz
comes within 1 % of that. LL stuck at 221 with L at 1495 is 22 % below it. The
hashes say the same: 11 % less work while running 5 C hotter.

A cooling weight on LL makes LL the side that wins. The allocator multiplies
each request by weight/1024 once any weight is set, so the weights are 4096 for
`cpufreq-cpu0` and 1024 for `cpufreq-cpu4` and the GPU. LL then climbs out of
221 MHz even against L's full 1.48 W request (that needs a ratio of at least
2.9), and in the plant model it settles at its top with L near 670 MHz. L is
not trapped either: once LL's share exceeds its 692 mW maximum, the allocator
hands the surplus to L. Only below about 0.7 W does L sit at its bottom, which
is still within 7 % of the optimum there.

The test is the same V9p with the same gains plus `IPA_WEIGHTS`, with total
hashes as the measure. If it holds, the weights become `contribution` in the
cooling maps and the gains go into the station init.

### Weighted V9p on station-work-96

The run is recorded in the
[CPU power test plan](../2026-11-08-cpu-power-test-plan/README.md) ("station-work-96
weighted V9p"). The first attempt stopped at its first log check and measured
nothing. About 70 s earlier, CPU1-7 had been brought back online, and the CCI's
passive governor logged "failed to update the frequency." for CPU3-7. Every failure
in the CCI driver's own target prints its own error, and none appeared, so the
update failed in the governor itself: it returns `-EINVAL` for an online CPU that
cpufreq has not yet added to its policy. That gap lies between a CPU coming online
and cpufreq's hotplug callback. The update is dropped before any clock or rail is
set, and the next transition of that policy retries it. Afterwards the CCI was at
611 MHz, which is what interpolation gives for LL at 897 MHz. This is an upstream
hotplug race, not a fault in these patches. The rerun on the same boot, after
`dmesg -c`, made 20,970 hashes: 10.8 % more than the 18,922 of the unweighted
tuned run. The SoC averaged 74.8 C (73.5-76.9 C), and LL held 1547 MHz in 53 of 60
samples. That is 1.8 % below the old-gains run, which averaged 4.6 C cooler but
swung 63-76 C. The pass bar of 21,347 sent with the request was the old-gains
total; the correct comparison is the unweighted tuned run.

LL at its top with L at 325-650 MHz is the split the energy model puts within a
few percent of the optimum, so a smaller LL weight would gain at most a few
percent and costs a boot. The weights stay at 4096/1024: `0687` puts them in the
device tree as `contribution`, and the station init writes the gains
60/60/10/3000 after it sets `power_allocator`. Both reach the device with the
next non-V11 image.

The same message recurs on every P2f blank, when CPU1-7 go offline and come
back. A last-CPU offline sends no frequency notification, so the CCI could have
kept policy4's point while blanked. On station-work-112 (boot `8990918b`,
`rate_limit_us` 804), the custodian read `cci/trans_stat` and policy0's
`time_in_state` right after offlining CPU7-1 and again after a bare 60 s sleep,
with the display off and the device unplugged. The CCI followed policy0 point for
point:

| CCI | CCI time | policy0 | policy0 time |
| --- | --- | --- | --- |
| 234 MHz | 56,188 ms | 221 MHz | 56,170 ms |
| 988 MHz | 1,536 ms | 1547 MHz | 1,520 ms |
| Transitions | 217 | Transitions | 232 |

So the message is log noise and the passive governor needs no patch. I2C6 ran at
about 52 interrupts/s in that quiet window.

### D3 item 3: the deferred CCI probe

The probe raises its request to the top CCI point before adding the devfreq
device. On `-EPROBE_DEFER` (CPU4-7 offline, so no policy4) the error path
disabled and released the regulators but never lowered the request, and the
regulator core does not rebalance a rail when a consumer is put. VSRAM_L
therefore stayed at 1.20 V, and VPROC1 presumably at 1.20 V too (the DA9214
was unreadable while bound), until `cpufreq-dt` unloaded. `0682` drops the
request on that path and in `remove()`. That was wrong: the regulator core clamps a 0 to INT_MAX
request to the rail's constraints, so it became a request for VPROC1's 770 mV
floor. While a CPU policy held its own vote, nothing changed. With none
(station-work-102 and -103, where `cpufreq-dt` deferred), the rail dropped
under the boot rates and the SoC hard-hung in the CCI probe. `0726` restores
the voltage read at probe instead. The station init also skips the CCI when
no policy exists (`failed-no-policy`).

Without the CCI bound, nothing holds VPROC1 up for the CCI's boot rate. In
item 3 N4, LL at 221 MHz requested 840 mV on VPROC1 (read back at N9, after
the unloads) while the CCI ran at its 630 MHz boot rate. The firmware runs that rate at 1.00 V, and the table puts it
at 1.06 V. V5 and V6 also step the clusters before V7 loads the CCI, but the
other cluster holds its 1.00 V point (L at 1209 MHz in V5, LL at 897 MHz in
V6), so VPROC1 stays at the firmware's own value there. Only a run with one
cluster offline, as in item 3, goes below it.

### Switch cost under video (V12)

On station-work-112 (boot `8990918b`), `perf record -a` during mpv H.264
1080p playback attributed 14.3 % of samples to `sugov:0`, more than mpv's
decode threads. The top symbols were the PLL change, `__delay_cycles`,
`mtk_i2c_transfer` and unlock points where interrupts come back on.
Over 761 s, policy0 made 62 changes/s and policy4 made 24/s. The samples are
relative and do not give CPU time; V12 measures it.

Reading the code, one cluster change does all of this in the sugov thread:

- **The cluster's PLL.** The FHCTL slew is polled every 10 us with preemption
  off for 70-120 us.
- **The CCI's change.** It follows synchronously through the passive governor
  and moves on most cluster changes, since it has 15 points: a second PLL
  slew and a second VPROC1 request.
- **I2C6 transfers for each VPROC1 request.** Each one sleeps under the DVFSP
  lease:
  - The coupler reads the rail once.
  - A set reads the old voltage and the old selector, does a read-modify-write
    with readback (three transfers), then reads the result.
  - So a request that moves the rail costs six transfers, and one that does
    not still costs one.

If a change takes longer than the 804 us rate limit, the thread never idles
while the load moves, and the two sugov threads queue on the I2C6 lease. That
would explain `sugov:4` in D state.

Three levers, in order of risk:

1. **`0749`**, which removes the reads (above).
2. **A longer `rate_limit_us`**, set by the init like the allocator's gains.
   Choose it from V12a's wall time per change, so the thread is idle most of
   the time.
3. **Only if V12 shows the PLL polling dominates:** let the clock driver drop
   semaphore 3 and sleep during the slew. This needs its own safety review,
   because the semaphore is shared with the firmware. Thinning the CCI table
   is a fourth option if V12 shows CCI changes per cluster change near 1.

The energy model should already make schedutil skip OPPs that share a
voltage with a faster one (LL 1443 and 1495 MHz, L 468 and 1950 MHz), so
removing them from the table would change little. V12a confirmed it: the
`inefficient` flags are set on exactly those four points.

**V12a** (station-work-112, boot `8990918b`):

- **Run:** 20 s of the H.264 1080p30 clip, with `mpv --hwdec=vaapi --fs` on
  profile `fast` and `rate_limit_us` at 804. Over 22 s of trace, no events
  were lost.
- **Changes:** policy0 made 231 changes/s and policy4 made 21/s. The CCI
  made 227/s, so it followed nearly every cluster change.
- **I2C6 load:** 3065 interrupts/s, about 12 per change. Each change sends
  two VPROC1 requests (one from the cluster, one from the CCI) at six
  transfers each.
- **Batched changes:** the tool's "changes" count runs from one S sleep to
  the next. With work queued, the sugov thread does about 1.8 changes before
  it sleeps, so each run shows about 3.6 PLL sets and 7.2 rail sets
  (VPROC1 and VSRAM_L).
- **Cost:** `sugov:0` was busy 21.8 % of one CPU, about 0.9 ms of CPU and
  2 ms of wall time per change. That is more than twice the rate limit, so it
  ran back to back. `sugov:4` used 1.1 %.
- **Frames:** mpv dropped 12 of 600 frames with tracing on, against 1 of 300
  in an untraced run of the same settings.

**V12b** (same boot; the owner approved write item 9):

- **Runs:** at each setting, one untraced and one traced 20 s run. The
  limit was restored to 804 and read back.
- **Results:**

  | `rate_limit_us` | policy0 changes/s (untraced) | I2C6 IRQ/s | `sugov:0` CPU (traced) | wall per run, p90 | dropped of 600 (untraced, traced) |
  | --- | --- | --- | --- | --- | --- |
  | 804 | 266.5 | 3519 | 22.7 % | 6.1 ms | 2, 2 |
  | 2000 | 193.8 | 2600 | 17.6 % | 2.6 ms | 1, 13 |
  | 5000 | 119.6 | 1595 | 12.0 % | 2.7 ms | 11, 2 |

- **What it shows:**
  - At 5000, the limit halves the changes and the sugov CPU.
  - The I2C6 load stays at about 13 interrupts per policy0 change.
  - Dropped frames vary between 1 and 13 with no trend against the setting,
    so these runs show no playback cost.
  - Each change still costs about 1 ms of CPU.

The owner approved 5000 at boot: the station init writes it after setting
schedutil, from the image that also carries `0749`. V12c measures both.

`0749` should halve the I2C6 transfers per change. A thinner CCI table remains the lever if the CCI still
doubles the work after both.

**V12c** (station-work-114, boot `4b7955ba`, source `77541707`):

- **Setup:**
  - The image carries `0749` and the init's `rate_limit_us` of 5000, which
    read back 5000 at boot.
  - The clip is a BT.709-tagged 1080p H.264 test pattern. mpv ran with no
    flags and decoded through VA-API.
  - One untraced and one traced 20 s run, with no lost events.
- **Results:**

  | Run | policy0 changes/s | I2C6 IRQ/s | `sugov:0` CPU | wall per run, mean/p90 | dropped of 600 |
  | --- | --- | --- | --- | --- | --- |
  | V12b, 5000, no `0749` | 119.6 | 1595 | 12.0 % | 2.0/2.7 ms | 11, 2 |
  | V12c untraced | 117.6 | 607 | - | - | 8 |
  | V12c traced | 119.3 | 603 | 9.67 % | 1.4/2.0 ms | 2 |

- **What it shows:**
  - **`0749` works.** I2C6 interrupts per policy0 change fell from about 13.3
    to about 5.1. No `changed behind the driver` line and no kernel warning
    appeared.
  - **The changes are no longer batched.** Each `sugov:0` run is now about one
    change: 1.98 PLL sets and 3.96 rail sets per run. These are the cluster and
    the CCI, each with VPROC1 and VSRAM_L.
  - **CPU cost.** From V12a, `sugov:0` fell from 22.7 % to 9.7 % of one CPU.
    `sugov:4` used 0.28 %.
- **What remains:** each change still costs 0.81 ms of CPU.
  - PLL polling explains at most 0.24 ms: two slews of 70-120 us.
  - Five I2C6 interrupts do not explain the rest.
  - V12d profiles the thread before any further change. Candidate levers are
    the clock-driver sleep, the regulator coupler's work per request, and a
    thinner CCI table (each change still moves the CCI).

## Conclusion

Pending.
