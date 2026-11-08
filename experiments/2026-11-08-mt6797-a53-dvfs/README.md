# Experiment: A53 voltage scaling, CCI and boot integration on MT6797

## Record

| Field | Value |
| --- | --- |
| ID | `2026-11-08-mt6797-a53-dvfs` |
| Status | `planned`: patches, profile and init gate pushed, compile-checked; no device test run |
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
| [`0662`](../../patches/proposals/0662-soc-mediatek-add-an-MT6797-CPU-rail-and-SRAM-LDO-cou.patch) | A built-in regulator coupler: VSRAM_L = clamp(VPROC1 + 10 mV, 1.0 V, 1.2 V), raised before VPROC1 and lowered after it |
| [`0663`](../../patches/proposals/0663-PM-devfreq-mtk-cci-make-the-intermediate-clock-optio.patch)-[`0665`](../../patches/proposals/0665-PM-devfreq-mtk-cci-add-MT6797.patch) | mtk-cci-devfreq with an optional intermediate clock (the MT6797 CCI PLL changes rate glitch-free itself) and an MT6797 entry; the passive governor follows cpufreq |
| [`0666`](../../patches/proposals/0666-arm64-dts-mediatek-gemini-station-scale-the-A53-volt.patch) | `mt6797-gemini-pda-station-dvfs.dts`: the station-a72 tree with the DA9214 on the legacy driver (BUCKA `vproc1` 770-1200 mV, BUCKB `vproc-big` 800-1200 mV, unused), VSRAM_L coupled to it, the full LL/L/CCI tables, `cpu-supply`, and required-opps to the CCI |

Profile `mt6797-a53-station-dvfs`: the `mt6797-a53-station-a72` fragments plus
[`gemini-a53-station-dvfs.fragment`](../../configs/gemini-a53-station-dvfs.fragment).
New drivers are modules (`da9213-legacy-regulator`, `mt6797-vsram-regulator`,
`clk-mt6797-mcusys`, `cpufreq-dt`, `mtk-cci-devfreq`). Only the coupler is
built in, because regulator couplers must register before any regulator. The
default governor in this profile is `userspace`, so loading cpufreq-dt does
not start scaling by itself. The DTB is `mt6797-gemini-pda-station-dvfs.dtb`.

Candidate (compile-checked on Buildbox, not run): commit `8a848ed3`, job
`8a848ed3b41f2443977c879304e31e418cb9aea9-mt6797-a53-station-dvfs-m1`,
package `linux-7.1.3-gemini-5326cdb1f374dbf136f52ea4d288c57e0c77fbcfcd847a0f2100753af69b64a3`:

| File | SHA-256 |
| --- | --- |
| `Image.gz` | `3c940e6e53c3d1716667cb7e6332cc744274db55569b97eea3286908237c559a` |
| `mt6797-gemini-pda-station-dvfs.dtb` | `bc155d57e64fda85c93fc7c4c7e6bbc77d4012a156907db65cfd91e11a160f1b` |
| `kernel.config` | `19046920fc478da20c41d15061195655b9e5b8c4999c4019d69d1f10dee5e576` |
| `da9213-legacy-regulator.ko` | `760d7a63f1d5e6c6cd7caed1bb39bf0e71d4f7b39d26edbd98984d2667bd01e8` |
| `mt6797-vsram-regulator.ko` | `efc041d2b3552b305f91f6ed6f5042ed4824bffc65914fb346503a193c847959` |
| `clk-mt6797-mcusys.ko` | `f5c53ff9466ef9c78160b0ac040d9b595c4ca8c2633b24303840454170fc0fd6` |
| `cpufreq-dt.ko` | `f558be9bfe9f82f31c5245fbba52d54ac3584fbfee98ebbb25f6582425dddba5` |
| `mtk-cci-devfreq.ko` | `2f8edde688670cecf795eb1b40560409ec7b03d227fce5c26ed4483f10e5aadd` |

Station init: the [station `init`](../2026-10-30-mainline-dev-station/initramfs/init)
loads whichever of those five modules the image carries, in that order, and
then sets every policy to schedutil. It runs only when
`/mnt/data/cpufreq-at-boot` exists, after the A72 block, and with the same
unfinished-load marker as the display. Nothing creates that file; the
custodian creates it after the heat soak (V9).

Energy model: `capacity-dmips-mhz` for all ten CPUs comes from the A72
station tree, from the all-cores session's per-MHz measurements
([all cores](../2026-11-01-mt6797-all-cores/README.md)). `dynamic-power-coefficient`
is absent, so cpufreq-dt registers no energy model; V10 measures it.

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

VSRAM_L follows the vendor rule from `set_cur_volt_extbuck()`: VPROC1 + 10 mV,
clamped to 1.0-1.2 V, rounded up to the LDO's 25 mV step.

| LL MHz | VCO MHz | post-div | divider | PCW | Base mV | EEM mV | +62.5 | Set mV | VPROC1 sel | VSRAM_L | CCI MHz |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1547 | 1547 | /1 | /1 | `0x0ee000` | 1200 | 1170 | 1232.5 | 1200 | `0x5a` | 1200 (`15`) | 988 |
| 1495 | 1495 | /1 | /1 | `0x0e6000` | 1190 | 1150 | 1212.5 | 1200 | `0x5a` | 1200 (`15`) | 975 |
| 1443 | 1443 | /1 | /1 | `0x0de000` | 1170 | 1140 | 1202.5 | 1200 | `0x5a` | 1200 (`15`) | 936 |
| 1391 | 1391 | /1 | /1 | `0x0d6000` | 1150 | 1110 | 1172.5 | 1180 | `0x58` | 1200 (`15`) | 910 |
| 1339 | 1339 | /1 | /1 | `0x0ce000` | 1140 | 1090 | 1152.5 | 1160 | `0x56` | 1175 (`14`) | 884 |
| 1274 | 1274 | /1 | /1 | `0x0c4000` | 1130 | 1070 | 1132.5 | 1140 | `0x54` | 1150 (`13`) | 845 |
| 1222 | 1222 | /1 | /1 | `0x0bc000` | 1100 | 1050 | 1112.5 | 1120 | `0x52` | 1150 (`13`) | 819 |
| 1118 | 1118 | /1 | /1 | `0x0ac000` | 1070 | 1000 | 1062.5 | 1070 | `0x4d` | 1100 (`11`) | 754 |
| 1014 | 2028 | /2 | /1 | `0x138000` | 1040 | 960 | 1022.5 | 1040 | `0x4a` | 1050 (`9`) | 676 |
| 897 | 1794 | /2 | /1 | `0x114000` | 1000 | 920 | 982.5 | 1000 | `0x46` | 1025 (`8`) | 611 |
| 806 | 1612 | /2 | /1 | `0x0f8000` | 970 | 880 | 942.5 | 970 | `0x43` | 1000 (`7`) | 533 |
| 715 | 1430 | /2 | /1 | `0x0dc000` | 940 | 840 | 902.5 | 940 | `0x40` | 1000 (`7`) | 481 |
| 624 | 1248 | /2 | /1 | `0x0c0000` | 900 | 810 | 872.5 | 900 | `0x3c` | 1000 (`7`) | 416 |
| 481 | 1924 | /2 | /2 | `0x128000` | 850 | 800 | 862.5 | 870 | `0x39` | 1000 (`7`) | 325 |
| 338 | 1352 | /2 | /2 | `0x0d0000` | 800 | 790 | 852.5 | 860 | `0x38` | 1000 (`7`) | 234 |
| 221 | 1768 | /2 | /4 | `0x110000` | 770 | 770 | 832.5 | 840 | `0x36` | 1000 (`7`) | 234 |

| L MHz | VCO MHz | post-div | divider | PCW | Base mV | EEM mV | +62.5 | Set mV | VPROC1 sel | VSRAM_L | CCI MHz |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2002 | 2002 | /1 | /1 | `0x134000` | 1200 | 1170 | 1232.5 | 1200 | `0x5a` | 1200 (`15`) | 988 |
| 1950 | 1950 | /1 | /1 | `0x12c000` | 1190 | 1150 | 1212.5 | 1200 | `0x5a` | 1200 (`15`) | 975 |
| 1885 | 1885 | /1 | /1 | `0x122000` | 1170 | 1120 | 1182.5 | 1190 | `0x59` | 1200 (`15`) | 936 |
| 1820 | 1820 | /1 | /1 | `0x118000` | 1150 | 1100 | 1162.5 | 1170 | `0x57` | 1200 (`15`) | 910 |
| 1755 | 1755 | /1 | /1 | `0x10e000` | 1140 | 1090 | 1152.5 | 1160 | `0x56` | 1175 (`14`) | 884 |
| 1703 | 1703 | /1 | /1 | `0x106000` | 1130 | 1060 | 1122.5 | 1130 | `0x53` | 1150 (`13`) | 845 |
| 1625 | 1625 | /1 | /1 | `0x0fa000` | 1100 | 1040 | 1102.5 | 1110 | `0x51` | 1125 (`12`) | 819 |
| 1495 | 1495 | /1 | /1 | `0x0e6000` | 1070 | 1000 | 1062.5 | 1070 | `0x4d` | 1100 (`11`) | 754 |
| 1352 | 1352 | /1 | /1 | `0x0d0000` | 1040 | 950 | 1012.5 | 1040 | `0x4a` | 1050 (`9`) | 676 |
| 1209 | 1209 | /1 | /1 | `0x0ba000` | 1000 | 900 | 962.5 | 1000 | `0x46` | 1025 (`8`) | 611 |
| 1092 | 1092 | /1 | /1 | `0x0a8000` | 970 | 850 | 912.5 | 970 | `0x43` | 1000 (`7`) | 533 |
| 962 | 1924 | /2 | /1 | `0x128000` | 940 | 820 | 882.5 | 940 | `0x40` | 1000 (`7`) | 481 |
| 832 | 1664 | /2 | /1 | `0x100000` | 900 | 790 | 852.5 | 900 | `0x3c` | 1000 (`7`) | 416 |
| 650 | 1300 | /2 | /1 | `0x0c8000` | 850 | 790 | 852.5 | 860 | `0x38` | 1000 (`7`) | 325 |
| 468 | 1872 | /2 | /2 | `0x120000` | 800 | 790 | 852.5 | 860 | `0x38` | 1000 (`7`) | 234 |
| 325 | 1300 | /2 | /2 | `0x0c8000` | 770 | 770 | 832.5 | 840 | `0x36` | 1000 (`7`) | 234 |

| CCI MHz | VCO MHz | post-div | divider | PCW | Base mV | EEM mV | +62.5 | Set mV | VPROC1 sel | VSRAM_L | CCI MHz |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 988 | 1976 | /2 | /1 | `0x130000` | 1200 | 1160 | 1222.5 | 1200 | `0x5a` | 1200 (`15`) |  |
| 975 | 1950 | /2 | /1 | `0x12c000` | 1190 | 1150 | 1212.5 | 1200 | `0x5a` | 1200 (`15`) |  |
| 936 | 1872 | /2 | /1 | `0x120000` | 1170 | 1130 | 1192.5 | 1200 | `0x5a` | 1200 (`15`) |  |
| 910 | 1820 | /2 | /1 | `0x118000` | 1150 | 1120 | 1182.5 | 1190 | `0x59` | 1200 (`15`) |  |
| 884 | 1768 | /2 | /1 | `0x110000` | 1140 | 1100 | 1162.5 | 1170 | `0x57` | 1200 (`15`) |  |
| 845 | 1690 | /2 | /1 | `0x104000` | 1130 | 1080 | 1142.5 | 1150 | `0x55` | 1175 (`14`) |  |
| 819 | 1638 | /2 | /1 | `0x0fc000` | 1100 | 1070 | 1132.5 | 1140 | `0x54` | 1150 (`13`) |  |
| 754 | 1508 | /2 | /1 | `0x0e8000` | 1070 | 1030 | 1092.5 | 1100 | `0x50` | 1125 (`12`) |  |
| 676 | 1352 | /2 | /1 | `0x0d0000` | 1040 | 990 | 1052.5 | 1060 | `0x4c` | 1075 (`10`) |  |
| 611 | 1222 | /2 | /1 | `0x0bc000` | 1000 | 950 | 1012.5 | 1020 | `0x48` | 1050 (`9`) |  |
| 533 | 1066 | /2 | /1 | `0x0a4000` | 970 | 900 | 962.5 | 970 | `0x43` | 1000 (`7`) |  |
| 481 | 1924 | /2 | /2 | `0x128000` | 940 | 870 | 932.5 | 940 | `0x40` | 1000 (`7`) |  |
| 416 | 1664 | /2 | /2 | `0x100000` | 900 | 840 | 902.5 | 910 | `0x3d` | 1000 (`7`) |  |
| 325 | 1300 | /2 | /2 | `0x0c8000` | 850 | 820 | 882.5 | 890 | `0x3b` | 1000 (`7`) |  |
| 234 | 1872 | /2 | /4 | `0x120000` | 800 | 790 | 852.5 | 860 | `0x38` | 1000 (`7`) |  |

The CCI's 169 MHz point is left out: the firmware leaves its sync DCM divider at
3, which needs at least 210 MHz (A53 cpufreq
[A1](../2026-11-07-mt6797-a53-cpufreq/README.md#a1)). LL and L points that map to
it require 234 MHz instead. VPROC1 is shared, so the rail is the highest of the
three consumers' requests; the CCI point at the same vendor index is often
10-20 mV above the cluster's.

### Open question: VSRAM_L below VPROC1 0.97 V

Gemian's manual path clamps VSRAM_L to at least 1.0 V but also asserts that it
is at most 30 mV above VPROC1, so that path would `BUG()` below VPROC1 0.97 V.
On the live unit those points run through the CSPM PCM firmware instead, whose
VSRAM_L choice there is not known. This tree keeps VSRAM_L at 1.0 V below that
point, up to 230 mV above VPROC1 at 221 MHz. The MediaTek upstream coupler
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
   selector 7-15 (1000-1200 mV). `0x10001f98` is not written.
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
5. V8 writes the `soc-thermal` zone's `emul_temp` (62000, then 0), as A53
   cpufreq t7.

No PMIC (MT6351), BUCKB, `0x5e`, VSRAM_B, A72 or secure call, and no write
outside the lists above.

### Limits

- VPROC1 770-1200 mV by constraint, 840-1200 mV in the tables; VSRAM_L
  1000-1200 mV; VSRAM_L never below VPROC1.
- CPU0-3 221-1547 MHz, CPU4-7 325-2002 MHz, CCI 234-988 MHz.
- SoC temperature: stop above 80 C. The 58 C passive trip caps both
  clusters; 95 C hot, 110 C critical and the 117 C hardware reset stay armed.
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

Each is one call; the custodian folds them into the test plan. "Read" means a
`devmem` read of a 32-bit word; DA9214 reads use `i2cget -fy 6 0x68 REG` (or
the regulator sysfs once bound). Run V0 on the current station image before
building anything on it.

| Test | Boot | What it does | Expected | Writes |
| --- | --- | --- | --- | --- |
| V0 | current station | Read `0x10001f98`, `0x10001f9c`, `0x10001fa0` and DA9214 `0xd7`, `0x5d`, `0xd9` | `CTRL_0` low byte `0xff`; `CTRL_1` = `CTRL_2` = code × `0x01010101` with code 7-15 (1.0-1.2 V); `0xd7` = `0x46` (1.00 V); VSRAM_L ≥ 1.00 V | none |
| V0g (optional, recommended) | Gemian | With the vendor `userspace` policy pin LL at 221 MHz and L at 325 MHz, then at 897/1209 MHz; at each, read `0x10001f9c` and CSPM `SW_RSV3`-`6` (`0x11015614`-`0x11015620`, `V_CURR`/`VS_CURR`) | The PCM's VPROC1 and VSRAM_L codes at the low and middle points; decides the 1.0 V floor question | none (read-only Gemian inspection) |
| V1 | new image, profile `mt6797-a53-station-dvfs`, DTB `station-dvfs` | A53 cpufreq t0 plus the V0 reads | As V0; cpufreq empty; all CPU0-7 online (blanking off) | boot2 |
| V2 | V1 | `insmod da9213-legacy-regulator.ko`, then `mt6797-vsram-regulator.ko`; read `/sys/class/regulator/*/{name,microvolts}` and `regulator_summary` | `DA9214 legacy direct-address identity matched; voltages are writable`; vproc1 1000000, vproc-big 1000000, vsram_l = V0 value; no write (selectors unchanged) | none |
| V3 | V1 | `insmod clk-mt6797-mcusys.ko`; debugfs `registers` | Three PLL lines: LL 897, L 1274 MHz, CCI ≈ 629.5 MHz, each "up to" 1547/2002/988 MHz; `faulted=0` | V3 list |
| V4 | V1 | `insmod cpufreq-dt.ko` (userspace) | policy0 0-3 221-1547 MHz, policy4 4-7 325-2002 MHz; L moves from its unlisted 1274 to 1352 MHz: VSRAM_L 1050, then VPROC1 1040 mV, then the clock; LL stays at 897 MHz/1000 mV | V4-V9 items 1-3 |
| V5 | V1 | CPU0-3 sweep: every LL point down then up, then 221↔1547 jumps; at each, measure CPU1 and CPU3, hash, read vproc1 and vsram_l | Clocks within 5 %, hashes equal, readbacks exactly the table, VSRAM_L ≥ VPROC1 | items 1-3 |
| V6 | V1 | CPU4-7 the same, 325-2002 MHz, including both post-divider crossings | As V5 | items 1-3 |
| V7 | V1 | `insmod mtk-cci-devfreq.ko`; step LL and L and read the devfreq `cur_freq` and the CCI PLL line; then schedutil on both, 10 s idle, 15 s of 8-CPU load, 10 s idle | CCI = the higher of the two clusters' mapped points; schedutil idles low and loads high; all load hashes equal; transitions counted | items 1-4 |
| V8 | V1 | Cooling: emulate 62 C, then release | Both policies' `scaling_max_freq` step down and come back | item 5 |
| V9 | V1 | Heat soak: 10 min of 8-CPU load under schedutil, sampling every 10 s the SoC temperature, both policies' frequencies, vproc1, vsram_l and hashes | The passive trip at 58 C caps the clusters and holds the SoC below 80 C; no hash difference. Pass opens the boot gate | items 1-3 |
| V10 | V1 | Energy model: on battery, per cluster, one busy CPU pinned at each point for 10 s, the rest idle; record the fuel gauge's average `current_now` and `voltage_now` against an idle baseline | Power per point for `dynamic-power-coefficient` (mW = C × MHz × V² / 10⁶) and the capacity ratio from a fixed workload's time per MHz | items 1-3 |
| V11 | new boot, same image | Create `/mnt/data/cpufreq-at-boot`; power off; owner selects boot2 | Station status `cpufreq=loaded,da9213-legacy-regulator,mt6797-vsram-regulator,clk-mt6797-mcusys,cpufreq-dt,mtk-cci-devfreq`; schedutil on both policies | items 1-4 at boot |

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

## Analysis

Pending.

## Conclusion

Pending.
